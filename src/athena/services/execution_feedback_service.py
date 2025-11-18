"""Service for capturing and processing task execution feedback.

Automatically captures:
- Actual duration vs estimated duration
- Success/failure status
- Blockers encountered
- Lessons learned
- Triggers downstream learning
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class ExecutionFeedbackService:
    """Captures execution feedback and triggers learning.

    When a task completes, this service:
    1. Records actual duration and outcome
    2. Calculates variance from estimate
    3. Updates effort prediction accuracy
    4. Updates planning pattern effectiveness
    5. Records blockers for pattern analysis
    6. Captures lessons learned for knowledge base
    """

    def __init__(
        self,
        prospective_store: Any,
        episodic_store: Optional[Any] = None,
        planning_store: Optional[Any] = None,
    ):
        """Initialize execution feedback service.

        Args:
            prospective_store: Prospective memory store for tasks
            episodic_store: Optional episodic store for event logging
            planning_store: Optional planning store for pattern updates
        """
        self.prospective_store = prospective_store
        self.episodic_store = episodic_store
        self.planning_store = planning_store

    async def capture_on_task_completion(
        self,
        task_id: int,
        actual_duration_minutes: int,
        success: bool = True,
        blockers: Optional[List[str]] = None,
        lessons_learned: Optional[str] = None,
        execution_start_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Capture feedback when a task completes.

        Args:
            task_id: ID of completed task
            actual_duration_minutes: Actual time taken (minutes)
            success: Whether task succeeded
            blockers: Optional list of blockers encountered
            lessons_learned: Optional lessons to record
            execution_start_time: When execution started (for variance calc)

        Returns:
            Feedback summary with metrics
        """
        try:
            # Get task
            task = self.prospective_store.get_task(task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return {"error": "Task not found"}

            # Calculate variance
            estimated = getattr(task, "estimated_duration", 0) or 120  # Default 2h
            variance_minutes = actual_duration_minutes - estimated
            variance_percent = (variance_minutes / estimated * 100) if estimated > 0 else 0

            # Create feedback record
            feedback = {
                "task_id": task_id,
                "task_type": getattr(task, "task_type", "general"),
                "actual_duration_minutes": actual_duration_minutes,
                "estimated_duration_minutes": estimated,
                "variance_minutes": variance_minutes,
                "variance_percent": variance_percent,
                "success": success,
                "blockers": blockers or [],
                "lessons_learned": lessons_learned,
                "timestamp": datetime.now(),
            }

            # Update task completion
            await self._update_task_completion(task, feedback)

            # Trigger learning cascade
            await self._trigger_learning(task, feedback)

            logger.info(
                f"Task {task_id} completion captured: "
                f"actual={actual_duration_minutes}m, variance={variance_percent:.1f}%"
            )

            return feedback

        except Exception as e:
            logger.error(f"Error capturing task completion feedback: {e}", exc_info=True)
            return {"error": str(e)}

    async def _update_task_completion(self, task: Any, feedback: Dict[str, Any]) -> None:
        """Update task with completion information.

        Args:
            task: Task to update
            feedback: Feedback data
        """
        try:
            task.status = "completed"
            task.completed_at = datetime.now()
            task.lessons_learned = feedback.get("lessons_learned")
            task.blocked_reason = (
                "; ".join(feedback.get("blockers", [])) if feedback.get("blockers") else None
            )
            task.actual_duration_minutes = feedback["actual_duration_minutes"]

            # Save updated task
            if hasattr(self.prospective_store, "save"):
                self.prospective_store.save(task)
            else:
                logger.warning("ProspectiveStore does not have save method")

        except Exception as e:
            logger.error(f"Error updating task completion: {e}")

    async def _trigger_learning(self, task: Any, feedback: Dict[str, Any]) -> None:
        """Trigger downstream learning systems.

        Updates:
        - Effort prediction accuracy
        - Planning pattern effectiveness
        - Blocker patterns
        - Knowledge base

        Args:
            task: Completed task
            feedback: Feedback data
        """
        try:
            # 1. Update effort accuracy for learning
            if hasattr(self.prospective_store, "record_effort_accuracy"):
                try:
                    await self.prospective_store.record_effort_accuracy(
                        task_type=feedback.get("task_type", "general"),
                        estimated_duration=feedback["estimated_duration_minutes"],
                        actual_duration=feedback["actual_duration_minutes"],
                        success=feedback["success"],
                    )
                except Exception as e:
                    logger.debug(f"Could not record effort accuracy: {e}")

            # 2. Update planning decision outcome if available
            if self.planning_store and hasattr(self.planning_store, "update_decision_outcome"):
                try:
                    # Find associated planning decision
                    if hasattr(task, "planning_decision_id"):
                        variance_percent = feedback.get("variance_percent", 0)
                        await self.planning_store.update_decision_outcome(
                            decision_id=task.planning_decision_id,
                            execution_successful=feedback["success"],
                            variance_percent=variance_percent,
                            improvement_opportunity=feedback.get("lessons_learned"),
                        )
                except Exception as e:
                    logger.debug(f"Could not update planning decision outcome: {e}")

            # 3. Record blocker patterns for analysis
            if feedback.get("blockers"):
                await self._analyze_blockers(task, feedback["blockers"])

            # 4. Record episodic event
            if self.episodic_store:
                await self._record_completion_event(task, feedback)

        except Exception as e:
            logger.error(f"Error triggering learning systems: {e}")

    async def _analyze_blockers(self, task: Any, blockers: List[str]) -> None:
        """Analyze blocker patterns for future prevention.

        Args:
            task: Task that was blocked
            blockers: List of blockers encountered
        """
        try:
            logger.info(f"Task {task.id} encountered blockers: {blockers}")
            # Future: Send to blocker analysis system for pattern detection

            # For now, just log for later analysis
            for blocker in blockers:
                logger.warning(f"  Blocker in {task.task_type}: {blocker}")

        except Exception as e:
            logger.error(f"Error analyzing blockers: {e}")

    async def _record_completion_event(self, task: Any, feedback: Dict[str, Any]) -> None:
        """Record completion event to episodic memory.

        Args:
            task: Completed task
            feedback: Feedback data
        """
        try:
            from ..episodic.models import EpisodicEvent, EventType, EventOutcome, EventContext

            # Determine outcome
            outcome = EventOutcome.SUCCESS if feedback["success"] else EventOutcome.FAILURE

            # Create event context
            event_context = EventContext(
                task=f"task_{task.id}",
                phase="completed",
            )

            # Create event
            event = EpisodicEvent(
                project_id=getattr(task, "project_id", 1) or 1,
                session_id="execution-feedback-service",
                event_type=EventType.SUCCESS if feedback["success"] else EventType.ERROR,
                content=f"Task completed: {task.content}",
                outcome=outcome,
                timestamp=datetime.now(),
                context=event_context,
                duration_ms=int(feedback["actual_duration_minutes"] * 60 * 1000),
                learned=f"Execution took {feedback['actual_duration_minutes']}m "
                f"vs {feedback['estimated_duration_minutes']}m estimate. "
                f"Variance: {feedback['variance_percent']:.1f}%",
                confidence=0.9 if feedback["success"] else 0.7,
            )

            # Save event
            if hasattr(self.episodic_store, "save_event_async"):
                await self.episodic_store.save_event_async(event)
            elif hasattr(self.episodic_store, "save_event"):
                self.episodic_store.save_event(event)

        except Exception as e:
            logger.error(f"Error recording completion event: {e}")

    async def get_task_feedback_summary(self, task_id: int) -> Dict[str, Any]:
        """Get feedback summary for a task.

        Args:
            task_id: Task ID

        Returns:
            Feedback summary or empty dict
        """
        try:
            task = self.prospective_store.get_task(task_id)
            if not task:
                return {}

            return {
                "task_id": task_id,
                "status": getattr(task, "status", "unknown"),
                "actual_duration_minutes": getattr(task, "actual_duration_minutes"),
                "lessons_learned": getattr(task, "lessons_learned"),
                "blockers": (
                    getattr(task, "blocked_reason", "").split(";")
                    if getattr(task, "blocked_reason")
                    else []
                ),
                "completed_at": getattr(task, "completed_at"),
            }

        except Exception as e:
            logger.error(f"Error getting feedback summary: {e}")
            return {}
