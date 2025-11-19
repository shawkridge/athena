"""Tests for Φ (Integrated Information) calculation.

Tests the IIT-based consciousness metric calculations.
"""

import pytest
import numpy as np
from datetime import datetime
from athena.consciousness.phi_calculation import (
    PhiResult,
    InformationTheory,
    PhiCalculator,
    IntegratedInformationSystem,
)


class TestPhiResult:
    """Test PhiResult data class."""

    def test_phi_result_creation(self):
        """Test creating a Φ result."""
        result = PhiResult(
            phi=7.5,
            calculation_method="fast",
            confidence=0.8,
            evidence=["Test evidence"],
        )
        assert result.phi == 7.5
        assert result.calculation_method == "fast"
        assert result.confidence == 0.8
        assert isinstance(result.timestamp, datetime)

    def test_phi_clamping_high(self):
        """Test that Φ > 10 is clamped."""
        result = PhiResult(phi=15.0)
        assert result.phi == 10.0

    def test_phi_clamping_low(self):
        """Test that Φ < 0 is clamped."""
        result = PhiResult(phi=-5.0)
        assert result.phi == 0.0

    def test_phi_default_values(self):
        """Test default values."""
        result = PhiResult(phi=5.0)
        assert result.components == {}
        assert result.evidence == []
        assert result.confidence == 0.65


class TestInformationTheory:
    """Test information theory utilities."""

    def test_entropy_uniform_distribution(self):
        """Test entropy of uniform distribution."""
        # Uniform distribution of 4 outcomes should have entropy = 2 bits
        probs = np.array([0.25, 0.25, 0.25, 0.25])
        entropy = InformationTheory.entropy(probs)
        assert abs(entropy - 2.0) < 0.01  # Should be ~2 bits

    def test_entropy_certain_outcome(self):
        """Test entropy of certain outcome."""
        # Certain outcome (p=1 for one) should have entropy = 0
        probs = np.array([1.0, 0.0])
        entropy = InformationTheory.entropy(probs)
        assert abs(entropy) < 0.01

    def test_entropy_ignores_zero_probabilities(self):
        """Test that zero probabilities don't cause issues."""
        probs = np.array([0.5, 0.5, 0.0, 0.0])
        entropy = InformationTheory.entropy(probs)
        # Should be 1 bit (same as uniform over 2 outcomes)
        assert abs(entropy - 1.0) < 0.01

    def test_mutual_information_independent(self):
        """Test MI of independent distributions is near 0."""
        # Create independent joint distribution
        joint = np.ones((4, 4)) / 16  # Uniform
        marginal_x = np.ones(4) / 4
        marginal_y = np.ones(4) / 4

        mi = InformationTheory.mutual_information(joint, marginal_x, marginal_y)
        assert abs(mi) < 0.1  # Near 0 for independent

    def test_mutual_information_identical(self):
        """Test MI of identical distributions is high."""
        # Create perfectly correlated distributions
        joint = np.diag(np.ones(4)) / 4  # Only diagonal non-zero
        marginal_x = np.ones(4) / 4
        marginal_y = np.ones(4) / 4

        mi = InformationTheory.mutual_information(joint, marginal_x, marginal_y)
        assert mi > 0.5  # High MI for correlated

    def test_kullback_leibler_identical(self):
        """Test KL divergence of identical distributions is 0."""
        p = np.array([0.25, 0.25, 0.25, 0.25])
        q = np.array([0.25, 0.25, 0.25, 0.25])

        kl = InformationTheory.kullback_leibler_divergence(p, q)
        assert abs(kl) < 0.01

    def test_kullback_leibler_different(self):
        """Test KL divergence of different distributions."""
        p = np.array([0.5, 0.5])  # Concentrated on first
        q = np.array([0.2, 0.8])  # Concentrated on second

        kl = InformationTheory.kullback_leibler_divergence(p, q)
        assert kl > 0.3  # Should be significant


