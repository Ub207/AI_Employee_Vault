"""Facebook & Instagram Graph API service — posting and summary generation."""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.token import Token
from backend.config import settings

logger = logging.getLogger(__name__)

# Facebook Graph API base
GRAPH_API_BASE = "https://graph.facebook.com/v21.0"

# Scopes needed: pages_manage_posts, pages_read_engagement, instagram_basic, instagram_content_publish
FACEBOOK_SCOPES = "pages_manage_posts,pages_read_engagement,instagram_basic,instagram_content_publish,publish_to_groups"


async def _http_with_retry(method: str, url: str, **kwargs) -> httpx.Response:
    """HTTP call with exponential backoff on transient errors."""
    async with httpx.AsyncClient(timeout=30) as client:
        for attempt in range(3):
            try:
                resp = await client.request(method, url, **kwargs)
                if resp.status_code in (429, 502, 503, 504) and attempt < 2:
                    await _sleep(2 ** attempt)
                    continue
                return resp
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                if attempt == 2:
                    raise
                logger.warning("HTTP %s %s attempt %d failed: %s", method, url, attempt + 1, exc)
                await _sleep(2 ** attempt)
    raise RuntimeError("Max retries exceeded")


async def _sleep(seconds: float) -> None:
    import asyncio
    await asyncio.sleep(seconds)


async def save_credentials(db: AsyncSession, access_token: str, expires_in: int,
                           page_id: str = "", instagram_id: str = "") -> Token:
    """Persist Facebook/Instagram token to DB."""
    result = await db.execute(select(Token).where(Token.provider == "facebook"))
    token_row = result.scalars().first()
    expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    if token_row:
        token_row.access_token = access_token
        token_row.expiry = expiry
        token_row.meta = {"page_id": page_id, "instagram_id": instagram_id}
    else:
        token_row = Token(
            provider="facebook",
            access_token=access_token,
            expiry=expiry,
            meta={"page_id": page_id, "instagram_id": instagram_id},
        )
        db.add(token_row)
    await db.flush()
    return token_row


async def get_valid_token(db: AsyncSession) -> Optional[tuple[str, Token]]:
    """Return (access_token, token_row) if valid token exists and isn't expired."""
    result = await db.execute(select(Token).where(Token.provider == "facebook"))
    token_row = result.scalars().first()
    if not token_row:
        return None
    if token_row.expiry and token_row.expiry.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        logger.warning("Facebook token expired at %s", token_row.expiry)
        return None
    return token_row.access_token, token_row


async def post_to_facebook_page(db: AsyncSession, message: str) -> dict:
    """Post a text update to the configured Facebook Page."""
    token_info = await get_valid_token(db)
    if not token_info:
        return {"success": False, "error": "No valid Facebook token. Please authenticate."}

    access_token, token_row = token_info
    page_id = (token_row.meta or {}).get("page_id") or settings.FACEBOOK_PAGE_ID
    if not page_id:
        return {"success": False, "error": "FACEBOOK_PAGE_ID not configured."}

    # Get page access token
    page_token_resp = await _http_with_retry(
        "GET",
        f"{GRAPH_API_BASE}/{page_id}",
        params={"fields": "access_token", "access_token": access_token},
    )
    if page_token_resp.status_code != 200:
        return {"success": False, "error": f"Failed to get page token: {page_token_resp.text}"}

    page_access_token = page_token_resp.json().get("access_token", access_token)

    resp = await _http_with_retry(
        "POST",
        f"{GRAPH_API_BASE}/{page_id}/feed",
        json={"message": message, "access_token": page_access_token},
    )
    if resp.status_code == 200:
        post_id = resp.json().get("id", "")
        logger.info("Posted to Facebook page %s: post_id=%s", page_id, post_id)
        return {"success": True, "post_id": post_id, "platform": "facebook"}
    return {"success": False, "error": resp.text}


async def post_to_instagram(db: AsyncSession, caption: str, image_url: str = "") -> dict:
    """Post a caption (with optional image) to the connected Instagram Business account."""
    token_info = await get_valid_token(db)
    if not token_info:
        return {"success": False, "error": "No valid Facebook/Instagram token. Please authenticate."}

    access_token, token_row = token_info
    ig_id = (token_row.meta or {}).get("instagram_id") or settings.INSTAGRAM_ACCOUNT_ID
    if not ig_id:
        return {"success": False, "error": "INSTAGRAM_ACCOUNT_ID not configured."}

    # Step 1: Create media container
    container_payload: dict = {"caption": caption, "access_token": access_token}
    if image_url:
        container_payload["image_url"] = image_url
        container_payload["media_type"] = "IMAGE"
    else:
        # Text-only not directly supported; use a default placeholder or skip image
        container_payload["media_type"] = "REELS"  # or fallback
        container_payload["video_url"] = ""  # placeholder

    # For simplest case: just caption with no media (carousel or single image needed)
    # Use page feed as fallback for text-only
    if not image_url:
        return await post_to_facebook_page(db, caption)

    container_resp = await _http_with_retry(
        "POST",
        f"{GRAPH_API_BASE}/{ig_id}/media",
        json=container_payload,
    )
    if container_resp.status_code != 200:
        return {"success": False, "error": f"Media container creation failed: {container_resp.text}"}

    creation_id = container_resp.json().get("id")

    # Step 2: Publish the media
    publish_resp = await _http_with_retry(
        "POST",
        f"{GRAPH_API_BASE}/{ig_id}/media_publish",
        json={"creation_id": creation_id, "access_token": access_token},
    )
    if publish_resp.status_code == 200:
        media_id = publish_resp.json().get("id", "")
        logger.info("Posted to Instagram account %s: media_id=%s", ig_id, media_id)
        return {"success": True, "media_id": media_id, "platform": "instagram"}
    return {"success": False, "error": publish_resp.text}


async def generate_social_summary(db: AsyncSession, period_days: int = 7) -> dict:
    """Generate a summary of recent Facebook/Instagram activity via Graph API insights."""
    token_info = await get_valid_token(db)
    if not token_info:
        return {"error": "No valid Facebook token.", "period_days": period_days}

    access_token, token_row = token_info
    page_id = (token_row.meta or {}).get("page_id") or settings.FACEBOOK_PAGE_ID
    if not page_id:
        return {"error": "FACEBOOK_PAGE_ID not configured.", "period_days": period_days}

    since = int((datetime.now(timezone.utc) - timedelta(days=period_days)).timestamp())
    until = int(datetime.now(timezone.utc).timestamp())

    insights_resp = await _http_with_retry(
        "GET",
        f"{GRAPH_API_BASE}/{page_id}/insights",
        params={
            "metric": "page_impressions,page_engaged_users,page_posts_impressions",
            "period": "week",
            "since": since,
            "until": until,
            "access_token": access_token,
        },
    )
    if insights_resp.status_code != 200:
        return {"error": f"Insights API failed: {insights_resp.text}", "period_days": period_days}

    data = insights_resp.json().get("data", [])
    summary = {"period_days": period_days, "page_id": page_id, "metrics": {}}
    for item in data:
        name = item.get("name", "")
        values = item.get("values", [])
        total = sum(v.get("value", 0) for v in values)
        summary["metrics"][name] = total

    return summary
