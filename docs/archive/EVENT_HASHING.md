# Event Hashing for Deduplication

## Overview

The EventHasher component provides content-based hashing for episodic events to prevent duplicate storage when events are ingested from multiple sources (CLI, MCP, git hooks, file watchers, etc.).

## Quick Start

```python
from athena.episodic import EventHasher, EpisodicEvent, EventType, EventContext
from datetime import datetime

# Create hasher
hasher = EventHasher()

# Create event
event = EpisodicEvent(
    project_id=1,
    session_id="my_session",
    timestamp=datetime.now(),
    event_type=EventType.ACTION,
    content="Implemented user authentication",
    context=EventContext(cwd="/home/user/project", files=["auth.py"])
)

# Compute hash
hash_value = hasher.compute_hash(event)
print(f"Event hash: {hash_value}")
# Output: Event hash: c59bcfa11657ac4535a7d91239d5ee31e696e9b23e0bd780c3d4c21881f8a9b0
```

Or use the convenience function:

```python
from athena.episodic import compute_event_hash

hash_value = compute_event_hash(event)
```

## How It Works

### Content Fingerprinting

Events are hashed based on their **semantic content**, excluding:

**Excluded Fields** (volatile or system-generated):
- `id` - Database-assigned, not part of content
- `consolidation_status` - Changes during consolidation lifecycle
- `consolidated_at` - Updated during consolidation

**Included Fields** (the "content fingerprint"):
- **Temporal/Spatial**: `project_id`, `session_id`, `timestamp`
- **Classification**: `event_type`, `code_event_type`, `outcome`
- **Content**: `content`, `learned`, `confidence`
- **Context**: `context.cwd`, `context.files`, `context.task`, `context.phase`, `context.branch`
- **Code-Aware**: `file_path`, `symbol_name`, `symbol_type`, `language`, `diff`
- **Version Control**: `git_commit`, `git_author`
- **Metrics**: `duration_ms`, `files_changed`, `lines_added`, `lines_deleted`
- **Testing**: `test_name`, `test_passed`, `error_type`, `stack_trace`
- **Quality**: `performance_metrics`, `code_quality_score`

### Hash Algorithm

- **Algorithm**: SHA256 (256-bit collision resistance)
- **Serialization**: Deterministic JSON (sorted keys, no whitespace)
- **Encoding**: Hex string (64 characters)
- **Performance**: <1ms per event (suitable for batch ingestion)

## Use Cases

### 1. Multi-Source Ingestion

**Scenario**: Git post-commit hook records a commit event. 5 minutes later, the user runs a CLI command that also tries to record the same commit.

```python
# Git hook ingestion
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
    context=EventContext(cwd="/home/user/project", files=["src/auth.py"])
)

git_hash = hasher.compute_hash(git_event)
# Store in database with hash: db.store_event_with_hash(git_event, git_hash)

# Later, CLI ingestion attempts same event
cli_event = git_event.model_copy(deep=True)
cli_event.id = 999  # Different ID (excluded from hash)
cli_event.consolidation_status = "consolidated"  # Different status (excluded)

cli_hash = hasher.compute_hash(cli_event)

# Check for duplicate
if cli_hash == git_hash:
    print("Duplicate detected! Skipping storage.")
    # Return existing event ID
else:
    print("New event, storing...")
    # Store new event
```

### 2. Database Integration

```python
from athena.episodic import EpisodicStore, EventHasher

class DeduplicatedEpisodicStore(EpisodicStore):
    """Episodic store with deduplication support."""

    def __init__(self, db):
        super().__init__(db)
        self.hasher = EventHasher()
        self._init_hash_schema()

    def _init_hash_schema(self):
        """Add hash column and index."""
        self.db.execute("""
            ALTER TABLE episodic_events
            ADD COLUMN content_hash TEXT
        """)
        self.db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_events_hash
            ON episodic_events(content_hash)
        """)
        self.db.conn.commit()

    def record_event_deduplicated(self, event: EpisodicEvent) -> int:
        """Record event with deduplication."""
        # Compute hash
        content_hash = self.hasher.compute_hash(event)

        # Check for existing event
        cursor = self.db.execute(
            "SELECT id FROM episodic_events WHERE content_hash = ?",
            (content_hash,),
            fetch_one=True
        )

        if cursor:
            # Duplicate found, return existing ID
            return cursor["id"]

        # New event, store with hash
        event_id = self.record_event(event)

        # Update hash
        self.db.execute(
            "UPDATE episodic_events SET content_hash = ? WHERE id = ?",
            (content_hash, event_id)
        )
        self.db.conn.commit()

        return event_id
```

