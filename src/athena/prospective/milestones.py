"""Milestone models for progress tracking."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CheckpointType(str, Enum):
    """Types of milestone checkpoints."""

    TEST_PASS = "test_pass"  # Unit tests passing
    REVIEW_APPROVED = "review_approved"  # Code review completed
    FEATURE_COMPLETE = "feature_complete"  # Feature fully implemented
    INTEGRATION_VERIFIED = "integration_verified"  # Integration working
    PERFORMANCE_BASELINE = "performance_baseline"  # Performance metrics meet baseline
    SECURITY_AUDIT = "security_audit"  # Security audit passed
    DOCUMENTATION_COMPLETE = "documentation_complete"  # Documentation written
    CUSTOM = "custom"  # Custom checkpoint


class Milestone(BaseModel):
    """Progress checkpoint for a task.

    Milestones break long tasks into 20-30 minute intervals for progress tracking.
    """

    id: Optional[int] = None
    task_id: Optional[int] = None

    # Milestone definition
    name: str = Field(..., description="Milestone name")
    description: Optional[str] = Field(None, description="Detailed description")
    order: int = Field(..., description="Sequence order (1-based)")
    completion_percentage: float = Field(
        ..., description="Expected completion % (0.25, 0.5, 0.75, 1.0)"
    )
    estimated_minutes: int = Field(30, description="Estimated duration")
    checkpoint_type: CheckpointType = CheckpointType.FEATURE_COMPLETE
    checkpoint_criteria: dict = Field(
        default_factory=dict, description="Completion criteria as JSON"
    )

    # Progress tracking
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    actual_minutes: Optional[float] = None

    # Delay tracking
    is_delayed: bool = False
    delay_percent: float = 0.0  # 0-100, percentage over estimated time
    delay_reason: Optional[str] = None

    # Status
    status: str = Field("pending", description="pending|in_progress|completed|blocked")

    class Config:
        use_enum_values = True


class MilestoneProgress(BaseModel):
    """Progress report for a milestone."""

    milestone_id: int
    task_id: int
    status: str  # pending|in_progress|completed|blocked
    actual_minutes: Optional[float] = None
    completion_notes: Optional[str] = None
    is_delayed: bool = False
    delay_percent: float = 0.0
    reported_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class TaskWithMilestones(BaseModel):
    """Task with milestone-based progress tracking.

    Extends Phase 1 Task with milestone support for granular progress tracking.
    """

    # From ProspectiveTask (Phase 1)
    id: Optional[int] = None
    project_id: Optional[int] = None
    content: str
    active_form: str
    priority: str = "medium"
    status: str = "pending"
    phase: str = "planning"
    created_at: datetime = Field(default_factory=datetime.now)
    due_at: Optional[datetime] = None

    # Milestones (Phase 2)
    milestones: list[Milestone] = Field(default_factory=list)
    current_milestone_order: Optional[int] = None
    milestone_start_time: Optional[datetime] = None
    milestone_progress_history: list[MilestoneProgress] = Field(default_factory=list)

    # Overall progress
    overall_completion_percent: float = 0.0
    is_milestone_delayed: bool = False
    milestone_delay_reason: Optional[str] = None

    class Config:
        use_enum_values = True
