"""Unit tests for ExecutionMonitor and execution feedback."""

import pytest
import asyncio
from datetime import datetime

from athena.safety.execution import (
    ExecutionMonitor,
    ExecutionEvent,
    ExecutionEventType,
    ExecutionContext,
    ExecutionSummary,
    TestStatus,
    ErrorSeverity,
    ExecutionCallback,
)


class TestCallback(ExecutionCallback):
    """Test callback implementation."""

    def __init__(self):
        """Initialize test callback."""
        self.events = []
        self.test_results = []
        self.errors = []
        self.metrics = []
        self.summaries = []

    async def on_event(self, event: ExecutionEvent) -> None:
        """Record all events."""
        self.events.append(event)

    async def on_test_result(
        self, test_name: str, status: TestStatus, duration_ms: int, output: str = None
    ) -> None:
        """Record test results."""
        self.test_results.append({
            "test_name": test_name,
            "status": status,
            "duration_ms": duration_ms,
            "output": output,
        })

    async def on_error(
        self,
        error_type: str,
        error_message: str,
        severity: ErrorSeverity,
        stack_trace: str = None,
        file_path: str = None,
        line_number: int = None,
    ) -> None:
        """Record errors."""
        self.errors.append({
            "error_type": error_type,
            "error_message": error_message,
            "severity": severity,
            "stack_trace": stack_trace,
            "file_path": file_path,
            "line_number": line_number,
        })

    async def on_metric(
        self, metric_name: str, metric_value: float, metric_unit: str, threshold: float = None
    ) -> None:
        """Record metrics."""
        self.metrics.append({
            "metric_name": metric_name,
            "metric_value": metric_value,
            "metric_unit": metric_unit,
            "threshold": threshold,
        })

    async def on_execution_complete(self, summary: ExecutionSummary) -> None:
        """Record execution complete."""
        self.summaries.append(summary)


@pytest.fixture
def monitor():
    """Create an ExecutionMonitor instance."""
    return ExecutionMonitor()


@pytest.fixture
def callback():
    """Create a test callback."""
    return TestCallback()


class TestExecutionContext:
    """Tests for ExecutionContext."""

    def test_create_context(self, monitor):
        """Test creating execution context."""
        context = monitor.start_execution(
            execution_id="exec-001",
            task_id=1,
            project_id=1,
            agent_id="agent-1",
        )
        assert context.execution_id == "exec-001"
        assert context.task_id == 1
        assert context.project_id == 1
        assert context.agent_id == "agent-1"

    def test_context_has_start_time(self, monitor):
        """Test context has start time."""
        context = monitor.start_execution(
            execution_id="exec-001",
            task_id=1,
            project_id=1,
        )
        assert context.start_time is not None
        assert isinstance(context.start_time, datetime)


class TestEventRecording:
    """Tests for event recording."""

    @pytest.mark.asyncio
    async def test_record_test_event(self, monitor, callback):
        """Test recording a test event."""
        monitor.register_callback(callback)
        context = monitor.start_execution(
            execution_id="exec-001",
            task_id=1,
            project_id=1,
        )

        event = ExecutionEvent(
            execution_id="exec-001",
            event_type=ExecutionEventType.TEST_PASS,
            test_name="test_auth_login",
            test_status=TestStatus.PASS,
            test_duration_ms=245,
        )

        recorded = await monitor.record_event("exec-001", event)
        assert recorded.sequence == 0

    @pytest.mark.asyncio
    async def test_record_error_event(self, monitor, callback):
        """Test recording an error event."""
        monitor.register_callback(callback)
        monitor.start_execution("exec-001", task_id=1, project_id=1)

        event = ExecutionEvent(
            execution_id="exec-001",
            event_type=ExecutionEventType.ERROR,
            error_type="AssertionError",
            error_message="Expected 200, got 401",
            error_severity=ErrorSeverity.ERROR,
            file_path="tests/test_api.py",
            line_number=45,
        )

        await monitor.record_event("exec-001", event)
        assert len(callback.errors) == 1
        assert callback.errors[0]["error_type"] == "AssertionError"

    @pytest.mark.asyncio
    async def test_record_metric_event(self, monitor, callback):
        """Test recording a metric event."""
        monitor.register_callback(callback)
        monitor.start_execution("exec-001", task_id=1, project_id=1)

        event = ExecutionEvent(
            execution_id="exec-001",
            event_type=ExecutionEventType.METRIC,
            metric_name="response_time",
            metric_value=142.5,
            metric_unit="ms",
            metric_threshold=200.0,
        )

        await monitor.record_event("exec-001", event)
        assert len(callback.metrics) == 1
        assert callback.metrics[0]["metric_name"] == "response_time"

    @pytest.mark.asyncio
    async def test_event_sequence(self, monitor):
        """Test event sequencing."""
        monitor.start_execution("exec-001", task_id=1, project_id=1)

        events = []
        for i in range(5):
            event = ExecutionEvent(
                execution_id="exec-001",
                event_type=ExecutionEventType.LOG,
                log_level="info",
                log_message=f"Message {i}",
            )
            recorded = await monitor.record_event("exec-001", event)
            events.append(recorded)

        # Check sequence numbering
        for i, event in enumerate(events):
            assert event.sequence == i