### 3. Batch Deduplication

```python
def batch_record_with_deduplication(
    store: EpisodicStore,
    events: List[EpisodicEvent]
) -> Dict[str, List[int]]:
    """Batch record events with deduplication.

    Returns:
        Dictionary with 'stored' (new) and 'skipped' (duplicate) IDs
    """
    hasher = EventHasher()

    # Compute hashes
    event_hashes = [(event, hasher.compute_hash(event)) for event in events]

    # Query existing hashes
    hash_values = [h for _, h in event_hashes]
    placeholders = ','.join('?' * len(hash_values))
    query = f"""
        SELECT content_hash, id FROM episodic_events
        WHERE content_hash IN ({placeholders})
    """
    existing = store.db.execute(query, hash_values, fetch_all=True)
    existing_hashes = {row["content_hash"]: row["id"] for row in existing}

    # Separate new vs duplicate
    new_events = []
    stored_ids = []
    skipped_ids = []

    for event, event_hash in event_hashes:
        if event_hash in existing_hashes:
            # Duplicate
            skipped_ids.append(existing_hashes[event_hash])
        else:
            # New event
            new_events.append((event, event_hash))

    # Batch store new events
    for event, event_hash in new_events:
        event_id = store.record_event(event)
        store.db.execute(
            "UPDATE episodic_events SET content_hash = ? WHERE id = ?",
            (event_hash, event_id)
        )
        stored_ids.append(event_id)

    store.db.conn.commit()

    return {
        "stored": stored_ids,
        "skipped": skipped_ids,
        "total": len(events),
        "duplicates": len(skipped_ids)
    }
```

### 4. Hash-Based Event Comparison

```python
def find_duplicate_events(
    store: EpisodicStore,
    project_id: int,
    days: int = 7
) -> List[Dict]:
    """Find duplicate events by comparing hashes.

    Returns list of duplicate groups with event IDs and hashes.
    """
    hasher = EventHasher()

    # Get recent events
    cutoff = datetime.now() - timedelta(days=days)
    events = store.get_events_by_date(project_id, cutoff)

    # Compute hashes
    hash_to_events = {}
    for event in events:
        event_hash = hasher.compute_hash(event)
        if event_hash not in hash_to_events:
            hash_to_events[event_hash] = []
        hash_to_events[event_hash].append(event)

    # Find duplicates (hashes with multiple events)
    duplicates = []
    for event_hash, event_list in hash_to_events.items():
        if len(event_list) > 1:
            duplicates.append({
                "hash": event_hash,
                "count": len(event_list),
                "event_ids": [e.id for e in event_list],
                "first_occurrence": min(e.timestamp for e in event_list),
                "last_occurrence": max(e.timestamp for e in event_list),
            })

    return duplicates
```

## Examples

### Example 1: Identical Events Produce Same Hash

```python
event_a = EpisodicEvent(
    project_id=1,
    session_id="session_123",
    timestamp=datetime(2025, 1, 10, 14, 30, 0),
    event_type=EventType.ACTION,
    content="Implemented user authentication flow",
    outcome=EventOutcome.SUCCESS,
    context=EventContext(
        cwd="/home/user/project",
        files=["src/auth.py", "tests/test_auth.py"],
        task="Add OAuth support",
        phase="implementation"
    ),
    duration_ms=1500,
    files_changed=2,
    lines_added=85,
    lines_deleted=12,
)

event_b = event_a.model_copy(deep=True)
event_b.id = 999  # Different ID (excluded)
event_b.consolidation_status = "consolidated"  # Different status (excluded)

hasher = EventHasher()
hash_a = hasher.compute_hash(event_a)
hash_b = hasher.compute_hash(event_b)

assert hash_a == hash_b  # True - excluded fields don't affect hash
```

### Example 2: Different Content Produces Different Hash

```python
event_c = event_a.model_copy(deep=True)
event_c.content = "Fixed bug in authentication"  # Different content

hash_c = hasher.compute_hash(event_c)
assert hash_a != hash_c  # True - content affects hash
```

### Example 3: Different Timestamps Produce Different Hashes

```python
event_d = event_a.model_copy(deep=True)
event_d.timestamp = datetime(2025, 1, 10, 15, 30, 0)  # 1 hour later

hash_d = hasher.compute_hash(event_d)
assert hash_a != hash_d  # True - timestamp is included in hash
```

### Example 4: Code-Aware Events

