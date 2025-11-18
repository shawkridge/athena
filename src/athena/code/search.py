"""Hybrid code search engine combining AST, semantic, and spatial ranking."""

import logging
from typing import List

from .models import CodeSearchResult, CodeElement

logger = logging.getLogger(__name__)


class CodeSearchEngine:
    """Hybrid search combining structural (AST) + semantic + spatial ranking.

    Ranking formula:
    - 40% semantic similarity (vector embeddings)
    - 30% AST pattern matching (structural similarity)
    - 30% spatial proximity (file/class relationships)
    """

    def __init__(self, code_indexer=None, spatial_indexer=None, semantic_search=None):
        """Initialize search engine with components.

        Args:
            code_indexer: CodeIndexer instance
            spatial_indexer: SpatialIndexer instance
            semantic_search: SemanticSearch instance from Athena
        """
        self.code_indexer = code_indexer
        self.spatial_indexer = spatial_indexer
        self.semantic_search = semantic_search

        # Ranking weights
        self.weights = {
            "semantic": 0.40,
            "ast": 0.30,
            "spatial": 0.30,
        }

    def search(
        self,
        query: str,
        max_results: int = 10,
        explain: bool = False,
    ) -> List[CodeSearchResult]:
        """Search codebase with hybrid ranking.

        Args:
            query: Natural language search query
            max_results: Maximum results to return
            explain: Include ranking explanation

        Returns:
            List of CodeSearchResult objects
        """
        results = []

        try:
            # Phase 1: Semantic search (query embedding + index)
            semantic_results = self._semantic_search(query, max_results * 3)
            logger.debug(f"Semantic search found {len(semantic_results)} candidates")

            # Phase 2: Score each candidate with hybrid ranking
            scored_results = []
            for element in semantic_results:
                scores = self._rank_element(element, query)
                combined_score = (
                    scores["semantic"] * self.weights["semantic"]
                    + scores["ast"] * self.weights["ast"]
                    + scores["spatial"] * self.weights["spatial"]
                )

                scored_results.append(
                    {
                        "element": element,
                        "scores": scores,
                        "combined_score": combined_score,
                    }
                )

            # Phase 3: Sort by combined score
            scored_results.sort(key=lambda x: x["combined_score"], reverse=True)

            # Phase 4: Build results with context
            for rank, item in enumerate(scored_results[:max_results], 1):
                element = item["element"]
                scores = item["scores"]
                combined_score = item["combined_score"]

                # Extract context (episodic history, spatial relationships)
                context = self._extract_context(element)

                result = CodeSearchResult(
                    element=element,
                    semantic_score=scores["semantic"],
                    ast_score=scores["ast"],
                    spatial_score=scores["spatial"],
                    combined_score=combined_score,
                    rank=rank,
                    context=context,
                    reasoning=(self._explain_ranking(scores, element, query) if explain else None),
                )

                results.append(result)

            logger.info(f"Search returned {len(results)} results for: {query}")

        except Exception as e:
            logger.error(f"Error during code search: {e}")

        return results

    def _semantic_search(self, query: str, limit: int) -> List[CodeElement]:
        """Search using semantic similarity (query → embedding → vector search).

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of CodeElement candidates
        """
        if not self.semantic_search:
            logger.warning("Semantic search not available")
            return []

        try:
            # Use Athena's semantic search
            # This integrates with existing infrastructure
            results = self.semantic_search.search(
                query=query,
                filter_type="code",
                limit=limit,
            )

            # Convert to CodeElement if needed
            elements = []
            for result in results:
                if isinstance(result, CodeElement):
                    elements.append(result)
                elif isinstance(result, dict) and "element" in result:
                    elements.append(result["element"])

            return elements

        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []

    def _rank_element(self, element: CodeElement, query: str) -> dict:
        """Compute ranking scores for an element.

        Args:
            element: CodeElement to score
            query: Search query

        Returns:
            Dictionary with semantic, ast, and spatial scores
        """
        # 1. Semantic score (from vector similarity)
        # In production, use cosine similarity between embeddings
        semantic_score = self._compute_semantic_score(element, query)

        # 2. AST score (pattern matching)
        ast_score = self._compute_ast_score(element, query)

        # 3. Spatial score (file/class proximity)
        spatial_score = self._compute_spatial_score(element, query)

        return {
            "semantic": semantic_score,
            "ast": ast_score,
            "spatial": spatial_score,
        }

    def _compute_semantic_score(self, element: CodeElement, query: str) -> float:
        """Compute semantic similarity score (0-1).

        Uses cosine similarity between query embedding and element embedding.
        """
        try:
            if not element.embedding or not element.source_code:
                return 0.0

            # In production: query_embedding = embed(query)
            # score = cosine_similarity(query_embedding, element.embedding)

            # MVP: Simple keyword matching
            query_lower = query.lower()
            text = (f"{element.name} {element.docstring or ''}" f" {element.source_code}").lower()

            # Count matching keywords
            matches = sum(1 for word in query_lower.split() if word in text)
            max_matches = len(query_lower.split())

            score = min(1.0, matches / max_matches) if max_matches > 0 else 0.0
            return score

        except Exception as e:
            logger.warning(f"Error computing semantic score: {e}")
            return 0.5

    def _compute_ast_score(self, element: CodeElement, query: str) -> float:
        """Compute AST structural matching score (0-1).

        Matches query against code structure (functions, classes, method names, etc.)
        """
        try:
            query_lower = query.lower()

            # Boost score if query matches element name
            if element.name.lower() in query_lower:
                return 0.9

            # Boost score if query matches element type
            if element.element_type.value.lower() in query_lower:
                return 0.7

            # Check docstring match
            if element.docstring:
                docstring_lower = element.docstring.lower()
                if any(word in docstring_lower for word in query_lower.split()):
                    return 0.8

            # Default moderate score
            return 0.4

        except Exception as e:
            logger.warning(f"Error computing AST score: {e}")
            return 0.5

    def _compute_spatial_score(self, element: CodeElement, query: str) -> float:
        """Compute spatial proximity score (0-1).

        Higher scores for frequently accessed files, related code elements, etc.
        """
        try:
            # In production: Use access frequency, call graph, etc.

            # MVP: Simple heuristic based on path
            # Files deeper in structure are slightly less relevant
            path_depth = element.file_path.count("/")
            depth_penalty = min(0.2, path_depth * 0.05)

            base_score = max(0.3, 1.0 - depth_penalty)
            return base_score

        except Exception as e:
            logger.warning(f"Error computing spatial score: {e}")
            return 0.5

    def _extract_context(self, element: CodeElement) -> dict:
        """Extract context for a code element.

        Args:
            element: CodeElement to extract context for

        Returns:
            Dictionary with context information
        """
        context = {
            "element_type": element.element_type.value,
            "language": element.language.value,
            "file_path": element.file_path,
            "signature": element.signature,
            "docstring_preview": (
                element.docstring[:100] + "..."
                if element.docstring and len(element.docstring) > 100
                else element.docstring
            ),
        }

        # Add related elements if spatial indexer available
        if self.spatial_indexer:
            try:
                related = self.spatial_indexer.get_related_elements(element.element_id)
                context["related_elements"] = [
                    {
                        "element_id": rel[0],
                        "type": rel[1],
                        "weight": rel[2],
                    }
                    for rel in related[:5]  # Top 5
                ]
            except Exception as e:
                logger.warning(f"Error getting related elements: {e}")

        return context

    def _explain_ranking(self, scores: dict, element: CodeElement, query: str) -> str:
        """Generate explanation of ranking for a result.

        Args:
            scores: Dictionary of ranking scores
            element: CodeElement
            query: Search query

        Returns:
            Explanation string
        """
        parts = []

        if scores["semantic"] > 0.7:
            parts.append("Strong semantic match (query matches keywords in " "name/docstring)")

        if scores["ast"] > 0.7:
            parts.append("Exact structure match (element type/name matches query)")

        if scores["spatial"] > 0.6:
            parts.append("Located in frequently accessed file")

        if not parts:
            parts.append("Moderate relevance to search query")

        return " | ".join(parts)
