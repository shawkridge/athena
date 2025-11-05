"""Tests for resilience & error handling infrastructure.

Tests retry policies, fallback chains, circuit breakers, and health checks.
"""

import pytest
import time
import sqlite3
from unittest.mock import Mock, patch
from datetime import datetime

from athena.resilience.degradation import (
    RetryPolicy,
    RetryStrategy,
    FallbackHandler,
    FallbackChain,
    with_retry,
    with_fallback,
    CircuitBreaker,
    CircuitBreakerOpen,
)
from athena.resilience.health import (
    HealthStatus,
    HealthReport,
    HealthChecker,
    SystemHealth,
)


# ============================================================================
# RetryPolicy Tests
# ============================================================================


class TestRetryPolicy:
    """Test RetryPolicy configuration and delay calculation."""

    def test_create_default_policy(self):
        """Test creating policy with defaults."""
        policy = RetryPolicy()
        assert policy.max_attempts == 3
        assert policy.initial_delay == 0.1
        assert policy.max_delay == 10.0
        assert policy.strategy == RetryStrategy.EXPONENTIAL

    def test_immediate_strategy(self):
        """Test IMMEDIATE retry strategy."""
        policy = RetryPolicy(strategy=RetryStrategy.IMMEDIATE)
        assert policy.get_delay(0) == 0.0
        assert policy.get_delay(1) == 0.0
        assert policy.get_delay(10) == 0.0

    def test_linear_strategy(self):
        """Test LINEAR retry strategy."""
        policy = RetryPolicy(
            strategy=RetryStrategy.LINEAR,
            initial_delay=1.0,
            multiplier=2.0,
            jitter=False,
        )
        assert policy.get_delay(0) == 1.0  # 1.0 + 0*2.0
        assert policy.get_delay(1) == 3.0  # 1.0 + 1*2.0
        assert policy.get_delay(2) == 5.0  # 1.0 + 2*2.0

    def test_exponential_strategy(self):
        """Test EXPONENTIAL retry strategy."""
        policy = RetryPolicy(
            strategy=RetryStrategy.EXPONENTIAL,
            initial_delay=1.0,
            multiplier=2.0,
            jitter=False,
        )
        assert policy.get_delay(0) == 1.0  # 1.0 * 2^0
        assert policy.get_delay(1) == 2.0  # 1.0 * 2^1
        assert policy.get_delay(2) == 4.0  # 1.0 * 2^2

    def test_fibonacci_strategy(self):
        """Test FIBONACCI retry strategy."""
        policy = RetryPolicy(
            strategy=RetryStrategy.FIBONACCI,
            initial_delay=1.0,
            multiplier=1.0,
            jitter=False,
        )
        # Fibonacci: 1, 1, 2, 3, 5, 8, ...
        delays = [policy.get_delay(i) for i in range(6)]
        assert delays[0] == 1.0  # fib(0) = 1
        assert delays[1] == 1.0  # fib(1) = 1
        assert delays[2] == 2.0  # fib(2) = 2
        assert delays[3] == 3.0  # fib(3) = 3
        assert delays[4] == 5.0  # fib(4) = 5

    def test_max_delay_cap(self):
        """Test that delays are capped at max_delay."""
        policy = RetryPolicy(
            strategy=RetryStrategy.EXPONENTIAL,
            initial_delay=1.0,
            multiplier=2.0,
            max_delay=5.0,
            jitter=False,
        )
        assert policy.get_delay(5) <= 5.0

    def test_jitter_adds_variation(self):
        """Test that jitter adds randomness to delays."""
        policy = RetryPolicy(jitter=True, initial_delay=10.0)
        delays = [policy.get_delay(1) for _ in range(10)]
        # Should have variation
        assert len(set(delays)) > 1

    def test_is_retryable_default_exceptions(self):
        """Test retryability of default exceptions."""
        policy = RetryPolicy()
        assert policy.is_retryable(sqlite3.OperationalError())
        assert policy.is_retryable(TimeoutError())
        assert policy.is_retryable(ConnectionError())
        assert not policy.is_retryable(ValueError())

    def test_custom_retryable_exceptions(self):
        """Test custom retryable exception types."""
        policy = RetryPolicy(retryable_exceptions=(ValueError, TypeError))
        assert policy.is_retryable(ValueError())
        assert policy.is_retryable(TypeError())
        assert not policy.is_retryable(sqlite3.OperationalError())


# ============================================================================
# Retry Decorator Tests
# ============================================================================


