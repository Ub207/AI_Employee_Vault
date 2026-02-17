"""LinkedIn OAuth2 service — token management, posting, and health polling."""

import asyncio
import json
import logging
import traceback
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import async_session
from backend.models.linkedin_post import ProcessedLinkedInPost
from backend.models.log import Log
from backend.models.token import Token

logger = logging.getLogger(__name__)

LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_API_BASE = "https://api.linkedin.com/v2"
LINKEDIN_UGC_URL = "https://api.linkedin.com/v2/ugcPosts"

# Refresh tokens proactively this many seconds before they expire.
_TOKEN_REFRESH_BUFFER = 300  # 5 minutes


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

    assert resp is not None
    return resp


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


async def _is_duplicate_post(db: AsyncSession, post_id: str) -> bool:
    """Return True if this LinkedIn post ID has already been published."""
    result = await db.execute(
        select(ProcessedLinkedInPost).where(ProcessedLinkedInPost.post_id == post_id)
    )
    return result.scalar_one_or_none() is not None


async def _mark_post_processed(db: AsyncSession, post_id: str) -> None:
    """Record this LinkedIn post ID to prevent future duplicate posts."""
    db.add(ProcessedLinkedInPost(post_id=post_id))
    await db.flush()


# ---------------------------------------------------------------------------
# Token management
# ---------------------------------------------------------------------------

async def save_credentials(
    db: AsyncSession,
    access_token: str,
    expires_in: int,
    refresh_token: str | None = None,
) -> Token:
    """Upsert LinkedIn OAuth credentials in the Token table."""
    result = await db.execute(select(Token).where(Token.provider == "linkedin"))
    token_row = result.scalars().first()

    expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    if token_row:
        token_row.access_token = access_token
        if refresh_token:
            token_row.refresh_token = refresh_token
        token_row.expiry = expiry
    else:
        token_row = Token(
            provider="linkedin",
            access_token=access_token,
            refresh_token=refresh_token,
            expiry=expiry,
        )
        db.add(token_row)

    await db.flush()
    logger.info("LinkedIn credentials saved (expires %s)", expiry.isoformat())
    return token_row


async def _refresh_access_token(token_row: Token, db: AsyncSession) -> str | None:
    """Attempt to obtain a new access token using the stored refresh_token."""
    if not token_row.refresh_token:
        logger.warning(
            "LinkedIn token expired and no refresh_token available — "
            "user must re-authenticate via /integrations/linkedin/auth"
        )
        return None

    try:
        resp = await _http_with_retry(
            "POST",
            LINKEDIN_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            form_data={
                "grant_type": "refresh_token",
                "refresh_token": token_row.refresh_token,
                "client_id": settings.LINKEDIN_CLIENT_ID,
                "client_secret": settings.LINKEDIN_CLIENT_SECRET,
            },
        )
    except Exception:
        logger.error(
            "LinkedIn token refresh request failed:\n%s", traceback.format_exc()
        )
        return None

    if resp.status_code != 200:
        logger.error(
            "LinkedIn token refresh failed (HTTP %d): %s",
            resp.status_code, resp.text,
        )
        return None

    data = resp.json()
    token_row.access_token = data["access_token"]
    expires_in = data.get("expires_in", 5184000)  # LinkedIn default: 60 days
    token_row.expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    if data.get("refresh_token"):
        token_row.refresh_token = data["refresh_token"]
    await db.flush()
    logger.info("LinkedIn access token refreshed successfully.")
    return token_row.access_token


async def get_valid_token(db: AsyncSession) -> tuple[str, Token] | None:
    """Return (access_token, token_row), refreshing proactively if near/past expiry."""
    result = await db.execute(select(Token).where(Token.provider == "linkedin"))
    token_row = result.scalars().first()
    if not token_row or not token_row.access_token:
        return None

    now = datetime.now(timezone.utc)
    expiry = token_row.expiry
    if expiry and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    if expiry and now >= (expiry - timedelta(seconds=_TOKEN_REFRESH_BUFFER)):
        token = await _refresh_access_token(token_row, db)
        if not token:
            return None
        return token, token_row

    return token_row.access_token, token_row


# ---------------------------------------------------------------------------
# LinkedIn API operations
# ---------------------------------------------------------------------------

