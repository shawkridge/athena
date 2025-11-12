"""Phase 3 Integration Tests: HookDispatcher ↔ SessionContextManager Integration.

Tests the bidirectional integration between hooks and session context tracking:
- Session lifecycle hooks trigger session context creation/end
- Conversation hooks record turn events in session context
- Consolidation hooks record consolidation metrics
- Session context auto-loads in memory queries
"""

import pytest
from datetime import datetime
from pathlib import Path

from athena.core.database import Database
from athena.hooks.dispatcher import HookDispatcher
from athena.session.context_manager import SessionContextManager
from athena.episodic.store import EpisodicStore
from athena.memory.store import MemoryStore


@pytest.fixture
def db(tmp_path):
    """Create temporary test database."""
    db_path = tmp_path / "test_hook_session.db"
    return Database(str(db_path))


@pytest.fixture
def session_manager(db):
    """Create SessionContextManager."""
    return SessionContextManager(db)


@pytest.fixture
def hook_dispatcher(db, session_manager):
    """Create HookDispatcher with SessionContextManager integration."""
    return HookDispatcher(db, project_id=1, session_manager=session_manager)


class TestHookSessionStartIntegration:
    """Test fire_session_start() ↔ session_manager.start_session() flow."""

    def test_session_start_creates_session_context(self, hook_dispatcher, session_manager):
        """fire_session_start() should auto-create session context."""
        session_id = hook_dispatcher.fire_session_start(
            session_id="test_session",
            context={"task": "Debug issue", "phase": "debugging"}
        )

        assert session_id == "test_session"

        # Verify session context was created
        ctx = session_manager.get_current_session()
        assert ctx is not None
        assert ctx.session_id == "test_session"
        assert ctx.current_task == "Debug issue"
        assert ctx.current_phase == "debugging"

    def test_session_start_without_context(self, hook_dispatcher, session_manager):
        """fire_session_start() should work without explicit context."""
        session_id = hook_dispatcher.fire_session_start()

        assert session_id is not None

        # Verify session context was created
        ctx = session_manager.get_current_session()
        assert ctx is not None
        assert ctx.session_id == session_id

    def test_session_start_with_none_manager(self, db):
        """HookDispatcher should work with None session_manager (graceful degradation)."""
        dispatcher = HookDispatcher(db, project_id=1, session_manager=None)
        session_id = dispatcher.fire_session_start(session_id="test")
        assert session_id == "test"

    def test_session_context_has_task_and_phase(self, hook_dispatcher, session_manager):
        """Session context should capture task and phase from hook context."""
        task = "Implement feature X"
        phase = "implementation"

        hook_dispatcher.fire_session_start(
            session_id="feat_session",
            context={"task": task, "phase": phase}
        )

        ctx = session_manager.get_current_session()
        assert ctx.current_task == task
        assert ctx.current_phase == phase


class TestHookSessionEndIntegration:
    """Test fire_session_end() ↔ session_manager.end_session() flow."""

    def test_session_end_closes_session_context(self, hook_dispatcher, session_manager):
        """fire_session_end() should auto-close session context."""
        # Start session first
        session_id = hook_dispatcher.fire_session_start(session_id="end_test")
        assert session_manager.get_current_session() is not None

        # End session
        success = hook_dispatcher.fire_session_end(session_id)
        assert success is True

        # Verify session context was closed
        ctx = session_manager.get_current_session()
        assert ctx is None or ctx.ended_at is not None

    def test_session_end_with_active_session(self, hook_dispatcher, session_manager):
        """fire_session_end() should end the active session if session_id not provided."""
        # Start session
        session_id = hook_dispatcher.fire_session_start(session_id="active_end_test")

        # End without specifying ID (uses active)
        success = hook_dispatcher.fire_session_end()
        assert success is True

    def test_session_end_without_active_session(self, hook_dispatcher):
        """fire_session_end() should handle case with no active session gracefully."""
        # No active session, no ID provided
        success = hook_dispatcher.fire_session_end()
        assert success is False


class TestHookConversationTurnIntegration:
    """Test fire_conversation_turn() ↔ session_manager.record_event() flow."""

    def test_conversation_turn_records_session_event(self, hook_dispatcher, session_manager):
        """fire_conversation_turn() should record event in session context."""
        # Start session
        hook_dispatcher.fire_session_start(session_id="conv_test")

        # Record conversation turn
        turn_id = hook_dispatcher.fire_conversation_turn(
            user_content="What's 2+2?",
            assistant_content="2+2 equals 4",
            duration_ms=150,
            user_tokens=5,
            assistant_tokens=6,
            task="Math lesson",
            phase="active_learning"
        )

        assert turn_id > 0

        # Verify event was recorded in session context
        ctx = session_manager.get_current_session()
        assert ctx is not None
        assert len(ctx.recent_events) > 0

        # Find conversation_turn event
        turn_events = [e for e in ctx.recent_events if e.get("event_type") == "conversation_turn"]
        assert len(turn_events) > 0

        event = turn_events[0]
        assert event["event_data"]["turn_number"] == 1
        assert event["event_data"]["user_tokens"] == 5
        assert event["event_data"]["assistant_tokens"] == 6
        assert event["event_data"]["duration_ms"] == 150

    def test_conversation_turn_auto_starts_session(self, hook_dispatcher, session_manager):
        """fire_conversation_turn() should auto-start session if not active."""
        # No active session
        ctx_before = session_manager.get_current_session()
        assert ctx_before is None

        # Record turn (should auto-start)
        turn_id = hook_dispatcher.fire_conversation_turn(
            user_content="Hello",
            assistant_content="Hi there!"
        )

        assert turn_id > 0

        # Verify session was auto-started
        ctx_after = session_manager.get_current_session()
        assert ctx_after is not None


