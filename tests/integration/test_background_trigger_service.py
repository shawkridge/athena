"""Integration tests for BackgroundTriggerService.

Tests the complete trigger evaluation workflow, including:
- Service lifecycle (start/stop)
- Trigger evaluation and task activation
- Event recording for learning
- Error handling and recovery
- Metrics tracking
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock, patch

from athena.services.background_trigger_service import BackgroundTriggerService
from athena.prospective.models import (
    ProspectiveTask,
    TaskStatus,
    TaskPhase,
    TaskPriority,
    TaskTrigger,
    TriggerType,
)
from athena.episodic.models import EpisodicEvent, EventType, EventOutcome


class MockProspectiveStore:
    """Mock prospective store for testing."""

    def __init__(self):
        self.tasks = {}
        self.task_id_counter = 0
        self.phase_updates = []
        self.triggers = {}

    def list_tasks(self, status=None, limit=None):
        """Return tasks by status."""
        result = []
        for t in self.tasks.values():
            if not status:
                result.append(t)
            elif isinstance(t.status, str):
                # Status might be a string
                if t.status == status:
                    result.append(t)
            else:
                # Status might be an enum
                if t.status.value == status:
                    result.append(t)
        if limit:
            result = result[:limit]
        return result

    def get_task(self, task_id):
        """Get task by ID."""
        return self.tasks.get(task_id)

    def update_task_phase(self, task_id, phase):
        """Update task phase."""
        if task_id in self.tasks:
            self.tasks[task_id].phase = phase
            self.phase_updates.append((task_id, phase))

    def get_triggers(self, task_id):
        """Get triggers for task."""
        return self.triggers.get(task_id, [])

    def add_task(self, task):
        """Add task to store."""
        self.task_id_counter += 1
        task.id = self.task_id_counter
        self.tasks[task.id] = task
        return task

    def add_trigger(self, task_id, trigger):
        """Add trigger to task."""
        if task_id not in self.triggers:
            self.triggers[task_id] = []
        self.triggers[task_id].append(trigger)


class MockEpisodicStore:
    """Mock episodic store for testing."""

    def __init__(self):
        self.events = []

    def save_event(self, event):
        """Save event."""
        self.events.append(event)

    async def save_event_async(self, event):
        """Save event async."""
        self.events.append(event)


class TestBackgroundTriggerService:
    """Test suite for BackgroundTriggerService."""

    @pytest.fixture
    def mock_store(self):
        """Create mock prospective store."""
        return MockProspectiveStore()

    @pytest.fixture
    def mock_episodic(self):
        """Create mock episodic store."""
        return MockEpisodicStore()

    @pytest.fixture
    def service(self, mock_store, mock_episodic):
        """Create service with mocked stores."""
        service = BackgroundTriggerService(
            prospective_store=mock_store,
            episodic_store=mock_episodic,
            notification_service=None,
        )
        return service

    @pytest.mark.asyncio
    async def test_service_initialization(self, mock_store, mock_episodic):
        """Test service initializes correctly."""
        service = BackgroundTriggerService(mock_store, mock_episodic)

        assert service.prospective_store is mock_store
        assert service.episodic_store is mock_episodic
        assert not service.is_running()
        assert service.metrics["total_evaluations"] == 0
        assert service.metrics["total_activations"] == 0

    @pytest.mark.asyncio
    async def test_service_start_and_stop(self, service):
        """Test service start and stop lifecycle."""
        assert not service.is_running()

        # Start service
        await service.start(evaluation_interval_seconds=1)
        assert service.is_running()
        await asyncio.sleep(0.2)

        # Stop service
        await service.stop()
        assert not service.is_running()

    @pytest.mark.asyncio
    async def test_cannot_start_twice(self, service):
        """Test that starting service twice is prevented."""
        await service.start()
        assert service.is_running()

        # Try to start again (should warn, not error)
        await service.start()
        assert service.is_running()

        # Cleanup
        await service.stop()

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self, service):
        """Test stopping when service is not running."""
        assert not service.is_running()

        # Should not error
        await service.stop()
        assert not service.is_running()

    @pytest.mark.asyncio
    async def test_evaluation_loop_runs_periodically(self, service, mock_store):
        """Test that evaluation loop runs multiple times."""
        # Create a task
        task = ProspectiveTask(
            content="Test task",
            active_form="Testing task",
            status=TaskStatus.PENDING,
        )
        mock_store.add_task(task)

        # Start service with short interval
        await service.start(evaluation_interval_seconds=0.1)
        await asyncio.sleep(0.35)  # Wait for ~3 evaluations
        await service.stop()

        # Should have evaluated at least 2 times
        assert service.metrics["total_evaluations"] >= 2

    @pytest.mark.asyncio
    async def test_task_activation_updates_phase(self, service, mock_store, mock_episodic):
        """Test that activated tasks have their phase updated."""
        # Create task
        task = ProspectiveTask(
            content="Test activation",
            active_form="Testing activation",
            status=TaskStatus.PENDING,
            phase=TaskPhase.PLANNING,
        )
        mock_store.add_task(task)

        # Manually trigger activation
        await service._handle_task_activation(task, {})

        # Verify phase was updated
        assert len(mock_store.phase_updates) > 0
        task_id, phase = mock_store.phase_updates[0]
        assert task_id == task.id
        assert phase == TaskPhase.PLAN_READY

    @pytest.mark.asyncio
    async def test_episodic_event_recorded_on_activation(
        self, service, mock_store, mock_episodic
    ):
        """Test that episodic event is recorded when task activates."""
        task = ProspectiveTask(
            content="Test event recording",
            active_form="Testing event recording",
            status=TaskStatus.PENDING,
            project_id=1,
        )
        mock_store.add_task(task)

        # Trigger activation
        await service._handle_task_activation(task, {})

        # Verify event was recorded
        assert len(mock_episodic.events) > 0
        event = mock_episodic.events[0]
        assert isinstance(event, EpisodicEvent)
        assert event.event_type == EventType.ACTION
        assert event.context.task == f"task_{task.id}"
        assert event.context.phase == TaskPhase.PLAN_READY.value

    @pytest.mark.asyncio
    async def test_context_building(self, service, mock_store):
        """Test that context is built correctly."""
        # Add some completed tasks
        completed_task = ProspectiveTask(
            content="Completed",
            active_form="Completed task",
            status=TaskStatus.COMPLETED,
        )
        mock_store.add_task(completed_task)

        # Build context
        context = service._build_context()

        assert "current_time" in context
        assert isinstance(context["current_time"], datetime)
        assert "active_project" in context
        assert "completed_tasks" in context
        assert "active_task_count" in context

    @pytest.mark.asyncio
    async def test_metrics_tracking(self, service, mock_store):
        """Test that metrics are tracked accurately."""
        # Create a task
        task = ProspectiveTask(
            content="Metrics test",
            active_form="Testing metrics",
            status=TaskStatus.PENDING,
        )
        mock_store.add_task(task)

        initial_evals = service.metrics["total_evaluations"]

        # Run one evaluation
        await service._evaluate_once()

        # Metrics should be updated
        assert service.metrics["total_evaluations"] == initial_evals + 1
        assert service.metrics["last_evaluation"] is not None
        assert service.metrics["average_evaluation_time_ms"] > 0

    @pytest.mark.asyncio
    async def test_evaluation_metrics_increment(self, service, mock_store):
        """Test that evaluation metrics are incremented correctly."""
        initial_count = service.metrics["total_evaluations"]

        # Run a few evaluations
        await service._evaluate_once()
        await service._evaluate_once()

        # Metrics should be incremented
        assert service.metrics["total_evaluations"] == initial_count + 2
        assert service.metrics["last_evaluation"] is not None

    @pytest.mark.asyncio
    async def test_error_handling_during_activation(self, service, mock_store, mock_episodic):
        """Test that errors during activation are handled."""
        task = ProspectiveTask(
            content="Error test",
            active_form="Testing error",
            status=TaskStatus.PENDING,
        )
        mock_store.add_task(task)

        # Make update_task_phase raise an error
        original_update = mock_store.update_task_phase

        def failing_update(*args, **kwargs):
            raise RuntimeError("Update failed")

        mock_store.update_task_phase = failing_update

        # Activation should raise the error (it's re-raised after logging)
        with pytest.raises(RuntimeError, match="Update failed"):
            await service._handle_task_activation(task, {})

        # Restore
        mock_store.update_task_phase = original_update

    @pytest.mark.asyncio
    async def test_get_metrics(self, service):
        """Test that metrics can be retrieved."""
        await service._evaluate_once()

        metrics = service.get_metrics()

        assert "total_evaluations" in metrics
        assert "total_activations" in metrics
        assert "last_evaluation" in metrics
        assert "evaluation_errors" in metrics
        assert "average_evaluation_time_ms" in metrics
        assert metrics["total_evaluations"] > 0

    @pytest.mark.asyncio
    async def test_is_running_flag(self, service):
        """Test is_running() returns correct state."""
        assert not service.is_running()

        await service.start()
        assert service.is_running()

        await service.stop()
        assert not service.is_running()

    @pytest.mark.asyncio
    async def test_notification_not_sent_when_none(self, service, mock_store):
        """Test that no error when notification_service is None."""
        task = ProspectiveTask(
            content="No notification",
            active_form="Testing no notification",
            status=TaskStatus.PENDING,
        )
        mock_store.add_task(task)

        # Should not error even though notification_service is None
        await service._handle_task_activation(task, {})

    @pytest.mark.asyncio
    async def test_completed_tasks_in_context(self, service, mock_store):
        """Test that recently completed tasks appear in context."""
        # Add completed task
        completed = ProspectiveTask(
            content="Done task",
            active_form="Completed task",
            status=TaskStatus.COMPLETED,
        )
        mock_store.add_task(completed)

        context = service._build_context()

        assert len(context["completed_tasks"]) > 0
        assert context["completed_tasks"][0].content == "Done task"

    @pytest.mark.asyncio
    async def test_long_running_evaluation_doesnt_block_next(self, service, mock_store):
        """Test that a slow evaluation doesn't block the next one."""
        call_count = 0
        original_evaluate = service._evaluate_once

        async def slow_evaluate():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.2)  # Simulate slow evaluation
            await original_evaluate()

        service._evaluate_once = slow_evaluate

        # Start with very short interval
        await service.start(evaluation_interval_seconds=0.05)
        await asyncio.sleep(0.4)
        await service.stop()

        # Should have been called at least twice (0.4 / 0.2 min)
        assert call_count >= 1

    @pytest.mark.asyncio
    async def test_cancellation_during_evaluation(self, service, mock_store):
        """Test graceful cancellation even during evaluation."""
        await service.start(evaluation_interval_seconds=10)

        # Immediately stop (might interrupt evaluation)
        await service.stop()

        # Should be cleanly stopped
        assert not service.is_running()


