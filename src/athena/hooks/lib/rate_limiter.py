"""Rate Limiter for Hook Safety.

Prevents hook execution storms by:
- Limiting executions per time window (token bucket)
- Throttling rapid-fire triggers
- Allowing burst capacity with sustained rate control
"""

import logging
import time
from typing import Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class TokenBucket:
    """Token bucket for rate limiting.

    Tracks available tokens for hook execution.
    Tokens regenerate at fixed rate (replenish_rate).
    """
    max_tokens: float
    current_tokens: float
    replenish_rate: float  # tokens per second
    last_refill: float = 0.0


class RateLimiter:
    """Rate limit hook executions using token bucket algorithm.

    Provides:
    - Per-hook rate limiting
    - Global rate limiting
    - Burst capacity (allows temporary exceedance)
    - Adaptive throttling

    Attributes:
        max_executions_per_second: Global rate limit
        burst_multiplier: Allows burst up to this multiple of sustained rate
    """

    def __init__(
        self,
        max_executions_per_second: float = 10.0,
        burst_multiplier: float = 2.0,
        enforcement_window_seconds: float = 60.0
    ):
        """Initialize rate limiter.

        Args:
            max_executions_per_second: Global sustained rate (default 10/sec)
            burst_multiplier: Burst capacity as multiple of sustained (default 2x)
            enforcement_window_seconds: Time window for rate calculation
        """
        self.max_executions_per_second = max_executions_per_second
        self.burst_multiplier = burst_multiplier
        self.enforcement_window_seconds = enforcement_window_seconds

        # Token bucket for global rate limit
        burst_capacity = max_executions_per_second * burst_multiplier
        self._global_bucket = TokenBucket(
            max_tokens=burst_capacity,
            current_tokens=burst_capacity,
            replenish_rate=max_executions_per_second,
            last_refill=time.time()
        )

        # Per-hook rate limiters
        self._per_hook_limiters: Dict[str, TokenBucket] = {}
        self._hook_rate_limits: Dict[str, float] = {}  # hook_id -> max_executions_per_sec

        self.logger = logging.getLogger(__name__)

    def _refill_bucket(self, bucket: TokenBucket) -> None:
        """Refill token bucket based on elapsed time.

        Args:
            bucket: Token bucket to refill
        """
        now = time.time()
        time_elapsed = now - bucket.last_refill
        tokens_to_add = time_elapsed * bucket.replenish_rate

        bucket.current_tokens = min(bucket.max_tokens, bucket.current_tokens + tokens_to_add)
        bucket.last_refill = now

    def set_hook_rate_limit(self, hook_id: str, rate: float) -> None:
        """Set custom rate limit for specific hook.

        Args:
            hook_id: Hook identifier
            rate: Maximum executions per second for this hook
        """
        burst_capacity = rate * self.burst_multiplier
        self._per_hook_limiters[hook_id] = TokenBucket(
            max_tokens=burst_capacity,
            current_tokens=burst_capacity,
            replenish_rate=rate,
            last_refill=time.time()
        )
        self._hook_rate_limits[hook_id] = rate
        self.logger.debug(f"Set rate limit for {hook_id}: {rate:.1f} executions/sec")

    def allow_execution(self, hook_id: str) -> bool:
        """Check if hook execution is allowed by rate limit.

        Uses token bucket algorithm:
        - Each execution requires 1 token
        - Tokens replenish at configured rate
        - Burst capacity allows temporary exceedance

        Args:
            hook_id: Hook identifier

        Returns:
            True if execution allowed, False if rate limit exceeded
        """
        # Check global rate limit
        self._refill_bucket(self._global_bucket)
        if self._global_bucket.current_tokens < 1.0:
            self.logger.warning(
                f"Global rate limit exceeded for {hook_id} "
                f"(tokens: {self._global_bucket.current_tokens:.2f})"
            )
            return False

        # Check per-hook rate limit if set
        if hook_id in self._per_hook_limiters:
            bucket = self._per_hook_limiters[hook_id]
            self._refill_bucket(bucket)

            if bucket.current_tokens < 1.0:
                self.logger.warning(
                    f"Per-hook rate limit exceeded for {hook_id} "
                    f"(tokens: {bucket.current_tokens:.2f})"
                )
                return False

            # Consume token from per-hook bucket
            bucket.current_tokens -= 1.0

        # Consume token from global bucket
        self._global_bucket.current_tokens -= 1.0
        return True

    def get_estimated_wait_time(self, hook_id: str) -> float:
        """Get estimated time to wait before hook can execute.

        Args:
            hook_id: Hook identifier

        Returns:
            Seconds to wait, or 0 if can execute immediately
        """
        self._refill_bucket(self._global_bucket)

        if self._global_bucket.current_tokens < 1.0:
            # Wait for 1 token to replenish
            tokens_needed = 1.0 - self._global_bucket.current_tokens
            wait_time = tokens_needed / self._global_bucket.replenish_rate
            return max(0, wait_time)

        if hook_id in self._per_hook_limiters:
            bucket = self._per_hook_limiters[hook_id]
            self._refill_bucket(bucket)

            if bucket.current_tokens < 1.0:
                tokens_needed = 1.0 - bucket.current_tokens
                wait_time = tokens_needed / bucket.replenish_rate
                return max(0, wait_time)

        return 0

    def reset_global_limit(self) -> None:
        """Reset global rate limit (refill tokens).

        Useful for testing or resetting after high load period.
        """
        burst_capacity = self.max_executions_per_second * self.burst_multiplier
        self._global_bucket.current_tokens = burst_capacity
        self._global_bucket.last_refill = time.time()
        self.logger.debug("Reset global rate limit")

    def reset_hook_limit(self, hook_id: str) -> None:
        """Reset rate limit for specific hook.

        Args:
            hook_id: Hook identifier
        """
        if hook_id in self._per_hook_limiters:
            bucket = self._per_hook_limiters[hook_id]
            bucket.current_tokens = bucket.max_tokens
            bucket.last_refill = time.time()
            self.logger.debug(f"Reset rate limit for {hook_id}")

    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics.

        Returns:
            Dictionary with current limits and token states
        """
        self._refill_bucket(self._global_bucket)

        per_hook_stats = {}
        for hook_id, bucket in self._per_hook_limiters.items():
            self._refill_bucket(bucket)
            per_hook_stats[hook_id] = {
                'current_tokens': round(bucket.current_tokens, 2),
                'max_tokens': bucket.max_tokens,
                'rate': self._hook_rate_limits.get(hook_id, 0),
            }

        return {
            'global_rate': self.max_executions_per_second,
            'burst_multiplier': self.burst_multiplier,
            'global_tokens': round(self._global_bucket.current_tokens, 2),
            'global_max_tokens': self._global_bucket.max_tokens,
            'per_hook_limits': per_hook_stats,
            'enforcement_window': self.enforcement_window_seconds
        }

    def get_hook_stats(self, hook_id: str) -> Dict[str, Any]:
        """Get rate limit stats for specific hook.

        Args:
            hook_id: Hook identifier

        Returns:
            Dictionary with hook-specific stats
        """
        if hook_id in self._per_hook_limiters:
            bucket = self._per_hook_limiters[hook_id]
            self._refill_bucket(bucket)
            return {
                'hook_id': hook_id,
                'current_tokens': round(bucket.current_tokens, 2),
                'max_tokens': bucket.max_tokens,
                'rate_limit': self._hook_rate_limits.get(hook_id),
            }

        return {
            'hook_id': hook_id,
            'message': 'No custom rate limit set, using global rate',
            'global_rate': self.max_executions_per_second
        }
