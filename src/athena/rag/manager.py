"""RAG Manager - orchestrates all advanced RAG techniques."""

import logging
from typing import Optional

from ..core.models import MemorySearchResult
from ..core.database import Database
from ..memory.store import MemoryStore
from ..graph.store import GraphStore
from ..temporal.kg_synthesis import TemporalKGSynthesis
from .hyde import HyDEConfig, HyDERetriever
from .llm_client import LLMClient
from .planning_rag import PlanningRAGRouter
from .query_transform import QueryTransformConfig, QueryTransformer
from .reflective import ReflectiveRAG, ReflectiveRAGConfig
from .reranker import LLMReranker, RerankerConfig
from .temporal_search_enrichment import TemporalSearchEnricher, EnrichedSearchResult

logger = logging.getLogger(__name__)


class RAGStrategy:
    """Available RAG strategies."""

    BASIC = "basic"  # Just vector search
    HYDE = "hyde"  # HyDE for ambiguous queries
    RERANK = "rerank"  # LLM reranking for better relevance
    TRANSFORM = "transform"  # Query transformation for context awareness
    REFLECTIVE = "reflective"  # Iterative refinement
    PLANNING = "planning"  # Planning-aware RAG with pattern recommendations
    AUTO = "auto"  # Automatic strategy selection


class RAGConfig:
    """Configuration for RAG manager."""

    def __init__(
        self,
        hyde_enabled: bool = True,
        reranking_enabled: bool = True,
        query_transform_enabled: bool = True,
        reflective_enabled: bool = False,  # Expensive, opt-in
        planning_enabled: bool = True,  # Planning-aware RAG
        temporal_enrichment_enabled: bool = True,  # P2: Temporal KG in search
        auto_strategy: bool = True,
        hyde_config: Optional[HyDEConfig] = None,
        reranker_config: Optional[RerankerConfig] = None,
        query_transform_config: Optional[QueryTransformConfig] = None,
        reflective_config: Optional[ReflectiveRAGConfig] = None,
    ):
        """Initialize RAG configuration.

        Args:
            hyde_enabled: Enable HyDE for ambiguous queries
            reranking_enabled: Enable LLM-based reranking
            query_transform_enabled: Enable conversation-aware query transformation
            reflective_enabled: Enable self-reflective iterative retrieval (expensive)
            planning_enabled: Enable planning-aware RAG with pattern recommendations
            temporal_enrichment_enabled: Enable temporal KG enrichment in search results (P2)
            auto_strategy: Automatically select best strategy for query
            hyde_config: HyDE configuration (uses defaults if None)
            reranker_config: Reranker configuration (uses defaults if None)
            query_transform_config: Query transform configuration (uses defaults if None)
            reflective_config: Reflective RAG configuration (uses defaults if None)
        """
        self.hyde_enabled = hyde_enabled
        self.reranking_enabled = reranking_enabled
        self.query_transform_enabled = query_transform_enabled
        self.reflective_enabled = reflective_enabled
        self.planning_enabled = planning_enabled
        self.temporal_enrichment_enabled = temporal_enrichment_enabled
        self.auto_strategy = auto_strategy

        # Component configs
        self.hyde_config = hyde_config or HyDEConfig()
        self.reranker_config = reranker_config or RerankerConfig()
        self.query_transform_config = query_transform_config or QueryTransformConfig()
        self.reflective_config = reflective_config or ReflectiveRAGConfig()