class TestHookConsolidationIntegration:
    """Test fire_consolidation_complete() ↔ session_manager.record_consolidation() flow."""

    def test_consolidation_complete_records_consolidation(self, hook_dispatcher, session_manager):
        """fire_consolidation_complete() should record consolidation in session context."""
        # Start session
        hook_dispatcher.fire_session_start(session_id="consol_test")

        # Record consolidation
        event_id = hook_dispatcher.fire_consolidation_complete(
            patterns_found=15,
            consolidation_time_ms=2500,
            quality_score=0.92
        )

        assert event_id > 0

        # Verify consolidation was recorded in session context
        ctx = session_manager.get_current_session()
        assert ctx is not None
        assert len(ctx.consolidation_history) > 0

        consol = ctx.consolidation_history[0]
        assert consol.get("consolidation_type") == "SEMANTIC_SYNTHESIS"
        # wm_size is set to patterns_found
        assert consol.get("wm_size") == 15
        assert consol.get("trigger_type") == "PERIODIC"

    def test_consolidation_auto_starts_session(self, hook_dispatcher, session_manager):
        """fire_consolidation_complete() should auto-start session if not active."""
        # No active session
        ctx_before = session_manager.get_current_session()
        assert ctx_before is None

        # Record consolidation (should auto-start)
        event_id = hook_dispatcher.fire_consolidation_complete(
            patterns_found=5,
            consolidation_time_ms=1000,
            quality_score=0.85
        )

        assert event_id > 0

        # Verify session was auto-started and consolidation recorded
        ctx_after = session_manager.get_current_session()
        assert ctx_after is not None
        assert len(ctx_after.consolidation_history) > 0


class TestBidirectionalSync:
    """Test bidirectional sync between hooks and session context."""

    def test_full_session_lifecycle(self, hook_dispatcher, session_manager):
        """Test complete session lifecycle with all hook types."""
        # Start session with context
        session_id = hook_dispatcher.fire_session_start(
            session_id="full_lifecycle",
            context={"task": "Build feature", "phase": "development"}
        )

        ctx = session_manager.get_current_session()
        assert ctx.session_id == session_id
        assert ctx.current_task == "Build feature"
        assert ctx.current_phase == "development"

        # Record conversation turns
        for i in range(3):
            hook_dispatcher.fire_conversation_turn(
                user_content=f"Question {i+1}",
                assistant_content=f"Answer {i+1}",
                task="Build feature",
                phase="development"
            )

        ctx = session_manager.get_current_session()
        turn_events = [e for e in ctx.recent_events if e.get("event_type") == "conversation_turn"]
        assert len(turn_events) == 3

        # Record consolidation
        hook_dispatcher.fire_consolidation_complete(
            patterns_found=10,
            consolidation_time_ms=2000,
            quality_score=0.88
        )

        ctx = session_manager.get_current_session()
        assert len(ctx.consolidation_history) == 1

        # End session
        success = hook_dispatcher.fire_session_end()
        assert success is True

        # Verify session is no longer active
        ctx_end = session_manager.get_current_session()
        assert ctx_end is None

    def test_multiple_sequential_sessions(self, hook_dispatcher, session_manager):
        """Test multiple sequential sessions with independent contexts."""
        # Session 1
        hook_dispatcher.fire_session_start(
            session_id="session_1",
            context={"task": "Task 1", "phase": "phase_1"}
        )
        hook_dispatcher.fire_conversation_turn("Q1", "A1")

        ctx1 = session_manager.get_current_session()
        assert ctx1.session_id == "session_1"
        assert len(ctx1.recent_events) == 1

        hook_dispatcher.fire_session_end("session_1")

        # Session 2
        hook_dispatcher.fire_session_start(
            session_id="session_2",
            context={"task": "Task 2", "phase": "phase_2"}
        )

        ctx2 = session_manager.get_current_session()
        assert ctx2.session_id == "session_2"
        assert ctx2.current_task == "Task 2"
        assert len(ctx2.recent_events) == 0  # Fresh session

    def test_context_isolation_between_projects(self, db):
        """Test that session contexts are isolated per project."""
        # Create two project-specific managers
        sm1 = SessionContextManager(db)
        sm2 = SessionContextManager(db)

        hd1 = HookDispatcher(db, project_id=1, session_manager=sm1)
        hd2 = HookDispatcher(db, project_id=2, session_manager=sm2)

        # Start sessions in each project
        hd1.fire_session_start(session_id="proj1_sess", context={"task": "Project 1 task"})
        hd2.fire_session_start(session_id="proj2_sess", context={"task": "Project 2 task"})

        # Verify isolation
        ctx1 = sm1.get_current_session()
        ctx2 = sm2.get_current_session()

        assert ctx1.session_id == "proj1_sess"
        assert ctx2.session_id == "proj2_sess"
        assert ctx1.current_task == "Project 1 task"
        assert ctx2.current_task == "Project 2 task"


