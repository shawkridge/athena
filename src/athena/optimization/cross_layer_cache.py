"""Cross-layer result caching for intelligent result reuse.

This module caches combinations of layer results, not just individual layers.
Instead of caching "episodic results" and "semantic results" separately,
it caches "episodic + semantic results together" which often can be reused
as a unit for similar queries.

Key features:
- Cache entries combine results from multiple layers
- Intelligent TTL management (shorter for volatile, longer for stable)
- Hit/miss tracking with per-combination statistics
- Cache invalidation based on confidence and age
- LRU eviction when cache is full
"""

import hashlib
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CrossLayerCacheEntry:
    """Single cache entry combining multiple layers' results."""

    cache_key: str  # Hash of (query_type, layers, params)
    timestamp: float  # When cached (Unix timestamp)
    layers_included: List[str]  # Which layers' results are combined
    aggregate_result: Dict[str, Any]  # Merged results from all layers
    confidence: float  # 0.0-1.0, quality/freshness of cache
    hit_count: int = 0  # Times this entry has been used
    total_queries_saved: int = 0  # Cumulative count of queries avoided
    ttl_seconds: int = 300  # Time to live
    size_bytes: int = 0  # Estimated memory usage

    def age_seconds(self) -> float:
        """Get age of cache entry in seconds."""
        return time.time() - self.timestamp

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return self.age_seconds() > self.ttl_seconds

    def update_confidence(self) -> None:
        """Recalculate confidence based on age.

        Recent entries have higher confidence.
        Confidence decays over time.
        """
        age_factor = max(1.0 - (self.age_seconds() / self.ttl_seconds), 0.1)
        hit_factor = min(self.hit_count / 10.0, 1.0)  # Cap at 10 hits

        # Combine: higher if recent, higher if frequently hit
        self.confidence = (age_factor * 0.7) + (hit_factor * 0.3)


