"""Phase transition tracking and metrics recording."""

import logging
from datetime import datetime
from typing import Optional

from ..core.database import Database
from ..episodic.models import EpisodicEvent, EventContext, EventOutcome, EventType
from ..episodic.store import EpisodicStore
from ..prospective.models import PhaseMetrics, ProspectiveTask, TaskPhase
from ..prospective.store import ProspectiveStore

logger = logging.getLogger(__name__)


class PhaseTracker:
    """Track task phase transitions and record metrics.

    Responsibilities:
    - Record when tasks transition between phases
    - Calculate phase duration
    - Store phase metrics in task
    - Create episodic events for phase changes
    - Integrate phase events with memory consolidation
    """

    def __init__(self, db: Database):
        """Initialize phase tracker.

        Args:
            db: Database instance
        """
        self.db = db
        self.prospective_store = ProspectiveStore(db)
        self.episodic_store = EpisodicStore(db)

    async def record_phase_change(
        self,
        task_id: int,
        from_phase: TaskPhase,
        to_phase: TaskPhase,
        notes: Optional[str] = None,
    ) -> Optional[ProspectiveTask]:
        """Record a phase transition for a task.

        Creates:
        - Episodic event for the phase transition
        - PhaseMetrics in the task
        - Updates task phase_metrics_json

        Args:
            task_id: Task ID
            from_phase: Current phase before transition
            to_phase: Target phase after transition
            notes: Optional notes about the transition

        Returns:
            Updated task with phase metrics, or None if task not found
        """
        task = self.prospective_store.get_task(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found for phase transition")
            return None

        # Record episodic event for phase transition
        try:
            phase_event = EpisodicEvent(
                project_id=task.project_id,
                session_id="phase-transition",
                event_type=EventType.DECISION,
                content=f"Task phase transition: {from_phase.value} → {to_phase.value}",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(
                    task=f"Task {task_id}: {task.content}",
                    phase=f"transition-{from_phase.value}-to-{to_phase.value}",
                ),
            )

            if notes:
                phase_event.notes = notes

            self.episodic_store.record_event(phase_event)
            logger.info(f"Recorded episodic event for task {task_id} phase transition")

        except Exception as e:
            logger.error(f"Failed to record episodic event for phase transition: {e}")

        # Update task phase with metrics
        try:
            updated_task = self.prospective_store.complete_phase(task_id, to_phase)
            logger.info(
                f"✓ Task {task_id} phase transition recorded: "
                f"{from_phase.value} → {to_phase.value}"
            )
            return updated_task

        except Exception as e:
            logger.error(f"Failed to update task phase: {e}")
            return None

    async def on_phase_start(
        self,
        task_id: int,
        phase: TaskPhase,
    ) -> Optional[ProspectiveTask]:
        """Called when a task enters a new phase.

        Updates:
        - phase_started_at timestamp
        - Records phase start in episodic memory

        Args:
            task_id: Task ID
            phase: Phase being entered

        Returns:
            Updated task, or None if not found
        """
        task = self.prospective_store.get_task(task_id)
        if not task:
            return None

        # Update phase_started_at
        updated_task = self.prospective_store.update_task_phase(task_id, phase)

        # Record episodic event
        try:
            phase_start_event = EpisodicEvent(
                project_id=task.project_id,
                session_id="phase-lifecycle",
                event_type=EventType.ACTION,
                content=f"Task entered phase: {phase.value}",
                outcome=EventOutcome.ONGOING,
                context=EventContext(
                    task=f"Task {task_id}: {task.content}",
                    phase=f"enter-{phase.value}",
                ),
            )
            self.episodic_store.record_event(phase_start_event)

        except Exception as e:
            logger.error(f"Failed to record phase start event: {e}")

        return updated_task

    async def on_phase_complete(
        self,
        task_id: int,
        completed_phase: TaskPhase,
        next_phase: TaskPhase,
    ) -> Optional[ProspectiveTask]:
        """Called when a task completes a phase and moves to the next.

        Calculates:
        - Time spent in completed_phase
        - Adds PhaseMetrics entry
        - Transitions to next_phase

        Args:
            task_id: Task ID
            completed_phase: Phase being completed
            next_phase: Phase to transition to

        Returns:
            Updated task, or None if not found
        """
        return await self.record_phase_change(
            task_id=task_id,
            from_phase=completed_phase,
            to_phase=next_phase,
            notes=f"Phase {completed_phase.value} completed successfully",
        )

    def get_phase_metrics(self, task_id: int) -> list[PhaseMetrics]:
        """Get all phase metrics for a task.

        Args:
            task_id: Task ID

        Returns:
            List of PhaseMetrics, or empty list if task not found
        """
        task = self.prospective_store.get_task(task_id)
        if not task:
            return []

        return task.phase_metrics or []

    def get_phase_duration(self, task_id: int, phase: TaskPhase) -> Optional[float]:
        """Get duration spent in a specific phase.

        Args:
            task_id: Task ID
            phase: Phase to query

        Returns:
            Duration in minutes, or None if phase not found
        """
        metrics = self.get_phase_metrics(task_id)
        for metric in metrics:
            if metric.phase == phase and metric.duration_minutes:
                return metric.duration_minutes

        return None

    def get_total_task_duration(self, task_id: int) -> Optional[float]:
        """Get total duration from task creation to completion.

        Args:
            task_id: Task ID

        Returns:
            Total duration in minutes from created_at to actual completion
        """
        task = self.prospective_store.get_task(task_id)
        if not task:
            return None

        return task.actual_duration_minutes

    def summarize_phase_metrics(self, task_id: int) -> dict:
        """Get a summary of all phase durations for a task.

        Returns:
            Dict with phase → duration mapping and total
        """
        task = self.prospective_store.get_task(task_id)
        if not task:
            return {}

        summary = {
            "task_id": task_id,
            "content": task.content,
            "total_duration_minutes": task.actual_duration_minutes,
            "phase_breakdown": {},
            "phase_count": len(task.phase_metrics) if task.phase_metrics else 0,
        }

        if task.phase_metrics:
            for metric in task.phase_metrics:
                phase_name = metric.phase.value if hasattr(metric.phase, "value") else metric.phase
                summary["phase_breakdown"][phase_name] = metric.duration_minutes

        return summary
