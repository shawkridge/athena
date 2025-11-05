"""Unit tests for Phase 7.1: Event Forwarding

Tests conversion of AI Coordination events to Memory-MCP format,
forwarding to episodic layer, and tracking of forwarded events.
"""

import json
import pytest
from datetime import datetime

from athena.core.database import Database
from athena.episodic.store import EpisodicStore
from athena.ai_coordination.execution_traces import ExecutionTrace, ExecutionError, ExecutionLesson, ExecutionOutcome
from athena.ai_coordination.thinking_traces import ThinkingTrace
from athena.ai_coordination.action_cycles import ActionCycle
from athena.ai_coordination.project_context import ProjectContext


class TestEventForwarderStore:
    """Test EventForwarderStore database operations"""

    def test_create_forwarding_log(self, tmp_path):
        """Test creating a forwarding log entry"""
        from athena.ai_coordination.integration.event_forwarder_store import EventForwarderStore

        db = Database(tmp_path / "test.db")
        store = EventForwarderStore(db)

        log_id = store.log_forwarding(
            source_type="ExecutionTrace",
            source_id="exec_1",
            target_type="EpisodicEvent",
            target_id="event_123",
            metadata={"goal_id": "goal_1"}
        )

        assert log_id is not None
        assert isinstance(log_id, int)

    def test_get_forwarding_status(self, tmp_path):
        """Test retrieving forwarding status"""
        from athena.ai_coordination.integration.event_forwarder_store import EventForwarderStore

        db = Database(tmp_path / "test.db")
        store = EventForwarderStore(db)

        # Log multiple forwards
        store.log_forwarding("ExecutionTrace", "exec_1", "EpisodicEvent", "event_1")
        store.log_forwarding("ExecutionTrace", "exec_2", "EpisodicEvent", "event_2")
        store.log_forwarding("ThinkingTrace", "think_1", "EpisodicEvent", "event_3")

        # Get status
        status = store.get_forwarding_status()

        assert status.total_forwarded == 3
        assert status.by_source_type["ExecutionTrace"] == 2
        assert status.by_source_type["ThinkingTrace"] == 1

    def test_get_forwarding_log_by_source(self, tmp_path):
        """Test retrieving forwarding log entries by source"""
        from athena.ai_coordination.integration.event_forwarder_store import EventForwarderStore

        db = Database(tmp_path / "test.db")
        store = EventForwarderStore(db)

        store.log_forwarding("ExecutionTrace", "exec_1", "EpisodicEvent", "event_1")
        store.log_forwarding("ExecutionTrace", "exec_2", "EpisodicEvent", "event_2")

        logs = store.get_forwarding_log_by_source("ExecutionTrace", "exec_1")

        assert len(logs) > 0
        assert logs[0]["source_id"] == "exec_1"

    def test_mark_forwarding_complete(self, tmp_path):
        """Test marking a forward as complete"""
        from athena.ai_coordination.integration.event_forwarder_store import EventForwarderStore

        db = Database(tmp_path / "test.db")
        store = EventForwarderStore(db)

        log_id = store.log_forwarding("ExecutionTrace", "exec_1", "EpisodicEvent", "event_1")
        store.mark_forwarding_complete(log_id)

        logs = store.get_all_forwarding_logs()
        assert logs[0]["status"] == "complete"

    def test_get_all_forwarding_logs(self, tmp_path):
        """Test retrieving all forwarding logs"""
        from athena.ai_coordination.integration.event_forwarder_store import EventForwarderStore

        db = Database(tmp_path / "test.db")
        store = EventForwarderStore(db)

        # Log multiple forwards
        for i in range(5):
            store.log_forwarding(
                f"Type{i}", f"source_{i}", "EpisodicEvent", f"event_{i}"
            )

        logs = store.get_all_forwarding_logs(limit=10)
        assert len(logs) == 5

    def test_get_forwarding_by_target(self, tmp_path):
        """Test retrieving forwarding entry by target"""
        from athena.ai_coordination.integration.event_forwarder_store import EventForwarderStore

        db = Database(tmp_path / "test.db")
        store = EventForwarderStore(db)

        store.log_forwarding("ExecutionTrace", "exec_1", "EpisodicEvent", "event_1")

        log = store.get_forwarding_by_target("EpisodicEvent", "event_1")

        assert log is not None
        assert log["source_id"] == "exec_1"

    def test_get_forwarding_stats(self, tmp_path):
        """Test retrieving forwarding statistics"""
        from athena.ai_coordination.integration.event_forwarder_store import EventForwarderStore

        db = Database(tmp_path / "test.db")
        store = EventForwarderStore(db)

        # Log multiple forwards
        store.log_forwarding("ExecutionTrace", "exec_1", "EpisodicEvent", "event_1")
        store.log_forwarding("ExecutionTrace", "exec_2", "EpisodicEvent", "event_2")
        store.log_forwarding("ThinkingTrace", "think_1", "EpisodicEvent", "event_3")

        stats = store.get_forwarding_stats()

        assert "ExecutionTrace" in stats
        assert stats["ExecutionTrace"]["count"] == 2
        assert stats["ThinkingTrace"]["count"] == 1

    def test_mark_forwarding_failed(self, tmp_path):
        """Test marking a forward as failed"""
        from athena.ai_coordination.integration.event_forwarder_store import EventForwarderStore

        db = Database(tmp_path / "test.db")
        store = EventForwarderStore(db)

        log_id = store.log_forwarding("ExecutionTrace", "exec_1", "EpisodicEvent", "event_1")
        store.mark_forwarding_failed(log_id, "Connection timeout")

        logs = store.get_all_forwarding_logs()
        assert logs[0]["status"] == "failed"


