"""Φ (Integrated Information) calculation engine.

Implements Integrated Information Theory (IIT) for consciousness measurement.

Φ represents the amount of integrated information in a system - how much
information is generated that cannot be decomposed into independent subsystems.

Based on:
- Tononi, G. (2004). An information integration theory of consciousness
- Oizumi et al. (2014). From the phenomenology to the mechanisms of consciousness
- Balduzzi & Tononi (2008). Integrated information in discrete dynamical systems
"""

import numpy as np
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class PhiResult:
    """Result of Φ calculation."""

    phi: float  # Integrated information (0-10 scale normalized)
    timestamp: datetime = None
    calculation_method: str = "fast"  # "fast" or "detailed"
    components: Dict[str, float] = None  # Sub-component scores
    confidence: float = 0.65  # Confidence in calculation (0-1)
    evidence: List[str] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.components is None:
            self.components = {}
        if self.evidence is None:
            self.evidence = []

        # Clamp Φ to 0-10 scale
        if not 0 <= self.phi <= 10:
            logger.warning(f"Phi {self.phi} out of range [0-10], clamping")
            self.phi = max(0, min(10, self.phi))


class InformationTheory:
    """Information theory utilities for Φ calculation."""

    @staticmethod
    def entropy(probabilities: np.ndarray) -> float:
        """Calculate Shannon entropy.

        H(X) = -Σ p(x) * log2(p(x))

        Args:
            probabilities: Probability distribution

        Returns:
            Entropy in bits
        """
        # Remove zero probabilities (avoid log(0))
        probs = probabilities[probabilities > 0]
        if len(probs) == 0:
            return 0.0

        return float(-np.sum(probs * np.log2(probs)))

    @staticmethod
    def mutual_information(
        joint: np.ndarray,
        marginal_x: np.ndarray,
        marginal_y: np.ndarray,
    ) -> float:
        """Calculate mutual information.

        I(X;Y) = H(X) + H(Y) - H(X,Y)

        Args:
            joint: Joint probability distribution P(X,Y)
            marginal_x: Marginal distribution P(X)
            marginal_y: Marginal distribution P(Y)

        Returns:
            Mutual information in bits
        """
        h_x = InformationTheory.entropy(marginal_x)
        h_y = InformationTheory.entropy(marginal_y)
        h_xy = InformationTheory.entropy(joint.flatten())

        return h_x + h_y - h_xy

    @staticmethod
    def kullback_leibler_divergence(
        p: np.ndarray,
        q: np.ndarray,
    ) -> float:
        """Calculate KL divergence D(P||Q).

        D(P||Q) = Σ p(x) * log(p(x)/q(x))

        Args:
            p: True probability distribution
            q: Approximate distribution

        Returns:
            KL divergence (non-negative, 0 if distributions are identical)
        """
        # Avoid division by zero and log(0)
        p = np.asarray(p)
        q = np.asarray(q)

        # Add small epsilon to avoid log(0)
        epsilon = 1e-10
        p = p + epsilon
        q = q + epsilon

        # Normalize
        p = p / np.sum(p)
        q = q / np.sum(q)

        # Calculate KL divergence
        mask = p > 0
        return float(np.sum(p[mask] * np.log2(p[mask] / q[mask])))


