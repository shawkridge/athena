"""Semantic search implementation using sqlite-vec native functions."""

import json
import time
from typing import Optional

from ..core.database import Database
from ..core.embeddings import EmbeddingModel
from ..core.models import Memory, MemorySearchResult, MemoryType


class SemanticSearch:
    """Semantic search over memory vectors using sqlite-vec."""

    def __init__(self, db: Database, embedder: EmbeddingModel):
        """Initialize semantic search.

        Args:
            db: Database instance
            embedder: Embedding model
        """
        self.db = db
        self.embedder = embedder

    def recall(
        self,
        query: str,
        project_id: int,
        k: int = 5,
        memory_types: Optional[list[MemoryType]] = None,
        min_similarity: float = 0.3,
    ) -> list[MemorySearchResult]:
        """Search for relevant memories using sqlite-vec's vector search.

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
        query_embedding_json = json.dumps(query_embedding)

        # Use sqlite-vec's native vector search with filtering
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
        """Search across all projects using sqlite-vec.

        Args:
            query: Search query
            exclude_project_id: Project ID to exclude (e.g., current project)
            k: Number of results

        Returns:
            Search results from all projects
        """
        query_embedding = self.embedder.embed(query)
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
