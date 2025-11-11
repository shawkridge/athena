"""Graceful Degradation: Retry Logic & Fallback Chains.

Implements retry policies with exponential backoff, fallback chains,
and circuit breaker-like patterns for resilient operations.
"""

import time
import logging
from typing import Any, Callable, List, Optional, TypeVar, Union
from dataclasses import dataclass
from enum import Enum
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryStrategy(Enum):
    """Retry backoff strategies."""

    IMMEDIATE = "immediate"  # No delay
    LINEAR = "linear"  # delay = attempt * multiplier
    EXPONENTIAL = "exponential"  # delay = multiplier ** attempt
    FIBONACCI = "fibonacci"  # delay = fibonacci(attempt) * multiplier


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    initial_delay: float = 0.1  # seconds
    max_delay: float = 10.0  # seconds
    multiplier: float = 2.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    retryable_exceptions: tuple = (
        sqlite3.OperationalError,
        TimeoutError,
        ConnectionError,
    )
    jitter: bool = True  # Add random jitter to delays

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        if self.strategy == RetryStrategy.IMMEDIATE:
            return 0.0
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.initial_delay + (attempt * self.multiplier)
        elif self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.initial_delay * (self.multiplier ** attempt)
        elif self.strategy == RetryStrategy.FIBONACCI:
            delay = self.initial_delay * self._fibonacci(attempt)
        else:
            delay = self.initial_delay

        # Cap at max delay
        delay = min(delay, self.max_delay)

        # Add jitter (±20%)
        if self.jitter:
            jitter_amount = delay * 0.2
            import random

            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0.0, delay)

    @staticmethod
    def _fibonacci(n: int) -> int:
        """Get nth Fibonacci number."""
        if n <= 1:
            return 1
        a, b = 1, 1
        for _ in range(n - 1):
            a, b = b, a + b
        return b

    def is_retryable(self, exception: Exception) -> bool:
        """Check if exception should trigger retry."""
        return isinstance(exception, self.retryable_exceptions)


@dataclass
class FallbackHandler:
    """Single fallback operation."""

    name: str
    operation: Callable[..., T]
    on_exception: Optional[Callable[[Exception], bool]] = None

    def can_handle(self, exception: Exception) -> bool:
        """Check if this handler should run for this exception."""
        if self.on_exception is None:
            return True
        return self.on_exception(exception)

    def execute(self, *args, **kwargs) -> T:
        """Execute fallback operation."""
        return self.operation(*args, **kwargs)


class FallbackChain:
    """Manages chain of fallback operations."""

    def __init__(self, name: str):
        """Initialize fallback chain."""
        self.name = name
        self.handlers: List[FallbackHandler] = []

    def add(
        self,
        name: str,
        operation: Callable[..., T],
        on_exception: Optional[Callable[[Exception], bool]] = None,
    ) -> "FallbackChain":
        """Add fallback handler to chain."""
        handler = FallbackHandler(name=name, operation=operation, on_exception=on_exception)
        self.handlers.append(handler)
        return self

    def execute(self, *args, **kwargs) -> Optional[T]:
        """Execute chain of fallbacks, return first success."""
        last_exception = None

        for handler in self.handlers:
            try:
                logger.info(f"Trying fallback: {handler.name}")
                result = handler.execute(*args, **kwargs)
                logger.info(f"Fallback succeeded: {handler.name}")
                return result
            except Exception as e:
                last_exception = e
                if not handler.can_handle(e):
                    # This handler doesn't handle this exception type
                    raise
                logger.warning(
                    f"Fallback failed",
                    extra={
                        "fallback": handler.name,
                        "error": str(e),
                        "chain": self.name,
                    },
                )

        # All fallbacks exhausted
        logger.error(
            f"All fallbacks exhausted for {self.name}",
            extra={"last_error": str(last_exception)},
        )
        return None


