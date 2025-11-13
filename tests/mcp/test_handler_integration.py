"""Integration tests for handler budget middleware with real scenarios."""

import pytest
import json
from mcp.types import TextContent

from athena.mcp.handler_middleware_wrapper import (
    HandlerMetricsAccumulator,
    get_metrics_accumulator,
)
from athena.mcp.budget_middleware import BudgetMiddleware
from athena.mcp.metrics_api import MetricsAPI, get_metrics_api
from athena.mcp.structured_result import StructuredResult, PaginationMetadata


class TestIntegrationMetricsFlow:
    """Tests for end-to-end metrics flow."""

    def setup_method(self):
        """Reset metrics before each test."""
        get_metrics_accumulator().reset()

    def test_metrics_api_creation(self):
        """Test metrics API can be created and accessed."""
        api = get_metrics_api()
        assert api is not None
        assert api.accumulator is not None
        assert api.middleware is not None

    def test_overall_metrics_with_data(self):
        """Test getting overall metrics with recorded data."""
        accumulator = get_metrics_accumulator()

        # Record some handler executions
        for i in range(5):
            accumulator.record_handler_execution(
                handler_name="test_handler",
                execution_time=0.1 + i * 0.01,
                tokens_counted=100 + i * 10,
                tokens_returned=90 + i * 10,
                had_violation=i % 2 == 0,
                was_compressed=i % 2 == 0,
            )

        api = get_metrics_api()
        metrics = api.get_overall_metrics()

        assert metrics["timestamp"] is not None
        assert metrics["handler_metrics"]["total_handlers_called"] == 5
        assert metrics["combined"]["total_budget_violations"] > 0

    def test_handler_performance_stats(self):
        """Test getting performance stats for specific handler."""
        accumulator = get_metrics_accumulator()

        accumulator.record_handler_execution(
            handler_name="list_memories",
            execution_time=0.05,
            tokens_counted=500,
            tokens_returned=300,
            had_violation=True,
            was_compressed=True,
        )

        api = get_metrics_api()
        stats = api.get_handler_performance("list_memories")

        assert stats is not None
        assert stats["call_count"] == 1
        assert stats["budget_violations"] == 1
        assert stats["compression_events"] == 1
        assert stats["compression_ratio"] < 1.0

    def test_top_violations_ranking(self):
        """Test ranking handlers by violations."""
        accumulator = get_metrics_accumulator()

        # Create scenarios with different violation counts
        for handler_name, violations in [("handler_a", 5), ("handler_b", 2), ("handler_c", 8)]:
            for i in range(violations):
                accumulator.record_handler_execution(
                    handler_name=handler_name,
                    execution_time=0.05,
                    tokens_counted=500,
                    tokens_returned=300,
                    had_violation=True,
                    was_compressed=True,
                )

        api = get_metrics_api()
        top_violations = api.get_top_handlers_by_violations(limit=3)

        assert len(top_violations) == 3
        assert top_violations[0]["handler_name"] == "handler_c"
        assert top_violations[0]["violations"] == 8

    def test_token_efficiency_report(self):
        """Test token efficiency report generation."""
        accumulator = get_metrics_accumulator()

        # Record executions with significant token savings
        for i in range(10):
            accumulator.record_handler_execution(
                handler_name="test_handler",
                execution_time=0.05,
                tokens_counted=1000,
                tokens_returned=500,
                had_violation=True,
                was_compressed=True,
            )

        api = get_metrics_api()
        report = api.get_token_efficiency_report()

        assert report["total_tokens_counted"] == 10000
        assert report["total_tokens_returned"] == 5000
        assert report["tokens_saved"] == 5000
        assert report["efficiency_percent"] == 50.0
        assert "recommendation" in report

    def test_metrics_snapshot(self):
        """Test getting complete metrics snapshot."""
        accumulator = get_metrics_accumulator()

        for i in range(3):
            accumulator.record_handler_execution(
                handler_name="handler_" + str(i),
                execution_time=0.05,
                tokens_counted=500 + i * 100,
                tokens_returned=300 + i * 100,
                had_violation=i % 2 == 0,
                was_compressed=True,
            )

        api = get_metrics_api()
        snapshot = api.get_metrics_snapshot()

        assert "timestamp" in snapshot
        assert "overall" in snapshot
        assert "efficiency_report" in snapshot
        assert "top_violations" in snapshot
        assert "top_compressions" in snapshot

    def test_metrics_json_export(self):
        """Test exporting metrics as JSON."""
        accumulator = get_metrics_accumulator()

        accumulator.record_handler_execution(
            handler_name="test_handler",
            execution_time=0.05,
            tokens_counted=500,
            tokens_returned=300,
            had_violation=True,
            was_compressed=True,
        )

        api = get_metrics_api()
        json_str = api.export_metrics_json()

        # Verify it's valid JSON
        data = json.loads(json_str)
        assert data is not None
        assert "timestamp" in data
        assert "overall" in data

    def test_metrics_reset(self):
        """Test resetting metrics."""
        accumulator = get_metrics_accumulator()

        # Record some data
        accumulator.record_handler_execution(
            handler_name="test_handler",
            execution_time=0.05,
            tokens_counted=500,
            tokens_returned=300,
            had_violation=True,
            was_compressed=True,
        )

        assert accumulator.total_handlers_called == 1

        # Reset
        api = get_metrics_api()
        api.reset_all_metrics()

        # Verify reset
        summary = accumulator.get_summary()
        assert summary["total_handlers_called"] == 0


class TestMetricsRecommendations:
    """Tests for metrics-based recommendations."""

    def test_recommendation_generation(self):
        """Test that recommendations are generated."""
        accumulator = get_metrics_accumulator()

        # Generate some metrics
        for i in range(10):
            accumulator.record_handler_execution(
                handler_name="test",
                execution_time=0.01,
                tokens_counted=1000,
                tokens_returned=500,
                had_violation=i < 2,  # 2 violations out of 10
                was_compressed=True,
            )

        api = get_metrics_api()
        report = api.get_token_efficiency_report()

        # Verify recommendation is generated
        assert "recommendation" in report
        assert len(report["recommendation"]) > 0
        assert isinstance(report["recommendation"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
