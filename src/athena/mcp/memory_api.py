"""Direct memory API for code execution paradigm.

This module provides direct Python APIs for agents to call instead of using MCP tools.
Agents write Python code that calls these methods directly, enabling sandbox execution
with full context and error handling.

Usage:
    from athena.mcp.memory_api import MemoryAPI

    api = MemoryAPI.create()

    # Store memory
    memory_id = api.remember(
        content="Important finding",
        memory_type="semantic"
    )

    # Recall memory
    results = api.recall(query="recent findings", limit=5)

    # Store event
    event_id = api.remember_event(
        event_type="action",
        content="Ran test suite",
        context={"test_count": 42}
    )
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional, List, Dict

from ..core.database import Database
from ..core.models import MemoryType
from ..episodic.models import EpisodicEvent, EventType, EventContext, EventOutcome
from ..episodic.store import EpisodicStore
from ..memory.store import MemoryStore
from ..procedural.models import Procedure, ProcedureCategory
from ..procedural.store import ProceduralStore
from ..prospective.models import ProspectiveTask, TaskStatus, TaskPriority, TaskPhase
from ..prospective.store import ProspectiveStore
from ..graph.models import Entity, Relation, EntityType, RelationType
from ..graph.store import GraphStore
from ..meta.store import MetaMemoryStore
from ..consolidation.system import ConsolidationSystem
from ..manager import UnifiedMemoryManager
from ..projects.manager import ProjectManager

logger = logging.getLogger(__name__)


class MemoryAPI:
    """Direct Python API for memory operations.

    Provides simple, callable methods that agents can use in executable code
    instead of calling MCP tools. This enables:

    1. Direct Python method calls (faster, no serialization)
    2. Full error handling and exceptions
    3. Type hints for IDE autocomplete
    4. Sandbox execution with isolation
    5. Progressive disclosure (discovery via introspection)
    """

    def __init__(
        self,
        manager: UnifiedMemoryManager,
        project_manager: ProjectManager,
        database: Database,
    ):
        """Initialize MemoryAPI with manager and stores.

        Args:
            manager: UnifiedMemoryManager orchestrating all layers
            project_manager: Project manager for context
            database: Database connection
        """
        self.manager = manager
        self.project_manager = project_manager
        self.db = database

        # Store layer references for quick access
        self.semantic = manager.semantic
        self.episodic = manager.episodic
        self.procedural = manager.procedural
        self.prospective = manager.prospective
        self.graph = manager.graph
        self.meta = manager.meta
        self.consolidation = manager.consolidation

        logger.info("MemoryAPI initialized with all memory layers")

    @staticmethod
    def create(db_path: Optional[str] = None) -> "MemoryAPI":
        """Factory method to create a MemoryAPI instance.

        Args:
            db_path: Optional database path (uses default if not provided)

        Returns:
            Initialized MemoryAPI instance
        """
        # Initialize database
        database = Database(db_path) if db_path else Database()

        # Initialize all memory layers
        semantic = MemoryStore(database)
        episodic = EpisodicStore(database)
        procedural = ProceduralStore(database)
        prospective = ProspectiveStore(database)
        graph = GraphStore(database)
        meta = MetaMemoryStore(database)
        consolidation = ConsolidationSystem(episodic, database)

        # Initialize project manager
        project_manager = ProjectManager(database)

        # Initialize unified manager
        manager = UnifiedMemoryManager(
            semantic=semantic,
            episodic=episodic,
            procedural=procedural,
            prospective=prospective,
            graph=graph,
            meta=meta,
            consolidation=consolidation,
            project_manager=project_manager,
        )

        return MemoryAPI(manager, project_manager, database)

    # ===== CORE REMEMBER OPERATIONS =====

    def remember(
        self,
        content: str,
        memory_type: str = "semantic",
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> int:
        """Store content in memory.

        Args:
            content: Content to store
            memory_type: Type of memory (semantic|event|procedure|task)
            context: Optional context metadata
            tags: Optional list of tags for categorization

        Returns:
            Memory ID (integer)

        Example:
            api = MemoryAPI.create()
            memory_id = api.remember(
                "Found bug in parser.py",
                memory_type="semantic",
                tags=["bug", "parser"]
            )
        """
        try:
            context = context or {}
            tags = tags or []
            project = self.project_manager.get_or_create_project()

            if not project or not project.id:
                raise RuntimeError("Failed to get/create project")

            memory_id = self.semantic.remember(
                content=content,
                memory_type=memory_type,
                project_id=project.id,
                tags=tags,
            )

            logger.info(f"Remembered content: {memory_type} (ID: {memory_id})")
            return memory_id

        except Exception as e:
            logger.error(f"Failed to remember: {e}")
            raise

    def recall(
        self,
        query: str,
        limit: int = 5,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Retrieve memories matching query.

        Args:
            query: Search query
            limit: Maximum results to return
            context: Optional context for routing (cwd, files, etc.)

        Returns:
            Dictionary with retrieved memories and metadata

        Example:
            results = api.recall("parser bugs", limit=10)
            for item in results.get("memories", []):
                print(item["content"])
        """
        try:
            results = self.manager.retrieve(
                query=query,
                context=context,
                k=limit,
                include_confidence_scores=True,
            )

            logger.info(f"Recalled {len(results)} results for query: {query}")
            return results

        except Exception as e:
            logger.error(f"Failed to recall: {e}")
            raise

    def forget(self, memory_id: int) -> bool:
        """Delete a memory by ID.

        Args:
            memory_id: ID of memory to delete

        Returns:
            True if deletion successful, False otherwise

        Example:
            success = api.forget(42)
        """
        try:
            success = self.semantic.delete_memory(memory_id)

            if success:
                logger.info(f"Forgot memory ID: {memory_id}")
            else:
                logger.warning(f"Memory not found: {memory_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to forget: {e}")
            raise

    # ===== EPISODIC MEMORY OPERATIONS =====

    def remember_event(
        self,
        event_type: str,
        content: str,
        outcome: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Store an episodic event (temporal memory with timestamp).

        Args:
            event_type: Type of event (action|decision|observation|error|success)
            content: Event description
            outcome: Outcome status (success|failure|partial|unknown)
            context: Optional context (files, cwd, metadata)

        Returns:
            Event ID

        Example:
            event_id = api.remember_event(
                event_type="action",
                content="Ran integration tests",
                outcome="success",
                context={"test_count": 42, "failures": 0}
            )
        """
        try:
            context = context or {}
            project = self.project_manager.get_or_create_project()

            if not project or not project.id:
                raise RuntimeError("Failed to get/create project")

            event = EpisodicEvent(
                project_id=project.id,
                session_id=context.get("session_id", f"session_{int(datetime.now().timestamp())}"),
                event_type=EventType(event_type),
                content=content,
                timestamp=datetime.now(),
                outcome=EventOutcome(outcome or "unknown"),
                context=EventContext(
                    working_directory=context.get("cwd"),
                    files=context.get("files", []),
                    metadata=context,
                ),
            )

            event_id = self.episodic.store_event(event)
            logger.info(f"Remembered event: {event_type} (ID: {event_id})")
            return event_id

        except Exception as e:
            logger.error(f"Failed to remember event: {e}")
            raise

    def recall_events(
        self,
        query: Optional[str] = None,
        event_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Retrieve events from episodic memory.

        Args:
            query: Optional search query (content-based)
            event_type: Filter by event type
            start_date: Start date range
            end_date: End date range
            limit: Maximum results

        Returns:
            List of events matching criteria

        Example:
            events = api.recall_events(
                event_type="action",
                start_date=datetime.now() - timedelta(days=1)
            )
        """
        try:
            project = self.project_manager.get_or_create_project()
            if not project or not project.id:
                return []

            # Use episodic store query methods
            if query:
                results = self._query_episodic(query, limit)
            else:
                # Query by filters
                results = self.episodic.list_events(
                    project_id=project.id,
                    event_type=event_type,
                    limit=limit,
                )

            logger.info(f"Recalled {len(results)} events")
            return results

        except Exception as e:
            logger.error(f"Failed to recall events: {e}")
            raise

    def _query_episodic(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Internal episodic query helper."""
        try:
            results = self.manager.retrieve(query, k=limit)
            return results.get("episodic", [])
        except Exception:
            return []

    # ===== PROCEDURAL MEMORY OPERATIONS =====

    def remember_procedure(
        self,
        name: str,
        steps: List[str],
        category: str = "general",
        context: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Store a reusable procedure (workflow).

        Args:
            name: Procedure name
            steps: List of procedural steps
            category: Category (general|analysis|optimization|debugging|testing)
            context: Optional context metadata

        Returns:
            Procedure ID

        Example:
            proc_id = api.remember_procedure(
                name="run_tests",
                steps=[
                    "Change to project directory",
                    "Run pytest tests/",
                    "Check coverage"
                ],
                category="testing"
            )
        """
        try:
            context = context or {}
            project = self.project_manager.get_or_create_project()

            if not project or not project.id:
                raise RuntimeError("Failed to get/create project")

            procedure = Procedure(
                project_id=project.id,
                name=name,
                steps=steps,
                category=ProcedureCategory(category),
                created_at=datetime.now(),
                description=context.get("description", ""),
                tags=context.get("tags", []),
            )

            proc_id = self.procedural.store_procedure(procedure)
            logger.info(f"Remembered procedure: {name} (ID: {proc_id})")
            return proc_id

        except Exception as e:
            logger.error(f"Failed to remember procedure: {e}")
            raise

    def recall_procedures(
        self,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Retrieve procedures matching query.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching procedures

        Example:
            procs = api.recall_procedures("testing workflow")
        """
        try:
            results = self.manager.retrieve(query, k=limit)
            procedures = results.get("procedural", [])
            logger.info(f"Recalled {len(procedures)} procedures")
            return procedures

        except Exception as e:
            logger.error(f"Failed to recall procedures: {e}")
            raise

    # ===== PROSPECTIVE MEMORY OPERATIONS =====

    def remember_task(
        self,
        name: str,
        deadline: Optional[datetime] = None,
        priority: str = "medium",
        context: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Store a prospective task (goal/reminder).

        Args:
            name: Task name
            deadline: Optional deadline
            priority: Priority level (low|medium|high|critical)
            context: Optional context metadata

        Returns:
            Task ID

        Example:
            task_id = api.remember_task(
                "Review parser implementation",
                deadline=datetime.now() + timedelta(days=3),
                priority="high"
            )
        """
        try:
            context = context or {}
            project = self.project_manager.get_or_create_project()

            if not project or not project.id:
                raise RuntimeError("Failed to get/create project")

            task = ProspectiveTask(
                project_id=project.id,
                name=name,
                description=context.get("description", ""),
                deadline=deadline,
                priority=TaskPriority(priority),
                phase=TaskPhase(context.get("phase", "planned")),
                status=TaskStatus.PENDING,
                created_at=datetime.now(),
                tags=context.get("tags", []),
            )

            task_id = self.prospective.store_task(task)
            logger.info(f"Remembered task: {name} (ID: {task_id})")
            return task_id

        except Exception as e:
            logger.error(f"Failed to remember task: {e}")
            raise

    def recall_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Retrieve tasks with optional status filter.

        Args:
            status: Task status filter (pending|active|completed|blocked)
            limit: Maximum results

        Returns:
            List of tasks

        Example:
            pending = api.recall_tasks(status="pending")
        """
        try:
            project = self.project_manager.get_or_create_project()
            if not project or not project.id:
                return []

            tasks = self.prospective.list_tasks(
                project_id=project.id,
                status=status,
                limit=limit,
            )

            logger.info(f"Recalled {len(tasks)} tasks")
            return tasks

        except Exception as e:
            logger.error(f"Failed to recall tasks: {e}")
            raise

    # ===== KNOWLEDGE GRAPH OPERATIONS =====

    def remember_entity(
        self,
        name: str,
        entity_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Store an entity in knowledge graph.

        Args:
            name: Entity name
            entity_type: Type (concept|person|place|artifact|system|process)
            context: Optional metadata

        Returns:
            Entity ID

        Example:
            entity_id = api.remember_entity(
                "parser.py",
                "artifact",
                context={"file_path": "src/parser.py"}
            )
        """
        try:
            context = context or {}
            project = self.project_manager.get_or_create_project()

            if not project or not project.id:
                raise RuntimeError("Failed to get/create project")

            entity = Entity(
                project_id=project.id,
                name=name,
                entity_type=EntityType(entity_type),
                description=context.get("description", ""),
                metadata=context.get("metadata", {}),
            )

            entity_id = self.graph.store_entity(entity)
            logger.info(f"Remembered entity: {name} (ID: {entity_id})")
            return entity_id

        except Exception as e:
            logger.error(f"Failed to remember entity: {e}")
            raise

    def relate_entities(
        self,
        source_id: int,
        target_id: int,
        relation_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Create a relation between entities.

        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            relation_type: Type of relation (calls|depends_on|contains|belongs_to|etc)
            context: Optional context

        Returns:
            Relation ID

        Example:
            rel_id = api.relate_entities(
                source_id=1,
                target_id=2,
                relation_type="calls"
            )
        """
        try:
            context = context or {}

            relation = Relation(
                source_id=source_id,
                target_id=target_id,
                relation_type=RelationType(relation_type),
                confidence=context.get("confidence", 1.0),
                metadata=context.get("metadata", {}),
                created_at=datetime.now(),
            )

            relation_id = self.graph.store_relation(relation)
            logger.info(f"Related entities: {source_id} -> {target_id} (ID: {relation_id})")
            return relation_id

        except Exception as e:
            logger.error(f"Failed to relate entities: {e}")
            raise

    def query_graph(
        self,
        query: str,
        limit: int = 5,
    ) -> Dict[str, Any]:
        """Query knowledge graph for entities and relations.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            Dictionary with entities and relations

        Example:
            results = api.query_graph("parser implementation")
        """
        try:
            results = self.manager.retrieve(query, k=limit)
            graph_results = results.get("graph", {})
            logger.info(f"Queried graph: found {len(graph_results)} results")
            return graph_results

        except Exception as e:
            logger.error(f"Failed to query graph: {e}")
            raise

    # ===== CONSOLIDATION OPERATIONS =====

    def consolidate(
        self,
        strategy: str = "balanced",
        days_back: int = 7,
    ) -> Dict[str, Any]:
        """Run consolidation to extract patterns from episodic events.

        Args:
            strategy: Consolidation strategy (balanced|speed|quality|minimal)
            days_back: How many days of events to consolidate

        Returns:
            Consolidation results (patterns extracted, statistics)

        Example:
            results = api.consolidate(strategy="balanced", days_back=7)
            print(f"Extracted {results['patterns_count']} patterns")
        """
        try:
            start_time = datetime.now()

            # Run consolidation with specified strategy
            results = self.consolidation.consolidate(strategy=strategy, days_back=days_back)

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"Consolidation completed in {duration:.2f}s (strategy: {strategy})")

            return {
                "success": True,
                "strategy": strategy,
                "duration_seconds": duration,
                **results,
            }

        except Exception as e:
            logger.error(f"Failed to consolidate: {e}")
            raise

    # ===== META-MEMORY OPERATIONS =====

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about memory system.

        Returns:
            Dictionary with memory stats (counts, sizes, quality metrics)

        Example:
            stats = api.get_memory_stats()
            print(f"Episodic events: {stats['episodic_count']}")
        """
        try:
            project = self.project_manager.get_or_create_project()
            if not project or not project.id:
                return {}

            stats = {
                "episodic_count": self.episodic.count_events(project.id),
                "semantic_count": self.semantic.count_memories(project.id),
                "procedural_count": self.procedural.count_procedures(project.id),
                "prospective_count": self.prospective.count_tasks(project.id),
                "graph_entities": self.graph.count_entities(project.id),
                "graph_relations": self.graph.count_relations(project.id),
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(f"Memory stats: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            raise

    # ===== UTILITY OPERATIONS =====

    def health_check(self) -> Dict[str, Any]:
        """Check health of memory system.

        Returns:
            Health status with any issues

        Example:
            health = api.health_check()
            assert health["status"] == "healthy"
        """
        try:
            # Check database connectivity
            db_healthy = True
            try:
                self.db.execute("SELECT 1")
            except Exception as e:
                logger.warning(f"Database check failed: {e}")
                db_healthy = False

            # Check layer initialization
            layers_healthy = {
                "episodic": True,
                "semantic": True,
                "procedural": True,
                "prospective": True,
                "graph": True,
                "meta": True,
                "consolidation": True,
            }

            overall_healthy = db_healthy and all(layers_healthy.values())

            return {
                "status": "healthy" if overall_healthy else "degraded",
                "database": "ok" if db_healthy else "failed",
                "layers": layers_healthy,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
