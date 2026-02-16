"""
LinkedIn service — creates a text post via the LinkedIn v2 API.

Docs: https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api
"""

import httpx
from app.core.config import settings
from app.services.log_service import log_activity

LINKEDIN_API_URL = "https://api.linkedin.com/v2/ugcPosts"


def create_linkedin_post(content: str) -> dict:
    """
    Publish a text-only post to LinkedIn under the configured person URN.
    Returns a result dict with status and detail.
    """
    if not settings.linkedin_access_token or not settings.linkedin_person_urn:
        detail = "LinkedIn credentials not configured in .env"
        log_activity("create_linkedin_post", detail, status="ERROR")
        return {"status": "error", "detail": detail}

    headers = {
        "Authorization": f"Bearer {settings.linkedin_access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    payload = {
        "author": settings.linkedin_person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": content},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    try:
        resp = httpx.post(LINKEDIN_API_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()

        post_id = resp.json().get("id", "unknown")
        detail = f"LinkedIn post created — id={post_id}"
        log_activity("create_linkedin_post", detail)
        return {"status": "ok", "detail": detail, "post_id": post_id}

    except httpx.HTTPStatusError as exc:
        detail = f"LinkedIn API {exc.response.status_code}: {exc.response.text[:300]}"
        log_activity("create_linkedin_post", detail, status="ERROR")
        return {"status": "error", "detail": detail}

    except httpx.RequestError as exc:
        detail = f"LinkedIn request failed: {exc}"
        log_activity("create_linkedin_post", detail, status="ERROR")
        return {"status": "error", "detail": detail}
