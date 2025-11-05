"""Tests for prompt caching support."""

import pytest

from athena.rag.prompt_caching import (
    CacheBlock,
    CacheBlockType,
    CacheMetrics,
    CacheStatus,
    CachingRecommendation,
    PromptCacheManager,
)


@pytest.fixture
def cache_manager():
    """Fixture providing cache manager."""
    return PromptCacheManager()


class TestCacheBlockType:
    """Tests for cache block types."""

    def test_all_block_types_defined(self):
        """Test that all block types are defined."""
        block_types = [
            CacheBlockType.SYSTEM_INSTRUCTIONS,
            CacheBlockType.CONTEXT_BLOCK,
            CacheBlockType.REFERENCE_MATERIAL,
            CacheBlockType.CONVERSATION_HISTORY,
            CacheBlockType.KNOWLEDGE_BASE,
            CacheBlockType.RETRIEVED_MEMORIES,
            CacheBlockType.TASK_DEFINITION,
        ]
        assert len(block_types) == 7


class TestCacheBlock:
    """Tests for CacheBlock."""

    def test_create_cache_block(self):
        """Test creating cache block."""
        block = CacheBlock(
            block_id="test_1",
            block_type=CacheBlockType.SYSTEM_INSTRUCTIONS,
            content="System prompt content",
        )

        assert block.block_id == "test_1"
        assert block.block_type == CacheBlockType.SYSTEM_INSTRUCTIONS
        assert block.cache_status == CacheStatus.NOT_CACHED

    def test_cache_block_hash_generation(self):
        """Test content hash is generated."""
        block = CacheBlock(
            block_id="test_1",
            block_type=CacheBlockType.SYSTEM_INSTRUCTIONS,
            content="Content",
        )

        assert block.content_hash != ""
        assert len(block.content_hash) == 64  # SHA256

    def test_cache_block_hash_deterministic(self):
        """Test that hash is deterministic."""
        content = "Test content"
        block1 = CacheBlock(
            block_id="test_1",
            block_type=CacheBlockType.SYSTEM_INSTRUCTIONS,
            content=content,
        )
        block2 = CacheBlock(
            block_id="test_2",
            block_type=CacheBlockType.SYSTEM_INSTRUCTIONS,
            content=content,
        )

        assert block1.content_hash == block2.content_hash

    def test_cache_block_freshness(self):
        """Test cache freshness detection."""
        block = CacheBlock(
            block_id="test_1",
            block_type=CacheBlockType.SYSTEM_INSTRUCTIONS,
            content="Content",
        )

        # Not cached yet
        assert block.is_stale() is False

        # Mark as cached
        block.cache_status = CacheStatus.CACHED
        from datetime import datetime, timedelta

        block.cached_at = datetime.now() - timedelta(minutes=10)

        # Should be stale (>5 min)
        assert block.is_stale(ttl_minutes=5) is True

    def test_estimate_tokens(self):
        """Test token estimation (1 token ≈ 4 chars)."""
        block = CacheBlock(
            block_id="test_1",
            block_type=CacheBlockType.SYSTEM_INSTRUCTIONS,
            content="A" * 400,  # 400 chars ≈ 100 tokens
        )

        estimated = block.estimate_tokens()
        assert estimated == 100


class TestPromptCacheManager:
    """Tests for PromptCacheManager."""

    def test_manager_initialization(self, cache_manager):
        """Test manager initializes correctly."""
        assert cache_manager.blocks == {}
        assert cache_manager.cache_ttl_minutes == 5

    def test_create_cache_block(self, cache_manager):
        """Test creating cache block."""
        block = cache_manager.create_cache_block(
            CacheBlockType.SYSTEM_INSTRUCTIONS,
            "System prompt content",
        )

        assert block.block_id in cache_manager.blocks
        assert cache_manager.blocks[block.block_id].content == "System prompt content"

    def test_create_multiple_blocks(self, cache_manager):
        """Test creating multiple blocks."""
        block1 = cache_manager.create_cache_block(
            CacheBlockType.SYSTEM_INSTRUCTIONS,
            "System prompt",
        )
        block2 = cache_manager.create_cache_block(
            CacheBlockType.CONTEXT_BLOCK,
            "Context content",
        )

        assert len(cache_manager.blocks) == 2
        assert block1.block_id != block2.block_id

    def test_mark_cached(self, cache_manager):
        """Test marking block as cached."""
        block = cache_manager.create_cache_block(
            CacheBlockType.SYSTEM_INSTRUCTIONS,
            "Content",
        )

        result = cache_manager.mark_cached(block.block_id, cache_tokens=100, input_tokens=150)

        assert result is True
        assert cache_manager.blocks[block.block_id].cache_status == CacheStatus.CACHED
        assert cache_manager.blocks[block.block_id].cache_tokens == 100

    def test_mark_cached_invalid_block(self, cache_manager):
        """Test marking non-existent block fails."""
        result = cache_manager.mark_cached("nonexistent", cache_tokens=100, input_tokens=150)

        assert result is False

    def test_record_cache_hit(self, cache_manager):
        """Test recording cache hit."""
        block = cache_manager.create_cache_block(
            CacheBlockType.SYSTEM_INSTRUCTIONS,
            "Content",
        )
        cache_manager.mark_cached(block.block_id, cache_tokens=100, input_tokens=150)

        result = cache_manager.record_cache_hit(block.block_id)

        assert result is True
        assert cache_manager.blocks[block.block_id].access_count == 1

    def test_record_multiple_cache_hits(self, cache_manager):
        """Test recording multiple cache hits."""
        block = cache_manager.create_cache_block(
            CacheBlockType.SYSTEM_INSTRUCTIONS,
            "Content",
        )
        cache_manager.mark_cached(block.block_id, cache_tokens=100, input_tokens=150)

        for _ in range(5):
            cache_manager.record_cache_hit(block.block_id)

        assert cache_manager.blocks[block.block_id].access_count == 5

    def test_stale_cache_detection(self, cache_manager):
        """Test that stale cache is detected."""
        from datetime import datetime, timedelta

        block = cache_manager.create_cache_block(
            CacheBlockType.SYSTEM_INSTRUCTIONS,
            "Content",
        )
        cache_manager.mark_cached(block.block_id, cache_tokens=100, input_tokens=150)

        # Make cache old
        cache_manager.blocks[block.block_id].cached_at = datetime.now() - timedelta(
            minutes=10
        )

        result = cache_manager.record_cache_hit(block.block_id)

        # Should fail because cache is stale
        assert result is False


