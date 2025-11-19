"""Consciousness metrics - Main interface for consciousness measurement and scoring.

Provides:
- Real-time consciousness indicator measurements
- Overall consciousness score calculation
- Historical tracking and trending
- Integration with dashboard API
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import logging
import json

from .indicators import ConsciousnessIndicators, IndicatorScore

logger = logging.getLogger(__name__)


@dataclass
class ConsciousnessScore:
    """Complete consciousness measurement snapshot."""

    timestamp: datetime = field(default_factory=datetime.now)
    overall_score: float = 0.0  # Average of 6 indicators (0-10)
    indicators: Dict[str, IndicatorScore] = field(default_factory=dict)  # All 6 indicators
    trend: str = "stable"  # "increasing", "decreasing", "stable"
    confidence: float = 0.65  # Overall confidence (0-1)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "overall_score": round(self.overall_score, 2),
            "indicators": {
                name: {
                    "score": round(score.score, 2),
                    "components": {k: round(v, 2) for k, v in score.components.items()},
                    "confidence": round(score.confidence, 2),
                    "evidence": score.evidence,
                }
                for name, score in self.indicators.items()
            },
            "trend": self.trend,
            "confidence": round(self.confidence, 2),
        }


class ConsciousnessMetrics:
    """Main consciousness metrics system.

    Measures, tracks, and exposes consciousness indicators through a unified interface.
    Integrates all 6 consciousness indicators and provides real-time scoring.
    """

    def __init__(
        self,
        working_memory_manager=None,
        graph_store=None,
        attention_module=None,
        meta_store=None,
        episodic_store=None,
        temporal_system=None,
        consolidation_system=None,
        manager=None,
        history_limit: int = 100,
    ):
        """Initialize consciousness metrics system.

        Args:
            working_memory_manager: Working memory system
            graph_store: Knowledge graph store
            attention_module: Attention system
            meta_store: Meta-memory store
            episodic_store: Episodic memory store
            temporal_system: Temporal system
            consolidation_system: Consolidation system
            manager: Unified memory manager
            history_limit: How many measurements to keep in history
        """
        self.indicators = ConsciousnessIndicators(
            working_memory_manager=working_memory_manager,
            graph_store=graph_store,
            attention_module=attention_module,
            meta_store=meta_store,
            episodic_store=episodic_store,
            temporal_system=temporal_system,
            consolidation_system=consolidation_system,
            manager=manager,
        )

        self.history: List[ConsciousnessScore] = []
        self.history_limit = history_limit
        self.last_score: Optional[ConsciousnessScore] = None

    async def measure_consciousness(self) -> ConsciousnessScore:
        """Measure current consciousness state.

        Returns:
            Complete consciousness score with all indicators
        """
        # Measure all indicators
        indicator_results = await self.indicators.measure_all()

        # Calculate overall score (average)
        scores = [result.score for result in indicator_results.values()]
        overall = sum(scores) / len(scores) if scores else 0.0

        # Calculate confidence (average of all indicator confidences)
        confidences = [result.confidence for result in indicator_results.values()]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5

        # Determine trend
        trend = self._calculate_trend(overall)

        # Create score object
        score = ConsciousnessScore(
            timestamp=datetime.now(),
            overall_score=overall,
            indicators=indicator_results,
            trend=trend,
            confidence=avg_confidence,
        )

        # Store in history
        self._add_to_history(score)
        self.last_score = score

        return score

    def _calculate_trend(self, current_score: float) -> str:
        """Calculate trend based on recent history.

        Args:
            current_score: Current consciousness score

        Returns:
            "increasing", "decreasing", or "stable"
        """
        if len(self.history) < 2:
            return "stable"

        # Get last score
        last = self.history[-1].overall_score if self.history else current_score

        # Define thresholds
        change_threshold = 0.5  # Must change by 0.5+ to be notable

        if current_score - last > change_threshold:
            return "increasing"
        elif last - current_score > change_threshold:
            return "decreasing"
        else:
            return "stable"

    def _add_to_history(self, score: ConsciousnessScore) -> None:
        """Add score to history with size limit.

        Args:
            score: Consciousness score to add
        """
        self.history.append(score)

        # Trim history if too large
        if len(self.history) > self.history_limit:
            self.history = self.history[-self.history_limit :]

    def get_history(self, limit: Optional[int] = None) -> List[ConsciousnessScore]:
        """Get historical consciousness measurements.

        Args:
            limit: Maximum number of recent scores to return

        Returns:
            List of consciousness scores
        """
        if limit is None:
            return self.history.copy()
        return self.history[-limit:].copy()

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about consciousness measurements.

        Returns:
            Dictionary with average, min, max, trend data
        """
        if not self.history:
            return {
                "measurements": 0,
                "average_score": 0.0,
                "min_score": 0.0,
                "max_score": 0.0,
                "current_score": 0.0,
                "trend": "stable",
            }

        scores = [s.overall_score for s in self.history]
        return {
            "measurements": len(self.history),
            "average_score": round(sum(scores) / len(scores), 2),
            "min_score": round(min(scores), 2),
            "max_score": round(max(scores), 2),
            "current_score": round(self.last_score.overall_score, 2) if self.last_score else 0.0,
            "trend": self.last_score.trend if self.last_score else "stable",
            "first_measurement": self.history[0].timestamp.isoformat(),
            "last_measurement": self.history[-1].timestamp.isoformat(),
        }

    def compare_indicators(self, window_size: int = 10) -> Dict[str, Any]:
        """Compare indicators over a time window.

        Args:
            window_size: Number of recent measurements to include

        Returns:
            Dictionary with indicator comparison data
        """
        recent = self.history[-window_size:] if self.history else []

        if not recent:
            return {"measurements": 0, "indicators": {}}

        # Aggregate by indicator
        indicator_data = {}
        for indicator_name in recent[0].indicators.keys():
            scores = [s.indicators[indicator_name].score for s in recent]
            indicator_data[indicator_name] = {
                "average": round(sum(scores) / len(scores), 2),
                "min": round(min(scores), 2),
                "max": round(max(scores), 2),
                "current": round(scores[-1], 2),
            }

        return {
            "window_size": len(recent),
            "indicators": indicator_data,
            "period": {
                "start": recent[0].timestamp.isoformat(),
                "end": recent[-1].timestamp.isoformat(),
            },
        }

    def reset_history(self) -> None:
        """Clear measurement history."""
        self.history = []
        self.last_score = None

    def as_dict(self) -> Dict[str, Any]:
        """Get current state as dictionary for API responses.

        Returns:
            Dictionary representation of metrics
        """
        if not self.last_score:
            return {
                "status": "not_measured",
                "message": "No consciousness measurements yet",
            }

        return self.last_score.to_dict()

    def __repr__(self) -> str:
        """String representation."""
        if not self.last_score:
            return "ConsciousnessMetrics(not_measured)"
        return (
            f"ConsciousnessMetrics("
            f"score={self.last_score.overall_score:.2f}, "
            f"trend={self.last_score.trend}, "
            f"measurements={len(self.history)})"
        )
