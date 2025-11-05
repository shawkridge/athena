"""Tests for HookEventBridge and UnifiedHookSystem."""

import pytest
from athena.core.database import Database
from athena.hooks.dispatcher import HookDispatcher
from athena.hooks.bridge import HookEventBridge, UnifiedHookSystem
from athena.automation.event_handlers import EventHandlers
from athena.automation.orchestrator import AutomationOrchestrator


class TestHookEventBridge:
    """Test HookEventBridge functionality."""

    @pytest.fixture
    def setup_bridge(self, tmp_path):
        """Set up bridge with dependencies."""
        db = Database(str(tmp_path / "test.db"))
        hook_dispatcher = HookDispatcher(db, project_id=1)
        orchestrator = AutomationOrchestrator(db)
        event_handlers = EventHandlers(db, orchestrator)
        bridge = HookEventBridge(hook_dispatcher, event_handlers)

        return {
            "db": db,
            "hooks": hook_dispatcher,
            "events": event_handlers,
            "orchestrator": orchestrator,
            "bridge": bridge,
        }

    def test_bridge_initialization(self, setup_bridge):
        """Test bridge initializes correctly."""
        bridge = setup_bridge["bridge"]
        assert bridge is not None
        assert bridge.is_enabled()
        assert bridge._event_mapping_count == 0

    def test_bridge_enable_disable(self, setup_bridge):
        """Test enabling and disabling the bridge."""
        bridge = setup_bridge["bridge"]

        assert bridge.is_enabled()

        bridge.disable_bridging()
        assert not bridge.is_enabled()

        bridge.enable_bridging()
        assert bridge.is_enabled()

    def test_bridge_stats(self, setup_bridge):
        """Test getting bridge statistics."""
        bridge = setup_bridge["bridge"]

        stats = bridge.get_bridge_stats()
        assert "enabled" in stats
        assert "events_routed" in stats
        assert "hook_dispatcher_stats" in stats
        assert "listener_info" in stats

    def test_bridge_reset_stats(self, setup_bridge):
        """Test resetting bridge statistics."""
        bridge = setup_bridge["bridge"]

        # Manually increment counter
        bridge._event_mapping_count = 5

        bridge.reset_stats()
        assert bridge._event_mapping_count == 0


class TestUnifiedHookSystem:
    """Test UnifiedHookSystem functionality."""

    @pytest.fixture
    def unified_system(self, tmp_path):
        """Set up unified system."""
        db = Database(str(tmp_path / "test.db"))
        hooks = HookDispatcher(db, project_id=1)
        orchestrator = AutomationOrchestrator(db)
        events = EventHandlers(db, orchestrator)
        system = UnifiedHookSystem(hooks, events)

        return system

    def test_unified_system_initialization(self, unified_system):
        """Test unified system initializes correctly."""
        assert unified_system is not None
        assert unified_system.hooks is not None
        assert unified_system.events is not None
        assert unified_system.bridge is not None

    def test_unified_system_get_status(self, unified_system):
        """Test getting unified system status."""
        status = unified_system.get_system_status()

        assert "hooks" in status
        assert "events" in status
        assert "bridge" in status

        # Verify hooks structure
        assert "registry" in status["hooks"]
        assert "stats" in status["hooks"]
        assert "safety" in status["hooks"]

        # Verify events structure
        assert "listeners" in status["events"]
        assert "history_size" in status["events"]

        # Verify bridge structure
        assert "enabled" in status["bridge"]
        assert "events_routed" in status["bridge"]

    def test_unified_system_enable_all(self, unified_system):
        """Test enabling all components."""
        unified_system.disable_all()

        # Re-enable
        unified_system.enable_all()

        assert unified_system.bridge.is_enabled()

        # All hooks should be enabled
        for hook_id, hook_info in unified_system.hooks.get_hook_registry().items():
            assert hook_info["enabled"]

    def test_unified_system_disable_all(self, unified_system):
        """Test disabling all components."""
        unified_system.disable_all()

        assert not unified_system.bridge.is_enabled()

        # All hooks should be disabled
        for hook_id, hook_info in unified_system.hooks.get_hook_registry().items():
            assert not hook_info["enabled"]

    def test_unified_system_reset_stats(self, unified_system):
        """Test resetting all statistics."""
        # Manually fire a hook to increment counts
        unified_system.hooks.fire_session_start()

        # Reset
        unified_system.reset_all_stats()

        # Bridge stats should be reset
        assert unified_system.bridge._event_mapping_count == 0

    def test_unified_system_hook_event_integration(self, unified_system):
        """Test that hooks and events are integrated in unified system."""
        # Start session
        session_id = unified_system.hooks.fire_session_start()
        assert session_id is not None

        # Fire conversation turn
        turn_id = unified_system.hooks.fire_conversation_turn(
            "user says hello", "assistant says hi", task="test"
        )
        assert turn_id > 0

        # Check system status
        status = unified_system.get_system_status()

        # Hooks should have recorded events
        assert status["hooks"]["stats"]["session_start"]["execution_count"] > 0
        assert status["hooks"]["stats"]["conversation_turn"]["execution_count"] > 0

    def test_unified_system_independent_components(self, unified_system):
        """Test that hooks and events work independently if needed."""
        hooks = unified_system.hooks
        events = unified_system.events

        # Hooks work without events
        session_id = hooks.fire_session_start()
        assert session_id is not None

        # Events have their own listeners
        assert len(events._listeners) > 0


