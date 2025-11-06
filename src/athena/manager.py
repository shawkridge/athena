"""Unified Memory Manager - orchestrates all memory layers with intelligent routing."""

import logging
import re
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
from .procedural.models import Procedure
from .procedural.store import ProceduralStore
from .projects.manager import ProjectManager
from .prospective.models import ProspectiveTask
from .prospective.store import ProspectiveStore
from .temporal.kg_synthesis import TemporalKGSynthesis

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
        """
        self.semantic = semantic
        self.episodic = episodic
        self.procedural = procedural
        self.prospective = prospective
        self.graph = graph
        self.meta = meta
        self.consolidation = consolidation
        self.project_manager = project_manager
        self.db = semantic.db  # Reference to database from semantic store

        # Initialize confidence scorer for result quality assessment
        self.confidence_scorer = ConfidenceScorer(meta_store=meta)

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
        conversation_history: Optional[list[dict]] = None,
        include_confidence_scores: bool = True,
        explain_reasoning: bool = False
    ) -> dict:
        """Intelligent multi-layer retrieval with optional confidence scoring and explanation.

        Args:
            query: Search query
            context: Optional context (cwd, files, recent actions, etc.)
            k: Number of results to return
            conversation_history: Recent conversation messages for context-aware queries
            include_confidence_scores: If True, add confidence scores to results
            explain_reasoning: If True, include query routing explanation

        Returns:
            Dictionary with results from relevant layers, optionally with confidence scores and explanation
        """
        context = context or {}

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
                    "overall": confidence.overall_score,
                    "level": confidence.confidence_level.value,
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
