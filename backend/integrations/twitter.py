"""Twitter/X OAuth2 PKCE integration routes."""

import base64
import hashlib
import logging
import os
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.services import twitter_service

router = APIRouter(prefix="/integrations/twitter", tags=["integrations"])
logger = logging.getLogger(__name__)

TWITTER_AUTH_URL = "https://twitter.com/i/oauth2/authorize"
TWITTER_TOKEN_URL = "https://api.twitter.com/2/oauth2/token"

# In-memory PKCE state store (single-process only; cleared on restart)
_pending_states: dict[str, dict] = {}  # state -> {code_verifier, ...}


def _generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge (S256)."""
    code_verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


@router.get("/auth")
async def twitter_auth():
    """Return Twitter OAuth2 PKCE authorization URL."""
    if not settings.TWITTER_CLIENT_ID:
        return {"error": "Twitter Client ID not configured", "configured": False}

    state = secrets.token_urlsafe(32)
    code_verifier, code_challenge = _generate_pkce_pair()
    _pending_states[state] = {"code_verifier": code_verifier}

    params = {
        "response_type": "code",
        "client_id": settings.TWITTER_CLIENT_ID,
        "redirect_uri": settings.TWITTER_REDIRECT_URI,
        "scope": twitter_service.TWITTER_SCOPES,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return {"auth_url": f"{TWITTER_AUTH_URL}?{urlencode(params)}", "configured": True}


@router.get("/callback")
async def twitter_callback(
    code: str = Query(...),
    state: str = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Exchange Twitter OAuth2 code for access + refresh tokens."""
    if state not in _pending_states:
        raise HTTPException(status_code=400, detail="Invalid or expired state token")
    code_verifier = _pending_states.pop(state)["code_verifier"]

    import httpx
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            TWITTER_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.TWITTER_REDIRECT_URI,
                "client_id": settings.TWITTER_CLIENT_ID,
                "code_verifier": code_verifier,
            },
            auth=(settings.TWITTER_CLIENT_ID, settings.TWITTER_CLIENT_SECRET),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Token exchange failed: {resp.text}")

    data = resp.json()

    # Fetch user info
    access_token = data["access_token"]
    user_id = ""
    username = ""
    async with httpx.AsyncClient(timeout=15) as client:
        me_resp = await client.get(
            "https://api.twitter.com/2/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if me_resp.status_code == 200:
            me_data = me_resp.json().get("data", {})
            user_id = me_data.get("id", "")
            username = me_data.get("username", "")

    await twitter_service.save_credentials(
        db=db,
        access_token=access_token,
        refresh_token=data.get("refresh_token"),
        expires_in=data.get("expires_in", 7200),
        twitter_user_id=user_id,
        twitter_username=username,
    )

    return {
        "status": "connected",
        "message": "Twitter/X account connected successfully.",
        "username": username,
        "user_id": user_id,
    }


@router.get("/status")
async def twitter_status(db: AsyncSession = Depends(get_db)):
    """Return current Twitter/X connection status."""
    configured = bool(settings.TWITTER_CLIENT_ID)
    token_info = await twitter_service.get_valid_token(db)
    if not token_info:
        return {"configured": configured, "connected": False}

    _, token_row = token_info
    return {
        "configured": configured,
        "connected": True,
        "username": (token_row.meta or {}).get("username"),
        "user_id": (token_row.meta or {}).get("user_id"),
        "expiry": token_row.expiry.isoformat() if token_row.expiry else None,
    }


@router.post("/disconnect")
async def twitter_disconnect(db: AsyncSession = Depends(get_db)):
    """Remove stored Twitter credentials."""
    from sqlalchemy import select
    from backend.models.token import Token
    result = await db.execute(select(Token).where(Token.provider == "twitter"))
    token_row = result.scalars().first()
    if token_row:
        await db.delete(token_row)
        await db.flush()
    return {"status": "disconnected", "message": "Twitter token removed"}


@router.post("/tweet")
async def post_tweet(
    text: str = Query(..., description="Tweet text (max 280 chars)"),
    db: AsyncSession = Depends(get_db),
):
    """Post a tweet on the connected Twitter/X account."""
    if len(text) > 280:
        raise HTTPException(status_code=400, detail="Tweet text exceeds 280 characters")
    result = await twitter_service.post_tweet(db, text)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Tweet failed"))
    return result


@router.get("/summary")
async def twitter_summary(
    period_days: int = Query(default=7, description="Number of days for the summary"),
    db: AsyncSession = Depends(get_db),
):
    """Return a Twitter/X engagement summary for recent tweets."""
    return await twitter_service.generate_twitter_summary(db, period_days)
