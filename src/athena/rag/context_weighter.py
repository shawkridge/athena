"""Context importance weighting with multi-factor scoring.

This module provides sophisticated context importance weighting using multiple factors:
1. Semantic relevance to query
2. Temporal freshness
3. Source credibility
4. Connection density in knowledge graph
5. Procedural applicability
6. User interaction signals
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime
import math

logger = logging.getLogger(__name__)


class ContextType(Enum):
    """Types of context items."""

    DOCUMENT = "document"  # Text document
    CODE = "code"  # Code snippet
    EXAMPLE = "example"  # Usage example
    DEFINITION = "definition"  # Term definition
    RELATIONSHIP = "relationship"  # Graph relationship
    PROCEDURE = "procedure"  # Step-by-step procedure
    METADATA = "metadata"  # Metadata/annotation


@dataclass
class WeightingFactors:
    """Factors for context weighting."""

    semantic_weight: float = 0.35  # Relevance to query
    temporal_weight: float = 0.15  # Freshness/recency
    credibility_weight: float = 0.15  # Source credibility
    connectivity_weight: float = 0.15  # Graph connectivity
    applicability_weight: float = 0.10  # Procedural fit
    interaction_weight: float = 0.10  # User signals

    def validate(self) -> bool:
        """Validate weights sum to 1.0."""
        total = (
            self.semantic_weight
            + self.temporal_weight
            + self.credibility_weight
            + self.connectivity_weight
            + self.applicability_weight
            + self.interaction_weight
        )
        return abs(total - 1.0) < 0.01

    def normalize(self) -> None:
        """Normalize weights to sum to 1.0."""
        total = (
            self.semantic_weight
            + self.temporal_weight
            + self.credibility_weight
            + self.connectivity_weight
            + self.applicability_weight
            + self.interaction_weight
        )

        if total > 0:
            self.semantic_weight /= total
            self.temporal_weight /= total
            self.credibility_weight /= total
            self.connectivity_weight /= total
            self.applicability_weight /= total
            self.interaction_weight /= total


@dataclass
class ContextItem:
    """An item of context to be weighted."""

    id: str
    content: str
    context_type: ContextType
    semantic_score: float  # 0-1, relevance to query
    created_at: datetime
    updated_at: datetime
    source: str  # Where this came from
    credibility: float = 0.5  # 0-1, source credibility
    connection_count: int = 0  # Num of connections in graph
    view_count: int = 0  # User interactions
    metadata: Dict = field(default_factory=dict)


@dataclass
class WeightedContext:
    """Context item with calculated weight."""

    item: ContextItem
    overall_weight: float  # Combined weight (0-1)
    factor_scores: Dict[str, float]  # Individual factor scores
    ranking_position: int = 0  # Position in ranking


class TemporalWeighter:
    """Weights context by temporal freshness."""

    def __init__(self, half_life_days: float = 30.0):
        """Initialize temporal weighter.

        Args:
            half_life_days: Days for relevance to decay to 50%
        """
        self.half_life_days = half_life_days

    def weight(self, item: ContextItem, reference_time: Optional[datetime] = None) -> float:
        """Calculate temporal weight.

        Args:
            item: Context item
            reference_time: Reference time (uses now if None)

        Returns:
            Weight 0-1, higher = more recent
        """
        now = reference_time or datetime.now()

        # Prefer updated_at, fall back to created_at
        target_time = item.updated_at or item.created_at

        # Calculate age in days
        age_delta = now - target_time
        age_days = age_delta.total_seconds() / (24 * 3600)

        # Exponential decay: weight = 2^(-age/half_life)
        weight = 2.0 ** (-age_days / self.half_life_days)

        return max(0.0, min(1.0, weight))


class CredibilityWeighter:
    """Weights context by source credibility."""

    def __init__(self):
        """Initialize credibility weighter."""
        # Source credibility ratings
        self.source_ratings = {
            "official_docs": 0.95,
            "academic": 0.90,
            "user_content": 0.70,
            "community": 0.60,
            "ai_generated": 0.50,
            "web": 0.40,
        }

    def weight(self, item: ContextItem) -> float:
        """Calculate credibility weight.

        Args:
            item: Context item

        Returns:
            Weight 0-1, higher = more credible
        """
        # Use explicit credibility if set
        if item.credibility > 0:
            return item.credibility

        # Try to infer from source
        source_lower = item.source.lower()
        for source_pattern, rating in self.source_ratings.items():
            if source_pattern in source_lower:
                return rating

        # Default to neutral
        return 0.5

    def set_source_rating(self, source: str, rating: float) -> None:
        """Set credibility rating for source.

        Args:
            source: Source identifier
            rating: Credibility rating 0-1
        """
        self.source_ratings[source.lower()] = max(0.0, min(1.0, rating))


class ConnectivityWeighter:
    """Weights context by knowledge graph connectivity."""

    def __init__(self, max_connections: int = 100):
        """Initialize connectivity weighter.

        Args:
            max_connections: Maximum connections to consider
        """
        self.max_connections = max_connections

    def weight(self, item: ContextItem) -> float:
        """Calculate connectivity weight.

        Args:
            item: Context item

        Returns:
            Weight 0-1, higher = more connected
        """
        # Normalize connection count
        # Sigmoid function: smooth transition
        normalized = item.connection_count / self.max_connections

        # Apply sigmoid: 1 / (1 + e^(-x))
        # Shifted to give 0.5 at max_connections/2
        x = (normalized - 0.5) * 6  # Steepness factor

        weight = 1.0 / (1.0 + math.exp(-x))

        return max(0.0, min(1.0, weight))


class ApplicabilityWeighter:
    """Weights context by procedural applicability."""

    def __init__(self):
        """Initialize applicability weighter."""
        pass

    def weight(self, item: ContextItem, context_type_query: Optional[ContextType] = None) -> float:
        """Calculate applicability weight.

        Args:
            item: Context item
            context_type_query: Required context type (None = all applicable)

        Returns:
            Weight 0-1, higher = more applicable
        """
        # Base score by type
        type_applicability = {
            ContextType.PROCEDURE: 0.9,  # Highly applicable
            ContextType.EXAMPLE: 0.8,
            ContextType.CODE: 0.7,
            ContextType.DOCUMENT: 0.6,
            ContextType.DEFINITION: 0.5,
            ContextType.RELATIONSHIP: 0.4,
            ContextType.METADATA: 0.3,
        }

        base_score = type_applicability.get(item.context_type, 0.5)

        # Adjust if specific type required
        if context_type_query is not None:
            if item.context_type == context_type_query:
                base_score = 0.95  # Perfect match
            elif item.context_type == ContextType.METADATA:
                base_score = 0.2  # Metadata is less useful

        return base_score

    def set_type_applicability(self, context_type: ContextType, score: float) -> None:
        """Set applicability score for context type.

        Args:
            context_type: Context type
            score: Applicability score 0-1
        """
        # Would store in dict if made persistent
        pass


class InteractionWeighter:
    """Weights context by user interaction signals."""

    def __init__(self, view_weight: float = 0.5, half_life_days: float = 90):
        """Initialize interaction weighter.

        Args:
            view_weight: Weight for view count
            half_life_days: Days for interaction recency to decay
        """
        self.view_weight = view_weight
        self.half_life_days = half_life_days

    def weight(self, item: ContextItem, reference_time: Optional[datetime] = None) -> float:
        """Calculate interaction weight.

        Args:
            item: Context item
            reference_time: Reference time for recency

        Returns:
            Weight 0-1, higher = more interacted
        """
        # View count factor
        normalized_views = min(1.0, item.view_count / 100)  # 100 views = max
        view_factor = normalized_views * self.view_weight

        # Recency factor
        now = reference_time or datetime.now()
        age_days = (now - item.updated_at).total_seconds() / (24 * 3600)
        recency_factor = 2.0 ** (-age_days / self.half_life_days)
        recency_factor = recency_factor * (1.0 - self.view_weight)

        return max(0.0, min(1.0, view_factor + recency_factor))


class ContextWeighter:
    """Comprehensive context weighting system."""

    def __init__(self, factors: Optional[WeightingFactors] = None):
        """Initialize context weighter.

        Args:
            factors: Weighting factors (uses defaults if None)
        """
        self.factors = factors or WeightingFactors()
        self.factors.normalize()

        # Initialize sub-weighters
        self.temporal_weighter = TemporalWeighter()
        self.credibility_weighter = CredibilityWeighter()
        self.connectivity_weighter = ConnectivityWeighter()
        self.applicability_weighter = ApplicabilityWeighter()
        self.interaction_weighter = InteractionWeighter()

    def weight(
        self,
        item: ContextItem,
        reference_time: Optional[datetime] = None,
        required_type: Optional[ContextType] = None,
    ) -> WeightedContext:
        """Calculate comprehensive weight for context item.

        Args:
            item: Context item
            reference_time: Reference time for temporal weighting
            required_type: Required context type

        Returns:
            WeightedContext with scores
        """
        # Calculate individual factor scores
        semantic_score = item.semantic_score
        temporal_score = self.temporal_weighter.weight(item, reference_time)
        credibility_score = self.credibility_weighter.weight(item)
        connectivity_score = self.connectivity_weighter.weight(item)
        applicability_score = self.applicability_weighter.weight(item, required_type)
        interaction_score = self.interaction_weighter.weight(item, reference_time)

        # Combine with weights
        overall_weight = (
            self.factors.semantic_weight * semantic_score
            + self.factors.temporal_weight * temporal_score
            + self.factors.credibility_weight * credibility_score
            + self.factors.connectivity_weight * connectivity_score
            + self.factors.applicability_weight * applicability_score
            + self.factors.interaction_weight * interaction_score
        )

        # Ensure within bounds
        overall_weight = max(0.0, min(1.0, overall_weight))

        factor_scores = {
            "semantic": semantic_score,
            "temporal": temporal_score,
            "credibility": credibility_score,
            "connectivity": connectivity_score,
            "applicability": applicability_score,
            "interaction": interaction_score,
            "overall": overall_weight,
        }

        return WeightedContext(
            item=item,
            overall_weight=overall_weight,
            factor_scores=factor_scores,
        )

    def weight_batch(
        self,
        items: List[ContextItem],
        reference_time: Optional[datetime] = None,
        required_type: Optional[ContextType] = None,
        sort: bool = True,
    ) -> List[WeightedContext]:
        """Weight multiple items.

        Args:
            items: Context items
            reference_time: Reference time for temporal weighting
            required_type: Required context type
            sort: Whether to sort by weight (descending)

        Returns:
            Weighted context items
        """
        weighted = []
        for item in items:
            weighted_item = self.weight(item, reference_time, required_type)
            weighted.append(weighted_item)

        # Sort by weight if requested
        if sort:
            weighted.sort(key=lambda w: w.overall_weight, reverse=True)

            # Set ranking positions
            for i, w in enumerate(weighted):
                w.ranking_position = i + 1

        return weighted

    def top_k(
        self,
        items: List[ContextItem],
        k: int = 10,
        reference_time: Optional[datetime] = None,
        required_type: Optional[ContextType] = None,
    ) -> List[WeightedContext]:
        """Get top-k weighted items.

        Args:
            items: Context items
            k: Number of items to return
            reference_time: Reference time for temporal weighting
            required_type: Required context type

        Returns:
            Top-k weighted items
        """
        weighted = self.weight_batch(items, reference_time, required_type, sort=True)
        return weighted[:k]

    def set_weights(self, **kwargs) -> None:
        """Set individual weighting factors.

        Args:
            **kwargs: Factor names and values (e.g., semantic_weight=0.4)
        """
        for key, value in kwargs.items():
            if hasattr(self.factors, key):
                setattr(self.factors, key, max(0.0, min(1.0, value)))

        self.factors.normalize()

    def get_weights(self) -> Dict[str, float]:
        """Get current weighting factors.

        Returns:
            Dictionary of factor names and weights
        """
        return {
            "semantic": self.factors.semantic_weight,
            "temporal": self.factors.temporal_weight,
            "credibility": self.factors.credibility_weight,
            "connectivity": self.factors.connectivity_weight,
            "applicability": self.factors.applicability_weight,
            "interaction": self.factors.interaction_weight,
        }

    def explain_weight(self, weighted_item: WeightedContext) -> str:
        """Generate human-readable explanation of weighting.

        Args:
            weighted_item: Weighted context item

        Returns:
            Explanation string
        """
        item = weighted_item.item
        scores = weighted_item.factor_scores

        lines = [
            f"Context Item: {item.id}",
            f"Type: {item.context_type.value}",
            f"Overall Weight: {weighted_item.overall_weight:.2%}",
            "",
            "Factor Contributions:",
        ]

        # Show each factor and its contribution
        factors = [
            ("Semantic Relevance", "semantic", self.factors.semantic_weight),
            ("Temporal Freshness", "temporal", self.factors.temporal_weight),
            ("Source Credibility", "credibility", self.factors.credibility_weight),
            ("Graph Connectivity", "connectivity", self.factors.connectivity_weight),
            ("Procedural Fit", "applicability", self.factors.applicability_weight),
            ("User Interactions", "interaction", self.factors.interaction_weight),
        ]

        for label, factor_key, weight in factors:
            score = scores.get(factor_key, 0.0)
            contribution = score * weight
            lines.append(f"  {label:25} {score:.2f} × {weight:.2f} = {contribution:.2f}")

        return "\n".join(lines)