class TestErrorHandling:
    """Test error handling and graceful degradation."""

    def test_session_manager_failure_doesnt_break_hooks(self, db):
        """Hook dispatcher should gracefully degrade if session_manager fails."""
        # Create a broken session manager mock
        class BrokenSessionManager:
            def start_session(self, *args, **kwargs):
                raise RuntimeError("Intentional failure")

            def end_session(self, *args, **kwargs):
                raise RuntimeError("Intentional failure")

            def record_event(self, *args, **kwargs):
                raise RuntimeError("Intentional failure")

            def record_consolidation(self, *args, **kwargs):
                raise RuntimeError("Intentional failure")

        broken_sm = BrokenSessionManager()
        dispatcher = HookDispatcher(db, project_id=1, session_manager=broken_sm)

        # Hooks should still work despite session_manager failures
        session_id = dispatcher.fire_session_start(session_id="test_resilience")
        assert session_id == "test_resilience"

        # Check error was recorded but didn't crash
        assert "session_manager" in dispatcher._hook_registry["session_start"]["last_error"]

    def test_missing_session_manager_param(self, db):
        """HookDispatcher should work fine with session_manager=None."""
        dispatcher = HookDispatcher(db, project_id=1, session_manager=None)

        # All hooks should work
        session_id = dispatcher.fire_session_start(session_id="test_none")
        assert session_id == "test_none"

        turn_id = dispatcher.fire_conversation_turn("Q", "A")
        assert turn_id > 0

        consol_id = dispatcher.fire_consolidation_complete(1, 100, 0.9)
        assert consol_id > 0


class TestEventDataIntegrity:
    """Test that event data is correctly captured and stored."""

    def test_conversation_turn_event_data_completeness(self, hook_dispatcher, session_manager):
        """Verify all conversation turn data is captured."""
        hook_dispatcher.fire_session_start(session_id="data_test")

        hook_dispatcher.fire_conversation_turn(
            user_content="Complex question?",
            assistant_content="Detailed response with explanation",
            duration_ms=342,
            user_tokens=12,
            assistant_tokens=45,
            task="Research",
            phase="analysis"
        )

        ctx = session_manager.get_current_session()
        event = ctx.recent_events[0]

        assert event["event_type"] == "conversation_turn"
        assert event["event_data"]["turn_number"] == 1
        assert event["event_data"]["duration_ms"] == 342
        assert event["event_data"]["user_tokens"] == 12
        assert event["event_data"]["assistant_tokens"] == 45
        assert event["event_data"]["task"] == "Research"
        assert event["event_data"]["phase"] == "analysis"

    def test_consolidation_event_data_completeness(self, hook_dispatcher, session_manager):
        """Verify all consolidation data is captured."""
        hook_dispatcher.fire_session_start(session_id="consol_data_test")

        hook_dispatcher.fire_consolidation_complete(
            patterns_found=23,
            consolidation_time_ms=3200,
            quality_score=0.945
        )

        ctx = session_manager.get_current_session()
        consol = ctx.consolidation_history[0]

        assert consol.get("consolidation_type") == "SEMANTIC_SYNTHESIS"
        assert consol.get("wm_size") == 23
        assert consol.get("trigger_type") == "PERIODIC"
        assert "timestamp" in consol


class TestSessionContextBiasing:
    """Test that session context biases memory query routing."""

    def test_session_context_stored_for_queries(self, hook_dispatcher, session_manager):
        """Verify session context is available for query biasing."""
        hook_dispatcher.fire_session_start(
            session_id="query_bias_test",
            context={"task": "Debug test failure", "phase": "debugging"}
        )

        hook_dispatcher.fire_conversation_turn(
            user_content="What's the error?",
            assistant_content="Null pointer exception",
            task="Debug test failure",
            phase="debugging"
        )

        # Get context for query biasing
        query_ctx = session_manager.get_context_for_query()

        assert query_ctx["session_id"] == "query_bias_test"
        assert query_ctx["task"] == "Debug test failure"
        assert query_ctx["phase"] == "debugging"
        assert "recent_events" in query_ctx
        assert len(query_ctx["recent_events"]) > 0
