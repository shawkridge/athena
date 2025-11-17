"""Tests for RAG fallback strategies.

Tests graceful degradation when:
1. LLM services are unavailable
2. Embedding services timeout
3. Cache hits on repeated queries
4. Confidence thresholds trigger fallbacks
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from athena.rag.fallback_strategies import (
    FallbackStrategyManager,
    FallbackConfig,
    ResultCache,
    PartialResultHandler,
)
from athena.core.models import MemorySearchResult


class TestResultCache:
    """Test result caching with TTL."""

    def test_cache_set_and_get(self):
        """Test basic cache set and get."""
        cache = ResultCache(ttl_seconds=3600)

        # Create test results
        results = [
            MagicMock(spec=MemorySearchResult, memory_id=1, content="Result 1"),
            MagicMock(spec=MemorySearchResult, memory_id=2, content="Result 2"),
        ]

        # Store results
        cache.set("test_key", results)

        # Retrieve results
        cached = cache.get("test_key")
        assert cached is not None
        assert len(cached) == 2
        assert cached[0].memory_id == 1

    def test_cache_ttl_expiration(self):
        """Test cache TTL expiration."""
        cache = ResultCache(ttl_seconds=1)

        results = [MagicMock(spec=MemorySearchResult, memory_id=1)]
        cache.set("test_key", results)

        # Should be available immediately
        assert cache.get("test_key") is not None

        # Simulate time passing by manipulating timestamp
        cache._cache["test_key"] = (
            results,
            datetime.now() - timedelta(seconds=2),  # 2 seconds ago
        )

        # Should be expired now
        assert cache.get("test_key") is None

    def test_cache_miss(self):
        """Test cache miss on unknown key."""
        cache = ResultCache()
        assert cache.get("unknown_key") is None

    def test_cache_clear(self):
        """Test cache clearing."""
        cache = ResultCache()
        results = [MagicMock(spec=MemorySearchResult)]

        cache.set("key1", results)
        cache.set("key2", results)

        assert len(cache._cache) == 2
        cache.clear()
        assert len(cache._cache) == 0


@pytest.mark.asyncio
class TestFallbackStrategyManager:
    """Test fallback strategy orchestration."""

    @pytest.fixture
    def manager(self):
        """Create fallback manager instance."""
        config = FallbackConfig(
            embedding_timeout=1.0,
            llm_timeout=1.0,
            search_timeout=2.0,
        )
        return FallbackStrategyManager(config)

    @pytest.fixture
    def mock_results(self):
        """Create mock search results."""
        return [
            MagicMock(
                spec=MemorySearchResult,
                memory_id=i,
                content=f"Result {i}",
                confidence=0.8,
            )
            for i in range(3)
        ]

    async def test_retrieve_with_fallback_primary_success(self, manager, mock_results):
        """Test fallback manager when primary retrieval succeeds."""
        # Mock successful primary retrieval
        primary_fn = AsyncMock(return_value=mock_results)
        fallback_fn = AsyncMock()

        results = await manager.retrieve_with_fallback(
            query="test query",
            project_id=1,
            primary_retrieval_fn=primary_fn,
            fallback_retrieval_fn=fallback_fn,
            k=3,
        )

        assert len(results) == 3
        assert primary_fn.called
        assert not fallback_fn.called  # Fallback not used

    async def test_retrieve_with_fallback_primary_fails(self, manager, mock_results):
        """Test fallback manager when primary fails."""
        # Mock failing primary, successful fallback
        primary_fn = AsyncMock(side_effect=Exception("Primary failed"))
        fallback_fn = AsyncMock(return_value=mock_results)

        results = await manager.retrieve_with_fallback(
            query="test query",
            project_id=1,
            primary_retrieval_fn=primary_fn,
            fallback_retrieval_fn=fallback_fn,
            k=3,
        )

        assert len(results) == 3
        assert primary_fn.called
        assert fallback_fn.called  # Fallback used

    async def test_retrieve_with_fallback_timeout(self, manager, mock_results):
        """Test fallback when primary times out."""
        # Create a function that times out
        async def slow_fn(*args, **kwargs):
            await asyncio.sleep(5)  # Longer than timeout
            return mock_results

        fallback_fn = AsyncMock(return_value=mock_results)

        results = await manager.retrieve_with_fallback(
            query="test query",
            project_id=1,
            primary_retrieval_fn=slow_fn,
            fallback_retrieval_fn=fallback_fn,
            k=3,
            timeout=0.5,  # Very short timeout
        )

        assert len(results) == 3
        assert fallback_fn.called

    async def test_retrieve_with_embedding_fallback_success(self, manager, mock_results):
        """Test embedding fallback when embedding search succeeds."""
        embedding_fn = AsyncMock(return_value=mock_results)
        keyword_fn = AsyncMock()

        results = await manager.retrieve_with_embedding_fallback(
            query="test",
            project_id=1,
            embedding_search_fn=embedding_fn,
            keyword_search_fn=keyword_fn,
            k=3,
        )

        assert len(results) == 3
        assert embedding_fn.called
        assert not keyword_fn.called

    async def test_retrieve_with_embedding_fallback_uses_keyword(self, manager, mock_results):
        """Test embedding fallback switches to keyword search."""
        embedding_fn = AsyncMock(side_effect=Exception("Embedding failed"))
        keyword_fn = AsyncMock(return_value=mock_results)

        results = await manager.retrieve_with_embedding_fallback(
            query="test",
            project_id=1,
            embedding_search_fn=embedding_fn,
            keyword_search_fn=keyword_fn,
            k=3,
        )

        assert len(results) == 3
        assert keyword_fn.called

    async def test_retrieve_with_llm_fallback_success(self, manager, mock_results):
        """Test LLM fallback when reranking succeeds."""
        llm_fn = AsyncMock(return_value=mock_results)
        basic_fn = AsyncMock()

        results = await manager.retrieve_with_llm_fallback(
            query="test",
            project_id=1,
            llm_rerank_fn=llm_fn,
            basic_search_fn=basic_fn,
            k=3,
        )

        assert len(results) == 3
        assert llm_fn.called
        assert not basic_fn.called

    async def test_retrieve_with_llm_fallback_uses_basic(self, manager, mock_results):
        """Test LLM fallback switches to basic search."""
        llm_fn = AsyncMock(side_effect=TimeoutError("LLM timed out"))
        basic_fn = AsyncMock(return_value=mock_results)

        results = await manager.retrieve_with_llm_fallback(
            query="test",
            project_id=1,
            llm_rerank_fn=llm_fn,
            basic_search_fn=basic_fn,
            k=3,
        )

        assert len(results) == 3
        assert basic_fn.called

    async def test_confidence_filtering_strict_mode(self, manager):
        """Test confidence-based filtering in strict mode."""
        # Create results with varying confidence
        high_conf = MagicMock(memory_id=1, confidence=0.9)
        med_conf = MagicMock(memory_id=2, confidence=0.5)
        low_conf = MagicMock(memory_id=3, confidence=0.2)

        search_fn = AsyncMock(return_value=[high_conf, med_conf, low_conf])

        results = await manager.retrieve_with_confidence_filtering(
            query="test",
            project_id=1,
            search_fn=search_fn,
            strict_mode=True,  # min_confidence = 0.7
            k=3,
        )

        # Only high confidence result should pass (>= 0.7)
        assert len(results) == 1
        assert results[0].memory_id == 1

    async def test_confidence_filtering_lenient_mode(self, manager):
        """Test confidence-based filtering in lenient mode."""
        high_conf = MagicMock(memory_id=1, confidence=0.9)
        med_conf = MagicMock(memory_id=2, confidence=0.5)
        low_conf = MagicMock(memory_id=3, confidence=0.2)

        search_fn = AsyncMock(return_value=[high_conf, med_conf, low_conf])

        results = await manager.retrieve_with_confidence_filtering(
            query="test",
            project_id=1,
            search_fn=search_fn,
            strict_mode=False,  # min_confidence = 0.3
            k=3,
        )

        # High and medium confidence should pass (>= 0.3)
        assert len(results) == 2
        assert results[0].memory_id == 1
        assert results[1].memory_id == 2

    def test_health_metrics(self, manager):
        """Test health metrics tracking."""
        metrics = manager.get_health_metrics()

        assert "timeout_failures" in metrics
        assert "llm_failures" in metrics
        assert "cache_size" in metrics
        assert "system_healthy" in metrics
        assert metrics["system_healthy"] is True

    def test_reset_health_metrics(self, manager):
        """Test health metrics reset."""
        manager._timeout_count = 5
        manager._llm_failure_count = 3

        manager.reset_health_metrics()

        assert manager._timeout_count == 0
        assert manager._llm_failure_count == 0

    def test_cache_clear(self, manager):
        """Test cache clearing."""
        # Add some cached results
        manager.cache.set("key1", [MagicMock()])
        manager.cache.set("key2", [MagicMock()])

        assert len(manager.cache._cache) == 2

        manager.clear_cache()

        assert len(manager.cache._cache) == 0


class TestPartialResultHandler:
    """Test partial result handling."""

    def test_merge_partial_results_no_duplicates(self):
        """Test merging partial and full results without duplicates."""
        full = [
            MagicMock(memory_id=1, content="A"),
            MagicMock(memory_id=2, content="B"),
        ]
        partial = [
            MagicMock(memory_id=2, content="B"),  # Duplicate
            MagicMock(memory_id=3, content="C"),
        ]

        merged = PartialResultHandler.merge_partial_results(partial, full)

        # Should have 3 unique results
        assert len(merged) == 3
        assert merged[0].memory_id == 1
        assert merged[1].memory_id == 2
        assert merged[2].memory_id == 3

    def test_merge_partial_results_empty_full(self):
        """Test merging when full results are empty."""
        partial = [MagicMock(memory_id=1)]
        full = []

        merged = PartialResultHandler.merge_partial_results(partial, full)

        assert len(merged) == 1
        assert merged[0].memory_id == 1

    def test_merge_partial_results_empty_partial(self):
        """Test merging when partial results are empty."""
        partial = []
        full = [MagicMock(memory_id=1)]

        merged = PartialResultHandler.merge_partial_results(partial, full)

        assert len(merged) == 1
        assert merged[0].memory_id == 1

    def test_filter_by_freshness(self):
        """Test filtering results by freshness."""
        now = datetime.now()

        # Create mocks with proper attributes
        fresh_result = MagicMock()
        fresh_result.created_at = now - timedelta(hours=1)

        old_result = MagicMock()
        old_result.created_at = now - timedelta(hours=48)

        # Result with no created_at attribute uses spec to prevent auto-mocking
        no_timestamp = MagicMock(spec=["content"])

        results = [old_result, fresh_result, no_timestamp]

        filtered = PartialResultHandler.filter_by_freshness(results, max_age_hours=24)

        # Should include fresh and no-timestamp, exclude old
        assert len(filtered) == 2

    def test_format_degradation_notice(self):
        """Test formatting degradation notice."""
        notice = PartialResultHandler.format_degradation_notice(
            reason="LLM timeout",
            fallback_strategy="basic search",
            result_count=3,
        )

        assert "fallback mode" in notice
        assert "LLM timeout" in notice
        assert "basic search" in notice
        assert "3 results" in notice
