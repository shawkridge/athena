"""Executive function metrics and efficiency tracking."""

from datetime import datetime, timedelta, date
from typing import Optional, Dict, List
from dataclasses import dataclass
from statistics import mean, stdev

from .models import GoalStatus


@dataclass
class MetricsSnapshot:
    """Snapshot of executive function metrics."""

    project_id: int
    metric_date: date
    total_goals: int
    completed_goals: int
    abandoned_goals: int
    failed_goals: int
    success_rate: float  # completed / (completed + abandoned + failed)
    average_switch_cost_ms: float
    total_switch_overhead_ms: int
    average_goal_completion_hours: Optional[float]
    efficiency_score: float  # 0-100


class ExecutiveMetrics:
    """
    Tracks executive function metrics.

    Efficiency Score Calculation:
    efficiency = 100 × (completed_goals / total_goals) × (1 - switch_overhead_ratio)
    switch_overhead_ratio = total_switch_ms / (total_goal_duration_ms)

    Target: >85% efficiency (good), <70% (needs improvement)
    """

    def __init__(self, db_path: str):
        """Initialize metrics tracker."""
        self.db_path = db_path

    async def calculate_metrics(self, project_id: int, date_range: Optional[tuple] = None) -> MetricsSnapshot:
        """
        Calculate metrics for a project.

        Args:
            project_id: Project ID
            date_range: Optional tuple (start_date, end_date) for filtering

        Returns:
            MetricsSnapshot with current metrics
        """
        async with AsyncConnection.connect(self.postgres_url) as conn:
            async with conn.cursor() as cursor:
                # Count goals by status
                status_query = "SELECT status, COUNT(*) FROM executive_goals WHERE project_id = ?"
                status_params = [project_id]

                if date_range:
                    status_query += " AND created_at >= ? AND created_at <= ?"
                    status_params.extend([date_range[0].isoformat(), date_range[1].isoformat()])

                status_query += " GROUP BY status"

                await cursor.execute(status_query, status_params)
                status_counts = {row[0]: row[1] for row in await cursor.fetchall()}

                completed = status_counts.get("completed", 0)
                abandoned = status_counts.get("abandoned", 0)
                failed = status_counts.get("failed", 0)
                total_goals = completed + abandoned + failed + status_counts.get("active", 0)

                # Calculate success rate
                terminal_goals = completed + abandoned + failed
                success_rate = completed / terminal_goals if terminal_goals > 0 else 0.0

                # Get switching metrics
                switch_metrics = await self._calculate_switch_overhead(project_id, cursor)

                # Get completion time distribution
                completion_times = await self._get_completion_times(project_id, cursor)
                avg_completion_hours = mean(completion_times) if completion_times else None

                # Calculate efficiency score
                efficiency_score = self._calculate_efficiency_score(
                    completed, total_goals, switch_metrics["total_ms"], completion_times
                )

                # Record metrics
                await cursor.execute(
                    """
                    INSERT INTO executive_metrics
                    (project_id, metric_date, total_goals, completed_goals, abandoned_goals,
                     average_switch_cost_ms, total_switch_overhead_ms, average_goal_completion_hours,
                     success_rate, efficiency_score)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        project_id,
                        date.today().isoformat(),
                        total_goals,
                        completed,
                        abandoned,
                        switch_metrics["average_ms"],
                        switch_metrics["total_ms"],
                        avg_completion_hours,
                        success_rate,
                        efficiency_score,
                    ),
                )
                await conn.commit()

                return MetricsSnapshot(
                    project_id=project_id,
                    metric_date=date.today(),
                    total_goals=total_goals,
                    completed_goals=completed,
                    abandoned_goals=abandoned,
                    failed_goals=failed,
                    success_rate=success_rate,
                    average_switch_cost_ms=switch_metrics["average_ms"],
                    total_switch_overhead_ms=switch_metrics["total_ms"],
                    average_goal_completion_hours=avg_completion_hours,
                    efficiency_score=efficiency_score,
                )

    async def get_metrics_trend(self, project_id: int, days: int = 30) -> List[MetricsSnapshot]:
        """Get metrics trend over time."""
        metrics = []

        async with AsyncConnection.connect(self.postgres_url) as conn:
            async with conn.cursor() as cursor:
                start_date = (date.today() - timedelta(days=days)).isoformat()

                await cursor.execute(
                    """
                    SELECT project_id, metric_date, total_goals, completed_goals, abandoned_goals,
                           average_switch_cost_ms, total_switch_overhead_ms, average_goal_completion_hours,
                           success_rate, efficiency_score
                    FROM executive_metrics
                    WHERE project_id = ? AND metric_date >= ?
                    ORDER BY metric_date ASC
                    """,
                    (project_id, start_date),
                )

                for row in await cursor.fetchall():
                    snapshot = MetricsSnapshot(
                        project_id=row[0],
                        metric_date=datetime.fromisoformat(row[1]).date(),
                        total_goals=row[2],
                        completed_goals=row[3],
                        abandoned_goals=row[4],
                        average_switch_cost_ms=row[5],
                        total_switch_overhead_ms=row[6],
                        average_goal_completion_hours=row[7],
                        efficiency_score=row[9],
                        success_rate=row[8],
                        failed_goals=0,  # Not stored, but can be calculated
                    )
                    metrics.append(snapshot)

        return metrics

    async def calculate_strategy_effectiveness(
        self, project_id: int, strategy_name: str
    ) -> Optional[Dict]:
        """
        Calculate effectiveness of a strategy.

        Returns: {
            'strategy': str,
            'total_used': int,
            'success_count': int,
            'failure_count': int,
            'success_rate': float,
            'avg_hours_to_complete': float
        }
        """
        async with AsyncConnection.connect(self.postgres_url) as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT outcome, COUNT(*) as count, AVG(hours_actual) as avg_hours
                    FROM strategy_recommendations sr
                    JOIN executive_goals eg ON sr.goal_id = eg.id
                    WHERE eg.project_id = ? AND sr.strategy_name = ? AND sr.outcome IS NOT NULL
                    GROUP BY outcome
                    """,
                    (project_id, strategy_name),
                )

                results = await cursor.fetchall()
                if not results:
                    return None

                outcome_data = {row[0]: {"count": row[1], "avg_hours": row[2]} for row in results}

                success_count = outcome_data.get("success", {}).get("count", 0)
                failure_count = outcome_data.get("failure", {}).get("count", 0)
                total_used = success_count + failure_count + outcome_data.get("partial", {}).get("count", 0)

                success_rate = success_count / total_used if total_used > 0 else 0.0

                return {
                    "strategy": strategy_name,
                    "total_used": total_used,
                    "success_count": success_count,
                    "failure_count": failure_count,
                    "success_rate": success_rate,
                    "avg_hours_to_complete": outcome_data.get("success", {}).get("avg_hours"),
                }

    async def get_efficiency_score(self, project_id: int) -> float:
        """Get current efficiency score for a project."""
        async with AsyncConnection.connect(self.postgres_url) as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT efficiency_score
                    FROM executive_metrics
                    WHERE project_id = ?
                    ORDER BY metric_date DESC
                    LIMIT 1
                    """,
                    (project_id,),
                )

                row = await cursor.fetchone()
                return row[0] if row else 0.0

    # Private helper methods

    async def _calculate_switch_overhead(self, project_id: int, cursor) -> Dict:
        """Calculate task switching overhead."""
        await cursor.execute(
            """
            SELECT switch_cost_ms FROM task_switches
            WHERE project_id = ?
            """,
            (project_id,),
        )

        switch_costs = [row[0] for row in await cursor.fetchall()]

        if not switch_costs:
            return {"total_ms": 0, "average_ms": 0.0}

        total_ms = sum(switch_costs)
        average_ms = total_ms / len(switch_costs) if switch_costs else 0.0

        return {"total_ms": total_ms, "average_ms": average_ms}

    async def _get_completion_times(self, project_id: int, cursor) -> List[float]:
        """Get goal completion times in hours."""
        await cursor.execute(
            """
            SELECT actual_hours
            FROM executive_goals
            WHERE project_id = ? AND status = 'completed' AND actual_hours IS NOT NULL
            AND actual_hours > 0
            """,
            (project_id,),
        )

        completion_times = [row[0] for row in await cursor.fetchall()]
        return completion_times

    def _calculate_efficiency_score(
        self, completed_goals: int, total_goals: int, total_switch_ms: int, completion_times: List[float]
    ) -> float:
        """
        Calculate efficiency score (0-100).

        efficiency = 100 × (completed_goals / total_goals) × (1 - switch_overhead_ratio)
        """
        if total_goals == 0:
            return 100.0

        completion_rate = completed_goals / total_goals

        # Calculate total time spent on goals
        total_goal_ms = sum(completion_times) * 3600 * 1000 if completion_times else 1.0
        switch_overhead_ratio = min(0.5, total_switch_ms / total_goal_ms)

        efficiency = 100.0 * completion_rate * (1.0 - switch_overhead_ratio)

        # Clamp to 0-100
        return max(0.0, min(100.0, efficiency))
