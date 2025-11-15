"""Link checkpoints to tasks for full context resumption.

A checkpoint represents a session resume point.
A task represents work to be done.
This module links them: checkpoint → task → test → file.

This enables: "Resume task X at checkpoint Y, validate with test Z, edit file F"
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional

from memory_bridge import MemoryBridge
from connection_pool import PooledConnection
from checkpoint_manager import CheckpointManager
from todowrite_sync import TodoWriteSync


class CheckpointTaskLinker:
    """Link checkpoints to tasks with full context."""

    def __init__(self):
        """Initialize linker."""
        self.bridge = MemoryBridge()

    def link_checkpoint_to_task(
        self,
        project_id: int,
        checkpoint_id: int,
        task_id: int,
        test_name: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Link a checkpoint to a task.

        Args:
            project_id: Project ID
            checkpoint_id: Checkpoint ID (from episodic_events.id where type='SESSION_CHECKPOINT')
            task_id: Task ID to link to
            test_name: Optional test that validates the task
            file_path: Optional primary file being edited

        Returns:
            Link result: {success, checkpoint_id, task_id, ...}
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                # Update task with checkpoint link
                cursor.execute(
                    """
                    UPDATE prospective_tasks
                    SET
                        checkpoint_id = %s,
                        related_test_name = %s,
                        related_file_path = %s,
                        last_claude_sync_at = %s
                    WHERE id = %s AND project_id = %s
                    """,
                    (
                        checkpoint_id,
                        test_name,
                        file_path,
                        datetime.now(),
                        task_id,
                        project_id,
                    ),
                )

                conn.commit()

                return {
                    "success": True,
                    "checkpoint_id": checkpoint_id,
                    "task_id": task_id,
                    "test_name": test_name,
                    "file_path": file_path,
                    "message": f"Linked checkpoint {checkpoint_id} to task {task_id}",
                }

        except Exception as e:
            return {"error": f"Link failed: {str(e)}"}

    def get_checkpoint_context(
        self, project_id: int, checkpoint_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get full context for a checkpoint including linked task.

        Args:
            project_id: Project ID
            checkpoint_id: Checkpoint ID

        Returns:
            Full context dict: checkpoint + linked task + test info
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                # Get task linked to checkpoint
                cursor.execute(
                    """
                    SELECT
                        id, title, status, priority, description,
                        checkpoint_id, related_test_name, related_file_path
                    FROM prospective_tasks
                    WHERE project_id = %s AND checkpoint_id = %s
                    LIMIT 1
                    """,
                    (project_id, checkpoint_id),
                )

                row = cursor.fetchone()

                if row:
                    return {
                        "checkpoint_id": checkpoint_id,
                        "task_id": row[0],
                        "task_name": row[1],
                        "task_status": row[2],
                        "task_priority": row[3],
                        "task_description": row[4],
                        "test_name": row[6],
                        "file_path": row[7],
                        "type": "checkpoint_task_link",
                    }

                return None

        except Exception as e:
            import sys

            print(f"⚠ Error getting checkpoint context: {e}", file=sys.stderr)
            return None

    def create_checkpoint_for_task(
        self,
        project_id: int,
        task_id: int,
        task_name: str,
        file_path: str,
        test_name: str,
        next_action: str,
    ) -> Dict[str, Any]:
        """Create a checkpoint specifically for a task.

        Args:
            project_id: Project ID
            task_id: Task ID
            task_name: Task name (for checkpoint)
            file_path: File being edited
            test_name: Test validating the task
            next_action: Next action to take

        Returns:
            Created checkpoint dict
        """
        try:
            # Create checkpoint
            checkpoint_mgr = CheckpointManager()
            checkpoint_id = checkpoint_mgr.save_checkpoint(
                project_id=project_id,
                task_name=task_name,
                file_path=file_path,
                test_name=test_name,
                next_action=next_action,
                status="in_progress",
            )
            checkpoint_mgr.close()

            if checkpoint_id:
                # Link checkpoint to task
                link_result = self.link_checkpoint_to_task(
                    project_id=project_id,
                    checkpoint_id=checkpoint_id,
                    task_id=task_id,
                    test_name=test_name,
                    file_path=file_path,
                )

                if link_result.get("success"):
                    return {
                        "success": True,
                        "checkpoint_id": checkpoint_id,
                        "task_id": task_id,
                        "message": f"Created checkpoint for task {task_id}",
                    }

                return link_result

            return {"error": "Failed to create checkpoint"}

        except Exception as e:
            return {"error": f"Error: {str(e)}"}

    def get_task_for_checkpoint(
        self, project_id: int, checkpoint_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get the task linked to a checkpoint.

        Args:
            project_id: Project ID
            checkpoint_id: Checkpoint ID

        Returns:
            Task dict or None
        """
        try:
            sync = TodoWriteSync()
            tasks = sync.load_tasks_from_postgres(project_id=project_id, limit=100)
            sync.close()

            for task in tasks:
                if task.get("checkpoint_id") == checkpoint_id:
                    return task

            return None

        except Exception as e:
            import sys

            print(f"⚠ Error getting task for checkpoint: {e}", file=sys.stderr)
            return None

    def suggest_next_task(
        self, project_id: int, completed_task_id: int
    ) -> Optional[Dict[str, Any]]:
        """Suggest next task after completing one.

        Strategy:
        1. In-progress tasks (highest priority first)
        2. Pending tasks with highest priority that are UNBLOCKED
        3. If Phase 3a available, respect task dependencies

        Args:
            project_id: Project ID
            completed_task_id: Task that was just completed

        Returns:
            Suggested next task or None
        """
        try:
            sync = TodoWriteSync()
            tasks = sync.load_tasks_from_postgres(
                project_id=project_id, limit=10, statuses=["pending", "in_progress"]
            )
            sync.close()

            if not tasks:
                return None

            # Try to use dependency manager if Phase 3a available
            try:
                from task_dependency_manager import TaskDependencyManager

                dep_mgr = TaskDependencyManager()
                unblocked_tasks = dep_mgr.get_unblocked_tasks(
                    project_id, statuses=["pending", "in_progress"], limit=10
                )
                dep_mgr_available = True
            except ImportError:
                unblocked_tasks = None
                dep_mgr_available = False

            # Prioritize: in_progress > higher priority pending
            in_progress = [t for t in tasks if t["status"] == "in_progress"]
            if in_progress:
                # If dependency aware, check if suggestion is unblocked
                if dep_mgr_available and unblocked_tasks:
                    unblocked_ids = {t["id"] for t in unblocked_tasks}
                    for task in in_progress:
                        if task["id"] in unblocked_ids:
                            return task
                else:
                    return in_progress[0]

            # Otherwise return highest priority pending (unblocked if available)
            pending = [t for t in tasks if t["status"] == "pending"]
            if pending:
                # Sort by priority descending
                pending.sort(key=lambda t: t.get("priority", 5), reverse=True)

                # If dependency aware, filter to unblocked only
                if dep_mgr_available and unblocked_tasks:
                    unblocked_ids = {t["id"] for t in unblocked_tasks}
                    for task in pending:
                        if task["id"] in unblocked_ids:
                            return task
                else:
                    return pending[0]

            return None

        except Exception as e:
            import sys

            print(f"⚠ Error suggesting next task: {e}", file=sys.stderr)
            return None

    def close(self):
        """Close linker."""
        self.bridge.close()


