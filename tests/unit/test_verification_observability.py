"""Unit tests for VerificationObserver."""

import pytest
from datetime import datetime

from athena.verification import (
    VerificationObserver,
    VerificationGateway,
    GateType,
    GateSeverity,
)


class TestDecisionRecording:
    """Test decision recording."""

    def test_record_decision(self):
        """Test recording a decision."""
        observer = VerificationObserver()
        gateway = VerificationGateway()

        result = gateway.verify(
            "test_operation",
            {
                "grounding_score": 0.8,
                "confidence": 0.85,
                "consistency_score": 0.9,
                "verified_properties": ["optimality"],
                "redundancy_ratio": 0.05,
                "coherence_score": 0.8,
                "execution_time_ms": 100,
                "base_confidence": 0.7,
            }
        )

        outcome = observer.record_decision(result, "accepted")

        assert outcome is not None
        assert outcome.operation_type == "test_operation"
        assert outcome.action_taken == "accepted"

    def test_record_outcome(self):
        """Test recording decision outcome."""
        observer = VerificationObserver()
        gateway = VerificationGateway()

        result = gateway.verify("test", {"grounding_score": 0.8, "base_confidence": 0.7})
        outcome = observer.record_decision(result, "accepted")

        observer.record_outcome(
            outcome.decision_id,
            "operation succeeded",
            True,
            ["lesson1", "lesson2"]
        )

        assert outcome.actual_outcome == "operation succeeded"
        assert outcome.was_correct == True
        assert len(outcome.learned_lessons) == 2


class TestViolationPatterns:
    """Test violation pattern detection."""

    def test_pattern_detection(self):
        """Test recurring violations are detected."""
        observer = VerificationObserver()
        gateway = VerificationGateway()

        # Record multiple violations of same type
        for i in range(3):
            result = gateway.verify(
                "consolidate",
                {
                    "grounding_score": 0.3,  # Low grounding
                    "base_confidence": 0.5,
                }
            )
            observer.record_decision(result, "rejected")

        patterns = observer.get_top_violation_patterns()
        assert len(patterns) > 0
        assert patterns[0].frequency >= 3

    def test_pattern_frequency_tracking(self):
        """Test pattern frequency increases."""
        observer = VerificationObserver()
        gateway = VerificationGateway()

        # Record same violation multiple times
        for _ in range(5):
            result = gateway.verify(
                "test",
                {"grounding_score": 0.2, "base_confidence": 0.5}
            )
            observer.record_decision(result, "rejected")

        patterns = observer.get_top_violation_patterns()
        if patterns:
            assert patterns[0].frequency == 5


class TestOperationHealth:
    """Test operation health metrics."""

    def test_operation_health_single_type(self):
        """Test health metrics for single operation type."""
        observer = VerificationObserver()
        gateway = VerificationGateway()

        # Record multiple operations
        for i in range(10):
            passed = i % 2 == 0  # 50% pass rate
            result = gateway.verify(
                "remember",
                {"grounding_score": 0.8 if passed else 0.3, "base_confidence": 0.7}
            )
            observer.record_decision(result, "accepted" if passed else "rejected")

        health = observer.get_operation_health("remember")
        assert health["operation_type"] == "remember"
        assert health["pass_rate"] == 0.5

    def test_decision_accuracy(self):
        """Test decision accuracy calculation."""
        observer = VerificationObserver()
        gateway = VerificationGateway()

        # Record decisions with outcomes
        for i in range(4):
            result = gateway.verify("test", {"grounding_score": 0.8, "base_confidence": 0.7})
            outcome = observer.record_decision(result, "accepted")
            observer.record_outcome(outcome.decision_id, "succeeded", i % 2 == 0)

        accuracy = observer.get_decision_accuracy("test")
        assert accuracy == 0.5  # 2 out of 4 correct


class TestGateHealth:
    """Test gate health metrics."""

    def test_gate_health_metrics(self):
        """Test gate health tracking."""
        observer = VerificationObserver()
        gateway = VerificationGateway()

        # Run multiple verifications
        for i in range(10):
            passed = i < 7  # 70% pass rate
            result = gateway.verify(
                "test",
                {"grounding_score": 0.8 if passed else 0.3, "base_confidence": 0.7}
            )
            observer.record_decision(result, "accepted" if passed else "rejected")

        gate_health = observer.get_gate_health()
        assert "grounding" in gate_health


class TestInsights:
    """Test actionable insights."""

    def test_actionable_insights_no_data(self):
        """Test insights with no data."""
        observer = VerificationObserver()
        insights = observer.get_actionable_insights()

        assert isinstance(insights, list)
        assert len(insights) > 0  # At least one message

    def test_actionable_insights_with_issues(self):
        """Test insights detect issues."""
        observer = VerificationObserver()
        gateway = VerificationGateway()

        # Record many failures
        for _ in range(10):
            result = gateway.verify("consolidate", {"grounding_score": 0.2, "base_confidence": 0.5})
            observer.record_decision(result, "rejected")

        insights = observer.get_actionable_insights()
        assert any("consolidate" in insight for insight in insights)


class TestDecisionHistory:
    """Test decision history."""

    def test_decision_history_limit(self):
        """Test history respects limit."""
        observer = VerificationObserver()
        gateway = VerificationGateway()

        # Record 20 decisions
        for i in range(20):
            result = gateway.verify("test", {"grounding_score": 0.8, "base_confidence": 0.7})
            observer.record_decision(result, "accepted")

        history = observer.get_decision_history(limit=5)
        assert len(history) <= 5

    def test_decision_history_content(self):
        """Test history contains expected fields."""
        observer = VerificationObserver()
        gateway = VerificationGateway()

        result = gateway.verify("test", {"grounding_score": 0.8, "base_confidence": 0.7})
        observer.record_decision(result, "accepted")

        history = observer.get_decision_history(limit=1)
        assert len(history) == 1
        assert "action_taken" in history[0]
        assert "gate_passed" in history[0]
        assert "confidence" in history[0]


class TestTelemetryExport:
    """Test telemetry export."""

    def test_export_telemetry_json(self):
        """Test exporting telemetry as JSON."""
        observer = VerificationObserver()
        gateway = VerificationGateway()

        result = gateway.verify("test", {"grounding_score": 0.8, "base_confidence": 0.7})
        observer.record_decision(result, "accepted")

        telemetry = observer.export_telemetry(format="json")
        assert isinstance(telemetry, str)
        assert "total_decisions" in telemetry
        assert "gate_health" in telemetry


class TestOperationTypeTracking:
    """Test tracking by operation type."""

    def test_multiple_operation_types(self):
        """Test tracking multiple operation types."""
        observer = VerificationObserver()
        gateway = VerificationGateway()

        operation_types = ["remember", "consolidate", "retrieve"]

        for op_type in operation_types:
            result = gateway.verify(op_type, {"grounding_score": 0.8, "base_confidence": 0.7})
            observer.record_decision(result, "accepted")

        health = observer.get_operation_health()
        assert len(health) >= len(operation_types)
        assert all(op_type in health for op_type in operation_types)


class TestViolationDetails:
    """Test violation detail tracking."""

    def test_violation_details_captured(self):
        """Test violation details are captured."""
        observer = VerificationObserver()
        gateway = VerificationGateway()

        result = gateway.verify(
            "test",
            {"grounding_score": 0.2, "base_confidence": 0.5}  # Will fail
        )
        observer.record_decision(result, "rejected")

        patterns = observer.get_top_violation_patterns()
        if patterns:
            assert patterns[0].severity_distribution is not None
            assert len(patterns[0].example_operations) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
