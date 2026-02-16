"""LinkedIn integration routes."""

from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Query, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import Settings
from backend.database import get_db
from backend.services.linkedin_service import LinkedInService

router = APIRouter(prefix="/integrations/linkedin", tags=["integrations"])

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"


@router.get("/auth")
async def linkedin_auth(request: Request):
    """Returns LinkedIn OAuth2 authorization URL."""
    settings = Settings()
    if not settings.LINKEDIN_CLIENT_ID:
        return {"error": "LinkedIn client ID not configured", "configured": False}

    params = {
        "response_type": "code",
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "redirect_uri": "http://localhost:8000/integrations/linkedin/callback",  # Update as needed
        "scope": "openid profile w_member_social email",
    }
    return {"auth_url": f"{LINKEDIN_AUTH_URL}?{urlencode(params)}", "configured": True}


@router.get("/callback")
async def linkedin_callback(code: str = Query(...), state: str = Query(None), db: AsyncSession = Depends(get_db)):
    """Exchanges OAuth2 code for access token."""
    settings = Settings()
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            LINKEDIN_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": "http://localhost:8000/integrations/linkedin/callback",
                "client_id": settings.LINKEDIN_CLIENT_ID,
                "client_secret": settings.LINKEDIN_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if resp.status_code != 200:
            return {"error": "Token exchange failed", "details": resp.json()}

        data = resp.json()
        access_token = data["access_token"]
        expires_in = data["expires_in"]
        
        service = LinkedInService(db)
        await service.save_credentials(
            access_token=access_token,
            expires_in=expires_in,
            refresh_token=data.get("refresh_token")
        )

        return {"status": "success", "message": "LinkedIn connected successfully."}


@router.post("/post")
async def post_to_linkedin(text: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Manually trigger a LinkedIn post (for testing)."""
    service = LinkedInService(db)
    success = await service.post_text(text)
    if success:
        return {"status": "success", "message": "Posted to LinkedIn"}
    else:
        raise HTTPException(status_code=500, detail="Failed to post to LinkedIn")
