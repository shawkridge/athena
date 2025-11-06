"""Data models for prospective memory."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class TaskStatus(str, Enum):
    """Task status values."""

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class TaskPhase(str, Enum):
    """Task execution phases (agentic workflow)."""

    PLANNING = "planning"           # Initial planning phase
    PLAN_READY = "plan_ready"       # Plan created and validated
    EXECUTING = "executing"         # Currently executing plan
    VERIFYING = "verifying"         # Verification phase
    COMPLETED = "completed"         # Task completed
    FAILED = "failed"               # Task failed
    ABANDONED = "abandoned"         # Task abandoned


class TaskPriority(str, Enum):
    """Task priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Plan(BaseModel):
    """Execution plan for a task."""

    id: Optional[int] = None
    task_id: Optional[int] = None
    steps: list[str] = []                       # Ordered list of execution steps
    estimated_duration_minutes: int = 30        # Total estimated time
    created_at: datetime = Field(default_factory=datetime.now)
    validated: bool = False                     # Plan has been validated
    validation_notes: Optional[str] = None      # Feedback from validation

    model_config = ConfigDict(use_enum_values=True)


class PhaseMetrics(BaseModel):
    """Metrics for phase transitions."""

    phase: TaskPhase
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_minutes: Optional[float] = None

    model_config = ConfigDict(use_enum_values=True)


class TriggerType(str, Enum):
    """Types of task triggers."""

    TIME = "time"  # Trigger at specific time
    EVENT = "event"  # Trigger on event occurrence
    CONTEXT = "context"  # Trigger when in specific context
    DEPENDENCY = "dependency"  # Trigger when dependency completes
    FILE = "file"  # Trigger when file is opened/modified


class ProspectiveTask(BaseModel):
    """Task with future intention and triggers."""

    id: Optional[int] = None
    project_id: Optional[int] = None  # None for cross-project tasks
    content: str
    active_form: str  # Present continuous form

    # Timing
    created_at: datetime = Field(default_factory=datetime.now)
    due_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Status
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM

    # Phase (agentic workflow) - NEW FIELDS
    phase: TaskPhase = TaskPhase.PLANNING              # Current execution phase
    plan: Optional[Plan] = None                         # Execution plan
    plan_created_at: Optional[datetime] = None         # When plan was created
    phase_started_at: Optional[datetime] = None        # When current phase started
    phase_metrics: list[PhaseMetrics] = []            # History of phase transitions
    actual_duration_minutes: Optional[float] = None   # Actual execution time

    # Assignment
    assignee: str = "user"  # user|claude|sub-agent:name

    # Metadata
    notes: Optional[str] = None
    blocked_reason: Optional[str] = None
    failure_reason: Optional[str] = None              # Why task failed (if failed)
    lessons_learned: Optional[str] = None             # What we learned from this task

    model_config = ConfigDict(use_enum_values=True)


class TaskTrigger(BaseModel):
    """Trigger condition for a task."""

    id: Optional[int] = None
    task_id: int
    trigger_type: TriggerType
    trigger_condition: dict  # JSON condition
    fired: bool = False
    fired_at: Optional[datetime] = None

    model_config = ConfigDict(use_enum_values=True)


class TaskDependency(BaseModel):
    """Dependency between tasks."""

    task_id: int
    depends_on_task_id: int
    dependency_type: str = "blocks"  # blocks|related|enables
