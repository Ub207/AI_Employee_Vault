"""Reasoner service — re-scores and routes tasks through the pipeline."""

import json

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.enums import TaskStatus
from backend.config import settings
from backend.models.task import Task
from backend.models.log import Log
from backend.services.sensitivity import score_sensitivity


async def process_task_pipeline(db: AsyncSession, task: Task) -> Task:
    """Re-score sensitivity and route task accordingly."""
    combined_text = f"{task.title} {task.body}"
    sens = score_sensitivity(combined_text, threshold=settings.SENSITIVITY_THRESHOLD)

    task.sensitivity_score = sens["score"]
    task.sensitivity_category = sens["category"]

    if settings.AUTONOMY_MODE:
        # Override sensitivity check if autonomy is enabled
        task.status = TaskStatus.IN_PROGRESS.value
        db.add(Log(
            action="autonomy_override",
            details="Approval bypassed due to AUTONOMY_MODE=True",
            task_id=task.id
        ))
    elif sens["requires_approval"] and task.status == TaskStatus.PENDING.value:
        task.status = TaskStatus.AWAITING_APPROVAL.value
    elif not sens["requires_approval"] and task.status == TaskStatus.PENDING.value:
        task.status = TaskStatus.IN_PROGRESS.value

    db.add(Log(
        action="reasoner_processed",
        details=json.dumps({"sensitivity": sens, "new_status": task.status, "autonomy_mode": settings.AUTONOMY_MODE}),
        task_id=task.id,
    ))

    return task
