"""Service for monitoring task execution deviations and triggering replanning.

Detects when tasks are deviating from planned duration and triggers
adaptive replanning to get back on track.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class DeviationAlert:
    """Alert when a task deviates significantly from plan."""

    def __init__(
        self,
        task_id: int,
        deviation_percent: float,
        elapsed_minutes: int,
        estimated_minutes: int,
        reason: Optional[str] = None,
        recommended_action: str = "replan",
    ):
        """Initialize deviation alert.

        Args:
            task_id: Task ID
            deviation_percent: Percentage deviation from estimate
            elapsed_minutes: Time spent so far
            estimated_minutes: Estimated total time
            reason: Reason for deviation (if known)
            recommended_action: Suggested action ("replan", "extend", "abandon")
        """
        self.task_id = task_id
        self.deviation_percent = deviation_percent
        self.elapsed_minutes = elapsed_minutes
        self.estimated_minutes = estimated_minutes
        self.reason = reason
        self.recommended_action = recommended_action
        self.detected_at = datetime.now()

    def __repr__(self) -> str:
        return (
            f"DeviationAlert(task={self.task_id}, "
            f"deviation={self.deviation_percent:.1f}%, "
            f"action={self.recommended_action})"
        )


class ExecutionDeviationMonitor:
    """Monitors task execution for deviations and triggers replanning.

    Features:
    - Tracks elapsed vs estimated time
    - Detects significant deviations (default >20%)
    - Analyzes root cause
    - Triggers adaptive replanning
    - Records deviation patterns for learning
    """

    def __init__(
        self,
        prospective_store: Any,
        planning_store: Optional[Any] = None,
        deviation_threshold_percent: float = 20.0,
    ):
        """Initialize deviation monitor.

        Args:
            prospective_store: Prospective memory store
            planning_store: Optional planning store for replanning
            deviation_threshold_percent: Deviation threshold (default 20%)
        """
        self.prospective_store = prospective_store
        self.planning_store = planning_store
        self.deviation_threshold_percent = deviation_threshold_percent

    async def check_deviation(self, task_id: int) -> Optional[DeviationAlert]:
        """Check if a task is deviating from plan.

        Args:
            task_id: Task ID to check

        Returns:
            DeviationAlert if deviating, None otherwise
        """
        try:
            task = self.prospective_store.get_task(task_id)
            if not task:
                return None

            # Only check active/executing tasks
            status = getattr(task, "status", "unknown")
            if status not in ["active", "executing"]:
                return None

            # Get elapsed time
            elapsed = self._get_elapsed_time(task)
            if elapsed is None:
                return None

            estimated = getattr(task, "estimated_duration", 120) or 120

            # Calculate deviation
            deviation_percent = ((elapsed - estimated) / estimated) * 100

            # Check against threshold
            if abs(deviation_percent) > self.deviation_threshold_percent:
                reason = self._analyze_cause(task, deviation_percent, elapsed)
                action = self._recommend_action(task, deviation_percent)

                alert = DeviationAlert(
                    task_id=task_id,
                    deviation_percent=deviation_percent,
                    elapsed_minutes=int(elapsed),
                    estimated_minutes=int(estimated),
                    reason=reason,
                    recommended_action=action,
                )

                logger.warning(f"Deviation detected: {alert}")
                return alert

            return None

        except Exception as e:
            logger.error(f"Error checking deviation for task {task_id}: {e}")
            return None

    async def trigger_replanning(self, task_id: int) -> bool:
        """Trigger replanning for off-track task.

        Args:
            task_id: Task ID to replan

        Returns:
            True if replanning succeeded, False otherwise
        """
        try:
            # Check deviation first
            alert = await self.check_deviation(task_id)
            if not alert:
                logger.debug(f"No deviation detected for task {task_id}")
                return False

            task = self.prospective_store.get_task(task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return False

            logger.info(
                f"Triggering replanning for task {task_id}: "
                f"deviation={alert.deviation_percent:.1f}%, "
                f"action={alert.recommended_action}"
            )

            # Trigger replanning if planning store available
            if self.planning_store and hasattr(self.planning_store, "replan"):
                try:
                    new_plan = await self.planning_store.replan(task_id)
                    if new_plan:
                        # Update task with new plan
                        task.plan = new_plan
                        plan_revision = getattr(task, "plan_revision", 0) or 0
                        task.plan_revision = plan_revision + 1

                        if hasattr(self.prospective_store, "save"):
                            self.prospective_store.save(task)

                        logger.info(f"Task {task_id} replanned (revision {task.plan_revision})")
                        return True

                except Exception as e:
                    logger.error(f"Error replanning task {task_id}: {e}")

            return False

        except Exception as e:
            logger.error(f"Error triggering replanning for task {task_id}: {e}")
            return False

    def _get_elapsed_time(self, task: Any) -> Optional[int]:
        """Get elapsed time for a task (in minutes).

        Args:
            task: Task to check

        Returns:
            Elapsed minutes or None if not started
        """
        try:
            # Try to get from task.actual_duration_minutes (if partially completed)
            if hasattr(task, "actual_duration_minutes"):
                actual = getattr(task, "actual_duration_minutes")
                if actual:
                    return actual

            # Calculate from phase_started_at
            phase_started = getattr(task, "phase_started_at", None)
            if phase_started:
                if isinstance(phase_started, str):
                    # Parse ISO format
                    phase_started = datetime.fromisoformat(phase_started)
                elapsed = (datetime.now() - phase_started).total_seconds() / 60
                return int(elapsed)

            # Fallback: check created_at
            created = getattr(task, "created_at", None)
            if created:
                if isinstance(created, str):
                    created = datetime.fromisoformat(created)
                elapsed = (datetime.now() - created).total_seconds() / 60
                return int(elapsed)

            return None

        except Exception as e:
            logger.debug(f"Error calculating elapsed time: {e}")
            return None

    def _analyze_cause(
        self, task: Any, deviation_percent: float, elapsed_minutes: int
    ) -> Optional[str]:
        """Analyze potential cause of deviation.

        Args:
            task: Task being analyzed
            deviation_percent: Deviation percentage
            elapsed_minutes: Elapsed time

        Returns:
            Reason string or None
        """
        try:
            # Check for blockers
            blockers = getattr(task, "blocked_reason", None)
            if blockers:
                return f"Blocked: {blockers}"

            # Check task complexity
            complexity = getattr(task, "complexity", 5)
            if complexity > 7 and deviation_percent > 30:
                return "High complexity task running over estimate"

            # Check task type
            task_type = getattr(task, "task_type", "general")
            if task_type == "feature" and deviation_percent > 25:
                return "Feature scope larger than estimated"

            if deviation_percent > 100:
                return "Significant scope creep or unexpected challenges"

            return None

        except Exception as e:
            logger.debug(f"Error analyzing deviation cause: {e}")
            return None

    def _recommend_action(self, task: Any, deviation_percent: float) -> str:
        """Recommend action based on deviation.

        Args:
            task: Task being analyzed
            deviation_percent: Deviation percentage

        Returns:
            Recommended action: "replan", "extend", or "abandon"
        """
        if deviation_percent < 0:
            # Task is ahead of schedule
            return "accelerate"  # Try to complete faster

        if deviation_percent < 50:
            return "extend"  # Small overrun - extend estimate

        elif deviation_percent < 100:
            return "replan"  # Moderate overrun - replan approach

        else:
            # Major overrun
            blockers = getattr(task, "blocked_reason", None)
            if blockers and "critical" in blockers.lower():
                return "abandon"  # Critical blocker - might need to abandon

            return "replan"  # Otherwise replan

    async def get_active_deviations(self) -> Dict[int, DeviationAlert]:
        """Get all currently deviating tasks.

        Returns:
            Dict of task_id -> DeviationAlert for deviating tasks
        """
        try:
            deviations = {}

            # Get all active/executing tasks
            active_tasks = self.prospective_store.list_tasks(status="active")
            if not active_tasks:
                return deviations

            for task in active_tasks:
                try:
                    alert = await self.check_deviation(task.id)
                    if alert:
                        deviations[task.id] = alert
                except Exception as e:
                    logger.debug(f"Error checking task {task.id}: {e}")

            return deviations

        except Exception as e:
            logger.error(f"Error getting active deviations: {e}")
            return {}
