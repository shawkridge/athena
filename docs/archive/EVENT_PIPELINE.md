# Event Processing Pipeline

Multi-stage event processing pipeline for high-throughput episodic event ingestion with intelligent deduplication.

## Overview

The `EventProcessingPipeline` implements a 6-stage processing pipeline optimized for:
- **High throughput**: 1000+ events/sec (target: 5000+ events/sec)
- **Deduplication**: In-memory LRU cache + database lookup
- **Batch processing**: Bulk operations minimize database round-trips
- **Graceful degradation**: Embedding failures don't fail entire batch

## Architecture

```
Input: List[EpisodicEvent]
    ↓
Stage 1: In-memory deduplication (LRU cache)
    ↓
Stage 2: Hash computation (content fingerprint)
    ↓
Stage 3: Action determination (bulk DB lookup)
    ↓
Stage 4: Enrichment (batch embedding generation)
    ↓
Stage 5: Persistence (bulk insert)
    ↓
Stage 6: Cleanup & metrics
    ↓
Output: {total, inserted, skipped_duplicate, skipped_existing, processing_time_ms}
```

## Usage

### Basic Usage

```python
from athena.episodic.pipeline import EventProcessingPipeline
from athena.episodic.store import EpisodicStore
from athena.episodic.hashing import EventHasher
from athena.core.embeddings import EmbeddingModel
from athena.core.database import Database
import asyncio

# Initialize components
db = Database("memory.db")
store = EpisodicStore(db)
hasher = EventHasher()
embedder = EmbeddingModel()

# Create pipeline
pipeline = EventProcessingPipeline(store, embedder, hasher)

# Process batch of events
stats = asyncio.run(pipeline.process_batch(events))

print(f"Inserted: {stats['inserted']}")
print(f"Skipped: {stats['skipped_existing']}")
print(f"Throughput: {stats['total'] / (stats['processing_time_ms'] / 1000):.0f} events/sec")
```

### Convenience Function

For one-off batch processing:

```python
from athena.episodic.pipeline import process_event_batch

stats = await process_event_batch(events, store)
```

### LRU Cache Configuration

Adjust cache size for memory-constrained environments:

```python
# Default: 5000 items
pipeline = EventProcessingPipeline(store, embedder, hasher, lru_cache_size=10000)
```

## Processing Stages

### Stage 1: In-Memory Deduplication

Maintains LRU cache of recent hashes to prevent repeated processing:

- **Cache size**: Configurable (default: 5000 items)
- **Lookup**: O(1) via OrderedDict
- **Eviction**: LRU policy when cache exceeds limit

**Example**:
```python
# Process batch with duplicate
duplicate_event = create_event("Same content")
batch = [duplicate_event] * 5

stats = await pipeline.process_batch(batch)
# Result: inserted=1, skipped_duplicate=4
```

### Stage 2: Hash Computation

Computes SHA256 content hash for each event using `EventHasher`:

- **Algorithm**: SHA256 (deterministic, collision-resistant)
- **Fields included**: All content fields (see `EventHasher` docs)
- **Fields excluded**: id, consolidation_status, consolidated_at
- **Performance**: <1ms per event

### Stage 3: Action Determination

Determines INSERT vs SKIP via bulk database lookup:

1. Check LRU cache first (O(1))
2. Bulk query database for remaining hashes (single query)
3. Mark events as INSERT or SKIP

**Optimization**: Single bulk query instead of N individual lookups.

### Stage 4: Enrichment

Generates embeddings for INSERT events:

- **Batch generation**: Amortizes API costs
- **Graceful fallback**: Embedding failures don't fail batch
- **Optional**: Events stored without embeddings if generation fails

### Stage 5: Persistence

Bulk inserts events and stores hashes:

- **Transaction**: Rollback on error
- **Hash storage**: event_hashes table for deduplication
- **Cache update**: Add new hashes to LRU cache

### Stage 6: Cleanup

Resource cleanup and metrics:

- **LRU eviction**: Maintain cache size limit
- **Statistics update**: Global tracking
- **Return**: Processing report

## Statistics Tracking

### Per-Batch Statistics

```python
stats = await pipeline.process_batch(events)

# Stats dictionary:
{
    "total": 1000,                   # Total events in batch
    "inserted": 950,                 # Events inserted
    "skipped_duplicate": 30,         # Duplicates within batch
    "skipped_existing": 20,          # Already in database
    "processing_time_ms": 209.4,     # Total processing time
    "errors": 0                      # Number of errors
}
```

### Global Statistics

```python
global_stats = pipeline.get_statistics()

# Global stats:
{
    "total_processed": 10000,        # Total events processed
    "total_inserted": 9500,          # Total events inserted
    "total_skipped_duplicate": 300,  # Total in-memory duplicates
    "total_skipped_existing": 200,   # Total database duplicates
    "cache_size": 5000               # Current cache size
}
```

## Performance

### Benchmarks

Tested on standard hardware (Python 3.13, SQLite):

| Batch Size | Time      | Throughput      | Notes                    |
|-----------|-----------|-----------------|--------------------------|
| 100       | 16ms      | 6,200 events/s  | Small batch overhead     |
| 500       | 70ms      | 7,181 events/s  | Optimal for most use     |
| 1,000     | 209ms     | 4,789 events/s  | Good throughput          |
| 5,000     | 747ms     | 6,696 events/s  | Large batch efficiency   |

