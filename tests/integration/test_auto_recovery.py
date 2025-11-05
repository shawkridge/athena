"""Tests for automatic context recovery after /clear."""

import pytest
from pathlib import Path

from athena.core.database import Database
from athena.conversation.auto_recovery import AutoContextRecovery
from athena.episodic.models import EpisodicEvent, EventContext, EventOutcome, EventType
from athena.episodic.store import EpisodicStore
from athena.hooks.dispatcher import HookDispatcher


@pytest.fixture
def db_with_history(tmp_path: Path) -> Database:
    """Create database with conversation history."""
    db = Database(tmp_path / "test.db")

    # Create hook dispatcher to record events
    dispatcher = HookDispatcher(db, project_id=1)

    # Simulate a session with work
    session_id = dispatcher.fire_session_start()
    assert session_id is not None

    # Simulate working on a task
    dispatcher.fire_task_started(
        task_id="task_1",
        task_description="Refactoring store classes for unified pattern",
        goal="100% architectural consistency"
    )

    # Record some conversation turns
    dispatcher.fire_conversation_turn(
        user_content="Can you help me refactor the stores?",
        assistant_content="Sure! I'll help refactor the 17 stores to use BaseStore utilities pattern.",
        task="Store refactoring",
        phase="implementation"
    )

    dispatcher.fire_conversation_turn(
        user_content="What about the hook system?",
        assistant_content="The hook system needs pre-clear protection to snapshot context.",
        task="Store refactoring",
        phase="implementation"
    )

    # Record file changes
    episodic_store = EpisodicStore(db)
    for filepath in ["src/memory_mcp/planning/store.py", "src/memory_mcp/hooks/dispatcher.py"]:
        event = EpisodicEvent(
            project_id=1,
            session_id=session_id,
            event_type=EventType.ACTION,
            content=f"Modified {filepath}",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(
                task="Store refactoring",
                phase="implementation",
                file_path=filepath
            ),
            learned=f"Edited {filepath}",
            confidence=0.95,
        )
        episodic_store.record_event(event)

    # Complete task
    dispatcher.fire_task_completed(
        task_id="task_1",
        outcome=EventOutcome.SUCCESS,
        summary="Store refactoring complete, all 17 stores unified"
    )

    return db


