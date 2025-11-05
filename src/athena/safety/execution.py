"""Real-time execution feedback and monitoring for agent actions."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ExecutionEventType(str, Enum):
    """Types of execution events."""

    TEST_START = "test_start"
    TEST_PASS = "test_pass"
    TEST_FAIL = "test_fail"
    TEST_SKIP = "test_skip"
    ERROR = "error"
    WARNING = "warning"
    LOG = "log"
    METRIC = "metric"
    COVERAGE = "coverage"
    PERFORMANCE = "performance"


class TestStatus(str, Enum):
    """Status of a test."""

    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


class ErrorSeverity(str, Enum):
    """Severity level of an error."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ExecutionContext(BaseModel):
    """Context information about the execution."""

    execution_id: str
    task_id: int
    agent_id: Optional[str] = None
    project_id: int
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None


class ExecutionEvent(BaseModel):
    """Event from live execution (test, error, metric, etc)."""

    id: Optional[int] = None
    execution_id: str  # Links to execution
    timestamp: datetime = Field(default_factory=datetime.now)
    event_type: ExecutionEventType
    sequence: int  # Order in execution sequence

    # Test event fields
    test_name: Optional[str] = None
    test_file: Optional[str] = None
    test_status: Optional[TestStatus] = None
    test_output: Optional[str] = None
    test_duration_ms: Optional[int] = None

    # Error event fields
    error_type: Optional[str] = None
    error_message: str = ""
    error_severity: Optional[ErrorSeverity] = None
    stack_trace: Optional[str] = None
    line_number: Optional[int] = None
    file_path: Optional[str] = None

    # Metric event fields
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    metric_unit: Optional[str] = None
    metric_threshold: Optional[float] = None

    # Coverage event fields
    coverage_percent: Optional[float] = None
    lines_covered: Optional[int] = None
    lines_total: Optional[int] = None
    files_covered: Optional[int] = None

    # Performance event fields
    duration_ms: Optional[int] = None
    memory_mb: Optional[float] = None
    cpu_percent: Optional[float] = None

    # Log output
    log_level: Optional[str] = None  # "debug", "info", "warning", "error"
    log_message: Optional[str] = None

    # General
    raw_output: Optional[str] = None  # Raw output line from tool

    class Config:
        use_enum_values = True


