"""Tests for consciousness metrics validation experiments."""

import numpy as np
from athena.consciousness.validation import (
    ExperimentResult,
    ValidationExperiments,
)


class TestExperimentResult:
    """Test experiment result representation."""

    def test_experiment_result_creation(self):
        """Test creating experiment result."""
        result = ExperimentResult(
            name="Test Experiment",
            hypothesis="Test hypothesis",
            prediction="Test prediction",
            result="PASS",
            correlation=0.85,
            p_value=0.001,
            effect_size=0.72,
            evidence=["Evidence 1"],
        )
        assert result.name == "Test Experiment"
        assert result.result == "PASS"
        assert result.correlation == 0.85

    def test_experiment_result_to_dict(self):
        """Test converting result to dict."""
        result = ExperimentResult(
            name="Test",
            hypothesis="Test hypothesis",
            prediction="Test prediction",
            result="PASS",
            correlation=0.85,
            p_value=0.001,
        )
        data = result.to_dict()

        assert data["name"] == "Test"
        assert data["result"] == "PASS"
        assert data["correlation"] == 0.85


class TestGWTHypothesis:
    """Test Global Workspace Theory hypothesis."""

    def test_gwt_strong_correlation(self):
        """Test GWT with strong positive correlation."""
        validator = ValidationExperiments()

        # Create strongly correlated data
        global_workspace = np.linspace(2, 9, 20).tolist()
        consciousness = [0.8 * x + np.random.normal(0, 0.3) for x in global_workspace]

        result = validator.test_gwt_hypothesis(global_workspace, consciousness)

        assert result.result == "PASS"
        assert result.correlation > 0.5
        assert result.p_value < 0.05

    def test_gwt_weak_correlation(self):
        """Test GWT with weak correlation."""
        validator = ValidationExperiments()

        # Random data (no correlation)
        global_workspace = np.random.uniform(2, 9, 20).tolist()
        consciousness = np.random.uniform(2, 9, 20).tolist()

        result = validator.test_gwt_hypothesis(global_workspace, consciousness)

        # Should be FAIL or INCONCLUSIVE
        assert result.result in ["FAIL", "INCONCLUSIVE"]

    def test_gwt_insufficient_data(self):
        """Test GWT with insufficient data."""
        validator = ValidationExperiments()

        result = validator.test_gwt_hypothesis([1, 2], [1, 2])

        assert result.result == "INCONCLUSIVE"
        assert "Insufficient" in result.evidence[0]


class TestPhiIntegrationCorrelation:
    """Test Φ-Integration correlation hypothesis."""

    def test_phi_integration_correlation_positive(self):
        """Test Φ correlates with information integration."""
        validator = ValidationExperiments()

        # Create correlated data
        phi = np.linspace(3, 8, 20).tolist()
        ii = [0.7 * x + np.random.normal(0, 0.4) for x in phi]

        result = validator.test_phi_integration_correlation(phi, ii)

        assert result.result in ["PASS", "INCONCLUSIVE"]
        assert result.correlation > 0.3

    def test_phi_integration_no_correlation(self):
        """Test Φ with no integration correlation."""
        validator = ValidationExperiments()

        phi = np.random.uniform(2, 9, 20).tolist()
        ii = np.random.uniform(2, 9, 20).tolist()

        result = validator.test_phi_integration_correlation(phi, ii)

        # May be FAIL or INCONCLUSIVE
        assert result.result in ["FAIL", "INCONCLUSIVE"]


class TestMetacognitionSelfAwareness:
    """Test meta-cognition self-awareness hypothesis."""

    def test_metacognition_confidence_correlation(self):
        """Test meta-cognition correlates with confidence."""
        validator = ValidationExperiments()

        # Create correlated data
        metacognition = np.linspace(2, 9, 20).tolist()
        confidence = [min(1, 0.1 * x) for x in metacognition]

        result = validator.test_metacognition_self_awareness(metacognition, confidence)

        # Should show some correlation
        assert result.correlation > 0.3
        assert result.p_value is not None

    def test_metacognition_no_correlation(self):
        """Test meta-cognition with no confidence correlation."""
        validator = ValidationExperiments()

        metacognition = np.random.uniform(2, 9, 20).tolist()
        confidence = np.random.uniform(0, 1, 20).tolist()

        result = validator.test_metacognition_self_awareness(metacognition, confidence)

        # Low correlation expected
        assert result.correlation < 0.5