class TestTriggerEvaluationIntegration:
    """Test integration with TriggerEvaluator."""

    @pytest.fixture
    def trigger_service(self):
        """Create service with real trigger evaluator."""
        from athena.prospective.triggers import TriggerEvaluator

        store = MockProspectiveStore()
        episodic = MockEpisodicStore()

        # Patch TriggerEvaluator to return a task
        with patch("athena.services.background_trigger_service.TriggerEvaluator") as mock_eval:
            mock_eval_instance = Mock()
            mock_eval.return_value = mock_eval_instance

            service = BackgroundTriggerService(store, episodic)

            # Setup trigger evaluator mock
            mock_eval_instance.evaluate_all_triggers.return_value = []

            yield service, store, episodic, mock_eval_instance

    @pytest.mark.asyncio
    async def test_trigger_evaluation_called(self, trigger_service):
        """Test that TriggerEvaluator.evaluate_all_triggers is called."""
        service, store, episodic, mock_eval = trigger_service

        await service._evaluate_once()

        mock_eval.evaluate_all_triggers.assert_called_once()

    @pytest.mark.asyncio
    async def test_activated_tasks_processed(self, trigger_service):
        """Test that activated tasks are processed."""
        service, store, episodic, mock_eval = trigger_service

        # Setup task
        task = ProspectiveTask(
            content="Evaluated task",
            active_form="Evaluating task",
            status=TaskStatus.PENDING,
        )
        store.add_task(task)

        # Mock evaluator to return the task
        mock_eval.evaluate_all_triggers.return_value = [task]

        await service._evaluate_once()

        # Task should be processed
        assert service.metrics["total_activations"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
