"""Strategy 1: Error Diagnosis - Learn from failures and prevent recurrence."""

import logging
import re
import traceback
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ErrorPattern:
    """A pattern in error occurrences."""
    pattern_name: str
    description: str
    regex: str
    severity: str  # critical, high, medium, low
    frequency: int = 0
    last_seen: str = ""


@dataclass
class DiagnosedError:
    """A fully diagnosed error with root cause and solution."""
    error_id: str
    error_type: str
    message: str
    stack_trace: str
    root_cause: str
    affected_component: str
    severity: str
    reproduction_steps: List[str]
    solution: str
    prevention: str
    related_errors: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ErrorFrequency:
    """Frequency information for an error."""
    error_type: str
    occurrences: int
    first_seen: str
    last_seen: str
    frequency_trend: str  # increasing, stable, decreasing


class ErrorDiagnostician:
    """Diagnoses errors from stack traces and logs."""

    def __init__(self):
        """Initialize error diagnostician."""
        self.error_patterns: Dict[str, ErrorPattern] = {}
        self.diagnosed_errors: Dict[str, DiagnosedError] = {}
        self.error_history: List[DiagnosedError] = []
        self._init_common_patterns()

    def diagnose(
        self,
        error_type: str,
        message: str,
        stack_trace: str,
        context: Dict[str, Any] = None,
    ) -> DiagnosedError:
        """Diagnose an error from its information.

        Args:
            error_type: Type of error (e.g., "AttributeError", "ConnectionError")
            message: Error message
            stack_trace: Full stack trace
            context: Additional context (logs, variables, etc.)

        Returns:
            DiagnosedError with root cause and solution
        """
        logger.info(f"Diagnosing {error_type}: {message}")

        # Analyze stack trace
        affected_component = self._identify_component(stack_trace)
        root_cause = self._identify_root_cause(error_type, message, stack_trace)
        severity = self._assess_severity(error_type, message, context)

        # Get reproduction steps
        reproduction_steps = self._extract_reproduction_steps(stack_trace, context)

        # Get solution and prevention
        solution = self._suggest_solution(error_type, root_cause)
        prevention = self._suggest_prevention(error_type, root_cause)

        # Find related errors
        related = self._find_related_errors(error_type, message)

        diagnosed = DiagnosedError(
            error_id=f"err_{len(self.diagnosed_errors)}",
            error_type=error_type,
            message=message,
            stack_trace=stack_trace,
            root_cause=root_cause,
            affected_component=affected_component,
            severity=severity,
            reproduction_steps=reproduction_steps,
            solution=solution,
            prevention=prevention,
            related_errors=related,
        )

        self.diagnosed_errors[diagnosed.error_id] = diagnosed
        self.error_history.append(diagnosed)

        logger.info(f"Diagnosed: {root_cause}")

        return diagnosed

    def analyze_traceback(self, traceback_str: str) -> Dict[str, Any]:
        """Analyze a Python traceback string.

        Args:
            traceback_str: Traceback from Python exception

        Returns:
            Analysis of the traceback
        """
        try:
            lines = traceback_str.strip().split("\n")

            # Extract error type and message
            last_line = lines[-1]
            if ":" in last_line:
                error_type, message = last_line.split(":", 1)
                error_type = error_type.strip()
                message = message.strip()
            else:
                error_type = "Unknown"
                message = last_line

            # Extract file and line number
            file_info = ""
            line_num = ""
            for line in lines:
                if 'File "' in line:
                    file_match = re.search(r'File "([^"]+)", line (\d+)', line)
                    if file_match:
                        file_info = file_match.group(1)
                        line_num = file_match.group(2)

            return {
                "error_type": error_type,
                "message": message,
                "file": file_info,
                "line": line_num,
                "full_trace": traceback_str,
            }

        except Exception as e:
            logger.error(f"Error analyzing traceback: {e}")
            return {"error": "Could not parse traceback"}

    def get_error_frequency(self, error_type: str) -> Optional[ErrorFrequency]:
        """Get frequency information for an error type.

        Args:
            error_type: Type of error to check

        Returns:
            Frequency information or None
        """
        matching = [e for e in self.error_history if e.error_type == error_type]

        if not matching:
            return None

        return ErrorFrequency(
            error_type=error_type,
            occurrences=len(matching),
            first_seen=matching[-1].timestamp,
            last_seen=matching[0].timestamp,
            frequency_trend=self._calculate_trend(matching),
        )

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all diagnosed errors.

        Returns:
            Summary statistics
        """
        if not self.error_history:
            return {"total_errors": 0}

        error_types = {}
        for error in self.error_history:
            error_types[error.error_type] = error_types.get(error.error_type, 0) + 1

        critical_errors = len([e for e in self.error_history if e.severity == "critical"])
        high_errors = len([e for e in self.error_history if e.severity == "high"])

        return {
            "total_errors": len(self.error_history),
            "error_types": error_types,
            "critical": critical_errors,
            "high": high_errors,
            "most_common": max(error_types.items(), key=lambda x: x[1])[0] if error_types else None,
        }

    def prevent_future_errors(self) -> List[str]:
        """Generate recommendations to prevent future errors.

        Returns:
            List of prevention recommendations
        """
        recommendations = []

        # Analyze patterns
        error_summary = self.get_error_summary()

        if error_summary.get("critical"):
            recommendations.append("Add monitoring for critical errors")

        if error_summary.get("total_errors") > 5:
            recommendations.append("Implement comprehensive error handling")

        # Suggest preventions based on error types
        for error_type, count in error_summary.get("error_types", {}).items():
            if count > 2:
                recommendations.append(
                    f"Add specific handling for {error_type} (occurred {count} times)"
                )

        return recommendations

    def _identify_component(self, stack_trace: str) -> str:
        """Identify which component had the error."""
        # Extract file path from stack trace
        match = re.search(r'File "([^"]+)"', stack_trace)
        if match:
            filepath = match.group(1)
            # Extract component from path
            parts = filepath.split("/")
            for part in parts:
                if part.endswith(".py"):
                    return part[:-3]  # Remove .py
        return "unknown"

    def _identify_root_cause(self, error_type: str, message: str, stack_trace: str) -> str:
        """Identify root cause of error."""
        cause_map = {
            "AttributeError": "Missing or incorrect attribute access",
            "TypeError": "Wrong type passed to function",
            "ValueError": "Invalid value provided",
            "KeyError": "Missing dictionary key",
            "IndexError": "Index out of range",
            "ConnectionError": "Network or service connection failed",
            "TimeoutError": "Operation took too long",
            "MemoryError": "Insufficient memory",
            "ImportError": "Module not found or import failed",
            "ZeroDivisionError": "Division by zero",
        }

        return cause_map.get(error_type, f"Error type: {error_type}")

    def _assess_severity(
        self,
        error_type: str,
        message: str,
        context: Dict[str, Any] = None,
    ) -> str:
        """Assess severity of error."""
        if error_type in ["MemoryError", "SystemExit", "KeyboardInterrupt"]:
            return "critical"

        if "connection" in message.lower() or "timeout" in message.lower():
            return "high"

        if "assert" in message.lower():
            return "high"

        return "medium"

    def _extract_reproduction_steps(
        self,
        stack_trace: str,
        context: Dict[str, Any] = None,
    ) -> List[str]:
        """Extract steps to reproduce the error."""
        steps = [
            "1. Note the error type and message",
            "2. Check the affected file and line number from stack trace",
            "3. Review the variables and context at point of failure",
            "4. Run with similar inputs to reproduce",
        ]

        return steps

    def _suggest_solution(self, error_type: str, root_cause: str) -> str:
        """Suggest a solution for the error."""
        solutions = {
            "AttributeError": "Check that the object has the expected attribute before accessing it",
            "TypeError": "Verify the type of values being passed to functions",
            "ValueError": "Validate input values before using them",
            "KeyError": "Use dict.get() with default value or check key exists first",
            "IndexError": "Check list length before accessing by index",
            "ConnectionError": "Implement retry logic with exponential backoff",
            "TimeoutError": "Increase timeout or optimize the operation",
            "ImportError": "Verify module is installed and path is correct",
        }

        return solutions.get(error_type, f"Review {root_cause} and fix accordingly")

    def _suggest_prevention(self, error_type: str, root_cause: str) -> str:
        """Suggest how to prevent the error in future."""
        preventions = {
            "AttributeError": "Use getattr() with defaults or type hints",
            "TypeError": "Add type hints and use mypy for type checking",
            "ValueError": "Validate all inputs at function entry points",
            "KeyError": "Use defaultdict or .get() method",
            "IndexError": "Always check length before indexing",
            "ConnectionError": "Implement connection pooling and retries",
            "TimeoutError": "Set reasonable timeouts and handle gracefully",
            "ImportError": "Document dependencies clearly",
        }

        return preventions.get(error_type, "Add proper error handling and validation")

    def _find_related_errors(self, error_type: str, message: str) -> List[str]:
        """Find related errors from history."""
        related = []

        for error in self.error_history[-10:]:  # Check last 10
            if error.error_type == error_type:
                related.append(error.error_id)

        return related

    def _calculate_trend(self, errors: List[DiagnosedError]) -> str:
        """Calculate frequency trend for an error."""
        if len(errors) < 2:
            return "insufficient_data"

        recent = len([e for e in errors[:5]])  # Last 5
        older = len([e for e in errors[5:10]])  # Previous 5

        if recent > older:
            return "increasing"
        elif recent < older:
            return "decreasing"
        else:
            return "stable"

    def _init_common_patterns(self) -> None:
        """Initialize common error patterns."""
        patterns = {
            "connection": ErrorPattern(
                pattern_name="Connection Error",
                description="Network or service connection failed",
                regex=r"(Connection|ConnectTimeout|ConnectionRefused)",
                severity="high",
            ),
            "timeout": ErrorPattern(
                pattern_name="Timeout",
                description="Operation exceeded time limit",
                regex=r"(TimeoutError|Timeout)",
                severity="high",
            ),
            "memory": ErrorPattern(
                pattern_name="Memory Error",
                description="Ran out of available memory",
                regex=r"(MemoryError|OutOfMemory)",
                severity="critical",
            ),
            "import": ErrorPattern(
                pattern_name="Import Error",
                description="Module not found or import failed",
                regex=r"(ImportError|ModuleNotFoundError)",
                severity="high",
            ),
        }

        self.error_patterns.update(patterns)
