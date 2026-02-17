"""Tracks processed Gmail message IDs to prevent duplicate task creation."""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class ProcessedGmailMessage(Base):
    __tablename__ = "processed_gmail_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gmail_message_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
