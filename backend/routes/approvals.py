"""Approval listing endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.approval import Approval
from backend.schemas import ApprovalResponse

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalResponse])
async def list_approvals(
    task_id: int | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(Approval).order_by(Approval.created_at.desc())
    if task_id:
        q = q.where(Approval.task_id == task_id)
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


@router.get("/{approval_id}", response_model=ApprovalResponse)
async def get_approval(approval_id: int, db: AsyncSession = Depends(get_db)):
    approval = await db.get(Approval, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval
