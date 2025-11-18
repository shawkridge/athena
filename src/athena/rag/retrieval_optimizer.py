"""Retrieval optimization with multi-backend support and intelligent caching.

This module provides optimized retrieval across multiple backends with:
1. Multi-backend support (semantic, graph, procedural)
2. Intelligent caching with LRU eviction
3. Result deduplication and merging
4. Performance monitoring and optimization
5. Fallback strategies for robustness
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Any
from datetime import datetime
from collections import OrderedDict
import hashlib

logger = logging.getLogger(__name__)


class RetrievalBackend(Enum):
    """Available retrieval backends."""

    SEMANTIC = "semantic"  # Vector/semantic search
    GRAPH = "graph"  # Knowledge graph traversal
    PROCEDURAL = "procedural"  # Procedural memory search
    TEMPORAL = "temporal"  # Temporal reasoning
    HYBRID = "hybrid"  # Combine multiple backends


class RetrievalMode(Enum):
    """Retrieval execution modes."""

    FAST = "fast"  # Single backend, highest speed
    BALANCED = "balanced"  # 2-3 backends, good speed/quality
    THOROUGH = "thorough"  # All applicable backends
    ADAPTIVE = "adaptive"  # Choose mode based on query


@dataclass
class RetrievalResult:
    """Result from retrieval operation."""

    query: str
    backend: RetrievalBackend
    items: List[Dict[str, Any]]  # Retrieved items
    count: int  # Number of results
    score: float  # Result quality (0-1)
    latency_ms: float  # Time taken (milliseconds)
    cached: bool = False  # Whether result was cached
    metadata: Dict = field(default_factory=dict)


@dataclass
class MergedResults:
    """Merged results from multiple backends."""

    query: str
    items: List[Dict[str, Any]]  # Merged items
    total_count: int  # Total unique items
    sources: Set[str]  # Which backends provided results
    overall_quality: float  # Quality score (0-1)
    total_latency_ms: float  # Total time taken
    deduplication_ratio: float  # % of duplicates removed
    metadata: Dict = field(default_factory=dict)


@dataclass
class CacheEntry:
    """Cached retrieval result."""

    query_hash: str
    results: List[Dict[str, Any]]
    created_at: datetime
    accessed_at: datetime
    access_count: int = 0
    ttl_seconds: Optional[int] = None


class RetrievalCache:
    """LRU cache for retrieval results."""

    def __init__(self, max_size: int = 1000, default_ttl_seconds: Optional[int] = 3600):
        """Initialize cache.

        Args:
            max_size: Maximum cache entries
            default_ttl_seconds: Default time-to-live (None = infinite)
        """
        self.max_size = max_size
        self.default_ttl_seconds = default_ttl_seconds
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
        }

    def get(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached result.

        Args:
            query: Query string

        Returns:
            Cached results or None
        """
        query_hash = self._hash_query(query)

        if query_hash not in self.cache:
            self.stats["misses"] += 1
            return None

        entry = self.cache[query_hash]

        # Check expiration
        if entry.ttl_seconds is not None:
            age = (datetime.now() - entry.created_at).total_seconds()
            if age > entry.ttl_seconds:
                del self.cache[query_hash]
                self.stats["expirations"] += 1
                return None

        # Update access tracking
        entry.accessed_at = datetime.now()
        entry.access_count += 1

        # Move to end (LRU)
        self.cache.move_to_end(query_hash)

        self.stats["hits"] += 1
        return entry.results

    def put(
        self, query: str, results: List[Dict[str, Any]], ttl_seconds: Optional[int] = None
    ) -> None:
        """Cache result.

        Args:
            query: Query string
            results: Results to cache
            ttl_seconds: Time-to-live (uses default if None)
        """
        query_hash = self._hash_query(query)

        # Remove if exists (will be re-added at end)
        if query_hash in self.cache:
            del self.cache[query_hash]

        # Add new entry
        entry = CacheEntry(
            query_hash=query_hash,
            results=results,
            created_at=datetime.now(),
            accessed_at=datetime.now(),
            access_count=0,
            ttl_seconds=ttl_seconds or self.default_ttl_seconds,
        )

        self.cache[query_hash] = entry

        # Evict LRU if over capacity
        while len(self.cache) > self.max_size:
            _, removed = self.cache.popitem(last=False)
            self.stats["evictions"] += 1
            logger.debug(f"Evicted cache entry: {removed.query_hash}")

    def clear(self) -> None:
        """Clear all cache."""
        self.cache.clear()
        self.stats = {"hits": 0, "misses": 0, "evictions": 0, "expirations": 0}

    def _hash_query(self, query: str) -> str:
        """Hash query for cache key."""
        return hashlib.md5(query.encode()).hexdigest()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0

        return {
            **self.stats,
            "hit_rate": hit_rate,
            "current_size": len(self.cache),
            "max_size": self.max_size,
            "utilization": len(self.cache) / self.max_size if self.max_size > 0 else 0,
        }


