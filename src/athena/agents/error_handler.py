"""
Error Handler for Phase 4 Integration Orchestrator.

Handles fault detection, classification, and automatic recovery strategies.
"""

import logging
import uuid
from typing import Optional
from datetime import datetime
from collections import defaultdict

from .orchestrator_models import ErrorRecord

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker pattern for fault tolerance."""

    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 60):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Failures before opening circuit
            timeout_seconds: Timeout before attempting to close
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half_open

    def record_success(self):
        """Record a successful operation."""
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self):
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

    def can_attempt(self) -> bool:
        """Check if operation can be attempted.

        Returns:
            True if circuit is closed or timeout has passed
        """
        if self.state == "closed":
            return True

        if self.state == "open" and self.last_failure_time:
            elapsed = (datetime.now() - self.last_failure_time).total_seconds()
            if elapsed >= self.timeout_seconds:
                self.state = "half_open"
                logger.info("Circuit breaker half-open, attempting reset")
                return True
            return False

        if self.state == "half_open":
            return True

        return False

    def get_status(self) -> dict:
        """Get circuit breaker status."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
        }


class ErrorHandler:
    """Handles error detection, classification, and recovery."""

    def __init__(self):
        """Initialize error handler."""
        self.error_records: dict[str, ErrorRecord] = {}
        self.error_count = 0
        self.recovery_strategies = {
            "timeout": self._handle_timeout,
            "resource_exhausted": self._handle_resource_exhausted,
            "agent_failure": self._handle_agent_failure,
            "dependency_failed": self._handle_dependency_failed,
            "unknown": self._handle_unknown,
        }
        self.circuit_breakers: dict[str, CircuitBreaker] = defaultdict(
            lambda: CircuitBreaker(failure_threshold=5, timeout_seconds=60)
        )
        self.retry_backoff_ms = 100  # Initial backoff in milliseconds

    def record_error(
        self,
        workflow_id: str,
        step_id: str,
        agent_type: str,
        error_type: str,
        error_message: str,
        severity: str = "medium",
    ) -> ErrorRecord:
        """Record an error.

        Args:
            workflow_id: Workflow ID where error occurred
            step_id: Step ID where error occurred
            agent_type: Type of agent that errored
            error_type: Type of error (timeout, resource_exhausted, etc.)
            error_message: Error message
            severity: Severity level (low, medium, high, critical)

        Returns:
            Created ErrorRecord
        """
        error_id = str(uuid.uuid4())
        error = ErrorRecord(
            error_id=error_id,
            workflow_id=workflow_id,
            step_id=step_id,
            agent_type=agent_type,
            error_type=error_type,
            error_message=error_message,
            severity=severity,
            is_recoverable=self._is_recoverable(error_type, severity),
        )

        self.error_records[error_id] = error
        self.error_count += 1

        # Record failure in circuit breaker
        self.circuit_breakers[agent_type].record_failure()

        logger.error(
            f"Error {error_id}: {error_type} in {agent_type} - {error_message}"
        )

        return error

    def attempt_recovery(self, error_id: str) -> dict:
        """Attempt to recover from an error.

        Args:
            error_id: Error record ID

        Returns:
            Recovery result dict
        """
        if error_id not in self.error_records:
            return {"success": False, "reason": "Unknown error"}

        error = self.error_records[error_id]

        if not error.is_recoverable:
            return {"success": False, "reason": "Error not recoverable"}

        if error.recovery_attempted:
            return {"success": False, "reason": "Recovery already attempted"}

        # Get recovery strategy
        strategy_fn = self.recovery_strategies.get(
            error.error_type, self.recovery_strategies["unknown"]
        )

        try:
            error.recovery_attempted = True
            result = strategy_fn(error)
            error.recovery_successful = result.get("success", False)
            return result
        except Exception as e:
            logger.error(f"Recovery attempt failed: {e}")
            error.recovery_successful = False
            return {"success": False, "reason": f"Recovery failed: {str(e)}"}

    def _is_recoverable(self, error_type: str, severity: str) -> bool:
        """Determine if an error is recoverable.

        Args:
            error_type: Type of error
            severity: Severity level

        Returns:
            True if recoverable
        """
        # Critical errors are generally not recoverable
        if severity == "critical":
            return False

        # Timeouts and resource exhaustion are recoverable
        if error_type in ["timeout", "resource_exhausted"]:
            return True

        # Dependencies are recoverable if not permanent failure
        if error_type == "dependency_failed":
            return True

        return error_type != "unknown"

    def _handle_timeout(self, error: ErrorRecord) -> dict:
        """Handle timeout error.

        Args:
            error: Error record

        Returns:
            Recovery result
        """
        logger.info(f"Attempting recovery from timeout in {error.step_id}")
        # Retry with longer timeout
        return {
            "success": True,
            "action": "retry",
            "recommendation": "Increase timeout and retry",
            "timeout_ms": 30000,
        }

    def _handle_resource_exhausted(self, error: ErrorRecord) -> dict:
        """Handle resource exhausted error.

        Args:
            error: Error record

        Returns:
            Recovery result
        """
        logger.info(f"Attempting recovery from resource exhaustion in {error.step_id}")
        # Wait and retry
        return {
            "success": True,
            "action": "wait_and_retry",
            "recommendation": "Wait for resource cleanup and retry",
            "wait_seconds": 5,
        }

    def _handle_agent_failure(self, error: ErrorRecord) -> dict:
        """Handle agent failure.

        Args:
            error: Error record

        Returns:
            Recovery result
        """
        logger.info(f"Attempting recovery from agent failure: {error.agent_type}")
        # Check if circuit breaker is open
        cb = self.circuit_breakers[error.agent_type]
        if cb.state == "open":
            return {
                "success": False,
                "reason": f"Circuit breaker open for {error.agent_type}",
            }
        # Retry step
        return {
            "success": True,
            "action": "retry_step",
            "recommendation": "Retry failed step with same agent",
        }

    def _handle_dependency_failed(self, error: ErrorRecord) -> dict:
        """Handle dependency failure.

        Args:
            error: Error record

        Returns:
            Recovery result
        """
        logger.info(f"Dependency failure in {error.step_id}")
        # Can't recover - parent step failed
        return {
            "success": False,
            "reason": "Parent step failed, cannot proceed",
        }

    def _handle_unknown(self, error: ErrorRecord) -> dict:
        """Handle unknown error.

        Args:
            error: Error record

        Returns:
            Recovery result
        """
        logger.info(f"Attempting recovery from unknown error in {error.step_id}")
        # Try to retry
        return {
            "success": True,
            "action": "retry",
            "recommendation": "Retry failed step",
        }

    def get_error_statistics(self) -> dict:
        """Get error statistics.

        Returns:
            Error statistics dict
        """
        by_type = defaultdict(int)
        by_severity = defaultdict(int)

        for error in self.error_records.values():
            by_type[error.error_type] += 1
            by_severity[error.severity] += 1

        recoverable = sum(
            1 for e in self.error_records.values() if e.is_recoverable
        )
        recovered = sum(
            1 for e in self.error_records.values() if e.recovery_successful
        )

        return {
            "total_errors": self.error_count,
            "by_type": dict(by_type),
            "by_severity": dict(by_severity),
            "recoverable_count": recoverable,
            "recovered_count": recovered,
            "recovery_success_rate": (
                (recovered / recoverable * 100) if recoverable > 0 else 0
            ),
        }

    def get_circuit_breaker_status(self, agent_type: str) -> dict:
        """Get circuit breaker status for an agent.

        Args:
            agent_type: Type of agent

        Returns:
            Circuit breaker status
        """
        return self.circuit_breakers[agent_type].get_status()

    def reset_circuit_breaker(self, agent_type: str):
        """Reset circuit breaker for an agent.

        Args:
            agent_type: Type of agent
        """
        self.circuit_breakers[agent_type] = CircuitBreaker(
            failure_threshold=5, timeout_seconds=60
        )
        logger.info(f"Circuit breaker reset for {agent_type}")

    def get_error_history(self, agent_type: str, limit: int = 10) -> list[dict]:
        """Get recent errors for an agent.

        Args:
            agent_type: Type of agent
            limit: Maximum number of errors to return

        Returns:
            List of error records
        """
        errors = [
            e.to_dict()
            for e in self.error_records.values()
            if e.agent_type == agent_type
        ]
        errors.sort(key=lambda x: x.get("error_id"), reverse=True)
        return errors[:limit]