### Performance Characteristics

- **Target throughput**: 1000+ events/sec
- **Achieved throughput**: 4,700-7,200 events/sec (exceeds target)
- **Database round-trips**: Minimized via bulk operations
- **Memory usage**: O(cache_size + batch_size)

### Optimization Tips

1. **Batch size**: 500-1000 events optimal for most workloads
2. **Cache size**: Increase for high-deduplication workloads
3. **Embeddings**: Disable for maximum throughput (optional feature)
4. **Database**: Use SSD for better I/O performance

## Deduplication Strategy

### Three-Level Deduplication

1. **Within-batch** (Stage 1): In-memory deduplication via hash set
2. **Cache-based** (Stage 3): LRU cache lookup (O(1))
3. **Database-based** (Stage 3): Bulk hash lookup (single query)

### Hash Storage

Hashes stored in `event_hashes` table:

```sql
CREATE TABLE event_hashes (
    event_id INTEGER PRIMARY KEY,
    content_hash TEXT NOT NULL UNIQUE,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (event_id) REFERENCES episodic_events(id)
);

CREATE INDEX idx_event_hashes_content ON event_hashes(content_hash);
```

### Cache Management

LRU cache maintains recent hashes:

- **Size limit**: Configurable (default: 5000)
- **Eviction**: Oldest items removed when limit exceeded
- **Clear**: `pipeline.clear_cache()` for testing

## Error Handling

### Graceful Degradation

Pipeline handles errors gracefully:

1. **Hash computation failure**: Event inserted anyway (fail-safe)
2. **Embedding generation failure**: Event stored without embedding
3. **Database error**: Transaction rolled back, error counted
4. **Per-event errors**: Don't fail entire batch

### Error Tracking

```python
stats = await pipeline.process_batch(events)

if stats["errors"] > 0:
    print(f"Warning: {stats['errors']} events encountered errors")
```

## Code-Aware Events

Pipeline supports code-aware events with rich metadata:

```python
from athena.episodic.models import CodeEventType

code_event = EpisodicEvent(
    project_id=1,
    session_id="code_session",
    timestamp=datetime.now(),
    event_type=EventType.ACTION,
    code_event_type=CodeEventType.CODE_EDIT,
    content="Refactored authentication module",
    file_path="src/auth.py",
    symbol_name="authenticate_user",
    symbol_type="function",
    language="python",
    diff="@@ -10,3 +10,5 @@ ...",
    git_commit="abc123",
    git_author="developer@example.com",
    context=EventContext(cwd="/project")
)

stats = await pipeline.process_batch([code_event])
```

## Examples

### Example 1: Basic Processing

```python
from athena.episodic.pipeline import EventProcessingPipeline
from athena.episodic.models import EpisodicEvent, EventType, EventContext
import asyncio

# Create events
events = [
    EpisodicEvent(
        project_id=1,
        session_id="demo",
        timestamp=datetime.now(),
        event_type=EventType.ACTION,
        content=f"Event {i}",
        context=EventContext(cwd="/project")
    ) for i in range(10)
]

# Process
pipeline = EventProcessingPipeline(store, embedder, hasher)
stats = asyncio.run(pipeline.process_batch(events))

print(f"Inserted {stats['inserted']} events")
```

### Example 2: Deduplication

```python
# Process initial batch
stats1 = await pipeline.process_batch(events)
# Result: inserted=10

# Re-process same batch (cached)
stats2 = await pipeline.process_batch(events)
# Result: inserted=0, skipped_existing=10

# Clear cache and re-process (database lookup)
pipeline.clear_cache()
stats3 = await pipeline.process_batch(events)
# Result: inserted=0, skipped_existing=10
```

### Example 3: High Throughput

```python
# Process large batch
large_batch = [create_event(i) for i in range(10000)]

stats = await pipeline.process_batch(large_batch)

print(f"Processed {stats['total']} events in {stats['processing_time_ms']:.1f}ms")
print(f"Throughput: {stats['total'] / (stats['processing_time_ms'] / 1000):.0f} events/sec")
```

## Integration

### MCP Server Integration

Pipeline can be integrated into MCP handlers:

```python
from athena.episodic.pipeline import EventProcessingPipeline

class MemoryMCPServer:
    def __init__(self):
        self.pipeline = EventProcessingPipeline(
            self.episodic_store,
            self.embedding_model,
            self.hasher
        )

    async def record_events_batch(self, events: List[EpisodicEvent]) -> Dict:
        """Record batch of events via pipeline."""
        return await self.pipeline.process_batch(events)
```

### Git Hook Integration

Process commits as events:

```python
# post-commit hook
commits = parse_git_commits()
events = [commit_to_event(c) for c in commits]
stats = await pipeline.process_batch(events)
```

## Testing

See `examples/event_pipeline_demo.py` for comprehensive demonstrations:

```bash
python examples/event_pipeline_demo.py
```

## See Also

- **EventHasher**: Content-based hashing for deduplication
- **EpisodicStore**: Low-level storage operations
- **Event Models**: Event data structures and types
