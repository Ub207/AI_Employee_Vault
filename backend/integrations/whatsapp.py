"""WhatsApp webhook integration using Twilio."""

import logging
import traceback

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.services import whatsapp_service

router = APIRouter(prefix="/integrations/whatsapp", tags=["integrations"])
logger = logging.getLogger(__name__)


@router.post("/webhook")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    MessageSid: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Handle incoming WhatsApp messages pushed by Twilio."""

    # ── Twilio signature validation ──────────────────────────────────────────
    # Requires TWILIO_AUTH_TOKEN + WHATSAPP_WEBHOOK_URL (your public ngrok/prod URL).
    # Skip silently if either is unset (local dev without ngrok).
    if settings.TWILIO_AUTH_TOKEN and settings.WHATSAPP_WEBHOOK_URL:
        try:
            from twilio.request_validator import RequestValidator
            validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
            form_data = dict(await request.form())
            signature = request.headers.get("X-Twilio-Signature", "")
            if not validator.validate(settings.WHATSAPP_WEBHOOK_URL, form_data, signature):
                logger.warning(
                    "Twilio signature validation failed for request from %s", From
                )
                raise HTTPException(status_code=403, detail="Invalid Twilio signature")
        except ImportError:
            logger.warning("twilio package not installed — skipping signature validation")

    logger.info("WhatsApp webhook received from %s (SID=%s)", From, MessageSid)

    try:
        result = await whatsapp_service.process_incoming_message(
            db=db,
            message_sid=MessageSid or "",
            sender=From,
            body=Body,
        )
    except Exception:
        logger.error(
            "Unhandled error in WhatsApp webhook (from=%s):\n%s",
            From, traceback.format_exc(),
        )
        return {"status": "error", "message": "Internal processing error"}

    if result["skipped_duplicate"]:
        return {"status": "duplicate", "message": "Message already processed"}

    return {
        "status": "success",
        "processed": result["processed"],
        "task_id": result["task_id"],
    }
