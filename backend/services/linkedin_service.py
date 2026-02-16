"""Service for LinkedIn API operations using OAuth2."""

import logging
import httpx
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import Settings
from backend.models.token import Token

logger = logging.getLogger(__name__)


class LinkedInService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = Settings()
        self.api_base = "https://api.linkedin.com/v2"

    async def get_access_token(self) -> str | None:
        """Retrieve valid access token from DB."""
        result = await self.db.execute(select(Token).where(Token.provider == "linkedin"))
        token_record = result.scalars().first()

        if not token_record:
            return None

        # internal expiry check (LinkedIn tokens last 60 days usually)
        if token_record.expiry and token_record.expiry <= datetime.now():
             logger.warning("LinkedIn token expired. Refreshing not implemented automatically.")
             return None

        return token_record.access_token

    async def save_credentials(self, access_token: str, expires_in: int, refresh_token: str = None):
        """Save LinkedIn credentials to DB."""
        result = await self.db.execute(select(Token).where(Token.provider == "linkedin"))
        token_record = result.scalars().first()
        
        expiry = datetime.now() + timedelta(seconds=expires_in)

        if token_record:
            token_record.access_token = access_token
            if refresh_token:
                token_record.refresh_token = refresh_token
            token_record.expiry = expiry
        else:
            token_record = Token(
                provider="linkedin",
                access_token=access_token,
                refresh_token=refresh_token,
                expiry=expiry,
            )
            self.db.add(token_record)
        
        await self.db.commit()

    async def get_user_urn(self) -> str | None:
        """Get the authenticated user's URN (ID)."""
        token = await self.get_access_token()
        if not token:
            return None
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.api_base}/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            if resp.status_code == 200:
                data = resp.json()
                return f"urn:li:person:{data['id']}"
            else:
                logger.error(f"Failed to get LinkedIn user: {resp.text}")
                return None

    async def post_text(self, text: str) -> bool:
        """Post a text update to LinkedIn."""
        token = await self.get_access_token()
        if not token:
            logger.error("No LinkedIn token found")
            return False

        urn = await self.get_user_urn()
        if not urn:
            return False

        url = "https://api.linkedin.com/v2/ugcPosts"
        payload = {
            "author": urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            )
            if resp.status_code == 201:
                logger.info(f"Posted to LinkedIn: {resp.json().get('id')}")
                return True
            else:
                logger.error(f"Failed to post to LinkedIn: {resp.text}")
                return False
