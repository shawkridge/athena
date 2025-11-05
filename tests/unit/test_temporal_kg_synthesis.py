"""Unit tests for Temporal KG Synthesis."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from athena.episodic.models import EpisodicEvent, EventContext, EventOutcome, EventType
from athena.temporal.kg_synthesis import TemporalKGSynthesis
from athena.temporal.models import TemporalKGRelation, EntityMetadata, KGSynthesisResult


class TestTemporalKGSynthesis:
    """Test Temporal KG Synthesis pipeline."""

    @pytest.fixture
    def mock_stores(self):
        """Create mock episodic and graph stores."""
        episodic_store = MagicMock()
        graph_store = MagicMock()
        return episodic_store, graph_store

    @pytest.fixture
    def synthesis(self, mock_stores):
        """Create TemporalKGSynthesis instance."""
        episodic_store, graph_store = mock_stores
        return TemporalKGSynthesis(
            episodic_store=episodic_store,
            graph_store=graph_store,
            causality_threshold=0.5,
            recency_decay_hours=1.0,
            frequency_threshold=10,
        )

    def test_synthesis_initialization(self, synthesis):
        """Test TemporalKGSynthesis initialization."""
        assert synthesis.causality_threshold == 0.5
        assert synthesis.recency_decay_seconds == 3600
        assert synthesis.frequency_threshold == 10

    def test_synthesize_empty_events(self, synthesis, mock_stores):
        """Test synthesis with no events."""
        episodic_store, _ = mock_stores
        episodic_store.get_events_for_session.return_value = []

        result = synthesis.synthesize(session_id="test-session")

        assert isinstance(result, KGSynthesisResult)
        assert result.entities_count == 0
        assert result.relations_count == 0
        assert result.temporal_relations_count == 0

    def test_synthesize_single_event(self, synthesis, mock_stores):
        """Test synthesis with single event."""
        episodic_store, graph_store = mock_stores

        event = EpisodicEvent(
            id=1,
            project_id=1,
            session_id="test-session",
            timestamp=datetime.now(),
            event_type=EventType.ACTION,
            content="Test action",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(cwd="/test", files=[], task="task1", phase="phase-1"),
        )

        episodic_store.get_events_for_session.return_value = [event]

        result = synthesis.synthesize(session_id="test-session")

        assert isinstance(result, KGSynthesisResult)
        # Single event has no relations
        assert result.relations_count == 0

    def test_calculate_causality_error_to_success(self, synthesis):
        """Test causality score for error → success pattern."""
        event_a = EpisodicEvent(
            id=1,
            project_id=1,
            session_id="session",
            timestamp=datetime.now(),
            event_type=EventType.ERROR,
            content="Error occurred",
            outcome=EventOutcome.FAILURE,
            context=EventContext(cwd="/test", files=[], task="task1", phase="phase-1"),
        )

        event_b = EpisodicEvent(
            id=2,
            project_id=1,
            session_id="session",
            timestamp=datetime.now() + timedelta(minutes=5),
            event_type=EventType.ACTION,
            content="Fixed error",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(cwd="/test", files=[], task="task1", phase="phase-1"),
        )

        causality = synthesis._calculate_causality(event_a, event_b)
        assert causality == 1.0  # Error → Success is perfect causality

    def test_calculate_causality_decision_to_action(self, synthesis):
        """Test causality score for decision → action pattern."""
        event_a = EpisodicEvent(
            id=1,
            project_id=1,
            session_id="session",
            timestamp=datetime.now(),
            event_type=EventType.DECISION,
            content="Refactoring decision",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(cwd="/test", files=[], task="task1", phase="phase-1"),
        )

        event_b = EpisodicEvent(
            id=2,
            project_id=1,
            session_id="session",
            timestamp=datetime.now() + timedelta(minutes=2),
            event_type=EventType.ACTION,
            content="Implement refactoring",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(cwd="/test", files=[], task="task1", phase="phase-1"),
        )

        causality = synthesis._calculate_causality(event_a, event_b)
        assert causality == 0.8  # Decision → Action is high causality

    def test_calculate_causality_no_relation(self, synthesis):
        """Test causality score for unrelated events."""
        event_a = EpisodicEvent(
            id=1,
            project_id=1,
            session_id="session",
            timestamp=datetime.now(),
            event_type=EventType.ACTION,
            content="Action 1",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(cwd="/test", files=[], task="task1", phase="phase-1"),
        )

        event_b = EpisodicEvent(
            id=2,
            project_id=1,
            session_id="session",
            timestamp=datetime.now() + timedelta(hours=1),
            event_type=EventType.ACTION,
            content="Action 2",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(cwd="/test", files=[], task="task2", phase="phase-2"),
        )

        causality = synthesis._calculate_causality(event_a, event_b)
        assert causality == 0.0  # No relation

    def test_detect_dependency_test_depends_on_build(self, synthesis):
        """Test dependency detection: test depends on build."""
        event_a = EpisodicEvent(
            id=1,
            project_id=1,
            session_id="session",
            timestamp=datetime.now(),
            event_type=EventType.ACTION,
            content="Build project",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(cwd="/test", files=[], task="build", phase="phase-1"),
        )

        event_b = EpisodicEvent(
            id=2,
            project_id=1,
            session_id="session",
            timestamp=datetime.now() + timedelta(minutes=1),
            event_type=EventType.TEST_RUN,
            content="Run tests",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(cwd="/test", files=[], task="test", phase="phase-1"),
        )

        dependency = synthesis._detect_dependency(event_a, event_b)
        assert dependency is True

    def test_calculate_frequency_same_task(self, synthesis):
        """Test frequency calculation for events in same task."""
        event_a = EpisodicEvent(
            id=1,
            project_id=1,
            session_id="session",
            timestamp=datetime.now(),
            event_type=EventType.ACTION,
            content="Action in task1",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(cwd="/test", files=[], task="task1", phase="phase-1"),
        )

        event_b = EpisodicEvent(
            id=2,
            project_id=1,
            session_id="session",
            timestamp=datetime.now() + timedelta(minutes=1),
            event_type=EventType.ACTION,
            content="Another action in task1",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(cwd="/test", files=[], task="task1", phase="phase-1"),
        )

        frequency = synthesis._calculate_frequency(event_a, event_b)
        assert frequency > 0.5  # Same task, same type, same outcome = high frequency

    def test_infer_temporal_relations_two_events(self, synthesis):
        """Test temporal relation inference for two events."""
        now = datetime.now()

        event_a = EpisodicEvent(
            id=1,
            project_id=1,
            session_id="session",
            timestamp=now,
            event_type=EventType.ERROR,
            content="Error occurred",
            outcome=EventOutcome.FAILURE,
            context=EventContext(cwd="/test", files=[], task="task1", phase="phase-1"),
        )

        event_b = EpisodicEvent(
            id=2,
            project_id=1,
            session_id="session",
            timestamp=now + timedelta(minutes=5),
            event_type=EventType.ACTION,
            content="Fixed error",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(cwd="/test", files=[], task="task1", phase="phase-1"),
        )

        relations = synthesis._infer_temporal_relations([event_a, event_b])

        assert len(relations) == 1
        assert isinstance(relations[0], TemporalKGRelation)
        assert relations[0].from_entity == "event_1"
        assert relations[0].to_entity == "event_2"
        assert relations[0].causality == 1.0  # Error → Success
        assert relations[0].dependency is False
        assert relations[0].temporal_score > 0.5

    def test_synthesize_result_structure(self, synthesis, mock_stores):
        """Test that synthesis returns proper result structure."""
        episodic_store, _ = mock_stores

        now = datetime.now()
        events = [
            EpisodicEvent(
                id=1,
                project_id=1,
                session_id="session",
                timestamp=now,
                event_type=EventType.DECISION,
                content="Design decision",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(cwd="/test", files=[], task="task1", phase="phase-1"),
            ),
            EpisodicEvent(
                id=2,
                project_id=1,
                session_id="session",
                timestamp=now + timedelta(minutes=5),
                event_type=EventType.ACTION,
                content="Implement design",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(cwd="/test", files=[], task="task1", phase="phase-1"),
            ),
        ]

        episodic_store.get_events_for_session.return_value = events

        result = synthesis.synthesize(session_id="session")

        assert isinstance(result, KGSynthesisResult)
        assert result.entities_count > 0
        assert result.relations_count > 0
        assert result.latency_ms >= 0.0
        assert 0.0 <= result.quality_score <= 1.0
