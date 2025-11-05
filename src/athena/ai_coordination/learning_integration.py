"""Data models for learning integration - close the feedback loop.

LearningIntegration orchestrates:
- Extract lessons from execution attempts
- Find patterns (cluster similar lessons)
- Create reusable procedures
- Apply feedback to ProjectContext
- Improve processes for next cycle

This completes the loop: Execute → Learn → Improve
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PatternType(str, Enum):
    """Type of pattern in lessons."""

    ERROR_RECOVERY = "error_recovery"  # How to recover from errors
    OPTIMIZATION = "optimization"  # How to optimize code/process
    DESIGN = "design"  # Design pattern or architectural choice
    WORKFLOW = "workflow"  # Process workflow improvement
    TESTING = "testing"  # Testing strategy improvement


class FeedbackUpdateType(str, Enum):
    """Type of feedback update to apply."""

    ERROR_PATTERN = "error_pattern"  # Update error pattern
    DECISION = "decision"  # Update architectural decision
    LESSON = "lesson"  # Record lesson in project context
    RECOMMENDATION = "recommendation"  # Add recommendation


class LessonToProcedure(BaseModel):
    """Maps a single lesson to a potential procedure.

    Evaluates whether a lesson can become a reusable procedure
    and suggests initial structure.
    """

    id: Optional[int] = None

    # Source
    lesson_id: int  # From ActionCycle.lessons
    lesson_text: str = Field(..., description="The lesson learned")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)  # Can this become procedure?

    # Classification
    applies_to: list[str] = Field(
        default_factory=list, description="e.g., ['async code', 'error handling']"
    )
    pattern_type: PatternType = PatternType.OPTIMIZATION

    # Proposed procedure
    suggested_procedure_name: Optional[str] = None
    procedure_steps: list[str] = Field(
        default_factory=list, description="Draft implementation steps"
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def can_create_procedure(self) -> bool:
        """Determine if confidence is high enough to create procedure."""
        return self.confidence >= 0.7

    class Config:
        use_enum_values = True


class ProcedureCandidate(BaseModel):
    """Cluster of similar lessons ready to become a procedure.

    Groups related lessons by pattern, confidence, and frequency.
    Represents a strong candidate for procedure creation.
    """

    id: Optional[int] = None

    # Identity
    name: str  # Proposed procedure name
    pattern_type: PatternType  # Type of pattern

    # Aggregated data
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)  # Combined confidence
    source_lessons: list[int] = Field(default_factory=list)  # Which lessons contributed

    # Procedure details
    draft_procedure: dict = Field(
        default_factory=dict,
        description="{ steps: [...], context: '...', success_rate: 0.85 }",
    )
    success_rate: float = Field(default=0.5, ge=0.0, le=1.0)  # Across source lessons
    estimated_impact: float = Field(
        default=0.5, ge=0.0, le=1.0, description="How much this helps (0.0-1.0)"
    )

    # Status
    ready_for_creation: bool = False  # Should auto-create?
    created_procedure_id: Optional[int] = None  # Link to created procedure
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def frequency(self) -> int:
        """How many times this pattern appeared."""
        return len(self.source_lessons)

    class Config:
        use_enum_values = True


class FeedbackUpdate(BaseModel):
    """Update to apply to ProjectContext based on learning.

    Represents a change that should be made to project state
    based on lessons learned.
    """

    id: Optional[int] = None

    # Target
    update_type: FeedbackUpdateType  # What type of update
    target_id: Optional[str] = None  # Which error pattern / decision / lesson

    # Change
    action: str = Field(..., description="update, deprecate, replace, add")
    new_data: dict = Field(
        default_factory=dict,
        description="What to update with",
    )

    # Context
    reason: str = Field(..., description="Why this feedback")
    source_lesson_id: Optional[int] = None  # Which lesson triggered this
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    # Status
    applied: bool = False
    applied_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class LearningCycle(BaseModel):
    """Orchestration of learning from a single action cycle.

    Tracks what was learned, what was created, and what impact.
    Completes the Execute → Learn → Improve loop.
    """

    id: Optional[int] = None

    # Source
    action_cycle_id: int  # Which cycle triggered learning
    session_id: str  # Which session

    # Learning results
    lessons_extracted: int = 0
    high_confidence_lessons: int = 0  # confidence >= 0.7
    procedures_created: int = 0
    procedure_candidates_identified: int = 0

    # Feedback
    feedback_updates_created: int = 0
    feedback_updates_applied: int = 0

    # Impact
    improvements_identified: int = 0
    estimated_impact: float = Field(default=0.0, ge=0.0, le=1.0)
    estimated_time_saved_seconds: int = 0  # How much faster next attempt

    # Success metrics
    learning_cycle_success_rate: float = Field(default=0.0, ge=0.0, le=1.0)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)


class LearningMetrics(BaseModel):
    """Aggregated learning metrics for reporting."""

    total_lessons_extracted: int = 0
    total_procedures_created: int = 0
    total_feedback_applied: int = 0

    # Quality
    average_lesson_confidence: float = 0.0
    procedure_success_rate: float = 0.0
    feedback_application_rate: float = 0.0

    # Impact
    estimated_time_saved_hours: float = 0.0
    estimated_error_reduction_percent: float = 0.0
    process_improvement_ideas: int = 0

    # Timeline
    period_days: int = 7
    measurement_period_start: datetime = Field(default_factory=datetime.now)
    measurement_period_end: datetime = Field(default_factory=datetime.now)
