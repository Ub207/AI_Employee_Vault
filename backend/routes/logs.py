"""Log listing endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.log import Log
from backend.schemas import LogResponse

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("", response_model=list[LogResponse])
async def list_logs(
    task_id: int | None = None,
    action: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(Log).order_by(Log.created_at.desc())
    if task_id:
        q = q.where(Log.task_id == task_id)
    if action:
        q = q.where(Log.action == action)
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())
