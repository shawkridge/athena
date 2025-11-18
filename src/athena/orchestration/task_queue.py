"""Task queue backed by episodic memory.

Manages task lifecycle: create → assign → run → complete/fail
Tasks are stored as episodic events for durability and learning.
"""

import uuid
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from ..episodic.store import EpisodicStore
from ..episodic.models import EpisodicEvent, EventType, EventOutcome
from ..graph.store import GraphStore
from .models import Task, TaskStatus, TaskPriority, QueueStatistics


class TaskQueue:
    """Manage task lifecycle in episodic memory.

    Tasks are stored as episodic events, enabling:
    - Durable persistence
    - Consolidation analysis (extract workflow patterns)
    - Audit trail (all transitions recorded)
    - Integration with memory layers
    """

    def __init__(self, episodic_store: EpisodicStore, graph_store: GraphStore):
        """Initialize task queue.

        Args:
            episodic_store: EpisodicStore instance for task storage
            graph_store: GraphStore instance (for future integration)
        """
        self.episodic = episodic_store
        self.graph = graph_store
        self.db = episodic_store.db

    def create_task(
        self,
        content: str,
        task_type: str,
        priority: str = "medium",
        requirements: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        project_id: int = 1,
    ) -> str:
        """Create task, return task_id.

        Args:
            content: Task description/prompt
            task_type: Type of task (research, analysis, synthesis, etc.)
            priority: low, medium, high
            requirements: Required agent capabilities
            dependencies: Task IDs this depends on
            project_id: Project context ID (default: 1)

        Returns:
            task_id (UUID string)
        """
        task_id = str(uuid.uuid4())
        now = int(datetime.now().timestamp())

        # Create episodic event for task creation
        event = EpisodicEvent(
            project_id=project_id,
            session_id="orchestration",
            event_type=EventType.ACTION,
            content=content,
            outcome=EventOutcome.ONGOING,
        )

        # Store event and get ID
        event_id = self.episodic.record_event(event)

        # Now update with task-specific fields
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            UPDATE episodic_events
            SET task_id = ?,
                task_type = ?,
                task_status = 'pending',
                priority = ?,
                requirements = ?,
                dependencies = ?
            WHERE id = ?
            """,
            [
                task_id,
                task_type,
                priority,
                json.dumps(requirements or []),
                json.dumps(dependencies or []),
                event_id,
            ],
        )
        # commit handled by cursor context

        return task_id

    def poll_tasks(
        self,
        agent_id: Optional[str] = None,
        status: str = "pending",
        limit: int = 10,
    ) -> List[Task]:
        """Get pending/assigned tasks for agent.

        Args:
            agent_id: If specified, only tasks assigned to this agent
            status: pending, assigned, running
            limit: Max tasks to return

        Returns:
            List of Task objects
        """
        cursor = self.db.get_cursor()

        query = """
            SELECT * FROM episodic_events
            WHERE task_status = ? AND task_id IS NOT NULL
        """
        params = [status]

        if agent_id:
            query += " AND assigned_to = ?"
            params.append(agent_id)

        query += f" ORDER BY CASE priority WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 ELSE 0 END DESC, timestamp ASC LIMIT {limit}"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [self._row_to_task(row) for row in rows]

    def assign_task(self, task_id: str, agent_id: str) -> None:
        """Assign task to agent.

        Args:
            task_id: Task UUID
            agent_id: Agent ID

        Raises:
            ValueError: If task not found
        """
        cursor = self.db.get_cursor()

        # Verify task exists
        cursor.execute("SELECT id FROM episodic_events WHERE task_id = ?", [task_id])
        if not cursor.fetchone():
            raise ValueError(f"Task {task_id} not found")

        now = int(datetime.now().timestamp())

        cursor.execute(
            """
            UPDATE episodic_events
            SET task_status = 'assigned',
                assigned_to = ?,
                assigned_at = ?
            WHERE task_id = ?
            """,
            [agent_id, now, task_id],
        )
        # commit handled by cursor context

    def start_task(self, task_id: str) -> None:
        """Mark task as running.

        Args:
            task_id: Task UUID
        """
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp())

        cursor.execute(
            """
            UPDATE episodic_events
            SET task_status = 'running', started_at = ?
            WHERE task_id = ?
            """,
            [now, task_id],
        )
        # commit handled by cursor context

    def complete_task(
        self,
        task_id: str,
        result: str,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mark task complete with result.

        Args:
            task_id: Task UUID
            result: Result content/output
            metrics: Execution metrics {duration_ms, rows_processed, ...}
        """
        metrics = metrics or {}
        duration = metrics.get("duration_ms", 0)
        now = int(datetime.now().timestamp())

        cursor = self.db.get_cursor()

        cursor.execute(
            """
            UPDATE episodic_events
            SET task_status = 'completed',
                completed_at = ?,
                execution_duration_ms = ?,
                success = 1
            WHERE task_id = ?
            """,
            [now, duration, task_id],
        )
        # commit handled by cursor context

        # TODO: Store result as separate linked event
        # TODO: Publish task_completed event for subscribers (Phase 2)

    def fail_task(self, task_id: str, error: str, should_retry: bool = True) -> None:
        """Mark task failed, optionally retry.

        Args:
            task_id: Task UUID
            error: Error message
            should_retry: Whether to schedule retry
        """
        cursor = self.db.get_cursor()

        if should_retry:
            # Retry: reset status, increment counter
            cursor.execute(
                """
                UPDATE episodic_events
                SET task_status = 'pending',
                    assigned_to = NULL,
                    retry_count = retry_count + 1,
                    error_message = NULL
                WHERE task_id = ?
                """,
                [task_id],
            )
        else:
            # No retry: mark failed
            now = int(datetime.now().timestamp())
            cursor.execute(
                """
                UPDATE episodic_events
                SET task_status = 'failed',
                    error_message = ?,
                    completed_at = ?
                WHERE task_id = ?
                """,
                [error, now, task_id],
            )

        # commit handled by cursor context

        # TODO: Publish task_failed event for subscribers (Phase 2)

    def get_task_status(self, task_id: str) -> Optional[Task]:
        """Get current task state.

        Args:
            task_id: Task UUID

        Returns:
            Task object or None if not found
        """
        cursor = self.db.get_cursor()
        cursor.execute("SELECT * FROM episodic_events WHERE task_id = ?", [task_id])
        row = cursor.fetchone()
        return self._row_to_task(row) if row else None

    def query_tasks(self, filters: Dict[str, Any]) -> List[Task]:
        """Complex query with multiple filters.

        Filters:
            status: pending, assigned, running, completed, failed
            agent_id: assigned to agent
            task_type: specific task type
            priority: low, medium, high
            created_after: timestamp (int)
            created_before: timestamp (int)

        Args:
            filters: Query filters

        Returns:
            List of matching tasks
        """
        cursor = self.db.get_cursor()

        query = "SELECT * FROM episodic_events WHERE task_id IS NOT NULL"
        params = []

        if "status" in filters:
            query += " AND task_status = ?"
            params.append(filters["status"])

        if "agent_id" in filters:
            query += " AND assigned_to = ?"
            params.append(filters["agent_id"])

        if "task_type" in filters:
            query += " AND task_type = ?"
            params.append(filters["task_type"])

        if "priority" in filters:
            query += " AND priority = ?"
            params.append(filters["priority"])

        if "created_after" in filters:
            query += " AND timestamp > ?"
            params.append(filters["created_after"])

        if "created_before" in filters:
            query += " AND timestamp < ?"
            params.append(filters["created_before"])

        query += " ORDER BY CASE priority WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 ELSE 0 END DESC, timestamp ASC"

        cursor.execute(query, params)
        return [self._row_to_task(row) for row in cursor.fetchall()]

    def get_queue_statistics(self) -> QueueStatistics:
        """Get statistics about queue state.

        Returns:
            QueueStatistics with counts and metrics
        """
        cursor = self.db.get_cursor()

        # Count by status
        cursor.execute(
            """
            SELECT task_status, COUNT(*) as count
            FROM episodic_events
            WHERE task_id IS NOT NULL
            GROUP BY task_status
            """
        )
        status_counts = {row["task_status"]: row["count"] for row in cursor.fetchall()}

        # Success rate
        cursor.execute(
            """
            SELECT
                COUNT(CASE WHEN success = 1 THEN 1 END) as succeeded,
                COUNT(CASE WHEN success = 0 THEN 1 END) as failed
            FROM episodic_events
            WHERE task_status = 'completed' AND task_id IS NOT NULL
            """
        )
        success_row = cursor.fetchone()
        succeeded = success_row["succeeded"] or 0
        failed = success_row["failed"] or 0
        success_rate = succeeded / (succeeded + failed) if (succeeded + failed) > 0 else 0.0

        # Average execution time
        cursor.execute(
            """
            SELECT AVG(execution_duration_ms) as avg_duration
            FROM episodic_events
            WHERE task_status = 'completed' AND execution_duration_ms IS NOT NULL
            """
        )
        avg_row = cursor.fetchone()
        avg_duration = avg_row["avg_duration"] or 0.0

        return QueueStatistics(
            pending_count=status_counts.get("pending", 0),
            assigned_count=status_counts.get("assigned", 0),
            running_count=status_counts.get("running", 0),
            completed_count=status_counts.get("completed", 0),
            failed_count=status_counts.get("failed", 0),
            success_rate=success_rate,
            avg_execution_time_ms=avg_duration,
        )

    # Private helpers

    def _row_to_task(self, row: Any) -> Task:
        """Convert database row to Task object.

        Args:
            row: Database row (psycopg Record)

        Returns:
            Task instance
        """
        requirements = []
        if row["requirements"]:
            try:
                requirements = json.loads(row["requirements"])
            except (json.JSONDecodeError, TypeError):
                requirements = []

        dependencies = []
        if row["dependencies"]:
            try:
                dependencies = json.loads(row["dependencies"])
            except (json.JSONDecodeError, TypeError):
                dependencies = []

        created_at = None
        if row["timestamp"]:
            created_at = datetime.fromtimestamp(row["timestamp"])

        assigned_at = None
        if row["assigned_at"]:
            assigned_at = datetime.fromtimestamp(row["assigned_at"])

        started_at = None
        if row["started_at"]:
            started_at = datetime.fromtimestamp(row["started_at"])

        completed_at = None
        if row["completed_at"]:
            completed_at = datetime.fromtimestamp(row["completed_at"])

        return Task(
            id=row["task_id"],
            content=row["content"] or "",
            task_type=row["task_type"] or "",
            status=TaskStatus(row["task_status"] or "pending"),
            priority=TaskPriority(row["priority"] or "medium"),
            requirements=requirements,
            dependencies=dependencies,
            assigned_to=row["assigned_to"],
            created_at=created_at,
            assigned_at=assigned_at,
            started_at=started_at,
            completed_at=completed_at,
            result=row["content"],  # Could store separately
            error=row["error_message"],
            retry_count=row["retry_count"] or 0,
            execution_duration_ms=row["execution_duration_ms"],
        )
