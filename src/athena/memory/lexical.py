"""BM25-based lexical search for semantic memories.

Complements vector-based semantic search with keyword matching.
"""

from typing import List, Tuple, Optional
import numpy as np


class LexicalSearch:
    """BM25-based lexical search for memories."""

    def __init__(self):
        """Initialize lexical search."""
        self.corpus = []
        self.memory_ids = []
        self.bm25 = None
        self._initialized = False

    def index_memories(self, memories: List[Tuple[int, str]]):
        """Index memories for BM25 search.

        Args:
            memories: List of (memory_id, content) tuples
        """
        from rank_bm25 import BM25Okapi

        if not memories:
            self._initialized = False
            return

        self.memory_ids = [m[0] for m in memories]

        # Tokenize corpus (simple whitespace splitting)
        self.corpus = [m[1].lower().split() for m in memories]

        # Create BM25 index
        self.bm25 = BM25Okapi(self.corpus)
        self._initialized = True

    def search(self, query: str, k: int = 10) -> List[Tuple[int, float]]:
        """Search using BM25.

        Args:
            query: Search query
            k: Number of results to return

        Returns:
            List of (memory_id, score) tuples sorted by score descending
        """
        if not self._initialized or not self.bm25:
            return []

        # Tokenize query
        tokenized_query = query.lower().split()

        # Get BM25 scores
        scores = self.bm25.get_scores(tokenized_query)

        # Get top k indices
        top_indices = np.argsort(scores)[::-1][:k]

        # Filter out zero scores
        results = [
            (self.memory_ids[idx], float(scores[idx]))
            for idx in top_indices
            if scores[idx] > 0
        ]

        return results

    def batch_search(self, queries: List[str], k: int = 10) -> List[List[Tuple[int, float]]]:
        """Search multiple queries.

        Args:
            queries: List of search queries
            k: Number of results per query

        Returns:
            List of result lists
        """
        return [self.search(q, k) for q in queries]


def reciprocal_rank_fusion(
    result_sets: List[List[Tuple[int, float]]],
    k: int = 60
) -> List[Tuple[int, float]]:
    """Combine multiple ranked result sets using Reciprocal Rank Fusion.

    RRF is a simple but effective rank aggregation method that doesn't require
    score normalization. Formula: score = sum(1 / (k + rank)) for each result set.

    Args:
        result_sets: List of ranked result lists [(id, score), ...]
        k: RRF constant (default 60, from original paper)

    Returns:
        Fused and reranked results as [(id, fused_score), ...]
    """
    scores = {}

    for result_set in result_sets:
        for rank, (item_id, _) in enumerate(result_set, start=1):
            score = 1.0 / (k + rank)

            if item_id not in scores:
                scores[item_id] = 0.0

            scores[item_id] += score

    # Sort by fused score descending
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    return ranked


def hybrid_search(
    query: str,
    vector_results: List[Tuple[int, float]],
    lexical_search: Optional['LexicalSearch'] = None,
    k: int = 10
) -> List[Tuple[int, float]]:
    """Combine vector and lexical search using RRF.

    Args:
        query: Search query
        vector_results: Results from vector search [(id, score), ...]
        lexical_search: Optional LexicalSearch instance for BM25
        k: Number of final results

    Returns:
        Fused results [(id, score), ...]
    """
    result_sets = [vector_results]

    # Add BM25 results if available
    if lexical_search and lexical_search._initialized:
        bm25_results = lexical_search.search(query, k=k*2)  # Get more for fusion
        if bm25_results:
            result_sets.append(bm25_results)

    # Fuse using RRF
    if len(result_sets) == 1:
        # Only vector search available
        return vector_results[:k]

    fused = reciprocal_rank_fusion(result_sets)
    return fused[:k]
