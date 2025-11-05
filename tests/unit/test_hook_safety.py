"""Unit tests for Hook Safety Components.

Tests for:
- IdempotencyTracker: Preventing duplicate executions
- CascadeMonitor: Detecting cycles and deep nesting
- RateLimiter: Preventing execution storms
"""

import pytest
import time
from datetime import datetime, timedelta

from athena.hooks.lib.idempotency_tracker import IdempotencyTracker, IdempotencyRecord
from athena.hooks.lib.cascade_monitor import CascadeMonitor, CallStack
from athena.hooks.lib.rate_limiter import RateLimiter, TokenBucket


# ============================================================================
# IdempotencyTracker Tests
# ============================================================================

class TestIdempotencyTrackerFingerprinting:
    """Tests for idempotency fingerprint computation."""

    def test_same_context_produces_same_fingerprint(self):
        """Same hook + context should produce identical fingerprint."""
        context = {'input': 'test', 'key': 'value'}
        fp1 = IdempotencyTracker._compute_fingerprint('hook1', context)
        fp2 = IdempotencyTracker._compute_fingerprint('hook1', context)

        assert fp1 == fp2
        assert len(fp1) == 64  # SHA256 hex length

    def test_different_contexts_produce_different_fingerprints(self):
        """Different contexts should produce different fingerprints."""
        fp1 = IdempotencyTracker._compute_fingerprint('hook1', {'a': 1})
        fp2 = IdempotencyTracker._compute_fingerprint('hook1', {'a': 2})

        assert fp1 != fp2

    def test_different_hooks_produce_different_fingerprints(self):
        """Different hook IDs should produce different fingerprints."""
        context = {'a': 1}
        fp1 = IdempotencyTracker._compute_fingerprint('hook1', context)
        fp2 = IdempotencyTracker._compute_fingerprint('hook2', context)

        assert fp1 != fp2

    def test_fingerprint_handles_nested_context(self):
        """Should handle nested/complex contexts."""
        context = {
            'nested': {'deep': {'value': 123}},
            'list': [1, 2, 3],
            'string': 'test'
        }
        fp = IdempotencyTracker._compute_fingerprint('hook', context)
        assert len(fp) == 64


class TestIdempotencyTrackerDuplicateDetection:
    """Tests for detecting duplicate executions."""

    def test_no_duplicates_when_empty(self):
        """Empty tracker should not detect duplicates."""
        tracker = IdempotencyTracker()
        is_dup = tracker.is_duplicate('hook1', {'test': 'data'})
        assert is_dup is False

    def test_first_execution_not_duplicate(self):
        """First execution of hook should not be duplicate."""
        tracker = IdempotencyTracker()
        context = {'input': 'test'}

        is_dup = tracker.is_duplicate('hook1', context)
        assert is_dup is False

        tracker.record_execution('hook1', context)

    def test_immediate_re_execution_is_duplicate(self):
        """Immediate re-execution should be detected as duplicate."""
        tracker = IdempotencyTracker(execution_window_seconds=30)
        context = {'input': 'test'}

        # First execution
        tracker.record_execution('hook1', context)

        # Immediate second execution
        is_dup = tracker.is_duplicate('hook1', context)
        assert is_dup is True

    def test_old_execution_not_duplicate(self):
        """Execution after grace period should not be duplicate."""
        tracker = IdempotencyTracker(execution_window_seconds=1)
        context = {'input': 'test'}

        tracker.record_execution('hook1', context)

        # Wait for window to expire
        time.sleep(1.1)

        is_dup = tracker.is_duplicate('hook1', context)
        assert is_dup is False

    def test_explicit_idempotency_key_tracking(self):
        """Should track explicit idempotency keys independently."""
        tracker = IdempotencyTracker(execution_window_seconds=30)
        context1 = {'input': 'test1'}
        context2 = {'input': 'test2'}

        # Record with first key
        tracker.record_execution('hook1', context1, idempotency_key='key_123')

        # Same key should be duplicate (even with different context, key takes precedence)
        is_dup = tracker.is_duplicate('hook1', context1, idempotency_key='key_123')
        assert is_dup is True

        # Different key should be checked by fingerprint (different context = not dup)
        is_dup = tracker.is_duplicate('hook1', context2, idempotency_key='key_456')
        assert is_dup is False

        # Record with second key
        tracker.record_execution('hook1', context2, idempotency_key='key_456')

        # Now same key_456 should be duplicate
        is_dup = tracker.is_duplicate('hook1', context2, idempotency_key='key_456')
        assert is_dup is True


