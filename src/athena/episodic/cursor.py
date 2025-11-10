"""Cursor management for incremental event sync from external sources.

This module provides cursor tracking for event sources to enable incremental
synchronization. Cursors store the state of the last sync operation, allowing
sources to retrieve only new events since the last sync.

Example Usage:

    # Initialize cursor manager
    cursor_mgr = CursorManager(db)

    # Full sync (first time)
    source = FileSystemSource(path="/project")
    events = source.fetch_events()  # No cursor, fetches all
    cursor_mgr.update_cursor(source.source_id, source.get_cursor())

    # Incremental sync (subsequent syncs)
    cursor_data = cursor_mgr.get_cursor(source.source_id)
    source.set_cursor(cursor_data)
    new_events = source.fetch_events()  # Only fetches new events
    cursor_mgr.update_cursor(source.source_id, source.get_cursor())

Cursor Schemas:

    - FileSystemCursor: Track file modification times
    - GitHubCursor: Track event IDs and commit SHAs
    - SlackCursor: Track channel message timestamps
    - APILogCursor: Track sequential log IDs

"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field

from ..core.database import Database


# ============================================================================
# Typed Cursor Schemas (Pydantic Models)
# ============================================================================


class FileSystemCursor(BaseModel):
    """Cursor for file system event source.

    Tracks the last scan time and modification times of processed files
    to enable incremental file change detection.

    Attributes:
        last_scan_time: Timestamp of last file system scan
        processed_files: Map of file path -> last modified time
    """

    last_scan_time: Optional[datetime] = None
    processed_files: Dict[str, datetime] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize cursor to dictionary for storage."""
        return {
            "last_scan_time": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "processed_files": {
                path: mtime.isoformat() for path, mtime in self.processed_files.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileSystemCursor":
        """Deserialize cursor from dictionary."""
        last_scan = None
        if data.get("last_scan_time"):
            # Handle both datetime objects and ISO strings
            if isinstance(data["last_scan_time"], datetime):
                last_scan = data["last_scan_time"]
            else:
                last_scan = datetime.fromisoformat(data["last_scan_time"])

        processed = {}
        for path, mtime_str in data.get("processed_files", {}).items():
            # Handle both datetime objects and ISO strings
            if isinstance(mtime_str, datetime):
                processed[path] = mtime_str
            else:
                processed[path] = datetime.fromisoformat(mtime_str)

        return cls(last_scan_time=last_scan, processed_files=processed)


class GitCommitCursor(BaseModel):
    """Cursor for git commit-based file system event source.

    Tracks the last synced commit SHA to enable incremental git commit history
    extraction. This enables efficient resumption from a previous sync point.

    Attributes:
        last_commit_sha: SHA of last processed commit
        timestamp: When cursor was last updated
        repo_path: Path to repository (for validation)
    """

    last_commit_sha: Optional[str] = None
    timestamp: Optional[datetime] = None
    repo_path: Optional[str] = None

    model_config = {"arbitrary_types_allowed": True}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize cursor to dictionary for storage."""
        return {
            "last_commit_sha": self.last_commit_sha,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "repo_path": self.repo_path,
            "source_type": "git_commit"  # For identification
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GitCommitCursor":
        """Deserialize cursor from dictionary."""
        timestamp = None
        if data.get("timestamp"):
            # Handle both datetime objects and ISO strings
            if isinstance(data["timestamp"], datetime):
                timestamp = data["timestamp"]
            else:
                timestamp = datetime.fromisoformat(data["timestamp"])

        return cls(
            last_commit_sha=data.get("last_commit_sha"),
            timestamp=timestamp,
            repo_path=data.get("repo_path")
        )


class GitHubCursor(BaseModel):
    """Cursor for GitHub event source.

    Tracks the last synced event ID and commit SHAs per repository
    to enable incremental event and commit fetching.

    Attributes:
        last_event_id: ID of last processed GitHub event
        last_sync_timestamp: Timestamp of last successful sync
        repositories: Map of repo name -> last synced commit SHA
    """

    last_event_id: Optional[str] = None
    last_sync_timestamp: Optional[datetime] = None
    repositories: Dict[str, str] = Field(default_factory=dict)  # repo_name -> last_sha

    model_config = {"arbitrary_types_allowed": True}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize cursor to dictionary for storage."""
        return {
            "last_event_id": self.last_event_id,
            "last_sync_timestamp": (
                self.last_sync_timestamp.isoformat() if self.last_sync_timestamp else None
            ),
            "repositories": self.repositories,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GitHubCursor":
        """Deserialize cursor from dictionary."""
        last_sync = None
        if data.get("last_sync_timestamp"):
            # Handle both datetime objects and ISO strings
            if isinstance(data["last_sync_timestamp"], datetime):
                last_sync = data["last_sync_timestamp"]
            else:
                last_sync = datetime.fromisoformat(data["last_sync_timestamp"])

        return cls(
            last_event_id=data.get("last_event_id"),
            last_sync_timestamp=last_sync,
            repositories=data.get("repositories", {}),
        )


class SlackCursor(BaseModel):
    """Cursor for Slack event source.

    Tracks the latest message timestamp per channel to enable
    incremental message fetching.

    Attributes:
        channel_cursors: Map of channel ID -> latest message timestamp
        last_sync_timestamp: Timestamp of last successful sync
    """

    channel_cursors: Dict[str, str] = Field(default_factory=dict)  # channel_id -> latest_ts
    last_sync_timestamp: Optional[datetime] = None

    model_config = {"arbitrary_types_allowed": True}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize cursor to dictionary for storage."""
        return {
            "channel_cursors": self.channel_cursors,
            "last_sync_timestamp": (
                self.last_sync_timestamp.isoformat() if self.last_sync_timestamp else None
            ),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SlackCursor":
        """Deserialize cursor from dictionary."""
        last_sync = None
        if data.get("last_sync_timestamp"):
            # Handle both datetime objects and ISO strings
            if isinstance(data["last_sync_timestamp"], datetime):
                last_sync = data["last_sync_timestamp"]
            else:
                last_sync = datetime.fromisoformat(data["last_sync_timestamp"])

        return cls(
            channel_cursors=data.get("channel_cursors", {}),
            last_sync_timestamp=last_sync,
        )


class APILogCursor(BaseModel):
    """Cursor for API log event source.

    Tracks the last processed log ID and timestamp to enable
    incremental log fetching from sequential log streams.

    Attributes:
        last_log_id: ID of last processed log entry
        last_timestamp: Timestamp of last processed log entry
    """

    last_log_id: Optional[int] = None
    last_timestamp: Optional[datetime] = None

    model_config = {"arbitrary_types_allowed": True}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize cursor to dictionary for storage."""
        return {
            "last_log_id": self.last_log_id,
            "last_timestamp": (
                self.last_timestamp.isoformat() if self.last_timestamp else None
            ),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "APILogCursor":
        """Deserialize cursor from dictionary."""
        last_ts = None
        if data.get("last_timestamp"):
            # Handle both datetime objects and ISO strings
            if isinstance(data["last_timestamp"], datetime):
                last_ts = data["last_timestamp"]
            else:
                last_ts = datetime.fromisoformat(data["last_timestamp"])

        return cls(
            last_log_id=data.get("last_log_id"),
            last_timestamp=last_ts,
        )


# ============================================================================
# Generic Cursor Wrapper
# ============================================================================


class EventSourceCursor:
    """Generic wrapper for event source cursors.

    Supports both typed (Pydantic schema) and untyped (raw dict) cursors.
    Provides a uniform interface for cursor manipulation across all sources.

    Example:
        # Typed cursor
        cursor = EventSourceCursor(
            cursor_schema=FileSystemCursor,
            data={"last_scan_time": None, "processed_files": {}}
        )
        cursor.update(last_scan_time=datetime.now())
        cursor.update(processed_files={"/file1.py": datetime.now()})

        # Untyped cursor
        cursor = EventSourceCursor(data={"offset": 0, "page": 1})
        cursor.update(offset=100, page=2)
    """

    def __init__(
        self,
        cursor_schema: Optional[Type[BaseModel]] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Initialize event source cursor.

        Args:
            cursor_schema: Optional Pydantic model class for typed cursor
            data: Initial cursor data (dict)
        """
        self.cursor_schema = cursor_schema
        self._data = data or {}

        # If schema provided, validate initial data
        if cursor_schema and data:
            try:
                # Validate through schema
                instance = cursor_schema.from_dict(data) if hasattr(cursor_schema, 'from_dict') else cursor_schema(**data)
                self._data = instance.to_dict() if hasattr(instance, 'to_dict') else instance.model_dump()
            except Exception as e:
                # If validation fails, fall back to untyped
                import logging
                logging.warning(f"Cursor schema validation failed: {e}. Using untyped cursor.")
                self.cursor_schema = None

    def update(self, **kwargs) -> None:
        """Update cursor fields.

        Args:
            **kwargs: Field updates to apply

        Example:
            cursor.update(last_scan_time=datetime.now(), processed_files={...})
        """
        if self.cursor_schema:
            # Typed cursor: validate through schema
            try:
                # Merge updates with existing data
                updated_data = {**self._data, **kwargs}

                # Validate through schema
                if hasattr(self.cursor_schema, 'from_dict'):
                    instance = self.cursor_schema.from_dict(updated_data)
                else:
                    instance = self.cursor_schema(**updated_data)

                # Serialize back to dict
                self._data = instance.to_dict() if hasattr(instance, 'to_dict') else instance.model_dump()
            except Exception as e:
                import logging
                logging.error(f"Failed to update typed cursor: {e}")
                raise
        else:
            # Untyped cursor: direct update
            self._data.update(kwargs)

    def get(self) -> Dict[str, Any]:
        """Get cursor data as dictionary.

        Returns:
            Current cursor state as dict
        """
        return self._data.copy()

    def reset(self) -> None:
        """Reset cursor to empty state."""
        self._data = {}


# ============================================================================
# Cursor Manager (Persistence Layer)
# ============================================================================


class CursorManager:
    """Manages persistence and retrieval of event source cursors.

    Provides database-backed storage for cursors with CRUD operations.
    Each cursor is identified by a unique source_id.

    Example:
        cursor_mgr = CursorManager(db)

        # Store cursor
        cursor_data = {"last_scan_time": datetime.now().isoformat()}
        cursor_mgr.update_cursor("filesystem:/project", cursor_data)

        # Retrieve cursor
        stored = cursor_mgr.get_cursor("filesystem:/project")

        # List all cursors
        all_cursors = cursor_mgr.list_cursors()

        # Delete cursor (reset sync)
        cursor_mgr.delete_cursor("filesystem:/project")
    """

    def __init__(self, db: Database):
        """Initialize cursor manager.

        Args:
            db: Database instance for cursor persistence
        """
        self.db = db
        self._init_schema()

    def _init_schema(self) -> None:
        """Create cursor storage table if not exists.

        Database schema:
            - source_id (TEXT, PRIMARY KEY): Unique identifier for event source
            - cursor_data (TEXT): JSON-serialized cursor state
            - updated_at (INTEGER): Unix timestamp of last update
        """
        cursor = self.db.get_cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_source_cursors (
                source_id TEXT PRIMARY KEY,
                cursor_data TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)

        # Index for fast lookup by source_id (implicit due to PRIMARY KEY)
        # Index for sorting by update time
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cursors_updated
            ON event_source_cursors(updated_at DESC)
        """)

        # commit handled by cursor context

    def get_cursor(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored cursor for a source.

        Args:
            source_id: Unique identifier for event source

        Returns:
            Cursor data as dict, or None if not found

        Example:
            cursor_data = cursor_mgr.get_cursor("github:user/repo")
            if cursor_data:
                cursor = GitHubCursor.from_dict(cursor_data)
        """
        try:
            cursor = self.db.get_cursor()
            cursor.execute("""
                SELECT cursor_data FROM event_source_cursors
                WHERE source_id = ?
            """, (source_id,))

            row = cursor.fetchone()
            if row:
                return json.loads(row[0])  # row[0] is cursor_data

            return None

        except Exception as e:
            import logging
            logging.error(f"Failed to retrieve cursor for {source_id}: {e}")
            return None

    def update_cursor(self, source_id: str, cursor_data: Dict[str, Any]) -> None:
        """Persist cursor data for a source.

        Uses INSERT OR REPLACE to handle both create and update cases.

        Args:
            source_id: Unique identifier for event source
            cursor_data: Cursor state to persist

        Example:
            cursor = FileSystemCursor(
                last_scan_time=datetime.now(),
                processed_files={"/file.py": datetime.now()}
            )
            cursor_mgr.update_cursor("filesystem:/project", cursor.to_dict())
        """
        try:
            cursor = self.db.get_cursor()
            now = int(datetime.now().timestamp())

            # Serialize cursor data to JSON
            cursor_json = json.dumps(cursor_data, default=str)  # default=str handles datetime

            cursor.execute("""
                INSERT OR REPLACE INTO event_source_cursors (source_id, cursor_data, updated_at)
                VALUES (?, ?, ?)
            """, (source_id, cursor_json, now))

            # commit handled by cursor context

        except Exception as e:
            # rollback handled by cursor context
            import logging
            logging.error(f"Failed to update cursor for {source_id}: {e}")
            raise

    def delete_cursor(self, source_id: str) -> bool:
        """Remove cursor for a source (reset sync state).

        Args:
            source_id: Unique identifier for event source

        Returns:
            True if cursor was deleted, False if not found

        Example:
            # Reset sync - next fetch will be full sync
            cursor_mgr.delete_cursor("slack:channel123")
        """
        try:
            cursor = self.db.get_cursor()
            cursor.execute("""
                DELETE FROM event_source_cursors
                WHERE source_id = ?
            """, (source_id,))

            deleted = cursor.rowcount > 0
            # commit handled by cursor context

            return deleted

        except Exception as e:
            # rollback handled by cursor context
            import logging
            logging.error(f"Failed to delete cursor for {source_id}: {e}")
            return False

    def list_cursors(self) -> List[Dict[str, Any]]:
        """List all stored cursors.

        Returns:
            List of cursor metadata dicts with keys:
                - source_id: Source identifier
                - cursor_data: Cursor state
                - updated_at: Last update timestamp

        Example:
            all_cursors = cursor_mgr.list_cursors()
            for cursor_info in all_cursors:
                print(f"{cursor_info['source_id']}: {cursor_info['updated_at']}")
        """
        try:
            cursor = self.db.get_cursor()
            cursor.execute("""
                SELECT source_id, cursor_data, updated_at
                FROM event_source_cursors
                ORDER BY updated_at DESC
            """)

            results = []
            for row in cursor.fetchall():
                results.append({
                    "source_id": row[0],
                    "cursor_data": json.loads(row[1]),
                    "updated_at": datetime.fromtimestamp(row[2]),
                })

            return results

        except Exception as e:
            import logging
            logging.error(f"Failed to list cursors: {e}")
            return []


# ============================================================================
# Example Usage Patterns
# ============================================================================


def example_full_sync():
    """Example: First-time full sync with cursor creation."""
    from ..core.database import Database

    db = Database("memory.db")
    cursor_mgr = CursorManager(db)

    # Simulate file system source
    source_id = "filesystem:/home/user/project"

    # Full sync (no cursor exists)
    cursor_data = cursor_mgr.get_cursor(source_id)
    assert cursor_data is None  # First sync

    # Fetch all files (full sync logic in source)
    # ... source.fetch_events() ...

    # After sync, save cursor
    cursor = FileSystemCursor(
        last_scan_time=datetime.now(),
        processed_files={
            "/home/user/project/file1.py": datetime.now(),
            "/home/user/project/file2.py": datetime.now(),
        }
    )
    cursor_mgr.update_cursor(source_id, cursor.to_dict())


def example_incremental_sync():
    """Example: Incremental sync using stored cursor."""
    from ..core.database import Database

    db = Database("memory.db")
    cursor_mgr = CursorManager(db)

    source_id = "github:user/repo"

    # Retrieve cursor from previous sync
    cursor_data = cursor_mgr.get_cursor(source_id)

    if cursor_data:
        # Incremental sync: only fetch new events
        cursor = GitHubCursor.from_dict(cursor_data)
        print(f"Last event ID: {cursor.last_event_id}")
        # ... source.fetch_events(since=cursor.last_event_id) ...

        # Update cursor after sync
        cursor.last_event_id = "new_event_12345"
        cursor.last_sync_timestamp = datetime.now()
        cursor_mgr.update_cursor(source_id, cursor.to_dict())
    else:
        # Full sync (no cursor)
        print("No cursor found, performing full sync")
        # ... source.fetch_events() ...


def example_integration_with_source_factory():
    """Example: Integration with EventSourceFactory pattern.

    This demonstrates how cursors work with the event source abstraction:

    1. EventSourceFactory creates source instances
    2. CursorManager loads/saves cursor for each source
    3. Source uses cursor to determine full vs incremental sync
    """
    from ..core.database import Database

    db = Database("memory.db")
    cursor_mgr = CursorManager(db)

    # Hypothetical EventSourceFactory usage
    # (actual implementation would be in separate module)

    # Factory creates source with cursor support
    # source = EventSourceFactory.create("filesystem", path="/project")
    # source_id = source.source_id  # e.g., "filesystem:/project"

    # Load cursor before sync
    # cursor_data = cursor_mgr.get_cursor(source_id)
    # if cursor_data:
    #     source.set_cursor(cursor_data)  # Source knows how to interpret cursor

    # Fetch events (source decides full vs incremental based on cursor)
    # events = source.fetch_events()

    # Save updated cursor after sync
    # updated_cursor = source.get_cursor()  # Source provides updated cursor
    # cursor_mgr.update_cursor(source_id, updated_cursor)

    pass


# ============================================================================
# Cursor Schema Registry (Optional: for dynamic schema lookup)
# ============================================================================


CURSOR_SCHEMA_REGISTRY = {
    "filesystem": FileSystemCursor,
    "github": GitHubCursor,
    "slack": SlackCursor,
    "api_log": APILogCursor,
}


def get_cursor_schema(source_type: str) -> Optional[Type[BaseModel]]:
    """Get cursor schema class for a source type.

    Args:
        source_type: Source type identifier (e.g., "filesystem", "github")

    Returns:
        Pydantic cursor schema class, or None if not found

    Example:
        schema = get_cursor_schema("github")
        cursor = schema.from_dict(cursor_data)
    """
    return CURSOR_SCHEMA_REGISTRY.get(source_type)
