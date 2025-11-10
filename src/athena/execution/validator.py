"""Assumption Validator - Verify plan assumptions hold during execution."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
import logging

from .models import (
    AssumptionValidationResult,
    AssumptionViolation,
    AssumptionValidationType,
    DeviationSeverity,
)

logger = logging.getLogger(__name__)


@dataclass
class Assumption:
    """An assumption in a plan."""
    assumption_id: str
    description: str
    expected_value: Any
    validation_method: AssumptionValidationType
    check_frequency: timedelta  # How often to check
    tolerance: float = 0.1  # Acceptable variance (0.0 to 1.0)
    severity: DeviationSeverity = DeviationSeverity.MEDIUM
    affected_tasks: List[str] = field(default_factory=list)
    check_function: Optional[Callable[[], Any]] = None  # Optional validation function


class AssumptionValidator:
    """Validate assumptions during plan execution."""

    def __init__(self):
        """Initialize assumption validator."""
        self.assumptions: Dict[str, Assumption] = {}
        self.validation_results: Dict[str, List[AssumptionValidationResult]] = {}
        self.violations: Dict[str, AssumptionViolation] = {}
        self.next_check_times: Dict[str, datetime] = {}

    def register_assumption(
        self,
        assumption_id: str,
        description: str,
        expected_value: Any,
        validation_method: AssumptionValidationType,
        check_frequency: timedelta = timedelta(minutes=5),
        tolerance: float = 0.1,
        severity: DeviationSeverity = DeviationSeverity.MEDIUM,
        affected_tasks: Optional[List[str]] = None,
        check_function: Optional[Callable[[], Any]] = None,
    ) -> None:
        """Register an assumption to validate.

        Args:
            assumption_id: Unique ID for the assumption
            description: Human-readable description
            expected_value: Expected value during execution
            validation_method: How to validate (auto/manual/external/sensor)
            check_frequency: How often to validate
            tolerance: Acceptable variance (0.0-1.0)
            severity: Severity if violated
            affected_tasks: List of task IDs affected if violated
            check_function: Optional callable to perform validation
        """
        assumption = Assumption(
            assumption_id=assumption_id,
            description=description,
            expected_value=expected_value,
            validation_method=validation_method,
            check_frequency=check_frequency,
            tolerance=tolerance,
            severity=severity,
            affected_tasks=affected_tasks or [],
            check_function=check_function,
        )

        self.assumptions[assumption_id] = assumption
        self.validation_results[assumption_id] = []
        self.next_check_times[assumption_id] = datetime.utcnow()

        logger.info(
            f"Assumption registered: {assumption_id} ({description}) - "
            f"Check every {check_frequency}"
        )

    def check_assumption(
        self,
        assumption_id: str,
        actual_value: Any,
    ) -> AssumptionValidationResult:
        """Check if an assumption still holds.

        Args:
            assumption_id: ID of assumption to check
            actual_value: Actual value during execution

        Returns:
            AssumptionValidationResult
        """
        if assumption_id not in self.assumptions:
            logger.warning(f"Unknown assumption: {assumption_id}")
            return AssumptionValidationResult(
                assumption_id=assumption_id,
                valid=False,
                validation_time=datetime.utcnow(),
                validation_type=AssumptionValidationType.MANUAL,
                actual_value=None,
                expected_value=None,
                confidence=0.0,
                notes="Assumption not registered",
            )

        assumption = self.assumptions[assumption_id]

        # Check if assumption is still valid
        valid, confidence = self._validate_value(
            actual_value, assumption.expected_value, assumption.tolerance
        )

        # Calculate error margin
        error_margin = self._calculate_error_margin(
            actual_value, assumption.expected_value
        )

        result = AssumptionValidationResult(
            assumption_id=assumption_id,
            valid=valid,
            validation_time=datetime.utcnow(),
            validation_type=assumption.validation_method,
            actual_value=actual_value,
            expected_value=assumption.expected_value,
            confidence=confidence,
            error_margin=error_margin,
            notes=f"Tolerance: {assumption.tolerance}",
        )

        # Record the result
        self.validation_results[assumption_id].append(result)

        # Update next check time
        self.next_check_times[assumption_id] = (
            datetime.utcnow() + assumption.check_frequency
        )

        # Check if this is a violation
        if not valid:
            self._create_violation(assumption, result, actual_value)
            logger.warning(f"Assumption violated: {assumption_id}")
        else:
            logger.debug(f"Assumption valid: {assumption_id}")

        return result

    def predict_assumption_failure(
        self, assumption_id: str
    ) -> Optional[AssumptionViolation]:
        """Predict if an assumption will likely be violated.

        Analyzes past validation results to predict future failures.

        Args:
            assumption_id: ID of assumption to predict

        Returns:
            Predicted violation or None
        """
        if assumption_id not in self.validation_results:
            return None

        results = self.validation_results[assumption_id]
        if len(results) < 2:
            return None  # Need history to predict

        assumption = self.assumptions[assumption_id]

        # Simple prediction: if last 2+ checks showed increasing deviation
        recent_results = results[-3:]
        error_margins = [r.error_margin for r in recent_results]

        # Check for increasing trend
        if len(error_margins) >= 2:
            is_increasing = all(
                error_margins[i] <= error_margins[i + 1]
                for i in range(len(error_margins) - 1)
            )

            if is_increasing and error_margins[-1] > assumption.tolerance:
                # Predict violation
                impact = (
                    f"If assumption '{assumption.description}' is violated, "
                    f"the following tasks would be affected: {assumption.affected_tasks}"
                )
                mitigation = (
                    f"Monitor {assumption_id} closely. Be prepared to trigger "
                    f"adaptive replanning."
                )

                return AssumptionViolation(
                    assumption_id=assumption_id,
                    violation_time=datetime.utcnow(),
                    severity=assumption.severity,
                    impact=impact,
                    mitigation=mitigation,
                    replanning_required=assumption.severity in [
                        DeviationSeverity.HIGH,
                        DeviationSeverity.CRITICAL,
                    ],
                    affected_tasks=assumption.affected_tasks,
                )

        return None

    def get_violated_assumptions(self) -> List[AssumptionViolation]:
        """Get list of currently violated assumptions.

        Returns:
            List of AssumptionViolation objects
        """
        return list(self.violations.values())

    def schedule_assumption_checks(self) -> Dict[str, datetime]:
        """Get schedule of when assumptions need checking.

        Returns:
            Dict mapping assumption_id to next check time
        """
        return dict(self.next_check_times)

    def get_assumption_timeline(
        self, assumption_id: str
    ) -> List[AssumptionValidationResult]:
        """Get validation history for an assumption.

        Args:
            assumption_id: ID of assumption

        Returns:
            List of validation results in chronological order
        """
        return self.validation_results.get(assumption_id, [])

    def clear_violations(self) -> None:
        """Clear violation records (after replanning, etc)."""
        self.violations.clear()
        logger.info("Violations cleared")

    def reset(self) -> None:
        """Reset the validator for a new plan."""
        self.assumptions.clear()
        self.validation_results.clear()
        self.violations.clear()
        self.next_check_times.clear()
        logger.info("Assumption validator reset")

    def _validate_value(
        self, actual: Any, expected: Any, tolerance: float
    ) -> tuple[bool, float]:
        """Validate if actual value is within tolerance of expected.

        Args:
            actual: Actual value
            expected: Expected value
            tolerance: Acceptable variance

        Returns:
            Tuple of (is_valid, confidence)
        """
        try:
            # Handle numeric values
            if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
                if expected == 0:
                    error = abs(actual - expected)
                    is_valid = error == 0
                    confidence = 1.0 if is_valid else 0.0
                else:
                    error_ratio = abs(actual - expected) / abs(expected)
                    is_valid = error_ratio <= tolerance
                    confidence = max(0.0, 1.0 - error_ratio)
                return is_valid, confidence

            # Handle boolean values
            if isinstance(actual, bool) and isinstance(expected, bool):
                is_valid = actual == expected
                confidence = 1.0 if is_valid else 0.0
                return is_valid, confidence

            # Handle string values (exact match)
            if isinstance(actual, str) and isinstance(expected, str):
                is_valid = actual == expected
                confidence = 1.0 if is_valid else 0.0
                return is_valid, confidence

            # Handle list/dict (length check for tolerance)
            if isinstance(actual, (list, dict)) and isinstance(
                expected, (list, dict)
            ):
                actual_len = len(actual)
                expected_len = len(expected)
                if expected_len == 0:
                    is_valid = actual_len == 0
                    confidence = 1.0 if is_valid else 0.0
                else:
                    error_ratio = abs(actual_len - expected_len) / expected_len
                    is_valid = error_ratio <= tolerance
                    confidence = max(0.0, 1.0 - error_ratio)
                return is_valid, confidence

            # Default: equality check
            is_valid = actual == expected
            confidence = 1.0 if is_valid else 0.0
            return is_valid, confidence

        except Exception as e:
            logger.error(f"Error validating value: {e}")
            return False, 0.0

    def _calculate_error_margin(self, actual: Any, expected: Any) -> float:
        """Calculate error margin between actual and expected values.

        Args:
            actual: Actual value
            expected: Expected value

        Returns:
            Error margin as float (0.0 to 1.0)
        """
        try:
            if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
                if expected == 0:
                    return 1.0 if actual != 0 else 0.0
                return abs(actual - expected) / abs(expected)

            if isinstance(actual, (list, dict)) and isinstance(expected, (list, dict)):
                if len(expected) == 0:
                    return 1.0 if len(actual) > 0 else 0.0
                return abs(len(actual) - len(expected)) / len(expected)

            return 1.0 if actual != expected else 0.0
        except Exception:
            return 0.5

    def _create_violation(
        self,
        assumption: Assumption,
        result: AssumptionValidationResult,
        actual_value: Any,
    ) -> None:
        """Create a violation record for a failed assumption.

        Args:
            assumption: The assumption that was violated
            result: The validation result
            actual_value: The actual value observed
        """
        impact = (
            f"Assumption '{assumption.description}' was violated. "
            f"Expected: {assumption.expected_value}, Actual: {actual_value}"
        )
        mitigation = (
            f"Affected tasks: {assumption.affected_tasks}. "
            f"Consider triggering adaptive replanning."
        )

        violation = AssumptionViolation(
            assumption_id=assumption.assumption_id,
            violation_time=result.validation_time,
            severity=assumption.severity,
            impact=impact,
            mitigation=mitigation,
            replanning_required=assumption.severity in [
                DeviationSeverity.HIGH,
                DeviationSeverity.CRITICAL,
            ],
            affected_tasks=assumption.affected_tasks,
            validation_result=result,
        )

        self.violations[assumption.assumption_id] = violation
