"""SLA tracking model."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class SLARecord(Base):
    __tablename__ = "sla_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    priority: Mapped[str] = mapped_column(String(10))
    sla_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    met_sla: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    task: Mapped["Task"] = relationship(back_populates="sla_records")
