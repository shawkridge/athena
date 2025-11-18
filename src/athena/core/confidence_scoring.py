"""Confidence scoring engine for memory retrieval results."""

import logging
from typing import Any, Dict, Optional

from .result_models import ConfidenceScores

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """Compute confidence scores for memory retrieval results."""

    def __init__(self, meta_store=None):
        """Initialize confidence scorer.

        Args:
            meta_store: Optional MetaMemoryStore for quality metrics
        """
        self.meta_store = meta_store

    def score(
        self,
        memory: Dict[str, Any],
        source_layer: str,
        semantic_score: Optional[float] = None,
    ) -> ConfidenceScores:
        """Compute confidence scores for a memory.

        Args:
            memory: Memory object to score
            source_layer: Layer the memory came from
            semantic_score: Optional semantic relevance score (0-1)

        Returns:
            ConfidenceScores object
        """
        # 1. Semantic relevance (from search score)
        semantic_relevance = semantic_score or 0.5

        # 2. Source quality (from meta-memory)
        source_quality = self._compute_source_quality(memory, source_layer)

        # 3. Recency (newer memories get higher scores)
        recency = self._compute_recency(memory)

        # 4. Consistency (how consistent with other memories)
        consistency = self._compute_consistency(memory)

        # 5. Completeness (how complete the information is)
        completeness = self._compute_completeness(memory)

        scores = ConfidenceScores(
            semantic_relevance=semantic_relevance,
            source_quality=source_quality,
            recency=recency,
            consistency=consistency,
            completeness=completeness,
        )

        logger.debug(
            f"Confidence scores - Semantic: {semantic_relevance:.2f}, "
            f"Quality: {source_quality:.2f}, Recency: {recency:.2f}, "
            f"Consistency: {consistency:.2f}, Completeness: {completeness:.2f}"
        )

        return scores

    def _compute_source_quality(self, memory: Dict[str, Any], source_layer: str) -> float:
        """Compute quality score based on source layer and meta-metrics.

        Args:
            memory: Memory object
            source_layer: Source layer name

        Returns:
            Quality score (0-1)
        """
        # Base quality by layer
        layer_quality = {
            "episodic": 0.85,  # Episodic is well-grounded in time
            "semantic": 0.80,  # Semantic is well-verified
            "procedural": 0.75,  # Procedural is learned from experience
            "graph": 0.70,  # Graph is synthesized
            "prospective": 0.65,  # Prospective is forward-looking
            "meta": 0.70,  # Meta is about meta-knowledge
        }

        base_quality = layer_quality.get(source_layer, 0.65)

        # Boost quality based on meta-memory metrics if available
        if self.meta_store:
            try:
                memory_id = memory.get("id") or memory.get("memory_id")
                if memory_id:
                    metrics = self.meta_store.get_quality_metrics(memory_id)
                    if metrics:
                        # Average with metrics
                        metrics_quality = metrics.get("quality_score", 0.7)
                        base_quality = (base_quality * 0.6) + (metrics_quality * 0.4)
            except Exception as e:
                logger.debug(f"Error getting quality metrics: {e}")

        return min(1.0, base_quality)

    @staticmethod
    def _compute_recency(memory: Dict[str, Any]) -> float:
        """Compute recency score (newer=higher).

        Args:
            memory: Memory object

        Returns:
            Recency score (0-1)
        """
        try:
            # Get timestamp
            timestamp = None
            for field in ["created_at", "timestamp", "date", "time"]:
                if field in memory and memory[field]:
                    timestamp = memory[field]
                    break

            if not timestamp:
                return 0.5  # Unknown age gets medium score

            # Parse timestamp if string
            if isinstance(timestamp, str):
                try:
                    from datetime import datetime

                    timestamp = datetime.fromisoformat(timestamp)
                except (ValueError, AttributeError):
                    return 0.5

            # Calculate age
            if isinstance(timestamp, datetime):
                age = datetime.now() - timestamp
            else:
                return 0.5

            # Score: exponential decay
            # 1 hour ago = 0.95, 1 day ago = 0.75, 7 days ago = 0.3, 30+ days = 0.0
            days_old = age.total_seconds() / (24 * 3600)

            if days_old < 0:
                return 1.0  # Future timestamp
            elif days_old < 1:
                return 0.95
            elif days_old < 7:
                return max(0.3, 0.95 - (days_old / 7) * 0.65)
            else:
                return max(0.0, 0.3 - (days_old - 7) / 30 * 0.3)

        except Exception as e:
            logger.debug(f"Error computing recency: {e}")
            return 0.5

    def _compute_consistency(self, memory: Dict[str, Any]) -> float:
        """Compute consistency with other memories.

        Args:
            memory: Memory object

        Returns:
            Consistency score (0-1)
        """
        try:
            # Check for consistency flags
            if memory.get("is_consistent"):
                return 0.9
            elif memory.get("has_conflicts"):
                return 0.4
            elif memory.get("is_speculative"):
                return 0.6

            # Default: assume consistent
            return 0.75

        except Exception as e:
            logger.debug(f"Error computing consistency: {e}")
            return 0.7

    @staticmethod
    def _compute_completeness(memory: Dict[str, Any]) -> float:
        """Compute completeness of memory.

        Args:
            memory: Memory object

        Returns:
            Completeness score (0-1)
        """
        try:
            # Check for required fields
            required_fields = ["content", "type"]
            present_fields = sum(
                1 for field in required_fields if field in memory and memory[field]
            )

            base_completeness = present_fields / len(required_fields) if required_fields else 0.5

            # Boost if has rich metadata
            metadata_fields = [
                "docstring",
                "source",
                "tags",
                "references",
                "context",
            ]
            metadata_count = sum(
                1 for field in metadata_fields if field in memory and memory[field]
            )

            metadata_boost = (metadata_count / len(metadata_fields)) * 0.2
            completeness = min(1.0, base_completeness + metadata_boost)

            return completeness

        except Exception as e:
            logger.debug(f"Error computing completeness: {e}")
            return 0.7

    @staticmethod
    def aggregate_confidence(
        scores: ConfidenceScores,
        weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """Aggregate multiple confidence factors into overall score.

        Args:
            scores: ConfidenceScores object
            weights: Optional weights for each factor

        Returns:
            Overall confidence score (0-1)
        """
        if weights is None:
            # Default weights
            weights = {
                "semantic_relevance": 0.35,
                "source_quality": 0.25,
                "recency": 0.15,
                "consistency": 0.15,
                "completeness": 0.10,
            }

        total_weight = sum(weights.values())
        weighted_sum = (
            scores.semantic_relevance * weights.get("semantic_relevance", 0.35)
            + scores.source_quality * weights.get("source_quality", 0.25)
            + scores.recency * weights.get("recency", 0.15)
            + scores.consistency * weights.get("consistency", 0.15)
            + scores.completeness * weights.get("completeness", 0.10)
        )

        overall = weighted_sum / total_weight if total_weight > 0 else 0.5
        return min(1.0, max(0.0, overall))


class ConfidenceFilter:
    """Filter results by confidence threshold."""

    @staticmethod
    def filter_by_confidence(
        results: list,
        min_confidence: float = 0.5,
        key: str = "confidence",
    ) -> list:
        """Filter results keeping only those meeting confidence threshold.

        Args:
            results: List of results (dicts with confidence field)
            min_confidence: Minimum confidence threshold
            key: Key name for confidence field

        Returns:
            Filtered results
        """
        return [r for r in results if r.get(key, 0) >= min_confidence]

    @staticmethod
    def rank_by_confidence(results: list, key: str = "confidence") -> list:
        """Sort results by confidence (descending).

        Args:
            results: List of results
            key: Key name for confidence field

        Returns:
            Sorted results
        """
        return sorted(results, key=lambda r: r.get(key, 0), reverse=True)

    @staticmethod
    def get_confidence_summary(results: list, key: str = "confidence") -> dict:
        """Get summary statistics of confidence scores.

        Args:
            results: List of results
            key: Key name for confidence field

        Returns:
            Dictionary with confidence statistics
        """
        if not results:
            return {
                "average": 0.0,
                "median": 0.0,
                "min": 0.0,
                "max": 0.0,
                "count": 0,
            }

        confidences = [r.get(key, 0) for r in results]
        confidences.sort()

        return {
            "average": sum(confidences) / len(confidences),
            "median": confidences[len(confidences) // 2],
            "min": min(confidences),
            "max": max(confidences),
            "count": len(confidences),
        }
