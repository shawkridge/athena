"""Task dependency management for Phase 3a.

Handles task relationships: one task can block another until completion.
Example: Write tests (task B) is blocked by implement feature (task A).

When task A completes, task B becomes unblocked and is suggested next.
"""

import json
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from connection_pool import PooledConnection


class TaskDependencyManager:
    """Manage task dependencies and blocking relationships."""

    def __init__(self):
        """Initialize dependency manager."""
        self._ensure_schema()

    def _ensure_schema(self):
        """Create task_dependencies table if it doesn't exist."""
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS task_dependencies (
                        id SERIAL PRIMARY KEY,
                        project_id INTEGER NOT NULL,
                        from_task_id INTEGER NOT NULL,
                        to_task_id INTEGER NOT NULL,
                        dependency_type VARCHAR(50) DEFAULT 'blocks',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (from_task_id) REFERENCES prospective_tasks(id),
                        FOREIGN KEY (to_task_id) REFERENCES prospective_tasks(id),
                        UNIQUE(from_task_id, to_task_id)
                    )
                    """
                )
                conn.commit()
        except Exception as e:
            print(f"⚠ Error ensuring schema: {e}", file=sys.stderr)

    def create_dependency(
        self, project_id: int, from_task_id: int, to_task_id: int, dependency_type: str = "blocks"
    ) -> Dict[str, Any]:
        """Create a dependency: from_task blocks to_task.

        Args:
            project_id: Project ID
            from_task_id: Task that must complete first
            to_task_id: Task that is blocked
            dependency_type: Type of dependency ('blocks' is default)

        Returns:
            Result dict with success status
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                # Check if both tasks exist
                cursor.execute(
                    """
                    SELECT id FROM prospective_tasks
                    WHERE id IN (%s, %s) AND project_id = %s
                    """,
                    (from_task_id, to_task_id, project_id),
                )
                rows = cursor.fetchall()

                if len(rows) != 2:
                    return {"error": f"One or both tasks not found in project {project_id}"}

                # Create dependency (ignore if already exists)
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
                conn.commit()

                if result:
                    return {
                        "success": True,
                        "dependency_id": result[0],
                        "from_task_id": from_task_id,
                        "to_task_id": to_task_id,
                        "message": f"Task {from_task_id} blocks Task {to_task_id}",
                    }
                else:
                    return {
                        "success": True,
                        "message": "Dependency already exists",
                    }

        except Exception as e:
            return {"error": f"Create dependency failed: {str(e)}"}

    def is_task_blocked(self, project_id: int, task_id: int) -> Tuple[bool, List[int]]:
        """Check if a task is blocked by incomplete dependencies.

        Args:
            project_id: Project ID
            task_id: Task ID to check

        Returns:
            (is_blocked, list_of_blocking_task_ids)
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                # Get all tasks that block this task
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
            print(f"⚠ Error checking if task blocked: {e}", file=sys.stderr)
            return False, []

    def get_blocking_tasks(self, project_id: int, task_id: int) -> Optional[List[Dict[str, Any]]]:
        """Get detailed info about tasks blocking this task.

        Args:
            project_id: Project ID
            task_id: Task ID

        Returns:
            List of blocking task dicts, or None on error
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT
                        t.id, t.title, t.status, t.priority,
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
                    tasks.append(
                        {
                            "id": row[0],
                            "content": row[1],
                            "status": row[2],
                            "priority": row[3],
                            "dependency_type": row[4],
                            "created_at": row[5],
                        }
                    )

                return tasks if tasks else None

        except Exception as e:
            print(f"⚠ Error getting blocking tasks: {e}", file=sys.stderr)
            return None

    def complete_task_and_unblock(self, project_id: int, task_id: int) -> Dict[str, Any]:
        """Mark task complete and identify newly unblocked tasks.

        When a task is marked complete, any tasks that were only blocked by this
        task become unblocked (ready to work on).

        Args:
            project_id: Project ID
            task_id: Task to mark complete

        Returns:
            Result dict with newly unblocked task IDs
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                # Get all tasks blocked by this task
                cursor.execute(
                    """
                    SELECT DISTINCT to_task_id FROM task_dependencies
                    WHERE project_id = %s AND from_task_id = %s
                    """,
                    (project_id, task_id),
                )

                blocked_task_ids = [row[0] for row in cursor.fetchall()]

                # Check which of these tasks are now unblocked
                newly_unblocked = []
                for blocked_task_id in blocked_task_ids:
                    is_blocked, _ = self.is_task_blocked(project_id, blocked_task_id)
                    if not is_blocked:
                        newly_unblocked.append(blocked_task_id)

                return {
                    "success": True,
                    "task_id": task_id,
                    "was_blocking": blocked_task_ids,
                    "newly_unblocked": newly_unblocked,
                    "message": f"Task {task_id} complete. Unblocked: {len(newly_unblocked)} task(s)",
                }

        except Exception as e:
            return {"error": f"Unblock failed: {str(e)}"}

    def get_task_with_dependencies(
        self, project_id: int, task_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get task with full dependency information.

        Args:
            project_id: Project ID
            task_id: Task ID

        Returns:
            Task dict with blocking_tasks and blocked_tasks lists
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                # Get task
                cursor.execute(
                    """
                    SELECT id, title, status, priority, description
                    FROM prospective_tasks
                    WHERE id = %s AND project_id = %s
                    """,
                    (task_id, project_id),
                )

                row = cursor.fetchone()
                if not row:
                    return None

                task = {
                    "id": row[0],
                    "content": row[1],
                    "status": row[2],
                    "priority": row[3],
                    "description": row[4],
                }

                # Get blocking tasks
                blocking_tasks = self.get_blocking_tasks(project_id, task_id)
                task["blocking_tasks"] = blocking_tasks or []

                # Get tasks blocked by this task
                cursor.execute(
                    """
                    SELECT DISTINCT to_task_id FROM task_dependencies
                    WHERE project_id = %s AND from_task_id = %s
                    """,
                    (project_id, task_id),
                )

                blocked_by_this = [row[0] for row in cursor.fetchall()]
                task["blocked_tasks"] = blocked_by_this

                # Check if this task is currently blocked
                is_blocked, blocking_list = self.is_task_blocked(project_id, task_id)
                task["is_blocked"] = is_blocked
                task["blocked_by"] = blocking_list

                return task

        except Exception as e:
            print(f"⚠ Error getting task with dependencies: {e}", file=sys.stderr)
            return None

    def get_unblocked_tasks(
        self, project_id: int, statuses: List[str] = None, limit: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        """Get unblocked tasks (ready to work on).

        Args:
            project_id: Project ID
            statuses: Filter by status (default: ['pending', 'in_progress'])
            limit: Max tasks to return

        Returns:
            List of unblocked task dicts
        """
        if statuses is None:
            statuses = ["pending", "in_progress"]

        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                # Get all tasks with given statuses
                placeholders = ",".join(["%s"] * len(statuses))
                cursor.execute(
                    f"""
                    SELECT id, title, status, priority
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
                        unblocked_tasks.append(
                            {
                                "id": task_id,
                                "content": row[1],
                                "status": row[2],
                                "priority": row[3],
                                "is_blocked": False,
                            }
                        )

                return unblocked_tasks

        except Exception as e:
            print(f"⚠ Error getting unblocked tasks: {e}", file=sys.stderr)
            return None

    def remove_dependency(
        self, project_id: int, from_task_id: int, to_task_id: int
    ) -> Dict[str, Any]:
        """Remove a dependency.

        Args:
            project_id: Project ID
            from_task_id: Blocking task
            to_task_id: Blocked task

        Returns:
            Result dict
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    DELETE FROM task_dependencies
                    WHERE project_id = %s AND from_task_id = %s AND to_task_id = %s
                    RETURNING id
                    """,
                    (project_id, from_task_id, to_task_id),
                )

                result = cursor.fetchone()
                conn.commit()

                if result:
                    return {
                        "success": True,
                        "message": f"Dependency removed between {from_task_id} and {to_task_id}",
                    }
                else:
                    return {"error": "Dependency not found"}

        except Exception as e:
            return {"error": f"Remove dependency failed: {str(e)}"}


