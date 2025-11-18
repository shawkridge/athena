"""Execution Monitor - Real-time tracking of plan execution vs. planned execution."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from .models import (
    TaskExecutionRecord,
    PlanDeviation,
    DeviationSeverity,
    TaskOutcome,
)

logger = logging.getLogger(__name__)


class ExecutionMonitor:
    """Monitor actual vs. planned execution in real-time."""

    def __init__(self):
        """Initialize execution monitor."""
        self.execution_records: Dict[str, TaskExecutionRecord] = {}
        self.plan_start_time: Optional[datetime] = None
        self.planned_completion_time: Optional[datetime] = None
        self.total_planned_tasks: int = 0

    def initialize_plan(
        self,
        total_tasks: int,
        planned_duration: timedelta,
        start_time: Optional[datetime] = None,
    ) -> None:
        """Initialize monitor with plan details.

        Args:
            total_tasks: Total number of tasks in plan
            planned_duration: Total planned duration
            start_time: When plan starts (defaults to now)
        """
        self.plan_start_time = start_time or datetime.utcnow()
        self.planned_completion_time = self.plan_start_time + planned_duration
        self.total_planned_tasks = total_tasks
        logger.info(
            f"Execution monitoring initialized: {total_tasks} tasks, "
            f"{planned_duration} planned duration"
        )

    def record_task_start(
        self,
        task_id: str,
        planned_start: datetime,
        planned_duration: timedelta,
    ) -> None:
        """Record when a task actually starts.

        Args:
            task_id: ID of the task
            planned_start: When the task was planned to start
            planned_duration: How long the task is planned to take
        """
        actual_start = datetime.utcnow()
        record = TaskExecutionRecord(
            task_id=task_id,
            planned_start=planned_start,
            actual_start=actual_start,
            planned_duration=planned_duration,
        )
        self.execution_records[task_id] = record

        # Calculate start time deviation
        start_deviation = (actual_start - planned_start).total_seconds()
        logger.info(f"Task {task_id} started (deviation: {start_deviation}s)")

    def record_task_completion(
        self,
        task_id: str,
        outcome: TaskOutcome,
        resources_used: Optional[Dict[str, float]] = None,
        notes: str = "",
    ) -> Optional[TaskExecutionRecord]:
        """Record task completion with metrics.

        Args:
            task_id: ID of the task
            outcome: How the task completed
            resources_used: Actual resources consumed
            notes: Any notes about the task

        Returns:
            Updated execution record or None if task not found
        """
        if task_id not in self.execution_records:
            logger.warning(f"Task {task_id} not found in execution records")
            return None

        record = self.execution_records[task_id]
        if record.actual_start is None:
            logger.warning(f"Task {task_id} has no start time recorded")
            return None

        actual_completion = datetime.utcnow()
        actual_duration = actual_completion - record.actual_start

        # Update record
        record.outcome = outcome
        record.actual_duration = actual_duration
        if resources_used:
            record.resources_used = resources_used
        record.notes = notes
        record.updated_at = datetime.utcnow()

        # Calculate deviation (-1.0 to 1.0)
        # positive = took longer than planned, negative = faster than planned
        if record.planned_duration.total_seconds() > 0:
            duration_ratio = (
                actual_duration.total_seconds() / record.planned_duration.total_seconds()
            )
            # Cap deviation at -1.0 to 1.0
            record.deviation = min(1.0, max(-1.0, duration_ratio - 1.0))
        else:
            record.deviation = 0.0

        # Set confidence based on outcome
        if outcome == TaskOutcome.SUCCESS:
            record.confidence = 0.95
        elif outcome == TaskOutcome.PARTIAL:
            record.confidence = 0.7
        elif outcome == TaskOutcome.FAILURE:
            record.confidence = 0.0
        else:  # BLOCKED
            record.confidence = 0.5

        logger.info(
            f"Task {task_id} completed: {outcome.value}, "
            f"duration={actual_duration}, deviation={record.deviation:.2f}"
        )

        return record

    def get_plan_deviation(self) -> PlanDeviation:
        """Calculate overall plan deviation metrics.

        Returns:
            PlanDeviation with current metrics
        """
        now = datetime.utcnow()
        completed_tasks = sum(1 for r in self.execution_records.values() if r.outcome is not None)
        total_tasks = self.total_planned_tasks

        # Calculate time deviation
        actual_duration = now - self.plan_start_time if self.plan_start_time else timedelta(0)
        planned_duration = (
            self.planned_completion_time - self.plan_start_time
            if self.planned_completion_time and self.plan_start_time
            else timedelta(0)
        )
        time_deviation = actual_duration - planned_duration

        # Calculate time deviation percentage
        if planned_duration.total_seconds() > 0:
            time_deviation_percent = (
                time_deviation.total_seconds() / planned_duration.total_seconds()
            ) * 100
        else:
            time_deviation_percent = 0.0

        # Calculate resource deviations
        resource_deviation: Dict[str, float] = {}
        all_resources = set()
        for record in self.execution_records.values():
            all_resources.update(record.resources_planned.keys())
            all_resources.update(record.resources_used.keys())

        for resource in all_resources:
            planned_total = sum(
                r.resources_planned.get(resource, 0) for r in self.execution_records.values()
            )
            used_total = sum(
                r.resources_used.get(resource, 0) for r in self.execution_records.values()
            )
            if planned_total > 0:
                deviation = (used_total - planned_total) / planned_total
                resource_deviation[resource] = deviation

        # Identify at-risk tasks (not started or failed)
        tasks_at_risk = [
            r.task_id
            for r in self.execution_records.values()
            if r.outcome is None or r.outcome == TaskOutcome.FAILURE
        ]

        # Determine critical path (longest chain of dependent tasks)
        critical_path = self._compute_critical_path()

        # Estimate completion time
        if completed_tasks > 0 and total_tasks > 0:
            completion_rate = completed_tasks / total_tasks
            if completion_rate > 0:
                elapsed = actual_duration
                avg_task_time = elapsed / completed_tasks
                remaining_tasks = total_tasks - completed_tasks
                estimated_remaining = timedelta(
                    seconds=avg_task_time.total_seconds() * remaining_tasks
                )
                estimated_completion = now + estimated_remaining
            else:
                estimated_completion = self.planned_completion_time or now
        else:
            estimated_completion = self.planned_completion_time or now

        completion_rate = completed_tasks / total_tasks if total_tasks > 0 else 0.0

        # Determine severity
        if time_deviation_percent > 50:
            severity = DeviationSeverity.CRITICAL
            confidence = 0.6
        elif time_deviation_percent > 25:
            severity = DeviationSeverity.HIGH
            confidence = 0.7
        elif time_deviation_percent > 10:
            severity = DeviationSeverity.MEDIUM
            confidence = 0.8
        else:
            severity = DeviationSeverity.LOW
            confidence = 0.9

        return PlanDeviation(
            time_deviation=time_deviation,
            time_deviation_percent=time_deviation_percent,
            resource_deviation=resource_deviation,
            completion_rate=completion_rate,
            completed_tasks=completed_tasks,
            total_tasks=total_tasks,
            tasks_at_risk=tasks_at_risk,
            critical_path=critical_path,
            estimated_completion=estimated_completion,
            confidence=confidence,
            deviation_severity=severity,
        )

    def predict_completion_time(self) -> datetime:
        """Forecast actual completion time based on current execution.

        Returns:
            Predicted completion time
        """
        deviation = self.get_plan_deviation()
        return deviation.estimated_completion

    def get_critical_path(self) -> List[str]:
        """Identify bottleneck tasks in critical path.

        Returns:
            List of task IDs on critical path
        """
        return self._compute_critical_path()

    def _compute_critical_path(self) -> List[str]:
        """Compute the critical path of tasks.

        Critical path is the longest sequence of dependent tasks.
        For now, we use a simple heuristic: longest chain by duration.

        Returns:
            List of task IDs on critical path
        """
        if not self.execution_records:
            return []

        # Sort by actual start time
        sorted_records = sorted(
            self.execution_records.values(),
            key=lambda r: r.actual_start or r.planned_start,
        )

        # For now, return top 3 tasks by duration as critical path
        sorted_by_duration = sorted(
            sorted_records,
            key=lambda r: (r.actual_duration or timedelta(0)).total_seconds(),
            reverse=True,
        )

        return [r.task_id for r in sorted_by_duration[:3]]

    def get_task_record(self, task_id: str) -> Optional[TaskExecutionRecord]:
        """Get execution record for a specific task.

        Args:
            task_id: ID of the task

        Returns:
            TaskExecutionRecord or None if not found
        """
        return self.execution_records.get(task_id)

    def get_all_task_records(self) -> List[TaskExecutionRecord]:
        """Get all task execution records.

        Returns:
            List of all execution records
        """
        return list(self.execution_records.values())

    def reset(self) -> None:
        """Reset the monitor (for new plan execution)."""
        self.execution_records.clear()
        self.plan_start_time = None
        self.planned_completion_time = None
        self.total_planned_tasks = 0
        logger.info("Execution monitor reset")
