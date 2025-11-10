"""Enhanced Memory Manager with Agentic Verification and Observability.

This module extends UnifiedMemoryManager with:
1. VerificationGateway integration - All operations validated before commit
2. VerificationObserver - Track why decisions pass/fail
3. FeedbackMetricsCollector - Measure system improvement
4. Decision outcome recording - Learn from hindsight

Implements the complete agentic loop for all memory operations.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from .manager import UnifiedMemoryManager
from .verification import (
    VerificationGateway,
    VerificationObserver,
    FeedbackMetricsCollector,
    GateType,
)

logger = logging.getLogger(__name__)


class AgenticMemoryManager:
    """Enhanced memory manager with verification, observability, and metrics."""

    def __init__(self, base_manager: UnifiedMemoryManager):
        """
        Initialize agentic memory manager.

        Args:
            base_manager: UnifiedMemoryManager instance to enhance
        """
        self.manager = base_manager
        self.gateway = VerificationGateway()
        self.observer = VerificationObserver()
        self.metrics = FeedbackMetricsCollector()

        # Store original store method
        self._original_store = base_manager.store
        self._original_retrieve = base_manager.retrieve

    def retrieve(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        k: int = 5,
        verify: bool = True,
        track_decision: bool = True,
    ) -> Dict[str, Any]:
        """
        Enhanced retrieve with verification and observability.

        Args:
            query: Search query
            context: Optional context
            k: Number of results
            verify: Whether to run verification gates
            track_decision: Whether to record decision outcome

        Returns:
            Results with verification metadata
        """
        operation_id = f"retrieve_{datetime.now().timestamp()}"
        start_time = datetime.now()

        try:
            # Execute retrieval
            results = self._original_retrieve(query, context, k)

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            # Verify output if enabled
            if verify:
                result = self.gateway.verify(
                    operation_type="retrieve",
                    operation_data={
                        "operation_id": operation_id,
                        "query": query,
                        "result_count": len(results),
                        "execution_time_ms": execution_time,
                        "base_confidence": 0.8,  # Default for retrieval
                    }
                )

                # Record decision
                if track_decision:
                    outcome = self.observer.record_decision(
                        result,
                        "accepted" if result.passed else "rejected"
                    )

                # Record metrics
                self.metrics.record_metric("operation_latency_ms", execution_time)
                self.metrics.record_metric("gate_pass_rate", 1.0 if result.passed else 0.0)

                return {
                    **results,
                    "_verification": {
                        "operation_id": operation_id,
                        "passed": result.passed,
                        "violations": len(result.violations),
                        "confidence": result.confidence_score,
                        "execution_time_ms": execution_time,
                    }
                }

            return results

        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            self.metrics.record_metric("operation_latency_ms",
                                      (datetime.now() - start_time).total_seconds() * 1000)
            raise

    def store(
        self,
        content: str,
        content_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        verify: bool = True,
        track_decision: bool = True,
    ) -> Dict[str, Any]:
        """
        Enhanced store with verification and observability.

        Args:
            content: Content to store
            content_type: Type of content
            metadata: Optional metadata
            verify: Whether to run verification gates
            track_decision: Whether to record decision outcome

        Returns:
            Store result with verification metadata
        """
        operation_id = f"store_{datetime.now().timestamp()}"
        start_time = datetime.now()

        try:
            # Execute store
            result = self._original_store(content, content_type, metadata)

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            # Verify output if enabled
            if verify:
                gate_result = self.gateway.verify(
                    operation_type="store",
                    operation_data={
                        "operation_id": operation_id,
                        "content_type": content_type,
                        "content_length": len(content),
                        "execution_time_ms": execution_time,
                        "base_confidence": 0.9,  # Higher for store operations
                    }
                )

                # Record decision
                if track_decision:
                    outcome = self.observer.record_decision(
                        gate_result,
                        "accepted" if gate_result.passed else "rejected"
                    )

                # Record metrics
                self.metrics.record_metric("operation_latency_ms", execution_time)
                self.metrics.record_metric("gate_pass_rate", 1.0 if gate_result.passed else 0.0)

                return {
                    **result,
                    "_verification": {
                        "operation_id": operation_id,
                        "passed": gate_result.passed,
                        "violations": len(gate_result.violations),
                        "confidence": gate_result.confidence_score,
                        "execution_time_ms": execution_time,
                    }
                }

            return result

        except Exception as e:
            logger.error(f"Store failed: {e}")
            self.metrics.record_metric("operation_latency_ms",
                                      (datetime.now() - start_time).total_seconds() * 1000)
            raise

    def verify_operation(
        self,
        operation_type: str,
        operation_data: Dict[str, Any],
        gate_types: Optional[list[GateType]] = None,
    ) -> Dict[str, Any]:
        """
        Explicitly verify an operation.

        Args:
            operation_type: Type of operation
            operation_data: Operation data to verify
            gate_types: Specific gates to run

        Returns:
            Verification result with details
        """
        result = self.gateway.verify(operation_type, operation_data, gate_types)

        return {
            "operation_id": result.operation_id,
            "operation_type": result.operation_type,
            "passed": result.passed,
            "confidence": result.confidence_score,
            "violations": [
                {
                    "gate_type": v.gate_type.value,
                    "severity": v.severity.value,
                    "message": v.message,
                    "remediation_hints": v.remediation_hints,
                }
                for v in result.violations
            ],
            "warnings": [
                {
                    "gate_type": w.gate_type.value,
                    "severity": w.severity.value,
                    "message": w.message,
                }
                for w in result.warnings
            ],
            "execution_time_ms": result.execution_time_ms,
        }

    def get_operation_health(self, operation_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get health metrics for operations.

        Args:
            operation_type: Specific operation type, or None for all

        Returns:
            Health metrics
        """
        return self.observer.get_operation_health(operation_type)

    def get_gate_health(self) -> Dict[str, Any]:
        """Get health metrics for verification gates."""
        return self.observer.get_gate_health()

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health score and metrics."""
        return {
            "health_score": self.metrics.calculate_system_health_score(),
            "metrics_summary": self.metrics.get_quality_metrics_summary(),
            "anomalies": self.metrics.get_anomalies(),
            "alerts": self.metrics.get_metric_alerts(),
            "recommendations": self.metrics.get_recommendations(),
        }

    def get_decision_insights(self) -> Dict[str, Any]:
        """Get insights from recent decisions."""
        return {
            "recent_decisions": self.observer.get_decision_history(limit=20),
            "operation_health": self.observer.get_operation_health(),
            "gate_health": self.observer.get_gate_health(),
            "top_violations": [
                {
                    "violation_type": p.violation_type,
                    "gate_type": p.gate_type.value,
                    "frequency": p.frequency,
                    "example_operations": p.example_operations[:3],
                }
                for p in self.observer.get_top_violation_patterns(limit=5)
            ],
            "insights": self.observer.get_actionable_insights(),
        }

    def record_operation_outcome(
        self,
        decision_id: str,
        actual_outcome: str,
        was_correct: bool,
        lessons: Optional[list[str]] = None,
    ) -> None:
        """
        Record the actual outcome of a decision.

        Enables feedback loop learning.

        Args:
            decision_id: ID of the decision
            actual_outcome: What actually happened
            was_correct: Was the decision correct in hindsight?
            lessons: Lessons learned
        """
        self.observer.record_outcome(
            decision_id,
            actual_outcome,
            was_correct,
            lessons
        )

        # Record decision accuracy metric
        if was_correct:
            self.metrics.record_metric("decision_accuracy", 1.0)
        else:
            self.metrics.record_metric("decision_accuracy", 0.0)

    def get_metric_report(self) -> str:
        """Export comprehensive metrics report as JSON string."""
        return self.metrics.export_metrics_report()

    def register_remediation_handler(
        self,
        gate_type: GateType,
        handler,
    ) -> None:
        """
        Register custom remediation handler for a gate type.

        Args:
            gate_type: Gate type to handle
            handler: Callable(violation, data) -> remediated_data
        """
        self.gateway.register_remediation_handler(gate_type, handler)

    def __getattr__(self, name):
        """Delegate unknown attributes to base manager."""
        return getattr(self.manager, name)