class TestCacheMetrics:
    """Tests for CacheMetrics."""

    def test_metrics_creation(self):
        """Test creating metrics."""
        metrics = CacheMetrics()

        assert metrics.total_blocks == 0
        assert metrics.cached_blocks == 0

    def test_cache_hit_rate(self):
        """Test cache hit rate calculation."""
        metrics = CacheMetrics()
        metrics.cache_hits = 80
        metrics.cache_misses = 20

        assert metrics.cache_hit_rate() == 0.8

    def test_cache_hit_rate_empty(self):
        """Test cache hit rate with no data."""
        metrics = CacheMetrics()
        assert metrics.cache_hit_rate() == 0.0

    def test_token_savings_calculation(self):
        """Test token savings calculation."""
        metrics = CacheMetrics()
        metrics.cache_hits = 10
        metrics.cache_misses = 90
        metrics.total_cache_tokens = 1000
        metrics.total_input_tokens = 1500

        savings_pct = metrics.token_savings_percentage()
        assert 0.0 <= savings_pct <= 1.0

    def test_cost_savings(self):
        """Test cost savings calculation."""
        metrics = CacheMetrics()
        metrics.cache_hits = 100
        metrics.cache_misses = 20
        metrics.total_cache_tokens = 5000
        metrics.total_input_tokens = 7500

        savings = metrics.estimated_cost_savings()

        assert "cost_without_cache" in savings
        assert "cost_with_cache" in savings
        assert "savings" in savings
        assert savings["cost_with_cache"] < savings["cost_without_cache"]


class TestGetMetrics:
    """Tests for metrics collection."""

    def test_get_metrics_with_blocks(self, cache_manager):
        """Test getting metrics with cached blocks."""
        block1 = cache_manager.create_cache_block(
            CacheBlockType.SYSTEM_INSTRUCTIONS,
            "Content 1",
        )
        block2 = cache_manager.create_cache_block(
            CacheBlockType.CONTEXT_BLOCK,
            "Content 2",
        )

        cache_manager.mark_cached(block1.block_id, cache_tokens=100, input_tokens=150)
        cache_manager.mark_cached(block2.block_id, cache_tokens=200, input_tokens=300)

        cache_manager.record_cache_hit(block1.block_id)
        cache_manager.record_cache_hit(block1.block_id)
        cache_manager.record_cache_hit(block2.block_id)

        metrics = cache_manager.get_metrics()

        assert metrics.total_blocks == 2
        assert metrics.cached_blocks == 2
        assert metrics.total_cache_tokens == 300
        assert metrics.cache_hits == 3

    def test_get_metrics_empty(self, cache_manager):
        """Test getting metrics with no blocks."""
        metrics = cache_manager.get_metrics()

        assert metrics.total_blocks == 0
        assert metrics.cached_blocks == 0
        assert metrics.cache_hits == 0


