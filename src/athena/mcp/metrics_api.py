"""Metrics API for monitoring handler execution and token budget.

Provides endpoints for accessing handler metrics, budget violations,
compression statistics, and performance data.
"""

import json
import logging
from typing import Any, Dict, Optional
from datetime import datetime

from .handler_middleware_wrapper import get_metrics_accumulator
from .budget_middleware import get_budget_middleware

logger = logging.getLogger(__name__)


class MetricsAPI:
    """API for accessing handler and budget metrics."""

    def __init__(self):
        """Initialize metrics API."""
        self.accumulator = get_metrics_accumulator()
        self.middleware = get_budget_middleware()

    def get_overall_metrics(self) -> Dict[str, Any]:
        """Get overall system metrics.

        Returns:
            Dictionary with overall metrics
        """
        handler_summary = self.accumulator.get_summary()
        middleware_metrics = self.middleware.get_metrics()

        return {
            "timestamp": datetime.now().isoformat(),
            "handler_metrics": handler_summary,
            "middleware_metrics": middleware_metrics,
            "combined": {
                "total_budget_violations": handler_summary["budget_violations"],
                "violation_rate_percent": handler_summary["violation_rate"] * 100,
                "overall_compression_ratio": handler_summary["overall_compression_ratio"],
                "average_handler_time_ms": handler_summary["avg_execution_time"] * 1000,
                "total_handlers_called": handler_summary["total_handlers_called"],
            }
        }

    def get_handler_performance(self, handler_name: str) -> Optional[Dict[str, Any]]:
        """Get performance metrics for a specific handler.

        Args:
            handler_name: Name of the handler

        Returns:
            Handler metrics or None if not found
        """
        stats = self.accumulator.get_handler_stats(handler_name)
        if stats is None:
            return None

        return {
            "handler_name": handler_name,
            "call_count": stats["call_count"],
            "total_execution_time_ms": stats["total_time"] * 1000,
            "average_execution_time_ms": stats["avg_execution_time"] * 1000,
            "budget_violations": stats["violations"],
            "compression_events": stats["compressions"],
            "average_tokens_counted": stats["avg_tokens_counted"],
            "average_tokens_returned": stats["avg_tokens_returned"],
            "compression_ratio": (
                stats["avg_tokens_returned"] / stats["avg_tokens_counted"]
                if stats["avg_tokens_counted"] > 0
                else 1.0
            ),
        }

    def get_top_handlers_by_violations(self, limit: int = 10) -> list[Dict[str, Any]]:
        """Get handlers with most budget violations.

        Args:
            limit: Maximum number of handlers to return

        Returns:
            List of handlers sorted by violation count (descending)
        """
        handlers = []
        for handler_name, stats in self.accumulator.handlers_by_name.items():
            if stats["violations"] > 0:
                handlers.append({
                    "handler_name": handler_name,
                    "violations": stats["violations"],
                    "call_count": stats["call_count"],
                    "violation_rate": stats["violations"] / stats["call_count"],
                })

        # Sort by violation count descending
        handlers.sort(key=lambda x: x["violations"], reverse=True)
        return handlers[:limit]

    def get_top_handlers_by_compression(self, limit: int = 10) -> list[Dict[str, Any]]:
        """Get handlers with most compression events.

        Args:
            limit: Maximum number of handlers to return

        Returns:
            List of handlers sorted by compression count (descending)
        """
        handlers = []
        for handler_name, stats in self.accumulator.handlers_by_name.items():
            if stats["compressions"] > 0:
                handlers.append({
                    "handler_name": handler_name,
                    "compressions": stats["compressions"],
                    "call_count": stats["call_count"],
                    "compression_rate": stats["compressions"] / stats["call_count"],
                })

        # Sort by compression count descending
        handlers.sort(key=lambda x: x["compressions"], reverse=True)
        return handlers[:limit]

    def get_token_efficiency_report(self) -> Dict[str, Any]:
        """Get detailed token efficiency report.

        Returns:
            Report on token usage and efficiency
        """
        summary = self.accumulator.get_summary()

        total_counted = summary["total_tokens_counted"]
        total_returned = summary["total_tokens_returned"]
        tokens_saved = total_counted - total_returned

        compression_ratio = summary["overall_compression_ratio"]

        return {
            "total_tokens_counted": total_counted,
            "total_tokens_returned": total_returned,
            "tokens_saved": tokens_saved,
            "compression_ratio": compression_ratio,
            "efficiency_percent": (1 - compression_ratio) * 100,
            "budget_violations_count": summary["budget_violations"],
            "violation_rate_percent": summary["violation_rate"] * 100,
            "recommendation": self._get_efficiency_recommendation(
                tokens_saved, summary["violation_rate"]
            ),
        }

    def _get_efficiency_recommendation(self, tokens_saved: int, violation_rate: float) -> str:
        """Get recommendation based on current metrics.

        Args:
            tokens_saved: Total tokens saved
            violation_rate: Rate of budget violations

        Returns:
            Recommendation string
        """
        if violation_rate > 0.2:
            return "⚠️  High violation rate (>20%). Consider increasing budget limits or optimizing handler outputs."
        elif violation_rate > 0.1:
            return "⚠️  Moderate violation rate (10-20%). Monitor closely and optimize high-violation handlers."
        elif tokens_saved > 100000:
            return "✅ Excellent efficiency! Compression is working well. Current settings are optimal."
        elif tokens_saved > 10000:
            return "✅ Good efficiency. Token savings are significant."
        else:
            return "ℹ️  Low compression needed. Handler outputs are within budget."

    def get_metrics_snapshot(self) -> Dict[str, Any]:
        """Get complete metrics snapshot.

        Returns:
            Comprehensive metrics snapshot
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "overall": self.get_overall_metrics(),
            "efficiency_report": self.get_token_efficiency_report(),
            "top_violations": self.get_top_handlers_by_violations(5),
            "top_compressions": self.get_top_handlers_by_compression(5),
        }

    def export_metrics_json(self) -> str:
        """Export all metrics as JSON.

        Returns:
            JSON string with all metrics
        """
        snapshot = self.get_metrics_snapshot()
        return json.dumps(snapshot, indent=2, default=str)

    def reset_all_metrics(self) -> None:
        """Reset all metrics counters."""
        self.accumulator.reset()
        self.middleware.reset_metrics()
        logger.info("All metrics reset")


# Global metrics API instance
_global_metrics_api: Optional[MetricsAPI] = None


def get_metrics_api() -> MetricsAPI:
    """Get or create global metrics API instance."""
    global _global_metrics_api
    if _global_metrics_api is None:
        _global_metrics_api = MetricsAPI()
    return _global_metrics_api
