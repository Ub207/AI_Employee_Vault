"""Gmail OAuth2 integration — full 6-endpoint router."""

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.models.gmail_token import GmailToken
from backend.schemas import GmailCallbackResponse, GmailPollResponse, GmailStatusResponse, TaskListResponse, TaskResponse
from backend.services import gmail_service

router = APIRouter(prefix="/integrations/gmail", tags=["integrations"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"


@router.get("/auth")
async def gmail_auth(db: AsyncSession = Depends(get_db)):
    """Generate state token, return Google OAuth2 authorization URL."""
    if not settings.GMAIL_CLIENT_ID:
        return {"error": "Gmail client ID not configured", "configured": False}

    state = await gmail_service.generate_state_token(db)

    params = {
        "client_id": settings.GMAIL_CLIENT_ID,
        "redirect_uri": settings.GMAIL_REDIRECT_URI,
        "response_type": "code",
        "scope": gmail_service.SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return {"auth_url": f"{GOOGLE_AUTH_URL}?{urlencode(params)}", "configured": True}


@router.get("/callback", response_model=GmailCallbackResponse)
async def gmail_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Verify state, exchange code for tokens, return connected status."""
    token_row = await gmail_service.verify_state_token(state, db)
    if not token_row:
        return GmailCallbackResponse(
            status="error",
            email="",
            message="Invalid or expired state token",
        )

    try:
        token_row = await gmail_service.exchange_code(code, token_row, db)
    except Exception as e:
        return GmailCallbackResponse(
            status="error",
            email="",
            message=f"Token exchange failed: {e}",
        )

    return GmailCallbackResponse(
        status="connected",
        email=token_row.email_address,
        message="Gmail account connected successfully",
    )


@router.get("/status", response_model=GmailStatusResponse)
async def gmail_status(db: AsyncSession = Depends(get_db)):
    """Check if a valid Gmail token exists."""
    configured = bool(settings.GMAIL_CLIENT_ID)

    token_info = await gmail_service.get_valid_token(db)
    if not token_info:
        return GmailStatusResponse(
            configured=configured,
            connected=False,
            auto_reply_enabled=settings.GMAIL_AUTO_REPLY_ENABLED,
        )

    _, token_row = token_info
    return GmailStatusResponse(
        configured=configured,
        connected=True,
        email=token_row.email_address,
        last_polled_at=token_row.last_polled_at,
        auto_reply_enabled=settings.GMAIL_AUTO_REPLY_ENABLED,
    )


@router.post("/disconnect")
async def gmail_disconnect(db: AsyncSession = Depends(get_db)):
    """Delete all stored Gmail tokens."""
    result = await db.execute(select(GmailToken))
    rows = result.scalars().all()
    for row in rows:
        await db.delete(row)
    await db.flush()
    return {"status": "disconnected", "message": "Gmail tokens removed"}


@router.post("/poll", response_model=GmailPollResponse)
async def gmail_poll(db: AsyncSession = Depends(get_db)):
    """Manually trigger a Gmail inbox poll."""
    summary = await gmail_service.poll_inbox(db)
    return GmailPollResponse(**summary)


@router.get("/processed", response_model=TaskListResponse)
async def gmail_processed(
    offset: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List tasks created from Gmail emails."""
    from backend.models.task import Task
    from sqlalchemy import func

    q = select(Task).where(Task.source == "gmail").order_by(Task.created_at.desc()).offset(offset).limit(limit)
    count_q = select(func.count(Task.id)).where(Task.source == "gmail")

    result = await db.execute(q)
    tasks = list(result.scalars().all())
    total = (await db.execute(count_q)).scalar() or 0

    return TaskListResponse(
        tasks=[TaskResponse.model_validate(t) for t in tasks],
        total=total,
    )
