"""Tests for handler middleware wrapper."""

import pytest
from mcp.types import TextContent
import asyncio
import json

from athena.mcp.handler_middleware_wrapper import (
    HandlerMetricsAccumulator,
    wrap_handler_with_budget,
    get_metrics_accumulator,
)
from athena.mcp.budget_middleware import BudgetMiddleware


class TestHandlerMetricsAccumulator:
    """Tests for HandlerMetricsAccumulator."""

    def test_accumulator_creation(self):
        """Test accumulator can be created."""
        accumulator = HandlerMetricsAccumulator()
        assert accumulator is not None
        assert accumulator.total_handlers_called == 0

    def test_record_handler_execution(self):
        """Test recording handler execution."""
        accumulator = HandlerMetricsAccumulator()

        accumulator.record_handler_execution(
            handler_name="test_handler",
            execution_time=0.1,
            tokens_counted=100,
            tokens_returned=80,
            had_violation=False,
            was_compressed=True,
        )

        assert accumulator.total_handlers_called == 1
        assert accumulator.total_execution_time == 0.1
        assert accumulator.total_tokens_counted == 100
        assert accumulator.total_tokens_returned == 80

    def test_violation_tracking(self):
        """Test budget violation tracking."""
        accumulator = HandlerMetricsAccumulator()

        # Record violation
        accumulator.record_handler_execution(
            handler_name="test_handler",
            execution_time=0.05,
            tokens_counted=500,
            tokens_returned=300,
            had_violation=True,
            was_compressed=True,
        )

        assert accumulator.budget_violations == 1

        # Record non-violation
        accumulator.record_handler_execution(
            handler_name="test_handler",
            execution_time=0.05,
            tokens_counted=200,
            tokens_returned=200,
            had_violation=False,
            was_compressed=False,
        )

        assert accumulator.budget_violations == 1
        assert accumulator.total_handlers_called == 2

    def test_get_summary(self):
        """Test getting summary metrics."""
        accumulator = HandlerMetricsAccumulator()

        accumulator.record_handler_execution(
            handler_name="handler1",
            execution_time=0.1,
            tokens_counted=100,
            tokens_returned=80,
            had_violation=False,
            was_compressed=True,
        )

        summary = accumulator.get_summary()
        assert summary["total_handlers_called"] == 1
        assert summary["total_execution_time"] == 0.1
        assert "violation_rate" in summary
        assert "overall_compression_ratio" in summary

    def test_handler_stats(self):
        """Test getting stats for specific handler."""
        accumulator = HandlerMetricsAccumulator()

        accumulator.record_handler_execution(
            handler_name="test_handler",
            execution_time=0.1,
            tokens_counted=100,
            tokens_returned=80,
            had_violation=False,
            was_compressed=True,
        )

        stats = accumulator.get_handler_stats("test_handler")
        assert stats is not None
        assert stats["call_count"] == 1
        assert stats["compressions"] == 1

    def test_reset_metrics(self):
        """Test resetting metrics."""
        accumulator = HandlerMetricsAccumulator()

        accumulator.record_handler_execution(
            handler_name="test_handler",
            execution_time=0.1,
            tokens_counted=100,
            tokens_returned=80,
            had_violation=False,
            was_compressed=True,
        )

        assert accumulator.total_handlers_called == 1

        accumulator.reset()
        assert accumulator.total_handlers_called == 0
        assert accumulator.total_tokens_counted == 0


class TestHandlerWrapper:
    """Tests for handler wrapper decorator."""

    @pytest.mark.asyncio
    async def test_wrap_simple_handler(self):
        """Test wrapping a simple async handler."""
        middleware = BudgetMiddleware()
        accumulator = HandlerMetricsAccumulator()

        async def simple_handler():
            return [TextContent(type="text", text="Simple response")]

        wrapped = wrap_handler_with_budget(
            handler=simple_handler,
            handler_name="simple_handler",
            middleware=middleware,
            accumulator=accumulator,
        )

        result = await wrapped()
        assert result is not None
        assert len(result) == 1
        assert isinstance(result[0], TextContent)

    @pytest.mark.asyncio
    async def test_wrap_handler_with_metrics(self):
        """Test that wrapper tracks metrics."""
        middleware = BudgetMiddleware()
        accumulator = HandlerMetricsAccumulator()

        async def test_handler():
            return [TextContent(type="text", text="Test response")]

        wrapped = wrap_handler_with_budget(
            handler=test_handler,
            handler_name="test_handler",
            middleware=middleware,
            accumulator=accumulator,
            track_metrics=True,
        )

        await wrapped()

        assert accumulator.total_handlers_called == 1
        assert accumulator.total_tokens_counted > 0

    @pytest.mark.asyncio
    async def test_wrap_handler_large_response(self):
        """Test wrapper handles large responses."""
        middleware = BudgetMiddleware(summary_limit=100, enable_enforcement=True)
        accumulator = HandlerMetricsAccumulator()

        # Create a response larger than budget
        large_data = {"data": [{"item": f"value_{i}"} for i in range(100)]}
        large_text = json.dumps(large_data)

        async def large_handler():
            return [TextContent(type="text", text=large_text)]

        wrapped = wrap_handler_with_budget(
            handler=large_handler,
            handler_name="large_handler",
            middleware=middleware,
            accumulator=accumulator,
        )

        result = await wrapped()
        assert result is not None
        assert len(result) == 1

        # Check metrics show compression
        summary = accumulator.get_summary()
        assert summary["budget_violations"] > 0

    @pytest.mark.asyncio
    async def test_wrap_handler_error_handling(self):
        """Test wrapper handles handler errors gracefully."""
        middleware = BudgetMiddleware()
        accumulator = HandlerMetricsAccumulator()

        async def error_handler():
            raise ValueError("Test error")

        wrapped = wrap_handler_with_budget(
            handler=error_handler,
            handler_name="error_handler",
            middleware=middleware,
            accumulator=accumulator,
        )

        with pytest.raises(ValueError):
            await wrapped()

    def test_global_accumulator_singleton(self):
        """Test global accumulator is a singleton."""
        acc1 = get_metrics_accumulator()
        acc2 = get_metrics_accumulator()
        assert acc1 is acc2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
