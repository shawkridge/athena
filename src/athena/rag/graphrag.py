"""GraphRAG - Graph-Based Retrieval Augmented Generation.

Implements retrieval strategies using knowledge graph communities for both
high-level global questions and targeted local deep-dives.

Reference: Microsoft GraphRAG
https://github.com/microsoft/graphrag
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field

from ..graph.store import GraphStore
from ..rag.manager import RAGManager
from ..core.models import Memory

logger = logging.getLogger(__name__)


@dataclass
class CommunitySummary:
    """Summary of a knowledge graph community."""

    community_id: int
    name: str
    summary_text: str
    summary_tokens: int
    key_entities: List[str] = field(default_factory=list)
    key_relations: List[str] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    # Relevance tracking
    relevance_score: Optional[float] = None
    query_used_for: Optional[str] = None


@dataclass
class RetrievalResult:
    """Result from GraphRAG retrieval."""

    documents: List[Memory]
    source: str  # "global", "local", "hybrid"
    relevance_scores: Dict[int, float] = field(default_factory=dict)
    confidence: float = 1.0
    community_ids: List[int] = field(default_factory=list)

    reasoning: Optional[str] = None


class GraphRAGManager:
    """GraphRAG implementation using existing graph layer.

    Supports:
    - Global search: Answer broad questions using community summaries
    - Local search: Deep dive into specific knowledge areas
    - Hybrid search: Combine semantic, graph, and text-based retrieval
    """

    def __init__(self,
                 graph_store: GraphStore,
                 semantic_search: RAGManager,
                 llm_client=None):
        """Initialize GraphRAG manager.

        Args:
            graph_store: GraphStore instance for entity/relation queries
            semantic_search: RAGManager for semantic search
            llm_client: Optional LLM client for summarization/reasoning
        """
        self.graph = graph_store
        self.semantic = semantic_search
        self.llm = llm_client

        # Cache community summaries
        self._community_summaries: Dict[int, CommunitySummary] = {}
        self._last_update = None

    # ========== Global Search ==========

    def global_search(self, query: str, top_k: int = 5, project_id: int = 1) -> RetrievalResult:
        """Answer high-level questions using community summaries.

        Approach:
        1. Get all community summaries
        2. Rank by relevance to query
        3. Generate answer from top summaries
        4. Return with source tracking

        Args:
            query: User question
            top_k: Number of top communities to use (default: 5)
            project_id: Project context for memory objects (default: 1)

        Returns:
            RetrievalResult with global perspective
        """
        logger.info(f"Global search: {query[:80]} (project={project_id})")

        # Get all community summaries (lazy-load if needed)
        summaries = self._get_all_summaries()

        if not summaries:
            logger.warning("No community summaries available for global search")
            return RetrievalResult(
                documents=[],
                source="global",
                reasoning="No knowledge graph communities found"
            )

        # Rank summaries by relevance
        ranked_summaries = self._rank_summaries(query, summaries, top_k)

        # Build context from top summaries
        context_text = self._build_global_context(ranked_summaries)

        # Generate reasoning about communities
        reasoning = f"Using summaries from {len(ranked_summaries)} key knowledge areas"

        # Convert summaries to Memory objects for return
        memory_results = []
        community_ids = []
        relevance_map = {}

        for i, summary in enumerate(ranked_summaries):
            memory = Memory(
                id=f"community_{summary.community_id}",
                project_id=project_id,
                content=summary.summary_text,
                memory_type="summary",
                tags=[summary.name, "community_summary", "global"]
            )
            memory_results.append(memory)
            community_ids.append(summary.community_id)
            relevance_map[summary.community_id] = summary.relevance_score or 0.0

        return RetrievalResult(
            documents=memory_results,
            source="global",
            relevance_scores=relevance_map,
            confidence=0.9,
            community_ids=community_ids,
            reasoning=reasoning
        )

    # ========== Local Search ==========

    def local_search(self, query: str,
                    community_id: Optional[int] = None,
                    max_hops: int = 2,
                    top_k: int = 10) -> RetrievalResult:
        """Deep dive into specific knowledge area.

        Approach:
        1. Find most relevant community if not specified
        2. Get entities in that community
        3. Expand to nearby entities (multi-hop)
        4. Rank and return most relevant

        Args:
            query: User question (for relevance scoring)
            community_id: Optional specific community to search
            max_hops: How many relationships to traverse (default: 2)
            top_k: Number of top entities to return (default: 10)

        Returns:
            RetrievalResult focused on specific knowledge area
        """
        logger.info(f"Local search: {query[:80]}, community={community_id}")

        # Find community if not specified
        if not community_id:
            community_id = self._find_relevant_community(query)
            if not community_id:
                logger.warning("Could not find relevant community for local search")
                return RetrievalResult(
                    documents=[],
                    source="local",
                    reasoning="No relevant knowledge area found"
                )

        # Get entities in community with multi-hop expansion
        entities = self._get_community_entities_with_expansion(
            community_id, max_hops
        )

        # Rank by relevance to query
        ranked_entities = self._rank_entities(query, entities, top_k)

        # Build result
        memory_results = []
        relevance_map = {}

        for entity in ranked_entities:
            # Create memory from entity
            memory = Memory(
                id=f"entity_{entity['id']}",
                project_id=1,
                content=self._entity_to_text(entity),
                memory_type="entity",
                tags=["local_search", entity.get('type', 'unknown')]
            )
            memory_results.append(memory)
            relevance_map[entity['id']] = entity.get('relevance', 0.5)

        reasoning = f"Deep dive into '{self._get_community_name(community_id)}' knowledge area"

        return RetrievalResult(
            documents=memory_results,
            source="local",
            relevance_scores=relevance_map,
            confidence=0.85,
            community_ids=[community_id],
            reasoning=reasoning
        )

    # ========== Hybrid Search ==========

    def hybrid_search(self, query: str,
                     use_global: bool = True,
                     use_local: bool = True,
                     use_semantic: bool = True,
                     weights: Optional[Dict[str, float]] = None) -> RetrievalResult:
        """Combine semantic, graph, and BM25 retrieval.

        Fusion approach:
        1. Global search (community summaries)
        2. Local search (multi-hop entity expansion)
        3. Semantic search (embedding-based)
        4. Weighted fusion of results

        Args:
            query: User question
            use_global: Include global search (default: True)
            use_local: Include local search (default: True)
            use_semantic: Include semantic search (default: True)
            weights: Custom weights for fusion (default: equal weights)
                     e.g., {"global": 0.3, "local": 0.3, "semantic": 0.4}

        Returns:
            RetrievalResult combining all strategies
        """
        logger.info(f"Hybrid search: {query[:80]}")

        # Set default weights
        if not weights:
            weights = {
                "global": 0.25,
                "local": 0.25,
                "semantic": 0.5
            }

        all_results = []
        relevance_scores = {}
        sources_used = []

        # Global search
        if use_global and weights.get("global", 0) > 0:
            global_result = self.global_search(query, top_k=5)
            all_results.extend(global_result.documents)
            sources_used.append("global")

            # Weight relevance scores
            for doc_id, score in global_result.relevance_scores.items():
                relevance_scores[f"global_{doc_id}"] = score * weights["global"]

        # Local search
        if use_local and weights.get("local", 0) > 0:
            local_result = self.local_search(query, top_k=5)
            all_results.extend(local_result.documents)
            sources_used.append("local")

            # Weight relevance scores
            for doc_id, score in local_result.relevance_scores.items():
                relevance_scores[f"local_{doc_id}"] = score * weights["local"]

        # Semantic search
        if use_semantic and weights.get("semantic", 0) > 0:
            semantic_results = self.semantic.recall(query, top_k=10)
            for result in semantic_results:
                all_results.append(result.memory)
                relevance_scores[f"semantic_{result.memory.id}"] = \
                    result.similarity * weights["semantic"]
            sources_used.append("semantic")

        # Deduplicate and rerank
        unique_docs = {}
        for doc in all_results:
            if doc.id not in unique_docs:
                unique_docs[doc.id] = doc

        # Return fused results
        reasoning = f"Hybrid search combining {', '.join(sources_used)}"

        return RetrievalResult(
            documents=list(unique_docs.values()),
            source="hybrid",
            relevance_scores=relevance_scores,
            confidence=0.88,
            reasoning=reasoning
        )

    # ========== Helper Methods ==========

    def _get_all_summaries(self) -> List[CommunitySummary]:
        """Get all community summaries (with caching)."""
        if self._community_summaries:
            return list(self._community_summaries.values())

        # Lazy-load summaries from graph
        try:
            communities = self.graph.get_communities()
            summaries = []

            for community in communities:
                summary = CommunitySummary(
                    community_id=community.get('id'),
                    name=community.get('name', f"Community {community.get('id')}"),
                    summary_text=community.get('summary',
                        f"Knowledge area focused on {community.get('topic', 'general topics')}")
                )
                summaries.append(summary)
                self._community_summaries[summary.community_id] = summary

            return summaries
        except Exception as e:
            logger.error(f"Error loading community summaries: {e}")
            return []

    def _rank_summaries(self, query: str,
                       summaries: List[CommunitySummary],
                       top_k: int) -> List[CommunitySummary]:
        """Rank summaries by relevance to query."""
        if not summaries:
            return []

        # Score each summary (TODO: use more sophisticated ranking)
        scored = []
        for summary in summaries:
            # Simple keyword matching for now
            score = self._compute_relevance(query, summary.summary_text)
            summary.relevance_score = score
            scored.append(summary)

        # Sort and return top-k
        sorted_summaries = sorted(scored, key=lambda x: x.relevance_score or 0,
                                 reverse=True)
        return sorted_summaries[:top_k]

    def _rank_entities(self, query: str,
                      entities: List[Dict],
                      top_k: int) -> List[Dict]:
        """Rank entities by relevance to query."""
        if not entities:
            return []

        scored = []
        for entity in entities:
            score = self._compute_relevance(
                query,
                f"{entity.get('name', '')} {entity.get('description', '')}"
            )
            entity['relevance'] = score
            scored.append(entity)

        sorted_entities = sorted(scored, key=lambda x: x.get('relevance', 0),
                                reverse=True)
        return sorted_entities[:top_k]

    def _compute_relevance(self, query: str, text: str) -> float:
        """Compute relevance score between query and text.

        Simple implementation - can be enhanced with semantic similarity.
        """
        if not text:
            return 0.0

        # Simple keyword overlap (TODO: use embeddings)
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())

        overlap = len(query_words & text_words)
        total = len(query_words | text_words)

        return overlap / total if total > 0 else 0.0

    def _find_relevant_community(self, query: str) -> Optional[int]:
        """Find most relevant community for query."""
        summaries = self._get_all_summaries()
        if not summaries:
            return None

        best_community = None
        best_score = 0

        for summary in summaries:
            score = self._compute_relevance(query, summary.summary_text)
            if score > best_score:
                best_score = score
                best_community = summary.community_id

        return best_community

    def _get_community_entities_with_expansion(self,
                                              community_id: int,
                                              max_hops: int) -> List[Dict]:
        """Get entities in community with multi-hop expansion."""
        try:
            entities = self.graph.get_community_entities(community_id)
            expanded = list(entities) if entities else []

            # Multi-hop expansion
            visited = set([e.get('id') for e in expanded])
            frontier = list(expanded)

            for _ in range(max_hops - 1):
                next_frontier = []
                for entity in frontier:
                    neighbors = self.graph.get_neighbors(entity.get('id'), max_hops=1)
                    for neighbor in neighbors:
                        if neighbor.get('id') not in visited:
                            visited.add(neighbor.get('id'))
                            expanded.append(neighbor)
                            next_frontier.append(neighbor)
                frontier = next_frontier

            return expanded
        except Exception as e:
            logger.error(f"Error expanding community entities: {e}")
            return []

    def _build_global_context(self, summaries: List[CommunitySummary]) -> str:
        """Build context from top summaries."""
        parts = []
        for summary in summaries:
            parts.append(f"## {summary.name}\n{summary.summary_text}")
        return "\n\n".join(parts)

    def _entity_to_text(self, entity: Dict) -> str:
        """Convert entity to text for Memory object."""
        parts = []
        if entity.get('name'):
            parts.append(f"**{entity['name']}**")
        if entity.get('description'):
            parts.append(entity['description'])
        if entity.get('type'):
            parts.append(f"Type: {entity['type']}")
        return "\n".join(parts)

    def _get_community_name(self, community_id: int) -> str:
        """Get display name for community."""
        summary = self._community_summaries.get(community_id)
        return summary.name if summary else f"Community {community_id}"

    # ========== Management Methods ==========

    def update_community_summary(self, community_id: int,
                                summary_text: str) -> None:
        """Update summary for a community."""
        if community_id in self._community_summaries:
            self._community_summaries[community_id].summary_text = summary_text
            self._community_summaries[community_id].last_updated = datetime.now()
            logger.info(f"Updated summary for community {community_id}")

    def clear_summary_cache(self) -> None:
        """Clear cached summaries to force refresh."""
        self._community_summaries.clear()
        self._last_update = None
        logger.info("Cleared community summary cache")

    def get_stats(self) -> Dict:
        """Get statistics about GraphRAG system."""
        summaries = self._get_all_summaries()
        return {
            "num_communities": len(summaries),
            "cached_summaries": len(self._community_summaries),
            "avg_summary_length": sum(s.summary_tokens for s in summaries) / len(summaries) if summaries else 0,
            "last_cache_update": self._last_update
        }
