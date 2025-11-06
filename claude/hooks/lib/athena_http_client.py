"""HTTP client for Athena integration in hooks."""

import logging
import os
from typing import Any, Dict, Optional
import sys

logger = logging.getLogger(__name__)

# Try to import the Athena HTTP client
try:
    from athena.client import AthenaHTTPClient, AthenaHTTPClientError
    ATHENA_AVAILABLE = True
except ImportError:
    ATHENA_AVAILABLE = False
    logger.warning("Athena HTTP client not available, will use fallback mode")


class AthenaHTTPClientWrapper:
    """Wrapper for Athena HTTP client used by hooks.

    Provides graceful fallback if Athena HTTP service is unavailable.
    """

    def __init__(self, url: Optional[str] = None, timeout: float = 5.0):
        """Initialize HTTP client.

        Args:
            url: Athena HTTP service URL (defaults to env var or localhost:3000)
            timeout: Request timeout in seconds (short for hooks)
        """
        self.url = url or os.environ.get("ATHENA_HTTP_URL", "http://localhost:3000")
        self.timeout = timeout
        self.client = None
        self._fallback_mode = False

        if ATHENA_AVAILABLE:
            try:
                self.client = AthenaHTTPClient(url=self.url, timeout=timeout, retries=1)
                logger.info(f"Connected to Athena HTTP at {self.url}")
            except Exception as e:
                logger.warning(f"Failed to initialize Athena HTTP client: {e}, using fallback mode")
                self._fallback_mode = True
        else:
            logger.warning("Athena package not available, using fallback mode")
            self._fallback_mode = True

    def record_event(
        self,
        content: str,
        event_type: str,
        outcome: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Record an episodic event.

        Args:
            content: Event description
            event_type: Type of event
            outcome: Event outcome (success/failure/partial)
            context: Additional context

        Returns:
            True if successful, False if fallback used
        """
        if self._fallback_mode or not self.client:
            logger.debug(f"Recording event in fallback mode: {content}")
            return False

        try:
            self.client.record_event(
                content=content,
                event_type=event_type,
                outcome=outcome,
                context=context,
            )
            logger.debug(f"Recorded event: {event_type}")
            return True
        except Exception as e:
            logger.error(f"Failed to record event: {e}, using fallback")
            return False

    def consolidate(self, strategy: str = "balanced", dry_run: bool = False) -> bool:
        """Run consolidation.

        Args:
            strategy: Consolidation strategy
            dry_run: Preview consolidation without executing

        Returns:
            True if successful, False if fallback used
        """
        if self._fallback_mode or not self.client:
            logger.debug(f"Running consolidation in fallback mode")
            return False

        try:
            self.client.run_consolidation(strategy=strategy, dry_run=dry_run)
            logger.debug("Consolidation completed")
            return True
        except Exception as e:
            logger.error(f"Failed to consolidate: {e}, using fallback")
            return False

    def get_cognitive_load(self) -> Optional[Dict[str, Any]]:
        """Get current cognitive load.

        Returns:
            Cognitive load info or None if fallback used
        """
        if self._fallback_mode or not self.client:
            logger.debug("Getting cognitive load in fallback mode")
            return None

        try:
            return self.client.check_cognitive_load()
        except Exception as e:
            logger.error(f"Failed to get cognitive load: {e}")
            return None

    def get_memory_health(self) -> Optional[Dict[str, Any]]:
        """Get memory system health.

        Returns:
            Memory health info or None if fallback used
        """
        if self._fallback_mode or not self.client:
            logger.debug("Getting memory health in fallback mode")
            return None

        try:
            return self.client.get_memory_quality_summary()
        except Exception as e:
            logger.error(f"Failed to get memory health: {e}")
            return None

    def recall_memories(self, query: str, k: int = 5) -> Optional[list]:
        """Recall memories matching query.

        Args:
            query: Search query
            k: Number of results

        Returns:
            List of memories or None if fallback used
        """
        if self._fallback_mode or not self.client:
            logger.debug(f"Recalling memories in fallback mode: {query}")
            return None

        try:
            return self.client.recall(query=query, k=k)
        except Exception as e:
            logger.error(f"Failed to recall memories: {e}")
            return None

    def health_check(self) -> bool:
        """Check if Athena HTTP service is healthy.

        Returns:
            True if healthy, False otherwise
        """
        if not self.client:
            return False

        try:
            health = self.client.health()
            return health.get("status") == "healthy"
        except Exception as e:
            logger.warning(f"Athena health check failed: {e}")
            return False

    def close(self):
        """Close the HTTP client."""
        if self.client:
            self.client.close()


# Global client instance for hooks
_client = None


def get_client() -> AthenaHTTPClientWrapper:
    """Get or create the global Athena HTTP client.

    Returns:
        AthenaHTTPClientWrapper instance
    """
    global _client
    if _client is None:
        _client = AthenaHTTPClientWrapper()
    return _client


def record_event(
    content: str,
    event_type: str,
    outcome: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> bool:
    """Record an event using the global client.

    Args:
        content: Event description
        event_type: Type of event
        outcome: Event outcome
        context: Additional context

    Returns:
        True if successful, False otherwise
    """
    return get_client().record_event(content, event_type, outcome, context)


def consolidate(strategy: str = "balanced", dry_run: bool = False) -> bool:
    """Run consolidation using the global client.

    Args:
        strategy: Consolidation strategy
        dry_run: Preview consolidation

    Returns:
        True if successful, False otherwise
    """
    return get_client().consolidate(strategy, dry_run)


def health_check() -> bool:
    """Check Athena health using the global client.

    Returns:
        True if healthy, False otherwise
    """
    return get_client().health_check()


def get_cognitive_load() -> Optional[Dict[str, Any]]:
    """Get cognitive load using the global client.

    Returns:
        Cognitive load info or None
    """
    return get_client().get_cognitive_load()


def recall_memories(query: str, k: int = 5) -> Optional[list]:
    """Recall memories using the global client.

    Args:
        query: Search query
        k: Number of results

    Returns:
        List of memories or None
    """
    return get_client().recall_memories(query, k)
