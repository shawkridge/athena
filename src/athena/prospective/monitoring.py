"""Real-time task monitoring and health tracking.

Provides:
- Real-time task status aggregation
- Health metrics and indicators
- Task progress visualization data
- Performance tracking
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Literal

from ..core.database import Database
from .models import ProspectiveTask, TaskPhase, TaskStatus, TaskPriority
from .store import ProspectiveStore

logger = logging.getLogger(__name__)


class TaskHealth:
    """Health status of a task."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"

    def __init__(
        self,
        task_id: int,
        health_status: Literal["healthy", "warning", "critical"],
        phase: TaskPhase,
        progress_percent: float,
        health_score: float,  # 0.0-1.0
        duration_variance: float,  # -1.0 to 2.0+ (0 = on track)
        blockers: int,
        errors: int,
        warnings: int,
    ):
        """Initialize task health."""
        self.task_id = task_id
        self.health_status = health_status
        self.phase = phase
        self.progress_percent = progress_percent
        self.health_score = health_score
        self.duration_variance = duration_variance
        self.blockers = blockers
        self.errors = errors
        self.warnings = warnings
        self.timestamp = datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "health_status": self.health_status,
            "phase": self.phase.value if hasattr(self.phase, "value") else str(self.phase),
            "progress_percent": self.progress_percent,
            "health_score": self.health_score,
            "duration_variance": self.duration_variance,
            "blockers": self.blockers,
            "errors": self.errors,
            "warnings": self.warnings,
            "timestamp": self.timestamp.isoformat(),
        }