class TestIdempotencyTrackerExecution:
    """Tests for recording and retrieving executions."""

    def test_record_execution_stores_result(self):
        """Should store execution result."""
        tracker = IdempotencyTracker()
        context = {'test': 'data'}

        tracker.record_execution('hook1', context, result={'success': True})

        last = tracker.get_last_execution('hook1')
        assert last is not None
        assert last.result == {'success': True}

    def test_get_execution_count(self):
        """Should accurately count executions."""
        tracker = IdempotencyTracker()
        context = {'test': 'data'}

        # Record 3 executions
        for i in range(3):
            tracker.record_execution('hook1', context)

        assert tracker.get_execution_count('hook1') == 3

    def test_get_execution_count_within_window(self):
        """Should count only recent executions."""
        tracker = IdempotencyTracker(execution_window_seconds=1)
        context = {'test': 'data'}

        tracker.record_execution('hook1', context)
        time.sleep(0.5)
        tracker.record_execution('hook1', context)
        time.sleep(0.7)  # First execution now outside window

        count = tracker.get_execution_count('hook1', within_seconds=1)
        assert count == 1


class TestIdempotencyTrackerStats:
    """Tests for statistics tracking."""

    def test_get_stats_returns_dictionary(self):
        """Stats should contain key metrics."""
        tracker = IdempotencyTracker()
        tracker.record_execution('hook1', {'test': 1})
        tracker.record_execution('hook1', {'test': 2})

        stats = tracker.get_stats()

        assert 'total_executions' in stats
        assert 'active_hooks' in stats
        assert stats['total_executions'] >= 2


# ============================================================================
# CascadeMonitor Tests
# ============================================================================

class TestCascadeMonitorCallStack:
    """Tests for call stack management."""

    def test_push_and_pop_hook(self):
        """Should push and pop hooks from stack."""
        monitor = CascadeMonitor()

        assert monitor.push_hook('hook1') is True
        assert monitor.get_depth() == 1

        popped = monitor.pop_hook()
        assert popped == 'hook1'
        assert monitor.get_depth() == 0

    def test_call_stack_path(self):
        """Should maintain correct call path."""
        monitor = CascadeMonitor()

        monitor.push_hook('hook1')
        monitor.push_hook('hook2')
        monitor.push_hook('hook3')

        path = monitor.get_call_stack()
        assert path == ['hook1', 'hook2', 'hook3']

    def test_hook_in_stack_detection(self):
        """Should detect if hook is in current stack."""
        monitor = CascadeMonitor()

        monitor.push_hook('hook1')
        monitor.push_hook('hook2')

        assert monitor._call_stack.contains('hook1') is True
        assert monitor._call_stack.contains('hook2') is True
        assert monitor._call_stack.contains('hook3') is False


class TestCascadeMonitorCycleDetection:
    """Tests for cycle (circular reference) detection."""

    def test_cycle_detection_simple(self):
        """Should detect simple cycle A -> A."""
        monitor = CascadeMonitor()

        monitor.push_hook('hook1')
        allowed = monitor.push_hook('hook1')  # Try to push same hook

        assert allowed is False

    def test_cycle_detection_complex(self):
        """Should detect cycle A -> B -> A."""
        monitor = CascadeMonitor()

        monitor.push_hook('hook1')
        monitor.push_hook('hook2')
        allowed = monitor.push_hook('hook1')  # Cycle back

        assert allowed is False

    def test_no_cycle_different_sequence(self):
        """Different sequence should not be detected as cycle."""
        monitor = CascadeMonitor()

        monitor.push_hook('hook1')
        monitor.pop_hook()
        monitor.push_hook('hook1')  # Same hook, different sequence

        # Should be allowed since previous is popped
        allowed = monitor.push_hook('hook2')
        assert allowed is True


class TestCascadeMonitorDepthLimit:
    """Tests for depth limiting."""

    def test_depth_limit_enforcement(self):
        """Should reject nesting beyond max depth."""
        monitor = CascadeMonitor(max_depth=3)

        monitor.push_hook('hook1')
        monitor.push_hook('hook2')
        monitor.push_hook('hook3')

        allowed = monitor.push_hook('hook4')
        assert allowed is False

    def test_depth_limit_at_boundary(self):
        """Should allow execution at exactly max depth."""
        monitor = CascadeMonitor(max_depth=3)

        monitor.push_hook('hook1')
        monitor.push_hook('hook2')
        allowed = monitor.push_hook('hook3')  # 3/3

        assert allowed is True

    def test_depth_limit_exceeded_by_one(self):
        """Should reject execution one level beyond limit."""
        monitor = CascadeMonitor(max_depth=3)

        monitor.push_hook('hook1')
        monitor.push_hook('hook2')
        monitor.push_hook('hook3')
        allowed = monitor.push_hook('hook4')  # 4/3

        assert allowed is False


