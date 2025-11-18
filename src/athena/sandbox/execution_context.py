"""Execution context for tracking and managing sandboxed code execution.

This module provides ExecutionContext for tracking execution state, capturing
I/O, monitoring resource usage, and logging violations in real-time.

Features:
- Real-time execution state tracking
- I/O capture (stdout/stderr)
- Resource usage monitoring (memory, time, files)
- Violation detection and logging
- Execution timeline with events
"""

import io
import json
import logging
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExecutionEvent:
    """Single event during code execution.

    Attributes:
        timestamp: When event occurred (ISO format)
        event_type: Type of event (io|violation|resource|exception)
        details: Event-specific data
        severity: Severity level (info|warning|error|critical)
    """

    timestamp: str
    event_type: str
    details: Dict[str, Any]
    severity: str = "info"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ResourceUsage:
    """Resource usage statistics.

    Attributes:
        peak_memory_mb: Peak memory usage in MB
        peak_cpu_percent: Peak CPU usage percentage
        file_operations_count: Number of file I/O operations
        network_operations_count: Number of network operations attempted
        duration_ms: Total execution time
    """

    peak_memory_mb: float = 0.0
    peak_cpu_percent: float = 0.0
    file_operations_count: int = 0
    network_operations_count: int = 0
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class IOCapture:
    """Capture stdout/stderr during execution.

    Intercepts writes to sys.stdout and sys.stderr, capturing all output
    while allowing it to pass through to the real streams (if desired).
    """

    def __init__(self, capture_stderr: bool = True):
        """Initialize IO capture.

        Args:
            capture_stderr: Whether to also capture stderr
        """
        self.capture_stderr = capture_stderr
        self.stdout_buffer = io.StringIO()
        self.stderr_buffer = io.StringIO()
        self.original_stdout = None
        self.original_stderr = None

    def start(self):
        """Start capturing I/O."""
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        # Create wrapper that writes to both buffer and original stream
        sys.stdout = self._create_wrapper(self.original_stdout, self.stdout_buffer)

        if self.capture_stderr:
            sys.stderr = self._create_wrapper(self.original_stderr, self.stderr_buffer)

    def stop(self):
        """Stop capturing I/O and restore original streams."""
        if self.original_stdout:
            sys.stdout = self.original_stdout
        if self.original_stderr and self.capture_stderr:
            sys.stderr = self.original_stderr

    def get_stdout(self) -> str:
        """Get captured stdout."""
        return self.stdout_buffer.getvalue()

    def get_stderr(self) -> str:
        """Get captured stderr."""
        return self.stderr_buffer.getvalue()

    @staticmethod
    def _create_wrapper(original_stream, buffer):
        """Create wrapper that writes to both original stream and buffer."""

        class StreamWrapper:
            def __init__(self, original, buffer):
                self.original = original
                self.buffer = buffer

            def write(self, data: str) -> int:
                self.buffer.write(data)
                return self.original.write(data)

            def flush(self):
                self.buffer.flush()
                self.original.flush()

            def isatty(self):
                return self.original.isatty()

            def fileno(self):
                try:
                    return self.original.fileno()
                except (AttributeError, io.UnsupportedOperation):
                    raise io.UnsupportedOperation("fileno")

        return StreamWrapper(original_stream, buffer)


