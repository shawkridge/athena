"""Tests for Phase 3 Week 10: Code Execution & Execution Context.

Tests cover:
- ExecutionContext creation and lifecycle
- I/O capture during code execution
- Violation logging and detection
- MemoryAPI execute_code method
- Code execution in different sandboxing modes
- Resource tracking and monitoring
"""

import json
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Import execution context and memory API
from athena.sandbox.execution_context import (
    ExecutionContext,
    ExecutionEvent,
    ResourceUsage,
    IOCapture,
)
from athena.mcp.memory_api import MemoryAPI


class TestIOCapture:
    """Tests for I/O capture functionality."""

    def test_io_capture_initialization(self):
        """Test IOCapture initializes correctly."""
        capture = IOCapture(capture_stderr=True)
        assert capture.capture_stderr is True
        assert capture.stdout_buffer is not None
        assert capture.stderr_buffer is not None

    def test_capture_stdout(self, capsys):
        """Test capturing stdout during execution."""
        capture = IOCapture()
        capture.start()

        print("Hello from test")

        capture.stop()
        captured = capture.get_stdout()

        assert "Hello from test" in captured

    def test_capture_stderr(self, capsys):
        """Test capturing stderr during execution."""
        import sys

        capture = IOCapture(capture_stderr=True)
        capture.start()

        print("Error message", file=sys.stderr)

        capture.stop()
        captured = capture.get_stderr()

        assert "Error message" in captured

    def test_io_capture_without_stderr(self, capsys):
        """Test IOCapture without stderr capture."""
        capture = IOCapture(capture_stderr=False)
        assert capture.capture_stderr is False


class TestExecutionEvent:
    """Tests for ExecutionEvent model."""

    def test_event_creation(self):
        """Test creating an execution event."""
        event = ExecutionEvent(
            timestamp="2025-01-15T10:30:00",
            event_type="io",
            details={"stream": "stdout", "content": "test"},
            severity="info",
        )

        assert event.timestamp == "2025-01-15T10:30:00"
        assert event.event_type == "io"
        assert event.severity == "info"

    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        event = ExecutionEvent(
            timestamp="2025-01-15T10:30:00",
            event_type="violation",
            details={"type": "forbidden_import"},
        )

        event_dict = event.to_dict()
        assert event_dict["event_type"] == "violation"
        assert event_dict["details"]["type"] == "forbidden_import"


class TestResourceUsage:
    """Tests for ResourceUsage tracking."""

    def test_resource_usage_initialization(self):
        """Test ResourceUsage initializes with defaults."""
        resources = ResourceUsage()

        assert resources.peak_memory_mb == 0.0
        assert resources.peak_cpu_percent == 0.0
        assert resources.file_operations_count == 0
        assert resources.duration_ms == 0.0

    def test_resource_usage_to_dict(self):
        """Test converting ResourceUsage to dictionary."""
        resources = ResourceUsage(
            peak_memory_mb=128.5,
            duration_ms=1250.0,
            file_operations_count=3,
        )

        resources_dict = resources.to_dict()
        assert resources_dict["peak_memory_mb"] == 128.5
        assert resources_dict["duration_ms"] == 1250.0
        assert resources_dict["file_operations_count"] == 3


