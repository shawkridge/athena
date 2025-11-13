"""Token Budget Middleware for MCP Handlers

This module provides middleware to enforce token budgets on MCP tool responses,
ensuring all responses stay within the 300-token summary limit while preserving
critical information through intelligent compression and truncation.

Features:
- Automatic token counting for responses
- Budget enforcement with configurable limits
- Multiple overflow strategies (compression, truncation, delegation)
- Violation logging and metrics
- Backward compatibility with existing handlers
"""

import json
import logging
from typing import Any, Dict, Optional, List
from mcp.types import TextContent

from ..efficiency.token_budget import (
    TokenBudgetManager,
    TokenBudgetConfig,
    TokenCountingStrategy,
    PriorityLevel,
    OverflowStrategy,
)
from .structured_result import StructuredResult, ResultStatus

logger = logging.getLogger(__name__)


class BudgetMiddleware:
    """Middleware for enforcing token budgets on MCP responses."""

    def __init__(
        self,
        summary_limit: int = 300,
        full_context_limit: int = 4000,
        enable_enforcement: bool = True,
        log_violations: bool = True,
    ):
        """Initialize budget middleware.

        Args:
            summary_limit: Target token limit for summary responses (default 300)
            full_context_limit: Max tokens for full context responses (default 4000)
            enable_enforcement: Whether to enforce limits (can disable for testing)
            log_violations: Whether to log budget violations
        """
        self.summary_limit = summary_limit
        self.full_context_limit = full_context_limit
        self.enable_enforcement = enable_enforcement
        self.log_violations = log_violations

        # Initialize TokenBudgetManager
        self.budget_config = TokenBudgetConfig(
            total_budget=summary_limit,
            buffer_tokens=50,
            min_response_tokens=50,
            counting_strategy=TokenCountingStrategy.CHARACTER_BASED,
            primary_overflow_strategy=OverflowStrategy.COMPRESS,
            allow_overflow=not enable_enforcement,
        )
        self.budget_manager = TokenBudgetManager(self.budget_config)

        # Metrics
        self.violations_count = 0
        self.total_processed = 0
        self.compression_applied_count = 0

    def process_response(
        self,
        response: TextContent,
        operation: str = "unknown",
        is_summary: bool = True,
    ) -> TextContent:
        """Process and enforce budget on a response.

        Args:
            response: TextContent response to process
            operation: Name of operation for logging
            is_summary: Whether this is a summary response (vs full context)

        Returns:
            Processed TextContent with budget enforced
        """
        self.total_processed += 1

        if not response or response.type != "text":
            return response

        # Count tokens in response
        token_count = self.budget_manager.count_tokens(response.text)
        limit = self.summary_limit if is_summary else self.full_context_limit

        # Check if over budget
        if token_count <= limit:
            return response

        # Log violation
        if self.log_violations:
            self.violations_count += 1
            logger.warning(
                f"Token budget violation: {operation} returned {token_count} tokens "
                f"(limit: {limit}). Applying compression."
            )

        # Apply compression
        if not self.enable_enforcement:
            # Just log, don't enforce
            return response

        compressed_text = self._compress_response(response.text, limit)
        self.compression_applied_count += 1

        return TextContent(type="text", text=compressed_text)

    def _compress_response(self, text: str, target_tokens: int) -> str:
        """Compress response to fit within token budget.

        Args:
            text: Original response text
            target_tokens: Target token limit

        Returns:
            Compressed response text
        """
        try:
            # Try to parse as JSON for smarter compression
            data = json.loads(text)

            # Compress JSON structure
            if isinstance(data, dict):
                # Keep status and summary, reduce data
                result = {"status": data.get("status", "error")}

                # Keep metadata if present
                if "metadata" in data:
                    result["metadata"] = data["metadata"]

                # Keep pagination but reduce data items
                if "pagination" in data:
                    result["pagination"] = data["pagination"]

                # Reduce data items
                if "data" in data:
                    if isinstance(data["data"], list):
                        # Keep top 5 items for lists
                        result["data"] = data["data"][:5]
                    elif isinstance(data["data"], dict):
                        # Keep only key fields
                        result["data"] = {
                            k: v
                            for k, v in list(data["data"].items())[:10]
                        }
                    else:
                        result["data"] = data["data"]

                # Add drill-down hint
                result["_note"] = "Response compressed to fit token budget. Use operation with drill-down parameters for full details."

                return json.dumps(result)
        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback: truncate text
        words = text.split()
        truncated = " ".join(words[: target_tokens * 4 // 5])  # Rough estimate
        truncated += "\n\n[Response truncated to fit token budget. Request full details with drill-down parameters.]"

        return truncated

    def get_metrics(self) -> Dict[str, Any]:
        """Get middleware metrics.

        Returns:
            Dictionary with metrics
        """
        return {
            "total_processed": self.total_processed,
            "violations_detected": self.violations_count,
            "compression_applied": self.compression_applied_count,
            "violation_rate": (
                self.violations_count / self.total_processed
                if self.total_processed > 0
                else 0
            ),
            "enforcement_enabled": self.enable_enforcement,
            "summary_limit_tokens": self.summary_limit,
        }

    def reset_metrics(self) -> None:
        """Reset metrics counters."""
        self.violations_count = 0
        self.total_processed = 0
        self.compression_applied_count = 0


class StructuredResultBudgetValidator:
    """Validator for StructuredResult responses with budget enforcement."""

    def __init__(self, summary_limit: int = 300):
        """Initialize validator.

        Args:
            summary_limit: Target token limit for summaries
        """
        self.middleware = BudgetMiddleware(
            summary_limit=summary_limit,
            enable_enforcement=True,
            log_violations=True,
        )

    def validate_result(
        self,
        result: StructuredResult,
        operation: str = "unknown",
    ) -> TextContent:
        """Validate and enforce budget on StructuredResult.

        Args:
            result: StructuredResult to validate
            operation: Operation name for logging

        Returns:
            Processed TextContent with budget enforced
        """
        # Convert to TextContent
        text_content = result.as_text_content()

        # Process through middleware
        processed = self.middleware.process_response(
            response=text_content,
            operation=operation,
            is_summary=True,
        )

        return processed

    def get_metrics(self) -> Dict[str, Any]:
        """Get validator metrics."""
        return self.middleware.get_metrics()


# Global middleware instance
_global_middleware: Optional[BudgetMiddleware] = None


def get_budget_middleware() -> BudgetMiddleware:
    """Get or create global budget middleware instance."""
    global _global_middleware
    if _global_middleware is None:
        _global_middleware = BudgetMiddleware()
    return _global_middleware


def enforce_response_budget(
    response: TextContent,
    operation: str = "unknown",
    limit: int = 300,
) -> TextContent:
    """Enforce token budget on a response (convenience function).

    Args:
        response: Response to process
        operation: Operation name for logging
        limit: Token limit to enforce

    Returns:
        Processed response with budget enforced
    """
    middleware = get_budget_middleware()
    return middleware.process_response(
        response=response,
        operation=operation,
        is_summary=(limit <= 300),
    )
