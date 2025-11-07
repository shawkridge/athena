"""Multi-modal RAG integration for semantic code search.

This module integrates code analysis with retrieval-augmented generation (RAG)
to enable advanced semantic search combining multiple signals:
- Semantic similarity (embeddings)
- Structural similarity (code patterns)
- Temporal relevance (recent changes)
- Network centrality (important entities)
"""

import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.athena.code_search.symbol_extractor import Symbol, SymbolIndex
from src.athena.code_search.code_chunker import Chunk
from src.athena.code_search.code_embeddings import CodeEmbeddingManager
from src.athena.code_search.code_graph_integration import CodeGraphBuilder, CodeEntity
from src.athena.code_search.code_temporal_analysis import CodeChangeTracker

logger = logging.getLogger(__name__)


class SearchStrategy(Enum):
    """Search strategies for retrieval."""
    SEMANTIC = "semantic"           # Pure embedding similarity
    STRUCTURAL = "structural"       # Code structure matching
    TEMPORAL = "temporal"           # Recent changes + quality
    HYBRID = "hybrid"              # Combine all signals
    CUSTOM = "custom"              # User-defined weights


@dataclass
class SearchResult:
    """Represents a search result."""
    entity_name: str
    entity_type: str
    file_path: str
    line_number: int
    semantic_score: float = 0.0    # Embedding similarity (0-1)
    structural_score: float = 0.0  # Pattern matching (0-1)
    temporal_score: float = 0.0    # Recency + quality (0-1)
    centrality_score: float = 0.0  # Network importance (0-1)
    combined_score: float = 0.0    # Final ranking score
    content_preview: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entity_name": self.entity_name,
            "entity_type": self.entity_type,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "semantic_score": self.semantic_score,
            "structural_score": self.structural_score,
            "temporal_score": self.temporal_score,
            "centrality_score": self.centrality_score,
            "combined_score": self.combined_score,
            "content_preview": self.content_preview,
            "context": self.context,
        }


