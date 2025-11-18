"""Trigger evaluation and firing logic for prospective memory."""

from datetime import datetime
from typing import List, Optional

from .models import ProspectiveTask, TaskTrigger, TriggerType
from .store import ProspectiveStore


class TriggerEvaluator:
    """Evaluates triggers and determines when tasks should be activated."""

    def __init__(self, prospective_store: ProspectiveStore):
        """Initialize trigger evaluator.

        Args:
            prospective_store: Prospective memory store
        """
        self.store = prospective_store

    def evaluate_all_triggers(
        self, current_context: Optional[dict] = None
    ) -> List[ProspectiveTask]:
        """Evaluate all triggers and return tasks that should be activated.

        Args:
            current_context: Current context (time, location, files, etc.)

        Returns:
            List of tasks whose triggers have fired
        """
        if current_context is None:
            current_context = {}

        # Get all pending tasks with unfired triggers
        pending_tasks = self.store.list_tasks(status="pending")
        activated_tasks = []

        for task in pending_tasks:
            triggers = self.store.get_triggers(task.id)

            # Check if any trigger has fired
            for trigger in triggers:
                if trigger.fired:
                    continue  # Already fired

                should_fire = self._evaluate_trigger(trigger, current_context)

                if should_fire:
                    # Mark trigger as fired
                    self.store.fire_trigger(trigger.id)

                    # Activate task
                    self.store.update_task_status(task.id, "active")
                    activated_tasks.append(task)
                    break  # One trigger is enough

        return activated_tasks

    def _evaluate_trigger(self, trigger: TaskTrigger, context: dict) -> bool:
        """Evaluate a single trigger.

        Args:
            trigger: Trigger to evaluate
            context: Current context

        Returns:
            True if trigger should fire
        """
        trigger_type = (
            trigger.trigger_type.value
            if hasattr(trigger.trigger_type, "value")
            else trigger.trigger_type
        )

        if trigger_type == "time":
            return self._evaluate_time_trigger(trigger, context)
        elif trigger_type == "event":
            return self._evaluate_event_trigger(trigger, context)
        elif trigger_type == "context":
            return self._evaluate_context_trigger(trigger, context)
        elif trigger_type == "dependency":
            return self._evaluate_dependency_trigger(trigger, context)
        elif trigger_type == "file":
            return self._evaluate_file_trigger(trigger, context)

        return False

    def _evaluate_time_trigger(self, trigger: TaskTrigger, context: dict) -> bool:
        """Evaluate time-based trigger.

        Args:
            trigger: Time trigger
            context: Current context with 'current_time'

        Returns:
            True if time condition is met
        """
        condition = trigger.trigger_condition
        current_time = context.get("current_time", datetime.now())

        # Check if due time has passed
        if "due_at" in condition:
            due_at = datetime.fromisoformat(condition["due_at"])
            if current_time >= due_at:
                return True

        # Check recurring schedule
        if "schedule" in condition:
            schedule = condition["schedule"]
            return self._check_schedule(schedule, current_time)

        return False

    def _check_schedule(self, schedule: dict, current_time: datetime) -> bool:
        """Check if current time matches schedule.

        Args:
            schedule: Schedule specification
            current_time: Current time

        Returns:
            True if schedule matches
        """
        # Daily schedule
        if schedule.get("frequency") == "daily":
            target_hour = schedule.get("hour", 9)
            target_minute = schedule.get("minute", 0)
            return current_time.hour == target_hour and current_time.minute == target_minute

        # Weekly schedule
        if schedule.get("frequency") == "weekly":
            target_weekday = schedule.get("weekday", 0)  # 0 = Monday
            if current_time.weekday() == target_weekday:
                target_hour = schedule.get("hour", 9)
                return current_time.hour == target_hour

        return False

    def _evaluate_event_trigger(self, trigger: TaskTrigger, context: dict) -> bool:
        """Evaluate event-based trigger.

        Args:
            trigger: Event trigger
            context: Current context with 'event'

        Returns:
            True if event condition is met
        """
        condition = trigger.trigger_condition
        event = context.get("event")

        if not event:
            return False

        # Check event type match
        if "event_type" in condition:
            expected_type = condition["event_type"]
            actual_type = (
                event.event_type.value
                if hasattr(event.event_type, "value")
                else str(event.event_type)
            )
            if actual_type != expected_type:
                return False

        # Check event outcome
        if "outcome" in condition:
            if event.outcome != condition["outcome"]:
                return False

        # Check content pattern
        if "content_pattern" in condition:
            pattern = condition["content_pattern"].lower()
            if pattern not in event.content.lower():
                return False

        # Check file involvement
        if "file_pattern" in condition:
            file_pattern = condition["file_pattern"]
            if event.context and hasattr(event.context, "cwd"):
                if file_pattern not in event.context.cwd:
                    return False

        return True

    def _evaluate_context_trigger(self, trigger: TaskTrigger, context: dict) -> bool:
        """Evaluate context-based trigger.

        Args:
            trigger: Context trigger
            context: Current context with location, files, etc.

        Returns:
            True if context condition is met
        """
        condition = trigger.trigger_condition

        # Check location/directory
        if "location" in condition:
            expected_location = condition["location"]
            current_location = context.get("current_location", "")
            if expected_location not in current_location:
                return False

        # Check if specific file is open
        if "file_open" in condition:
            expected_file = condition["file_open"]
            open_files = context.get("open_files", [])
            if expected_file not in open_files:
                return False

        # Check tech stack/tags
        if "tags" in condition:
            required_tags = condition["tags"]
            current_tags = context.get("current_tags", [])
            if not any(tag in current_tags for tag in required_tags):
                return False

        return True

    def _evaluate_dependency_trigger(self, trigger: TaskTrigger, context: dict) -> bool:
        """Evaluate dependency-based trigger.

        Args:
            trigger: Dependency trigger
            context: Current context

        Returns:
            True if dependency is satisfied
        """
        condition = trigger.trigger_condition

        # Check if dependent task is completed
        if "depends_on_task" in condition:
            task_id = condition["depends_on_task"]
            dependent_task = self.store.get_task(task_id)

            if not dependent_task:
                return False  # Dependent task doesn't exist

            if dependent_task.status != "completed":
                return False  # Not completed yet

        return True

    def _evaluate_file_trigger(self, trigger: TaskTrigger, context: dict) -> bool:
        """Evaluate file-based trigger.

        Args:
            trigger: File trigger
            context: Current context with file changes

        Returns:
            True if file condition is met
        """
        condition = trigger.trigger_condition
        file_changes = context.get("file_changes", [])

        if not file_changes:
            return False

        # Check if specific file was modified
        if "file_path" in condition:
            expected_file = condition["file_path"]
            if expected_file in file_changes:
                return True

        # Check if file pattern matches
        if "file_pattern" in condition:
            pattern = condition["file_pattern"]
            for changed_file in file_changes:
                if pattern in changed_file:
                    return True

        return False


