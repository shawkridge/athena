"""Unit tests for token tracking and cost analysis.

Tests the token tracking module for compression, caching, and cost metrics.
"""

import pytest
from datetime import datetime, timedelta

from athena.evaluation.token_tracking import (
    TokenSource,
    CompressionMetric,
    TokenCount,
    CompressionResult,
    CacheResult,
    ConsolidationTokenMetrics,
    TokenTracker,
    TokenMetricsAggregator,
)


class TestCompressionResult:
    """Test compression result data structure."""

    def test_compression_result_creation(self):
        """Test creating compression result."""
        result = CompressionResult(
            original_tokens=1000,
            compressed_tokens=350,
            compression_ratio=0.35,
            tokens_saved=650,
            latency_ms=150,
            quality_preservation=0.98,
        )

        assert result.original_tokens == 1000
        assert result.compressed_tokens == 350
        assert result.compression_ratio == 0.35
        assert result.tokens_saved == 650
        assert result.compression_percentage == 65.0
        assert result.quality_preservation == 0.98

    def test_compression_result_validation(self):
        """Test compression result validation."""
        # Invalid ratio should fail
        with pytest.raises(AssertionError):
            CompressionResult(
                original_tokens=1000,
                compressed_tokens=350,
                compression_ratio=1.5,  # Invalid: >1.0
                tokens_saved=650,
                latency_ms=150,
                quality_preservation=0.98,
            )

        # Mismatched tokens should fail
        with pytest.raises(AssertionError):
            CompressionResult(
                original_tokens=1000,
                compressed_tokens=350,
                compression_ratio=0.35,
                tokens_saved=700,  # Should be 650
                latency_ms=150,
                quality_preservation=0.98,
            )

    def test_compression_result_string(self):
        """Test string representation."""
        result = CompressionResult(
            original_tokens=1000,
            compressed_tokens=350,
            compression_ratio=0.35,
            tokens_saved=650,
            latency_ms=150,
            quality_preservation=0.98,
        )

        result_str = str(result)
        assert "1,000" in result_str
        assert "350" in result_str
        assert "65.0%" in result_str


class TestCacheResult:
    """Test cache result data structure."""

    def test_cache_hit(self):
        """Test cache hit."""
        result = CacheResult(
            cache_hit=True,
            tokens_sent_to_claude=350,
            tokens_saved_via_cache=650,
            cache_age_seconds=60,
        )

        assert result.cache_hit is True
        assert result.cache_savings_percentage == pytest.approx(65.0)

    def test_cache_miss(self):
        """Test cache miss."""
        result = CacheResult(
            cache_hit=False,
            tokens_sent_to_claude=1000,
            tokens_saved_via_cache=0,
        )

        assert result.cache_hit is False
        assert result.cache_savings_percentage == 0.0

    def test_cache_result_string(self):
        """Test string representation."""
        hit_result = CacheResult(
            cache_hit=True,
            tokens_sent_to_claude=350,
            tokens_saved_via_cache=650,
        )

        assert "HIT" in str(hit_result)
        assert "650" in str(hit_result)

        miss_result = CacheResult(
            cache_hit=False,
            tokens_sent_to_claude=1000,
            tokens_saved_via_cache=0,
        )

        assert "MISS" in str(miss_result)