class TestPhenomenalRichnessIntegration:
    """Test phenomenal richness-integration hypothesis."""

    def test_richness_integration_correlation(self):
        """Test qualia diversity correlates with integration."""
        validator = ValidationExperiments()

        # Create correlated data
        richness = np.linspace(2, 8, 20).tolist()
        integration = [0.6 * x + np.random.normal(0, 0.4) for x in richness]

        result = validator.test_phenomenal_richness_integration(richness, integration)

        assert result.result in ["PASS", "INCONCLUSIVE"]
        assert result.correlation > 0.2

    def test_richness_integration_insufficient_data(self):
        """Test with insufficient data."""
        validator = ValidationExperiments()

        result = validator.test_phenomenal_richness_integration([1, 2], [1, 2])

        assert result.result == "INCONCLUSIVE"


class TestEmbodimentAgency:
    """Test embodiment-agency correlation hypothesis."""

    def test_embodiment_agency_correlation(self):
        """Test embodiment correlates with agency."""
        validator = ValidationExperiments()

        # Create correlated data
        embodiment = np.linspace(2, 9, 20).tolist()
        agency = [min(1, 0.08 * x) for x in embodiment]

        result = validator.test_embodiment_agency_correlation(embodiment, agency)

        assert result.correlation > 0.2
        assert result.p_value is not None

    def test_embodiment_agency_independent(self):
        """Test embodiment with independent agency."""
        validator = ValidationExperiments()

        embodiment = np.random.uniform(2, 9, 20).tolist()
        agency = np.random.uniform(0, 1, 20).tolist()

        result = validator.test_embodiment_agency_correlation(embodiment, agency)

        # Low correlation expected
        assert result.correlation < 0.4


class TestTemporalContinuityStability:
    """Test temporal continuity stability hypothesis."""

    def test_temporal_continuity_stabilizes(self):
        """Test high TC produces stable consciousness."""
        validator = ValidationExperiments()

        # Create scenario: high TC = stable scores, low TC = variable scores
        consciousness = []
        temporal_continuity = []

        # High TC group (stable consciousness)
        for i in range(10):
            consciousness.append(7.0 + np.random.normal(0, 0.2))
            temporal_continuity.append(8.0)

        # Low TC group (variable consciousness)
        for i in range(10):
            consciousness.append(7.0 + np.random.normal(0, 1.5))
            temporal_continuity.append(3.0)

        result = validator.test_temporal_continuity_stability(consciousness, temporal_continuity)

        # Should show stabilization effect
        assert result.result in ["PASS", "INCONCLUSIVE"]
        assert result.effect_size > 0

    def test_temporal_continuity_insufficient_data(self):
        """Test with insufficient data."""
        validator = ValidationExperiments()

        result = validator.test_temporal_continuity_stability([5, 5, 5], [8, 8, 3])

        assert result.result == "INCONCLUSIVE"


