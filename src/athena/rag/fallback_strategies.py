"""RAG Fallback Strategies for Graceful Degradation.

Provides fallback mechanisms when primary retrieval methods fail:
1. Embedding Failure → Keyword-only search
2. LLM Unavailable → Basic vector + keyword fallback
3. Timeout → Partial result with caching
4. Low Confidence → Conservative result filtering
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..core.models import MemorySearchResult

logger = logging.getLogger(__name__)


@dataclass
class FallbackConfig:
    """Configuration for fallback strategies."""

    # Timeout configurations (seconds)
    embedding_timeout: float = 5.0
    llm_timeout: float = 10.0
    search_timeout: float = 15.0

    # Confidence thresholds
    min_confidence_strict: float = 0.7  # Strict mode (high confidence required)
    min_confidence_lenient: float = 0.3  # Lenient mode (accept lower confidence)

    # Caching
    cache_results: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour

    # Result limits
    min_results_required: int = 1  # Return at least this many results
    max_timeout_results: int = 3  # Max results before timeout fallback


class ResultCache:
    """Simple in-memory cache for search results with TTL."""

    def __init__(self, ttl_seconds: int = 3600):
        """Initialize cache with TTL.

        Args:
            ttl_seconds: Time-to-live for cached entries
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, tuple[List[MemorySearchResult], datetime]] = {}

    def get(self, key: str) -> Optional[List[MemorySearchResult]]:
        """Get cached results if available and not expired.

        Args:
            key: Cache key (typically query hash)

        Returns:
            Cached results or None if expired/missing
        """
        if key not in self._cache:
            return None

        results, timestamp = self._cache[key]
        if datetime.now() - timestamp > timedelta(seconds=self.ttl_seconds):
            # Expired, remove it
            del self._cache[key]
            return None

        logger.debug(f"Cache hit for key: {key}")
        return results

    def set(self, key: str, results: List[MemorySearchResult]) -> None:
        """Cache results.

        Args:
            key: Cache key
            results: Results to cache
        """
        self._cache[key] = (results, datetime.now())
        logger.debug(f"Cached {len(results)} results for key: {key}")

    def clear(self) -> None:
        """Clear all cached results."""
        self._cache.clear()

    def cleanup_expired(self) -> None:
        """Remove expired entries."""
        now = datetime.now()
        expired_keys = [
            key
            for key, (_, timestamp) in self._cache.items()
            if now - timestamp > timedelta(seconds=self.ttl_seconds)
        ]
        for key in expired_keys:
            del self._cache[key]
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")


