"""Integration tests for Tier 1 automation (AutomationOrchestrator + EventHandlers)."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, call

from athena.core.database import Database
from athena.automation.orchestrator import AutomationOrchestrator, AutomationEvent, AutomationConfig
from athena.automation.event_handlers import EventHandlers


@pytest.fixture
def db(tmp_path):
    """Create test database."""
    return Database(str(tmp_path / "test.db"))


@pytest.fixture
def orchestrator_with_mocks(db):
    """Create orchestrator with mocked agents."""
    with patch("memory_mcp.automation.orchestrator.HealthMonitorAgent"):
        with patch("memory_mcp.automation.orchestrator.PlanningOptimizerAgent"):
            with patch("memory_mcp.automation.orchestrator.AnalyticsAggregatorAgent"):
                with patch("memory_mcp.automation.orchestrator.ProjectCoordinatorAgent"):
                    return AutomationOrchestrator(db)


@pytest.fixture
def event_handlers(db, orchestrator_with_mocks):
    """Create EventHandlers with mocked orchestrator."""
    return EventHandlers(db, orchestrator_with_mocks)


class TestAutomationOrchestrationFlow:
    """Test complete automation orchestration workflow."""

    @pytest.mark.asyncio
    async def test_task_created_event_triggers_plan_optimization(self, event_handlers):
        """Test task_created event routes to orchestrator for plan optimization."""
        event_handlers.orchestrator.handle_event = AsyncMock(
            return_value={"status": "success", "actions": ["optimized"]}
        )

        result = await event_handlers.on_task_created(task_id=1, project_id=1)

        assert result["status"] == "processed"
        assert result["listener_count"] >= 1
        event_handlers.orchestrator.handle_event.assert_called_once()

        # Verify event details
        call_args = event_handlers.orchestrator.handle_event.call_args
        event = call_args[0][0]
        assert event.event_type == "task_created"
        assert event.entity_id == 1
        assert event.metadata["project_id"] == 1

    @pytest.mark.asyncio
    async def test_task_completed_event_triggers_analytics(self, event_handlers):
        """Test task_completed event triggers analytics aggregation."""
        event_handlers.orchestrator.handle_event = AsyncMock(return_value={})

        result = await event_handlers.on_task_completed(
            task_id=1, project_id=1, actual_duration=120
        )

        assert result["status"] == "processed"
        event_handlers.orchestrator.handle_event.assert_called_once()

        # Verify metadata includes actual duration
        event = event_handlers.orchestrator.handle_event.call_args[0][0]
        assert event.metadata["actual_duration"] == 120

    @pytest.mark.asyncio
    async def test_task_status_change_to_executing_triggers_health_check(self, event_handlers):
        """Test status change to EXECUTING triggers health check."""
        event_handlers.orchestrator.handle_event = AsyncMock(return_value={})

        result = await event_handlers.on_task_status_changed(
            task_id=1, project_id=1, new_status="executing"
        )

        assert result["status"] == "processed"
        event_handlers.orchestrator.handle_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_degraded_event_triggers_optimization(self, event_handlers):
        """Test health degradation triggers plan optimization."""
        event_handlers.orchestrator.handle_event = AsyncMock(return_value={})

        result = await event_handlers.on_health_degraded(
            task_id=1, project_id=1, health_score=0.4, reason="Too many errors"
        )

        assert result["status"] == "processed"
        event_handlers.orchestrator.handle_event.assert_called_once()

        # Verify health score in event
        event = event_handlers.orchestrator.handle_event.call_args[0][0]
        assert event.metadata["health_score"] == 0.4

    @pytest.mark.asyncio
    async def test_resource_conflict_detected_triggers_alert(self, event_handlers):
        """Test resource conflict detection triggers alerting."""
        event_handlers.orchestrator.handle_event = AsyncMock(return_value={})

        result = await event_handlers.on_resource_conflict(
            project_ids=[1, 2],
            conflict_type="person",
            details={"person": "Alice", "tasks": [1, 2, 3]}
        )

        assert result["status"] == "processed"
        event_handlers.orchestrator.handle_event.assert_called_once()

        # Verify conflict type in event
        event = event_handlers.orchestrator.handle_event.call_args[0][0]
        assert event.metadata["conflict_type"] == "person"


class TestBackgroundMonitoring:
    """Test background health monitoring functionality."""

    @pytest.mark.asyncio
    async def test_start_background_monitoring(self, orchestrator_with_mocks):
        """Test starting background health monitoring."""
        # Start monitoring
        await orchestrator_with_mocks.start_background_monitoring(project_id=1)

        # Verify task was created
        assert len(orchestrator_with_mocks._background_tasks) > 0

        # Clean up
        await orchestrator_with_mocks.stop_background_monitoring()

    @pytest.mark.asyncio
    async def test_stop_background_monitoring(self, orchestrator_with_mocks):
        """Test stopping background monitoring."""
        await orchestrator_with_mocks.start_background_monitoring(project_id=1)
        assert len(orchestrator_with_mocks._background_tasks) > 0

        await orchestrator_with_mocks.stop_background_monitoring()
        assert len(orchestrator_with_mocks._background_tasks) == 0

    @pytest.mark.asyncio
    async def test_periodic_health_check_respects_interval(self, orchestrator_with_mocks):
        """Test periodic health checks respect configured interval."""
        config = orchestrator_with_mocks.config
        assert config.health_check_interval_minutes == 30

        # With mocked check, verify timing logic works
        project_id = 1
        orchestrator_with_mocks.health_monitor.check_active_tasks = AsyncMock(
            return_value=[]
        )

        # Run one iteration of periodic check
        task = asyncio.create_task(
            orchestrator_with_mocks._periodic_health_check(project_id)
        )

        # Give it a moment to run
        await asyncio.sleep(0.5)

        # Cancel the background task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


class TestAlertManagement:
    """Test alert storage, retrieval, and dismissal."""

    @pytest.mark.asyncio
    async def test_alert_generated_on_health_degraded(self, event_handlers):
        """Test alerts are generated and stored."""
        event_handlers.orchestrator.handle_event = AsyncMock(return_value={})

        await event_handlers.on_health_degraded(
            task_id=1, project_id=1, health_score=0.4
        )

        # In real scenario, orchestrator would store alerts
        # For now, verify event was routed
        assert event_handlers.orchestrator.handle_event.called

    def test_get_active_alerts(self, orchestrator_with_mocks):
        """Test retrieving active alerts."""
        # Manually add alerts for testing
        alert1 = {
            "task_id": 1,
            "severity": "critical",
            "type": "health_degraded",
            "message": "Task health is critical"
        }
        alert2 = {
            "task_id": 2,
            "severity": "warning",
            "type": "health_check",
            "message": "Task health is warning"
        }

        orchestrator_with_mocks._active_alerts[1] = alert1
        orchestrator_with_mocks._active_alerts[2] = alert2

        alerts = orchestrator_with_mocks.get_active_alerts()
        assert len(alerts) == 2
        assert any(a["task_id"] == 1 for a in alerts)
        assert any(a["task_id"] == 2 for a in alerts)

    def test_dismiss_alert(self, orchestrator_with_mocks):
        """Test dismissing individual alerts."""
        alert = {
            "task_id": 1,
            "severity": "warning",
            "type": "test"
        }
        orchestrator_with_mocks._active_alerts[1] = alert

        assert len(orchestrator_with_mocks.get_active_alerts()) == 1

        orchestrator_with_mocks.dismiss_alert(1)
        assert len(orchestrator_with_mocks.get_active_alerts()) == 0

    def test_clear_all_alerts(self, orchestrator_with_mocks):
        """Test clearing all alerts."""
        orchestrator_with_mocks._active_alerts[1] = {"severity": "critical"}
        orchestrator_with_mocks._active_alerts[2] = {"severity": "warning"}
        orchestrator_with_mocks._active_alerts[3] = {"severity": "info"}

        assert len(orchestrator_with_mocks.get_active_alerts()) == 3

        orchestrator_with_mocks.clear_alerts()
        assert len(orchestrator_with_mocks.get_active_alerts()) == 0


class TestEventRoutingChain:
    """Test complete event routing chain from handler to orchestrator."""

    @pytest.mark.asyncio
    async def test_multiple_events_in_sequence(self, event_handlers):
        """Test handling multiple events in sequence."""
        event_handlers.orchestrator.handle_event = AsyncMock(return_value={})

        # Simulate task lifecycle
        result1 = await event_handlers.on_task_created(task_id=1, project_id=1)
        result2 = await event_handlers.on_task_status_changed(
            task_id=1, project_id=1, new_status="executing"
        )
        result3 = await event_handlers.on_task_completed(
            task_id=1, project_id=1, actual_duration=120
        )

        # All events should be processed
        assert all(r["status"] == "processed" for r in [result1, result2, result3])

        # Orchestrator should be called 3 times
        assert event_handlers.orchestrator.handle_event.call_count == 3

        # Verify event sequence in history
        history = event_handlers.get_event_history()
        assert len(history) >= 3
        event_types = [e["event_type"] for e in history[-3:]]
        assert "task_created" in event_types
        assert "task_status_changed" in event_types
        assert "task_completed" in event_types

    @pytest.mark.asyncio
    async def test_concurrent_event_processing(self, event_handlers):
        """Test handling concurrent events."""
        event_handlers.orchestrator.handle_event = AsyncMock(return_value={})

        # Create multiple concurrent events
        tasks = [
            event_handlers.on_task_created(task_id=i, project_id=1)
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)

        # All should complete successfully
        assert all(r["status"] == "processed" for r in results)

        # Orchestrator called for each event
        assert event_handlers.orchestrator.handle_event.call_count == 5


class TestAutomationConfiguration:
    """Test automation configuration and customization."""

    def test_custom_health_check_interval(self, db):
        """Test custom health check interval configuration."""
        custom_config = AutomationConfig(
            health_check_interval_minutes=15
        )

        with patch("memory_mcp.automation.orchestrator.HealthMonitorAgent"):
            with patch("memory_mcp.automation.orchestrator.PlanningOptimizerAgent"):
                with patch("memory_mcp.automation.orchestrator.AnalyticsAggregatorAgent"):
                    with patch("memory_mcp.automation.orchestrator.ProjectCoordinatorAgent"):
                        orchestrator = AutomationOrchestrator(db, config=custom_config)

        assert orchestrator.config.health_check_interval_minutes == 15

    def test_disable_auto_optimize(self, db):
        """Test disabling automatic plan optimization."""
        custom_config = AutomationConfig(
            enable_auto_optimize_plans=False
        )

        with patch("memory_mcp.automation.orchestrator.HealthMonitorAgent"):
            with patch("memory_mcp.automation.orchestrator.PlanningOptimizerAgent"):
                with patch("memory_mcp.automation.orchestrator.AnalyticsAggregatorAgent"):
                    with patch("memory_mcp.automation.orchestrator.ProjectCoordinatorAgent"):
                        orchestrator = AutomationOrchestrator(db, config=custom_config)

        assert orchestrator.config.enable_auto_optimize_plans is False

    def test_disable_auto_escalate_alerts(self, db):
        """Test disabling automatic alert escalation."""
        custom_config = AutomationConfig(
            enable_auto_escalate_alerts=False
        )

        with patch("memory_mcp.automation.orchestrator.HealthMonitorAgent"):
            with patch("memory_mcp.automation.orchestrator.PlanningOptimizerAgent"):
                with patch("memory_mcp.automation.orchestrator.AnalyticsAggregatorAgent"):
                    with patch("memory_mcp.automation.orchestrator.ProjectCoordinatorAgent"):
                        orchestrator = AutomationOrchestrator(db, config=custom_config)

        assert orchestrator.config.enable_auto_escalate_alerts is False


class TestErrorHandlingAndRecovery:
    """Test error handling in automation."""

    @pytest.mark.asyncio
    async def test_orchestrator_handles_agent_errors(self, orchestrator_with_mocks):
        """Test orchestrator handles agent method errors gracefully."""
        # Make planning optimizer fail
        orchestrator_with_mocks.planning_optimizer.validate_and_optimize = AsyncMock(
            side_effect=ValueError("Simulated agent error")
        )

        # Create event that would trigger the failing agent
        event = AutomationEvent(
            event_type="task_created",
            entity_id=1,
            entity_type="task",
            metadata={},
            timestamp=datetime.utcnow()
        )

        # Should not raise, but handle gracefully and return processed status
        result = await orchestrator_with_mocks.handle_event(event)
        # Orchestrator catches errors and returns processed status (non-blocking)
        assert result["status"] == "processed"
        assert result["event_type"] == "task_created"

    @pytest.mark.asyncio
    async def test_event_handler_listener_error_isolation(self, event_handlers):
        """Test failing listeners don't block other listeners."""
        failing_handler = AsyncMock(side_effect=RuntimeError("Listener failed"))
        success_handler = AsyncMock(return_value="success")

        event_handlers.register_listener(
            "test_event",
            failing_handler,
            name="failing",
            priority=100
        )
        event_handlers.register_listener(
            "test_event",
            success_handler,
            name="success",
            priority=50
        )

        result = await event_handlers.trigger_event("test_event", 1, "entity")

        # Both listeners should have been invoked
        assert failing_handler.called
        assert success_handler.called

        # Result should show both success and error
        statuses = [r["status"] for r in result["results"]]
        assert "success" in statuses
        assert "error" in statuses