def with_retry(
    policy: Optional[RetryPolicy] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator: Retry operation with exponential backoff.

    Args:
        policy: RetryPolicy configuration (uses defaults if None)

    Example:
        @with_retry(RetryPolicy(max_attempts=3))
        def my_operation():
            # Will retry up to 3 times with exponential backoff
            ...
    """
    if policy is None:
        policy = RetryPolicy()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(policy.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if not policy.is_retryable(e):
                        # Non-retryable exception, fail immediately
                        logger.error(
                            f"Non-retryable exception in {func.__name__}",
                            exc_info=True,
                        )
                        raise

                    if attempt < policy.max_attempts - 1:
                        delay = policy.get_delay(attempt)
                        logger.warning(
                            f"Attempt {attempt + 1}/{policy.max_attempts} failed, "
                            f"retrying in {delay:.2f}s",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "delay_seconds": delay,
                                "error": str(e),
                            },
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {policy.max_attempts} retry attempts exhausted",
                            extra={
                                "function": func.__name__,
                                "error": str(last_exception),
                            },
                            exc_info=True,
                        )

            raise last_exception

        return wrapper

    return decorator


def with_fallback(
    fallback_chain: FallbackChain,
) -> Callable[[Callable[..., T]], Callable[..., Optional[T]]]:
    """Decorator: Use fallback chain on operation failure.

    Args:
        fallback_chain: FallbackChain with fallback handlers

    Example:
        chain = FallbackChain("my_chain")
        chain.add("simple_method", simple_func)
        chain.add("empty_result", lambda: [])

        @with_fallback(chain)
        def my_operation():
            # Will use fallback chain on failure
            ...
    """

    def decorator(
        func: Callable[..., T],
    ) -> Callable[..., Optional[T]]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Optional[T]:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    f"Operation {func.__name__} failed, trying fallback chain",
                    extra={"error": str(e), "chain": fallback_chain.name},
                )
                return fallback_chain.execute(*args, **kwargs)

        return wrapper

    return decorator


class CircuitBreaker:
    """Circuit breaker pattern for failing operations.

    States:
    - CLOSED: Normal operation, attempts continue
    - OPEN: Operation is failing, fast-fail without attempting
    - HALF_OPEN: Testing if operation recovered
    """

    class State(Enum):
        CLOSED = "closed"
        OPEN = "open"
        HALF_OPEN = "half_open"

    def __init__(
        self,
        name: str,
        fail_threshold: int = 5,
        success_threshold: int = 2,
        timeout: float = 60.0,
    ):
        """Initialize circuit breaker.

        Args:
            name: Circuit breaker identifier
            fail_threshold: Failures before opening circuit
            success_threshold: Successes (in HALF_OPEN) to close circuit
            timeout: Seconds before attempting half-open
        """
        self.name = name
        self.fail_threshold = fail_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout

        self.state = self.State.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args, **kwargs: Arguments for function

        Returns:
            Function result

        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: Any exception from func
        """
        if self.state == self.State.OPEN:
            if self._should_attempt_reset():
                self.state = self.State.HALF_OPEN
                self.success_count = 0
                logger.info(
                    f"Circuit {self.name} entering HALF_OPEN state",
                )
            else:
                raise CircuitBreakerOpen(
                    f"Circuit {self.name} is OPEN, failing fast"
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time passed to attempt reset."""
        if self.last_failure_time is None:
            return False
        return (time.time() - self.last_failure_time) >= self.timeout

    def _on_success(self) -> None:
        """Handle successful operation."""
        self.failure_count = 0

        if self.state == self.State.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = self.State.CLOSED
                logger.info(
                    f"Circuit {self.name} CLOSED after recovery",
                )

    def _on_failure(self) -> None:
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == self.State.HALF_OPEN:
            # Failure during recovery test, reopen
            self.state = self.State.OPEN
            logger.warning(
                f"Circuit {self.name} reopened after recovery test failed",
            )
        elif self.failure_count >= self.fail_threshold:
            self.state = self.State.OPEN
            logger.error(
                f"Circuit {self.name} opened after {self.failure_count} failures",
            )


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""

    pass
