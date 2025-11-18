"""Uncertainty calibration and abstention logic for RAG systems.

Addresses research gap: "Getting LLMs to recognize when they lack sufficient context to answer"
(Rank 16, Credibility 1.0 from 2024-2025 LLM Memory Research)

Provides:
- Confidence scoring for RAG results
- Abstention triggers (when to refuse to answer)
- Uncertainty metrics tracking
- Context sufficiency validation
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ..core.models import MemorySearchResult

logger = logging.getLogger(__name__)


class ConfidenceLevel(str, Enum):
    """Confidence levels for RAG results."""

    HIGH = "high"  # ≥ 0.8: Answer with confidence
    MEDIUM = "medium"  # 0.6-0.8: Answer with caveats
    LOW = "low"  # 0.4-0.6: Answer with significant uncertainty
    ABSTAIN = "abstain"  # < 0.4: Refuse to answer (insufficient context)


class AbstentionReason(str, Enum):
    """Reasons for refusing to answer."""

    INSUFFICIENT_CONTEXT = "insufficient_context"
    LOW_RELEVANCE = "low_relevance"
    CONFLICTING_RESULTS = "conflicting_results"
    OUT_OF_DOMAIN = "out_of_domain"
    QUERY_AMBIGUITY = "query_ambiguity"


@dataclass
class UncertaintyMetrics:
    """Metrics for uncertainty in RAG results."""

    confidence_score: float  # 0.0-1.0
    confidence_level: ConfidenceLevel
    should_abstain: bool
    abstention_reason: Optional[AbstentionReason] = None

    # Component scores (contributing to overall confidence)
    relevance_score: float = 0.0  # How relevant are results to query
    coverage_score: float = 0.0  # How comprehensively covered is the topic
    consistency_score: float = 0.0  # How consistent are the results
    recency_score: float = 0.0  # How up-to-date is the information

    # Context quality
    context_quality: float = 0.0  # 0.0-1.0 overall context quality
    min_result_similarity: float = 0.0  # Minimum similarity in result set
    max_result_similarity: float = 1.0  # Maximum similarity in result set
    result_count: int = 0  # Number of results retrieved

    # Additional context
    explanation: str = ""  # Why this confidence level


@dataclass
class UncertaintyConfig:
    """Configuration for uncertainty calibration."""

    # Confidence thresholds
    high_confidence_threshold: float = 0.8
    medium_confidence_threshold: float = 0.6
    low_confidence_threshold: float = 0.4
    abstention_threshold: float = 0.4

    # Component weights (sum to 1.0)
    relevance_weight: float = 0.4
    coverage_weight: float = 0.3
    consistency_weight: float = 0.2
    recency_weight: float = 0.1

    # Context sufficiency requirements
    min_result_count: int = 3  # Require at least N results
    min_avg_similarity: float = 0.6  # Require average similarity ≥ threshold
    min_coverage_for_confidence: float = 0.7  # For high confidence, need broad coverage

    # Consistency checking
    check_consistency: bool = True
    consistency_threshold: float = 0.7  # Min consistency to be confident

    # Out-of-domain detection
    check_out_of_domain: bool = True
    ood_threshold: float = 0.3  # If max similarity < this, likely out-of-domain

    def __post_init__(self):
        """Validate configuration."""
        weights_sum = (
            self.relevance_weight
            + self.coverage_weight
            + self.consistency_weight
            + self.recency_weight
        )
        if not (0.99 <= weights_sum <= 1.01):
            raise ValueError(f"Component weights must sum to 1.0, got {weights_sum}")


class UncertaintyCalibrator:
    """Calibrates confidence in RAG results and triggers abstention when appropriate."""

    def __init__(self, config: Optional[UncertaintyConfig] = None):
        """Initialize uncertainty calibrator.

        Args:
            config: Configuration (uses defaults if None)
        """
        self.config = config or UncertaintyConfig()

    def calibrate(
        self,
        results: list[MemorySearchResult],
        query: str,
        query_embedding: Optional[list[float]] = None,
    ) -> UncertaintyMetrics:
        """Calibrate confidence in RAG results.

        Args:
            results: Search results from RAG
            query: Original query string
            query_embedding: Query embedding (for additional analysis)

        Returns:
            UncertaintyMetrics with confidence score and abstention decision

        Examples:
            >>> calibrator = UncertaintyCalibrator()
            >>> metrics = calibrator.calibrate(results, "How do I authenticate users?")
            >>> if metrics.should_abstain:
            ...     return "I don't have sufficient information to answer this."
            >>> else:
            ...     return f"Answer: ... (confidence: {metrics.confidence_level})"
        """
        # Compute component scores
        relevance_score = self._compute_relevance(results)
        coverage_score = self._compute_coverage(results, len(query.split()))
        consistency_score = (
            self._compute_consistency(results) if self.config.check_consistency else 1.0
        )
        recency_score = self._compute_recency(results)

        # Weighted combination
        confidence_score = (
            self.config.relevance_weight * relevance_score
            + self.config.coverage_weight * coverage_score
            + self.config.consistency_weight * consistency_score
            + self.config.recency_weight * recency_score
        )

        # Determine confidence level
        if confidence_score >= self.config.high_confidence_threshold:
            confidence_level = ConfidenceLevel.HIGH
        elif confidence_score >= self.config.medium_confidence_threshold:
            confidence_level = ConfidenceLevel.MEDIUM
        elif confidence_score >= self.config.low_confidence_threshold:
            confidence_level = ConfidenceLevel.LOW
        else:
            confidence_level = ConfidenceLevel.ABSTAIN

        # Determine abstention and reason
        should_abstain, abstention_reason = self._determine_abstention(
            results, confidence_score, relevance_score, consistency_score
        )

        # Build explanation
        explanation = self._build_explanation(
            confidence_score,
            confidence_level,
            should_abstain,
            abstention_reason,
            relevance_score,
            coverage_score,
            consistency_score,
        )

        # Compute min/max similarity
        similarities = [r.similarity for r in results] if results else [0.0]
        min_sim = min(similarities) if similarities else 0.0
        max_sim = max(similarities) if similarities else 0.0

        return UncertaintyMetrics(
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            should_abstain=should_abstain,
            abstention_reason=abstention_reason,
            relevance_score=relevance_score,
            coverage_score=coverage_score,
            consistency_score=consistency_score,
            recency_score=recency_score,
            context_quality=confidence_score,  # Use overall confidence as context quality
            min_result_similarity=min_sim,
            max_result_similarity=max_sim,
            result_count=len(results),
            explanation=explanation,
        )

    def _compute_relevance(self, results: list[MemorySearchResult]) -> float:
        """Compute relevance score based on result similarities.

        Args:
            results: Search results

        Returns:
            Relevance score (0.0-1.0)
        """
        if not results:
            return 0.0

        # Check minimum result count
        if len(results) < self.config.min_result_count:
            penalty = (1.0 - (len(results) / self.config.min_result_count)) * 0.3  # 30% penalty
        else:
            penalty = 0.0

        # Average similarity of top results
        similarities = [r.similarity for r in results[: self.config.min_result_count]]
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0

        # Apply minimum similarity threshold
        if avg_similarity < self.config.min_avg_similarity:
            avg_similarity = max(0, avg_similarity - 0.2)  # Penalize low similarity

        return max(0.0, avg_similarity - penalty)

    def _compute_coverage(self, results: list[MemorySearchResult], query_length: int) -> float:
        """Compute coverage score (how comprehensive the results are).

        Args:
            results: Search results
            query_length: Number of words in query

        Returns:
            Coverage score (0.0-1.0)
        """
        if not results:
            return 0.0

        # Simple heuristic: more results + more diverse content = better coverage
        result_count_score = min(len(results) / 5.0, 1.0)  # 5+ results = good coverage

        # Diversity check: are results from different sources/types?
        unique_event_types = len(set(getattr(r, "event_type", "unknown") for r in results))
        diversity_score = min(unique_event_types / 3.0, 1.0)  # 3+ types = good diversity

        # Combined coverage score
        return result_count_score * 0.6 + diversity_score * 0.4

    def _compute_consistency(self, results: list[MemorySearchResult]) -> float:
        """Compute consistency score (agreement between results).

        Args:
            results: Search results

        Returns:
            Consistency score (0.0-1.0)
        """
        if len(results) < 2:
            return 1.0  # Can't assess consistency with <2 results

        # Consistency: results with similar content should have similar meanings
        # Approximate by checking if top results are semantically similar
        similarities = [r.similarity for r in results]

        # Good consistency if top results are close in similarity
        # Bad consistency if they vary wildly
        if len(similarities) > 1:
            variance = sum(
                (s - sum(similarities) / len(similarities)) ** 2 for s in similarities
            ) / len(similarities)
            # Lower variance = higher consistency
            # Normalize: variance of 0-0.5 maps to 1.0-0.0
            consistency = max(0.0, 1.0 - (variance * 2))
        else:
            consistency = 1.0

        return consistency

    def _compute_recency(self, results: list[MemorySearchResult]) -> float:
        """Compute recency score (how recent the information is).

        Args:
            results: Search results

        Returns:
            Recency score (0.0-1.0)
        """
        # Simple approach: assume all results are reasonably recent
        # In a real implementation, would check timestamps
        # For now, return 1.0 (assume consolidation keeps things fresh)
        return 1.0

    def _determine_abstention(
        self,
        results: list[MemorySearchResult],
        confidence_score: float,
        relevance_score: float,
        consistency_score: float,
    ) -> tuple[bool, Optional[AbstentionReason]]:
        """Determine if we should abstain from answering.

        Args:
            results: Search results
            confidence_score: Overall confidence score
            relevance_score: Relevance component score
            consistency_score: Consistency component score

        Returns:
            (should_abstain, reason) tuple
        """
        # Rule 1: Insufficient results
        if len(results) < self.config.min_result_count:
            return True, AbstentionReason.INSUFFICIENT_CONTEXT

        # Rule 2: Low relevance
        if relevance_score < self.config.low_confidence_threshold:
            return True, AbstentionReason.LOW_RELEVANCE

        # Rule 3: Poor consistency (conflicting information)
        if consistency_score < self.config.consistency_threshold:
            return True, AbstentionReason.CONFLICTING_RESULTS

        # Rule 4: Out of domain (all results have very low similarity)
        if (
            self.config.check_out_of_domain
            and results
            and max(r.similarity for r in results) < self.config.ood_threshold
        ):
            return True, AbstentionReason.OUT_OF_DOMAIN

        # Rule 5: Below abstention threshold
        if confidence_score < self.config.abstention_threshold:
            return True, AbstentionReason.INSUFFICIENT_CONTEXT

        return False, None

    def _build_explanation(
        self,
        confidence_score: float,
        confidence_level: ConfidenceLevel,
        should_abstain: bool,
        abstention_reason: Optional[AbstentionReason],
        relevance_score: float,
        coverage_score: float,
        consistency_score: float,
    ) -> str:
        """Build human-readable explanation of confidence.

        Args:
            confidence_score: Overall confidence (0.0-1.0)
            confidence_level: ConfidenceLevel enum value
            should_abstain: Whether to abstain
            abstention_reason: Reason for abstention
            relevance_score: Relevance component
            coverage_score: Coverage component
            consistency_score: Consistency component

        Returns:
            Human-readable explanation
        """
        if should_abstain:
            reason_text = (
                abstention_reason.value.replace("_", " ").title()
                if abstention_reason
                else "Unknown"
            )
            return (
                f"Abstaining: {reason_text}. "
                f"Confidence: {confidence_score:.2f} (below {self.config.abstention_threshold})"
            )

        confidence_pct = int(confidence_score * 100)
        details = (
            f"Relevance: {relevance_score:.2f}, "
            f"Coverage: {coverage_score:.2f}, "
            f"Consistency: {consistency_score:.2f}"
        )

        if confidence_level == ConfidenceLevel.HIGH:
            return f"High confidence ({confidence_pct}%). {details}"
        elif confidence_level == ConfidenceLevel.MEDIUM:
            return f"Medium confidence ({confidence_pct}%). Answer with some caveats. {details}"
        elif confidence_level == ConfidenceLevel.LOW:
            return f"Low confidence ({confidence_pct}%). Answer with significant uncertainty. {details}"
        else:
            return f"Unclear confidence ({confidence_pct}%). {details}"

    def compute_context_sufficiency(
        self,
        results: list[MemorySearchResult],
        required_confidence: float = 0.75,
    ) -> dict:
        """Compute context sufficiency metrics.

        Args:
            results: Search results
            required_confidence: Minimum confidence needed (0.0-1.0)

        Returns:
            Dictionary with sufficiency metrics
        """
        metrics = self.calibrate(results, "")
        is_sufficient = metrics.confidence_score >= required_confidence

        return {
            "is_sufficient": is_sufficient,
            "confidence_score": metrics.confidence_score,
            "required_confidence": required_confidence,
            "gap": max(0, required_confidence - metrics.confidence_score),
            "metrics": metrics,
        }
