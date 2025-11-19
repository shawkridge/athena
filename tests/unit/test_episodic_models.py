"""Tests for episodic memory models and data structures."""

import pytest
from datetime import datetime, timedelta
from athena.episodic.models import (
    EpisodicEvent,
    EventType,
    EventOutcome,
    EventContext,
    CodeEventType,
)


class TestEventContext:
    """Test EventContext model."""

    def test_event_context_defaults(self):
        """Test EventContext with default values."""
        ctx = EventContext()
        assert ctx.cwd is None
        assert ctx.files == []
        assert ctx.task is None
        assert ctx.phase is None

    def test_event_context_with_values(self):
        """Test EventContext with provided values."""
        ctx = EventContext(
            cwd="/home/user/project",
            files=["/file1.py", "/file2.py"],
            task="implement-feature",
            phase="development",
        )
        assert ctx.cwd == "/home/user/project"
        assert ctx.files == ["/file1.py", "/file2.py"]
        assert ctx.task == "implement-feature"
        assert ctx.phase == "development"


class TestEpisodicEvent:
    """Test EpisodicEvent model."""

    def test_episodic_event_defaults(self):
        """Test EpisodicEvent with default values."""
        event = EpisodicEvent(
            project_id=1,
            session_id="test-session",
            content="Test event",
        )
        assert event.id is None
        assert event.project_id == 1
        assert event.session_id == "test-session"
        assert event.content == "Test event"
        assert event.event_type is None
        assert event.outcome is None
        assert event.lifecycle_status == "active"
        assert event.consolidation_score == 0.0
        assert event.activation_count == 0
        assert event.importance_score == 0.5
        assert event.confidence == 1.0

    def test_episodic_event_with_event_type(self):
        """Test EpisodicEvent with event type."""
        event = EpisodicEvent(
            project_id=1,
            session_id="test",
            content="Test",
            event_type=EventType.ACTION,
        )
        assert event.event_type == EventType.ACTION

    def test_episodic_event_with_outcome(self):
        """Test EpisodicEvent with outcome."""
        event = EpisodicEvent(
            project_id=1,
            session_id="test",
            content="Test",
            outcome=EventOutcome.SUCCESS,
        )
        assert event.outcome == EventOutcome.SUCCESS

    def test_episodic_event_importance_clamped(self):
        """Test EpisodicEvent importance score validation."""
        # Pydantic should validate 0.0-1.0 range
        event = EpisodicEvent(
            project_id=1,
            session_id="test",
            content="Test",
            importance_score=0.75,
        )
        assert event.importance_score == 0.75

    def test_episodic_event_lifecycle_states(self):
        """Test all lifecycle states."""
        for state in ["active", "consolidated", "archived"]:
            event = EpisodicEvent(
                project_id=1,
                session_id="test",
                content="Test",
                lifecycle_status=state,
            )
            assert event.lifecycle_status == state

    def test_episodic_event_code_awareness(self):
        """Test code-aware fields."""
        event = EpisodicEvent(
            project_id=1,
            session_id="test",
            content="Fixed bug in parser",
            code_event_type=CodeEventType.BUG_DISCOVERY,
            file_path="src/parser.py",
            symbol_name="Parser.parse",
            symbol_type="method",
            language="python",
            error_type="ValueError",
            stack_trace="Traceback...",
        )
        assert event.code_event_type == CodeEventType.BUG_DISCOVERY
        assert event.file_path == "src/parser.py"
        assert event.symbol_name == "Parser.parse"
        assert event.language == "python"
        assert event.error_type == "ValueError"

    def test_episodic_event_activation_tracking(self):
        """Test activation and consolidation tracking."""
        now = datetime.now()
        event = EpisodicEvent(
            project_id=1,
            session_id="test",
            content="Test",
            activation_count=5,
            consolidation_score=0.8,
            last_activation=now,
        )
        assert event.activation_count == 5
        assert event.consolidation_score == 0.8
        assert event.last_activation == now

    def test_episodic_event_working_memory_optimization(self):
        """Test working memory optimization fields."""
        event = EpisodicEvent(
            project_id=1,
            session_id="test",
            content="Test",
            importance_score=0.9,
            actionability_score=0.8,
            context_completeness_score=0.7,
            has_next_step=True,
            has_blocker=False,
            required_decisions="[decision_1, decision_2]",
        )
        assert event.importance_score == 0.9
        assert event.actionability_score == 0.8
        assert event.context_completeness_score == 0.7
        assert event.has_next_step is True
        assert event.has_blocker is False
        assert event.required_decisions == "[decision_1, decision_2]"

    def test_episodic_event_enum_values_serialization(self):
        """Test that enums are serialized correctly."""
        event = EpisodicEvent(
            project_id=1,
            session_id="test",
            content="Test",
            event_type=EventType.ERROR,
            outcome=EventOutcome.FAILURE,
        )
        # Pydantic's use_enum_values=True should convert to strings
        model_dict = event.model_dump()
        assert model_dict["event_type"] == "error"
        assert model_dict["outcome"] == "failure"

    def test_episodic_event_timestamp_default(self):
        """Test timestamp is auto-set to current time."""
        before = datetime.now()
        event = EpisodicEvent(
            project_id=1,
            session_id="test",
            content="Test",
        )
        after = datetime.now()
        assert before <= event.timestamp <= after

    def test_episodic_event_context_default(self):
        """Test context is auto-initialized."""
        event = EpisodicEvent(
            project_id=1,
            session_id="test",
            content="Test",
        )
        assert isinstance(event.context, EventContext)
        assert event.context.cwd is None
        assert event.context.files == []
