"""Data models for execution traces - what AI tried and what happened."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from ..episodic.models import EpisodicEvent, EventOutcome, EventType


class ExecutionOutcome(str, Enum):
    """Outcome of an execution attempt."""

    SUCCESS = "success"  # Goal achieved
    FAILURE = "failure"  # Attempt failed
    PARTIAL = "partial"  # Partially successful


class CodeChange(BaseModel):
    """Code change during execution."""

    file_path: str
    lines_added: int = 0
    lines_deleted: int = 0
    change_summary: Optional[str] = None


class ExecutionError(BaseModel):
    """Error encountered during execution."""

    error_type: str  # "syntax", "logic", "type", "runtime", "test"
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    stack_trace: Optional[str] = None


class ExecutionDecision(BaseModel):
    """Decision made during execution."""

    decision: str
    rationale: str
    alternative_considered: Optional[str] = None
    confidence: float = 0.5  # 0.0-1.0


class ExecutionLesson(BaseModel):
    """Lesson learned from execution."""

    lesson: str
    confidence: float = 0.5  # 0.0-1.0
    applies_to: list[str] = Field(default_factory=list)  # e.g., ["async code", "error handling"]


class QualityAssessment(BaseModel):
    """Assessment of execution quality."""

    code_quality: float = 0.5  # 0.0-1.0: Is code well-written?
    approach_quality: float = 0.5  # 0.0-1.0: Was approach good?
    efficiency: float = 0.5  # 0.0-1.0: Could we do it faster?
    correctness: float = 0.5  # 0.0-1.0: Did it work?


class ExecutionTrace(BaseModel):
    """Single execution attempt (extends episodic event).

    Captures what AI tried, what happened, and what was learned.
    Links to goals, tasks, and plans for context.
    """

    id: Optional[int] = None

    # Links to coordination layer
    goal_id: Optional[str] = None  # UUID as string
    task_id: Optional[str] = None  # UUID as string
    plan_id: Optional[str] = None  # UUID as string

    # Execution metadata
    session_id: str  # Session this execution happened in
    timestamp: datetime = Field(default_factory=datetime.now)
    action_type: str  # "code_generation", "testing", "refactoring", "debugging"
    description: str  # Human-readable summary

    # Execution outcome
    outcome: ExecutionOutcome

    # Code changes
    code_changes: list[CodeChange] = Field(default_factory=list)

    # Errors encountered
    errors: list[ExecutionError] = Field(default_factory=list)

    # Decisions made
    decisions: list[ExecutionDecision] = Field(default_factory=list)

    # Lessons learned
    lessons: list[ExecutionLesson] = Field(default_factory=list)

    # Quality assessment
    quality_assessment: Optional[QualityAssessment] = None

    # Metadata
    duration_seconds: int = 0
    ai_model_used: Optional[str] = None
    tokens_used: Optional[int] = None

    # Consolidation tracking
    consolidation_status: Optional[str] = None  # "unconsolidated", "consolidated"
    consolidated_at: Optional[datetime] = None

    model_config = ConfigDict(use_enum_values=True)