def create_time_trigger(task_id: int, due_at: datetime) -> TaskTrigger:
    """Create a time-based trigger.

    Args:
        task_id: Task ID
        due_at: When task should be triggered

    Returns:
        Time trigger
    """
    return TaskTrigger(
        task_id=task_id,
        trigger_type=TriggerType.TIME,
        trigger_condition={"due_at": due_at.isoformat()},
    )


def create_recurring_trigger(
    task_id: int, frequency: str, hour: int = 9, minute: int = 0, weekday: Optional[int] = None
) -> TaskTrigger:
    """Create a recurring schedule trigger.

    Args:
        task_id: Task ID
        frequency: "daily" or "weekly"
        hour: Hour of day (0-23)
        minute: Minute of hour (0-59)
        weekday: Day of week for weekly (0=Monday, 6=Sunday)

    Returns:
        Recurring trigger
    """
    schedule = {"frequency": frequency, "hour": hour, "minute": minute}

    if frequency == "weekly" and weekday is not None:
        schedule["weekday"] = weekday

    return TaskTrigger(
        task_id=task_id, trigger_type=TriggerType.TIME, trigger_condition={"schedule": schedule}
    )


def create_event_trigger(
    task_id: int,
    event_type: Optional[str] = None,
    outcome: Optional[str] = None,
    content_pattern: Optional[str] = None,
) -> TaskTrigger:
    """Create an event-based trigger.

    Args:
        task_id: Task ID
        event_type: Event type to match
        outcome: Event outcome to match
        content_pattern: Pattern in event content

    Returns:
        Event trigger
    """
    condition = {}
    if event_type:
        condition["event_type"] = event_type
    if outcome:
        condition["outcome"] = outcome
    if content_pattern:
        condition["content_pattern"] = content_pattern

    return TaskTrigger(task_id=task_id, trigger_type=TriggerType.EVENT, trigger_condition=condition)


def create_file_trigger(task_id: int, file_path: str) -> TaskTrigger:
    """Create a file modification trigger.

    Args:
        task_id: Task ID
        file_path: Path to watch for changes

    Returns:
        File trigger
    """
    return TaskTrigger(
        task_id=task_id,
        trigger_type=TriggerType.FILE,
        trigger_condition={"file_path": file_path},
    )


def create_context_trigger(
    task_id: int, location: Optional[str] = None, tags: Optional[List[str]] = None
) -> TaskTrigger:
    """Create a context-based trigger.

    Args:
        task_id: Task ID
        location: Directory/location to trigger in
        tags: Tags that must be present

    Returns:
        Context trigger
    """
    condition = {}
    if location:
        condition["location"] = location
    if tags:
        condition["tags"] = tags

    return TaskTrigger(
        task_id=task_id, trigger_type=TriggerType.CONTEXT, trigger_condition=condition
    )


def create_dependency_trigger(task_id: int, depends_on_task_id: int) -> TaskTrigger:
    """Create a dependency trigger.

    Args:
        task_id: Task ID
        depends_on_task_id: Task that must complete first

    Returns:
        Dependency trigger
    """
    return TaskTrigger(
        task_id=task_id,
        trigger_type=TriggerType.DEPENDENCY,
        trigger_condition={"depends_on_task": depends_on_task_id},
    )