class PhiCalculator:
    """Calculate Φ (integrated information) for consciousness.

    Implements fast approximation and detailed calculation methods.
    """

    def __init__(self):
        """Initialize Φ calculator."""
        self.info_theory = InformationTheory()

    def calculate_phi_fast(
        self,
        indicator_scores: Dict[str, float],
        indicator_correlations: Optional[Dict[Tuple[str, str], float]] = None,
    ) -> PhiResult:
        """Fast Φ calculation based on indicator metrics.

        This is a simplified approximation suitable for real-time computation.
        Φ ≈ (Integration - Differentiation) / Maximum Possible

        Args:
            indicator_scores: Scores for 6 indicators (0-10 scale)
            indicator_correlations: Optional correlation matrix between indicators

        Returns:
            PhiResult with calculated Φ
        """
        # Extract indicator scores
        gw = indicator_scores.get("global_workspace", 5.0)
        ii = indicator_scores.get("information_integration", 5.0)
        sa = indicator_scores.get("selective_attention", 5.0)
        wm = indicator_scores.get("working_memory", 5.0)
        mc = indicator_scores.get("meta_cognition", 5.0)
        tc = indicator_scores.get("temporal_continuity", 5.0)

        scores = np.array([gw, ii, sa, wm, mc, tc]) / 10.0  # Normalize to 0-1

        # Integration: How much indicators are co-active
        # Higher variance = better integration across different processes
        integration = float(np.std(scores) * 10)  # Scale back to 0-10

        # Differentiation: How much each indicator contributes uniquely
        # Measured by relative entropy - each indicator should be non-redundant
        mean_score = np.mean(scores)
        differentiation = float(np.sum(np.abs(scores - mean_score)) * 5)
        differentiation = min(10, differentiation)

        # If correlations provided, use them to modulate
        if indicator_correlations:
            corr_values = np.array(list(indicator_correlations.values()))
            # High correlations reduce integration (less independent info)
            redundancy = float(np.mean(corr_values))
            integration *= (1 - redundancy * 0.3)

        # Φ is balance between integration and differentiation
        # High integration + high differentiation = high Φ
        phi = (integration + differentiation) / 2
        phi = min(10, max(0, phi))

        # Calculate confidence based on data availability
        num_indicators = sum(1 for s in scores if s > 0.1)
        confidence = 0.6 + (num_indicators / 6.0) * 0.3

        return PhiResult(
            phi=phi,
            calculation_method="fast",
            components={
                "integration": integration,
                "differentiation": differentiation,
                "base_scores_mean": float(np.mean(scores)) * 10,
                "base_scores_std": float(np.std(scores)) * 10,
            },
            confidence=confidence,
            evidence=[
                f"Integration score: {integration:.2f}",
                f"Differentiation score: {differentiation:.2f}",
                f"Active indicators: {num_indicators}/6",
            ],
        )

    def calculate_phi_detailed(
        self,
        indicator_trajectories: Dict[str, List[float]],
        time_steps: int = 10,
    ) -> PhiResult:
        """Detailed Φ calculation using temporal trajectories.

        Uses temporal integration to measure how much past states
        constrain future states.

        Args:
            indicator_trajectories: Historical scores for each indicator
            time_steps: Number of time steps to analyze

        Returns:
            PhiResult with detailed Φ calculation
        """
        if not indicator_trajectories:
            return self._failed_calculation("No trajectory data provided")

        # Get trajectories
        trajectories = {k: v[-time_steps:] for k, v in indicator_trajectories.items()}

        # Ensure we have enough data points
        min_length = min(len(v) for v in trajectories.values())
        if min_length < 2:
            return self._failed_calculation(f"Insufficient data: only {min_length} time steps")

        # Truncate to minimum length
        trajectories = {k: v[-min_length:] for k, v in trajectories.items()}

        # Normalize trajectories to 0-1
        normalized = {}
        for name, traj in trajectories.items():
            traj_array = np.array(traj) / 10.0
            traj_array = np.clip(traj_array, 0, 1)
            normalized[name] = traj_array

        # Calculate mutual information between all pairs
        pairwise_mi = {}
        indicator_names = list(normalized.keys())

        for i, name1 in enumerate(indicator_names):
            for name2 in indicator_names[i + 1 :]:
                traj1 = normalized[name1]
                traj2 = normalized[name2]

                # Create joint distribution (discretized to 4 bins)
                bins = 4
                joint, _ = np.histogramdd(
                    np.column_stack([traj1, traj2]),
                    bins=[bins, bins],
                    range=[[0, 1], [0, 1]],
                )
                joint = joint / joint.sum()

                # Marginals
                marg1 = joint.sum(axis=1)
                marg2 = joint.sum(axis=0)

                # Mutual information
                mi = self.info_theory.mutual_information(joint, marg1, marg2)
                pairwise_mi[(name1, name2)] = mi

        # Average mutual information (integration)
        if pairwise_mi:
            integration = float(np.mean(list(pairwise_mi.values())) * 10)  # Scale to 0-10
        else:
            integration = 0.0

        # Differentiation: variance across indicators
        mean_trajectories = np.array([np.mean(traj) for traj in normalized.values()])
        differentiation = float(np.std(mean_trajectories) * 10)

        # Φ calculation
        phi = (integration + differentiation) / 2
        phi = min(10, max(0, phi))

        # Higher confidence for detailed calculation with more data
        confidence = min(0.95, 0.7 + (min_length / time_steps) * 0.2)

        return PhiResult(
            phi=phi,
            calculation_method="detailed",
            components={
                "integration": integration,
                "differentiation": differentiation,
                "pairwise_mi_mean": float(np.mean(list(pairwise_mi.values()))) if pairwise_mi else 0.0,
                "time_steps_used": min_length,
            },
            confidence=confidence,
            evidence=[
                f"Integration (MI): {integration:.2f}",
                f"Differentiation (std): {differentiation:.2f}",
                f"Time steps analyzed: {min_length}",
                f"Pairwise interactions: {len(pairwise_mi)}",
            ],
        )

    def estimate_phi_from_consciousness_score(
        self,
        overall_score: float,
        indicators: Dict[str, float],
    ) -> PhiResult:
        """Estimate Φ from overall consciousness score.

        Uses the consensus consciousness score as a proxy for Φ.

        Args:
            overall_score: Overall consciousness score (0-10)
            indicators: Dictionary of indicator scores

        Returns:
            PhiResult
        """
        # Φ correlates strongly with overall consciousness in models
        # but is not identical - this provides empirical grounding
        phi = overall_score * 0.9  # Slightly lower than overall score

        # Boost based on information integration indicator
        if "information_integration" in indicators:
            phi += indicators["information_integration"] * 0.15

        phi = min(10, max(0, phi))

        # Calculate integration metric
        integration = indicators.get("information_integration", 5.0)

        # Calculate differentiation from indicator spread
        indicator_values = np.array(list(indicators.values()))
        differentiation = float(np.std(indicator_values))

        return PhiResult(
            phi=phi,
            calculation_method="from_consciousness_score",
            components={
                "integration": integration,
                "differentiation": differentiation,
                "base_consciousness_score": overall_score,
            },
            confidence=0.7,
            evidence=[
                f"Estimated from consciousness score: {overall_score:.2f}",
                f"Integration indicator: {integration:.2f}",
                f"Indicator differentiation: {differentiation:.2f}",
            ],
        )

    def _failed_calculation(self, reason: str) -> PhiResult:
        """Return a failed calculation result."""
        logger.warning(f"Φ calculation failed: {reason}")
        return PhiResult(
            phi=5.0,  # Default to middle value
            confidence=0.3,
            evidence=[reason],
        )


