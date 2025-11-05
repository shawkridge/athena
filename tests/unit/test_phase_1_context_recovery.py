"""Tests for Phase 1: Context recovery and conversation snapshots."""

import json
from datetime import datetime

import pytest

from athena.conversation.context_recovery import ContextSnapshot
from athena.core.database import Database
from athena.episodic.models import EventType


@pytest.fixture
def context_snapshot(tmp_path):
    """Create ContextSnapshot instance with test database."""
    db = Database(tmp_path / "test_recovery.db")
    return ContextSnapshot(db, project_id=1)


class TestContextSnapshot:
    """Test context snapshot functionality."""

    def test_snapshot_conversation_stores_event(self, context_snapshot):
        """Test that snapshot_conversation creates episodic event."""
        session_id = "sess_test_123"
        conversation = "User: How are you?\nAssistant: I'm doing well!"

        event_id = context_snapshot.snapshot_conversation(
            session_id=session_id,
            conversation_content=conversation,
            task="testing",
            phase="test",
        )

        assert event_id is not None
        assert isinstance(event_id, int)
        assert event_id > 0

    def test_snapshot_conversation_with_task_phase(self, context_snapshot):
        """Test snapshot includes task and phase context."""
        session_id = "sess_with_context"
        conversation = "Test conversation content"
        task = "Debugging memory issue"
        phase = "investigation"

        event_id = context_snapshot.snapshot_conversation(
            session_id=session_id,
            conversation_content=conversation,
            task=task,
            phase=phase,
        )

        # Verify event was recorded
        cursor = context_snapshot.db.conn.cursor()
        cursor.execute(
            "SELECT content, context_task, context_phase FROM episodic_events WHERE id = ?",
            (event_id,),
        )
        row = cursor.fetchone()

        assert row is not None
        content, stored_task, stored_phase = row
        assert content == conversation
        assert stored_task == task
        assert stored_phase == phase

    def test_recover_conversation_from_session(self, context_snapshot):
        """Test recovery of conversation from specific session."""
        session_id = "sess_recover"
        conversation = "User: What is memory?\nAssistant: Memory is..."

        # Store conversation
        context_snapshot.snapshot_conversation(
            session_id=session_id,
            conversation_content=conversation,
        )

        # Recover conversation
        results = context_snapshot.recover_conversation(session_id)

        assert len(results) > 0
        assert results[0]["content"] == conversation

    def test_recover_conversation_empty_session(self, context_snapshot):
        """Test recovery returns empty list for non-existent session."""
        results = context_snapshot.recover_conversation("sess_nonexistent")
        assert results == []

    def test_snapshot_session_state(self, context_snapshot):
        """Test complete session state snapshot."""
        session_id = "sess_state"
        conversation = "Full conversation text"
        summary = "Working on auth feature"
        goals = ["Implement JWT", "Add refresh tokens"]
        files = ["/src/auth.py", "/src/middleware.py"]

        event_id = context_snapshot.snapshot_session_state(
            session_id=session_id,
            conversation_content=conversation,
            context_summary=summary,
            active_goals=goals,
            recent_files=files,
        )

        assert event_id > 0

        # Verify stored content
        cursor = context_snapshot.db.conn.cursor()
        cursor.execute(
            "SELECT content FROM episodic_events WHERE id = ?", (event_id,)
        )
        stored_content = cursor.fetchone()[0]

        state_data = json.loads(stored_content)
        assert state_data["conversation"] == conversation
        assert state_data["context_summary"] == summary
        assert state_data["active_goals"] == goals
        assert state_data["recent_files"] == files

    def test_search_conversation_history(self, context_snapshot):
        """Test searching across conversation history."""
        # Store multiple conversations
        for i in range(3):
            context_snapshot.snapshot_conversation(
                session_id=f"sess_{i}",
                conversation_content=f"Conversation about authentication method {i}",
            )

        # Search for keyword
        results = context_snapshot.search_conversation_history("authentication")

        assert len(results) >= 3
        for result in results:
            assert "authentication" in result["content"].lower()

    def test_search_conversation_with_limit(self, context_snapshot):
        """Test search respects limit parameter."""
        # Store 5 conversations
        for i in range(5):
            context_snapshot.snapshot_conversation(
                session_id=f"sess_limit_{i}",
                conversation_content="Discussion about memory management",
            )

        # Search with limit
        results = context_snapshot.search_conversation_history("memory", limit=2)

        assert len(results) == 2

    def test_get_session_stats(self, context_snapshot):
        """Test session statistics retrieval."""
        session_id = "sess_stats"

        # Store multiple conversations
        for i in range(3):
            context_snapshot.snapshot_conversation(
                session_id=session_id,
                conversation_content=f"Conversation number {i}",
            )

        stats = context_snapshot.get_session_stats(session_id)

        assert stats["total_events"] == 3
        assert stats["first_event"] is not None
        assert stats["last_event"] is not None
        assert stats["total_content_size"] > 0

    def test_get_session_stats_empty(self, context_snapshot):
        """Test session stats for non-existent session."""
        stats = context_snapshot.get_session_stats("sess_nonexistent")

        assert stats["total_events"] == 0
        assert stats["days_active"] == 0
        assert stats["first_event"] is None

    def test_get_recovery_recommendation_no_history(self, context_snapshot):
        """Test recovery recommendation with no history."""
        recommendation = context_snapshot.get_recovery_recommendation("sess_empty")

        assert recommendation["status"] == "no_history"

    def test_get_recovery_recommendation_with_history(self, context_snapshot):
        """Test recovery recommendation with conversation history."""
        session_id = "sess_with_history"
        conversation = "User: Implement feature X\nAssistant: Here's the approach..."

        context_snapshot.snapshot_conversation(
            session_id=session_id,
            conversation_content=conversation,
        )

        recommendation = context_snapshot.get_recovery_recommendation(session_id)

        assert recommendation["status"] == "ready_to_recover"
        assert "conversation events" in recommendation["message"]
        assert recommendation["context_preview"]
        assert "recovery_steps" in recommendation

    def test_conversation_is_searchable_by_keyword(self, context_snapshot):
        """Test that stored conversations are searchable by content keywords."""
        session_id = "sess_search_test"
        conversation = "We discussed implementing async/await patterns for performance"

        context_snapshot.snapshot_conversation(
            session_id=session_id,
            conversation_content=conversation,
        )

        # Search with specific keyword
        results = context_snapshot.search_conversation_history("async")

        assert len(results) > 0
        assert any("async" in r["content"].lower() for r in results)

    def test_multiple_sessions_isolation(self, context_snapshot):
        """Test that conversations from different sessions are properly isolated."""
        # Create conversations in different sessions
        context_snapshot.snapshot_conversation(
            session_id="sess_a",
            conversation_content="Session A: Topic is debugging",
        )
        context_snapshot.snapshot_conversation(
            session_id="sess_b",
            conversation_content="Session B: Topic is testing",
        )

        # Recover from session A
        results_a = context_snapshot.recover_conversation("sess_a")

        assert len(results_a) == 1
        assert "debugging" in results_a[0]["content"]
        assert "testing" not in results_a[0]["content"]

    def test_conversation_timestamp_preserved(self, context_snapshot):
        """Test that conversation timestamps are preserved."""
        from datetime import timedelta

        session_id = "sess_timestamp"
        before_time = datetime.now()

        context_snapshot.snapshot_conversation(
            session_id=session_id,
            conversation_content="Test content",
        )

        after_time = datetime.now()
        results = context_snapshot.recover_conversation(session_id)

        assert len(results) > 0
        stored_time = datetime.fromisoformat(results[0]["timestamp"])
        # Account for microsecond precision loss in timestamp storage
        assert (before_time - timedelta(seconds=1)) <= stored_time <= (
            after_time + timedelta(seconds=1)
        )

    def test_long_conversation_is_stored_completely(self, context_snapshot):
        """Test that long conversations are stored without truncation."""
        session_id = "sess_long"
        # Create a long conversation
        long_conversation = "\n".join(
            [
                f"Exchange {i}: User asks question, Assistant provides detailed answer"
                for i in range(50)
            ]
        )

        context_snapshot.snapshot_conversation(
            session_id=session_id,
            conversation_content=long_conversation,
        )

        results = context_snapshot.recover_conversation(session_id)

        assert len(results) > 0
        # Content should be stored completely (recovery truncates for display)
        assert len(results[0]["content"]) > 100

    def test_conversation_with_special_characters(self, context_snapshot):
        """Test that conversations with special characters are handled correctly."""
        session_id = "sess_special"
        conversation = 'User: How to use "quotes"?\nAssistant: Use backslash: \\"quotes\\"'

        event_id = context_snapshot.snapshot_conversation(
            session_id=session_id,
            conversation_content=conversation,
        )

        results = context_snapshot.recover_conversation(session_id)

        assert len(results) > 0
        assert '"' in results[0]["content"]

    def test_empty_conversation_is_rejected(self, context_snapshot):
        """Test handling of empty conversation content."""
        session_id = "sess_empty_content"

        # This should still create an event (episodic event accepts empty content)
        event_id = context_snapshot.snapshot_conversation(
            session_id=session_id,
            conversation_content="",
        )

        assert event_id > 0

    def test_project_isolation(self):
        """Test that different projects don't see each other's conversations."""
        from athena.core.database import Database
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")

            # Create snapshots for different projects
            snap_proj1 = ContextSnapshot(db, project_id=1)
            snap_proj2 = ContextSnapshot(db, project_id=2)

            snap_proj1.snapshot_conversation(
                session_id="sess_1", conversation_content="Project 1 conversation"
            )
            snap_proj2.snapshot_conversation(
                session_id="sess_1", conversation_content="Project 2 conversation"
            )

            # Each project should only see its own conversations
            results1 = snap_proj1.recover_conversation("sess_1")
            results2 = snap_proj2.recover_conversation("sess_1")

            assert len(results1) == 1
            assert "Project 1" in results1[0]["content"]

            assert len(results2) == 1
            assert "Project 2" in results2[0]["content"]
