"""Task dependency management - Athena prospective layer.

Manages task blocking relationships and dependency chains.
Part of Phase 3a: Task Dependencies + Metadata integration.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

from ..core.database import Database
from ..core.base_store import BaseStore

logger = logging.getLogger(__name__)


class DependencyStore(BaseStore):
    """Manages task dependencies within Athena prospective memory."""

    table_name = "task_dependencies"

    def __init__(self, db: Database):
        """Initialize dependency store.

        Args:
            db: Database instance
        """
        super().__init__(db)
        self._ensure_schema()

    def _ensure_schema(self):
        """Ensure task_dependencies table exists."""
        if not hasattr(self.db, 'get_cursor'):
            # Async database, schema handled elsewhere
            logger.debug("Async database detected, skipping sync schema")
            return

        cursor = self.db.get_cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_dependencies (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                from_task_id INTEGER NOT NULL,
                to_task_id INTEGER NOT NULL,
                dependency_type VARCHAR(50) DEFAULT 'blocks',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (from_task_id) REFERENCES prospective_tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (to_task_id) REFERENCES prospective_tasks(id) ON DELETE CASCADE,
                UNIQUE(from_task_id, to_task_id)
            )
        """)

    def create_dependency(
        self, project_id: int, from_task_id: int, to_task_id: int,
        dependency_type: str = "blocks"
    ) -> Optional[int]:
        """Create a dependency: from_task blocks to_task.

        Args:
            project_id: Project ID
            from_task_id: Task that must complete first
            to_task_id: Task that is blocked
            dependency_type: Type of dependency

        Returns:
            Dependency ID or None on error
        """
        try:
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                INSERT INTO task_dependencies
                (project_id, from_task_id, to_task_id, dependency_type)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (from_task_id, to_task_id) DO NOTHING
                RETURNING id
                """,
                (project_id, from_task_id, to_task_id, dependency_type),
            )
            result = cursor.fetchone()
            if result:
                self.db.commit()
                return result[0]
            return None
        except Exception as e:
            logger.error(f"Failed to create dependency: {e}")
            return None

    def is_task_blocked(self, project_id: int, task_id: int) -> Tuple[bool, List[int]]:
        """Check if a task is blocked by incomplete dependencies.

        Args:
            project_id: Project ID
            task_id: Task ID to check

        Returns:
            (is_blocked, list_of_blocking_task_ids)
        """
        try:
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                SELECT DISTINCT d.from_task_id, t.status
                FROM task_dependencies d
                JOIN prospective_tasks t ON d.from_task_id = t.id
                WHERE d.project_id = %s AND d.to_task_id = %s
                """,
                (project_id, task_id),
            )

            rows = cursor.fetchall()
            blocking_tasks = []

            for from_task_id, status in rows:
                if status != "completed":
                    blocking_tasks.append(from_task_id)

            return len(blocking_tasks) > 0, blocking_tasks
        except Exception as e:
            logger.error(f"Failed to check if task blocked: {e}")
            return False, []

    def get_blocking_tasks(
        self, project_id: int, task_id: int
    ) -> Optional[List[Dict[str, Any]]]:
        """Get detailed info about tasks blocking this task.

        Args:
            project_id: Project ID
            task_id: Task ID

        Returns:
            List of blocking task dicts
        """
        try:
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                SELECT
                    t.id, t.content, t.status, t.priority,
                    d.dependency_type, d.created_at
                FROM task_dependencies d
                JOIN prospective_tasks t ON d.from_task_id = t.id
                WHERE d.project_id = %s AND d.to_task_id = %s
                ORDER BY d.created_at
                """,
                (project_id, task_id),
            )

            rows = cursor.fetchall()
            tasks = []

            for row in rows:
                tasks.append({
                    "id": row[0],
                    "content": row[1],
                    "status": row[2],
                    "priority": row[3],
                    "dependency_type": row[4],
                    "created_at": row[5],
                })

            return tasks if tasks else None
        except Exception as e:
            logger.error(f"Failed to get blocking tasks: {e}")
            return None

    def get_blocked_tasks(
        self, project_id: int, task_id: int
    ) -> Optional[List[int]]:
        """Get tasks blocked by this task.

        Args:
            project_id: Project ID
            task_id: Task that is blocking

        Returns:
            List of task IDs blocked by this task
        """
        try:
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                SELECT DISTINCT to_task_id FROM task_dependencies
                WHERE project_id = %s AND from_task_id = %s
                """,
                (project_id, task_id),
            )

            rows = cursor.fetchall()
            return [row[0] for row in rows] if rows else None
        except Exception as e:
            logger.error(f"Failed to get blocked tasks: {e}")
            return None

    def get_unblocked_tasks(
        self, project_id: int, statuses: List[str] = None, limit: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        """Get unblocked tasks (ready to work on).

        Args:
            project_id: Project ID
            statuses: Filter by status
            limit: Max tasks to return

        Returns:
            List of unblocked task dicts
        """
        if statuses is None:
            statuses = ["pending", "in_progress"]

        try:
            cursor = self.db.get_cursor()

            # Get all tasks with given statuses
            placeholders = ",".join(["%s"] * len(statuses))
            cursor.execute(
                f"""
                SELECT id, content, status, priority
                FROM prospective_tasks
                WHERE project_id = %s AND status IN ({placeholders})
                ORDER BY priority DESC, id
                LIMIT %s
                """,
                [project_id] + statuses + [limit],
            )

            rows = cursor.fetchall()
            unblocked_tasks = []

            for row in rows:
                task_id = row[0]
                is_blocked, _ = self.is_task_blocked(project_id, task_id)

                if not is_blocked:
                    unblocked_tasks.append({
                        "id": task_id,
                        "content": row[1],
                        "status": row[2],
                        "priority": row[3],
                        "is_blocked": False,
                    })

            return unblocked_tasks
        except Exception as e:
            logger.error(f"Failed to get unblocked tasks: {e}")
            return None

    def remove_dependency(
        self, project_id: int, from_task_id: int, to_task_id: int
    ) -> bool:
        """Remove a dependency.

        Args:
            project_id: Project ID
            from_task_id: Blocking task
            to_task_id: Blocked task

        Returns:
            True if successful
        """
        try:
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                DELETE FROM task_dependencies
                WHERE project_id = %s AND from_task_id = %s AND to_task_id = %s
                """,
                (project_id, from_task_id, to_task_id),
            )
            self.db.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to remove dependency: {e}")
            return False
