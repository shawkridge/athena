"""Tests for dream sandbox execution and testing."""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from athena.testing.dream_sandbox import (
    DreamSandbox,
    DreamTestResult,
    TestOutcome,
    ErrorCategory,
)
from athena.testing.synthetic_test_generator import SyntheticTestGenerator
from athena.sandbox.srt_executor import ExecutionResult


@pytest.fixture
def dream_sandbox():
    """Create sandbox instance for testing."""
    return DreamSandbox(
        timeout_seconds=5,
        memory_limit_mb=256,
        max_output_lines=100,
    )


@pytest.fixture
def test_generator():
    """Create test generator instance."""
    return SyntheticTestGenerator(seed=42)


@pytest.fixture
def simple_dream_code():
    """Simple valid dream code for testing."""
    return '''
def add_numbers(a: int, b: int) -> int:
    """Add two numbers."""
    _result = a + b
    return _result
'''


@pytest.fixture
def complex_dream_code():
    """More complex dream code."""
    return '''
def process_list(items: list, multiplier: int = 2) -> list:
    """Process a list of items."""
    _result = [x * multiplier for x in items]
    return _result
'''


@pytest.fixture
def broken_dream_code():
    """Dream code with syntax error."""
    return '''
def broken_function(x):
    if x > 0  # Missing colon
        return x * 2
'''


@pytest.fixture
def type_error_dream_code():
    """Dream code that causes type error."""
    return '''
def type_error_function(x: int) -> int:
    _result = "string" + x  # Type error
    return _result
'''