class ResultMerger:
    """Merges results from multiple backends."""

    def __init__(self):
        """Initialize merger."""
        pass

    def merge(self, results: List[RetrievalResult]) -> MergedResults:
        """Merge results from multiple backends.

        Args:
            results: List of RetrievalResult from different backends

        Returns:
            MergedResults with deduplicated items
        """
        if not results:
            return MergedResults(
                query="",
                items=[],
                total_count=0,
                sources=set(),
                overall_quality=0.0,
                total_latency_ms=0.0,
                deduplication_ratio=0.0,
            )

        # Extract query and sources
        query = results[0].query if results else ""
        sources = {r.backend.value for r in results}

        # Collect all items
        all_items = []
        for result in results:
            all_items.extend(result.items)

        # Deduplicate
        unique_items = self._deduplicate(all_items)
        dedup_ratio = 1.0 - (len(unique_items) / len(all_items)) if all_items else 0.0

        # Calculate overall quality
        overall_quality = self._calculate_overall_quality(results)

        # Calculate total latency
        total_latency = sum(r.latency_ms for r in results)

        return MergedResults(
            query=query,
            items=unique_items,
            total_count=len(unique_items),
            sources=sources,
            overall_quality=overall_quality,
            total_latency_ms=total_latency,
            deduplication_ratio=dedup_ratio,
        )

    def _deduplicate(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate items.

        Args:
            items: Items to deduplicate

        Returns:
            List of unique items
        """
        seen_ids: Set[str] = set()
        unique_items = []

        for item in items:
            # Try to extract ID-like fields
            item_id = item.get("id") or item.get("uid") or item.get("name")

            if item_id and item_id in seen_ids:
                continue

            if item_id:
                seen_ids.add(str(item_id))

            unique_items.append(item)

        return unique_items

    def _calculate_overall_quality(self, results: List[RetrievalResult]) -> float:
        """Calculate overall quality from multiple results."""
        if not results:
            return 0.0

        # Weight by result count (more results = higher confidence)
        quality_scores = []
        for result in results:
            # Quality = backend score * count factor
            count_factor = min(1.0, result.count / 10)  # 10 results = full score
            quality = result.score * (0.7 + 0.3 * count_factor)
            quality_scores.append(quality)

        # Average quality across backends
        return sum(quality_scores) / len(quality_scores)


class RetrievalOptimizer:
    """Optimizes retrieval across multiple backends."""

    def __init__(
        self,
        cache_size: int = 1000,
        cache_ttl_seconds: Optional[int] = 3600,
    ):
        """Initialize optimizer.

        Args:
            cache_size: Max cache entries
            cache_ttl_seconds: Default cache TTL
        """
        self.cache = RetrievalCache(cache_size, cache_ttl_seconds)
        self.merger = ResultMerger()
        self.backends: Dict[RetrievalBackend, Any] = {}
        self.mode = RetrievalMode.BALANCED

    def register_backend(self, backend: RetrievalBackend, retriever: Any) -> None:
        """Register a retrieval backend.

        Args:
            backend: Backend type
            retriever: Retriever implementation
        """
        self.backends[backend] = retriever
        logger.info(f"Registered retrieval backend: {backend.value}")

    def retrieve(
        self,
        query: str,
        mode: Optional[RetrievalMode] = None,
        backends: Optional[List[RetrievalBackend]] = None,
        use_cache: bool = True,
        top_k: int = 10,
    ) -> MergedResults:
        """Retrieve from optimal backends.

        Args:
            query: Query string
            mode: Retrieval mode (uses default if None)
            backends: Specific backends to use (uses all if None)
            use_cache: Whether to use cache
            top_k: Number of results to retrieve

        Returns:
            MergedResults from retrieval
        """
        # Check cache
        if use_cache:
            cached = self.cache.get(query)
            if cached is not None:
                latency = 0.0
                return MergedResults(
                    query=query,
                    items=cached[:top_k],
                    total_count=len(cached),
                    sources={"cache"},
                    overall_quality=0.95,  # Assume high quality if cached
                    total_latency_ms=latency,
                    deduplication_ratio=0.0,
                )

        # Determine mode
        mode = mode or self.mode

        # Determine which backends to use
        if backends is None:
            backends = self._select_backends_by_mode(mode)

        # Retrieve from selected backends
        results = []
        start_time = time.time()

        for backend_type in backends:
            if backend_type not in self.backends:
                logger.warning(f"Backend not registered: {backend_type.value}")
                continue

            retriever = self.backends[backend_type]

            try:
                backend_start = time.time()

                # Call backend retriever
                items = retriever.search(query, top_k=top_k)
                backend_latency = (time.time() - backend_start) * 1000

                # Create result
                result = RetrievalResult(
                    query=query,
                    backend=backend_type,
                    items=items if items else [],
                    count=len(items) if items else 0,
                    score=self._score_backend_results(items),
                    latency_ms=backend_latency,
                )

                results.append(result)

            except Exception as e:
                logger.warning(f"Backend {backend_type.value} failed: {e}")
                continue

        total_latency = (time.time() - start_time) * 1000

        # Merge results
        merged = self.merger.merge(results)
        merged.total_latency_ms = total_latency

        # Cache results if retrieved
        if results:
            all_items = [item for result in results for item in result.items]
            self.cache.put(query, all_items)

        # Limit to top_k
        merged.items = merged.items[:top_k]

        return merged

    def _select_backends_by_mode(self, mode: RetrievalMode) -> List[RetrievalBackend]:
        """Select backends based on mode."""
        available_backends = list(self.backends.keys())

        if mode == RetrievalMode.FAST:
            # Single fastest backend
            return available_backends[:1]
        elif mode == RetrievalMode.BALANCED:
            # 2-3 backends for good balance
            return available_backends[: min(2, len(available_backends))]
        elif mode == RetrievalMode.THOROUGH:
            # All available backends
            return available_backends
        else:  # ADAPTIVE
            # Choose based on query characteristics
            return available_backends[: min(2, len(available_backends))]

    def _score_backend_results(self, items: List[Dict[str, Any]]) -> float:
        """Score quality of backend results."""
        if not items:
            return 0.0

        # Check for result quality indicators
        has_scores = any("score" in item or "relevance" in item for item in items)
        has_metadata = any("metadata" in item or "context" in item for item in items)

        score = 0.5  # Base score

        if has_scores:
            score += 0.25

        if has_metadata:
            score += 0.25

        # Bonus for more results (up to 10)
        result_bonus = min(0.1, len(items) / 100)
        score += result_bonus

        return min(1.0, score)

    def clear_cache(self) -> None:
        """Clear retrieval cache."""
        self.cache.clear()
        logger.info("Retrieval cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.get_stats()

    def get_backend_stats(self) -> Dict[str, int]:
        """Get backend statistics."""
        return {
            "registered_backends": len(self.backends),
            "backend_types": [b.value for b in self.backends.keys()],
        }