async def get_user_urn(access_token: str) -> str | None:
    """Fetch the authenticated user's LinkedIn URN."""
    try:
        resp = await _http_with_retry(
            "GET",
            f"{LINKEDIN_API_BASE}/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    except Exception:
        logger.error("Failed to fetch LinkedIn user URN:\n%s", traceback.format_exc())
        return None

    if resp.status_code == 200:
        return f"urn:li:person:{resp.json()['id']}"

    logger.error(
        "Failed to get LinkedIn user URN (HTTP %d): %s",
        resp.status_code, resp.text,
    )
    return None


async def post_text(db: AsyncSession, text: str) -> bool:
    """Post a text update to LinkedIn with retry and duplicate-post prevention."""
    token_info = await get_valid_token(db)
    if not token_info:
        logger.error("LinkedIn post skipped — no valid token.")
        return False

    access_token, _ = token_info
    urn = await get_user_urn(access_token)
    if not urn:
        return False

    payload = {
        "author": urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }

    try:
        resp = await _http_with_retry(
            "POST",
            LINKEDIN_UGC_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json_body=payload,
        )
    except Exception:
        logger.error("LinkedIn ugcPosts request failed:\n%s", traceback.format_exc())
        await _log(db, "linkedin_post_failed", {"error": "request exception", "text": text[:200]})
        return False

    if resp.status_code == 201:
        post_id = resp.json().get("id", "")
        logger.info("Posted to LinkedIn — ID %s", post_id)
        if post_id:
            await _mark_post_processed(db, post_id)
        await _log(db, "linkedin_post_published", {
            "post_id": post_id,
            "text": text[:200],
        })
        return True

    logger.error(
        "LinkedIn post failed (HTTP %d):\n%s", resp.status_code, resp.text
    )
    await _log(db, "linkedin_post_failed", {
        "status": resp.status_code,
        "error": resp.text[:500],
    })
    return False


# ---------------------------------------------------------------------------
# Token health poll
# ---------------------------------------------------------------------------

async def poll_token_health(db: AsyncSession) -> dict:
    """Verify the LinkedIn token is still accepted; refresh proactively if near expiry."""
    summary = {"healthy": False, "refreshed": False, "errors": []}

    token_info = await get_valid_token(db)
    if not token_info:
        summary["errors"].append(
            "No valid LinkedIn token — re-authentication required"
        )
        return summary

    access_token, _ = token_info

    try:
        resp = await _http_with_retry(
            "GET",
            f"{LINKEDIN_API_BASE}/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    except Exception:
        summary["errors"].append("LinkedIn /me request failed")
        logger.error("LinkedIn health check request failed:\n%s", traceback.format_exc())
        return summary

    if resp.status_code == 200:
        summary["healthy"] = True
        logger.debug("LinkedIn token health check: OK")
    elif resp.status_code == 401:
        summary["errors"].append(
            "LinkedIn token rejected (401) — re-authentication required"
        )
        logger.warning("LinkedIn token health check: INVALID (401)")
    else:
        summary["errors"].append(
            f"LinkedIn health check returned HTTP {resp.status_code}"
        )
        logger.warning("LinkedIn token health check returned HTTP %d", resp.status_code)

    return summary


# ---------------------------------------------------------------------------
# Background polling loop with graceful shutdown
# ---------------------------------------------------------------------------

async def run_linkedin_poll_loop(shutdown_event: asyncio.Event | None = None) -> None:
    """Periodically verify LinkedIn token health and refresh proactively.

    Args:
        shutdown_event: When set, the loop exits without waiting a full cycle.
    """
    _stop = shutdown_event or asyncio.Event()
    interval = settings.LINKEDIN_POLL_INTERVAL_SECONDS
    logger.info("LinkedIn poll loop starting (interval=%ds)", interval)

    while not _stop.is_set():
        try:
            async with async_session() as db:
                summary = await poll_token_health(db)
                await db.commit()
                if not summary["healthy"]:
                    for err in summary["errors"]:
                        logger.warning("LinkedIn health: %s", err)

        except asyncio.CancelledError:
            logger.info("LinkedIn poll loop cancelled.")
            raise
        except Exception:
            logger.error(
                "Unhandled exception in LinkedIn poll loop:\n%s",
                traceback.format_exc(),
            )

        # Wait for next cycle; exit immediately on shutdown signal
        try:
            await asyncio.wait_for(_stop.wait(), timeout=float(interval))
        except asyncio.TimeoutError:
            pass  # Normal — continue to next poll

    logger.info("LinkedIn poll loop stopped.")
