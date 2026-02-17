"""LinkedIn OAuth2 integration routes."""

import logging
import secrets
import traceback
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.models.token import Token
from backend.services import linkedin_service

router = APIRouter(prefix="/integrations/linkedin", tags=["integrations"])
logger = logging.getLogger(__name__)

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
SCOPES = "openid profile w_member_social email"

# In-memory pending OAuth state tokens (CSRF protection).
# Single-process only; cleared on restart which is acceptable for OAuth flows.
_pending_states: set[str] = set()


@router.get("/auth")
async def linkedin_auth():
    """Return LinkedIn OAuth2 authorization URL with a CSRF state token."""
    if not settings.LINKEDIN_CLIENT_ID:
        return {"error": "LinkedIn client ID not configured", "configured": False}

    state = secrets.token_urlsafe(32)
    _pending_states.add(state)

    params = {
        "response_type": "code",
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
    }
    return {"auth_url": f"{LINKEDIN_AUTH_URL}?{urlencode(params)}", "configured": True}


@router.get("/callback")
async def linkedin_callback(
    code: str = Query(...),
    state: str = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Exchange OAuth2 code for access token and persist credentials."""
    # CSRF validation
    if state:
        if state not in _pending_states:
            raise HTTPException(status_code=400, detail="Invalid or expired state token")
        _pending_states.discard(state)

    try:
        resp = await linkedin_service._http_with_retry(
            "POST",
            "https://www.linkedin.com/oauth/v2/accessToken",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            form_data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
                "client_id": settings.LINKEDIN_CLIENT_ID,
                "client_secret": settings.LINKEDIN_CLIENT_SECRET,
            },
        )
    except Exception:
        logger.error("LinkedIn token exchange request failed:\n%s", traceback.format_exc())
        raise HTTPException(status_code=502, detail="Token exchange network error")

    if resp.status_code != 200:
        logger.error(
            "LinkedIn token exchange returned HTTP %d: %s",
            resp.status_code, resp.text,
        )
        return {"error": "Token exchange failed", "details": resp.json()}

    data = resp.json()
    await linkedin_service.save_credentials(
        db=db,
        access_token=data["access_token"],
        expires_in=data.get("expires_in", 5184000),
        refresh_token=data.get("refresh_token"),
    )

    return {"status": "connected", "message": "LinkedIn connected successfully."}


@router.get("/status")
async def linkedin_status(db: AsyncSession = Depends(get_db)):
    """Return current LinkedIn connection status and token expiry."""
    configured = bool(settings.LINKEDIN_CLIENT_ID)
    token_info = await linkedin_service.get_valid_token(db)
    if not token_info:
        return {"configured": configured, "connected": False}

    _, token_row = token_info
    return {
        "configured": configured,
        "connected": True,
        "expiry": token_row.expiry.isoformat() if token_row.expiry else None,
    }


@router.post("/disconnect")
async def linkedin_disconnect(db: AsyncSession = Depends(get_db)):
    """Remove stored LinkedIn credentials."""
    result = await db.execute(select(Token).where(Token.provider == "linkedin"))
    token_row = result.scalars().first()
    if token_row:
        await db.delete(token_row)
        await db.flush()
    return {"status": "disconnected", "message": "LinkedIn token removed"}


@router.post("/post")
async def post_to_linkedin(
    text: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Post a text update to LinkedIn."""
    try:
        success = await linkedin_service.post_text(db, text)
    except Exception:
        logger.error("LinkedIn post endpoint error:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail="Failed to post to LinkedIn")

    if success:
        return {"status": "success", "message": "Posted to LinkedIn"}
    raise HTTPException(status_code=500, detail="Failed to post to LinkedIn")
