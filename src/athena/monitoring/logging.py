"""Structured logging infrastructure for ATHENA.

Provides JSON-formatted logging with context, tracing, and operational visibility.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Optional
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format record as JSON."""
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add context if available
        if hasattr(record, "context"):
            log_obj["context"] = record.context

        # Add timing info if available
        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = record.duration_ms

        # Add error info
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra"):
            log_obj.update(record.extra)

        return json.dumps(log_obj)


def setup_logging(
    name: str = "athena",
    level: str = "INFO",
    log_file: Optional[Path] = None,
    json_format: bool = True,
) -> logging.Logger:
    """
    Setup structured logging for ATHENA.

    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file to write logs to
        json_format: Use JSON formatting if True

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))

    # Remove existing handlers
    logger.handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level))

    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


class LogContext:
    """Context manager for structured logging context."""

    def __init__(self, logger: logging.Logger, **context):
        """Initialize with logger and context fields."""
        self.logger = logger
        self.context = context

    def __enter__(self):
        """Enter context."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        if exc_type is not None:
            self.logger.error(
                f"Exception in context: {exc_type.__name__}",
                extra={"context": self.context, "exception": str(exc_val)},
            )

    def log(self, level: str, message: str, **extra):
        """Log with context."""
        record = logging.LogRecord(
            name=self.logger.name,
            level=getattr(logging, level),
            pathname="",
            lineno=0,
            msg=message,
            args=(),
            exc_info=None,
        )
        record.context = self.context
        record.extra = extra
        self.logger.handle(record)


# Global logger instance
_logger: Optional[logging.Logger] = None


def get_logger(name: str = "athena") -> logging.Logger:
    """Get or create the global logger."""
    global _logger
    if _logger is None:
        _logger = setup_logging(name)
    return _logger


def log_operation(
    logger: logging.Logger, operation: str, duration_ms: float, success: bool, **context
):
    """Log an operation with timing and context."""
    level = "INFO" if success else "ERROR"
    status = "SUCCESS" if success else "FAILED"

    record = logging.LogRecord(
        name=logger.name,
        level=getattr(logging, level),
        pathname="",
        lineno=0,
        msg=f"{operation}: {status}",
        args=(),
        exc_info=None,
    )
    record.duration_ms = duration_ms
    record.context = context
    logger.handle(record)


def log_query(
    logger: logging.Logger,
    query: str,
    layer: str,
    duration_ms: float,
    result_count: int,
    project_id: Optional[int] = None,
):
    """Log a memory query operation."""
    context = {
        "operation": "query",
        "layer": layer,
        "project_id": project_id,
        "result_count": result_count,
        "query": query[:100],  # Truncate long queries
    }
    log_operation(logger, f"Query {layer}", duration_ms, True, **context)


def log_consolidation(
    logger: logging.Logger,
    project_id: int,
    duration_ms: float,
    events_processed: int,
    patterns_extracted: int,
    success: bool = True,
):
    """Log a consolidation operation."""
    context = {
        "operation": "consolidation",
        "project_id": project_id,
        "events_processed": events_processed,
        "patterns_extracted": patterns_extracted,
    }
    log_operation(logger, "Consolidation", duration_ms, success, **context)


def log_retrieval_failure(
    logger: logging.Logger,
    layer: str,
    query: str,
    reason: str,
    project_id: Optional[int] = None,
):
    """Log a failed retrieval operation."""
    record = logging.LogRecord(
        name=logger.name,
        level=logging.WARNING,
        pathname="",
        lineno=0,
        msg=f"Retrieval failed: {layer} - {reason}",
        args=(),
        exc_info=None,
    )
    record.context = {
        "operation": "retrieval",
        "layer": layer,
        "query": query[:100],
        "project_id": project_id,
        "reason": reason,
    }
    logger.handle(record)
