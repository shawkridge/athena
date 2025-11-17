"""Unit tests for MCP rate limiting system.

Tests the token bucket algorithm, per-tool categorization,
and rate limit enforcement across all tool types.
"""

import pytest
import time
from athena.mcp.rate_limiter import (
    MCPRateLimiter,
    ToolCategory,
    ToolRateLimit,
    TokenBucket,
    rate_limit_response,
)


class TestToolRateLimit:
    """Test ToolRateLimit configuration."""

    def test_tool_rate_limit_creation(self):
        """Test creating rate limit configuration."""
        limit = ToolRateLimit(
            tool_name="recall",
            category=ToolCategory.READ,
            max_per_minute=100
        )
        assert limit.tool_name == "recall"
        assert limit.category == ToolCategory.READ
        assert limit.max_per_minute == 100
        assert limit.burst_size == max(2, 100 // 5)  # 100 / 5 = 20

    def test_tool_rate_limit_custom_burst(self):
        """Test custom burst size."""
        limit = ToolRateLimit(
            tool_name="record_event",
            category=ToolCategory.WRITE,
            max_per_minute=30,
            burst_size=5
        )
        assert limit.burst_size == 5

    def test_refill_rate_calculation(self):
        """Test refill rate (tokens per second)."""
        limit = ToolRateLimit(
            tool_name="test",
            category=ToolCategory.READ,
            max_per_minute=60  # 1 token per second
        )
        assert limit.refill_rate == 1.0


class TestTokenBucket:
    """Test TokenBucket algorithm."""

    def test_token_bucket_initialization(self):
        """Test bucket starts with full capacity."""
        limit = ToolRateLimit("test", ToolCategory.READ, max_per_minute=100)
        bucket = TokenBucket(config=limit)
        assert bucket.tokens == 20  # Burst size

    def test_token_consumption(self):
        """Test consuming tokens."""
        limit = ToolRateLimit("test", ToolCategory.READ, max_per_minute=100)
        bucket = TokenBucket(config=limit)

        # First request should succeed
        assert bucket.try_consume(1) is True
        assert bucket.tokens < 20

    def test_burst_capacity(self):
        """Test burst capacity allows temporary exceedance."""
        limit = ToolRateLimit("test", ToolCategory.READ, max_per_minute=100)
        bucket = TokenBucket(config=limit)

        # Should allow burst_size requests
        for i in range(20):
            assert bucket.try_consume(1) is True

        # 21st request should fail (no burst beyond capacity)
        assert bucket.try_consume(1) is False

    def test_token_refill(self):
        """Test tokens refill over time."""
        limit = ToolRateLimit(
            "test",
            ToolCategory.READ,
            max_per_minute=60  # 1 token per second
        )
        bucket = TokenBucket(config=limit)

        # Consume all tokens
        for i in range(bucket.config.burst_size):
            bucket.try_consume(1)
        # Allow small floating point error
        assert bucket.tokens < 0.01

        # Wait for refill (60 tokens/min = 1 token/sec)
        time.sleep(1.1)

        # Should have at least 1 token
        bucket._refill()
        assert bucket.tokens >= 1.0

    def test_get_wait_time(self):
        """Test calculating wait time before next request."""
        limit = ToolRateLimit(
            "test",
            ToolCategory.READ,
            max_per_minute=60  # 1 token per second
        )
        bucket = TokenBucket(config=limit)

        # Consume all tokens
        for i in range(bucket.config.burst_size):
            bucket.try_consume(1)

        # Wait time should be > 0
        wait_time = bucket.get_wait_time()
        assert wait_time > 0


class TestMCPRateLimiter:
    """Test MCPRateLimiter."""

    def test_rate_limiter_initialization(self):
        """Test initializing rate limiter with custom limits."""
        limiter = MCPRateLimiter(read_limit=100, write_limit=30, admin_limit=10)
        assert limiter.read_limit == 100
        assert limiter.write_limit == 30
        assert limiter.admin_limit == 10

    def test_tool_auto_categorization_read(self):
        """Test auto-categorizing read tools."""
        limiter = MCPRateLimiter()

        # Test read tool patterns
        read_tools = [
            "recall", "list_memories", "get_active_goals",
            "search_graph", "analyze_coverage", "find_procedures",
            "get_working_memory", "get_expertise", "validate_plan"
        ]

        for tool_name in read_tools:
            category = limiter._categorize_tool(tool_name)
            assert category == ToolCategory.READ, f"{tool_name} should be READ"

    def test_tool_auto_categorization_write(self):
        """Test auto-categorizing write tools."""
        limiter = MCPRateLimiter()

        # Test write tool patterns
        write_tools = [
            "remember", "record_event", "create_task",
            "update_task_status", "create_entity", "add_observation",
            "set_goal", "strengthen_association", "consolidate_working_memory"
        ]

        for tool_name in write_tools:
            category = limiter._categorize_tool(tool_name)
            assert category == ToolCategory.WRITE, f"{tool_name} should be WRITE"

    def test_tool_auto_categorization_admin(self):
        """Test auto-categorizing admin tools."""
        limiter = MCPRateLimiter()

        # Test admin tool patterns
        admin_tools = [
            "forget", "optimize", "delete_rule",
            "clear_working_memory", "reset_metrics"
        ]

        for tool_name in admin_tools:
            category = limiter._categorize_tool(tool_name)
            assert category == ToolCategory.ADMIN, f"{tool_name} should be ADMIN"

    def test_allow_request_succeeds_within_limit(self):
        """Test requests are allowed within rate limit."""
        limiter = MCPRateLimiter(read_limit=100, write_limit=50, admin_limit=20)

        # Should allow many requests (within burst)
        allowed = 0
        for i in range(30):
            if limiter.allow_request("recall"):
                allowed += 1
        assert allowed > 0  # At least some allowed

    def test_allow_request_fails_above_limit(self):
        """Test requests are denied above rate limit."""
        limiter = MCPRateLimiter(read_limit=20, write_limit=10, admin_limit=5)

        # Use up the burst capacity
        allowed = 0
        for i in range(30):
            if limiter.allow_request("recall"):
                allowed += 1

        # Should have some allowed and some denied
        assert allowed > 0
        assert allowed < 30

    def test_separate_limits_per_tool(self):
        """Test each tool gets separate rate limit bucket."""
        limiter = MCPRateLimiter(read_limit=30, write_limit=15)

        # Use read tool limit
        read_allowed = 0
        for i in range(20):
            if limiter.allow_request("recall"):
                read_allowed += 1

        # Write tool should have separate limit
        write_allowed = 0
        for i in range(15):
            if limiter.allow_request("remember"):
                write_allowed += 1

        # Both should allow some
        assert read_allowed > 0
        assert write_allowed > 0

    def test_get_retry_after(self):
        """Test getting retry_after time."""
        limiter = MCPRateLimiter(read_limit=60)  # 1 per second

        # Create bucket first by making a request
        limiter.allow_request("recall")

        # Get retry time
        retry_time = limiter.get_retry_after("recall")
        assert retry_time >= 0

    def test_metrics_tracking(self):
        """Test metrics are tracked correctly."""
        limiter = MCPRateLimiter(read_limit=30, write_limit=15)

        # Make requests
        allowed = 0
        for i in range(25):
            if limiter.allow_request("recall"):
                allowed += 1

        stats = limiter.get_stats()
        assert stats["total_requests"] == 25
        assert stats["allowed"] > 0
        assert stats["allowed"] == allowed

    def test_metrics_by_category(self):
        """Test metrics are tracked by category."""
        limiter = MCPRateLimiter(read_limit=30, write_limit=15, admin_limit=10)

        # Read requests
        read_allowed = 0
        for i in range(20):
            if limiter.allow_request("recall"):
                read_allowed += 1

        # Write requests
        write_allowed = 0
        for i in range(15):
            if limiter.allow_request("remember"):
                write_allowed += 1

        # Admin requests
        admin_allowed = 0
        for i in range(10):
            if limiter.allow_request("forget"):
                admin_allowed += 1

        stats = limiter.get_stats()
        assert stats["by_category"]["read"]["total"] == 20
        assert stats["by_category"]["read"]["allowed"] == read_allowed

        assert stats["by_category"]["write"]["total"] == 15
        assert stats["by_category"]["write"]["allowed"] == write_allowed

        assert stats["by_category"]["admin"]["total"] == 10
        assert stats["by_category"]["admin"]["allowed"] == admin_allowed

    def test_reset_metrics(self):
        """Test resetting metrics."""
        limiter = MCPRateLimiter(read_limit=5)

        # Make some requests
        for i in range(6):
            limiter.allow_request("recall")

        assert limiter.metrics["total_requests"] == 6

        # Reset
        limiter.reset_metrics()
        assert limiter.metrics["total_requests"] == 0
        assert limiter.metrics["allowed"] == 0
        assert limiter.metrics["rate_limited"] == 0

    def test_rate_limit_response(self):
        """Test rate limit error response format."""
        response = rate_limit_response(1.5)

        assert response["status"] == "error"
        assert response["error"] == "Rate limit exceeded"
        assert response["retry_after"] == 1.5
        assert "Too many requests" in response["message"]


class TestRateLimitingIntegration:
    """Integration tests for rate limiting with realistic scenarios."""

    def test_read_tools_higher_limit_than_write(self):
        """Test read tools have higher limit than write tools."""
        limiter = MCPRateLimiter(read_limit=100, write_limit=30)

        # Read tools can handle more requests
        read_allowed = 0
        for i in range(100):
            if limiter.allow_request("recall"):
                read_allowed += 1

        write_allowed = 0
        for i in range(100):
            if limiter.allow_request("remember"):
                write_allowed += 1

        # Reset for next test
        limiter.reset_metrics()

        assert read_allowed >= write_allowed

    def test_admin_tools_lowest_limit(self):
        """Test admin tools have lowest limit."""
        limiter = MCPRateLimiter(read_limit=100, write_limit=30, admin_limit=10)

        # Fill up buckets
        read_count = sum(1 for _ in range(100) if limiter.allow_request("recall"))
        write_count = sum(1 for _ in range(100) if limiter.allow_request("remember"))
        admin_count = sum(1 for _ in range(100) if limiter.allow_request("forget"))

        assert admin_count <= write_count <= read_count

    def test_realistic_burst_handling(self):
        """Test realistic burst pattern with refill."""
        limiter = MCPRateLimiter(read_limit=60)  # 1 token/second

        # Initial burst
        burst_count = 0
        for i in range(20):
            if limiter.allow_request("recall"):
                burst_count += 1
            else:
                break

        assert burst_count >= 10  # Should allow some burst

        # Wait for refill
        time.sleep(1.1)

        # Should allow more requests after refill
        refilled_count = 0
        for i in range(5):
            if limiter.allow_request("recall"):
                refilled_count += 1

        assert refilled_count > 0

    def test_mixed_tool_access_patterns(self):
        """Test mixed access patterns don't interfere."""
        limiter = MCPRateLimiter(read_limit=20, write_limit=10)

        # Alternating tool access
        requests = ["recall", "remember", "recall", "remember", "get_expertise"]
        results = []

        for i in range(25):
            tool = requests[i % len(requests)]
            results.append(limiter.allow_request(tool))

        # Should have mix of successes and failures
        assert any(results)  # Some allowed
        assert not all(results)  # Some denied


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
