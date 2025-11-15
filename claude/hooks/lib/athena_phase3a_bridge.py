"""Bridge between hook libraries and main Athena Phase 3a.

This module provides a unified interface that:
1. Uses main Athena Phase 3a stores when available
2. Falls back to local implementations if Athena unavailable
3. Keeps hooks/lib independent but integrated

Usage in hooks:
    from athena_phase3a_bridge import get_dependency_manager, get_metadata_manager

    dep_mgr = get_dependency_manager()
    meta_mgr = get_metadata_manager()
"""

import sys
import os
from typing import Optional, Tuple, List, Dict, Any

# Try to import from main Athena codebase
try:
    # Add Athena source to path
    athena_path = "/home/user/.work/athena/src"
    if athena_path not in sys.path:
        sys.path.insert(0, athena_path)

    from athena.core.database import Database
    from athena.prospective.dependencies import DependencyStore
    from athena.prospective.metadata import MetadataStore
    from athena.core.config import DatabaseConfig

    ATHENA_AVAILABLE = True
except ImportError as e:
    print(f"⚠ Athena Phase 3a not available, falling back to local: {e}")
    ATHENA_AVAILABLE = False
    DependencyStore = None
    MetadataStore = None


class DependencyManagerBridge:
    """Bridge for dependency management.

    Uses Athena DependencyStore when available, otherwise local implementation.
    """

    def __init__(self):
        """Initialize bridge with Athena or fallback."""
        self.use_athena = ATHENA_AVAILABLE
        self.store = None

        if ATHENA_AVAILABLE:
            try:
                config = DatabaseConfig()
                db = Database(config)
                self.store = DependencyStore(db)
            except Exception as e:
                print(f"⚠ Failed to initialize Athena Phase 3a: {e}", file=sys.stderr)
                self.use_athena = False

    def create_dependency(
        self, project_id: int, from_task_id: int, to_task_id: int,
        dependency_type: str = "blocks"
    ) -> Optional[int]:
        """Create dependency via Athena or local."""
        if self.use_athena and self.store:
            return self.store.create_dependency(
                project_id, from_task_id, to_task_id, dependency_type
            )
        else:
            # Fallback to local implementation
            from task_dependency_manager import TaskDependencyManager
            mgr = TaskDependencyManager()
            result = mgr.create_dependency(
                project_id, from_task_id, to_task_id, dependency_type
            )
            return result.get("dependency_id") if result.get("success") else None

    def is_task_blocked(
        self, project_id: int, task_id: int
    ) -> Tuple[bool, List[int]]:
        """Check if task is blocked via Athena or local."""
        if self.use_athena and self.store:
            return self.store.is_task_blocked(project_id, task_id)
        else:
            from task_dependency_manager import TaskDependencyManager
            mgr = TaskDependencyManager()
            return mgr.is_task_blocked(project_id, task_id)

    def get_blocking_tasks(
        self, project_id: int, task_id: int
    ) -> Optional[List[Dict[str, Any]]]:
        """Get blocking tasks via Athena or local."""
        if self.use_athena and self.store:
            return self.store.get_blocking_tasks(project_id, task_id)
        else:
            from task_dependency_manager import TaskDependencyManager
            mgr = TaskDependencyManager()
            return mgr.get_blocking_tasks(project_id, task_id)

    def get_blocked_tasks(
        self, project_id: int, task_id: int
    ) -> Optional[List[int]]:
        """Get tasks blocked by this task via Athena or local."""
        if self.use_athena and self.store:
            return self.store.get_blocked_tasks(project_id, task_id)
        else:
            from task_dependency_manager import TaskDependencyManager
            mgr = TaskDependencyManager()
            return mgr.get_task_with_dependencies(project_id, task_id)["blocked_tasks"]

    def get_unblocked_tasks(
        self, project_id: int, statuses: List[str] = None, limit: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        """Get unblocked tasks via Athena or local."""
        if self.use_athena and self.store:
            return self.store.get_unblocked_tasks(project_id, statuses, limit)
        else:
            from task_dependency_manager import TaskDependencyManager
            mgr = TaskDependencyManager()
            return mgr.get_unblocked_tasks(project_id, statuses, limit)

    def remove_dependency(
        self, project_id: int, from_task_id: int, to_task_id: int
    ) -> bool:
        """Remove dependency via Athena or local."""
        if self.use_athena and self.store:
            return self.store.remove_dependency(project_id, from_task_id, to_task_id)
        else:
            from task_dependency_manager import TaskDependencyManager
            mgr = TaskDependencyManager()
            result = mgr.remove_dependency(project_id, from_task_id, to_task_id)
            return result.get("success", False)


class MetadataManagerBridge:
    """Bridge for metadata management.

    Uses Athena MetadataStore when available, otherwise local implementation.
    """

    def __init__(self):
        """Initialize bridge with Athena or fallback."""
        self.use_athena = ATHENA_AVAILABLE
        self.store = None

        if ATHENA_AVAILABLE:
            try:
                config = DatabaseConfig()
                db = Database(config)
                self.store = MetadataStore(db)
            except Exception as e:
                print(f"⚠ Failed to initialize Athena Phase 3a: {e}", file=sys.stderr)
                self.use_athena = False

    def set_metadata(
        self, project_id: int, task_id: int,
        effort_estimate: Optional[int] = None,
        complexity_score: Optional[int] = None,
        priority_score: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """Set metadata via Athena or local."""
        if self.use_athena and self.store:
            return self.store.set_metadata(
                project_id, task_id, effort_estimate, complexity_score,
                priority_score, tags
            )
        else:
            from metadata_manager import MetadataManager
            mgr = MetadataManager()
            result = mgr.set_metadata(
                project_id, task_id, effort_estimate, complexity_score,
                priority_score, tags
            )
            return result.get("success", False)

    def record_actual_effort(
        self, project_id: int, task_id: int, actual_minutes: int
    ) -> bool:
        """Record effort via Athena or local."""
        if self.use_athena and self.store:
            return self.store.record_actual_effort(project_id, task_id, actual_minutes)
        else:
            from metadata_manager import MetadataManager
            mgr = MetadataManager()
            result = mgr.record_actual_effort(project_id, task_id, actual_minutes)
            return result.get("success", False)

    def calculate_accuracy(
        self, project_id: int, task_id: int
    ) -> Optional[Dict[str, Any]]:
        """Calculate accuracy via Athena or local."""
        if self.use_athena and self.store:
            return self.store.calculate_accuracy(project_id, task_id)
        else:
            from metadata_manager import MetadataManager
            mgr = MetadataManager()
            return mgr.calculate_accuracy(project_id, task_id)

    def get_task_metadata(
        self, project_id: int, task_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get metadata via Athena or local."""
        if self.use_athena and self.store:
            return self.store.get_task_metadata(project_id, task_id)
        else:
            from metadata_manager import MetadataManager
            mgr = MetadataManager()
            return mgr.get_task_metadata(project_id, task_id)

    def get_project_analytics(self, project_id: int) -> Dict[str, Any]:
        """Get analytics via Athena or local."""
        if self.use_athena and self.store:
            return self.store.get_project_analytics(project_id)
        else:
            from metadata_manager import MetadataManager
            mgr = MetadataManager()
            return mgr.get_project_analytics(project_id)

    def add_tags(
        self, project_id: int, task_id: int, tags: List[str]
    ) -> bool:
        """Add tags via Athena or local."""
        if self.use_athena and self.store:
            return self.store.add_tags(project_id, task_id, tags)
        else:
            from metadata_manager import MetadataManager
            mgr = MetadataManager()
            result = mgr.add_tags(project_id, task_id, tags)
            return result.get("success", False)

    def set_completed_timestamp(
        self, project_id: int, task_id: int
    ) -> bool:
        """Set completion timestamp via Athena or local."""
        if self.use_athena and self.store:
            return self.store.set_completed_timestamp(project_id, task_id)
        else:
            from metadata_manager import MetadataManager
            mgr = MetadataManager()
            result = mgr.set_completed_timestamp(project_id, task_id)
            return result.get("success", False)


# Global instances
_dep_mgr = None
_meta_mgr = None


def get_dependency_manager() -> DependencyManagerBridge:
    """Get global dependency manager instance."""
    global _dep_mgr
    if _dep_mgr is None:
        _dep_mgr = DependencyManagerBridge()
    return _dep_mgr


def get_metadata_manager() -> MetadataManagerBridge:
    """Get global metadata manager instance."""
    global _meta_mgr
    if _meta_mgr is None:
        _meta_mgr = MetadataManagerBridge()
    return _meta_mgr


def is_athena_phase3a_available() -> bool:
    """Check if Athena Phase 3a is available."""
    return ATHENA_AVAILABLE
