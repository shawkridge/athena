"""Sandbox infrastructure for safely executing and testing dream procedures."""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

from ..sandbox.srt_executor import SRTExecutor, ExecutionResult
from ..sandbox.config import SandboxConfig, SandboxMode, ExecutionLanguage

logger = logging.getLogger(__name__)


class TestOutcome(str, Enum):
    """Outcome of a dream procedure test."""

    SUCCESS = "success"
    SYNTAX_ERROR = "syntax_error"
    RUNTIME_ERROR = "runtime_error"
    TYPE_ERROR = "type_error"
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    OUTPUT_VALIDATION_FAILED = "output_validation_failed"
    UNKNOWN_ERROR = "unknown_error"


class ErrorCategory(str, Enum):
    """Categories of test failures for learning."""

    SYNTAX = "syntax"
    RUNTIME = "runtime"
    TYPE = "type"
    LOGIC = "logic"
    RESOURCE = "resource"
    DEPENDENCY = "dependency"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


@dataclass
class FailurePattern:
    """Pattern extracted from a failure for learning."""

    error_category: ErrorCategory
    error_message: str
    code_snippet: str  # The failing line(s)
    frequency: int = 1  # How many times has this pattern appeared?
    last_seen: datetime = field(default_factory=datetime.now)
    suggested_fix: Optional[str] = None


@dataclass
class DreamTestResult:
    """Result of executing a dream procedure in sandbox."""

    dream_id: int
    test_outcome: TestOutcome
    success: bool
    execution_time_ms: float
    stdout: str
    stderr: str
    exit_code: int
    sandbox_id: str
    timestamp: datetime = field(default_factory=datetime.now)

    # Validation results
    output_validation_passed: bool = True
    output_validation_error: Optional[str] = None

    # Error analysis
    error_category: Optional[ErrorCategory] = None
    error_summary: str = ""

    # Resource usage
    memory_used_mb: float = 0.0
    cpu_time_ms: float = 0.0

    # Test configuration
    input_params: Dict[str, Any] = field(default_factory=dict)
    expected_output_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "dream_id": self.dream_id,
            "test_outcome": self.test_outcome.value,
            "success": self.success,
            "execution_time_ms": self.execution_time_ms,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "sandbox_id": self.sandbox_id,
            "timestamp": self.timestamp.isoformat(),
            "output_validation_passed": self.output_validation_passed,
            "output_validation_error": self.output_validation_error,
            "error_category": self.error_category.value if self.error_category else None,
            "error_summary": self.error_summary,
            "memory_used_mb": self.memory_used_mb,
            "cpu_time_ms": self.cpu_time_ms,
        }


