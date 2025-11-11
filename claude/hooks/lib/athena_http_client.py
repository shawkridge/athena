"""Direct HTTP client for Athena REST API.

This client communicates directly with the Athena HTTP server running in Docker
at http://localhost:8000 (or ATHENA_HTTP_URL environment variable).

It does NOT depend on the athena.client library (which may not be installed locally).
Instead, it makes direct HTTP requests to the REST endpoints.
"""

import logging
import os
import sys
from typing import Any, Dict, Optional
import json

logger = logging.getLogger(__name__)

# Try to import requests, fallback to urllib if not available
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    import urllib.request
    import urllib.error


class AthenaHTTPClient:
    """Direct HTTP client for Athena REST API."""

    def __init__(self, url: Optional[str] = None, timeout: float = 5.0, retries: int = 1):
        """Initialize HTTP client.

        Args:
            url: Athena HTTP service URL (defaults to env var or localhost:8000)
            timeout: Request timeout in seconds
            retries: Number of retries for failed requests
        """
        self.url = (url or os.environ.get("ATHENA_HTTP_URL", "http://localhost:8000")).rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self.session = None

        if REQUESTS_AVAILABLE:
            self.session = requests.Session()
            self.session.timeout = timeout
            logger.info(f"Initialized Athena HTTP client with requests library: {self.url}")
        else:
            logger.info(f"Initialized Athena HTTP client with urllib: {self.url}")

    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None) -> Optional[Dict]:
        """Make HTTP request to Athena API.

        Args:
            method: HTTP method (GET, POST, etc)
            endpoint: API endpoint (e.g., "/api/memory/recall")
            params: Query parameters
            json_data: JSON body data

        Returns:
            Response data as dict, or None if failed
        """
        url = f"{self.url}{endpoint}"

        for attempt in range(self.retries):
            try:
                if REQUESTS_AVAILABLE:
                    if method == "GET":
                        response = self.session.get(url, params=params, timeout=self.timeout)
                    elif method == "POST":
                        response = self.session.post(url, params=params, json=json_data, timeout=self.timeout)
                    else:
                        raise ValueError(f"Unsupported method: {method}")

                    if response.status_code >= 200 and response.status_code < 300:
                        return response.json()
                    else:
                        logger.warning(f"HTTP {response.status_code}: {response.text}")
                        return None
                else:
                    # Fallback to urllib
                    full_url = url
                    if params:
                        from urllib.parse import urlencode
                        full_url += "?" + urlencode(params)

                    if method == "GET":
                        req = urllib.request.Request(full_url)
                        with urllib.request.urlopen(req, timeout=self.timeout) as response:
                            return json.loads(response.read().decode())
                    elif method == "POST":
                        req = urllib.request.Request(
                            full_url,
                            data=json.dumps(json_data).encode(),
                            headers={"Content-Type": "application/json"}
                        )
                        with urllib.request.urlopen(req, timeout=self.timeout) as response:
                            return json.loads(response.read().decode())

            except Exception as e:
                logger.debug(f"Request failed (attempt {attempt + 1}/{self.retries}): {e}")
                if attempt == self.retries - 1:
                    logger.error(f"Failed to call {method} {endpoint}: {e}")
                    return None

    def health(self) -> Dict[str, Any]:
        """Check service health.

        Returns:
            Health status dict with status, version, uptime, etc.
        """
        result = self._make_request("GET", "/health")
        return result or {}

    def record_event(
        self,
        content: str,
        event_type: str = "general",
        outcome: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Record an episodic event by storing as a memory.

        Args:
            content: Event description
            event_type: Type of event (general, action, decision, error, etc)
            outcome: Event outcome (success, failure, partial)
            context: Additional context dict

        Returns:
            True if successful
        """
        # Store event as a memory using /api/memory/remember endpoint
        memory_content = f"[{event_type.upper()}] {content}"
        if outcome:
            memory_content += f" (outcome: {outcome})"

        tags = [event_type]
        if outcome:
            tags.append(outcome)
        if context:
            tags.append("contextual")

        data = {
            "content": memory_content,
            "memory_type": "event",
            "tags": tags,
            "importance": 0.7,
        }

        result = self._make_request("POST", "/api/memory/remember", json_data=data)
        return result is not None

    def recall(self, query: str, k: int = 5) -> Optional[list]:
        """Recall memories matching query.

        Args:
            query: Search query
            k: Number of results to return

        Returns:
            List of matching memories or None if failed
        """
        # Use POST with query as a form parameter since /api/memory/recall is POST
        result = self._make_request("POST", "/api/memory/recall", params={"query": query, "k": k})
        if result and "data" in result:
            return result["data"]
        return result

    def remember(self, content: str, memory_type: str = "knowledge", tags: Optional[list] = None, importance: Optional[float] = None) -> bool:
        """Store new memory.

        Args:
            content: Memory content
            memory_type: Type of memory
            tags: Optional tags
            importance: Optional importance score (0-1)

        Returns:
            True if successful
        """
        data = {
            "content": content,
            "memory_type": memory_type,
        }
        if tags:
            data["tags"] = tags
        if importance is not None:
            data["importance"] = importance

        result = self._make_request("POST", "/api/memory/remember", json_data=data)
        return result is not None

    def forget(self, memory_id: int) -> bool:
        """Forget (delete) a memory.

        Args:
            memory_id: ID of memory to delete

        Returns:
            True if successful
        """
        result = self._make_request("POST", "/api/memory/forget", json_data={"memory_id": memory_id})
        return result is not None

    def get_memory_quality_summary(self) -> Optional[Dict[str, Any]]:
        """Get memory system health/quality summary.

        Returns:
            Quality summary dict or None if failed
        """
        result = self._make_request("GET", "/api/memory/health")
        if result and "data" in result:
            return result["data"]
        return result

    def run_consolidation(self, strategy: str = "balanced", dry_run: bool = False) -> Optional[Dict[str, Any]]:
        """Run consolidation with specified strategy.

        Args:
            strategy: Consolidation strategy (balanced, speed, quality, minimal)
            dry_run: If True, preview without executing

        Returns:
            Consolidation result or None if failed
        """
        result = self._make_request(
            "POST",
            "/api/consolidation/run",
            params={"strategy": strategy, "dry_run": dry_run}
        )
        if result and "data" in result:
            return result["data"]
        return result

    def check_cognitive_load(self) -> Optional[Dict[str, Any]]:
        """Check current cognitive load (7±2 model).

        Returns:
            Cognitive load info or None if failed
        """
        result = self._make_request("GET", "/api/memory/health")  # Using health as proxy
        if result and "data" in result:
            return {"status": result.get("status"), "info": result.get("data")}
        return None

    def close(self):
        """Close the client connection."""
        if self.session:
            self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class AthenaHTTPClientWrapper:
    """Wrapper for Athena HTTP client with graceful fallback."""

    def __init__(self, url: Optional[str] = None, timeout: float = 5.0):
        """Initialize HTTP client.

        Args:
            url: Athena HTTP service URL (defaults to env var or localhost:8000)
            timeout: Request timeout in seconds
        """
        self.url = url or os.environ.get("ATHENA_HTTP_URL", "http://localhost:8000")
        self.timeout = timeout
        self.client = None
        self._fallback_mode = False

        try:
            self.client = AthenaHTTPClient(url=self.url, timeout=timeout, retries=1)
            # Verify connection with health check
            health = self.client.health()
            if health.get("status") == "healthy":
                logger.info(f"✓ Connected to Athena HTTP at {self.url}")
            else:
                logger.warning(f"Athena at {self.url} is not healthy, using fallback mode")
                self._fallback_mode = True
        except Exception as e:
            logger.warning(f"Failed to initialize Athena HTTP client: {e}, using fallback mode")
            self._fallback_mode = True

    def record_event(
        self,
        content: str,
        event_type: str = "general",
        outcome: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Record an episodic event."""
        if self._fallback_mode or not self.client:
            logger.debug(f"Recording event in fallback mode: {content}")
            return False

        return self.client.record_event(content, event_type, outcome, context)

    def consolidate(self, strategy: str = "balanced", dry_run: bool = False) -> bool:
        """Run consolidation."""
        if self._fallback_mode or not self.client:
            logger.debug(f"Running consolidation in fallback mode")
            return False

        return self.client.run_consolidation(strategy, dry_run) is not None

    def get_cognitive_load(self) -> Optional[Dict[str, Any]]:
        """Get current cognitive load."""
        if self._fallback_mode or not self.client:
            logger.debug("Getting cognitive load in fallback mode")
            return None

        return self.client.check_cognitive_load()

    def get_memory_health(self) -> Optional[Dict[str, Any]]:
        """Get memory system health."""
        if self._fallback_mode or not self.client:
            logger.debug("Getting memory health in fallback mode")
            return None

        return self.client.get_memory_quality_summary()

    def recall_memories(self, query: str, k: int = 5) -> Optional[list]:
        """Recall memories matching query."""
        if self._fallback_mode or not self.client:
            logger.debug(f"Recalling memories in fallback mode: {query}")
            return None

        return self.client.recall(query, k)

    def health_check(self) -> bool:
        """Check if Athena HTTP service is healthy."""
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
    event_type: str = "general",
    outcome: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> bool:
    """Record an event using the global client."""
    return get_client().record_event(content, event_type, outcome, context)


def consolidate(strategy: str = "balanced", dry_run: bool = False) -> bool:
    """Run consolidation using the global client."""
    return get_client().consolidate(strategy, dry_run)


def health_check() -> bool:
    """Check Athena health using the global client."""
    return get_client().health_check()


def get_cognitive_load() -> Optional[Dict[str, Any]]:
    """Get cognitive load using the global client."""
    return get_client().get_cognitive_load()


def recall_memories(query: str, k: int = 5) -> Optional[list]:
    """Recall memories using the global client."""
    return get_client().recall_memories(query, k)


# Alias the old class name for backward compatibility
AthenaHTTPClientError = Exception
