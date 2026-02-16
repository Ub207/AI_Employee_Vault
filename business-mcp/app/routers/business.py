"""
Business MCP router — exposes /send-email, /create-linkedin-post, /log-activity.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, EmailStr

from app.services.email_service import send_email
from app.services.linkedin_service import create_linkedin_post
from app.services.log_service import log_activity

router = APIRouter(prefix="/mcp", tags=["business-mcp"])


# ── Request / Response schemas ──


class SendEmailRequest(BaseModel):
    to: EmailStr = Field(..., description="Recipient email address")
    subject: str = Field(..., min_length=1, max_length=998, description="Email subject line")
    body: str = Field(..., min_length=1, description="Plain-text email body")


class LinkedInPostRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=3000, description="Post text (max 3 000 chars)")


class LogActivityRequest(BaseModel):
    action: str = Field(..., min_length=1, max_length=128, description="Action identifier")
    detail: str = Field(..., min_length=1, description="Human-readable detail string")
    status: str = Field("OK", max_length=32, description="Status tag (OK, ERROR, etc.)")


class MCPResponse(BaseModel):
    status: str
    detail: str


# ── Endpoints ──


@router.post("/send-email", response_model=MCPResponse)
def endpoint_send_email(req: SendEmailRequest):
    """Send an email via SMTP."""
    result = send_email(to=req.to, subject=req.subject, body=req.body)
    if result["status"] != "ok":
        raise HTTPException(status_code=502, detail=result["detail"])
    return result


@router.post("/create-linkedin-post", response_model=MCPResponse)
def endpoint_create_linkedin_post(req: LinkedInPostRequest):
    """Publish a text post to LinkedIn."""
    result = create_linkedin_post(content=req.content)
    if result["status"] != "ok":
        raise HTTPException(status_code=502, detail=result["detail"])
    return result


@router.post("/log-activity", response_model=MCPResponse)
def endpoint_log_activity(req: LogActivityRequest):
    """Write an entry to the business activity log."""
    result = log_activity(action=req.action, detail=req.detail, status=req.status)
    return {"status": "ok", "detail": f"Logged: {result['action']}"}
