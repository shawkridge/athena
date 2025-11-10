"""Base abstract class for episodic event sources.

This module provides the foundational interface for all event ingestion sources.
Event sources extract episodic events from various external systems (filesystem,
GitHub, Slack, API logs, etc.) and transform them into EpisodicEvent instances.

Design Patterns:
- Abstract Base Class (ABC): Enforces consistent interface across all sources
- Factory Method: create() classmethod for dependency injection
- Template Method: Common utilities with extensible core methods
- Async Generator: Streaming event extraction for memory efficiency
- Cursor-based Incremental Sync: Optional support for resumable ingestion
"""

import logging
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, Dict, Any, List
from datetime import datetime

from ..models import EpisodicEvent


class BaseEventSource(ABC):
    """Abstract base class for all episodic event sources.

    Event sources are responsible for:
    1. Connecting to external data sources (filesystem, APIs, databases, etc.)
    2. Extracting raw event data
    3. Transforming data into EpisodicEvent instances
    4. Supporting incremental sync (optional, via cursors)
    5. Health checks and validation

    Usage Pattern:
    ```python
    # Create source instance
    source = await FilesystemEventSource.create(
        credentials={'api_key': 'xxx'},
        config={'root_dir': '/path/to/code'}
    )

    # Validate connection
    if await source.validate():
        # Generate events (async iterator)
        async for event in source.generate_events():
            episodic_store.record_event(event)

    # Save sync state for incremental updates
    cursor = await source.get_cursor()
    cursor_store.save(source.source_id, cursor)
    ```

    Incremental Sync Pattern:
    ```python
    # Load previous sync state
    cursor = cursor_store.load(source.source_id)

    # Create source with cursor
    source = await FilesystemEventSource.create(
        credentials={...},
        config={'cursor': cursor}
    )

    # Only new events since last sync
    async for event in source.generate_events():
        episodic_store.record_event(event)
    ```
    """

    def __init__(
        self,
        source_id: str,
        source_type: str,
        source_name: str,
        config: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None
    ):
        """Initialize base event source.

        Args:
            source_id: Unique identifier (e.g., 'github-athena-repo')
            source_type: Source category ('filesystem', 'github', 'slack', 'api_log')
            source_name: Human-readable name (e.g., 'Athena Repository')
            config: Source-specific configuration
            logger: Optional logger instance
        """
        self._source_id = source_id
        self._source_type = source_type
        self._source_name = source_name
        self._config = config or {}
        self._logger = logger or logging.getLogger(self.__class__.__name__)

        # Event generation metrics
        self._events_generated = 0
        self._events_failed = 0
        self._last_event_time: Optional[datetime] = None

    # ========================================================================
    # Required Properties (Subclasses must provide these)
    # ========================================================================

    @property
    def source_id(self) -> str:
        """Unique identifier for this source instance.

        Example: 'github-athena-repo', 'slack-dev-channel'
        """
        return self._source_id

    @property
    def source_type(self) -> str:
        """Source type category.

        Returns:
            One of: 'filesystem', 'github', 'slack', 'api_log', 'custom'
        """
        return self._source_type

    @property
    def source_name(self) -> str:
        """Human-readable source name.

        Example: 'Athena Repository', 'Development Slack Channel'
        """
        return self._source_name

    # ========================================================================
    # Required Abstract Methods (Subclasses MUST implement)
    # ========================================================================

    @classmethod
    @abstractmethod
    async def create(
        cls,
        credentials: Dict[str, Any],
        config: Dict[str, Any]
    ) -> "BaseEventSource":
        """Factory method to create and initialize an event source.

        This is the primary entry point for creating event sources. Subclasses
        should:
        1. Validate credentials and config
        2. Establish connections (API clients, file handles, etc.)
        3. Load previous sync state (cursor) if available
        4. Return initialized instance

        Args:
            credentials: Authentication credentials
                Examples:
                - GitHub: {'token': 'ghp_xxx'}
                - Slack: {'bot_token': 'xoxb-xxx'}
                - Filesystem: {} (no auth)
            config: Source-specific configuration
                Examples:
                - GitHub: {'owner': 'user', 'repo': 'athena', 'branch': 'main'}
                - Filesystem: {'root_dir': '/path', 'patterns': ['*.py']}
                - Cursor: {'cursor': {...}} (for incremental sync)

        Returns:
            Initialized event source instance

        Raises:
            ValueError: Invalid credentials or config
            ConnectionError: Failed to connect to external source
        """
        pass

    @abstractmethod
    async def generate_events(self) -> AsyncGenerator[EpisodicEvent, None]:
        """Generate episodic events from this source.

        This is the main extraction method. It should:
        1. Fetch raw data from external source
        2. Transform into EpisodicEvent instances
        3. Yield events incrementally (don't buffer all in memory)
        4. Handle pagination/batching for large datasets
        5. Update internal cursor state as events are generated

        Yields:
            EpisodicEvent instances

        Example Implementation:
        ```python
        async def generate_events(self):
            # Fetch data in batches
            async for batch in self._fetch_batches():
                # Transform each item to event
                for item in batch:
                    event = self._transform_to_event(item)

                    # Validate before yielding
                    if await self._validate_event(event):
                        self._log_event_generated(event)
                        yield event
                    else:
                        self._events_failed += 1
        ```
        """
        pass

    @abstractmethod
    async def validate(self) -> bool:
        """Validate source health and connectivity.

        This method should check:
        1. Credentials are valid
        2. Connection to external system works
        3. Required permissions are granted
        4. Configuration is correct

        Returns:
            True if source is healthy, False otherwise

        Example Implementation:
        ```python
        async def validate(self):
            try:
                # Test API connection
                response = await self.client.get('/user')
                return response.status == 200
            except Exception as e:
                self._logger.error(f"Validation failed: {e}")
                return False
        ```
        """
        pass

    # ========================================================================
    # Optional Methods (Incremental Sync Support)
    # ========================================================================

    async def supports_incremental(self) -> bool:
        """Check if this source supports incremental sync.

        Incremental sync allows resuming from a previous sync point,
        avoiding re-processing of already-seen events.

        Returns:
            True if incremental sync is supported, False otherwise
        """
        return False

    async def get_cursor(self) -> Optional[Dict[str, Any]]:
        """Get current sync cursor (state for incremental sync).

        The cursor represents the current position in the event stream.
        It should contain enough information to resume from this point.

        Returns:
            Cursor dict with source-specific state
            Examples:
            - GitHub: {'last_commit_sha': 'abc123', 'last_pr_number': 42}
            - Filesystem: {'last_modified_time': 1699999999}
            - Slack: {'latest_timestamp': '1699999999.123456'}

        Returns None if:
        - Incremental sync not supported
        - No events have been generated yet
        """
        return None

    async def set_cursor(self, cursor: Dict[str, Any]) -> None:
        """Set sync cursor (for resuming from a previous state).

        This should be called when loading a source with saved state:
        ```python
        source = await GitHubEventSource.create(
            credentials={'token': 'xxx'},
            config={'cursor': saved_cursor}
        )
        ```

        Args:
            cursor: Previously saved cursor dict
        """
        pass

    # ========================================================================
    # Common Utility Methods (Available to all subclasses)
    # ========================================================================

    async def _batch_events(
        self,
        events: List[EpisodicEvent],
        batch_size: int = 100
    ) -> AsyncGenerator[List[EpisodicEvent], None]:
        """Batch events for efficient processing.

        Useful when source returns large volumes of events.

        Args:
            events: List of events to batch
            batch_size: Number of events per batch

        Yields:
            Batches of events

        Example Usage:
        ```python
        events = await self._fetch_all_events()
        async for batch in self._batch_events(events):
            # Process batch
            for event in batch:
                yield event
        ```
        """
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            yield batch

    def _log_event_generated(self, event: EpisodicEvent) -> None:
        """Log successful event generation (for monitoring).

        Updates internal metrics and logs debug info.

        Args:
            event: Generated event
        """
        self._events_generated += 1
        self._last_event_time = event.timestamp

        self._logger.debug(
            f"Generated event {self._events_generated}: "
            f"type={event.event_type}, content={event.content[:50]}"
        )

    async def _validate_event(self, event: EpisodicEvent) -> bool:
        """Validate an event before yielding.

        Checks:
        1. Required fields are present
        2. Timestamp is valid
        3. Content is not empty
        4. Event type is valid

        Args:
            event: Event to validate

        Returns:
            True if event is valid, False otherwise
        """
        try:
            # Check required fields
            if not event.content or not event.event_type:
                self._logger.warning("Event missing required fields")
                return False

            # Check timestamp is reasonable (not in future, not too old)
            now = datetime.now()
            if event.timestamp > now:
                self._logger.warning(f"Event timestamp in future: {event.timestamp}")
                return False

            # Passed all checks
            return True

        except Exception as e:
            self._logger.error(f"Event validation error: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get source statistics.

        Returns:
            Dict with generation metrics
            Example:
            {
                'source_id': 'github-athena-repo',
                'source_type': 'github',
                'events_generated': 142,
                'events_failed': 3,
                'last_event_time': datetime(2025, 11, 10, 10, 30)
            }
        """
        return {
            'source_id': self.source_id,
            'source_type': self.source_type,
            'source_name': self.source_name,
            'events_generated': self._events_generated,
            'events_failed': self._events_failed,
            'last_event_time': self._last_event_time,
        }

    # ========================================================================
    # Context Manager Support (Optional)
    # ========================================================================

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit (cleanup)."""
        # Subclasses can override to close connections, etc.
        pass

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<{self.__class__.__name__} "
            f"source_id='{self.source_id}' "
            f"type='{self.source_type}' "
            f"events={self._events_generated}>"
        )
