# Cursor Management for Incremental Event Sync

This document describes the cursor management system for Athena's episodic memory, which enables incremental synchronization from external event sources.

## Overview

The cursor management system provides:

- **Typed cursor schemas** for different event source types (filesystem, GitHub, Slack, API logs)
- **Generic cursor wrapper** supporting both typed and untyped cursors
- **Persistent cursor storage** with database-backed state management
- **Full and incremental sync** workflows for event sources

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Event Source Layer                        │
│  (FileSystemSource, GitHubSource, SlackSource, etc.)        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ get_cursor() / set_cursor()
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    EventSourceCursor                         │
│             (Generic cursor wrapper with update)             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Typed Schema Validation
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Cursor Schemas                            │
│  - FileSystemCursor   - GitHubCursor                        │
│  - SlackCursor        - APILogCursor                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ to_dict() / from_dict()
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    CursorManager                             │
│            (Database persistence layer)                      │
│  - get_cursor()     - update_cursor()                       │
│  - delete_cursor()  - list_cursors()                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │   SQLite DB  │
                  │  (cursors)   │
                  └──────────────┘
```

## Core Components

### 1. Cursor Schemas (Pydantic Models)

Typed cursor schemas define the state structure for different event source types.

#### FileSystemCursor

Tracks file modification times for incremental file change detection.

```python
from athena.episodic.cursor import FileSystemCursor
from datetime import datetime

cursor = FileSystemCursor(
    last_scan_time=datetime.now(),
    processed_files={
        "/project/file1.py": datetime.now(),
        "/project/file2.py": datetime.now(),
    }
)

# Serialize for storage
cursor_data = cursor.to_dict()

# Deserialize from storage
restored = FileSystemCursor.from_dict(cursor_data)
```

**Schema:**
- `last_scan_time`: Last file system scan timestamp
- `processed_files`: Dict of `{file_path: last_modified_time}`

#### GitHubCursor

Tracks GitHub event IDs and commit SHAs per repository.

```python
from athena.episodic.cursor import GitHubCursor

cursor = GitHubCursor(
    last_event_id="event_12345",
    last_sync_timestamp=datetime.now(),
    repositories={
        "user/repo1": "abc123def456",  # repo -> last commit SHA
        "user/repo2": "789ghi012jkl",
    }
)
```

**Schema:**
- `last_event_id`: Last processed GitHub event ID
- `last_sync_timestamp`: Last successful sync time
- `repositories`: Dict of `{repo_name: last_commit_sha}`

#### SlackCursor

Tracks latest message timestamps per Slack channel.

```python
from athena.episodic.cursor import SlackCursor

cursor = SlackCursor(
    channel_cursors={
        "C123ABC": "1234567890.123456",  # channel_id -> latest message timestamp
        "C456DEF": "1234567891.654321",
    },
    last_sync_timestamp=datetime.now()
)
```

**Schema:**
- `channel_cursors`: Dict of `{channel_id: latest_message_ts}`
- `last_sync_timestamp`: Last successful sync time

#### APILogCursor

Tracks sequential log IDs and timestamps for API log streams.

```python
from athena.episodic.cursor import APILogCursor

cursor = APILogCursor(
    last_log_id=12345,
    last_timestamp=datetime.now()
)
```

**Schema:**
- `last_log_id`: ID of last processed log entry
- `last_timestamp`: Timestamp of last processed entry

### 2. EventSourceCursor (Generic Wrapper)

Provides a uniform interface for cursor manipulation across all sources.

```python
from athena.episodic.cursor import EventSourceCursor, FileSystemCursor

# Typed cursor with schema validation
cursor = EventSourceCursor(
    cursor_schema=FileSystemCursor,
    data={"last_scan_time": None, "processed_files": {}}
)

# Update cursor fields
cursor.update(last_scan_time=datetime.now())
cursor.update(processed_files={"/file.py": datetime.now()})

# Get cursor data
data = cursor.get()

# Reset cursor
cursor.reset()
```

**For untyped cursors:**

```python
# No schema validation
cursor = EventSourceCursor(data={"offset": 0, "page": 1})
cursor.update(offset=100, page=2)
```

### 3. CursorManager (Persistence Layer)

Manages database-backed storage and retrieval of cursors.

```python
from athena.core.database import Database
from athena.episodic.cursor import CursorManager

