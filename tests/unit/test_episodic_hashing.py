"""Tests for episodic event hashing and deduplication."""

import pytest
from datetime import datetime, timedelta

from src.athena.episodic.hashing import EventHasher, compute_event_hash
from src.athena.episodic.models import (
    EpisodicEvent,
    EventType,
    EventOutcome,
    EventContext,
    CodeEventType,
)


class TestEventHasher:
    """Test suite for EventHasher content-based hashing."""

    @pytest.fixture
    def hasher(self):
        """Create EventHasher instance."""
        return EventHasher()

    @pytest.fixture
    def base_event(self):
        """Create base event for testing."""
        return EpisodicEvent(
            project_id=1,
            session_id="test_session",
            timestamp=datetime(2025, 1, 10, 12, 0, 0),
            event_type=EventType.ACTION,
            content="Test event content",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(
                cwd="/home/user/project",
                files=["test.py"],
                task="Testing",
                phase="development",
            ),
        )

    def test_identical_events_same_hash(self, hasher, base_event):
        """Test that identical events produce the same hash."""
        event1 = base_event
        event2 = base_event.model_copy(deep=True)

        hash1 = hasher.compute_hash(event1)
        hash2 = hasher.compute_hash(event2)

        assert hash1 == hash2, "Identical events should have same hash"
        assert len(hash1) == 64, "SHA256 hash should be 64 hex characters"

    def test_different_content_different_hash(self, hasher, base_event):
        """Test that different content produces different hashes."""
        event1 = base_event
        event2 = base_event.model_copy(deep=True)
        event2.content = "Different content"

        hash1 = hasher.compute_hash(event1)
        hash2 = hasher.compute_hash(event2)

        assert hash1 != hash2, "Different content should produce different hash"

    def test_id_excluded_from_hash(self, hasher, base_event):
        """Test that id field is excluded from hash computation."""
        event1 = base_event.model_copy(deep=True)
        event1.id = None

        event2 = base_event.model_copy(deep=True)
        event2.id = 999

        hash1 = hasher.compute_hash(event1)
        hash2 = hasher.compute_hash(event2)

        assert hash1 == hash2, "ID should be excluded from hash"

    def test_consolidation_status_excluded_from_hash(self, hasher, base_event):
        """Test that consolidation_status is excluded from hash."""
        event1 = base_event.model_copy(deep=True)
        event1.consolidation_status = "unconsolidated"

        event2 = base_event.model_copy(deep=True)
        event2.consolidation_status = "consolidated"

        hash1 = hasher.compute_hash(event1)
        hash2 = hasher.compute_hash(event2)

        assert hash1 == hash2, "Consolidation status should be excluded from hash"

    def test_consolidated_at_excluded_from_hash(self, hasher, base_event):
        """Test that consolidated_at timestamp is excluded from hash."""
        event1 = base_event.model_copy(deep=True)
        event1.consolidated_at = None

        event2 = base_event.model_copy(deep=True)
        event2.consolidated_at = datetime(2025, 1, 11, 12, 0, 0)

        hash1 = hasher.compute_hash(event1)
        hash2 = hasher.compute_hash(event2)

        assert hash1 == hash2, "consolidated_at should be excluded from hash"

    def test_timestamp_included_in_hash(self, hasher, base_event):
        """Test that timestamp IS included in hash (different times = different events)."""
        event1 = base_event.model_copy(deep=True)
        event1.timestamp = datetime(2025, 1, 10, 12, 0, 0)

        event2 = base_event.model_copy(deep=True)
        event2.timestamp = datetime(2025, 1, 10, 13, 0, 0)

        hash1 = hasher.compute_hash(event1)
        hash2 = hasher.compute_hash(event2)

        assert hash1 != hash2, "Timestamp should be included in hash"

    def test_different_event_types_different_hash(self, hasher, base_event):
        """Test that different event types produce different hashes."""
        event1 = base_event.model_copy(deep=True)
        event1.event_type = EventType.ACTION

        event2 = base_event.model_copy(deep=True)
        event2.event_type = EventType.DECISION

        hash1 = hasher.compute_hash(event1)
        hash2 = hasher.compute_hash(event2)

        assert hash1 != hash2, "Different event types should have different hashes"

    def test_different_outcomes_different_hash(self, hasher, base_event):
        """Test that different outcomes produce different hashes."""
        event1 = base_event.model_copy(deep=True)
        event1.outcome = EventOutcome.SUCCESS

        event2 = base_event.model_copy(deep=True)
        event2.outcome = EventOutcome.FAILURE

        hash1 = hasher.compute_hash(event1)
        hash2 = hasher.compute_hash(event2)

        assert hash1 != hash2, "Different outcomes should have different hashes"

    def test_context_included_in_hash(self, hasher, base_event):
        """Test that context differences affect hash."""
        event1 = base_event.model_copy(deep=True)
        event1.context.cwd = "/path/a"

        event2 = base_event.model_copy(deep=True)
        event2.context.cwd = "/path/b"

        hash1 = hasher.compute_hash(event1)
        hash2 = hasher.compute_hash(event2)

        assert hash1 != hash2, "Context changes should affect hash"

    def test_context_files_order_independent(self, hasher, base_event):
        """Test that file order in context affects hash (list order matters)."""
        event1 = base_event.model_copy(deep=True)
        event1.context.files = ["a.py", "b.py"]

        event2 = base_event.model_copy(deep=True)
        event2.context.files = ["b.py", "a.py"]

        hash1 = hasher.compute_hash(event1)
        hash2 = hasher.compute_hash(event2)

        # Lists preserve order in JSON, so different order = different hash
        assert hash1 != hash2, "File order should affect hash (list ordering)"

    def test_metrics_included_in_hash(self, hasher, base_event):
        """Test that metrics are included in hash."""
        event1 = base_event.model_copy(deep=True)
        event1.duration_ms = 1000
        event1.files_changed = 2
        event1.lines_added = 50
        event1.lines_deleted = 10

        event2 = base_event.model_copy(deep=True)
        event2.duration_ms = 2000  # Different metric

        hash1 = hasher.compute_hash(event1)
        hash2 = hasher.compute_hash(event2)

        assert hash1 != hash2, "Metric changes should affect hash"

    def test_learned_included_in_hash(self, hasher, base_event):
        """Test that learned field is included in hash."""
        event1 = base_event.model_copy(deep=True)
        event1.learned = "Learning A"

        event2 = base_event.model_copy(deep=True)
        event2.learned = "Learning B"

        hash1 = hasher.compute_hash(event1)
        hash2 = hasher.compute_hash(event2)

        assert hash1 != hash2, "Learned content should affect hash"

    def test_confidence_included_in_hash(self, hasher, base_event):
        """Test that confidence is included in hash."""
        event1 = base_event.model_copy(deep=True)
        event1.confidence = 0.9

        event2 = base_event.model_copy(deep=True)
        event2.confidence = 0.5

        hash1 = hasher.compute_hash(event1)
        hash2 = hasher.compute_hash(event2)

        assert hash1 != hash2, "Confidence should affect hash"

    def test_code_aware_fields_included(self, hasher, base_event):
        """Test that code-aware fields are included in hash."""
        event1 = base_event.model_copy(deep=True)
        event1.code_event_type = CodeEventType.CODE_EDIT
        event1.file_path = "src/auth.py"
        event1.symbol_name = "authenticate"
        event1.symbol_type = "function"
        event1.language = "python"

        event2 = base_event.model_copy(deep=True)
        event2.code_event_type = CodeEventType.CODE_EDIT
        event2.file_path = "src/utils.py"  # Different file

        hash1 = hasher.compute_hash(event1)
        hash2 = hasher.compute_hash(event2)

        assert hash1 != hash2, "Code-aware fields should affect hash"

    def test_git_metadata_included(self, hasher, base_event):
        """Test that git metadata is included in hash."""
        event1 = base_event.model_copy(deep=True)
        event1.git_commit = "abc123"
        event1.git_author = "dev@example.com"

        event2 = base_event.model_copy(deep=True)
        event2.git_commit = "def456"  # Different commit

        hash1 = hasher.compute_hash(event1)
        hash2 = hasher.compute_hash(event2)

        assert hash1 != hash2, "Git metadata should affect hash"

    def test_test_fields_included(self, hasher, base_event):
        """Test that test-related fields are included in hash."""
        event1 = base_event.model_copy(deep=True)
        event1.test_name = "test_authentication"
        event1.test_passed = True

        event2 = base_event.model_copy(deep=True)
        event2.test_name = "test_authentication"
        event2.test_passed = False

        hash1 = hasher.compute_hash(event1)
        hash2 = hasher.compute_hash(event2)

        assert hash1 != hash2, "Test outcome should affect hash"

    def test_error_fields_included(self, hasher, base_event):
        """Test that error fields are included in hash."""
        event1 = base_event.model_copy(deep=True)
        event1.error_type = "ValueError"
        event1.stack_trace = "Traceback: line 42"

        event2 = base_event.model_copy(deep=True)
        event2.error_type = "TypeError"

        hash1 = hasher.compute_hash(event1)
        hash2 = hasher.compute_hash(event2)

        assert hash1 != hash2, "Error details should affect hash"

    def test_performance_metrics_included(self, hasher, base_event):
        """Test that performance metrics are included in hash."""
        event1 = base_event.model_copy(deep=True)
        event1.performance_metrics = {"cpu": 50, "memory": 100}

        event2 = base_event.model_copy(deep=True)
        event2.performance_metrics = {"cpu": 75, "memory": 150}

        hash1 = hasher.compute_hash(event1)
        hash2 = hasher.compute_hash(event2)

        assert hash1 != hash2, "Performance metrics should affect hash"

    def test_hash_deterministic_across_runs(self, hasher, base_event):
        """Test that hash is deterministic across multiple computations."""
        hashes = [hasher.compute_hash(base_event) for _ in range(10)]

        assert len(set(hashes)) == 1, "Hash should be deterministic"

    def test_hash_collision_resistance(self, hasher):
        """Test that different events produce different hashes (collision resistance)."""
        hashes = set()

        for i in range(1000):
            event = EpisodicEvent(
                project_id=i % 10,
                session_id=f"session_{i}",
                timestamp=datetime(2025, 1, 1) + timedelta(minutes=i),
                event_type=EventType.ACTION,
                content=f"Event content {i}",
                context=EventContext(cwd="/project"),
            )
            hash_val = hasher.compute_hash(event)
            hashes.add(hash_val)

        assert len(hashes) == 1000, "All hashes should be unique (no collisions)"

    def test_should_exclude_field(self, hasher):
        """Test field exclusion logic."""
        assert hasher._should_exclude_field("id") is True
        assert hasher._should_exclude_field("consolidation_status") is True
        assert hasher._should_exclude_field("consolidated_at") is True
        assert hasher._should_exclude_field("content") is False
        assert hasher._should_exclude_field("timestamp") is False

    def test_normalize_datetime(self, hasher):
        """Test datetime normalization to ISO format."""
        dt = datetime(2025, 1, 10, 12, 30, 45, 123456)
        normalized = hasher._normalize_for_hashing(dt)

        assert isinstance(normalized, str)
        assert "2025-01-10" in normalized
        assert "12:30:45" in normalized

    def test_normalize_enum(self, hasher):
        """Test enum normalization to string value."""
        event_type = EventType.ACTION
        normalized = hasher._normalize_for_hashing(event_type)

        assert normalized == "action"
        assert isinstance(normalized, str)

    def test_normalize_nested_dict(self, hasher):
        """Test normalization of nested dictionaries."""
        nested = {
            "a": {"b": datetime(2025, 1, 10)},
            "c": [EventType.ACTION, EventType.DECISION],
        }
        normalized = hasher._normalize_for_hashing(nested)

        assert isinstance(normalized["a"]["b"], str)
        assert normalized["c"][0] == "action"

    def test_serialize_deterministically(self, hasher):
        """Test deterministic JSON serialization."""
        # Different key order should produce same serialization
        dict1 = {"z": 1, "a": 2, "m": 3}
        dict2 = {"a": 2, "m": 3, "z": 1}

        json1 = hasher._serialize_deterministically(dict1)
        json2 = hasher._serialize_deterministically(dict2)

        assert json1 == json2, "Serialization should be order-independent"

    def test_convenience_function(self, base_event):
        """Test convenience compute_event_hash function."""
        hash_val = compute_event_hash(base_event)

        assert isinstance(hash_val, str)
        assert len(hash_val) == 64

    def test_empty_optional_fields(self, hasher):
        """Test events with minimal required fields."""
        minimal_event = EpisodicEvent(
            project_id=1,
            session_id="test",
            event_type=EventType.ACTION,
            content="Minimal event",
        )

        hash_val = hasher.compute_hash(minimal_event)

        assert isinstance(hash_val, str)
        assert len(hash_val) == 64

    def test_code_event_with_diff(self, hasher):
        """Test hashing of code events with diffs."""
        event1 = EpisodicEvent(
            project_id=1,
            session_id="test",
            timestamp=datetime(2025, 1, 10, 12, 0, 0),
            event_type=EventType.ACTION,
            code_event_type=CodeEventType.CODE_EDIT,
            content="Refactored function",
            file_path="src/main.py",
            diff="@@ -10,3 +10,5 @@ def main():\n     print('hello')",
            context=EventContext(cwd="/project"),
        )

        event2 = event1.model_copy(deep=True)
        event2.diff = "@@ -10,3 +10,5 @@ def main():\n     print('goodbye')"

        hash1 = hasher.compute_hash(event1)
        hash2 = hasher.compute_hash(event2)

        assert hash1 != hash2, "Different diffs should produce different hashes"

    def test_real_world_deduplication_scenario(self, hasher):
        """Test realistic deduplication scenario: git hook + CLI both record same commit."""
        # Git hook records commit
        git_event = EpisodicEvent(
            project_id=1,
            session_id="git_hook_session",
            timestamp=datetime(2025, 1, 10, 14, 30, 0),
            event_type=EventType.ACTION,
            code_event_type=CodeEventType.CODE_EDIT,
            content="Fixed authentication bug",
            file_path="src/auth.py",
            git_commit="abc123def456",
            git_author="dev@example.com",
            lines_added=15,
            lines_deleted=3,
            context=EventContext(
                cwd="/home/user/project",
                files=["src/auth.py"],
                branch="feature/auth-fix"
            ),
        )

        # CLI command tries to record same commit (with different internal metadata)
        cli_event = git_event.model_copy(deep=True)
        cli_event.session_id = "cli_session"  # Different session
        cli_event.id = 999  # Different ID (excluded)
        cli_event.consolidation_status = "consolidated"  # Different status (excluded)

        hash_git = hasher.compute_hash(git_event)
        hash_cli = hasher.compute_hash(cli_event)

        # Different sessions = different events (session_id is included in hash)
        assert hash_git != hash_cli, "Different sessions should produce different hashes"

        # Now test with identical session (true duplicate)
        cli_event_duplicate = git_event.model_copy(deep=True)
        cli_event_duplicate.id = 999  # Different ID
        cli_event_duplicate.consolidation_status = "consolidated"

        hash_duplicate = hasher.compute_hash(cli_event_duplicate)
        hash_original = hasher.compute_hash(git_event)

        assert hash_duplicate == hash_original, "True duplicates should have same hash"


class TestEventHasherEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def hasher(self):
        """Create EventHasher instance."""
        return EventHasher()

    def test_none_values(self, hasher):
        """Test handling of None values in optional fields."""
        event = EpisodicEvent(
            project_id=1,
            session_id="test",
            event_type=EventType.ACTION,
            content="Test",
            outcome=None,
            learned=None,
            file_path=None,
        )

        hash_val = hasher.compute_hash(event)
        assert isinstance(hash_val, str)
        assert len(hash_val) == 64

    def test_unicode_content(self, hasher):
        """Test handling of unicode characters in content."""
        event = EpisodicEvent(
            project_id=1,
            session_id="test",
            event_type=EventType.ACTION,
            content="Unicode test: 你好世界 🚀 émojis",
            context=EventContext(cwd="/project"),
        )

        hash_val = hasher.compute_hash(event)
        assert isinstance(hash_val, str)
        assert len(hash_val) == 64

    def test_very_long_content(self, hasher):
        """Test handling of very long content strings."""
        long_content = "x" * 100000  # 100k characters

        event = EpisodicEvent(
            project_id=1,
            session_id="test",
            event_type=EventType.ACTION,
            content=long_content,
            context=EventContext(cwd="/project"),
        )

        hash_val = hasher.compute_hash(event)
        assert isinstance(hash_val, str)
        assert len(hash_val) == 64

    def test_empty_context(self, hasher):
        """Test event with empty context."""
        event = EpisodicEvent(
            project_id=1,
            session_id="test",
            event_type=EventType.ACTION,
            content="Test",
            context=EventContext(),  # Empty context
        )

        hash_val = hasher.compute_hash(event)
        assert isinstance(hash_val, str)

    def test_large_performance_metrics(self, hasher):
        """Test handling of large performance metrics dictionary."""
        metrics = {f"metric_{i}": float(i) for i in range(100)}

        event = EpisodicEvent(
            project_id=1,
            session_id="test",
            event_type=EventType.ACTION,
            content="Performance test",
            performance_metrics=metrics,
            context=EventContext(cwd="/project"),
        )

        hash_val = hasher.compute_hash(event)
        assert isinstance(hash_val, str)
        assert len(hash_val) == 64

    def test_special_characters_in_paths(self, hasher):
        """Test handling of special characters in file paths."""
        event = EpisodicEvent(
            project_id=1,
            session_id="test",
            event_type=EventType.ACTION,
            content="Test",
            file_path="/path/with spaces/and'quotes/and\"doublequotes",
            context=EventContext(
                cwd="/path/with spaces",
                files=["file with spaces.py", "file'with'quotes.py"]
            ),
        )

        hash_val = hasher.compute_hash(event)
        assert isinstance(hash_val, str)
        assert len(hash_val) == 64
