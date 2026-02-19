"""Twitter/X API v2 service — posting and summary generation."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.token import Token
from backend.config import settings

logger = logging.getLogger(__name__)

TWITTER_API_BASE = "https://api.twitter.com/2"
TWITTER_AUTH_URL = "https://twitter.com/i/oauth2/authorize"
TWITTER_TOKEN_URL = "https://api.twitter.com/2/oauth2/token"

# Scopes for OAuth 2.0 PKCE
TWITTER_SCOPES = "tweet.read tweet.write users.read offline.access"


async def _http_with_retry(method: str, url: str, **kwargs) -> httpx.Response:
    """HTTP call with exponential backoff on rate limits / transient errors."""
    async with httpx.AsyncClient(timeout=30) as client:
        for attempt in range(3):
            try:
                resp = await client.request(method, url, **kwargs)
                if resp.status_code in (429, 502, 503, 504) and attempt < 2:
                    retry_after = int(resp.headers.get("x-rate-limit-reset", "1"))
                    wait = max(2 ** attempt, min(retry_after, 60))
                    await _sleep(wait)
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


async def save_credentials(
    db: AsyncSession,
    access_token: str,
    refresh_token: Optional[str],
    expires_in: int,
    twitter_user_id: str = "",
    twitter_username: str = "",
) -> Token:
    """Persist Twitter OAuth2 tokens to DB."""
    result = await db.execute(select(Token).where(Token.provider == "twitter"))
    token_row = result.scalars().first()
    expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    meta = {"user_id": twitter_user_id, "username": twitter_username}
    if token_row:
        token_row.access_token = access_token
        token_row.refresh_token = refresh_token
        token_row.expiry = expiry
        token_row.meta = meta
    else:
        token_row = Token(
            provider="twitter",
            access_token=access_token,
            refresh_token=refresh_token,
            expiry=expiry,
            meta=meta,
        )
        db.add(token_row)
    await db.flush()
    return token_row


async def refresh_access_token(db: AsyncSession, token_row: Token) -> Optional[str]:
    """Use the refresh token to get a new access token."""
    if not token_row.refresh_token:
        return None
    resp = await _http_with_retry(
        "POST",
        TWITTER_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": token_row.refresh_token,
            "client_id": settings.TWITTER_CLIENT_ID,
        },
        auth=(settings.TWITTER_CLIENT_ID, settings.TWITTER_CLIENT_SECRET),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if resp.status_code != 200:
        logger.error("Twitter token refresh failed: %s", resp.text)
        return None
    data = resp.json()
    token_row.access_token = data["access_token"]
    token_row.refresh_token = data.get("refresh_token", token_row.refresh_token)
    token_row.expiry = datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 7200))
    await db.flush()
    return token_row.access_token


async def get_valid_token(db: AsyncSession) -> Optional[tuple[str, Token]]:
    """Return (access_token, token_row), refreshing if needed."""
    result = await db.execute(select(Token).where(Token.provider == "twitter"))
    token_row = result.scalars().first()
    if not token_row:
        return None
    if token_row.expiry and token_row.expiry.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        logger.info("Twitter token expired, attempting refresh...")
        new_token = await refresh_access_token(db, token_row)
        if not new_token:
            return None
        return new_token, token_row
    return token_row.access_token, token_row


async def post_tweet(db: AsyncSession, text: str) -> dict:
    """Post a tweet using the authenticated Twitter account."""
    token_info = await get_valid_token(db)
    if not token_info:
        return {"success": False, "error": "No valid Twitter token. Please authenticate."}

    access_token, token_row = token_info
    resp = await _http_with_retry(
        "POST",
        f"{TWITTER_API_BASE}/tweets",
        json={"text": text},
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    if resp.status_code in (200, 201):
        data = resp.json().get("data", {})
        tweet_id = data.get("id", "")
        logger.info("Tweet posted successfully: id=%s", tweet_id)
        return {"success": True, "tweet_id": tweet_id, "platform": "twitter"}
    return {"success": False, "error": resp.text}


async def get_recent_tweets(db: AsyncSession, max_results: int = 10) -> list[dict]:
    """Fetch the authenticated user's recent tweets."""
    token_info = await get_valid_token(db)
    if not token_info:
        return []

    access_token, token_row = token_info
    user_id = (token_row.meta or {}).get("user_id")
    if not user_id:
        # Fetch user info
        me_resp = await _http_with_retry(
            "GET",
            f"{TWITTER_API_BASE}/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if me_resp.status_code == 200:
            user_id = me_resp.json().get("data", {}).get("id", "")

    if not user_id:
        return []

    resp = await _http_with_retry(
        "GET",
        f"{TWITTER_API_BASE}/users/{user_id}/tweets",
        params={
            "max_results": max_results,
            "tweet.fields": "created_at,public_metrics",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if resp.status_code != 200:
        return []

    tweets = resp.json().get("data", [])
    return [
        {
            "id": t.get("id"),
            "text": t.get("text"),
            "created_at": t.get("created_at"),
            "likes": t.get("public_metrics", {}).get("like_count", 0),
            "retweets": t.get("public_metrics", {}).get("retweet_count", 0),
            "replies": t.get("public_metrics", {}).get("reply_count", 0),
        }
        for t in tweets
    ]


async def generate_twitter_summary(db: AsyncSession, period_days: int = 7) -> dict:
    """Generate an engagement summary for recent tweets."""
    tweets = await get_recent_tweets(db, max_results=20)
    if not tweets:
        return {"error": "No tweets found or not authenticated.", "period_days": period_days}

    total_likes = sum(t["likes"] for t in tweets)
    total_retweets = sum(t["retweets"] for t in tweets)
    total_replies = sum(t["replies"] for t in tweets)
    top_tweet = max(tweets, key=lambda t: t["likes"], default=None)

    return {
        "period_days": period_days,
        "total_tweets": len(tweets),
        "total_likes": total_likes,
        "total_retweets": total_retweets,
        "total_replies": total_replies,
        "top_tweet": top_tweet,
        "avg_likes": round(total_likes / len(tweets), 1) if tweets else 0,
    }
