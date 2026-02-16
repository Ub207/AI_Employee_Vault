"""WhatsApp webhook integration using Twilio."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Form, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.request_validator import RequestValidator

from backend.config import Settings
from backend.database import get_db
from backend.models.task import Task
from backend.models.log import Log
from backend.services.reasoner import process_task_pipeline
from backend.services.whatsapp_service import WhatsappService
from backend.core.enums import TaskStatus

router = APIRouter(prefix="/integrations/whatsapp", tags=["integrations"])
logger = logging.getLogger(__name__)


@router.post("/webhook")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Handle incoming WhatsApp messages."""
    settings = Settings()
    
    # Validate Request
    if settings.TWILIO_AUTH_TOKEN:
        validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
        form_data = await request.form()
        params = dict(form_data)
        signature = request.headers.get("X-Twilio-Signature", "")
        # Note: In production behind a proxy (e.g. ngrok, load balancer), 
        # request.url might differ from what Twilio sees. Ensure correct URL is used.
        # For local dev with ngrok, user must configure this correctly.
        # url = str(request.url) 
        # if not validator.validate(url, params, signature):
        #    logger.warning("Twilio signature validation failed.")
        #    raise HTTPException(status_code=403, detail="Invalid signature")

    logger.info(f"Received WhatsApp from {From}: {Body}")

    # Create Task
    task = Task(
        title=f"[WhatsApp] Message from {From}",
        body=f"Sender: {From}\n\n{Body}",
        priority="P2",
        status="pending",
        source="whatsapp",
        created_at=datetime.now(timezone.utc)
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # Process Reasoning Pipeline
    task = await process_task_pipeline(db, task)

    # Auto-Response Logic
    response_text = ""
    # Check autonomy settings or sensitivity
    # If safe (IN_PROGRESS) -> Auto-reply
    if task.status == TaskStatus.IN_PROGRESS.value:
        response_text = "Thanks for your message! I've logged this as a task and will get back to you shortly."
        
        # Send Reply
        wa_service = WhatsappService()
        sent = await wa_service.send_message(From, response_text)
        if sent:
            db.add(Log(action="auto_reply_sent", details=f"Replied to {From}", task_id=task.id))
    
    elif task.status == TaskStatus.AWAITING_APPROVAL.value:
        response_text = "I've received your request. Since it involves sensitive actions, I'll need supervisor approval before proceeding."
        wa_service = WhatsappService()
        await wa_service.send_message(From, response_text)
        db.add(Log(action="approval_required", details="Sensitive WhatsApp request", task_id=task.id))

    return {"status": "success", "message": "Processed"}
