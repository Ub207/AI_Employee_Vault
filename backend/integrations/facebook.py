"""Facebook & Instagram OAuth2 integration routes."""

import logging
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.services import facebook_service

router = APIRouter(prefix="/integrations/facebook", tags=["integrations"])
logger = logging.getLogger(__name__)

FACEBOOK_AUTH_URL = "https://www.facebook.com/v21.0/dialog/oauth"
_pending_states: set[str] = set()


@router.get("/auth")
async def facebook_auth():
    """Return Facebook OAuth2 authorization URL."""
    if not settings.FACEBOOK_APP_ID:
        return {"error": "Facebook App ID not configured", "configured": False}

    state = secrets.token_urlsafe(32)
    _pending_states.add(state)

    params = {
        "client_id": settings.FACEBOOK_APP_ID,
        "redirect_uri": settings.FACEBOOK_REDIRECT_URI,
        "scope": facebook_service.FACEBOOK_SCOPES,
        "state": state,
        "response_type": "code",
    }
    return {"auth_url": f"{FACEBOOK_AUTH_URL}?{urlencode(params)}", "configured": True}


@router.get("/callback")
async def facebook_callback(
    code: str = Query(...),
    state: str = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Exchange Facebook OAuth2 code for an access token."""
    if state:
        if state not in _pending_states:
            raise HTTPException(status_code=400, detail="Invalid or expired state token")
        _pending_states.discard(state)

    import httpx
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            "https://graph.facebook.com/v21.0/oauth/access_token",
            params={
                "client_id": settings.FACEBOOK_APP_ID,
                "client_secret": settings.FACEBOOK_APP_SECRET,
                "redirect_uri": settings.FACEBOOK_REDIRECT_URI,
                "code": code,
            },
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Token exchange failed: {resp.text}")

    data = resp.json()
    access_token = data.get("access_token", "")
    expires_in = data.get("expires_in", 5184000)  # ~60 days

    # Fetch connected page and Instagram account IDs
    page_id = settings.FACEBOOK_PAGE_ID or ""
    instagram_id = settings.INSTAGRAM_ACCOUNT_ID or ""

    await facebook_service.save_credentials(
        db=db,
        access_token=access_token,
        expires_in=expires_in,
        page_id=page_id,
        instagram_id=instagram_id,
    )

    return {
        "status": "connected",
        "message": "Facebook/Instagram account connected successfully.",
        "page_id": page_id,
        "instagram_id": instagram_id,
    }


@router.get("/status")
async def facebook_status(db: AsyncSession = Depends(get_db)):
    """Return current Facebook/Instagram connection status."""
    configured = bool(settings.FACEBOOK_APP_ID)
    token_info = await facebook_service.get_valid_token(db)
    if not token_info:
        return {"configured": configured, "connected": False}

    _, token_row = token_info
    return {
        "configured": configured,
        "connected": True,
        "page_id": (token_row.meta or {}).get("page_id"),
        "instagram_id": (token_row.meta or {}).get("instagram_id"),
        "expiry": token_row.expiry.isoformat() if token_row.expiry else None,
    }


@router.post("/post/facebook")
async def post_to_facebook(
    message: str = Query(..., description="Text to post on Facebook Page"),
    db: AsyncSession = Depends(get_db),
):
    """Post a text update to the connected Facebook Page."""
    result = await facebook_service.post_to_facebook_page(db, message)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Post failed"))
    return result


@router.post("/post/instagram")
async def post_to_instagram(
    caption: str = Query(..., description="Caption for the Instagram post"),
    image_url: str = Query(default="", description="Public URL of image (required for images)"),
    db: AsyncSession = Depends(get_db),
):
    """Post an image/caption to the connected Instagram Business account."""
    result = await facebook_service.post_to_instagram(db, caption, image_url)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Post failed"))
    return result


@router.get("/summary")
async def social_summary(
    period_days: int = Query(default=7, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db),
):
    """Return a summary of Facebook/Instagram insights for the given period."""
    return await facebook_service.generate_social_summary(db, period_days)
