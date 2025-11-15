"""Data models for planning memory."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PatternType(str, Enum):
    """Types of planning patterns."""

    HIERARCHICAL = "hierarchical"
    RECURSIVE = "recursive"
    HYBRID = "hybrid"
    GRAPH_BASED = "graph_based"
    FLAT = "flat"


class DecompositionType(str, Enum):
    """Types of task decomposition."""

    ADAPTIVE = "adaptive"
    FIXED = "fixed"
    HIERARCHICAL = "hierarchical"
    RECURSIVE = "recursive"


class ValidationRuleType(str, Enum):
    """Types of validation rules."""

    FORMAL = "formal"
    HEURISTIC = "heuristic"
    LLM_BASED = "llm_based"
    SYMBOLIC = "symbolic"


class ExecutionOutcome(str, Enum):
    """Outcomes of plan execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    BLOCKED = "blocked"


class CoordinationType(str, Enum):
    """Types of multi-agent coordination."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"
    HYBRID = "hybrid"


class PlanningPattern(BaseModel):
    """Planning strategy pattern with effectiveness metrics."""

    id: Optional[int] = None
    project_id: int
    pattern_type: PatternType
    name: str = Field(..., description="Human-readable pattern name")
    description: str = Field(..., description="Detailed description of the pattern")

    # Effectiveness metrics
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    execution_count: int = Field(default=0, ge=0)

    # Domain and applicability
    applicable_domains: list[str] = Field(
        default_factory=list,
        description="e.g., ['robotics', 'web', 'project-mgmt', 'coding']"
    )
    applicable_task_types: list[str] = Field(
        default_factory=list,
        description="e.g., ['refactoring', 'feature', 'bug-fix']"
    )
    complexity_range: tuple[int, int] = Field(
        default=(1, 10),
        description="Min-max complexity (1-10 scale)"
    )

    # When to use
    conditions: dict = Field(
        default_factory=dict,
        description="Conditions for applying this pattern (e.g., {'team_size': '>3'})"
    )

    # Source and learning
    source: str = Field(default="user")  # user|learned|imported|research
    research_reference: Optional[str] = None  # e.g., arXiv:2311.05772 (ADaPT)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    feedback_count: int = Field(default=0, ge=0)

    class Config:
        use_enum_values = True

    @field_validator("success_rate", "quality_score")
    @classmethod
    def validate_rates(cls, v):
        """Validate rates are between 0 and 1."""
        if not (0.0 <= v <= 1.0):
            raise ValueError("Rate must be between 0.0 and 1.0")
        return v


class DecompositionStrategy(BaseModel):
    """Task decomposition strategy with metrics."""

    id: Optional[int] = None
    project_id: int
    strategy_name: str = Field(..., description="e.g., 'hierarchical-30min', 'adaptive-depth'")
    description: str = Field(..., description="How this decomposition strategy works")

    # Decomposition parameters
    decomposition_type: DecompositionType
    chunk_size_minutes: int = Field(default=30, ge=5, le=480)
    max_depth: Optional[int] = None  # None for unlimited
    adaptive_depth: bool = Field(default=False)

    # Validation gates
    validation_gates: list[str] = Field(
        default_factory=list,
        description="e.g., ['pre_execution', 'post_phase', 'milestone']"
    )

    # Applicability
    applicable_task_types: list[str] = Field(
        default_factory=list,
        description="Task types this works well for"
    )

    # Metrics
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    avg_actual_vs_planned_ratio: float = Field(default=1.0, ge=0.5, le=3.0)
    quality_improvement_pct: float = Field(default=0.0)
    token_efficiency: float = Field(default=1.0)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    usage_count: int = Field(default=0, ge=0)

    class Config:
        use_enum_values = True

    @field_validator("success_rate")
    @classmethod
    def validate_success_rate(cls, v):
        """Validate success rate."""
        if not (0.0 <= v <= 1.0):
            raise ValueError("Success rate must be between 0.0 and 1.0")
        return v


class OrchestratorPattern(BaseModel):
    """Multi-agent orchestration pattern with effectiveness tracking."""

    id: Optional[int] = None
    project_id: int
    pattern_name: str = Field(..., description="e.g., 'orchestrator-worker', 'parallel-specialists'")
    description: str = Field(..., description="How agents are coordinated")

    # Agent configuration
    agent_roles: list[str] = Field(
        default_factory=list,
        description="e.g., ['orchestrator', 'frontend-specialist', 'backend-specialist']"
    )
    coordination_type: CoordinationType
    num_agents: int = Field(default=1, ge=1, le=100)

    # Effectiveness metrics
    effectiveness_improvement_pct: float = Field(default=0.0)
    handoff_success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    speedup_factor: float = Field(default=1.0, ge=1.0, le=100.0)
    token_overhead_multiplier: float = Field(default=1.0, ge=1.0)

    # Applicability
    applicable_domains: list[str] = Field(
        default_factory=list,
        description="e.g., ['robotics', 'web', 'backend']"
    )
    applicable_task_types: list[str] = Field(
        default_factory=list,
        description="Task types this pattern works for"
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    execution_count: int = Field(default=0, ge=0)
    successful_executions: int = Field(default=0, ge=0)

    class Config:
        use_enum_values = True

    @field_validator("handoff_success_rate")
    @classmethod
    def validate_handoff_rate(cls, v):
        """Validate handoff success rate."""
        if not (0.0 <= v <= 1.0):
            raise ValueError("Handoff success rate must be between 0.0 and 1.0")
        return v


class ValidationRule(BaseModel):
    """Rule for validating plans before execution."""

    id: Optional[int] = None
    project_id: int
    rule_name: str = Field(..., description="e.g., 'check-task-duration', 'verify-dependencies'")
    description: str = Field(..., description="What this rule checks")

    # Rule definition
    rule_type: ValidationRuleType
    check_function: str = Field(..., description="Python function name or formal check")
    parameters: dict = Field(
        default_factory=dict,
        description="Rule-specific parameters (e.g., {'max_duration_hours': 8})"
    )

    # Applicability
    applicable_to_task_types: list[str] = Field(
        default_factory=list,
        description="Task types this rule applies to"
    )
    applies_to_phases: list[str] = Field(
        default_factory=list,
        description="Phases this rule checks (empty = all)"
    )

    # Risk assessment
    risk_level: str = Field(default="medium")  # low|medium|high|critical
    dependencies: list[str] = Field(
        default_factory=list,
        description="Other rules that must pass first"
    )

    # Effectiveness metrics
    accuracy_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    precision: float = Field(default=0.0, ge=0.0, le=1.0)
    recall: float = Field(default=0.0, ge=0.0, le=1.0)
    f1_score: float = Field(default=0.0, ge=0.0, le=1.0)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    execution_count: int = Field(default=0, ge=0)
    violations_caught: int = Field(default=0, ge=0)

    class Config:
        use_enum_values = True

    @field_validator("accuracy_pct")
    @classmethod
    def validate_accuracy(cls, v):
        """Validate accuracy percentage."""
        if not (0.0 <= v <= 100.0):
            raise ValueError("Accuracy must be between 0.0 and 100.0")
        return v


class ExecutionFeedback(BaseModel):
    """Feedback from plan execution used to improve future planning."""

    id: Optional[int] = None
    project_id: int
    task_id: Optional[int] = None
    pattern_id: Optional[int] = None
    orchestration_pattern_id: Optional[int] = None

    # Execution results
    execution_outcome: ExecutionOutcome
    execution_quality_score: float = Field(default=0.0, ge=0.0, le=1.0)

    # Duration tracking
    planned_duration_minutes: Optional[int] = None
    actual_duration_minutes: Optional[int] = None
    duration_variance_pct: float = Field(default=0.0)

    # Execution details
    blockers_encountered: list[str] = Field(
        default_factory=list,
        description="What went wrong or was unexpected"
    )
    adjustments_made: list[str] = Field(
        default_factory=list,
        description="Changes to plan during execution"
    )
    assumption_violations: list[str] = Field(
        default_factory=list,
        description="Plan assumptions that didn't hold"
    )

    # Learning
    learning_extracted: Optional[str] = Field(
        default=None,
        description="Key insights from this execution"
    )
    confidence_in_learning: float = Field(default=0.0, ge=0.0, le=1.0)

    # Metrics
    quality_metrics: dict = Field(
        default_factory=dict,
        description="Custom quality metrics (e.g., {'code_coverage': 0.85})"
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    executor_agent: Optional[str] = None
    phase_number: Optional[int] = None

    class Config:
        use_enum_values = True

    @field_validator("execution_quality_score", "confidence_in_learning")
    @classmethod
    def validate_scores(cls, v):
        """Validate scores are between 0 and 1."""
        if not (0.0 <= v <= 1.0):
            raise ValueError("Score must be between 0.0 and 1.0")
        return v

    def calculate_duration_variance(self) -> None:
        """Calculate duration variance if both planned and actual are set."""
        if self.planned_duration_minutes and self.actual_duration_minutes:
            self.duration_variance_pct = (
                (self.actual_duration_minutes - self.planned_duration_minutes) /
                self.planned_duration_minutes * 100
            )


# ============================================================================
# GOAL DECOMPOSITION MODELS (Phase 4)
# ============================================================================


class GoalDecompositionStatus(str, Enum):
    """Status of a goal decomposition."""
    PENDING = "pending"
    DECOMPOSING = "decomposing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFINED = "refined"


class TaskNodeStatus(str, Enum):
    """Status of a task node in decomposition."""
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class TaskNode(BaseModel):
    """Represents a single task in a decomposed goal."""

    id: str
    title: str
    description: str = ""

    # Hierarchy
    parent_id: Optional[str] = None
    subtask_ids: list[str] = Field(default_factory=list)

    # Dependencies
    depends_on: list[str] = Field(default_factory=list)
    blocks: list[str] = Field(default_factory=list)

    # Effort & Complexity
    estimated_effort_minutes: int = Field(default=0, ge=0)
    estimated_complexity: int = Field(default=5, ge=1, le=10)
    estimated_priority: int = Field(default=5, ge=1, le=10)

    # Status & Tracking
    status: TaskNodeStatus = TaskNodeStatus.PENDING
    sequence_order: int = Field(default=0, ge=0)
    critical_path: bool = False

    # Metadata
    tags: list[str] = Field(default_factory=list)
    assignee: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class Goal(BaseModel):
    """Represents a high-level goal to be decomposed."""

    id: str
    title: str
    description: str
    context: Optional[str] = None

    # Constraints
    target_effort_minutes: Optional[int] = None
    target_complexity: Optional[int] = None
    deadline: Optional[datetime] = None

    # Metadata
    project_id: Optional[int] = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class DecomposedGoal(BaseModel):
    """Result of decomposing a goal into tasks."""

    goal_id: str
    goal_title: str

    # Task breakdown
    root_tasks: list[TaskNode] = Field(default_factory=list)
    all_tasks: dict[str, TaskNode] = Field(default_factory=dict)

    # Analysis
    total_estimated_effort: int = Field(default=0, ge=0)
    avg_complexity: float = Field(default=0.0, ge=0.0)
    num_tasks: int = Field(default=0, ge=0)
    num_subtasks: int = Field(default=0, ge=0)
    max_depth: int = Field(default=0, ge=0)
    critical_path_length: int = Field(default=0, ge=0)

    # Quality metrics
    completeness_score: float = Field(default=0.0, ge=0.0, le=1.0)
    clarity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    feasibility_score: float = Field(default=0.0, ge=0.0, le=1.0)

    # Metadata
    decomposition_method: str = "goal_decomposition_service"
    decomposed_by: Optional[str] = None
    decomposed_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class DecompositionResult(BaseModel):
    """Complete result of a decomposition operation."""

    success: bool
    decomposed_goal: Optional[DecomposedGoal] = None
    error_message: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)

    execution_time_seconds: float = Field(default=0.0, ge=0.0)
    tokens_used: dict = Field(default_factory=dict)

    class Config:
        use_enum_values = True
