"""Observability and monitoring for verification decisions.

Tracks why decisions succeeded/failed and enables learning from verification outcomes.
Implements the feedback loop in the agentic diagram.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from collections import defaultdict
import json

from .gateway import GateResult, GateType, GateSeverity


@dataclass
class DecisionOutcome:
    """Record of a verification decision and its outcome."""

    decision_id: str
    operation_type: str
    gate_result: GateResult
    action_taken: str  # "accepted", "rejected", "remediated", "escalated"
    actual_outcome: Optional[str] = None  # What happened after decision?
    was_correct: Optional[bool] = None  # Was the decision correct in hindsight?
    learned_lessons: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ViolationPattern:
    """Recurring pattern of gate violations."""

    violation_type: str
    gate_type: GateType
    frequency: int
    last_seen: datetime
    example_operations: List[str] = field(default_factory=list)
    root_causes: List[str] = field(default_factory=list)
    severity_distribution: Dict[str, int] = field(default_factory=dict)


class VerificationObserver:
    """Track and analyze verification decisions for learning."""

    def __init__(self):
        """Initialize observer."""
        self.decisions: List[DecisionOutcome] = []
        self.violation_patterns: Dict[str, ViolationPattern] = {}
        self.operation_type_stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"total": 0, "passed": 0, "failed": 0}
        )
        self.gate_type_stats: Dict[GateType, Dict[str, int]] = {
            gate_type: {"passed": 0, "failed": 0, "warnings": 0} for gate_type in GateType
        }

    def record_decision(
        self, gate_result: GateResult, action_taken: str, details: Optional[Dict[str, Any]] = None
    ) -> DecisionOutcome:
        """
        Record a verification decision.

        Args:
            gate_result: Result from verification gateway
            action_taken: Action taken based on result ("accepted", "rejected", etc.)
            details: Additional context

        Returns:
            Recorded decision
        """
        decision_id = f"{gate_result.operation_id}_{datetime.now().timestamp()}"

        outcome = DecisionOutcome(
            decision_id=decision_id,
            operation_type=gate_result.operation_type,
            gate_result=gate_result,
            action_taken=action_taken,
        )

        self.decisions.append(outcome)

        # Update statistics
        stats = self.operation_type_stats[gate_result.operation_type]
        stats["total"] += 1
        if gate_result.passed:
            stats["passed"] += 1
        else:
            stats["failed"] += 1

        # Track gate statistics
        for violation in gate_result.violations + gate_result.warnings:
            gate_stats = self.gate_type_stats[violation.gate_type]
            if violation.severity in (GateSeverity.ERROR, GateSeverity.CRITICAL):
                gate_stats["failed"] += 1
            else:
                gate_stats["warnings"] += 1

        # Track patterns
        self._update_violation_patterns(gate_result)

        return outcome

    def record_outcome(
        self,
        decision_id: str,
        actual_outcome: str,
        was_correct: bool,
        lessons: Optional[List[str]] = None,
    ) -> None:
        """
        Record the actual outcome of a decision.

        Args:
            decision_id: ID of the decision
            actual_outcome: What actually happened
            was_correct: Was the decision correct in hindsight?
            lessons: Lessons learned
        """
        # Find decision
        for decision in self.decisions:
            if decision.decision_id == decision_id:
                decision.actual_outcome = actual_outcome
                decision.was_correct = was_correct
                decision.learned_lessons = lessons or []
                break

    def _update_violation_patterns(self, gate_result: GateResult) -> None:
        """Track recurring violation patterns."""
        for violation in gate_result.violations + gate_result.warnings:
            pattern_key = f"{violation.gate_type.value}_{violation.message[:50]}"

            if pattern_key not in self.violation_patterns:
                self.violation_patterns[pattern_key] = ViolationPattern(
                    violation_type=violation.message,
                    gate_type=violation.gate_type,
                    frequency=0,
                    last_seen=datetime.now(),
                    severity_distribution={},
                )

            pattern = self.violation_patterns[pattern_key]
            pattern.frequency += 1
            pattern.last_seen = datetime.now()
            pattern.example_operations.append(gate_result.operation_id)

            severity_key = violation.severity.value
            pattern.severity_distribution[severity_key] = (
                pattern.severity_distribution.get(severity_key, 0) + 1
            )

    def get_decision_accuracy(self, operation_type: Optional[str] = None) -> float:
        """Get accuracy of decisions (% that were correct in hindsight)."""
        decisions = self.decisions

        if operation_type:
            decisions = [d for d in decisions if d.operation_type == operation_type]

        if not decisions:
            return 0.0

        evaluated = [d for d in decisions if d.was_correct is not None]
        if not evaluated:
            return 0.0

        correct = sum(1 for d in evaluated if d.was_correct)
        return correct / len(evaluated)

    def get_operation_health(self, operation_type: Optional[str] = None) -> Dict[str, Any]:
        """Get health metrics for operations."""
        if operation_type:
            stats = self.operation_type_stats.get(
                operation_type, {"total": 0, "passed": 0, "failed": 0}
            )
            return {
                "operation_type": operation_type,
                "total_operations": stats["total"],
                "passed": stats["passed"],
                "failed": stats["failed"],
                "pass_rate": stats["passed"] / stats["total"] if stats["total"] > 0 else 0.0,
                "accuracy": self.get_decision_accuracy(operation_type),
            }
        else:
            # Return all operation types
            health = {}
            for op_type in self.operation_type_stats.keys():
                health[op_type] = self.get_operation_health(op_type)
            return health

    def get_gate_health(self) -> Dict[str, Any]:
        """Get health metrics for gates."""
        health = {}

        for gate_type, stats in self.gate_type_stats.items():
            total = stats["passed"] + stats["failed"] + stats["warnings"]
            health[gate_type.value] = {
                "passed": stats["passed"],
                "failed": stats["failed"],
                "warnings": stats["warnings"],
                "total": total,
                "failure_rate": stats["failed"] / total if total > 0 else 0.0,
            }

        return health

    def get_top_violation_patterns(self, limit: int = 5) -> List[ViolationPattern]:
        """Get most frequent violation patterns."""
        patterns = list(self.violation_patterns.values())
        patterns.sort(key=lambda p: p.frequency, reverse=True)
        return patterns[:limit]

    def get_actionable_insights(self) -> List[str]:
        """Get actionable insights from verification data."""
        insights = []

        # Insight 1: Most problematic operations
        op_health = self.get_operation_health()
        for op_type, health in op_health.items():
            if health["fail_rate"] > 0.3:
                insights.append(
                    f"⚠️ Operation '{op_type}' has high failure rate "
                    f"({health['fail_rate']:.0%}). Review validation rules."
                )

        # Insight 2: Recurring violations
        top_violations = self.get_top_violation_patterns(3)
        for pattern in top_violations:
            if pattern.frequency > 10:
                insights.append(
                    f"🔄 Violation pattern '{pattern.violation_type}' occurred "
                    f"{pattern.frequency} times. Consider systematic fix."
                )

        # Insight 3: Gate effectiveness
        gate_health = self.get_gate_health()
        for gate_type, health in gate_health.items():
            if health["total"] > 0 and health["failure_rate"] > 0.5:
                insights.append(
                    f"🚨 Gate '{gate_type}' is very permissive "
                    f"({health['failure_rate']:.0%} of checks fail). Review thresholds."
                )

        # Insight 4: Decision accuracy
        for op_type in self.operation_type_stats.keys():
            accuracy = self.get_decision_accuracy(op_type)
            if accuracy < 0.7 and accuracy > 0:
                insights.append(
                    f"📊 Decision accuracy for '{op_type}' is {accuracy:.0%}. "
                    f"Consider retraining validation rules."
                )

        return insights if insights else ["✅ No actionable issues detected"]

    def get_decision_history(
        self, limit: int = 10, operation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent decision history."""
        decisions = self.decisions

        if operation_type:
            decisions = [d for d in decisions if d.operation_type == operation_type]

        recent = decisions[-limit:]

        history = []
        for decision in recent:
            history.append(
                {
                    "decision_id": decision.decision_id,
                    "operation_type": decision.operation_type,
                    "action_taken": decision.action_taken,
                    "gate_passed": decision.gate_result.passed,
                    "confidence": decision.gate_result.confidence_score,
                    "violations": len(decision.gate_result.violations),
                    "warnings": len(decision.gate_result.warnings),
                    "was_correct": decision.was_correct,
                    "timestamp": decision.timestamp.isoformat(),
                }
            )

        return history

    def export_telemetry(self, format: str = "json") -> str:
        """Export verification telemetry."""
        telemetry = {
            "total_decisions": len(self.decisions),
            "operation_health": self.get_operation_health(),
            "gate_health": self.get_gate_health(),
            "top_violations": [
                {
                    "violation_type": p.violation_type,
                    "gate_type": p.gate_type.value,
                    "frequency": p.frequency,
                }
                for p in self.get_top_violation_patterns()
            ],
            "insights": self.get_actionable_insights(),
            "timestamp": datetime.now().isoformat(),
        }

        if format == "json":
            return json.dumps(telemetry, indent=2)
        else:
            return str(telemetry)

    def get_recommendations(self) -> List[str]:
        """Get recommendations for improving verification."""
        recommendations = []

        # Get patterns
        patterns = self.get_top_violation_patterns()

        for pattern in patterns:
            if pattern.frequency > 5:
                if pattern.gate_type == GateType.GROUNDING:
                    recommendations.append(
                        f"Increase source event collection before consolidation (pattern: {pattern.violation_type[:40]}...)"
                    )
                elif pattern.gate_type == GateType.CONFIDENCE:
                    recommendations.append(
                        f"Apply confidence penalties for low-sample cases (pattern: {pattern.violation_type[:40]}...)"
                    )
                elif pattern.gate_type == GateType.CONSISTENCY:
                    recommendations.append(
                        f"Review conflicting memories in {pattern.example_operations[0] if pattern.example_operations else 'unknown'}"
                    )

        # Add gate-specific recommendations
        gate_health = self.get_gate_health()
        for gate_type, health in gate_health.items():
            if health["total"] > 20 and health["failure_rate"] > 0.2:
                recommendations.append(
                    f"Review threshold for {gate_type} gate (currently too strict: {health['failure_rate']:.0%} rejection rate)"
                )

        return recommendations if recommendations else ["Continue monitoring - system is healthy"]
