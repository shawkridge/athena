"""Auto-triggered adaptive replanning system.

Continuously monitors task execution and automatically triggers replanning
when specific conditions are met (duration exceeded, quality degradation,
milestone delays, etc.).
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Literal

from ..core.database import Database
from ..episodic.models import EpisodicEvent, EventContext, EventOutcome, EventType
from ..episodic.store import EpisodicStore
from ..prospective.models import ProspectiveTask, TaskPhase
from ..prospective.store import ProspectiveStore
from ..integration.milestone_tracker import MilestoneTracker

logger = logging.getLogger(__name__)


class ReplanningMonitor:
    """Monitor task execution and auto-trigger replanning.

    Trigger conditions:
    - Duration exceeded: task running >150% of estimate
    - Quality degradation: 3+ errors in recent time window
    - Milestone delayed: milestone >50% over estimate
    - Blocker encountered: task marked as blocked
    """

    # Thresholds for triggering replanning
    DURATION_THRESHOLD_PERCENT = 150  # 1.5x means replan
    QUALITY_ERROR_THRESHOLD = 3  # 3+ errors = quality degradation
    MILESTONE_DELAY_THRESHOLD_PERCENT = 50  # 50% over = replan
    MONITORING_WINDOW_MINUTES = 60  # Look back N minutes for events

    def __init__(self, db: Database):
        """Initialize replanning monitor.

        Args:
            db: Database instance
        """
        self.db = db
        self.prospective_store = ProspectiveStore(db)
        self.episodic_store = EpisodicStore(db)
        self.milestone_tracker = MilestoneTracker(db)
        self.last_check_time = datetime.now()

    async def check_all_active_tasks(self) -> list[dict]:
        """Check all active/executing tasks for replanning triggers.

        Returns:
            List of tasks that should trigger replanning with reasons
        """
        replan_candidates = []

        try:
            # Get all tasks in EXECUTING or PLAN_READY phases
            executing_tasks = self.prospective_store.get_tasks_by_phase(
                TaskPhase.EXECUTING, limit=100
            )

            for task in executing_tasks:
                trigger = await self._check_task_for_replanning(task)
                if trigger:
                    replan_candidates.append(trigger)

        except Exception as e:
            logger.error(f"Error checking active tasks for replanning: {e}")

        return replan_candidates

    async def _check_task_for_replanning(self, task: ProspectiveTask) -> Optional[dict]:
        """Check single task for replanning triggers.

        Args:
            task: Task to check

        Returns:
            Dict with trigger info if replanning should be triggered, else None
        """
        triggers = []

        # Check 1: Duration exceeded
        if await self._check_duration_exceeded(task):
            triggers.append(
                {
                    "type": "duration_exceeded",
                    "reason": "Task duration exceeded 150% of estimate",
                }
            )

        # Check 2: Quality degradation
        quality_errors = await self._check_quality_degradation(task)
        if quality_errors:
            triggers.append(
                {
                    "type": "quality_degradation",
                    "reason": f"Detected {quality_errors} errors in task execution",
                }
            )

        # Check 3: Milestone delay
        if await self._check_milestone_delay(task):
            triggers.append(
                {
                    "type": "milestone_delayed",
                    "reason": "Current milestone delayed >50% of estimate",
                }
            )

        if triggers:
            return {
                "task_id": task.id,
                "task_content": task.content,
                "current_phase": task.phase,
                "triggers": triggers,
                "recommended_action": self._decide_replanning_action(triggers),
            }

        return None

    async def _check_duration_exceeded(self, task: ProspectiveTask) -> bool:
        """Check if task duration exceeded threshold.

        Args:
            task: Task to check

        Returns:
            True if duration exceeded threshold
        """
        if not task.plan or not task.plan.estimated_duration_minutes:
            return False

        if not task.phase_started_at:
            return False

        # Calculate elapsed time
        elapsed_minutes = (datetime.now() - task.phase_started_at).total_seconds() / 60
        estimate = task.plan.estimated_duration_minutes

        # Check if exceeded 150% of estimate
        if elapsed_minutes > (estimate * (self.DURATION_THRESHOLD_PERCENT / 100)):
            logger.warning(
                f"Task {task.id} duration exceeded: "
                f"{elapsed_minutes:.1f} min vs {estimate} min estimate"
            )
            return True

        return False

    async def _check_quality_degradation(self, task: ProspectiveTask) -> int:
        """Check for quality degradation (errors in execution).

        Args:
            task: Task to check

        Returns:
            Number of errors found, 0 if below threshold
        """
        try:
            # Count error events in recent time window
            cutoff_time = datetime.now() - timedelta(minutes=self.MONITORING_WINDOW_MINUTES)

            cursor = self.db.get_cursor()
            cursor.execute(
                """
                SELECT COUNT(*) as error_count
                FROM episodic_events
                WHERE project_id = ? AND event_type = 'error' AND timestamp > ?
            """,
                (task.project_id, int(cutoff_time.timestamp())),
            )

            result = cursor.fetchone()
            error_count = result["error_count"] if result else 0

            if error_count >= self.QUALITY_ERROR_THRESHOLD:
                logger.warning(
                    f"Task {task.id} quality degradation detected: "
                    f"{error_count} errors in last {self.MONITORING_WINDOW_MINUTES} min"
                )
                return error_count

        except Exception as e:
            logger.error(f"Error checking quality degradation: {e}")

        return 0

    async def _check_milestone_delay(self, task: ProspectiveTask) -> bool:
        """Check if current milestone is delayed.

        Args:
            task: Task to check

        Returns:
            True if milestone delayed >50%
        """
        # Would check milestone status if milestones were stored with task
        # For now, use simple heuristic based on phase timing
        if not task.phase_started_at or not task.plan:
            return False

        elapsed = (datetime.now() - task.phase_started_at).total_seconds() / 60
        estimate_per_phase = task.plan.estimated_duration_minutes / 5  # Rough estimate

        if elapsed > (estimate_per_phase * 1.5):  # >150% of phase estimate
            logger.warning(
                f"Task {task.id} current phase delayed: "
                f"{elapsed:.1f} min vs {estimate_per_phase:.1f} min estimate"
            )
            return True

        return False

    def _decide_replanning_action(
        self, triggers: list[dict]
    ) -> Literal["continue", "adapt", "replan", "escalate"]:
        """Decide what replanning action to take.

        Args:
            triggers: List of trigger conditions

        Returns:
            Action: "continue" | "adapt" | "replan" | "escalate"
        """
        if not triggers:
            return "continue"

        trigger_types = [t["type"] for t in triggers]

        # Multiple triggers = escalate
        if len(triggers) >= 2:
            return "escalate"

        # Duration exceeded alone = replan
        if "duration_exceeded" in trigger_types:
            return "replan"

        # Quality degradation = escalate (needs human review)
        if "quality_degradation" in trigger_types:
            return "escalate"

        # Single milestone delay = adapt
        if "milestone_delayed" in trigger_types:
            return "adapt"

        return "continue"

    async def on_post_tool_use(self, event: dict) -> None:
        """Hook called after tool execution.

        Periodically checks if any active tasks need replanning.

        Args:
            event: Post-tool-use event
        """
        # Avoid checking too frequently - only check every N seconds
        now = datetime.now()
        if (now - self.last_check_time).total_seconds() < 30:
            return

        self.last_check_time = now

        try:
            replan_candidates = await self.check_all_active_tasks()

            for candidate in replan_candidates:
                # Record replanning trigger event
                self.episodic_store.record_event(
                    EpisodicEvent(
                        project_id=candidate.get("task_id"),
                        session_id="auto-replanning-monitor",
                        event_type=EventType.DECISION,
                        content=f"Auto-replanning triggered: {candidate['recommended_action']}",
                        outcome=EventOutcome.PARTIAL,
                        context=EventContext(
                            task=candidate["task_content"],
                            phase="replanning-trigger",
                        ),
                    )
                )

                logger.info(
                    f"Replanning trigger detected for task {candidate['task_id']}: "
                    f"Action={candidate['recommended_action']}"
                )

        except Exception as e:
            logger.error(f"Error in post-tool-use monitoring: {e}")

    async def estimate_new_plan(self, task: ProspectiveTask, reason: str) -> Optional[list[str]]:
        """Estimate new plan for task based on actual progress.

        Args:
            task: Task to replan
            reason: Reason for replanning

        Returns:
            New plan steps, or None if cannot replan
        """
        if not task.plan:
            return None

        # Simple strategy: extend remaining steps and add buffer
        try:
            # Estimate remaining work based on elapsed time vs estimate
            if task.phase_started_at:
                elapsed = (datetime.now() - task.phase_started_at).total_seconds() / 60
                estimate = task.plan.estimated_duration_minutes

                if elapsed > estimate:
                    # Add 20% buffer for recovery
                    buffer_factor = 1.2
                    new_steps = [step + " (adapted)" for step in task.plan.steps]
                    return new_steps

        except Exception as e:
            logger.error(f"Error estimating new plan: {e}")

        return None

    def get_monitor_status(self) -> dict:
        """Get current monitor status.

        Returns:
            Status dict with thresholds and last check
        """
        return {
            "last_check_time": self.last_check_time.isoformat(),
            "duration_threshold_percent": self.DURATION_THRESHOLD_PERCENT,
            "quality_error_threshold": self.QUALITY_ERROR_THRESHOLD,
            "milestone_delay_threshold_percent": self.MILESTONE_DELAY_THRESHOLD_PERCENT,
            "monitoring_window_minutes": self.MONITORING_WINDOW_MINUTES,
        }
