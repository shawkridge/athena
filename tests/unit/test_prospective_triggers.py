"""Tests for prospective memory triggers."""

from datetime import datetime, timedelta

import pytest

from athena.core.database import Database
from athena.episodic.models import EpisodicEvent, EventContext, EventType
from athena.prospective.models import ProspectiveTask, TaskStatus, TriggerType
from athena.prospective.store import ProspectiveStore
from athena.prospective.triggers import (
    TriggerEvaluator,
    create_context_trigger,
    create_dependency_trigger,
    create_event_trigger,
    create_file_trigger,
    create_recurring_trigger,
    create_time_trigger,
)


@pytest.fixture
def db():
    """Create in-memory database."""
    return Database(":memory:")


@pytest.fixture
def prospective_store(db):
    """Create prospective store."""
    return ProspectiveStore(db)


@pytest.fixture
def evaluator(prospective_store):
    """Create trigger evaluator."""
    return TriggerEvaluator(prospective_store)


def test_time_trigger_evaluation(prospective_store, evaluator):
    """Test time-based trigger evaluation."""
    # Create task with time trigger
    task = ProspectiveTask(
        project_id=1,
        content="Run tests before commit",
        active_form="Running tests before commit",
        status=TaskStatus.PENDING,
    )
    task_id = prospective_store.create_task(task)

    # Create trigger for 1 hour ago (should fire)
    trigger = create_time_trigger(task_id, datetime.now() - timedelta(hours=1))
    prospective_store.add_trigger(trigger)

    # Evaluate triggers
    context = {"current_time": datetime.now()}
    activated = evaluator.evaluate_all_triggers(context)

    # Should activate the task
    assert len(activated) == 1
    assert activated[0].id == task_id


def test_time_trigger_not_yet_due(prospective_store, evaluator):
    """Test time trigger that hasn't fired yet."""
    task = ProspectiveTask(
        project_id=1,
        content="Future task",
        active_form="Running future task",
        status=TaskStatus.PENDING,
    )
    task_id = prospective_store.create_task(task)

    # Create trigger for 1 hour in future (should not fire)
    trigger = create_time_trigger(task_id, datetime.now() + timedelta(hours=1))
    prospective_store.add_trigger(trigger)

    # Evaluate triggers
    context = {"current_time": datetime.now()}
    activated = evaluator.evaluate_all_triggers(context)

    # Should not activate
    assert len(activated) == 0


def test_recurring_trigger_daily(prospective_store, evaluator):
    """Test daily recurring trigger."""
    task = ProspectiveTask(
        project_id=1,
        content="Daily standup reminder",
        active_form="Reminding about daily standup",
        status=TaskStatus.PENDING,
    )
    task_id = prospective_store.create_task(task)

    # Create daily trigger for current hour
    current_time = datetime.now()
    trigger = create_recurring_trigger(
        task_id, frequency="daily", hour=current_time.hour, minute=current_time.minute
    )
    prospective_store.add_trigger(trigger)

    # Evaluate at the scheduled time
    context = {"current_time": current_time}
    activated = evaluator.evaluate_all_triggers(context)

    # Should activate
    assert len(activated) == 1


def test_event_trigger_evaluation(prospective_store, evaluator):
    """Test event-based trigger."""
    task = ProspectiveTask(
        project_id=1,
        content="Update docs after auth changes",
        active_form="Updating docs",
        status=TaskStatus.PENDING,
    )
    task_id = prospective_store.create_task(task)

    # Create trigger for file changes in auth
    trigger = create_event_trigger(
        task_id, event_type="file_change", content_pattern="auth"
    )
    prospective_store.add_trigger(trigger)

    # Create matching event
    event = EpisodicEvent(
        project_id=1,
        session_id="test",
        event_type=EventType.FILE_CHANGE,
        content="Modified auth middleware",
        timestamp=datetime.now(),
    )

    # Evaluate with event
    context = {"event": event}
    activated = evaluator.evaluate_all_triggers(context)

    # Should activate
    assert len(activated) == 1


def test_file_trigger_evaluation(prospective_store, evaluator):
    """Test file modification trigger."""
    task = ProspectiveTask(
        project_id=1,
        content="Run linter after config change",
        active_form="Running linter",
        status=TaskStatus.PENDING,
    )
    task_id = prospective_store.create_task(task)

    # Create file trigger
    trigger = create_file_trigger(task_id, ".eslintrc.json")
    prospective_store.add_trigger(trigger)

    # Simulate file change
    context = {"file_changes": [".eslintrc.json", "src/index.ts"]}
    activated = evaluator.evaluate_all_triggers(context)

    # Should activate
    assert len(activated) == 1


def test_context_trigger_evaluation(prospective_store, evaluator):
    """Test context-based trigger."""
    task = ProspectiveTask(
        project_id=1,
        content="Remind about testing when in tests directory",
        active_form="Reminding about testing",
        status=TaskStatus.PENDING,
    )
    task_id = prospective_store.create_task(task)

    # Create context trigger for tests directory
    trigger = create_context_trigger(task_id, location="/project/tests")
    prospective_store.add_trigger(trigger)

    # Evaluate with matching location
    context = {"current_location": "/project/tests/unit"}
    activated = evaluator.evaluate_all_triggers(context)

    # Should activate
    assert len(activated) == 1