class RAGManager:
    """Unified advanced RAG operations manager."""

    def __init__(
        self,
        memory_store: MemoryStore,
        llm_client: Optional[LLMClient] = None,
        config: Optional[RAGConfig] = None,
        planning_store: Optional[object] = None,  # Optional PlanningStore
        db: Optional[Database] = None,  # Optional Database for temporal enrichment
        graph_store: Optional[GraphStore] = None,  # Optional GraphStore for temporal enrichment
        temporal_kg: Optional[TemporalKGSynthesis] = None,  # Optional temporal KG for enrichment
    ):
        """Initialize RAG manager.

        Args:
            memory_store: Memory store for retrieval
            llm_client: LLM client (required for advanced features)
            config: RAG configuration (uses defaults if None)
            planning_store: Optional planning store for planning-aware RAG
            db: Optional database connection for temporal KG enrichment (P2)
            graph_store: Optional graph store for temporal KG enrichment (P2)
            temporal_kg: Optional temporal KG synthesis for enrichment (P2)
        """
        self.store = memory_store
        self.llm = llm_client
        self.config = config or RAGConfig()
        self.planning_store = planning_store
        self.db = db
        self.graph_store = graph_store
        self.temporal_kg = temporal_kg

        # Initialize components if LLM is available
        if self.llm:
            self.hyde = HyDERetriever(memory_store.search, llm_client)
            self.reranker = LLMReranker(llm_client)
            self.query_transformer = QueryTransformer(llm_client)
            self.reflective = ReflectiveRAG(memory_store.search, llm_client)
            # Initialize planning RAG if planning store is available
            if planning_store and self.config.planning_enabled:
                self.planning_rag = PlanningRAGRouter(memory_store, planning_store, llm_client)
            else:
                self.planning_rag = None
        else:
            logger.warning(
                "RAGManager initialized without LLM client. "
                "Advanced features (HyDE, reranking, etc.) will not be available."
            )
            self.hyde = None
            self.reranker = None
            self.query_transformer = None
            self.reflective = None
            self.planning_rag = None

        # Initialize temporal KG enricher if all components available (P2)
        if (
            self.config.temporal_enrichment_enabled
            and self.db
            and self.graph_store
            and self.temporal_kg
        ):
            self.temporal_enricher = TemporalSearchEnricher(
                self.db,
                self.graph_store,
                self.temporal_kg,
            )
            logger.info("Temporal KG search enrichment (P2) enabled")
        else:
            self.temporal_enricher = None
            if self.config.temporal_enrichment_enabled and not (
                self.db and self.graph_store and self.temporal_kg
            ):
                logger.warning(
                    "Temporal enrichment requested but dependencies missing. "
                    "(requires db, graph_store, temporal_kg)"
                )

    async def retrieve(
        self,
        query: str,
        project_id: int,
        k: int = 5,
        strategy: str = RAGStrategy.AUTO,
        conversation_history: Optional[list[dict]] = None,
    ) -> list[MemorySearchResult]:
        """Smart retrieval with automatic or manual strategy selection.

        Args:
            query: User query
            project_id: Project ID
            k: Number of results to return
            strategy: Retrieval strategy ("basic", "hyde", "rerank", "transform", "reflective", "auto")
            conversation_history: Recent conversation messages for context
                Format: [{"role": "user"|"assistant", "content": str}, ...]

        Returns:
            Search results (list of MemorySearchResult)

        Raises:
            ValueError: If advanced strategy requested but LLM client not available
        """
        # Fallback to basic if no LLM
        if not self.llm and strategy != RAGStrategy.BASIC:
            logger.warning(
                f"Strategy '{strategy}' requires LLM client. Falling back to basic search."
            )
            strategy = RAGStrategy.BASIC

        # Auto-select strategy
        if strategy == RAGStrategy.AUTO:
            strategy = self._select_strategy(query, conversation_history)
            logger.info(f"Auto-selected strategy: {strategy}")

        # Execute strategy
        try:
            if strategy == RAGStrategy.PLANNING:
                return await self._retrieve_planning(query, project_id, k)

            elif strategy == RAGStrategy.HYDE:
                return await self._retrieve_hyde(query, project_id, k)

            elif strategy == RAGStrategy.RERANK:
                return await self._retrieve_rerank(query, project_id, k)

            elif strategy == RAGStrategy.TRANSFORM:
                return await self._retrieve_transform(query, project_id, k, conversation_history)

            elif strategy == RAGStrategy.REFLECTIVE:
                return await self._retrieve_reflective(query, project_id, k)

            else:  # BASIC
                return await self._retrieve_basic(query, project_id, k)

        except Exception as e:
            logger.error(f"Error in RAG retrieval (strategy={strategy}): {e}", exc_info=True)
            # Graceful degradation to basic search
            logger.info("Falling back to basic search due to error")
            return await self._retrieve_basic(query, project_id, k)

    def _select_strategy(
        self, query: str, conversation_history: Optional[list[dict]] = None
    ) -> str:
        """Automatically select best retrieval strategy.

        Uses LLM analysis for ambiguous cases, falls back to heuristics.

        Args:
            query: User query
            conversation_history: Recent conversation messages

        Returns:
            Selected strategy name
        """
        if not self.llm:
            return RAGStrategy.BASIC

        # Try LLM-powered analysis for ambiguous cases
        llm_strategy = self._analyze_query_with_llm(query, conversation_history)
        if llm_strategy and llm_strategy != "fallback":
            return llm_strategy

        query_lower = query.lower()

        # Check for planning-related queries (high priority)
        if self.config.planning_enabled and self.planning_rag:
            planning_keywords = {
                "decompose",
                "break down",
                "split",
                "chunk",
                "hierarchical",
                "recursive",
                "planning",
                "strategy",
                "approach",
                "structure",
                "organize",
                "orchestrate",
                "coordinate",
                "validate",
                "verify",
                "pattern",
                "workflow",
                "timeline",
                "estimate",
                "complexity",
            }
            if any(kw in query_lower for kw in planning_keywords):
                logger.info(f"Auto-selected PLANNING strategy for query: {query[:50]}")
                return RAGStrategy.PLANNING

        # Check for reflective scenarios (complex, multi-faceted queries)
        if self.config.reflective_enabled:
            # Multi-part questions or "and" clauses
            if " and " in query_lower or "?" in query and query.count("?") > 1:
                return RAGStrategy.REFLECTIVE

        # Check for context-dependent queries (pronouns, references)
        if self.config.query_transform_enabled and conversation_history:
            pronouns = ["it", "that", "this", "they", "them", "those", "these"]
            implicit = ["the function", "the class", "the file", "previous", "earlier"]
            if any(p in query_lower for p in pronouns + implicit):
                return RAGStrategy.TRANSFORM

        # Check for ambiguous queries (short, vague, "how does X work")
        if self.config.hyde_enabled:
            # Short queries (<5 words) are often ambiguous
            if len(query.split()) < 5:
                return RAGStrategy.HYDE
            # "How does X work" type questions
            if any(
                phrase in query_lower for phrase in ["how does", "how do", "what is", "explain"]
            ):
                return RAGStrategy.HYDE

        # Default to reranking for better relevance scoring
        if self.config.reranking_enabled:
            return RAGStrategy.RERANK

        # Fallback to basic
        return RAGStrategy.BASIC

    def _analyze_query_with_llm(
        self, query: str, conversation_history: Optional[list[dict]] = None
    ) -> Optional[str]:
        """Use LLM to analyze query and recommend optimal RAG strategy.

        This method uses Claude to understand query characteristics when heuristics
        are ambiguous. It's optional and doesn't block retrieval if it fails.

        Args:
            query: User query
            conversation_history: Recent conversation for context

        Returns:
            Recommended strategy name or "fallback" to use heuristics
        """
        if not self.llm:
            return "fallback"

        try:
            import json

            # Build conversation context if available
            context = ""
            if conversation_history and len(conversation_history) > 0:
                recent = (
                    conversation_history[-2:]
                    if len(conversation_history) >= 2
                    else conversation_history
                )
                context = "\nRecent context:\n"
                for msg in recent:
                    context += f"- {msg.get('role', 'user')}: {msg.get('content', '')[:100]}\n"

            prompt = f"""Analyze this user query and recommend the best RAG retrieval strategy.

Query: {query}
{context}

Available strategies:
1. HYDE - For ambiguous, vague, or short queries that need expansion
2. TRANSFORM - For queries with pronouns/references (it, that, this, the function, etc.)
3. PLANNING - For queries about structure, decomposition, timeline, strategy, patterns
4. REFLECTIVE - For complex multi-faceted questions needing iterative refinement
5. RERANK - For straightforward queries needing semantic reranking for relevance
6. BASIC - Simple vector search only

Respond with JSON: {{"strategy": "STRATEGY_NAME", "confidence": 0.0-1.0, "reasoning": "..."}}

Choose the SINGLE best strategy. Default to RERANK if unsure.
"""

            result = self.llm.generate(prompt, max_tokens=150)
            analysis = json.loads(result)

            recommended = analysis.get("strategy", "").upper()
            confidence = float(analysis.get("confidence", 0.5))

            # Only use LLM recommendation if confidence is high
            if confidence >= 0.7 and recommended in [
                RAGStrategy.HYDE,
                RAGStrategy.TRANSFORM,
                RAGStrategy.PLANNING,
                RAGStrategy.REFLECTIVE,
                RAGStrategy.RERANK,
            ]:
                logger.info(
                    f"LLM-selected {recommended} strategy (confidence: {confidence:.0%}): "
                    f"{analysis.get('reasoning', 'N/A')[:80]}"
                )
                return recommended

            return "fallback"

        except Exception as e:
            # LLM analysis failed, use heuristics instead
            logger.debug(f"LLM strategy analysis failed, falling back to heuristics: {e}")
            return "fallback"

    async def _retrieve_planning(
        self, query: str, project_id: int, k: int
    ) -> list[MemorySearchResult]:
        """Planning-aware RAG retrieval."""
        if not self.planning_rag:
            raise ValueError("Planning RAG not available (no planning store)")

        # Route through planning RAG system
        routing_result = self.planning_rag.route_query(query, project_id=project_id)

        # Extract semantic results from hybrid search
        if routing_result.get("hybrid_search_results"):
            hybrid_results = routing_result["hybrid_search_results"]
            results = hybrid_results.semantic_results[:k]

            # Log planning recommendations
            if routing_result.get("pattern_recommendations"):
                patterns = routing_result["pattern_recommendations"]
                for i, rec in enumerate(patterns[:3], 1):
                    logger.info(
                        f"Planning recommendation {i}: {rec.pattern.name} "
                        f"(confidence: {rec.confidence:.2%}, success_rate: {rec.success_rate:.0%})"
                    )

            return results
        else:
            # Fallback to basic search
            return await self.store.recall(query, project_id, k)

    async def _retrieve_basic(
        self, query: str, project_id: int, k: int
    ) -> list[MemorySearchResult]:
        """Basic vector search."""
        return await self.store.recall(query, project_id, k)

    async def _retrieve_hyde(self, query: str, project_id: int, k: int) -> list[MemorySearchResult]:
        """HyDE-enhanced retrieval."""
        if not self.hyde:
            raise ValueError("HyDE not available (no LLM client)")
        return self.hyde.retrieve(query, project_id, k, use_hyde=True)

    async def _retrieve_rerank(
        self, query: str, project_id: int, k: int
    ) -> list[MemorySearchResult]:
        """Retrieval with LLM reranking."""
        if not self.reranker:
            raise ValueError("Reranker not available (no LLM client)")

        # Get more candidates for reranking
        candidates = await self.store.recall(query, project_id, k=k * 3, min_similarity=0.2)

        # Rerank with LLM
        return self.reranker.rerank(query, candidates, k)

    async def _retrieve_transform(
        self,
        query: str,
        project_id: int,
        k: int,
        conversation_history: Optional[list[dict]] = None,
    ) -> list[MemorySearchResult]:
        """Retrieval with query transformation."""
        if not self.query_transformer:
            raise ValueError("Query transformer not available (no LLM client)")

        # Transform query
        transformed_query = self.query_transformer.transform(query, conversation_history)
        logger.info(f"Transformed query: '{query}' -> '{transformed_query}'")

        # Use transformed query for retrieval with reranking
        if self.reranker:
            candidates = await self.store.recall(
                transformed_query, project_id, k=k * 3, min_similarity=0.2
            )
            return self.reranker.rerank(transformed_query, candidates, k)
        else:
            return await self.store.recall(transformed_query, project_id, k)

    async def _retrieve_reflective(
        self, query: str, project_id: int, k: int
    ) -> list[MemorySearchResult]:
        """Reflective iterative retrieval."""
        if not self.reflective:
            raise ValueError("Reflective RAG not available (no LLM client)")
        return self.reflective.retrieve(query, project_id, k)

    def route_planning_query(
        self,
        query: str,
        project_id: int = 1,
        task_type: Optional[str] = None,
        complexity: Optional[int] = None,
        domain: Optional[str] = None,
    ) -> dict:
        """Route query through planning-aware RAG system (explicit planning RAG).

        Args:
            query: User query
            project_id: Project ID
            task_type: Optional task type hint
            complexity: Optional complexity hint
            domain: Optional domain hint

        Returns:
            Planning routing result with pattern recommendations and analysis

        Raises:
            ValueError: If planning RAG not available
        """
        if not self.planning_rag:
            raise ValueError("Planning RAG not available (no planning store)")

        return self.planning_rag.route_query(
            query,
            project_id=project_id,
            task_type=task_type,
            complexity=complexity,
            domain=domain,
        )

    def enrich_with_temporal_kg(
        self,
        results: list[MemorySearchResult],
        project_id: int,
    ) -> list[EnrichedSearchResult]:
        """Enrich search results with temporal KG relationships (P2).

        Args:
            results: Base search results
            project_id: Project ID for context

        Returns:
            Enriched results with causal relationships
        """
        if not self.temporal_enricher:
            logger.debug("Temporal enrichment not available, returning base results")
            # Convert to enriched results without relations
            return [EnrichedSearchResult(base_result=r, causal_relations=[]) for r in results]

        try:
            return self.temporal_enricher.enrich_results(
                results,
                project_id,
                include_related=True,
                max_relations_per_result=5,
            )
        except Exception as e:
            logger.error(f"Error enriching results with temporal KG: {e}")
            # Graceful degradation
            return [EnrichedSearchResult(base_result=r, causal_relations=[]) for r in results]

    def get_causal_context(
        self,
        memory_id: int,
        project_id: int,
    ) -> Optional[dict]:
        """Get causal context for a memory via temporal KG (P2).

        Args:
            memory_id: Memory to get context for
            project_id: Project ID

        Returns:
            Dict with causes and effects, or None if unavailable
        """
        if not self.temporal_enricher:
            logger.debug("Temporal enrichment not available")
            return None

        try:
            return self.temporal_enricher.get_causal_context(
                memory_id,
                project_id,
                context_depth=2,
            )
        except Exception as e:
            logger.error(f"Error getting causal context for memory {memory_id}: {e}")
            return None

    def get_stats(self) -> dict:
        """Get RAG manager statistics.

        Returns:
            Dictionary with stats about enabled features and usage
        """
        return {
            "llm_available": self.llm is not None,
            "hyde_enabled": self.config.hyde_enabled and self.hyde is not None,
            "reranking_enabled": self.config.reranking_enabled and self.reranker is not None,
            "query_transform_enabled": self.config.query_transform_enabled
            and self.query_transformer is not None,
            "reflective_enabled": self.config.reflective_enabled and self.reflective is not None,
            "planning_enabled": self.config.planning_enabled and self.planning_rag is not None,
            "temporal_enrichment_enabled": self.config.temporal_enrichment_enabled
            and self.temporal_enricher is not None,
            "auto_strategy": self.config.auto_strategy,
        }
