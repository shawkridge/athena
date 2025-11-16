"""Task pattern models and stores for learning from completed tasks."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class PatternType(str, Enum):
    """Types of task patterns."""

    DURATION = "duration"  # Pattern about task duration
    SUCCESS_RATE = "success_rate"  # Pattern about success conditions
    PHASE_CORRELATION = "phase_correlation"  # Pattern about phase interactions
    PROPERTY_CORRELATION = "property_correlation"  # Pattern about properties


class ExtractionMethod(str, Enum):
    """How the pattern was extracted."""

    STATISTICAL = "statistical"  # System 1: Fast statistical extraction
    LLM_VALIDATED = "llm_validated"  # System 2: LLM validated
    MANUAL = "manual"  # Manually created


class PatternStatus(str, Enum):
    """Pattern lifecycle status."""

    ACTIVE = "active"  # Currently used for planning
    DEPRECATED = "deprecated"  # Old, superseded
    ARCHIVED = "archived"  # Historical record


class TaskPattern(BaseModel):
    """Learned pattern from task analysis."""

    id: Optional[int] = None
    project_id: Optional[int] = None  # NULL for cross-project patterns

    # Pattern Identity
    pattern_name: str  # e.g., "long_planning_improves_success"
    pattern_type: PatternType
    description: str  # Human-readable description

    # Pattern Conditions (extracted rule)
    condition_json: str  # JSON: {"phase": "planning", "min_duration_minutes": 120}
    prediction: str  # What the pattern predicts

    # Validation Metrics
    sample_size: int = 1  # Number of tasks used to extract pattern
    confidence_score: float  # 0.0-1.0 (System 1: statistical OR System 2: LLM validated)
    success_rate: float  # Observed success rate when pattern applies
    failure_count: int = 0  # Tasks that violated pattern

    # Pattern Lifecycle
    status: PatternStatus = PatternStatus.ACTIVE
    extraction_method: ExtractionMethod
    system_2_validated: bool = False
    validation_notes: Optional[str] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_validated_at: Optional[datetime] = None

    # Relationships (JSON arrays as strings)
    learned_from_tasks: str = "[]"  # JSON array of task IDs
    related_patterns: str = "[]"  # JSON array of pattern IDs

    model_config = ConfigDict(use_enum_values=True)


class TaskExecutionMetrics(BaseModel):
    """Execution metrics for a completed task."""

    id: Optional[int] = None
    task_id: int  # FK to prospective_tasks

    # Time Estimates vs Actual
    estimated_total_minutes: int  # From plan.estimated_duration_minutes
    actual_total_minutes: float
    estimation_error_percent: Optional[float] = None  # (actual - estimated) / estimated * 100

    # Phase Breakdown (in minutes)
    planning_phase_minutes: float = 0
    plan_ready_phase_minutes: float = 0
    executing_phase_minutes: float = 0
    verifying_phase_minutes: float = 0

    # Success Metrics
    success: bool = True
    failure_mode: Optional[str] = None

    # Task Properties (snapshot at completion)
    priority: str = "medium"  # low|medium|high|critical
    complexity_estimate: Optional[int] = None  # 1-5 scale
    dependencies_count: int = 0
    has_blockers: bool = False

    # Execution Quality
    retries_count: int = 0
    external_blockers: bool = False
    scope_change: bool = False

    # Metadata
    completed_at: datetime
    created_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(use_enum_values=True)


class TaskPropertyCorrelation(BaseModel):
    """Correlation between task property value and success."""

    id: Optional[int] = None
    project_id: Optional[int] = None

    # Property Being Analyzed
    property_name: str  # priority|complexity|dependencies_count|assignee_type
    property_value: str  # Specific value (e.g., "high", "claude", "3-5")

    # Correlation Metrics
    total_tasks: int = 1
    successful_tasks: int = 0
    failed_tasks: int = 0
    success_rate: float = 0.0  # successful / total

    # Statistical Significance
    sample_size: int = 1
    confidence_level: Optional[float] = None  # 0.0-1.0
    p_value: Optional[float] = None

    # Time Correlation
    avg_estimated_minutes: float = 0.0
    avg_actual_minutes: float = 0.0
    estimation_accuracy_percent: float = 0.0

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_analyzed: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(use_enum_values=True)