def test_context_trigger_wrong_location(prospective_store, evaluator):
    """Test context trigger with wrong location."""
    task = ProspectiveTask(
        project_id=1,
        content="Testing task",
        active_form="Running testing task",
        status=TaskStatus.PENDING,
    )
    task_id = prospective_store.create_task(task)

    # Create context trigger
    trigger = create_context_trigger(task_id, location="/project/tests")
    prospective_store.add_trigger(trigger)

    # Evaluate with non-matching location
    context = {"current_location": "/project/src"}
    activated = evaluator.evaluate_all_triggers(context)

    # Should not activate
    assert len(activated) == 0


def test_dependency_trigger(prospective_store, evaluator):
    """Test dependency-based trigger."""
    # Create first task
    task1 = ProspectiveTask(
        project_id=1,
        content="Build project",
        active_form="Building project",
        status=TaskStatus.COMPLETED,  # Already completed
        completed_at=datetime.now(),
    )
    task1_id = prospective_store.create_task(task1)

    # Create dependent task
    task2 = ProspectiveTask(
        project_id=1,
        content="Run tests after build",
        active_form="Running tests",
        status=TaskStatus.PENDING,
    )
    task2_id = prospective_store.create_task(task2)

    # Create dependency trigger
    trigger = create_dependency_trigger(task2_id, depends_on_task_id=task1_id)
    prospective_store.add_trigger(trigger)

    # Evaluate
    activated = evaluator.evaluate_all_triggers({})

    # Should activate because dependency is complete
    assert len(activated) == 1
    assert activated[0].id == task2_id


def test_dependency_trigger_not_ready(prospective_store, evaluator):
    """Test dependency trigger when dependency not complete."""
    # Create first task (not completed)
    task1 = ProspectiveTask(
        project_id=1,
        content="Build project",
        active_form="Building project",
        status=TaskStatus.PENDING,
    )
    task1_id = prospective_store.create_task(task1)

    # Create dependent task
    task2 = ProspectiveTask(
        project_id=1,
        content="Run tests",
        active_form="Running tests",
        status=TaskStatus.PENDING,
    )
    task2_id = prospective_store.create_task(task2)

    # Create dependency trigger
    trigger = create_dependency_trigger(task2_id, depends_on_task_id=task1_id)
    prospective_store.add_trigger(trigger)

    # Evaluate
    activated = evaluator.evaluate_all_triggers({})

    # Should not activate - dependency not complete
    assert len(activated) == 0


def test_trigger_fires_only_once(prospective_store, evaluator):
    """Test that triggers only fire once."""
    task = ProspectiveTask(
        project_id=1,
        content="One-time reminder",
        active_form="Showing reminder",
        status=TaskStatus.PENDING,
    )
    task_id = prospective_store.create_task(task)

    # Create time trigger
    trigger = create_time_trigger(task_id, datetime.now() - timedelta(hours=1))
    prospective_store.add_trigger(trigger)

    # First evaluation - should activate
    context = {"current_time": datetime.now()}
    activated1 = evaluator.evaluate_all_triggers(context)
    assert len(activated1) == 1

    # Second evaluation - should not activate again
    activated2 = evaluator.evaluate_all_triggers(context)
    assert len(activated2) == 0


def test_multiple_triggers_any_fires(prospective_store, evaluator):
    """Test task with multiple triggers - any can activate."""
    task = ProspectiveTask(
        project_id=1,
        content="Flexible reminder",
        active_form="Showing flexible reminder",
        status=TaskStatus.PENDING,
    )
    task_id = prospective_store.create_task(task)

    # Add time trigger (not yet due)
    trigger1 = create_time_trigger(task_id, datetime.now() + timedelta(hours=1))
    prospective_store.add_trigger(trigger1)

    # Add file trigger (will fire)
    trigger2 = create_file_trigger(task_id, "config.json")
    prospective_store.add_trigger(trigger2)

    # Evaluate with file change
    context = {"file_changes": ["config.json"]}
    activated = evaluator.evaluate_all_triggers(context)

    # Should activate via file trigger
    assert len(activated) == 1


def test_event_trigger_outcome_matching(prospective_store, evaluator):
    """Test event trigger with outcome matching."""
    task = ProspectiveTask(
        project_id=1,
        content="Celebrate test success",
        active_form="Celebrating",
        status=TaskStatus.PENDING,
    )
    task_id = prospective_store.create_task(task)

    # Create trigger for successful test events
    trigger = create_event_trigger(
        task_id, event_type="action", outcome="success", content_pattern="test"
    )
    prospective_store.add_trigger(trigger)

    # Create matching event
    event = EpisodicEvent(
        project_id=1,
        session_id="test",
        event_type=EventType.ACTION,
        content="Run tests",
        outcome="success",
        timestamp=datetime.now(),
    )

    context = {"event": event}
    activated = evaluator.evaluate_all_triggers(context)

    # Should activate
    assert len(activated) == 1


def test_event_trigger_wrong_outcome(prospective_store, evaluator):
    """Test event trigger with wrong outcome."""
    task = ProspectiveTask(
        project_id=1,
        content="Handle test failure",
        active_form="Handling failure",
        status=TaskStatus.PENDING,
    )
    task_id = prospective_store.create_task(task)

    # Create trigger for failed tests
    trigger = create_event_trigger(task_id, outcome="failure")
    prospective_store.add_trigger(trigger)

    # Create event with success outcome
    event = EpisodicEvent(
        project_id=1,
        session_id="test",
        event_type=EventType.ACTION,
        content="Run tests",
        outcome="success",  # Wrong outcome
        timestamp=datetime.now(),
    )

    context = {"event": event}
    activated = evaluator.evaluate_all_triggers(context)

    # Should not activate
    assert len(activated) == 0
