"""
Service to manage Athena Phase 3 prospective memory stores.

This service initializes and provides access to:
- ProspectiveStore (Layer 4 task management)
- DependencyStore (task dependencies and blocking)
- MetadataStore (effort estimates, complexity, tags)
- PredictiveEstimator (effort predictions with confidence)
- WorkflowPatternStore (workflow pattern mining)
- PatternSuggestionEngine (smart task suggestions)
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Add Athena src to path
ATHENA_SRC = Path(__file__).parent.parent.parent.parent / "src"
if str(ATHENA_SRC) not in sys.path:
    sys.path.insert(0, str(ATHENA_SRC))


class AthenaStoresService:
    """Manages Athena Phase 3 prospective memory stores."""

    def __init__(self):
        """Initialize the service (stores not yet loaded)."""
        self.prospective_store = None
        self.dependency_store = None
        self.metadata_store = None
        self.predictive_estimator = None
        self.workflow_patterns = None
        self.suggestions_engine = None
        self.db = None
        self._initialized = False

    def initialize(self, db_connection: Optional[Any] = None) -> bool:
        """
        Initialize all Athena stores.

        Args:
            db_connection: Optional pre-configured database connection

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Import Athena components
            from athena.core.database import Database
            from athena.prospective.store import ProspectiveStore
            from athena.prospective.dependencies import DependencyStore
            from athena.prospective.metadata import MetadataStore
            from athena.prospective.triggers import TriggerEvaluator
            from athena.prospective.monitoring import TaskMonitor
            from athena.predictive.estimator import PredictiveEstimator
            from athena.workflow.patterns import WorkflowPatternStore
            from athena.workflow.suggestions import PatternSuggestionEngine
            from athena.workflow.analyzer import TaskTypeClassifier

            # Initialize or use provided database connection
            if db_connection is not None:
                self.db = db_connection
                logger.info("Using provided database connection for Athena stores")
            else:
                # Try to get database from Athena config
                try:
                    from athena.core.config import Settings
                    settings = Settings()
                    self.db = Database(settings)
                    logger.info(f"Initialized Athena database from config")
                except Exception as e:
                    logger.warning(f"Could not initialize from config: {e}, using SQLite fallback")
                    # Fallback to SQLite for development
                    self.db = Database(":memory:")

            # Initialize Phase 4: Prospective Memory stores
            self.prospective_store = ProspectiveStore(self.db)
            logger.info("✓ ProspectiveStore initialized")

            self.dependency_store = DependencyStore(self.db)
            logger.info("✓ DependencyStore initialized")

            self.metadata_store = MetadataStore(self.db)
            logger.info("✓ MetadataStore initialized")

            self.trigger_evaluator = TriggerEvaluator(self.prospective_store)
            logger.info("✓ TriggerEvaluator initialized")

            self.task_monitor = TaskMonitor(self.db)
            logger.info("✓ TaskMonitor initialized")

            # Initialize Phase 3c: Predictive Layer
            self.predictive_estimator = PredictiveEstimator(self.db)
            logger.info("✓ PredictiveEstimator initialized")

            # Initialize Phase 3b: Workflow Patterns
            self.workflow_patterns = WorkflowPatternStore(self.db)
            logger.info("✓ WorkflowPatternStore initialized")

            self.suggestions_engine = PatternSuggestionEngine(self.db)
            logger.info("✓ PatternSuggestionEngine initialized")

            self.task_classifier = TaskTypeClassifier()
            logger.info("✓ TaskTypeClassifier initialized")

            self._initialized = True
            logger.info("✅ All Athena Phase 3 stores initialized successfully")
            return True

        except ImportError as e:
            logger.error(f"❌ Failed to import Athena components: {e}")
            logger.error("Make sure Athena is installed and in the Python path")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to initialize Athena stores: {e}", exc_info=True)
            return False

    def is_initialized(self) -> bool:
        """Check if stores are initialized."""
        return self._initialized

    def close(self) -> None:
        """Close database connection."""
        if self.db:
            try:
                self.db.close()
                logger.info("Athena database connection closed")
            except Exception as e:
                logger.error(f"Error closing Athena database: {e}")

    # ========================================================================
    # Layer 4: Prospective Memory Methods
    # ========================================================================

    def get_tasks_with_metadata(
        self, project_id: Optional[int] = None, status: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get tasks with rich metadata (dependencies, effort, complexity).

        Args:
            project_id: Optional project filter
            status: Optional status filter
            limit: Maximum tasks to return

        Returns:
            List of task dicts with full metadata
        """
        if not self._initialized or not self.prospective_store:
            return []

        try:
            # Get base tasks
            tasks_result = self.prospective_store.list(
                filters={"project_id": project_id} if project_id else {},
                limit=limit,
            )
            tasks = tasks_result if isinstance(tasks_result, list) else tasks_result.get("tasks", [])

            # Enrich each task with metadata
            enriched = []
            for task in tasks:
                task_dict = task.model_dump() if hasattr(task, "model_dump") else task
                task_id = task_dict.get("id")

                if not task_id:
                    enriched.append(task_dict)
                    continue

                # Get dependencies
                dependencies = []
                try:
                    blocking = self.dependency_store.get_blocking_tasks(project_id or 1, task_id)
                    if blocking:
                        dependencies = blocking
                except Exception as e:
                    logger.debug(f"Could not fetch dependencies for task {task_id}: {e}")

                # Get metadata
                metadata = {}
                try:
                    metadata = self.metadata_store.get_task_metadata(project_id or 1, task_id) or {}
                except Exception as e:
                    logger.debug(f"Could not fetch metadata for task {task_id}: {e}")

                # Get blockers (tasks blocking this one)
                blockers = []
                try:
                    is_blocked, blocker_ids = self.dependency_store.is_task_blocked(
                        project_id or 1, task_id
                    )
                    blockers = blocker_ids if is_blocked else []
                except Exception as e:
                    logger.debug(f"Could not check blockers for task {task_id}: {e}")

                # Combine into enriched task
                enriched_task = {
                    **task_dict,
                    "dependencies": dependencies,
                    "blockers": blockers,
                    "blocked": len(blockers) > 0,
                    "effort_estimate": metadata.get("effort_estimate"),
                    "effort_actual": metadata.get("effort_actual"),
                    "complexity_score": metadata.get("complexity_score"),
                    "priority_score": metadata.get("priority_score"),
                    "tags": metadata.get("tags", []),
                    "accuracy_percent": metadata.get("accuracy_percent"),
                }

                enriched.append(enriched_task)

            return enriched

        except Exception as e:
            logger.error(f"Error getting tasks with metadata: {e}", exc_info=True)
            return []

    def get_task_by_id(self, task_id: int, project_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get single task with full metadata."""
        if not self._initialized or not self.prospective_store:
            return None

        try:
            task = self.prospective_store.get(task_id)
            if not task:
                return None

            task_dict = task.model_dump() if hasattr(task, "model_dump") else task

            # Enrich with metadata
            dependencies = self.dependency_store.get_blocking_tasks(project_id or 1, task_id) or []
            is_blocked, blocker_ids = self.dependency_store.is_task_blocked(project_id or 1, task_id)
            metadata = self.metadata_store.get_task_metadata(project_id or 1, task_id) or {}

            return {
                **task_dict,
                "dependencies": dependencies,
                "blockers": blocker_ids,
                "blocked": is_blocked,
                "metadata": metadata,
            }
        except Exception as e:
            logger.error(f"Error getting task {task_id}: {e}")
            return None

    # ========================================================================
    # Phase 3c: Predictive Estimation Methods
    # ========================================================================

    def get_effort_predictions(
        self, task_id: int, project_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get effort prediction with confidence score.

        Args:
            task_id: Task to predict
            project_id: Project context

        Returns:
            Prediction dict with effort range and confidence
        """
        if not self._initialized or not self.predictive_estimator:
            return None

        try:
            task = self.prospective_store.get(task_id)
            if not task:
                return None

            # Get task metadata for task type classification
            metadata = self.metadata_store.get_task_metadata(project_id or 1, task_id) or {}
            base_estimate = metadata.get("effort_estimate", 120)

            # Classify task type
            task_type = self.task_classifier.classify(
                content=getattr(task, "content", ""),
                tags=metadata.get("tags"),
            )

            # Get prediction
            prediction = self.predictive_estimator.predict_effort(
                project_id=project_id or 1,
                task_type=task_type,
                base_estimate=base_estimate,
            )

            return prediction or {"predicted_effort": base_estimate, "confidence": 0.0}

        except Exception as e:
            logger.error(f"Error predicting effort for task {task_id}: {e}")
            return None

    def get_predictions_for_tasks(
        self, task_ids: List[int], project_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get predictions for multiple tasks."""
        return [
            self.get_effort_predictions(task_id, project_id) for task_id in task_ids if task_id
        ]

    # ========================================================================
    # Phase 3b: Workflow Pattern Methods
    # ========================================================================

    def get_task_suggestions(
        self, completed_task_id: int, project_id: Optional[int] = None, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get suggested next tasks based on workflow patterns.

        Args:
            completed_task_id: Recently completed task
            project_id: Project context
            limit: Number of suggestions

        Returns:
            List of suggested tasks with confidence scores
        """
        if not self._initialized or not self.suggestions_engine:
            return []

        try:
            suggestions = self.suggestions_engine.suggest_next_task_with_patterns(
                project_id=project_id or 1,
                completed_task_id=completed_task_id,
                limit=limit,
            )

            return suggestions or []

        except Exception as e:
            logger.error(f"Error getting suggestions: {e}")
            return []

    def get_typical_workflow_steps(
        self, task_type: str, project_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get typical workflow sequence for task type."""
        if not self._initialized or not self.suggestions_engine:
            return []

        try:
            steps = self.suggestions_engine.get_typical_workflow_steps(
                project_id=project_id or 1,
                task_type=task_type,
                confidence_threshold=0.5,
            )
            return steps or []
        except Exception as e:
            logger.error(f"Error getting workflow steps: {e}")
            return []

    # ========================================================================
    # Project Analytics
    # ========================================================================

    def get_project_analytics(self, project_id: int) -> Dict[str, Any]:
        """
        Get comprehensive project analytics from metadata.

        Args:
            project_id: Project to analyze

        Returns:
            Analytics dict with effort trends, accuracy, complexity
        """
        if not self._initialized or not self.metadata_store:
            return {}

        try:
            analytics = self.metadata_store.get_project_analytics(project_id)
            return analytics or {}
        except Exception as e:
            logger.error(f"Error getting project analytics: {e}")
            return {}

    def get_unblocked_ready_tasks(
        self, project_id: int, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get tasks that are ready to work on (unblocked, pending)."""
        if not self._initialized or not self.dependency_store:
            return []

        try:
            tasks = self.dependency_store.get_unblocked_tasks(
                project_id=project_id,
                statuses=["pending"],
                limit=limit,
            )
            return tasks or []
        except Exception as e:
            logger.error(f"Error getting unblocked tasks: {e}")
            return []
