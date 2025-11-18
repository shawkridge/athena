"""Unified Memory Manager - orchestrates all memory layers with intelligent routing."""

import asyncio
import logging
import re
import time
from datetime import datetime
from typing import Any, Optional

from .consolidation.system import ConsolidationSystem
from .core.confidence_scoring import ConfidenceScorer
from .core.database import Database
from .episodic.models import EpisodicEvent, EventContext, EventType
from .episodic.store import EpisodicStore
from .graph.models import Entity, Observation, Relation
from .graph.store import GraphStore
from .memory.store import MemoryStore
from .meta.store import MetaMemoryStore
from .optimization.auto_tuner import AutoTuner, TuningStrategy
from .optimization.parallel_tier1 import ParallelTier1Executor
from .optimization.performance_profiler import PerformanceProfiler, QueryMetrics
from .optimization.query_cache import QueryCache, SessionContextCache
from .optimization.tier_selection import TierSelector
from .procedural.models import Procedure
from .procedural.store import ProceduralStore
from .projects.manager import ProjectManager
from .prospective.models import ProspectiveTask
from .prospective.store import ProspectiveStore
from .session.context_manager import SessionContextManager
from .temporal.kg_synthesis import TemporalKGSynthesis

# Import Architecture layer (optional)
try:
    from .architecture.manager import ArchitectureManager
    ARCHITECTURE_AVAILABLE = True
except ImportError:
    ARCHITECTURE_AVAILABLE = False

# Import RAG components (optional - graceful degradation if not available)
try:
    from .rag import RAGConfig, RAGManager
    from .rag.llm_client import LLMClient, create_llm_client
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

logger = logging.getLogger(__name__)


class QueryType:
    """Query type classification."""

    TEMPORAL = "temporal"  # When, what happened on date
    FACTUAL = "factual"  # What is, facts, knowledge
    RELATIONAL = "relational"  # What depends on, relationships
    PROCEDURAL = "procedural"  # How to, workflows
    PROSPECTIVE = "prospective"  # What tasks, reminders
    META = "meta"  # What do we know about
    PLANNING = "planning"  # Planning, decomposition, strategy, orchestration
    ARCHITECTURE = "architecture"  # Architectural decisions, patterns, constraints


