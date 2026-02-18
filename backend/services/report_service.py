"""Minimal weekly report generator."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.task import Task


async def generate_weekly_report(db: AsyncSession) -> str:
    """Query tasks from the last 7 days and produce a markdown summary."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    # Total tasks this week
    total = (await db.execute(
        select(func.count(Task.id)).where(Task.created_at >= cutoff)
    )).scalar() or 0

    # Completed
    completed = (await db.execute(
        select(func.count(Task.id)).where(
            Task.created_at >= cutoff, Task.status == "completed"
        )
    )).scalar() or 0

    # Pending approval
    pending_approval = (await db.execute(
        select(func.count(Task.id)).where(Task.status == "awaiting_approval")
    )).scalar() or 0

    # In progress
    in_progress = (await db.execute(
        select(func.count(Task.id)).where(
            Task.created_at >= cutoff, Task.status == "in_progress"
        )
    )).scalar() or 0

    lines = [
        "# Weekly Summary",
        "",
        f"Report generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Metrics",
        "",
        f"- Total tasks created: {total}",
        f"- Completed: {completed}",
        f"- In progress: {in_progress}",
        "",
        "## Pending Approvals",
        "",
        f"- Tasks awaiting approval: {pending_approval}",
        "",
        "## Income",
        "",
        "- Financial task tracking: coming soon",
        "",
    ]
    return "\n".join(lines)
