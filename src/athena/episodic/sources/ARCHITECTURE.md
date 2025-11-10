# Event Source Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    External Data Sources                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │   Git    │  │  GitHub  │  │  Slack   │  │  API Log │  ...  │
│  │ Repository│  │   API    │  │   API    │  │  Files   │       │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘       │
└────────┼─────────────┼─────────────┼─────────────┼─────────────┘
         │             │             │             │
         ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Event Source Implementations                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Filesystem   │  │   GitHub     │  │    Slack     │          │
│  │ EventSource  │  │ EventSource  │  │ EventSource  │   ...    │
│  │              │  │              │  │              │          │
│  │ - extract    │  │ - extract    │  │ - extract    │          │
│  │ - transform  │  │ - transform  │  │ - transform  │          │
│  │ - validate   │  │ - validate   │  │ - validate   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼──────────────────┼──────────────────┼──────────────────┘
          │                  │                  │
          │ implements       │ implements       │ implements
          │                  │                  │
          └──────────────────┴──────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   BaseEventSource (ABC)                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Required Abstract Methods:                                │ │
│  │  - create(credentials, config) -> EventSource              │ │
│  │  - generate_events() -> AsyncGenerator[EpisodicEvent]      │ │
│  │  - validate() -> bool                                      │ │
│  │                                                            │ │
│  │  Optional Methods (Incremental Sync):                     │ │
│  │  - supports_incremental() -> bool                         │ │
│  │  - get_cursor() -> dict                                   │ │
│  │  - set_cursor(cursor: dict)                               │ │
│  │                                                            │ │
│  │  Common Utilities:                                        │ │
│  │  - _batch_events()                                        │ │
│  │  - _log_event_generated()                                 │ │
│  │  - _validate_event()                                      │ │
│  │  - get_stats()                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                             │
                             │ used by
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  EventSourceFactory                              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Source Registry:                                          │ │
│  │  - register_source(type, class)                           │ │
│  │  - get_registered_sources() -> List[str]                  │ │
│  │  - is_source_available(type) -> bool                      │ │
│  │                                                            │ │
│  │  Source Creation:                                         │ │
│  │  - create_source(type, id, creds, config) -> Source      │ │
│  │                                                            │ │
│  │  Cursor Management:                                       │ │
│  │  - save_cursor(source_id)                                 │ │
│  │  - _load_cursor(source_id) -> dict                        │ │
│  │                                                            │ │
│  │  Lifecycle:                                               │ │
│  │  - get_active_sources() -> dict                           │ │
│  │  - close_source(source_id)                                │ │
│  │  - close_all_sources()                                    │ │
│  └────────────────────────────────────────────────────────────┘ │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        │ creates & manages
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Active Event Sources                            │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐               │
│  │  Source 1  │  │  Source 2  │  │  Source 3  │               │
│  │  (github)  │  │(filesystem)│  │  (slack)   │               │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘               │
└────────┼───────────────┼───────────────┼────────────────────────┘
         │               │               │
         │ generates     │ generates     │ generates
         │               │               │
         ▼               ▼               ▼
    EpisodicEvent   EpisodicEvent   EpisodicEvent
         │               │               │
         └───────────────┴───────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EpisodicStore                                 │
│  - record_event(event)                                          │
│  - batch_record_events(events)                                  │
│  - get_events_by_session(session_id)                            │
│  - search_events(query)                                         │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Source Registration (Module Import Time)

```
┌─────────────────────┐
│  filesystem.py      │
│  imported           │
└──────┬──────────────┘
       │
       │ calls
       ▼
┌─────────────────────────────────────┐
│ EventSourceFactory.register_source( │
│   'filesystem',                     │
│   FilesystemEventSource             │
│ )                                   │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────┐
│  Registry Updated   │
│  'filesystem' ->    │
│  FilesystemEvent... │
└─────────────────────┘
```

### 2. Source Creation & Event Generation

