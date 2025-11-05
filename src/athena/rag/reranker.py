"""LLM-based semantic reranking for improved retrieval quality."""

import logging
from typing import Optional

from ..core.models import MemorySearchResult
from .llm_client import LLMClient

logger = logging.getLogger(__name__)


class LLMReranker:
    """Two-stage reranking with LLM semantic scoring.

    Stage 1: Fast vector search (k*10 candidates)
    Stage 2: LLM scores semantic relevance (return top k)
    """

    def __init__(self, llm_client: LLMClient):
        """Initialize LLM reranker.

        Args:
            llm_client: LLM client for relevance scoring
        """
        self.llm = llm_client

    def rerank(
        self,
        query: str,
        candidates: list[MemorySearchResult],
        k: int = 5,
        llm_weight: float = 0.7,
        vector_weight: float = 0.3,
    ) -> list[MemorySearchResult]:
        """Rerank candidates using LLM semantic relevance.

        Args:
            query: User query
            candidates: Initial search results from vector search
            k: Number of results to return
            llm_weight: Weight for LLM score (0-1, default 0.7)
            vector_weight: Weight for vector similarity (0-1, default 0.3)

        Returns:
            Reranked top-k results with updated similarity scores

        Examples:
            >>> reranker = LLMReranker(llm_client)
            >>> candidates = search.recall("auth", project_id=1, k=30)
            >>> reranked = reranker.rerank("How is authentication handled?", candidates, k=5)
            >>> # reranked[0] has highest LLM relevance score
        """
        if not candidates:
            return []

        # Validate weights
        if not (0 <= llm_weight <= 1 and 0 <= vector_weight <= 1):
            raise ValueError("Weights must be between 0 and 1")

        if abs((llm_weight + vector_weight) - 1.0) > 0.01:
            logger.warning(
                f"Weights don't sum to 1.0 (llm={llm_weight}, vector={vector_weight}). "
                "Normalizing..."
            )
            total = llm_weight + vector_weight
            llm_weight = llm_weight / total
            vector_weight = vector_weight / total

        logger.info(f"Reranking {len(candidates)} candidates (weights: LLM={llm_weight:.2f}, vector={vector_weight:.2f})")

        # Score each candidate with LLM
        reranked = []
        for i, result in enumerate(candidates):
            try:
                # Get LLM relevance score
                llm_score = self.llm.score_relevance(
                    query=query, document=result.memory.content
                )

                # Combine with vector similarity
                final_score = (
                    llm_weight * llm_score + vector_weight * result.similarity
                )

                # Store scores for debugging
                reranked.append((result, final_score, llm_score))

                if (i + 1) % 10 == 0:
                    logger.debug(f"Scored {i + 1}/{len(candidates)} candidates")

            except Exception as e:
                logger.error(f"Failed to score candidate {i}: {e}")
                # Use vector similarity only as fallback
                reranked.append((result, result.similarity, None))

        # Sort by final score (descending)
        reranked.sort(key=lambda x: x[1], reverse=True)

        # Update ranks and create final results
        final_results = []
        for rank, (result, final_score, llm_score) in enumerate(reranked[:k], 1):
            # Update rank
            result.rank = rank

            # Store reranking metadata
            if not hasattr(result, "metadata") or result.metadata is None:
                result.metadata = {}

            result.metadata.update({
                "reranking_applied": True,
                "llm_score": llm_score,
                "vector_similarity": result.similarity,
                "final_score": final_score,
                "llm_weight": llm_weight,
                "vector_weight": vector_weight,
            })

            # Update similarity to final score for consistency
            result.similarity = final_score

            final_results.append(result)

        logger.info(f"Reranked to top {len(final_results)} results")
        return final_results

    def rerank_batch(
        self,
        queries: list[str],
        candidates_list: list[list[MemorySearchResult]],
        k: int = 5,
        **kwargs,
    ) -> list[list[MemorySearchResult]]:
        """Rerank multiple queries in batch.

        Args:
            queries: List of user queries
            candidates_list: List of candidate lists (one per query)
            k: Number of results per query
            **kwargs: Additional arguments passed to rerank()

        Returns:
            List of reranked results (one list per query)

        Note:
            Currently processes sequentially. Could be parallelized
            in the future for better performance.
        """
        if len(queries) != len(candidates_list):
            raise ValueError("Number of queries must match number of candidate lists")

        results = []
        for i, (query, candidates) in enumerate(zip(queries, candidates_list)):
            logger.debug(f"Reranking batch {i+1}/{len(queries)}")
            reranked = self.rerank(query, candidates, k=k, **kwargs)
            results.append(reranked)

        return results


