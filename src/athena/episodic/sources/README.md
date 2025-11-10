# Multi-Source Event Ingestion System

This module provides the foundational infrastructure for extracting episodic events from external data sources and transforming them into `EpisodicEvent` instances for storage in Athena's memory system.

## Architecture Overview

### Core Components

1. **BaseEventSource** (`_base.py`)
   - Abstract base class defining the event source interface
   - Enforces consistent API across all source implementations
   - Provides common utilities (batching, validation, logging)
   - Supports incremental sync via cursor-based state management

2. **EventSourceFactory** (`factory.py`)
   - Factory pattern for creating and managing event sources
   - Plugin-style source registration system
   - Dependency injection for logger, cursor store
   - Source lifecycle management

3. **Concrete Implementations** (to be implemented)
   - `filesystem.py`: File system events (git commits, file changes)
   - `github.py`: GitHub API events (PRs, commits, issues)
   - `slack.py`: Slack workspace events (messages, reactions)
   - `api_log.py`: API request logs (HTTP requests/responses)

## Design Patterns

### 1. Abstract Base Class (ABC)

All event sources inherit from `BaseEventSource` and must implement:

- `create()`: Factory method for initialization with credentials and config
- `generate_events()`: Async generator yielding `EpisodicEvent` instances
- `validate()`: Health check for source connectivity

**Benefits:**
- Enforces consistent interface
- Type safety with mypy
- Clear contract for implementers

### 2. Factory Method Pattern

`EventSourceFactory` provides centralized source creation:

```python
factory = EventSourceFactory()

# Factory handles validation, dependency injection, etc.
source = await factory.create_source(
    source_type='github',
    source_id='athena-repo',
    credentials={'token': 'ghp_xxx'},
    config={'owner': 'user', 'repo': 'athena'}
)
```

**Benefits:**
- Single point of source creation
- Dependency injection (logger, cursor store)
- Validation and error handling
- Source registry management

### 3. Registry Pattern

Sources self-register with the factory:

```python
# In github.py
class GitHubEventSource(BaseEventSource):
    ...

# Auto-register on module import
EventSourceFactory.register_source('github', GitHubEventSource)
```

**Benefits:**
- Plugin-style architecture
- Dynamic source discovery
- Extensibility without modifying core code

### 4. Async Generator Pattern

Event generation uses async generators for memory efficiency:

```python
async def generate_events(self) -> AsyncGenerator[EpisodicEvent, None]:
    async for batch in self._fetch_batches():
        for item in batch:
            event = self._transform_to_event(item)
            yield event  # Streaming, not buffering
```

**Benefits:**
- Memory efficient (no buffering all events)
- Natural pagination support
- Backpressure handling

### 5. Cursor-Based Incremental Sync

Sources optionally support resumable ingestion:

```python
# First sync
source = await factory.create_source(...)
async for event in source.generate_events():
    store.record_event(event)

# Save state
await factory.save_cursor(source.source_id)

# Later: incremental sync (only new events)
source = await factory.create_source(
    config={'cursor': saved_cursor}
)
async for event in source.generate_events():
    # Only new events since last sync
    store.record_event(event)
```

**Benefits:**
- Efficient re-ingestion
- Avoid duplicate processing
- Resumable after failures

## Usage Examples

### Basic Usage

```python
from athena.episodic.sources import EventSourceFactory
from athena.episodic.store import EpisodicStore

# Create factory
factory = EventSourceFactory()

# Create source
source = await factory.create_source(
    source_type='filesystem',
    source_id='athena-codebase',
    credentials={},
    config={
        'root_dir': '/home/user/.work/athena',
        'branch': 'main'
    }
)

# Validate connection
if not await source.validate():
    raise ConnectionError("Source validation failed")

# Generate and store events
episodic_store = EpisodicStore(db)
async for event in source.generate_events():
    episodic_store.record_event(event)

# Get statistics
stats = source.get_stats()
print(f"Generated {stats['events_generated']} events")
```

### Incremental Sync

```python
# First sync (full)
source = await factory.create_source(
    source_type='github',
    source_id='athena-repo',
    credentials={'token': 'ghp_xxx'},
    config={'owner': 'user', 'repo': 'athena'}
)

async for event in source.generate_events():
    episodic_store.record_event(event)

# Save cursor
cursor = await source.get_cursor()
cursor_store.save('athena-repo', cursor)

# Later: incremental sync
saved_cursor = cursor_store.load('athena-repo')
source = await factory.create_source(
    source_type='github',
    source_id='athena-repo',
    credentials={'token': 'ghp_xxx'},
    config={
        'owner': 'user',
        'repo': 'athena',
        'cursor': saved_cursor  # Resume from here
    }
)

# Only new events since last sync
async for event in source.generate_events():
    episodic_store.record_event(event)
```

### Custom Source Implementation

```python
from athena.episodic.sources import BaseEventSource, EventSourceFactory
from athena.episodic.models import EpisodicEvent, EventType

class CustomEventSource(BaseEventSource):
    """Custom event source implementation."""

    @classmethod
    async def create(cls, credentials: dict, config: dict):
        # Validate and initialize
        api_key = credentials.get('api_key')
        if not api_key:
            raise ValueError("api_key required")

        # Create instance
        return cls(
            source_id=config['source_id'],
            source_type='custom',
            source_name='Custom Source',
            config=config
        )

    async def generate_events(self):
        # Fetch data from external source
        data = await self._fetch_data()

        # Transform and yield events
        for item in data:
            event = EpisodicEvent(
                project_id=1,
                session_id='custom-session',
                event_type=EventType.ACTION,
                content=item['description'],
                # ... other fields
            )

            if await self._validate_event(event):
                self._log_event_generated(event)
                yield event

    async def validate(self) -> bool:
        # Check connectivity
        try:
            await self._test_connection()
            return True
        except Exception:
            return False

# Register with factory
EventSourceFactory.register_source('custom', CustomEventSource)
```

