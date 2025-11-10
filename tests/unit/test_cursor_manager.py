"""Unit tests for cursor management system."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from athena.core.database import Database
from athena.episodic.cursor import (
    APILogCursor,
    CursorManager,
    EventSourceCursor,
    FileSystemCursor,
    GitHubCursor,
    SlackCursor,
    get_cursor_schema,
)


@pytest.fixture
def db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test.db"
    return Database(str(db_path))


@pytest.fixture
def cursor_mgr(db):
    """Create cursor manager with test database."""
    return CursorManager(db)


# ============================================================================
# Cursor Schema Tests
# ============================================================================


class TestFileSystemCursor:
    """Test FileSystemCursor schema."""

    def test_create_empty_cursor(self):
        """Test creating empty cursor."""
        cursor = FileSystemCursor()
        assert cursor.last_scan_time is None
        assert cursor.processed_files == {}

    def test_create_cursor_with_data(self):
        """Test creating cursor with initial data."""
        now = datetime.now()
        cursor = FileSystemCursor(
            last_scan_time=now,
            processed_files={"/file1.py": now, "/file2.py": now}
        )
        assert cursor.last_scan_time == now
        assert len(cursor.processed_files) == 2

    def test_cursor_serialization(self):
        """Test cursor to_dict and from_dict."""
        now = datetime.now()
        cursor = FileSystemCursor(
            last_scan_time=now,
            processed_files={"/file1.py": now}
        )

        # Serialize
        data = cursor.to_dict()
        assert "last_scan_time" in data
        assert "processed_files" in data

        # Deserialize
        restored = FileSystemCursor.from_dict(data)
        assert restored.last_scan_time is not None
        assert abs((restored.last_scan_time - now).total_seconds()) < 1
        assert "/file1.py" in restored.processed_files


class TestGitHubCursor:
    """Test GitHubCursor schema."""

    def test_create_empty_cursor(self):
        """Test creating empty cursor."""
        cursor = GitHubCursor()
        assert cursor.last_event_id is None
        assert cursor.last_sync_timestamp is None
        assert cursor.repositories == {}

    def test_create_cursor_with_data(self):
        """Test creating cursor with repository tracking."""
        now = datetime.now()
        cursor = GitHubCursor(
            last_event_id="event_123",
            last_sync_timestamp=now,
            repositories={"user/repo1": "abc123", "user/repo2": "def456"}
        )
        assert cursor.last_event_id == "event_123"
        assert len(cursor.repositories) == 2

    def test_cursor_serialization(self):
        """Test cursor to_dict and from_dict."""
        now = datetime.now()
        cursor = GitHubCursor(
            last_event_id="event_123",
            last_sync_timestamp=now,
            repositories={"user/repo": "sha123"}
        )

        data = cursor.to_dict()
        restored = GitHubCursor.from_dict(data)

        assert restored.last_event_id == "event_123"
        assert restored.repositories == {"user/repo": "sha123"}


class TestSlackCursor:
    """Test SlackCursor schema."""

    def test_create_empty_cursor(self):
        """Test creating empty cursor."""
        cursor = SlackCursor()
        assert cursor.channel_cursors == {}
        assert cursor.last_sync_timestamp is None

    def test_create_cursor_with_channels(self):
        """Test creating cursor with channel tracking."""
        cursor = SlackCursor(
            channel_cursors={"C123": "1234567890.123456", "C456": "1234567891.654321"}
        )
        assert len(cursor.channel_cursors) == 2
        assert cursor.channel_cursors["C123"] == "1234567890.123456"

    def test_cursor_serialization(self):
        """Test cursor to_dict and from_dict."""
        now = datetime.now()
        cursor = SlackCursor(
            channel_cursors={"C123": "1234567890.123456"},
            last_sync_timestamp=now
        )

        data = cursor.to_dict()
        restored = SlackCursor.from_dict(data)

        assert restored.channel_cursors == {"C123": "1234567890.123456"}
        assert restored.last_sync_timestamp is not None


class TestAPILogCursor:
    """Test APILogCursor schema."""

    def test_create_empty_cursor(self):
        """Test creating empty cursor."""
        cursor = APILogCursor()
        assert cursor.last_log_id is None
        assert cursor.last_timestamp is None

    def test_create_cursor_with_data(self):
        """Test creating cursor with log tracking."""
        now = datetime.now()
        cursor = APILogCursor(last_log_id=12345, last_timestamp=now)
        assert cursor.last_log_id == 12345
        assert cursor.last_timestamp == now

    def test_cursor_serialization(self):
        """Test cursor to_dict and from_dict."""
        now = datetime.now()
        cursor = APILogCursor(last_log_id=12345, last_timestamp=now)

        data = cursor.to_dict()
        restored = APILogCursor.from_dict(data)

        assert restored.last_log_id == 12345
        assert restored.last_timestamp is not None


# ============================================================================
# EventSourceCursor Tests
# ============================================================================


class TestEventSourceCursor:
    """Test generic EventSourceCursor wrapper."""

    def test_untyped_cursor(self):
        """Test untyped cursor (raw dict)."""
        cursor = EventSourceCursor(data={"offset": 0, "page": 1})
        assert cursor.get() == {"offset": 0, "page": 1}

        # Update cursor
        cursor.update(offset=100, page=2)
        assert cursor.get()["offset"] == 100
        assert cursor.get()["page"] == 2

    def test_typed_cursor(self):
        """Test typed cursor with schema."""
        cursor = EventSourceCursor(
            cursor_schema=FileSystemCursor,
            data={"last_scan_time": None, "processed_files": {}}
        )

        # Update with datetime
        now = datetime.now()
        cursor.update(last_scan_time=now)
        data = cursor.get()
        assert "last_scan_time" in data

    def test_cursor_reset(self):
        """Test cursor reset."""
        cursor = EventSourceCursor(data={"key": "value"})
        cursor.reset()
        assert cursor.get() == {}


# ============================================================================
# CursorManager Tests
# ============================================================================


class TestCursorManager:
    """Test CursorManager persistence operations."""

    def test_schema_initialization(self, cursor_mgr):
        """Test that database schema is created."""
        cursor = cursor_mgr.db.conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='event_source_cursors'
        """)
        assert cursor.fetchone() is not None

    def test_store_and_retrieve_cursor(self, cursor_mgr):
        """Test storing and retrieving cursor."""
        source_id = "test_source_1"
        cursor_data = {"offset": 100, "last_id": "abc123"}

        # Store cursor
        cursor_mgr.update_cursor(source_id, cursor_data)

        # Retrieve cursor
        retrieved = cursor_mgr.get_cursor(source_id)
        assert retrieved == cursor_data

    def test_retrieve_nonexistent_cursor(self, cursor_mgr):
        """Test retrieving cursor that doesn't exist."""
        cursor_data = cursor_mgr.get_cursor("nonexistent")
        assert cursor_data is None

    def test_update_existing_cursor(self, cursor_mgr):
        """Test updating existing cursor (upsert)."""
        source_id = "test_source_2"

        # Initial store
        cursor_mgr.update_cursor(source_id, {"offset": 0})

        # Update
        cursor_mgr.update_cursor(source_id, {"offset": 100, "page": 2})

        # Retrieve
        retrieved = cursor_mgr.get_cursor(source_id)
        assert retrieved["offset"] == 100
        assert retrieved["page"] == 2

    def test_delete_cursor(self, cursor_mgr):
        """Test deleting cursor."""
        source_id = "test_source_3"

        # Store cursor
        cursor_mgr.update_cursor(source_id, {"data": "test"})

        # Delete cursor
        deleted = cursor_mgr.delete_cursor(source_id)
        assert deleted is True

        # Verify deletion
        retrieved = cursor_mgr.get_cursor(source_id)
        assert retrieved is None

    def test_delete_nonexistent_cursor(self, cursor_mgr):
        """Test deleting cursor that doesn't exist."""
        deleted = cursor_mgr.delete_cursor("nonexistent")
        assert deleted is False

    def test_list_cursors(self, cursor_mgr):
        """Test listing all cursors."""
        # Store multiple cursors
        cursor_mgr.update_cursor("source1", {"offset": 0})
        cursor_mgr.update_cursor("source2", {"offset": 100})
        cursor_mgr.update_cursor("source3", {"offset": 200})

        # List all cursors
        all_cursors = cursor_mgr.list_cursors()
        assert len(all_cursors) == 3

        # Verify structure
        for cursor_info in all_cursors:
            assert "source_id" in cursor_info
            assert "cursor_data" in cursor_info
            assert "updated_at" in cursor_info
            assert isinstance(cursor_info["updated_at"], datetime)

    def test_list_cursors_empty(self, cursor_mgr):
        """Test listing cursors when none exist."""
        all_cursors = cursor_mgr.list_cursors()
        assert all_cursors == []

    def test_cursor_updated_at_timestamp(self, cursor_mgr):
        """Test that updated_at timestamp is set correctly."""
        source_id = "test_source_4"
        before = datetime.now()

        cursor_mgr.update_cursor(source_id, {"data": "test"})

        after = datetime.now()

        cursors = cursor_mgr.list_cursors()
        assert len(cursors) == 1
        updated_at = cursors[0]["updated_at"]

        # Verify timestamp is within range (allow for integer timestamp precision loss)
        # The database stores timestamps as integers (seconds), so we lose sub-second precision
        assert (before - timedelta(seconds=1)) <= updated_at <= (after + timedelta(seconds=1))


