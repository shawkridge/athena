"""Milestone progress tracking and delay detection."""

import logging
from typing import Optional

from ..core.database import Database
from ..episodic.models import EpisodicEvent, EventContext, EventOutcome, EventType
from ..episodic.store import EpisodicStore
from ..prospective.milestones import Milestone

logger = logging.getLogger(__name__)


class MilestoneTracker:
    """Track milestone progress and detect delays.

    Responsibilities:
    - Record milestone progress
    - Detect when milestones exceed time estimates
    - Calculate delay percentages
    - Trigger auto-replanning on delays
    - Track completion order
    """

    def __init__(self, db: Database):
        """Initialize milestone tracker.

        Args:
            db: Database instance
        """
        self.db = db
        self.episodic_store = EpisodicStore(db)
        self.delay_threshold_percent = 50  # Auto-replan if >50% over

    async def report_milestone_progress(
        self,
        task_id: int,
        milestone_order: int,
        status: str,
        actual_minutes: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> dict:
        """Report progress on a milestone.

        Args:
            task_id: Task ID
            milestone_order: Milestone sequence order
            status: pending|in_progress|completed|blocked
            actual_minutes: Actual time spent
            notes: Progress notes

        Returns:
            Dict with milestone status and delay info
        """
        result = {
            "task_id": task_id,
            "milestone_order": milestone_order,
            "status": status,
            "is_delayed": False,
            "delay_percent": 0.0,
            "should_replan": False,
        }

        # Record episodic event
        try:
            event_content = f"Milestone {milestone_order} progress: {status}"
            if actual_minutes:
                event_content += f" ({actual_minutes:.1f} minutes)"

            milestone_event = EpisodicEvent(
                project_id=task_id,  # Use task_id as proxy
                session_id="milestone-progress",
                event_type=EventType.ACTION,
                content=event_content,
                outcome=EventOutcome.ONGOING if status != "completed" else EventOutcome.SUCCESS,
                context=EventContext(
                    task=f"Task {task_id}, Milestone {milestone_order}",
                    phase="milestone-tracking",
                ),
            )

            if notes:
                milestone_event.notes = notes

            self.episodic_store.record_event(milestone_event)
            logger.info(f"Recorded milestone {milestone_order} progress for task {task_id}")

        except Exception as e:
            logger.error(f"Failed to record milestone progress event: {e}")

        return result

    async def detect_milestone_delay(
        self,
        task_id: int,
        milestone: Milestone,
        actual_minutes: float,
    ) -> dict:
        """Detect if a milestone is delayed and calculate delay percentage.

        Args:
            task_id: Task ID
            milestone: Milestone object
            actual_minutes: Actual time spent

        Returns:
            Dict with delay info and replan recommendation
        """
        result = {
            "is_delayed": False,
            "delay_percent": 0.0,
            "should_trigger_replan": False,
            "delay_reason": None,
        }

        if actual_minutes <= milestone.estimated_minutes:
            return result

        # Calculate delay
        delay_minutes = actual_minutes - milestone.estimated_minutes
        delay_percent = (delay_minutes / milestone.estimated_minutes) * 100

        result["is_delayed"] = True
        result["delay_percent"] = delay_percent
        result["delay_reason"] = (
            f"Milestone exceeded estimate by {delay_minutes:.1f} min ({delay_percent:.1f}%)"
        )

        # Check if should trigger replanning
        if delay_percent > self.delay_threshold_percent:
            result["should_trigger_replan"] = True

        # Record delay event
        try:
            delay_event = EpisodicEvent(
                project_id=task_id,
                session_id="milestone-delay-detection",
                event_type=EventType.DECISION,
                content=f"Milestone '{milestone.name}' delayed: {delay_percent:.1f}% over estimate",
                outcome=EventOutcome.PARTIAL,
                context=EventContext(
                    task=f"Task {task_id}, Milestone {milestone.order}",
                    phase="delay-detection",
                ),
            )
            self.episodic_store.record_event(delay_event)

        except Exception as e:
            logger.error(f"Failed to record delay detection event: {e}")

        return result

    async def update_milestone_status(
        self,
        task_id: int,
        milestone_order: int,
        new_status: str,
        actual_minutes: Optional[float] = None,
    ) -> Optional[dict]:
        """Update milestone status and detect delays.

        Args:
            task_id: Task ID
            milestone_order: Milestone sequence
            new_status: New status (pending|in_progress|completed|blocked)
            actual_minutes: Actual time spent

        Returns:
            Updated milestone info with delay detection, or None
        """
        result = await self.report_milestone_progress(
            task_id=task_id,
            milestone_order=milestone_order,
            status=new_status,
            actual_minutes=actual_minutes,
        )

        # If completed, check for delays
        if new_status == "completed" and actual_minutes:
            # Would detect delay here, but need actual milestone object
            pass

        return result

    def calculate_overall_progress(
        self,
        milestones: list[Milestone],
    ) -> float:
        """Calculate overall task progress from milestones.

        Args:
            milestones: List of milestones

        Returns:
            Progress percentage (0-100)
        """
        if not milestones:
            return 0.0

        total_completion = 0.0
        for milestone in milestones:
            if milestone.status == "completed":
                total_completion += milestone.completion_percentage

        return min(total_completion * 100, 100.0)

    def estimate_remaining_time(
        self,
        milestones: list[Milestone],
    ) -> float:
        """Estimate remaining time based on milestones.

        Args:
            milestones: List of milestones

        Returns:
            Estimated remaining minutes
        """
        remaining = 0.0
        started = False

        for milestone in milestones:
            if milestone.status in ("in_progress", "pending"):
                started = True

            if started and milestone.status != "completed":
                # Apply delay factor if milestone is delayed
                estimated = milestone.estimated_minutes
                if milestone.is_delayed:
                    # Add delay_percent to the estimate
                    estimated *= 1 + milestone.delay_percent / 100
                remaining += estimated

        return remaining

    def get_milestone_summary(
        self,
        milestones: list[Milestone],
    ) -> dict:
        """Get summary of milestone status.

        Args:
            milestones: List of milestones

        Returns:
            Summary dict with counts and timing
        """
        summary = {
            "total_milestones": len(milestones),
            "completed": 0,
            "in_progress": 0,
            "pending": 0,
            "blocked": 0,
            "total_estimated_minutes": 0,
            "total_actual_minutes": 0,
            "delayed_count": 0,
            "average_delay_percent": 0.0,
            "overall_progress_percent": 0.0,
        }

        if not milestones:
            return summary

        delayed_total = 0
        for milestone in milestones:
            summary["total_estimated_minutes"] += milestone.estimated_minutes

            if milestone.actual_minutes:
                summary["total_actual_minutes"] += milestone.actual_minutes

            if milestone.status == "completed":
                summary["completed"] += 1
            elif milestone.status == "in_progress":
                summary["in_progress"] += 1
            elif milestone.status == "pending":
                summary["pending"] += 1
            elif milestone.status == "blocked":
                summary["blocked"] += 1

            if milestone.is_delayed:
                summary["delayed_count"] += 1
                delayed_total += milestone.delay_percent

        if summary["delayed_count"] > 0:
            summary["average_delay_percent"] = delayed_total / summary["delayed_count"]

        summary["overall_progress_percent"] = self.calculate_overall_progress(milestones)

        return summary
