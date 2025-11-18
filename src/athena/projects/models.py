"""Data models for project planning and execution tracking."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


class TaskStatus(str, Enum):
    """Status of a task in project execution."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class PhaseStatus(str, Enum):
    """Status of a phase in project execution."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class MilestoneStatus(str, Enum):
    """Status of a milestone."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    AT_RISK = "at_risk"


class ProjectPlan(BaseModel):
    """Complete project plan linking planning patterns to project structure."""

    id: Optional[int] = None
    project_id: int
    title: str = Field(..., description="Project title")
    description: str = Field(..., description="Project description")

    # Planning pattern links
    planning_pattern_id: Optional[int] = None
    decomposition_strategy_id: Optional[int] = None
    orchestration_pattern_id: Optional[int] = None

    # Project structure
    phases: list[int] = Field(default_factory=list, description="List of phase IDs in order")
    milestones: list[int] = Field(default_factory=list, description="List of milestone IDs")

    # Validation approach
    validation_rule_ids: list[int] = Field(
        default_factory=list, description="Validation rules to apply to this project"
    )

    # Project metrics
    estimated_duration_days: Optional[float] = None
    actual_duration_days: Optional[float] = None
    progress_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)

    # Status
    status: str = Field(default="pending")  # pending|in_progress|completed|on_hold
    assumptions: list[str] = Field(
        default_factory=list, description="Key assumptions about the project"
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    start_date: Optional[datetime] = None
    target_completion_date: Optional[datetime] = None
    actual_completion_date: Optional[datetime] = None

    model_config = ConfigDict(use_enum_values=True)


class PhasePlan(BaseModel):
    """Plan for a single phase in project execution."""

    id: Optional[int] = None
    project_id: int
    project_plan_id: int
    phase_number: int = Field(..., ge=1, description="Phase sequence number")
    title: str = Field(..., description="Phase title")
    description: str = Field(..., description="Phase description")

    # Execution tracking
    tasks: list[int] = Field(default_factory=list, description="List of task IDs in this phase")

    # Duration tracking
    planned_duration_days: float = Field(..., ge=0.1, description="Estimated duration")
    actual_duration_days: Optional[float] = None
    duration_variance_pct: float = Field(default=0.0)

    # Status
    status: PhaseStatus = PhaseStatus.PENDING
    progress_percentage: float = Field(default=0.0, ge=0.0, le=100.0)

    # Validation gates
    pre_phase_validation_rules: list[int] = Field(
        default_factory=list, description="Validation rules to check before starting phase"
    )
    post_phase_validation_rules: list[int] = Field(
        default_factory=list, description="Validation rules to check after completing phase"
    )

    # Quality tracking
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    completion_criteria: list[str] = Field(
        default_factory=list, description="What defines successful completion"
    )

    # Feedback
    feedback_enabled: bool = Field(default=True)
    blockers: list[str] = Field(default_factory=list, description="Current blockers for this phase")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    start_date: Optional[datetime] = None
    target_completion_date: Optional[datetime] = None
    actual_completion_date: Optional[datetime] = None

    model_config = ConfigDict(use_enum_values=True)

    @field_validator("duration_variance_pct")
    @classmethod
    def validate_variance(cls, v):
        """Validate duration variance percentage."""
        if v < -100.0:
            raise ValueError("Duration variance cannot be less than -100%")
        return v


class TaskStatusModel(BaseModel):
    """Track status and metrics for individual tasks."""

    id: Optional[int] = None
    project_id: int
    phase_plan_id: int
    content: str = Field(..., description="Task description")
    active_form: str = Field(
        ..., description="Active form for status messages (e.g., 'Implementing X')"
    )

    # Status
    status: TaskStatus = TaskStatus.PENDING
    priority: str = Field(default="medium")  # low|medium|high|critical
    assignee: Optional[str] = None

    # Duration tracking
    planned_duration_minutes: Optional[int] = None
    actual_duration_minutes: Optional[int] = None

    # Completion
    completion_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    acceptance_criteria: list[str] = Field(
        default_factory=list, description="Criteria for task completion"
    )

    # Metrics
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    completion_metrics: dict = Field(
        default_factory=dict, description="Custom metrics (e.g., code coverage, test pass rate)"
    )

    # Dependencies and blockers
    depends_on_task_ids: list[int] = Field(
        default_factory=list, description="Task IDs that must complete first"
    )
    blockers: list[str] = Field(default_factory=list, description="Current blockers")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    start_date: Optional[datetime] = None
    target_completion_date: Optional[datetime] = None
    actual_completion_date: Optional[datetime] = None

    model_config = ConfigDict(use_enum_values=True)


class Milestone(BaseModel):
    """Significant point in project execution."""

    id: Optional[int] = None
    project_id: int
    project_plan_id: int
    title: str = Field(..., description="Milestone title")
    description: str = Field(..., description="Milestone description")

    # Sequencing
    phase_number: Optional[int] = None
    sequence_number: int = Field(..., ge=1, description="Milestone order")

    # Dependencies
    depends_on_task_ids: list[int] = Field(
        default_factory=list, description="Task IDs that must complete before this milestone"
    )
    depends_on_milestone_ids: list[int] = Field(
        default_factory=list, description="Other milestone IDs that must complete first"
    )

    # Validation
    validation_rule_ids: list[int] = Field(
        default_factory=list, description="Rules to validate before unlocking next phase"
    )

    # Assumptions
    assumptions: list[str] = Field(
        default_factory=list, description="Assumptions to verify at this milestone"
    )

    # Success criteria
    success_criteria: list[str] = Field(
        default_factory=list, description="Definitions of successful milestone completion"
    )

    # Status
    status: MilestoneStatus = MilestoneStatus.NOT_STARTED
    completion_percentage: float = Field(default=0.0, ge=0.0, le=100.0)

    # Dates
    target_date: Optional[datetime] = None
    actual_completion_date: Optional[datetime] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(use_enum_values=True)


class ProjectDependency(BaseModel):
    """Dependency between tasks or phases (forms DAG)."""

    id: Optional[int] = None
    project_id: int
    project_plan_id: int

    # Dependency definition
    from_task_id: Optional[int] = None
    to_task_id: Optional[int] = None
    from_phase_id: Optional[int] = None
    to_phase_id: Optional[int] = None

    # Type
    dependency_type: str = Field(default="blocks", description="blocks|depends_on|relates_to")
    criticality: str = Field(default="medium", description="low|medium|high|critical")

    # Validation
    validation_before_transition: bool = Field(
        default=True, description="Whether to validate dependency before transition"
    )

    # Description
    description: Optional[str] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(use_enum_values=True)

    @field_validator("dependency_type")
    @classmethod
    def validate_dependency_type(cls, v):
        """Validate dependency type."""
        valid_types = {"blocks", "depends_on", "relates_to"}
        if v not in valid_types:
            raise ValueError(f"Invalid dependency type. Must be one of {valid_types}")
        return v

    @field_validator("criticality")
    @classmethod
    def validate_criticality(cls, v):
        """Validate criticality level."""
        valid_levels = {"low", "medium", "high", "critical"}
        if v not in valid_levels:
            raise ValueError(f"Invalid criticality. Must be one of {valid_levels}")
        return v