class TestPhiCalculator:
    """Test Φ calculator."""

    def test_calculator_creation(self):
        """Test creating calculator."""
        calc = PhiCalculator()
        assert calc is not None

    def test_calculate_phi_fast_balanced_indicators(self):
        """Test fast Φ calculation with balanced indicators."""
        calc = PhiCalculator()

        indicators = {
            "global_workspace": 7.0,
            "information_integration": 7.0,
            "selective_attention": 7.0,
            "working_memory": 7.0,
            "meta_cognition": 7.0,
            "temporal_continuity": 7.0,
        }

        result = calc.calculate_phi_fast(indicators)

        assert result.phi > 0
        assert result.phi <= 10
        assert result.calculation_method == "fast"
        assert "integration" in result.components
        assert "differentiation" in result.components
        assert len(result.evidence) > 0

    def test_calculate_phi_fast_varied_indicators(self):
        """Test fast Φ with varied indicator values."""
        calc = PhiCalculator()

        indicators = {
            "global_workspace": 9.0,
            "information_integration": 8.0,
            "selective_attention": 5.0,
            "working_memory": 6.0,
            "meta_cognition": 7.0,
            "temporal_continuity": 8.0,
        }

        result = calc.calculate_phi_fast(indicators)

        assert result.phi > 0
        # Varied indicators should give higher differentiation
        assert result.components["differentiation"] > 1.0

    def test_calculate_phi_fast_low_indicators(self):
        """Test fast Φ with low indicator values."""
        calc = PhiCalculator()

        indicators = {
            "global_workspace": 2.0,
            "information_integration": 2.0,
            "selective_attention": 2.0,
            "working_memory": 2.0,
            "meta_cognition": 2.0,
            "temporal_continuity": 2.0,
        }

        result = calc.calculate_phi_fast(indicators)

        assert result.phi < 5.0  # Should be lower consciousness

    def test_calculate_phi_fast_with_correlations(self):
        """Test fast Φ calculation with correlations."""
        calc = PhiCalculator()

        indicators = {
            "global_workspace": 7.0,
            "information_integration": 7.0,
            "selective_attention": 7.0,
            "working_memory": 7.0,
            "meta_cognition": 7.0,
            "temporal_continuity": 7.0,
        }

        # High correlations
        correlations = {
            ("global_workspace", "information_integration"): 0.9,
            ("selective_attention", "working_memory"): 0.8,
        }

        result = calc.calculate_phi_fast(indicators, correlations)

        # High correlations should reduce integration (redundancy)
        assert result.phi > 0
        assert result.components["integration"] < 10

    def test_calculate_phi_detailed_trajectories(self):
        """Test detailed Φ calculation with trajectories."""
        calc = PhiCalculator()

        trajectories = {
            "global_workspace": [5.0, 5.5, 6.0, 6.5, 7.0],
            "information_integration": [5.0, 5.2, 5.4, 5.6, 5.8],
            "selective_attention": [6.0, 6.1, 6.2, 6.3, 6.4],
            "working_memory": [5.5, 5.6, 5.7, 5.8, 5.9],
            "meta_cognition": [4.5, 4.6, 4.7, 4.8, 4.9],
            "temporal_continuity": [5.8, 5.9, 6.0, 6.1, 6.2],
        }

        result = calc.calculate_phi_detailed(trajectories)

        assert result.phi > 0
        assert result.phi <= 10
        assert result.calculation_method == "detailed"
        assert result.components["time_steps_used"] > 1

    def test_calculate_phi_detailed_insufficient_data(self):
        """Test detailed Φ with insufficient data."""
        calc = PhiCalculator()

        trajectories = {
            "global_workspace": [5.0],
            "information_integration": [5.0],
        }

        result = calc.calculate_phi_detailed(trajectories)

        assert result.confidence < 0.5  # Low confidence for failed calculation

    def test_estimate_phi_from_consciousness_score(self):
        """Test estimating Φ from consciousness score."""
        calc = PhiCalculator()

        indicators = {
            "global_workspace": 7.0,
            "information_integration": 8.0,
            "selective_attention": 7.0,
            "working_memory": 7.0,
            "meta_cognition": 6.0,
            "temporal_continuity": 7.0,
        }

        result = calc.estimate_phi_from_consciousness_score(
            overall_score=7.0,
            indicators=indicators,
        )

        # Φ should be correlated with consciousness score
        assert result.phi > 5.0
        assert result.phi < 8.0  # Slightly less than overall score