# ============================================================================
# Integration Tests
# ============================================================================


class TestCursorIntegration:
    """Test cursor system integration scenarios."""

    def test_full_sync_workflow(self, cursor_mgr):
        """Test full sync workflow (first-time sync)."""
        source_id = "filesystem:/project"

        # Check no cursor exists
        cursor_data = cursor_mgr.get_cursor(source_id)
        assert cursor_data is None

        # Simulate full sync
        now = datetime.now()
        cursor = FileSystemCursor(
            last_scan_time=now,
            processed_files={
                "/file1.py": now,
                "/file2.py": now,
            }
        )

        # Save cursor after sync
        cursor_mgr.update_cursor(source_id, cursor.to_dict())

        # Verify cursor was saved
        retrieved = cursor_mgr.get_cursor(source_id)
        assert retrieved is not None
        assert "last_scan_time" in retrieved
        assert "processed_files" in retrieved
        assert len(retrieved["processed_files"]) == 2

    def test_incremental_sync_workflow(self, cursor_mgr):
        """Test incremental sync workflow (subsequent sync)."""
        source_id = "github:user/repo"

        # Initial sync (full)
        initial_cursor = GitHubCursor(
            last_event_id="event_100",
            last_sync_timestamp=datetime.now(),
            repositories={"user/repo": "abc123"}
        )
        cursor_mgr.update_cursor(source_id, initial_cursor.to_dict())

        # Simulate incremental sync
        cursor_data = cursor_mgr.get_cursor(source_id)
        assert cursor_data is not None

        cursor = GitHubCursor.from_dict(cursor_data)
        assert cursor.last_event_id == "event_100"

        # Update cursor after incremental sync
        cursor.last_event_id = "event_200"
        cursor.last_sync_timestamp = datetime.now()
        cursor.repositories["user/repo"] = "def456"

        cursor_mgr.update_cursor(source_id, cursor.to_dict())

        # Verify update
        updated_cursor = cursor_mgr.get_cursor(source_id)
        restored = GitHubCursor.from_dict(updated_cursor)
        assert restored.last_event_id == "event_200"
        assert restored.repositories["user/repo"] == "def456"

    def test_multi_channel_slack_sync(self, cursor_mgr):
        """Test Slack multi-channel sync workflow."""
        source_id = "slack:workspace123"

        # Initial sync for multiple channels
        cursor = SlackCursor(
            channel_cursors={
                "C001": "1234567890.123456",
                "C002": "1234567891.654321",
                "C003": "1234567892.111111",
            },
            last_sync_timestamp=datetime.now()
        )
        cursor_mgr.update_cursor(source_id, cursor.to_dict())

        # Incremental sync: update one channel
        cursor_data = cursor_mgr.get_cursor(source_id)
        cursor = SlackCursor.from_dict(cursor_data)

        cursor.channel_cursors["C001"] = "1234567893.999999"  # New message in C001
        cursor.last_sync_timestamp = datetime.now()

        cursor_mgr.update_cursor(source_id, cursor.to_dict())

        # Verify update
        updated = cursor_mgr.get_cursor(source_id)
        restored = SlackCursor.from_dict(updated)
        assert restored.channel_cursors["C001"] == "1234567893.999999"
        assert restored.channel_cursors["C002"] == "1234567891.654321"  # Unchanged

    def test_api_log_sequential_sync(self, cursor_mgr):
        """Test API log sequential sync workflow."""
        source_id = "api_log:service_logs"

        # Initial sync
        cursor = APILogCursor(last_log_id=1000, last_timestamp=datetime.now())
        cursor_mgr.update_cursor(source_id, cursor.to_dict())

        # Simulate multiple incremental syncs
        for i in range(5):
            cursor_data = cursor_mgr.get_cursor(source_id)
            cursor = APILogCursor.from_dict(cursor_data)

            # Advance cursor by 100 log entries
            cursor.last_log_id += 100
            cursor.last_timestamp = datetime.now()

            cursor_mgr.update_cursor(source_id, cursor.to_dict())

        # Verify final state
        final_cursor = cursor_mgr.get_cursor(source_id)
        restored = APILogCursor.from_dict(final_cursor)
        assert restored.last_log_id == 1500  # 1000 + (5 * 100)


