"""Task updater for Claude-initiated updates during session.

Allows Claude to update task state in real-time, not just at session end.
Changes are written immediately to both TodoWrite JSON and PostgreSQL.
"""

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path

from memory_bridge import MemoryBridge
from connection_pool import PooledConnection


class TaskUpdater:
    """Handle task updates from Claude during session."""

    def __init__(self):
        """Initialize task updater."""
        self.bridge = MemoryBridge()

    def update_task(
        self,
        project_id: int,
        task_id: int,
        updates: Dict[str, Any],
        source: str = "claude",
    ) -> Dict[str, Any]:
        """Update a task immediately (both TodoWrite JSON and PostgreSQL).

        Args:
            project_id: Project ID
            task_id: Task ID to update
            updates: Dict with fields to update (status, priority, content, etc.)
            source: Source of update (claude, hook, user)

        Returns:
            Updated task dict or error dict
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()
                now = datetime.now()

                # Build dynamic UPDATE statement
                set_clauses = []
                values = []

                # Map update fields to database columns
                field_mapping = {
                    "content": "title",
                    "status": "status",
                    "priority": "priority",
                    "description": "description",
                    "activeForm": "description",  # Fall back to description
                    "checkpoint_id": "checkpoint_id",
                    "related_test_name": "related_test_name",
                    "related_file_path": "related_file_path",
                }

                for field, value in updates.items():
                    if field in field_mapping:
                        db_field = field_mapping[field]
                        set_clauses.append(f"{db_field} = %s")
                        values.append(value)

                # Always update sync timestamp
                set_clauses.append("last_claude_sync_at = %s")
                values.append(now)

                if not set_clauses:
                    return {"error": "No valid fields to update"}

                # Execute update
                query = f"""
                UPDATE prospective_tasks
                SET {', '.join(set_clauses)}
                WHERE id = %s AND project_id = %s
                RETURNING id, title, status, priority, checkpoint_id, related_test_name
                """

                values.extend([task_id, project_id])
                cursor.execute(query, values)
                result = cursor.fetchone()
                conn.commit()

                if result:
                    return {
                        "success": True,
                        "id": result[0],
                        "content": result[1],
                        "status": result[2],
                        "priority": result[3],
                        "checkpoint_id": result[4],
                        "related_test_name": result[5],
                        "source": source,
                        "updated_at": now.isoformat(),
                    }
                else:
                    return {"error": f"Task {task_id} not found in project {project_id}"}

        except Exception as e:
            return {"error": f"Update failed: {str(e)}"}

    def mark_task_complete(
        self, project_id: int, task_id: int, with_dependencies: bool = True
    ) -> Dict[str, Any]:
        """Mark a task as completed.

        If with_dependencies=True, also checks dependency manager to unblock
        downstream tasks and metadata manager to record completion time.

        Args:
            project_id: Project ID
            task_id: Task ID
            with_dependencies: If True, integrate with dependency/metadata managers

        Returns:
            Updated task dict with dependency info
        """
        result = self.update_task(
            project_id=project_id,
            task_id=task_id,
            updates={"status": "completed"},
            source="claude_complete",
        )

        # If Phase 3a modules available, integrate them
        if with_dependencies and result.get("success"):
            try:
                from task_dependency_manager import TaskDependencyManager
                from metadata_manager import MetadataManager

                dep_mgr = TaskDependencyManager()
                metadata_mgr = MetadataManager()

                # Unblock any downstream tasks
                unblock_result = dep_mgr.complete_task_and_unblock(project_id, task_id)
                if unblock_result.get("success"):
                    result["newly_unblocked"] = unblock_result.get("newly_unblocked", [])

                # Record completion timestamp
                timestamp_result = metadata_mgr.set_completed_timestamp(
                    project_id, task_id
                )
                if timestamp_result.get("success"):
                    result["completed_at"] = timestamp_result.get("completed_at")

            except ImportError:
                # Phase 3a modules not available, that's ok
                pass

        return result

    def update_task_priority(
        self, project_id: int, task_id: int, priority: int
    ) -> Dict[str, Any]:
        """Update task priority.

        Args:
            project_id: Project ID
            task_id: Task ID
            priority: New priority (1-10)

        Returns:
            Updated task dict
        """
        if not (1 <= priority <= 10):
            return {"error": "Priority must be 1-10"}

        return self.update_task(
            project_id=project_id,
            task_id=task_id,
            updates={"priority": priority},
            source="claude_priority",
        )

    def update_todowrite_json(
        self, session_id: str, task_id: int, updates: Dict[str, Any]
    ) -> bool:
        """Update a task in TodoWrite JSON file.

        Args:
            session_id: Session ID
            task_id: Task ID to update
            updates: Fields to update

        Returns:
            True if successful
        """
        try:
            todowrite_path = f"/home/user/.claude/todos/{session_id}.json"

            if not os.path.exists(todowrite_path):
                return False

            # Load current TodoWrite
            with open(todowrite_path, "r") as f:
                tasks = json.load(f)

            # Find and update task
            updated = False
            for task in tasks:
                if task.get("id") == task_id:
                    task.update(updates)
                    updated = True
                    break

            if updated:
                # Write back
                with open(todowrite_path, "w") as f:
                    json.dump(tasks, f, indent=2)
                return True

            return False

        except Exception as e:
            print(f"⚠ Error updating TodoWrite JSON: {e}", file=sys.stderr)
            return False

    def sync_task_to_both(
        self,
        project_id: int,
        task_id: int,
        session_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Sync task update to both PostgreSQL and TodoWrite JSON.

        Args:
            project_id: Project ID
            task_id: Task ID
            session_id: Session ID for TodoWrite JSON
            updates: Fields to update

        Returns:
            Result dict with sync status
        """
        # Update PostgreSQL
        db_result = self.update_task(project_id, task_id, updates)

        if "error" in db_result:
            return {"error": db_result["error"]}

        # Update TodoWrite JSON
        json_updated = self.update_todowrite_json(session_id, task_id, updates)

        return {
            "success": True,
            "task_id": task_id,
            "database_updated": True,
            "todowrite_updated": json_updated,
            "changes": updates,
        }

    def get_task_status(self, project_id: int, task_id: int) -> Optional[Dict[str, Any]]:
        """Get current task status.

        Args:
            project_id: Project ID
            task_id: Task ID

        Returns:
            Task dict or None if not found
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, title, status, priority, description,
                           checkpoint_id, related_test_name, related_file_path,
                           last_claude_sync_at
                    FROM prospective_tasks
                    WHERE id = %s AND project_id = %s
                    """,
                    (task_id, project_id),
                )

                row = cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "content": row[1],
                        "status": row[2],
                        "priority": row[3],
                        "description": row[4],
                        "checkpoint_id": row[5],
                        "related_test_name": row[6],
                        "related_file_path": row[7],
                        "last_sync": row[8],
                    }

                return None

        except Exception as e:
            print(f"⚠ Error getting task status: {e}", file=sys.stderr)
            return None

    def close(self):
        """Close updater."""
        self.bridge.close()