class TestRetryDecorator:
    """Test @with_retry decorator."""

    def test_success_on_first_attempt(self):
        """Test successful operation on first attempt."""
        mock_func = Mock(return_value="success")
        policy = RetryPolicy(max_attempts=3)

        @with_retry(policy)
        def my_operation():
            return mock_func()

        result = my_operation()
        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_on_retryable_exception(self):
        """Test retry on retryable exception."""
        mock_func = Mock(side_effect=[TimeoutError(), TimeoutError(), "success"])
        policy = RetryPolicy(
            max_attempts=3,
            initial_delay=0.01,
            retryable_exceptions=(TimeoutError,),
        )

        @with_retry(policy)
        def my_operation():
            return mock_func()

        result = my_operation()
        assert result == "success"
        assert mock_func.call_count == 3

    def test_no_retry_on_non_retryable_exception(self):
        """Test that non-retryable exceptions fail immediately."""
        mock_func = Mock(side_effect=ValueError("not retryable"))
        policy = RetryPolicy(retryable_exceptions=(TimeoutError,))

        @with_retry(policy)
        def my_operation():
            return mock_func()

        with pytest.raises(ValueError):
            my_operation()

        assert mock_func.call_count == 1

    def test_exhausts_retry_attempts(self):
        """Test that decorator fails after max attempts."""
        mock_func = Mock(side_effect=TimeoutError("always fails"))
        policy = RetryPolicy(
            max_attempts=3,
            initial_delay=0.01,
            retryable_exceptions=(TimeoutError,),
        )

        @with_retry(policy)
        def my_operation():
            return mock_func()

        with pytest.raises(TimeoutError):
            my_operation()

        assert mock_func.call_count == 3

    def test_default_policy(self):
        """Test retry with default policy."""
        attempt_count = 0

        @with_retry()
        def my_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise sqlite3.OperationalError()
            return "success"

        result = my_operation()
        assert result == "success"
        assert attempt_count == 2


# ============================================================================
# Fallback Chain Tests
# ============================================================================


class TestFallbackChain:
    """Test FallbackChain and fallback handler logic."""

    def test_create_chain(self):
        """Test creating fallback chain."""
        chain = FallbackChain("my_chain")
        assert chain.name == "my_chain"
        assert len(chain.handlers) == 0

    def test_add_handler(self):
        """Test adding handlers to chain."""
        chain = FallbackChain("my_chain")
        chain.add("handler1", lambda: "result1")
        chain.add("handler2", lambda: "result2")
        assert len(chain.handlers) == 2

    def test_execute_first_succeeds(self):
        """Test that first successful handler is used."""
        chain = FallbackChain("my_chain")
        chain.add("primary", lambda: "primary_result")
        chain.add("fallback", lambda: "fallback_result")

        result = chain.execute()
        assert result == "primary_result"

    def test_fallback_on_failure(self):
        """Test fallback is used when primary fails."""
        chain = FallbackChain("my_chain")
        chain.add("primary", Mock(side_effect=ValueError()))
        chain.add("fallback", lambda: "fallback_result")

        result = chain.execute()
        assert result == "fallback_result"

    def test_multiple_fallbacks(self):
        """Test multiple fallback attempts."""
        chain = FallbackChain("my_chain")
        chain.add("primary", Mock(side_effect=ValueError()))
        chain.add("secondary", Mock(side_effect=RuntimeError()))
        chain.add("tertiary", lambda: "tertiary_result")

        result = chain.execute()
        assert result == "tertiary_result"

    def test_all_fallbacks_fail(self):
        """Test when all fallbacks fail."""
        chain = FallbackChain("my_chain")
        chain.add("primary", Mock(side_effect=ValueError()))
        chain.add("fallback", Mock(side_effect=RuntimeError()))

        result = chain.execute()
        assert result is None

    def test_conditional_exception_handler(self):
        """Test exception predicate for handler selection."""
        chain = FallbackChain("my_chain")

        def only_on_timeout(exc):
            return isinstance(exc, TimeoutError)

        chain.add("timeout_handler", lambda: "timeout_handled", only_on_timeout)

        # Should use handler for TimeoutError
        chain.add("primary", Mock(side_effect=TimeoutError()))
        result = chain.execute()
        assert result == "timeout_handled"

    def test_fallback_decorator(self):
        """Test @with_fallback decorator."""
        chain = FallbackChain("my_chain")
        chain.add("fallback", lambda: "fallback_result")

        @with_fallback(chain)
        def my_operation():
            raise ValueError("operation failed")

        result = my_operation()
        assert result == "fallback_result"


# ============================================================================
# Circuit Breaker Tests
# ============================================================================


