"""Unified scoring framework for composite metrics.

Consolidates scoring logic across all memory layers.
Provides:
- Weighted composite scoring
- Configurable component weights
- Clamping to [0, 1] range
- Reusable scorer instances
"""

from typing import Dict, Optional


class CompositeScorer:
    """Unified scoring with configurable weighted components.

    Implements weighted sum: score = sum(weights[k] * components[k])
    All scores are clamped to [0.0, 1.0] range.

    Example:
        scorer = CompositeScorer({
            'feature1': 0.4,
            'feature2': 0.3,
            'feature3': 0.2,
            'feature4': 0.1
        })
        score = scorer.score({
            'feature1': 0.8,
            'feature2': 0.9,
            'feature3': 0.5,
            'feature4': 0.7
        })
        # Returns: min(1.0, max(0.0, 0.4*0.8 + 0.3*0.9 + 0.2*0.5 + 0.1*0.7))
    """

    def __init__(self, weights: Dict[str, float], normalize: bool = True):
        """Initialize scorer with component weights.

        Args:
            weights: Dict mapping component names to weights (should sum ~1.0)
            normalize: If True, normalize weights to sum to 1.0
        """
        self.weights = weights.copy()

        if normalize:
            total_weight = sum(weights.values())
            if total_weight > 0:
                self.weights = {k: v / total_weight for k, v in weights.items()}

    def score(self, components: Dict[str, float]) -> float:
        """Calculate composite score from components.

        Args:
            components: Dict mapping component names to scores [0.0, 1.0]

        Returns:
            Composite score clamped to [0.0, 1.0]
        """
        total = 0.0

        for key, weight in self.weights.items():
            if key in components:
                component_value = float(components[key])
                # Clamp component to [0, 1]
                component_value = max(0.0, min(1.0, component_value))
                total += weight * component_value

        # Clamp final score to [0, 1]
        return max(0.0, min(1.0, total))

    def debug_score(self, components: Dict[str, float]) -> Dict:
        """Calculate score and return detailed breakdown.

        Args:
            components: Dict mapping component names to scores [0.0, 1.0]

        Returns:
            Dict with:
                - 'score': final score
                - 'components': dict of {name: (weight, value, weighted_value)}
                - 'total': sum before clamping
        """
        breakdown = {}
        total = 0.0

        for key, weight in self.weights.items():
            if key in components:
                component_value = float(components[key])
                component_value = max(0.0, min(1.0, component_value))
                weighted_value = weight * component_value
                total += weighted_value
                breakdown[key] = {
                    "weight": weight,
                    "value": component_value,
                    "weighted": weighted_value,
                }

        return {
            "score": max(0.0, min(1.0, total)),
            "components": breakdown,
            "total_before_clamp": total,
        }


# Predefined scorers for common use cases

EFFICIENCY_SCORER = CompositeScorer(
    {
        "duration_variance": 0.4,
        "completion_rate": 0.3,
        "resource_utilization": 0.2,
        "quality_score": 0.1,
    }
)

MEMORY_QUALITY_SCORER = CompositeScorer(
    {"accuracy": 0.4, "completeness": 0.3, "recency": 0.2, "relevance": 0.1}
)

STRATEGY_EFFECTIVENESS_SCORER = CompositeScorer(
    {"success_rate": 0.4, "efficiency": 0.3, "learning_gain": 0.2, "adaptability": 0.1}
)

TASK_HEALTH_SCORER = CompositeScorer(
    {
        "progress": 0.5,
        "quality": 0.25,
        "blockers": -0.2,  # Negative weight for risk factors
        "error_rate": -0.05,  # Negative weight for error rate
    }
)

SALIENCY_SCORER = CompositeScorer({"novelty": 0.4, "surprise": 0.3, "contradiction": 0.3})

CONSOLIDATION_QUALITY_SCORER = CompositeScorer(
    {"compression_ratio": 0.25, "recall": 0.25, "consistency": 0.25, "information_density": 0.25}
)

# Negative-weight scorers (for risk/penalty calculation)
RISK_SCORER = CompositeScorer(
    {"complexity": 0.4, "uncertainty": 0.3, "dependencies": 0.2, "unknowns": 0.1}
)


def create_scorer(weights: Dict[str, float], name: Optional[str] = None) -> CompositeScorer:
    """Factory function to create named scorers.

    Args:
        weights: Dict mapping component names to weights
        name: Optional name for the scorer (for debugging)

    Returns:
        CompositeScorer instance
    """
    scorer = CompositeScorer(weights)
    if name:
        scorer._name = name
    return scorer
