"""Gmail OAuth2 service — token management, email fetch/parse, polling, auto-reply."""

import asyncio
import base64
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

import httpx
from sqlalchemy import select

from backend.config import settings
from backend.database import async_session
from backend.models.gmail_token import GmailToken
from backend.models.log import Log
from backend.schemas import TaskCreate

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

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
# OAuth state management
# ---------------------------------------------------------------------------

async def generate_state_token(db) -> str:
    """Create a random state token and store it in a pending GmailToken row."""
    state = secrets.token_urlsafe(32)
    token_row = GmailToken(state_token=state)
    db.add(token_row)
    await db.flush()
    return state


async def verify_state_token(state: str, db) -> GmailToken | None:
    """Validate state against the DB and return the matching row."""
    result = await db.execute(
        select(GmailToken).where(GmailToken.state_token == state)
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Token exchange + refresh
# ---------------------------------------------------------------------------

async def exchange_code(code: str, token_row: GmailToken, db) -> GmailToken:
    """Exchange authorization code for access + refresh tokens, store in DB."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.GMAIL_CLIENT_ID,
            "client_secret": settings.GMAIL_CLIENT_SECRET,
            "redirect_uri": settings.GMAIL_REDIRECT_URI,
            "grant_type": "authorization_code",
        })
        resp.raise_for_status()
        data = resp.json()

    token_row.access_token = data["access_token"]
    token_row.refresh_token = data.get("refresh_token", token_row.refresh_token)
    expires_in = data.get("expires_in", 3600)
    token_row.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    token_row.state_token = ""  # consumed

    # Fetch user email
    async with httpx.AsyncClient() as client:
        info = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token_row.access_token}"},
        )
        if info.status_code == 200:
            token_row.email_address = info.json().get("email", "")

    await db.flush()
    return token_row


async def _refresh_access_token(token_row: GmailToken, db) -> str:
    """Use refresh_token to get a new access_token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data={
            "client_id": settings.GMAIL_CLIENT_ID,
            "client_secret": settings.GMAIL_CLIENT_SECRET,
            "refresh_token": token_row.refresh_token,
            "grant_type": "refresh_token",
        })
        resp.raise_for_status()
        data = resp.json()

    token_row.access_token = data["access_token"]
    expires_in = data.get("expires_in", 3600)
    token_row.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    await db.flush()
    return token_row.access_token


async def get_valid_token(db) -> tuple[str, GmailToken] | None:
    """Load token from DB; refresh if expired. Returns (access_token, row) or None."""
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

    if expiry and now >= expiry:
        if not row.refresh_token:
            return None
        token = await _refresh_access_token(row, db)
        return token, row

    return row.access_token, row


# ---------------------------------------------------------------------------
# Email operations (Gmail REST API via httpx)
# ---------------------------------------------------------------------------

async def fetch_unread_emails(access_token: str, max_results: int = 10) -> list[dict]:
    """Fetch unread emails from Gmail. Returns list of parsed message dicts."""
    messages = []
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GMAIL_API_BASE}/messages",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"q": "is:unread", "maxResults": max_results},
        )
        resp.raise_for_status()
        msg_list = resp.json().get("messages", [])

        for msg_ref in msg_list:
            msg_resp = await client.get(
                f"{GMAIL_API_BASE}/messages/{msg_ref['id']}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"format": "full"},
            )
            if msg_resp.status_code != 200:
                continue
            raw = msg_resp.json()
            parsed = _parse_message(raw)
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
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{GMAIL_API_BASE}/messages/{message_id}/modify",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"removeLabelIds": ["UNREAD"]},
        )


async def send_reply(access_token: str, original_msg: dict, reply_text: str) -> bool:
    """Send an RFC2822 reply to the original message via Gmail API."""
    reply = MIMEText(reply_text)
    reply["To"] = original_msg["sender"]
    reply["Subject"] = f"Re: {original_msg['subject']}"
    reply["In-Reply-To"] = original_msg.get("message_id", "")
    reply["References"] = original_msg.get("message_id", "")

    raw_msg = base64.urlsafe_b64encode(reply.as_bytes()).decode("ascii")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GMAIL_API_BASE}/messages/send",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"raw": raw_msg, "threadId": original_msg.get("thread_id", "")},
        )
        return resp.status_code == 200


# ---------------------------------------------------------------------------
# Main polling function
# ---------------------------------------------------------------------------

async def poll_inbox(db) -> dict:
    """Poll Gmail for unread emails, create tasks, optionally auto-reply."""
    from backend.services.task_service import create_task

    result = {"processed": 0, "tasks_created": 0, "auto_replied": 0, "errors": []}

    token_info = await get_valid_token(db)
    if not token_info:
        result["errors"].append("Gmail not connected")
        return result

    access_token, token_row = token_info
    emails = await fetch_unread_emails(access_token, settings.GMAIL_MAX_EMAILS_PER_POLL)

    for email in emails:
        try:
            task_data = TaskCreate(
                title=f"[Gmail] {email['subject'][:450]}",
                body=f"From: {email['sender']}\n\n{email['body'][:5000]}",
                source="gmail",
            )
            task = await create_task(db, task_data)
            result["tasks_created"] += 1

            if settings.GMAIL_AUTO_REPLY_ENABLED and task.status == "in_progress":
                sent = await send_reply(access_token, email, AUTO_REPLY_TEMPLATE)
                if sent:
                    result["auto_replied"] += 1

            await mark_as_read(access_token, email["id"])
            result["processed"] += 1

            db.add(Log(
                action="gmail_email_ingested",
                details=json.dumps({
                    "gmail_id": email["id"],
                    "subject": email["subject"],
                    "sender": email["sender"],
                    "task_id": task.id,
                    "task_status": task.status,
                    "auto_replied": settings.GMAIL_AUTO_REPLY_ENABLED and task.status == "in_progress",
                }, default=str),
                task_id=task.id,
            ))
        except Exception as e:
            logger.error(f"Error processing email {email.get('id')}: {e}")
            result["errors"].append(f"Email {email.get('id')}: {str(e)}")

    token_row.last_polled_at = datetime.now(timezone.utc)
    await db.flush()

    return result


# ---------------------------------------------------------------------------
# Background polling loop
# ---------------------------------------------------------------------------

async def run_gmail_poll_loop() -> None:
    """Background loop that polls Gmail inbox at configured interval."""
    while True:
        try:
            async with async_session() as db:
                token_info = await get_valid_token(db)
                if token_info:
                    summary = await poll_inbox(db)
                    await db.commit()
                    if summary["processed"] > 0:
                        logger.info(
                            f"Gmail poll: {summary['processed']} processed, "
                            f"{summary['tasks_created']} tasks, "
                            f"{summary['auto_replied']} auto-replied"
                        )
        except Exception as e:
            logger.error(f"Gmail poll loop error: {e}")
        await asyncio.sleep(settings.GMAIL_POLL_INTERVAL_SECONDS)
