"""Gmail OAuth2 service — token management, email fetch/parse, polling, auto-reply."""

import asyncio
import base64
import json
import logging
import secrets
import traceback
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import async_session
from backend.models.gmail_message import ProcessedGmailMessage
from backend.models.gmail_token import GmailToken
from backend.models.log import Log
from backend.schemas import TaskCreate

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# Refresh tokens proactively this many seconds before they expire.
_TOKEN_REFRESH_BUFFER = 300  # 5 minutes

SCOPES = " ".join([
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
])

AUTO_REPLY_TEMPLATE = (
    "Thank you for your email. This message has been received and logged "
    "by the Digital FTE system. A team member will follow up if needed."
)


# ---------------------------------------------------------------------------
# HTTP helper with exponential backoff retry
# ---------------------------------------------------------------------------

async def _http_with_retry(
    method: str,
    url: str,
    *,
    headers: dict | None = None,
    params: dict | None = None,
    json_body: dict | None = None,
    form_data: dict | None = None,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> httpx.Response:
    """Execute an HTTP request with exponential backoff on network errors and 5xx/429."""
    delay = base_delay
    last_exc: Exception | None = None
    resp: httpx.Response | None = None

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=json_body,
                    data=form_data,
                )

            # Retry on rate-limit or server errors (not on final attempt)
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt < max_retries - 1:
                    logger.warning(
                        "HTTP %s %s returned %d; retrying in %.1fs (attempt %d/%d)",
                        method, url, resp.status_code, delay, attempt + 1, max_retries,
                    )
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
            return resp

        except (httpx.NetworkError, httpx.TimeoutException) as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                logger.warning(
                    "HTTP %s %s failed with %s; retrying in %.1fs (attempt %d/%d)",
                    method, url, exc, delay, attempt + 1, max_retries,
                    exc_info=True,
                )
                await asyncio.sleep(delay)
                delay *= 2
            else:
                logger.error(
                    "HTTP %s %s failed after %d attempts:\n%s",
                    method, url, max_retries, traceback.format_exc(),
                )
                raise

    # Final attempt returned a bad status — return it so callers can decide
    assert resp is not None
    return resp


# ---------------------------------------------------------------------------
# Internal logging helper
# ---------------------------------------------------------------------------

async def _log(
    db: AsyncSession,
    action: str,
    details: dict,
    task_id: int | None = None,
) -> None:
    """Persist an activity log entry to the database."""
    entry = Log(action=action, details=json.dumps(details), task_id=task_id)
    db.add(entry)
    await db.flush()


# ---------------------------------------------------------------------------
# OAuth state management
# ---------------------------------------------------------------------------

async def generate_state_token(db: AsyncSession) -> str:
    """Create a random state token and store it in a pending GmailToken row."""
    state = secrets.token_urlsafe(32)
    token_row = GmailToken(state_token=state)
    db.add(token_row)
    await db.flush()
    return state