db = Database("memory.db")
cursor_mgr = CursorManager(db)

# Store cursor
cursor_mgr.update_cursor("filesystem:/project", cursor.to_dict())

# Retrieve cursor
cursor_data = cursor_mgr.get_cursor("filesystem:/project")

# Delete cursor (reset sync)
cursor_mgr.delete_cursor("filesystem:/project")

# List all cursors
all_cursors = cursor_mgr.list_cursors()
```

#### Database Schema

```sql
CREATE TABLE event_source_cursors (
    source_id TEXT PRIMARY KEY,           -- Unique source identifier
    cursor_data TEXT NOT NULL,            -- JSON-serialized cursor state
    updated_at INTEGER NOT NULL           -- Unix timestamp
);

CREATE INDEX idx_cursors_updated
ON event_source_cursors(updated_at DESC);
```

## Usage Patterns

### Full Sync (First-Time Sync)

When no cursor exists, perform a full sync to fetch all events.

```python
from athena.core.database import Database
from athena.episodic.cursor import CursorManager, FileSystemCursor

db = Database("memory.db")
cursor_mgr = CursorManager(db)

source_id = "filesystem:/home/user/project"

# Check if cursor exists
cursor_data = cursor_mgr.get_cursor(source_id)

if cursor_data is None:
    # First sync - fetch all events
    print("Performing full sync...")
    # ... source.fetch_all_events() ...

    # Save cursor after sync
    cursor = FileSystemCursor(
        last_scan_time=datetime.now(),
        processed_files={
            "/file1.py": datetime.now(),
            "/file2.py": datetime.now(),
        }
    )
    cursor_mgr.update_cursor(source_id, cursor.to_dict())
```

### Incremental Sync (Subsequent Syncs)

When cursor exists, fetch only new events since last sync.

```python
# Retrieve cursor from previous sync
cursor_data = cursor_mgr.get_cursor(source_id)

if cursor_data:
    # Incremental sync
    cursor = FileSystemCursor.from_dict(cursor_data)
    print(f"Last scan: {cursor.last_scan_time}")

    # Fetch only new/modified files
    # ... source.fetch_new_events(since=cursor.last_scan_time) ...

    # Update cursor after sync
    cursor.last_scan_time = datetime.now()
    cursor.processed_files["/new_file.py"] = datetime.now()
    cursor_mgr.update_cursor(source_id, cursor.to_dict())
```

### Reset Sync (Full Resync)

Delete cursor to force full resync on next run.

```python
# Reset sync state
cursor_mgr.delete_cursor(source_id)
print("Cursor deleted. Next sync will be full sync.")
```

## Integration with Event Sources

Event sources should implement the following interface:

```python
class EventSource:
    """Base interface for event sources."""

    @property
    def source_id(self) -> str:
        """Unique identifier for this source (e.g., 'filesystem:/path')."""
        pass

    def fetch_events(self, cursor: Optional[Dict] = None) -> List[EpisodicEvent]:
        """Fetch events (full or incremental based on cursor).

        Args:
            cursor: Optional cursor state for incremental sync

        Returns:
            List of episodic events
        """
        pass

    def get_cursor(self) -> Dict[str, Any]:
        """Get current cursor state after sync.

        Returns:
            Cursor data as dict
        """
        pass

    def set_cursor(self, cursor_data: Dict[str, Any]) -> None:
        """Set cursor state before sync.

        Args:
            cursor_data: Cursor state from previous sync
        """
        pass
```

### Example: FileSystemSource Integration

```python
from pathlib import Path
from datetime import datetime
from athena.episodic.cursor import FileSystemCursor, CursorManager

