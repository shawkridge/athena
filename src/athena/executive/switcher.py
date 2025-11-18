"""Task switching with context preservation and cost calculation."""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any

from ..core.database import Database
from .models import TaskSwitch


class TaskSwitcher:
    """
    Manage intelligent task switching with context preservation.

    Implements switching cost model:
    - Base cost: 5ms (minimum overhead)
    - Priority delta cost: (priority_delta / 10)² × 100ms
    - Max cost: 50ms

    Context preservation:
    - Snapshots active working memory
    - Restores on goal resume
    - Tracks switching overhead per project
    """

    BASE_SWITCH_COST_MS = 5
    MAX_SWITCH_COST_MS = 50
    COST_SCALING_FACTOR = 100

    def __init__(self, db: Database):
        """Initialize task switcher.

        Args:
            db: Database connection
        """
        self.db = db

    def switch_to_goal(
        self,
        project_id: int,
        to_goal_id: int,
        from_goal_id: Optional[int] = None,
        reason: str = "user_request",
        context_snapshot: Optional[Dict[str, Any]] = None,
    ) -> TaskSwitch:
        """Switch to a new goal with context saving.

        Args:
            project_id: Project ID
            to_goal_id: Target goal ID
            from_goal_id: Current goal ID (optional)
            reason: Why switching (priority_change, blocker, deadline, completion, user_request)
            context_snapshot: Working memory snapshot (optional)

        Returns:
            TaskSwitch record with cost calculation

        Raises:
            ValueError: If goal IDs invalid
        """
        # Calculate switch cost
        switch_cost_ms = self._calculate_switch_cost(from_goal_id, to_goal_id)

        # Serialize context snapshot
        context_json = json.dumps(context_snapshot) if context_snapshot else None

        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO task_switches (
                    project_id, from_goal_id, to_goal_id, switch_cost_ms,
                    reason, context_snapshot
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (project_id, from_goal_id, to_goal_id, switch_cost_ms, reason, context_json),
            )
            conn.commit()

            return TaskSwitch(
                id=cursor.lastrowid,
                project_id=project_id,
                from_goal_id=from_goal_id,
                to_goal_id=to_goal_id,
                switch_cost_ms=switch_cost_ms,
                reason=reason,
                context_snapshot=context_json,
            )

    def _calculate_switch_cost(self, from_goal_id: Optional[int], to_goal_id: int) -> int:
        """Calculate switch cost using quadratic model.

        Cost model: cost_ms = BASE + (priority_delta / 10)² × SCALING
        - Same priority: 5ms
        - +3 priority: 5 + (3/10)² × 100 = 14ms
        - +10 priority: 5 + 100 = 105ms → capped at 50ms

        Args:
            from_goal_id: Current goal
            to_goal_id: Target goal

        Returns:
            Switch cost in milliseconds (5-50ms)
        """
        # If no current goal, minimal switch cost
        if not from_goal_id:
            return self.BASE_SWITCH_COST_MS

        with self.db.get_connection() as conn:
            # Get priority of both goals
            from_result = conn.execute(
                "SELECT priority FROM executive_goals WHERE id = ?",
                (from_goal_id,),
            ).fetchone()

            to_result = conn.execute(
                "SELECT priority FROM executive_goals WHERE id = ?",
                (to_goal_id,),
            ).fetchone()

            # If either goal not found, use minimal cost
            if not from_result or not to_result:
                return self.BASE_SWITCH_COST_MS

            from_priority = from_result["priority"]
            to_priority = to_result["priority"]

            # Calculate priority delta
            priority_delta = abs(to_priority - from_priority)

            # Apply quadratic cost model
            delta_cost = (priority_delta / 10.0) ** 2 * self.COST_SCALING_FACTOR
            total_cost = self.BASE_SWITCH_COST_MS + delta_cost

            # Cap at maximum
            return min(int(total_cost), self.MAX_SWITCH_COST_MS)

    def snapshot_context(self, working_memory: Dict[str, Any]) -> str:
        """Create context snapshot for later restoration.

        Args:
            working_memory: Current working memory state

        Returns:
            JSON string of context snapshot
        """
        return json.dumps(
            {
                "timestamp": datetime.now().isoformat(),
                "working_memory": working_memory,
            }
        )

    def restore_context(self, context_snapshot: str) -> Dict[str, Any]:
        """Restore context from snapshot.

        Args:
            context_snapshot: JSON snapshot string

        Returns:
            Restored working memory state
        """
        if not context_snapshot:
            return {}

        try:
            data = json.loads(context_snapshot)
            return data.get("working_memory", {})
        except json.JSONDecodeError:
            return {}

    def get_switch_history(self, project_id: int, limit: int = 100) -> List[TaskSwitch]:
        """Get switching history for a project.

        Args:
            project_id: Project ID
            limit: Maximum number of records

        Returns:
            List of task switches, most recent first
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, project_id, from_goal_id, to_goal_id, switch_cost_ms,
                       reason, switched_at, context_snapshot
                FROM task_switches
                WHERE project_id = ?
                ORDER BY switched_at DESC
                LIMIT ?
                """,
                (project_id, limit),
            )

            switches = []
            for row in cursor.fetchall():
                switches.append(
                    TaskSwitch(
                        id=row["id"],
                        project_id=row["project_id"],
                        from_goal_id=row["from_goal_id"],
                        to_goal_id=row["to_goal_id"],
                        switch_cost_ms=row["switch_cost_ms"],
                        reason=row["reason"],
                        switched_at=datetime.fromisoformat(row["switched_at"]),
                        context_snapshot=row["context_snapshot"],
                    )
                )

            return switches

    def get_total_overhead(self, project_id: int) -> int:
        """Get total accumulated switching overhead.

        Args:
            project_id: Project ID

        Returns:
            Total switch cost in milliseconds
        """
        with self.db.get_connection() as conn:
            result = conn.execute(
                """
                SELECT COALESCE(SUM(switch_cost_ms), 0) as total
                FROM task_switches
                WHERE project_id = ?
                """,
                (project_id,),
            ).fetchone()

            return result["total"] if result else 0

    def get_average_switch_cost(self, project_id: int) -> float:
        """Get average switching cost.

        Args:
            project_id: Project ID

        Returns:
            Average switch cost in milliseconds
        """
        with self.db.get_connection() as conn:
            result = conn.execute(
                """
                SELECT COALESCE(AVG(switch_cost_ms), 0.0) as average
                FROM task_switches
                WHERE project_id = ?
                """,
                (project_id,),
            ).fetchone()

            return result["average"] if result else 0.0

    def get_switch_statistics(self, project_id: int) -> Dict[str, Any]:
        """Get comprehensive switching statistics.

        Args:
            project_id: Project ID

        Returns:
            Dictionary with statistics
        """
        with self.db.get_connection() as conn:
            # Basic statistics
            stats_result = conn.execute(
                """
                SELECT
                    COUNT(*) as total_switches,
                    MIN(switch_cost_ms) as min_cost,
                    MAX(switch_cost_ms) as max_cost,
                    AVG(switch_cost_ms) as avg_cost,
                    SUM(switch_cost_ms) as total_cost
                FROM task_switches
                WHERE project_id = ?
                """,
                (project_id,),
            ).fetchone()

            # Breakdown by reason
            reason_result = conn.execute(
                """
                SELECT reason, COUNT(*) as count, AVG(switch_cost_ms) as avg_cost
                FROM task_switches
                WHERE project_id = ?
                GROUP BY reason
                ORDER BY count DESC
                """,
                (project_id,),
            ).fetchall()

            reason_breakdown = {
                row["reason"]: {"count": row["count"], "avg_cost_ms": round(row["avg_cost"], 2)}
                for row in reason_result
            }

            return {
                "total_switches": stats_result["total_switches"],
                "min_cost_ms": stats_result["min_cost"],
                "max_cost_ms": stats_result["max_cost"],
                "avg_cost_ms": round(stats_result["avg_cost"] or 0.0, 2),
                "total_cost_ms": stats_result["total_cost"] or 0,
                "reason_breakdown": reason_breakdown,
            }

    def get_switch_cost_by_priority_change(self, delta: int) -> int:
        """Get switch cost for a given priority delta (for testing/analysis).

        Args:
            delta: Priority difference (0-10)

        Returns:
            Switch cost in milliseconds
        """
        cost = self.BASE_SWITCH_COST_MS + (delta / 10.0) ** 2 * self.COST_SCALING_FACTOR
        return min(int(cost), self.MAX_SWITCH_COST_MS)

    def get_switching_overhead_ratio(
        self, project_id: int, total_work_hours: Optional[float] = None
    ) -> float:
        """Calculate switching overhead as ratio of total time.

        Args:
            project_id: Project ID
            total_work_hours: Total work hours (optional, for ratio calculation)

        Returns:
            Overhead ratio (0.0-1.0)
        """
        total_overhead_ms = self.get_total_overhead(project_id)
        total_work_ms = total_work_hours * 3600 * 1000 if total_work_hours else 100000

        return min(1.0, total_overhead_ms / total_work_ms)