class TestEventForwarder:
    """Test EventForwarder conversion logic"""

    def test_event_forwarder_creation(self, tmp_path):
        """Test creating an EventForwarder"""
        from athena.ai_coordination.integration.event_forwarder import EventForwarder

        db = Database(tmp_path / "test.db")
        episodic_store = EpisodicStore(db)

        forwarder = EventForwarder(db, episodic_store)

        assert forwarder is not None
        assert forwarder.db is not None
        assert forwarder.episodic is not None

    def test_forward_execution_trace(self, tmp_path):
        """Test forwarding a simple execution trace"""
        from athena.ai_coordination.integration.event_forwarder import EventForwarder

        db = Database(tmp_path / "test.db")
        episodic_store = EpisodicStore(db)

        forwarder = EventForwarder(db, episodic_store)

        # Create a simple execution trace
        trace = ExecutionTrace(
            goal_id="goal_1",
            session_id="session_1",
            action_type="testing",
            description="Test execution",
            outcome=ExecutionOutcome.SUCCESS,
            duration_seconds=42,
            timestamp=datetime.now()
        )

        # Forward it
        event_id = forwarder.forward_execution_trace(trace)

        assert event_id is not None

    def test_forward_with_errors(self, tmp_path):
        """Test forwarding execution trace with errors"""
        from athena.ai_coordination.integration.event_forwarder import EventForwarder

        db = Database(tmp_path / "test.db")
        episodic_store = EpisodicStore(db)

        forwarder = EventForwarder(db, episodic_store)

        trace = ExecutionTrace(
            goal_id="goal_1",
            session_id="session_1",
            action_type="testing",
            description="Test with errors",
            outcome=ExecutionOutcome.FAILURE,
            duration_seconds=120,
            errors=[ExecutionError(error_type="ValueError", message="Invalid input")],
            timestamp=datetime.now()
        )

        event_id = forwarder.forward_execution_trace(trace)

        assert event_id is not None

    def test_forward_with_lessons(self, tmp_path):
        """Test forwarding execution with lessons learned"""
        from athena.ai_coordination.integration.event_forwarder import EventForwarder

        db = Database(tmp_path / "test.db")
        episodic_store = EpisodicStore(db)

        forwarder = EventForwarder(db, episodic_store)

        trace = ExecutionTrace(
            goal_id="goal_1",
            session_id="session_1",
            action_type="testing",
            description="Test with lessons",
            outcome=ExecutionOutcome.SUCCESS,
            duration_seconds=50,
            lessons=[ExecutionLesson(lesson="This approach works", confidence=0.9)],
            timestamp=datetime.now()
        )

        event_id = forwarder.forward_execution_trace(trace)

        assert event_id is not None

    def test_get_forwarding_status(self, tmp_path):
        """Test getting forwarding status"""
        from athena.ai_coordination.integration.event_forwarder import EventForwarder
        from athena.ai_coordination.integration.event_forwarder_store import EventForwarderStore

        db = Database(tmp_path / "test.db")
        episodic_store = EpisodicStore(db)
        store = EventForwarderStore(db)

        forwarder = EventForwarder(db, episodic_store, store)

        trace = ExecutionTrace(
            goal_id="goal_1",
            session_id="session_1",
            action_type="testing",
            description="Status test",
            outcome=ExecutionOutcome.SUCCESS,
            duration_seconds=30,
            timestamp=datetime.now()
        )

        forwarder.forward_execution_trace(trace)

        status = forwarder.get_forwarding_status()

        assert status is not None
        assert status["total_forwarded"] >= 1


