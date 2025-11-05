"""Circuit breaker pattern for error recovery and source health monitoring."""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit opened, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    source: str
    failure_threshold: int = 5  # Failures before opening circuit
    success_threshold: int = 2  # Successes before closing circuit (from half-open)
    timeout_seconds: int = 60  # Time before attempting half-open


class CircuitBreaker:
    """Circuit breaker for handling source failures gracefully."""

    def __init__(self, config: CircuitBreakerConfig):
        """Initialize circuit breaker.

        Args:
            config: Circuit breaker configuration
        """
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.opened_at: Optional[float] = None

    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_recovery():
                logger.info(f"Circuit breaker {self.config.source}: Entering HALF_OPEN state")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                raise Exception(
                    f"Circuit breaker OPEN for {self.config.source}. "
                    f"Retry after {self._time_until_retry():.1f}s"
                )

        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise

    def on_success(self):
        """Record successful call."""
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                logger.info(f"Circuit breaker {self.config.source}: Closing (recovered)")
                self.state = CircuitState.CLOSED
                self.success_count = 0
                self.opened_at = None

    def on_failure(self):
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit breaker {self.config.source}: Reopening (recovery failed)")
            self.state = CircuitState.OPEN
            self.opened_at = time.time()
            self.success_count = 0
        elif self.failure_count >= self.config.failure_threshold:
            logger.warning(
                f"Circuit breaker {self.config.source}: Opening "
                f"({self.failure_count} failures)"
            )
            self.state = CircuitState.OPEN
            self.opened_at = time.time()

    def _should_attempt_recovery(self) -> bool:
        """Check if circuit should attempt recovery from open state."""
        if self.opened_at is None:
            return False

        elapsed = time.time() - self.opened_at
        return elapsed >= self.config.timeout_seconds

    def _time_until_retry(self) -> float:
        """Get time until circuit can retry."""
        if self.opened_at is None:
            return 0.0

        elapsed = time.time() - self.opened_at
        remaining = self.config.timeout_seconds - elapsed
        return max(0.0, remaining)

    def get_status(self) -> dict:
        """Get circuit breaker status.

        Returns:
            Status dict
        """
        return {
            "source": self.config.source,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "opened_at": self.opened_at,
            "time_until_retry_seconds": self._time_until_retry(),
        }


class CircuitBreakerManager:
    """Manages circuit breakers for multiple sources."""

    def __init__(self):
        """Initialize circuit breaker manager."""
        self.breakers: dict[str, CircuitBreaker] = {}

    def get_breaker(self, source: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get or create circuit breaker for source.

        Args:
            source: Source name
            config: Optional custom configuration

        Returns:
            Circuit breaker
        """
        if source not in self.breakers:
            if config is None:
                config = CircuitBreakerConfig(source)
            self.breakers[source] = CircuitBreaker(config)

        return self.breakers[source]

    def reset_breaker(self, source: str):
        """Reset circuit breaker to closed state.

        Args:
            source: Source name
        """
        if source in self.breakers:
            self.breakers[source].state = CircuitState.CLOSED
            self.breakers[source].failure_count = 0
            self.breakers[source].success_count = 0
            self.breakers[source].opened_at = None
            logger.info(f"Circuit breaker reset for {source}")

    def get_all_status(self) -> dict[str, dict]:
        """Get status of all circuit breakers.

        Returns:
            Dict mapping source to status
        """
        return {source: breaker.get_status() for source, breaker in self.breakers.items()}

    def get_healthy_sources(self) -> list[str]:
        """Get list of healthy sources.

        Returns:
            List of sources not in OPEN state
        """
        return [
            source
            for source, breaker in self.breakers.items()
            if breaker.state != CircuitState.OPEN
        ]

    def get_failing_sources(self) -> list[str]:
        """Get list of failing sources.

        Returns:
            List of sources in OPEN state
        """
        return [
            source
            for source, breaker in self.breakers.items()
            if breaker.state == CircuitState.OPEN
        ]