class RerankerConfig:
    """Configuration for LLM reranking."""

    # Enable/disable reranking
    enabled: bool = True

    # Scoring weights
    llm_weight: float = 0.7  # Weight for LLM semantic score
    vector_weight: float = 0.3  # Weight for vector similarity

    # Candidate selection
    candidate_multiplier: int = 6  # Get k*6 candidates for reranking (e.g., 5*6=30)
    min_similarity: float = 0.2  # Minimum vector similarity for candidates

    # Performance
    batch_size: Optional[int] = None  # Future: parallel processing batch size

    def __init__(self, **kwargs):
        """Initialize config with overrides.

        Args:
            **kwargs: Config options to override

        Examples:
            >>> config = RerankerConfig(llm_weight=0.8, vector_weight=0.2)
            >>> config = RerankerConfig(candidate_multiplier=10)
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                logger.warning(f"Unknown reranker config option: {key}")

        # Validate weights
        if abs((self.llm_weight + self.vector_weight) - 1.0) > 0.01:
            logger.warning(
                f"Weights don't sum to 1.0: llm={self.llm_weight}, vector={self.vector_weight}"
            )


def analyze_reranking_impact(
    original_results: list[MemorySearchResult],
    reranked_results: list[MemorySearchResult],
) -> dict:
    """Analyze the impact of reranking on result ordering.

    Args:
        original_results: Results before reranking
        reranked_results: Results after reranking

    Returns:
        Dict with metrics: rank_changes, top_3_overlap, score_improvements

    Examples:
        >>> impact = analyze_reranking_impact(original, reranked)
        >>> print(f"Top-3 overlap: {impact['top_3_overlap']:.0%}")
        >>> print(f"Avg rank change: {impact['avg_rank_change']:.1f}")
    """
    # Create ID to rank mappings
    original_ranks = {r.memory.id: r.rank for r in original_results}
    reranked_ranks = {r.memory.id: r.rank for r in reranked_results}

    # Calculate rank changes
    rank_changes = []
    for mem_id in reranked_ranks:
        if mem_id in original_ranks:
            change = abs(original_ranks[mem_id] - reranked_ranks[mem_id])
            rank_changes.append(change)

    # Top-k overlap
    top_3_original = {r.memory.id for r in original_results[:3]}
    top_3_reranked = {r.memory.id for r in reranked_results[:3]}
    top_3_overlap = len(top_3_original & top_3_reranked) / 3

    # Score improvements (if metadata available)
    score_improvements = []
    for result in reranked_results:
        if hasattr(result, "metadata") and result.metadata:
            llm_score = result.metadata.get("llm_score")
            vector_sim = result.metadata.get("vector_similarity")
            if llm_score and vector_sim:
                improvement = llm_score - vector_sim
                score_improvements.append(improvement)

    return {
        "total_candidates": len(original_results),
        "rank_changes": rank_changes,
        "avg_rank_change": sum(rank_changes) / len(rank_changes) if rank_changes else 0,
        "max_rank_change": max(rank_changes) if rank_changes else 0,
        "top_3_overlap": top_3_overlap,
        "score_improvements": score_improvements,
        "avg_score_improvement": (
            sum(score_improvements) / len(score_improvements)
            if score_improvements
            else None
        ),
    }