class FallbackStrategyManager:
    """Manages fallback strategies for RAG failures."""

    def __init__(self, config: Optional[FallbackConfig] = None):
        """Initialize fallback manager.

        Args:
            config: Fallback configuration (uses defaults if None)
        """
        self.config = config or FallbackConfig()
        self.cache = ResultCache(self.config.cache_ttl_seconds)
        self._timeout_count = 0
        self._llm_failure_count = 0

    async def retrieve_with_fallback(
        self,
        query: str,
        project_id: int,
        primary_retrieval_fn,
        fallback_retrieval_fn,
        k: int = 5,
        timeout: float = None,
    ) -> List[MemorySearchResult]:
        """Execute retrieval with automatic fallback on failure.

        Args:
            query: Search query
            project_id: Project ID
            primary_retrieval_fn: Primary retrieval function (async)
            fallback_retrieval_fn: Fallback retrieval function (async)
            k: Number of results to return
            timeout: Optional timeout override (seconds)

        Returns:
            Search results (primary or fallback)
        """
        timeout = timeout or self.config.search_timeout
        cache_key = f"{project_id}:{query}:{k}"

        # Try cache first
        if self.config.cache_results:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning cached results for query: {query[:50]}")
                return cached[:k]

        # Try primary retrieval with timeout
        try:
            logger.debug(f"Attempting primary retrieval (timeout={timeout}s)")
            results = await self._execute_with_timeout(
                primary_retrieval_fn(query, project_id, k),
                timeout=timeout,
            )

            if results:
                # Cache successful results
                if self.config.cache_results:
                    self.cache.set(cache_key, results)
                self._timeout_count = 0  # Reset counter
                return results
            else:
                logger.warning("Primary retrieval returned empty results")

        except TimeoutError:
            logger.warning(f"Primary retrieval timed out after {timeout}s")
            self._timeout_count += 1

        except Exception as e:
            logger.warning(f"Primary retrieval failed: {e}")
            self._timeout_count += 1

        # Fallback to secondary retrieval
        logger.info("Falling back to secondary retrieval strategy")
        try:
            results = await self._execute_with_timeout(
                fallback_retrieval_fn(query, project_id, k),
                timeout=timeout * 0.5,  # More aggressive timeout for fallback
            )

            if results:
                if self.config.cache_results:
                    self.cache.set(cache_key, results)
                return results
            else:
                logger.error("Fallback retrieval also returned empty results")
                return []

        except Exception as e:
            logger.error(f"Fallback retrieval failed: {e}")
            return []

    async def retrieve_with_embedding_fallback(
        self,
        query: str,
        project_id: int,
        embedding_search_fn,
        keyword_search_fn,
        k: int = 5,
    ) -> List[MemorySearchResult]:
        """Fallback from embedding-based search to keyword search.

        Args:
            query: Search query
            project_id: Project ID
            embedding_search_fn: Function that performs embedding search (async)
            keyword_search_fn: Function that performs keyword search (async)
            k: Number of results

        Returns:
            Search results (embedding-based or keyword-based)
        """
        try:
            logger.debug("Attempting embedding-based search")
            results = await self._execute_with_timeout(
                embedding_search_fn(query, project_id, k),
                timeout=self.config.embedding_timeout,
            )

            if results:
                return results
            logger.warning("Embedding search returned empty results")

        except TimeoutError:
            logger.warning(f"Embedding search timed out after {self.config.embedding_timeout}s")

        except Exception as e:
            logger.warning(f"Embedding search failed: {e}. Falling back to keyword search.")

        # Fallback to keyword-only search
        try:
            logger.info("Falling back to keyword-based search")
            results = await self._execute_with_timeout(
                keyword_search_fn(query, project_id, k),
                timeout=self.config.search_timeout,
            )

            return results or []

        except Exception as e:
            logger.error(f"Keyword search also failed: {e}")
            return []

    async def retrieve_with_llm_fallback(
        self,
        query: str,
        project_id: int,
        llm_rerank_fn,
        basic_search_fn,
        k: int = 5,
    ) -> List[MemorySearchResult]:
        """Fallback from LLM-based reranking to basic search.

        Args:
            query: Search query
            project_id: Project ID
            llm_rerank_fn: Function that performs LLM-based reranking (async)
            basic_search_fn: Function that performs basic search (async)
            k: Number of results

        Returns:
            Search results (reranked or basic)
        """
        try:
            logger.debug("Attempting LLM-based reranking")
            results = await self._execute_with_timeout(
                llm_rerank_fn(query, project_id, k),
                timeout=self.config.llm_timeout,
            )

            if results:
                self._llm_failure_count = 0  # Reset counter
                return results

            logger.warning("LLM reranking returned empty results")

        except TimeoutError:
            self._llm_failure_count += 1
            logger.warning(
                f"LLM reranking timed out after {self.config.llm_timeout}s "
                f"(failure #{self._llm_failure_count})"
            )

        except Exception as e:
            self._llm_failure_count += 1
            logger.warning(
                f"LLM reranking failed: {e} (failure #{self._llm_failure_count}). "
                "Falling back to basic search."
            )

        # Fallback to basic search
        try:
            logger.info("Falling back to basic search")
            results = await self._execute_with_timeout(
                basic_search_fn(query, project_id, k),
                timeout=self.config.search_timeout,
            )

            return results or []

        except Exception as e:
            logger.error(f"Basic search also failed: {e}")
            return []

    async def retrieve_with_confidence_filtering(
        self,
        query: str,
        project_id: int,
        search_fn,
        strict_mode: bool = False,
        k: int = 5,
    ) -> List[MemorySearchResult]:
        """Apply confidence-based filtering to results.

        Args:
            query: Search query
            project_id: Project ID
            search_fn: Search function (async)
            strict_mode: If True, require high confidence (>=0.7). Otherwise lenient (>=0.3)
            k: Number of results to return

        Returns:
            Filtered search results
        """
        try:
            results = await self._execute_with_timeout(
                search_fn(query, project_id, k * 2),  # Get more for filtering
                timeout=self.config.search_timeout,
            )

            min_conf = (
                self.config.min_confidence_strict
                if strict_mode
                else self.config.min_confidence_lenient
            )

            filtered = []
            for result in results:
                # Check confidence if available
                confidence = getattr(result, "confidence", 1.0)
                if confidence >= min_conf:
                    filtered.append(result)
                    if len(filtered) >= k:
                        break

            logger.debug(
                f"Confidence filtering (strict={strict_mode}): "
                f"{len(results)} → {len(filtered)} results"
            )

            return filtered

        except Exception as e:
            logger.error(f"Confidence filtering failed: {e}")
            return []

    async def _execute_with_timeout(self, coro, timeout: float = None):
        """Execute async coroutine with timeout.

        Args:
            coro: Coroutine to execute
            timeout: Timeout in seconds

        Returns:
            Coroutine result or raises TimeoutError

        Raises:
            TimeoutError: If execution exceeds timeout
        """
        import asyncio

        if timeout is None:
            return await coro

        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Operation timed out after {timeout}s")

    def get_health_metrics(self) -> Dict[str, Any]:
        """Get health metrics for fallback strategies.

        Returns:
            Dictionary with metrics
        """
        return {
            "timeout_failures": self._timeout_count,
            "llm_failures": self._llm_failure_count,
            "cache_size": len(self.cache._cache),
            "system_healthy": self._llm_failure_count < 5,  # Alert if >5 consecutive failures
        }

    def reset_health_metrics(self) -> None:
        """Reset health metrics."""
        self._timeout_count = 0
        self._llm_failure_count = 0

    def clear_cache(self) -> None:
        """Clear result cache."""
        self.cache.clear()