def test_task_dependency_manager():
    """Test dependency manager functionality."""
    print("\n=== Task Dependency Manager Test ===\n")

    mgr = TaskDependencyManager()

    # Test 1: Create dependency
    print("1. Creating dependency (task 1 blocks task 2)...")
    result = mgr.create_dependency(project_id=1, from_task_id=1, to_task_id=2)
    if result.get("success"):
        print(f"  ✓ {result['message']}")
    else:
        print(f"  ✗ {result.get('error')}")
        return

    # Test 2: Check if task is blocked
    print("\n2. Checking if task 2 is blocked...")
    is_blocked, blocking_list = mgr.is_task_blocked(project_id=1, task_id=2)
    print(f"  ✓ Task 2 blocked: {is_blocked}, by: {blocking_list}")

    # Test 3: Get blocking tasks
    print("\n3. Getting tasks blocking task 2...")
    blocking_tasks = mgr.get_blocking_tasks(project_id=1, task_id=2)
    if blocking_tasks:
        for task in blocking_tasks:
            print(f"  ✓ Task {task['id']}: {task['content']} (status: {task['status']})")
    else:
        print("  ℹ No blocking tasks")

    # Test 4: Get task with dependencies
    print("\n4. Getting task 2 with dependencies...")
    task_with_deps = mgr.get_task_with_dependencies(project_id=1, task_id=2)
    if task_with_deps:
        print(f"  ✓ Task: {task_with_deps['content']}")
        print(f"    Is blocked: {task_with_deps['is_blocked']}")
        print(f"    Blocked by: {task_with_deps['blocked_by']}")
    else:
        print("  ℹ Task not found")

    # Test 5: Get unblocked tasks
    print("\n5. Getting unblocked tasks...")
    unblocked = mgr.get_unblocked_tasks(project_id=1)
    if unblocked:
        for task in unblocked:
            print(f"  ✓ Task {task['id']}: {task['content']}")
    else:
        print("  ℹ No unblocked tasks")

    # Test 6: Complete task and unblock
    print("\n6. Completing task 1 (should unblock task 2)...")
    result = mgr.complete_task_and_unblock(project_id=1, task_id=1)
    if result.get("success"):
        print(f"  ✓ {result['message']}")
        print(f"    Newly unblocked: {result.get('newly_unblocked')}")
    else:
        print(f"  ✗ {result.get('error')}")

    print("\n✓ Task Dependency Manager tests complete\n")


if __name__ == "__main__":
    test_task_dependency_manager()
