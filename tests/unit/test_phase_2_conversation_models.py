"""Tests for Phase 2: Conversation models, store, and database schema."""

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from athena.conversation import (
    Conversation,
    ConversationStore,
    ConversationTurn,
    Message,
    MessageRole,
)
from athena.core.database import Database


@pytest.fixture
def conversation_store():
    """Create ConversationStore with test database."""
    with TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test_conversations.db")
        yield ConversationStore(db)


class TestConversationModels:
    """Test conversation data models."""

    def test_message_creation(self):
        """Test Message model creation."""
        msg = Message(
            role=MessageRole.USER,
            content="Hello, how are you?",
            tokens_estimate=5,
            model="claude-3",
        )

        assert msg.role == MessageRole.USER
        assert msg.content == "Hello, how are you?"
        assert msg.tokens_estimate == 5
        assert msg.model == "claude-3"

    def test_message_with_metadata(self):
        """Test Message with metadata."""
        msg = Message(
            role=MessageRole.ASSISTANT,
            content="I'm doing well!",
            metadata={"confidence": 0.95, "source": "episodic"},
        )

        assert msg.metadata["confidence"] == 0.95
        assert msg.metadata["source"] == "episodic"

    def test_conversation_turn_creation(self):
        """Test ConversationTurn model."""
        user_msg = Message(role=MessageRole.USER, content="Question?")
        asst_msg = Message(role=MessageRole.ASSISTANT, content="Answer!")

        turn = ConversationTurn(
            turn_number=1,
            user_message=user_msg,
            assistant_message=asst_msg,
            duration_ms=1500,
            total_tokens=20,
        )

        assert turn.turn_number == 1
        assert turn.duration_ms == 1500
        assert turn.total_tokens == 20

    def test_conversation_creation(self):
        """Test Conversation model."""
        conv = Conversation(
            project_id=1,
            session_id="sess_123",
            thread_id="thread_abc",
            title="Test Conversation",
            status="active",
            total_tokens=100,
        )

        assert conv.project_id == 1
        assert conv.thread_id == "thread_abc"
        assert conv.status == "active"
        assert len(conv.turns) == 0

    def test_conversation_with_turns(self):
        """Test Conversation with multiple turns."""
        turns = []
        for i in range(3):
            turn = ConversationTurn(
                turn_number=i + 1,
                user_message=Message(role=MessageRole.USER, content=f"Q{i}"),
                assistant_message=Message(
                    role=MessageRole.ASSISTANT, content=f"A{i}"
                ),
            )
            turns.append(turn)

        conv = Conversation(
            project_id=1,
            session_id="sess_123",
            thread_id="thread_abc",
            turns=turns,
        )

        assert len(conv.turns) == 3
        assert conv.turns[0].turn_number == 1
        assert conv.turns[2].turn_number == 3