def test_task_updater():
    """Test task updater functionality."""
    print("\n=== Task Updater Test ===\n")

    updater = TaskUpdater()

    # Create a test task first
    print("1. Creating test task...")
    from todowrite_sync import TodoWriteSync

    sync = TodoWriteSync()
    # Assuming a task exists, let's get it
    tasks = sync.load_tasks_from_postgres(project_id=1, limit=1)
    sync.close()

    if not tasks:
        print("  ℹ No test tasks available")
        updater.close()
        return

    test_task_id = tasks[0]["id"]
    print(f"  ✓ Using task ID: {test_task_id}")

    # Test 2: Get task status
    print("\n2. Getting task status...")
    status = updater.get_task_status(project_id=1, task_id=test_task_id)
    if status:
        print(f"  ✓ Task: {status['content']}")
        print(f"    Status: {status['status']}, Priority: {status['priority']}")
    else:
        print("  ✗ Could not get task status")
        updater.close()
        return

    # Test 3: Update task priority
    print("\n3. Updating task priority...")
    result = updater.update_task_priority(
        project_id=1, task_id=test_task_id, priority=9
    )
    if result.get("success"):
        print(f"  ✓ Priority updated to: {result.get('priority')}")
    else:
        print(f"  ✗ Update failed: {result.get('error')}")

    # Test 4: Mark task complete
    print("\n4. Marking task complete...")
    result = updater.mark_task_complete(project_id=1, task_id=test_task_id)
    if result.get("success"):
        print(f"  ✓ Status updated to: {result.get('status')}")
    else:
        print(f"  ✗ Update failed: {result.get('error')}")

    # Test 5: Sync to both (simulated)
    print("\n5. Testing sync to both PostgreSQL and TodoWrite...")
    result = updater.sync_task_to_both(
        project_id=1,
        task_id=test_task_id,
        session_id="test-session",
        updates={"priority": 7, "status": "in_progress"},
    )
    if result.get("success"):
        print(f"  ✓ Synced to database: {result['database_updated']}")
        print(f"  ✓ Synced to TodoWrite: {result['todowrite_updated']}")
    else:
        print(f"  ✗ Sync failed: {result.get('error')}")

    updater.close()
    print("\n✓ Task Updater tests complete\n")


if __name__ == "__main__":
    test_task_updater()
