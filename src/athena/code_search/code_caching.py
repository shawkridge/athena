"""Caching strategies for code search and analysis operations.

This module provides multi-layer caching for embeddings, queries, graph operations,
and pattern detection to optimize performance and reduce redundant computations.
"""

import logging
import time
import json
import hashlib
from typing import Any, Dict, Optional, List, Tuple
from dataclasses import dataclass
from collections import OrderedDict
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Cache strategies for different use cases."""
    LRU = "lru"              # Least recently used
    LFU = "lfu"              # Least frequently used
    TTL = "ttl"              # Time-to-live based expiration
    FIFO = "fifo"            # First in, first out
    ARC = "arc"              # Adaptive replacement cache


@dataclass
class CacheEntry:
    """Represents a single cache entry."""
    key: str
    value: Any
    timestamp: float
    access_count: int = 0
    size_bytes: int = 0

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if entry has expired based on TTL."""
        if ttl_seconds <= 0:
            return False
        age = time.time() - self.timestamp
        return age > ttl_seconds


class BaseCache(ABC):
    """Abstract base class for cache implementations."""

    def __init__(self, max_size: int = 1000, strategy: CacheStrategy = CacheStrategy.LRU):
        """Initialize cache."""
        self.max_size = max_size
        self.strategy = strategy
        self.entries: Dict[str, CacheEntry] = {}
        self.hits = 0
        self.misses = 0

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all entries."""
        pass

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0.0
        total_size = sum(e.size_bytes for e in self.entries.values())

        return {
            "strategy": self.strategy.value,
            "size": len(self.entries),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "total_size_bytes": total_size,
        }

    def _get_size_bytes(self, obj: Any) -> int:
        """Estimate object size in bytes."""
        try:
            if isinstance(obj, str):
                return len(obj.encode('utf-8'))
            elif isinstance(obj, (dict, list)):
                return len(json.dumps(obj))
            else:
                return 1000  # Default estimate
        except:
            return 1000


class LRUCache(BaseCache):
    """Least Recently Used cache implementation."""

    def __init__(self, max_size: int = 1000):
        """Initialize LRU cache."""
        super().__init__(max_size, CacheStrategy.LRU)
        self.access_order: OrderedDict[str, None] = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        """Get value and move to end (recently used)."""
        if key not in self.entries:
            self.misses += 1
            return None

        entry = self.entries[key]
        entry.access_count += 1
        self.hits += 1

        # Move to end (most recently used)
        self.access_order.move_to_end(key)
        return entry.value

    def set(self, key: str, value: Any) -> None:
        """Set value and update LRU order."""
        size = self._get_size_bytes(value)

        if key in self.entries:
            self.access_order.move_to_end(key)
            self.entries[key].value = value
            self.entries[key].size_bytes = size
        else:
            self.entries[key] = CacheEntry(key, value, time.time(), size_bytes=size)
            self.access_order[key] = None

        # Evict if over capacity
        while len(self.entries) > self.max_size:
            lru_key = next(iter(self.access_order))
            del self.entries[lru_key]
            del self.access_order[lru_key]

    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        if key in self.entries:
            del self.entries[key]
            del self.access_order[key]
            return True
        return False

    def clear(self) -> None:
        """Clear cache."""
        self.entries.clear()
        self.access_order.clear()
        self.hits = 0
        self.misses = 0


class TTLCache(BaseCache):
    """Time-To-Live based cache with automatic expiration."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """Initialize TTL cache."""
        super().__init__(max_size, CacheStrategy.TTL)
        self.ttl_seconds = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """Get value if not expired."""
        if key not in self.entries:
            self.misses += 1
            return None

        entry = self.entries[key]

        # Check expiration
        if entry.is_expired(self.ttl_seconds):
            del self.entries[key]
            self.misses += 1
            return None

        entry.access_count += 1
        self.hits += 1
        entry.timestamp = time.time()  # Update access time
        return entry.value

    def set(self, key: str, value: Any) -> None:
        """Set value with TTL."""
        size = self._get_size_bytes(value)
        self.entries[key] = CacheEntry(key, value, time.time(), size_bytes=size)

        # Evict oldest if over capacity
        if len(self.entries) > self.max_size:
            oldest_key = min(
                self.entries.keys(),
                key=lambda k: self.entries[k].timestamp
            )
            del self.entries[oldest_key]

    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        if key in self.entries:
            del self.entries[key]
            return True
        return False

    def clear(self) -> None:
        """Clear cache."""
        self.entries.clear()
        self.hits = 0
        self.misses = 0


class EmbeddingCache(LRUCache):
    """Specialized cache for code embeddings."""

    def get_embedding(self, code_text: str, model: str = "default") -> Optional[List[float]]:
        """Get cached embedding for code."""
        key = self._make_key(code_text, model)
        return self.get(key)

    def set_embedding(self, code_text: str, embedding: List[float], model: str = "default") -> None:
        """Cache embedding for code."""
        key = self._make_key(code_text, model)
        self.set(key, embedding)

    def _make_key(self, code_text: str, model: str) -> str:
        """Generate cache key from code text and model."""
        code_hash = hashlib.md5(code_text.encode()).hexdigest()
        return f"embedding:{model}:{code_hash}"


class QueryCache(LRUCache):
    """Specialized cache for search query results."""

    def get_results(self, query_text: str, strategy: str = "hybrid", top_k: int = 10) -> Optional[List[Any]]:
        """Get cached search results."""
        key = self._make_key(query_text, strategy, top_k)
        return self.get(key)

    def set_results(self, query_text: str, results: List[Any], strategy: str = "hybrid", top_k: int = 10) -> None:
        """Cache search results."""
        key = self._make_key(query_text, strategy, top_k)
        self.set(key, results)

    def _make_key(self, query_text: str, strategy: str, top_k: int) -> str:
        """Generate cache key from query parameters."""
        query_hash = hashlib.md5(query_text.encode()).hexdigest()
        return f"query:{strategy}:{top_k}:{query_hash}"


class GraphCache(LRUCache):
    """Specialized cache for code graph operations."""

    def get_related_entities(self, entity_name: str, max_depth: int = 2) -> Optional[List[str]]:
        """Get cached related entities."""
        key = f"graph:related:{entity_name}:{max_depth}"
        return self.get(key)

    def set_related_entities(self, entity_name: str, entities: List[str], max_depth: int = 2) -> None:
        """Cache related entities."""
        key = f"graph:related:{entity_name}:{max_depth}"
        self.set(key, entities)

    def get_dependencies(self, entity_name: str) -> Optional[List[str]]:
        """Get cached dependencies."""
        key = f"graph:deps:{entity_name}"
        return self.get(key)

    def set_dependencies(self, entity_name: str, deps: List[str]) -> None:
        """Cache dependencies."""
        key = f"graph:deps:{entity_name}"
        self.set(key, deps)

    def get_path(self, source: str, target: str) -> Optional[List[str]]:
        """Get cached path between entities."""
        key = f"graph:path:{source}:{target}"
        return self.get(key)

    def set_path(self, source: str, target: str, path: List[str]) -> None:
        """Cache path between entities."""
        key = f"graph:path:{source}:{target}"
        self.set(key, path)


class PatternCache(LRUCache):
    """Specialized cache for pattern detection results."""

    def get_patterns(self, entity_name: str, pattern_type: str = "all") -> Optional[List[Dict]]:
        """Get cached patterns."""
        key = f"pattern:{pattern_type}:{entity_name}"
        return self.get(key)

    def set_patterns(self, entity_name: str, patterns: List[Dict], pattern_type: str = "all") -> None:
        """Cache patterns."""
        key = f"pattern:{pattern_type}:{entity_name}"
        self.set(key, patterns)


class CacheManager:
    """Unified cache manager for all cache layers."""

    def __init__(self, max_size: int = 1000):
        """Initialize cache manager."""
        self.max_size = max_size
        self.embedding_cache = EmbeddingCache(max_size)
        self.query_cache = QueryCache(max_size)
        self.graph_cache = GraphCache(max_size)
        self.pattern_cache = PatternCache(max_size)
        self.ttl_cache = TTLCache(max_size, ttl_seconds=3600)

        self.cache_layers = {
            "embeddings": self.embedding_cache,
            "queries": self.query_cache,
            "graph": self.graph_cache,
            "patterns": self.pattern_cache,
            "ttl": self.ttl_cache,
        }

    def clear_all(self) -> None:
        """Clear all cache layers."""
        for cache in self.cache_layers.values():
            cache.clear()

    def clear_layer(self, layer_name: str) -> None:
        """Clear specific cache layer."""
        if layer_name in self.cache_layers:
            self.cache_layers[layer_name].clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all cache layers."""
        stats = {}
        for name, cache in self.cache_layers.items():
            stats[name] = cache.get_stats()

        # Aggregate stats
        total_hits = sum(s["hits"] for s in stats.values())
        total_misses = sum(s["misses"] for s in stats.values())
        total = total_hits + total_misses
        overall_hit_rate = total_hits / total if total > 0 else 0.0

        return {
            "layers": stats,
            "total_hits": total_hits,
            "total_misses": total_misses,
            "overall_hit_rate": overall_hit_rate,
            "total_size_bytes": sum(
                sum(e.size_bytes for e in cache.entries.values())
                for cache in self.cache_layers.values()
            ),
        }

    def generate_cache_report(self) -> str:
        """Generate comprehensive cache statistics report."""
        stats = self.get_stats()

        report = "CACHE PERFORMANCE REPORT\n"
        report += "=" * 60 + "\n\n"

        report += f"Overall Hit Rate: {stats['overall_hit_rate']:.1%}\n"
        report += f"Total Hits: {stats['total_hits']}\n"
        report += f"Total Misses: {stats['total_misses']}\n"
        report += f"Total Cache Size: {stats['total_size_bytes']:,} bytes\n\n"

        report += "Cache Layer Performance:\n"
        report += "-" * 60 + "\n"

        for layer_name, layer_stats in stats["layers"].items():
            report += f"\n{layer_name.upper()}:\n"
            report += f"  Size: {layer_stats['size']}/{layer_stats['max_size']}\n"
            report += f"  Hit Rate: {layer_stats['hit_rate']:.1%}\n"
            report += f"  Hits: {layer_stats['hits']}\n"
            report += f"  Misses: {layer_stats['misses']}\n"
            report += f"  Bytes: {layer_stats['total_size_bytes']:,}\n"

        return report
