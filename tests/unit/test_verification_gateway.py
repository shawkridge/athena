"""Unit tests for VerificationGateway and gate implementations."""

import pytest
from datetime import datetime

from athena.verification import (
    VerificationGateway,
    GroundingGate,
    ConfidenceGate,
    ConsistencyGate,
    SoundnessGate,
    MinimalityGate,
    CoherenceGate,
    EfficiencyGate,
    GateType,
    GateSeverity,
)


class TestGroundingGate:
    """Test GroundingGate."""

    def test_pass_sufficient_grounding(self):
        """Test gate passes with sufficient grounding."""
        gate = GroundingGate(min_grounding_score=0.5)
        violation = gate.verify({"grounding_score": 0.8})
        assert violation is None

    def test_fail_insufficient_grounding(self):
        """Test gate fails with insufficient grounding."""
        gate = GroundingGate(min_grounding_score=0.5)
        violation = gate.verify({"grounding_score": 0.3})
        assert violation is not None
        assert violation.gate_type == GateType.GROUNDING
        assert violation.severity == GateSeverity.ERROR

    def test_grounding_at_threshold(self):
        """Test gate at exact threshold."""
        gate = GroundingGate(min_grounding_score=0.5)
        violation = gate.verify({"grounding_score": 0.5})
        assert violation is None


class TestConfidenceGate:
    """Test ConfidenceGate."""

    def test_pass_reasonable_confidence(self):
        """Test gate passes with reasonable confidence."""
        gate = ConfidenceGate()
        violation = gate.verify({"confidence": 0.75, "sample_count": 5})
        assert violation is None

    def test_fail_high_confidence_low_samples(self):
        """Test gate fails with high confidence and low samples."""
        gate = ConfidenceGate()
        violation = gate.verify({"confidence": 0.85, "sample_count": 1})
        assert violation is not None
        assert violation.gate_type == GateType.CONFIDENCE

    def test_fail_overconfident(self):
        """Test gate fails with overconfident estimate."""
        gate = ConfidenceGate(max_confidence=0.95)
        violation = gate.verify({"confidence": 0.98, "sample_count": 10})
        assert violation is not None


class TestConsistencyGate:
    """Test ConsistencyGate."""

    def test_pass_consistent(self):
        """Test gate passes with consistent data."""
        gate = ConsistencyGate()
        violation = gate.verify({
            "consistency_score": 0.9,
            "existing_conflicts": []
        })
        assert violation is None

    def test_fail_inconsistent(self):
        """Test gate fails with inconsistent data."""
        gate = ConsistencyGate(consistency_threshold=0.7)
        violation = gate.verify({
            "consistency_score": 0.6,
            "existing_conflicts": ["conflict1", "conflict2"]
        })
        assert violation is not None
        assert violation.gate_type == GateType.CONSISTENCY


class TestSoundnessGate:
    """Test SoundnessGate."""

    def test_pass_all_properties(self):
        """Test gate passes when all properties verified."""
        gate = SoundnessGate()
        violation = gate.verify({
            "verified_properties": [
                "optimality", "completeness", "consistency",
                "soundness", "minimality"
            ]
        })
        assert violation is None

    def test_fail_missing_properties(self):
        """Test gate fails when properties missing."""
        gate = SoundnessGate()
        violation = gate.verify({
            "verified_properties": ["optimality"]
        })
        assert violation is not None
        assert violation.gate_type == GateType.SOUNDNESS


class TestMinimalityGate:
    """Test MinimalityGate."""

    def test_pass_minimal(self):
        """Test gate passes with minimal representation."""
        gate = MinimalityGate()
        violation = gate.verify({
            "redundancy_ratio": 0.05,
            "duplicate_count": 0
        })
        assert violation is None

    def test_fail_redundant(self):
        """Test gate fails with high redundancy."""
        gate = MinimalityGate(max_redundancy_ratio=0.2)
        violation = gate.verify({
            "redundancy_ratio": 0.35,
            "duplicate_count": 5
        })
        assert violation is not None
        assert violation.gate_type == GateType.MINIMALITY


class TestCoherenceGate:
    """Test CoherenceGate."""

    def test_pass_coherent(self):
        """Test gate passes with coherent knowledge."""
        gate = CoherenceGate()
        violation = gate.verify({"coherence_score": 0.8})
        assert violation is None

    def test_fail_incoherent(self):
        """Test gate fails with incoherent knowledge."""
        gate = CoherenceGate(min_coherence_score=0.6)
        violation = gate.verify({"coherence_score": 0.4})
        assert violation is not None
        assert violation.gate_type == GateType.COHERENCE


