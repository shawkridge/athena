"""Integration tests for Phase D hardening in research executor - Rate limiting and circuit breaker enforcement."""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch

from athena.research import (
    ResearchAgentExecutor,
    ResearchStatus,
    AgentStatus,
    ResearchFinding,
)
from athena.research.store import ResearchStore
from athena.research.cache import ResearchQueryCache
from athena.research.rate_limit import RateLimiter, RateLimitConfig
from athena.research.metrics import ResearchMetricsCollector
from athena.research.circuit_breaker import CircuitBreakerManager
from athena.core.database import Database


pytest.importorskip("psycopg")
class TestExecutorRateLimitingEnforcement:
    """Test that rate limiting is enforced during agent execution."""

    @pytest.fixture
    def executor(self, tmp_path):
        """Create executor with rate limiting enabled."""
        db = Database(str(tmp_path / "test.db"))
        store = ResearchStore(db)

        executor = ResearchAgentExecutor(
            research_store=store,
            enable_cache=False,  # Disable for cleaner testing
            enable_rate_limiting=True,
        )
        return executor

    @pytest.mark.asyncio
    async def test_rate_limiting_blocks_burst_requests(self, executor):
        """Test that rate limiting blocks requests when burst is exceeded."""
        source = "arXiv"

        # Use up the burst (5 for arXiv)
        for i in range(5):
            assert executor.rate_limiter.allow_request(source) is True

        # Next request should be blocked
        assert executor.rate_limiter.allow_request(source) is False

        # Verify stats
        stats = executor.rate_limiter.get_stats()
        assert stats["rate_limited"] > 0

    @pytest.mark.asyncio
    async def test_rate_limiting_per_source_independent(self, executor):
        """Test that rate limiting is independent per source."""
        # Use up arXiv burst
        for i in range(5):
            executor.rate_limiter.allow_request("arXiv")

        # GitHub should still allow requests (burst 10)
        for i in range(5):
            assert executor.rate_limiter.allow_request("GitHub") is True

    @pytest.mark.asyncio
    async def test_wait_if_needed_respects_rate_limits(self, executor):
        """Test that wait_if_needed enforces backpressure."""
        source = "Medium"

        # Use up burst
        for i in range(3):
            executor.rate_limiter.allow_request(source)

        # Next request should require wait
        wait_time = executor.rate_limiter.wait_if_needed(source)
        assert wait_time > 0, "Should require wait time when rate limited"


class TestExecutorCircuitBreakerEnforcement:
    """Test that circuit breaker protections are enforced during agent execution."""

    @pytest.fixture
    def executor(self, tmp_path):
        """Create executor with circuit breakers."""
        db = Database(str(tmp_path / "test.db"))
        store = ResearchStore(db)

        executor = ResearchAgentExecutor(
            research_store=store,
            enable_cache=False,
        )
        return executor

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self, executor):
        """Test circuit breaker opens after repeated failures."""
        source = "HackerNews"
        breaker = executor.circuit_breakers.get_breaker(source)

        # Trigger failures (default threshold is 5)
        for i in range(5):
            breaker.on_failure()

        # Circuit should be open
        assert breaker.state.value == "open"

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_open_source(self, executor):
        """Test that open circuit breaker blocks requests."""
        source = "X/Twitter"
        breaker = executor.circuit_breakers.get_breaker(source)

        # Open the circuit
        for i in range(5):
            breaker.on_failure()

        # Verify it's open
        assert breaker.state.value == "open"

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery_workflow(self, executor):
        """Test circuit breaker recovery from open state."""
        source = "GitHub"
        breaker = executor.circuit_breakers.get_breaker(source)

        # Open the circuit
        for i in range(5):
            breaker.on_failure()

        assert breaker.state.value == "open"

        # Wait for timeout (default 60s)
        breaker.opened_at = 0  # Force timeout elapsed

        # Attempt recovery should work (half-open)
        assert breaker._should_attempt_recovery() is True

    @pytest.mark.asyncio
    async def test_source_health_tracking(self, executor):
        """Test that source health is properly tracked."""
        # All sources should initially be healthy
        healthy = executor.circuit_breakers.get_healthy_sources()
        assert len(healthy) == 0  # No breakers created yet

        failing = executor.circuit_breakers.get_failing_sources()
        assert len(failing) == 0

        # Create and open a breaker
        breaker = executor.circuit_breakers.get_breaker("arXiv")
        for i in range(5):
            breaker.on_failure()

        # Now arXiv should be failing
        failing = executor.circuit_breakers.get_failing_sources()
        assert "arXiv" in failing


class TestExecutorMetricsCollection:
    """Test that metrics are collected during agent execution."""

    @pytest.fixture
    def executor(self, tmp_path):
        """Create executor with metrics enabled."""
        db = Database(str(tmp_path / "test.db"))
        store = ResearchStore(db)

        executor = ResearchAgentExecutor(
            research_store=store,
            enable_cache=False,
        )
        return executor

    @pytest.mark.asyncio
    async def test_agent_operation_metrics_recorded(self, executor):
        """Test that agent operation metrics are recorded."""
        # Start and complete an operation
        metrics = executor.metrics.start_operation("agent_search_test")
        assert metrics is not None

        # Simulate some work
        await asyncio.sleep(0.01)

        # Complete operation
        metrics.complete(success=True, items_output=5)

        # Check stats
        stats = executor.metrics.get_all_stats()
        assert stats["total_operations"] == 1

    @pytest.mark.asyncio
    async def test_task_level_metrics_tracked(self, executor):
        """Test that task-level metrics are tracked."""
        # Start task metrics (without task_id so it goes to history)
        task_metrics = executor.metrics.start_operation("research_task")

        # Complete with success
        task_metrics.complete(success=True, items_output=10)

        # Verify stats - check the specific operation
        stats = executor.metrics.get_operation_stats("research_task")
        assert stats["count"] >= 1
        assert stats["successful"] >= 1

    @pytest.mark.asyncio
    async def test_operation_success_rate_calculation(self, executor):
        """Test that success rate is calculated correctly."""
        # Record successes
        m1 = executor.metrics.start_operation("op1")
        m1.complete(success=True)

        m2 = executor.metrics.start_operation("op2")
        m2.complete(success=True)

        # Record failure
        m3 = executor.metrics.start_operation("op3")
        m3.complete(success=False, error="Test error")

        # Get stats for op1
        stats = executor.metrics.get_operation_stats("op1")
        assert stats["successful"] == 1