class TestExecutionSummary:
    """Tests for execution summary."""

    @pytest.mark.asyncio
    async def test_summary_all_pass(self, monitor, callback):
        """Test summary with all passing tests."""
        monitor.register_callback(callback)
        monitor.start_execution("exec-001", task_id=1, project_id=1)

        # Record passing tests
        for i in range(5):
            event = ExecutionEvent(
                execution_id="exec-001",
                event_type=ExecutionEventType.TEST_PASS,
                test_name=f"test_{i}",
                test_status=TestStatus.PASS,
                test_duration_ms=100 + i * 10,
            )
            await monitor.record_event("exec-001", event)

        summary = await monitor.end_execution("exec-001")
        assert summary.total_tests == 5
        assert summary.passed_tests == 5
        assert summary.failed_tests == 0
        assert summary.success is True

    @pytest.mark.asyncio
    async def test_summary_with_failures(self, monitor, callback):
        """Test summary with test failures."""
        monitor.register_callback(callback)
        monitor.start_execution("exec-001", task_id=1, project_id=1)

        # Record passing tests
        for i in range(3):
            event = ExecutionEvent(
                execution_id="exec-001",
                event_type=ExecutionEventType.TEST_PASS,
                test_name=f"test_pass_{i}",
                test_status=TestStatus.PASS,
                test_duration_ms=100,
            )
            await monitor.record_event("exec-001", event)

        # Record failing tests
        for i in range(2):
            event = ExecutionEvent(
                execution_id="exec-001",
                event_type=ExecutionEventType.TEST_FAIL,
                test_name=f"test_fail_{i}",
                test_status=TestStatus.FAIL,
                test_duration_ms=150,
                test_output=f"AssertionError: expected X, got Y",
            )
            await monitor.record_event("exec-001", event)

        summary = await monitor.end_execution("exec-001")
        assert summary.total_tests == 5
        assert summary.passed_tests == 3
        assert summary.failed_tests == 2
        assert summary.success is False
        assert len(summary.failures_blocking) == 2

    @pytest.mark.asyncio
    async def test_summary_with_errors(self, monitor, callback):
        """Test summary with errors."""
        monitor.register_callback(callback)
        monitor.start_execution("exec-001", task_id=1, project_id=1)

        # Record errors
        event = ExecutionEvent(
            execution_id="exec-001",
            event_type=ExecutionEventType.ERROR,
            error_type="RuntimeError",
            error_message="Database connection failed",
            error_severity=ErrorSeverity.CRITICAL,
        )
        await monitor.record_event("exec-001", event)

        summary = await monitor.end_execution("exec-001")
        assert summary.total_errors == 1
        assert summary.critical_errors == 1
        assert summary.success is False

    @pytest.mark.asyncio
    async def test_summary_with_coverage(self, monitor, callback):
        """Test summary with code coverage."""
        monitor.register_callback(callback)
        monitor.start_execution("exec-001", task_id=1, project_id=1)

        event = ExecutionEvent(
            execution_id="exec-001",
            event_type=ExecutionEventType.COVERAGE,
            coverage_percent=87.5,
            lines_covered=875,
            lines_total=1000,
        )
        await monitor.record_event("exec-001", event)

        summary = await monitor.end_execution("exec-001")
        assert summary.code_coverage_percent == 87.5

    @pytest.mark.asyncio
    async def test_summary_duration(self, monitor):
        """Test execution duration in summary."""
        monitor.start_execution("exec-001", task_id=1, project_id=1)

        # Simulate some work
        await asyncio.sleep(0.01)  # 10ms

        summary = await monitor.end_execution("exec-001")
        assert summary.duration_ms >= 10
        assert summary.end_time > summary.start_time


