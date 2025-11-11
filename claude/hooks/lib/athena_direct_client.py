"""Direct Python client for Athena memory operations (local-first).

This client imports and uses the Athena MemoryAPI directly, without HTTP.
It provides the same interface as the HTTP client but with direct Python calls.

Usage:
    from athena_direct_client import AthenaDirectClient

    client = AthenaDirectClient()

    # Store memory
    memory_id = client.remember(
        content="Important finding",
        memory_type="semantic"
    )

    # Recall memory
    results = client.recall(query="recent findings", limit=5)

    # Record event
    event_id = client.record_event(
        event_type="action",
        content="Ran test suite"
    )
"""

import logging
import sys
from typing import Any, Dict, Optional, List

logger = logging.getLogger(__name__)


class AthenaDirectClient:
    """Direct Python client for Athena memory API."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize direct Athena client.

        Args:
            db_path: Optional path to database file. If None, uses default.
        """
        self.db_path = db_path
        self.api = None
        self._initialized = False

        # Lazy initialization of API on first use
        logger.info("Initialized AthenaDirectClient (lazy-loading)")

    def _ensure_initialized(self) -> bool:
        """Initialize the MemoryAPI on first use.

        Returns:
            True if successfully initialized, False otherwise
        """
        if self._initialized:
            return True

        try:
            # Import MemoryAPI from local athena package
            from athena.mcp.memory_api import MemoryAPI

            logger.debug("Importing MemoryAPI from athena package")
            self.api = MemoryAPI.create(db_path=self.db_path)
            self._initialized = True
            logger.info("✅ MemoryAPI initialized successfully")
            return True

        except ImportError as e:
            logger.error(f"❌ Failed to import MemoryAPI: {e}")
            logger.error("Make sure athena is installed in your Python environment")
            logger.error("Run: pip install -e . (in athena directory)")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to initialize MemoryAPI: {e}")
            logger.debug(f"Exception details: {e}", exc_info=True)
            return False

    def health(self) -> Dict[str, Any]:
        """Check Athena health status.

        Returns:
            Health status dictionary
        """
        if not self._ensure_initialized():
            return {"status": "error", "message": "MemoryAPI not available"}

        try:
            # Check if database is accessible
            if hasattr(self.api, "db") and self.api.db:
                return {
                    "status": "healthy",
                    "message": "Athena memory system is operational",
                    "api_type": "direct_python",
                }
            else:
                return {"status": "degraded", "message": "Database connection not available"}
        except Exception as e:
            return {"status": "error", "message": f"Health check failed: {e}"}

    def record_event(
        self,
        event_type: str,
        content: str,
        outcome: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """Record an episodic event.

        Args:
            event_type: Type of event (action|decision|observation|error|success)
            content: Event description
            outcome: Outcome status (success|failure|partial|unknown)
            context: Additional context data

        Returns:
            Event ID if successful, None otherwise
        """
        if not self._ensure_initialized():
            return None

        try:
            event_id = self.api.remember_event(
                event_type=event_type,
                content=content,
                outcome=outcome or "unknown",
                context=context or {},
            )
            logger.debug(f"Recorded event {event_type}: {event_id}")
            return event_id
        except Exception as e:
            logger.warning(f"Failed to record event: {e}")
            return None

    def recall(self, query: str, k: int = 5) -> Optional[Dict]:
        """Recall memories matching query.

        Args:
            query: Search query
            k: Number of results to return (limit)

        Returns:
            Dictionary of matching memories, None on error
        """
        if not self._ensure_initialized():
            return None

        try:
            results = self.api.recall(query=query, limit=k)
            logger.debug(f"Recalled memories for query: {query}")
            return results
        except Exception as e:
            logger.warning(f"Failed to recall memories: {e}")
            return None

    def remember(
        self,
        content: str,
        memory_type: str = "semantic",
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[int]:
        """Store a semantic memory.

        Args:
            content: Memory content
            memory_type: Type of memory (semantic|fact|event|context|procedure|pattern|task|decision)
            context: Optional context metadata
            tags: Optional tags for categorization

        Returns:
            Memory ID if successful, None otherwise
        """
        if not self._ensure_initialized():
            return None

        try:
            memory_id = self.api.remember(
                content=content,
                memory_type=memory_type,
                context=context,
                tags=tags or [],
            )
            logger.debug(f"Stored {memory_type} memory: {memory_id}")
            return memory_id
        except Exception as e:
            logger.warning(f"Failed to store memory: {e}")
            return None

    def forget(self, memory_id: int) -> bool:
        """Delete a memory.

        Args:
            memory_id: ID of memory to delete

        Returns:
            True if successful, False otherwise
        """
        if not self._ensure_initialized():
            return False

        try:
            success = self.api.forget(memory_id=memory_id)
            if success:
                logger.debug(f"Forgot memory: {memory_id}")
            return success
        except Exception as e:
            logger.warning(f"Failed to forget memory: {e}")
            return False

    def get_memory_quality_summary(self) -> Optional[Dict[str, Any]]:
        """Get memory quality metrics.

        Returns:
            Quality summary dictionary, None on error
        """
        if not self._ensure_initialized():
            return None

        try:
            summary = self.api.get_memory_quality()
            return summary
        except Exception as e:
            logger.warning(f"Failed to get memory quality: {e}")
            return None

    def run_consolidation(
        self, strategy: str = "balanced", dry_run: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Run memory consolidation.

        Args:
            strategy: Consolidation strategy (balanced, speed, quality, minimal)
            dry_run: If True, don't persist results

        Returns:
            Consolidation results, None on error
        """
        if not self._ensure_initialized():
            return None

        try:
            results = self.api.consolidate(strategy=strategy, dry_run=dry_run)
            logger.info(f"Consolidation complete ({strategy} strategy)")
            return results
        except Exception as e:
            logger.warning(f"Failed to run consolidation: {e}")
            return None

    def check_cognitive_load(self) -> Optional[Dict[str, Any]]:
        """Check current cognitive load.

        Returns:
            Cognitive load metrics, None on error
        """
        if not self._ensure_initialized():
            return None

        try:
            load = self.api.get_cognitive_load()
            return load
        except Exception as e:
            logger.warning(f"Failed to check cognitive load: {e}")
            return None

    def get_memory_health(self) -> Optional[Dict[str, Any]]:
        """Get overall memory system health.

        Returns:
            Health metrics, None on error
        """
        if not self._ensure_initialized():
            return None

        try:
            health = self.api.get_memory_health()
            return health
        except Exception as e:
            logger.warning(f"Failed to get memory health: {e}")
            return None

    def close(self):
        """Clean up resources."""
        if self.api and hasattr(self.api, "db"):
            try:
                if hasattr(self.api.db, "close"):
                    self.api.db.close()
            except Exception as e:
                logger.debug(f"Error closing database: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, *args):
        """Context manager exit."""
        self.close()
