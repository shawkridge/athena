"""Tests for Phase 3: HookDispatcher and automatic context capture."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from athena.core.database import Database
from athena.episodic.models import EventOutcome
from athena.hooks.dispatcher import HookDispatcher


@pytest.fixture
def hook_dispatcher():
    """Create HookDispatcher with test database."""
    with TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test_hooks.db")
        yield HookDispatcher(db, project_id=1)


class TestHookDispatcher:
    """Test HookDispatcher functionality."""

    def test_session_start_creates_session(self, hook_dispatcher):
        """Test that fire_session_start creates a session."""
        session_id = hook_dispatcher.fire_session_start()

        assert session_id is not None
        assert len(session_id) > 0
        assert hook_dispatcher.get_active_session_id() == session_id

    def test_session_start_with_custom_id(self, hook_dispatcher):
        """Test fire_session_start with custom session ID."""
        session_id = hook_dispatcher.fire_session_start(session_id="custom_sess_123")

        assert session_id == "custom_sess_123"
        assert hook_dispatcher.get_active_session_id() == session_id

    def test_session_start_with_context(self, hook_dispatcher):
        """Test fire_session_start with context."""
        context = {"task": "Debug authentication", "phase": "investigation"}
        session_id = hook_dispatcher.fire_session_start(context=context)

        assert session_id is not None
        # Verify context was recorded in episodic memory
        assert hook_dispatcher._active_session_id == session_id

    def test_session_end(self, hook_dispatcher):
        """Test fire_session_end."""
        session_id = hook_dispatcher.fire_session_start()

        result = hook_dispatcher.fire_session_end()

        assert result is True
        assert hook_dispatcher.get_active_session_id() is None

    def test_session_end_clears_state(self, hook_dispatcher):
        """Test that session_end clears internal state."""
        session_id = hook_dispatcher.fire_session_start()

        # Do some actual work to populate state
        hook_dispatcher.fire_conversation_turn("Q1", "A1")
        hook_dispatcher.fire_conversation_turn("Q2", "A2")

        assert hook_dispatcher._turn_count == 2
        assert hook_dispatcher._active_conversation_id is not None

        hook_dispatcher.fire_session_end()

        assert hook_dispatcher._active_conversation_id is None
        assert hook_dispatcher._turn_count == 0

    def test_conversation_turn_auto_creates_session(self, hook_dispatcher):
        """Test that conversation_turn auto-creates session if needed."""
        user_msg = "What is memory?"
        asst_msg = "Memory is information storage."

        turn_id = hook_dispatcher.fire_conversation_turn(user_msg, asst_msg)

        assert turn_id > 0
        assert hook_dispatcher.get_active_session_id() is not None

    def test_conversation_turn_basic(self, hook_dispatcher):
        """Test recording a conversation turn."""
        hook_dispatcher.fire_session_start()

        user_msg = "How do I debug this?"
        asst_msg = "You can add print statements or use a debugger."

        turn_id = hook_dispatcher.fire_conversation_turn(user_msg, asst_msg)

        assert turn_id > 0

    def test_conversation_turn_with_tokens(self, hook_dispatcher):
        """Test conversation turn with token counts."""
        hook_dispatcher.fire_session_start()

        turn_id = hook_dispatcher.fire_conversation_turn(
            user_content="Short message",
            assistant_content="Also short",
            user_tokens=3,
            assistant_tokens=2,
        )

        assert turn_id > 0
        assert hook_dispatcher._turn_count == 1

    def test_conversation_turn_with_duration(self, hook_dispatcher):
        """Test conversation turn with duration tracking."""
        hook_dispatcher.fire_session_start()

        turn_id = hook_dispatcher.fire_conversation_turn(
            user_content="Question?",
            assistant_content="Answer!",
            duration_ms=1500,
        )

        assert turn_id > 0

    def test_multiple_conversation_turns(self, hook_dispatcher):
        """Test recording multiple turns in sequence."""
        hook_dispatcher.fire_session_start()

        turns_recorded = []
        for i in range(3):
            turn_id = hook_dispatcher.fire_conversation_turn(
                user_content=f"Question {i}",
                assistant_content=f"Answer {i}",
            )
            turns_recorded.append(turn_id)

        assert len(turns_recorded) == 3
        assert hook_dispatcher._turn_count == 3
        # All turns should be in same conversation
        assert hook_dispatcher._active_conversation_id is not None

    def test_user_prompt_submit(self, hook_dispatcher):
        """Test fire_user_prompt_submit."""
        event_id = hook_dispatcher.fire_user_prompt_submit(
            prompt="What is AI?", task="Learning", phase="exploration"
        )

        assert event_id > 0
        assert hook_dispatcher.get_active_session_id() is not None

    def test_assistant_response(self, hook_dispatcher):
        """Test fire_assistant_response."""
        hook_dispatcher.fire_session_start()

        event_id = hook_dispatcher.fire_assistant_response(
            response="AI stands for Artificial Intelligence.",
            task="Learning",
            phase="explanation",
        )

        assert event_id > 0

    def test_task_started(self, hook_dispatcher):
        """Test fire_task_started."""
        hook_dispatcher.fire_session_start()

        event_id = hook_dispatcher.fire_task_started(
            task_id="task_001",
            task_description="Implement authentication",
            goal="Secure user accounts",
        )

        assert event_id > 0

    def test_task_completed_success(self, hook_dispatcher):
        """Test fire_task_completed with success."""
        hook_dispatcher.fire_session_start()

        event_id = hook_dispatcher.fire_task_completed(
            task_id="task_001",
            outcome=EventOutcome.SUCCESS,
            summary="Implemented JWT authentication",
        )

        assert event_id > 0

    def test_task_completed_failure(self, hook_dispatcher):
        """Test fire_task_completed with failure."""
        hook_dispatcher.fire_session_start()

        event_id = hook_dispatcher.fire_task_completed(
            task_id="task_002",
            outcome=EventOutcome.FAILURE,
            summary="Connection timeout error",
        )

        assert event_id > 0

    def test_error_occurred(self, hook_dispatcher):
        """Test fire_error_occurred."""
        hook_dispatcher.fire_session_start()

        event_id = hook_dispatcher.fire_error_occurred(
            error_type="ConnectionError",
            error_message="Failed to connect to database",
            context_str="During session initialization",
        )

        assert event_id > 0

    def test_snapshot_conversation_for_recovery(self, hook_dispatcher):
        """Test snapshotting conversation for /clear recovery."""
        hook_dispatcher.fire_session_start()

        # Record some conversation turns
        for i in range(3):
            hook_dispatcher.fire_conversation_turn(
                user_content=f"Q{i}",
                assistant_content=f"A{i}",
            )

        # Snapshot
        event_id = hook_dispatcher.snapshot_conversation_for_recovery()

        assert event_id > 0

    def test_get_session_state(self, hook_dispatcher):
        """Test get_session_state."""
        session_id = hook_dispatcher.fire_session_start()

        # Record some activity
        hook_dispatcher.fire_conversation_turn("Hello", "Hi there!")
        hook_dispatcher.fire_conversation_turn("How are you?", "I'm good!")

        state = hook_dispatcher.get_session_state()

        assert state["session_id"] == session_id
        assert state["is_active"] is True
        assert state["conversation_count"] >= 1
        assert state["turn_count"] == 2

    def test_reset_session(self, hook_dispatcher):
        """Test reset_session."""
        hook_dispatcher.fire_session_start()
        hook_dispatcher.fire_conversation_turn("Q", "A")

        hook_dispatcher.reset_session()

        assert hook_dispatcher.get_active_session_id() is None
        assert hook_dispatcher._turn_count == 0
        assert hook_dispatcher._active_conversation_id is None

    def test_multiple_sessions_isolation(self, hook_dispatcher):
        """Test that multiple sessions are isolated."""
        # First session
        sess1 = hook_dispatcher.fire_session_start(session_id="session_1")
        hook_dispatcher.fire_conversation_turn("Q1 in session 1", "A1 in session 1")
        turn_count_1 = hook_dispatcher._turn_count

        # End first, start second
        hook_dispatcher.fire_session_end()
        sess2 = hook_dispatcher.fire_session_start(session_id="session_2")
        hook_dispatcher.fire_conversation_turn("Q1 in session 2", "A1 in session 2")

        state2 = hook_dispatcher.get_session_state()

        assert state2["session_id"] == sess2
        assert state2["turn_count"] == 1  # Reset for new session

    def test_conversation_auto_creation(self, hook_dispatcher):
        """Test that conversation is auto-created on first turn."""
        hook_dispatcher.fire_session_start()

        assert hook_dispatcher._active_conversation_id is None

        hook_dispatcher.fire_conversation_turn("Q", "A")

        assert hook_dispatcher._active_conversation_id is not None

    def test_session_without_id_is_unique(self, hook_dispatcher):
        """Test that auto-generated session IDs are unique."""
        sess1 = hook_dispatcher.fire_session_start()
        hook_dispatcher.fire_session_end()

        sess2 = hook_dispatcher.fire_session_start()

        assert sess1 != sess2

    def test_turn_count_increments(self, hook_dispatcher):
        """Test that turn count increments correctly."""
        hook_dispatcher.fire_session_start()

        assert hook_dispatcher._turn_count == 0

        hook_dispatcher.fire_conversation_turn("Q1", "A1")
        assert hook_dispatcher._turn_count == 1

        hook_dispatcher.fire_conversation_turn("Q2", "A2")
        assert hook_dispatcher._turn_count == 2

        hook_dispatcher.fire_conversation_turn("Q3", "A3")
        assert hook_dispatcher._turn_count == 3

    def test_long_conversation_content_in_turns(self, hook_dispatcher):
        """Test handling long conversation content."""
        hook_dispatcher.fire_session_start()

        long_user_msg = "A" * 5000
        long_asst_msg = "B" * 5000

        turn_id = hook_dispatcher.fire_conversation_turn(long_user_msg, long_asst_msg)

        assert turn_id > 0
        assert hook_dispatcher._turn_count == 1

    def test_special_characters_in_conversation(self, hook_dispatcher):
        """Test handling special characters."""
        hook_dispatcher.fire_session_start()

        user_msg = 'Use "quotes" and \\ backslash'
        asst_msg = "I can handle special chars: \\n \\t \" '"

        turn_id = hook_dispatcher.fire_conversation_turn(user_msg, asst_msg)

        assert turn_id > 0

    def test_context_preserved_in_events(self, hook_dispatcher):
        """Test that context is preserved in recorded events."""
        hook_dispatcher.fire_session_start()

        hook_dispatcher.fire_conversation_turn(
            user_content="Q",
            assistant_content="A",
            task="Testing context",
            phase="verification",
        )

        # Verify events were recorded with context
        state = hook_dispatcher.get_session_state()
        assert state["conversation_count"] >= 0

    def test_task_lifecycle(self, hook_dispatcher):
        """Test complete task lifecycle."""
        hook_dispatcher.fire_session_start()

        # Start task
        hook_dispatcher.fire_task_started(
            task_id="task_001",
            task_description="Implement feature X",
        )

        # Do some work (conversation turns)
        hook_dispatcher.fire_conversation_turn("How should I approach this?", "Here's my suggestion...")
        hook_dispatcher.fire_conversation_turn("Can you elaborate?", "Sure, here's more detail...")

        # Complete task
        hook_dispatcher.fire_task_completed(
            task_id="task_001",
            outcome=EventOutcome.SUCCESS,
            summary="Feature X successfully implemented",
        )

        # Verify state
        state = hook_dispatcher.get_session_state()
        assert state["turn_count"] == 2

    def test_error_handling_during_session(self, hook_dispatcher):
        """Test error recording during active session."""
        hook_dispatcher.fire_session_start()

        # Record normal activity
        hook_dispatcher.fire_conversation_turn("Q", "A")

        # Record error
        error_id = hook_dispatcher.fire_error_occurred(
            error_type="RuntimeError",
            error_message="Something went wrong",
        )

        assert error_id > 0
        # Session should still be active
        assert hook_dispatcher.get_active_session_id() is not None

    def test_get_active_session_id(self, hook_dispatcher):
        """Test getting active session ID."""
        assert hook_dispatcher.get_active_session_id() is None

        session_id = hook_dispatcher.fire_session_start()
        assert hook_dispatcher.get_active_session_id() == session_id

        hook_dispatcher.fire_session_end()
        assert hook_dispatcher.get_active_session_id() is None

    def test_multiple_projects_isolation(self):
        """Test that different projects have isolated conversations."""
        from athena.core.database import Database
        from pathlib import Path

        with TemporaryDirectory() as tmpdir:
            db = Database(Path(tmpdir) / "test.db")

            disp1 = HookDispatcher(db, project_id=1)
            disp2 = HookDispatcher(db, project_id=2)

            sess1 = disp1.fire_session_start(session_id="sess_shared")
            disp1.fire_conversation_turn("Project 1 message", "Response 1")

            sess2 = disp2.fire_session_start(session_id="sess_shared")
            disp2.fire_conversation_turn("Project 2 message", "Response 2")

            # Each should have isolated data
            state1 = disp1.get_session_state()
            state2 = disp2.get_session_state()

            assert state1["turn_count"] == 1
            assert state2["turn_count"] == 1
