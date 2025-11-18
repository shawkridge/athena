"""Data models for meta-cognition system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List


class GapType(str, Enum):
    """Type of knowledge gap."""

    CONTRADICTION = "contradiction"
    UNCERTAINTY = "uncertainty"
    MISSING_INFO = "missing_info"


class GapPriority(str, Enum):
    """Priority level of a knowledge gap."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SaturationLevel(str, Enum):
    """Cognitive load saturation levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InsightType(str, Enum):
    """Type of meta-cognition insight."""

    MEMORY_QUALITY = "memory_quality"
    LEARNING_STRATEGY = "learning_strategy"
    CONTRADICTION = "contradiction"
    CAPACITY = "capacity"
    BIAS = "bias"


@dataclass
class QualityMetrics:
    """Memory quality metrics."""

    memory_id: int
    memory_layer: str  # 'semantic', 'episodic', 'procedural', etc
    query_count: int = 0
    successful_retrievals: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    accuracy_score: float = 0.0
    last_evaluated: Optional[datetime] = None

    def calculate_accuracy(self) -> float:
        """Calculate accuracy: successful / total_queries."""
        if self.query_count == 0:
            return 1.0
        return self.successful_retrievals / self.query_count

    def calculate_false_positive_rate(self) -> float:
        """Calculate false positive rate."""
        if self.query_count == 0:
            return 0.0
        return self.false_positives / self.query_count

    def calculate_quality_score(self) -> float:
        """
        Calculate overall quality score.

        quality = accuracy × (1 - false_positive_rate)
        """
        accuracy = self.calculate_accuracy()
        false_pos_rate = self.calculate_false_positive_rate()
        return accuracy * (1.0 - false_pos_rate)


@dataclass
class LearningRate:
    """Encoding strategy learning rate."""

    encoding_strategy: str
    success_rate: float = 0.0
    trial_count: int = 0
    success_count: int = 0
    recommendation: str = "neutral"  # 'increase_use', 'decrease_use', 'neutral'
    last_evaluated: Optional[datetime] = None

    def update_success_rate(self):
        """Update success rate based on trials."""
        if self.trial_count == 0:
            self.success_rate = 0.0
        else:
            self.success_rate = self.success_count / self.trial_count

    def generate_recommendation(self):
        """Generate recommendation based on success rate."""
        if self.success_rate >= 0.8:
            self.recommendation = "increase_use"
        elif self.success_rate <= 0.4:
            self.recommendation = "decrease_use"
        else:
            self.recommendation = "neutral"


@dataclass
class KnowledgeGap:
    """Knowledge gap or contradiction."""

    gap_type: GapType
    description: str
    memory_ids: List[int]
    confidence: float  # 0.0-1.0, how certain about the gap
    priority: GapPriority
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ConfidenceCalibration:
    """Confidence calibration data."""

    memory_id: int
    confidence_reported: float  # User-reported or inferred
    confidence_actual: float  # Actual accuracy
    memory_type: str
    calibration_error: float = 0.0
    updated_at: datetime = field(default_factory=datetime.now)

    def calculate_error(self):
        """Calculate calibration error."""
        self.calibration_error = abs(self.confidence_reported - self.confidence_actual)
        return self.calibration_error


@dataclass
class CognitiveLoad:
    """Cognitive load snapshot."""

    project_id: int
    active_memory_count: int
    max_capacity: int
    utilization_percent: float
    query_latency_ms: float
    saturation_level: SaturationLevel
    recommendation: str = ""
    metric_timestamp: datetime = field(default_factory=datetime.now)

    def calculate_utilization(self) -> float:
        """Calculate utilization percentage."""
        if self.max_capacity == 0:
            return 0.0
        return (self.active_memory_count / self.max_capacity) * 100.0

    def determine_saturation_level(self) -> SaturationLevel:
        """Determine saturation level based on utilization and latency."""
        utilization = self.calculate_utilization()

        if utilization > 90 or self.query_latency_ms > 500:
            return SaturationLevel.CRITICAL
        elif utilization > 75 or self.query_latency_ms > 300:
            return SaturationLevel.HIGH
        elif utilization > 50 or self.query_latency_ms > 100:
            return SaturationLevel.MEDIUM
        else:
            return SaturationLevel.LOW


@dataclass
class MetaCognitionInsight:
    """Meta-cognition insight."""

    insight_type: InsightType
    description: str
    severity: str  # 'low', 'medium', 'high'
    actionable: bool = True
    suggested_action: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
