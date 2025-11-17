"""Background service for evaluating triggers and activating tasks."""

import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from ..prospective.models import ProspectiveTask, TaskStatus, TaskPhase
from ..prospective.triggers import TriggerEvaluator
from ..prospective.store import ProspectiveStore
from ..episodic.models import EpisodicEvent, EventType, EventOutcome
from ..episodic.store import EpisodicStore as EpisodicEventStore

logger = logging.getLogger(__name__)


class BackgroundTriggerService:
    """Manages background trigger evaluation and task activation.

    This service runs in the background, periodically evaluating all triggers
    in the system and activating tasks when their conditions are met.

    Features:
    - Periodic trigger evaluation (configurable interval)
    - Automatic task activation and phase transition
    - Event recording for learning
    - Graceful error handling
    - Metrics tracking for health monitoring
    """

    def __init__(
        self,
        prospective_store: ProspectiveStore,
        episodic_store: Optional[EpisodicEventStore] = None,
        notification_service: Optional[Any] = None,
    ):
        """Initialize background trigger service.

        Args:
            prospective_store: Prospective memory store for task management
            episodic_store: Optional episodic memory store for event recording
            notification_service: Optional service for sending notifications
        """
        self.prospective_store = prospective_store
        self.episodic_store = episodic_store
        self.notification_service = notification_service
        self.trigger_evaluator = TriggerEvaluator(prospective_store)

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        # Metrics for monitoring
        self.metrics = {
            "total_evaluations": 0,
            "total_activations": 0,
            "last_evaluation": None,
            "last_error": None,
            "evaluation_errors": 0,
            "average_evaluation_time_ms": 0.0,
        }

    async def start(self, evaluation_interval_seconds: int = 30) -> None:
        """Start background trigger evaluation service.

        The service will periodically evaluate all triggers in the system
        at the specified interval. Only one evaluation runs at a time (guarded by lock).

        Args:
            evaluation_interval_seconds: How often to check triggers (default 30s)
                Shorter intervals = more responsive but higher CPU
                Longer intervals = less responsive but lower CPU
                Recommended: 30s for production

        Raises:
            RuntimeError: If service is already running
        """
        async with self._lock:
            if self._running:
                logger.warning("Trigger evaluation service already running")
                return

            self._running = True
            logger.info(
                f"Starting background trigger evaluation service "
                f"(interval: {evaluation_interval_seconds}s)"
            )

            self._task = asyncio.create_task(
                self._evaluation_loop(evaluation_interval_seconds)
            )

    async def stop(self) -> None:
        """Stop background service gracefully.

        Waits for current evaluation to complete before stopping.
        """
        async with self._lock:
            if not self._running:
                logger.debug("Trigger service not running, nothing to stop")
                return

            self._running = False
            if self._task:
                logger.debug("Cancelling trigger evaluation task")
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass

            logger.info("Trigger evaluation service stopped")

    async def _evaluation_loop(self, interval: int) -> None:
        """Main evaluation loop that runs periodically.

        Evaluates triggers every `interval` seconds. If an evaluation
        takes longer than the interval, the next one starts immediately.

        Args:
            interval: Seconds between evaluations
        """
        while self._running:
            try:
                await self._evaluate_once()
            except Exception as e:
                self.metrics["evaluation_errors"] += 1
                self.metrics["last_error"] = str(e)
                logger.error(
                    f"Error in trigger evaluation cycle: {e}",
                    exc_info=True
                )

            if self._running:
                # Wait before next evaluation
                try:
                    await asyncio.sleep(interval)
                except asyncio.CancelledError:
                    break

    async def _evaluate_once(self) -> None:
        """Execute a single trigger evaluation cycle.

        This method:
        1. Builds current context (time, files, dependencies, etc.)
        2. Evaluates all pending triggers
        3. Activates tasks whose triggers fire
        4. Checks for execution deviations (Phase 5)
        5. Records events for learning
        6. Updates metrics
        """
        start_time = datetime.now()

        # Build current execution context
        context = self._build_context()

        # Evaluate all triggers and get activated tasks
        activated_tasks = self.trigger_evaluator.evaluate_all_triggers(context)

        # Process each activation
        activation_count = 0
        for task in activated_tasks:
            try:
                await self._handle_task_activation(task, context)
                activation_count += 1
            except Exception as e:
                logger.error(
                    f"Error handling task activation for task {task.id}: {e}",
                    exc_info=True
                )

        # Phase 5: Check for deviations in executing tasks (optional, if deviation_monitor available)
        deviation_count = 0
        if hasattr(self, "deviation_monitor"):
            try:
                active_deviations = await self.deviation_monitor.get_active_deviations()
                deviation_count = len(active_deviations)
            except Exception as e:
                logger.debug(f"Error checking deviations: {e}")

        # Update metrics
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        self.metrics["total_evaluations"] += 1
        self.metrics["total_activations"] += activation_count
        self.metrics["last_evaluation"] = datetime.now()

        # Calculate rolling average of evaluation time
        prev_avg = self.metrics["average_evaluation_time_ms"]
        eval_count = self.metrics["total_evaluations"]
        new_avg = (prev_avg * (eval_count - 1) + elapsed_ms) / eval_count
        self.metrics["average_evaluation_time_ms"] = new_avg

        if activation_count > 0 or deviation_count > 0:
            logger.info(
                f"Trigger evaluation: {activation_count} task(s) activated, "
                f"{deviation_count} deviation(s) detected in {elapsed_ms:.1f}ms"
            )

    async def _handle_task_activation(
        self,
        task: ProspectiveTask,
        context: Dict[str, Any],
    ) -> None:
        """Handle activation of a task whose trigger fired.

        Steps:
        1. Update task phase to PLAN_READY (ready to execute)
        2. Record activation event for learning
        3. Send notification (if available)

        Args:
            task: Task that was activated
            context: Execution context that triggered activation
        """
        logger.info(
            f"Task activated by trigger: '{task.content}' (id={task.id})"
        )

        # Update task phase to PLAN_READY
        # This indicates the task is ready to be executed
        try:
            self.prospective_store.update_task_phase(task.id, TaskPhase.PLAN_READY)
        except Exception as e:
            logger.error(
                f"Failed to update task phase for task {task.id}: {e}",
                exc_info=True
            )
            raise

        # Record episodic event for learning
        if self.episodic_store:
            try:
                from ..episodic.models import EventContext

                # Build event context with task information
                event_context = EventContext(
                    task=f"task_{task.id}",
                    phase=TaskPhase.PLAN_READY.value,
                    cwd=context.get("current_location", ""),
                )

                event = EpisodicEvent(
                    project_id=task.project_id or 1,  # Use default project if not set
                    session_id="background-trigger-service",
                    event_type=EventType.ACTION,
                    content=f"Task automatically activated by trigger: {task.content}",
                    outcome=EventOutcome.SUCCESS,
                    timestamp=datetime.now(),
                    context=event_context,
                    learned=f"Task {task.id} activated automatically via trigger evaluation",
                    confidence=1.0,
                )
                # Store event asynchronously if possible, otherwise synchronously
                if hasattr(self.episodic_store, "save_event_async"):
                    await self.episodic_store.save_event_async(event)
                else:
                    self.episodic_store.save_event(event)
            except Exception as e:
                logger.error(
                    f"Failed to record episodic event for task {task.id}: {e}",
                    exc_info=True
                )

        # Send notification (if available)
        if self.notification_service:
            try:
                await self._send_notification(task)
            except Exception as e:
                logger.error(
                    f"Failed to send notification for task {task.id}: {e}",
                    exc_info=True
                )

    async def _send_notification(self, task: ProspectiveTask) -> None:
        """Send notification about task activation.

        Args:
            task: Activated task
        """
        if hasattr(self.notification_service, "notify_async"):
            await self.notification_service.notify_async(
                title="Task Ready",
                message=f"Task ready to start: {task.content}",
                priority="high",
                metadata={"task_id": task.id},
            )
        elif hasattr(self.notification_service, "notify"):
            # Sync notification service - wrap in thread
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.notification_service.notify,
                "Task Ready",
                f"Task ready to start: {task.content}",
                "high",
            )

    def _build_context(self) -> Dict[str, Any]:
        """Build current execution context for trigger evaluation.

        Returns a dictionary with:
        - current_time: Current datetime
        - completed_tasks: Recently completed tasks
        - active_files: Currently open/modified files
        - active_project: Currently active project
        - task_count: Total task counts by status

        Returns:
            Context dict for trigger evaluation
        """
        context = {
            "current_time": datetime.now(),
            "active_project": "current",  # Can be enhanced to track actual project
        }

        # Add recently completed tasks (for dependency triggers)
        try:
            completed = self.prospective_store.list_tasks(
                status=TaskStatus.COMPLETED.value,
                limit=100,
            )
            context["completed_tasks"] = completed
        except Exception as e:
            logger.warning(f"Failed to fetch completed tasks for context: {e}")
            context["completed_tasks"] = []

        # Add active tasks count
        try:
            active = self.prospective_store.list_tasks(
                status=TaskStatus.ACTIVE.value,
                limit=None,
            )
            context["active_task_count"] = len(active) if active else 0
        except Exception as e:
            logger.warning(f"Failed to fetch active task count: {e}")
            context["active_task_count"] = 0

        return context

    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics for monitoring.

        Returns:
            Dictionary with metrics:
            - total_evaluations: How many times we've evaluated
            - total_activations: How many tasks activated total
            - last_evaluation: When we last evaluated
            - last_error: Last error encountered
            - evaluation_errors: Count of errors
            - average_evaluation_time_ms: Average time per evaluation
        """
        return self.metrics.copy()

    def is_running(self) -> bool:
        """Check if service is currently running.

        Returns:
            True if background service is running
        """
        return self._running
