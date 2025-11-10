"""Structured JSON logging for Athena (Phase 3).

Formats logs as JSON for easy aggregation with ELK, Datadog, etc.
Includes contextual fields:
- operation_id: Trace ID for correlated logging
- duration: Operation duration
- error details: Exception types and messages
- Business context: memory_type, operation_type, etc.
"""

import json
import logging
import traceback
import time
from typing import Any, Dict, Optional
from datetime import datetime
from contextvars import ContextVar

# Context variables for trace propagation
operation_id_context: ContextVar[Optional[str]] = ContextVar('operation_id', default=None)
user_context: ContextVar[Optional[str]] = ContextVar('user_id', default=None)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def __init__(self, include_timestamp: bool = True, include_traceback: bool = True):
        """Initialize JSON formatter.

        Args:
            include_timestamp: Include timestamp in log
            include_traceback: Include traceback for exceptions
        """
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_traceback = include_traceback

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        log_data = {
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add timestamp
        if self.include_timestamp:
            log_data['timestamp'] = datetime.utcnow().isoformat() + 'Z'

        # Add contextual fields from record
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                # Skip standard logging fields
                if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                             'levelname', 'levelno', 'lineno', 'module', 'msecs',
                             'message', 'pathname', 'process', 'processName', 'relativeCreated',
                             'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info']:
                    log_data[key] = value

        # Add operation context
        operation_id = operation_id_context.get()
        if operation_id:
            log_data['operation_id'] = operation_id

        user_id = user_context.get()
        if user_id:
            log_data['user_id'] = user_id

        # Add exception information
        if record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            log_data['exception'] = {
                'type': exc_type.__name__ if exc_type else 'Unknown',
                'message': str(exc_value) if exc_value else '',
            }

            if self.include_traceback and exc_tb:
                log_data['traceback'] = traceback.format_tb(exc_tb)

        return json.dumps(log_data)


class StructuredLogger:
    """Structured logger with context management."""

    def __init__(self, name: str):
        """Initialize structured logger.

        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(name)

    def _log_with_extra(self, level: int, msg: str, extra: Optional[Dict[str, Any]] = None, **kwargs):
        """Log message with extra fields.

        Args:
            level: Logging level
            msg: Log message
            extra: Extra fields to include
            **kwargs: Additional keyword arguments
        """
        if extra:
            self.logger.log(level, msg, extra=extra, **kwargs)
        else:
            self.logger.log(level, msg, **kwargs)

    def debug(self, msg: str, extra: Optional[Dict[str, Any]] = None):
        """Log debug message."""
        self._log_with_extra(logging.DEBUG, msg, extra)

    def info(self, msg: str, extra: Optional[Dict[str, Any]] = None):
        """Log info message."""
        self._log_with_extra(logging.INFO, msg, extra)

    def warning(self, msg: str, extra: Optional[Dict[str, Any]] = None):
        """Log warning message."""
        self._log_with_extra(logging.WARNING, msg, extra)

    def error(self, msg: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = False):
        """Log error message."""
        self._log_with_extra(logging.ERROR, msg, extra, exc_info=exc_info)

    def critical(self, msg: str, extra: Optional[Dict[str, Any]] = None):
        """Log critical message."""
        self._log_with_extra(logging.CRITICAL, msg, extra)

    def operation(self, operation_type: str, **fields):
        """Log operation with structured fields.

        Args:
            operation_type: Type of operation
            **fields: Operation-specific fields
        """
        extra = {
            'operation_type': operation_type,
            **fields
        }
        self.info(f"Operation: {operation_type}", extra)

    def operation_complete(self, operation_type: str, duration_seconds: float, **fields):
        """Log operation completion.

        Args:
            operation_type: Type of operation
            duration_seconds: Duration in seconds
            **fields: Operation-specific fields
        """
        extra = {
            'operation_type': operation_type,
            'duration_seconds': duration_seconds,
            'status': 'complete',
            **fields
        }
        self.info(f"Operation complete: {operation_type} ({duration_seconds:.3f}s)", extra)

    def operation_error(self, operation_type: str, error: Exception, **fields):
        """Log operation error.

        Args:
            operation_type: Type of operation
            error: Exception that occurred
            **fields: Operation-specific fields
        """
        extra = {
            'operation_type': operation_type,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'status': 'error',
            **fields
        }
        self.error(f"Operation error: {operation_type}: {str(error)}", extra, exc_info=True)

    def audit(self, action: str, **fields):
        """Log audit event.

        Args:
            action: Audit action (store, delete, update, etc.)
            **fields: Audit fields (user_id, project_id, resource, etc.)
        """
        extra = {
            'audit_action': action,
            'audit': True,
            **fields
        }
        self.info(f"Audit: {action}", extra)

    def performance(self, metric_name: str, value: float, unit: str = '', **fields):
        """Log performance metric.

        Args:
            metric_name: Name of metric
            value: Metric value
            unit: Unit of measurement
            **fields: Additional fields
        """
        extra = {
            'metric_name': metric_name,
            'metric_value': value,
            'metric_unit': unit,
            **fields
        }
        self.info(f"Performance: {metric_name}={value}{unit}", extra)


def setup_structured_logging(
    name: str = 'athena',
    log_file: Optional[str] = None,
    log_level: int = logging.INFO
) -> logging.Logger:
    """Set up structured logging for application.

    Args:
        name: Logger name
        log_file: Optional log file path
        log_level: Logging level

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Console handler with JSON formatting
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

    return logger


def set_operation_context(operation_id: str):
    """Set operation ID for log correlation.

    Args:
        operation_id: Unique operation identifier
    """
    operation_id_context.set(operation_id)


def clear_operation_context():
    """Clear operation context."""
    operation_id_context.set(None)


def set_user_context(user_id: str):
    """Set user ID for log correlation.

    Args:
        user_id: User identifier
    """
    user_context.set(user_id)


def get_structured_logger(name: str) -> StructuredLogger:
    """Get structured logger instance.

    Args:
        name: Logger name

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name)