class TestDreamSandbox:
    """Test DreamSandbox execution."""

    @pytest.mark.asyncio
    async def test_sandbox_creation(self, dream_sandbox):
        """Test sandbox can be created."""
        assert dream_sandbox is not None
        assert dream_sandbox.timeout_seconds == 5
        assert dream_sandbox.memory_limit_mb == 256

    @pytest.mark.asyncio
    async def test_wrap_dream_code(self, dream_sandbox, simple_dream_code):
        """Test code wrapping for sandboxed execution."""
        inputs = {"a": 1, "b": 2}
        wrapped = dream_sandbox._wrap_dream_code(simple_dream_code, inputs)

        assert "_dream_params" in wrapped
        assert "import json" in wrapped
        assert "_dream_output" in wrapped
        assert "json.dumps(result_output)" in wrapped
        assert "{'a': 1, 'b': 2}" in wrapped

    def test_indent_code(self, dream_sandbox):
        """Test code indentation."""
        code = "line1\nline2\nline3"
        indented = dream_sandbox._indent_code(code, 4)

        lines = indented.split("\n")
        assert lines[0] == "    line1"
        assert lines[1] == "    line2"
        assert lines[2] == "    line3"

    def test_categorize_error_syntax(self, dream_sandbox):
        """Test error categorization for syntax errors."""
        stderr = "SyntaxError: invalid syntax at line 5"
        outcome, category = dream_sandbox._categorize_error(stderr)

        assert outcome == TestOutcome.SYNTAX_ERROR
        assert category == ErrorCategory.SYNTAX

    def test_categorize_error_type(self, dream_sandbox):
        """Test error categorization for type errors."""
        stderr = "TypeError: unsupported operand type(s)"
        outcome, category = dream_sandbox._categorize_error(stderr)

        assert outcome == TestOutcome.TYPE_ERROR
        assert category == ErrorCategory.TYPE

    def test_categorize_error_runtime(self, dream_sandbox):
        """Test error categorization for runtime errors."""
        stderr = "ValueError: invalid value"
        outcome, category = dream_sandbox._categorize_error(stderr)

        assert outcome == TestOutcome.RUNTIME_ERROR
        assert category == ErrorCategory.RUNTIME

    def test_categorize_error_memory(self, dream_sandbox):
        """Test error categorization for memory errors."""
        stderr = "MemoryError: out of memory"
        outcome, category = dream_sandbox._categorize_error(stderr)

        assert outcome == TestOutcome.RESOURCE_EXHAUSTION
        assert category == ErrorCategory.RESOURCE

    def test_extract_error_message(self, dream_sandbox):
        """Test error message extraction."""
        stderr = "line 1\nline 2\nFinal error message"
        message = dream_sandbox._extract_error_message(stderr)

        assert message == "Final error message"

    def test_extract_error_message_empty(self, dream_sandbox):
        """Test error message extraction with empty stderr."""
        stderr = ""
        message = dream_sandbox._extract_error_message(stderr)

        assert message == "Unknown error"

    def test_validate_output_valid_json(self, dream_sandbox):
        """Test output validation with valid JSON."""
        output = json.dumps({"output": [1, 2, 3], "error": None})
        passed, error = dream_sandbox._validate_output(output, "list")

        assert passed is True
        assert error is None

    def test_validate_output_type_mismatch(self, dream_sandbox):
        """Test output validation with type mismatch."""
        output = json.dumps({"output": "string", "error": None})
        passed, error = dream_sandbox._validate_output(output, "list")

        assert passed is False
        assert "Expected list" in error

    def test_validate_output_invalid_json(self, dream_sandbox):
        """Test output validation with invalid JSON."""
        output = "not valid json"
        passed, error = dream_sandbox._validate_output(output, "dict")

        assert passed is False
        assert "not valid JSON" in error

    def test_validate_output_missing_field(self, dream_sandbox):
        """Test output validation with missing output field."""
        output = json.dumps({"error": None})
        passed, error = dream_sandbox._validate_output(output, "int")

        assert passed is False
        assert "missing 'output' field" in error

    def test_record_failure_pattern_new(self, dream_sandbox):
        """Test recording new failure pattern."""
        result = DreamTestResult(
            dream_id=1,
            test_outcome=TestOutcome.SYNTAX_ERROR,
            success=False,
            execution_time_ms=100.0,
            stdout="",
            stderr="SyntaxError: invalid",
            exit_code=1,
            sandbox_id="test1",
            error_category=ErrorCategory.SYNTAX,
            error_summary="SyntaxError: invalid",
        )

        dream_sandbox._record_failure_pattern(result, "def foo(:\n  pass")

        patterns = dream_sandbox.get_failure_patterns()
        assert len(patterns) > 0

    def test_record_failure_pattern_update(self, dream_sandbox):
        """Test updating existing failure pattern."""
        result = DreamTestResult(
            dream_id=1,
            test_outcome=TestOutcome.SYNTAX_ERROR,
            success=False,
            execution_time_ms=100.0,
            stdout="",
            stderr="SyntaxError: invalid",
            exit_code=1,
            sandbox_id="test1",
            error_category=ErrorCategory.SYNTAX,
            error_summary="SyntaxError: invalid",
        )

        # Record same error twice
        dream_sandbox._record_failure_pattern(result, "code1")
        dream_sandbox._record_failure_pattern(result, "code2")

        patterns = dream_sandbox.get_failure_patterns()
        for pattern in patterns.values():
            if pattern.frequency > 1:
                assert pattern.frequency == 2

    def test_get_test_statistics(self, dream_sandbox):
        """Test test statistics calculation."""
        # Add some results
        for i in range(5):
            result = DreamTestResult(
                dream_id=i,
                test_outcome=TestOutcome.SUCCESS if i < 3 else TestOutcome.TIMEOUT,
                success=i < 3,
                execution_time_ms=100.0 * (i + 1),
                stdout="output",
                stderr="",
                exit_code=0 if i < 3 else 1,
                sandbox_id=f"test{i}",
            )
            dream_sandbox.test_history.append(result)

        stats = dream_sandbox.get_test_statistics()

        assert stats["total_tests"] == 5
        assert stats["successful_tests"] == 3
        assert stats["success_rate"] == 0.6
        assert stats["average_execution_time_ms"] > 0