class ExecutionSummary(BaseModel):
    """Summary of execution results."""

    execution_id: str
    task_id: int
    project_id: int
    agent_id: Optional[str] = None

    start_time: datetime
    end_time: datetime
    duration_ms: int

    # Test summary
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    total_test_duration_ms: int = 0

    # Error summary
    total_errors: int = 0
    critical_errors: int = 0
    warnings: int = 0

    # Coverage
    code_coverage_percent: Optional[float] = None
    coverage_trend: Optional[str] = None  # "improving", "declining", "stable"

    # Performance
    avg_memory_mb: Optional[float] = None
    peak_memory_mb: Optional[float] = None
    avg_cpu_percent: Optional[float] = None

    # Overall status
    success: bool = True
    failures_blocking: list[str] = Field(default_factory=list)  # Blocking issues
    warnings_detected: list[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True


class ExecutionCallback:
    """Callback interface for execution events."""

    async def on_event(self, event: ExecutionEvent) -> None:
        """Called when an execution event occurs.

        Args:
            event: The execution event
        """
        pass

    async def on_test_result(
        self, test_name: str, status: TestStatus, duration_ms: int, output: Optional[str] = None
    ) -> None:
        """Called when a test completes.

        Args:
            test_name: Name of the test
            status: Test status
            duration_ms: Duration in milliseconds
            output: Optional test output
        """
        pass

    async def on_error(
        self,
        error_type: str,
        error_message: str,
        severity: ErrorSeverity,
        stack_trace: Optional[str] = None,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
    ) -> None:
        """Called when an error occurs.

        Args:
            error_type: Type of error
            error_message: Error message
            severity: Error severity
            stack_trace: Optional stack trace
            file_path: Optional file path
            line_number: Optional line number
        """
        pass

    async def on_metric(
        self, metric_name: str, metric_value: float, metric_unit: str, threshold: Optional[float] = None
    ) -> None:
        """Called when a metric is recorded.

        Args:
            metric_name: Name of metric
            metric_value: Metric value
            metric_unit: Unit of measurement
            threshold: Optional threshold value
        """
        pass

    async def on_coverage(
        self, coverage_percent: float, lines_covered: int, lines_total: int
    ) -> None:
        """Called when coverage is recorded.

        Args:
            coverage_percent: Coverage percentage
            lines_covered: Lines covered
            lines_total: Total lines
        """
        pass

    async def on_execution_complete(self, summary: ExecutionSummary) -> None:
        """Called when execution completes.

        Args:
            summary: Execution summary
        """
        pass


class ExecutionMonitor:
    """Monitors live agent execution."""

    def __init__(self):
        """Initialize monitor."""
        self.executions: dict[str, ExecutionContext] = {}
        self.events: dict[str, list[ExecutionEvent]] = {}
        self.callbacks: list[ExecutionCallback] = []
        self.sequence_counters: dict[str, int] = {}

    def start_execution(
        self,
        execution_id: str,
        task_id: int,
        project_id: int,
        agent_id: Optional[str] = None,
    ) -> ExecutionContext:
        """Start tracking an execution.

        Args:
            execution_id: Unique execution ID
            task_id: Task ID
            project_id: Project ID
            agent_id: Optional agent ID

        Returns:
            ExecutionContext
        """
        context = ExecutionContext(
            execution_id=execution_id,
            task_id=task_id,
            project_id=project_id,
            agent_id=agent_id,
        )
        self.executions[execution_id] = context
        self.events[execution_id] = []
        self.sequence_counters[execution_id] = 0
        return context

    async def record_event(self, execution_id: str, event: ExecutionEvent) -> ExecutionEvent:
        """Record an execution event.

        Args:
            execution_id: Execution ID
            event: The event to record

        Returns:
            The recorded event (with sequence number added)
        """
        if execution_id not in self.events:
            self.events[execution_id] = []

        # Add sequence number
        event.sequence = self.sequence_counters.get(execution_id, 0)
        self.sequence_counters[execution_id] = event.sequence + 1

        self.events[execution_id].append(event)

        # Trigger callbacks
        for callback in self.callbacks:
            await callback.on_event(event)

        # Trigger specific callbacks based on event type
        if event.event_type in [
            ExecutionEventType.TEST_PASS,
            ExecutionEventType.TEST_FAIL,
            ExecutionEventType.TEST_SKIP,
        ]:
            for callback in self.callbacks:
                status = TestStatus(event.test_status) if event.test_status else TestStatus.SKIP
                await callback.on_test_result(
                    event.test_name or "",
                    status,
                    event.test_duration_ms or 0,
                    event.test_output,
                )
        elif event.event_type == ExecutionEventType.ERROR:
            for callback in self.callbacks:
                await callback.on_error(
                    event.error_type or "unknown",
                    event.error_message,
                    ErrorSeverity(event.error_severity) if event.error_severity else ErrorSeverity.ERROR,
                    event.stack_trace,
                    event.file_path,
                    event.line_number,
                )
        elif event.event_type == ExecutionEventType.METRIC:
            for callback in self.callbacks:
                await callback.on_metric(
                    event.metric_name or "",
                    event.metric_value or 0.0,
                    event.metric_unit or "",
                    event.metric_threshold,
                )
        elif event.event_type == ExecutionEventType.COVERAGE:
            for callback in self.callbacks:
                await callback.on_coverage(
                    event.coverage_percent or 0.0,
                    event.lines_covered or 0,
                    event.lines_total or 0,
                )

        return event

    async def end_execution(self, execution_id: str) -> ExecutionSummary:
        """Complete execution and generate summary.

        Args:
            execution_id: Execution ID

        Returns:
            ExecutionSummary
        """
        context = self.executions[execution_id]
        context.end_time = datetime.now()
        context.duration_ms = int((context.end_time - context.start_time).total_seconds() * 1000)

        events = self.events.get(execution_id, [])

        # Summarize events
        summary = ExecutionSummary(
            execution_id=execution_id,
            task_id=context.task_id,
            project_id=context.project_id,
            agent_id=context.agent_id,
            start_time=context.start_time,
            end_time=context.end_time,
            duration_ms=context.duration_ms,
        )

        for event in events:
            if event.event_type == ExecutionEventType.TEST_PASS:
                summary.total_tests += 1
                summary.passed_tests += 1
                summary.total_test_duration_ms += event.test_duration_ms or 0
            elif event.event_type == ExecutionEventType.TEST_FAIL:
                summary.total_tests += 1
                summary.failed_tests += 1
                summary.total_test_duration_ms += event.test_duration_ms or 0
                if event.test_name:
                    summary.failures_blocking.append(f"Test failed: {event.test_name}")
            elif event.event_type == ExecutionEventType.TEST_SKIP:
                summary.total_tests += 1
                summary.skipped_tests += 1
            elif event.event_type == ExecutionEventType.ERROR:
                summary.total_errors += 1
                if event.error_severity == ErrorSeverity.CRITICAL:
                    summary.critical_errors += 1
                if event.error_message:
                    summary.failures_blocking.append(f"Error: {event.error_message}")
            elif event.event_type == ExecutionEventType.WARNING:
                summary.warnings += 1
                if event.log_message:
                    summary.warnings_detected.append(event.log_message)
            elif event.event_type == ExecutionEventType.COVERAGE:
                summary.code_coverage_percent = event.coverage_percent

        # Overall success: no critical errors and no test failures
        summary.success = summary.critical_errors == 0 and summary.failed_tests == 0

        # Trigger completion callbacks
        for callback in self.callbacks:
            await callback.on_execution_complete(summary)

        return summary

    def register_callback(self, callback: ExecutionCallback) -> None:
        """Register an execution callback.

        Args:
            callback: The callback to register
        """
        self.callbacks.append(callback)

    def get_events(self, execution_id: str) -> list[ExecutionEvent]:
        """Get all events for an execution.

        Args:
            execution_id: Execution ID

        Returns:
            List of ExecutionEvent objects
        """
        return self.events.get(execution_id, [])

    def get_context(self, execution_id: str) -> Optional[ExecutionContext]:
        """Get execution context.

        Args:
            execution_id: Execution ID

        Returns:
            ExecutionContext or None
        """
        return self.executions.get(execution_id)