class FileSystemSource:
    """Event source for file system changes."""

    def __init__(self, path: str, db: Database):
        self.path = Path(path)
        self.cursor_mgr = CursorManager(db)
        self._cursor = None

    @property
    def source_id(self) -> str:
        return f"filesystem:{self.path}"

    def fetch_events(self) -> List[EpisodicEvent]:
        """Fetch file change events (full or incremental)."""
        # Load cursor
        cursor_data = self.cursor_mgr.get_cursor(self.source_id)

        if cursor_data:
            # Incremental sync
            cursor = FileSystemCursor.from_dict(cursor_data)
            events = self._fetch_modified_files(cursor)
        else:
            # Full sync
            events = self._fetch_all_files()

        # Update cursor after sync
        new_cursor = FileSystemCursor(
            last_scan_time=datetime.now(),
            processed_files=self._get_file_mtimes()
        )
        self.cursor_mgr.update_cursor(self.source_id, new_cursor.to_dict())

        return events

    def _fetch_all_files(self) -> List[EpisodicEvent]:
        """Full sync: fetch all files."""
        events = []
        for file_path in self.path.rglob("*.py"):
            event = self._create_event(file_path, "file_added")
            events.append(event)
        return events

    def _fetch_modified_files(self, cursor: FileSystemCursor) -> List[EpisodicEvent]:
        """Incremental sync: fetch only modified files."""
        events = []
        for file_path in self.path.rglob("*.py"):
            path_str = str(file_path)
            current_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

            if path_str not in cursor.processed_files:
                # New file
                event = self._create_event(file_path, "file_added")
                events.append(event)
            elif cursor.processed_files[path_str] < current_mtime:
                # Modified file
                event = self._create_event(file_path, "file_modified")
                events.append(event)

        return events

    def _get_file_mtimes(self) -> Dict[str, datetime]:
        """Get modification times for all files."""
        return {
            str(f): datetime.fromtimestamp(f.stat().st_mtime)
            for f in self.path.rglob("*.py")
        }
```

## Cursor Schema Registry

For dynamic schema lookup, use the schema registry:

```python
from athena.episodic.cursor import get_cursor_schema

# Get schema class for source type
schema = get_cursor_schema("github")  # Returns GitHubCursor

# Create cursor instance
cursor_data = {"last_event_id": "123", "repositories": {}}
cursor = schema.from_dict(cursor_data)
```

**Registered schemas:**
- `filesystem` → FileSystemCursor
- `github` → GitHubCursor
- `slack` → SlackCursor
- `api_log` → APILogCursor

## Best Practices

### 1. Use Typed Cursors When Possible

Typed cursors provide:
- **Validation**: Pydantic ensures data integrity
- **Autocomplete**: IDE support for cursor fields
- **Documentation**: Clear schema definition

```python
# Good: Typed cursor with validation
cursor = EventSourceCursor(
    cursor_schema=GitHubCursor,
    data={"last_event_id": "123"}
)

# Acceptable: Untyped cursor for simple cases
cursor = EventSourceCursor(data={"offset": 0})
```

### 2. Always Store Cursors After Sync

Ensure cursor is updated after every sync operation:

```python
# Fetch events
events = source.fetch_events()

# Store events to database
for event in events:
    episodic_store.record_event(event)

# Update cursor (critical!)
cursor_mgr.update_cursor(source.source_id, source.get_cursor())
```

### 3. Handle Cursor Corruption Gracefully

If cursor is corrupted, fall back to full sync:

```python
try:
    cursor_data = cursor_mgr.get_cursor(source_id)
    cursor = GitHubCursor.from_dict(cursor_data)
except Exception as e:
    logging.warning(f"Cursor corrupted: {e}. Performing full sync.")
    cursor_mgr.delete_cursor(source_id)
    # Proceed with full sync
```

### 4. Use Source-Specific IDs

Create unique source_id for each event source:

```python
# Good: Specific and unique
source_id = "filesystem:/home/user/project"
source_id = "github:user/repo"
source_id = "slack:workspace_T123:channel_C456"

# Bad: Generic and ambiguous
source_id = "filesystem"
source_id = "github"
```

### 5. Monitor Cursor Update Times

Track cursor ages to detect sync failures:

```python
all_cursors = cursor_mgr.list_cursors()

for cursor_info in all_cursors:
    age = datetime.now() - cursor_info["updated_at"]
    if age > timedelta(hours=24):
        logging.warning(f"Stale cursor: {cursor_info['source_id']} ({age})")
