"""Data models for prospective memory."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

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

    PLANNING = "planning"  # Initial planning phase
    PLAN_READY = "plan_ready"  # Plan created and validated
    EXECUTING = "executing"  # Currently executing plan
    VERIFYING = "verifying"  # Verification phase
    COMPLETED = "completed"  # Task completed
    FAILED = "failed"  # Task failed
    ABANDONED = "abandoned"  # Task abandoned


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
    steps: list[str] = []  # Ordered list of execution steps
    estimated_duration_minutes: int = 30  # Total estimated time
    created_at: datetime = Field(default_factory=datetime.now)
    validated: bool = False  # Plan has been validated
    validation_notes: Optional[str] = None  # Feedback from validation

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
    """Task with future intention and goals."""

    # Core fields (match database schema)
    id: Optional[int] = None
    project_id: Optional[int] = None
    title: str  # Task title (required)
    description: Optional[str] = None  # Task description

    # Timing (match database schema)
    created_at: datetime = Field(default_factory=datetime.now)
    due_date: Optional[datetime] = None  # Due date
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Status and Priority
    status: str = "pending"  # pending, in_progress, completed, cancelled
    priority: int = 5  # 1-10, default 5

    # Goal/Task relationships
    goal_id: Optional[int] = None
    parent_task_id: Optional[int] = None

    # Effort tracking
    estimated_effort_hours: Optional[float] = None
    actual_effort_hours: Optional[float] = None
    completion_percentage: int = 0
    success_rate: Optional[float] = None

    # Related resources
    related_memory_ids: Optional[list[int]] = None
    related_code_ids: Optional[list[int]] = None
    related_test_name: Optional[str] = None
    related_file_path: Optional[str] = None
    checkpoint_id: Optional[int] = None
    last_claude_sync_at: Optional[datetime] = None

    # Extended metadata (optional, for future use)
    # Can be populated from future schema additions
    notes: Optional[str] = None

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
