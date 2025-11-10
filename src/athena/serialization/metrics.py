"""TOON serialization metrics and monitoring.

Tracks TOON encoding/decoding performance, token savings, and effectiveness.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TOONOperationMetrics:
    """Metrics for a single TOON operation."""

    operation_type: str  # "encode" or "decode"
    schema_name: str
    duration_ms: float
    input_size_bytes: int
    output_size_bytes: int
    success: bool
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    json_size_bytes: Optional[int] = None
    token_savings_percent: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "operation_type": self.operation_type,
            "schema_name": self.schema_name,
            "duration_ms": self.duration_ms,
            "input_size_bytes": self.input_size_bytes,
            "output_size_bytes": self.output_size_bytes,
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp,
            "json_size_bytes": self.json_size_bytes,
            "token_savings_percent": self.token_savings_percent,
        }


class TOONMetricsCollector:
    """Collects and analyzes TOON serialization metrics."""

    def __init__(self, max_history: int = 10000):
        """Initialize metrics collector.

        Args:
            max_history: Maximum number of metrics to keep in memory
        """
        self.max_history = max_history
        self.metrics: List[TOONOperationMetrics] = []
        self._lock = None  # Thread safety if needed

    def record_operation(self, metric: TOONOperationMetrics) -> None:
        """Record a TOON operation.

        Args:
            metric: TOONOperationMetrics instance
        """
        self.metrics.append(metric)

        # Trim history if needed
        if len(self.metrics) > self.max_history:
            self.metrics = self.metrics[-self.max_history :]

    def record_encode(
        self,
        schema_name: str,
        duration_ms: float,
        json_str: str,
        toon_str: str,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """Record an encoding operation.

        Args:
            schema_name: Schema used
            duration_ms: Operation duration in milliseconds
            json_str: Original JSON string
            toon_str: Encoded TOON string
            success: Whether operation succeeded
            error: Error message if failed
        """
        json_size = len(json_str.encode("utf-8"))
        toon_size = len(toon_str.encode("utf-8")) if toon_str else 0
        token_savings = self._calculate_token_savings(json_size, toon_size)

        metric = TOONOperationMetrics(
            operation_type="encode",
            schema_name=schema_name,
            duration_ms=duration_ms,
            input_size_bytes=json_size,
            output_size_bytes=toon_size,
            json_size_bytes=json_size,
            success=success,
            error=error,
            token_savings_percent=token_savings,
        )
        self.record_operation(metric)

        if success:
            logger.debug(
                f"TOON encode ({schema_name}): {json_size} -> {toon_size} bytes "
                f"({token_savings:.1f}% savings) in {duration_ms:.2f}ms"
            )
        else:
            logger.warning(f"TOON encode failed ({schema_name}): {error}")

    def record_decode(
        self,
        schema_name: str,
        duration_ms: float,
        toon_size_bytes: int,
        json_size_bytes: int,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """Record a decoding operation.

        Args:
            schema_name: Schema used
            duration_ms: Operation duration in milliseconds
            toon_size_bytes: Decoded TOON size
            json_size_bytes: Resulting JSON size
            success: Whether operation succeeded
            error: Error message if failed
        """
        metric = TOONOperationMetrics(
            operation_type="decode",
            schema_name=schema_name,
            duration_ms=duration_ms,
            input_size_bytes=toon_size_bytes,
            output_size_bytes=json_size_bytes,
            json_size_bytes=json_size_bytes,
            success=success,
            error=error,
        )
        self.record_operation(metric)

        if success:
            logger.debug(
                f"TOON decode ({schema_name}): {toon_size_bytes} -> {json_size_bytes} bytes "
                f"in {duration_ms:.2f}ms"
            )
        else:
            logger.warning(f"TOON decode failed ({schema_name}): {error}")

    def get_summary(self) -> Dict:
        """Get summary statistics.

        Returns:
            Dictionary with overall metrics
        """
        if not self.metrics:
            return {
                "total_operations": 0,
                "encode_operations": 0,
                "decode_operations": 0,
                "success_rate": 0.0,
                "avg_token_savings_percent": 0.0,
                "avg_duration_ms": 0.0,
                "total_json_bytes": 0,
                "total_toon_bytes": 0,
            }

        encodes = [m for m in self.metrics if m.operation_type == "encode"]
        decodes = [m for m in self.metrics if m.operation_type == "decode"]
        successful = [m for m in self.metrics if m.success]

        total_json_bytes = sum(m.json_size_bytes or 0 for m in encodes)
        total_toon_bytes = sum(m.output_size_bytes for m in encodes)
        avg_token_savings = (
            sum(m.token_savings_percent for m in encodes) / len(encodes)
            if encodes
            else 0.0
        )
        avg_duration = (
            sum(m.duration_ms for m in self.metrics) / len(self.metrics)
            if self.metrics
            else 0.0
        )

        return {
            "total_operations": len(self.metrics),
            "encode_operations": len(encodes),
            "decode_operations": len(decodes),
            "success_count": len(successful),
            "success_rate": len(successful) / len(self.metrics) if self.metrics else 0.0,
            "avg_token_savings_percent": avg_token_savings,
            "avg_duration_ms": avg_duration,
            "total_json_bytes": total_json_bytes,
            "total_toon_bytes": total_toon_bytes,
            "overall_compression_ratio": (
                total_toon_bytes / total_json_bytes if total_json_bytes > 0 else 0.0
            ),
        }

    def get_schema_stats(self, schema_name: str) -> Dict:
        """Get statistics for a specific schema.

        Args:
            schema_name: Schema name to analyze

        Returns:
            Dictionary with schema-specific metrics
        """
        schema_metrics = [m for m in self.metrics if m.schema_name == schema_name]

        if not schema_metrics:
            return {"schema_name": schema_name, "operations": 0}

        encodes = [m for m in schema_metrics if m.operation_type == "encode"]
        successful = [m for m in schema_metrics if m.success]

        total_json = sum(m.json_size_bytes or 0 for m in encodes)
        total_toon = sum(m.output_size_bytes for m in encodes)

        return {
            "schema_name": schema_name,
            "total_operations": len(schema_metrics),
            "encode_operations": len(encodes),
            "success_count": len(successful),
            "success_rate": (
                len(successful) / len(schema_metrics) if schema_metrics else 0.0
            ),
            "avg_duration_ms": (
                sum(m.duration_ms for m in schema_metrics) / len(schema_metrics)
                if schema_metrics
                else 0.0
            ),
            "total_json_bytes": total_json,
            "total_toon_bytes": total_toon,
            "compression_ratio": total_toon / total_json if total_json > 0 else 0.0,
            "avg_token_savings_percent": (
                sum(m.token_savings_percent for m in encodes) / len(encodes)
                if encodes
                else 0.0
            ),
        }

    def get_all_schema_stats(self) -> Dict[str, Dict]:
        """Get statistics for all schemas.

        Returns:
            Dictionary mapping schema names to their stats
        """
        schemas = set(m.schema_name for m in self.metrics)
        return {schema: self.get_schema_stats(schema) for schema in schemas}

    def get_errors(self) -> List[TOONOperationMetrics]:
        """Get all failed operations.

        Returns:
            List of failed operation metrics
        """
        return [m for m in self.metrics if not m.success]

    def get_performance_report(self) -> str:
        """Get formatted performance report.

        Returns:
            Human-readable performance report
        """
        summary = self.get_summary()
        schema_stats = self.get_all_schema_stats()

        report = "=" * 80 + "\n"
        report += "TOON SERIALIZATION PERFORMANCE REPORT\n"
        report += "=" * 80 + "\n\n"

        # Overall summary
        report += "OVERALL SUMMARY\n"
        report += "-" * 80 + "\n"
        report += f"Total Operations: {summary['total_operations']}\n"
        report += f"Encodes: {summary['encode_operations']}\n"
        report += f"Decodes: {summary['decode_operations']}\n"
        report += f"Success Rate: {summary['success_rate']*100:.1f}%\n"
        report += f"Avg Token Savings: {summary['avg_token_savings_percent']:.1f}%\n"
        report += f"Avg Duration: {summary['avg_duration_ms']:.2f}ms\n"
        report += f"Overall Compression Ratio: {summary['overall_compression_ratio']:.2f}\n"
        report += f"  (JSON bytes: {summary['total_json_bytes']} -> "
        report += f"TOON bytes: {summary['total_toon_bytes']})\n\n"

        # Per-schema breakdown
        if schema_stats:
            report += "PER-SCHEMA BREAKDOWN\n"
            report += "-" * 80 + "\n"
            for schema_name, stats in sorted(schema_stats.items()):
                if stats.get("total_operations", 0) > 0:
                    report += f"\n{schema_name}:\n"
                    report += f"  Operations: {stats['total_operations']} "
                    report += f"({stats['encode_operations']} encodes)\n"
                    report += f"  Success Rate: {stats['success_rate']*100:.1f}%\n"
                    report += f"  Avg Duration: {stats['avg_duration_ms']:.2f}ms\n"
                    report += f"  Compression: {stats['compression_ratio']:.2f}x "
                    report += f"({stats['avg_token_savings_percent']:.1f}% savings)\n"

        # Errors if any
        errors = self.get_errors()
        if errors:
            report += "\n\nERRORS\n"
            report += "-" * 80 + "\n"
            for err in errors[-10:]:  # Show last 10 errors
                report += f"{err.operation_type.upper()} "
                report += f"({err.schema_name}): {err.error}\n"

        report += "\n" + "=" * 80 + "\n"
        return report

    def export_metrics(self, filepath: str) -> None:
        """Export all metrics to JSON file.

        Args:
            filepath: Path to write metrics to
        """
        try:
            data = {
                "summary": self.get_summary(),
                "schema_stats": self.get_all_schema_stats(),
                "operations": [m.to_dict() for m in self.metrics],
            }
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"Metrics exported to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")

    @staticmethod
    def _calculate_token_savings(json_size: int, toon_size: int) -> float:
        """Calculate token savings percentage.

        Args:
            json_size: Original JSON size in bytes
            toon_size: Encoded TOON size in bytes

        Returns:
            Percentage reduction (0-100)
        """
        if json_size == 0:
            return 0.0
        return ((json_size - toon_size) / json_size) * 100


# Global metrics collector
_metrics_collector: Optional[TOONMetricsCollector] = None


def get_metrics_collector() -> TOONMetricsCollector:
    """Get or create global metrics collector.

    Returns:
        TOONMetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = TOONMetricsCollector()
    return _metrics_collector


def record_encode_metric(
    schema_name: str,
    duration_ms: float,
    json_str: str,
    toon_str: str,
    success: bool = True,
    error: Optional[str] = None,
) -> None:
    """Record an encoding metric globally.

    Args:
        schema_name: Schema name
        duration_ms: Operation duration in milliseconds
        json_str: Original JSON string
        toon_str: Encoded TOON string
        success: Whether operation succeeded
        error: Error message if failed
    """
    get_metrics_collector().record_encode(
        schema_name, duration_ms, json_str, toon_str, success, error
    )


def record_decode_metric(
    schema_name: str,
    duration_ms: float,
    toon_size_bytes: int,
    json_size_bytes: int,
    success: bool = True,
    error: Optional[str] = None,
) -> None:
    """Record a decoding metric globally.

    Args:
        schema_name: Schema name
        duration_ms: Operation duration in milliseconds
        toon_size_bytes: Encoded TOON size
        json_size_bytes: Decoded JSON size
        success: Whether operation succeeded
        error: Error message if failed
    """
    get_metrics_collector().record_decode(
        schema_name, duration_ms, toon_size_bytes, json_size_bytes, success, error
    )