```

## Performance Considerations

### Cursor Storage Overhead

- **Small cursors** (<1KB): Negligible overhead
- **Large cursors** (1-10KB): Acceptable for most use cases
- **Very large cursors** (>10KB): Consider pagination or pruning

Example of large cursor optimization:

```python
# Instead of storing all processed files (potentially thousands)
cursor = FileSystemCursor(
    last_scan_time=datetime.now(),
    processed_files={...}  # Could be 10,000+ entries
)

# Store only recent files (e.g., last 1000)
recent_files = dict(sorted(
    processed_files.items(),
    key=lambda x: x[1],
    reverse=True
)[:1000])

cursor = FileSystemCursor(
    last_scan_time=datetime.now(),
    processed_files=recent_files
)
```

### Database Query Performance

- **Indexed queries**: `source_id` is PRIMARY KEY (fast lookup)
- **List all cursors**: Uses index on `updated_at` (fast sort)
- **Transaction overhead**: Minimal (single INSERT/UPDATE per sync)

### Sync Frequency

Balance sync frequency vs. cursor overhead:

- **High frequency** (every minute): Use simple cursors (timestamp, ID)
- **Medium frequency** (hourly): Use detailed cursors (file mtimes, commit SHAs)
- **Low frequency** (daily): Full resync may be acceptable

## Error Handling

### Cursor Not Found

```python
cursor_data = cursor_mgr.get_cursor(source_id)
if cursor_data is None:
    # First sync or cursor was deleted
    perform_full_sync()
```

### JSON Deserialization Error

```python
try:
    cursor = GitHubCursor.from_dict(cursor_data)
except (ValueError, KeyError) as e:
    logging.error(f"Invalid cursor format: {e}")
    cursor_mgr.delete_cursor(source_id)  # Reset
    perform_full_sync()
```

### Database Write Failure

```python
try:
    cursor_mgr.update_cursor(source_id, cursor.to_dict())
except Exception as e:
    logging.error(f"Failed to save cursor: {e}")
    # Cursor not saved - next sync will use old cursor
    # Consider retry logic or alerting
```

## Testing

See `/home/user/.work/athena/tests/unit/test_cursor_manager.py` for comprehensive test suite covering:

- Cursor schema serialization/deserialization
- Generic cursor wrapper operations
- CursorManager CRUD operations
- Full and incremental sync workflows
- Multi-source sync scenarios
- Edge cases and error handling

Run tests:

```bash
pytest tests/unit/test_cursor_manager.py -v
```

## Future Enhancements

### 1. Cursor Versioning

Support schema migrations for cursor format changes:

```python
class FileSystemCursor(BaseModel):
    version: int = 2  # Schema version
    last_scan_time: Optional[datetime] = None
    processed_files: Dict[str, datetime] = {}

    @classmethod
    def migrate_v1_to_v2(cls, old_data: Dict) -> Dict:
        """Migrate v1 cursor to v2."""
        # Migration logic
```

### 2. Cursor Compression

For large cursors, compress before storage:

```python
import gzip
import base64

def compress_cursor(cursor_data: Dict) -> str:
    json_str = json.dumps(cursor_data)
    compressed = gzip.compress(json_str.encode())
    return base64.b64encode(compressed).decode()
```

### 3. Cursor Expiration

Auto-delete stale cursors:

```python
cursor_mgr.delete_expired_cursors(max_age_days=30)
```

### 4. Multi-Tenant Cursors

Support project-scoped cursors:

```python
cursor_mgr.update_cursor(
    source_id="github:user/repo",
    cursor_data={...},
    project_id=123  # Scope to project
)
```

## Related Documentation

- **Event Sources**: See `/docs/EVENT_SOURCES.md` (to be created)
- **Episodic Memory**: See `/docs/ARCHITECTURE.md` (Layer 1)
- **Database Schema**: See `/src/athena/core/database.py`
- **API Reference**: See `/docs/API_REFERENCE.md`

## Support

For issues or questions:
- File an issue on GitHub
- Check test cases for usage examples
- Review cursor schema Pydantic models for field documentation