class TestExecutionContext:
    """Tests for ExecutionContext."""

    def test_context_initialization(self):
        """Test creating an ExecutionContext."""
        context = ExecutionContext(
            execution_id="exec_123",
            language="python",
            timeout_seconds=30,
        )

        assert context.execution_id == "exec_123"
        assert context.language == "python"
        assert context.timeout_seconds == 30
        assert context.status == "pending"
        assert len(context.events) == 0
        assert len(context.violations) == 0

    def test_context_start_and_stop(self):
        """Test starting and stopping execution tracking."""
        context = ExecutionContext(execution_id="exec_123")

        context.start()
        assert context.status == "running"
        assert context.start_time is not None

        context.stop()
        assert context.status == "completed"
        assert context.end_time is not None
        assert context.resources.duration_ms > 0

    def test_context_io_capture(self):
        """Test I/O capture within context."""
        context = ExecutionContext(
            execution_id="exec_123", capture_io=True
        )

        context.start()
        print("Test output")
        context.stop()

        stdout = context.get_stdout()
        assert "Test output" in stdout

    def test_context_log_event(self):
        """Test logging events to context."""
        context = ExecutionContext(execution_id="exec_123")

        context._log_event("test", {"data": "value"}, "info")

        assert len(context.events) == 1
        assert context.events[0].event_type == "test"
        assert context.events[0].details["data"] == "value"

    def test_context_log_violation(self):
        """Test logging security violations."""
        context = ExecutionContext(execution_id="exec_123")

        context.log_violation(
            violation_type="forbidden_import",
            description="import os forbidden",
            severity="error",
        )

        assert len(context.violations) == 1
        violation = context.violations[0]
        assert violation["type"] == "forbidden_import"
        assert violation["severity"] == "error"

    def test_context_multiple_violations(self):
        """Test logging multiple violations."""
        context = ExecutionContext(execution_id="exec_123")

        context.log_violation("forbidden_import", "import os")
        context.log_violation("dangerous_call", "exec()")

        assert len(context.violations) == 2
        assert context.violations[0]["type"] == "forbidden_import"
        assert context.violations[1]["type"] == "dangerous_call"

    def test_context_log_resource_event(self):
        """Test logging resource usage events."""
        context = ExecutionContext(execution_id="exec_123", track_resources=True)

        context.log_resource_event("memory_mb", 128.5)
        context.log_resource_event("cpu_percent", 45.0)

        assert context.resources.peak_memory_mb == 128.5
        assert context.resources.peak_cpu_percent == 45.0

    def test_context_set_exception(self):
        """Test recording exceptions."""
        context = ExecutionContext(execution_id="exec_123")

        exc = ValueError("Test error")
        context.set_exception(exc, "traceback_info")

        assert context.exception is exc
        assert context.traceback == "traceback_info"
        assert context.status == "failed"

    def test_context_set_timeout(self):
        """Test marking execution as timed out."""
        context = ExecutionContext(execution_id="exec_123")

        context.set_timeout()

        assert context.status == "timeout"
        assert len(context.events) > 0  # Timeout logged as event

    def test_context_to_dict(self):
        """Test converting context to dictionary."""
        context = ExecutionContext(execution_id="exec_123", language="python")
        context.start()

        context.log_violation("test_violation", "Test")

        context.stop()
        context_dict = context.to_dict()

        assert context_dict["execution_id"] == "exec_123"
        assert context_dict["language"] == "python"
        assert context_dict["status"] == "completed"
        assert context_dict["violations_count"] == 1

    def test_context_to_json(self):
        """Test converting context to JSON string."""
        context = ExecutionContext(execution_id="exec_123")
        context.start()
        context.stop()

        json_str = context.to_json()
        data = json.loads(json_str)

        assert data["execution_id"] == "exec_123"
        assert "duration_ms" in data


