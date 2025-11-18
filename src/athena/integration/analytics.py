"""Task analytics: estimation accuracy, efficiency, and learning effectiveness.

Provides:
- Estimation accuracy analysis (actual vs estimated duration)
- Phase efficiency metrics (which phases take longest)
- Learning effectiveness tracking (how well we learn from tasks)
- Pattern discovery from completed tasks
"""

import logging
from datetime import datetime, timedelta

from ..core.database import Database
from ..prospective.models import TaskPhase, TaskStatus
from ..prospective.store import ProspectiveStore

logger = logging.getLogger(__name__)


class EstimationAccuracy:
    """Estimation accuracy metrics."""

    def __init__(
        self,
        total_tasks: int,
        accurate_estimates: int,
        underestimated_count: int,
        overestimated_count: int,
        average_variance_percent: float,
        accuracy_rate: float,
    ):
        """Initialize estimation accuracy."""
        self.total_tasks = total_tasks
        self.accurate_estimates = accurate_estimates
        self.underestimated_count = underestimated_count
        self.overestimated_count = overestimated_count
        self.average_variance_percent = average_variance_percent
        self.accuracy_rate = accuracy_rate  # 0.0-1.0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_tasks": self.total_tasks,
            "accurate_estimates": self.accurate_estimates,
            "underestimated_count": self.underestimated_count,
            "overestimated_count": self.overestimated_count,
            "average_variance_percent": self.average_variance_percent,
            "accuracy_rate": self.accuracy_rate,
        }


class PhaseEfficiency:
    """Phase-level efficiency metrics."""

    def __init__(
        self,
        phase: TaskPhase,
        total_duration_minutes: float,
        average_duration_minutes: float,
        task_count: int,
        percentage_of_total: float,
    ):
        """Initialize phase efficiency."""
        self.phase = phase
        self.total_duration_minutes = total_duration_minutes
        self.average_duration_minutes = average_duration_minutes
        self.task_count = task_count
        self.percentage_of_total = percentage_of_total

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        phase_name = self.phase.value if hasattr(self.phase, "value") else str(self.phase)
        return {
            "phase": phase_name,
            "total_duration_minutes": self.total_duration_minutes,
            "average_duration_minutes": self.average_duration_minutes,
            "task_count": self.task_count,
            "percentage_of_total": self.percentage_of_total,
        }


