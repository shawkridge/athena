"""Unit tests for EventHandlers system."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from athena.core.database import Database
from athena.automation.orchestrator import AutomationOrchestrator, AutomationEvent
from athena.automation.event_handlers import EventHandlers, EventListener


@pytest.fixture
def db(tmp_path):
    """Create test database."""
    return Database(str(tmp_path / "test.db"))


@pytest.fixture
def orchestrator(db):
    """Create mock orchestrator."""
    with patch("memory_mcp.automation.orchestrator.HealthMonitorAgent"):
        with patch("memory_mcp.automation.orchestrator.PlanningOptimizerAgent"):
            with patch("memory_mcp.automation.orchestrator.AnalyticsAggregatorAgent"):
                with patch("memory_mcp.automation.orchestrator.ProjectCoordinatorAgent"):
                    return AutomationOrchestrator(db)


@pytest.fixture
def handlers(db, orchestrator):
    """Create EventHandlers instance."""
    return EventHandlers(db, orchestrator)


class TestEventHandlersBasics:
    """Test basic EventHandlers functionality."""

    def test_initialization(self, handlers):
        """Test EventHandlers initialization."""
        assert handlers.db is not None
        assert handlers.orchestrator is not None
        assert len(handlers._listeners) == 5
        assert "task_created" in handlers._listeners
        assert "task_completed" in handlers._listeners
        assert "task_status_changed" in handlers._listeners
        assert "resource_conflict_detected" in handlers._listeners
        assert "health_degraded" in handlers._listeners

    def test_builtin_handlers_registered(self, handlers):
        """Test that built-in handlers are registered."""
        task_created_listeners = handlers._listeners["task_created"]
        assert len(task_created_listeners) > 0
        assert any(l.name == "orchestrator_task_created" for l in task_created_listeners)

    def test_register_listener(self, handlers):
        """Test registering custom event listener."""
        custom_handler = AsyncMock()

        handlers.register_listener(
            "task_created",
            custom_handler,
            name="custom_handler",
            priority=50,
        )

        listeners = handlers._listeners["task_created"]
        assert any(l.name == "custom_handler" for l in listeners)
        custom_listener = next(l for l in listeners if l.name == "custom_handler")
        assert custom_listener.priority == 50

    def test_listener_priority_ordering(self, handlers):
        """Test listeners are ordered by priority."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        handler3 = AsyncMock()

        handlers.register_listener("task_created", handler1, name="low_priority", priority=10)
        handlers.register_listener("task_created", handler2, name="high_priority", priority=100)
        handlers.register_listener("task_created", handler3, name="mid_priority", priority=50)

        listeners = handlers._listeners["task_created"]
        # Find our custom listeners
        custom = [l for l in listeners if l.name in ["low_priority", "high_priority", "mid_priority"]]
        assert custom[0].name == "high_priority"
        assert custom[1].name == "mid_priority"
        assert custom[2].name == "low_priority"

    def test_unregister_listener(self, handlers):
        """Test unregistering listener."""
        custom_handler = AsyncMock()
        handlers.register_listener(
            "task_created",
            custom_handler,
            name="test_handler",
        )

        assert any(l.name == "test_handler" for l in handlers._listeners["task_created"])

        removed = handlers.unregister_listener("task_created", "test_handler")
        assert removed is True
        assert not any(l.name == "test_handler" for l in handlers._listeners["task_created"])

    def test_unregister_nonexistent_listener(self, handlers):
        """Test unregistering listener that doesn't exist."""
        removed = handlers.unregister_listener("task_created", "nonexistent")
        assert removed is False

    def test_unregister_from_nonexistent_type(self, handlers):
        """Test unregistering from event type that doesn't exist."""
        removed = handlers.unregister_listener("nonexistent_type", "some_handler")
        assert removed is False


