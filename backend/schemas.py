"""Pydantic request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from backend.core.enums import Priority, TaskStatus


# --- Task ---

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    body: str = ""
    priority: Priority = Priority.P2
    source: str = "api"


class TaskUpdate(BaseModel):
    title: str | None = None
    body: str | None = None
    priority: Priority | None = None
    status: TaskStatus | None = None


class TaskResponse(BaseModel):
    id: int
    title: str
    body: str
    priority: str
    status: str
    sensitivity_score: float
    sensitivity_category: str
    sla_deadline: datetime | None
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int


# --- Approval ---

class ApprovalRequest(BaseModel):
    reason: str = ""
    decided_by: str = "human"


class ApprovalResponse(BaseModel):
    id: int
    task_id: int
    decision: str
    reason: str
    decided_by: str
    decided_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Log ---

class LogResponse(BaseModel):
    id: int
    action: str
    details: str
    task_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- SLA ---

class SLAResponse(BaseModel):
    id: int
    task_id: int
    priority: str
    sla_deadline: datetime
    completed_at: datetime | None
    met_sla: bool | None

    model_config = {"from_attributes": True}


# --- Gmail ---

class GmailStatusResponse(BaseModel):
    configured: bool
    connected: bool
    email: str | None = None
    last_polled_at: datetime | None = None
    auto_reply_enabled: bool = False


class GmailPollResponse(BaseModel):
    processed: int = 0
    tasks_created: int = 0
    auto_replied: int = 0
    errors: list[str] = []


class GmailCallbackResponse(BaseModel):
    status: str
    email: str
    message: str


# --- Health ---

class HealthResponse(BaseModel):
    status: str
    version: str
    tier: str
    uptime_seconds: float