class TestEfficiencyGate:
    """Test EfficiencyGate."""

    def test_pass_efficient(self):
        """Test gate passes with efficient operation."""
        gate = EfficiencyGate()
        violation = gate.verify({"execution_time_ms": 100.0})
        assert violation is None

    def test_warn_slow(self):
        """Test gate warns on slow operation."""
        gate = EfficiencyGate(max_execution_time_ms=5000)
        violation = gate.verify({"execution_time_ms": 8000})
        assert violation is not None
        assert violation.gate_type == GateType.EFFICIENCY
        assert violation.severity == GateSeverity.INFO


class TestVerificationGateway:
    """Test VerificationGateway."""

    def test_all_gates_pass(self):
        """Test verification when all gates pass."""
        gateway = VerificationGateway()
        result = gateway.verify(
            "test_operation",
            {
                "grounding_score": 0.8,
                "confidence": 0.85,
                "consistency_score": 0.9,
                "verified_properties": ["optimality", "completeness", "consistency", "soundness", "minimality"],
                "redundancy_ratio": 0.05,
                "coherence_score": 0.8,
                "execution_time_ms": 100,
                "base_confidence": 0.7,
            }
        )
        assert result.passed
        assert len(result.violations) == 0

    def test_gate_violations_recorded(self):
        """Test violations are recorded."""
        gateway = VerificationGateway()
        result = gateway.verify(
            "test_operation",
            {
                "grounding_score": 0.3,  # Below threshold
                "confidence": 0.85,
                "consistency_score": 0.9,
                "verified_properties": ["optimality"],  # Missing properties
                "redundancy_ratio": 0.05,
                "coherence_score": 0.8,
                "execution_time_ms": 100,
                "base_confidence": 0.7,
            }
        )
        assert not result.passed
        assert len(result.violations) > 0

    def test_confidence_adjusted_by_violations(self):
        """Test confidence adjusted based on violations."""
        gateway = VerificationGateway()
        result = gateway.verify(
            "test_operation",
            {
                "grounding_score": 0.3,
                "confidence": 0.9,
                "consistency_score": 0.5,
                "verified_properties": [],
                "redundancy_ratio": 0.05,
                "coherence_score": 0.3,
                "execution_time_ms": 100,
                "base_confidence": 0.9,
            }
        )
        # Confidence should be reduced due to violations
        assert result.confidence_score < 0.9

    def test_remediation_handler_registration(self):
        """Test registering custom remediation handler."""
        gateway = VerificationGateway()

        def custom_handler(violation, data):
            data["remediated"] = True
            return data

        gateway.register_remediation_handler(GateType.GROUNDING, custom_handler)

        result = gateway.verify(
            "test",
            {"grounding_score": 0.3, "base_confidence": 0.5}
        )

        remediated = gateway.apply_remediation(result, {})
        assert remediated.get("remediated") == True

    def test_gate_health_tracking(self):
        """Test gate success rate tracking."""
        gateway = VerificationGateway()

        # Run several verifications
        for i in range(5):
            data = {
                "grounding_score": 0.5 + (i * 0.1),
                "confidence": 0.7,
                "consistency_score": 0.8,
                "verified_properties": ["optimality"],
                "redundancy_ratio": 0.05,
                "coherence_score": 0.7,
                "execution_time_ms": 100,
                "base_confidence": 0.7,
            }
            gateway.verify("test", data)

        health = gateway.get_gate_health()
        assert "grounding" in health
        assert health["grounding"]["success_rate"] > 0

    def test_decision_logging(self):
        """Test decisions are logged."""
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

        assert len(gateway.decision_log) > 0
        logged = gateway.decision_log[-1]
        assert logged.operation_type == "test_operation"
        assert logged.passed == result.passed

    def test_specific_gate_types(self):
        """Test running specific gate types only."""
        gateway = VerificationGateway()
        result = gateway.verify(
            "test",
            {
                "grounding_score": 0.8,
                "confidence": 0.85,
                "base_confidence": 0.7,
            },
            gate_types=[GateType.GROUNDING, GateType.CONFIDENCE]
        )
        # Only 2 gates should run
        assert len(result.violations) + len(result.warnings) <= 2


class TestGateRemediation:
    """Test gate remediation workflow."""

    def test_grounding_remediation_hints(self):
        """Test grounding gate provides remediation hints."""
        gate = GroundingGate(min_grounding_score=0.5)
        violation = gate.verify({"grounding_score": 0.3})

        assert violation is not None
        assert len(violation.remediation_hints) > 0
        assert any("evidence" in hint.lower() for hint in violation.remediation_hints)

    def test_confidence_remediation_hints(self):
        """Test confidence gate provides remediation hints."""
        gate = ConfidenceGate()
        violation = gate.verify({"confidence": 0.85, "sample_count": 1})

        assert violation is not None
        assert len(violation.remediation_hints) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
