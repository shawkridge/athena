"""Direct Python client for Athena memory operations (filesystem API paradigm).

This client uses the FilesystemAPIAdapter to implement the code execution paradigm:
- Discover operations via filesystem (progressive disclosure)
- Read operation code before executing
- Execute locally (in sandbox, not in model context)
- Return summaries (never full data objects)

This achieves ~99% token reduction compared to the old pattern.

Usage:
    from athena_direct_client import AthenaDirectClient

    client = AthenaDirectClient()

    # Health check (via filesystem API)
    health = client.health()

    # Recall memories (returns summary, not full objects)
    summary = client.recall(query="recent findings", limit=5)

    # Record event
    event_id = client.record_event(
        event_type="action",
        content="Ran test suite"
    )
"""

import logging
from typing import Any, Dict, Optional, List

logger = logging.getLogger(__name__)


class AthenaDirectClient:
    """Direct Python client for Athena memory API using filesystem API paradigm."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize direct Athena client with filesystem API adapter.

        Args:
            db_path: Optional path to database file (used by executor)
        """
        self.db_path = db_path
        self.adapter = None
        self._initialized = False

        # Lazy initialization of adapter on first use
        logger.info("Initialized AthenaDirectClient (filesystem API paradigm)")

    def _ensure_initialized(self) -> bool:
        """Initialize the FilesystemAPIAdapter on first use.

        Returns:
            True if successfully initialized, False otherwise
        """
        if self._initialized:
            return True

        try:
            # Import adapter - try absolute import first (hooks lib context)
            # Then fallback to relative import (package context)
            try:
                from filesystem_api_adapter import FilesystemAPIAdapter
            except ImportError:
                from .filesystem_api_adapter import FilesystemAPIAdapter

            logger.debug("Importing FilesystemAPIAdapter")
            self.adapter = FilesystemAPIAdapter()
            self._initialized = True
            logger.info("✅ FilesystemAPIAdapter initialized successfully")
            return True

        except ImportError as e:
            logger.error(f"❌ Failed to import FilesystemAPIAdapter: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to initialize FilesystemAPIAdapter: {e}")
            logger.debug(f"Exception details: {e}", exc_info=True)
            return False

    def health(self) -> Dict[str, Any]:
        """Check Athena health status.

        Uses filesystem API to execute health check operation.

        Returns:
            Health status summary (not full data)
        """
        if not self._ensure_initialized():
            return {"status": "error", "message": "FilesystemAPIAdapter not available"}

        try:
            # Execute health check operation locally
            result = self.adapter.execute_operation(
                "semantic",  # Most layers have health operations
                "health",
                {"db_path": self.db_path or "~/.athena/memory.db"}
            )

            # Extract summary from result
            if result.get("status") == "success":
                return {
                    "status": "healthy",
                    "message": "Athena memory system is operational",
                    "execution_method": "filesystem_api",
                    "summary": result.get("result", {})
                }
            else:
                return {
                    "status": "error",
                    "message": result.get("error", "Unknown error"),
                    "error_type": result.get("error_type")
                }

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

        Executes episodic layer's event recording operation locally.

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
            # Execute record_event operation in episodic layer
            result = self.adapter.execute_operation(
                "episodic",
                "record_event",
                {
                    "event_type": event_type,
                    "content": content,
                    "outcome": outcome or "unknown",
                    "context": context or {},
                    "db_path": self.db_path or "~/.athena/memory.db"
                }
            )

            if result.get("status") == "success":
                event_id = result.get("result", {}).get("event_id")
                logger.debug(f"Recorded event {event_type}: {event_id}")
                return event_id
            else:
                logger.warning(f"Failed to record event: {result.get('error')}")
                return None

        except Exception as e:
            logger.warning(f"Failed to record event: {e}")
            return None

    def recall(self, query: str, k: int = 5) -> Optional[Dict]:
        """Recall memories matching query.

        Executes semantic search operation locally, returns summary.
        Key: Returns counts, IDs, relevance scores - NOT full memory objects.

        Args:
            query: Search query
            k: Number of results to return (limit)

        Returns:
            Summary dictionary with results metadata (not full objects), None on error
        """
        if not self._ensure_initialized():
            return None

        try:
            # Execute recall operation in semantic layer
            result = self.adapter.execute_operation(
                "semantic",
                "recall",
                {
                    "query": query,
                    "limit": k,
                    "db_path": self.db_path or "~/.athena/memory.db"
                }
            )

            if result.get("status") == "success":
                logger.debug(f"Recalled memories for query: {query}")
                # Return summary (counts, IDs, metadata) - never full objects
                return result.get("result", {})
            else:
                logger.warning(f"Failed to recall memories: {result.get('error')}")
                return None

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

        Executes remember operation in semantic layer locally.

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
            # Execute remember operation in semantic layer
            result = self.adapter.execute_operation(
                "semantic",
                "remember",
                {
                    "content": content,
                    "memory_type": memory_type,
                    "context": context,
                    "tags": tags or [],
                    "db_path": self.db_path or "~/.athena/memory.db"
                }
            )

            if result.get("status") == "success":
                memory_id = result.get("result", {}).get("memory_id")
                logger.debug(f"Stored {memory_type} memory: {memory_id}")
                return memory_id
            else:
                logger.warning(f"Failed to store memory: {result.get('error')}")
                return None

        except Exception as e:
            logger.warning(f"Failed to store memory: {e}")
            return None

    def forget(self, memory_id: int) -> bool:
        """Delete a memory.

        Executes forget operation in semantic layer locally.

        Args:
            memory_id: ID of memory to delete

        Returns:
            True if successful, False otherwise
        """
        if not self._ensure_initialized():
            return False

        try:
            # Execute forget operation in semantic layer
            result = self.adapter.execute_operation(
                "semantic",
                "forget",
                {
                    "memory_id": memory_id,
                    "db_path": self.db_path or "~/.athena/memory.db"
                }
            )

            if result.get("status") == "success":
                logger.debug(f"Forgot memory: {memory_id}")
                return True
            else:
                logger.warning(f"Failed to forget memory: {result.get('error')}")
                return False

        except Exception as e:
            logger.warning(f"Failed to forget memory: {e}")
            return False

    def get_memory_quality_summary(self) -> Optional[Dict[str, Any]]:
        """Get memory quality metrics.

        Executes quality check operation in meta layer, returns summary metrics.

        Returns:
            Quality summary dictionary (metrics, not full data), None on error
        """
        if not self._ensure_initialized():
            return None

        try:
            # Execute quality check in meta layer
            result = self.adapter.execute_operation(
                "meta",
                "quality",
                {"db_path": self.db_path or "~/.athena/memory.db"}
            )

            if result.get("status") == "success":
                return result.get("result", {})
            else:
                logger.warning(f"Failed to get memory quality: {result.get('error')}")
                return None

        except Exception as e:
            logger.warning(f"Failed to get memory quality: {e}")
            return None

    def run_consolidation(
        self, strategy: str = "balanced", dry_run: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Run memory consolidation.

        Executes consolidation operation in consolidation layer locally.

        Args:
            strategy: Consolidation strategy (balanced, speed, quality, minimal)
            dry_run: If True, don't persist results

        Returns:
            Consolidation summary (counts, patterns extracted), None on error
        """
        if not self._ensure_initialized():
            return None

        try:
            # Execute consolidation in consolidation layer
            result = self.adapter.execute_operation(
                "consolidation",
                "consolidate",
                {
                    "strategy": strategy,
                    "dry_run": dry_run,
                    "db_path": self.db_path or "~/.athena/memory.db"
                }
            )

            if result.get("status") == "success":
                logger.info(f"Consolidation complete ({strategy} strategy)")
                return result.get("result", {})
            else:
                logger.warning(f"Failed to run consolidation: {result.get('error')}")
                return None

        except Exception as e:
            logger.warning(f"Failed to run consolidation: {e}")
            return None

    def check_cognitive_load(self) -> Optional[Dict[str, Any]]:
        """Check current cognitive load.

        Executes cognitive load check in meta layer.

        Returns:
            Cognitive load metrics summary, None on error
        """
        if not self._ensure_initialized():
            return None

        try:
            # Execute cognitive load check in meta layer
            result = self.adapter.execute_operation(
                "meta",
                "cognitive_load",
                {"db_path": self.db_path or "~/.athena/memory.db"}
            )

            if result.get("status") == "success":
                return result.get("result", {})
            else:
                logger.warning(f"Failed to check cognitive load: {result.get('error')}")
                return None

        except Exception as e:
            logger.warning(f"Failed to check cognitive load: {e}")
            return None

    def get_memory_health(self) -> Optional[Dict[str, Any]]:
        """Get overall memory system health.

        Executes health check across all layers via cross-layer operation.

        Returns:
            Health metrics summary, None on error
        """
        if not self._ensure_initialized():
            return None

        try:
            # Execute cross-layer health check
            result = self.adapter.execute_cross_layer_operation(
                "health_check",
                {"db_path": self.db_path or "~/.athena/memory.db"}
            )

            if result.get("status") == "success":
                return result.get("result", {})
            else:
                logger.warning(f"Failed to get memory health: {result.get('error')}")
                return None

        except Exception as e:
            logger.warning(f"Failed to get memory health: {e}")
            return None

    def close(self):
        """Clean up resources."""
        # Filesystem API doesn't require cleanup
        logger.debug("AthenaDirectClient closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, *args):
        """Context manager exit."""
        self.close()
