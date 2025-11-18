"""Configurable decay rates for working memory items.

Supports:
- Content-type specific half-lives
- Importance-based multipliers
- Custom per-item decay settings
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class DecayConfig:
    """Configuration for working memory decay."""

    default_half_life: float = 30.0  # seconds

    # Decay by content type (verbal, spatial, action, decision)
    content_type_half_lives: Dict[str, float] = field(
        default_factory=lambda: {
            "verbal": 30.0,  # Fast decay (verbal loop)
            "spatial": 45.0,  # Slightly slower (spatial sketchpad)
            "action": 20.0,  # Very fast (transient actions)
            "decision": 60.0,  # Slow decay (important decisions)
        }
    )

    # Decay by importance level
    importance_multipliers: Dict[str, float] = field(
        default_factory=lambda: {
            "low": 1.5,  # Low importance: decay 1.5x faster
            "medium": 1.0,  # Medium: normal decay
            "high": 0.7,  # High: decay 1.4x slower (0.7 = 1/1.43)
        }
    )

    def get_half_life_for_content_type(self, content_type: str) -> float:
        """Get half-life for a content type.

        Args:
            content_type: Type of content ("verbal", "spatial", "action", "decision")

        Returns:
            Half-life in seconds
        """
        return self.content_type_half_lives.get(content_type, self.default_half_life)

    def get_multiplier_for_importance(self, importance: float) -> float:
        """Get decay multiplier for importance level.

        Args:
            importance: Importance score 0-1

        Returns:
            Decay multiplier (>1 = faster decay, <1 = slower decay)
        """
        if importance < 0.33:
            return self.importance_multipliers.get("low", 1.5)
        elif importance < 0.67:
            return self.importance_multipliers.get("medium", 1.0)
        else:
            return self.importance_multipliers.get("high", 0.7)

    def compute_effective_half_life(self, content_type: str, importance: float) -> float:
        """Compute effective half-life for an item.

        Combines content type half-life with importance multiplier.

        Args:
            content_type: Type of content
            importance: Importance score 0-1

        Returns:
            Effective half-life in seconds
        """
        base_half_life = self.get_half_life_for_content_type(content_type)
        multiplier = self.get_multiplier_for_importance(importance)
        return base_half_life * multiplier

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "default_half_life": self.default_half_life,
            "content_type_half_lives": self.content_type_half_lives,
            "importance_multipliers": self.importance_multipliers,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DecayConfig":
        """Create DecayConfig from dictionary."""
        return cls(
            default_half_life=data.get("default_half_life", 30.0),
            content_type_half_lives=data.get(
                "content_type_half_lives",
                {
                    "verbal": 30.0,
                    "spatial": 45.0,
                    "action": 20.0,
                    "decision": 60.0,
                },
            ),
            importance_multipliers=data.get(
                "importance_multipliers",
                {
                    "low": 1.5,
                    "medium": 1.0,
                    "high": 0.7,
                },
            ),
        )


class DecayCalculator:
    """Calculates activation with configurable decay."""

    def __init__(self, config: Optional[DecayConfig] = None):
        """Initialize decay calculator.

        Args:
            config: DecayConfig instance (uses defaults if None)
        """
        self.config = config or DecayConfig()
        logger.info(
            f"DecayCalculator initialized with default_half_life={self.config.default_half_life}s"
        )

    def compute_activation(
        self,
        importance: float,
        content_type: str,
        age_seconds: float,
    ) -> float:
        """Compute activation with decay.

        Args:
            importance: Initial importance 0-1
            content_type: Type of content
            age_seconds: Age of item in seconds

        Returns:
            Current activation level (importance * decay_factor)
        """
        # Get effective half-life
        half_life = self.config.compute_effective_half_life(content_type, importance)

        # Compute exponential decay
        decay_factor = math.exp(-age_seconds / half_life)

        # Return weighted activation
        return importance * decay_factor

    def get_remaining_lifespan(
        self,
        importance: float,
        content_type: str,
        threshold: float = 0.1,
    ) -> float:
        """Get time until item drops below threshold activation.

        Args:
            importance: Initial importance 0-1
            content_type: Type of content
            threshold: Activation threshold (default 0.1)

        Returns:
            Time in seconds until item drops below threshold
        """
        # Get effective half-life
        half_life = self.config.compute_effective_half_life(content_type, importance)

        # Solve for t: importance * exp(-t/half_life) = threshold
        # exp(-t/half_life) = threshold / importance
        # -t/half_life = ln(threshold / importance)
        # t = -half_life * ln(threshold / importance)

        if importance <= 0 or threshold < 0:
            return 0.0

        ratio = threshold / importance
        if ratio >= 1:
            return 0.0  # Already below threshold

        lifespan = -half_life * math.log(ratio)
        return max(0.0, lifespan)

    def update_config(self, new_config: DecayConfig) -> None:
        """Update decay configuration.

        Args:
            new_config: New DecayConfig instance
        """
        logger.info(f"Updating DecayConfig: {new_config.default_half_life}s default")
        self.config = new_config

    def update_content_type_half_life(self, content_type: str, half_life: float) -> None:
        """Update half-life for a specific content type.

        Args:
            content_type: Content type to update
            half_life: New half-life in seconds
        """
        self.config.content_type_half_lives[content_type] = half_life
        logger.info(f"Updated {content_type} half-life to {half_life}s")

    def update_importance_multiplier(self, importance_level: str, multiplier: float) -> None:
        """Update decay multiplier for an importance level.

        Args:
            importance_level: "low", "medium", or "high"
            multiplier: New multiplier (>1 = faster decay)
        """
        self.config.importance_multipliers[importance_level] = multiplier
        logger.info(f"Updated {importance_level} importance multiplier to {multiplier}x")
