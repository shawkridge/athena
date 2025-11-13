"""Data models for dream procedures."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class DreamType(str, Enum):
    """Types of dream variants."""

    CONSTRAINT_RELAXATION = "constraint_relaxation"
    CROSS_PROJECT_SYNTHESIS = "cross_project_synthesis"
    PARAMETER_EXPLORATION = "parameter_exploration"
    CONDITIONAL_VARIANT = "conditional_variant"


class DreamTier(int, Enum):
    """Viability tiers for dreams."""

    VIABLE = 1  # Ready to test, high confidence
    SPECULATIVE = 2  # Interesting but risky, medium confidence
    ARCHIVE = 3  # Creative but not currently viable, low confidence


class DreamStatus(str, Enum):
    """Status of a dream procedure."""

    PENDING_EVALUATION = "pending_evaluation"
    EVALUATED = "evaluated"
    PENDING_TEST = "pending_test"
    TESTED = "tested"
    ARCHIVED = "archived"


class DreamProcedure(BaseModel):
    """A speculative procedure variant generated during dream phase."""

    id: Optional[int] = None
    base_procedure_id: int
    base_procedure_name: str
    dream_type: DreamType
    code: str  # Python code of the dream variant
    model_used: str  # Which model generated this (deepseek-v3.1, qwen-coder, local, etc.)
    reasoning: str  # Why this variant was generated
    generated_description: Optional[str] = None

    # Evaluation (by Claude)
    status: DreamStatus = DreamStatus.PENDING_EVALUATION
    tier: Optional[DreamTier] = None  # Assigned by Claude
    viability_score: Optional[float] = None  # 0.0-1.0 confidence
    claude_reasoning: Optional[str] = None  # Claude's explanation

    # Testing
    test_outcome: Optional[str] = None  # success|failure|pending
    test_error: Optional[str] = None  # Error message if failed
    test_timestamp: Optional[datetime] = None

    # Metrics
    novelty_score: Optional[float] = None  # How novel is this dream?
    cross_project_matches: int = 0  # How many projects could use this?
    effectiveness_metric: Optional[float] = None  # Does it work better than baseline?

    # Metadata
    generated_at: datetime = Field(default_factory=datetime.now)
    evaluated_at: Optional[datetime] = None
    created_by: str = "dream_system"

    model_config = ConfigDict(use_enum_values=True)


class DreamGenerationRun(BaseModel):
    """Record of a dream generation run."""

    id: Optional[int] = None
    strategy: str  # "light", "balanced", "deep"
    timestamp: datetime = Field(default_factory=datetime.now)
    total_dreams_generated: int
    constraint_relaxation_count: int
    cross_project_synthesis_count: int
    parameter_exploration_count: int
    conditional_variant_count: int
    duration_seconds: float
    model_usage: dict = Field(default_factory=dict)  # Track API call counts per model


class DreamMetrics(BaseModel):
    """Aggregated dream system metrics."""

    id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    # Quality metrics
    average_viability_score: float = 0.0
    tier1_count: int = 0  # Viable dreams
    tier2_count: int = 0  # Speculative dreams
    tier3_count: int = 0  # Archive dreams

    # Testing metrics
    tier1_test_success_rate: float = 0.0  # % of tier 1 dreams that passed tests
    tier1_test_count: int = 0

    # Novelty metrics
    average_novelty_score: float = 0.0
    high_novelty_count: int = 0  # Dreams with novelty > 0.7

    # Cross-project metrics
    cross_project_adoption_rate: float = 0.0  # % of dreams used across projects
    dreams_adopted_count: int = 0

    # Efficiency metrics
    average_generation_time_seconds: float = 0.0
    api_requests_per_dream: float = 0.0

    # Compound score
    novelty_score_weighted: float = 0.0  # 60% of compound
    quality_evolution_weighted: float = 0.0  # 15% of compound
    cross_project_leverage_weighted: float = 0.0  # 15% of compound
    efficiency_weighted: float = 0.0  # 10% of compound
    compound_health_score: float = 0.0  # Overall 0.0-1.0

    model_config = ConfigDict(use_enum_values=True)
