"""Task CRUD + approve/reject/complete endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.schemas import (
    ApprovalRequest,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
)
from backend.services import task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(data: TaskCreate, db: AsyncSession = Depends(get_db)):
    task = await task_service.create_task(db, data)
    return task


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: str | None = None,
    priority: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    tasks, total = await task_service.list_tasks(db, status=status, priority=priority, offset=offset, limit=limit)
    return TaskListResponse(tasks=tasks, total=total)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: int, data: TaskUpdate, db: AsyncSession = Depends(get_db)):
    task = await task_service.update_task(db, task_id, data)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await task_service.delete_task(db, task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/{task_id}/approve", response_model=TaskResponse)
async def approve_task(task_id: int, data: ApprovalRequest = ApprovalRequest(), db: AsyncSession = Depends(get_db)):
    task = await task_service.approve_task(db, task_id, reason=data.reason, decided_by=data.decided_by)
    if not task:
        raise HTTPException(status_code=400, detail="Task not found or not awaiting approval")
    return task


@router.post("/{task_id}/reject", response_model=TaskResponse)
async def reject_task(task_id: int, data: ApprovalRequest = ApprovalRequest(), db: AsyncSession = Depends(get_db)):
    task = await task_service.reject_task(db, task_id, reason=data.reason, decided_by=data.decided_by)
    if not task:
        raise HTTPException(status_code=400, detail="Task not found or not awaiting approval")
    return task


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await task_service.complete_task(db, task_id)
    if not task:
        raise HTTPException(status_code=400, detail="Task not found or already completed/cancelled")
    return task