```python
code_event = EpisodicEvent(
    project_id=1,
    session_id="session_456",
    timestamp=datetime(2025, 1, 10, 16, 0, 0),
    event_type=EventType.ACTION,
    code_event_type=CodeEventType.CODE_EDIT,
    content="Refactored authentication module",
    file_path="src/auth.py",
    symbol_name="authenticate_user",
    symbol_type="function",
    language="python",
    diff="@@ -10,3 +10,5 @@ def authenticate_user(credentials):\n     return validate(credentials)",
    git_commit="abc123def456",
    git_author="developer@example.com",
    context=EventContext(cwd="/home/user/project"),
)

hash_code = hasher.compute_hash(code_event)
print(f"Code event hash: {hash_code}")
# Output: Code event hash: 1aed16afc245d85950756669b39304f2d26e5a8ad4333db7d1cd78c7a4a3fb7d
```

## Hash Properties

### Determinism

Same event content always produces the same hash:

```python
event = create_test_event()
hash1 = hasher.compute_hash(event)
hash2 = hasher.compute_hash(event)
assert hash1 == hash2  # Always True
```

### Collision Resistance

SHA256 provides 256-bit security (2^256 possible hashes):

```python
# Generate 1000 unique events
hashes = set()
for i in range(1000):
    event = create_unique_event(i)
    hash_val = hasher.compute_hash(event)
    hashes.add(hash_val)

assert len(hashes) == 1000  # All hashes unique (no collisions)
```

### Performance

Hashing is fast enough for batch ingestion:

```python
import time

events = [create_test_event(i) for i in range(1000)]
start = time.time()
hashes = [hasher.compute_hash(e) for e in events]
elapsed = time.time() - start

print(f"Hashed {len(events)} events in {elapsed:.2f}s")
print(f"Average: {elapsed/len(events)*1000:.2f}ms per event")
# Output: Hashed 1000 events in 0.15s
#         Average: 0.15ms per event
```

## Testing

Run the comprehensive test suite:

```bash
pytest tests/unit/test_episodic_hashing.py -v
```

Test coverage includes:
- ✅ Identical events produce same hash
- ✅ Different content produces different hash
- ✅ Excluded fields don't affect hash (id, consolidation_status, consolidated_at)
- ✅ Included fields affect hash (timestamp, content, context, metrics, etc.)
- ✅ Hash determinism across multiple runs
- ✅ Collision resistance (1000 unique events)
- ✅ Edge cases (None values, unicode, long content, special characters)
- ✅ Real-world deduplication scenarios

## Integration with EventProcessingPipeline

The EventHasher will be integrated into the EventProcessingPipeline for automatic deduplication:

```python
class EventProcessingPipeline:
    def __init__(self, store: EpisodicStore):
        self.store = store
        self.hasher = EventHasher()

    def ingest_event(self, event: EpisodicEvent) -> Dict[str, Any]:
        """Ingest event with deduplication."""
        # Compute hash
        content_hash = self.hasher.compute_hash(event)

        # Check for duplicate
        existing = self.store.get_event_by_hash(content_hash)
        if existing:
            return {
                "status": "duplicate",
                "event_id": existing.id,
                "hash": content_hash,
            }

        # Store new event
        event_id = self.store.record_event(event)
        self.store.update_event_hash(event_id, content_hash)

        return {
            "status": "stored",
            "event_id": event_id,
            "hash": content_hash,
        }
```

## FAQ

**Q: Why is `timestamp` included in the hash if events can have the same timestamp?**

A: Timestamp is part of the event's semantic identity. Events at different times are fundamentally different events, even if the content is similar. If you need to deduplicate events regardless of timestamp, you can create a custom hasher that excludes it.

**Q: What happens if two events have the same content but different sessions?**

A: They will have different hashes because `session_id` is included. Sessions represent different execution contexts, so events in different sessions are considered distinct.

**Q: Can I customize which fields are excluded?**

A: Yes, subclass `EventHasher` and override `EXCLUDED_FIELDS`:

```python
class CustomHasher(EventHasher):
    EXCLUDED_FIELDS = EventHasher.EXCLUDED_FIELDS | {"session_id"}  # Also exclude session_id
```

**Q: How do I handle hash collisions?**

A: SHA256 collisions are astronomically unlikely (2^128 probability). For practical purposes, you don't need to handle them. If you're paranoid, you can add a secondary content comparison check.

**Q: What's the performance impact of hashing?**

A: Minimal. Hashing takes ~0.15ms per event, which is negligible compared to database I/O (~10-50ms). Batch operations can hash 1000+ events per second.

## References

- [SHA256 Specification](https://en.wikipedia.org/wiki/SHA-2)
- [Content-Addressable Storage](https://en.wikipedia.org/wiki/Content-addressable_storage)
- [Git Object Model](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects) (similar hash-based deduplication)
