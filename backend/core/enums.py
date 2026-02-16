"""Gold-tier enums and constants mirroring Silver config.yaml."""

from enum import Enum


class Priority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SensitivityCategory(str, Enum):
    FINANCIAL = "financial"
    EXTERNAL_COMMUNICATION = "external_communication"
    DATA_DELETION = "data_deletion"
    ACCESS_CHANGE = "access_change"
    NONE = "none"
    UNKNOWN = "unknown"


class ApprovalDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


# SLA hours by priority — matches config.yaml
SLA_HOURS: dict[str, int] = {
    Priority.P0: 1,
    Priority.P1: 4,
    Priority.P2: 24,
    Priority.P3: 72,
}

# Priority keywords — matches config.yaml
PRIORITY_KEYWORDS: dict[str, Priority] = {
    "urgent": Priority.P0,
    "asap": Priority.P1,
    "critical": Priority.P0,
    "deadline": Priority.P1,
}

DEFAULT_PRIORITY = Priority.P2
