"""Prospective integration for task triggers and memory.

Uses prospective memory (Memory-MCP's task triggers) to:
- Create new tasks based on learned patterns
- Trigger tasks at appropriate times
- Evaluate task feasibility using historical data
- Track task creation effectiveness

This enables proactive learning: Pattern → Task Trigger → Future Work
"""

import json
from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from athena.core.database import Database


class ProspectiveTask:
    """A prospective task created from learning."""

    def __init__(
        self,
        content: str,
        priority: str,
        trigger_type: str,
        trigger_value: str,
        source_pattern_id: int,
        estimated_effort_hours: float
    ):
        """Initialize prospective task.

        Args:
            content: Task description
            priority: Priority (low, medium, high, critical)
            trigger_type: Trigger type (time, event, context, file)
            trigger_value: When/how to trigger
            source_pattern_id: Pattern ID that triggered task creation
            estimated_effort_hours: Estimated effort
        """
        self.content = content
        self.priority = priority
        self.trigger_type = trigger_type
        self.trigger_value = trigger_value
        self.source_pattern_id = source_pattern_id
        self.estimated_effort_hours = estimated_effort_hours


class ProspectiveIntegration:
    """Integrates prospective memory for task management.

    Purpose:
    - Create tasks from learned patterns
    - Set up task triggers for future work
    - Evaluate task feasibility using history
    - Track effectiveness of created tasks
    - Enable proactive learning and planning

    This creates forward-looking tasks:
    Learned Pattern → Trigger Defined → Task Ready for Future
    """

    def __init__(self, db: "Database"):
        """Initialize ProspectiveIntegration.

        Args:
            db: Database connection
        """
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self):
        """Create prospective integration tables."""
        cursor = self.db.get_cursor()

        # Table: Prospective tasks created from learning
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prospective_tasks (
                id INTEGER PRIMARY KEY,
                task_content TEXT NOT NULL,
                priority TEXT NOT NULL,
                trigger_type TEXT NOT NULL,
                trigger_value TEXT,
                source_pattern_id INTEGER,
                estimated_effort_hours REAL,
                feasibility_score REAL DEFAULT 0.5,
                created_at INTEGER NOT NULL,
                triggered_at INTEGER,
                completed_at INTEGER,
                status TEXT DEFAULT 'pending'  -- pending, triggered, active, completed, cancelled
            )
        """)

        # Table: Task effectiveness tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_effectiveness (
                id INTEGER PRIMARY KEY,
                task_id INTEGER NOT NULL,
                trigger_event TEXT,
                was_useful BOOLEAN,
                actual_effort_hours REAL,
                outcome TEXT,  -- useful, marginally_useful, not_useful
                feedback TEXT,
                recorded_at INTEGER NOT NULL,
                FOREIGN KEY (task_id) REFERENCES prospective_tasks(id)
            )
        """)

        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_prospective_tasks_status
            ON prospective_tasks(status, priority)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_prospective_tasks_trigger
            ON prospective_tasks(trigger_type, trigger_value)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_effectiveness_outcome
            ON task_effectiveness(outcome)
        """)

        # commit handled by cursor context

    def create_prospective_task(
        self,
        task: ProspectiveTask,
        goal_context: Optional[str] = None
    ) -> int:
        """Create a prospective task from a pattern.

        Args:
            task: ProspectiveTask to create
            goal_context: Optional goal context

        Returns:
            Task ID
        """
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp() * 1000)

        # Calculate feasibility
        feasibility = self._calculate_feasibility(task)

        cursor.execute("""
            INSERT INTO prospective_tasks
            (task_content, priority, trigger_type, trigger_value,
             source_pattern_id, estimated_effort_hours, feasibility_score,
             created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task.content,
            task.priority,
            task.trigger_type,
            task.trigger_value,
            task.source_pattern_id,
            task.estimated_effort_hours,
            feasibility,
            now,
            "pending"
        ))

        task_id = cursor.lastrowid
        # commit handled by cursor context
        return task_id

    def should_trigger_task(self, task_id: int, current_context: dict) -> bool:
        """Determine if a task should be triggered now.

        Args:
            task_id: Task ID
            current_context: Current context (goal, session, time, etc)

        Returns:
            True if task should be triggered
        """
        cursor = self.db.get_cursor()

        cursor.execute("""
            SELECT trigger_type, trigger_value, status
            FROM prospective_tasks
            WHERE id = ?
        """, (task_id,))

        row = cursor.fetchone()
        if not row:
            return False

        trigger_type, trigger_value, status = row

        if status != "pending":
            return False

        # Check trigger conditions
        if trigger_type == "time":
            # Would check if current time matches trigger_value
            return self._check_time_trigger(trigger_value)
        elif trigger_type == "event":
            # Would check if event occurred
            return self._check_event_trigger(trigger_value, current_context)
        elif trigger_type == "context":
            # Would check current context
            return self._check_context_trigger(trigger_value, current_context)
        elif trigger_type == "file":
            # Would check file modification
            return self._check_file_trigger(trigger_value)

        return False

    def trigger_task(self, task_id: int) -> bool:
        """Mark a task as triggered.

        Args:
            task_id: Task ID

        Returns:
            Success status
        """
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp() * 1000)

        cursor.execute("""
            UPDATE prospective_tasks
            SET status = 'triggered', triggered_at = ?
            WHERE id = ?
        """, (now, task_id))

        # commit handled by cursor context
        return cursor.rowcount > 0

    def complete_task(self, task_id: int) -> bool:
        """Mark a task as completed.

        Args:
            task_id: Task ID

        Returns:
            Success status
        """
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp() * 1000)

        cursor.execute("""
            UPDATE prospective_tasks
            SET status = 'completed', completed_at = ?
            WHERE id = ?
        """, (now, task_id))

        # commit handled by cursor context
        return cursor.rowcount > 0

    def record_task_effectiveness(
        self,
        task_id: int,
        was_useful: bool,
        actual_effort_hours: Optional[float],
        outcome: str,
        feedback: Optional[str] = None
    ) -> int:
        """Record effectiveness of a triggered task.

        Args:
            task_id: Task ID
            was_useful: Whether task was useful
            actual_effort_hours: Actual effort spent
            outcome: Outcome (useful, marginally_useful, not_useful)
            feedback: Optional feedback

        Returns:
            Effectiveness record ID
        """
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp() * 1000)

        cursor.execute("""
            INSERT INTO task_effectiveness
            (task_id, was_useful, actual_effort_hours, outcome,
             feedback, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (task_id, was_useful, actual_effort_hours, outcome, feedback, now))

        effectiveness_id = cursor.lastrowid

        # Update task status and feasibility
        self._update_task_feasibility(task_id)

        # commit handled by cursor context
        return effectiveness_id

    def get_pending_tasks(self) -> list[dict]:
        """Get all pending prospective tasks.

        Returns:
            List of pending task dicts
        """
        cursor = self.db.get_cursor()

        try:
            cursor.execute("""
                SELECT id, task_content, priority, trigger_type,
                       estimated_effort_hours, feasibility_score
                FROM prospective_tasks
                WHERE status = 'pending'
                ORDER BY priority DESC, feasibility_score DESC
            """)

            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    "id": row[0],
                    "content": row[1],
                    "priority": row[2],
                    "trigger_type": row[3],
                    "estimated_effort": row[4],
                    "feasibility": row[5],
                })

            return tasks
        except Exception:
            # Table doesn't exist yet - return empty list
            return []

    def get_task_effectiveness_metrics(self) -> dict:
        """Get metrics on task effectiveness.

        Returns:
            Effectiveness metrics dict
        """
        cursor = self.db.get_cursor()

        # Count by outcome
        cursor.execute("""
            SELECT outcome, COUNT(*), AVG(actual_effort_hours)
            FROM task_effectiveness
            GROUP BY outcome
        """)

        by_outcome = {}
        for row in cursor.fetchall():
            by_outcome[row[0]] = {
                "count": row[1],
                "average_effort": row[2],
            }

        # Overall usefulness
        cursor.execute("""
            SELECT COUNT(*), SUM(CASE WHEN was_useful THEN 1 ELSE 0 END)
            FROM task_effectiveness
        """)

        row = cursor.fetchone()
        total_tracked = row[0] or 0
        useful_count = row[1] or 0
        usefulness_rate = (useful_count / total_tracked * 100) if total_tracked > 0 else 0

        return {
            "total_tasks_tracked": total_tracked,
            "usefulness_rate": usefulness_rate,
            "by_outcome": by_outcome,
        }

    def _calculate_feasibility(self, task: ProspectiveTask) -> float:
        """Calculate feasibility score for a task.

        Args:
            task: ProspectiveTask

        Returns:
            Feasibility score (0.0-1.0)
        """
        score = 0.5  # Base score

        # Adjust based on effort estimate
        if task.estimated_effort_hours < 1:
            score += 0.2
        elif task.estimated_effort_hours > 4:
            score -= 0.2

        # Adjust based on priority
        priority_boost = {
            "low": 0,
            "medium": 0.1,
            "high": 0.2,
            "critical": 0.3
        }
        score += priority_boost.get(task.priority, 0)

        return min(score, 1.0)

    def _update_task_feasibility(self, task_id: int):
        """Update feasibility score based on effectiveness.

        Args:
            task_id: Task ID
        """
        cursor = self.db.get_cursor()

        cursor.execute("""
            SELECT AVG(CASE WHEN was_useful THEN 1 ELSE 0 END)
            FROM task_effectiveness
            WHERE task_id = ?
        """, (task_id,))

        row = cursor.fetchone()
        effectiveness = row[0] or 0.5

        cursor.execute("""
            UPDATE prospective_tasks
            SET feasibility_score = ?
            WHERE id = ?
        """, (effectiveness, task_id))

    def _check_time_trigger(self, trigger_value: str) -> bool:
        """Check if time-based trigger should fire.

        Args:
            trigger_value: Trigger time value

        Returns:
            True if should trigger
        """
        # Would check if current time matches trigger_value
        return False

    def _check_event_trigger(self, trigger_value: str, context: dict) -> bool:
        """Check if event-based trigger should fire.

        Args:
            trigger_value: Event trigger value
            context: Current context

        Returns:
            True if should trigger
        """
        # Would check if event occurred in context
        return False

    def _check_context_trigger(self, trigger_value: str, context: dict) -> bool:
        """Check if context-based trigger should fire.

        Args:
            trigger_value: Context trigger value
            context: Current context

        Returns:
            True if should trigger
        """
        # Would check if current context matches trigger
        return False

    def _check_file_trigger(self, trigger_value: str) -> bool:
        """Check if file-based trigger should fire.

        Args:
            trigger_value: File path trigger value

        Returns:
            True if should trigger
        """
        # Would check if file was modified
        return False
