"""Event source ingestion system for episodic memory.

This module provides the foundational infrastructure for extracting episodic
events from external data sources (filesystem, GitHub, Slack, API logs, etc.)
and transforming them into EpisodicEvent instances for storage.

Core Components:
- BaseEventSource: Abstract base class for all event sources
- EventSourceFactory: Factory for creating and managing sources

Usage:
```python
from athena.episodic.sources import EventSourceFactory

# Create factory
factory = EventSourceFactory()

# Create a source
source = await factory.create_source(
    source_type='github',
    source_id='athena-repo',
    credentials={'token': 'ghp_xxx'},
    config={'owner': 'user', 'repo': 'athena'}
)

# Generate events
async for event in source.generate_events():
    episodic_store.record_event(event)

# Save cursor for incremental sync
await factory.save_cursor(source.source_id)
```

Available Source Types (when implemented):
- 'filesystem': File system events (git commits, file changes)
- 'github': GitHub API events (PRs, commits, issues, reviews)
- 'slack': Slack workspace events (messages, reactions, threads)
- 'api_log': API request logs (HTTP requests/responses)
"""

from ._base import BaseEventSource
from .factory import EventSourceFactory

# Import source implementations to auto-register them
try:
    from .filesystem import FileSystemEventSource
except ImportError:
    FileSystemEventSource = None

try:
    from .github import GitHubEventSource
except ImportError:
    GitHubEventSource = None

try:
    from .slack import SlackEventSource
except ImportError:
    SlackEventSource = None

__all__ = [
    "BaseEventSource",
    "EventSourceFactory",
    "FileSystemEventSource",
    "GitHubEventSource",
    "SlackEventSource",
]