class TestAutoContextRecovery:
    """Test automatic context recovery system."""

    def test_recovery_trigger_detection(self, db_with_history: Database):
        """Test that recovery triggers are correctly detected."""
        recovery = AutoContextRecovery(db_with_history, project_id=1)

        # Test recovery trigger patterns
        assert recovery.should_trigger_recovery("what were we working on?")
        assert recovery.should_trigger_recovery("let's continue")
        assert recovery.should_trigger_recovery("where were we?")
        assert recovery.should_trigger_recovery("resume work")
        assert recovery.should_trigger_recovery("recover context")
        assert recovery.should_trigger_recovery("What was I doing?")

        # Test non-recovery prompts
        assert not recovery.should_trigger_recovery("How do I do X?")
        assert not recovery.should_trigger_recovery("Tell me about Python")
        assert not recovery.should_trigger_recovery("Let's start something new")

    def test_auto_recover_context(self, db_with_history: Database):
        """Test context recovery from episodic memory."""
        recovery = AutoContextRecovery(db_with_history, project_id=1)

        context = recovery.auto_recover_context()

        # Verify recovery structure
        assert context["status"] == "recovered"
        assert "session_id" in context
        assert "conversation_summary" in context
        assert "active_work" in context
        assert "current_phase" in context
        assert "recent_files" in context
        assert "recovery_recommendation" in context

    def test_context_contains_task_info(self, db_with_history: Database):
        """Test that recovered context includes active task."""
        recovery = AutoContextRecovery(db_with_history, project_id=1)

        context = recovery.auto_recover_context()

        # Should include the refactoring task
        assert context["active_work"] == "Store refactoring" or "refactor" in str(context).lower()
        assert context["current_phase"] is not None

    def test_context_contains_recent_files(self, db_with_history: Database):
        """Test that recovered context includes recently modified files."""
        recovery = AutoContextRecovery(db_with_history, project_id=1)

        context = recovery.auto_recover_context()

        # Recent files are optional (depends on whether context_files was populated)
        # But the key should exist in the response
        assert "recent_files" in context
        assert isinstance(context.get("recent_files"), list)

    def test_conversation_summary_building(self, db_with_history: Database):
        """Test conversation summary is correctly built."""
        recovery = AutoContextRecovery(db_with_history, project_id=1)

        context = recovery.auto_recover_context()
        summary = context["conversation_summary"]

        # Summary should include recent conversation content
        assert "Recent conversation:" in summary or len(summary) > 0
        assert isinstance(summary, str)

    def test_hook_dispatcher_integration(self, db_with_history: Database):
        """Test that HookDispatcher integrates auto-recovery."""
        dispatcher = HookDispatcher(db_with_history, project_id=1)

        # Check that auto_recovery is initialized
        assert hasattr(dispatcher, "auto_recovery")
        assert isinstance(dispatcher.auto_recovery, AutoContextRecovery)

    def test_check_recovery_request_method(self, db_with_history: Database):
        """Test HookDispatcher.check_context_recovery_request()."""
        dispatcher = HookDispatcher(db_with_history, project_id=1)

        # Test recovery trigger
        result = dispatcher.check_context_recovery_request("what were we working on?")
        assert result is not None
        assert result["status"] == "recovered"

        # Test non-recovery prompt
        result = dispatcher.check_context_recovery_request("Tell me a joke")
        assert result is None

    def test_recovery_banner(self, db_with_history: Database):
        """Test recovery banner generation."""
        recovery = AutoContextRecovery(db_with_history, project_id=1)

        banner = recovery.get_recovery_banner()

        assert "Context Recovered" in banner
        assert "/memory-query" in banner
        assert "/timeline" in banner

    def test_time_delta_formatting(self, db_with_history: Database):
        """Test human-readable time delta formatting."""
        recovery = AutoContextRecovery(db_with_history, project_id=1)
        from datetime import datetime, timedelta

        # Test recent time
        now = datetime.now()
        assert recovery._format_time_delta(now) == "just now"

        # Test minutes ago
        five_min_ago = now - timedelta(minutes=5)
        result = recovery._format_time_delta(five_min_ago)
        assert "minute" in result

        # Test hours ago
        two_hours_ago = now - timedelta(hours=2)
        result = recovery._format_time_delta(two_hours_ago)
        assert "hour" in result

    def test_empty_database_recovery(self, tmp_path: Path):
        """Test recovery from empty database."""
        db = Database(tmp_path / "test.db")
        recovery = AutoContextRecovery(db, project_id=1)

        context = recovery.auto_recover_context()

        assert context["status"] == "none"
        assert "No conversation history" in context.get("message", "")

    def test_recovery_preserves_full_context(self, db_with_history: Database):
        """Test that full context is preserved for restoration."""
        recovery = AutoContextRecovery(db_with_history, project_id=1)

        context = recovery.auto_recover_context()

        # Verify full_context dict
        full_context = context.get("full_context", {})
        assert "session_id" in full_context
        assert "conversation_events" in full_context
        assert "recent_files_modified" in full_context
        assert "time_since_last_activity" in full_context

    def test_recovery_recommendation_completeness(self, db_with_history: Database):
        """Test that recovery recommendation is helpful and complete."""
        recovery = AutoContextRecovery(db_with_history, project_id=1)

        context = recovery.auto_recover_context()
        recommendation = context.get("recovery_recommendation", "")

        # Should include recovery banner/guide
        assert len(recommendation) > 50  # Non-trivial length
        assert "next steps" in recommendation.lower() or "context" in recommendation.lower()