class TestEventTriggering:
    """Test event triggering and routing."""

    @pytest.mark.asyncio
    async def test_trigger_task_created_event(self, handlers):
        """Test triggering task_created event."""
        handlers.orchestrator.handle_event = AsyncMock(return_value={"status": "success"})

        result = await handlers.trigger_event(
            "task_created",
            entity_id=1,
            entity_type="task",
            metadata={"project_id": 1},
        )

        assert result["event_type"] == "task_created"
        assert result["entity_id"] == 1
        assert result["status"] == "processed"
        assert result["listener_count"] >= 1

    @pytest.mark.asyncio
    async def test_trigger_event_with_all_listeners(self, handlers):
        """Test event triggers all registered listeners."""
        handler1 = AsyncMock(return_value="result1")
        handler2 = AsyncMock(return_value="result2")

        handlers.register_listener("test_event", handler1, name="handler1", priority=1)
        handlers.register_listener("test_event", handler2, name="handler2", priority=2)

        result = await handlers.trigger_event("test_event", 1, "test_entity")

        assert handler1.called
        assert handler2.called
        assert result["listener_count"] == 2

    @pytest.mark.asyncio
    async def test_trigger_event_with_no_listeners(self, handlers):
        """Test triggering event with no registered listeners."""
        # Create new event type with no listeners
        handlers._listeners["unique_event_type"] = []

        result = await handlers.trigger_event("unique_event_type", 1, "entity")

        # Event type exists but has no listeners - status is still processed
        assert result["status"] == "processed"
        assert result["listener_count"] == 0

    @pytest.mark.asyncio
    async def test_trigger_event_handler_error_handling(self, handlers):
        """Test event handler errors are caught and recorded."""
        failing_handler = AsyncMock(side_effect=ValueError("Test error"))

        handlers.register_listener("task_created", failing_handler, name="failing_handler")

        result = await handlers.trigger_event("task_created", 1, "task")

        assert result["status"] == "processed"
        # Should have at least one failed result
        failed_results = [r for r in result["results"] if r["status"] == "error"]
        assert len(failed_results) > 0

    @pytest.mark.asyncio
    async def test_trigger_event_with_metadata(self, handlers):
        """Test event includes custom metadata."""
        captured_event = None

        async def capture_handler(event):
            nonlocal captured_event
            captured_event = event
            return {}

        handlers.register_listener("test_event", capture_handler, name="capture")

        metadata = {"custom_key": "custom_value", "nested": {"data": 123}}
        await handlers.trigger_event("test_event", 1, "entity", metadata=metadata)

        assert captured_event is not None
        assert captured_event.metadata["custom_key"] == "custom_value"
        assert captured_event.metadata["nested"]["data"] == 123


class TestEventHistory:
    """Test event history tracking."""

    @pytest.mark.asyncio
    async def test_event_recorded_in_history(self, handlers):
        """Test events are recorded in history."""
        handlers.orchestrator.handle_event = AsyncMock(return_value={})

        await handlers.on_task_created(task_id=1, project_id=1)

        history = handlers.get_event_history()
        assert len(history) > 0
        last_event = history[-1]
        assert last_event["event_type"] == "task_created"
        assert last_event["entity_id"] == 1

    @pytest.mark.asyncio
    async def test_event_history_filtering(self, handlers):
        """Test filtering event history by type."""
        handlers.orchestrator.handle_event = AsyncMock(return_value={})

        await handlers.on_task_created(task_id=1, project_id=1)
        await handlers.on_task_completed(task_id=1, project_id=1)
        await handlers.on_task_created(task_id=2, project_id=1)

        all_history = handlers.get_event_history()
        assert len(all_history) >= 3

        created_history = handlers.get_event_history(event_type="task_created")
        assert all(e["event_type"] == "task_created" for e in created_history)

    def test_event_history_size_bounded(self, handlers):
        """Test event history size is bounded."""
        # Set small max size for testing
        handlers._max_history_size = 10

        # Add more events than max
        for i in range(20):
            event = AutomationEvent(
                event_type="test",
                entity_id=i,
                entity_type="test",
                metadata={},
                timestamp=datetime.utcnow(),
            )
            handlers._record_event_history(event)

        assert len(handlers._event_history) <= 10

    def test_event_history_limit_parameter(self, handlers):
        """Test limit parameter in get_event_history."""
        handlers.orchestrator.handle_event = AsyncMock(return_value={})

        # Record events
        for i in range(5):
            event = AutomationEvent(
                event_type="test",
                entity_id=i,
                entity_type="test",
                metadata={},
                timestamp=datetime.utcnow(),
            )
            handlers._record_event_history(event)

        history = handlers.get_event_history(limit=2)
        assert len(history) == 2


class TestConvenienceMethods:
    """Test convenience event triggering methods."""

    @pytest.mark.asyncio
    async def test_on_task_created(self, handlers):
        """Test on_task_created convenience method."""
        handlers.orchestrator.handle_event = AsyncMock(return_value={})

        result = await handlers.on_task_created(task_id=1, project_id=1)

        assert result["event_type"] == "task_created"
        assert result["status"] == "processed"

    @pytest.mark.asyncio
    async def test_on_task_completed(self, handlers):
        """Test on_task_completed convenience method."""
        handlers.orchestrator.handle_event = AsyncMock(return_value={})

        result = await handlers.on_task_completed(
            task_id=1, project_id=1, actual_duration=120
        )

        assert result["event_type"] == "task_completed"
        assert result["status"] == "processed"

    @pytest.mark.asyncio
    async def test_on_task_status_changed(self, handlers):
        """Test on_task_status_changed convenience method."""
        handlers.orchestrator.handle_event = AsyncMock(return_value={})

        result = await handlers.on_task_status_changed(
            task_id=1, project_id=1, new_status="executing", reason="Started work"
        )

        assert result["event_type"] == "task_status_changed"
        assert result["status"] == "processed"

    @pytest.mark.asyncio
    async def test_on_resource_conflict(self, handlers):
        """Test on_resource_conflict convenience method."""
        handlers.orchestrator.handle_event = AsyncMock(return_value={})

        result = await handlers.on_resource_conflict(
            project_ids=[1, 2],
            conflict_type="person",
            details={"person": "Alice", "tasks": [1, 2]},
        )

        assert result["event_type"] == "resource_conflict_detected"
        assert result["status"] == "processed"

    @pytest.mark.asyncio
    async def test_on_health_degraded(self, handlers):
        """Test on_health_degraded convenience method."""
        handlers.orchestrator.handle_event = AsyncMock(return_value={})

        result = await handlers.on_health_degraded(
            task_id=1,
            project_id=1,
            health_score=0.4,
            reason="Too many errors",
        )

        assert result["event_type"] == "health_degraded"
        assert result["status"] == "processed"