async def verify_state_token(state: str, db: AsyncSession) -> GmailToken | None:
    """Validate state against the DB and return the matching row."""
    result = await db.execute(
        select(GmailToken).where(GmailToken.state_token == state)
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Token exchange + refresh
# ---------------------------------------------------------------------------

async def exchange_code(code: str, token_row: GmailToken, db: AsyncSession) -> GmailToken:
    """Exchange authorization code for access + refresh tokens, store in DB."""
    resp = await _http_with_retry(
        "POST",
        GOOGLE_TOKEN_URL,
        form_data={
            "code": code,
            "client_id": settings.GMAIL_CLIENT_ID,
            "client_secret": settings.GMAIL_CLIENT_SECRET,
            "redirect_uri": settings.GMAIL_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
    )
    resp.raise_for_status()
    data = resp.json()

    token_row.access_token = data["access_token"]
    token_row.refresh_token = data.get("refresh_token", token_row.refresh_token)
    expires_in = data.get("expires_in", 3600)
    token_row.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    token_row.state_token = ""  # consumed

    # Fetch user email
    info = await _http_with_retry(
        "GET",
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {token_row.access_token}"},
    )
    if info.status_code == 200:
        token_row.email_address = info.json().get("email", "")

    await db.flush()
    return token_row


async def _refresh_access_token(token_row: GmailToken, db: AsyncSession) -> str:
    """Use refresh_token to obtain a new access_token and persist it."""
    resp = await _http_with_retry(
        "POST",
        GOOGLE_TOKEN_URL,
        form_data={
            "client_id": settings.GMAIL_CLIENT_ID,
            "client_secret": settings.GMAIL_CLIENT_SECRET,
            "refresh_token": token_row.refresh_token,
            "grant_type": "refresh_token",
        },
    )
    resp.raise_for_status()
    data = resp.json()

    token_row.access_token = data["access_token"]
    expires_in = data.get("expires_in", 3600)
    token_row.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    await db.flush()
    logger.info("Gmail access token refreshed for %s", token_row.email_address)
    return token_row.access_token


async def get_valid_token(db: AsyncSession) -> tuple[str, GmailToken] | None:
    """Load token from DB; refresh proactively if near/past expiry.

    Returns ``(access_token, token_row)`` or ``None`` if Gmail is not connected.
    """
    result = await db.execute(
        select(GmailToken)
        .where(GmailToken.access_token != "")
        .order_by(GmailToken.id.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if not row:
        return None

    now = datetime.now(timezone.utc)
    expiry = row.token_expiry
    if expiry and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    # Refresh if expired or within the proactive-refresh buffer window
    if expiry and now >= (expiry - timedelta(seconds=_TOKEN_REFRESH_BUFFER)):
        if not row.refresh_token:
            logger.error("Gmail token expired and no refresh_token available.")
            return None
        try:
            token = await _refresh_access_token(row, db)
            return token, row
        except Exception:
            logger.error(
                "Failed to refresh Gmail access token:\n%s", traceback.format_exc()
            )
            return None

    return row.access_token, row


# ---------------------------------------------------------------------------
# Email operations (Gmail REST API)
# ---------------------------------------------------------------------------

async def fetch_unread_emails(access_token: str, max_results: int = 10) -> list[dict]:
    """Fetch unread emails from Gmail. Returns list of parsed message dicts."""
    messages: list[dict] = []

    list_resp = await _http_with_retry(
        "GET",
        f"{GMAIL_API_BASE}/messages",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"q": "is:unread", "maxResults": max_results},
    )
    list_resp.raise_for_status()
    msg_refs = list_resp.json().get("messages", [])

    for msg_ref in msg_refs:
        msg_resp = await _http_with_retry(
            "GET",
            f"{GMAIL_API_BASE}/messages/{msg_ref['id']}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"format": "full"},
        )
        if msg_resp.status_code != 200:
            logger.warning(
                "Failed to fetch Gmail message %s: HTTP %d",
                msg_ref["id"], msg_resp.status_code,
            )
            continue
        parsed = _parse_message(msg_resp.json())
        if parsed:
            messages.append(parsed)

    return messages


def _parse_message(raw: dict) -> dict | None:
    """Extract id, subject, sender, body from a Gmail message resource."""
    headers = {
        h["name"].lower(): h["value"]
        for h in raw.get("payload", {}).get("headers", [])
    }
    subject = headers.get("subject", "(no subject)")
    sender = headers.get("from", "unknown")
    thread_id = raw.get("threadId", "")
    message_id = headers.get("message-id", "")
    body = _extract_body(raw.get("payload", {}))
    return {
        "id": raw["id"],
        "thread_id": thread_id,
        "message_id": message_id,
        "subject": subject,
        "sender": sender,
        "body": body,
    }


def _extract_body(payload: dict) -> str:
    """Walk MIME parts and extract text/plain body, base64url-decoded."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return _b64url_decode(payload["body"]["data"])

    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return _b64url_decode(part["body"]["data"])
        if part.get("parts"):
            result = _extract_body(part)
            if result:
                return result

    # Fallback to HTML
    if payload.get("mimeType") == "text/html" and payload.get("body", {}).get("data"):
        return _b64url_decode(payload["body"]["data"])
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
            return _b64url_decode(part["body"]["data"])

    return ""


def _b64url_decode(data: str) -> str:
    """Decode base64url string to UTF-8 text."""
    padded = data + "=" * (4 - len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


async def mark_as_read(access_token: str, message_id: str) -> None:
    """Remove UNREAD label from a message."""
    await _http_with_retry(
        "POST",
        f"{GMAIL_API_BASE}/messages/{message_id}/modify",
        headers={"Authorization": f"Bearer {access_token}"},
        json_body={"removeLabelIds": ["UNREAD"]},
    )


async def send_reply(access_token: str, original_msg: dict, reply_text: str) -> bool:
    """Send an RFC 2822 reply to the original message via Gmail API."""
    reply = MIMEText(reply_text)
    reply["To"] = original_msg["sender"]
    reply["Subject"] = f"Re: {original_msg['subject']}"
    reply["In-Reply-To"] = original_msg.get("message_id", "")
    reply["References"] = original_msg.get("message_id", "")

    raw_msg = base64.urlsafe_b64encode(reply.as_bytes()).decode("ascii")

    resp = await _http_with_retry(
        "POST",
        f"{GMAIL_API_BASE}/messages/send",
        headers={"Authorization": f"Bearer {access_token}"},
        json_body={"raw": raw_msg, "threadId": original_msg.get("thread_id", "")},
    )
    return resp.status_code == 200


# ---------------------------------------------------------------------------
# Duplicate-prevention helpers
# ---------------------------------------------------------------------------

async def _is_duplicate(db: AsyncSession, gmail_id: str) -> bool:
    """Return True if this Gmail message ID has already been processed."""
    result = await db.execute(
        select(ProcessedGmailMessage).where(
            ProcessedGmailMessage.gmail_message_id == gmail_id
        )
    )
    return result.scalar_one_or_none() is not None


async def _mark_processed(db: AsyncSession, gmail_id: str) -> None:
    """Record this Gmail message ID as processed to block future duplicates."""
    db.add(ProcessedGmailMessage(gmail_message_id=gmail_id))
    await db.flush()


# ---------------------------------------------------------------------------
# Main polling function
# ---------------------------------------------------------------------------

async def poll_inbox(db: AsyncSession) -> dict:
    """Poll Gmail for unread emails, create tasks, and optionally auto-reply."""
    from backend.services.task_service import create_task
    from backend.core.enums import TaskStatus

    result = {"processed": 0, "tasks_created": 0, "auto_replied": 0, "errors": []}

    token_info = await get_valid_token(db)
    if not token_info:
        result["errors"].append("Gmail not connected")
        return result

    access_token, token_row = token_info
    emails = await fetch_unread_emails(access_token, settings.GMAIL_MAX_EMAILS_PER_POLL)

    for email in emails:
        gmail_id = email.get("id", "")
        try:
            # ── Duplicate prevention ─────────────────────────────────────────
            if await _is_duplicate(db, gmail_id):
                logger.debug("Skipping already-processed Gmail message %s", gmail_id)
                await mark_as_read(access_token, gmail_id)
                continue

            # ── Create task ──────────────────────────────────────────────────
            task_data = TaskCreate(
                title=f"[Gmail] {email['subject'][:450]}",
                body=f"From: {email['sender']}\n\n{email['body'][:5000]}",
                source="gmail",
            )
            task = await create_task(db, task_data)
            result["tasks_created"] += 1

            # Record ID immediately so a crash mid-loop can't reprocess later
            await _mark_processed(db, gmail_id)

            # ── Auto-reply ───────────────────────────────────────────────────
            should_reply = (
                settings.GMAIL_AUTO_REPLY_ENABLED
                and task.status == TaskStatus.IN_PROGRESS.value
            )
            if should_reply:
                from backend.services.reasoner import generate_reply
                reply_text = await generate_reply(task)
                sent = await send_reply(access_token, email, reply_text)
                if sent:
                    result["auto_replied"] += 1
                    await _log(db, "gmail_auto_reply_sent", {
                        "gmail_id": gmail_id,
                        "to": email["sender"],
                        "task_id": task.id,
                        "reply_text": reply_text[:200],
                    }, task.id)

            await mark_as_read(access_token, gmail_id)
            result["processed"] += 1

            await _log(db, "gmail_email_ingested", {
                "gmail_id": gmail_id,
                "subject": email["subject"],
                "sender": email["sender"],
                "task_id": task.id,
                "task_status": task.status,
                "auto_replied": should_reply,
            }, task.id)

        except Exception as e:
            logger.error(
                "Error processing Gmail message %s: %s\n%s",
                gmail_id, e, traceback.format_exc(),
            )
            result["errors"].append(f"Email {gmail_id}: {str(e)}")

    token_row.last_polled_at = datetime.now(timezone.utc)
    await db.flush()
    return result


# ---------------------------------------------------------------------------
# Background polling loop with graceful shutdown
# ---------------------------------------------------------------------------

async def run_gmail_poll_loop(shutdown_event: asyncio.Event | None = None) -> None:
    """Poll Gmail inbox on a fixed interval.

    Args:
        shutdown_event: When set, the loop exits cleanly without waiting for
                        the next full poll cycle.  If omitted a private event
                        is used (the loop then only stops on task cancellation).
    """
    _stop = shutdown_event or asyncio.Event()
    interval = settings.GMAIL_POLL_INTERVAL_SECONDS
    logger.info("Gmail poll loop starting (interval=%ds)", interval)

    while not _stop.is_set():
        try:
            async with async_session() as db:
                token_info = await get_valid_token(db)
                if token_info:
                    summary = await poll_inbox(db)
                    await db.commit()
                    logger.info(
                        "Gmail poll complete — processed=%d tasks=%d "
                        "auto_replied=%d errors=%d",
                        summary["processed"],
                        summary["tasks_created"],
                        summary["auto_replied"],
                        len(summary["errors"]),
                    )
                    for err in summary["errors"]:
                        logger.warning("Poll error detail: %s", err)

        except asyncio.CancelledError:
            logger.info("Gmail poll loop cancelled.")
            raise
        except Exception:
            logger.error(
                "Unhandled exception in Gmail poll loop:\n%s",
                traceback.format_exc(),
            )

        # Wait for next cycle; exit immediately if shutdown is signalled
        try:
            await asyncio.wait_for(_stop.wait(), timeout=float(interval))
        except asyncio.TimeoutError:
            pass  # Normal — move on to next poll

    logger.info("Gmail poll loop stopped.")
