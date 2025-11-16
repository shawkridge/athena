"""Semantic search for marketplace procedures using embeddings."""

from typing import List, Optional, Dict, Any
from .marketplace import MarketplaceProcedure
from .marketplace_store import MarketplaceStore


class SemanticProcedureSearch:
    """Semantic search engine for marketplace procedures."""

    def __init__(self, marketplace_store: MarketplaceStore, embedding_model=None):
        """Initialize semantic search engine.

        Args:
            marketplace_store: MarketplaceStore instance
            embedding_model: Optional embedding model for vector search
        """
        self.store = marketplace_store
        self.embedding_model = embedding_model
        self.procedure_cache: Dict[str, List[float]] = {}

    def search_by_semantic_similarity(
        self,
        query: str,
        limit: int = 10,
        similarity_threshold: float = 0.5,
    ) -> List[tuple[MarketplaceProcedure, float]]:
        """Search procedures by semantic similarity to query.

        Args:
            query: Search query or natural language description
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score (0.0-1.0)

        Returns:
            List of (procedure, similarity_score) tuples
        """
        if not self.embedding_model:
            # Fallback to keyword search if no embedding model
            return self._keyword_search(query, limit)

        # Generate query embedding
        try:
            query_embedding = self.embedding_model.embed(query)
        except (AttributeError, ValueError, TypeError):
            # Fallback to keyword search on embedding failure
            return self._keyword_search(query, limit)

        # Get all procedures from store
        all_procedures = list(self.store._procedures.values())

        results = []
        for procedure in all_procedures:
            # Get or compute procedure embedding
            proc_embedding = self._get_procedure_embedding(procedure)
            if not proc_embedding:
                continue

            # Compute cosine similarity
            similarity = self._cosine_similarity(query_embedding, proc_embedding)

            if similarity >= similarity_threshold:
                results.append((procedure, similarity))

        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:limit]

    def search_by_use_case(
        self,
        use_case_description: str,
        limit: int = 10,
    ) -> List[MarketplaceProcedure]:
        """Find procedures relevant to a use case description.

        Args:
            use_case_description: Natural language description of use case
            limit: Maximum number of results

        Returns:
            List of relevant procedures
        """
        # Use semantic similarity with lower threshold for broader results
        results = self.search_by_semantic_similarity(
            use_case_description,
            limit=limit,
            similarity_threshold=0.3,
        )

        return [proc for proc, _ in results]

    def search_related_procedures(
        self,
        procedure_id: str,
        limit: int = 5,
    ) -> List[tuple[MarketplaceProcedure, float]]:
        """Find procedures related to a specific procedure.

        Args:
            procedure_id: Reference procedure ID
            limit: Maximum number of related procedures

        Returns:
            List of (procedure, relatedness_score) tuples
        """
        procedure = self.store.get_procedure(procedure_id)
        if not procedure:
            return []

        # Create query from procedure metadata
        query = f"{procedure.metadata.name} {procedure.metadata.description}"

        # Search semantically, excluding the original procedure
        results = self.search_by_semantic_similarity(query, limit=limit + 1)

        # Filter out the original procedure
        filtered = [
            (proc, score)
            for proc, score in results
            if proc.metadata.procedure_id != procedure_id
        ]

        return filtered[:limit]

    def search_by_tags_semantic(
        self,
        query_tags: List[str],
        limit: int = 10,
    ) -> List[MarketplaceProcedure]:
        """Search procedures by semantic similarity to tags.

        Args:
            query_tags: List of tags or keywords
            limit: Maximum number of results

        Returns:
            List of procedures matching tags
        """
        # Create a query string from tags
        query = " ".join(query_tags)

        results = self.search_by_semantic_similarity(
            query,
            limit=limit,
            similarity_threshold=0.4,
        )

        return [proc for proc, _ in results]

    def get_trending_procedures(
        self,
        limit: int = 10,
        min_installations: int = 0,
    ) -> List[tuple[MarketplaceProcedure, float]]:
        """Get trending procedures by installation count and ratings.

        Args:
            limit: Maximum number of results
            min_installations: Minimum installation count

        Returns:
            List of (procedure, trend_score) tuples
        """
        all_procedures = list(self.store._procedures.values())

        results = []
        for procedure in all_procedures:
            proc_id = procedure.metadata.procedure_id
            installation_count = self.store.get_installation_count(proc_id)
            if installation_count < min_installations:
                continue

            # Calculate trend score: installations + ratings + execution count
            rating = self.store.get_average_rating(proc_id) or 0.0
            trend_score = (
                0.4 * (installation_count / max(procedure.metadata.execution_count, 1))
                + 0.4 * (rating / 5.0)
                + 0.2 * (procedure.metadata.execution_count / 1000.0)
            )

            results.append((procedure, trend_score))

        # Sort by trend score
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:limit]

    def get_quality_recommendations(
        self,
        quality_threshold: str = "stable",
        limit: int = 10,
    ) -> List[MarketplaceProcedure]:
        """Get high-quality procedures recommended for use.

        Args:
            quality_threshold: Minimum quality level (experimental|beta|stable|production)
            limit: Maximum number of results

        Returns:
            List of recommended procedures
        """
        quality_map = {
            "experimental": 0,
            "beta": 1,
            "stable": 2,
            "production": 3,
        }
        min_quality = quality_map.get(quality_threshold, 2)
        quality_values = {"experimental": 0, "beta": 1, "stable": 2, "production": 3}

        all_procedures = list(self.store._procedures.values())

        # Filter and sort by quality and success rate
        procedures = [
            p for p in all_procedures
            if quality_values.get(p.metadata.quality_level.value, 0) >= min_quality
        ]
        procedures.sort(
            key=lambda p: (
                quality_values.get(p.metadata.quality_level.value, 0),
                p.metadata.success_rate,
            ),
            reverse=True,
        )

        return procedures[:limit]

    def _get_procedure_embedding(self, procedure: MarketplaceProcedure) -> Optional[List[float]]:
        """Get or compute embedding for procedure.

        Args:
            procedure: Procedure object

        Returns:
            Embedding vector or None
        """
        proc_id = procedure.metadata.procedure_id

        # Check cache
        if proc_id in self.procedure_cache:
            return self.procedure_cache[proc_id]

        if not self.embedding_model:
            return None

        # Compute embedding from procedure metadata and description
        text = f"{procedure.metadata.name} {procedure.metadata.description} {' '.join(procedure.metadata.tags)}"

        try:
            embedding = self.embedding_model.embed(text)
            self.procedure_cache[proc_id] = embedding
            return embedding
        except (AttributeError, ValueError, TypeError, KeyError):
            return None

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score (0.0-1.0)
        """
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _keyword_search(
        self,
        query: str,
        limit: int = 10,
    ) -> List[tuple[MarketplaceProcedure, float]]:
        """Fallback keyword search when embedding model unavailable.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of (procedure, relevance_score) tuples
        """
        query_lower = query.lower()
        all_procedures = list(self.store._procedures.values())

        results = []
        for procedure in all_procedures:
            # Calculate keyword relevance score
            name_match = query_lower in procedure.metadata.name.lower()
            desc_match = query_lower in procedure.metadata.description.lower()
            tags_match = any(query_lower in tag.lower() for tag in procedure.metadata.tags)

            relevance = (1.0 if name_match else 0) + (0.5 if desc_match else 0) + (0.3 if tags_match else 0)

            if relevance > 0:
                results.append((procedure, relevance))

        # Sort by relevance
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:limit]

    def clear_cache(self):
        """Clear embedding cache."""
        self.procedure_cache.clear()
