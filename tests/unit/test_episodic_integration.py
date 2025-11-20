"""Integration tests for Layer 1 episodic memory fixes."""

import pytest
from datetime import datetime, timedelta
from athena.episodic.models import (
    EpisodicEvent,
    EventType,
    EventOutcome,
)
from athena.episodic.store import EpisodicStore
from athena.episodic.activation import compute_activation
from athena.episodic.surprise import BayesianSurprise


class TestEpisodicIntegration:
    """Integration tests for fixed episodic memory layer."""

    @pytest.fixture
    def store(self):
        """Create episodic store for testing."""
        from athena.core.database import get_database

        db = get_database(dbname="athena_test")
        return EpisodicStore(db)

    def test_full_event_lifecycle(self, store):
        """Test complete event lifecycle: create → store → retrieve → activate."""
        # 1. Create event
        now = datetime.now()
        event = EpisodicEvent(
            project_id=1,
            session_id="test-integration",
            timestamp=now,
            event_type=EventType.ACTION,
            content="Integration test event",
            outcome=EventOutcome.SUCCESS,
            importance_score=0.8,
            actionability_score=0.9,
            has_next_step=True,
            activation_count=0,
        )

        # 2. Convert to row and back (simulates DB round-trip)
        row = {
            "id": 1,
            "project_id": event.project_id,
            "session_id": event.session_id,
            "timestamp": int(now.timestamp()),
            "event_type": "action",
            "content": event.content,
            "outcome": "success",
            "context_cwd": None,
            "context_files": None,
            "context_task": None,
            "context_phase": None,
            "duration_ms": None,
            "files_changed": 0,
            "lines_added": 0,
            "lines_deleted": 0,
            "learned": None,
            "confidence": 1.0,
            "lifecycle_status": "active",
            "consolidation_score": 0.0,
            "last_activation": now,
            "activation_count": 0,
            "importance_score": 0.8,
            "actionability_score": 0.9,
            "context_completeness_score": 0.5,
            "has_next_step": 1,
            "has_blocker": 0,
        }

        # 3. Retrieve from row (tests timestamp fix)
        retrieved = store._row_to_model(row)
        assert retrieved.content == "Integration test event"
        assert retrieved.timestamp is not None
        assert retrieved.event_type == EventType.ACTION
        assert retrieved.outcome == EventOutcome.SUCCESS

        # 4. Calculate activation (tests activation system)
        activation = compute_activation(retrieved)
        assert activation > 0.0
        assert isinstance(activation, (int, float))

    def test_timestamp_conversion_unix_epoch_roundtrip(self, store):
        """Test Unix epoch timestamp conversion roundtrip."""
        now = datetime.now()
        epoch = int(now.timestamp())

        # Parse from epoch
        parsed = store._parse_timestamp(epoch)
        assert isinstance(parsed, datetime)
        assert abs((parsed - now).total_seconds()) < 1

    def test_timestamp_conversion_from_datetime_object(self, store):
        """Test timestamp conversion from datetime object (PostgreSQL native)."""
        now = datetime.now()

        # Parse from datetime object (what PostgreSQL returns)
        parsed = store._parse_timestamp(now)
        assert parsed == now
        assert isinstance(parsed, datetime)

    def test_timestamp_conversion_from_iso_string(self, store):
        """Test timestamp conversion from ISO string format."""
        iso_string = "2024-01-15T10:30:45"

        parsed = store._parse_timestamp(iso_string)
        assert isinstance(parsed, datetime)
        assert parsed.year == 2024
        assert parsed.month == 1
        assert parsed.day == 15

    def test_json_parsing_with_context_files(self, store):
        """Test JSON parsing of context files list."""
        json_str = '["file1.py", "file2.py", "file3.py"]'
        parsed = store._safe_json_loads(json_str)
        assert isinstance(parsed, list)
        assert len(parsed) == 3
        assert "file1.py" in parsed

    def test_enum_handling_unknown_event_type(self, store):
        """Test graceful handling of unknown event types (legacy data)."""
        now = datetime.now()
        row = {
            "id": 1,
            "project_id": 1,
            "session_id": "test",
            "timestamp": int(now.timestamp()),
            "event_type": "unknown_future_type",  # Not in EventType enum
            "content": "Test",
            "outcome": None,
            "context_cwd": None,
            "context_files": None,
            "context_task": None,
            "context_phase": None,
            "duration_ms": None,
            "files_changed": 0,
            "lines_added": 0,
            "lines_deleted": 0,
            "learned": None,
            "confidence": 1.0,
            "lifecycle_status": "active",
            "consolidation_score": 0.0,
            "last_activation": now,
            "activation_count": 0,
            "importance_score": 0.5,
            "actionability_score": 0.5,
            "context_completeness_score": 0.5,
        }

        # Should not raise exception
        event = store._row_to_model(row)
        assert event is not None
        assert event.event_type is None  # Unknown type gracefully becomes None

    def test_activation_decay_with_retrieved_event(self, store):
        """Test activation decay calculation on retrieved event."""
        now = datetime.now()
        old_time = now - timedelta(hours=24)

        # Create row simulating retrieved event from DB
        row = {
            "id": 1,
            "project_id": 1,
            "session_id": "test",
            "timestamp": int(old_time.timestamp()),
            "event_type": "action",
            "content": "Old event",
            "outcome": "success",
            "context_cwd": None,
            "context_files": None,
            "context_task": None,
            "context_phase": None,
            "duration_ms": None,
            "files_changed": 0,
            "lines_added": 0,
            "lines_deleted": 0,
            "learned": None,
            "confidence": 1.0,
            "lifecycle_status": "active",
            "consolidation_score": 0.0,
            "last_activation": old_time,
            "activation_count": 5,  # Accessed 5 times
            "importance_score": 0.9,  # Important
            "actionability_score": 0.8,
            "context_completeness_score": 0.7,
            "has_next_step": 1,
            "has_blocker": 0,
        }

        event = store._row_to_model(row)

        # Calculate activation with reference time as now
        activation = compute_activation(event, current_time=now)

        # Should be positive (base level decay applies)
        assert activation > 0.0
        # Should be reasonable (not extremely high despite importance)
        assert activation < 10.0

    def test_event_with_code_awareness_fields(self, store):
        """Test retrieval of event with code-aware fields."""
        now = datetime.now()
        row = {
            "id": 1,
            "project_id": 1,
            "session_id": "test",
            "timestamp": int(now.timestamp()),
            "event_type": "action",
            "content": "Fixed bug in parser module",
            "outcome": "success",
            "context_cwd": "/home/user/project",
            "context_files": '["src/parser.py"]',
            "context_task": "fix-parser-bug",
            "context_phase": "development",
            "duration_ms": 3600000,
            "files_changed": 1,
            "lines_added": 45,
            "lines_deleted": 10,
            "learned": "Parser needed null-check",
            "confidence": 0.95,
            "lifecycle_status": "active",
            "consolidation_score": 0.6,
            "last_activation": now,
            "activation_count": 2,
            "code_event_type": "bug_discovery",
            "file_path": "src/parser.py",
            "symbol_name": "parse_expr",
            "symbol_type": "method",
            "language": "python",
            "error_type": "AttributeError",
            "stack_trace": "Traceback...",
            "test_name": "test_parse_null",
            "test_passed": 1,
            "importance_score": 0.85,
            "actionability_score": 0.9,
            "context_completeness_score": 0.9,
            "has_next_step": 1,
            "has_blocker": 0,
        }

        event = store._row_to_model(row)

        # Verify code-aware fields
        assert event.file_path == "src/parser.py"
        assert event.symbol_name == "parse_expr"
        assert event.language == "python"
        assert event.error_type == "AttributeError"
        assert event.test_passed is True
        assert event.lines_added == 45
        assert event.lines_deleted == 10

        # Verify activation calculation works with code event
        activation = compute_activation(event)
        assert activation > 0.0

    def test_working_memory_optimization_fields(self, store):
        """Test working memory optimization field retrieval."""
        now = datetime.now()
        row = {
            "id": 1,
            "project_id": 1,
            "session_id": "test",
            "timestamp": int(now.timestamp()),
            "event_type": "action",
            "content": "Schema migration decision needed",
            "outcome": None,
            "context_cwd": None,
            "context_files": None,
            "context_task": None,
            "context_phase": None,
            "duration_ms": None,
            "files_changed": 0,
            "lines_added": 0,
            "lines_deleted": 0,
            "learned": None,
            "confidence": 1.0,
            "lifecycle_status": "active",
            "consolidation_score": 0.0,
            "last_activation": now,
            "activation_count": 0,
            "importance_score": 0.95,  # Very important decision
            "actionability_score": 0.5,  # Needs clarification
            "context_completeness_score": 0.4,  # Incomplete context
            "has_next_step": 0,
            "has_blocker": 1,  # Blocked on something
            "project_name": "athena",
            "project_goal": "Build memory system",
            "project_phase_status": "architecture-phase",
            "required_decisions": '["db-choice", "schema-design"]',
        }

        event = store._row_to_model(row)

        # Verify working memory optimization fields
        assert event.importance_score == 0.95
        assert event.actionability_score == 0.5
        assert event.context_completeness_score == 0.4
        assert event.has_next_step is False
        assert event.has_blocker is True
        assert event.project_name == "athena"
        assert event.project_goal == "Build memory system"
        assert event.required_decisions == '["db-choice", "schema-design"]'

    def test_surprise_event_detection(self):
        """Test surprise event detection for important boundaries."""
        surprise_calc = BayesianSurprise()

        # Simulate normal repetitive text
        tokens = ["the", "same", "the", "same", "the", "same"]
        surprise_normal = surprise_calc.calculate_surprise(tokens, 2)

        # Insert unexpected token
        tokens_unexpected = ["the", "same", "UNEXPECTED", "the", "same"]
        surprise_high = surprise_calc.calculate_surprise(tokens_unexpected, 2)

        # Both should be valid
        assert isinstance(surprise_normal, (int, float))
        assert isinstance(surprise_high, (int, float))

    def test_event_lifecycle_progression(self, store):
        """Test event lifecycle state transitions."""
        now = datetime.now()

        # Create active event
        row_active = self._create_lifecycle_row(
            now, lifecycle_status="active", consolidation_score=0.0
        )
        event_active = store._row_to_model(row_active)
        activation_active = compute_activation(event_active)
        assert activation_active > 0.0

        # Create consolidated event
        row_consolidated = self._create_lifecycle_row(
            now, lifecycle_status="consolidated", consolidation_score=0.8
        )
        event_consolidated = store._row_to_model(row_consolidated)
        activation_consolidated = compute_activation(event_consolidated)
        assert activation_consolidated == 0.0

        # Create archived event
        row_archived = self._create_lifecycle_row(
            now, lifecycle_status="archived", consolidation_score=1.0
        )
        event_archived = store._row_to_model(row_archived)
        activation_archived = compute_activation(event_archived)
        assert activation_archived == 0.0

    @staticmethod
    def _create_lifecycle_row(now, lifecycle_status, consolidation_score):
        """Helper to create lifecycle test row."""
        return {
            "id": 1,
            "project_id": 1,
            "session_id": "test",
            "timestamp": int(now.timestamp()),
            "event_type": "action",
            "content": "Test",
            "outcome": "success",
            "context_cwd": None,
            "context_files": None,
            "context_task": None,
            "context_phase": None,
            "duration_ms": None,
            "files_changed": 0,
            "lines_added": 0,
            "lines_deleted": 0,
            "learned": None,
            "confidence": 1.0,
            "lifecycle_status": lifecycle_status,
            "consolidation_score": consolidation_score,
            "last_activation": now,
            "activation_count": 1,
            "importance_score": 0.5,
            "actionability_score": 0.5,
            "context_completeness_score": 0.5,
        }
