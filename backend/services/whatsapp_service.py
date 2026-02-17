"""WhatsApp service — Twilio client, send with retry, dedup, and inbox polling."""

import asyncio
import json
import logging
import traceback
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import async_session
from backend.core.enums import TaskStatus
from backend.models.log import Log
from backend.models.whatsapp_message import ProcessedWhatsappMessage
from backend.schemas import TaskCreate

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Twilio client — lazy module-level singleton
# ---------------------------------------------------------------------------

_client = None  # twilio.rest.Client


def _get_client():
    """Return a cached Twilio Client, initialising it on first call."""
    global _client
    if _client is None and settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
        try:
            from twilio.rest import Client
            _client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            logger.info("Twilio client initialised.")
        except Exception:
            logger.error("Failed to initialise Twilio client:\n%s", traceback.format_exc())
    return _client


def _wa_number(number: str) -> str:
    """Normalise a phone number to whatsapp:+XXXXXXXXXX format."""
    return number if number.startswith("whatsapp:") else f"whatsapp:{number}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _log(
    db: AsyncSession,
    action: str,
    details: dict,
    task_id: int | None = None,
) -> None:
    """Persist an activity log entry to the database."""
    db.add(Log(action=action, details=json.dumps(details), task_id=task_id))
    await db.flush()


async def _is_duplicate(db: AsyncSession, message_sid: str) -> bool:
    """Return True if this Twilio SID has already been processed."""
    result = await db.execute(
        select(ProcessedWhatsappMessage).where(
            ProcessedWhatsappMessage.message_sid == message_sid
        )
    )
    return result.scalar_one_or_none() is not None


async def _mark_processed(db: AsyncSession, message_sid: str) -> None:
    """Record this Twilio SID as processed to block future duplicates."""
    db.add(ProcessedWhatsappMessage(message_sid=message_sid))
    await db.flush()


# ---------------------------------------------------------------------------
# Send with exponential backoff retry
# ---------------------------------------------------------------------------

async def send_message(to: str, body: str, max_retries: int = 3) -> bool:
    """Send a WhatsApp message via Twilio with exponential backoff retry."""
    client = _get_client()
    if not client:
        logger.error("WhatsApp send skipped — Twilio client not available.")
        return False

    from_number = _wa_number(settings.TWILIO_PHONE_NUMBER)
    to_number = _wa_number(to)
    delay = 1.0

    for attempt in range(max_retries):
        try:
            msg = await asyncio.to_thread(
                client.messages.create,
                from_=from_number,
                body=body,
                to=to_number,
            )
            logger.info("WhatsApp sent to %s — SID %s", to, msg.sid)
            return True

        except Exception as exc:
            # Non-retryable 4xx errors (except 429 rate-limit)
            try:
                from twilio.base.exceptions import TwilioRestException
                if (
                    isinstance(exc, TwilioRestException)
                    and exc.status
                    and 400 <= exc.status < 500
                    and exc.status != 429
                ):
                    logger.error(
                        "WhatsApp send failed (non-retryable HTTP %d): %s",
                        exc.status, exc, exc_info=True,
                    )
                    return False
            except ImportError:
                pass

            if attempt < max_retries - 1:
                logger.warning(
                    "WhatsApp send attempt %d/%d failed: %s — retrying in %.1fs",
                    attempt + 1, max_retries, exc, delay, exc_info=True,
                )
                await asyncio.sleep(delay)
                delay *= 2
            else:
                logger.error(
                    "WhatsApp send failed after %d attempts:\n%s",
                    max_retries, traceback.format_exc(),
                )

    return False


# ---------------------------------------------------------------------------
# Process a single inbound message (used by both webhook and poll paths)
# ---------------------------------------------------------------------------

async def process_incoming_message(
    db: AsyncSession,
    message_sid: str,
    sender: str,
    body: str,
) -> dict:
    """Deduplicate, create task, optionally auto-reply, and log one inbound message.

    Returns a result dict with keys: processed, task_id, auto_replied, skipped_duplicate.
    """
    from backend.services.task_service import create_task

    result = {
        "processed": False,
        "task_id": None,
        "auto_replied": False,
        "skipped_duplicate": False,
    }

    # ── Duplicate prevention ─────────────────────────────────────────────────
    if message_sid and await _is_duplicate(db, message_sid):
        logger.debug("Skipping duplicate WhatsApp SID %s", message_sid)
        result["skipped_duplicate"] = True
        return result

    # ── Create task ──────────────────────────────────────────────────────────
    task_data = TaskCreate(
        title=f"[WhatsApp] Message from {sender}",
        body=f"Sender: {sender}\n\n{body}",
        source="whatsapp",
    )
    task = await create_task(db, task_data)
    result["task_id"] = task.id

    # Record SID immediately so a crash mid-flow can't reprocess later
    if message_sid:
        await _mark_processed(db, message_sid)

    # ── Auto-reply ───────────────────────────────────────────────────────────
    if task.status == TaskStatus.IN_PROGRESS.value:
        reply = (
            "Thanks for your message! I've logged this as a task "
            "and will get back to you shortly."
        )
        sent = await send_message(sender, reply)
        if sent:
            result["auto_replied"] = True
            await _log(db, "whatsapp_auto_reply_sent", {
                "message_sid": message_sid,
                "to": sender,
                "task_id": task.id,
                "reply": reply,
            }, task.id)

    elif task.status == TaskStatus.AWAITING_APPROVAL.value:
        reply = (
            "I've received your request. Since it involves sensitive actions, "
            "I'll need supervisor approval before proceeding."
        )
        await send_message(sender, reply)
        await _log(db, "whatsapp_approval_required", {
            "message_sid": message_sid,
            "sender": sender,
            "task_id": task.id,
        }, task.id)

    await _log(db, "whatsapp_message_ingested", {
        "message_sid": message_sid,
        "sender": sender,
        "task_id": task.id,
        "task_status": task.status,
    }, task.id)

    result["processed"] = True
    return result


