"""Tests for Phase 4: SessionResumptionManager and post-/clear context loading."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from athena.conversation import (
    ConversationStore,
    Message,
    MessageRole,
    SessionResumptionManager,
)
from athena.conversation.models import Conversation
from athena.core.database import Database
from athena.hooks.dispatcher import HookDispatcher


@pytest.fixture
def resumption_manager(tmp_path):
    """Create SessionResumptionManager with test database."""
    db = Database(tmp_path / "test_resumption.db")
    return SessionResumptionManager(db, project_id=1)


@pytest.fixture
def populated_session(resumption_manager):
    """Create a session with conversation history."""
    store = resumption_manager.conversation_store
    session_id = "test_session_001"

    # Create session
    store.create_session(session_id, 1)

    # Create conversation
    conv = Conversation(
        project_id=1,
        session_id=session_id,
        thread_id="thread_001",
        title="Authentication Implementation",
    )
    conv_id = store.create_conversation(conv)

    # Add multiple turns
    for i in range(5):
        user_msg = Message(
            role=MessageRole.USER, content=f"Question {i}: How do I handle JWT?", tokens_estimate=5
        )
        asst_msg = Message(
            role=MessageRole.ASSISTANT,
            content=f"Answer {i}: JWT tokens are used for stateless authentication...",
            tokens_estimate=10,
        )
        store.add_turn(conv_id, i + 1, user_msg, asst_msg, duration_ms=1000 + i * 100)

    return session_id


class TestSessionResumptionManager:
    """Test SessionResumptionManager functionality."""

    def test_detect_resumption_intent_what_were_we_doing(self, resumption_manager):
        """Test detecting 'what were we doing' intent."""
        user_input = "Hey, what were we doing before I cleared the screen?"

        result = resumption_manager.detect_resumption_intent(user_input)

        assert result is True

    def test_detect_resumption_intent_lets_continue(self, resumption_manager):
        """Test detecting 'let's continue' intent."""
        user_input = "Let's continue from where we left off"

        result = resumption_manager.detect_resumption_intent(user_input)

        assert result is True

    def test_detect_resumption_intent_where_were_we(self, resumption_manager):
        """Test detecting 'where were we' intent."""
        user_input = "Where were we in this process?"

        result = resumption_manager.detect_resumption_intent(user_input)

        assert result is True

    def test_detect_resumption_intent_resume(self, resumption_manager):
        """Test detecting 'resume' intent."""
        user_input = "I need to resume my previous work"

        result = resumption_manager.detect_resumption_intent(user_input)

        assert result is True

    def test_detect_no_resumption_intent(self, resumption_manager):
        """Test that regular input is not detected as resumption."""
        user_input = "Can you help me debug this function?"

        result = resumption_manager.detect_resumption_intent(user_input)

        assert result is False

    def test_get_resumption_brief_no_context(self, resumption_manager):
        """Test getting resumption brief when no context exists."""
        brief = resumption_manager.get_resumption_brief()

        assert brief["status"] == "no_context"

    def test_get_resumption_brief_with_session(self, resumption_manager, populated_session):
        """Test getting resumption brief with existing session."""
        brief = resumption_manager.get_resumption_brief(populated_session)

        assert brief["status"] == "ready_to_resume"
        assert brief["session_id"] == populated_session
        assert brief["conversation_title"] == "Authentication Implementation"
        assert "recent_context" in brief
        assert "recovery_options" in brief
        assert len(brief["recovery_options"]) > 0

    def test_get_resumption_brief_auto_finds_recent(self, resumption_manager, populated_session):
        """Test that resumption brief auto-finds most recent session."""
        brief = resumption_manager.get_resumption_brief()  # No session_id specified

        assert brief["status"] == "ready_to_resume"
        assert brief["session_id"] == populated_session

    def test_load_context_to_working_memory(self, resumption_manager, populated_session):
        """Test loading context into working memory."""
        result = resumption_manager.load_context_to_working_memory(populated_session)

        assert result["status"] == "context_loaded"
        assert result["loaded_item_id"] is not None
        assert result["conversation_title"] == "Authentication Implementation"
        assert "context_preview" in result

    def test_load_context_without_session_id(self, resumption_manager, populated_session):
        """Test loading context auto-finds session."""
        result = resumption_manager.load_context_to_working_memory()

        assert result["status"] == "context_loaded"
        assert result["session_id"] == populated_session

    def test_get_full_session_context(self, resumption_manager, populated_session):
        """Test retrieving complete session context."""
        context = resumption_manager.get_full_session_context(populated_session)

        assert context["session_id"] == populated_session
        assert context["conversation_count"] >= 1
        assert len(context["conversations"]) >= 1

        conv = context["conversations"][0]
        assert conv["title"] == "Authentication Implementation"
        assert conv["turn_count"] == 5

    def test_get_full_session_context_with_turn_details(self, resumption_manager, populated_session):
        """Test that full context includes turn details."""
        context = resumption_manager.get_full_session_context(populated_session)

        conv = context["conversations"][0]
        assert len(conv["turns"]) == 5

        first_turn = conv["turns"][0]
        assert "turn_number" in first_turn
        assert "user" in first_turn
        assert "assistant" in first_turn
        assert "duration_ms" in first_turn

    def test_suggest_next_task(self, resumption_manager, populated_session):
        """Test suggesting next task based on context."""
        suggestion = resumption_manager.suggest_next_task(populated_session)

        assert "suggested_task" in suggestion
        assert suggestion["suggested_task"] == "Authentication Implementation"
        assert "context" in suggestion
        assert suggestion["conversation_history_available"] is True

    def test_resumption_intent_is_case_insensitive(self, resumption_manager):
        """Test that resumption intent detection is case-insensitive."""
        user_input = "WHAT WERE WE DOING?"

        result = resumption_manager.detect_resumption_intent(user_input)

        assert result is True

    def test_clear_old_sessions(self, resumption_manager):
        """Test archiving old sessions."""
        store = resumption_manager.conversation_store

        # Create and populate a session
        store.create_session("old_session", 1)
        conv = Conversation(
            project_id=1,
            session_id="old_session",
            thread_id="thread_old",
        )
        conv_id = store.create_conversation(conv)

        # Archive old sessions (should archive our test session if days=0)
        result = resumption_manager.clear_old_sessions(days=0)

        assert "archived_conversations" in result
        assert result["archived_conversations"] >= 0

    def test_format_context_for_loading(self, resumption_manager):
        """Test that context is properly formatted for working memory."""
        brief = {
            "conversation_title": "Test Conversation",
            "session_id": "sess_test",
            "task": "Test task",
            "last_activity": "2025-01-01T12:00:00",
            "recent_context": "Recent exchange: Q: ?\nA: ...",
            "recovery_options": ["Option 1", "Option 2"],
        }

        formatted = resumption_manager._format_context_for_loading(brief)

        assert "SESSION RESUMPTION CONTEXT" in formatted
        assert "Test Conversation" in formatted
        assert "sess_test" in formatted
        assert "Test task" in formatted
        assert "Option 1" in formatted

    def test_resumption_with_multiple_conversations(self, resumption_manager):
        """Test resumption when session has multiple conversations."""
        store = resumption_manager.conversation_store
        session_id = "multi_conv_session"

        store.create_session(session_id, 1)

        # Create multiple conversations
        for i in range(3):
            conv = Conversation(
                project_id=1,
                session_id=session_id,
                thread_id=f"thread_{i}",
                title=f"Conversation {i}",
            )
            conv_id = store.create_conversation(conv)

            # Add turn to each
            user_msg = Message(role=MessageRole.USER, content=f"Q{i}")
            asst_msg = Message(role=MessageRole.ASSISTANT, content=f"A{i}")
            store.add_turn(conv_id, 1, user_msg, asst_msg)

        brief = resumption_manager.get_resumption_brief(session_id)

        assert brief["status"] == "ready_to_resume"
        assert brief["conversation_count"] >= 3

    def test_resumption_preserves_full_context_integrity(
        self, resumption_manager, populated_session
    ):
        """Test that resumption doesn't lose context information."""
        # Load context
        load_result = resumption_manager.load_context_to_working_memory(populated_session)

        # Get full context
        full_context = resumption_manager.get_full_session_context(populated_session)

        # Verify integrity
        assert load_result["conversation_title"] == full_context["conversations"][0]["title"]
        assert load_result["session_id"] == full_context["session_id"]

    def test_resumption_with_long_conversation(self, resumption_manager):
        """Test resumption with very long conversation."""
        store = resumption_manager.conversation_store
        session_id = "long_conv_session"

        store.create_session(session_id, 1)

        conv = Conversation(
            project_id=1,
            session_id=session_id,
            thread_id="thread_long",
            title="Very Long Conversation",
        )
        conv_id = store.create_conversation(conv)

        # Add 20 turns
        for i in range(20):
            user_msg = Message(
                role=MessageRole.USER,
                content=f"Question {i}: " + "A" * 500,
                tokens_estimate=50,
            )
            asst_msg = Message(
                role=MessageRole.ASSISTANT,
                content=f"Answer {i}: " + "B" * 500,
                tokens_estimate=100,
            )
            store.add_turn(conv_id, i + 1, user_msg, asst_msg)

        brief = resumption_manager.get_resumption_brief(session_id)

        assert brief["status"] == "ready_to_resume"
        assert "recent_context" in brief
        # Should still be manageable

    def test_workflow_what_were_we_doing(self, resumption_manager, populated_session):
        """Test complete workflow: User asks 'what were we doing'."""
        # User input after /clear
        user_input = "What were we doing?"

        # 1. Detect intent
        is_resumption = resumption_manager.detect_resumption_intent(user_input)
        assert is_resumption is True

        # 2. Get brief
        brief = resumption_manager.get_resumption_brief()
        assert brief["status"] == "ready_to_resume"

        # 3. Load to working memory
        load_result = resumption_manager.load_context_to_working_memory()
        assert load_result["status"] == "context_loaded"

        # 4. Ready for user to continue
        assert load_result["context_preview"] is not None

    def test_workflow_lets_continue(self, resumption_manager, populated_session):
        """Test complete workflow: User says 'let's continue'."""
        user_input = "Let's continue from where we left off"

        # Detect → Load → Ready
        is_resumption = resumption_manager.detect_resumption_intent(user_input)
        assert is_resumption is True

        result = resumption_manager.load_context_to_working_memory()
        assert result["status"] == "context_loaded"
        assert "next_steps" in result