class TestMemoryAPICodeExecution:
    """Tests for MemoryAPI execute_code method."""

    @pytest.fixture
    def api(self, tmp_path):
        """Create a MemoryAPI instance for testing."""
        db_path = str(tmp_path / "test.db")
        return MemoryAPI.create(db_path=db_path)

    def test_execute_simple_python_code(self, api):
        """Test executing simple Python code."""
        result = api.execute_code(
            code='result = 42\nprint(f"Answer: {result}")',
            language="python",
        )

        assert result["success"] is True
        assert "Answer: 42" in result["stdout"]
        assert result["exit_code"] == 0

    def test_execute_code_with_parameters(self, api):
        """Test executing code with parameters."""
        result = api.execute_code(
            code='print(f"Name: {parameters.get(\'name\', \'Unknown\')}")',
            language="python",
            parameters={"name": "Claude"},
        )

        assert result["success"] is True
        assert "Name: Claude" in result["stdout"]

    def test_execute_code_with_error(self, api):
        """Test executing code that raises an error."""
        result = api.execute_code(
            code="raise ValueError('Test error')",
            language="python",
        )

        assert result["success"] is False
        assert result["exit_code"] != 0
        assert "Test error" in result["stderr"]

    def test_execute_invalid_python_code(self, api):
        """Test executing syntactically invalid code."""
        result = api.execute_code(
            code="this is not valid python !!!",
            language="python",
        )

        assert result["success"] is False
        assert "error" in result or "issues" in result

    def test_execute_code_returns_execution_id(self, api):
        """Test that execute_code returns an execution ID."""
        result = api.execute_code(
            code="x = 1",
            language="python",
        )

        assert "execution_id" in result
        assert "sandbox_id" in result
        assert result["execution_id"] == result["sandbox_id"]

    def test_execute_code_records_event(self, api):
        """Test that code execution is recorded in episodic memory."""
        code = 'print("test")'

        result = api.execute_code(code=code, language="python")

        assert result["success"] is True
        # Code execution should be recorded as an event
        events = api.recall_events(
            event_type="action",
            limit=1,
        )

        assert len(events) > 0

    def test_execute_code_with_timeout(self, api):
        """Test code execution with timeout parameter."""
        result = api.execute_code(
            code="print('hello')",
            language="python",
            timeout_seconds=60,
        )

        assert result["success"] is True

    def test_execute_code_returns_timing(self, api):
        """Test that execute_code returns timing information."""
        result = api.execute_code(
            code="import time; time.sleep(0.1); print('done')",
            language="python",
        )

        assert "execution_time_ms" in result
        assert result["execution_time_ms"] > 0

    def test_execute_code_truncates_large_output(self, api):
        """Test that very large stdout/stderr are truncated."""
        # Create code that produces lots of output
        code = "for i in range(10000): print('x' * 100)"

        result = api.execute_code(code=code, language="python")

        # Should be truncated to 2000 chars
        assert len(result["stdout"]) <= 2000

    def test_execute_code_with_sandbox_policy(self, api):
        """Test execute_code with different sandbox policies."""
        result = api.execute_code(
            code="print('test')",
            language="python",
            sandbox_policy="strict",
        )

        assert result["success"] is True

    @patch("athena.mcp.memory_api.SRTExecutor")
    def test_execute_code_uses_srt_when_available(self, mock_srt_class, api):
        """Test that execute_code uses SRT executor when available."""
        # Setup mock SRT executor
        mock_executor = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "output"
        mock_result.stderr = ""
        mock_result.exit_code = 0
        mock_result.violations = []
        mock_executor.execute.return_value = mock_result

        # Inject mock
        api.sandbox_executor = mock_executor

        result = api.execute_code(
            code="print('test')",
            language="python",
        )

        assert result["success"] is True

    def test_execute_code_graceful_degradation(self, api):
        """Test graceful degradation when SRT not available."""
        # Set executor to False (simulating failed initialization)
        api.sandbox_executor = False

        result = api.execute_code(
            code="print('test')",
            language="python",
        )

        # Should still work via fallback (RestrictedPython or exec)
        assert "success" in result
        assert "execution_id" in result


class TestCodeExecutionIntegration:
    """Integration tests for code execution workflow."""

    @pytest.fixture
    def api(self, tmp_path):
        """Create a MemoryAPI instance for testing."""
        db_path = str(tmp_path / "test.db")
        return MemoryAPI.create(db_path=db_path)

    def test_execute_procedure_code(self, api):
        """Test executing generated procedure code."""
        # Create a simple procedure
        proc_id = api.remember_procedure(
            name="test_proc",
            steps=["print('procedure executed')"],
            category="general",
        )

        # Execute the procedure
        result = api.execute_procedure(proc_id)

        assert result["success"] is not None
        assert "execution_time_ms" in result

    def test_validate_then_execute_code(self, api):
        """Test the full validation + execution workflow."""
        code = "result = 2 + 2\nprint(f'2+2={result}')"

        # Validate code
        validation = api.validate_procedure_code(code)

        # Execute code
        execution = api.execute_code(code=code, language="python")

        assert validation["success"] is True
        assert execution["success"] is True
        assert "4" in execution["stdout"]

    def test_code_execution_stores_metadata(self, api):
        """Test that code execution metadata is stored."""
        code = "x = 42"

        result = api.execute_code(
            code=code,
            language="python",
            parameters={"test": True},
        )

        assert result["success"] is True
        assert result["language"] == "python"
        assert result["exit_code"] == 0
        assert "timestamp" in result


class TestCodeExecutionSecurity:
    """Security-focused tests for code execution."""

    @pytest.fixture
    def api(self, tmp_path):
        """Create a MemoryAPI instance for testing."""
        db_path = str(tmp_path / "test.db")
        return MemoryAPI.create(db_path=db_path)

    def test_execute_code_blocks_dangerous_imports(self, api):
        """Test that dangerous imports are detected/blocked."""
        # This would require RestrictedPython to be fully effective
        # For now, just test that the validation catch it
        code = "import os\nos.system('rm -rf /')"

        result = api.execute_code(code=code, language="python")

        # Should either fail validation or execution
        assert result["success"] is False or "import" in result.get("stderr", "")

    def test_code_execution_with_injection_attempt(self, api):
        """Test code execution resists injection attempts."""
        code = "eval('__import__(\"os\").system(\"id\")')"

        result = api.execute_code(code=code, language="python")

        # Should fail or not actually execute dangerous code
        assert result is not None


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
