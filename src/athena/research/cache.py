"""Caching layer for research queries to improve performance."""

import hashlib
import logging
from typing import Optional, List
from dataclasses import dataclass, field
import time

logger = logging.getLogger(__name__)


@dataclass
class CachedResult:
    """Cached research result."""

    task_id: int
    topic: str
    findings: list = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    ttl_seconds: int = 3600  # 1 hour default
    hit_count: int = 0

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        age = time.time() - self.timestamp
        return age > self.ttl_seconds

    def record_hit(self):
        """Record a cache hit."""
        self.hit_count += 1


class ResearchQueryCache:
    """In-memory cache for research query results."""

    def __init__(self, max_entries: int = 100, default_ttl_seconds: int = 3600):
        """Initialize research cache.

        Args:
            max_entries: Maximum cache entries before eviction
            default_ttl_seconds: Default time-to-live for cache entries
        """
        self.max_entries = max_entries
        self.default_ttl_seconds = default_ttl_seconds
        self.cache: dict[str, CachedResult] = {}
        self.metrics = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
        }

    def _generate_key(self, topic: str) -> str:
        """Generate cache key from topic.

        Args:
            topic: Research topic

        Returns:
            Cache key
        """
        # Normalize topic for consistent caching
        normalized = topic.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()

    def get(self, topic: str) -> Optional[List[dict]]:
        """Get cached research findings.

        Args:
            topic: Research topic

        Returns:
            Cached findings or None if not found/expired
        """
        key = self._generate_key(topic)

        if key not in self.cache:
            self.metrics["misses"] += 1
            return None

        cached = self.cache[key]

        # Check expiration
        if cached.is_expired():
            del self.cache[key]
            self.metrics["expirations"] += 1
            logger.debug(f"Cache expired for topic: {topic}")
            return None

        # Record hit
        cached.record_hit()
        self.metrics["hits"] += 1
        logger.debug(f"Cache hit for topic: {topic} (hit #{cached.hit_count})")
        return cached.findings

    def set(self, topic: str, findings: List[dict], ttl_seconds: Optional[int] = None):
        """Store research findings in cache.

        Args:
            topic: Research topic
            findings: Research findings to cache
            ttl_seconds: Time-to-live for this entry (uses default if not specified)
        """
        key = self._generate_key(topic)
        ttl = ttl_seconds or self.default_ttl_seconds

        # Evict least recently used if at capacity
        if len(self.cache) >= self.max_entries and key not in self.cache:
            self._evict_lru()

        self.cache[key] = CachedResult(
            task_id=0,  # Will be set by executor
            topic=topic,
            findings=findings,
            timestamp=time.time(),
            ttl_seconds=ttl,
        )
        logger.debug(f"Cache set for topic: {topic} ({len(findings)} findings, TTL: {ttl}s)")

    def _evict_lru(self):
        """Evict least recently used entry."""
        if not self.cache:
            return

        # Find entry with lowest hit count and oldest timestamp
        lru_key = min(
            self.cache.keys(),
            key=lambda k: (self.cache[k].hit_count, self.cache[k].timestamp),
        )

        evicted_topic = self.cache[lru_key].topic
        del self.cache[lru_key]
        self.metrics["evictions"] += 1
        logger.debug(f"Evicted LRU cache entry: {evicted_topic}")

    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        logger.info("Cache cleared")

    def get_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Cache stats dict
        """
        total_requests = self.metrics["hits"] + self.metrics["misses"]
        hit_rate = self.metrics["hits"] / total_requests if total_requests > 0 else 0.0

        return {
            "size": len(self.cache),
            "max_entries": self.max_entries,
            "hits": self.metrics["hits"],
            "misses": self.metrics["misses"],
            "hit_rate": hit_rate,
            "evictions": self.metrics["evictions"],
            "expirations": self.metrics["expirations"],
            "total_requests": total_requests,
        }