class TestCircuitBreaker:
    """Test CircuitBreaker pattern."""

    def test_create_circuit_breaker(self):
        """Test creating circuit breaker."""
        breaker = CircuitBreaker("my_breaker")
        assert breaker.name == "my_breaker"
        assert breaker.state == CircuitBreaker.State.CLOSED

    def test_closed_allows_calls(self):
        """Test that CLOSED state allows calls."""
        breaker = CircuitBreaker("my_breaker")
        mock_func = Mock(return_value="success")

        result = breaker.call(mock_func)
        assert result == "success"
        assert mock_func.call_count == 1

    def test_open_after_failures(self):
        """Test circuit opens after threshold failures."""
        breaker = CircuitBreaker("my_breaker", fail_threshold=3)
        mock_func = Mock(side_effect=ValueError())

        # Fail 3 times
        for _ in range(3):
            with pytest.raises(ValueError):
                breaker.call(mock_func)

        # Circuit should be open
        assert breaker.state == CircuitBreaker.State.OPEN

        # Next call should fail fast
        with pytest.raises(CircuitBreakerOpen):
            breaker.call(mock_func)

        # Function should not be called again (fast-fail)
        assert mock_func.call_count == 3

    def test_half_open_on_timeout(self):
        """Test circuit transitions to HALF_OPEN after timeout."""
        breaker = CircuitBreaker(
            "my_breaker", fail_threshold=1, timeout=0.05
        )
        mock_func = Mock(side_effect=ValueError())

        # Open circuit
        with pytest.raises(ValueError):
            breaker.call(mock_func)

        assert breaker.state == CircuitBreaker.State.OPEN

        # Wait for timeout
        time.sleep(0.1)

        # Next call should attempt to reset (HALF_OPEN) then fail
        mock_func.reset_mock()
        mock_func.side_effect = ValueError()

        with pytest.raises(ValueError):
            breaker.call(mock_func)

        # After attempting in HALF_OPEN and failing, reopen
        assert breaker.state == CircuitBreaker.State.OPEN

    def test_half_open_closes_on_success(self):
        """Test circuit closes after successful recovery."""
        breaker = CircuitBreaker(
            "my_breaker",
            fail_threshold=1,
            success_threshold=2,
            timeout=0.1,
        )
        mock_func = Mock(side_effect=ValueError())

        # Open circuit
        with pytest.raises(ValueError):
            breaker.call(mock_func)

        # Wait for timeout
        time.sleep(0.15)

        # Success in HALF_OPEN transitions to CLOSED
        mock_func.side_effect = None
        mock_func.return_value = "success"

        breaker.call(mock_func)  # 1st success
        assert breaker.state == CircuitBreaker.State.HALF_OPEN

        breaker.call(mock_func)  # 2nd success - triggers close
        assert breaker.state == CircuitBreaker.State.CLOSED

    def test_half_open_reopens_on_failure(self):
        """Test circuit reopens on failure during recovery."""
        breaker = CircuitBreaker(
            "my_breaker",
            fail_threshold=1,
            success_threshold=2,
            timeout=0.1,
        )
        mock_func = Mock(side_effect=ValueError())

        # Open circuit
        with pytest.raises(ValueError):
            breaker.call(mock_func)

        # Wait for timeout to enter HALF_OPEN
        time.sleep(0.15)

        # Failure during recovery reopens
        with pytest.raises(ValueError):
            breaker.call(mock_func)

        assert breaker.state == CircuitBreaker.State.OPEN


# ============================================================================
# Health Check Tests
# ============================================================================


class TestHealthStatus:
    """Test HealthStatus enum."""

    def test_status_comparison(self):
        """Test comparing health statuses."""
        assert HealthStatus.UNHEALTHY < HealthStatus.DEGRADED
        assert HealthStatus.DEGRADED < HealthStatus.HEALTHY
        assert HealthStatus.HEALTHY > HealthStatus.DEGRADED

    def test_is_ok(self):
        """Test is_ok() method."""
        assert HealthStatus.HEALTHY.is_ok()
        assert HealthStatus.DEGRADED.is_ok()
        assert not HealthStatus.UNHEALTHY.is_ok()


class TestHealthReport:
    """Test HealthReport dataclass."""

    def test_create_report(self):
        """Test creating health report."""
        report = HealthReport(
            name="test_check",
            status=HealthStatus.HEALTHY,
            message="All good",
        )
        assert report.name == "test_check"
        assert report.status == HealthStatus.HEALTHY

    def test_to_dict(self):
        """Test converting report to dictionary."""
        report = HealthReport(
            name="test_check",
            status=HealthStatus.HEALTHY,
            message="All good",
            details={"key": "value"},
        )
        data = report.to_dict()
        assert data["name"] == "test_check"
        assert data["status"] == "healthy"
        assert data["details"]["key"] == "value"