```
User Code
   │
   │ 1. Create factory
   ▼
┌──────────────────────┐
│ factory = EventSource│
│ Factory()            │
└──────┬───────────────┘
       │
       │ 2. Create source
       ▼
┌──────────────────────────────────┐
│ source = await factory.create_   │
│   source(                         │
│     type='filesystem',            │
│     id='athena-repo',             │
│     credentials={},               │
│     config={'root_dir': '/path'} │
│   )                               │
└──────┬───────────────────────────┘
       │
       │ 3. Factory internals
       ├─────────────────────────────────┐
       │                                 │
       ▼                                 ▼
┌─────────────────┐           ┌─────────────────┐
│ Load cursor     │           │ Validate type   │
│ (if available)  │           │ is registered   │
└─────┬───────────┘           └────────┬────────┘
      │                                │
      │ 4. Inject cursor               │
      ▼                                │
┌─────────────────┐                    │
│ config['cursor']│◄───────────────────┘
│ = saved_cursor  │
└─────┬───────────┘
      │
      │ 5. Call source's create()
      ▼
┌──────────────────────────────────┐
│ FilesystemEventSource.create(    │
│   credentials={},                 │
│   config={'root_dir': '...'}     │
│ )                                 │
└──────┬───────────────────────────┘
       │
       │ 6. Validate source
       ▼
┌──────────────────────┐
│ await source.        │
│   validate()         │
└──────┬───────────────┘
       │
       │ 7. Track active
       ▼
┌──────────────────────┐
│ factory._active_     │
│   sources[id] =      │
│   source             │
└──────┬───────────────┘
       │
       │ 8. Return source
       ▼
User Code
   │
   │ 9. Generate events
   ▼
┌──────────────────────────────────┐
│ async for event in               │
│   source.generate_events():      │
│     episodic_store.record_event( │
│       event                       │
│     )                             │
└──────┬───────────────────────────┘
       │
       │ 10. Save cursor
       ▼
┌──────────────────────┐
│ await factory.       │
│   save_cursor(       │
│     source.source_id │
│   )                  │
└──────────────────────┘
```

### 3. Incremental Sync Flow

```
┌─────────────────────┐
│  First Sync         │
│  (full extraction)  │
└──────┬──────────────┘
       │
       │ 1. Generate events
       ▼
┌─────────────────────┐
│  All events         │
│  extracted          │
└──────┬──────────────┘
       │
       │ 2. Get cursor
       ▼
┌─────────────────────┐
│ cursor = await      │
│   source.get_cursor()│
└──────┬──────────────┘
       │
       │ 3. Save cursor
       ▼
┌─────────────────────┐
│ cursor_store.save(  │
│   source_id, cursor │
│ )                   │
└──────┬──────────────┘
       │
       │ ... time passes ...
       │
       │ 4. Load cursor
       ▼
┌─────────────────────┐
│ saved_cursor =      │
│   cursor_store.load(│
│     source_id       │
│   )                 │
└──────┬──────────────┘
       │
       │ 5. Create source with cursor
       ▼
┌─────────────────────────────┐
│ source = await factory.     │
│   create_source(            │
│     ...,                    │
│     config={                │
│       'cursor': saved_cursor│
│     }                       │
│   )                         │
└──────┬──────────────────────┘
       │
       │ 6. Generate events
       ▼
┌─────────────────────┐
│  Only NEW events    │
│  (since cursor)     │
└─────────────────────┘
```

## Class Hierarchy

```
BaseEventSource (ABC)
    │
    ├── FilesystemEventSource
    │   └── Extracts git commits from local repos
    │
    ├── GitHubEventSource (to be implemented)
    │   └── Extracts PRs, commits, issues from GitHub API
    │
    ├── SlackEventSource (to be implemented)
    │   └── Extracts messages, reactions from Slack API
    │
    └── APILogEventSource (to be implemented)
        └── Extracts HTTP requests from log files
```

## Interface Contract

