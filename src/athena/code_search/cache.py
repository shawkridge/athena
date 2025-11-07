"""Caching layer for code search results."""

from typing import Dict, List, Optional, Tuple
from functools import lru_cache
import hashlib
import logging

from .models import SearchResult

logger = logging.getLogger(__name__)


class SearchResultCache:
    """LRU cache for search results."""

    def __init__(self, max_size: int = 1000):
        """Initialize cache.

        Args:
            max_size: Maximum number of cached results
        """
        self.max_size = max_size
        self.cache: Dict[str, List[SearchResult]] = {}
        self.hits = 0
        self.misses = 0

    def _make_key(self, query: str, limit: int, min_score: float) -> str:
        """Create cache key from query parameters."""
        key_str = f"{query}:{limit}:{min_score}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, query: str, limit: int, min_score: float) -> Optional[List[SearchResult]]:
        """Get cached search results.

        Args:
            query: Search query
            limit: Result limit
            min_score: Minimum score threshold

        Returns:
            Cached results or None if not found
        """
        key = self._make_key(query, limit, min_score)
        if key in self.cache:
            self.hits += 1
            logger.debug(f"Cache hit: {query} (hits={self.hits})")
            return self.cache[key]
        self.misses += 1
        return None

    def set(
        self,
        query: str,
        limit: int,
        min_score: float,
        results: List[SearchResult],
    ) -> None:
        """Cache search results.

        Args:
            query: Search query
            limit: Result limit
            min_score: Minimum score threshold
            results: Search results to cache
        """
        key = self._make_key(query, limit, min_score)

        # Simple LRU: remove oldest if cache is full
        if len(self.cache) >= self.max_size:
            # Remove first (oldest) item
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            logger.debug(f"Cache evicted: {oldest_key}")

        self.cache[key] = results
        logger.debug(f"Cache set: {query} ({len(results)} results)")

    def clear(self) -> None:
        """Clear all cached results."""
        self.cache.clear()
        logger.debug("Cache cleared")

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        return {
            "cached_queries": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "total": total,
            "hit_rate": hit_rate,
            "max_size": self.max_size,
        }


class EmbeddingCache:
    """LRU cache for embeddings."""

    def __init__(self, max_size: int = 5000):
        """Initialize embedding cache.

        Args:
            max_size: Maximum number of cached embeddings
        """
        self.max_size = max_size
        self.cache: Dict[str, List[float]] = {}
        self.hits = 0
        self.misses = 0

    def _make_key(self, text: str) -> str:
        """Create cache key from text."""
        return hashlib.md5(text.encode()).hexdigest()

    def get(self, text: str) -> Optional[List[float]]:
        """Get cached embedding.

        Args:
            text: Text to get embedding for

        Returns:
            Cached embedding or None if not found
        """
        key = self._make_key(text)
        if key in self.cache:
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None

    def set(self, text: str, embedding: List[float]) -> None:
        """Cache embedding.

        Args:
            text: Text that was embedded
            embedding: Embedding vector
        """
        key = self._make_key(text)

        # Simple LRU: remove oldest if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        self.cache[key] = embedding

    def clear(self) -> None:
        """Clear all cached embeddings."""
        self.cache.clear()

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        return {
            "cached_embeddings": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "total": total,
            "hit_rate": hit_rate,
            "max_size": self.max_size,
        }


class TypeFilterCache:
    """Cache for type-based filtering results."""

    def __init__(self, max_size: int = 500):
        """Initialize type filter cache.

        Args:
            max_size: Maximum number of cached filters
        """
        self.max_size = max_size
        self.cache: Dict[str, List[str]] = {}

    def _make_key(self, unit_type: str) -> str:
        """Create cache key from unit type."""
        return f"type:{unit_type}"

    def get(self, unit_type: str) -> Optional[List[str]]:
        """Get cached type filter results.

        Args:
            unit_type: Unit type to filter by

        Returns:
            Cached unit IDs or None if not found
        """
        key = self._make_key(unit_type)
        return self.cache.get(key)

    def set(self, unit_type: str, unit_ids: List[str]) -> None:
        """Cache type filter results.

        Args:
            unit_type: Unit type
            unit_ids: List of matching unit IDs
        """
        key = self._make_key(unit_type)

        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        self.cache[key] = unit_ids

    def clear(self) -> None:
        """Clear all cached filters."""
        self.cache.clear()


class CombinedSearchCache:
    """Combined cache for search operations."""

    def __init__(
        self,
        search_cache_size: int = 1000,
        embedding_cache_size: int = 5000,
        type_cache_size: int = 500,
    ):
        """Initialize combined cache.

        Args:
            search_cache_size: Max size of search result cache
            embedding_cache_size: Max size of embedding cache
            type_cache_size: Max size of type filter cache
        """
        self.search_cache = SearchResultCache(search_cache_size)
        self.embedding_cache = EmbeddingCache(embedding_cache_size)
        self.type_cache = TypeFilterCache(type_cache_size)

    def clear_all(self) -> None:
        """Clear all caches."""
        self.search_cache.clear()
        self.embedding_cache.clear()
        self.type_cache.clear()

    def get_stats(self) -> Dict:
        """Get statistics from all caches.

        Returns:
            Dictionary with combined cache stats
        """
        return {
            "search": self.search_cache.get_stats(),
            "embedding": self.embedding_cache.get_stats(),
            "type_filter": {
                "cached_filters": len(self.type_cache.cache),
                "max_size": self.type_cache.max_size,
            },
        }
