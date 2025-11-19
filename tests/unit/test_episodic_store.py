"""Tests for episodic memory storage operations."""

import pytest
from datetime import datetime, timedelta
from athena.episodic.models import (
    EpisodicEvent,
    EventType,
    EventOutcome,
    EventContext,
)
from athena.episodic.store import EpisodicStore
from athena.core.database import get_database, reset_database


@pytest.fixture
def db():
    """Get database instance for testing."""
    return get_database(dbname="athena_test")


@pytest.fixture
def episodic_store(db):
    """Create episodic store for testing."""
    return EpisodicStore(db)


@pytest.fixture
def test_event():
    """Create a test event."""
    return EpisodicEvent(
        project_id=1,
        session_id="test-session",
        timestamp=datetime.now(),
        event_type=EventType.ACTION,
        content="Test event content",
        outcome=EventOutcome.SUCCESS,
        confidence=0.9,
        importance_score=0.8,
    )


class TestEpisodicStoreParsing:
    """Test row-to-model conversion with various timestamp formats."""

    def test_parse_timestamp_with_unix_epoch(self, episodic_store):
        """Test _parse_timestamp with Unix epoch integer."""
        now = datetime.now()
        epoch = int(now.timestamp())
        parsed = episodic_store._parse_timestamp(epoch)
        assert isinstance(parsed, datetime)
        # Allow small tolerance for timestamp conversion
        assert abs((parsed - now).total_seconds()) < 1

    def test_parse_timestamp_with_datetime_object(self, episodic_store):
        """Test _parse_timestamp with datetime object."""
        now = datetime.now()
        parsed = episodic_store._parse_timestamp(now)
        assert parsed == now

    def test_parse_timestamp_with_none(self, episodic_store):
        """Test _parse_timestamp with None."""
        parsed = episodic_store._parse_timestamp(None)
        assert parsed is None

    def test_parse_timestamp_with_string_iso(self, episodic_store):
        """Test _parse_timestamp with ISO format string."""
        iso_string = "2024-01-15T10:30:00"
        parsed = episodic_store._parse_timestamp(iso_string)
        assert isinstance(parsed, datetime)
        assert parsed.year == 2024
        assert parsed.month == 1
        assert parsed.day == 15

    def test_parse_timestamp_with_invalid_value(self, episodic_store):
        """Test _parse_timestamp with invalid value."""
        parsed = episodic_store._parse_timestamp("invalid")
        assert parsed is None

    def test_parse_timestamp_with_float(self, episodic_store):
        """Test _parse_timestamp with float Unix epoch."""
        now = datetime.now()
        epoch = float(now.timestamp())
        parsed = episodic_store._parse_timestamp(epoch)
        assert isinstance(parsed, datetime)


class TestEpisodicStoreSafeJsonLoads:
    """Test JSON parsing with fallback."""

    def test_safe_json_loads_valid_json(self, episodic_store):
        """Test parsing valid JSON."""
        json_str = '{"key": "value"}'
        result = episodic_store._safe_json_loads(json_str)
        assert result == {"key": "value"}

    def test_safe_json_loads_invalid_json(self, episodic_store):
        """Test parsing invalid JSON returns default (empty dict)."""
        result = episodic_store._safe_json_loads("invalid json")
        assert result == {}

    def test_safe_json_loads_with_default(self, episodic_store):
        """Test parsing with custom default."""
        result = episodic_store._safe_json_loads("invalid", default={"default": True})
        assert result == {"default": True}

    def test_safe_json_loads_empty_string(self, episodic_store):
        """Test parsing empty string returns default."""
        result = episodic_store._safe_json_loads("")
        assert result is None