class TestSyntheticTestGenerator:
    """Test synthetic test input generation."""

    def test_generator_creation(self, test_generator):
        """Test generator can be created."""
        assert test_generator is not None

    def test_generate_test_inputs_simple(self, test_generator, simple_dream_code):
        """Test generating test inputs from simple code."""
        inputs = test_generator.generate_test_inputs(simple_dream_code, num_variants=3)

        assert len(inputs) == 3
        for variant in inputs:
            assert "a" in variant
            assert "b" in variant
            assert isinstance(variant["a"], int)
            assert isinstance(variant["b"], int)

    def test_generate_test_inputs_with_defaults(self, test_generator, complex_dream_code):
        """Test generating test inputs from code with default values."""
        inputs = test_generator.generate_test_inputs(complex_dream_code, num_variants=3)

        assert len(inputs) == 3
        for variant in inputs:
            assert "items" in variant
            assert isinstance(variant["items"], list)

    def test_generate_edge_case_inputs(self, test_generator, simple_dream_code):
        """Test generating edge case inputs."""
        edge_cases = test_generator.generate_edge_case_inputs(simple_dream_code)

        assert len(edge_cases) > 0
        # At least some edge cases should be present
        assert any(edge_cases)

    def test_get_expected_output_type(self, test_generator, simple_dream_code):
        """Test inferring expected output type."""
        output_type = test_generator.get_expected_output_type(simple_dream_code)

        assert output_type == "int"

    def test_generate_value_int(self, test_generator):
        """Test generating integer values."""
        value = test_generator._generate_value("int", False, None, 0)
        assert isinstance(value, int)

    def test_generate_value_str(self, test_generator):
        """Test generating string values."""
        value = test_generator._generate_value("str", False, None, 0)
        assert isinstance(value, str)

    def test_generate_value_list(self, test_generator):
        """Test generating list values."""
        value = test_generator._generate_value("list", False, None, 0)
        assert isinstance(value, list)

    def test_generate_value_dict(self, test_generator):
        """Test generating dict values."""
        value = test_generator._generate_value("dict", False, None, 0)
        assert isinstance(value, dict)

    def test_generate_list_with_element_type(self, test_generator):
        """Test list generation with specific element type."""
        lst = test_generator._generate_list("List[int]", 0)
        assert isinstance(lst, list)
        assert all(isinstance(x, int) for x in lst)

    def test_extract_generic_type(self, test_generator):
        """Test extracting generic type from annotation."""
        type_str = test_generator._extract_generic_type("List[int]")
        assert type_str == "int"

    def test_extract_tuple_types(self, test_generator):
        """Test extracting tuple element types."""
        types = test_generator._extract_tuple_types("Tuple[int, str, float]")
        assert types == ["int", "str", "float"]


class TestDreamTestResultModel:
    """Test DreamTestResult data model."""

    def test_result_creation(self):
        """Test creating a test result."""
        result = DreamTestResult(
            dream_id=1,
            test_outcome=TestOutcome.SUCCESS,
            success=True,
            execution_time_ms=100.0,
            stdout="output",
            stderr="",
            exit_code=0,
            sandbox_id="test1",
        )

        assert result.dream_id == 1
        assert result.test_outcome == TestOutcome.SUCCESS
        assert result.success is True

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = DreamTestResult(
            dream_id=1,
            test_outcome=TestOutcome.SUCCESS,
            success=True,
            execution_time_ms=100.0,
            stdout="output",
            stderr="",
            exit_code=0,
            sandbox_id="test1",
            error_category=ErrorCategory.SYNTAX,
            error_summary="Test error",
        )

        result_dict = result.to_dict()

        assert result_dict["dream_id"] == 1
        assert result_dict["success"] is True
        assert result_dict["test_outcome"] == "success"
        assert result_dict["error_category"] == "syntax"

    def test_result_timestamp(self):
        """Test result includes timestamp."""
        result = DreamTestResult(
            dream_id=1,
            test_outcome=TestOutcome.SUCCESS,
            success=True,
            execution_time_ms=100.0,
            stdout="",
            stderr="",
            exit_code=0,
            sandbox_id="test1",
        )

        assert isinstance(result.timestamp, datetime)
        assert result.timestamp <= datetime.now()