class TestConsolidationTokenMetrics:
    """Test consolidation token metrics."""

    def test_basic_metrics(self):
        """Test basic token metrics."""
        metrics = ConsolidationTokenMetrics(
            original_tokens=1000,
            final_tokens_to_claude=350,
            tokens_from_claude=100,
        )

        assert metrics.total_input_tokens == 350
        assert metrics.total_tokens_processed == 450
        assert metrics.compression_ratio == 0.35
        assert metrics.compression_percentage == 65.0
        assert metrics.tokens_saved_total == 650

    def test_with_compression(self):
        """Test metrics with compression result."""
        compression = CompressionResult(
            original_tokens=1000,
            compressed_tokens=350,
            compression_ratio=0.35,
            tokens_saved=650,
            latency_ms=150,
            quality_preservation=0.98,
        )

        metrics = ConsolidationTokenMetrics(
            original_tokens=1000,
            final_tokens_to_claude=350,
            tokens_from_claude=100,
            compression_result=compression,
        )

        assert metrics.compression_result == compression
        assert metrics.compression_percentage == 65.0

    def test_with_cache_hit(self):
        """Test metrics with cache hit."""
        cache = CacheResult(
            cache_hit=True,
            tokens_sent_to_claude=35,  # 10% of original due to caching
            tokens_saved_via_cache=315,
        )

        metrics = ConsolidationTokenMetrics(
            original_tokens=1000,
            final_tokens_to_claude=35,
            tokens_from_claude=100,
            cache_result=cache,
        )

        assert metrics.cache_result.cache_hit is True
        assert metrics.compression_percentage == 96.5  # 96.5% total reduction

    def test_cost_reduction_with_compression_only(self):
        """Test cost reduction with compression only."""
        compression = CompressionResult(
            original_tokens=10000,
            compressed_tokens=3500,
            compression_ratio=0.35,
            tokens_saved=6500,
            latency_ms=150,
            quality_preservation=0.98,
        )

        metrics = ConsolidationTokenMetrics(
            original_tokens=10000,
            final_tokens_to_claude=3500,
            tokens_from_claude=500,
            compression_result=compression,
        )

        # Cost reduction = (original - final) / original
        # (10000 - 3500) / 10000 = 65%
        assert metrics.cost_reduction_percentage == pytest.approx(65.0)

    def test_cost_reduction_with_cache_hit(self):
        """Test cost reduction with cache hit (90% savings on cached)."""
        compression = CompressionResult(
            original_tokens=10000,
            compressed_tokens=3500,
            compression_ratio=0.35,
            tokens_saved=6500,
            latency_ms=150,
            quality_preservation=0.98,
        )

        cache = CacheResult(
            cache_hit=True,
            tokens_sent_to_claude=350,  # Only 10% due to caching (90% discount)
            tokens_saved_via_cache=3150,
        )

        metrics = ConsolidationTokenMetrics(
            original_tokens=10000,
            final_tokens_to_claude=350,
            tokens_from_claude=50,
            compression_result=compression,
            cache_result=cache,
        )

        # With compression (35% cost) + cache (10% of that) = 3.5% of original cost
        # Cost reduction = (10000 - 350) / 10000 = 96.5%
        assert metrics.cost_reduction_percentage == pytest.approx(96.5)

    def test_metrics_string(self):
        """Test string representation."""
        metrics = ConsolidationTokenMetrics(
            original_tokens=1000,
            final_tokens_to_claude=350,
            tokens_from_claude=100,
        )

        metrics_str = str(metrics)
        assert "Original tokens" in metrics_str
        assert "1,000" in metrics_str
        assert "Compression" in metrics_str


class TestTokenTracker:
    """Test token tracker for recording metrics."""

    def test_create_tracker(self):
        """Test creating token tracker."""
        tracker = TokenTracker(
            consolidation_id="test_123",
            original_tokens=1000,
        )

        assert tracker.consolidation_id == "test_123"
        assert tracker.original_tokens == 1000

    def test_record_compression(self):
        """Test recording compression."""
        tracker = TokenTracker(
            consolidation_id="test_123",
            original_tokens=1000,
        )

        compression = CompressionResult(
            original_tokens=1000,
            compressed_tokens=350,
            compression_ratio=0.35,
            tokens_saved=650,
            latency_ms=150,
            quality_preservation=0.98,
        )

        tracker.record_compression(compression)

        assert tracker.compression_result == compression
        assert tracker.tokens_after_compression == 350

    def test_record_cache_lookup(self):
        """Test recording cache lookup."""
        tracker = TokenTracker(
            consolidation_id="test_123",
            original_tokens=1000,
        )

        cache = CacheResult(
            cache_hit=True,
            tokens_sent_to_claude=350,
            tokens_saved_via_cache=650,
        )

        tracker.record_cache_lookup(cache, latency_ms=5)

        assert tracker.cache_result == cache
        assert tracker.metadata["cache_lookup_ms"] == 5

    def test_record_claude_call(self):
        """Test recording Claude API call."""
        tracker = TokenTracker(
            consolidation_id="test_123",
            original_tokens=1000,
        )

        tracker.record_claude_call(input_tokens=350, output_tokens=100, latency_ms=2000)

        assert tracker.tokens_to_claude == 350
        assert tracker.tokens_from_claude == 100
        assert tracker.metadata["claude_call_ms"] == 2000

    def test_to_metrics(self):
        """Test converting tracker to metrics."""
        tracker = TokenTracker(
            consolidation_id="test_123",
            original_tokens=1000,
        )

        compression = CompressionResult(
            original_tokens=1000,
            compressed_tokens=350,
            compression_ratio=0.35,
            tokens_saved=650,
            latency_ms=150,
            quality_preservation=0.98,
        )

        tracker.record_compression(compression)
        tracker.record_claude_call(input_tokens=350, output_tokens=100, latency_ms=2000)

        metrics = tracker.to_metrics()

        assert isinstance(metrics, ConsolidationTokenMetrics)
        assert metrics.original_tokens == 1000
        assert metrics.after_compression == 350
        assert metrics.final_tokens_to_claude == 350
        assert metrics.tokens_from_claude == 100


