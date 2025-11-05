"""Rate limiting for research sources to prevent overload."""

import logging
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""

    pass


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting per source."""

    source: str
    requests_per_minute: int = 10
    burst_size: int = 5  # Allow burst of 5 requests

    @property
    def min_interval_seconds(self) -> float:
        """Minimum interval between requests in seconds."""
        return 60.0 / self.requests_per_minute


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""

    source: str
    capacity: float
    refill_rate: float  # tokens per second
    last_refill: float
    tokens: float = 0.0

    def __post_init__(self):
        """Initialize with full capacity."""
        self.tokens = self.capacity
        self.last_refill = time.time()

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(
            self.capacity,
            self.tokens + (elapsed * self.refill_rate),
        )
        self.last_refill = now

    def try_consume(self, tokens: float = 1.0) -> bool:
        """Try to consume tokens.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if consumed, False if rate limited
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def get_wait_time(self, tokens: float = 1.0) -> float:
        """Get time to wait before next request can be made.

        Args:
            tokens: Number of tokens needed

        Returns:
            Wait time in seconds
        """
        self._refill()

        if self.tokens >= tokens:
            return 0.0

        needed = tokens - self.tokens
        return needed / self.refill_rate


class RateLimiter:
    """Rate limiter for research sources using token bucket algorithm."""

    # Default rate limiting configs per source
    DEFAULT_CONFIGS = {
        "arXiv": RateLimitConfig("arXiv", requests_per_minute=30, burst_size=5),
        "GitHub": RateLimitConfig("GitHub", requests_per_minute=60, burst_size=10),
        "Anthropic Docs": RateLimitConfig("Anthropic Docs", requests_per_minute=60, burst_size=10),
        "Papers with Code": RateLimitConfig("Papers with Code", requests_per_minute=30, burst_size=5),
        "HackerNews": RateLimitConfig("HackerNews", requests_per_minute=30, burst_size=5),
        "Medium": RateLimitConfig("Medium", requests_per_minute=20, burst_size=3),
        "Tech Blogs": RateLimitConfig("Tech Blogs", requests_per_minute=30, burst_size=5),
        "X/Twitter": RateLimitConfig("X/Twitter", requests_per_minute=15, burst_size=3),
    }

    def __init__(self):
        """Initialize rate limiter with default configs."""
        self.buckets: dict[str, TokenBucket] = {}
        self.configs = self.DEFAULT_CONFIGS.copy()
        self.metrics = {
            "total_requests": 0,
            "rate_limited": 0,
            "allowed": 0,
        }

    def set_config(self, source: str, config: RateLimitConfig):
        """Set rate limiting config for a source.

        Args:
            source: Source name
            config: Rate limit configuration
        """
        self.configs[source] = config
        # Reset bucket if exists
        if source in self.buckets:
            del self.buckets[source]
        logger.info(f"Updated rate limit for {source}: {config.requests_per_minute} req/min")

    def _get_bucket(self, source: str) -> TokenBucket:
        """Get or create token bucket for source.

        Args:
            source: Source name

        Returns:
            Token bucket
        """
        if source not in self.buckets:
            config = self.configs.get(
                source,
                RateLimitConfig(source, requests_per_minute=10, burst_size=2),
            )
            self.buckets[source] = TokenBucket(
                source=source,
                capacity=config.burst_size,
                refill_rate=config.requests_per_minute / 60.0,
                last_refill=time.time(),
            )

        return self.buckets[source]

    def allow_request(self, source: str) -> bool:
        """Check if request is allowed for source.

        Args:
            source: Source name

        Returns:
            True if allowed, False if rate limited
        """
        self.metrics["total_requests"] += 1
        bucket = self._get_bucket(source)

        if bucket.try_consume():
            self.metrics["allowed"] += 1
            return True

        self.metrics["rate_limited"] += 1
        return False

    def wait_if_needed(self, source: str) -> float:
        """Wait if needed to respect rate limits.

        Args:
            source: Source name

        Returns:
            Time waited in seconds
        """
        bucket = self._get_bucket(source)
        wait_time = bucket.get_wait_time()

        if wait_time > 0:
            logger.debug(f"Rate limit: waiting {wait_time:.2f}s for {source}")
            time.sleep(wait_time)

        return wait_time

    def get_stats(self) -> dict:
        """Get rate limiting statistics.

        Returns:
            Statistics dict
        """
        total = self.metrics["total_requests"]
        rate_limited_pct = (
            (self.metrics["rate_limited"] / total * 100) if total > 0 else 0
        )

        return {
            "total_requests": total,
            "allowed": self.metrics["allowed"],
            "rate_limited": self.metrics["rate_limited"],
            "rate_limited_percentage": rate_limited_pct,
            "sources_configured": len(self.configs),
            "active_buckets": len(self.buckets),
        }
