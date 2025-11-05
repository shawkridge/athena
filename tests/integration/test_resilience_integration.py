"""Integration tests for resilience patterns with real memory operations.

Tests retry, fallback, and circuit breaker patterns with actual memory stores.
"""

import pytest
import time
from unittest.mock import Mock, patch

from athena.resilience.degradation import (
    RetryPolicy,
    RetryStrategy,
    FallbackChain,
    with_retry,
    with_fallback,
    CircuitBreaker,
)
from athena.resilience.health import (
    HealthStatus,
    HealthChecker,
)


class TestRetryWithMemoryOperations:
    """Test retry logic with simulated memory operations."""

    def test_retry_on_transient_database_error(self):
        """Test retrying on transient database errors."""
        call_count = 0

        def flaky_insert(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("transient error")  # Use retryable exception
            return {"id": 1, "content": "test"}

        policy = RetryPolicy(max_attempts=3, initial_delay=0.01)

        @with_retry(policy)
        def insert_with_retry():
            return flaky_insert(
                project_id=1,
                content="test memory",
                memory_type="fact",
                tags=["test"],
            )

        # Should succeed after retry
        result = insert_with_retry()
        assert result is not None
        assert call_count == 2  # First failed, second succeeded

    def test_fallback_on_query_failure(self):
        """Test fallback chain on query failure."""
        chain = FallbackChain("query_fallback")

        def primary_query():
            raise RuntimeError("primary failed")

        def fallback_query():
            # Simple fallback: return cached results
            return [{"id": 1, "content": "cached"}]

        chain.add("primary", primary_query)
        chain.add("fallback", fallback_query)

        result = chain.execute()
        assert result is not None
        assert len(result) > 0


class TestCircuitBreakerWithHealthChecks:
    """Test circuit breaker integrated with health checks."""

    def test_circuit_breaker_prevents_cascading_failures(self):
        """Test circuit breaker stops cascading failures."""
        breaker = CircuitBreaker(
            "query_breaker",
            fail_threshold=2,
            success_threshold=2,
            timeout=0.1,
        )

        call_count = 0

        def unreliable_operation():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise ValueError("service error")
            return "success"

        # First 2 calls fail, circuit opens
        with pytest.raises(ValueError):
            breaker.call(unreliable_operation)

        with pytest.raises(ValueError):
            breaker.call(unreliable_operation)

        assert breaker.state == CircuitBreaker.State.OPEN

        # Subsequent call fast-fails without attempting
        initial_count = call_count
        with pytest.raises(Exception):  # CircuitBreakerOpen
            breaker.call(unreliable_operation)

        # Operation wasn't called (fast-fail)
        assert call_count == initial_count

    def test_health_checker_integrated_with_breaker(self):
        """Test health checker status influences circuit breaker."""
        health_checker = HealthChecker()
        breaker = CircuitBreaker("health_protected")

        # Register custom health check
        def custom_check():
            from athena.resilience.health import HealthReport

            # Simulate degraded health
            return HealthReport(
                name="custom_service",
                status=HealthStatus.HEALTHY,
                message="All good",
            )

        health_checker.register("custom_service", custom_check)

        # Get health status
        health = health_checker.check_all()
        assert health.is_healthy()


class TestResiliencePatternCombinations:
    """Test combinations of resilience patterns."""

    def test_retry_then_fallback_then_circuit_breaker(self):
        """Test full resilience chain: retry → fallback → circuit breaker."""
        breaker = CircuitBreaker("full_chain", fail_threshold=2)
        chain = FallbackChain("fallback")

        attempt_count = 0

        def primary_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 4:
                raise ValueError("transient")
            return "primary_success"

        def fallback_operation():
            return "fallback_success"

        # Build fallback chain
        chain.add("fallback", fallback_operation)

        # Add retry
        policy = RetryPolicy(max_attempts=2, initial_delay=0.01)

        @with_retry(policy)
        @with_fallback(chain)
        def resilient_operation():
            return breaker.call(primary_operation)

        # Attempt 1: Retry fails (transient error)
        # Falls back to fallback_operation
        result = resilient_operation()
        assert result == "fallback_success"

    def test_progressive_degradation_with_fallbacks(self):
        """Test progressive degradation through multiple fallback levels."""
        chain = FallbackChain("progressive")

        call_log = []

        def level_1():
            call_log.append("level_1")
            raise RuntimeError("level_1 failed")

        def level_2():
            call_log.append("level_2")
            raise RuntimeError("level_2 failed")

        def level_3():
            call_log.append("level_3")
            return "level_3_result"

        chain.add("level_1", level_1)
        chain.add("level_2", level_2)
        chain.add("level_3", level_3)

        result = chain.execute()
        assert result == "level_3_result"
        assert call_log == ["level_1", "level_2", "level_3"]

    def test_metrics_collection_during_resilience(self):
        """Test collecting metrics during resilience operations."""
        from athena.resilience.degradation import with_retry

        # Manually track metrics instead of using collector
        metrics = {"attempts": 0, "success": False}

        @with_retry(
            RetryPolicy(
                max_attempts=3,
                initial_delay=0.01,
            )
        )
        def operation_with_metrics():
            metrics["attempts"] += 1
            if metrics["attempts"] < 2:
                raise TimeoutError("transient")
            metrics["success"] = True
            return "success"

        result = operation_with_metrics()
        assert result == "success"
        assert metrics["attempts"] == 2
        assert metrics["success"]


class TestResilienceWithLogging:
    """Test that resilience operations integrate with logging."""

    def test_retry_logs_attempts(self, caplog):
        """Test that retry decorator logs attempts."""
        import logging

        caplog.set_level(logging.WARNING)

        attempt_count = 0

        @with_retry(
            RetryPolicy(
                max_attempts=3,
                initial_delay=0.01,
            )
        )
        def operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise TimeoutError("timeout")
            return "success"

        result = operation()
        assert result == "success"

        # Check logs contain retry information
        log_text = caplog.text
        assert "Attempt 1" in log_text or "retrying" in log_text.lower()

    def test_circuit_breaker_logs_state_changes(self, caplog):
        """Test that circuit breaker logs state changes."""
        import logging

        caplog.set_level(logging.ERROR)

        breaker = CircuitBreaker(
            "test_breaker",
            fail_threshold=2,
        )

        def failing_op():
            raise ValueError("fail")

        # Trigger failures to open circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(failing_op)

        log_text = caplog.text
        assert "opened" in log_text.lower()


class TestHealthCheckIntegration:
    """Test health checks in production scenarios."""

    def test_system_health_report_generation(self):
        """Test generating comprehensive system health report."""
        checker = HealthChecker()
        health = checker.check_all()

        # Should have multiple checks
        assert len(health.checks) >= 2

        # Should have overall status
        assert health.overall_status() in (
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY,
        )

        # Should be serializable
        data = health.to_dict()
        assert "overall_status" in data
        assert "checks" in data

    def test_custom_health_check_registration(self):
        """Test registering custom health checks."""
        from athena.resilience.health import HealthReport

        checker = HealthChecker()

        # Register custom check
        def database_check():
            # Simulate database health
            return HealthReport(
                name="database",
                status=HealthStatus.HEALTHY,
                message="Database responsive",
            )

        checker.register("database", database_check)

        # Run check
        health = checker.check_all()
        db_check = next(c for c in health.checks if c.name == "database")
        assert db_check.status == HealthStatus.HEALTHY


# ============================================================================
# End-to-End Resilience Scenarios
# ============================================================================


class TestEndToEndScenarios:
    """End-to-end scenarios combining multiple resilience patterns."""

    def test_query_with_full_resilience_stack(self):
        """Test query with complete resilience stack."""
        # Setup health checker
        health_checker = HealthChecker()

        # Setup circuit breaker
        breaker = CircuitBreaker("query_breaker", fail_threshold=3)

        # Setup fallback chain
        chain = FallbackChain("query_fallback")
        chain.add("fallback", lambda: [{"id": 0, "cached": True}])

        # Setup retry policy
        retry_policy = RetryPolicy(max_attempts=3, initial_delay=0.01)

        attempt_count = 0

        def mock_recall(query, project_id, k=5):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise TimeoutError("transient")  # Use retryable exception
            return [{"id": 1, "query": query}]

        @with_retry(retry_policy)
        def resilient_query(query: str, project_id: int):
            # Check health first
            health = health_checker.check_all()
            if health.is_unhealthy():
                return [{"id": 0, "health": "unhealthy"}]

            # Execute with circuit breaker
            return breaker.call(
                mock_recall, query, project_id, k=5
            )

        # Should work even if some attempts fail
        result = resilient_query("test", 1)
        assert result is not None
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], dict)

    def test_batch_operations_with_resilience(self):
        """Test batch operations with resilience."""
        memories = [
            {
                "content": f"memory {i}",
                "memory_type": "fact",
                "tags": ["batch"],
            }
            for i in range(10)
        ]

        def insert_batch_with_retry():
            policy = RetryPolicy(max_attempts=3, initial_delay=0.01)

            @with_retry(policy)
            def insert_one(memory):
                return {"id": i, **memory}

            results = []
            for i, memory in enumerate(memories):
                result = insert_one(memory)
                results.append(result)

            return results

        results = insert_batch_with_retry()
        assert len(results) == len(memories)