class TestEpisodicStoreRowToModel:
    """Test database row to model conversion."""

    def test_row_to_model_with_all_fields(self, episodic_store):
        """Test converting row with all fields populated."""
        now = datetime.now()
        row = {
            "id": 1,
            "project_id": 1,
            "session_id": "test",
            "timestamp": int(now.timestamp()),
            "event_type": "action",
            "content": "Test content",
            "outcome": "success",
            "context_cwd": "/home/user",
            "context_files": '["file1.py"]',
            "context_task": "test-task",
            "context_phase": "development",
            "duration_ms": 1000,
            "files_changed": 2,
            "lines_added": 10,
            "lines_deleted": 5,
            "learned": "Something interesting",
            "confidence": 0.9,
            "lifecycle_status": "active",
            "consolidation_score": 0.5,
            "last_activation": now,
            "activation_count": 3,
            "code_event_type": None,
            "importance_score": 0.7,
            "actionability_score": 0.6,
            "context_completeness_score": 0.8,
            "has_next_step": 1,
            "has_blocker": 0,
        }

        event = episodic_store._row_to_model(row)

        assert event.id == 1
        assert event.project_id == 1
        assert event.session_id == "test"
        assert event.content == "Test content"
        assert event.event_type == EventType.ACTION
        assert event.outcome == EventOutcome.SUCCESS
        assert event.files_changed == 2
        assert event.lines_added == 10
        assert event.confidence == 0.9
        assert event.lifecycle_status == "active"
        assert event.activation_count == 3
        assert event.has_next_step is True
        assert event.has_blocker is False

    def test_row_to_model_with_unknown_event_type(self, episodic_store):
        """Test conversion with unknown event type (legacy data)."""
        row = {
            "id": 1,
            "project_id": 1,
            "session_id": "test",
            "timestamp": int(datetime.now().timestamp()),
            "event_type": "unknown_type",
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
            "last_activation": datetime.now(),
            "activation_count": 0,
            "importance_score": 0.5,
            "actionability_score": 0.5,
            "context_completeness_score": 0.5,
        }

        # Should not raise, should handle unknown type gracefully
        event = episodic_store._row_to_model(row)
        assert event.id == 1
        assert event.event_type is None  # Unknown types become None

    def test_row_to_model_with_missing_optional_fields(self, episodic_store):
        """Test conversion with missing optional fields."""
        row = {
            "id": 1,
            "project_id": 1,
            "session_id": "test",
            "timestamp": int(datetime.now().timestamp()),
            "event_type": "action",
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
            "last_activation": datetime.now(),
            "activation_count": 0,
            "importance_score": 0.5,
            "actionability_score": 0.5,
            "context_completeness_score": 0.5,
            # Intentionally missing code event fields
        }

        event = episodic_store._row_to_model(row)
        assert event.code_event_type is None
        assert event.file_path is None
        assert event.symbol_name is None

    def test_row_to_model_with_code_event_fields(self, episodic_store):
        """Test conversion with code event fields."""
        now = datetime.now()
        row = {
            "id": 1,
            "project_id": 1,
            "session_id": "test",
            "timestamp": int(now.timestamp()),
            "event_type": "action",
            "content": "Fixed parser",
            "outcome": "success",
            "context_cwd": "/home/user",
            "context_files": None,
            "context_task": None,
            "context_phase": None,
            "duration_ms": None,
            "files_changed": 1,
            "lines_added": 20,
            "lines_deleted": 5,
            "learned": None,
            "confidence": 1.0,
            "lifecycle_status": "active",
            "consolidation_score": 0.0,
            "last_activation": now,
            "activation_count": 1,
            "code_event_type": "bug_discovery",
            "file_path": "src/parser.py",
            "symbol_name": "parse",
            "symbol_type": "function",
            "language": "python",
            "error_type": "ValueError",
            "stack_trace": "Traceback...",
            "test_passed": 1,
            "test_name": "test_parser",
            "importance_score": 0.7,
            "actionability_score": 0.6,
            "context_completeness_score": 0.8,
        }

        event = episodic_store._row_to_model(row)
        # code_event_type should be converted from "bug_discovery" string to enum
        assert event.code_event_type is not None
        # Check it's the correct type (enum value string)
        assert "bug_discovery" in str(event.code_event_type)
        assert event.file_path == "src/parser.py"
        assert event.symbol_name == "parse"
        assert event.language == "python"
        assert event.error_type == "ValueError"
        assert event.test_passed is True

    def test_row_to_model_test_passed_conversion(self, episodic_store):
        """Test boolean conversion from SQLite integer."""
        now = datetime.now()

        # Test with 1 (true)
        row_true = self._create_minimal_row(now, test_passed=1)
        event_true = episodic_store._row_to_model(row_true)
        assert event_true.test_passed is True

        # Test with 0 (false)
        row_false = self._create_minimal_row(now, test_passed=0)
        event_false = episodic_store._row_to_model(row_false)
        assert event_false.test_passed is False

        # Test with None
        row_none = self._create_minimal_row(now, test_passed=None)
        event_none = episodic_store._row_to_model(row_none)
        assert event_none.test_passed is None

    @staticmethod
    def _create_minimal_row(now, **kwargs):
        """Helper to create minimal row dict."""
        row = {
            "id": 1,
            "project_id": 1,
            "session_id": "test",
            "timestamp": int(now.timestamp()),
            "event_type": "action",
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
        row.update(kwargs)
        return row