class PartialResultHandler:
    """Handles partial results from timed-out operations."""

    @staticmethod
    def merge_partial_results(
        partial: List[MemorySearchResult], full: List[MemorySearchResult]
    ) -> List[MemorySearchResult]:
        """Merge partial and full results, deduplicating.

        Args:
            partial: Results from partial/timed-out operation
            full: Results from complete operation

        Returns:
            Merged results with duplicates removed
        """
        if not full:
            return partial
        if not partial:
            return full

        # Track seen memory IDs to avoid duplicates
        seen = {getattr(r, "memory_id", id(r)) for r in full}
        merged = list(full)

        for result in partial:
            result_id = getattr(result, "memory_id", id(result))
            if result_id not in seen:
                merged.append(result)
                seen.add(result_id)

        return merged

    @staticmethod
    def filter_by_freshness(
        results: List[MemorySearchResult], max_age_hours: int = 24
    ) -> List[MemorySearchResult]:
        """Filter results by recency (fresher results prioritized).

        Args:
            results: Search results
            max_age_hours: Maximum age in hours

        Returns:
            Filtered results sorted by recency
        """
        now = datetime.now()
        max_age = timedelta(hours=max_age_hours)

        fresh = []
        for result in results:
            if hasattr(result, "created_at") and isinstance(result.created_at, datetime):
                if now - result.created_at <= max_age:
                    fresh.append(result)
            else:
                # No timestamp info, include it
                fresh.append(result)

        # Sort by recency (newest first)
        fresh.sort(
            key=lambda r: getattr(r, "created_at", None) or now,
            reverse=True,
        )

        return fresh

    @staticmethod
    def format_degradation_notice(reason: str, fallback_strategy: str, result_count: int) -> str:
        """Format a user-visible notice about degraded service.

        Args:
            reason: Why degradation occurred
            fallback_strategy: What strategy was used instead
            result_count: Number of results returned

        Returns:
            Formatted notice string
        """
        return (
            f"Search service using fallback mode ({reason}). "
            f"Using {fallback_strategy}. "
            f"Found {result_count} results."
        )
