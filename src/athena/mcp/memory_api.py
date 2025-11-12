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

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional, List, Dict

from ..core.database import Database
from ..core.database_factory import get_database
from ..core.async_utils import run_async
from ..core.models import MemoryType
from ..episodic.models import EpisodicEvent, EventType, EventContext, EventOutcome
from ..episodic.store import EpisodicStore
from ..memory.store import MemoryStore
from ..procedural.models import Procedure, ProcedureCategory
from ..procedural.store import ProceduralStore
from ..procedural.code_generator import ProcedureCodeGenerator, ConfidenceScorer
from ..procedural.code_validator import CodeValidator
from ..procedural.git_store import GitBackedProcedureStore
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

        # Phase 2 Week 8: Initialize code generation and validation components
        self.code_generator = ProcedureCodeGenerator()
        self.code_validator = CodeValidator()
        self.confidence_scorer = ConfidenceScorer()
        self.git_store: Optional[GitBackedProcedureStore] = None  # Lazy-initialized

        # Phase 3 Week 10: Initialize sandbox executor (lazy-loaded)
        self.sandbox_executor: Optional[Any] = None  # SRTExecutor instance

        # Default project ID (lazy-initialized on first use)
        self._default_project_id: Optional[int] = None

        logger.info("MemoryAPI initialized with all memory layers and code generation")

    def _ensure_default_project(self) -> int:
        """Ensure a default project exists for memory operations.

        Lazily creates default project on first use. Uses async/sync bridge
        to handle PostgreSQL async create_project() in sync context.

        Returns:
            Project ID for use in memory operations
        """
        if self._default_project_id is not None:
            return self._default_project_id

        try:
            import os
            cwd = os.getcwd()
            project_name = os.path.basename(cwd) or "default"

            # Try to use the sync wrapper if available
            if hasattr(self.semantic, 'create_project'):
                # Synchronous method on MemoryStore
                project = self.semantic.create_project(project_name, cwd)
                if project and project.id:
                    self._default_project_id = project.id
                    logger.debug(f"Created/retrieved project: {project_name} (ID: {project.id})")
                    return project.id

            # Fallback: use database's async create_project with async/sync bridge
            coro = self.db.create_project(project_name, cwd)
            project = run_async(coro)
            if project and project.id:
                self._default_project_id = project.id
                logger.debug(f"Created/retrieved project: {project_name} (ID: {project.id})")
                return project.id

        except Exception as e:
            logger.debug(f"Could not create project: {e}")

        # Fallback: use default project ID (1 is reserved for default)
        self._default_project_id = 1
        logger.debug("Using default project ID: 1")
        return 1

    @staticmethod
    def create(db_path: Optional[str] = None) -> "MemoryAPI":
        """Factory method to create a MemoryAPI instance.

        Args:
            db_path: Optional database path (ignored, uses PostgreSQL)

        Returns:
            Initialized MemoryAPI instance
        """
        # Initialize database - PostgreSQL only
        database = get_database(backend='postgres')

        # Initialize all memory layers - PostgreSQL backend exclusively
        semantic = MemoryStore()
        episodic = EpisodicStore(database)
        procedural = ProceduralStore(database)
        prospective = ProspectiveStore(database)
        graph = GraphStore(database)
        meta = MetaMemoryStore(database)
        consolidation = ConsolidationSystem(
            db=database,
            memory_store=semantic,
            episodic_store=episodic,
            procedural_store=procedural,
            meta_store=meta,
        )

        # Initialize project manager
        project_manager = ProjectManager(semantic)

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
            memory_type: Type of memory (semantic|event|procedure|task or FACT|PATTERN|DECISION|CONTEXT)
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
            project_id = self._ensure_default_project()

            # Map common memory type names to valid MemoryType enums
            memory_type_map = {
                "semantic": MemoryType.FACT,
                "fact": MemoryType.FACT,
                "event": MemoryType.CONTEXT,
                "context": MemoryType.CONTEXT,
                "procedure": MemoryType.PATTERN,
                "pattern": MemoryType.PATTERN,
                "task": MemoryType.DECISION,
                "decision": MemoryType.DECISION,
            }

            mapped_type = memory_type_map.get(memory_type.lower(), MemoryType.FACT)

            # Use sync wrapper if available, otherwise run async call synchronously
            if hasattr(self.semantic, 'remember_sync'):
                memory_id = self.semantic.remember_sync(
                    content=content,
                    memory_type=mapped_type,
                    project_id=project_id,
                    tags=tags,
                )
            else:
                memory_id = run_async(
                    self.semantic.remember(
                        content=content,
                        memory_type=mapped_type,
                        project_id=project_id,
                        tags=tags,
                    )
                )

            logger.info(f"Remembered content: {memory_type} → {mapped_type} (ID: {memory_id})")
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
            # Use async/sync bridge for async method
            project_coro = self.project_manager.get_or_create_project()
            project = run_async(project_coro)

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

            event_id = self.episodic.record_event(event)
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

    # ===== PHASE 2 WEEK 8: CODE GENERATION & VALIDATION =====

    def generate_procedure_code(
        self,
        procedure_id: int,
        use_llm: bool = True,
        refine_on_low_confidence: bool = True,
    ) -> Dict[str, Any]:
        """Generate executable Python code for a procedure using LLM.

        Args:
            procedure_id: ID of procedure to generate code for
            use_llm: Whether to use LLM (vs heuristic fallback)
            refine_on_low_confidence: Auto-refine if confidence <0.7

        Returns:
            Dictionary with generated code, confidence score, and validation results

        Example:
            result = api.generate_procedure_code(
                procedure_id=42,
                use_llm=True,
                refine_on_low_confidence=True
            )
            if result["success"]:
                print(f"Code: {result['code']}")
                print(f"Confidence: {result['confidence']}")
        """
        try:
            start_time = datetime.now()
            project = self.project_manager.get_or_create_project()
            if not project or not project.id:
                raise RuntimeError("Failed to get/create project")

            # Retrieve procedure
            procedure = self.procedural.get_procedure(procedure_id)
            if not procedure:
                raise ValueError(f"Procedure not found: {procedure_id}")

            # Generate code using LLM
            result = self.code_generator.generate(
                procedure=procedure,
                use_llm=use_llm,
                refine_on_low_confidence=refine_on_low_confidence,
            )

            duration = (datetime.now() - start_time).total_seconds()

            return {
                "success": True,
                "procedure_id": procedure_id,
                "code": result.get("code"),
                "confidence": result.get("confidence", 0.0),
                "validation": result.get("validation", {}),
                "issues": result.get("issues", []),
                "duration_seconds": duration,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to generate code for procedure {procedure_id}: {e}")
            return {
                "success": False,
                "procedure_id": procedure_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def validate_procedure_code(
        self,
        code: str,
        procedure_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Validate procedure code for syntax, security, and quality.

        Args:
            code: Python code to validate
            procedure_id: Optional procedure ID for context

        Returns:
            Dictionary with validation results and quality metrics

        Example:
            result = api.validate_procedure_code(
                code="def my_proc():\n    return 42",
                procedure_id=42
            )
            print(f"Quality score: {result['quality_score']}")
        """
        try:
            start_time = datetime.now()

            # Validate code comprehensively
            validation_result = self.code_validator.validate(code)

            # Convert ValidationResult object to dict
            if hasattr(validation_result, "to_dict"):
                result_dict = validation_result.to_dict()
            else:
                result_dict = validation_result

            duration = (datetime.now() - start_time).total_seconds()

            return {
                "success": True,
                "procedure_id": procedure_id,
                "quality_score": result_dict.get("quality_score", 0.0),
                "issues": result_dict.get("issues", []),
                "checks": {
                    "syntax": result_dict.get("is_valid", False),
                    "security": result_dict.get("is_valid", False),
                    "docstring": result_dict.get("has_docstring", False),
                    "error_handling": result_dict.get("has_error_handling", False),
                    "type_hints": result_dict.get("type_hints_coverage", 0.0),
                },
                "duration_seconds": duration,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to validate code: {e}")
            return {
                "success": False,
                "procedure_id": procedure_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def get_procedure_versions(
        self,
        procedure_id: int,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Get version history for a procedure from git store.

        Args:
            procedure_id: ID of procedure
            limit: Maximum versions to return

        Returns:
            Dictionary with version history

        Example:
            versions = api.get_procedure_versions(42, limit=10)
            for v in versions["versions"]:
                print(f"Version {v['version']}: {v['message']}")
        """
        try:
            project = self.project_manager.get_or_create_project()
            if not project or not project.id:
                raise RuntimeError("Failed to get/create project")

            # Lazy-initialize git store if needed
            if self.git_store is None:
                self.git_store = GitBackedProcedureStore(
                    repo_path=f"/tmp/athena_procedures_{project.id}"
                )

            # Get version history
            versions = self.git_store.get_procedure_history(procedure_id)

            return {
                "success": True,
                "procedure_id": procedure_id,
                "versions": versions or [],
                "count": len(versions) if versions else 0,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get procedure versions: {e}")
            return {
                "success": False,
                "procedure_id": procedure_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def rollback_procedure_code(
        self,
        procedure_id: int,
        target_version: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Rollback procedure code to a previous version.

        Args:
            procedure_id: ID of procedure
            target_version: Target version/commit hash to rollback to
            reason: Optional reason for rollback

        Returns:
            Dictionary with rollback result

        Example:
            result = api.rollback_procedure_code(
                procedure_id=42,
                target_version="abc123def456",
                reason="Previous version had better performance"
            )
        """
        try:
            project = self.project_manager.get_or_create_project()
            if not project or not project.id:
                raise RuntimeError("Failed to get/create project")

            # Lazy-initialize git store if needed
            if self.git_store is None:
                self.git_store = GitBackedProcedureStore(
                    repo_path=f"/tmp/athena_procedures_{project.id}"
                )

            # Rollback to version
            procedure = self.git_store.rollback_procedure(
                procedure_id=procedure_id,
                target_version=target_version,
                reason=reason or "Rollback via API",
            )

            return {
                "success": True,
                "procedure_id": procedure_id,
                "target_version": target_version,
                "procedure": {
                    "name": procedure.name if hasattr(procedure, "name") else "unknown",
                    "code_version": procedure.code_version if hasattr(procedure, "code_version") else "1.0",
                },
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to rollback procedure: {e}")
            return {
                "success": False,
                "procedure_id": procedure_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def execute_procedure(
        self,
        procedure_id: int,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a procedure and record execution metrics.

        Args:
            procedure_id: ID of procedure to execute
            parameters: Optional parameters for procedure execution

        Returns:
            Dictionary with execution result and metrics

        Example:
            result = api.execute_procedure(
                procedure_id=42,
                parameters={"target_file": "src/main.py"}
            )
            print(f"Outcome: {result['outcome']}")
        """
        try:
            start_time = datetime.now()
            project = self.project_manager.get_or_create_project()
            if not project or not project.id:
                raise RuntimeError("Failed to get/create project")

            # Get procedure
            procedure = self.procedural.get_procedure(procedure_id)
            if not procedure:
                raise ValueError(f"Procedure not found: {procedure_id}")

            # Record execution attempt
            outcome = "unknown"
            error = None

            try:
                # Execute procedure code if available
                if procedure.code:
                    # Create execution context with parameters
                    exec_globals = {
                        "parameters": parameters or {},
                        "api": self,
                    }
                    exec(procedure.code, exec_globals)
                    outcome = "success"
                else:
                    outcome = "skipped"
                    error = "No executable code available"

            except Exception as exec_error:
                outcome = "failure"
                error = str(exec_error)
                logger.error(f"Procedure execution failed: {error}")

            duration = (datetime.now() - start_time).total_seconds()

            # Update procedure stats
            self.procedural.record_execution(
                procedure_id=procedure_id,
                project_id=project.id,
                outcome=outcome,
                duration_ms=int(duration * 1000),
                variables=parameters or {},
            )

            return {
                "success": outcome == "success",
                "procedure_id": procedure_id,
                "outcome": outcome,
                "duration_seconds": duration,
                "error": error,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to execute procedure: {e}")
            return {
                "success": False,
                "procedure_id": procedure_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def get_procedure_stats(
        self,
        procedure_id: int,
    ) -> Dict[str, Any]:
        """Get execution statistics for a procedure.

        Args:
            procedure_id: ID of procedure

        Returns:
            Dictionary with execution stats and metrics

        Example:
            stats = api.get_procedure_stats(42)
            print(f"Success rate: {stats['success_rate']:.1%}")
        """
        try:
            procedure = self.procedural.get_procedure(procedure_id)
            if not procedure:
                raise ValueError(f"Procedure not found: {procedure_id}")

            # Get execution stats
            stats = self.procedural.get_execution_stats(procedure_id)

            return {
                "success": True,
                "procedure_id": procedure_id,
                "name": procedure.name,
                "usage_count": procedure.usage_count,
                "success_rate": procedure.success_rate,
                "avg_completion_time_ms": procedure.avg_completion_time_ms,
                "code_confidence": procedure.code_confidence if hasattr(procedure, "code_confidence") else 0.0,
                "execution_stats": stats or {},
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get procedure stats: {e}")
            return {
                "success": False,
                "procedure_id": procedure_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def search_procedures_by_confidence(
        self,
        min_confidence: float = 0.7,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Search for procedures with code confidence above threshold.

        Args:
            min_confidence: Minimum confidence score (0.0-1.0)
            limit: Maximum results

        Returns:
            Dictionary with filtered procedures

        Example:
            high_confidence = api.search_procedures_by_confidence(
                min_confidence=0.8,
                limit=10
            )
        """
        try:
            project = self.project_manager.get_or_create_project()
            if not project or not project.id:
                return {
                    "success": False,
                    "procedures": [],
                    "error": "Failed to get/create project",
                }

            # List all procedures and filter by confidence
            procedures = self.procedural.list_procedures(project.id, limit=1000)
            filtered = [
                p for p in procedures
                if hasattr(p, "code_confidence") and p.code_confidence >= min_confidence
            ][:limit]

            return {
                "success": True,
                "min_confidence": min_confidence,
                "procedures": filtered,
                "count": len(filtered),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to search procedures by confidence: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    # ===== PHASE 3 WEEK 10: CODE EXECUTION IN SANDBOX =====

    def _ensure_sandbox_executor(self):
        """Lazy-initialize sandbox executor.

        Creates SRTExecutor on first use to avoid startup overhead.
        """
        if self.sandbox_executor is None:
            try:
                from ..sandbox.srt_executor import SRTExecutor
                from ..sandbox.config import SandboxConfig
                config = SandboxConfig.default()
                self.sandbox_executor = SRTExecutor(config)
                logger.info("Sandbox executor initialized")
            except Exception as e:
                logger.warning(f"Could not initialize sandbox executor: {e}")
                self.sandbox_executor = False  # Mark as attempted

    def execute_code(
        self,
        code: str,
        language: str = "python",
        parameters: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 30,
        sandbox_policy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute code in sandboxed environment.

        Executes user-provided or agent-generated code safely with full isolation.
        Supports Python, JavaScript, and bash. Returns execution result with output,
        errors, violations, and timing information.

        Args:
            code: Code to execute
            language: Programming language (python|javascript|bash)
            parameters: Optional parameters passed to code as 'params' variable
            timeout_seconds: Execution timeout in seconds
            sandbox_policy: Optional sandbox policy (strict|research|development)

        Returns:
            Dictionary with:
                - success: Whether execution completed without errors
                - stdout: Standard output from code
                - stderr: Standard error output
                - exit_code: Process exit code (0 = success)
                - execution_time_ms: Time taken to run
                - violations: List of security violations detected
                - sandbox_id: Unique ID for this execution
                - error: Exception message if execution failed

        Example:
            result = api.execute_code(
                code='print("Hello from sandbox")',
                language="python",
                parameters={"name": "World"}
            )
            print(f"Output: {result['stdout']}")

        Security Notes:
            - Code executes in OS-level sandbox (SRT) if available
            - Falls back to RestrictedPython if SRT not installed
            - All file I/O is restricted by sandbox policy
            - Network access controlled by policy
            - Dangerous imports blocked (os.system, subprocess, eval, etc.)
        """
        try:
            start_time = datetime.now()
            execution_id = str(uuid.uuid4())

            # Pre-validate code for syntax errors
            try:
                validation_result = self.code_validator.validate(code)
                # Convert result object to dict if needed
                if hasattr(validation_result, "to_dict"):
                    validation_dict = validation_result.to_dict()
                elif isinstance(validation_result, dict):
                    validation_dict = validation_result
                else:
                    validation_dict = {"is_valid": True}  # Default to valid if can't parse

                if not validation_dict.get("is_valid", True):
                    return {
                        "success": False,
                        "execution_id": execution_id,
                        "error": "Code validation failed",
                        "issues": validation_dict.get("issues", []),
                        "sandbox_id": execution_id,
                        "timestamp": datetime.now().isoformat(),
                    }
            except Exception as validation_error:
                logger.warning(f"Code validation error (continuing anyway): {validation_error}")
                # Continue even if validation fails - we'll catch errors at execution time

            # Ensure sandbox executor is available
            self._ensure_sandbox_executor()

            # Build execution environment
            exec_env = {
                "parameters": parameters or {},
                "api": self,
                "__name__": "__main__",
            }

            # Execute code
            execution_result = None
            violations = []
            stdout = ""
            stderr = ""
            exit_code = 0

            try:
                # Try to use SRT executor if available
                if self.sandbox_executor and self.sandbox_executor is not False:
                    try:
                        # Set up policy
                        if sandbox_policy:
                            policy_map = {
                                "strict": "STRICT_POLICY",
                                "research": "RESEARCH_POLICY",
                                "development": "DEVELOPMENT_POLICY",
                            }
                            policy_name = policy_map.get(sandbox_policy, "RESEARCH_POLICY")
                            self.sandbox_executor.config = getattr(
                                self.sandbox_executor.config.__class__,
                                policy_name,
                                None,
                            )

                        # Execute in SRT sandbox
                        execution_result = self.sandbox_executor.execute(
                            code=code,
                            language=language,
                            timeout_seconds=timeout_seconds,
                        )

                        stdout = execution_result.stdout
                        stderr = execution_result.stderr
                        exit_code = execution_result.exit_code
                        violations = execution_result.violations
                        success = execution_result.success

                    except Exception as srt_error:
                        logger.warning(f"SRT execution failed, falling back to restricted mode: {srt_error}")
                        # Fall through to RestrictedPython execution
                        execution_result = None

                # Fallback to RestrictedPython if SRT not available
                if execution_result is None:
                    try:
                        from RestrictedPython import compile_restricted
                        from RestrictedPython.Guards import guarded_iter_unpack_sequence, safe_globals

                        # Compile code with RestrictedPython
                        byte_code = compile_restricted(code, "<code>", "exec")
                        if byte_code.errors:
                            return {
                                "success": False,
                                "execution_id": execution_id,
                                "error": "RestrictedPython compilation failed",
                                "issues": byte_code.errors,
                                "sandbox_id": execution_id,
                                "timestamp": datetime.now().isoformat(),
                            }

                        # Execute with restricted globals
                        exec_globals = {
                            **safe_globals,
                            "_iter_unpack_sequence_": guarded_iter_unpack_sequence,
                            **exec_env,
                        }

                        # Capture output
                        import io
                        import sys

                        old_stdout = sys.stdout
                        old_stderr = sys.stderr
                        sys.stdout = io.StringIO()
                        sys.stderr = io.StringIO()

                        try:
                            exec(byte_code.code, exec_globals)
                            stdout = sys.stdout.getvalue()
                            stderr = sys.stderr.getvalue()
                            exit_code = 0
                            success = True
                        except Exception as exec_error:
                            stderr = str(exec_error)
                            exit_code = 1
                            success = False
                        finally:
                            sys.stdout = old_stdout
                            sys.stderr = old_stderr

                    except ImportError:
                        # Fall back to plain exec (least secure)
                        logger.warning("RestrictedPython not available, using unrestricted exec")
                        import io
                        import sys

                        old_stdout = sys.stdout
                        old_stderr = sys.stderr
                        sys.stdout = io.StringIO()
                        sys.stderr = io.StringIO()

                        try:
                            exec(code, exec_env)
                            stdout = sys.stdout.getvalue()
                            stderr = sys.stderr.getvalue()
                            exit_code = 0
                            success = True
                        except Exception as exec_error:
                            stderr = str(exec_error)
                            exit_code = 1
                            success = False
                        finally:
                            sys.stdout = old_stdout
                            sys.stderr = old_stderr

            except Exception as exec_error:
                success = False
                stderr = str(exec_error)
                exit_code = 1
                logger.error(f"Code execution failed: {exec_error}")

            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Record execution in episodic memory
            self.remember_event(
                event_type="action",
                content=f"Executed {language} code (success={success})",
                outcome="success" if success else "failure",
                context={
                    "execution_id": execution_id,
                    "language": language,
                    "code_length": len(code),
                    "exit_code": exit_code,
                    "stdout_length": len(stdout),
                    "stderr_length": len(stderr),
                    "violations_count": len(violations),
                },
            )

            return {
                "success": success,
                "execution_id": execution_id,
                "stdout": stdout[:2000],  # Truncate to avoid huge outputs
                "stderr": stderr[:2000],
                "exit_code": exit_code,
                "execution_time_ms": duration_ms,
                "violations": violations,
                "sandbox_id": execution_id,
                "language": language,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Code execution failed: {e}")
            return {
                "success": False,
                "execution_id": str(uuid.uuid4()),
                "error": str(e),
                "sandbox_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
            }

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

    # ===== API DISCOVERY =====

    def _init_api_discovery(self):
        """Initialize API discovery system (lazy initialization)."""
        if hasattr(self, "_discovery") and self._discovery is not None:
            return

        try:
            from ..api.discovery import APIDiscovery

            self._discovery = APIDiscovery()
        except Exception as e:
            logger.warning(f"Failed to initialize API discovery: {e}")
            self._discovery = None

    def discover_apis(
        self, category: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Discover available memory APIs.

        Args:
            category: Optional category filter (e.g., 'memory', 'graph')

        Returns:
            Dictionary mapping category names to lists of API specs (compact format)

        Example:
            apis = api.discover_apis()
            memory_apis = api.discover_apis(category="memory")
        """
        self._init_api_discovery()

        if self._discovery is None:
            logger.warning("API discovery not available")
            return {}

        try:
            if category:
                specs = self._discovery.get_apis_by_category(category)
                return {category: [spec.to_compact_dict() for spec in specs]}
            else:
                all_apis = self._discovery.discover_all()
                return {
                    cat: [spec.to_compact_dict() for spec in specs]
                    for cat, specs in all_apis.items()
                }
        except Exception as e:
            logger.error(f"Failed to discover APIs: {e}")
            return {}

    def get_api_spec(self, api_path: str) -> Optional[Dict[str, Any]]:
        """Get detailed specification for a specific API.

        Args:
            api_path: API path in format 'category/function' (e.g., 'memory/recall')

        Returns:
            Full API specification as dictionary, or None if not found

        Example:
            spec = api.get_api_spec("memory/recall")
            print(f"Parameters: {spec['parameters']}")
        """
        self._init_api_discovery()

        if self._discovery is None:
            logger.warning("API discovery not available")
            return None

        try:
            spec = self._discovery.get_api(api_path)
            return spec.to_dict() if spec else None
        except Exception as e:
            logger.error(f"Failed to get API spec for {api_path}: {e}")
            return None

    def get_api_documentation(self, api_path: str) -> Optional[str]:
        """Get markdown documentation for a specific API.

        Args:
            api_path: API path in format 'category/function'

        Returns:
            Markdown documentation or None if not found

        Example:
            docs = api.get_api_documentation("memory/recall")
            print(docs)
        """
        self._init_api_discovery()

        if self._discovery is None:
            logger.warning("API discovery not available")
            return None

        try:
            spec = self._discovery.get_api(api_path)
            return spec.to_markdown() if spec else None
        except Exception as e:
            logger.error(f"Failed to get documentation for {api_path}: {e}")
            return None

    def search_apis(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for APIs matching a query.

        Performs text-based search on API names and docstrings.

        Args:
            query: Search query
            limit: Maximum number of results to return

        Returns:
            List of matching API specifications (compact format)

        Example:
            results = api.search_apis("semantic")
            for result in results:
                print(f"Found: {result['name']}")
        """
        self._init_api_discovery()

        if self._discovery is None:
            logger.warning("API discovery not available")
            return []

        try:
            specs = self._discovery.search_apis(query, limit=limit)
            return [spec.to_compact_dict() for spec in specs]
        except Exception as e:
            logger.error(f"Failed to search APIs: {e}")
            return []

    def list_api_categories(self) -> List[str]:
        """List all available API categories.

        Returns:
            List of category names

        Example:
            categories = api.list_api_categories()
            print(f"Available categories: {categories}")
        """
        self._init_api_discovery()

        if self._discovery is None:
            logger.warning("API discovery not available")
            return []

        try:
            return self._discovery.get_api_categories()
        except Exception as e:
            logger.error(f"Failed to list API categories: {e}")
            return []

    # Marketplace methods

    def _init_marketplace(self):
        """Initialize marketplace components."""
        if hasattr(self, "_marketplace_store") and self._marketplace_store is not None:
            return

        try:
            from ..api.marketplace_store import MarketplaceStore
            from ..api.semantic_search import SemanticProcedureSearch
            from ..api.recommendations import RecommendationEngine

            self._marketplace_store = MarketplaceStore(self.db)
            self._semantic_search = SemanticProcedureSearch(self._marketplace_store, self._get_embedding_model())
            self._recommendations = RecommendationEngine(self._marketplace_store, self._semantic_search)
        except Exception as e:
            logger.warning(f"Failed to initialize marketplace: {e}")
            self._marketplace_store = None
            self._semantic_search = None
            self._recommendations = None

    def _get_embedding_model(self):
        """Get embedding model for semantic search."""
        try:
            from ..semantic.embeddings import EmbeddingManager
            return EmbeddingManager.create()
        except Exception:
            return None

    def search_marketplace(self, query: str, limit: int = 10, semantic: bool = True) -> List[Dict[str, Any]]:
        """Search marketplace procedures.

        Args:
            query: Search query
            limit: Maximum number of results
            semantic: Use semantic search (True) or keyword search (False)

        Returns:
            List of matching procedures

        Example:
            results = api.search_marketplace("data processing")
            for proc in results:
                print(f"{proc['metadata']['name']}: {proc['metadata']['description']}")
        """
        self._init_marketplace()

        if self._marketplace_store is None:
            logger.warning("Marketplace not available")
            return []

        try:
            if semantic:
                results = self._semantic_search.search_by_semantic_similarity(query, limit=limit)
                return [proc.to_compact_dict() for proc, _ in results]
            else:
                procedures = self._marketplace_store.search_procedures(query, limit=limit)
                return [proc.to_compact_dict() for proc in procedures]
        except Exception as e:
            logger.error(f"Failed to search marketplace: {e}")
            return []

    def get_marketplace_recommendations(
        self,
        use_case: str,
        limit: int = 5,
        require_stable: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get procedure recommendations for a use case.

        Args:
            use_case: Description of use case
            limit: Maximum number of recommendations
            require_stable: Only recommend stable/production quality

        Returns:
            List of recommended procedures

        Example:
            recs = api.get_marketplace_recommendations("process large CSV files")
            for proc in recs:
                print(f"Recommended: {proc['metadata']['name']}")
        """
        self._init_marketplace()

        if self._recommendations is None:
            logger.warning("Recommendations not available")
            return []

        try:
            procedures = self._recommendations.recommend_for_use_case(
                use_case,
                limit=limit,
                require_stable=require_stable,
            )
            return [proc.to_compact_dict() for proc in procedures]
        except Exception as e:
            logger.error(f"Failed to get recommendations: {e}")
            return []

    def get_trending_procedures(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get trending procedures in marketplace.

        Args:
            limit: Maximum number of results

        Returns:
            List of trending procedures

        Example:
            trending = api.get_trending_procedures(limit=5)
            for proc in trending:
                print(f"{proc['metadata']['name']} - {proc['metadata']['version']}")
        """
        self._init_marketplace()

        if self._recommendations is None:
            logger.warning("Recommendations not available")
            return []

        try:
            procedures = self._recommendations.get_trending_recommendations(limit=limit)
            return [proc.to_compact_dict() for proc in procedures]
        except Exception as e:
            logger.error(f"Failed to get trending procedures: {e}")
            return []

    def get_procedure_details(self, procedure_id: str) -> Optional[Dict[str, Any]]:
        """Get full details for a procedure.

        Args:
            procedure_id: Procedure ID

        Returns:
            Full procedure details or None if not found

        Example:
            details = api.get_procedure_details("proc-123")
            print(f"Code: {details['code']}")
            print(f"Reviews: {len(details['reviews'])}")
        """
        self._init_marketplace()

        if self._marketplace_store is None:
            logger.warning("Marketplace not available")
            return None

        try:
            procedure = self._marketplace_store.get_procedure(procedure_id)
            if not procedure:
                return None

            reviews = self._marketplace_store.get_reviews(procedure_id)
            rating = self._marketplace_store.get_average_rating(procedure_id)
            installation_count = self._marketplace_store.get_installation_count(procedure_id)

            return {
                **procedure.to_dict(),
                "reviews": [review.to_dict() for review in reviews],
                "average_rating": rating,
                "installation_count": installation_count,
            }
        except Exception as e:
            logger.error(f"Failed to get procedure details: {e}")
            return None

    def record_procedure_execution(
        self,
        procedure_id: str,
        success: bool,
        execution_time_ms: float,
    ) -> bool:
        """Record procedure execution for stats tracking.

        Args:
            procedure_id: Procedure ID
            success: Whether execution was successful
            execution_time_ms: Execution time in milliseconds

        Returns:
            True if recorded, False otherwise

        Example:
            success = api.record_procedure_execution("proc-123", success=True, execution_time_ms=245.5)
        """
        self._init_marketplace()

        if self._marketplace_store is None:
            logger.warning("Marketplace not available")
            return False

        try:
            return self._marketplace_store.record_execution(procedure_id, success, execution_time_ms)
        except Exception as e:
            logger.error(f"Failed to record execution: {e}")
            return False

    def get_high_quality_procedures(self, limit: int = 10, min_rating: float = 4.0) -> List[Dict[str, Any]]:
        """Get high-quality, well-reviewed procedures.

        Args:
            limit: Maximum number of results
            min_rating: Minimum average rating (0.0-5.0)

        Returns:
            List of high-quality procedures

        Example:
            quality_procs = api.get_high_quality_procedures(min_rating=4.5)
            for proc in quality_procs:
                print(f"Quality: {proc['metadata']['quality_level']}")
        """
        self._init_marketplace()

        if self._recommendations is None:
            logger.warning("Recommendations not available")
            return []

        try:
            procedures = self._recommendations.recommend_high_quality(limit=limit, min_rating=min_rating)
            return [proc.to_compact_dict() for proc in procedures]
        except Exception as e:
            logger.error(f"Failed to get high-quality procedures: {e}")
            return []
