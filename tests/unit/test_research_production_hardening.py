"""Unit tests for research production hardening components."""

import pytest
import asyncio
import time

from athena.research import (
    ResearchQueryCache,
    RateLimiter,
    RateLimitConfig,
    ResearchMetricsCollector,
    CircuitBreaker,
    CircuitBreakerManager,
    CircuitBreakerConfig,
    CircuitState,
)


class TestResearchQueryCache:
    """Test caching for research queries."""

    @pytest.fixture
    def cache(self):
        """Create cache fixture."""
        return ResearchQueryCache(max_entries=5, default_ttl_seconds=3600)

    def test_cache_initialization(self, cache):
        """Test cache initializes correctly."""
        assert cache.max_entries == 5
        assert len(cache.cache) == 0
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0

    def test_cache_set_and_get(self, cache):
        """Test storing and retrieving from cache."""
        findings = [{"title": "Test", "source": "arXiv"}]
        cache.set("machine learning", findings)

        result = cache.get("machine learning")
        assert result == findings

    def test_cache_case_insensitive(self, cache):
        """Test cache is case insensitive."""
        findings = [{"title": "Test"}]
        cache.set("Machine Learning", findings)

        result = cache.get("MACHINE LEARNING")
        assert result == findings

    def test_cache_miss(self, cache):
        """Test cache miss."""
        result = cache.get("nonexistent topic")
        assert result is None
        stats = cache.get_stats()
        assert stats["misses"] == 1

    def test_cache_expiration(self, cache):
        """Test cache entry expiration."""
        findings = [{"title": "Test"}]
        cache.set("topic", findings, ttl_seconds=0.1)

        # Should be in cache immediately
        assert cache.get("topic") is not None

        # Wait for expiration
        time.sleep(0.15)

        # Should be expired
        result = cache.get("topic")
        assert result is None
        stats = cache.get_stats()
        assert stats["expirations"] == 1

    def test_cache_hit_tracking(self, cache):
        """Test cache hit tracking."""
        findings = [{"title": "Test"}]
        cache.set("topic", findings)

        # First get is a hit
        cache.get("topic")
        # Second get is another hit
        cache.get("topic")

        stats = cache.get_stats()
        assert stats["hits"] == 2

    def test_cache_lru_eviction(self, cache):
        """Test LRU eviction when cache is full."""
        # Fill cache
        for i in range(5):
            cache.set(f"topic{i}", [{"title": f"Finding {i}"}])

        # All should be present
        assert len(cache.cache) == 5

        # Add one more (should trigger eviction)
        cache.set("topic5", [{"title": "Finding 5"}])

        # Should still be 5
        assert len(cache.cache) == 5
        stats = cache.get_stats()
        assert stats["evictions"] == 1


class TestRateLimiter:
    """Test rate limiting for research sources."""

    @pytest.fixture
    def limiter(self):
        """Create rate limiter fixture."""
        return RateLimiter()

    def test_rate_limiter_initialization(self, limiter):
        """Test rate limiter initializes with defaults."""
        stats = limiter.get_stats()
        assert stats["sources_configured"] == 8

    def test_allow_request_within_limit(self, limiter):
        """Test requests are allowed within limit."""
        # arXiv has 30 req/min = 0.5 req/sec
        # Burst size is 5, so first 5 should be allowed
        for i in range(5):
            assert limiter.allow_request("arXiv") is True

    def test_rate_limit_exceeded(self, limiter):
        """Test rate limit is enforced."""
        # Use up burst
        for i in range(5):
            limiter.allow_request("arXiv")

        # 6th should be blocked
        assert limiter.allow_request("arXiv") is False

    def test_rate_limit_stats(self, limiter):
        """Test rate limit statistics."""
        for i in range(5):
            limiter.allow_request("arXiv")

        assert limiter.allow_request("arXiv") is False

        stats = limiter.get_stats()
        assert stats["allowed"] == 5
        assert stats["rate_limited"] == 1

    def test_different_sources_independent(self, limiter):
        """Test rate limits are independent per source."""
        # Use up GitHub burst
        for i in range(10):
            limiter.allow_request("GitHub")

        # arXiv should still work
        assert limiter.allow_request("arXiv") is True