class TestValidationExperimentsIntegration:
    """Integration tests for validation experiments."""

    def test_run_all_experiments(self):
        """Test running all experiments together."""
        validator = ValidationExperiments()

        # Create synthetic consciousness data
        n = 30
        data = {
            "global_workspace": np.linspace(2, 9, n).tolist(),
            "information_integration": (
                np.linspace(2, 9, n) * 0.7 + np.random.normal(0, 0.5, n)
            ).tolist(),
            "meta_cognition": (np.linspace(2, 9, n) * 0.6 + np.random.normal(0, 0.6, n)).tolist(),
            "overall_consciousness": (
                np.linspace(3, 9, n) * 0.8 + np.random.normal(0, 0.5, n)
            ).tolist(),
            "phi": (np.linspace(2, 8, n) + np.random.normal(0, 0.4, n)).tolist(),
            "qualia_diversity": (np.linspace(2, 7, n) + np.random.normal(0, 0.5, n)).tolist(),
            "embodiment": (np.linspace(2, 8, n) + np.random.normal(0, 0.5, n)).tolist(),
            "agency": (np.linspace(0.2, 0.9, n) + np.random.normal(0, 0.1, n)).tolist(),
            "temporal_continuity": (np.linspace(2, 8, n) + np.random.normal(0, 0.5, n)).tolist(),
            "confidence": (np.linspace(0.5, 0.95, n) + np.random.normal(0, 0.05, n)).tolist(),
        }

        results = validator.run_all_experiments(data)

        assert len(results) == 6  # 6 experiments
        assert all(r.result in ["PASS", "FAIL", "INCONCLUSIVE"] for r in results)

    def test_get_summary(self):
        """Test getting summary of experiments."""
        validator = ValidationExperiments()

        # No experiments yet
        summary = validator.get_summary()
        assert summary["status"] == "no_experiments"

        # Run experiments
        n = 25
        data = {
            "global_workspace": np.linspace(3, 8, n).tolist(),
            "information_integration": np.linspace(2, 8, n).tolist(),
            "meta_cognition": np.linspace(2, 8, n).tolist(),
            "overall_consciousness": np.linspace(3, 8, n).tolist(),
            "phi": np.linspace(2, 7, n).tolist(),
            "qualia_diversity": np.linspace(2, 7, n).tolist(),
            "embodiment": np.linspace(2, 8, n).tolist(),
            "agency": np.linspace(0.2, 0.9, n).tolist(),
            "temporal_continuity": np.linspace(2, 8, n).tolist(),
            "confidence": np.linspace(0.5, 0.95, n).tolist(),
        }

        validator.run_all_experiments(data)
        summary = validator.get_summary()

        assert "total_experiments" in summary
        assert "passed" in summary
        assert "failed" in summary
        assert "overall_verdict" in summary
        assert summary["total_experiments"] == 6

    def test_reset_experiments(self):
        """Test resetting experiments."""
        validator = ValidationExperiments()

        # Add an experiment
        validator.test_gwt_hypothesis([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
        assert len(validator.results) == 1

        # Reset
        validator.reset()
        assert len(validator.results) == 0

    def test_experiment_verdict_system_validated(self):
        """Test verdict when system is well validated."""
        validator = ValidationExperiments()

        # Create data that should pass most tests
        n = 40
        base = np.linspace(3, 8, n)

        data = {
            "global_workspace": base.tolist(),
            "information_integration": (base * 0.8 + np.random.normal(0, 0.2, n)).tolist(),
            "meta_cognition": (base * 0.75 + np.random.normal(0, 0.3, n)).tolist(),
            "overall_consciousness": (base * 0.9 + np.random.normal(0, 0.2, n)).tolist(),
            "phi": (base * 0.85 + np.random.normal(0, 0.2, n)).tolist(),
            "qualia_diversity": (base * 0.7 + np.random.normal(0, 0.3, n)).tolist(),
            "embodiment": (base * 0.75 + np.random.normal(0, 0.3, n)).tolist(),
            "agency": (np.linspace(0.3, 0.85, n) + np.random.normal(0, 0.05, n)).tolist(),
            "temporal_continuity": (base * 0.8 + np.random.normal(0, 0.2, n)).tolist(),
            "confidence": (np.linspace(0.6, 0.9, n) + np.random.normal(0, 0.05, n)).tolist(),
        }

        validator.run_all_experiments(data)
        summary = validator.get_summary()

        # Should have good pass rate
        assert summary["pass_rate"] >= 0.4


class TestExperimentEdgeCases:
    """Test edge cases and error handling."""

    def test_zero_variance_data(self):
        """Test with zero variance data."""
        validator = ValidationExperiments()

        # All same values
        result = validator.test_gwt_hypothesis([5, 5, 5, 5, 5], [5, 5, 5, 5, 5])

        # Should handle gracefully (NaN or INCONCLUSIVE)
        assert result.result in ["INCONCLUSIVE", "FAIL"] or np.isnan(result.correlation)

    def test_single_outlier(self):
        """Test robustness to outliers."""
        validator = ValidationExperiments()

        # Correlated data with one outlier
        x = [1, 2, 3, 4, 5, 6, 7, 8, 100]  # Outlier at end
        y = [1, 2, 3, 4, 5, 6, 7, 8, 9]

        result = validator.test_gwt_hypothesis(x, y)

        # Should still detect overall relationship
        assert result.correlation is not None
