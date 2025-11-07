"""Semantic code search using embeddings and similarity matching."""

import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass
import numpy as np

from .models import CodeUnit, SearchResult, SearchQuery
from .indexer import CodebaseIndexer

logger = logging.getLogger(__name__)


@dataclass
class SearchScores:
    """Scores for a search result."""
    semantic_score: float  # Vector similarity (0-1)
    name_score: float      # Exact/partial name match (0-1)
    type_score: float      # Type match (0-1)
    combined_score: float  # Weighted combination


class SemanticCodeSearcher:
    """
    Search code semantically using embeddings and vector similarity.

    Combines embedding-based semantic search with syntactic matching
    for comprehensive code discovery.
    """

    def __init__(self, indexer: CodebaseIndexer, embedding_manager=None):
        """
        Initialize semantic searcher.

        Args:
            indexer: CodebaseIndexer with indexed code units
            embedding_manager: Optional manager for generating query embeddings
        """
        self.indexer = indexer
        self.embedding_manager = embedding_manager
        self.units = indexer.get_units()

        # Build embedding vectors for units
        self.embeddings = self._build_embeddings()

        # Scoring weights
        self.semantic_weight = 0.5    # Embedding similarity
        self.name_weight = 0.25       # Name matching
        self.type_weight = 0.25       # Type matching

    def _build_embeddings(self) -> dict:
        """Build embedding vectors for all indexed units."""
        embeddings = {}

        for unit in self.units:
            if unit.embedding:
                embeddings[unit.id] = np.array(unit.embedding)
            elif self.embedding_manager:
                try:
                    search_text = self._create_search_text(unit)
                    embedding = self.embedding_manager.generate(search_text)
                    embeddings[unit.id] = np.array(embedding)
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for {unit.id}: {e}")
            else:
                # No embedding available
                embeddings[unit.id] = None

        return embeddings

    def search(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.3,
        types: Optional[List[str]] = None,
        files: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        """
        Search for code units matching query.

        Args:
            query: Search query string
            limit: Maximum results to return
            min_score: Minimum relevance score (0-1)
            types: Filter by unit types (e.g., ["function", "class"])
            files: Filter by file paths

        Returns:
            List of SearchResult objects sorted by relevance
        """
        if not query or not query.strip():
            return []

        # Parse query
        parsed_query = SearchQuery(original=query, intent=query)

        # Generate query embedding if available
        query_embedding = None
        if self.embedding_manager:
            try:
                query_embedding = np.array(
                    self.embedding_manager.generate(query)
                )
            except Exception as e:
                logger.warning(f"Failed to generate query embedding: {e}")

        # Score all units
        results = []
        for unit in self.units:
            # Apply filters
            if types and unit.type not in types:
                continue
            if files and unit.file_path not in files:
                continue

            # Calculate scores
            scores = self._score_unit(unit, parsed_query, query_embedding)

            # Skip below threshold
            if scores.combined_score < min_score:
                continue

            # Create result
            result = SearchResult(
                unit=unit,
                relevance=scores.combined_score,
                context="semantic_match",
            )
            results.append(result)

        # Sort by relevance (descending)
        results.sort(key=lambda r: r.relevance, reverse=True)

        return results[:limit]

    def find_similar(
        self,
        unit_id: str,
        limit: int = 5,
        min_score: float = 0.3,
    ) -> List[SearchResult]:
        """
        Find code units similar to a given unit.

        Args:
            unit_id: ID of reference unit
            limit: Maximum results to return
            min_score: Minimum similarity score

        Returns:
            List of similar SearchResult objects
        """
        # Get reference unit
        reference_unit = self.indexer.get_unit(unit_id)
        if not reference_unit:
            return []

        # Get reference embedding
        if unit_id not in self.embeddings or self.embeddings[unit_id] is None:
            logger.warning(f"No embedding for reference unit {unit_id}")
            return []

        ref_embedding = self.embeddings[unit_id]

        # Score all units against reference
        results = []
        for unit in self.units:
            if unit.id == unit_id:
                continue  # Skip the reference unit itself

            # Get unit embedding
            if unit.id not in self.embeddings or self.embeddings[unit.id] is None:
                continue  # Skip units without embeddings

            unit_embedding = self.embeddings[unit.id]

            # Calculate similarity
            similarity = self._cosine_similarity(ref_embedding, unit_embedding)

            # Skip below threshold
            if similarity < min_score:
                continue

            # Create result
            result = SearchResult(
                unit=unit,
                relevance=similarity,
                context="similar_to_" + unit_id,
            )
            results.append(result)

        # Sort by relevance (descending)
        results.sort(key=lambda r: r.relevance, reverse=True)

        return results[:limit]

    def search_by_type(
        self,
        unit_type: str,
        query: Optional[str] = None,
        limit: int = 10,
    ) -> List[SearchResult]:
        """
        Search units of specific type, optionally filtered by query.

        Args:
            unit_type: Type to search for (e.g., "function", "class")
            query: Optional text query for further filtering
            limit: Maximum results to return

        Returns:
            List of SearchResult objects
        """
        units = self.indexer.find_by_type(unit_type)

        if not query:
            # No query, return type-matched results
            results = [
                SearchResult(
                    unit=unit,
                    relevance=1.0,
                    context="type_match",
                )
                for unit in units[:limit]
            ]
            return results

        # Filter by query
        return self.search(query, limit=limit, types=[unit_type])

    def search_by_name(
        self,
        name_query: str,
        limit: int = 10,
        exact: bool = False,
    ) -> List[SearchResult]:
        """
        Search units by name.

        Args:
            name_query: Name to search for
            limit: Maximum results to return
            exact: If True, only exact matches; if False, partial matches

        Returns:
            List of SearchResult objects
        """
        results = []

        for unit in self.units:
            if exact:
                # Exact match
                if unit.name.lower() != name_query.lower():
                    continue
                score = 1.0
                result = SearchResult(
                    unit=unit,
                    relevance=score,
                    context="name_match_exact",
                )
                results.append(result)
            else:
                # Partial match with scoring
                query_lower = name_query.lower()
                name_lower = unit.name.lower()

                if query_lower in name_lower:
                    # Calculate match quality
                    if name_lower == query_lower:
                        score = 1.0  # Exact match
                    elif name_lower.startswith(query_lower):
                        score = 0.9  # Starts with
                    else:
                        score = 0.7  # Contains

                    result = SearchResult(
                        unit=unit,
                        relevance=score,
                        context="name_match",
                    )
                    results.append(result)

        # Sort by relevance (descending)
        results.sort(key=lambda r: r.relevance, reverse=True)

        return results[:limit]

    def _score_unit(
        self,
        unit: CodeUnit,
        query: SearchQuery,
        query_embedding: Optional[np.ndarray],
    ) -> SearchScores:
        """
        Score a unit against a query.

        Args:
            unit: Code unit to score
            query: Parsed search query
            query_embedding: Query embedding vector (if available)

        Returns:
            SearchScores object with component scores
        """
        semantic_score = 0.0
        name_score = 0.0
        type_score = 0.0

        # Semantic similarity (embedding-based)
        if query_embedding is not None and unit.id in self.embeddings:
            if self.embeddings[unit.id] is not None:
                semantic_score = self._cosine_similarity(
                    query_embedding, self.embeddings[unit.id]
                )

        # Name matching
        query_text = query.original or query.intent
        if query_text.lower() in unit.name.lower():
            name_score = 0.8
            if unit.name.lower() == query_text.lower():
                name_score = 1.0
        elif any(
            word.lower() in unit.name.lower() for word in query_text.split()
        ):
            name_score = 0.5

        # Type matching (if query specifies type)
        # (SearchQuery doesn't have type field, so this is omitted)

        # Combined score (weighted)
        combined_score = (
            self.semantic_weight * semantic_score
            + self.name_weight * name_score
            + self.type_weight * type_score
        )

        return SearchScores(
            semantic_score=semantic_score,
            name_score=name_score,
            type_score=type_score,
            combined_score=combined_score,
        )

    @staticmethod
    def _cosine_similarity(
        a: np.ndarray, b: np.ndarray
    ) -> float:
        """Calculate cosine similarity between vectors."""
        if a is None or b is None:
            return 0.0

        # Normalize vectors
        a_norm = np.linalg.norm(a)
        b_norm = np.linalg.norm(b)

        if a_norm == 0 or b_norm == 0:
            return 0.0

        # Calculate cosine similarity
        similarity = np.dot(a, b) / (a_norm * b_norm)

        # Clamp to [0, 1]
        return max(0.0, min(1.0, float(similarity)))

    @staticmethod
    def _create_search_text(unit: CodeUnit) -> str:
        """Create searchable text from code unit."""
        parts = [
            unit.name,
            unit.type,
            unit.signature,
            unit.docstring,
        ]

        # Add code snippet (first few lines)
        code_lines = unit.code.split("\n")[:3]
        parts.extend([line.strip() for line in code_lines if line.strip()])

        return " ".join(filter(None, parts))

    def get_search_stats(self) -> dict:
        """Get statistics about indexed units and embeddings."""
        total_units = len(self.units)
        units_with_embeddings = sum(
            1 for e in self.embeddings.values() if e is not None
        )

        return {
            "total_units": total_units,
            "units_with_embeddings": units_with_embeddings,
            "embedding_coverage": (
                units_with_embeddings / total_units if total_units > 0 else 0
            ),
            "units_by_type": self._count_by_type(),
        }

    def _count_by_type(self) -> dict:
        """Count units by type."""
        counts = {}
        for unit in self.units:
            counts[unit.type] = counts.get(unit.type, 0) + 1
        return counts