class TestTokenMetricsAggregator:
    """Test aggregating metrics across multiple consolidations."""

    def test_empty_aggregator(self):
        """Test empty aggregator."""
        agg = TokenMetricsAggregator()

        assert agg.total_consolidations == 0
        assert agg.total_original_tokens == 0
        assert agg.total_final_tokens == 0
        assert agg.average_compression_ratio == 1.0
        assert agg.average_cache_hit_rate == 0.0

    def test_add_single_metrics(self):
        """Test adding single metrics."""
        agg = TokenMetricsAggregator()

        metrics = ConsolidationTokenMetrics(
            original_tokens=1000,
            final_tokens_to_claude=350,
            tokens_from_claude=100,
        )

        agg.add_metrics(metrics)

        assert agg.total_consolidations == 1
        assert agg.total_original_tokens == 1000
        assert agg.total_final_tokens == 350

    def test_average_compression_ratio(self):
        """Test average compression ratio."""
        agg = TokenMetricsAggregator()

        # Add two metrics with different compression ratios
        metrics1 = ConsolidationTokenMetrics(
            original_tokens=1000,
            final_tokens_to_claude=350,  # 35%
            tokens_from_claude=100,
        )

        metrics2 = ConsolidationTokenMetrics(
            original_tokens=2000,
            final_tokens_to_claude=400,  # 20%
            tokens_from_claude=100,
        )

        agg.add_metrics(metrics1)
        agg.add_metrics(metrics2)

        # Average ratio = (350 + 400) / (1000 + 2000) = 750 / 3000 = 0.25
        assert agg.average_compression_ratio == pytest.approx(0.25)
        assert agg.average_compression_percentage == pytest.approx(75.0)

    def test_cache_hit_rate(self):
        """Test cache hit rate calculation."""
        agg = TokenMetricsAggregator()

        # Add metrics with cache hits and misses
        cache_hit = CacheResult(cache_hit=True, tokens_sent_to_claude=350, tokens_saved_via_cache=650)
        cache_miss = CacheResult(cache_hit=False, tokens_sent_to_claude=1000, tokens_saved_via_cache=0)

        metrics1 = ConsolidationTokenMetrics(
            original_tokens=1000,
            final_tokens_to_claude=350,
            tokens_from_claude=100,
            cache_result=cache_hit,
        )

        metrics2 = ConsolidationTokenMetrics(
            original_tokens=1000,
            final_tokens_to_claude=1000,
            tokens_from_claude=100,
            cache_result=cache_miss,
        )

        agg.add_metrics(metrics1)
        agg.add_metrics(metrics2)

        # Hit rate = 1 / 2 = 0.5 (50%)
        assert agg.average_cache_hit_rate == pytest.approx(0.5)

    def test_total_tokens_saved(self):
        """Test total tokens saved."""
        agg = TokenMetricsAggregator()

        metrics1 = ConsolidationTokenMetrics(
            original_tokens=1000,
            final_tokens_to_claude=350,
            tokens_from_claude=100,
        )

        metrics2 = ConsolidationTokenMetrics(
            original_tokens=2000,
            final_tokens_to_claude=400,
            tokens_from_claude=100,
        )

        agg.add_metrics(metrics1)
        agg.add_metrics(metrics2)

        # Total saved = (1000 - 350) + (2000 - 400) = 650 + 1600 = 2250
        assert agg.total_tokens_saved == 2250

    def test_summary(self):
        """Test summary generation."""
        agg = TokenMetricsAggregator()

        metrics = ConsolidationTokenMetrics(
            original_tokens=1000,
            final_tokens_to_claude=350,
            tokens_from_claude=100,
        )

        agg.add_metrics(metrics)

        summary = agg.get_summary()

        assert "Token Metrics Summary" in summary
        assert "Consolidations: 1" in summary
        assert "Original tokens: 1,000" in summary
        assert "65.0%" in summary  # compression percentage