def test_checkpoint_task_linker():
    """Test checkpoint task linking."""
    import sys

    print("\n=== Checkpoint Task Linker Test ===\n", file=sys.stderr)

    linker = CheckpointTaskLinker()

    # Test 1: Get checkpoint context
    print("1. Getting checkpoint context...", file=sys.stderr)
    # Assuming checkpoint 1 exists from earlier tests
    context = linker.get_checkpoint_context(project_id=1, checkpoint_id=7833)
    if context:
        print(f"  ✓ Found context:", file=sys.stderr)
        print(f"    Task: {context.get('task_name')}", file=sys.stderr)
        print(f"    Test: {context.get('test_name')}", file=sys.stderr)
        print(f"    File: {context.get('file_path')}", file=sys.stderr)
    else:
        print("  ℹ No context found (checkpoint may not have linked task)", file=sys.stderr)

    # Test 2: Suggest next task
    print("\n2. Suggesting next task...", file=sys.stderr)
    next_task = linker.suggest_next_task(project_id=1, completed_task_id=1)
    if next_task:
        print(f"  ✓ Suggested task: {next_task.get('content')}", file=sys.stderr)
        print(f"    Status: {next_task.get('status')}, Priority: {next_task.get('priority')}", file=sys.stderr)
    else:
        print("  ℹ No tasks to suggest", file=sys.stderr)

    linker.close()
    print("\n✓ Checkpoint Task Linker tests complete\n", file=sys.stderr)


if __name__ == "__main__":
    test_checkpoint_task_linker()
