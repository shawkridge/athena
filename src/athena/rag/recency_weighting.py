"""
Recency-Weighted Retrieval

Addresses the "Lost in Middle" attention bias where LLMs focus on recent/early content
and ignore middle sections. This module implements recency-weighted retrieval that
balances semantic relevance with temporal recency.

Reference:
- Liu et al. (2024): "Lost in the Middle: How Language Models Use Long Contexts"
- Shows LLMs have U-shaped attention curve, forgetting middle content
"""

import math
import logging
from typing import List, Optional
from datetime import datetime

from ..semantic.search import MemorySearchResult
from ..core.models import Memory

logger = logging.getLogger(__name__)


class RecencyWeightingConfig:
    """Configuration for recency-weighted retrieval."""

    def __init__(
        self,
        recency_weight: float = 0.3,
        semantic_weight: float = 0.7,
        decay_rate: float = 1.0,  # Days for exponential decay
        normalize: bool = True,
    ):
        """Initialize recency weighting configuration.

        Args:
            recency_weight: How much to weight recency (0.0-1.0).
                           0.0 = pure semantic, 1.0 = pure recency
                           Recommended: 0.3 (70% semantic, 30% recency)
            semantic_weight: How much to weight semantic relevance.
                            Must sum with recency_weight to 1.0
            decay_rate: Half-life in days for exponential decay.
                       Higher = slower decay (memories stay relevant longer)
            normalize: Whether to normalize scores to 0-1 range
        """
        if not (0.0 <= recency_weight <= 1.0):
            raise ValueError(f"recency_weight must be 0.0-1.0, got {recency_weight}")

        self.recency_weight = recency_weight
        self.semantic_weight = 1.0 - recency_weight  # Ensure they sum to 1.0
        self.decay_rate = decay_rate
        self.normalize = normalize


class RecencyWeightedRetriever:
    """Retrieves memories balancing semantic relevance with recency."""

    def __init__(self, config: Optional[RecencyWeightingConfig] = None):
        """Initialize recency-weighted retriever.

        Args:
            config: Recency weighting configuration (uses defaults if None)
        """
        self.config = config or RecencyWeightingConfig()

    def calculate_recency_score(self, memory: Memory) -> float:
        """Calculate recency score (0-1) for a memory.

        Args:
            memory: Memory object with created_at timestamp

        Returns:
            Recency score between 0 (old) and 1 (very recent)
        """
        if not memory.created_at:
            # No timestamp -> treat as neutral
            return 0.5

        try:
            # Parse created_at if it's a string
            if isinstance(memory.created_at, str):
                created = datetime.fromisoformat(memory.created_at)
            else:
                created = memory.created_at

            # Calculate age in days
            age_days = (datetime.now() - created).total_seconds() / 86400

            # Exponential decay: e^(-age / decay_rate)
            # At decay_rate days, score = 0.368 (37% of original)
            recency_score = math.exp(-age_days / self.config.decay_rate)

            return max(0.0, min(1.0, recency_score))
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to calculate recency score: {e}")
            return 0.5

    def calculate_combined_score(self, memory: Memory, semantic_score: float) -> float:
        """Calculate combined score balancing semantic + recency.

        Args:
            memory: Memory object
            semantic_score: Semantic relevance score (0-1)

        Returns:
            Combined score (0-1) weighted by configuration
        """
        # Calculate recency component
        recency_score = self.calculate_recency_score(memory)

        # Combine: (semantic * semantic_weight) + (recency * recency_weight)
        combined = (
            semantic_score * self.config.semantic_weight
            + recency_score * self.config.recency_weight
        )

        return max(0.0, min(1.0, combined))

    def retrieve_with_recency(
        self,
        query: str,
        candidates: List[MemorySearchResult],
        k: int = 5,
    ) -> List[MemorySearchResult]:
        """Retrieve memories with recency weighting.

        Args:
            query: Search query (for logging)
            candidates: List of candidate memories from semantic search
            k: Number of top results to return

        Returns:
            List of top-k memories reranked by combined score
        """
        if not candidates:
            return []

        # Calculate combined scores
        scored_memories = []
        for result in candidates:
            # Extract semantic score from result
            semantic_score = getattr(result, "score", 0.5) or 0.5

            # Calculate combined score using the memory object
            combined_score = self.calculate_combined_score(result.memory, semantic_score)

            scored_memories.append(
                {
                    "result": result,
                    "semantic_score": semantic_score,
                    "recency_score": self.calculate_recency_score(result.memory),
                    "combined_score": combined_score,
                }
            )

        # Sort by combined score (descending)
        scored_memories.sort(key=lambda x: x["combined_score"], reverse=True)

        # Return top-k results
        return [item["result"] for item in scored_memories[:k]]

    def get_recency_explanation(self, memory: Memory, semantic_score: float) -> str:
        """Get human-readable explanation of recency weighting.

        Args:
            memory: Memory object
            semantic_score: Semantic relevance score

        Returns:
            Explanation string
        """
        recency_score = self.calculate_recency_score(memory)
        combined_score = self.calculate_combined_score(memory, semantic_score)

        return (
            f"Semantic: {semantic_score:.2f}, "
            f"Recency: {recency_score:.2f}, "
            f"Combined: {combined_score:.2f}"
        )


def apply_recency_weighting(
    results: List[MemorySearchResult],
    recency_weight: float = 0.3,
    k: int = 5,
) -> List[MemorySearchResult]:
    """Convenience function to apply recency weighting to search results.

    Args:
        results: List of search results from semantic search
        recency_weight: Weight for recency (0-1)
        k: Number of top results to return

    Returns:
        Reranked results with recency weighting applied
    """
    config = RecencyWeightingConfig(recency_weight=recency_weight)
    retriever = RecencyWeightedRetriever(config)
    return retriever.retrieve_with_recency("", results, k)
