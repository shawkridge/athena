"""In-memory caching layer for high performance queries."""

import hashlib
from collections import OrderedDict
from datetime import datetime
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")


class CacheEntry:
    """Single cache entry with TTL and metadata."""

    def __init__(self, value: Any, ttl_seconds: int = 3600):
        """Initialize cache entry.

        Args:
            value: Cached value
            ttl_seconds: Time to live in seconds (default: 1 hour)
        """
        self.value = value
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        self.ttl_seconds = ttl_seconds
        self.access_count = 0

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        age = (datetime.now() - self.created_at).total_seconds()
        return age > self.ttl_seconds

    def mark_accessed(self):
        """Update access timestamp and count."""
        self.last_accessed = datetime.now()
        self.access_count += 1

    def get_value(self) -> Any:
        """Get value and update access info."""
        if self.is_expired():
            return None
        self.mark_accessed()
        return self.value


class LRUCache:
    """Least Recently Used cache with TTL support."""

    def __init__(self, max_size: int = 1000, default_ttl_seconds: int = 3600):
        """Initialize LRU cache.

        Args:
            max_size: Maximum number of entries (default: 1000)
            default_ttl_seconds: Default TTL for entries (default: 1 hour)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl_seconds
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """Set cache entry.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Custom TTL (uses default if not specified)
        """
        ttl = ttl_seconds or self.default_ttl

        # Remove if exists (to reorder)
        if key in self.cache:
            del self.cache[key]

        # Add new entry
        self.cache[key] = CacheEntry(value, ttl)

        # Evict if over capacity
        if len(self.cache) > self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

    def get(self, key: str) -> Optional[Any]:
        """Get cache entry.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key not in self.cache:
            self.misses += 1
            return None

        entry = self.cache[key]

        # Check expiration
        if entry.is_expired():
            del self.cache[key]
            self.misses += 1
            return None

        # Move to end (most recently used)
        del self.cache[key]
        self.cache[key] = entry

        # Track hit
        self.hits += 1
        entry.mark_accessed()

        return entry.value

    def remove(self, key: str):
        """Remove entry from cache.

        Args:
            key: Cache key
        """
        if key in self.cache:
            del self.cache[key]

    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def get_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "total_requests": total_requests,
        }

    def warmup(self, data: dict[str, Any], ttl_seconds: Optional[int] = None):
        """Pre-load cache with data.

        Args:
            data: Dictionary of key-value pairs to cache
            ttl_seconds: Custom TTL for warmup data
        """
        for key, value in data.items():
            self.set(key, value, ttl_seconds)


class QueryCache:
    """Cache for database query results."""

    def __init__(self, max_queries: int = 1000):
        """Initialize query cache.

        Args:
            max_queries: Maximum queries to cache
        """
        self.cache = LRUCache(max_size=max_queries)

    @staticmethod
    def _hash_query(query: str, params: tuple = ()) -> str:
        """Generate hash for query + parameters.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Hash string
        """
        combined = f"{query}:{tuple(params)}"
        return hashlib.md5(combined.encode()).hexdigest()

    def get(self, query: str, params: tuple = ()) -> Optional[Any]:
        """Get cached query result.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Cached result or None
        """
        key = self._hash_query(query, params)
        return self.cache.get(key)

    def set(self, query: str, params: tuple, result: Any, ttl_seconds: int = 300):
        """Cache query result.

        Args:
            query: SQL query
            params: Query parameters
            result: Query result to cache
            ttl_seconds: Cache duration (default: 5 minutes)
        """
        key = self._hash_query(query, params)
        self.cache.set(key, result, ttl_seconds)

    def invalidate_pattern(self, table_pattern: str):
        """Invalidate cache entries for table.

        Args:
            table_pattern: Table name pattern (e.g., 'code_entities')
        """
        # Remove entries mentioning this table
        keys_to_remove = [
            key for key in self.cache.cache.keys() if table_pattern.lower() in key.lower()
        ]
        for key in keys_to_remove:
            self.cache.remove(key)

    def clear(self):
        """Clear all query cache."""
        self.cache.clear()

    def get_stats(self) -> dict:
        """Get cache statistics."""
        return self.cache.get_stats()


class EntityCache:
    """Specialized cache for code entities with relationships."""

    def __init__(self, max_entities: int = 5000):
        """Initialize entity cache.

        Args:
            max_entities: Maximum entities to cache
        """
        self.entities = LRUCache(max_size=max_entities)
        self.by_file = {}  # file_path -> set of entity IDs
        self.by_type = {}  # entity_type -> set of entity IDs

    def set(self, entity_id: int, entity: Any, file_path: str = "", entity_type: str = ""):
        """Cache entity.

        Args:
            entity_id: Entity ID
            entity: Entity object
            file_path: File path for grouping
            entity_type: Entity type for grouping
        """
        # Cache entity
        self.entities.set(f"entity:{entity_id}", entity, ttl_seconds=3600)

        # Index by file
        if file_path:
            if file_path not in self.by_file:
                self.by_file[file_path] = set()
            self.by_file[file_path].add(entity_id)

        # Index by type
        if entity_type:
            if entity_type not in self.by_type:
                self.by_type[entity_type] = set()
            self.by_type[entity_type].add(entity_id)

    def get(self, entity_id: int) -> Optional[Any]:
        """Get cached entity.

        Args:
            entity_id: Entity ID

        Returns:
            Entity or None
        """
        return self.entities.get(f"entity:{entity_id}")

    def get_by_file(self, file_path: str) -> list[int]:
        """Get entity IDs in file.

        Args:
            file_path: File path

        Returns:
            List of entity IDs
        """
        return list(self.by_file.get(file_path, set()))

    def get_by_type(self, entity_type: str) -> list[int]:
        """Get entity IDs of type.

        Args:
            entity_type: Entity type

        Returns:
            List of entity IDs
        """
        return list(self.by_type.get(entity_type, set()))

    def invalidate_file(self, file_path: str):
        """Invalidate entities in file.

        Args:
            file_path: File path
        """
        entity_ids = self.by_file.pop(file_path, set())
        for entity_id in entity_ids:
            self.entities.remove(f"entity:{entity_id}")

    def clear(self):
        """Clear all entity cache."""
        self.entities.clear()
        self.by_file.clear()
        self.by_type.clear()

    def get_stats(self) -> dict:
        """Get cache statistics."""
        return {
            **self.entities.get_stats(),
            "indexed_files": len(self.by_file),
            "indexed_types": len(self.by_type),
        }


class CachedQuery:
    """Decorator for caching function results."""

    def __init__(self, cache: LRUCache, ttl_seconds: int = 300):
        """Initialize cached query decorator.

        Args:
            cache: Cache instance
            ttl_seconds: Cache duration
        """
        self.cache = cache
        self.ttl_seconds = ttl_seconds

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorate function to cache results.

        Args:
            func: Function to decorate

        Returns:
            Wrapped function with caching
        """

        def wrapper(*args, **kwargs) -> T:
            # Generate cache key from function name and arguments
            key = f"{func.__name__}:{args}:{kwargs}"
            key_hash = hashlib.md5(key.encode()).hexdigest()

            # Check cache
            cached = self.cache.get(key_hash)
            if cached is not None:
                return cached

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            self.cache.set(key_hash, result, self.ttl_seconds)

            return result

        return wrapper