class ExecutionContext:
    """Context for managing sandboxed code execution.

    Tracks execution state, captures I/O, monitors resources, and logs violations.
    Provides a complete execution record for analysis and debugging.

    Example:
        context = ExecutionContext(execution_id="exec_123")
        context.start()
        try:
            # Execute code
            exec(code, context.exec_globals)
        finally:
            context.stop()
            print(f"Captured output: {context.get_stdout()}")
    """

    def __init__(
        self,
        execution_id: str,
        language: str = "python",
        timeout_seconds: int = 30,
        track_resources: bool = True,
        capture_io: bool = True,
    ):
        """Initialize execution context.

        Args:
            execution_id: Unique execution ID
            language: Programming language (python|javascript|bash)
            timeout_seconds: Execution timeout in seconds
            track_resources: Whether to track resource usage
            capture_io: Whether to capture stdout/stderr
        """
        self.execution_id = execution_id
        self.language = language
        self.timeout_seconds = timeout_seconds
        self.track_resources = track_resources
        self.capture_io = capture_io

        # Execution state
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.status = "pending"  # pending|running|completed|failed|timeout

        # I/O capture
        self.io_capture = IOCapture() if capture_io else None

        # Execution events timeline
        self.events: List[ExecutionEvent] = []

        # Resource tracking
        self.resources = ResourceUsage()

        # Violations log
        self.violations: List[Dict[str, Any]] = []

        # Execution globals (for Python code)
        self.exec_globals: Dict[str, Any] = {
            "__name__": "__main__",
            "__builtins__": __builtins__,
        }

        # Exception info
        self.exception: Optional[Exception] = None
        self.traceback: Optional[str] = None

        logger.info(f"ExecutionContext created: {execution_id}")

    def start(self):
        """Start execution tracking.

        Initializes I/O capture, sets start time, and begins monitoring.
        """
        self.start_time = time.time()
        self.status = "running"

        if self.io_capture:
            self.io_capture.start()

        self._log_event("execution", {"status": "started"}, "info")
        logger.debug(f"Execution started: {self.execution_id}")

    def stop(self):
        """Stop execution tracking.

        Finalizes I/O capture, calculates metrics, and sets status.
        """
        if self.start_time is None:
            logger.warning("ExecutionContext.stop() called before start()")
            return

        self.end_time = time.time()

        if self.io_capture:
            self.io_capture.stop()

        # Calculate duration
        self.resources.duration_ms = (self.end_time - self.start_time) * 1000

        # Update status if not already set
        if self.status == "running":
            self.status = "completed"

        self._log_event("execution", {"status": self.status}, "info")
        logger.debug(f"Execution stopped: {self.execution_id} (status={self.status})")

    def get_stdout(self) -> str:
        """Get captured stdout."""
        if self.io_capture:
            return self.io_capture.get_stdout()
        return ""

    def get_stderr(self) -> str:
        """Get captured stderr."""
        if self.io_capture:
            return self.io_capture.get_stderr()
        return ""

    def _log_event(
        self,
        event_type: str,
        details: Dict[str, Any],
        severity: str = "info",
    ):
        """Log an execution event.

        Args:
            event_type: Type of event
            details: Event details
            severity: Severity level
        """
        event = ExecutionEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=event_type,
            details=details,
            severity=severity,
        )
        self.events.append(event)

    def log_io(self, stream: str, content: str, truncate: bool = False):
        """Log I/O event.

        Args:
            stream: Stream name (stdout|stderr)
            content: Content written
            truncate: Whether to truncate large output
        """
        truncated_content = content[:500] if truncate and len(content) > 500 else content

        self._log_event(
            "io",
            {
                "stream": stream,
                "content_length": len(content),
                "truncated": truncate,
            },
            "info",
        )

    def log_violation(
        self,
        violation_type: str,
        description: str,
        severity: str = "warning",
        context: Optional[Dict[str, Any]] = None,
    ):
        """Log a security violation.

        Args:
            violation_type: Type of violation (forbidden_import|dangerous_call|etc)
            description: Human-readable description
            severity: Severity level (warning|error|critical)
            context: Additional context
        """
        violation = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": violation_type,
            "description": description,
            "severity": severity,
            "context": context or {},
        }
        self.violations.append(violation)

        self._log_event(
            "violation",
            violation,
            severity,
        )

        logger.warning(f"Violation detected: {violation_type} - {description}")

    def log_resource_event(self, metric: str, value: float):
        """Log a resource usage event.

        Args:
            metric: Metric name (memory_mb|cpu_percent|file_operations|etc)
            value: Metric value
        """
        if metric == "memory_mb":
            self.resources.peak_memory_mb = max(self.resources.peak_memory_mb, value)
        elif metric == "cpu_percent":
            self.resources.peak_cpu_percent = max(self.resources.peak_cpu_percent, value)
        elif metric == "file_operations":
            self.resources.file_operations_count += int(value)
        elif metric == "network_operations":
            self.resources.network_operations_count += int(value)

        self._log_event("resource", {"metric": metric, "value": value}, "info")

    def set_exception(self, exc: Exception, traceback_str: Optional[str] = None):
        """Record an exception that occurred during execution.

        Args:
            exc: The exception that occurred
            traceback_str: Optional traceback string
        """
        self.exception = exc
        self.traceback = traceback_str
        self.status = "failed"

        self._log_event(
            "exception",
            {
                "type": type(exc).__name__,
                "message": str(exc),
                "has_traceback": traceback_str is not None,
            },
            "error",
        )

        logger.error(f"Exception during execution: {type(exc).__name__}: {exc}")

    def set_timeout(self):
        """Mark execution as timed out."""
        self.status = "timeout"
        self._log_event("timeout", {}, "critical")
        logger.warning(f"Execution timeout: {self.execution_id}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert execution context to dictionary.

        Returns:
            Complete execution record for logging/analysis
        """
        return {
            "execution_id": self.execution_id,
            "language": self.language,
            "status": self.status,
            "start_time": (
                datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None
            ),
            "end_time": (
                datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None
            ),
            "duration_ms": self.resources.duration_ms,
            "stdout": self.get_stdout()[:1000],  # Truncate for readability
            "stderr": self.get_stderr()[:1000],
            "violations": self.violations,
            "violations_count": len(self.violations),
            "resources": self.resources.to_dict(),
            "events_count": len(self.events),
            "exception": (
                {
                    "type": type(self.exception).__name__,
                    "message": str(self.exception),
                }
                if self.exception
                else None
            ),
        }

    def to_json(self) -> str:
        """Convert execution context to JSON string.

        Returns:
            JSON representation of execution record
        """
        return json.dumps(self.to_dict(), indent=2, default=str)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"ExecutionContext(id={self.execution_id}, status={self.status}, "
            f"duration_ms={self.resources.duration_ms:.1f}, "
            f"violations={len(self.violations)})"
        )
