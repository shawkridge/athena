"""Health Monitor Agent - Continuous task health tracking and alerts.

Phase 5-8 Agent: Monitors task health in real-time and suggests optimizations
when tasks enter warning or critical status.
"""

from typing import Optional
from dataclasses import dataclass
from ..prospective.monitoring import TaskMonitor
from ..core.database import Database


@dataclass
class HealthAlert:
    """Alert generated when task health degradation detected."""

    task_id: int
    health_score: float
    status: str  # healthy, warning, critical
    primary_issue: str  # duration_variance, errors, or blockers
    recommendation: str  # suggested action


class HealthMonitorAgent:
    """Autonomous agent for continuous task health monitoring.

    Monitors active tasks and generates alerts when health drops below thresholds.
    Suggests specific interventions based on the identified issue.
    """

    def __init__(self, db: Database):
        """Initialize health monitor agent.

        Args:
            db: Database connection for accessing task data
        """
        self.db = db
        self.monitor = TaskMonitor(db)
        self.warning_threshold = 0.65
        self.critical_threshold = 0.50

    async def check_active_tasks(
        self, project_id: int, task_ids: Optional[list[int]] = None
    ) -> list[HealthAlert]:
        """Check health of active tasks and generate alerts.

        Args:
            project_id: Project to monitor
            task_ids: Specific task IDs to check, or None for all active

        Returns:
            List of HealthAlert objects for unhealthy tasks
        """
        alerts = []

        # Get active tasks
        if task_ids is None:
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                SELECT id FROM prospective_tasks
                WHERE project_id = ? AND status IN ('active', 'pending')
                ORDER BY created_at DESC
                """,
                (project_id,),
            )
            task_ids = [row[0] for row in cursor.fetchall()]

        # Check health for each task
        for task_id in task_ids:
            try:
                health = await self.monitor.get_task_health(task_id)

                if health.health_score < self.critical_threshold:
                    alert = HealthAlert(
                        task_id=task_id,
                        health_score=health.health_score,
                        status="critical",
                        primary_issue=self._identify_primary_issue(health),
                        recommendation=self._suggest_intervention(
                            health, "critical"
                        ),
                    )
                    alerts.append(alert)
                elif health.health_score < self.warning_threshold:
                    alert = HealthAlert(
                        task_id=task_id,
                        health_score=health.health_score,
                        status="warning",
                        primary_issue=self._identify_primary_issue(health),
                        recommendation=self._suggest_intervention(
                            health, "warning"
                        ),
                    )
                    alerts.append(alert)
            except Exception as e:
                # Log error but continue monitoring other tasks
                print(
                    f"Error checking health for task {task_id}: {e}"
                )

        return alerts

    def _identify_primary_issue(self, health) -> str:
        """Identify which factor is causing health degradation.

        Args:
            health: TaskHealth object with metrics

        Returns:
            String identifying primary issue
        """
        # Check which factor is most problematic
        variance_impact = health.duration_variance * 0.5
        error_impact = min(health.errors / 10, 1.0) * 0.4
        blocker_impact = min(health.blockers / 5, 1.0) * 0.2

        if blocker_impact >= max(variance_impact, error_impact):
            return "blockers"
        elif error_impact >= max(variance_impact, blocker_impact):
            return "errors"
        else:
            return "duration_variance"

    def _suggest_intervention(self, health, severity: str) -> str:
        """Generate specific intervention recommendation.

        Args:
            health: TaskHealth object
            severity: 'warning' or 'critical'

        Returns:
            Recommended action
        """
        primary_issue = self._identify_primary_issue(health)

        if primary_issue == "blockers":
            if health.blockers >= 3:
                return "CRITICAL: Multiple blockers detected. Escalate to team lead immediately."
            else:
                return f"Resolve active blockers ({health.blockers} identified). Run /plan optimize to find workarounds."

        elif primary_issue == "errors":
            if health.errors >= 5:
                return "CRITICAL: High error rate detected. Consider different approach or escalate."
            else:
                return f"Address errors ({health.errors} logged). Review error log and adjust implementation."

        else:  # duration_variance
            if health.duration_variance > 0.8:
                return "CRITICAL: Task taking much longer than estimated. Reassess scope or request help."
            else:
                return "Duration variance high. Run /plan optimize to identify time sinks."

    async def get_project_health_summary(self, project_id: int) -> dict:
        """Get overall health summary for a project.

        Args:
            project_id: Project to analyze

        Returns:
            Dictionary with health metrics and alerts
        """
        dashboard = await self.monitor.get_project_dashboard(project_id)
        alerts = await self.check_active_tasks(project_id)

        return {
            "project_id": project_id,
            "total_tasks": dashboard.total_tasks,
            "completed_tasks": dashboard.completed_tasks,
            "active_tasks": dashboard.active_tasks,
            "average_health": dashboard.average_health_score,
            "health_status": dashboard.overall_health_status,
            "alerts": [
                {
                    "task_id": alert.task_id,
                    "health_score": alert.health_score,
                    "status": alert.status,
                    "primary_issue": alert.primary_issue,
                    "recommendation": alert.recommendation,
                }
                for alert in alerts
            ],
            "critical_count": sum(1 for a in alerts if a.status == "critical"),
            "warning_count": sum(1 for a in alerts if a.status == "warning"),
        }

    async def should_halt_execution(self, task_id: int) -> bool:
        """Check if a task should halt due to critical health.

        Args:
            task_id: Task to check

        Returns:
            True if task should halt and wait for intervention
        """
        try:
            health = await self.monitor.get_task_health(task_id)

            # Halt if critical AND multiple issues
            if health.health_score < self.critical_threshold:
                issue_count = 0
                if health.errors > 0:
                    issue_count += 1
                if health.blockers > 0:
                    issue_count += 1
                if health.duration_variance > 0.6:
                    issue_count += 1

                return issue_count >= 2

            return False
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            return False
