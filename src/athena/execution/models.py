"""Data models for Phase 7 Execution Intelligence."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskOutcome(str, Enum):
    """Possible outcomes of task execution."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    BLOCKED = "blocked"


class DeviationSeverity(str, Enum):
    """Severity levels for plan deviations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AssumptionValidationType(str, Enum):
    """Types of assumption validation."""
    AUTO = "auto"  # Sensor data, automatic checks
    MANUAL = "manual"  # User input
    EXTERNAL = "external"  # API calls
    SENSOR = "sensor"  # System monitors


class ReplanningStrategy(str, Enum):
    """Strategies for adaptive replanning."""
    NONE = "none"  # Continue as planned
    LOCAL = "local"  # Adjust current task parameters
    SEGMENT = "segment"  # Replan next 3-5 tasks
    FULL = "full"  # Generate completely new plan
    ABORT = "abort"  # Stop and escalate


@dataclass
class TaskExecutionRecord:
    """Record of actual task execution."""
    task_id: str
    planned_start: datetime
    actual_start: Optional[datetime] = None
    planned_duration: timedelta = field(default_factory=lambda: timedelta(0))
    actual_duration: Optional[timedelta] = None
    outcome: Optional[TaskOutcome] = None
    resources_planned: Dict[str, float] = field(default_factory=dict)
    resources_used: Dict[str, float] = field(default_factory=dict)
    deviation: float = 0.0  # -1.0 to 1.0
    confidence: float = 0.0  # 0.0 to 1.0
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PlanDeviation:
    """Metrics about overall plan deviation."""
    time_deviation: timedelta
    time_deviation_percent: float
    resource_deviation: Dict[str, float]
    completion_rate: float  # 0.0 to 1.0
    completed_tasks: int
    total_tasks: int
    tasks_at_risk: List[str]
    critical_path: List[str]
    estimated_completion: datetime
    confidence: float
    deviation_severity: DeviationSeverity
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AssumptionValidationResult:
    """Result of validating an assumption."""
    assumption_id: str
    valid: bool
    validation_time: datetime
    validation_type: AssumptionValidationType
    actual_value: Any
    expected_value: Any
    confidence: float
    error_margin: float = 0.0
    notes: str = ""


@dataclass
class AssumptionViolation:
    """A violated assumption that requires attention."""
    assumption_id: str
    violation_time: datetime
    severity: DeviationSeverity
    impact: str  # Description of impact
    mitigation: str  # Suggested mitigation
    replanning_required: bool
    affected_tasks: List[str] = field(default_factory=list)
    validation_result: Optional[AssumptionValidationResult] = None


@dataclass
class ReplanningEvaluation:
    """Evaluation of whether replanning is needed."""
    replanning_needed: bool
    strategy: ReplanningStrategy
    confidence: float
    rationale: str
    affected_tasks: List[str]
    estimated_time_impact: timedelta
    estimated_cost_impact: float
    risk_level: str  # low/medium/high
    recommended_option: int
    evaluation_time: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ReplanningOption:
    """A possible replanning option."""
    option_id: int
    title: str
    description: str
    timeline_impact: timedelta
    cost_impact: float
    resource_impact: Dict[str, float]
    success_probability: float
    implementation_effort: str  # low/medium/high/very_high
    risks: List[str] = field(default_factory=list)
    benefits: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExecutionPattern:
    """Pattern learned from execution outcomes."""
    pattern_id: str
    description: str
    confidence: float  # 0.0 to 1.0
    frequency: int  # How many times observed
    affected_tasks: List[str]
    impact: float  # -1.0 to 1.0 (negative=bad, positive=good)
    actionable: bool  # Whether we can act on it
    recommendation: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
