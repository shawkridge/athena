"""Tests for Strategy 1 - Error diagnosis and failure analysis."""

import pytest
from athena.learning.error_diagnostician import (
    ErrorDiagnostician,
    DiagnosedError,
    ErrorPattern,
    ErrorFrequency,
)


@pytest.fixture
def error_diagnostician():
    """Create error diagnostician for testing."""
    return ErrorDiagnostician()


class TestErrorDiagnostician:
    """Tests for ErrorDiagnostician class."""

    def test_error_diagnostician_creation(self, error_diagnostician):
        """Test error diagnostician initializes correctly."""
        assert error_diagnostician is not None
        assert isinstance(error_diagnostician, ErrorDiagnostician)

    def test_diagnose_attribute_error(self, error_diagnostician):
        """Test diagnosing an AttributeError."""
        stack_trace = """Traceback (most recent call last):
  File "src/main.py", line 42, in process_data
    value = obj.nonexistent_attribute
AttributeError: 'MyClass' object has no attribute 'nonexistent_attribute'
"""

        diagnosed = error_diagnostician.diagnose(
            error_type="AttributeError",
            message="'MyClass' object has no attribute 'nonexistent_attribute'",
            stack_trace=stack_trace,
            context={"obj_type": "MyClass"},
        )

        assert diagnosed.error_type == "AttributeError"
        assert diagnosed.error_id.startswith("err_")
        assert "attribute" in diagnosed.root_cause.lower()
        assert diagnosed.severity in ["low", "medium", "high", "critical"]
        assert diagnosed.solution is not None
        assert diagnosed.prevention is not None
        assert len(diagnosed.reproduction_steps) > 0

    def test_diagnose_type_error(self, error_diagnostician):
        """Test diagnosing a TypeError."""
        stack_trace = """Traceback (most recent call last):
  File "src/calc.py", line 15, in add
    return a + b
TypeError: unsupported operand type(s) for +: 'int' and 'str'
"""

        diagnosed = error_diagnostician.diagnose(
            error_type="TypeError",
            message="unsupported operand type(s) for +: 'int' and 'str'",
            stack_trace=stack_trace,
        )

        assert diagnosed.error_type == "TypeError"
        assert "type" in diagnosed.root_cause.lower()
        assert "Verify the type" in diagnosed.solution

    def test_diagnose_value_error(self, error_diagnostician):
        """Test diagnosing a ValueError."""
        diagnosed = error_diagnostician.diagnose(
            error_type="ValueError",
            message="invalid literal for int() with base 10: 'abc'",
            stack_trace="ValueError: invalid literal for int() with base 10: 'abc'",
        )

        assert diagnosed.error_type == "ValueError"
        assert "Validate" in diagnosed.solution

    def test_diagnose_key_error(self, error_diagnostician):
        """Test diagnosing a KeyError."""
        diagnosed = error_diagnostician.diagnose(
            error_type="KeyError",
            message="'missing_key'",
            stack_trace="KeyError: 'missing_key'",
        )

        assert diagnosed.error_type == "KeyError"
        assert ".get()" in diagnosed.solution

    def test_diagnose_index_error(self, error_diagnostician):
        """Test diagnosing an IndexError."""
        diagnosed = error_diagnostician.diagnose(
            error_type="IndexError",
            message="list index out of range",
            stack_trace="IndexError: list index out of range",
        )

        assert diagnosed.error_type == "IndexError"
        assert "length" in diagnosed.solution.lower()

    def test_diagnose_connection_error(self, error_diagnostician):
        """Test diagnosing a ConnectionError."""
        diagnosed = error_diagnostician.diagnose(
            error_type="ConnectionError",
            message="Failed to connect to database",
            stack_trace="ConnectionError: Failed to connect",
            context={"service": "database"},
        )

        assert diagnosed.error_type == "ConnectionError"
        # ConnectionError maps to "high" severity when "connection" is in message
        assert diagnosed.severity in ["high", "medium"]
        assert diagnosed.solution is not None

    def test_diagnose_timeout_error(self, error_diagnostician):
        """Test diagnosing a TimeoutError."""
        diagnosed = error_diagnostician.diagnose(
            error_type="TimeoutError",
            message="Operation timed out",
            stack_trace="TimeoutError: Operation timed out",
        )

        assert diagnosed.error_type == "TimeoutError"
        # TimeoutError has "timeout" in message, so severity is "high"
        assert diagnosed.severity in ["high", "medium"]
        assert diagnosed.solution is not None

    def test_diagnose_memory_error(self, error_diagnostician):
        """Test diagnosing a critical MemoryError."""
        diagnosed = error_diagnostician.diagnose(
            error_type="MemoryError",
            message="Unable to allocate memory",
            stack_trace="MemoryError: Unable to allocate memory",
        )

        assert diagnosed.error_type == "MemoryError"
        assert diagnosed.severity == "critical"

    def test_analyze_traceback(self, error_diagnostician):
        """Test analyzing a Python traceback."""
        traceback_str = """Traceback (most recent call last):
  File "src/app.py", line 123, in main
    result = process()
  File "src/processor.py", line 45, in process
    return data.transform()
AttributeError: 'NoneType' object has no attribute 'transform'
"""

        analysis = error_diagnostician.analyze_traceback(traceback_str)

        assert "error_type" in analysis
        assert "message" in analysis
        assert "file" in analysis
        assert "line" in analysis
        assert "full_trace" in analysis
        assert analysis["error_type"] == "AttributeError"

    def test_analyze_traceback_with_multiple_frames(self, error_diagnostician):
        """Test analyzing complex multi-frame traceback."""
        traceback_str = """Traceback (most recent call last):
  File "src/main.py", line 10, in <module>
    app.run()
  File "src/app.py", line 50, in run
    result = self.process_request(request)
  File "src/handler.py", line 30, in process_request
    return database.query(request.query)
  File "src/db.py", line 100, in query
    return self.execute(sql)
ConnectionError: Connection lost
"""

        analysis = error_diagnostician.analyze_traceback(traceback_str)

        assert analysis["error_type"] == "ConnectionError"
        assert "db.py" in analysis["file"]

    def test_get_error_frequency(self, error_diagnostician):
        """Test getting error frequency information."""
        # Diagnose same error multiple times
        for i in range(3):
            error_diagnostician.diagnose(
                error_type="ValueError",
                message="Invalid input",
                stack_trace="ValueError: Invalid input",
            )

        frequency = error_diagnostician.get_error_frequency("ValueError")

        assert frequency is not None
        assert frequency.error_type == "ValueError"
        assert frequency.occurrences == 3
        assert frequency.frequency_trend in [
            "increasing",
            "stable",
            "decreasing",
            "insufficient_data",
        ]

    def test_get_error_frequency_nonexistent(self, error_diagnostician):
        """Test getting frequency for error type that hasn't occurred."""
        frequency = error_diagnostician.get_error_frequency("NonexistentError")

        assert frequency is None

    def test_get_error_summary(self, error_diagnostician):
        """Test getting summary of all diagnosed errors."""
        # Diagnose various errors
        error_diagnostician.diagnose(
            error_type="ValueError",
            message="Invalid value",
            stack_trace="ValueError",
        )
        error_diagnostician.diagnose(
            error_type="ValueError",
            message="Invalid value",
            stack_trace="ValueError",
        )
        error_diagnostician.diagnose(
            error_type="TypeError",
            message="Wrong type",
            stack_trace="TypeError",
        )
        error_diagnostician.diagnose(
            error_type="MemoryError",
            message="Out of memory",
            stack_trace="MemoryError",
        )

        summary = error_diagnostician.get_error_summary()

        assert "total_errors" in summary
        assert summary["total_errors"] >= 4
        assert "error_types" in summary
        assert "critical" in summary
        assert "high" in summary
        assert "most_common" in summary

    def test_prevent_future_errors(self, error_diagnostician):
        """Test getting prevention recommendations."""
        # Diagnose multiple errors
        for i in range(5):
            error_diagnostician.diagnose(
                error_type="ValueError",
                message="Invalid input",
                stack_trace="ValueError",
            )

        recommendations = error_diagnostician.prevent_future_errors()

        assert isinstance(recommendations, list)
        # Should provide recommendations based on error patterns
        assert len(recommendations) > 0

    def test_error_severity_levels(self, error_diagnostician):
        """Test that errors get appropriate severity levels."""
        # Critical errors
        critical = error_diagnostician.diagnose(
            error_type="MemoryError",
            message="Out of memory",
            stack_trace="MemoryError",
        )
        assert critical.severity == "critical"

        # High severity
        high = error_diagnostician.diagnose(
            error_type="ConnectionError",
            message="Connection failed",
            stack_trace="ConnectionError",
        )
        assert high.severity == "high"

        # Medium/Low severity
        medium = error_diagnostician.diagnose(
            error_type="ValueError",
            message="Invalid value",
            stack_trace="ValueError",
        )
        assert medium.severity in ["medium", "low"]

    def test_relate_similar_errors(self, error_diagnostician):
        """Test finding related errors in history."""
        # Diagnose first error
        error1 = error_diagnostician.diagnose(
            error_type="ValueError",
            message="Invalid input",
            stack_trace="ValueError",
        )

        # Diagnose same type again
        error2 = error_diagnostician.diagnose(
            error_type="ValueError",
            message="Invalid data",
            stack_trace="ValueError",
        )

        assert len(error2.related_errors) > 0
        assert error1.error_id in error2.related_errors