# ============================================================================
# Cursor Schema Registry Tests
# ============================================================================


class TestCursorSchemaRegistry:
    """Test cursor schema registry."""

    def test_get_filesystem_schema(self):
        """Test getting filesystem cursor schema."""
        schema = get_cursor_schema("filesystem")
        assert schema == FileSystemCursor

    def test_get_github_schema(self):
        """Test getting github cursor schema."""
        schema = get_cursor_schema("github")
        assert schema == GitHubCursor

    def test_get_slack_schema(self):
        """Test getting slack cursor schema."""
        schema = get_cursor_schema("slack")
        assert schema == SlackCursor

    def test_get_api_log_schema(self):
        """Test getting api_log cursor schema."""
        schema = get_cursor_schema("api_log")
        assert schema == APILogCursor

    def test_get_unknown_schema(self):
        """Test getting unknown schema."""
        schema = get_cursor_schema("unknown")
        assert schema is None


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestCursorEdgeCases:
    """Test edge cases and error handling."""

    def test_cursor_with_special_characters(self, cursor_mgr):
        """Test cursor with special characters in source_id."""
        source_id = "github:user/repo-name_v1.2.3"
        cursor_mgr.update_cursor(source_id, {"data": "test"})

        retrieved = cursor_mgr.get_cursor(source_id)
        assert retrieved is not None

    def test_cursor_with_large_data(self, cursor_mgr):
        """Test cursor with large data payload."""
        source_id = "test_large_data"

        # Create large cursor with many processed files
        large_cursor = FileSystemCursor(
            last_scan_time=datetime.now(),
            processed_files={
                f"/file{i}.py": datetime.now()
                for i in range(1000)
            }
        )

        cursor_mgr.update_cursor(source_id, large_cursor.to_dict())

        # Verify retrieval
        retrieved = cursor_mgr.get_cursor(source_id)
        assert len(retrieved["processed_files"]) == 1000

    def test_cursor_datetime_serialization(self, cursor_mgr):
        """Test datetime serialization edge cases."""
        source_id = "test_datetime"

        # Test various datetime formats
        now = datetime.now()
        past = datetime.now() - timedelta(days=365)
        future = datetime.now() + timedelta(days=365)

        cursor = FileSystemCursor(
            last_scan_time=now,
            processed_files={
                "/past.py": past,
                "/now.py": now,
                "/future.py": future,
            }
        )

        cursor_mgr.update_cursor(source_id, cursor.to_dict())

        # Retrieve and verify
        retrieved = cursor_mgr.get_cursor(source_id)
        restored = FileSystemCursor.from_dict(retrieved)

        assert len(restored.processed_files) == 3
        # Verify datetime restoration (allow 1 second tolerance)
        for path, timestamp in restored.processed_files.items():
            assert isinstance(timestamp, datetime)

    def test_empty_cursor_update(self, cursor_mgr):
        """Test updating cursor with empty data."""
        source_id = "test_empty"

        # Store empty cursor
        cursor_mgr.update_cursor(source_id, {})

        retrieved = cursor_mgr.get_cursor(source_id)
        assert retrieved == {}

    def test_concurrent_cursor_updates(self, cursor_mgr):
        """Test multiple updates to same cursor."""
        source_id = "test_concurrent"

        # Simulate rapid updates
        for i in range(10):
            cursor_mgr.update_cursor(source_id, {"iteration": i})

        # Verify last update wins
        retrieved = cursor_mgr.get_cursor(source_id)
        assert retrieved["iteration"] == 9
