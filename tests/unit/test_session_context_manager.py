"""Tests for SessionContextManager."""

import pytest
from datetime import datetime
from pathlib import Path

from athena.core.database import Database
from athena.session.context_manager import SessionContext, SessionContextManager


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Create test database."""
    db_path = tmp_path / "test.db"
    return Database(str(db_path))


@pytest.fixture
def session_manager(db: Database) -> SessionContextManager:
    """Create session context manager."""
    return SessionContextManager(db)


class TestSessionContext:
    """Tests for SessionContext dataclass."""

    def test_create_session_context(self):
        """Test creating a session context."""
        ctx = SessionContext(
            session_id="session_123",
            project_id=1,
            current_task="Debug failing test",
            current_phase="debugging",
        )

        assert ctx.session_id == "session_123"
        assert ctx.project_id == 1
        assert ctx.current_task == "Debug failing test"
        assert ctx.current_phase == "debugging"
        assert ctx.is_active()
        assert ctx.ended_at is None

    def test_session_context_to_dict(self):
        """Test converting session context to dict."""
        ctx = SessionContext(
            session_id="session_123",
            project_id=1,
            current_task="Test task",
            current_phase="testing",
        )

        data = ctx.to_dict()

        assert data["session_id"] == "session_123"
        assert data["project_id"] == 1
        assert data["current_task"] == "Test task"
        assert data["current_phase"] == "testing"
        assert isinstance(data["started_at"], str)
        assert data["ended_at"] is None

    def test_session_context_is_active(self):
        """Test checking if session is active."""
        ctx = SessionContext(
            session_id="session_123",
            project_id=1,
        )

        assert ctx.is_active()

        ctx.ended_at = datetime.now()
        assert not ctx.is_active()


class TestSessionContextManagerBasics:
    """Basic functionality tests for SessionContextManager."""

    def test_init_creates_tables(self, db: Database):
        """Test that initialization creates required tables."""
        manager = SessionContextManager(db)

        # Check tables exist
        cursor = db.get_cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='session_contexts'"
        )
        assert cursor.fetchone() is not None

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='session_context_events'"
        )
        assert cursor.fetchone() is not None

    def test_init_with_none_database_raises_error(self):
        """Test that None database raises ValueError."""
        with pytest.raises(ValueError):
            SessionContextManager(None)

    def test_start_session(self, session_manager: SessionContextManager):
        """Test starting a session."""
        ctx = session_manager.start_session(
            session_id="session_abc123",
            project_id=1,
            task="Debug failing test",
            phase="debugging",
        )

        assert ctx.session_id == "session_abc123"
        assert ctx.project_id == 1
        assert ctx.current_task == "Debug failing test"
        assert ctx.current_phase == "debugging"
        assert ctx.is_active()

    def test_start_session_missing_id_raises_error(
        self, session_manager: SessionContextManager
    ):
        """Test that missing session_id raises ValueError."""
        with pytest.raises(ValueError):
            session_manager.start_session(
                session_id=None,
                project_id=1,
            )

    def test_start_session_missing_project_id_raises_error(
        self, session_manager: SessionContextManager
    ):
        """Test that missing project_id raises ValueError."""
        with pytest.raises(ValueError):
            session_manager.start_session(
                session_id="session_123",
                project_id=None,
            )

    def test_get_current_session(self, session_manager: SessionContextManager):
        """Test getting current session."""
        assert session_manager.get_current_session() is None

        session_manager.start_session(
            session_id="session_123",
            project_id=1,
        )

        ctx = session_manager.get_current_session()
        assert ctx is not None
        assert ctx.session_id == "session_123"

    def test_end_session(self, session_manager: SessionContextManager):
        """Test ending a session."""
        session_manager.start_session(
            session_id="session_123",
            project_id=1,
        )

        success = session_manager.end_session("session_123")
        assert success is True

        ctx = session_manager.get_current_session()
        assert ctx.ended_at is not None
        assert not ctx.is_active()

    def test_end_session_with_no_active_session(
        self, session_manager: SessionContextManager
    ):
        """Test ending session when no session is active."""
        success = session_manager.end_session(None)
        assert success is False

    def test_end_session_uses_current_session(
        self, session_manager: SessionContextManager
    ):
        """Test that end_session uses current session if no ID provided."""
        session_manager.start_session(
            session_id="session_123",
            project_id=1,
        )

        success = session_manager.end_session()
        assert success is True


class TestSessionContextManagerEvents:
    """Tests for event recording."""

    def test_record_event(self, session_manager: SessionContextManager):
        """Test recording an event."""
        session_manager.start_session(
            session_id="session_123",
            project_id=1,
        )

        event_id = session_manager.record_event(
            session_id="session_123",
            event_type="conversation_turn",
            event_data={"turn_number": 1, "content": "Hello"},
        )

        assert event_id > 0

    def test_record_event_missing_session_id_raises_error(
        self, session_manager: SessionContextManager
    ):
        """Test that missing session_id raises ValueError."""
        with pytest.raises(ValueError):
            session_manager.record_event(
                session_id=None,
                event_type="conversation_turn",
                event_data={},
            )

    def test_record_event_missing_event_type_raises_error(
        self, session_manager: SessionContextManager
    ):
        """Test that missing event_type raises ValueError."""
        session_manager.start_session(
            session_id="session_123",
            project_id=1,
        )

        with pytest.raises(ValueError):
            session_manager.record_event(
                session_id="session_123",
                event_type=None,
                event_data={},
            )

    def test_record_consolidation(self, session_manager: SessionContextManager):
        """Test recording a consolidation event."""
        session_manager.start_session(
            session_id="session_123",
            project_id=1,
        )

        session_manager.record_consolidation(
            project_id=1,
            consolidation_type="CAPACITY",
            wm_size=7,
            consolidation_run_id=42,
            trigger_type="CAPACITY",
        )

        # Check event was recorded
        ctx = session_manager.get_current_session()
        assert len(ctx.consolidation_history) == 1
        assert ctx.consolidation_history[0]["consolidation_run_id"] == 42

    def test_record_consolidation_no_active_session(
        self, session_manager: SessionContextManager
    ):
        """Test recording consolidation with no active session."""
        # Should not raise error, just log warning
        session_manager.record_consolidation(
            project_id=1,
            consolidation_type="CAPACITY",
            wm_size=7,
        )

    def test_multiple_consolidations_tracked(
        self, session_manager: SessionContextManager
    ):
        """Test tracking multiple consolidations."""
        session_manager.start_session(
            session_id="session_123",
            project_id=1,
        )

        for i in range(3):
            session_manager.record_consolidation(
                project_id=1,
                consolidation_type="CAPACITY",
                wm_size=7 + i,
                consolidation_run_id=100 + i,
            )

        ctx = session_manager.get_current_session()
        assert len(ctx.consolidation_history) == 3


class TestSessionContextManagerUpdates:
    """Tests for context updates."""

    def test_update_task(self, session_manager: SessionContextManager):
        """Test updating task."""
        session_manager.start_session(
            session_id="session_123",
            project_id=1,
            task="Original task",
        )

        session_manager.update_context(task="New task")

        ctx = session_manager.get_current_session()
        assert ctx.current_task == "New task"

    def test_update_phase(self, session_manager: SessionContextManager):
        """Test updating phase."""
        session_manager.start_session(
            session_id="session_123",
            project_id=1,
            phase="debugging",
        )

        session_manager.update_context(phase="refactoring")

        ctx = session_manager.get_current_session()
        assert ctx.current_phase == "refactoring"

    def test_update_task_and_phase(self, session_manager: SessionContextManager):
        """Test updating both task and phase."""
        session_manager.start_session(
            session_id="session_123",
            project_id=1,
            task="Task 1",
            phase="phase1",
        )

        session_manager.update_context(task="Task 2", phase="phase2")

        ctx = session_manager.get_current_session()
        assert ctx.current_task == "Task 2"
        assert ctx.current_phase == "phase2"

    def test_update_context_no_active_session(
        self, session_manager: SessionContextManager
    ):
        """Test updating context with no active session."""
        # Should not raise error, just log warning
        session_manager.update_context(task="New task")


class TestSessionContextManagerRecovery:
    """Tests for context recovery."""

    def test_recover_context(self, session_manager: SessionContextManager):
        """Test recovering context."""
        session_manager.start_session(
            session_id="session_123",
            project_id=1,
            task="Debug test",
        )

        recovered = session_manager.recover_context()

        assert recovered is not None
        assert recovered.session_id == "session_123"
        assert recovered.current_task == "Debug test"

    def test_recover_context_no_active_session(
        self, session_manager: SessionContextManager
    ):
        """Test recovering when no session is active."""
        recovered = session_manager.recover_context()
        assert recovered is None

    def test_recover_context_with_patterns(
        self, session_manager: SessionContextManager
    ):
        """Test recovering context with patterns."""
        session_manager.start_session(
            session_id="session_123",
            project_id=1,
        )

        recovered = session_manager.recover_context(
            recovery_patterns=["task", "phase"],
            source="episodic_memory",
        )

        assert recovered is not None


class TestSessionContextManagerQueryIntegration:
    """Tests for query integration."""

    def test_get_context_for_query(self, session_manager: SessionContextManager):
        """Test getting context formatted for queries."""
        session_manager.start_session(
            session_id="session_123",
            project_id=1,
            task="Debug test",
            phase="debugging",
        )

        query_context = session_manager.get_context_for_query()

        assert query_context["session_id"] == "session_123"
        assert query_context["task"] == "Debug test"
        assert query_context["phase"] == "debugging"
        assert "recent_events" in query_context
        assert "consolidation_count" in query_context

    def test_get_context_for_query_no_session(
        self, session_manager: SessionContextManager
    ):
        """Test getting context when no session is active."""
        query_context = session_manager.get_context_for_query()
        assert query_context == {}

    def test_context_consolidation_count(self, session_manager: SessionContextManager):
        """Test that context includes consolidation count."""
        session_manager.start_session(
            session_id="session_123",
            project_id=1,
        )

        session_manager.record_consolidation(project_id=1)
        session_manager.record_consolidation(project_id=1)

        query_context = session_manager.get_context_for_query()
        assert query_context["consolidation_count"] == 2


class TestSessionContextManagerAsync:
    """Tests for async methods."""

    @pytest.mark.asyncio
    async def test_start_session_async(self, session_manager: SessionContextManager):
        """Test async start_session."""
        ctx = await session_manager.start_session_async(
            session_id="session_123",
            project_id=1,
            task="Test",
            phase="testing",
        )

        assert ctx.session_id == "session_123"
        assert ctx.current_task == "Test"

    @pytest.mark.asyncio
    async def test_end_session_async(self, session_manager: SessionContextManager):
        """Test async end_session."""
        await session_manager.start_session_async(
            session_id="session_123",
            project_id=1,
        )

        success = await session_manager.end_session_async("session_123")
        assert success is True

    @pytest.mark.asyncio
    async def test_record_event_async(self, session_manager: SessionContextManager):
        """Test async record_event."""
        await session_manager.start_session_async(
            session_id="session_123",
            project_id=1,
        )

        event_id = await session_manager.record_event_async(
            session_id="session_123",
            event_type="test_event",
            event_data={"key": "value"},
        )

        assert event_id > 0

    @pytest.mark.asyncio
    async def test_update_context_async(self, session_manager: SessionContextManager):
        """Test async update_context."""
        await session_manager.start_session_async(
            session_id="session_123",
            project_id=1,
            phase="phase1",
        )

        await session_manager.update_context_async(phase="phase2")

        ctx = session_manager.get_current_session()
        assert ctx.current_phase == "phase2"


class TestSessionContextManagerIntegration:
    """Integration tests."""

    def test_full_session_lifecycle(self, session_manager: SessionContextManager):
        """Test complete session lifecycle."""
        # Start session
        session_manager.start_session(
            session_id="session_full",
            project_id=1,
            task="Debug failing test",
            phase="debugging",
        )

        # Record events
        session_manager.record_event(
            session_id="session_full",
            event_type="conversation_turn",
            event_data={"turn": 1},
        )

        # Update context
        session_manager.update_context(phase="refactoring")

        # Record consolidation
        session_manager.record_consolidation(
            project_id=1,
            consolidation_type="CAPACITY",
            wm_size=8,
        )

        # Get context for query
        query_ctx = session_manager.get_context_for_query()
        assert query_ctx["task"] == "Debug failing test"
        assert query_ctx["phase"] == "refactoring"
        assert query_ctx["consolidation_count"] == 1

        # End session
        session_manager.end_session()

        ctx = session_manager.get_current_session()
        assert not ctx.is_active()

    def test_multiple_sessions_isolation(self, session_manager: SessionContextManager):
        """Test that sessions are properly isolated."""
        # Start and end first session
        session_manager.start_session(
            session_id="session_1",
            project_id=1,
            task="Task 1",
        )
        session_manager.record_consolidation(project_id=1)
        session_manager.end_session("session_1")

        # Start second session
        session_manager.start_session(
            session_id="session_2",
            project_id=1,
            task="Task 2",
        )

        # Second session should have no consolidations
        ctx = session_manager.get_current_session()
        assert len(ctx.consolidation_history) == 0
        assert ctx.current_task == "Task 2"