class TestDiagnosedError:
    """Tests for DiagnosedError dataclass."""

    def test_diagnosed_error_creation(self):
        """Test DiagnosedError dataclass creation."""
        error = DiagnosedError(
            error_id="err_1",
            error_type="ValueError",
            message="Invalid value provided",
            stack_trace="ValueError: Invalid value",
            root_cause="User provided invalid input",
            affected_component="input_validation",
            severity="medium",
            reproduction_steps=["Run with invalid input"],
            solution="Validate input before use",
            prevention="Add input validation",
            related_errors=[],
        )

        assert error.error_id == "err_1"
        assert error.error_type == "ValueError"
        assert error.severity == "medium"
        assert error.timestamp is not None


class TestErrorPattern:
    """Tests for ErrorPattern dataclass."""

    def test_error_pattern_creation(self):
        """Test ErrorPattern dataclass creation."""
        pattern = ErrorPattern(
            pattern_name="Connection Timeout",
            description="Network connection exceeded timeout",
            regex=r"(TimeoutError|timeout)",
            severity="high",
            frequency=5,
            last_seen="2024-01-01T00:00:00",
        )

        assert pattern.pattern_name == "Connection Timeout"
        assert pattern.severity == "high"
        assert pattern.frequency == 5


class TestErrorFrequency:
    """Tests for ErrorFrequency dataclass."""

    def test_error_frequency_creation(self):
        """Test ErrorFrequency dataclass creation."""
        frequency = ErrorFrequency(
            error_type="ValueError",
            occurrences=10,
            first_seen="2024-01-01T00:00:00",
            last_seen="2024-01-10T00:00:00",
            frequency_trend="increasing",
        )

        assert frequency.error_type == "ValueError"
        assert frequency.occurrences == 10
        assert frequency.frequency_trend == "increasing"


