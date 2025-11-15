"""Tests for meta field roundtrip integrity (write-read cycle)."""

import pytest
from datetime import datetime
from src.athena.core.database import Database
from src.athena.episodic.store import EpisodicStore
from src.athena.episodic.models import (
    EpisodicEvent,
    EventType,
    EventOutcome,
    EventContext,
)


class TestMetaFieldRoundtrip:
    """Test suite for meta field persistence through write-read cycles."""

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
        return EpisodicStore(db)

    def test_single_event_roundtrip_all_meta_fields(self, event_store):
        """Test that all meta fields survive a complete write-read cycle."""
        # Create event with all meta fields populated
        original_event = EpisodicEvent(
            project_id=1,
            session_id="roundtrip_test",
            timestamp=datetime(2025, 1, 15, 14, 30, 0),
            event_type=EventType.DISCOVERY,
            content="Testing complete roundtrip with all meta fields",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(
                cwd="/home/user/project",
                files=["test.py", "test_utils.py"],
                task="Implementing meta field persistence",
                phase="development",
            ),
            duration_ms=1500,
            files_changed=2,
            lines_added=45,
            lines_deleted=12,
            learned="Meta fields must be included in read path",
            confidence=0.95,
            # All 9 meta fields with meaningful values
            project_name="Athena Memory System",
            project_goal="Optimize working memory context retrieval",
            project_phase_status="phase_2_implementation",
            importance_score=0.9,
            actionability_score=0.85,
            context_completeness_score=0.95,
            has_next_step=True,
            has_blocker=False,
            required_decisions="Should we cache ranking scores?",
        )

        # Write to database
        event_id = event_store.record_event(original_event)
        assert event_id is not None

        # Read back from database
        retrieved_event = event_store.get_event(event_id)
        assert retrieved_event is not None

        # Verify all meta fields are preserved
        assert retrieved_event.project_name == "Athena Memory System"
        assert retrieved_event.project_goal == "Optimize working memory context retrieval"
        assert retrieved_event.project_phase_status == "phase_2_implementation"
        assert retrieved_event.importance_score == 0.9
        assert retrieved_event.actionability_score == 0.85
        assert retrieved_event.context_completeness_score == 0.95
        assert retrieved_event.has_next_step is True
        assert retrieved_event.has_blocker is False
        assert retrieved_event.required_decisions == "Should we cache ranking scores?"

    def test_batch_roundtrip_meta_fields(self, event_store):
        """Test that meta fields survive batch write and retrieval."""
        # Create multiple events with different meta field values
        events = [
            EpisodicEvent(
                project_id=1,
                session_id="batch_test",
                timestamp=datetime(2025, 1, 15, 14, 0, 0),
                event_type=EventType.ACTION,
                content="First batch event",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(cwd="/home/user/project", files=["main.py"], task="Batch test", phase="test"),
                project_name="Project A",
                importance_score=0.7,
                actionability_score=0.8,
            ),
            EpisodicEvent(
                project_id=1,
                session_id="batch_test",
                timestamp=datetime(2025, 1, 15, 14, 1, 0),
                event_type=EventType.DISCOVERY,
                content="Second batch event",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(cwd="/home/user/project", files=["utils.py"], task="Batch test", phase="test"),
                project_name="Project B",
                importance_score=0.6,
                actionability_score=0.7,
            ),
            EpisodicEvent(
                project_id=1,
                session_id="batch_test",
                timestamp=datetime(2025, 1, 15, 14, 2, 0),
                event_type=EventType.ACTION,
                content="Third batch event",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(cwd="/home/user/project", files=["test.py"], task="Batch test", phase="test"),
                project_name="Project C",
                importance_score=0.8,
                actionability_score=0.9,
            ),
        ]

        # Write in batch
        event_ids = event_store.batch_record_events(events)
        assert len(event_ids) == 3

        # Read back and verify each event's meta fields
        for i, event_id in enumerate(event_ids):
            retrieved = event_store.get_event(event_id)
            assert retrieved is not None
            assert retrieved.project_name == f"Project {chr(65+i)}"  # A, B, C
            assert retrieved.importance_score == [0.7, 0.6, 0.8][i]
            assert retrieved.actionability_score == [0.8, 0.7, 0.9][i]

    def test_default_meta_values_roundtrip(self, event_store):
        """Test that default meta field values are preserved through roundtrip."""
        # Create event without setting meta fields (use defaults)
        event = EpisodicEvent(
            project_id=1,
            session_id="defaults_test",
            timestamp=datetime(2025, 1, 15, 15, 0, 0),
            event_type=EventType.ACTION,
            content="Event with default meta values",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(cwd="/home/user/project", files=[], task="Default test", phase="test"),
            # Not setting any meta fields
        )

        # Write and read back
        event_id = event_store.record_event(event)
        retrieved = event_store.get_event(event_id)

        assert retrieved is not None
        # Verify defaults are preserved
        assert retrieved.project_name is None
        assert retrieved.project_goal is None
        assert retrieved.project_phase_status is None
        assert retrieved.importance_score == 0.5  # Default
        assert retrieved.actionability_score == 0.5  # Default
        assert retrieved.context_completeness_score == 0.5  # Default
        assert retrieved.has_next_step is False  # Default
        assert retrieved.has_blocker is False  # Default
        assert retrieved.required_decisions is None

    def test_partial_meta_fields_roundtrip(self, event_store):
        """Test that partial meta field assignments roundtrip correctly."""
        # Create event with only some meta fields set
        event = EpisodicEvent(
            project_id=1,
            session_id="partial_test",
            timestamp=datetime(2025, 1, 15, 15, 30, 0),
            event_type=EventType.ACTION,
            content="Event with partial meta fields",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(cwd="/home/user/project", files=[], task="Partial test", phase="test"),
            project_name="Partial Project",
            importance_score=0.75,
            has_next_step=True,
            # Other fields left as default/None
        )

        event_id = event_store.record_event(event)
        retrieved = event_store.get_event(event_id)

        # Verify set fields
        assert retrieved.project_name == "Partial Project"
        assert retrieved.importance_score == 0.75
        assert retrieved.has_next_step is True

        # Verify unset fields have defaults
        assert retrieved.project_goal is None
        assert retrieved.actionability_score == 0.5
        assert retrieved.has_blocker is False

    def test_get_events_by_date_includes_meta_fields(self, event_store):
        """Test that events retrieved via date range include meta fields."""
        events = [
            EpisodicEvent(
                project_id=1,
                session_id="date_test",
                timestamp=datetime(2025, 1, 15, 10, 0, 0),
                event_type=EventType.ACTION,
                content="Event 1",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(cwd="/home/user/project", files=[], task="Date test", phase="test"),
                project_name="EventA",
                importance_score=0.6,
            ),
            EpisodicEvent(
                project_id=1,
                session_id="date_test",
                timestamp=datetime(2025, 1, 15, 12, 0, 0),
                event_type=EventType.ACTION,
                content="Event 2",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(cwd="/home/user/project", files=[], task="Date test", phase="test"),
                project_name="EventB",
                importance_score=0.7,
            ),
        ]

        event_store.batch_record_events(events)

        # Retrieve by date range
        retrieved = event_store.get_events_by_date(
            start_time=datetime(2025, 1, 15, 0, 0, 0),
            end_time=datetime(2025, 1, 15, 23, 59, 59),
            project_id=1
        )

        assert len(retrieved) >= 2
        # Verify meta fields are present in retrieved events
        for event in retrieved:
            if event.session_id == "date_test":
                assert event.project_name in ["EventA", "EventB"]
                assert event.importance_score in [0.6, 0.7]

    def test_boolean_meta_fields_conversion(self, event_store):
        """Test that boolean meta fields are correctly converted to/from integers."""
        # Create event with explicit boolean values
        event = EpisodicEvent(
            project_id=1,
            session_id="bool_test",
            timestamp=datetime(2025, 1, 15, 16, 0, 0),
            event_type=EventType.ACTION,
            content="Testing boolean conversion",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(cwd="/home/user/project", files=[], task="Bool test", phase="test"),
            has_next_step=True,
            has_blocker=True,
        )

        event_id = event_store.record_event(event)

        # Verify directly in database (should be 1, not True)
        cursor = event_store.execute(
            "SELECT has_next_step, has_blocker FROM episodic_events WHERE id = %s",
            (event_id,)
        )
        db_has_next_step, db_has_blocker = cursor.fetchone()
        assert db_has_next_step == 1  # True stored as 1
        assert db_has_blocker == 1  # True stored as 1

        # Verify roundtrip through model
        retrieved = event_store.get_event(event_id)
        assert retrieved.has_next_step is True
        assert retrieved.has_blocker is True
