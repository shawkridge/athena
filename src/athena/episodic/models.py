"""Data models for episodic memory."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class EventType(str, Enum):
    """Types of episodic events."""

    CONVERSATION = "conversation"
    ACTION = "action"
    DECISION = "decision"
    ERROR = "error"
    SUCCESS = "success"
    FILE_CHANGE = "file_change"
    TEST_RUN = "test_run"
    DEPLOYMENT = "deployment"
    REFACTORING = "refactoring"
    DEBUGGING = "debugging"


class CodeEventType(str, Enum):
    """Specialized event types for code-aware memory tracking."""

    CODE_EDIT = "code_edit"  # File/symbol-level edit with diff
    SYMBOL_LOOKUP = "symbol_lookup"  # Navigate to function/class definition
    REFACTORING = "refactoring"  # Semantic code transformation pattern
    TEST_RUN = "test_run"  # Test execution with pass/fail metrics
    BUG_DISCOVERY = "bug_discovery"  # Stack trace and reproduction steps
    PERFORMANCE_PROFILE = "perf_profile"  # Timing/memory metrics
    CODE_REVIEW = "code_review"  # Feedback on code structure
    ARCHITECTURE_DECISION = "arch_decision"  # Major design choice
    DEPENDENCY_CHANGE = "dependency_change"  # Add/remove/update dependency
    MERGE_CONFLICT = "merge_conflict"  # Git merge with resolution


class EventOutcome(str, Enum):
    """Outcomes of events."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    ONGOING = "ongoing"


class EvidenceType(str, Enum):
    """Types of evidence for episodic events (source of knowledge)."""

    OBSERVED = "observed"  # Directly witnessed/confirmed by user
    INFERRED = "inferred"  # Derived from code analysis, logs, or context
    DEDUCED = "deduced"  # Logically concluded from other facts
    HYPOTHETICAL = "hypothetical"  # Speculative or assumed
    LEARNED = "learned"  # Extracted as a procedure or pattern
    EXTERNAL = "external"  # From external source (docs, web, etc.)


class EventContext(BaseModel):
    """Context snapshot at time of event."""

    cwd: Optional[str] = None
    files: list[str] = Field(default_factory=list)
    task: Optional[str] = None
    phase: Optional[str] = None
    branch: Optional[str] = None


class EpisodicEvent(BaseModel):
    """Temporal event in episodic memory."""

    id: Optional[int] = None
    project_id: int
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    event_type: Optional[EventType] = None  # Optional to handle legacy data with unknown types
    content: str
    outcome: Optional[EventOutcome] = None

    # Context snapshot
    context: EventContext = Field(default_factory=EventContext)

    # Metrics
    duration_ms: Optional[int] = None
    files_changed: int = 0
    lines_added: int = 0
    lines_deleted: int = 0

    # Learning
    learned: Optional[str] = None
    confidence: float = 1.0

    # Evidence tracking (what kind of knowledge is this?)
    evidence_type: EvidenceType = EvidenceType.OBSERVED  # How was this knowledge acquired?
    source_id: Optional[str] = None  # ID of the source (file path, URL, agent ID, etc.)
    evidence_quality: float = Field(
        default=1.0, ge=0.0, le=1.0
    )  # Quality of the evidence (0.0-1.0) - auto-inferred during consolidation

    # Lifecycle management (activation-based system for consolidation tracking)
    lifecycle_status: str = "active"  # 'active', 'consolidated', 'archived'
    consolidation_score: float = Field(
        default=0.0, ge=0.0, le=1.0
    )  # Likelihood pattern was extracted (0.0-1.0)
    last_activation: datetime = Field(default_factory=datetime.now)  # Last time accessed/consolidated
    activation_count: int = 0  # How many times retrieved or consolidated

    # Code-aware tracking (optional fields for code events)
    code_event_type: Optional[CodeEventType] = None
    file_path: Optional[str] = None  # Absolute or relative file path
    symbol_name: Optional[str] = None  # Function, class, or module name
    symbol_type: Optional[str] = None  # 'function', 'class', 'method', 'module'
    language: Optional[str] = None  # 'python', 'typescript', 'go', etc.
    diff: Optional[str] = None  # Code diff (unified diff format)
    git_commit: Optional[str] = None  # Git commit hash
    git_author: Optional[str] = None  # Git author name/email
    test_name: Optional[str] = None  # Test function name
    test_passed: Optional[bool] = None  # Test outcome
    error_type: Optional[str] = None  # Exception/error class name
    stack_trace: Optional[str] = None  # Stack trace for debugging
    performance_metrics: Optional[dict] = None  # {metric_name: value}
    code_quality_score: Optional[float] = None  # 0.0-1.0 quality rating

    # Enhanced context metadata for working memory optimization
    project_name: Optional[str] = None  # Project name for context
    project_goal: Optional[str] = None  # Current project goal/objective
    project_phase_status: Optional[str] = (
        None  # Current phase of project (planning, development, testing, etc.)
    )
    importance_score: float = Field(
        default=0.5, ge=0.0, le=1.0
    )  # 0.0-1.0, drives working memory ranking
    actionability_score: float = Field(
        default=0.5, ge=0.0, le=1.0
    )  # 0.0-1.0, indicates if item is actionable
    context_completeness_score: float = Field(
        default=0.5, ge=0.0, le=1.0
    )  # 0.0-1.0, whether item has sufficient context
    has_next_step: bool = False  # Whether this discovery has a clear next step
    has_blocker: bool = False  # Whether this discovery has blockers
    required_decisions: Optional[str] = None  # JSON list of decisions needed

    model_config = ConfigDict(use_enum_values=True)


class EventMetric(BaseModel):
    """Metric associated with an event."""

    id: Optional[int] = None
    event_id: int
    metric_name: str
    metric_value: str  # JSON string
