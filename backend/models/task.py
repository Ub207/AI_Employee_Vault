"""Task model."""

from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(10), default="P2")
    status: Mapped[str] = mapped_column(String(50), default="pending")
    sensitivity_score: Mapped[float] = mapped_column(Float, default=0.0)
    sensitivity_category: Mapped[str] = mapped_column(String(50), default="none")
    sla_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(100), default="api")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    approvals: Mapped[list["Approval"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    logs: Mapped[list["Log"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    sla_records: Mapped[list["SLARecord"]] = relationship(back_populates="task", cascade="all, delete-orphan")
