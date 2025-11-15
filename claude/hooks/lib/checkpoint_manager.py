"""Checkpoint Manager for session continuity.

Manages operational checkpoints that enable autonomous continuation of work.
A checkpoint captures: task, file, test, next action (+ current state).

This allows sessions to resume with full context, not just semantic memory.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from memory_bridge import MemoryBridge
from connection_pool import PooledConnection


class CheckpointSchema:
    """Define the checkpoint data structure."""

    VERSION = "1.0"

    @staticmethod
    def create(
        task_name: str,
        file_path: str,
        test_name: str,
        next_action: str,
        status: str = "in_progress",
        test_status: str = "not_run",
        error_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a checkpoint dictionary.

        Args:
            task_name: What we're building
            file_path: File being worked on
            test_name: Test that defines success
            next_action: Specific actionable next step
            status: in_progress|blocked|ready
            test_status: passing|failing|not_run
            error_message: Error message if test failing

        Returns:
            Checkpoint dict
        """
        return {
            "checkpoint_version": CheckpointSchema.VERSION,
            "task_name": task_name,
            "file_path": file_path,
            "test_name": test_name,
            "next_action": next_action,
            "status": status,
            "test_status": test_status,
            "error_message": error_message,
            "last_updated": datetime.utcnow().isoformat(),
        }


class CheckpointManager:
    """Manage session checkpoints for work continuity."""

    def __init__(self):
        """Initialize checkpoint manager with memory bridge."""
        self.bridge = MemoryBridge()

    def save_checkpoint(
        self,
        project_id: int,
        task_name: str,
        file_path: str,
        test_name: str,
        next_action: str,
        status: str = "in_progress",
        test_status: str = "not_run",
        error_message: Optional[str] = None,
    ) -> Optional[int]:
        """Save a checkpoint for session resumption.

        Args:
            project_id: Project ID
            task_name: What we're building
            file_path: File being worked on
            test_name: Test that defines success
            next_action: Specific actionable next step
            status: in_progress|blocked|ready
            test_status: passing|failing|not_run
            error_message: Error if test failing

        Returns:
            Event ID or None if failed
        """
        checkpoint = CheckpointSchema.create(
            task_name=task_name,
            file_path=file_path,
            test_name=test_name,
            next_action=next_action,
            status=status,
            test_status=test_status,
            error_message=error_message,
        )

        content = json.dumps(checkpoint)

        return self.bridge.record_event(
            project_id=project_id,
            event_type="SESSION_CHECKPOINT",
            content=content,
            outcome="checkpoint_saved",
        )

    def load_latest_checkpoint(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Load the most recent checkpoint for a project.

        Args:
            project_id: Project ID

        Returns:
            Checkpoint dict or None if not found
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                # Get the most recent checkpoint
                cursor.execute(
                    """
                    SELECT content, timestamp FROM episodic_events
                    WHERE project_id = %s AND event_type = 'SESSION_CHECKPOINT'
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """,
                    (project_id,),
                )

                row = cursor.fetchone()
                if row:
                    content = row[0]
                    timestamp = row[1]

                    # Parse JSON
                    checkpoint = json.loads(content)
                    checkpoint["_loaded_timestamp"] = timestamp
                    return checkpoint

                return None

        except Exception as e:
            print(f"⚠ Error loading checkpoint: {e}", file=__import__("sys").stderr)
            return None

    def close(self):
        """Close manager."""
        self.bridge.close()


def test_checkpoint_flow():
    """Test checkpoint save and load."""
    manager = CheckpointManager()

    # Get or create test project
    project_id = 1  # Default project

    # Save a checkpoint
    event_id = manager.save_checkpoint(
        project_id=project_id,
        task_name="Implement feature X",
        file_path="src/auth.ts",
        test_name="test_jwt_validation",
        next_action="Add token refresh logic in refresh handler",
        status="in_progress",
        test_status="failing",
        error_message="Assertion: token should not be null",
    )

    print(f"Saved checkpoint with ID: {event_id}")

    # Load it back
    checkpoint = manager.load_latest_checkpoint(project_id)
    if checkpoint:
        print(f"✓ Loaded checkpoint:")
        print(f"  Task: {checkpoint['task_name']}")
        print(f"  File: {checkpoint['file_path']}")
        print(f"  Test: {checkpoint['test_name']}")
        print(f"  Next: {checkpoint['next_action']}")
        print(f"  Test Status: {checkpoint['test_status']}")
        if checkpoint["error_message"]:
            print(f"  Error: {checkpoint['error_message']}")
    else:
        print("✗ No checkpoint loaded")

    manager.close()


if __name__ == "__main__":
    test_checkpoint_flow()