class TestConversationStore:
    """Test ConversationStore functionality."""

    def test_session_creation(self, conversation_store):
        """Test creating a session."""
        session_id = conversation_store.create_session("sess_test", 1)

        assert session_id == "sess_test"

    def test_session_end(self, conversation_store):
        """Test ending a session."""
        session_id = conversation_store.create_session("sess_end_test", 1)

        result = conversation_store.end_session(session_id)

        assert result is True

    def test_conversation_creation(self, conversation_store):
        """Test creating a conversation."""
        session_id = conversation_store.create_session("sess_conv", 1)

        conv = Conversation(
            project_id=1,
            session_id=session_id,
            thread_id="thread_001",
            title="First Conversation",
        )

        conv_id = conversation_store.create_conversation(conv)

        assert conv_id > 0

    def test_conversation_retrieval(self, conversation_store):
        """Test retrieving a conversation."""
        session_id = conversation_store.create_session("sess_retrieval", 1)

        conv = Conversation(
            project_id=1,
            session_id=session_id,
            thread_id="thread_002",
            title="Retrieve Test",
        )

        conv_id = conversation_store.create_conversation(conv)
        retrieved = conversation_store.get_conversation(conv_id)

        assert retrieved is not None
        assert retrieved.title == "Retrieve Test"
        assert retrieved.thread_id == "thread_002"

    def test_add_turn_to_conversation(self, conversation_store):
        """Test adding a turn to conversation."""
        session_id = conversation_store.create_session("sess_turns", 1)

        conv = Conversation(
            project_id=1,
            session_id=session_id,
            thread_id="thread_003",
        )

        conv_id = conversation_store.create_conversation(conv)

        user_msg = Message(role=MessageRole.USER, content="What is AI?", tokens_estimate=4)
        asst_msg = Message(
            role=MessageRole.ASSISTANT,
            content="AI is artificial intelligence...",
            tokens_estimate=8,
        )

        turn_id = conversation_store.add_turn(
            conv_id, 1, user_msg, asst_msg, duration_ms=2000
        )

        assert turn_id > 0

        # Verify turn was added
        retrieved = conversation_store.get_conversation(conv_id)
        assert len(retrieved.turns) == 1
        assert retrieved.turns[0].turn_number == 1
        assert retrieved.turns[0].duration_ms == 2000
        assert retrieved.total_tokens == 12  # 4 + 8

    def test_multiple_turns_in_conversation(self, conversation_store):
        """Test adding multiple turns."""
        session_id = conversation_store.create_session("sess_multi", 1)

        conv = Conversation(
            project_id=1,
            session_id=session_id,
            thread_id="thread_004",
        )

        conv_id = conversation_store.create_conversation(conv)

        # Add 3 turns
        for i in range(3):
            user_msg = Message(
                role=MessageRole.USER,
                content=f"Question {i}",
                tokens_estimate=3,
            )
            asst_msg = Message(
                role=MessageRole.ASSISTANT,
                content=f"Answer {i}",
                tokens_estimate=4,
            )
            conversation_store.add_turn(conv_id, i + 1, user_msg, asst_msg)

        # Verify all turns
        retrieved = conversation_store.get_conversation(conv_id)
        assert len(retrieved.turns) == 3
        assert retrieved.total_tokens == 21  # (3+4) * 3

    def test_search_conversations(self, conversation_store):
        """Test searching conversations."""
        session_id = conversation_store.create_session("sess_search", 1)

        # Create conversations with different titles
        for i in range(3):
            conv = Conversation(
                project_id=1,
                session_id=session_id,
                thread_id=f"thread_{i}",
                title=f"Discussion about authentication {i}",
            )
            conversation_store.create_conversation(conv)

        # Search
        results = conversation_store.search_conversations(1, "authentication")

        assert len(results) >= 3

    def test_get_recent_conversations(self, conversation_store):
        """Test getting recent conversations."""
        session_id = conversation_store.create_session("sess_recent", 1)

        # Create 5 conversations
        conv_ids = []
        for i in range(5):
            conv = Conversation(
                project_id=1,
                session_id=session_id,
                thread_id=f"thread_recent_{i}",
                title=f"Conversation {i}",
            )
            conv_id = conversation_store.create_conversation(conv)
            conv_ids.append(conv_id)

        # Get recent
        recent = conversation_store.get_recent_conversations(1, limit=3)

        assert len(recent) == 3
        # Should return 3 recent conversations
        for r in recent:
            assert r["id"] in conv_ids

    def test_archive_conversation(self, conversation_store):
        """Test archiving a conversation."""
        session_id = conversation_store.create_session("sess_archive", 1)

        conv = Conversation(
            project_id=1,
            session_id=session_id,
            thread_id="thread_archive",
            status="active",
        )

        conv_id = conversation_store.create_conversation(conv)

        # Archive
        result = conversation_store.archive_conversation(conv_id)

        assert result is True

        # Verify status changed
        retrieved = conversation_store.get_conversation(conv_id)
        assert retrieved.status == "archived"

    def test_get_session_conversations(self, conversation_store):
        """Test getting all conversations in a session."""
        session_id = conversation_store.create_session("sess_all", 1)

        # Create 3 conversations
        for i in range(3):
            conv = Conversation(
                project_id=1,
                session_id=session_id,
                thread_id=f"thread_session_{i}",
            )
            conversation_store.create_conversation(conv)

        # Get all in session
        convs = conversation_store.get_session_conversations(session_id)

        assert len(convs) == 3

    def test_update_conversation_metadata(self, conversation_store):
        """Test updating conversation metadata."""
        session_id = conversation_store.create_session("sess_meta", 1)

        conv = Conversation(
            project_id=1,
            session_id=session_id,
            thread_id="thread_meta",
            title="Original Title",
        )

        conv_id = conversation_store.create_conversation(conv)

        # Update title
        result = conversation_store.update_conversation_metadata(
            conv_id, title="Updated Title"
        )

        assert result is True

        # Verify update
        retrieved = conversation_store.get_conversation(conv_id)
        assert retrieved.title == "Updated Title"

    def test_message_with_special_characters(self, conversation_store):
        """Test handling messages with special characters."""
        session_id = conversation_store.create_session("sess_special", 1)

        conv = Conversation(
            project_id=1,
            session_id=session_id,
            thread_id="thread_special",
        )

        conv_id = conversation_store.create_conversation(conv)

        user_msg = Message(
            role=MessageRole.USER,
            content='Use "quotes" and backslash: \\ and newline\n',
        )
        asst_msg = Message(
            role=MessageRole.ASSISTANT,
            content='I understand special chars: "quotes" \\ \n',
        )

        turn_id = conversation_store.add_turn(conv_id, 1, user_msg, asst_msg)

        assert turn_id > 0

        # Verify content
        retrieved = conversation_store.get_conversation(conv_id)
        assert '"quotes"' in retrieved.turns[0].user_message.content

    def test_long_conversation_content(self, conversation_store):
        """Test handling long conversation content."""
        session_id = conversation_store.create_session("sess_long", 1)

        conv = Conversation(
            project_id=1,
            session_id=session_id,
            thread_id="thread_long",
        )

        conv_id = conversation_store.create_conversation(conv)

        # Create a long message
        long_content = "A" * 10000
        user_msg = Message(role=MessageRole.USER, content=long_content)
        asst_msg = Message(
            role=MessageRole.ASSISTANT, content="Long response: " + "B" * 10000
        )

        turn_id = conversation_store.add_turn(conv_id, 1, user_msg, asst_msg)

        assert turn_id > 0

        # Verify full content is stored
        retrieved = conversation_store.get_conversation(conv_id)
        assert len(retrieved.turns[0].user_message.content) == 10000

    def test_conversation_metadata_json_handling(self, conversation_store):
        """Test handling metadata as JSON."""
        session_id = conversation_store.create_session("sess_json", 1)

        conv = Conversation(
            project_id=1,
            session_id=session_id,
            thread_id="thread_json",
        )

        conv_id = conversation_store.create_conversation(conv)

        metadata = {
            "source": "user_input",
            "context": {"file": "/path/to/file.py", "line": 42},
            "tags": ["urgent", "security"],
        }

        user_msg = Message(
            role=MessageRole.USER,
            content="Test",
            metadata=metadata,
        )
        asst_msg = Message(role=MessageRole.ASSISTANT, content="Response")

        conversation_store.add_turn(conv_id, 1, user_msg, asst_msg)

        # Verify metadata
        retrieved = conversation_store.get_conversation(conv_id)
        assert retrieved.turns[0].user_message.metadata["source"] == "user_input"
        assert retrieved.turns[0].user_message.metadata["context"]["line"] == 42

    def test_conversation_tokens_tracking(self, conversation_store):
        """Test token counting across turns."""
        session_id = conversation_store.create_session("sess_tokens", 1)

        conv = Conversation(
            project_id=1,
            session_id=session_id,
            thread_id="thread_tokens",
        )

        conv_id = conversation_store.create_conversation(conv)

        # Add turns with different token counts
        tokens_list = [(10, 15), (20, 25), (5, 10)]
        total_expected = sum(u + a for u, a in tokens_list)

        for i, (user_tokens, asst_tokens) in enumerate(tokens_list):
            user_msg = Message(
                role=MessageRole.USER,
                content=f"Q{i}",
                tokens_estimate=user_tokens,
            )
            asst_msg = Message(
                role=MessageRole.ASSISTANT,
                content=f"A{i}",
                tokens_estimate=asst_tokens,
            )
            conversation_store.add_turn(conv_id, i + 1, user_msg, asst_msg)

        # Verify total tokens
        retrieved = conversation_store.get_conversation(conv_id)
        assert retrieved.total_tokens == total_expected
