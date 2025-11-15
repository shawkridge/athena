"""Bidirectional sync between TodoWrite (session JSON) and prospective_tasks (PostgreSQL).

This module makes TodoWrite the session-scoped interface to persistent prospective_tasks.
Tasks created/edited in TodoWrite automatically sync back to PostgreSQL at session end.
Tasks from PostgreSQL are loaded into TodoWrite at session start.
"""

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

from memory_bridge import MemoryBridge
from connection_pool import PooledConnection


class TodoWriteSync:
    """Bidirectional sync between TodoWrite and prospective_tasks."""

    def __init__(self):
        """Initialize sync manager."""
        self.bridge = MemoryBridge()

    def load_tasks_from_postgres(
        self,
        project_id: int,
        limit: int = 10,
        statuses: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Load active tasks from PostgreSQL.

        Args:
            project_id: Project ID
            limit: Maximum tasks to load
            statuses: Filter by status (default: pending, in_progress, blocked)

        Returns:
            List of task dicts with content, status, activeForm
        """
        if statuses is None:
            statuses = ["pending", "in_progress", "blocked"]

        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                # Build WHERE clause for statuses
                status_placeholders = ",".join(["%s"] * len(statuses))
                query = f"""
                SELECT
                    id, title, status, priority, description,
                    created_at, completed_at, checkpoint_id,
                    related_test_name, related_file_path
                FROM prospective_tasks
                WHERE project_id = %s
                  AND status IN ({status_placeholders})
                ORDER BY
                    CASE WHEN status = 'in_progress' THEN 1
                         WHEN status = 'blocked' THEN 2
                         ELSE 3 END,
                    priority DESC,
                    created_at DESC
                LIMIT %s
                """

                params = [project_id] + statuses + [limit]
                cursor.execute(query, params)
                rows = cursor.fetchall()

                tasks = []
                for row in rows:
                    # Map prospective_tasks columns to task dict
                    task = {
                        "id": row[0],
                        "content": row[1],  # title → content
                        "status": row[2],
                        "activeForm": f"Working on: {row[1][:40]}" if row[1] else "Task",
                        "priority": row[3],
                        "description": row[4],
                        "created_at": row[5],
                        "completed_at": row[6],
                        "checkpoint_id": row[7],
                        "related_test_name": row[8],
                        "related_file_path": row[9],
                    }
                    tasks.append(task)

                return tasks

        except Exception as e:
            print(
                f"⚠ Error loading tasks from PostgreSQL: {e}",
                file=sys.stderr,
            )
            return []

    def save_todowrite_to_postgres(
        self,
        project_id: int,
        tasks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Save TodoWrite updates back to PostgreSQL.

        Handles both new tasks (created during session) and existing tasks (updated).

        Args:
            project_id: Project ID
            tasks: List of task dicts from TodoWrite

        Returns:
            Summary of changes: {created: int, updated: int, errors: list}
        """
        summary = {"created": 0, "updated": 0, "errors": []}

        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()
                now = datetime.now()

                for task in tasks:
                    task_id = task.get("id")
                    title = task.get("content", "")  # content → title
                    description = task.get("description", "")
                    status = task.get("status", "pending")
                    priority = task.get("priority", 5)  # Default priority
                    checkpoint_id = task.get("checkpoint_id")
                    test_name = task.get("related_test_name")
                    file_path = task.get("related_file_path")

                    try:
                        if task_id and isinstance(task_id, int):
                            # Update existing task
                            cursor.execute(
                                """
                                UPDATE prospective_tasks
                                SET
                                    title = %s,
                                    description = %s,
                                    status = %s,
                                    priority = %s,
                                    checkpoint_id = %s,
                                    related_test_name = %s,
                                    related_file_path = %s,
                                    last_claude_sync_at = %s
                                WHERE id = %s AND project_id = %s
                                """,
                                (
                                    title,
                                    description,
                                    status,
                                    priority,
                                    checkpoint_id,
                                    test_name,
                                    file_path,
                                    now,
                                    task_id,
                                    project_id,
                                ),
                            )
                            summary["updated"] += 1

                        else:
                            # Create new task
                            cursor.execute(
                                """
                                INSERT INTO prospective_tasks
                                (project_id, title, description, status, priority,
                                 checkpoint_id, related_test_name, related_file_path,
                                 created_at, last_claude_sync_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """,
                                (
                                    project_id,
                                    title,
                                    description,
                                    status,
                                    priority,
                                    checkpoint_id,
                                    test_name,
                                    file_path,
                                    now,
                                    now,
                                ),
                            )
                            summary["created"] += 1

                    except Exception as e:
                        summary["errors"].append(
                            f"Error syncing task '{title[:30]}': {str(e)}"
                        )

                conn.commit()

        except Exception as e:
            print(f"⚠ Error during TodoWrite sync: {e}", file=sys.stderr)
            summary["errors"].append(str(e))

        return summary

    def convert_to_todowrite_format(
        self, postgres_tasks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert PostgreSQL tasks to TodoWrite format.

        Args:
            postgres_tasks: Tasks from PostgreSQL

        Returns:
            TodoWrite-compatible format: [{content, status, activeForm}]
        """
        todowrite_tasks = []

        for task in postgres_tasks:
            todowrite_task = {
                "id": task.get("id"),  # Keep ID for later sync
                "content": task.get("content", ""),
                "status": task.get("status", "pending"),
                "activeForm": task.get(
                    "activeForm", f"Working on: {task.get('content', '')[:30]}"
                ),
            }
            todowrite_tasks.append(todowrite_task)

        return todowrite_tasks

    def link_task_to_checkpoint(
        self,
        project_id: int,
        task_id: int,
        checkpoint_id: int,
    ) -> bool:
        """Link a task to a checkpoint.

        Args:
            project_id: Project ID
            task_id: Task ID
            checkpoint_id: Checkpoint ID (from checkpoint.id)

        Returns:
            True if successful
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE prospective_tasks
                    SET checkpoint_id = %s
                    WHERE id = %s AND project_id = %s
                    """,
                    (checkpoint_id, task_id, project_id),
                )
                conn.commit()
                return True

        except Exception as e:
            print(
                f"⚠ Error linking task to checkpoint: {e}",
                file=sys.stderr,
            )
            return False

    def get_task_by_checkpoint(
        self, project_id: int, checkpoint_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get task associated with a checkpoint.

        Args:
            project_id: Project ID
            checkpoint_id: Checkpoint ID

        Returns:
            Task dict or None if not found
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT
                        id, content, status, active_form, priority,
                        related_test_name, related_file_path
                    FROM prospective_tasks
                    WHERE project_id = %s AND checkpoint_id = %s
                    LIMIT 1
                    """,
                    (project_id, checkpoint_id),
                )

                row = cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "content": row[1],
                        "status": row[2],
                        "activeForm": row[3],
                        "priority": row[4],
                        "related_test_name": row[5],
                        "related_file_path": row[6],
                    }

                return None

        except Exception as e:
            print(
                f"⚠ Error retrieving task by checkpoint: {e}",
                file=sys.stderr,
            )
            return None

    def close(self):
        """Close sync manager."""
        self.bridge.close()


