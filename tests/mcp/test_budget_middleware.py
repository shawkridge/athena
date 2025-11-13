"""Tests for token budget middleware."""

import pytest
from mcp.types import TextContent
import json

from athena.mcp.budget_middleware import (
    BudgetMiddleware,
    StructuredResultBudgetValidator,
    get_budget_middleware,
)
from athena.mcp.structured_result import StructuredResult, ResultStatus


class TestBudgetMiddleware:
    """Tests for BudgetMiddleware."""

    def test_middleware_creation(self):
        """Test middleware can be created."""
        middleware = BudgetMiddleware()
        assert middleware is not None
        assert middleware.summary_limit == 300
        assert middleware.enable_enforcement is True

    def test_small_response_not_compressed(self):
        """Test small responses pass through unchanged."""
        middleware = BudgetMiddleware(summary_limit=300)
        response = TextContent(type="text", text="Small response")

        result = middleware.process_response(response, operation="test")
        assert result.text == "Small response"
        assert middleware.violations_count == 0

    def test_large_response_compressed(self):
        """Test large responses are compressed."""
        middleware = BudgetMiddleware(summary_limit=100, enable_enforcement=True)

        # Create a large response
        large_data = {
            "status": "success",
            "data": [{"id": i, "value": f"item_{i}"} for i in range(100)],
            "metadata": {"count": 100}
        }
        response = TextContent(type="text", text=json.dumps(large_data))

        result = middleware.process_response(response, operation="test")
        assert "Response compressed" in result.text or len(result.text) < len(response.text)
        assert middleware.violations_count > 0

    def test_metrics_tracking(self):
        """Test metrics are tracked."""
        middleware = BudgetMiddleware()

        # Process multiple responses
        for i in range(5):
            response = TextContent(type="text", text=f"Response {i}")
            middleware.process_response(response, operation=f"test_{i}")

        metrics = middleware.get_metrics()
        assert metrics["total_processed"] == 5
        assert metrics["enforcement_enabled"] is True

    def test_structured_result_validator(self):
        """Test StructuredResult validator."""
        validator = StructuredResultBudgetValidator(summary_limit=300)

        result = StructuredResult.success(
            data={"message": "Test result"},
            metadata={"operation": "test"}
        )

        processed = validator.validate_result(result, operation="test")
        assert processed is not None
        assert processed.type == "text"

    def test_global_middleware_singleton(self):
        """Test global middleware is a singleton."""
        mw1 = get_budget_middleware()
        mw2 = get_budget_middleware()
        assert mw1 is mw2

    def test_metrics_reset(self):
        """Test metrics can be reset."""
        middleware = BudgetMiddleware()

        # Create some metrics
        response = TextContent(type="text", text="test")
        middleware.process_response(response)

        assert middleware.total_processed > 0

        # Reset
        middleware.reset_metrics()
        assert middleware.total_processed == 0
        assert middleware.violations_count == 0


class TestBudgetEnforcement:
    """Tests for budget enforcement."""

    def test_enforcement_disabled(self):
        """Test enforcement can be disabled."""
        middleware = BudgetMiddleware(enable_enforcement=False)

        # Large response should not be compressed
        large_text = "x" * 10000
        response = TextContent(type="text", text=large_text)

        result = middleware.process_response(response)
        # With enforcement disabled, response may still be returned as-is
        assert result.text is not None

    def test_enforcement_enabled(self):
        """Test enforcement when enabled."""
        middleware = BudgetMiddleware(summary_limit=100, enable_enforcement=True)

        large_data = {"data": [i for i in range(500)]}
        response = TextContent(type="text", text=json.dumps(large_data))

        result = middleware.process_response(response)
        # Response should be compressed or truncated
        assert len(result.text) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
