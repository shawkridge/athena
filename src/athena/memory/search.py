"""Semantic search implementation using PostgreSQL pgvector hybrid search."""

import asyncio
import time
import logging
from typing import Optional

from ..core.embeddings import EmbeddingModel
from ..core.models import Memory, MemorySearchResult, MemoryType
from ..core.database_postgres import PostgresDatabase
from ..core.config import (
    RAG_QUERY_EXPANSION_ENABLED,
    RAG_QUERY_EXPANSION_VARIANTS,
    RAG_QUERY_EXPANSION_CACHE,
    RAG_QUERY_EXPANSION_CACHE_SIZE,
)

logger = logging.getLogger(__name__)


class SemanticSearch:
    """Semantic search over memory vectors using PostgreSQL pgvector."""

    def __init__(
        self,
        db: PostgresDatabase,
        embedder: EmbeddingModel,
    ):
        """Initialize semantic search.

        Args:
            db: PostgresDatabase instance (required)
            embedder: Embedding model for vector generation
        """
        self.db = db
        self.embedder = embedder

        # Initialize query expander (optional, graceful degradation)
        self._query_expander = None
        if RAG_QUERY_EXPANSION_ENABLED:
            try:
                from ..rag.llm_client import create_llm_client
                from ..rag.query_expansion import QueryExpander, QueryExpansionConfig

                # Create LLM client from config
                # Try Claude first, fall back to Ollama
                try:
                    llm_client = create_llm_client("claude")
                    logger.info("Initialized QueryExpander with Claude")
                except Exception:
                    try:
                        llm_client = create_llm_client("ollama")
                        logger.info("Initialized QueryExpander with Ollama")
                    except Exception as e:
                        logger.warning(f"Failed to initialize LLM for query expansion: {e}")
                        llm_client = None

                if llm_client:
                    # Configure expander from config
                    config = QueryExpansionConfig(
                        enabled=RAG_QUERY_EXPANSION_ENABLED,
                        num_variants=RAG_QUERY_EXPANSION_VARIANTS,
                        enable_cache=RAG_QUERY_EXPANSION_CACHE,
                        cache_size=RAG_QUERY_EXPANSION_CACHE_SIZE,
                    )
                    self._query_expander = QueryExpander(llm_client, config)
                    logger.info(f"Query expansion enabled ({RAG_QUERY_EXPANSION_VARIANTS} variants)")

            except ImportError as e:
                logger.warning(f"Query expansion unavailable (missing dependencies): {e}")

        logger.info("SemanticSearch initialized with PostgreSQL pgvector backend")

    def recall(
        self,
        query: str,
        project_id: int,
        k: int = 5,
        memory_types: Optional[list[MemoryType]] = None,
        min_similarity: float = 0.3,
    ) -> list[MemorySearchResult]:
        """Search for relevant memories with optional query expansion.

        Flow:
        1. If query expansion enabled: Generate alternative query phrasings
        2. Execute parallel searches for all query variants
        3. Merge and deduplicate results from all variants
        4. Rerank merged results by similarity
        5. Return top-k results

        Uses PostgreSQL pgvector hybrid search.

        Args:
            query: Search query
            project_id: Project ID to search within
            k: Number of results to return
            memory_types: Filter by memory types (None = all types)
            min_similarity: Minimum cosine similarity threshold

        Returns:
            List of search results with similarity scores
        """
        # Query expansion: Generate alternative phrasings if enabled
        if self._query_expander:
            try:
                start_time = time.time()
                expanded = self._query_expander.expand(query)
                expansion_time = time.time() - start_time

                logger.info(
                    f"Query expansion: {len(expanded)} variants in {expansion_time:.2f}s"
                )

                # Execute parallel searches for all variants
                # Request more results per variant (k*2) to increase recall
                results_per_variant = k * 2

                all_results = []
                search_start = time.time()

                for variant_query in expanded.all_queries():
                    logger.debug(f"Searching variant: '{variant_query}'")

                    # Generate embedding for variant
                    query_embedding = self.embedder.embed(variant_query)

                    # Execute PostgreSQL search
                    variant_results = self._recall_postgres(
                        query_embedding,
                        project_id,
                        variant_query,
                        results_per_variant,
                        memory_types,
                        min_similarity,
                    )

                    all_results.extend(variant_results)

                search_time = time.time() - search_start
                logger.info(
                    f"Searched {len(expanded)} variants in {search_time:.2f}s "
                    f"({len(all_results)} raw results)"
                )

                # Merge and deduplicate results
                merged_results = self._merge_results(all_results, k)

                logger.info(
                    f"Query expansion complete: {len(merged_results)} final results "
                    f"(total time: {expansion_time + search_time:.2f}s)"
                )

                return merged_results

            except Exception as e:
                logger.warning(f"Query expansion failed, falling back to single query: {e}")
                # Fall through to single query below

        # Single query (no expansion or expansion failed)
        query_embedding = self.embedder.embed(query)

        # Use PostgreSQL pgvector hybrid search
        return self._recall_postgres(
            query_embedding, project_id, query, k, memory_types, min_similarity
        )

    def _recall_postgres(
        self,
        query_embedding: list[float],
        project_id: int,
        query_text: str,
        k: int,
        memory_types: Optional[list[MemoryType]],
        min_similarity: float,
    ) -> list[MemorySearchResult]:
        """Search using PostgreSQL native hybrid search.

        Uses native SQL combining semantic similarity + full-text search + recency.

        Args:
            query_embedding: Query embedding vector
            project_id: Project ID to filter by
            query_text: Original query text for full-text search
            k: Number of results
            memory_types: Optional memory type filter
            min_similarity: Minimum similarity threshold

        Returns:
            List of search results
        """
        # Use asyncio.run() to bridge sync/async gap
        # This is safe because SemanticSearch is meant to be called from sync code
        results = asyncio.run(
            self._recall_postgres_async(
                query_embedding, project_id, query_text, k, memory_types, min_similarity
            )
        )
        logger.debug(f"PostgreSQL hybrid search returned {len(results)} results")
        return results

    async def _recall_postgres_async(
        self,
        query_embedding: list[float],
        project_id: int,
        query_text: str,
        k: int,
        memory_types: Optional[list[MemoryType]],
        min_similarity: float,
    ) -> list[MemorySearchResult]:
        """Async PostgreSQL hybrid search implementation.

        Args:
            query_embedding: Query embedding vector
            project_id: Project ID
            query_text: Original query text
            k: Number of results
            memory_types: Optional memory type filter
            min_similarity: Minimum similarity threshold

        Returns:
            List of search results
        """
        # Build type filter if provided
        type_filter = None
        if memory_types:
            type_filter = [mt.value for mt in memory_types]

        # Use hybrid search from PostgresDatabase
        # The hybrid_search method combines:
        # - Semantic similarity (vector cosine similarity)
        # - Full-text search (BM25-like scoring via PostgreSQL tsvector)
        # - Relational filtering (project, type, consolidation state)
        pg_db = self.db  # Type: PostgresDatabase
        search_results = await pg_db.hybrid_search(
            project_id=project_id,
            embedding=query_embedding,
            query_text=query_text,
            memory_types=type_filter,
            limit=k,
            semantic_weight=0.7,
            keyword_weight=0.3,
            consolidation_state="consolidated",
        )

        # Convert database results to MemorySearchResult objects
        results = []
        for rank, db_result in enumerate(search_results, 1):
            # db_result is a dict with: id, content, similarity_score, fts_score, recency_score, etc.
            memory_id = db_result.get("id")
            similarity = db_result.get("similarity_score", 0.0)

            # Get full memory object for context
            memory = await pg_db.get_memory(memory_id)
            if memory:
                # Update access stats asynchronously
                try:
                    await pg_db.update_access_stats(memory_id)
                except Exception as e:
                    logger.debug(f"Failed to update access stats: {e}")

                results.append(
                    MemorySearchResult(
                        memory=memory,
                        similarity=similarity,
                        rank=rank,
                    )
                )

        return results

    def _merge_results(
        self, all_results: list[MemorySearchResult], k: int
    ) -> list[MemorySearchResult]:
        """Merge and deduplicate results from multiple query variants.

        Strategy:
        1. Group results by memory_id
        2. For each memory, keep the highest similarity score across variants
        3. Sort by similarity (highest first)
        4. Take top-k results
        5. Update ranks

        Args:
            all_results: Combined results from all query variants
            k: Number of results to return

        Returns:
            Merged and deduplicated results (top-k by similarity)

        Examples:
            >>> # Variant 1 returns: [(mem_1, 0.8), (mem_2, 0.7)]
            >>> # Variant 2 returns: [(mem_1, 0.75), (mem_3, 0.6)]
            >>> # Merged: [(mem_1, 0.8), (mem_2, 0.7), (mem_3, 0.6)]
        """
        if not all_results:
            return []

        # Group by memory_id, keeping highest similarity
        best_results = {}  # memory_id -> MemorySearchResult

        for result in all_results:
            memory_id = result.memory.id

            if memory_id not in best_results:
                best_results[memory_id] = result
            else:
                # Keep result with higher similarity
                if result.similarity > best_results[memory_id].similarity:
                    best_results[memory_id] = result

        # Convert to list and sort by similarity (descending)
        merged = list(best_results.values())
        merged.sort(key=lambda r: r.similarity, reverse=True)

        # Take top-k and update ranks
        final_results = []
        for rank, result in enumerate(merged[:k], 1):
            result.rank = rank
            final_results.append(result)

        logger.debug(
            f"Merged {len(all_results)} results into {len(final_results)} unique memories "
            f"(deduplication: {len(all_results) - len(merged)} duplicates)"
        )

        return final_results

    def recall_with_reranking(
        self,
        query: str,
        project_id: int,
        k: int = 5,
        memory_types: Optional[list[MemoryType]] = None,
        recency_weight: float = 0.1,
        usefulness_weight: float = 0.2,
    ) -> list[MemorySearchResult]:
        """Search with composite scoring (similarity + recency + usefulness).

        Uses PostgreSQL for initial retrieval, then reranks with additional factors.

        Args:
            query: Search query
            project_id: Project ID
            k: Number of results
            memory_types: Filter by types
            recency_weight: Weight for recency score (0-1)
            usefulness_weight: Weight for usefulness score (0-1)

        Returns:
            Reranked search results
        """
        # Get more candidates for reranking
        similarity_weight = 1.0 - recency_weight - usefulness_weight
        results = self.recall(
            query, project_id, k=k * 3, memory_types=memory_types, min_similarity=0.2
        )

        if not results:
            return []

        # Calculate composite scores
        from datetime import datetime
        now = datetime.now()
        rescored = []

        for result in results:
            memory = result.memory

            # Similarity score (already 0-1 from PostgreSQL hybrid search)
            sim_score = result.similarity

            # Recency score (decay over 90 days)
            if memory.last_accessed:
                days_since_access = (now - memory.last_accessed).total_seconds() / 86400
                recency_score = max(0, 1.0 - (days_since_access / 90))
            else:
                recency_score = 0.5

            # Usefulness score (already 0-1)
            useful_score = memory.usefulness_score

            # Composite score
            composite = (
                similarity_weight * sim_score
                + recency_weight * recency_score
                + usefulness_weight * useful_score
            )

            rescored.append((result, composite))

        # Re-sort by composite score
        rescored.sort(key=lambda x: x[1], reverse=True)

        # Take top-k and update ranks
        final_results = []
        for rank, (result, score) in enumerate(rescored[:k], 1):
            result.rank = rank
            final_results.append(result)

        return final_results

    def search_across_projects(
        self, query: str, exclude_project_id: Optional[int] = None, k: int = 5
    ) -> list[MemorySearchResult]:
        """Search across all projects.

        Uses PostgreSQL pgvector hybrid search.

        Args:
            query: Search query
            exclude_project_id: Project ID to exclude (e.g., current project)
            k: Number of results

        Returns:
            Search results from all projects
        """
        query_embedding = self.embedder.embed(query)

        # Use PostgreSQL (always available per __init__)
        return self._search_across_projects_postgres(
            query_embedding, query, exclude_project_id, k
        )

    def _search_across_projects_postgres(
        self,
        query_embedding: list[float],
        query_text: str,
        exclude_project_id: Optional[int],
        k: int,
    ) -> list[MemorySearchResult]:
        """Search across projects using PostgreSQL hybrid search.

        Args:
            query_embedding: Query embedding vector
            query_text: Original query text
            exclude_project_id: Project ID to exclude
            k: Number of results

        Returns:
            Search results from all projects
        """
        results = asyncio.run(
            self._search_across_projects_postgres_async(
                query_embedding, query_text, exclude_project_id, k
            )
        )
        return results

    async def _search_across_projects_postgres_async(
        self,
        query_embedding: list[float],
        query_text: str,
        exclude_project_id: Optional[int],
        k: int,
    ) -> list[MemorySearchResult]:
        """Async PostgreSQL cross-project search.

        Args:
            query_embedding: Query embedding vector
            query_text: Original query text
            exclude_project_id: Project ID to exclude
            k: Number of results

        Returns:
            Search results
        """
        pg_db = self.db  # Type: PostgresDatabase

        # Get all project IDs (or all except excluded)
        # For now, use a large project_id range, or query projects table
        # We'll search with project_id filtering if needed
        try:
            # Search across all with hybrid scoring
            search_results = await pg_db.hybrid_search(
                project_id=None,  # Cross-project search
                embedding=query_embedding,
                query_text=query_text,
                memory_types=None,
                limit=k * 2,  # Get more for filtering
                min_similarity=0.2,  # Lower threshold for cross-project
            )
        except TypeError:
            # If hybrid_search doesn't support None project_id, use semantic search
            search_results = await pg_db.semantic_search(
                project_id=None,
                embedding=query_embedding,
                limit=k * 2,
                min_similarity=0.2,
            )

        # Filter out excluded project if specified
        results = []
        for rank, db_result in enumerate(search_results, 1):
            memory_id = db_result.get("id")
            similarity = db_result.get("similarity_score", 0.0)

            memory = await pg_db.get_memory(memory_id)
            if memory:
                # Skip if matches exclude_project_id
                if exclude_project_id and memory.project_id == exclude_project_id:
                    continue

                results.append(
                    MemorySearchResult(
                        memory=memory,
                        similarity=similarity,
                        rank=len(results) + 1,
                    )
                )

                if len(results) >= k:
                    break

        return results



def diversify_by_type(results: list[MemorySearchResult], k: int) -> list[MemorySearchResult]:
    """Ensure diversity of memory types in results.

    Tries to include at least one of each memory type if available.

    Args:
        results: Search results
        k: Target number of results

    Returns:
        Diversified results
    """
    if len(results) <= k:
        return results

    # Group by type
    by_type = {mt: [] for mt in MemoryType}
    for result in results:
        by_type[result.memory.memory_type].append(result)

    # Take top result from each type first
    diversified = []
    for type_results in by_type.values():
        if type_results:
            diversified.append(type_results[0])
            if len(diversified) >= k:
                break

    # Fill remaining slots with highest-ranked remaining
    if len(diversified) < k:
        seen_ids = {r.memory.id for r in diversified}
        for result in results:
            if result.memory.id not in seen_ids:
                diversified.append(result)
                if len(diversified) >= k:
                    break

    # Re-sort by original rank
    diversified.sort(key=lambda x: x.rank)

    return diversified[:k]
