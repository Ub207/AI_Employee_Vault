"""Gmail OAuth2 integration skeleton."""

from urllib.parse import urlencode

from fastapi import APIRouter, Query

from backend.config import settings

router = APIRouter(prefix="/integrations/gmail", tags=["integrations"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
SCOPES = "https://www.googleapis.com/auth/gmail.readonly"


@router.get("/auth")
async def gmail_auth():
    """Returns Google OAuth2 authorization URL."""
    if not settings.GMAIL_CLIENT_ID:
        return {"error": "Gmail client ID not configured", "configured": False}

    params = {
        "client_id": settings.GMAIL_CLIENT_ID,
        "redirect_uri": settings.GMAIL_REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    return {"auth_url": f"{GOOGLE_AUTH_URL}?{urlencode(params)}", "configured": True}


@router.get("/callback")
async def gmail_callback(code: str = Query(...)):
    """Receives OAuth2 callback code. Token exchange is a placeholder."""
    return {
        "status": "callback_received",
        "code": code[:10] + "...",
        "message": "Token exchange not yet implemented — placeholder for Gold+ tier",
    }


@router.get("/status")
async def gmail_status():
    """Check Gmail integration status."""
    return {
        "configured": bool(settings.GMAIL_CLIENT_ID),
        "connected": False,
        "message": "OAuth2 skeleton — connect via /integrations/gmail/auth",
    }