## Configuration Patterns

### Filesystem Source

```python
config = {
    'root_dir': '/path/to/repo',     # Git repository path
    'branch': 'main',                # Branch to extract
    'max_commits': 100,              # Max commits to extract
    'patterns': ['*.py', '*.md'],    # File patterns to include
}
```

### GitHub Source

```python
credentials = {
    'token': 'ghp_xxxxxxxxxxxxx'     # GitHub personal access token
}

config = {
    'owner': 'user',                 # Repository owner
    'repo': 'athena',                # Repository name
    'branch': 'main',                # Branch to extract
    'events': ['push', 'pull_request', 'issues'],
    'since': '2025-01-01'            # Start date
}
```

### Slack Source

```python
credentials = {
    'bot_token': 'xoxb-xxxxx'        # Slack bot token
}

config = {
    'workspace': 'my-workspace',     # Workspace ID
    'channels': ['general', 'dev'],  # Channels to monitor
    'since': '2025-01-01'            # Start date
}
```

### API Log Source

```python
config = {
    'log_file': '/var/log/api.log',  # Log file path
    'format': 'json',                # Log format (json, text)
    'filters': {
        'status': [500, 503],        # Only errors
        'endpoint': '/api/v1/*'      # Endpoint pattern
    }
}
```

## Implementation Checklist

When implementing a new event source:

### Required Methods
- [ ] `create()` - Factory method for initialization
- [ ] `generate_events()` - Async generator yielding events
- [ ] `validate()` - Health check for connectivity

### Optional Methods (Incremental Sync)
- [ ] `supports_incremental()` - Return True if cursor-based sync supported
- [ ] `get_cursor()` - Return current sync state
- [ ] `set_cursor()` - Restore previous sync state

### Registration
- [ ] Call `EventSourceFactory.register_source()` at module import time

### Testing
- [ ] Unit tests for event transformation
- [ ] Integration tests for full extraction
- [ ] Test incremental sync behavior
- [ ] Test error handling and validation

## Error Handling

### Connection Errors

```python
try:
    source = await factory.create_source(...)
except ConnectionError as e:
    logger.error(f"Failed to connect: {e}")
    # Retry logic here
```

### Validation Failures

```python
if not await source.validate():
    raise ConnectionError("Source validation failed")
```

### Event Generation Errors

```python
async for event in source.generate_events():
    try:
        episodic_store.record_event(event)
    except Exception as e:
        logger.error(f"Failed to store event: {e}")
        # Continue with next event
```

## Performance Considerations

### Memory Efficiency

- Use async generators (don't buffer all events)
- Implement batching for large datasets
- Stream directly to database

### Rate Limiting

```python
class GitHubEventSource(BaseEventSource):
    async def generate_events(self):
        async for batch in self._fetch_batches():
            for event in batch:
                yield event

            # Rate limiting between batches
            await asyncio.sleep(1)
```

### Caching

```python
class CachedEventSource(BaseEventSource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache = {}

    async def generate_events(self):
        # Check cache first
        cache_key = self._get_cache_key()
        if cache_key in self._cache:
            yield from self._cache[cache_key]
            return

        # Fetch fresh data
        events = []
        async for event in self._fetch_events():
            events.append(event)
            yield event

        # Update cache
        self._cache[cache_key] = events
```

## Testing

### Unit Tests

```python
import pytest
from athena.episodic.sources import EventSourceFactory

@pytest.mark.asyncio
async def test_create_source():
    factory = EventSourceFactory()

    source = await factory.create_source(
        source_type='filesystem',
        source_id='test-repo',
        credentials={},
        config={'root_dir': '/tmp/test-repo'}
    )

    assert source.source_id == 'test-repo'
    assert source.source_type == 'filesystem'

@pytest.mark.asyncio
async def test_generate_events():
    source = await factory.create_source(...)

    events = []
    async for event in source.generate_events():
        events.append(event)

    assert len(events) > 0
    assert all(event.content for event in events)
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_end_to_end_ingestion(db):
    factory = EventSourceFactory()
    episodic_store = EpisodicStore(db)

    # Create source
    source = await factory.create_source(...)

    # Generate and store events
    event_count = 0
    async for event in source.generate_events():
        episodic_store.record_event(event)
        event_count += 1

    # Verify stored events
    stored_events = episodic_store.get_recent_events(
        project_id=1,
        hours=24
    )

    assert len(stored_events) == event_count
```

## Future Enhancements

### Parallel Processing

```python
async def generate_events_parallel(sources: List[BaseEventSource]):
    async with asyncio.TaskGroup() as tg:
        for source in sources:
            tg.create_task(process_source(source))
```

### Monitoring and Metrics

```python
class MonitoredEventSource(BaseEventSource):
    async def generate_events(self):
        start_time = time.time()

        try:
            async for event in self._generate_events_impl():
                yield event
        finally:
            duration = time.time() - start_time
            metrics.record('event_generation_duration', duration)
            metrics.record('events_generated', self._events_generated)
```

### Retry Logic

```python
async def create_source_with_retry(
    factory: EventSourceFactory,
    max_retries: int = 3,
    **kwargs
):
    for attempt in range(max_retries):
        try:
            return await factory.create_source(**kwargs)
        except ConnectionError:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

## References

- [Episodic Memory Layer](/home/user/.work/athena/src/athena/episodic/)
- [Event Models](/home/user/.work/athena/src/athena/episodic/models.py)
- [Event Store](/home/user/.work/athena/src/athena/episodic/store.py)
- [Example Implementation](/home/user/.work/athena/src/athena/episodic/sources/_example_filesystem.py)