# ---------------------------------------------------------------------------
# Fallback inbox poll (catches messages missed by webhook delivery failures)
# ---------------------------------------------------------------------------

_last_poll_at: datetime | None = None


async def poll_inbox(db: AsyncSession) -> dict:
    """Query Twilio for recent inbound messages as a fallback for missed webhooks.

    Messages already tracked in processed_whatsapp_messages are silently skipped.
    """
    global _last_poll_at

    summary = {"processed": 0, "tasks_created": 0, "auto_replied": 0, "errors": []}

    client = _get_client()
    if not client:
        summary["errors"].append("Twilio client not available")
        return summary

    if not settings.TWILIO_PHONE_NUMBER:
        summary["errors"].append("TWILIO_PHONE_NUMBER not configured")
        return summary

    # Look back 2× the poll interval to avoid gaps at the boundary
    since = _last_poll_at or (
        datetime.now(timezone.utc)
        - timedelta(seconds=settings.WHATSAPP_POLL_INTERVAL_SECONDS * 2)
    )
    poll_start = datetime.now(timezone.utc)

    try:
        messages = await asyncio.to_thread(
            client.messages.list,
            date_sent_after=since,
            limit=settings.WHATSAPP_MAX_MESSAGES_PER_POLL,
        )
    except Exception:
        logger.error("Failed to list Twilio messages:\n%s", traceback.format_exc())
        summary["errors"].append("Twilio messages.list() failed")
        return summary

    # Keep only inbound messages, process oldest first (FIFO)
    inbound = sorted(
        [m for m in messages if m.direction == "inbound"],
        key=lambda m: m.date_sent or datetime.min.replace(tzinfo=timezone.utc),
    )

    for msg in inbound:
        try:
            result = await process_incoming_message(
                db, msg.sid, msg.from_ or "", msg.body or ""
            )
            if result["skipped_duplicate"]:
                continue
            if result["processed"]:
                summary["processed"] += 1
                summary["tasks_created"] += 1
            if result["auto_replied"]:
                summary["auto_replied"] += 1
        except Exception:
            logger.error(
                "Error processing WhatsApp SID %s:\n%s",
                msg.sid, traceback.format_exc(),
            )
            summary["errors"].append(f"SID {msg.sid}: processing error")

    _last_poll_at = poll_start
    return summary


# ---------------------------------------------------------------------------
# Background polling loop with graceful shutdown
# ---------------------------------------------------------------------------

async def run_whatsapp_poll_loop(shutdown_event: asyncio.Event | None = None) -> None:
    """Poll Twilio for missed inbound messages on a fixed interval.

    Args:
        shutdown_event: When set, the loop exits at the next check without
                        waiting the full poll cycle.
    """
    _stop = shutdown_event or asyncio.Event()
    interval = settings.WHATSAPP_POLL_INTERVAL_SECONDS
    logger.info("WhatsApp poll loop starting (interval=%ds)", interval)

    while not _stop.is_set():
        try:
            async with async_session() as db:
                summary = await poll_inbox(db)
                await db.commit()
                logger.info(
                    "WhatsApp poll complete — processed=%d tasks=%d "
                    "auto_replied=%d errors=%d",
                    summary["processed"],
                    summary["tasks_created"],
                    summary["auto_replied"],
                    len(summary["errors"]),
                )
                for err in summary["errors"]:
                    logger.warning("WhatsApp poll error detail: %s", err)

        except asyncio.CancelledError:
            logger.info("WhatsApp poll loop cancelled.")
            raise
        except Exception:
            logger.error(
                "Unhandled exception in WhatsApp poll loop:\n%s",
                traceback.format_exc(),
            )

        # Wait for next cycle; wake immediately on shutdown signal
        try:
            await asyncio.wait_for(_stop.wait(), timeout=float(interval))
        except asyncio.TimeoutError:
            pass  # Normal — continue to next poll

    logger.info("WhatsApp poll loop stopped.")
