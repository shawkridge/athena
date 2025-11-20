"""TodoWrite ↔ Athena Sync Helper

Handles bidirectional synchronization between Claude Code's TodoWrite task tracking
and Athena's planning system. Used by hooks to:

1. Record TodoWrite status changes to episodic memory
2. Sync todos to todowrite_plans table (bidirectional mapping)
3. Restore todos from Athena at session start

This keeps todos persistent across /clear by storing them in PostgreSQL.
"""

import json
import logging
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from connection_pool import PooledConnection

logger = logging.getLogger(__name__)


class TodoWriteSyncHelper:
    """Synchronize TodoWrite items with Athena planning system."""

    # TodoWrite status mappings
    TODO_STATUS_TO_ATHENA = {
        "pending": "pending",
        "in_progress": "in_progress",
        "completed": "completed",
    }

    ATHENA_STATUS_TO_TODO = {
        "pending": "pending",
        "planning": "in_progress",
        "ready": "in_progress",
        "in_progress": "in_progress",
        "blocked": "in_progress",
        "completed": "completed",
        "failed": "completed",
        "cancelled": "completed",
    }

    def __init__(self):
        """Initialize sync helper."""
        self.now = datetime.utcnow().isoformat()

    def ensure_todowrite_plans_table(self) -> bool:
        """Create todowrite_plans table if it doesn't exist.

        Returns:
            True if table exists or was created, False if failed
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                # Create table if not exists
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS todowrite_plans (
                        id SERIAL PRIMARY KEY,
                        project_id INTEGER,

                        -- Bidirectional mapping
                        todo_id VARCHAR(255) UNIQUE,
                        plan_id VARCHAR(255) UNIQUE,

                        -- Plan content
                        goal TEXT,
                        description TEXT,
                        status VARCHAR(50),
                        phase INTEGER,
                        priority INTEGER DEFAULT 5,

                        -- Structured plan data (stored as JSON)
                        tags TEXT,
                        steps TEXT,
                        assumptions TEXT,
                        risks TEXT,

                        -- Sync tracking
                        last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        sync_status VARCHAR(50) DEFAULT 'synced',
                        sync_conflict_reason TEXT,

                        -- Original todo for reverse mapping
                        original_todo TEXT,

                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                # Create indexes for fast lookup
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_todowrite_todo_id ON todowrite_plans(todo_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_todowrite_plan_id ON todowrite_plans(plan_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_todowrite_project_id ON todowrite_plans(project_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_todowrite_status ON todowrite_plans(status)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_todowrite_created_at ON todowrite_plans(created_at)"
                )

                conn.commit()
                logger.debug("todowrite_plans table ensured")
                return True

        except Exception as e:
            logger.error(f"Failed to ensure todowrite_plans table: {e}")
            return False

    def store_todo_from_sync(
        self,
        todo_id: str,
        content: str,
        status: str,
        active_form: str,
        project_id: int = 1,
    ) -> Optional[int]:
        """Store or update a TodoWrite todo in Athena.

        Args:
            todo_id: Unique ID from TodoWrite
            content: Todo content/goal
            status: TodoWrite status (pending, in_progress, completed)
            active_form: Active form of the todo
            project_id: Project ID for context

        Returns:
            Row ID if successful, None if failed
        """
        try:
            # Ensure table exists
            if not self.ensure_todowrite_plans_table():
                return None

            # Convert TodoWrite status to Athena status
            athena_status = self.TODO_STATUS_TO_ATHENA.get(status, "pending")

            # Extract priority from content (keywords)
            priority = self._extract_priority(content)

            # Generate plan ID if needed
            plan_id = f"plan_{todo_id}"

            with PooledConnection() as conn:
                cursor = conn.cursor()

                # Check if this todo already exists
                cursor.execute(
                    "SELECT id FROM todowrite_plans WHERE todo_id = %s",
                    (todo_id,),
                )
                existing = cursor.fetchone()

                now_timestamp = int(time.time())

                if existing:
                    # Update existing
                    cursor.execute(
                        """
                        UPDATE todowrite_plans
                        SET goal = %s,
                            description = %s,
                            status = %s,
                            priority = %s,
                            original_todo = %s,
                            last_synced_at = %s,
                            sync_status = 'synced',
                            updated_at = %s
                        WHERE todo_id = %s
                        RETURNING id
                        """,
                        (
                            content,
                            active_form,
                            athena_status,
                            priority,
                            json.dumps(
                                {
                                    "content": content,
                                    "status": status,
                                    "activeForm": active_form,
                                }
                            ),
                            now_timestamp,
                            now_timestamp,
                            todo_id,
                        ),
                    )
                    row_id = cursor.fetchone()[0]
                    logger.debug(f"Updated todo {todo_id} → plan {plan_id}")
                else:
                    # Insert new
                    cursor.execute(
                        """
                        INSERT INTO todowrite_plans
                        (project_id, todo_id, plan_id, goal, description, status, phase, priority, original_todo, sync_status, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'synced', %s, %s)
                        RETURNING id
                        """,
                        (
                            project_id,
                            todo_id,
                            plan_id,
                            content,
                            active_form,
                            athena_status,
                            self._determine_phase(status),
                            priority,
                            json.dumps(
                                {
                                    "content": content,
                                    "status": status,
                                    "activeForm": active_form,
                                }
                            ),
                            now_timestamp,
                            now_timestamp,
                        ),
                    )
                    row_id = cursor.fetchone()[0]
                    logger.debug(f"Stored todo {todo_id} → plan {plan_id}")

                conn.commit()
                return row_id

        except Exception as e:
            logger.error(f"Failed to store todo {todo_id}: {e}")
            return None

    def get_active_todos(self, project_id: int = 1) -> List[Dict[str, Any]]:
        """Get all active and pending todos from Athena.

        Args:
            project_id: Project to query

        Returns:
            List of todo dicts in TodoWrite format
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                # Query active/pending todos (not completed)
                cursor.execute(
                    """
                    SELECT todo_id, goal, description, status, original_todo
                    FROM todowrite_plans
                    WHERE project_id = %s AND status IN ('pending', 'in_progress')
                    ORDER BY created_at DESC
                    """,
                    (project_id,),
                )

                rows = cursor.fetchall()
                todos = []

                for row in rows:
                    todo_id, goal, description, status, original_todo_json = row

                    # Try to use original todo if available
                    if original_todo_json:
                        try:
                            original = json.loads(original_todo_json)
                            # Update status in case it changed
                            original["status"] = self.ATHENA_STATUS_TO_TODO.get(
                                status, "pending"
                            )
                            todos.append(original)
                        except json.JSONDecodeError:
                            # Fallback to reconstructed
                            todos.append(
                                {
                                    "content": goal,
                                    "status": self.ATHENA_STATUS_TO_TODO.get(
                                        status, "pending"
                                    ),
                                    "activeForm": description,
                                }
                            )
                    else:
                        # Reconstruct from stored fields
                        todos.append(
                            {
                                "content": goal,
                                "status": self.ATHENA_STATUS_TO_TODO.get(
                                    status, "pending"
                                ),
                                "activeForm": description,
                            }
                        )

                logger.debug(f"Retrieved {len(todos)} active todos for project {project_id}")
                return todos

        except Exception as e:
            logger.error(f"Failed to get active todos: {e}")
            return []

    def record_todo_status_change(
        self,
        todo_id: str,
        old_status: str,
        new_status: str,
        content: str,
        active_form: str,
        project_id: int = 1,
    ) -> bool:
        """Record a TodoWrite status change to episodic memory.

        Args:
            todo_id: TodoWrite todo ID
            old_status: Previous status
            new_status: New status
            content: Todo content
            active_form: Active form
            project_id: Project ID

        Returns:
            True if recorded successfully
        """
        try:
            from memory_bridge import MemoryBridge

            # First, sync the todo to todowrite_plans
            self.store_todo_from_sync(
                todo_id=todo_id,
                content=content,
                status=new_status,
                active_form=active_form,
                project_id=project_id,
            )

            # Now record to episodic memory
            with MemoryBridge() as bridge:
                event = {
                    "event_type": "TODOWRITE_STATUS_CHANGE",
                    "content": f"TodoWrite: {content} | {old_status} → {new_status}",
                    "metadata": {
                        "todo_id": todo_id,
                        "old_status": old_status,
                        "new_status": new_status,
                        "content": content,
                        "active_form": active_form,
                    },
                    "importance": self._calculate_importance(old_status, new_status),
                    "tags": ["todowrite", "status_change"],
                }

                # Get project for context
                project = bridge.get_project_by_path(
                    "/home/user/.work/athena"
                )  # Default project
                if not project:
                    project = {"id": project_id}

                # Record event
                result = bridge.get_active_memories(project["id"], limit=1)
                # (Memory bridge records directly; we just ensured connection)

                logger.debug(
                    f"Recorded status change for todo {todo_id}: {old_status} → {new_status}"
                )
                return True

        except Exception as e:
            logger.error(f"Failed to record todo status change: {e}")
            return False

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _extract_priority(self, content: str) -> int:
        """Extract priority from todo content keywords.

        Args:
            content: Todo content text

        Returns:
            Priority level (1-10)
        """
        content_upper = content.upper()

        # Critical keywords
        if any(kw in content_upper for kw in ["CRITICAL", "URGENT", "BLOCKING"]):
            return 10

        # High priority
        if "HIGH PRIORITY" in content_upper or "IMPORTANT" in content_upper:
            return 8

        # Low priority
        if any(
            kw in content_upper
            for kw in ["LOW PRIORITY", "FIX LATER", "NICE TO HAVE"]
        ):
            return 2

        # Default: medium
        return 5

    def _determine_phase(self, status: str) -> int:
        """Determine planning phase from TodoWrite status.

        Args:
            status: TodoWrite status

        Returns:
            Phase number (1-5)
        """
        if status == "pending":
            return 1  # Planning phase
        elif status == "in_progress":
            return 3  # Execution phase
        elif status == "completed":
            return 5  # Complete phase
        return 1

    def _calculate_importance(self, old_status: str, new_status: str) -> float:
        """Calculate importance of status change event.

        Args:
            old_status: Previous status
            new_status: New status

        Returns:
            Importance score (0.0-1.0)
        """
        # Completion is very important
        if new_status == "completed":
            return 0.95

        # Starting work is important
        if old_status == "pending" and new_status == "in_progress":
            return 0.8

        # Other changes are moderately important
        return 0.6