class TaskMonitor:
    """Monitor task execution and health in real-time."""

    def __init__(self, db: Database):
        """Initialize task monitor.

        Args:
            db: Database instance
        """
        self.db = db
        self.prospective_store = ProspectiveStore(db)
        self.last_check = datetime.now()

    async def get_task_health(self, task_id: int) -> Optional[TaskHealth]:
        """Get health status of a specific task.

        Args:
            task_id: Task ID to check

        Returns:
            TaskHealth with current metrics
        """
        task = self.prospective_store.get_task(task_id)
        if not task:
            return None

        # Calculate progress percentage
        progress = self._calculate_progress(task)

        # Calculate duration variance
        variance = self._calculate_duration_variance(task)

        # Count issues
        blockers = 1 if task.blocked_reason else 0
        errors = self._count_issues(task_id, "error")
        warnings = self._count_issues(task_id, "warning")

        # Determine health status
        health_score = self._calculate_health_score(variance, errors, blockers)
        health_status = self._determine_health_status(health_score, errors, blockers)

        return TaskHealth(
            task_id=task_id,
            health_status=health_status,
            phase=task.phase or TaskPhase.PLANNING,
            progress_percent=progress,
            health_score=health_score,
            duration_variance=variance,
            blockers=blockers,
            errors=errors,
            warnings=warnings,
        )

    async def get_project_dashboard(self, project_id: int) -> dict:
        """Get dashboard summary for entire project.

        Args:
            project_id: Project ID

        Returns:
            Dictionary with project metrics and task overview
        """
        tasks = self.prospective_store.get_tasks_by_project(project_id)

        # Aggregate metrics
        total_tasks = len(tasks)
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        in_progress = sum(
            1
            for t in tasks
            if t.status == TaskStatus.PENDING or t.phase in [TaskPhase.PLANNING, TaskPhase.EXECUTING]
        )
        blocked = sum(1 for t in tasks if t.blocked_reason)

        # Phase breakdown
        phase_breakdown = {}
        for task in tasks:
            phase_name = (
                task.phase.value if hasattr(task.phase, "value") else str(task.phase)
            )
            phase_breakdown[phase_name] = phase_breakdown.get(phase_name, 0) + 1

        # Priority breakdown
        priority_breakdown = {}
        for task in tasks:
            priority_name = (
                task.priority.value if hasattr(task.priority, "value") else str(task.priority)
            )
            priority_breakdown[priority_name] = priority_breakdown.get(priority_name, 0) + 1

        # Health overview
        health_statuses = {"healthy": 0, "warning": 0, "critical": 0}
        total_health_score = 0.0
        for task in tasks:
            health = await self.get_task_health(task.id)
            if health:
                health_statuses[health.health_status] += 1
                total_health_score += health.health_score

        avg_health = (
            total_health_score / len(tasks) if len(tasks) > 0 else 0
        )

        return {
            "project_id": project_id,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tasks": total_tasks,
                "completed": completed,
                "in_progress": in_progress,
                "blocked": blocked,
                "completion_percent": (completed / total_tasks * 100) if total_tasks > 0 else 0,
            },
            "health": {
                "average_score": avg_health,
                "statuses": health_statuses,
            },
            "phases": phase_breakdown,
            "priorities": priority_breakdown,
        }

    async def get_active_tasks_status(self, project_id: int) -> list[dict]:
        """Get status of all active tasks in project.

        Args:
            project_id: Project ID

        Returns:
            List of task status dictionaries
        """
        tasks = self.prospective_store.get_tasks_by_phase(TaskPhase.EXECUTING, limit=100)
        tasks = [t for t in tasks if t.project_id == project_id]

        result = []
        for task in tasks:
            health = await self.get_task_health(task.id)
            if health:
                result.append(
                    {
                        "task_id": task.id,
                        "content": task.content,
                        "phase": task.phase.value if hasattr(task.phase, "value") else str(task.phase),
                        "progress": self._calculate_progress(task),
                        **health.to_dict(),
                    }
                )

        return result

    def _calculate_progress(self, task: ProspectiveTask) -> float:
        """Calculate task progress percentage."""
        if task.status == TaskStatus.COMPLETED:
            return 100.0
        if task.phase == TaskPhase.FAILED or task.phase == TaskPhase.ABANDONED:
            return 0.0

        # Estimate based on phase
        phase_progress = {
            TaskPhase.PLANNING: 10,
            TaskPhase.PLAN_READY: 20,
            TaskPhase.EXECUTING: 60,
            TaskPhase.VERIFYING: 90,
            TaskPhase.COMPLETED: 100,
            TaskPhase.FAILED: 0,
            TaskPhase.ABANDONED: 0,
        }

        current_phase = task.phase or TaskPhase.PLANNING
        return float(phase_progress.get(current_phase, 0))

    def _calculate_duration_variance(self, task: ProspectiveTask) -> float:
        """Calculate duration variance (-1 to 2+).

        -1 = 50% faster, 0 = on track, 1 = 100% slower, etc.
        """
        if not task.plan or not task.plan.estimated_duration_minutes:
            return 0.0

        if not task.actual_duration_minutes:
            # Estimate from elapsed time if still executing
            if task.phase_started_at:
                elapsed = (datetime.now() - task.phase_started_at).total_seconds() / 60
                estimated = task.plan.estimated_duration_minutes
                return (elapsed - estimated) / estimated if estimated > 0 else 0.0
            return 0.0

        estimated = task.plan.estimated_duration_minutes
        actual = task.actual_duration_minutes
        return (actual - estimated) / estimated if estimated > 0 else 0.0

    def _count_issues(self, task_id: int, issue_type: str) -> int:
        """Count issues of a type for a task."""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute(
                f"""
                SELECT COUNT(*) as count
                FROM episodic_events
                WHERE context_task LIKE ? AND event_type = ?
            """,
                (f"%Task {task_id}%", issue_type),
            )
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error counting issues: {e}")
            return 0

    def _calculate_health_score(
        self, duration_variance: float, errors: int, blockers: int
    ) -> float:
        """Calculate overall health score (0.0-1.0).

        Factors:
        - Duration variance (higher variance = lower score)
        - Errors (more errors = lower score)
        - Blockers (blocked = lower score)
        """
        score = 1.0

        # Duration variance penalty
        if duration_variance > 0.5:
            score -= min(0.3, duration_variance * 0.1)  # Up to 30% penalty
        elif duration_variance < -0.5:
            score += 0.1  # 10% bonus for faster completion

        # Error penalty
        error_penalty = min(0.4, errors * 0.05)  # Up to 40% penalty
        score -= error_penalty

        # Blocker penalty
        if blockers > 0:
            score -= 0.2

        return max(0.0, min(1.0, score))

    def _determine_health_status(
        self, health_score: float, errors: int, blockers: int
    ) -> str:
        """Determine health status from metrics."""
        if blockers > 0 or errors >= 5:
            return TaskHealth.CRITICAL
        elif health_score < 0.5 or errors >= 2:
            return TaskHealth.WARNING
        else:
            return TaskHealth.HEALTHY