class TestRecommendations:
    """Tests for caching recommendations."""

    def test_get_recommendations_empty(self, cache_manager):
        """Test recommendations with no blocks."""
        recommendations = cache_manager.get_recommendations()
        assert isinstance(recommendations, list)

    def test_get_recommendations_with_blocks(self, cache_manager):
        """Test recommendations with cached blocks."""
        # Create and cache large, frequently-used block
        block = cache_manager.create_cache_block(
            CacheBlockType.SYSTEM_INSTRUCTIONS,
            "A" * 1000,  # Large content
        )
        cache_manager.mark_cached(block.block_id, cache_tokens=250, input_tokens=400)

        # Record multiple cache hits
        for _ in range(10):
            cache_manager.record_cache_hit(block.block_id)

        recommendations = cache_manager.get_recommendations()

        assert len(recommendations) > 0
        # Frequently-used blocks should be recommended
        assert any(r.priority == "high" for r in recommendations)

    def test_recommendation_properties(self):
        """Test recommendation has required properties."""
        rec = CachingRecommendation(
            block_type=CacheBlockType.SYSTEM_INSTRUCTIONS,
            block_id="test_1",
            content_size_tokens=500,
            estimated_hit_rate=0.8,
            priority="high",
            reason="Large and frequently used",
        )

        assert rec.estimated_hit_rate == 0.8
        assert rec.priority == "high"


class TestOptimizeCache:
    """Tests for cache optimization."""

    def test_optimize_cache_blocks(self, cache_manager):
        """Test cache optimization analysis."""
        block = cache_manager.create_cache_block(
            CacheBlockType.SYSTEM_INSTRUCTIONS,
            "Content",
        )
        cache_manager.mark_cached(block.block_id, cache_tokens=100, input_tokens=150)

        report = cache_manager.optimize_cache_blocks()

        assert "metrics" in report
        assert "recommendations" in report
        assert "optimization_opportunities" in report

    def test_identify_unused_blocks(self, cache_manager):
        """Test identification of unused blocks."""
        block1 = cache_manager.create_cache_block(
            CacheBlockType.SYSTEM_INSTRUCTIONS,
            "Used",
        )
        block2 = cache_manager.create_cache_block(
            CacheBlockType.CONTEXT_BLOCK,
            "Unused",
        )

        cache_manager.mark_cached(block1.block_id, cache_tokens=100, input_tokens=150)
        cache_manager.mark_cached(block2.block_id, cache_tokens=100, input_tokens=150)

        cache_manager.record_cache_hit(block1.block_id)
        # block2 is not used

        report = cache_manager.optimize_cache_blocks()

        assert report["unused_blocks_count"] >= 1


class TestSummaryReport:
    """Tests for summary report generation."""

    def test_summary_report_format(self, cache_manager):
        """Test summary report has expected format."""
        block = cache_manager.create_cache_block(
            CacheBlockType.SYSTEM_INSTRUCTIONS,
            "Content" * 100,
        )
        cache_manager.mark_cached(block.block_id, cache_tokens=100, input_tokens=150)
        cache_manager.record_cache_hit(block.block_id)

        report = cache_manager.summary_report()

        assert "PROMPT CACHING" in report
        assert "SUMMARY" in report
        assert "COST ESTIMATES" in report

    def test_integration_guide(self, cache_manager):
        """Test integration guide generation."""
        guide = cache_manager.integration_guide()

        assert "PROMPT CACHING INTEGRATION GUIDE" in guide
        assert "cache_control" in guide
        assert "90% savings" in guide


class TestCacheStatus:
    """Tests for cache status enum."""

    def test_all_cache_statuses(self):
        """Test all cache statuses are defined."""
        statuses = [
            CacheStatus.NOT_CACHED,
            CacheStatus.PENDING_CACHE,
            CacheStatus.CACHED,
            CacheStatus.STALE,
            CacheStatus.INVALID,
        ]
        assert len(statuses) == 5


class TestIntegration:
    """Integration tests for caching workflow."""

    def test_full_caching_workflow(self, cache_manager):
        """Test complete caching workflow."""
        # 1. Create blocks
        system_block = cache_manager.create_cache_block(
            CacheBlockType.SYSTEM_INSTRUCTIONS,
            "You are a helpful assistant." * 100,
        )

        context_block = cache_manager.create_cache_block(
            CacheBlockType.CONTEXT_BLOCK,
            "Here is the context..." * 50,
        )

        # 2. Mark as cached
        cache_manager.mark_cached(system_block.block_id, cache_tokens=250, input_tokens=375)
        cache_manager.mark_cached(context_block.block_id, cache_tokens=150, input_tokens=225)

        # 3. Record cache hits
        for _ in range(20):
            cache_manager.record_cache_hit(system_block.block_id)
        for _ in range(5):
            cache_manager.record_cache_hit(context_block.block_id)

        # 4. Get metrics
        metrics = cache_manager.get_metrics()
        assert metrics.total_blocks == 2
        assert metrics.cached_blocks == 2
        assert metrics.cache_hits == 25

        # 5. Get recommendations
        recommendations = cache_manager.get_recommendations()
        assert len(recommendations) > 0

        # 6. Generate report
        report = cache_manager.summary_report()
        assert "PROMPT CACHING" in report
        assert metrics.cache_hit_rate() > 0