class TestResearchMetricsCollector:
    """Test metrics collection."""

    @pytest.fixture
    def collector(self):
        """Create metrics collector fixture."""
        return ResearchMetricsCollector()

    def test_metrics_initialization(self, collector):
        """Test metrics collector initializes."""
        stats = collector.get_all_stats()
        assert stats["total_operations"] == 0
        assert stats["unique_operations"] == 0

    def test_record_operation(self, collector):
        """Test recording operation metrics."""
        metrics = collector.start_operation("agent_search")
        time.sleep(0.01)
        metrics.complete(success=True, items_output=5)

        stats = collector.get_all_stats()
        assert stats["total_operations"] == 1
        assert stats["operations"]["agent_search"]["count"] == 1
        assert stats["operations"]["agent_search"]["successful"] == 1

    def test_operation_duration_tracking(self, collector):
        """Test operation duration is tracked."""
        metrics = collector.start_operation("test_op")
        time.sleep(0.05)
        metrics.complete(success=True)

        stats = collector.get_operation_stats("test_op")
        assert stats["avg_duration_ms"] >= 50

    def test_failed_operation_tracking(self, collector):
        """Test failed operations are tracked."""
        metrics = collector.start_operation("failing_op")
        metrics.complete(success=False, error="Test error")

        stats = collector.get_operation_stats("failing_op")
        assert stats["failed"] == 1
        assert stats["success_rate"] == 0.0


class TestCircuitBreaker:
    """Test circuit breaker pattern."""

    @pytest.fixture
    def breaker(self):
        """Create circuit breaker fixture."""
        config = CircuitBreakerConfig("test_source", failure_threshold=3, timeout_seconds=1)
        return CircuitBreaker(config)

    def test_circuit_breaker_closed_state(self, breaker):
        """Test circuit starts in closed state."""
        assert breaker.state == CircuitState.CLOSED

    def test_circuit_opens_on_failures(self, breaker):
        """Test circuit opens after threshold failures."""
        # Trigger failures
        for i in range(3):
            breaker.on_failure()

        assert breaker.state == CircuitState.OPEN

    def test_circuit_blocks_when_open(self, breaker):
        """Test circuit blocks calls when open."""
        for i in range(3):
            breaker.on_failure()

        def dummy_func():
            return "success"

        with pytest.raises(Exception, match="Circuit breaker OPEN"):
            breaker.call(dummy_func)

    def test_circuit_half_open_recovery(self, breaker):
        """Test circuit transitions to half-open for recovery."""
        # Open the circuit
        for i in range(3):
            breaker.on_failure()

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(1.1)

        # Next call should attempt recovery (half-open)
        def dummy_func():
            return "success"

        result = breaker.call(dummy_func)
        assert result == "success"
        assert breaker.state == CircuitState.HALF_OPEN

    def test_circuit_closes_after_recovery(self, breaker):
        """Test circuit closes after successful recovery."""
        # Open circuit
        for i in range(3):
            breaker.on_failure()

        # Wait for timeout
        time.sleep(1.1)

        # Trigger recovery
        def dummy_func():
            return "success"

        breaker.call(dummy_func)
        breaker.on_success()

        # Should close after 2 successes (success_threshold)
        breaker.call(dummy_func)
        breaker.on_success()

        assert breaker.state == CircuitState.CLOSED

    def test_circuit_status(self, breaker):
        """Test getting circuit breaker status."""
        breaker.on_failure()
        breaker.on_failure()

        status = breaker.get_status()
        assert status["state"] == "closed"
        assert status["failure_count"] == 2


class TestCircuitBreakerManager:
    """Test circuit breaker manager."""

    @pytest.fixture
    def manager(self):
        """Create manager fixture."""
        return CircuitBreakerManager()

    def test_manager_creates_breakers(self, manager):
        """Test manager creates breakers on demand."""
        breaker1 = manager.get_breaker("source1")
        breaker2 = manager.get_breaker("source1")

        assert breaker1 is breaker2

    def test_manager_tracks_healthy_sources(self, manager):
        """Test manager tracks healthy sources."""
        breaker = manager.get_breaker("arXiv")

        # Initially healthy
        healthy = manager.get_healthy_sources()
        assert "arXiv" in healthy

        # Open the circuit
        for i in range(5):
            breaker.on_failure()

        healthy = manager.get_healthy_sources()
        assert "arXiv" not in healthy

    def test_manager_tracks_failing_sources(self, manager):
        """Test manager identifies failing sources."""
        breaker = manager.get_breaker("GitHub")

        # Trigger failures
        for i in range(5):
            breaker.on_failure()

        failing = manager.get_failing_sources()
        assert "GitHub" in failing

    def test_manager_reset_breaker(self, manager):
        """Test resetting a circuit breaker."""
        breaker = manager.get_breaker("test")

        # Open it
        for i in range(5):
            breaker.on_failure()

        assert breaker.state == CircuitState.OPEN

        # Reset
        manager.reset_breaker("test")

        assert breaker.state == CircuitState.CLOSED
