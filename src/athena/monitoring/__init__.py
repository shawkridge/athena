"""Monitoring infrastructure for Memory MCP.

Includes structured logging, metrics collection, health checks, and layer monitoring.
"""

from .logging import setup_logging, get_logger, log_operation, LogContext
from .metrics import get_collector, MetricsCollector, track_operation
from .health import HealthChecker, HealthStatus, get_health_checker
from .layer_health_dashboard import (
    LayerHealthMonitor,
    LayerHealth,
    SystemHealth,
    LayerType,
)

# Phase 3: Production monitoring (Prometheus + JSON logging)
from .exporters import (
    PrometheusMetrics,
    get_metrics,
    initialize_metrics,
)

from .structured_logging import (
    JSONFormatter,
    StructuredLogger,
    setup_structured_logging,
    set_operation_context,
    clear_operation_context,
    set_user_context,
    get_structured_logger,
)

__all__ = [
    "setup_logging",
    "get_logger",
    "log_operation",
    "LogContext",
    "get_collector",
    "MetricsCollector",
    "track_operation",
    "HealthChecker",
    "HealthStatus",
    "get_health_checker",
    "LayerHealthMonitor",
    "LayerHealth",
    "SystemHealth",
    "LayerType",
    # Phase 3 additions
    "PrometheusMetrics",
    "get_metrics",
    "initialize_metrics",
    "JSONFormatter",
    "StructuredLogger",
    "setup_structured_logging",
    "set_operation_context",
    "clear_operation_context",
    "set_user_context",
    "get_structured_logger",
]