class TestPhase7Integration:
    """Integration tests for Phase 7.1"""

    def test_full_forwarding_cycle(self, tmp_path):
        """Test complete cycle: create trace → forward → verify"""
        from athena.ai_coordination.integration.event_forwarder import EventForwarder
        from athena.ai_coordination.integration.event_forwarder_store import EventForwarderStore

        db = Database(tmp_path / "test.db")
        episodic_store = EpisodicStore(db)
        store = EventForwarderStore(db)

        forwarder = EventForwarder(db, episodic_store, store)

        # Create execution trace
        trace = ExecutionTrace(
            goal_id="goal_1",
            session_id="session_1",
            action_type="testing",
            description="Full cycle test",
            outcome=ExecutionOutcome.SUCCESS,
            duration_seconds=42,
            lessons=[ExecutionLesson(lesson="Test lesson", confidence=0.8)],
            timestamp=datetime.now()
        )

        # Forward it
        event_id = forwarder.forward_execution_trace(trace)

        assert event_id is not None

        # Verify in forwarding log
        status = store.get_forwarding_status()
        assert status.total_forwarded >= 1

    def test_multiple_forwards(self, tmp_path):
        """Test forwarding multiple traces"""
        from athena.ai_coordination.integration.event_forwarder import EventForwarder

        db = Database(tmp_path / "test.db")
        episodic_store = EpisodicStore(db)

        forwarder = EventForwarder(db, episodic_store)

        # Forward multiple traces
        for i in range(5):
            trace = ExecutionTrace(
                goal_id=f"goal_{i}",
                session_id="session_1",
                action_type="testing",
                description=f"Test {i}",
                outcome=ExecutionOutcome.SUCCESS if i % 2 == 0 else ExecutionOutcome.FAILURE,
                duration_seconds=10 + i,
                timestamp=datetime.now()
            )
            forwarder.forward_execution_trace(trace)

        # Verify all forwarded - get events by session since we know it's "session_1"
        from athena.episodic.models import EventType

        events = episodic_store.get_events_by_session("session_1")
        assert len(events) >= 5
        # Verify they're action events
        assert all(e.event_type == EventType.ACTION for e in events)

    def test_forwarding_preserves_metadata(self, tmp_path):
        """Test that forwarding preserves important metadata"""
        from athena.ai_coordination.integration.event_forwarder import EventForwarder

        db = Database(tmp_path / "test.db")
        episodic_store = EpisodicStore(db)

        forwarder = EventForwarder(db, episodic_store)

        trace = ExecutionTrace(
            goal_id="goal_1",
            session_id="session_1",
            action_type="testing",
            description="Metadata test",
            outcome=ExecutionOutcome.SUCCESS,
            duration_seconds=42,
            timestamp=datetime.now()
        )

        event_id = forwarder.forward_execution_trace(trace)
        event = episodic_store.get_event(event_id)

        # Verify metadata preserved in content
        assert event is not None
        assert "goal_1" in event.content or event.session_id == "session_1"

    def test_forwarding_handles_none_values(self, tmp_path):
        """Test that forwarding handles None values gracefully"""
        from athena.ai_coordination.integration.event_forwarder import EventForwarder

        db = Database(tmp_path / "test.db")
        episodic_store = EpisodicStore(db)

        forwarder = EventForwarder(db, episodic_store)

        # Create trace with minimal fields
        trace = ExecutionTrace(
            goal_id=None,
            session_id="session_1",
            action_type="testing",
            description="None test",
            outcome=ExecutionOutcome.SUCCESS,
            duration_seconds=42,
            timestamp=datetime.now()
        )

        # Should not raise
        try:
            event_id = forwarder.forward_execution_trace(trace)
            assert event_id is not None
        except Exception as e:
            pytest.fail(f"Forwarding should handle None values: {e}")

    def test_project_context_forward(self, tmp_path):
        """Test forwarding project context"""
        from athena.ai_coordination.integration.event_forwarder import EventForwarder

        db = Database(tmp_path / "test.db")
        episodic_store = EpisodicStore(db)

        forwarder = EventForwarder(db, episodic_store)

        from athena.ai_coordination.project_context import ProjectPhase

        context = ProjectContext(
            project_id="proj_1",
            name="Test Project",
            description="Test project for Phase 7.1",
            current_phase=ProjectPhase.FEATURE_DEVELOPMENT,
            completed_goal_count=3,
            in_progress_goal_count=2,
            blocked_goal_count=1
        )

        event_id = forwarder.forward_project_context(context)

        assert event_id is not None

    def test_schema_creates_correctly(self, tmp_path):
        """Test that database schema is created correctly"""
        from athena.ai_coordination.integration.event_forwarder_store import EventForwarderStore

        db = Database(tmp_path / "test.db")
        store = EventForwarderStore(db)

        # Check that tables exist
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name LIKE 'forwarding%'
        """)

        tables = [row[0] for row in cursor.fetchall()]
        assert "forwarding_log" in tables
        assert "forwarding_stats" in tables

    def test_forwarding_log_indexing(self, tmp_path):
        """Test that forwarding log has proper indexes"""
        from athena.ai_coordination.integration.event_forwarder_store import EventForwarderStore

        db = Database(tmp_path / "test.db")
        store = EventForwarderStore(db)

        # Check that indexes exist
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND tbl_name = 'forwarding_log'
        """)

        indexes = [row[0] for row in cursor.fetchall()]
        assert "idx_forwarding_source" in indexes
        assert "idx_forwarding_target" in indexes
        assert "idx_forwarding_time" in indexes
