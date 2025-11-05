"""Resilience & Error Handling Infrastructure.

Provides retry logic, circuit breakers, graceful degradation, and health checking
for production-ready error handling and recovery.
"""

from .degradation import (
    RetryPolicy,
    FallbackChain,
    FallbackHandler,
    with_retry,
    with_fallback,
)
from .health import (
    HealthStatus,
    HealthReport,
    HealthChecker,
    SystemHealth,
)

__all__ = [
    "RetryPolicy",
    "FallbackChain",
    "FallbackHandler",
    "with_retry",
    "with_fallback",
    "HealthStatus",
    "HealthReport",
    "HealthChecker",
    "SystemHealth",
]
