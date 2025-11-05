"""
Pydantic models for Predictor Agent - prediction results, confidence, patterns.

This module defines the data structures for:
- Prediction results with confidence intervals
- Bottleneck alerts and mitigation
- Temporal patterns and cycles
- Resource forecasts
"""

from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Risk levels for predictions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PatternType(str, Enum):
    """Types of temporal patterns."""
    STATIONARY = "stationary"
    TRENDING = "trending"
    CYCLICAL = "cyclical"
    SEASONAL = "seasonal"
    ANOMALOUS = "anomalous"


class ResourceType(str, Enum):
    """Resource types for bottleneck detection."""
    CPU = "cpu"
    MEMORY = "memory"
    IO = "io"
    NETWORK = "network"
    DISK = "disk"


class ConfidenceInterval(BaseModel):
    """Confidence interval for predictions."""
    lower_bound: float = Field(..., description="Lower confidence bound (default 5%)")
    point_estimate: float = Field(..., description="Point estimate (mean/median)")
    upper_bound: float = Field(..., description="Upper confidence bound (default 95%)")
    confidence_level: float = Field(default=0.9, description="Confidence level (0.0-1.0)")

    @property
    def margin_of_error(self) -> float:
        """Calculate margin of error."""
        return (self.upper_bound - self.lower_bound) / 2.0

    @property
    def relative_uncertainty(self) -> float:
        """Calculate relative uncertainty (margin / point_estimate)."""
        if self.point_estimate == 0:
            return 0.0
        return self.margin_of_error / abs(self.point_estimate)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "lower_bound": self.lower_bound,
            "point_estimate": self.point_estimate,
            "upper_bound": self.upper_bound,
            "confidence_level": self.confidence_level,
            "margin_of_error": self.margin_of_error,
            "relative_uncertainty": self.relative_uncertainty,
        }


class TemporalPattern(BaseModel):
    """Detected temporal pattern in metrics."""
    pattern_type: PatternType = Field(..., description="Type of pattern")
    strength: float = Field(..., ge=0.0, le=1.0, description="Pattern strength (0-1)")
    period_hours: Optional[float] = Field(None, description="Period in hours (for cyclical)")
    trend_slope: Optional[float] = Field(None, description="Trend slope (for trending)")
    variance: float = Field(..., ge=0.0, description="Variance of pattern")
    explanation: str = Field(..., description="Human-readable explanation")
    detected_at: datetime = Field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "pattern_type": self.pattern_type.value,
            "strength": self.strength,
            "period_hours": self.period_hours,
            "trend_slope": self.trend_slope,
            "variance": self.variance,
            "explanation": self.explanation,
            "detected_at": self.detected_at.isoformat(),
        }


class ResourceForecast(BaseModel):
    """Forecast for a specific resource."""
    resource_type: ResourceType = Field(..., description="Type of resource")
    current_usage: float = Field(..., ge=0.0, description="Current usage")
    forecasted_peak: ConfidenceInterval = Field(..., description="Peak usage forecast")
    forecasted_average: ConfidenceInterval = Field(..., description="Average usage forecast")
    time_to_peak_hours: float = Field(..., ge=0.0, description="Hours until peak")
    is_constrained: bool = Field(default=False, description="Is this resource constrained?")
    utilization_percent: float = Field(..., ge=0.0, le=100.0, description="Current utilization %")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "resource_type": self.resource_type.value,
            "current_usage": self.current_usage,
            "forecasted_peak": self.forecasted_peak.to_dict(),
            "forecasted_average": self.forecasted_average.to_dict(),
            "time_to_peak_hours": self.time_to_peak_hours,
            "is_constrained": self.is_constrained,
            "utilization_percent": self.utilization_percent,
        }


class BottleneckAlert(BaseModel):
    """Alert for predicted bottleneck."""
    resource_type: ResourceType = Field(..., description="Bottleneck resource")
    severity: RiskLevel = Field(..., description="Severity level")
    predicted_saturation_time: float = Field(..., ge=0.0, description="Hours until saturation")
    current_utilization: float = Field(..., ge=0.0, le=100.0, description="Current utilization %")
    peak_predicted_utilization: float = Field(..., ge=0.0, le=100.0, description="Predicted peak %")
    mitigation_options: list[str] = Field(default_factory=list, description="Mitigation strategies")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Prediction confidence")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "resource_type": self.resource_type.value,
            "severity": self.severity.value,
            "predicted_saturation_time": self.predicted_saturation_time,
            "current_utilization": self.current_utilization,
            "peak_predicted_utilization": self.peak_predicted_utilization,
            "mitigation_options": self.mitigation_options,
            "confidence": self.confidence,
        }