class TestErrorDiagnosisIntegration:
    """Integration tests for error diagnosis workflow."""

    def test_diagnose_and_track_multiple_errors(self, error_diagnostician):
        """Test diagnosing multiple different errors."""
        errors = [
            ("ValueError", "Invalid input", "ValueError: Invalid"),
            ("TypeError", "Wrong type", "TypeError: Wrong type"),
            ("KeyError", "Missing key", "KeyError: 'key'"),
            ("AttributeError", "Missing attr", "AttributeError: Missing"),
        ]

        diagnosed_errors = []
        for error_type, message, trace in errors:
            diagnosed = error_diagnostician.diagnose(
                error_type=error_type,
                message=message,
                stack_trace=trace,
            )
            diagnosed_errors.append(diagnosed)

        assert len(diagnosed_errors) == 4

        # Get summary
        summary = error_diagnostician.get_error_summary()
        assert summary["total_errors"] >= 4
        assert len(summary["error_types"]) == 4

    def test_error_trends_detection(self, error_diagnostician):
        """Test detecting error frequency trends."""
        # Diagnose ValueError multiple times to establish trend
        for i in range(7):
            error_diagnostician.diagnose(
                error_type="ValueError",
                message="Invalid input",
                stack_trace="ValueError",
            )

        frequency = error_diagnostician.get_error_frequency("ValueError")

        assert frequency is not None
        assert frequency.frequency_trend in [
            "increasing",
            "stable",
            "decreasing",
            "insufficient_data",
        ]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
