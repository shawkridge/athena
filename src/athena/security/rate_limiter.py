"""Rate limiting for Athena MCP operations (Phase 3).

Per-operation rate limiting to prevent abuse:
- Recall: 100 req/minute per project
- Remember: 50 req/minute per project
- Consolidate: 10 req/minute per project
- Create task: 50 req/minute per project
"""

import time
import logging
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque
from threading import Lock

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rate: int, period: int = 60):
        """Initialize rate limiter.

        Args:
            rate: Number of requests allowed
            period: Time period in seconds (default: 60 = 1 minute)
        """
        self.rate = rate
        self.period = period
        self.tokens = rate
        self.last_update = time.time()
        self.lock = Lock()

    def is_allowed(self) -> bool:
        """Check if request is allowed.

        Returns:
            True if request allowed, False if rate limited
        """
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update

            # Add tokens based on elapsed time
            self.tokens = min(
                self.rate,
                self.tokens + (elapsed * self.rate / self.period)
            )
            self.last_update = now

            if self.tokens >= 1:
                self.tokens -= 1
                return True

            return False

    def get_retry_after(self) -> float:
        """Get seconds to wait before retry.

        Returns:
            Seconds until next token available
        """
        if self.tokens >= 1:
            return 0

        with self.lock:
            tokens_needed = 1 - self.tokens
            return (tokens_needed * self.period) / self.rate


class OperationRateLimiter:
    """Rate limiter for MCP operations by project."""

    # Default rate limits (requests per minute)
    DEFAULT_LIMITS = {
        'recall': 100,
        'remember': 50,
        'forget': 30,
        'consolidate': 10,
        'create_task': 50,
        'create_entity': 100,
        'search_graph': 200,
        'smart_retrieve': 100,
        'record_event': 100,
        'list_tasks': 200,
    }

    def __init__(self, limits: Optional[Dict[str, int]] = None):
        """Initialize operation rate limiter.

        Args:
            limits: Custom rate limits by operation
        """
        self.limits = {**self.DEFAULT_LIMITS}
        if limits:
            self.limits.update(limits)

        # Per-project limiters: {project_id: {operation: RateLimiter}}
        self.limiters: Dict[str, Dict[str, RateLimiter]] = defaultdict(dict)
        self.lock = Lock()

    def is_allowed(self, project_id: str, operation: str) -> Tuple[bool, Optional[float]]:
        """Check if operation is allowed.

        Args:
            project_id: Project identifier
            operation: Operation name

        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        if operation not in self.limits:
            # Unknown operation, allow by default
            return True, None

        with self.lock:
            if project_id not in self.limiters:
                self.limiters[project_id] = {}

            if operation not in self.limiters[project_id]:
                rate = self.limits[operation]
                self.limiters[project_id][operation] = RateLimiter(rate)

            limiter = self.limiters[project_id][operation]

        allowed = limiter.is_allowed()

        if not allowed:
            retry_after = limiter.get_retry_after()
            return False, retry_after

        return True, None

    def set_limit(self, operation: str, rate: int):
        """Set rate limit for operation.

        Args:
            operation: Operation name
            rate: Requests per minute
        """
        self.limits[operation] = rate
        logger.info(f"Rate limit updated: {operation} = {rate} req/min")

    def get_limit(self, operation: str) -> Optional[int]:
        """Get rate limit for operation.

        Args:
            operation: Operation name

        Returns:
            Requests per minute or None if not limited
        """
        return self.limits.get(operation)

    def reset_project(self, project_id: str):
        """Reset all rate limiters for project.

        Args:
            project_id: Project identifier
        """
        with self.lock:
            if project_id in self.limiters:
                del self.limiters[project_id]
                logger.info(f"Rate limiters reset for project: {project_id}")


class RateLimitError(Exception):
    """Rate limit exceeded error."""

    def __init__(self, message: str, retry_after: float):
        """Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to retry after
        """
        super().__init__(message)
        self.retry_after = retry_after


# Global rate limiter instance
_rate_limiter: Optional[OperationRateLimiter] = None


def get_rate_limiter() -> OperationRateLimiter:
    """Get global rate limiter.

    Returns:
        OperationRateLimiter instance
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = OperationRateLimiter()
    return _rate_limiter


def initialize_rate_limiter(limits: Optional[Dict[str, int]] = None) -> OperationRateLimiter:
    """Initialize global rate limiter.

    Args:
        limits: Custom rate limits

    Returns:
        OperationRateLimiter instance
    """
    global _rate_limiter
    _rate_limiter = OperationRateLimiter(limits)
    return _rate_limiter


def check_rate_limit(project_id: str, operation: str) -> Optional[float]:
    """Check if operation is rate limited.

    Args:
        project_id: Project identifier
        operation: Operation name

    Returns:
        Retry-after seconds if limited, None if allowed

    Raises:
        RateLimitError: If rate limited
    """
    limiter = get_rate_limiter()
    allowed, retry_after = limiter.is_allowed(project_id, operation)

    if not allowed:
        msg = f"Rate limit exceeded for {operation} in project {project_id}"
        raise RateLimitError(msg, retry_after or 1.0)

    return None