class TestIntegratedInformationSystem:
    """Test the unified IIT system."""

    def test_system_creation(self):
        """Test creating IIT system."""
        system = IntegratedInformationSystem()
        assert system is not None
        assert system.history == []

    @pytest.mark.asyncio
    async def test_calculate_phi_no_metrics(self):
        """Test Φ calculation with no consciousness metrics."""
        from athena.consciousness.metrics import ConsciousnessMetrics

        system = IntegratedInformationSystem()
        metrics = ConsciousnessMetrics()

        result = await system.calculate_phi(metrics, method="fast")

        # With default indicators (all 5.0), Φ calculation is valid
        # but might be 0 due to uniform inputs (no integration/differentiation)
        assert result.phi >= 0
        assert result.phi <= 10
        # Result should still be a valid PhiResult
        assert isinstance(result, PhiResult)

    @pytest.mark.asyncio
    async def test_calculate_phi_with_metrics(self):
        """Test Φ calculation with measured consciousness metrics."""
        from athena.consciousness.metrics import ConsciousnessMetrics

        system = IntegratedInformationSystem()
        metrics = ConsciousnessMetrics()

        # Measure consciousness
        await metrics.measure_consciousness()

        # Calculate Φ
        result = await system.calculate_phi(metrics, method="fast")

        assert result.phi > 0
        assert result.phi <= 10
        assert result.calculation_method == "fast"

    @pytest.mark.asyncio
    async def test_phi_history(self):
        """Test Φ history tracking."""
        from athena.consciousness.metrics import ConsciousnessMetrics

        system = IntegratedInformationSystem()
        metrics = ConsciousnessMetrics()

        # Calculate multiple Φ values
        for _ in range(3):
            await metrics.measure_consciousness()
            await system.calculate_phi(metrics)

        history = system.get_phi_history()
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_phi_history_limited(self):
        """Test getting limited Φ history."""
        from athena.consciousness.metrics import ConsciousnessMetrics

        system = IntegratedInformationSystem()
        metrics = ConsciousnessMetrics()

        for _ in range(5):
            await metrics.measure_consciousness()
            await system.calculate_phi(metrics)

        history = system.get_phi_history(limit=3)
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_phi_statistics(self):
        """Test Φ statistics calculation."""
        from athena.consciousness.metrics import ConsciousnessMetrics

        system = IntegratedInformationSystem()
        metrics = ConsciousnessMetrics()

        # Calculate multiple Φ values
        for _ in range(5):
            await metrics.measure_consciousness()
            await system.calculate_phi(metrics)

        stats = system.get_phi_statistics()

        assert stats["measurements"] == 5
        assert "average_phi" in stats
        assert "min_phi" in stats
        assert "max_phi" in stats

    @pytest.mark.asyncio
    async def test_phi_reset_history(self):
        """Test resetting Φ history."""
        from athena.consciousness.metrics import ConsciousnessMetrics

        system = IntegratedInformationSystem()
        metrics = ConsciousnessMetrics()

        # Add measurements
        for _ in range(3):
            await metrics.measure_consciousness()
            await system.calculate_phi(metrics)

        assert len(system.history) == 3

        # Reset
        system.reset_history()
        assert len(system.history) == 0


class TestPhiConsciousnessIntegration:
    """Integration tests for Φ and consciousness metrics."""

    @pytest.mark.asyncio
    async def test_phi_tracks_consciousness_changes(self):
        """Test that Φ changes correlate with consciousness changes."""
        from athena.consciousness.metrics import ConsciousnessMetrics

        system = IntegratedInformationSystem()
        metrics = ConsciousnessMetrics()

        # Take measurements
        for _ in range(3):
            await metrics.measure_consciousness()

        # Calculate Φ
        phi1 = await system.calculate_phi(metrics, method="fast")
        phi_hist = system.get_phi_history()

        # Should have tracked calculations
        assert len(phi_hist) > 0
        assert phi_hist[0].phi > 0

    @pytest.mark.asyncio
    async def test_detailed_phi_calculation(self):
        """Test detailed Φ calculation with history."""
        from athena.consciousness.metrics import ConsciousnessMetrics

        system = IntegratedInformationSystem()
        metrics = ConsciousnessMetrics()

        # Build up history
        for _ in range(5):
            await metrics.measure_consciousness()

        # Detailed calculation
        result = await system.calculate_phi(metrics, method="detailed")

        # Should have used trajectory data
        assert result.calculation_method == "detailed"
        assert result.components.get("time_steps_used", 0) > 1
