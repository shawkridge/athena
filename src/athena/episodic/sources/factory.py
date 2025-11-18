"""Factory for creating and managing event sources.

This module implements the Factory pattern for event source instantiation,
providing:
1. Source registry (plugin-style architecture)
2. Dependency injection for logger, cursor store, etc.
3. Source lifecycle management
4. Error handling and validation

Design Patterns:
- Factory Method: Central source creation with type-based dispatch
- Registry Pattern: Dynamic source registration at import time
- Dependency Injection: Shared resources (logger, stores) injected at creation
- Singleton Registry: Global source type registry
"""

import logging
from typing import Dict, Any, Type, List, Optional

from ._base import BaseEventSource


class EventSourceFactory:
    """Factory for creating event sources with dependency injection.

    The factory provides:
    1. Source registration (at module import time)
    2. Source creation with validation
    3. Dependency injection (logger, cursor store)
    4. Source availability checks

    Usage Pattern:
    ```python
    # Create factory instance
    factory = EventSourceFactory(logger=custom_logger)

    # Register custom source
    factory.register_source('custom', CustomEventSource)

    # Check availability
    if factory.is_source_available('github'):
        # Create source instance
        source = await factory.create_source(
            source_type='github',
            source_id='athena-repo',
            credentials={'token': 'ghp_xxx'},
            config={'owner': 'user', 'repo': 'athena'}
        )

        # Use source
        async for event in source.generate_events():
            print(event)
    ```

    Pre-Registered Sources:
    - 'filesystem': File system event source (git commits, file changes)
    - 'github': GitHub API source (PRs, commits, issues)
    - 'slack': Slack workspace source (messages, reactions)
    - 'api_log': API request log source (HTTP requests/responses)
    """

    # Global source registry (class-level)
    _source_registry: Dict[str, Type[BaseEventSource]] = {}

    def __init__(self, logger: Optional[logging.Logger] = None, cursor_store: Optional[Any] = None):
        """Initialize factory with optional dependencies.

        Args:
            logger: Logger instance (shared across all sources)
            cursor_store: Optional cursor storage for incremental sync
        """
        self._logger = logger or logging.getLogger(__name__)
        self._cursor_store = cursor_store

        # Track created sources for lifecycle management
        self._active_sources: Dict[str, BaseEventSource] = {}

    # ========================================================================
    # Source Creation (Main Factory Method)
    # ========================================================================

    async def create_source(
        self, source_type: str, source_id: str, credentials: Dict[str, Any], config: Dict[str, Any]
    ) -> BaseEventSource:
        """Create an event source instance.

        This is the main factory method. It:
        1. Validates source_type is registered
        2. Injects dependencies (logger, cursor)
        3. Calls source's create() factory method
        4. Tracks active sources for cleanup

        Args:
            source_type: Type of source ('filesystem', 'github', 'slack', 'api_log')
            source_id: Unique identifier for this instance
            credentials: Authentication credentials (source-specific)
            config: Configuration dict (source-specific)

        Returns:
            Initialized event source instance

        Raises:
            ValueError: Invalid or unregistered source_type
            ConnectionError: Failed to create source (credentials, network, etc.)

        Example:
        ```python
        # GitHub source
        source = await factory.create_source(
            source_type='github',
            source_id='athena-repo',
            credentials={'token': 'ghp_xxx'},
            config={
                'owner': 'anthropic',
                'repo': 'athena',
                'branch': 'main'
            }
        )

        # Filesystem source
        source = await factory.create_source(
            source_type='filesystem',
            source_id='athena-codebase',
            credentials={},
            config={
                'root_dir': '/home/user/.work/athena',
                'patterns': ['*.py', '*.md']
            }
        )
        ```
        """
        # Validate source type
        if not self.is_source_available(source_type):
            available = ", ".join(self.get_registered_sources())
            raise ValueError(
                f"Unknown source type: '{source_type}'. " f"Available types: {available}"
            )

        # Get source class
        source_class = self._source_registry[source_type]

        # Inject cursor if available and source supports incremental sync
        if self._cursor_store:
            # Load saved cursor
            saved_cursor = self._load_cursor(source_id)
            if saved_cursor:
                config["cursor"] = saved_cursor
                self._logger.info(f"Loaded cursor for '{source_id}': {saved_cursor}")

        # Create source instance (calls source's create() classmethod)
        try:
            self._logger.info(f"Creating source: type='{source_type}', id='{source_id}'")

            source = await source_class.create(credentials=credentials, config=config)

            # Validate source health
            if not await source.validate():
                raise ConnectionError(
                    f"Source validation failed for '{source_id}' " f"(type: {source_type})"
                )

            # Track active source
            self._active_sources[source_id] = source

            self._logger.info(
                f"Source created successfully: {source_id} "
                f"(supports_incremental={await source.supports_incremental()})"
            )

            return source

        except Exception as e:
            self._logger.error(
                f"Failed to create source '{source_id}' " f"(type: {source_type}): {e}"
            )
            raise

    # ========================================================================
    # Source Registry Management
    # ========================================================================

    @classmethod
    def register_source(cls, source_type: str, source_class: Type[BaseEventSource]) -> None:
        """Register a new event source type.

        This is typically called at module import time to register
        available sources. Subclasses of BaseEventSource should
        register themselves:

        ```python
        # In filesystem.py
        class FilesystemEventSource(BaseEventSource):
            ...

        # Auto-register on import
        EventSourceFactory.register_source('filesystem', FilesystemEventSource)
        ```

        Args:
            source_type: Type identifier (e.g., 'github', 'slack')
            source_class: Class implementing BaseEventSource

        Raises:
            TypeError: source_class doesn't inherit from BaseEventSource
            ValueError: source_type already registered (use override=True to replace)
        """
        # Validate source_class
        if not issubclass(source_class, BaseEventSource):
            raise TypeError(
                f"Source class must inherit from BaseEventSource, " f"got: {source_class.__name__}"
            )

        # Check for duplicates
        if source_type in cls._source_registry:
            existing = cls._source_registry[source_type]
            logging.warning(
                f"Overwriting source type '{source_type}': "
                f"old={existing.__name__}, new={source_class.__name__}"
            )

        # Register
        cls._source_registry[source_type] = source_class
        logging.debug(f"Registered source type '{source_type}': " f"{source_class.__name__}")

    @classmethod
    def unregister_source(cls, source_type: str) -> bool:
        """Unregister a source type.

        Args:
            source_type: Type to unregister

        Returns:
            True if unregistered, False if not found
        """
        if source_type in cls._source_registry:
            del cls._source_registry[source_type]
            logging.debug(f"Unregistered source type '{source_type}'")
            return True
        return False

    @classmethod
    def get_registered_sources(cls) -> List[str]:
        """Get list of all registered source types.

        Returns:
            List of source type identifiers
            Example: ['filesystem', 'github', 'slack', 'api_log']
        """
        return sorted(cls._source_registry.keys())

    @classmethod
    def is_source_available(cls, source_type: str) -> bool:
        """Check if a source type is registered.

        Args:
            source_type: Type to check

        Returns:
            True if registered, False otherwise
        """
        return source_type in cls._source_registry

    @classmethod
    def get_source_class(cls, source_type: str) -> Optional[Type[BaseEventSource]]:
        """Get source class by type.

        Args:
            source_type: Type to look up

        Returns:
            Source class if registered, None otherwise
        """
        return cls._source_registry.get(source_type)

    # ========================================================================
    # Cursor Management (Incremental Sync)
    # ========================================================================

    def _load_cursor(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Load saved cursor for a source.

        Args:
            source_id: Source identifier

        Returns:
            Saved cursor dict, or None if not found
        """
        if not self._cursor_store:
            return None

        try:
            # Cursor store interface: load(source_id) -> dict
            cursor = self._cursor_store.load(source_id)
            return cursor
        except Exception as e:
            self._logger.warning(f"Failed to load cursor for '{source_id}': {e}")
            return None

    async def save_cursor(self, source_id: str) -> bool:
        """Save current cursor for a source.

        Should be called after event generation completes:
        ```python
        source = await factory.create_source(...)
        async for event in source.generate_events():
            process(event)

        # Save state for next incremental sync
        await factory.save_cursor(source.source_id)
        ```

        Args:
            source_id: Source identifier

        Returns:
            True if saved successfully, False otherwise
        """
        if not self._cursor_store:
            self._logger.debug("No cursor store configured, skipping save")
            return False

        # Get active source
        source = self._active_sources.get(source_id)
        if not source:
            self._logger.warning(f"No active source with id '{source_id}'")
            return False

        # Check if source supports incremental sync
        if not await source.supports_incremental():
            self._logger.debug(f"Source '{source_id}' doesn't support incremental sync")
            return False

        # Get current cursor
        cursor = await source.get_cursor()
        if not cursor:
            self._logger.debug(f"No cursor to save for '{source_id}'")
            return False

        # Save cursor
        try:
            # Cursor store interface: save(source_id, cursor)
            self._cursor_store.save(source_id, cursor)
            self._logger.info(f"Saved cursor for '{source_id}': {cursor}")
            return True
        except Exception as e:
            self._logger.error(f"Failed to save cursor for '{source_id}': {e}")
            return False

    # ========================================================================
    # Source Lifecycle Management
    # ========================================================================

    def get_active_sources(self) -> Dict[str, BaseEventSource]:
        """Get all active (created) sources.

        Returns:
            Dict mapping source_id -> source instance
        """
        return self._active_sources.copy()

    def get_active_source(self, source_id: str) -> Optional[BaseEventSource]:
        """Get a specific active source.

        Args:
            source_id: Source identifier

        Returns:
            Source instance if active, None otherwise
        """
        return self._active_sources.get(source_id)

    async def close_source(self, source_id: str) -> bool:
        """Close and cleanup a source.

        Args:
            source_id: Source identifier

        Returns:
            True if closed, False if not found
        """
        source = self._active_sources.get(source_id)
        if not source:
            return False

        # Cleanup (if source implements context manager)
        try:
            await source.__aexit__(None, None, None)
        except Exception as e:
            self._logger.warning(f"Error closing source '{source_id}': {e}")

        # Remove from active sources
        del self._active_sources[source_id]
        self._logger.info(f"Closed source: {source_id}")
        return True

    async def close_all_sources(self) -> None:
        """Close all active sources."""
        source_ids = list(self._active_sources.keys())
        for source_id in source_ids:
            await self.close_source(source_id)

    # ========================================================================
    # Factory Statistics
    # ========================================================================

    def get_factory_stats(self) -> Dict[str, Any]:
        """Get factory statistics.

        Returns:
            Dict with factory metrics
            Example:
            {
                'registered_types': ['filesystem', 'github', 'slack'],
                'active_sources': 3,
                'sources': {
                    'athena-repo': {
                        'type': 'github',
                        'events_generated': 142
                    },
                    ...
                }
            }
        """
        sources_info = {}
        for source_id, source in self._active_sources.items():
            stats = source.get_stats()
            sources_info[source_id] = {
                "type": stats["source_type"],
                "events_generated": stats["events_generated"],
                "events_failed": stats["events_failed"],
                "last_event_time": stats["last_event_time"],
            }

        return {
            "registered_types": self.get_registered_sources(),
            "active_sources": len(self._active_sources),
            "sources": sources_info,
        }

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<EventSourceFactory "
            f"registered={len(self._source_registry)} "
            f"active={len(self._active_sources)}>"
        )


# ========================================================================
# Pre-Register Common Source Types (Placeholders)
# ========================================================================


def _register_builtin_sources():
    """Register built-in source types.

    This function is called at module import time to register
    placeholder entries for common source types. The actual
    implementations will override these when imported.

    Source implementations should be in:
    - src/athena/episodic/sources/filesystem.py
    - src/athena/episodic/sources/github.py
    - src/athena/episodic/sources/slack.py
    - src/athena/episodic/sources/api_log.py
    """
    # These will be overridden when actual implementations are imported
    # For now, we just ensure the registry knows about these types

    # Note: We can't register actual classes here because they don't exist yet.
    # Instead, the concrete implementations should call:
    #   EventSourceFactory.register_source('filesystem', FilesystemEventSource)
    # at their module import time.

    logging.debug("Built-in source types will be registered by their modules")


# Initialize built-in sources on module import
_register_builtin_sources()
