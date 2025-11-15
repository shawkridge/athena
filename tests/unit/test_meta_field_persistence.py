"""Tests for meta field persistence in episodic events."""

import pytest
from datetime import datetime
from src.athena.core.database import Database
from src.athena.episodic.store import EpisodicEventStore
from src.athena.episodic.models import (
    EpisodicEvent,
    EventType,
    EventOutcome,
    EventContext,
)


class TestMetaFieldPersistence:
    """Test suite for meta field persistence in episodic events."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a test database instance."""
        db = Database(":memory:")
        db.initialize()
        yield db
        db.close()

    @pytest.fixture
    def event_store(self, db):
        """Create an episodic event store."""
        return EpisodicEventStore(db)

    @pytest.fixture
    def event_with_meta(self):
        """Create an episodic event with all meta fields set."""
        return EpisodicEvent(
            project_id=1,
            session_id="test_session",
            timestamp=datetime(2025, 1, 15, 12, 0, 0),
            event_type=EventType.ACTION,
            content="Test event with meta information",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(
                cwd="/home/user/project",
                files=["test.py"],
                task="Testing meta fields",
                phase="development",
            ),
            # Meta fields
            project_name="Athena Memory System",
            project_goal="Implement working memory context optimization",
            project_phase_status="development",
            importance_score=0.8,
            actionability_score=0.7,
            context_completeness_score=0.9,
            has_next_step=True,
            has_blocker=False,
            required_decisions="Should we use vector DB or PostgreSQL native vectors?",
        )

    def test_meta_fields_persisted_on_record(self, event_store, event_with_meta):
        """Test that meta fields are persisted when recording an event."""
        # Record the event
        event_id = event_store.record_event(event_with_meta)
        assert event_id is not None, "Event should be recorded and return an ID"

        # Retrieve the event directly from database
        cursor = event_store.execute(
            "SELECT project_name, project_goal, project_phase_status, "
            "importance_score, actionability_score, context_completeness_score, "
            "has_next_step, has_blocker, required_decisions "
            "FROM episodic_events WHERE id = %s",
            (event_id,)
        )
        result = cursor.fetchone()

        assert result is not None, "Event should be retrievable from database"
        (
            project_name,
            project_goal,
            project_phase_status,
            importance_score,
            actionability_score,
            context_completeness_score,
            has_next_step,
            has_blocker,
            required_decisions,
        ) = result

        # Verify all meta fields match what was stored
        assert project_name == "Athena Memory System"
        assert project_goal == "Implement working memory context optimization"
        assert project_phase_status == "development"
        assert importance_score == 0.8
        assert actionability_score == 0.7
        assert context_completeness_score == 0.9
        assert has_next_step == 1  # Boolean converted to int in database
        assert has_blocker == 0  # False -> 0
        assert required_decisions == "Should we use vector DB or PostgreSQL native vectors?"

    def test_meta_fields_with_batch_insert(self, event_store):
        """Test that meta fields are persisted in batch inserts."""
        events = [
            EpisodicEvent(
                project_id=1,
                session_id="test_session",
                timestamp=datetime(2025, 1, 15, 12, 0, 0),
                event_type=EventType.ACTION,
                content="Batch event 1",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(
                    cwd="/home/user/project",
                    files=["test.py"],
                    task="Batch testing",
                    phase="development",
                ),
                project_name="Athena",
                project_goal="Test batch meta fields",
                importance_score=0.6,
                actionability_score=0.5,
            ),
            EpisodicEvent(
                project_id=1,
                session_id="test_session",
                timestamp=datetime(2025, 1, 15, 12, 1, 0),
                event_type=EventType.DISCOVERY,
                content="Batch event 2",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(
                    cwd="/home/user/project",
                    files=["test.py"],
                    task="Batch testing",
                    phase="development",
                ),
                project_name="Athena",
                project_goal="Test batch meta fields",
                importance_score=0.7,
                actionability_score=0.6,
            ),
        ]

        # Record events in batch
        event_ids = event_store.batch_record_events(events)
        assert len(event_ids) == 2, "Both events should be recorded"

        # Verify meta fields for first event
        cursor = event_store.execute(
            "SELECT project_name, importance_score, actionability_score FROM episodic_events WHERE id = %s",
            (event_ids[0],)
        )
        result = cursor.fetchone()
        assert result[0] == "Athena"
        assert result[1] == 0.6
        assert result[2] == 0.5

        # Verify meta fields for second event
        cursor = event_store.execute(
            "SELECT project_name, importance_score, actionability_score FROM episodic_events WHERE id = %s",
            (event_ids[1],)
        )
        result = cursor.fetchone()
        assert result[0] == "Athena"
        assert result[1] == 0.7
        assert result[2] == 0.6

    def test_default_meta_field_values(self, event_store):
        """Test that default meta field values are used when not specified."""
        event = EpisodicEvent(
            project_id=1,
            session_id="test_session",
            timestamp=datetime(2025, 1, 15, 12, 0, 0),
            event_type=EventType.ACTION,
            content="Event with default meta values",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(
                cwd="/home/user/project",
                files=["test.py"],
                task="Testing defaults",
                phase="development",
            ),
            # Not setting any meta fields - should use defaults
        )

        event_id = event_store.record_event(event)
        assert event_id is not None

        # Retrieve and check defaults
        cursor = event_store.execute(
            "SELECT importance_score, actionability_score, context_completeness_score, "
            "has_next_step, has_blocker, project_name, project_goal "
            "FROM episodic_events WHERE id = %s",
            (event_id,)
        )
        result = cursor.fetchone()

        importance_score, actionability_score, context_completeness_score, has_next_step, has_blocker, project_name, project_goal = result

        assert importance_score == 0.5, "Default importance_score should be 0.5"
        assert actionability_score == 0.5, "Default actionability_score should be 0.5"
        assert context_completeness_score == 0.5, "Default context_completeness_score should be 0.5"
        assert has_next_step == 0, "Default has_next_step should be False (0)"
        assert has_blocker == 0, "Default has_blocker should be False (0)"
        assert project_name is None, "Default project_name should be None"
        assert project_goal is None, "Default project_goal should be None"

    def test_working_memory_ranking_view(self, event_store, event_with_meta):
        """Test that the working memory ranking view calculates combined_rank correctly."""
        event_id = event_store.record_event(event_with_meta)
        assert event_id is not None

        # Query the working memory ranking view
        cursor = event_store.execute(
            "SELECT combined_rank FROM v_working_memory_ranked WHERE id = %s",
            (event_id,)
        )
        result = cursor.fetchone()

        assert result is not None, "Event should appear in working memory ranking view"
        combined_rank = result[0]

        # combined_rank = importance_score × context_completeness_score × actionability_score
        expected_rank = 0.8 * 0.9 * 0.7  # 0.504
        assert combined_rank == pytest.approx(expected_rank, rel=0.001), f"Combined rank should be {expected_rank}, got {combined_rank}"