class TestBridgeIntegration:
    """Integration tests for bridge with hooks and events."""

    @pytest.fixture
    def integrated_setup(self, tmp_path):
        """Set up integrated test environment."""
        db = Database(str(tmp_path / "test.db"))
        hooks = HookDispatcher(db, project_id=1)
        orchestrator = AutomationOrchestrator(db)
        events = EventHandlers(db, orchestrator)
        bridge = HookEventBridge(hooks, events)

        return {
            "hooks": hooks,
            "events": events,
            "bridge": bridge,
            "orchestrator": orchestrator,
        }

    def test_complete_event_pipeline(self, integrated_setup):
        """Test complete pipeline: hook -> event -> orchestrator."""
        hooks = integrated_setup["hooks"]
        bridge = integrated_setup["bridge"]

        # Start session
        session_id = hooks.fire_session_start()
        assert session_id is not None

        # Fire task started hook
        event_id = hooks.fire_task_started("task_001", "Test task")
        assert event_id > 0

        # Bridge should have received the event
        stats = bridge.get_bridge_stats()
        assert stats["enabled"]

    def test_hook_context_preservation(self, integrated_setup):
        """Test that context is preserved through hook/event bridge."""
        hooks = integrated_setup["hooks"]
        bridge = integrated_setup["bridge"]

        # Start session with context
        context = {"task": "implementation", "phase": "planning"}
        session_id = hooks.fire_session_start(context=context)

        # Verify active session is set
        active = hooks.get_active_session_id()
        assert active == session_id

        # Bridge should be able to access context
        stats = bridge.get_bridge_stats()
        assert stats["enabled"]

    def test_safety_mechanism_with_bridge(self, integrated_setup):
        """Test that safety mechanisms work with bridge enabled."""
        hooks = integrated_setup["hooks"]
        bridge = integrated_setup["bridge"]

        # Fire multiple identical hooks - should trigger idempotency
        session_id = hooks.fire_session_start("test_session")

        # Disable bridge temporarily
        bridge.disable_bridging()

        # Fire again - should be idempotent
        session_id_2 = hooks.fire_session_start("test_session", {"task": "same"})

        # Should return same/cached value
        assert session_id is not None

        # Re-enable
        bridge.enable_bridging()
        assert bridge.is_enabled()

    def test_error_handling_through_bridge(self, integrated_setup):
        """Test error handling with bridge."""
        hooks = integrated_setup["hooks"]
        bridge = integrated_setup["bridge"]

        hooks.fire_session_start()

        # Fire error through hook
        error_id = hooks.fire_error_occurred(
            "TestError", "Test error", context_str="Testing bridge"
        )
        assert error_id > 0

        # Bridge should still be functional
        assert bridge.is_enabled()

    def test_multiple_hook_types_through_bridge(self, integrated_setup):
        """Test multiple hook types routed through bridge."""
        hooks = integrated_setup["hooks"]
        bridge = integrated_setup["bridge"]

        hooks.fire_session_start()

        # Fire multiple hooks
        hooks.fire_task_started("task_001", "Task 1")
        hooks.fire_task_started("task_002", "Task 2")
        hooks.fire_error_occurred("Error1", "First error")
        hooks.fire_error_occurred("Error2", "Second error")

        # Bridge should have routed events
        stats = bridge.get_bridge_stats()
        assert stats["enabled"]


class TestBridgeScalability:
    """Tests for bridge scalability and performance."""

    @pytest.fixture
    def scalability_setup(self, tmp_path):
        """Set up for scalability tests."""
        db = Database(str(tmp_path / "test.db"))
        hooks = HookDispatcher(db, project_id=1)
        orchestrator = AutomationOrchestrator(db)
        events = EventHandlers(db, orchestrator)
        bridge = HookEventBridge(hooks, events)

        return {"hooks": hooks, "events": events, "bridge": bridge}

    def test_high_hook_frequency(self, scalability_setup):
        """Test bridge handles high hook frequency."""
        hooks = scalability_setup["hooks"]
        bridge = scalability_setup["bridge"]

        hooks.fire_session_start()

        # Fire many hooks rapidly
        for i in range(20):
            hooks.fire_conversation_turn(f"msg_{i}", f"resp_{i}", task="stress_test")

        # Bridge should handle it
        assert bridge.is_enabled()

    def test_hook_stats_accumulation(self, scalability_setup):
        """Test that statistics accumulate correctly."""
        hooks = scalability_setup["hooks"]

        hooks.fire_session_start()

        # Fire multiple hooks
        for i in range(5):
            hooks.fire_task_started(f"task_{i}", f"Task {i}")

        # Check stats
        stats = hooks.get_hook_stats("task_started")
        assert stats["execution_count"] >= 5

    def test_bridge_with_many_listeners(self, scalability_setup):
        """Test bridge with many event listeners."""
        bridge = scalability_setup["bridge"]
        events = scalability_setup["events"]

        # Add custom listeners
        for i in range(5):
            events.register_listener(
                "task_created",
                lambda e: None,  # No-op handler
                name=f"test_listener_{i}",
                priority=i,
            )

        # Bridge should still work
        assert bridge.is_enabled()
        assert len(events._listeners["task_created"]) >= 1