class DreamSandbox:
    """Safe execution environment for dream procedures."""

    def __init__(
        self,
        timeout_seconds: int = 30,
        memory_limit_mb: int = 512,
        max_output_lines: int = 1000,
        enable_network: bool = False,
        enable_filesystem: bool = False,
    ):
        """Initialize dream sandbox.

        Args:
            timeout_seconds: Maximum execution time per test
            memory_limit_mb: Maximum memory allocation
            max_output_lines: Maximum lines of output to capture
            enable_network: Allow network access (dangerous!)
            enable_filesystem: Allow filesystem access (limited)
        """
        self.timeout_seconds = timeout_seconds
        self.memory_limit_mb = memory_limit_mb
        self.max_output_lines = max_output_lines
        self.enable_network = enable_network
        self.enable_filesystem = enable_filesystem

        # Configure SRT executor (with fallback to mock mode if SRT unavailable)
        config = SandboxConfig()
        config.timeout_seconds = timeout_seconds
        config.max_memory_mb = memory_limit_mb
        config.language = ExecutionLanguage.PYTHON
        config.allow_network = enable_network
        # Filesystem access is controlled differently in SRT

        try:
            config.mode = SandboxMode.SRT
            self.executor = SRTExecutor(config)
        except RuntimeError:
            # Fall back to mock mode if SRT not available
            logger.warning("SRT binary not available, using mock mode for testing")
            config.mode = SandboxMode.MOCK
            self.executor = SRTExecutor(config)

        # Failure pattern tracking
        self.failure_patterns: Dict[str, FailurePattern] = {}
        self.test_history: List[DreamTestResult] = []

    async def execute_dream(
        self,
        dream_id: int,
        code: str,
        input_params: Dict[str, Any],
        expected_output_type: Optional[str] = None,
    ) -> DreamTestResult:
        """Execute a dream procedure in the sandbox.

        Args:
            dream_id: ID of the dream being tested
            code: Python code of the dream procedure
            input_params: Input parameters for the procedure
            expected_output_type: Expected output type for validation

        Returns:
            DreamTestResult with execution outcome
        """
        start_time = time.time()

        # Wrap dream code with input injection and output capture
        wrapped_code = self._wrap_dream_code(code, input_params)

        # Execute in SRT
        try:
            execution_result: ExecutionResult = await asyncio.to_thread(
                self.executor.execute,
                wrapped_code,
            )
        except Exception as e:
            return DreamTestResult(
                dream_id=dream_id,
                test_outcome=TestOutcome.UNKNOWN_ERROR,
                success=False,
                execution_time_ms=(time.time() - start_time) * 1000,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                sandbox_id="",
                error_category=ErrorCategory.UNKNOWN,
                error_summary=str(e),
                input_params=input_params,
                expected_output_type=expected_output_type,
            )

        # Analyze execution result
        result = self._analyze_execution(
            dream_id,
            execution_result,
            input_params,
            expected_output_type,
            time.time() - start_time,
        )

        # Track result for learning
        self.test_history.append(result)
        if not result.success:
            self._record_failure_pattern(result, code)

        return result

    def _wrap_dream_code(self, code: str, input_params: Dict[str, Any]) -> str:
        """Wrap dream code with input injection and error handling.

        Args:
            code: Original dream code
            input_params: Parameters to inject

        Returns:
            Wrapped code ready for execution
        """
        params_str = repr(input_params)

        wrapper = f"""
import sys
import json
import traceback

# Injected parameters
_dream_params = {params_str}

# Capture output
_dream_output = None
_dream_error = None

try:
    # Dream code execution
    {self._indent_code(code, 4)}

    # Capture result if assigned to _result variable
    if '_result' in dir():
        _dream_output = _result

except Exception as _e:
    _dream_error = {{
        'type': type(_e).__name__,
        'message': str(_e),
        'traceback': traceback.format_exc()
    }}

# Output results in JSON for parsing
result_output = {{
    'output': _dream_output,
    'error': _dream_error,
    'params_used': _dream_params
}}
print(json.dumps(result_output))
"""
        return wrapper.strip()

    @staticmethod
    def _indent_code(code: str, spaces: int) -> str:
        """Indent code block by specified spaces.

        Args:
            code: Code to indent
            spaces: Number of spaces

        Returns:
            Indented code
        """
        indent = " " * spaces
        return "\n".join(indent + line if line.strip() else line for line in code.split("\n"))

    def _analyze_execution(
        self,
        dream_id: int,
        execution_result: ExecutionResult,
        input_params: Dict[str, Any],
        expected_output_type: Optional[str],
        elapsed_time: float,
    ) -> DreamTestResult:
        """Analyze execution result and determine outcome.

        Args:
            dream_id: Dream ID
            execution_result: Result from SRT execution
            input_params: Input parameters used
            expected_output_type: Expected output type
            elapsed_time: Elapsed time in seconds

        Returns:
            Analyzed DreamTestResult
        """
        # Check for timeout
        if elapsed_time > self.timeout_seconds:
            return DreamTestResult(
                dream_id=dream_id,
                test_outcome=TestOutcome.TIMEOUT,
                success=False,
                execution_time_ms=elapsed_time * 1000,
                stdout=execution_result.stdout,
                stderr=execution_result.stderr,
                exit_code=execution_result.exit_code,
                sandbox_id=execution_result.sandbox_id,
                error_category=ErrorCategory.TIMEOUT,
                error_summary="Execution exceeded timeout",
                memory_used_mb=execution_result.memory_used_mb,
                input_params=input_params,
                expected_output_type=expected_output_type,
            )

        # Check for execution success
        if not execution_result.success:
            outcome, category = self._categorize_error(execution_result.stderr)
            return DreamTestResult(
                dream_id=dream_id,
                test_outcome=outcome,
                success=False,
                execution_time_ms=execution_result.execution_time_ms,
                stdout=execution_result.stdout,
                stderr=execution_result.stderr,
                exit_code=execution_result.exit_code,
                sandbox_id=execution_result.sandbox_id,
                error_category=category,
                error_summary=self._extract_error_message(execution_result.stderr),
                memory_used_mb=execution_result.memory_used_mb,
                input_params=input_params,
                expected_output_type=expected_output_type,
            )

        # Validate output if expected type provided
        validation_passed = True
        validation_error = None
        if expected_output_type:
            validation_passed, validation_error = self._validate_output(
                execution_result.stdout,
                expected_output_type,
            )

        return DreamTestResult(
            dream_id=dream_id,
            test_outcome=(
                TestOutcome.SUCCESS if validation_passed else TestOutcome.OUTPUT_VALIDATION_FAILED
            ),
            success=validation_passed,
            execution_time_ms=execution_result.execution_time_ms,
            stdout=execution_result.stdout,
            stderr=execution_result.stderr,
            exit_code=execution_result.exit_code,
            sandbox_id=execution_result.sandbox_id,
            output_validation_passed=validation_passed,
            output_validation_error=validation_error,
            memory_used_mb=execution_result.memory_used_mb,
            input_params=input_params,
            expected_output_type=expected_output_type,
        )

    @staticmethod
    def _categorize_error(stderr: str) -> Tuple[TestOutcome, ErrorCategory]:
        """Categorize error from stderr.

        Args:
            stderr: Standard error output

        Returns:
            Tuple of (TestOutcome, ErrorCategory)
        """
        stderr_lower = stderr.lower()

        if "syntaxerror" in stderr_lower:
            return TestOutcome.SYNTAX_ERROR, ErrorCategory.SYNTAX
        elif "typeerror" in stderr_lower:
            return TestOutcome.TYPE_ERROR, ErrorCategory.TYPE
        elif "memoryerror" in stderr_lower or "out of memory" in stderr_lower:
            return TestOutcome.RESOURCE_EXHAUSTION, ErrorCategory.RESOURCE
        elif "timeout" in stderr_lower or "timed out" in stderr_lower:
            return TestOutcome.TIMEOUT, ErrorCategory.TIMEOUT
        elif "importerror" in stderr_lower or "modulenotfounderror" in stderr_lower:
            return TestOutcome.RUNTIME_ERROR, ErrorCategory.DEPENDENCY
        else:
            return TestOutcome.RUNTIME_ERROR, ErrorCategory.RUNTIME

    @staticmethod
    def _extract_error_message(stderr: str) -> str:
        """Extract concise error message from stderr.

        Args:
            stderr: Standard error output

        Returns:
            Concise error message
        """
        lines = stderr.strip().split("\n")
        # Return last non-empty line as error message
        for line in reversed(lines):
            if line.strip():
                return line.strip()[:200]  # Max 200 chars
        return "Unknown error"

    def _validate_output(
        self,
        output: str,
        expected_type: str,
    ) -> Tuple[bool, Optional[str]]:
        """Validate output matches expected type.

        Args:
            output: Execution output
            expected_type: Expected output type (e.g., 'dict', 'list', 'int')

        Returns:
            Tuple of (passed: bool, error_message: Optional[str])
        """
        try:
            import json

            result = json.loads(output)

            # Check if 'output' field exists and matches type
            if "output" not in result:
                return False, "Result missing 'output' field"

            value = result["output"]

            # Type validation
            type_map = {
                "dict": dict,
                "list": list,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "tuple": tuple,
            }

            expected_python_type = type_map.get(expected_type.lower())
            if expected_python_type and not isinstance(value, expected_python_type):
                return False, f"Expected {expected_type}, got {type(value).__name__}"

            return True, None

        except json.JSONDecodeError as e:
            return False, f"Output not valid JSON: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def _record_failure_pattern(
        self,
        result: DreamTestResult,
        code: str,
    ) -> None:
        """Record failure pattern for learning system.

        Args:
            result: Test result
            code: Dream code that failed
        """
        # Extract error pattern key
        pattern_key = f"{result.error_category}_{result.error_summary[:50]}"

        if pattern_key in self.failure_patterns:
            # Update existing pattern
            pattern = self.failure_patterns[pattern_key]
            pattern.frequency += 1
            pattern.last_seen = datetime.now()
        else:
            # Record new pattern
            self.failure_patterns[pattern_key] = FailurePattern(
                error_category=result.error_category or ErrorCategory.UNKNOWN,
                error_message=result.error_summary,
                code_snippet=code[:200],
                frequency=1,
                last_seen=datetime.now(),
            )

    def get_failure_patterns(self) -> Dict[str, FailurePattern]:
        """Get all recorded failure patterns.

        Returns:
            Dictionary of failure patterns
        """
        return self.failure_patterns.copy()

    def get_test_statistics(self) -> Dict[str, Any]:
        """Get statistics on all tests executed.

        Returns:
            Dictionary with test statistics
        """
        total = len(self.test_history)
        if total == 0:
            return {
                "total_tests": 0,
                "success_rate": 0.0,
                "average_execution_time_ms": 0.0,
            }

        successful = sum(1 for t in self.test_history if t.success)
        avg_time = sum(t.execution_time_ms for t in self.test_history) / total

        # Count by outcome
        outcomes = {}
        for test in self.test_history:
            outcome = test.test_outcome.value
            outcomes[outcome] = outcomes.get(outcome, 0) + 1

        return {
            "total_tests": total,
            "successful_tests": successful,
            "success_rate": successful / total,
            "average_execution_time_ms": avg_time,
            "outcomes": outcomes,
            "failure_patterns_count": len(self.failure_patterns),
        }
