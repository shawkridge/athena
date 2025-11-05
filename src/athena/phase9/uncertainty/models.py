"""Data models for Phase 9.1: Uncertainty-Aware Generation."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class UncertaintyType(str, Enum):
    """Types of uncertainty in planning."""

    EPISTEMIC = "epistemic"  # Knowledge uncertainty (can be reduced with more data)
    ALEATORIC = "aleatoric"  # Inherent randomness (cannot be reduced)
    MODELING = "modeling"  # Uncertainty from model approximations


class ConfidenceLevel(str, Enum):
    """Confidence level classifications."""

    VERY_LOW = "very_low"      # < 40%
    LOW = "low"                # 40-60%
    MEDIUM = "medium"          # 60-75%
    HIGH = "high"              # 75-90%
    VERY_HIGH = "very_high"    # > 90%


class PlanAlternative(BaseModel):
    """Alternative plan with confidence metrics."""

    id: Optional[int] = None
    task_id: int
    plan_type: str  # "sequential", "parallel", "iterative", "hybrid"
    steps: list[str] = Field(default_factory=list)
    estimated_duration_minutes: int
    confidence_score: float = Field(..., ge=0.0, le=1.0)  # 0-1 confidence
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    risk_factors: list[str] = Field(default_factory=list)
    parallelizable_steps: int = 0  # Number of steps that can run in parallel
    uncertainty_sources: list[str] = Field(default_factory=list)
    dependencies: list[int] = Field(default_factory=list)  # Other plan IDs this depends on
    created_at: datetime = Field(default_factory=datetime.now)
    rank: int = 1  # Rank by confidence (1=highest)

    class Config:
        use_enum_values = True


class ConfidenceScore(BaseModel):
    """Confidence score for a task/prediction/estimate."""

    id: Optional[int] = None
    task_id: int
    aspect: str  # "estimate", "prediction", "resource", "timeline", "quality"
    value: float = Field(..., ge=0.0, le=1.0)  # 0-1 confidence
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    uncertainty_sources: list[UncertaintyType] = Field(default_factory=list)
    contributing_factors: dict[str, float] = Field(default_factory=dict)  # Factor: weight
    lower_bound: Optional[float] = None  # Lower confidence bound
    upper_bound: Optional[float] = None  # Upper confidence bound
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class ConfidenceInterval(BaseModel):
    """Confidence interval for estimates (e.g., task duration)."""

    estimate: float  # Central estimate
    lower_bound: float  # Lower bound (e.g., 25th percentile)
    upper_bound: float  # Upper bound (e.g., 75th percentile)
    confidence_level: float = Field(..., ge=0.0, le=1.0)  # 0.5, 0.68, 0.95, 0.99
    unit: str = "minutes"  # Unit of measure
    method: str = "bayesian"  # Estimation method used
    sample_size: Optional[int] = None  # Number of samples used


class UncertaintyBreakdown(BaseModel):
    """Breakdown of uncertainty by source."""

    task_id: int
    total_uncertainty: float = Field(..., ge=0.0, le=1.0)  # 0-1
    uncertainty_sources: dict[str, dict] = Field(default_factory=dict)
    # {source: {type, value, explanation, reducibility}}
    reducible_uncertainty: float  # Can be reduced with more data/effort
    irreducible_uncertainty: float  # Inherent randomness
    mitigations: list[str] = Field(default_factory=list)  # Ways to reduce uncertainty
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class ConfidenceCalibration(BaseModel):
    """Calibration data for confidence score accuracy."""

    id: Optional[int] = None
    project_id: int
    aspect: str  # "estimate", "prediction", "resource", "timeline"
    predicted_confidence: float  # Predicted confidence level
    actual_outcome: bool  # Did prediction come true?
    calibration_error: Optional[float] = None  # Deviation from expected
    sample_count: int = 0  # Number of calibration samples
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class ConfidenceTrendAnalysis(BaseModel):
    """Analysis of confidence trends over time."""

    project_id: int
    aspect: str
    average_confidence: float  # Average confidence level over period
    confidence_trend: str  # "increasing", "decreasing", "stable"
    trend_strength: float = Field(..., ge=0.0, le=1.0)  # How strong the trend
    overconfidence_ratio: float = 0.0  # % of times predicted but didn't happen
    underconfidence_ratio: float = 0.0  # % of times predicted not to happen but did
    recommendations: list[str] = Field(default_factory=list)
    period_days: int = 30
    sample_size: int = 0
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True