class TestListenerInfo:
    """Test listener information retrieval."""

    def test_get_listener_info(self, handlers):
        """Test getting listener information."""
        info = handlers.get_listener_info()

        assert "total_event_types" in info
        assert "by_type" in info
        assert len(info["by_type"]) == 5

    def test_get_listener_info_shows_all_listeners(self, handlers):
        """Test listener info shows all registered listeners."""
        custom_handler = AsyncMock()
        handlers.register_listener(
            "task_created",
            custom_handler,
            name="custom_listener",
            priority=50,
        )

        info = handlers.get_listener_info()
        task_created_info = info["by_type"]["task_created"]

        assert task_created_info["listener_count"] >= 2
        listener_names = [l["name"] for l in task_created_info["listeners"]]
        assert "orchestrator_task_created" in listener_names
        assert "custom_listener" in listener_names

    def test_get_listener_info_order(self, handlers):
        """Test listener info shows correct execution order."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        handlers.register_listener("task_created", handler1, name="low", priority=10)
        handlers.register_listener("task_created", handler2, name="high", priority=100)

        info = handlers.get_listener_info()
        listeners = info["by_type"]["task_created"]["listeners"]

        # Find our custom listeners
        custom_listeners = [l for l in listeners if l["name"] in ["low", "high"]]
        # High priority should come before low
        high_idx = next(i for i, l in enumerate(listeners) if l["name"] == "high")
        low_idx = next(i for i, l in enumerate(listeners) if l["name"] == "low")
        assert high_idx < low_idx


class TestBuiltinHandlers:
    """Test built-in event handlers."""

    @pytest.mark.asyncio
    async def test_task_created_handler_routes_to_orchestrator(self, handlers):
        """Test task_created event routes to orchestrator."""
        handlers.orchestrator.handle_event = AsyncMock(
            return_value={"status": "success", "actions": ["optimized"]}
        )

        result = await handlers.on_task_created(task_id=1, project_id=1)

        handlers.orchestrator.handle_event.assert_called_once()
        call_args = handlers.orchestrator.handle_event.call_args
        event = call_args[0][0]
        assert event.event_type == "task_created"

    @pytest.mark.asyncio
    async def test_task_completed_handler_routes_to_orchestrator(self, handlers):
        """Test task_completed event routes to orchestrator."""
        handlers.orchestrator.handle_event = AsyncMock(return_value={})

        await handlers.on_task_completed(task_id=1, project_id=1, actual_duration=120)

        handlers.orchestrator.handle_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_builtin_handlers_route_to_orchestrator(self, handlers):
        """Test all built-in handlers route to orchestrator."""
        handlers.orchestrator.handle_event = AsyncMock(return_value={})

        await handlers.on_task_created(task_id=1, project_id=1)
        await handlers.on_task_completed(task_id=1, project_id=1)
        await handlers.on_task_status_changed(task_id=1, project_id=1, new_status="completed")
        await handlers.on_resource_conflict(project_ids=[1], conflict_type="person")
        await handlers.on_health_degraded(task_id=1, project_id=1, health_score=0.4)

        assert handlers.orchestrator.handle_event.call_count == 5


class TestEventSynchronization:
    """Test event handling synchronization."""

    @pytest.mark.asyncio
    async def test_concurrent_event_handling(self, handlers):
        """Test concurrent event handling."""
        handlers.orchestrator.handle_event = AsyncMock(return_value={})

        tasks = [
            handlers.on_task_created(task_id=i, project_id=1)
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert all(r["status"] == "processed" for r in results)

    @pytest.mark.asyncio
    async def test_event_listener_exception_isolation(self, handlers):
        """Test one listener's exception doesn't affect others."""
        handler1 = AsyncMock(side_effect=ValueError("Error in handler1"))
        handler2 = AsyncMock(return_value="success")

        handlers.register_listener("task_created", handler1, name="failing", priority=100)
        handlers.register_listener("task_created", handler2, name="success", priority=50)

        result = await handlers.trigger_event("task_created", 1, "task")

        # Both handlers should have been called
        assert handler1.called
        assert handler2.called

        # Both should appear in results
        assert len(result["results"]) >= 2

        # One should be success, one should be error
        statuses = [r["status"] for r in result["results"]]
        assert "success" in statuses
        assert "error" in statuses
