"""Task CRUD, status transitions, and SLA tracking."""

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.enums import (
    ApprovalDecision,
    SLA_HOURS,
    TaskStatus,
    PRIORITY_KEYWORDS,
    DEFAULT_PRIORITY,
)
from backend.config import settings
from backend.models.task import Task
from backend.models.approval import Approval
from backend.models.log import Log
from backend.models.sla import SLARecord
from backend.schemas import TaskCreate, TaskUpdate
from backend.services.sensitivity import score_sensitivity


def _detect_priority(text: str, explicit: str) -> str:
    """Auto-detect priority from text keywords if not explicitly set high."""
    text_lower = text.lower()
    for kw, prio in PRIORITY_KEYWORDS.items():
        if kw in text_lower and prio.value < explicit:
            return prio.value
    return explicit


async def _log(db: AsyncSession, action: str, details: dict, task_id: int | None = None) -> None:
    db.add(Log(action=action, details=json.dumps(details, default=str), task_id=task_id))


async def create_task(db: AsyncSession, data: TaskCreate) -> Task:
    combined_text = f"{data.title} {data.body}"
    sens = score_sensitivity(combined_text, threshold=settings.SENSITIVITY_THRESHOLD)

    priority = _detect_priority(combined_text, data.priority.value)
    sla_hours = SLA_HOURS.get(priority, 24)
    sla_deadline = datetime.now(timezone.utc) + timedelta(hours=sla_hours)

    if sens["requires_approval"]:
        status = TaskStatus.AWAITING_APPROVAL.value
    else:
        status = TaskStatus.IN_PROGRESS.value

    task = Task(
        title=data.title,
        body=data.body,
        priority=priority,
        status=status,
        sensitivity_score=sens["score"],
        sensitivity_category=sens["category"],
        sla_deadline=sla_deadline,
        source=data.source,
    )
    db.add(task)
    await db.flush()

    db.add(SLARecord(
        task_id=task.id,
        priority=priority,
        sla_deadline=sla_deadline,
    ))

    await _log(db, "task_created", {
        "title": data.title,
        "priority": priority,
        "status": status,
        "sensitivity": sens,
    }, task.id)

    return task


async def get_task(db: AsyncSession, task_id: int) -> Task | None:
    return await db.get(Task, task_id)


async def list_tasks(
    db: AsyncSession,
    status: str | None = None,
    priority: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[Task], int]:
    q = select(Task)
    count_q = select(func.count(Task.id))

    if status:
        q = q.where(Task.status == status)
        count_q = count_q.where(Task.status == status)
    if priority:
        q = q.where(Task.priority == priority)
        count_q = count_q.where(Task.priority == priority)

    q = q.order_by(Task.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(q)
    tasks = list(result.scalars().all())
    total = (await db.execute(count_q)).scalar() or 0
    return tasks, total


async def update_task(db: AsyncSession, task_id: int, data: TaskUpdate) -> Task | None:
    task = await db.get(Task, task_id)
    if not task:
        return None

    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        if field == "priority":
            value = value.value
        elif field == "status":
            value = value.value
        setattr(task, field, value)

    await _log(db, "task_updated", update_fields, task_id)
    await db.flush()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task_id: int) -> bool:
    task = await db.get(Task, task_id)
    if not task:
        return False
    await db.delete(task)
    await _log(db, "task_deleted", {"task_id": task_id})
    return True


async def approve_task(db: AsyncSession, task_id: int, reason: str = "", decided_by: str = "human") -> Task | None:
    task = await db.get(Task, task_id)
    if not task or task.status != TaskStatus.AWAITING_APPROVAL.value:
        return None

    task.status = TaskStatus.APPROVED.value
    db.add(Approval(
        task_id=task_id,
        decision=ApprovalDecision.APPROVED.value,
        reason=reason,
        decided_by=decided_by,
    ))
    await _log(db, "task_approved", {"reason": reason, "decided_by": decided_by}, task_id)
    await db.flush()
    await db.refresh(task)
    return task


async def reject_task(db: AsyncSession, task_id: int, reason: str = "", decided_by: str = "human") -> Task | None:
    task = await db.get(Task, task_id)
    if not task or task.status != TaskStatus.AWAITING_APPROVAL.value:
        return None

    task.status = TaskStatus.REJECTED.value
    db.add(Approval(
        task_id=task_id,
        decision=ApprovalDecision.REJECTED.value,
        reason=reason,
        decided_by=decided_by,
    ))
    await _log(db, "task_rejected", {"reason": reason, "decided_by": decided_by}, task_id)
    await db.flush()
    await db.refresh(task)
    return task


async def complete_task(db: AsyncSession, task_id: int) -> Task | None:
    task = await db.get(Task, task_id)
    if not task or task.status in (TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value):
        return None

    now = datetime.now(timezone.utc)
    task.status = TaskStatus.COMPLETED.value

    # Update SLA record
    q = select(SLARecord).where(SLARecord.task_id == task_id).order_by(SLARecord.id.desc()).limit(1)
    result = await db.execute(q)
    sla = result.scalar_one_or_none()
    if sla:
        sla.completed_at = now
        if sla.sla_deadline:
            deadline = sla.sla_deadline
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            sla.met_sla = now <= deadline
        else:
            sla.met_sla = True

    await _log(db, "task_completed", {
        "met_sla": sla.met_sla if sla else None,
    }, task_id)
    await db.flush()
    await db.refresh(task)
    return task