class TestSystemHealth:
    """Test SystemHealth aggregate."""

    def test_create_system_health(self):
        """Test creating system health."""
        health = SystemHealth()
        assert len(health.checks) == 0

    def test_overall_status_empty(self):
        """Test overall status with no checks."""
        health = SystemHealth()
        assert health.overall_status() == HealthStatus.HEALTHY

    def test_overall_status_all_healthy(self):
        """Test overall status with all healthy checks."""
        health = SystemHealth()
        health.checks.append(
            HealthReport("check1", HealthStatus.HEALTHY)
        )
        health.checks.append(
            HealthReport("check2", HealthStatus.HEALTHY)
        )
        assert health.overall_status() == HealthStatus.HEALTHY

    def test_overall_status_worst_wins(self):
        """Test that worst status is reported."""
        health = SystemHealth()
        health.checks.append(
            HealthReport("check1", HealthStatus.HEALTHY)
        )
        health.checks.append(
            HealthReport("check2", HealthStatus.DEGRADED)
        )
        health.checks.append(
            HealthReport("check3", HealthStatus.UNHEALTHY)
        )
        assert health.overall_status() == HealthStatus.UNHEALTHY

    def test_is_methods(self):
        """Test is_healthy, is_degraded, is_unhealthy methods."""
        health1 = SystemHealth(
            checks=[
                HealthReport("check", HealthStatus.HEALTHY)
            ]
        )
        assert health1.is_healthy()
        assert not health1.is_degraded()
        assert not health1.is_unhealthy()

        health2 = SystemHealth(
            checks=[
                HealthReport("check", HealthStatus.DEGRADED)
            ]
        )
        assert not health2.is_healthy()
        assert health2.is_degraded()
        assert not health2.is_unhealthy()

        health3 = SystemHealth(
            checks=[
                HealthReport("check", HealthStatus.UNHEALTHY)
            ]
        )
        assert not health3.is_healthy()
        assert not health3.is_degraded()
        assert health3.is_unhealthy()


class TestHealthChecker:
    """Test HealthChecker with custom checks."""

    def test_create_checker(self):
        """Test creating health checker."""
        checker = HealthChecker()
        assert len(checker.checks) > 0  # Has default checks

    def test_register_custom_check(self):
        """Test registering custom check."""
        checker = HealthChecker()
        initial_count = len(checker.checks)

        def custom_check():
            return HealthReport("custom", HealthStatus.HEALTHY)

        checker.register("custom_check", custom_check)
        assert len(checker.checks) == initial_count + 1
        assert "custom_check" in checker.checks

    def test_check_single(self):
        """Test running single check."""
        checker = HealthChecker()

        def test_check():
            return HealthReport(
                "test", HealthStatus.HEALTHY, "test message"
            )

        checker.register("test", test_check)
        report = checker.check("test")
        assert report.name == "test"
        assert report.status == HealthStatus.HEALTHY

    def test_check_not_found(self):
        """Test checking non-existent check."""
        checker = HealthChecker()
        with pytest.raises(ValueError, match="not found"):
            checker.check("nonexistent")

    def test_check_all(self):
        """Test running all checks."""
        checker = HealthChecker()
        system_health = checker.check_all()
        assert len(system_health.checks) > 0

    def test_get_summary(self):
        """Test getting health summary."""
        checker = HealthChecker()
        summary = checker.get_summary()
        assert "overall_status" in summary
        assert "is_healthy" in summary
        assert "checks_passed" in summary


# ============================================================================
# Integration Tests
# ============================================================================


class TestResilienceIntegration:
    """Integration tests combining multiple resilience patterns."""

    def test_retry_with_circuit_breaker(self):
        """Test retry logic with circuit breaker."""
        breaker = CircuitBreaker("test", fail_threshold=2, timeout=0.1)
        attempt_count = 0

        def flaky_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 4:
                raise ValueError("flaky")
            return "success"

        policy = RetryPolicy(max_attempts=3, initial_delay=0.01)

        @with_retry(policy)
        def protected_operation():
            return breaker.call(flaky_operation)

        # First call: 3 failures, circuit opens
        with pytest.raises((ValueError, CircuitBreakerOpen)):
            protected_operation()

    def test_fallback_after_retry(self):
        """Test fallback chain after retry exhaustion."""
        chain = FallbackChain("fallback")
        chain.add("fallback", lambda: "fallback_result")

        policy = RetryPolicy(max_attempts=2, initial_delay=0.01)

        @with_retry(policy)
        @with_fallback(chain)
        def operation():
            raise ValueError("always fails")

        result = operation()
        assert result == "fallback_result"
