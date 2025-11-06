"""Cache manager for Redis-backed caching."""

import json
import logging
from typing import Any, Optional
from datetime import timedelta

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """Manage caching with Redis fallback to in-memory cache."""

    def __init__(self, redis_url: str = settings.REDIS_URL, ttl: int = settings.CACHE_TTL_SECONDS):
        """Initialize cache manager.

        Args:
            redis_url: Redis connection URL
            ttl: Time to live for cache entries in seconds
        """
        self.ttl = ttl
        self.use_redis = REDIS_AVAILABLE and settings.CACHE_ENABLED
        self.redis: Optional[redis.Redis] = None
        self.memory_cache: dict = {}

        if self.use_redis:
            try:
                self.redis = redis.from_url(redis_url, decode_responses=True)
                self.redis.ping()
                logger.info("Connected to Redis cache")
            except Exception as e:
                logger.warning(f"Redis unavailable, using in-memory cache: {e}")
                self.use_redis = False

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        try:
            if self.use_redis and self.redis:
                value = self.redis.get(key)
                if value:
                    return json.loads(value)
            else:
                return self.memory_cache.get(key)
        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {e}")
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override in seconds

        Returns:
            True if successful
        """
        ttl = ttl or self.ttl
        try:
            serialized = json.dumps(value, default=str)
            if self.use_redis and self.redis:
                self.redis.setex(key, ttl, serialized)
            else:
                self.memory_cache[key] = value
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if successful
        """
        try:
            if self.use_redis and self.redis:
                self.redis.delete(key)
            else:
                self.memory_cache.pop(key, None)
            return True
        except Exception as e:
            logger.warning(f"Cache delete failed for key {key}: {e}")
            return False

    def clear(self) -> bool:
        """Clear all cache.

        Returns:
            True if successful
        """
        try:
            if self.use_redis and self.redis:
                self.redis.flushdb()
            else:
                self.memory_cache.clear()
            return True
        except Exception as e:
            logger.warning(f"Cache clear failed: {e}")
            return False

    def get_or_compute(self, key: str, compute_fn, ttl: Optional[int] = None) -> Any:
        """Get from cache or compute and cache.

        Args:
            key: Cache key
            compute_fn: Function to compute value if not cached
            ttl: Optional TTL override

        Returns:
            Cached or computed value
        """
        # Try to get from cache
        cached = self.get(key)
        if cached is not None:
            return cached

        # Compute and cache
        try:
            value = compute_fn()
            self.set(key, value, ttl)
            return value
        except Exception as e:
            logger.error(f"Computation failed for cache key {key}: {e}")
            raise

    def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        if self.use_redis and self.redis:
            return bool(self.redis.exists(key))
        else:
            return key in self.memory_cache

    def keys(self, pattern: str = "*") -> list:
        """Get all keys matching pattern.

        Args:
            pattern: Key pattern

        Returns:
            List of matching keys
        """
        try:
            if self.use_redis and self.redis:
                return self.redis.keys(pattern)
            else:
                if pattern == "*":
                    return list(self.memory_cache.keys())
                # Simple pattern matching for in-memory cache
                import fnmatch
                return [k for k in self.memory_cache.keys() if fnmatch.fnmatch(k, pattern)]
        except Exception as e:
            logger.warning(f"Key listing failed: {e}")
            return []

    @staticmethod
    def cache_key(*parts: str) -> str:
        """Generate cache key from parts.

        Args:
            *parts: Key parts

        Returns:
            Formatted cache key
        """
        return ":".join(parts)
