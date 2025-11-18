"""Data models for compression features (v1.1).

Dataclasses for temporal decay, importance budgeting, and consolidation compression.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional


# ============================================================================
# Enums
# ============================================================================


class CompressionLevel(int, Enum):
    """Compression level (0-3)."""

    NONE = 0  # No compression (100% fidelity)
    SUMMARY = 1  # ~50% compression (detailed summary)
    GIST = 2  # ~80% compression (key points only)
    REFERENCE = 3  # ~95% compression (metadata only)


# ============================================================================
# Temporal Decay Models
# ============================================================================


@dataclass
class TemporalDecayConfig:
    """Configuration for temporal decay compression."""

    enable: bool = True

    # Age thresholds for each compression level (in days)
    decay_schedule: Dict[str, int] = field(
        default_factory=lambda: {
            "recent": 7,  # < 7 days: no compression
            "detailed": 30,  # 7-30 days: 50% compression
            "gist": 90,  # 30-90 days: 80% compression
            "reference": 999,  # > 90 days: 95% compression
        }
    )

    # Optional: custom compression settings
    min_fidelity: float = 0.5  # Don't return < 50% quality
    enable_caching: bool = True  # Cache compressed versions

    def get_level(self, age_days: int) -> CompressionLevel:
        """
        Determine compression level based on age.

        Args:
            age_days: Age of memory in days

        Returns:
            CompressionLevel (0-3)
        """
        if age_days < self.decay_schedule["recent"]:
            return CompressionLevel.NONE
        elif age_days < self.decay_schedule["detailed"]:
            return CompressionLevel.SUMMARY
        elif age_days < self.decay_schedule["gist"]:
            return CompressionLevel.GIST
        else:
            return CompressionLevel.REFERENCE

    def get_fidelity(self, compression_level: CompressionLevel) -> float:
        """
        Get approximate fidelity for compression level.

        Args:
            compression_level: Compression level (0-3)

        Returns:
            Fidelity (0.0-1.0) where 1.0 is full content
        """
        fidelity_map = {
            CompressionLevel.NONE: 1.0,
            CompressionLevel.SUMMARY: 0.5,
            CompressionLevel.GIST: 0.2,
            CompressionLevel.REFERENCE: 0.05,
        }
        return fidelity_map.get(compression_level, 1.0)


# ============================================================================
# Importance Weighted Budgeting Models
# ============================================================================


@dataclass
class ImportanceWeightedBudgetConfig:
    """Configuration for importance-weighted budgeting."""

    enable: bool = True

    # Weights for importance score calculation
    # Must sum to 1.0
    weights: Dict[str, float] = field(
        default_factory=lambda: {
            "usefulness": 0.40,  # usefulness_score field
            "recency": 0.30,  # exponential decay of age
            "frequency": 0.20,  # access_count field
            "domain": 0.10,  # entity_type based weights
        }
    )

    # Domain type weights
    domain_weights: Dict[str, float] = field(
        default_factory=lambda: {
            "decision": 1.0,  # Highest value
            "pattern": 0.9,
            "fact": 0.8,
            "context": 0.6,  # Lowest value
        }
    )

    # Thresholds
    min_usefulness_score: float = 0.3  # Skip very low-value memories
    access_count_cap: int = 10  # Normalize high counts at 10 accesses

    def validate(self):
        """Verify weights sum to 1.0."""
        total = sum(self.weights.values())
        assert abs(total - 1.0) < 0.01, f"Weights must sum to 1.0, got {total}"

    def calculate_value_score(
        self, usefulness: float, age_days: int, access_count: int, entity_type: str = "fact"
    ) -> float:
        """
        Calculate importance score for a memory.

        Args:
            usefulness: usefulness_score (0.0-1.0)
            age_days: Age in days
            access_count: Number of times accessed
            entity_type: Type of memory (fact, pattern, decision, context)

        Returns:
            Importance score (0.0-1.0)
        """
        # Calculate recency boost (exponential decay)
        recency_boost = min(1.0, max(0.0, (1.0 - (age_days / 365.0))))

        # Normalize access count
        normalized_freq = min(1.0, access_count / self.access_count_cap)

        # Get domain weight
        domain_weight = self.domain_weights.get(entity_type, 0.8)

        # Weighted combination
        score = (
            self.weights["usefulness"] * usefulness
            + self.weights["recency"] * recency_boost
            + self.weights["frequency"] * normalized_freq
            + self.weights["domain"] * domain_weight
        )

        return score


# ============================================================================
# Consolidation Compression Models
# ============================================================================


@dataclass
class ConsolidationCompressionConfig:
    """Configuration for consolidation compression."""

    enable: bool = True

    # Generate executive summaries during consolidation
    generate_executive_summary: bool = True

    # Compression quality targets
    target_compression_ratio: float = 0.1  # 10% of original (10x compression)
    min_fidelity: float = 0.85  # Executive summary should preserve 85% of meaning

    # Token estimation
    tokens_per_char: float = 0.25  # ~4 chars per token


@dataclass
class CompressedMemory:
    """Memory with compression metadata."""

    memory_id: int
    content_full: str
    content_compressed: Optional[str] = None
    compression_level: CompressionLevel = CompressionLevel.NONE
    compression_timestamp: Optional[datetime] = None
    tokens_original: int = 0
    tokens_compressed: int = 0
    fidelity: float = 1.0  # 1.0=full, 0.5=50% quality

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Consolidation compression metadata
    content_executive: Optional[str] = None
    compression_source_events: Optional[list] = None
    compression_generated_at: Optional[datetime] = None

    @property
    def tokens_saved(self) -> int:
        """How many tokens saved by compression."""
        return self.tokens_original - self.tokens_compressed

    @property
    def is_compressed(self) -> bool:
        """Whether this memory is currently compressed."""
        return self.compression_level != CompressionLevel.NONE

    @property
    def compression_ratio(self) -> float:
        """Compression ratio (compressed/original)."""
        if self.tokens_original == 0:
            return 0.0
        return self.tokens_compressed / self.tokens_original


# ============================================================================
# Master Compression Configuration
# ============================================================================


@dataclass
class CompressionConfig:
    """Master configuration for all compression features."""

    temporal_decay: TemporalDecayConfig = field(default_factory=TemporalDecayConfig)
    importance_budgeting: ImportanceWeightedBudgetConfig = field(
        default_factory=ImportanceWeightedBudgetConfig
    )
    consolidation_compression: ConsolidationCompressionConfig = field(
        default_factory=ConsolidationCompressionConfig
    )

    # Global settings
    enable_all: bool = True
    default_min_fidelity: float = 0.5
    enable_caching: bool = True

    # Logging & metrics
    log_compression_operations: bool = True
    track_compression_metrics: bool = True

    def validate(self):
        """Validate all sub-configurations."""
        self.temporal_decay.get_level(0)  # Basic validation
        self.importance_budgeting.validate()
        # consolidation_compression has no validation

    def to_dict(self) -> Dict:
        """Export configuration as dictionary."""
        return {
            "temporal_decay": {
                "enable": self.temporal_decay.enable,
                "decay_schedule": self.temporal_decay.decay_schedule,
                "min_fidelity": self.temporal_decay.min_fidelity,
            },
            "importance_budgeting": {
                "enable": self.importance_budgeting.enable,
                "weights": self.importance_budgeting.weights,
                "domain_weights": self.importance_budgeting.domain_weights,
            },
            "consolidation_compression": {
                "enable": self.consolidation_compression.enable,
                "generate_executive_summary": self.consolidation_compression.generate_executive_summary,
                "target_compression_ratio": self.consolidation_compression.target_compression_ratio,
            },
            "global": {
                "enable_all": self.enable_all,
                "default_min_fidelity": self.default_min_fidelity,
                "enable_caching": self.enable_caching,
            },
        }


# ============================================================================
# Result Models (for API responses)
# ============================================================================


@dataclass
class CompressionMetrics:
    """Metrics from compression operations."""

    total_memories: int
    compressed_memories: int
    total_tokens_original: int
    total_tokens_compressed: int
    average_fidelity: float
    compression_timestamp: datetime = field(default_factory=datetime.now)

    @property
    def overall_compression_ratio(self) -> float:
        """Overall compression across all memories."""
        if self.total_tokens_original == 0:
            return 0.0
        return self.total_tokens_compressed / self.total_tokens_original

    @property
    def compression_percentage(self) -> float:
        """What percentage of memories are compressed."""
        if self.total_memories == 0:
            return 0.0
        return (self.compressed_memories / self.total_memories) * 100