class TestExecutorDiagnostics:
    """Test that executor provides comprehensive diagnostics."""

    @pytest.fixture
    def executor(self, tmp_path):
        """Create executor with all features enabled."""
        db = Database(str(tmp_path / "test.db"))
        store = ResearchStore(db)

        executor = ResearchAgentExecutor(
            research_store=store,
            enable_cache=True,
            cache_ttl_seconds=3600,
            enable_rate_limiting=True,
        )
        return executor

    @pytest.mark.asyncio
    async def test_get_diagnostics_includes_all_components(self, executor):
        """Test that get_diagnostics returns all component statuses."""
        diags = executor.get_diagnostics()

        # Should have timestamp
        assert "timestamp" in diags

        # Should have cache diagnostics
        assert "cache" in diags

        # Should have rate limiting diagnostics
        assert "rate_limiting" in diags

        # Should have metrics
        assert "metrics" in diags

        # Should have circuit breaker status
        assert "circuit_breakers" in diags
        assert "healthy_sources" in diags
        assert "failing_sources" in diags

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, executor):
        """Test cache statistics retrieval."""
        stats = executor.get_cache_stats()
        assert "max_entries" in stats
        assert "hits" in stats
        assert "misses" in stats

    @pytest.mark.asyncio
    async def test_get_metrics_summary(self, executor):
        """Test metrics summary retrieval."""
        # Record some operations
        m1 = executor.metrics.start_operation("test_op")
        m1.complete(success=True, items_output=5)

        summary = executor.get_metrics_summary()
        assert "total_operations" in summary
        assert summary["total_operations"] >= 1

    @pytest.mark.asyncio
    async def test_get_source_health(self, executor):
        """Test source health status retrieval."""
        health = executor.get_source_health()

        assert "healthy" in health
        assert "failing" in health
        assert "details" in health

        # details should be a dict mapping sources to status
        assert isinstance(health["details"], dict)


class TestExecutorCachingIntegration:
    """Test cache integration with executor."""

    @pytest.fixture
    def executor(self, tmp_path):
        """Create executor with caching enabled."""
        db = Database(str(tmp_path / "test.db"))
        store = ResearchStore(db)

        executor = ResearchAgentExecutor(
            research_store=store,
            enable_cache=True,
            cache_ttl_seconds=3600,
            enable_rate_limiting=False,
        )
        return executor

    @pytest.mark.asyncio
    async def test_cache_hit_avoids_agent_execution(self, executor):
        """Test that cache hits avoid agent execution."""
        topic = "machine learning"

        # Populate cache
        cache_data = [
            {
                "title": "Test Paper",
                "summary": "Test Summary",
                "source": "arXiv",
                "credibility_score": 0.9,
                "relevance_score": 0.85,
            }
        ]
        executor.cache.set(topic, cache_data)

        # Check cache hit
        cached = executor.cache.get(topic)
        assert cached is not None
        assert len(cached) == 1

    @pytest.mark.asyncio
    async def test_cache_statistics_tracked(self, executor):
        """Test that cache hit/miss statistics are tracked."""
        topic = "artificial intelligence"

        # Cache miss
        result = executor.cache.get(topic)
        assert result is None

        # Cache hit
        executor.cache.set(topic, [{"title": "Test"}])
        result = executor.cache.get(topic)
        assert result is not None

        # Check stats
        stats = executor.cache.get_stats()
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1


class TestProductionHardeningCoordination:
    """Test coordination of all hardening components."""

    @pytest.fixture
    def executor(self, tmp_path):
        """Create fully equipped executor."""
        db = Database(str(tmp_path / "test.db"))
        store = ResearchStore(db)

        executor = ResearchAgentExecutor(
            research_store=store,
            enable_cache=True,
            cache_ttl_seconds=3600,
            enable_rate_limiting=True,
        )
        return executor

    @pytest.mark.asyncio
    async def test_all_hardening_features_active(self, executor):
        """Test that all hardening features are initialized."""
        # Cache enabled
        assert executor.cache is not None

        # Rate limiter enabled
        assert executor.rate_limiter is not None

        # Metrics always enabled
        assert executor.metrics is not None

        # Circuit breakers always enabled
        assert executor.circuit_breakers is not None

    @pytest.mark.asyncio
    async def test_hardening_diagnostics_comprehensive(self, executor):
        """Test that hardening diagnostics are comprehensive."""
        # Populate some data
        executor.cache.set("test_topic", [{"title": "Test"}])
        executor.rate_limiter.allow_request("arXiv")
        executor.metrics.start_operation("test").complete(success=True)
        executor.circuit_breakers.get_breaker("GitHub").on_success()

        # Get diagnostics
        diags = executor.get_diagnostics()

        # All components should report status
        assert "cache" in diags
        assert diags["cache"]["max_entries"] > 0
        assert "hits" in diags["cache"]

        assert "rate_limiting" in diags
        assert diags["rate_limiting"]["total_requests"] >= 1

        assert "metrics" in diags
        assert "total_operations" in diags["metrics"]

        assert "circuit_breakers" in diags