class UnifiedMemoryManager:
    """Unified interface to all memory layers with intelligent routing."""

    def __init__(
        self,
        semantic: "MemoryStore",
        episodic: "EpisodicStore",
        procedural: "ProceduralStore",
        prospective: "ProspectiveStore",
        graph: "GraphStore",
        meta: "MetaMemoryStore",
        consolidation: "ConsolidationSystem",
        project_manager: ProjectManager,
        rag_manager: Optional["RAGManager"] = None,
        enable_advanced_rag: bool = False,
        session_manager: Optional[SessionContextManager] = None,
        architecture_manager: Optional["ArchitectureManager"] = None,
    ):
        """Initialize unified memory manager.

        Args:
            semantic: Semantic memory store
            episodic: Episodic memory store
            procedural: Procedural memory store
            prospective: Prospective memory store
            graph: Knowledge graph store
            meta: Meta-memory store
            consolidation: Consolidation system
            project_manager: Project manager
            rag_manager: Optional RAG manager for advanced retrieval
            enable_advanced_rag: If True, attempt to initialize RAG manager with default config
            session_manager: Optional session context manager for query-aware retrieval
            architecture_manager: Optional architecture manager for ADRs, patterns, constraints
        """
        self.semantic = semantic
        self.episodic = episodic
        self.procedural = procedural
        self.prospective = prospective
        self.graph = graph
        self.meta = meta
        self.consolidation = consolidation
        self.project_manager = project_manager
        self.session_manager = session_manager
        self.db = semantic.db  # Reference to database from semantic store

        # Initialize architecture manager (Layer 9: Architecture & Design)
        if architecture_manager:
            self.architecture = architecture_manager
        elif ARCHITECTURE_AVAILABLE:
            self.architecture = ArchitectureManager(self.db)
            logger.info("Architecture manager initialized")
        else:
            self.architecture = None
            logger.debug("Architecture layer not available")

        # Initialize confidence scorer for result quality assessment
        self.confidence_scorer = ConfidenceScorer(meta_store=meta)

        # Initialize performance optimization components
        self.tier_selector = TierSelector()
        self.query_cache = QueryCache(max_entries=1000, default_ttl_seconds=300)
        self.session_context_cache = SessionContextCache(ttl_seconds=60)

        # Initialize performance profiler for tracking query metrics
        self.performance_profiler = PerformanceProfiler(
            window_hours=24,
            max_metrics=10000,
            temporal_bins=24,
        )

        # Initialize auto-tuner for dynamic parameter optimization
        self.auto_tuner = AutoTuner(
            profiler=self.performance_profiler,
            strategy=TuningStrategy.BALANCED,
            adjustment_interval=100,
            min_samples=10,
        )

        # Phase 7bc: Initialize ultimate hybrid execution system
        from .optimization.dependency_graph import DependencyGraph
        from .optimization.cross_layer_cache import CrossLayerCache
        from .optimization.adaptive_strategy_selector import AdaptiveStrategySelector
        from .optimization.result_aggregator import ResultAggregator
        from .optimization.worker_pool_executor import WorkerPool
        from .optimization.execution_telemetry import ExecutionTelemetryCollector

        self.dependency_graph = DependencyGraph(self.performance_profiler)
        self.cross_layer_cache = CrossLayerCache(max_entries=5000, default_ttl_seconds=300)
        self.strategy_selector = AdaptiveStrategySelector(
            profiler=self.performance_profiler,
            dependency_graph=self.dependency_graph,
            cross_layer_cache=self.cross_layer_cache,
        )
        self.result_aggregator = ResultAggregator(confidence_scorer=self.confidence_scorer)
        self.worker_pool = WorkerPool(min_workers=2, max_workers=20)
        self.execution_telemetry = ExecutionTelemetryCollector(retention_hours=24)

        logger.info("Phase 7bc: Ultimate hybrid execution system initialized")

        # Initialize parallel Tier 1 executor for concurrent layer queries
        query_methods = {
            "episodic": self._query_episodic,
            "semantic": self._query_semantic,
            "procedural": self._query_procedural,
            "prospective": self._query_prospective,
            "graph": self._query_graph,
        }
        self.parallel_tier1_executor = ParallelTier1Executor(
            query_methods=query_methods,
            max_concurrent=5,
            timeout_seconds=10.0,
            enable_parallel=True,
        )

        # Advanced RAG setup
        self.rag_manager = rag_manager
        if enable_advanced_rag and not rag_manager and RAG_AVAILABLE:
            # Try to initialize RAG manager with available LLM
            try:
                # Try Ollama first (local, no API key needed)
                try:
                    llm_client = create_llm_client(provider="ollama")  # type: ignore
                    logger.info("RAG Manager: Trying Ollama LLM client")
                except Exception as ollama_err:
                    # Fall back to Claude if Ollama not available
                    logger.debug(f"Ollama not available ({ollama_err}), trying Claude")
                    llm_client = create_llm_client(provider="claude")  # type: ignore

                # Create temporal KG synthesis for temporal enrichment features
                temporal_kg = TemporalKGSynthesis(
                    episodic_store=episodic,
                    graph_store=graph,
                    causality_threshold=0.5,
                )

                # Initialize RAG manager with all optional components for full feature set
                self.rag_manager = RAGManager(  # type: ignore
                    memory_store=semantic,
                    llm_client=llm_client,
                    db=self.db,
                    graph_store=graph,
                    temporal_kg=temporal_kg,
                )
                logger.info(f"Advanced RAG initialized successfully with temporal enrichment enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize advanced RAG: {e}")
                self.rag_manager = None

    def retrieve(
        self,
        query: str,
        context: Optional[dict] = None,
        k: int = 5,
        fields: Optional[list[str]] = None,
        conversation_history: Optional[list[dict]] = None,
        include_confidence_scores: bool = True,
        explain_reasoning: bool = False
    ) -> dict:
        """Intelligent multi-layer retrieval with optional confidence scoring and explanation.

        Args:
            query: Search query
            context: Optional context (cwd, files, recent actions, etc.)
            k: Number of results to return (pagination)
            fields: Optional field projection - if specified, only return these fields from each result
            conversation_history: Recent conversation messages for context-aware queries
            include_confidence_scores: If True, add confidence scores to results
            explain_reasoning: If True, include query routing explanation

        Returns:
            Dictionary with results from relevant layers, optionally with confidence scores and explanation
        """
        context = context or {}

        # Load session context if available
        if self.session_manager:
            try:
                session_context = self.session_manager.get_current_session()
                if session_context:
                    # Merge session context into query context
                    context.update({
                        "session_id": session_context.session_id,
                        "task": session_context.current_task,
                        "phase": session_context.current_phase,
                        "recent_events": session_context.recent_events,
                    })
            except Exception as e:
                logger.warning(f"Failed to load session context: {e}")

        # Classify query type
        query_type = self._classify_query(query)

        # Route to appropriate layers
        results = {}

        if query_type == QueryType.TEMPORAL:
            results["episodic"] = self._query_episodic(query, context, k)

        elif query_type == QueryType.FACTUAL:
            results["semantic"] = self._query_semantic(
                query, context, k, conversation_history=conversation_history
            )

        elif query_type == QueryType.RELATIONAL:
            results["graph"] = self._query_graph(query, context, k)

        elif query_type == QueryType.PROCEDURAL:
            results["procedural"] = self._query_procedural(query, context, k)

        elif query_type == QueryType.PROSPECTIVE:
            results["prospective"] = self._query_prospective(query, context, k)

        elif query_type == QueryType.META:
            results["meta"] = self._query_meta(query, context)

        elif query_type == QueryType.PLANNING:
            # Planning queries - use planning-aware RAG
            results["planning"] = self._query_planning(query, context, k)

        else:
            # Hybrid search across multiple layers
            results = self._hybrid_search(query, context, k, conversation_history)

        # Track query for meta-memory
        self._track_query(query, query_type, results)

        # Apply confidence scores if requested
        if include_confidence_scores:
            results = self.apply_confidence_scores(results)

        # Add reasoning explanation if requested
        if explain_reasoning:
            results["_explanation"] = self._explain_query_routing(query, query_type, results)

        # Apply field projection if requested (for response optimization)
        if fields:
            results = self._project_fields(results, fields)

        return results

    def store(self, content: str, content_type: str, metadata: Optional[dict] = None) -> dict:
        """Store content in appropriate memory layers.

        Args:
            content: Content to store
            content_type: Type (fact|pattern|decision|context|event|procedure|task)
            metadata: Optional metadata

        Returns:
            Dictionary with storage results (layer: id)
        """
        metadata = metadata or {}
        project = self.project_manager.get_or_create_project()
        if not project or not project.id:
            raise RuntimeError("Failed to create or retrieve project")
        stored_ids = {}

        # Route based on content type
        if content_type in ["fact", "pattern", "decision", "context"]:
            # Semantic memory
            memory_id = self.semantic.remember(
                content=content,
                memory_type=content_type,
                project_id=project.id,
                tags=metadata.get("tags", []),
            )
            stored_ids["semantic"] = memory_id

        if content_type == "event" or metadata.get("timestamp"):
            # Episodic memory
            event = EpisodicEvent(
                project_id=project.id,
                session_id=metadata.get("session_id", f"session_{int(datetime.now().timestamp())}"),
                event_type=EventType(metadata.get("event_type", "action")),
                content=content,
                context=EventContext(
                    cwd=metadata.get("cwd"),
                    files=metadata.get("files", []),
                    task=metadata.get("task"),
                    phase=metadata.get("phase"),
                ),
            )
            event_id = self.episodic.record_event(event)
            stored_ids["episodic"] = event_id

        if content_type == "procedure":
            # Procedural memory
            # Would need full Procedure object - simplified here
            stored_ids["procedural"] = "procedure_creation_not_implemented_in_store"

        if content_type == "task":
            # Prospective memory
            task = ProspectiveTask(
                project_id=project.id,
                content=content,
                active_form=metadata.get("active_form", content),
            )
            task_id = self.prospective.create_task(task)
            stored_ids["prospective"] = task_id

        if metadata.get("entities") or metadata.get("relations"):
            # Knowledge graph
            # Would handle entity/relation creation
            stored_ids["graph"] = "graph_update_not_implemented_in_store"

        # Update meta-memory
        # TODO: Implement domain coverage updates when storing content
        pass

        return stored_ids

    def _classify_query(self, query: str) -> str:
        """Classify query type.

        Args:
            query: Query string

        Returns:
            Query type
        """
        query_lower = query.lower()

        # Temporal indicators
        if any(word in query_lower for word in ["when", "last", "recent", "yesterday", "week", "month", "date", "time"]):
            return QueryType.TEMPORAL

        # Relational indicators
        if any(word in query_lower for word in ["depends", "related", "connection", "linked", "uses", "implements"]):
            return QueryType.RELATIONAL

        # Planning indicators (Phase 3.5 addition - check BEFORE procedural/prospective)
        if any(word in query_lower for word in [
            "decompose", "plan", "strategy", "orchestration", "validate",
            "project status", "orchestrate", "execution", "recommendation",
            "how should i", "suggest", "suggest a", "suggest"
        ]):
            return QueryType.PLANNING

        # Procedural indicators
        if any(word in query_lower for word in ["how to", "how do", "workflow", "process", "steps", "procedure"]):
            return QueryType.PROCEDURAL

        # Prospective indicators
        if any(word in query_lower for word in ["task", "todo", "remind", "remember to", "pending", "need to"]):
            return QueryType.PROSPECTIVE

        # Meta indicators
        if any(word in query_lower for word in ["what do we know", "what have we learned", "coverage", "expertise"]):
            return QueryType.META

        # Default to factual
        return QueryType.FACTUAL

    def _query_episodic(self, query: str, context: dict, k: int) -> list:
        """Query episodic memory."""
        project = self.project_manager.get_or_create_project()
        if not project or not project.id:
            return []

        # Check for date-specific queries
        if "yesterday" in query.lower():
            from datetime import timedelta
            start = datetime.now() - timedelta(days=1)
            events = self.episodic.get_events_by_date(project.id, start) if project.id else []
        elif "week" in query.lower():
            events = self.episodic.get_recent_events(project.id, hours=168, limit=k) if project.id else []
        else:
            # General search
            events = self.episodic.search_events(project.id, query, limit=k) if project.id else []

        return [{"event_id": e.id, "content": e.content, "timestamp": e.timestamp, "type": e.event_type} for e in events]

    def _query_semantic(
        self,
        query: str,
        context: dict,
        k: int,
        use_advanced_rag: bool = True,
        conversation_history: Optional[list[dict]] = None
    ) -> list:
        """Query semantic memory.

        Args:
            query: Search query
            context: Context dictionary
            k: Number of results
            use_advanced_rag: If True, use RAG manager for advanced retrieval
            conversation_history: Recent conversation for context-aware queries

        Returns:
            List of search results with content, type, similarity, tags
        """
        project = self.project_manager.require_project()
        assert project.id is not None, "Project ID should not be None after require_project()"

        # Use advanced RAG if available and enabled
        if use_advanced_rag and self.rag_manager:
            try:
                results = self.rag_manager.retrieve(
                    query=query,
                    project_id=project.id,
                    k=k,
                    strategy="auto",  # Let RAG manager decide
                    conversation_history=conversation_history,
                )
                logger.info(f"Advanced RAG retrieved {len(results)} results")
            except Exception as e:
                logger.warning(f"Advanced RAG failed, falling back to basic: {e}")
                # Fallback to existing reranking
                results = self.semantic.recall_with_reranking(
                    query=query,
                    project_id=project.id,
                    k=k,
                )
        else:
            # Use existing composite reranking
            results = self.semantic.recall_with_reranking(
                query=query,
                project_id=project.id,
                k=k,
            )

        return [
            {
                "content": r.memory.content,
                "type": r.memory.memory_type,
                "similarity": r.similarity,
                "tags": r.memory.tags,
            }
            for r in results
        ]

    def _query_graph(self, query: str, context: dict, k: int) -> list:
        """Query knowledge graph."""
        # Extract entity name from query
        # Simple heuristic - improve with NLP
        words = query.split()
        entity_name = words[-1] if words else query

        entities = self.graph.search_entities(entity_name)[:k]

        results = []
        for entity in entities:
            if entity.id is None:
                continue
            relations = self.graph.get_entity_relations(entity.id, direction="both")  # type: ignore
            results.append({
                "entity": entity.name,
                "type": entity.entity_type.value,
                "relations": [
                    {
                        "relation": r.relation_type.value,
                        "to": related.name,
                    }
                    for r, related in relations[:5]
                ],
            })

        return results

    def _query_procedural(self, query: str, context: dict, k: int) -> list:
        """Query procedural memory."""
        # Extract context tags from context dict
        context_tags = context.get("technologies", []) if context else []

        procedures = self.procedural.search_procedures(query, context=context_tags)

        return [
            {
                "name": p.name,
                "category": p.category.value,
                "template": p.template,
                "success_rate": p.success_rate,
            }
            for p in procedures[:k]
        ]

    def _query_prospective(self, query: str, context: dict, k: int) -> list:
        """Query prospective memory."""
        project = self.project_manager.require_project()
        assert project.id is not None, "Project ID should not be None after require_project()"

        # Check for status filters in query
        if "pending" in query.lower():
            from .prospective.models import TaskStatus
            tasks = self.prospective.list_tasks(project.id, status=TaskStatus.PENDING, limit=k)
        elif "ready" in query.lower():
            tasks = self.prospective.get_ready_tasks(project.id)[:k]
        else:
            tasks = self.prospective.list_tasks(project.id, limit=k)

        return [
            {
                "content": t.content,
                "status": t.status.value,
                "priority": t.priority.value,
                "assignee": t.assignee,
            }
            for t in tasks
        ]

    def _query_meta(self, query: str, context: dict) -> dict:
        """Query meta-memory."""
        # Extract domain from query
        domain = query.split("about")[-1].strip() if "about" in query else None

        if domain:
            coverage = self.meta.get_domain(domain)
            if coverage:
                expertise_str = coverage.expertise_level.value if hasattr(coverage.expertise_level, 'value') else str(coverage.expertise_level)
                return {
                    "domain": coverage.domain,
                    "memory_count": coverage.memory_count,
                    "expertise_level": expertise_str,
                    "avg_usefulness": coverage.avg_usefulness,
                }

        # Otherwise list all coverage
        all_coverage = self.meta.list_domains()
        return {
            "domains": [
                {
                    "domain": c.domain,
                    "memory_count": c.memory_count,
                    "expertise": c.expertise_level.value if hasattr(c.expertise_level, 'value') else str(c.expertise_level),
                }
                for c in all_coverage[:10]
            ]
        }

    def _query_planning(self, query: str, context: dict, k: int) -> list:
        """Query planning-aware layer for planning, strategy, and orchestration queries.

        Phase 3.5 addition: Routes planning queries through planning-aware RAG
        and returns patterns, strategies, and recommendations.

        Args:
            query: Planning query (decompose, strategy, orchestration, validation, etc.)
            context: Context dictionary
            k: Number of results

        Returns:
            List of planning recommendations with patterns, strategies, and confidence
        """
        project = self.project_manager.get_or_create_project()
        if not project or not project.id:
            return []

        try:
            # Use planning-aware RAG if available
            from .rag.planning_rag import PlanningRAGRouter

            planning_rag = PlanningRAGRouter(self.semantic)

            # Route through planning-aware RAG
            results = planning_rag.route_planning_query(
                query=query,
                context=context,
                k=k
            )

            # Format results
            return [
                {
                    "type": "planning_pattern",
                    "content": r.get("content", ""),
                    "confidence": r.get("confidence", 0.0),
                    "pattern_type": r.get("pattern_type", "unknown"),
                    "rationale": r.get("rationale", ""),
                }
                for r in results
            ]
        except Exception as e:
            logger.warning(f"Planning RAG query failed: {e}")
            # Fallback to empty results
            return []

    def _hybrid_search(
        self,
        query: str,
        context: dict,
        k: int,
        conversation_history: Optional[list[dict]] = None
    ) -> dict:
        """Hybrid search combining vector, lexical, and graph search."""
        results = {}

        # 1. Vector search (semantic memory) with advanced RAG
        semantic_results = self._query_semantic(
            query, context, k, conversation_history=conversation_history
        )

        # 2. Lexical search (BM25)
        lexical_results = self._query_lexical(query, context, k)

        # 3. Fuse semantic + lexical using RRF
        from .memory.lexical import reciprocal_rank_fusion

        # Convert to (id, score) tuples for fusion
        semantic_tuples = [
            (i, r.get('similarity', 0.5))
            for i, r in enumerate(semantic_results)
        ]
        lexical_tuples = [
            (i, r.get('score', 0.5))
            for i, r in enumerate(lexical_results)
        ]

        if semantic_tuples and lexical_tuples:
            # Fuse results
            fused = reciprocal_rank_fusion([semantic_tuples, lexical_tuples])

            # Map back to content (combine both result sets)
            all_results = semantic_results + lexical_results
            fused_results = []

            for idx, score in fused[:k]:
                if idx < len(all_results):
                    result = all_results[idx].copy()
                    result['fused_score'] = score
                    fused_results.append(result)

            results["semantic"] = fused_results
        else:
            # Fallback to semantic only
            results["semantic"] = semantic_results

        # 4. Query episodic for recent relevant events
        results["episodic"] = self._query_episodic(query, context, k=3)

        # 5. Query procedural if query suggests workflow
        if any(word in query.lower() for word in ["do", "make", "create", "implement"]):
            results["procedural"] = self._query_procedural(query, context, k=2)

        # 6. Query graph for entities mentioned
        results["graph"] = self._query_graph(query, context, k=3)

        return results

    def _query_lexical(self, query: str, context: dict, k: int) -> list:
        """Query using BM25 lexical matching."""
        from .memory.lexical import LexicalSearch

        project = self.project_manager.require_project()
        assert project.id is not None, "Project ID should not be None after require_project()"

        # Get all memories for indexing
        all_memories = self.semantic.list_memories(
            project_id=project.id,
            limit=1000,
            sort_by='recent'
        )

        if not all_memories:
            return []

        # Filter out memories with None IDs and index
        valid_memories = [(m.id, m.content) for m in all_memories if m.id is not None]
        if not valid_memories:
            return []

        # Index memories
        lexical = LexicalSearch()
        lexical.index_memories(valid_memories)  # type: ignore

        # Search
        results = lexical.search(query, k=k)

        # Convert to standard format
        formatted_results = []
        for memory_id, score in results:
            # Find memory by ID
            memory = next((m for m in all_memories if m.id == memory_id), None)
            if memory:
                formatted_results.append({
                    'content': memory.content,
                    'type': memory.memory_type.value if hasattr(memory.memory_type, 'value') else str(memory.memory_type),
                    'score': score,
                    'tags': memory.tags
                })

        return formatted_results

    def _track_query(self, query: str, query_type: str, results: dict):
        """Track query for meta-memory analytics."""
        # Could log queries for pattern analysis
        # For now, just update access counts for returned memories
        if "semantic" in results:
            for result in results["semantic"]:
                if "id" in result:
                    self.semantic.db.update_access_stats(result["id"])

    def apply_confidence_scores(self, results: dict) -> dict:
        """Apply confidence scores to retrieval results from all layers.

        Args:
            results: Dictionary of results from retrieve() method

        Returns:
            Dictionary with confidence scores added to each result layer
        """
        scored_results = {}

        # Apply scores to each layer
        for layer, layer_results in results.items():
            if not isinstance(layer_results, list):
                scored_results[layer] = layer_results
                continue

            scored_layer = []
            for result in layer_results:
                # Create a copy to avoid modifying original
                scored_result = dict(result) if isinstance(result, dict) else {"content": str(result)}

                # Compute confidence scores
                confidence = self.confidence_scorer.score(
                    memory=scored_result,
                    source_layer=layer,
                    semantic_score=result.get("similarity") if isinstance(result, dict) else None
                )

                # Add confidence scores to result
                scored_result["confidence"] = {
                    "semantic_relevance": confidence.semantic_relevance,
                    "source_quality": confidence.source_quality,
                    "recency": confidence.recency,
                    "consistency": confidence.consistency,
                    "completeness": confidence.completeness,
                    "overall": confidence.average(),
                    "level": confidence.level().value,
                }

                scored_layer.append(scored_result)

            scored_results[layer] = scored_layer

        return scored_results

    def _explain_query_routing(self, query: str, query_type: str, results: dict) -> dict:
        """Explain how a query was classified and routed.

        Args:
            query: Original query string
            query_type: Classified query type
            results: Results returned from the query

        Returns:
            Dictionary with explanation details
        """
        # Determine which layers were searched
        searched_layers = [layer for layer in results.keys() if layer != "_explanation"]

        # Map query type to human-readable explanation
        type_explanations = {
            QueryType.TEMPORAL: "Searched episodic memory - you asked about when something happened",
            QueryType.FACTUAL: "Searched semantic memory - you asked for factual information",
            QueryType.RELATIONAL: "Searched knowledge graph - you asked about relationships",
            QueryType.PROCEDURAL: "Searched procedural memory - you asked how to do something",
            QueryType.PROSPECTIVE: "Searched prospective memory - you asked about tasks/goals",
            QueryType.META: "Searched meta-memory - you asked about what we know",
            QueryType.PLANNING: "Searched planning layer - you asked for strategy/decomposition",
        }

        return {
            "query": query,
            "query_type": query_type,
            "reasoning": type_explanations.get(query_type, "Performed hybrid search across all layers"),
            "layers_searched": searched_layers,
            "result_count": sum(len(r) if isinstance(r, list) else 1 for r in results.values() if r != "_explanation"),
        }

    def recall(
        self,
        query: str,
        context: Optional[dict] = None,
        k: int = 5,
        cascade_depth: Optional[int] = None,
        include_scores: bool = True,
        explain_reasoning: bool = False,
        use_cache: bool = True,
        auto_select_depth: bool = True,
        use_parallel: bool = True,
    ) -> dict:
        """Cascading recall with multi-tier search across memory layers.

        Implements a sophisticated multi-tier recall strategy:
        1. **Tier 1** (Exact): Fast layer-specific searches (episodic, semantic, etc.)
        2. **Tier 2** (Enriched): Cross-layer context from session and recent events
        3. **Tier 3** (Synthesized): LLM-enhanced synthesis from multiple layers

        Uses session context to bias retrieval and cascade through layers
        with decreasing specificity.

        Performance optimizations:
        - Automatic cascade depth selection (30-50% faster on simple queries)
        - Query result caching (10-30x faster for repeated queries)
        - Session context caching (reduces DB queries)
        - Parallel Tier 1 execution (3-4x faster with 5 layers)

        Args:
            query: Recall query (e.g., "What was the failing test?")
            context: Optional context (task, phase, recent_events, etc.)
            k: Number of results per tier
            cascade_depth: How many tiers to search (1-3). If None, auto-selects.
            include_scores: Include confidence scores in results
            explain_reasoning: Include tier information and reasoning
            use_cache: If True, check cache before searching (default True)
            auto_select_depth: If True and cascade_depth is None, use tier selector (default True)
            use_parallel: If True, execute Tier 1 layers in parallel (default True, 3-4x faster)

        Returns:
            Dictionary with cascading recall results:
            - "tier_1": Fast layer-specific results
            - "tier_2": Enriched cross-layer results (if depth >= 2)
            - "tier_3": LLM-synthesized results (if depth >= 3)
            - "_cascade_explanation": Reasoning (if explain_reasoning=True)
            - "_cache_hit": True if result came from cache

        Example:
            # Basic recall (auto-selects depth based on query)
            results = manager.recall("What was the failing test?", k=3)

            # With session context
            results = manager.recall(
                "What were we working on?",
                context={"phase": "debugging"},
                auto_select_depth=True
            )

            # With full reasoning
            results = manager.recall(
                query,
                cascade_depth=3,
                explain_reasoning=True
            )
        """
        context = context or {}

        # Load session context if available (with caching)
        if self.session_manager:
            try:
                # Try cache first
                session_id = context.get("session_id")
                if session_id and use_cache:
                    cached_ctx = self.session_context_cache.get(session_id)
                    if cached_ctx:
                        context.update(cached_ctx)
                    else:
                        session_context = self.session_manager.get_current_session()
                        if session_context:
                            session_data = {
                                "session_id": session_context.session_id,
                                "task": session_context.current_task,
                                "phase": session_context.current_phase,
                                "recent_events": session_context.recent_events,
                            }
                            context.update(session_data)
                            # Cache for future use
                            self.session_context_cache.put(session_id, session_data)
                else:
                    # No cache key, fetch directly
                    session_context = self.session_manager.get_current_session()
                    if session_context:
                        context.update({
                            "session_id": session_context.session_id,
                            "task": session_context.current_task,
                            "phase": session_context.current_phase,
                            "recent_events": session_context.recent_events,
                        })
            except Exception as e:
                logger.warning(f"Failed to load session context in recall: {e}")

        # Check query cache if enabled
        if use_cache:
            cached_results = self.query_cache.get(query, context)
            if cached_results is not None:
                cached_results["_cache_hit"] = True
                return cached_results

        # Auto-select cascade depth if not specified
        if cascade_depth is None and auto_select_depth:
            cascade_depth = self.tier_selector.select_depth(query, context)
        else:
            cascade_depth = cascade_depth or 3

        cascade_depth = min(max(1, cascade_depth), 3)  # Clamp to 1-3
        results = {"_cascade_depth": cascade_depth, "_cache_hit": False}

        try:
            # Tier 1: Fast layer-specific searches (with optional parallel execution)
            if use_parallel:
                # Use parallel executor for concurrent layer queries
                tier_1_results = self._recall_tier_1_parallel(query, context, k)
            else:
                # Fall back to sequential execution
                tier_1_results = self._recall_tier_1(query, context, k)
            results["tier_1"] = tier_1_results

            # Tier 2: Enriched cross-layer context (if requested)
            if cascade_depth >= 2:
                tier_2_results = self._recall_tier_2(
                    query, context, tier_1_results, k
                )
                results["tier_2"] = tier_2_results

            # Tier 3: LLM-synthesized results (if requested and RAG available)
            if cascade_depth >= 3 and self.rag_manager:
                tier_3_results = self._recall_tier_3(
                    query, context, tier_1_results, k
                )
                results["tier_3"] = tier_3_results

            # Apply confidence scores if requested
            if include_scores:
                results = self._score_cascade_results(results)

            # Include reasoning if requested
            if explain_reasoning:
                results["_cascade_explanation"] = {
                    "query": query,
                    "context_keys": list(context.keys()),
                    "depth": cascade_depth,
                    "tiers_used": [
                        "tier_1",
                        "tier_2" if cascade_depth >= 2 else None,
                        "tier_3" if cascade_depth >= 3 and self.rag_manager else None,
                    ],
                    "filters": "session_context" if "session_id" in context else "none",
                }

        except Exception as e:
            logger.error(f"Error in cascading recall: {e}")
            results["_error"] = str(e)

        # Cache results if caching is enabled and no errors
        if use_cache and "_error" not in results:
            self.query_cache.put(query, results, context)

        return results

    def _recall_tier_1(self, query: str, context: dict, k: int) -> dict:
        """Tier 1: Fast layer-specific searches.

        Queries each memory layer independently for quick retrieval.

        Args:
            query: Search query
            context: Query context
            k: Number of results per layer

        Returns:
            Dictionary with results from each layer
        """
        tier_1 = {}

        try:
            # Episodic: Temporal queries, recent events
            if context.get("phase") == "debugging" or any(
                word in query.lower()
                for word in ["when", "last", "recent", "error", "failed"]
            ):
                tier_1["episodic"] = self._query_episodic(query, context, k)

            # Semantic: Factual queries
            tier_1["semantic"] = self._query_semantic(query, context, k)

            # Procedural: How-to, workflow queries
            if any(word in query.lower() for word in ["how", "do", "build", "implement"]):
                tier_1["procedural"] = self._query_procedural(query, context, k)

            # Prospective: Task and goal queries
            if any(word in query.lower() for word in ["task", "goal", "todo", "should"]):
                tier_1["prospective"] = self._query_prospective(query, context, k)

            # Graph: Relationship queries
            if any(word in query.lower() for word in ["relates", "depends", "connected"]):
                tier_1["graph"] = self._query_graph(query, context, k)

        except Exception as e:
            logger.error(f"Error in tier 1 recall: {e}")

        return tier_1

    def _recall_tier_1_parallel(self, query: str, context: dict, k: int) -> dict:
        """Tier 1: Fast layer-specific searches using parallel execution.

        Executes layer queries concurrently for 3-4x speedup when multiple
        layers are selected. Gracefully falls back to sequential if needed.

        Args:
            query: Search query
            context: Query context
            k: Number of results per layer

        Returns:
            Dictionary with results from each layer
        """
        start_time = time.time()

        # Get optimized config from auto-tuner
        query_type = self._classify_query(query)
        optimized_config = self.auto_tuner.get_optimized_config(query_type)

        # Update executor with optimized parameters
        self.parallel_tier1_executor.executor.max_concurrent = optimized_config.max_concurrent
        self.parallel_tier1_executor.executor.timeout_seconds = optimized_config.timeout_seconds
        self.parallel_tier1_executor.enable_parallel = optimized_config.enable_parallel

        try:
            # Try to execute in parallel using async
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                tier_1_results = loop.run_until_complete(
                    self.parallel_tier1_executor.execute_tier_1_parallel(
                        query=query,
                        context=context,
                        k=k,
                        use_parallel=optimized_config.enable_parallel,
                    )
                )

                # Record metrics for auto-tuning
                elapsed_ms = (time.time() - start_time) * 1000
                layers = list(self.parallel_tier1_executor.LAYER_KEYWORDS.keys())
                layer_latencies = self.parallel_tier1_executor.executor.latest_layer_latencies or {}
                result_count = sum(
                    len(v) if isinstance(v, list) else (1 if v else 0)
                    for k, v in tier_1_results.items()
                    if not k.startswith("_")
                )

                self._record_query_metrics(
                    query=query,
                    query_type=query_type,
                    layers_queried=layers,
                    layer_latencies=layer_latencies,
                    total_latency_ms=elapsed_ms,
                    result_count=result_count,
                    success=True,
                    cache_hit=False,
                    parallel=optimized_config.enable_parallel,
                )

                return tier_1_results
            finally:
                loop.close()
        except Exception as e:
            logger.warning(
                f"Parallel Tier 1 execution failed ({e}), falling back to sequential"
            )
            # Record failed attempt
            elapsed_ms = (time.time() - start_time) * 1000
            self._record_query_metrics(
                query=query,
                query_type=query_type,
                layers_queried=[],
                layer_latencies={},
                total_latency_ms=elapsed_ms,
                result_count=0,
                success=False,
                parallel=True,
            )

            # Fall back to sequential execution
            return self._recall_tier_1(query, context, k)

    def _recall_tier_2(
        self, query: str, context: dict, tier_1_results: dict, k: int
    ) -> dict:
        """Tier 2: Enriched cross-layer context.

        Uses results from tier 1 to inform cross-layer queries
        and enriches results with session context.

        Args:
            query: Search query
            context: Query context (includes session context)
            tier_1_results: Results from tier 1
            k: Number of results to add

        Returns:
            Dictionary with enriched cross-layer results
        """
        tier_2 = {}

        try:
            # Hybrid search across multiple layers
            if tier_1_results:
                tier_2["hybrid"] = self._hybrid_search(
                    query, context, k, conversation_history=None
                )

            # Meta queries: What do we know about the situation?
            if context.get("phase"):
                tier_2["meta"] = self._query_meta(
                    f"What do we know about {context.get('phase')} phase?", context
                )

            # Session-aware enrichment
            if context.get("recent_events"):
                tier_2["session_context"] = {
                    "recent_events": context["recent_events"][:k],
                    "task": context.get("task"),
                    "phase": context.get("phase"),
                }

        except Exception as e:
            logger.error(f"Error in tier 2 recall: {e}")

        return tier_2

    def _recall_tier_3(
        self, query: str, context: dict, tier_1_results: dict, k: int
    ) -> dict:
        """Tier 3: LLM-synthesized results.

        Uses RAG to synthesize insights from tier 1 results
        with LLM enhancement for complex reasoning.

        Args:
            query: Search query
            context: Query context
            tier_1_results: Results from tier 1
            k: Number of results to synthesize

        Returns:
            Dictionary with LLM-enhanced results
        """
        tier_3 = {}

        try:
            if not self.rag_manager:
                logger.debug("RAG manager not available for tier 3")
                return tier_3

            # Use RAG for advanced synthesis
            rag_results = self.rag_manager.retrieve(
                query,
                context=context,
                k=k,
            )

            tier_3["synthesized"] = rag_results.get("results", [])

            # Planning synthesis for complex queries
            if context.get("phase") in ["planning", "refactoring"]:
                planning_results = self._query_planning(query, context, k)
                tier_3["planning"] = planning_results

        except Exception as e:
            logger.debug(f"Tier 3 recall failed (expected if RAG unavailable): {e}")

        return tier_3

    def _score_cascade_results(self, results: dict) -> dict:
        """Apply confidence scores to cascade results.

        Uses the existing confidence scoring mechanism
        across all tiers.

        Args:
            results: Cascade results from all tiers

        Returns:
            Results with confidence scores applied
        """
        try:
            # Score tier 1 results using standard confidence scorer
            if "tier_1" in results and results["tier_1"]:
                results["tier_1"] = self.apply_confidence_scores(results["tier_1"])

            # Score tier 2 results
            if "tier_2" in results and results["tier_2"]:
                results["tier_2"] = self.apply_confidence_scores(results["tier_2"])

            # Tier 3 already includes scores from RAG/planning

        except Exception as e:
            logger.debug(f"Confidence scoring failed: {e}")

        return results

    def _project_fields(self, results: dict, fields: list[str]) -> dict:
        """Project results to include only specified fields (for response optimization).

        Args:
            results: Dictionary of results from various memory layers
            fields: List of field names to project (include in output)

        Returns:
            Dictionary with same structure but only specified fields
        """
        projected = {}

        for layer, layer_results in results.items():
            if layer.startswith("_"):
                # Preserve metadata fields (like _explanation)
                projected[layer] = layer_results
                continue

            if isinstance(layer_results, list):
                # Project each result in the list
                projected[layer] = [self._project_record(record, fields) for record in layer_results]
            elif isinstance(layer_results, dict):
                # Project dictionary result
                projected[layer] = self._project_record(layer_results, fields)
            else:
                # Keep as-is if not list/dict
                projected[layer] = layer_results

        return projected

    def _project_record(self, record: Any, fields: list[str]) -> Any:
        """Project a single record to include only specified fields.

        Args:
            record: Record to project (dict, object, or primitive)
            fields: List of field names to include

        Returns:
            Projected record with only specified fields
        """
        if isinstance(record, dict):
            # Dictionary projection
            return {k: v for k, v in record.items() if k in fields}
        elif hasattr(record, "__dict__"):
            # Object projection - convert to dict first
            record_dict = record.__dict__ if hasattr(record, "__dict__") else {}
            return {k: v for k, v in record_dict.items() if k in fields}
        else:
            # Primitive value - return as-is
            return record

    def _record_query_metrics(
        self,
        query: str,
        query_type: str,
        layers_queried: list,
        layer_latencies: dict,
        total_latency_ms: float,
        result_count: int,
        success: bool,
        cache_hit: bool = False,
        parallel: bool = False,
    ) -> None:
        """Record query execution metrics for auto-tuning.

        Args:
            query: Query text
            query_type: Classified query type
            layers_queried: List of layers that were queried
            layer_latencies: Dict of layer_name -> latency_ms
            total_latency_ms: Total execution time in milliseconds
            result_count: Number of results returned
            success: Whether query succeeded
            cache_hit: Whether result came from cache
            parallel: Whether parallel execution was used
        """
        metrics = QueryMetrics(
            query_id=f"q_{int(time.time() * 1000)}",
            query_text=query,
            query_type=query_type,
            timestamp=time.time(),
            latency_ms=total_latency_ms,
            memory_mb=0.0,  # TODO: Track memory usage
            cache_hit=cache_hit,
            result_count=result_count,
            layers_queried=layers_queried,
            layer_latencies=layer_latencies,
            success=success,
            parallel_execution=parallel,
            concurrency_level=self.parallel_tier1_executor.executor.max_concurrent if parallel else 1,
            accuracy_score=1.0 if success else 0.8,
        )

        self.performance_profiler.record_query(metrics)

    def update_tuning_strategy(self, strategy: TuningStrategy) -> None:
        """Update the auto-tuning strategy.

        Args:
            strategy: New tuning strategy (LATENCY, THROUGHPUT, COST, BALANCED)
        """
        self.auto_tuner.update_strategy(strategy)
        logger.info(f"Updated tuning strategy to {strategy.value}")

    def get_tuning_report(self) -> dict:
        """Get auto-tuning diagnostics and recommendations.

        Returns:
            Dictionary with tuning metrics, current config, and recommendations
        """
        return self.auto_tuner.get_tuning_report()

    def get_performance_statistics(self) -> dict:
        """Get comprehensive performance statistics.

        Returns:
            Dictionary with cache effectiveness, concurrency effectiveness,
            slow queries, layer metrics, and temporal patterns
        """
        return {
            "cache_effectiveness": self.performance_profiler.get_cache_effectiveness(),
            "concurrency_effectiveness": self.performance_profiler.get_concurrency_effectiveness(),
            "slow_queries": self.performance_profiler.get_slow_queries(limit=5),
            "trending_queries": self.performance_profiler.get_trending_queries(limit=5),
            "layer_dependencies": self.performance_profiler.get_layer_dependency_analysis(),
            "temporal_pattern": self.performance_profiler.get_temporal_pattern(),
        }

    # Phase 7bc: Ultimate Hybrid Execution System Methods

    def get_dependency_graph_stats(self) -> dict:
        """Get dependency graph statistics and insights.

        Returns:
            Dictionary with dependency graph metrics
        """
        return self.dependency_graph.get_graph_statistics()

    def get_cross_layer_cache_stats(self) -> dict:
        """Get cross-layer cache effectiveness metrics.

        Returns:
            Dictionary with cache effectiveness, hit rate, etc.
        """
        return self.cross_layer_cache.get_cache_effectiveness()

    def get_strategy_selection_stats(self) -> dict:
        """Get adaptive strategy selector statistics.

        Returns:
            Dictionary with strategy distribution and accuracy
        """
        return self.strategy_selector.get_strategy_statistics()

    def get_execution_telemetry_report(self) -> dict:
        """Get comprehensive execution telemetry report.

        Returns:
            Dictionary with strategy effectiveness, decision accuracy, trends, recommendations
        """
        return self.execution_telemetry.export_metrics()

    def get_worker_pool_health(self) -> dict:
        """Get worker pool health status.

        Returns:
            Dictionary with worker count, queue depth, throughput, etc.
        """
        return self.worker_pool.get_health_status()

    def get_phase_7bc_diagnostics(self) -> dict:
        """Get complete Phase 7bc system diagnostics.

        Returns:
            Dictionary with all Phase 7bc component metrics
        """
        return {
            "dependency_graph": self.get_dependency_graph_stats(),
            "cross_layer_cache": self.get_cross_layer_cache_stats(),
            "strategy_selection": self.get_strategy_selection_stats(),
            "execution_telemetry": self.get_execution_telemetry_report(),
            "worker_pool": self.get_worker_pool_health(),
        }

    def invalidate_cross_layer_cache_layer(self, layer_name: str) -> int:
        """Invalidate cache entries containing a specific layer.

        Args:
            layer_name: Layer name to invalidate

        Returns:
            Number of cache entries invalidated
        """
        return self.cross_layer_cache.invalidate_layer(layer_name)