@dataclass
class SearchQuery:
    """Represents a semantic search query."""
    query_text: str
    query_type: str = "general"  # general, function, class, pattern, etc.
    strategy: SearchStrategy = SearchStrategy.HYBRID
    top_k: int = 10
    threshold: float = 0.3  # Minimum combined score
    filters: Dict[str, Any] = field(default_factory=dict)  # Entity type, file, etc.
    weights: Dict[str, float] = field(default_factory=dict)  # Custom scoring weights
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize default weights."""
        if not self.weights:
            if self.strategy == SearchStrategy.SEMANTIC:
                self.weights = {"semantic": 1.0, "structural": 0.0, "temporal": 0.0, "centrality": 0.0}
            elif self.strategy == SearchStrategy.STRUCTURAL:
                self.weights = {"semantic": 0.0, "structural": 1.0, "temporal": 0.0, "centrality": 0.0}
            elif self.strategy == SearchStrategy.TEMPORAL:
                self.weights = {"semantic": 0.2, "structural": 0.2, "temporal": 0.6, "centrality": 0.0}
            else:  # HYBRID
                self.weights = {"semantic": 0.4, "structural": 0.3, "temporal": 0.2, "centrality": 0.1}


class CodeRAGRetriever:
    """Retrieves code using multi-modal RAG."""

    def __init__(
        self,
        symbol_index: SymbolIndex,
        graph_builder: CodeGraphBuilder,
        embedding_manager: CodeEmbeddingManager,
        change_tracker: CodeChangeTracker,
    ):
        """Initialize retriever."""
        self.symbol_index = symbol_index
        self.graph_builder = graph_builder
        self.embedding_manager = embedding_manager
        self.change_tracker = change_tracker
        self.cached_embeddings: Dict[str, List[float]] = {}
        self.cached_results: Dict[str, List[SearchResult]] = {}

    def search(self, query: SearchQuery) -> List[SearchResult]:
        """Execute semantic search with RAG."""
        # Generate query embedding
        query_embedding = self.embedding_manager.embed(query.query_text)
        self.cached_embeddings[query.query_text] = query_embedding

        # Get candidate symbols
        candidates = self._get_candidates(query)

        # Score candidates using multiple signals
        results = []
        for candidate in candidates:
            result = self._score_candidate(candidate, query, query_embedding)
            if result.combined_score >= query.threshold:
                results.append(result)

        # Sort by combined score
        results.sort(key=lambda r: r.combined_score, reverse=True)

        # Return top-k
        return results[: query.top_k]

    def search_by_pattern(self, pattern_name: str, top_k: int = 10) -> List[SearchResult]:
        """Search for code matching a specific pattern."""
        query = SearchQuery(
            query_text=pattern_name,
            query_type="pattern",
            strategy=SearchStrategy.STRUCTURAL,
            top_k=top_k,
        )
        return self.search(query)

    def search_by_complexity(
        self, min_complexity: int = 3, max_complexity: int = 10, top_k: int = 10
    ) -> List[SearchResult]:
        """Search for functions with specific complexity range."""
        symbols = self.symbol_index.get_all()
        candidates = [
            s for s in symbols
            if min_complexity <= s.complexity <= max_complexity
        ]

        results = []
        for symbol in candidates[:top_k]:
            entity = self.graph_builder.get_entity(symbol.name)
            result = SearchResult(
                entity_name=symbol.name,
                entity_type=symbol.type.value,
                file_path=symbol.file_path,
                line_number=symbol.line_number,
                structural_score=min(symbol.complexity / 10.0, 1.0),
                content_preview=symbol.docstring or symbol.signature,
            )
            results.append(result)

        return results

    def search_related_entities(self, entity_name: str, top_k: int = 10) -> List[SearchResult]:
        """Find entities related to given entity."""
        entity = self.graph_builder.get_entity(entity_name)
        if not entity:
            return []

        # Get related entities from graph
        related = self.graph_builder.get_related_entities(entity_name)

        results = []
        for related_name in related[:top_k]:
            related_entity = self.graph_builder.get_entity(related_name)
            if related_entity:
                result = SearchResult(
                    entity_name=related_entity.name,
                    entity_type=related_entity.entity_type.value,
                    file_path=related_entity.file_path,
                    line_number=related_entity.line_number,
                    structural_score=0.9,  # High score for direct relationships
                )
                results.append(result)

        return results

    def _get_candidates(self, query: SearchQuery) -> List[Symbol]:
        """Get candidate symbols based on query filters."""
        candidates = self.symbol_index.search(query.query_text)

        # Apply filters
        if "entity_type" in query.filters:
            entity_type = query.filters["entity_type"]
            candidates = [s for s in candidates if s.type.value == entity_type]

        if "file_path" in query.filters:
            file_path = query.filters["file_path"]
            candidates = [s for s in candidates if s.file_path == file_path]

        if "min_complexity" in query.filters:
            min_complexity = query.filters["min_complexity"]
            candidates = [s for s in candidates if s.complexity >= min_complexity]

        return candidates

    def _score_candidate(
        self,
        candidate: Symbol,
        query: SearchQuery,
        query_embedding: List[float],
    ) -> SearchResult:
        """Score a candidate using multiple signals."""
        # Semantic score: embedding similarity
        semantic_score = self._calculate_semantic_score(candidate, query_embedding)

        # Structural score: pattern and complexity matching
        structural_score = self._calculate_structural_score(candidate, query)

        # Temporal score: recency and stability
        temporal_score = self._calculate_temporal_score(candidate)

        # Centrality score: network importance
        centrality_score = self._calculate_centrality_score(candidate)

        # Combine scores with weights
        weights = query.weights
        combined_score = (
            semantic_score * weights.get("semantic", 0.4)
            + structural_score * weights.get("structural", 0.3)
            + temporal_score * weights.get("temporal", 0.2)
            + centrality_score * weights.get("centrality", 0.1)
        )

        return SearchResult(
            entity_name=candidate.name,
            entity_type=candidate.type.value,
            file_path=candidate.file_path,
            line_number=candidate.line_number,
            semantic_score=semantic_score,
            structural_score=structural_score,
            temporal_score=temporal_score,
            centrality_score=centrality_score,
            combined_score=combined_score,
            content_preview=candidate.docstring or candidate.signature,
            context={
                "complexity": candidate.complexity,
                "dependencies": candidate.dependencies,
            },
        )

    def _calculate_semantic_score(
        self, candidate: Symbol, query_embedding: List[float]
    ) -> float:
        """Calculate semantic similarity score."""
        # Get or generate candidate embedding
        cache_key = f"{candidate.name}:{candidate.file_path}"
        if cache_key not in self.cached_embeddings:
            text = f"{candidate.name} {candidate.docstring or ''} {candidate.signature or ''}"
            self.cached_embeddings[cache_key] = self.embedding_manager.embed(text)

        candidate_embedding = self.cached_embeddings[cache_key]

        # Calculate cosine similarity
        similarity = self._cosine_similarity(query_embedding, candidate_embedding)
        return max(0.0, min(similarity, 1.0))  # Clamp to 0-1

    def _calculate_structural_score(self, candidate: Symbol, query: SearchQuery) -> float:
        """Calculate structural matching score."""
        score = 0.0

        # Match on entity type
        if "entity_type" in query.filters:
            if candidate.type.value == query.filters["entity_type"]:
                score += 0.5

        # Match on complexity range
        if "min_complexity" in query.filters or "max_complexity" in query.filters:
            min_c = query.filters.get("min_complexity", 0)
            max_c = query.filters.get("max_complexity", 10)
            if min_c <= candidate.complexity <= max_c:
                score += 0.5

        # Match on query type
        if query.query_type in candidate.name.lower():
            score += 0.3

        return min(score, 1.0)

    def _calculate_temporal_score(self, candidate: Symbol) -> float:
        """Calculate temporal relevance score."""
        # Get change history
        history = self.change_tracker.get_entity_history(candidate.name)
        if not history:
            return 0.3  # Low score for unchanged code

        # Recency: recent changes = higher score
        if history:
            latest_change = max(h.timestamp for h in history)
            days_since = (datetime.now() - latest_change).days
            recency_score = max(0.0, 1.0 - (days_since / 365.0))  # 1 year decay
        else:
            recency_score = 0.0

        # Stability: less churn = higher score
        change_frequency = self.change_tracker.calculate_change_frequency(candidate.name)
        stability = 1.0 / (1.0 + change_frequency)

        return recency_score * 0.5 + stability * 0.5

    def _calculate_centrality_score(self, candidate: Symbol) -> float:
        """Calculate network centrality score."""
        entity = self.graph_builder.get_entity(candidate.name)
        if not entity:
            return 0.0

        # Count relationships
        outgoing = len(self.graph_builder.get_relationships_from(candidate.name))
        incoming = len(self.graph_builder.get_relationships_to(candidate.name))

        # Normalize to 0-1
        total_relationships = max(outgoing + incoming, 1)
        max_possible = 20  # Threshold for high centrality
        centrality = min(total_relationships / max_possible, 1.0)

        return centrality

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)


class CodeRAGPipeline:
    """Full RAG pipeline for code search and retrieval."""

    def __init__(self, retriever: CodeRAGRetriever):
        """Initialize pipeline."""
        self.retriever = retriever
        self.search_history: List[Tuple[SearchQuery, List[SearchResult]]] = []

    def execute_query(self, query_text: str, strategy: SearchStrategy = SearchStrategy.HYBRID) -> List[SearchResult]:
        """Execute a search query."""
        query = SearchQuery(
            query_text=query_text,
            strategy=strategy,
        )
        results = self.retriever.search(query)
        self.search_history.append((query, results))
        return results

    def execute_advanced_query(
        self,
        query_text: str,
        entity_type: Optional[str] = None,
        min_complexity: Optional[int] = None,
        strategy: SearchStrategy = SearchStrategy.HYBRID,
    ) -> List[SearchResult]:
        """Execute advanced query with filters."""
        filters = {}
        if entity_type:
            filters["entity_type"] = entity_type
        if min_complexity is not None:
            filters["min_complexity"] = min_complexity

        query = SearchQuery(
            query_text=query_text,
            strategy=strategy,
            filters=filters,
        )
        results = self.retriever.search(query)
        self.search_history.append((query, results))
        return results

    def find_similar_code(self, entity_name: str, top_k: int = 5) -> List[SearchResult]:
        """Find code similar to a given entity."""
        return self.retriever.search_related_entities(entity_name, top_k)

    def find_by_complexity(
        self, min_complexity: int = 3, max_complexity: int = 10, top_k: int = 10
    ) -> List[SearchResult]:
        """Find functions by complexity range."""
        return self.retriever.search_by_complexity(min_complexity, max_complexity, top_k)

    def get_search_analytics(self) -> Dict[str, Any]:
        """Get analytics from search history."""
        if not self.search_history:
            return {}

        return {
            "total_searches": len(self.search_history),
            "strategies_used": list(set(q.strategy.value for q, _ in self.search_history)),
            "avg_results": sum(len(r) for _, r in self.search_history) / len(self.search_history),
            "avg_top_score": sum(
                max((r.combined_score for r in results), default=0)
                for _, results in self.search_history
            ) / len(self.search_history),
        }

    def generate_rag_report(self) -> str:
        """Generate report on RAG retrieval performance."""
        analytics = self.get_search_analytics()

        report = "RAG RETRIEVAL REPORT\n"
        report += "=" * 50 + "\n\n"
        report += f"Total Searches: {analytics.get('total_searches', 0)}\n"
        report += f"Average Results per Query: {analytics.get('avg_results', 0):.1f}\n"
        report += f"Average Top Score: {analytics.get('avg_top_score', 0):.2f}\n"

        strategies = analytics.get("strategies_used", [])
        if strategies:
            report += f"Strategies Used: {', '.join(strategies)}\n"

        return report