class TestCascadeMonitorBreadthLimit:
    """Tests for breadth (repetition) limiting."""

    def test_breadth_limit_enforcement(self):
        """Should limit repeated triggering of same hook."""
        monitor = CascadeMonitor(max_breadth=2)

        monitor.push_hook('hook1')
        monitor.pop_hook()
        monitor.push_hook('hook1')
        monitor.pop_hook()

        # 3rd trigger
        allowed = monitor.push_hook('hook1')
        assert allowed is False


class TestCascadeMonitorReset:
    """Tests for monitor reset."""

    def test_reset_clears_stack(self):
        """Reset should clear call stack."""
        monitor = CascadeMonitor()

        monitor.push_hook('hook1')
        monitor.reset()

        assert monitor.get_depth() == 0
        assert monitor.get_call_stack() == []


# ============================================================================
# RateLimiter Tests
# ============================================================================

class TestRateLimiterAllowExecution:
    """Tests for rate limit enforcement."""

    def test_initial_burst_capacity(self):
        """Should allow initial burst of executions."""
        limiter = RateLimiter(
            max_executions_per_second=10,
            burst_multiplier=2.0
        )

        # Should allow 20 immediate executions (2x burst capacity)
        for i in range(20):
            assert limiter.allow_execution('hook1') is True

        # 21st should fail
        assert limiter.allow_execution('hook1') is False

    def test_rate_enforcement_over_time(self):
        """Should enforce sustained rate limit."""
        limiter = RateLimiter(max_executions_per_second=5)

        # Use burst capacity (10 tokens)
        for i in range(10):
            assert limiter.allow_execution('hook1') is True

        # All tokens consumed, next should fail
        assert limiter.allow_execution('hook1') is False

        # Wait 1 second, should replenish 5 tokens
        time.sleep(1.0)
        assert limiter.allow_execution('hook1') is True

    def test_per_hook_rate_limits(self):
        """Should allow per-hook custom rate limits."""
        limiter = RateLimiter(max_executions_per_second=10)
        limiter.set_hook_rate_limit('slow_hook', 2)

        # slow_hook should be limited to 4 burst (2 * 2)
        for i in range(4):
            assert limiter.allow_execution('slow_hook') is True

        assert limiter.allow_execution('slow_hook') is False


class TestRateLimiterWaitTime:
    """Tests for wait time estimation."""

    def test_zero_wait_when_available(self):
        """Should report zero wait when capacity available."""
        limiter = RateLimiter(max_executions_per_second=10)
        wait_time = limiter.get_estimated_wait_time('hook1')
        assert wait_time == 0

    def test_positive_wait_when_exhausted(self):
        """Should report wait time when rate exceeded."""
        limiter = RateLimiter(max_executions_per_second=10)

        # Exhaust tokens
        for i in range(20):
            limiter.allow_execution('hook1')

        wait_time = limiter.get_estimated_wait_time('hook1')
        assert wait_time > 0


class TestRateLimiterReset:
    """Tests for rate limiter reset."""

    def test_reset_global_limit(self):
        """Reset should refill global tokens."""
        limiter = RateLimiter(max_executions_per_second=10)

        # Exhaust tokens
        for i in range(20):
            limiter.allow_execution('hook1')

        assert limiter.allow_execution('hook1') is False

        # Reset
        limiter.reset_global_limit()
        assert limiter.allow_execution('hook1') is True


class TestTokenBucketRefill:
    """Tests for token bucket refill logic."""

    def test_bucket_refill_over_time(self):
        """Bucket should refill tokens over time."""
        bucket = TokenBucket(
            max_tokens=10,
            current_tokens=0,
            replenish_rate=10,  # 10 tokens/sec
            last_refill=0
        )

        time.sleep(0.5)
        bucket.current_tokens += 0.5 * bucket.replenish_rate

        assert bucket.current_tokens == pytest.approx(5, 0.1)

    def test_bucket_respects_max_capacity(self):
        """Bucket should not exceed max capacity."""
        bucket = TokenBucket(
            max_tokens=10,
            current_tokens=10,
            replenish_rate=1,
            last_refill=0
        )

        time.sleep(1)
        tokens_to_add = 1 * bucket.replenish_rate
        bucket.current_tokens = min(bucket.max_tokens, bucket.current_tokens + tokens_to_add)

        assert bucket.current_tokens == 10  # Still at max
