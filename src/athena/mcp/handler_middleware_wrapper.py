"""Handler middleware wrapper for applying budget enforcement to MCP handlers.

This module provides decorators and wrappers to apply budget middleware
to MCP handlers automatically, with metrics tracking.
"""

import functools
import logging
import time
from typing import Any, Callable, List, TypeVar, Optional
from mcp.types import TextContent

from .budget_middleware import BudgetMiddleware, get_budget_middleware
from .structured_result import StructuredResult

logger = logging.getLogger(__name__)

# Type variables for generic handler wrapper
HandlerFunc = TypeVar('HandlerFunc', bound=Callable)


class HandlerMetricsAccumulator:
    """Accumulates metrics across all handler executions."""

    def __init__(self):
        """Initialize accumulator."""
        self.total_handlers_called = 0
        self.total_execution_time = 0.0
        self.budget_violations = 0
        self.total_tokens_counted = 0
        self.total_tokens_returned = 0
        self.handlers_by_name: dict[str, dict[str, Any]] = {}
        self.compression_events: list[dict[str, Any]] = []

    def record_handler_execution(
        self,
        handler_name: str,
        execution_time: float,
        tokens_counted: int,
        tokens_returned: int,
        had_violation: bool,
        was_compressed: bool,
    ) -> None:
        """Record metrics for a handler execution.

        Args:
            handler_name: Name of the handler
            execution_time: Execution time in seconds
            tokens_counted: Tokens in original response
            tokens_returned: Tokens in final response
            had_violation: Whether budget was exceeded
            was_compressed: Whether response was compressed
        """
        self.total_handlers_called += 1
        self.total_execution_time += execution_time
        self.total_tokens_counted += tokens_counted
        self.total_tokens_returned += tokens_returned

        if had_violation:
            self.budget_violations += 1

        if handler_name not in self.handlers_by_name:
            self.handlers_by_name[handler_name] = {
                "call_count": 0,
                "total_time": 0.0,
                "violations": 0,
                "compressions": 0,
                "avg_tokens_counted": 0,
                "avg_tokens_returned": 0,
            }

        stats = self.handlers_by_name[handler_name]
        stats["call_count"] += 1
        stats["total_time"] += execution_time

        if had_violation:
            stats["violations"] += 1

        if was_compressed:
            stats["compressions"] += 1
            self.compression_events.append({
                "handler": handler_name,
                "time": time.time(),
                "tokens_before": tokens_counted,
                "tokens_after": tokens_returned,
                "compression_ratio": tokens_returned / tokens_counted if tokens_counted > 0 else 1.0,
            })

        # Update averages
        stats["avg_tokens_counted"] = (
            stats["avg_tokens_counted"] * (stats["call_count"] - 1) + tokens_counted
        ) / stats["call_count"]
        stats["avg_tokens_returned"] = (
            stats["avg_tokens_returned"] * (stats["call_count"] - 1) + tokens_returned
        ) / stats["call_count"]

    def get_summary(self) -> dict[str, Any]:
        """Get summary metrics.

        Returns:
            Summary metrics dictionary
        """
        avg_execution_time = (
            self.total_execution_time / self.total_handlers_called
            if self.total_handlers_called > 0
            else 0
        )

        compression_ratio = (
            self.total_tokens_returned / self.total_tokens_counted
            if self.total_tokens_counted > 0
            else 1.0
        )

        return {
            "total_handlers_called": self.total_handlers_called,
            "total_execution_time": self.total_execution_time,
            "avg_execution_time": avg_execution_time,
            "budget_violations": self.budget_violations,
            "violation_rate": (
                self.budget_violations / self.total_handlers_called
                if self.total_handlers_called > 0
                else 0
            ),
            "total_tokens_counted": self.total_tokens_counted,
            "total_tokens_returned": self.total_tokens_returned,
            "overall_compression_ratio": compression_ratio,
            "handlers_count": len(self.handlers_by_name),
            "compression_events_count": len(self.compression_events),
        }

    def get_handler_stats(self, handler_name: str) -> Optional[dict[str, Any]]:
        """Get stats for a specific handler.

        Args:
            handler_name: Name of the handler

        Returns:
            Handler stats or None if not found
        """
        if handler_name not in self.handlers_by_name:
            return None

        stats = self.handlers_by_name[handler_name].copy()
        stats["avg_execution_time"] = (
            stats["total_time"] / stats["call_count"]
            if stats["call_count"] > 0
            else 0
        )
        return stats

    def reset(self) -> None:
        """Reset all metrics."""
        self.total_handlers_called = 0
        self.total_execution_time = 0.0
        self.budget_violations = 0
        self.total_tokens_counted = 0
        self.total_tokens_returned = 0
        self.handlers_by_name.clear()
        self.compression_events.clear()


# Global accumulator
_global_accumulator: Optional[HandlerMetricsAccumulator] = None