def test_todowrite_sync():
    """Test TodoWriteSync functionality."""
    print("\n=== TodoWriteSync Test ===\n")

    sync = TodoWriteSync()

    # Test 1: Load tasks from PostgreSQL
    print("1. Loading tasks from PostgreSQL...")
    tasks = sync.load_tasks_from_postgres(project_id=1, limit=5)
    if tasks:
        print(f"  ✓ Loaded {len(tasks)} tasks:")
        for task in tasks[:3]:
            print(f"    - [{task['status']}] {task['content'][:50]}")
    else:
        print("  ℹ No tasks found (this is OK)")

    # Test 2: Convert to TodoWrite format
    print("\n2. Converting to TodoWrite format...")
    todowrite_format = sync.convert_to_todowrite_format(tasks)
    if todowrite_format:
        print(f"  ✓ Converted {len(todowrite_format)} tasks")
        print(f"    Sample: {json.dumps(todowrite_format[0], indent=2)}")

    # Test 3: Save back to PostgreSQL (with modified data)
    if todowrite_format:
        print("\n3. Saving changes back to PostgreSQL...")
        # Modify a task for testing
        test_tasks = todowrite_format[:1]
        if test_tasks:
            test_tasks[0]["status"] = "in_progress"  # Simulate edit
            summary = sync.save_todowrite_to_postgres(
                project_id=1, tasks=test_tasks
            )
            print(f"  ✓ Sync complete:")
            print(f"    - Created: {summary['created']}")
            print(f"    - Updated: {summary['updated']}")
            if summary["errors"]:
                print(f"    - Errors: {summary['errors']}")

    sync.close()
    print("\n✓ TodoWriteSync tests complete\n")


if __name__ == "__main__":
    test_todowrite_sync()
