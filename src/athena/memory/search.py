"""Semantic search implementation using PostgreSQL hybrid, Qdrant, or sqlite-vec fallback."""

import asyncio
import json
import time
import logging
from typing import Optional, TYPE_CHECKING, Union

from ..core.database import Database
from ..core.embeddings import EmbeddingModel
from ..core.models import Memory, MemorySearchResult, MemoryType

if TYPE_CHECKING:
    from ..rag.qdrant_adapter import QdrantAdapter
    from ..core.database_postgres import PostgresDatabase

logger = logging.getLogger(__name__)


class SemanticSearch:
    """Semantic search over memory vectors with PostgreSQL hybrid, Qdrant, or sqlite-vec."""

    def __init__(
        self,
        db: Union[Database, "PostgresDatabase"],
        embedder: EmbeddingModel,
        qdrant: Optional["QdrantAdapter"] = None
    ):
        """Initialize semantic search.

        Args:
            db: Database instance (SQLite Database or PostgresDatabase)
            embedder: Embedding model
            qdrant: Optional Qdrant adapter for vector search
        """
        self.db = db
        self.embedder = embedder
        self.qdrant = qdrant

        # Detect database backend
        self._is_postgres = self._check_postgres()

        if self._is_postgres:
            logger.info("SemanticSearch initialized with PostgreSQL hybrid backend")
        elif qdrant:
            logger.info("SemanticSearch initialized with Qdrant backend")
        else:
            logger.info("SemanticSearch initialized with sqlite-vec backend")

    def _check_postgres(self) -> bool:
        """Check if database is PostgresDatabase.

        Returns:
            True if database is PostgreSQL, False otherwise
        """
        try:
            from ..core.database_postgres import PostgresDatabase
            return isinstance(self.db, PostgresDatabase)
        except (ImportError, AttributeError):
            return False

    def recall(
        self,
        query: str,
        project_id: int,
        k: int = 5,
        memory_types: Optional[list[MemoryType]] = None,
        min_similarity: float = 0.3,
    ) -> list[MemorySearchResult]:
        """Search for relevant memories.

        Uses PostgreSQL hybrid search (best), Qdrant (if available), or sqlite-vec (fallback).

        Args:
            query: Search query
            project_id: Project ID to search within
            k: Number of results to return
            memory_types: Filter by memory types (None = all types)
            min_similarity: Minimum cosine similarity threshold

        Returns:
            List of search results with similarity scores
        """
        # Generate query embedding
        query_embedding = self.embedder.embed(query)

        # Use PostgreSQL hybrid search if available (best performance + quality)
        if self._is_postgres:
            return self._recall_postgres(
                query_embedding, project_id, query, k, memory_types, min_similarity
            )
        # Use Qdrant if available
        elif self.qdrant:
            return self._recall_qdrant(
                query_embedding, project_id, k, memory_types, min_similarity
            )
        # Fall back to sqlite-vec
        else:
            return self._recall_sqlite(
                query_embedding, project_id, k, memory_types, min_similarity
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
        try:
            # Use asyncio.run() to bridge sync/async gap
            # This is safe because SemanticSearch is meant to be called from sync code
            results = asyncio.run(
                self._recall_postgres_async(
                    query_embedding, project_id, query_text, k, memory_types, min_similarity
                )
            )
            logger.debug(f"PostgreSQL hybrid search returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"PostgreSQL search failed: {e}. Falling back to Qdrant/SQLite.")
            # Fall back to other backends
            if self.qdrant:
                return self._recall_qdrant(
                    query_embedding, project_id, k, memory_types, min_similarity
                )
            else:
                return self._recall_sqlite(
                    query_embedding, project_id, k, memory_types, min_similarity
                )

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
        # - Recency boost (exponential decay over time)
        pg_db = self.db  # Type: PostgresDatabase
        search_results = await pg_db.hybrid_search(
            project_id=project_id,
            embedding=query_embedding,
            query_text=query_text,
            memory_types=type_filter,
            limit=k,
            min_similarity=min_similarity,
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

    def _recall_qdrant(
        self,
        query_embedding: list[float],
        project_id: int,
        k: int,
        memory_types: Optional[list[MemoryType]],
        min_similarity: float,
    ) -> list[MemorySearchResult]:
        """Search using Qdrant vector database.

        Args:
            query_embedding: Query embedding vector
            project_id: Project ID to filter by
            k: Number of results
            memory_types: Optional memory type filter
            min_similarity: Minimum similarity threshold

        Returns:
            List of search results
        """
        # Build filters for Qdrant
        filters = {"project_id": project_id}
        if memory_types:
            filters["memory_type"] = [mt.value for mt in memory_types]

        # Search Qdrant
        qdrant_results = self.qdrant.search(
            query_embedding=query_embedding,
            limit=k,
            score_threshold=min_similarity,
            filters=filters,
        )

        # Convert Qdrant results to MemorySearchResult
        results = []
        for rank, qdrant_mem in enumerate(qdrant_results, 1):
            # Fetch full memory metadata from SQLite
            memory = self.db.get_memory(qdrant_mem.id)
            if memory:
                # Update access stats
                self.db.update_access_stats(memory.id)

                results.append(
                    MemorySearchResult(
                        memory=memory,
                        similarity=qdrant_mem.score if qdrant_mem.score else 0.0,
                        rank=rank
                    )
                )

        logger.debug(f"Qdrant search returned {len(results)} results")
        return results

    def _recall_sqlite(
        self,
        query_embedding: list[float],
        project_id: int,
        k: int,
        memory_types: Optional[list[MemoryType]],
        min_similarity: float,
    ) -> list[MemorySearchResult]:
        """Fallback search using sqlite-vec.

        Args:
            query_embedding: Query embedding vector
            project_id: Project ID
            k: Number of results
            memory_types: Optional memory type filter
            min_similarity: Minimum similarity threshold

        Returns:
            List of search results
        """
        query_embedding_json = json.dumps(query_embedding)
        cursor = self.db.conn.cursor()

        if memory_types:
            type_values = [mt.value for mt in memory_types]
            placeholders = ",".join("?" * len(type_values))

            # Use vec_distance_cosine for similarity calculation
            # Note: sqlite-vec returns distance (0 = identical, 2 = opposite)
            # Convert to similarity: similarity = 1 - (distance / 2)
            query = f"""
                SELECT
                    m.id,
                    (1 - vec_distance_cosine(v.embedding, ?1) / 2.0) as similarity
                FROM memories m
                JOIN memory_vectors v ON m.id = v.rowid
                WHERE m.project_id = ?2
                AND m.memory_type IN ({placeholders})
                AND (1 - vec_distance_cosine(v.embedding, ?1) / 2.0) >= ?{3 + len(type_values)}
                ORDER BY similarity DESC
                LIMIT ?{4 + len(type_values)}
            """
            params = [query_embedding_json, project_id] + type_values + [min_similarity, k]
        else:
            query = """
                SELECT
                    m.id,
                    (1 - vec_distance_cosine(v.embedding, ?1) / 2.0) as similarity
                FROM memories m
                JOIN memory_vectors v ON m.id = v.rowid
                WHERE m.project_id = ?2
                AND (1 - vec_distance_cosine(v.embedding, ?1) / 2.0) >= ?3
                ORDER BY similarity DESC
                LIMIT ?4
            """
            params = [query_embedding_json, project_id, min_similarity, k]

        cursor.execute(query, params)
        results = []

        for rank, row in enumerate(cursor.fetchall(), 1):
            memory_id = row[0]
            similarity = row[1]

            memory = self.db.get_memory(memory_id)
            if memory:
                # Update access stats
                self.db.update_access_stats(memory_id)

                results.append(
                    MemorySearchResult(memory=memory, similarity=similarity, rank=rank)
                )

        logger.debug(f"SQLite search returned {len(results)} results")
        return results

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

        Uses sqlite-vec for initial retrieval, then reranks with additional factors.

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

            # Similarity score (already 0-1 from sqlite-vec)
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

        Uses PostgreSQL (if available) or sqlite-vec fallback.

        Args:
            query: Search query
            exclude_project_id: Project ID to exclude (e.g., current project)
            k: Number of results

        Returns:
            Search results from all projects
        """
        query_embedding = self.embedder.embed(query)

        # Use PostgreSQL if available
        if self._is_postgres:
            return self._search_across_projects_postgres(
                query_embedding, query, exclude_project_id, k
            )
        # Fall back to sqlite-vec
        else:
            return self._search_across_projects_sqlite(
                query_embedding, exclude_project_id, k
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
        try:
            results = asyncio.run(
                self._search_across_projects_postgres_async(
                    query_embedding, query_text, exclude_project_id, k
                )
            )
            return results
        except Exception as e:
            logger.error(f"PostgreSQL cross-project search failed: {e}")
            return self._search_across_projects_sqlite(
                query_embedding, exclude_project_id, k
            )

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

    def _search_across_projects_sqlite(
        self,
        query_embedding: list[float],
        exclude_project_id: Optional[int],
        k: int,
    ) -> list[MemorySearchResult]:
        """Search across projects using sqlite-vec.

        Args:
            query_embedding: Query embedding vector
            exclude_project_id: Project ID to exclude
            k: Number of results

        Returns:
            Search results from all projects
        """
        query_embedding_json = json.dumps(query_embedding)

        cursor = self.db.conn.cursor()

        if exclude_project_id:
            cursor.execute(
                """
                SELECT
                    m.id,
                    (1 - vec_distance_cosine(v.embedding, ?) / 2.0) as similarity
                FROM memories m
                JOIN memory_vectors v ON m.id = v.rowid
                WHERE m.project_id != ?
                ORDER BY similarity DESC
                LIMIT ?
            """,
                (query_embedding_json, exclude_project_id, k),
            )
        else:
            cursor.execute(
                """
                SELECT
                    m.id,
                    (1 - vec_distance_cosine(v.embedding, ?) / 2.0) as similarity
                FROM memories m
                JOIN memory_vectors v ON m.id = v.rowid
                ORDER BY similarity DESC
                LIMIT ?
            """,
                (query_embedding_json, k),
            )

        # Build results
        results = []
        for rank, row in enumerate(cursor.fetchall(), 1):
            memory_id = row[0]
            similarity = row[1]

            memory = self.db.get_memory(memory_id)
            if memory:
                results.append(
                    MemorySearchResult(memory=memory, similarity=similarity, rank=rank)
                )

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