def get_metrics_accumulator() -> HandlerMetricsAccumulator:
    """Get or create global metrics accumulator."""
    global _global_accumulator
    if _global_accumulator is None:
        _global_accumulator = HandlerMetricsAccumulator()
    return _global_accumulator


def wrap_handler_with_budget(
    handler: HandlerFunc,
    handler_name: str,
    middleware: Optional[BudgetMiddleware] = None,
    accumulator: Optional[HandlerMetricsAccumulator] = None,
    track_metrics: bool = True,
) -> HandlerFunc:
    """Wrap a handler to apply budget middleware.

    Args:
        handler: Handler function to wrap
        handler_name: Name of the handler (for logging)
        middleware: BudgetMiddleware instance (uses global if None)
        accumulator: MetricsAccumulator instance (uses global if None)
        track_metrics: Whether to track metrics

    Returns:
        Wrapped handler function
    """
    if middleware is None:
        middleware = get_budget_middleware()
    if accumulator is None and track_metrics:
        accumulator = get_metrics_accumulator()

    @functools.wraps(handler)
    async def wrapped_handler(*args: Any, **kwargs: Any) -> Any:
        """Wrapped handler with budget enforcement and metrics."""
        start_time = time.time()

        try:
            # Call the original handler
            result = await handler(*args, **kwargs)

            # Apply budget middleware to responses
            execution_time = time.time() - start_time

            if isinstance(result, list) and len(result) > 0:
                # Handle list of TextContent responses
                processed_results = []
                for item in result:
                    if isinstance(item, TextContent):
                        # Count tokens before processing
                        tokens_before = middleware.budget_manager.count_tokens(item.text)

                        # Process through middleware
                        processed = middleware.process_response(
                            response=item,
                            operation=handler_name,
                            is_summary=True,
                        )

                        # Count tokens after processing
                        tokens_after = middleware.budget_manager.count_tokens(processed.text)

                        processed_results.append(processed)

                        # Track metrics
                        if track_metrics and accumulator:
                            had_violation = tokens_before > 300
                            was_compressed = tokens_after < tokens_before
                            accumulator.record_handler_execution(
                                handler_name=handler_name,
                                execution_time=execution_time,
                                tokens_counted=tokens_before,
                                tokens_returned=tokens_after,
                                had_violation=had_violation,
                                was_compressed=was_compressed,
                            )

                            if had_violation:
                                logger.info(
                                    f"Handler {handler_name}: Budget violation detected "
                                    f"({tokens_before} → {tokens_after} tokens, "
                                    f"compression: {tokens_after/tokens_before:.1%})"
                                )
                    else:
                        processed_results.append(item)

                return processed_results
            elif isinstance(result, TextContent):
                # Single TextContent response
                tokens_before = middleware.budget_manager.count_tokens(result.text)

                processed = middleware.process_response(
                    response=result,
                    operation=handler_name,
                    is_summary=True,
                )

                tokens_after = middleware.budget_manager.count_tokens(processed.text)

                if track_metrics and accumulator:
                    had_violation = tokens_before > 300
                    was_compressed = tokens_after < tokens_before
                    accumulator.record_handler_execution(
                        handler_name=handler_name,
                        execution_time=execution_time,
                        tokens_counted=tokens_before,
                        tokens_returned=tokens_after,
                        had_violation=had_violation,
                        was_compressed=was_compressed,
                    )

                return [processed]
            else:
                # Non-TextContent response, pass through
                if track_metrics and accumulator:
                    accumulator.record_handler_execution(
                        handler_name=handler_name,
                        execution_time=execution_time,
                        tokens_counted=0,
                        tokens_returned=0,
                        had_violation=False,
                        was_compressed=False,
                    )
                return result

        except Exception as e:
            # Log error but don't fail
            logger.error(f"Error in handler wrapper for {handler_name}: {e}", exc_info=True)
            raise

    return wrapped_handler


class HandlerBudgetMiddlewareMixin:
    """Mixin to add budget middleware support to MemoryMCPServer."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize mixin with budget middleware."""
        super().__init__(*args, **kwargs)

        # Initialize budget middleware and metrics
        self.budget_middleware = get_budget_middleware()
        self.handler_metrics = get_metrics_accumulator()

        logger.info("Budget middleware and metrics accumulator initialized")

    def get_handler_metrics_summary(self) -> dict[str, Any]:
        """Get summary of handler metrics.

        Returns:
            Metrics summary dictionary
        """
        return self.handler_metrics.get_summary()

    def get_handler_stats(self, handler_name: str) -> Optional[dict[str, Any]]:
        """Get stats for a specific handler.

        Args:
            handler_name: Name of the handler

        Returns:
            Handler stats or None
        """
        return self.handler_metrics.get_handler_stats(handler_name)

    def reset_handler_metrics(self) -> None:
        """Reset all handler metrics."""
        self.handler_metrics.reset()
        logger.info("Handler metrics reset")