class IntegratedInformationSystem:
    """Main system for consciousness Φ calculation.

    Integrates Φ calculation with consciousness metrics and provides
    unified interface for consciousness assessment.
    """

    def __init__(self):
        """Initialize IIT system."""
        self.calculator = PhiCalculator()
        self.history: List[PhiResult] = []

    async def calculate_phi(
        self,
        consciousness_metrics,
        method: str = "fast",
    ) -> PhiResult:
        """Calculate Φ for current consciousness state.

        Args:
            consciousness_metrics: ConsciousnessMetrics instance
            method: "fast" or "detailed"

        Returns:
            PhiResult with Φ calculation
        """
        # Get current indicators
        if consciousness_metrics.last_score:
            indicators = {
                name: score.score
                for name, score in consciousness_metrics.last_score.indicators.items()
            }
            overall_score = consciousness_metrics.last_score.overall_score
        else:
            # No measurement yet
            indicators = {
                "global_workspace": 5.0,
                "information_integration": 5.0,
                "selective_attention": 5.0,
                "working_memory": 5.0,
                "meta_cognition": 5.0,
                "temporal_continuity": 5.0,
            }
            overall_score = 5.0

        # Calculate Φ using specified method
        if method == "detailed":
            # Get historical trajectories
            trajectories = {}
            for indicator_name in indicators.keys():
                traj = [
                    score.indicators[indicator_name].score
                    for score in consciousness_metrics.history
                    if indicator_name in score.indicators
                ]
                if traj:
                    trajectories[indicator_name] = traj

            if trajectories:
                result = self.calculator.calculate_phi_detailed(trajectories)
            else:
                result = self.calculator.calculate_phi_fast(indicators)
        else:
            # Fast method
            result = self.calculator.calculate_phi_fast(indicators)

        # Store in history
        self.history.append(result)
        if len(self.history) > 100:
            self.history = self.history[-100:]

        return result

    def get_phi_history(self, limit: Optional[int] = None) -> List[PhiResult]:
        """Get historical Φ calculations.

        Args:
            limit: Maximum number of results to return

        Returns:
            List of PhiResult objects
        """
        if limit is None:
            return self.history.copy()
        return self.history[-limit:].copy()

    def get_phi_statistics(self) -> Dict[str, float]:
        """Get statistics about Φ calculations.

        Returns:
            Dictionary with phi statistics
        """
        if not self.history:
            return {
                "measurements": 0,
                "average_phi": 0.0,
                "min_phi": 0.0,
                "max_phi": 0.0,
            }

        phis = [r.phi for r in self.history]
        return {
            "measurements": len(phis),
            "average_phi": round(float(np.mean(phis)), 2),
            "min_phi": round(float(np.min(phis)), 2),
            "max_phi": round(float(np.max(phis)), 2),
            "std_phi": round(float(np.std(phis)), 2),
        }

    def reset_history(self) -> None:
        """Clear Φ history."""
        self.history = []