### BaseEventSource Required Methods

```python
class BaseEventSource(ABC):
    # Factory method - MUST implement
    @classmethod
    @abstractmethod
    async def create(
        cls,
        credentials: Dict[str, Any],
        config: Dict[str, Any]
    ) -> "BaseEventSource":
        """Create and initialize source."""
        pass

    # Event generation - MUST implement
    @abstractmethod
    async def generate_events(
        self
    ) -> AsyncGenerator[EpisodicEvent, None]:
        """Generate events from source."""
        pass

    # Health check - MUST implement
    @abstractmethod
    async def validate(self) -> bool:
        """Validate source connectivity."""
        pass

    # Incremental sync - OPTIONAL
    async def supports_incremental(self) -> bool:
        """Does this source support cursors?"""
        return False  # Default: no

    async def get_cursor(self) -> Optional[Dict[str, Any]]:
        """Get current sync state."""
        return None  # Default: no cursor

    async def set_cursor(self, cursor: Dict[str, Any]) -> None:
        """Restore previous sync state."""
        pass  # Default: no-op
```

## Configuration Examples

### Filesystem Source

```python
credentials = {}  # No auth needed

config = {
    'root_dir': '/home/user/.work/athena',
    'branch': 'main',
    'max_commits': 100,
    'patterns': ['*.py', '*.md'],
    'cursor': {  # Optional: for incremental sync
        'last_commit_sha': 'abc123'
    }
}
```

### GitHub Source (to be implemented)

```python
credentials = {
    'token': 'ghp_xxxxxxxxxxxxx'
}

config = {
    'owner': 'user',
    'repo': 'athena',
    'branch': 'main',
    'events': ['push', 'pull_request', 'issues'],
    'since': '2025-01-01',
    'cursor': {  # Optional
        'last_pr_number': 42,
        'last_commit_sha': 'abc123'
    }
}
```

### Slack Source (to be implemented)

```python
credentials = {
    'bot_token': 'xoxb-xxxxxxxxxxxxx'
}

config = {
    'workspace': 'my-workspace',
    'channels': ['general', 'dev', 'random'],
    'since': '2025-01-01',
    'cursor': {  # Optional
        'latest_timestamp': '1699999999.123456'
    }
}
```

## Thread Safety

The factory and sources are designed for async/await concurrency:

- **Factory**: Thread-safe for source creation (asyncio concurrency)
- **Sources**: Each source instance is not thread-safe (use one per task)
- **Registry**: Class-level registry is global (all factories share)

**Recommendation**: Create one factory instance per application, create separate source instances per concurrent task.

```python
# Single factory (shared)
factory = EventSourceFactory()

# Multiple sources (concurrent)
async with asyncio.TaskGroup() as tg:
    for source_config in configs:
        source = await factory.create_source(**source_config)
        tg.create_task(process_source(source))
```

## Error Handling Strategy

### Source Creation Errors

```python
try:
    source = await factory.create_source(...)
except ValueError:
    # Invalid config or credentials
    pass
except ConnectionError:
    # Network or API errors
    pass
```

### Validation Errors

```python
source = await factory.create_source(...)
if not await source.validate():
    # Source is unhealthy
    pass
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

## Performance Characteristics

| Operation                | Complexity | Notes                          |
|--------------------------|-----------|--------------------------------|
| Source registration      | O(1)      | Hash table lookup              |
| Source creation          | O(1)      | Factory overhead minimal       |
| Event generation         | O(n)      | Streaming, no buffering        |
| Cursor save/load         | O(1)      | Direct storage access          |
| Factory stats            | O(k)      | k = active sources             |

## Memory Usage

- **Factory**: ~1KB (registry + active sources dict)
- **Source instance**: ~10KB (varies by implementation)
- **Event streaming**: O(1) (async generator, no buffering)
- **Cursor storage**: O(n) where n = number of sources

**Total**: ~10KB per active source + cursor overhead