class DurationPrediction(BaseModel):
    """Prediction for task duration."""
    task_type: str = Field(..., description="Type of task")
    historical_average: float = Field(..., ge=0.0, description="Historical average in seconds")
    historical_median: float = Field(..., ge=0.0, description="Historical median in seconds")
    forecasted_duration: ConfidenceInterval = Field(..., description="Predicted duration in seconds")
    similar_tasks: int = Field(..., ge=0, description="Number of similar tasks used")
    pattern_match_score: float = Field(..., ge=0.0, le=1.0, description="How well task matches pattern")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "task_type": self.task_type,
            "historical_average": self.historical_average,
            "historical_median": self.historical_median,
            "forecasted_duration": self.forecasted_duration.to_dict(),
            "similar_tasks": self.similar_tasks,
            "pattern_match_score": self.pattern_match_score,
        }


class PredictionResult(BaseModel):
    """Complete prediction result from PredictorAgent."""
    task_id: Optional[int] = Field(None, description="Associated task ID")
    prediction_id: str = Field(..., description="Unique prediction ID")
    predicted_at: datetime = Field(default_factory=datetime.now, description="Prediction timestamp")

    # Duration prediction
    duration_prediction: Optional[DurationPrediction] = None

    # Resource forecasts
    resource_forecasts: dict[ResourceType, ResourceForecast] = Field(default_factory=dict)

    # Bottleneck alerts
    bottleneck_alerts: list[BottleneckAlert] = Field(default_factory=list)

    # Temporal patterns
    temporal_patterns: list[TemporalPattern] = Field(default_factory=list)

    # Overall metrics
    overall_risk_level: RiskLevel = Field(default=RiskLevel.LOW)
    success_probability: float = Field(..., ge=0.0, le=1.0, description="Probability of success")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall confidence (0-1)")

    # Recommendations
    recommendations: list[str] = Field(default_factory=list, description="Actionable recommendations")
    critical_constraints: list[str] = Field(default_factory=list, description="Critical constraints")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "prediction_id": self.prediction_id,
            "predicted_at": self.predicted_at.isoformat(),
            "duration_prediction": (
                self.duration_prediction.to_dict() if self.duration_prediction else None
            ),
            "resource_forecasts": {
                k.value: v.to_dict() for k, v in self.resource_forecasts.items()
            },
            "bottleneck_alerts": [alert.to_dict() for alert in self.bottleneck_alerts],
            "temporal_patterns": [pattern.to_dict() for pattern in self.temporal_patterns],
            "overall_risk_level": self.overall_risk_level.value,
            "success_probability": self.success_probability,
            "confidence_score": self.confidence_score,
            "recommendations": self.recommendations,
            "critical_constraints": self.critical_constraints,
        }


class PredictionAccuracy(BaseModel):
    """Tracking of prediction accuracy over time."""
    prediction_id: str = Field(..., description="Prediction that was made")
    actual_duration: float = Field(..., ge=0.0, description="Actual duration in seconds")
    predicted_duration: ConfidenceInterval = Field(..., description="Predicted duration")
    duration_error_percent: float = Field(..., description="Error % (negative=underestimate)")

    actual_resources: dict[ResourceType, float] = Field(default_factory=dict)
    predicted_resources: dict[ResourceType, ConfidenceInterval] = Field(default_factory=dict)
    resource_errors: dict[ResourceType, float] = Field(default_factory=dict, description="Error % per resource")

    # Confidence interval coverage
    duration_in_interval: bool = Field(..., description="Did actual fall within confidence interval?")
    resource_in_intervals: dict[ResourceType, bool] = Field(default_factory=dict)

    verified_at: datetime = Field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "prediction_id": self.prediction_id,
            "actual_duration": self.actual_duration,
            "predicted_duration": self.predicted_duration.to_dict(),
            "duration_error_percent": self.duration_error_percent,
            "actual_resources": {k.value: v for k, v in self.actual_resources.items()},
            "predicted_resources": {
                k.value: v.to_dict() for k, v in self.predicted_resources.items()
            },
            "resource_errors": {k.value: v for k, v in self.resource_errors.items()},
            "duration_in_interval": self.duration_in_interval,
            "resource_in_intervals": {k.value: v for k, v in self.resource_in_intervals.items()},
            "verified_at": self.verified_at.isoformat(),
        }