class CrossLayerCache:
    """Caches combinations of layer results for intelligent reuse.

    Tracks which layer combinations are cached together, their hit rates,
    and the value (queries saved) of caching them.

    Example:
        cache = CrossLayerCache(max_entries=5000, default_ttl_seconds=300)

        # Try to get cached results
        cached = cache.try_get_cached(
            query_type="temporal",
            layers=["episodic", "semantic"],
            params={"k": 5}
        )

        if cached:
            return cached  # Use cache
        else:
            # Execute query
            results = await query_all_layers(layers)

            # Cache results for next time
            cache.cache_result(
                query_type="temporal",
                layers=["episodic", "semantic"],
                results=results,
                ttl=300
            )
    """

    def __init__(self, max_entries: int = 5000, default_ttl_seconds: int = 300):
        """Initialize cross-layer cache.

        Args:
            max_entries: Maximum cache entries before LRU eviction
            default_ttl_seconds: Default time-to-live for entries
        """
        self.max_entries = max_entries
        self.default_ttl_seconds = default_ttl_seconds

        # OrderedDict maintains insertion order for LRU
        self.entries: OrderedDict[str, CrossLayerCacheEntry] = OrderedDict()

        # Hit statistics
        self.hit_stats: Dict[str, int] = {}  # cache_key -> hit count
        self.miss_stats: Dict[str, int] = {}  # cache_key -> miss count

        # Layer combination stats
        self.layer_combo_stats: Dict[str, Dict[str, Any]] = {}  # "layer1:layer2" -> stats

        # Total statistics
        self.total_hits = 0
        self.total_misses = 0
        self.total_queries_saved = 0
        self.total_bytes_cached = 0

        # Layer-specific TTL overrides (can be customized)
        self.layer_ttl_overrides: Dict[str, int] = {
            "episodic": 180,  # Events decay faster
            "semantic": 300,  # Knowledge lasts longer
            "procedural": 600,  # Procedures very stable
            "prospective": 240,  # Tasks change moderately
            "graph": 600,  # Graph structure stable
            "meta": 120,  # Meta-info changes frequently
        }

        logger.info(f"CrossLayerCache initialized: max_entries={max_entries}")

    def get_cache_key(
        self, query_type: str, layers: List[str], params: Optional[Dict] = None
    ) -> str:
        """Generate deterministic cache key.

        Args:
            query_type: Type of query
            layers: Layers being queried (will be sorted)
            params: Optional parameters (k, filters, etc.)

        Returns:
            Deterministic hash key
        """
        # Sort layers for consistency
        sorted_layers = sorted(layers)

        # Build key components
        key_parts = [query_type, ":".join(sorted_layers)]

        # Add relevant params (ignore ones that shouldn't affect cache)
        if params:
            param_subset = {
                k: v
                for k, v in params.items()
                if k in ("k", "query_text", "query_hash", "start_date", "end_date")
            }
            key_parts.append(json.dumps(param_subset, sort_keys=True))

        key_str = "|".join(key_parts)

        # Create hash
        return hashlib.sha256(key_str.encode()).hexdigest()

    def try_get_cached(
        self,
        query_type: str,
        layers: List[str],
        params: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        """Try to get cached results for this query.

        Args:
            query_type: Type of query
            layers: Layers being queried
            params: Optional parameters

        Returns:
            Cached results if available and not expired, None otherwise
        """
        cache_key = self.get_cache_key(query_type, layers, params)

        # Check if in cache
        if cache_key not in self.entries:
            self._record_miss(cache_key)
            return None

        entry = self.entries[cache_key]

        # Check if expired
        if entry.is_expired():
            del self.entries[cache_key]
            self._record_miss(cache_key)
            return None

        # Update entry stats
        entry.hit_count += 1
        entry.update_confidence()

        # Move to end (LRU)
        self.entries.move_to_end(cache_key)

        # Record hit
        self._record_hit(cache_key, entry)

        logger.debug(
            f"Cache HIT: {cache_key[:16]}... layers={layers}, "
            f"hit_count={entry.hit_count}, age={entry.age_seconds():.1f}s"
        )

        return entry.aggregate_result

    def cache_result(
        self,
        query_type: str,
        layers: List[str],
        results: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> None:
        """Cache results from multiple layers.

        Args:
            query_type: Type of query
            layers: Layers that were queried
            results: Dictionary of results from all layers
            ttl: Optional custom TTL (seconds)
        """
        cache_key = self.get_cache_key(query_type, layers)

        # Determine TTL
        if ttl is None:
            ttl = self._compute_ttl(layers)

        # Estimate size
        size_bytes = self._estimate_size(results)

        # Create entry
        entry = CrossLayerCacheEntry(
            cache_key=cache_key,
            timestamp=time.time(),
            layers_included=sorted(layers),
            aggregate_result=results,
            confidence=1.0,  # New entries have high confidence
            ttl_seconds=ttl,
            size_bytes=size_bytes,
        )

        # Check if cache is full
        if len(self.entries) >= self.max_entries:
            self._evict_lru()

        # Add to cache
        self.entries[cache_key] = entry
        self.total_bytes_cached += size_bytes

        # Update layer combo stats
        self._update_layer_combo_stats(layers, size_bytes)

        logger.debug(
            f"Cache PUT: {cache_key[:16]}... layers={layers}, "
            f"ttl={ttl}s, size={size_bytes} bytes"
        )

    def _compute_ttl(self, layers: List[str]) -> int:
        """Compute TTL based on layers being cached.

        Args:
            layers: Layer names

        Returns:
            TTL in seconds
        """
        # Use the shortest TTL from involved layers
        # (most volatile layer determines cache lifetime)
        min_ttl = self.default_ttl_seconds

        for layer in layers:
            layer_ttl = self.layer_ttl_overrides.get(layer, self.default_ttl_seconds)
            min_ttl = min(min_ttl, layer_ttl)

        return min_ttl

    def _estimate_size(self, results: Dict[str, Any]) -> int:
        """Estimate memory size of results.

        Args:
            results: Result dictionary

        Returns:
            Estimated size in bytes
        """
        try:
            json_str = json.dumps(results, default=str)
            return len(json_str.encode())
        except Exception:
            # Fallback
            return 1024

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self.entries:
            return

        # Remove oldest (least recently used) entry
        key_to_evict = next(iter(self.entries))
        entry = self.entries.pop(key_to_evict)

        self.total_bytes_cached -= entry.size_bytes

        logger.debug(
            f"Cache EVICT (LRU): {key_to_evict[:16]}... "
            f"freed {entry.size_bytes} bytes"
        )

    def _record_hit(self, cache_key: str, entry: CrossLayerCacheEntry) -> None:
        """Record cache hit."""
        self.hit_stats[cache_key] = self.hit_stats.get(cache_key, 0) + 1
        self.total_hits += 1
        self.total_queries_saved += len(entry.layers_included)

    def _record_miss(self, cache_key: str) -> None:
        """Record cache miss."""
        self.miss_stats[cache_key] = self.miss_stats.get(cache_key, 0) + 1
        self.total_misses += 1

    def _update_layer_combo_stats(self, layers: List[str], size_bytes: int) -> None:
        """Update statistics for this layer combination."""
        combo_key = ":".join(sorted(layers))

        if combo_key not in self.layer_combo_stats:
            self.layer_combo_stats[combo_key] = {
                "cache_count": 0,
                "total_size": 0,
                "hit_count": 0,
            }

        stats = self.layer_combo_stats[combo_key]
        stats["cache_count"] += 1
        stats["total_size"] += size_bytes

    def get_cache_effectiveness(self) -> Dict[str, Any]:
        """Get cache effectiveness metrics.

        Returns:
            Dictionary with hit rate, bytes saved, efficiency, etc.
        """
        total_queries = self.total_hits + self.total_misses

        if total_queries == 0:
            hit_rate = 0.0
        else:
            hit_rate = self.total_hits / total_queries

        # Estimate queries saved (assuming avg 2-3 layers per hit)
        avg_layers_per_hit = self.total_queries_saved / max(self.total_hits, 1)

        return {
            "hit_rate": hit_rate,
            "total_hits": self.total_hits,
            "total_misses": self.total_misses,
            "total_cached_entries": len(self.entries),
            "total_bytes_cached": self.total_bytes_cached,
            "total_queries_saved": self.total_queries_saved,
            "avg_layers_per_hit": avg_layers_per_hit,
            "cache_size_mb": self.total_bytes_cached / (1024 * 1024),
            "entries_at_capacity": len(self.entries) >= self.max_entries,
            "top_hit_entries": self._get_top_entries(limit=5),
            "layer_combination_stats": self.layer_combo_stats,
        }

    def _get_top_entries(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get entries with highest hit count.

        Args:
            limit: Number of top entries to return

        Returns:
            List of entry stats
        """
        sorted_entries = sorted(
            self.entries.items(),
            key=lambda x: x[1].hit_count,
            reverse=True,
        )

        result = []
        for key, entry in sorted_entries[:limit]:
            result.append(
                {
                    "layers": entry.layers_included,
                    "hit_count": entry.hit_count,
                    "age_seconds": entry.age_seconds(),
                    "confidence": entry.confidence,
                    "size_bytes": entry.size_bytes,
                }
            )

        return result

    def invalidate_layer(self, layer_name: str) -> int:
        """Invalidate all cache entries containing a specific layer.

        Args:
            layer_name: Layer to invalidate

        Returns:
            Number of entries invalidated
        """
        keys_to_remove = []

        for key, entry in self.entries.items():
            if layer_name in entry.layers_included:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            entry = self.entries.pop(key)
            self.total_bytes_cached -= entry.size_bytes

        logger.info(f"Invalidated {len(keys_to_remove)} cache entries for layer {layer_name}")
        return len(keys_to_remove)

    def clear(self) -> None:
        """Clear entire cache."""
        self.entries.clear()
        self.hit_stats.clear()
        self.miss_stats.clear()
        self.layer_combo_stats.clear()
        self.total_hits = 0
        self.total_misses = 0
        self.total_queries_saved = 0
        self.total_bytes_cached = 0

        logger.info("CrossLayerCache cleared")

    def prune_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries removed
        """
        keys_to_remove = []

        for key, entry in self.entries.items():
            if entry.is_expired():
                keys_to_remove.append(key)

        for key in keys_to_remove:
            entry = self.entries.pop(key)
            self.total_bytes_cached -= entry.size_bytes

        logger.debug(f"Pruned {len(keys_to_remove)} expired cache entries")
        return len(keys_to_remove)
