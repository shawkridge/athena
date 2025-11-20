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
# DESIGN: Sources are OPTIONAL but must fail LOUDLY if used when unavailable
# This allows graceful degradation (app starts without Slack) but prevents
# silent failures (trying to use Slack crashes immediately with clear message)

import logging

logger = logging.getLogger(__name__)

FileSystemEventSource = None
GitHubEventSource = None
SlackEventSource = None

try:
    from .filesystem import FileSystemEventSource
except ImportError as e:
    logger.warning(
        f"FileSystemEventSource unavailable: {e}. Install with: pip install athena[filesystem]"
    )

try:
    from .github import GitHubEventSource
except ImportError as e:
    logger.warning(f"GitHubEventSource unavailable: {e}. Install with: pip install aiohttp")

try:
    from .slack import SlackEventSource
except ImportError as e:
    logger.warning(f"SlackEventSource unavailable: {e}. Install with: pip install slack-sdk")

__all__ = [
    "BaseEventSource",
    "EventSourceFactory",
    "FileSystemEventSource",
    "GitHubEventSource",
    "SlackEventSource",
]