class TaskAnalytics:
    """Analyze task metrics and patterns."""

    def __init__(self, db: Database):
        """Initialize analytics engine.

        Args:
            db: Database instance
        """
        self.db = db
        self.prospective_store = ProspectiveStore(db)

    async def analyze_estimation_accuracy(
        self, project_id: int, days_back: int = 30
    ) -> EstimationAccuracy:
        """Analyze how accurate task duration estimates are.

        Args:
            project_id: Project ID
            days_back: Look back N days

        Returns:
            EstimationAccuracy with metrics
        """
        cutoff_time = datetime.now() - timedelta(days=days_back)

        # Get completed tasks
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            SELECT * FROM prospective_tasks
            WHERE project_id = ? AND status = ? AND completed_at IS NOT NULL
            ORDER BY completed_at DESC
        """,
            (project_id, TaskStatus.COMPLETED.value),
        )

        completed_tasks = cursor.fetchall()
        if not completed_tasks:
            return EstimationAccuracy(0, 0, 0, 0, 0.0, 0.0)

        # Analyze variances
        total_tasks = len(completed_tasks)
        accurate = 0
        underestimated = 0
        overestimated = 0
        total_variance = 0.0

        for row in completed_tasks:
            task_dict = dict(row) if hasattr(row, "keys") else row

            # Parse plan JSON if available
            plan_json = task_dict.get("plan_json")
            actual_duration = task_dict.get("actual_duration_minutes")

            if plan_json and actual_duration:
                import json

                try:
                    plan = json.loads(plan_json)
                    estimated = plan.get("estimated_duration_minutes", 0)

                    if estimated > 0:
                        variance = abs(actual_duration - estimated) / estimated
                        total_variance += variance

                        if variance <= 0.2:  # Within 20%
                            accurate += 1
                        elif actual_duration > estimated:
                            underestimated += 1
                        else:
                            overestimated += 1
                except json.JSONDecodeError:
                    pass

        avg_variance = (total_variance / total_tasks * 100) if total_tasks > 0 else 0
        accuracy_rate = accurate / total_tasks if total_tasks > 0 else 0

        return EstimationAccuracy(
            total_tasks=total_tasks,
            accurate_estimates=accurate,
            underestimated_count=underestimated,
            overestimated_count=overestimated,
            average_variance_percent=avg_variance,
            accuracy_rate=accuracy_rate,
        )

    async def analyze_phase_efficiency(self, project_id: int) -> list[PhaseEfficiency]:
        """Analyze which phases take longest.

        Args:
            project_id: Project ID

        Returns:
            List of PhaseEfficiency metrics per phase
        """
        tasks = self.prospective_store.get_tasks_by_project(project_id)

        # Aggregate metrics by phase
        phase_metrics = {}
        total_duration = 0.0

        for task in tasks:
            if task.phase_metrics:
                for metric in task.phase_metrics:
                    phase_name = (
                        metric.phase.value if hasattr(metric.phase, "value") else str(metric.phase)
                    )
                    duration = metric.duration_minutes or 0

                    if phase_name not in phase_metrics:
                        phase_metrics[phase_name] = {
                            "total": 0.0,
                            "count": 0,
                            "phase_obj": metric.phase,
                        }

                    phase_metrics[phase_name]["total"] += duration
                    phase_metrics[phase_name]["count"] += 1
                    total_duration += duration

        # Convert to efficiency objects
        result = []
        for phase_name, metrics in phase_metrics.items():
            if metrics["count"] > 0:
                avg_duration = metrics["total"] / metrics["count"]
                percentage = (metrics["total"] / total_duration * 100) if total_duration > 0 else 0

                result.append(
                    PhaseEfficiency(
                        phase=metrics["phase_obj"],
                        total_duration_minutes=metrics["total"],
                        average_duration_minutes=avg_duration,
                        task_count=metrics["count"],
                        percentage_of_total=percentage,
                    )
                )

        # Sort by total duration descending
        result.sort(key=lambda x: x.total_duration_minutes, reverse=True)
        return result

    async def analyze_learning_effectiveness(self, project_id: int) -> dict:
        """Analyze how effectively we're learning from completed tasks.

        Args:
            project_id: Project ID

        Returns:
            Dictionary with learning metrics
        """
        tasks = self.prospective_store.get_tasks_by_project(project_id)
        completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]

        if not completed_tasks:
            return {
                "total_completed": 0,
                "with_lessons_learned": 0,
                "lessons_per_task": 0,
                "learning_rate": 0.0,
            }

        # Count tasks with lessons learned
        with_lessons = sum(1 for t in completed_tasks if t.lessons_learned)

        # Average lessons per completed task
        total_lessons = sum(
            len(t.lessons_learned.split(";")) for t in completed_tasks if t.lessons_learned
        )
        avg_lessons = total_lessons / len(completed_tasks) if completed_tasks else 0

        # Learning effectiveness score
        learning_rate = with_lessons / len(completed_tasks)

        return {
            "total_completed": len(completed_tasks),
            "with_lessons_learned": with_lessons,
            "lessons_per_task": avg_lessons,
            "learning_rate": learning_rate,
        }

    async def discover_patterns(self, project_id: int) -> dict:
        """Discover patterns in completed tasks.

        Args:
            project_id: Project ID

        Returns:
            Dictionary with discovered patterns
        """
        tasks = self.prospective_store.get_tasks_by_project(project_id)
        completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]

        if not completed_tasks:
            return {
                "average_duration_minutes": 0.0,
                "most_common_priority": "unknown",
                "completion_rate": 0.0,
                "failure_count": 0,
            }

        # Average task duration
        total_duration = sum(
            t.actual_duration_minutes for t in completed_tasks if t.actual_duration_minutes
        )
        avg_duration = total_duration / len(completed_tasks) if completed_tasks else 0

        # Most common priority
        priority_counts = {}
        for task in completed_tasks:
            priority_name = (
                task.priority.value if hasattr(task.priority, "value") else str(task.priority)
            )
            priority_counts[priority_name] = priority_counts.get(priority_name, 0) + 1

        most_common = (
            max(priority_counts, key=priority_counts.get) if priority_counts else "unknown"
        )

        # Completion rate
        all_tasks = self.prospective_store.get_tasks_by_project(project_id)
        completion_rate = len(completed_tasks) / len(all_tasks) if all_tasks else 0

        # Failure count
        failed_tasks = [t for t in tasks if t.phase == TaskPhase.FAILED]

        return {
            "average_duration_minutes": avg_duration,
            "most_common_priority": most_common,
            "completion_rate": completion_rate,
            "failure_count": len(failed_tasks),
            "priority_distribution": priority_counts,
        }

    async def get_project_analytics_summary(self, project_id: int) -> dict:
        """Get comprehensive analytics summary for project.

        Args:
            project_id: Project ID

        Returns:
            Dictionary with all analytics
        """
        estimation_acc = await self.analyze_estimation_accuracy(project_id)
        phase_eff = await self.analyze_phase_efficiency(project_id)
        learning = await self.analyze_learning_effectiveness(project_id)
        patterns = await self.discover_patterns(project_id)

        return {
            "project_id": project_id,
            "timestamp": datetime.now().isoformat(),
            "estimation_accuracy": estimation_acc.to_dict(),
            "phase_efficiency": [p.to_dict() for p in phase_eff],
            "learning_effectiveness": learning,
            "discovered_patterns": patterns,
        }