class TestCallbacks:
    """Tests for callback registration and invocation."""

    @pytest.mark.asyncio
    async def test_register_callback(self, monitor, callback):
        """Test registering a callback."""
        monitor.register_callback(callback)
        assert len(monitor.callbacks) == 1

    @pytest.mark.asyncio
    async def test_multiple_callbacks(self, monitor):
        """Test multiple callbacks."""
        callback1 = TestCallback()
        callback2 = TestCallback()
        monitor.register_callback(callback1)
        monitor.register_callback(callback2)

        monitor.start_execution("exec-001", task_id=1, project_id=1)
        event = ExecutionEvent(
            execution_id="exec-001",
            event_type=ExecutionEventType.TEST_PASS,
            test_name="test_1",
            test_status=TestStatus.PASS,
            test_duration_ms=100,
        )
        await monitor.record_event("exec-001", event)

        assert len(callback1.events) == 1
        assert len(callback2.events) == 1

    @pytest.mark.asyncio
    async def test_callback_completion(self, monitor, callback):
        """Test callback on execution complete."""
        monitor.register_callback(callback)
        monitor.start_execution("exec-001", task_id=1, project_id=1)

        event = ExecutionEvent(
            execution_id="exec-001",
            event_type=ExecutionEventType.TEST_PASS,
            test_name="test_1",
            test_status=TestStatus.PASS,
            test_duration_ms=100,
        )
        await monitor.record_event("exec-001", event)

        summary = await monitor.end_execution("exec-001")

        assert len(callback.summaries) == 1
        assert callback.summaries[0].success is True


class TestEventTypes:
    """Tests for different event types."""

    @pytest.mark.asyncio
    async def test_all_event_types(self, monitor):
        """Test recording all event types."""
        monitor.start_execution("exec-001", task_id=1, project_id=1)

        event_types = [
            ExecutionEventType.TEST_START,
            ExecutionEventType.TEST_PASS,
            ExecutionEventType.ERROR,
            ExecutionEventType.WARNING,
            ExecutionEventType.LOG,
            ExecutionEventType.METRIC,
            ExecutionEventType.COVERAGE,
            ExecutionEventType.PERFORMANCE,
        ]

        for event_type in event_types:
            event = ExecutionEvent(
                execution_id="exec-001",
                event_type=event_type,
                log_message="test message",
            )
            await monitor.record_event("exec-001", event)

        events = monitor.get_events("exec-001")
        assert len(events) == len(event_types)


class TestContextManagement:
    """Tests for execution context management."""

    def test_get_context(self, monitor):
        """Test retrieving execution context."""
        context = monitor.start_execution("exec-001", task_id=1, project_id=1)
        retrieved = monitor.get_context("exec-001")
        assert retrieved == context

    def test_get_events(self, monitor):
        """Test retrieving recorded events."""
        monitor.start_execution("exec-001", task_id=1, project_id=1)
        events = monitor.get_events("exec-001")
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_get_events_after_recording(self, monitor):
        """Test retrieving events after recording."""
        monitor.start_execution("exec-001", task_id=1, project_id=1)

        event = ExecutionEvent(
            execution_id="exec-001",
            event_type=ExecutionEventType.TEST_PASS,
            test_name="test_1",
            test_status=TestStatus.PASS,
            test_duration_ms=100,
        )
        await monitor.record_event("exec-001", event)

        events = monitor.get_events("exec-001")
        assert len(events) == 1
        assert events[0].test_name == "test_1"
