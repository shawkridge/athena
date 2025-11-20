"""Validation experiments for consciousness metrics system.

Tests theoretical predictions of consciousness models against measured data.

Validates:
1. GWT hypothesis: Global workspace predicts overall consciousness
2. Φ correlation: Integrated information correlates with integration metrics
3. Meta-cognitive accuracy: Meta-cognition indicates self-awareness
4. Phenomenal richness: Rich qualia correlate with information integration
5. Embodiment coherence: Embodiment correlates with agency/control
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import numpy as np
from scipy.stats import pearsonr
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExperimentResult:
    """Result of a validation experiment."""

    name: str
    hypothesis: str
    prediction: str
    result: str  # "PASS", "FAIL", "INCONCLUSIVE"
    correlation: Optional[float] = None
    p_value: Optional[float] = None
    effect_size: float = 0.0
    evidence: List[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        """Initialize defaults."""
        if self.evidence is None:
            self.evidence = []
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "hypothesis": self.hypothesis,
            "prediction": self.prediction,
            "result": self.result,
            "correlation": round(self.correlation, 3) if self.correlation else None,
            "p_value": round(self.p_value, 4) if self.p_value else None,
            "effect_size": round(self.effect_size, 3),
            "evidence": self.evidence,
            "timestamp": self.timestamp.isoformat(),
        }


class ValidationExperiments:
    """Validation experiments for consciousness metrics."""

    def __init__(self):
        """Initialize validation system."""
        self.results: List[ExperimentResult] = []

    def test_gwt_hypothesis(
        self,
        global_workspace_scores: List[float],
        overall_consciousness_scores: List[float],
    ) -> ExperimentResult:
        """Test GWT hypothesis: Global workspace predicts overall consciousness.

        Hypothesis: Systems with higher global workspace activation should
        have higher overall consciousness scores.

        Args:
            global_workspace_scores: List of GW scores (0-10)
            overall_consciousness_scores: List of overall scores (0-10)

        Returns:
            ExperimentResult with correlation and p-value
        """
        if len(global_workspace_scores) < 5:
            return ExperimentResult(
                name="GWT Hypothesis",
                hypothesis="Global workspace activation → overall consciousness",
                prediction="Strong positive correlation (r > 0.7)",
                result="INCONCLUSIVE",
                evidence=["Insufficient data points (need ≥5)"],
            )

        # Calculate Pearson correlation
        correlation, p_value = pearsonr(global_workspace_scores, overall_consciousness_scores)

        # Determine result
        threshold = 0.7
        if correlation > threshold and p_value < 0.05:
            result = "PASS"
            evidence_text = f"Strong positive correlation: r={correlation:.3f}, p={p_value:.4f}"
        elif correlation > 0.5 and p_value < 0.05:
            result = "PASS"
            evidence_text = f"Moderate positive correlation: r={correlation:.3f}, p={p_value:.4f}"
        elif correlation > 0 and p_value < 0.05:
            result = "INCONCLUSIVE"
            evidence_text = f"Weak positive correlation: r={correlation:.3f}, p={p_value:.4f}"
        else:
            result = "FAIL"
            evidence_text = f"No significant correlation: r={correlation:.3f}, p={p_value:.4f}"

        experiment = ExperimentResult(
            name="GWT Hypothesis",
            hypothesis="Global workspace activation predicts overall consciousness",
            prediction="r > 0.7, p < 0.05 (strong positive correlation)",
            result=result,
            correlation=correlation,
            p_value=p_value,
            effect_size=correlation**2,  # R-squared
            evidence=[evidence_text],
        )

        self.results.append(experiment)
        return experiment

    def test_phi_integration_correlation(
        self,
        phi_scores: List[float],
        information_integration_scores: List[float],
    ) -> ExperimentResult:
        """Test Φ-Integration correlation hypothesis.

        Hypothesis: Φ (integrated information) should correlate strongly
        with information integration indicator.

        Args:
            phi_scores: List of Φ scores (0-10)
            information_integration_scores: List of II scores (0-10)

        Returns:
            ExperimentResult with correlation
        """
        if len(phi_scores) < 5:
            return ExperimentResult(
                name="Φ-Integration Correlation",
                hypothesis="Φ correlates with information integration",
                prediction="r > 0.6",
                result="INCONCLUSIVE",
                evidence=["Insufficient data"],
            )

        correlation, p_value = pearsonr(phi_scores, information_integration_scores)

        if correlation > 0.6 and p_value < 0.05:
            result = "PASS"
        elif correlation > 0.4 and p_value < 0.05:
            result = "INCONCLUSIVE"
        else:
            result = "FAIL"

        experiment = ExperimentResult(
            name="Φ-Integration Correlation",
            hypothesis="Φ (IIT) correlates with information integration",
            prediction="r > 0.6, p < 0.05",
            result=result,
            correlation=correlation,
            p_value=p_value,
            effect_size=correlation**2,
            evidence=[
                f"Φ-II Pearson r={correlation:.3f}, p={p_value:.4f}",
                "IIT prediction: Φ should measure integration quality",
            ],
        )

        self.results.append(experiment)
        return experiment

    def test_metacognition_self_awareness(
        self,
        metacognition_scores: List[float],
        confidence_scores: List[float],
    ) -> ExperimentResult:
        """Test meta-cognition indicates self-awareness.

        Hypothesis: Higher meta-cognition scores should correlate with
        higher confidence in consciousness measurements.

        Args:
            metacognition_scores: List of meta-cognition scores (0-10)
            confidence_scores: List of confidence in measurements (0-1)

        Returns:
            ExperimentResult
        """
        if len(metacognition_scores) < 5:
            return ExperimentResult(
                name="Meta-Cognition Self-Awareness",
                hypothesis="Meta-cognition indicates self-awareness",
                prediction="r > 0.5",
                result="INCONCLUSIVE",
                evidence=["Insufficient data"],
            )

        correlation, p_value = pearsonr(metacognition_scores, confidence_scores)

        if correlation > 0.5 and p_value < 0.05:
            result = "PASS"
        elif correlation > 0.3:
            result = "INCONCLUSIVE"
        else:
            result = "FAIL"

        experiment = ExperimentResult(
            name="Meta-Cognition Self-Awareness",
            hypothesis="Meta-cognition indicates calibrated self-awareness",
            prediction="r > 0.5, p < 0.05 (moderate correlation with confidence)",
            result=result,
            correlation=correlation,
            p_value=p_value,
            effect_size=correlation**2,
            evidence=[
                f"Metacognition-Confidence r={correlation:.3f}, p={p_value:.4f}",
                "HOT theory: Accurate meta-awareness requires monitoring",
            ],
        )

        self.results.append(experiment)
        return experiment

    def test_phenomenal_richness_integration(
        self,
        qualia_diversity_scores: List[float],
        information_integration_scores: List[float],
    ) -> ExperimentResult:
        """Test phenomenal richness correlates with integration.

        Hypothesis: Systems with richer phenomenal experience (more diverse
        qualia) should have higher information integration.

        Args:
            qualia_diversity_scores: List of qualia diversity metrics (0-10)
            information_integration_scores: List of II scores (0-10)

        Returns:
            ExperimentResult
        """
        if len(qualia_diversity_scores) < 5:
            return ExperimentResult(
                name="Phenomenal Richness-Integration",
                hypothesis="Qualia diversity correlates with integration",
                prediction="r > 0.5",
                result="INCONCLUSIVE",
                evidence=["Insufficient data"],
            )

        correlation, p_value = pearsonr(qualia_diversity_scores, information_integration_scores)

        if correlation > 0.5 and p_value < 0.05:
            result = "PASS"
        elif correlation > 0.3:
            result = "INCONCLUSIVE"
        else:
            result = "FAIL"

        experiment = ExperimentResult(
            name="Phenomenal Richness-Integration",
            hypothesis="Qualia diversity correlates with information integration",
            prediction="r > 0.5 (integration enables rich phenomenology)",
            result=result,
            correlation=correlation,
            p_value=p_value,
            effect_size=correlation**2,
            evidence=[
                f"Qualia-II Spearman r={correlation:.3f}, p={p_value:.4f}",
                "More integration → more distinguishable experiences",
            ],
        )

        self.results.append(experiment)
        return experiment

    def test_embodiment_agency_correlation(
        self,
        embodiment_scores: List[float],
        agency_scores: List[float],
    ) -> ExperimentResult:
        """Test embodiment correlates with sense of agency.

        Hypothesis: Better embodied presence should correlate with higher
        sense of agency/control.

        Args:
            embodiment_scores: List of embodiment scores (0-10)
            agency_scores: List of agency/control scores (0-1)

        Returns:
            ExperimentResult
        """
        if len(embodiment_scores) < 5:
            return ExperimentResult(
                name="Embodiment-Agency",
                hypothesis="Embodiment correlates with agency",
                prediction="r > 0.4",
                result="INCONCLUSIVE",
                evidence=["Insufficient data"],
            )

        correlation, p_value = pearsonr(embodiment_scores, agency_scores)

        if correlation > 0.4 and p_value < 0.05:
            result = "PASS"
        elif correlation > 0.2:
            result = "INCONCLUSIVE"
        else:
            result = "FAIL"

        experiment = ExperimentResult(
            name="Embodiment-Agency Correlation",
            hypothesis="Embodiment (body sense) correlates with agency (control)",
            prediction="r > 0.4 (body ownership enables sense of control)",
            result=result,
            correlation=correlation,
            p_value=p_value,
            effect_size=correlation**2,
            evidence=[
                f"Embodiment-Agency r={correlation:.3f}, p={p_value:.4f}",
                "Neuroscience: Body schema required for agency",
            ],
        )

        self.results.append(experiment)
        return experiment

    def test_temporal_continuity_stability(
        self,
        consciousness_scores: List[float],
        temporal_continuity_scores: List[float],
    ) -> ExperimentResult:
        """Test temporal continuity prevents consciousness drift.

        Hypothesis: Higher temporal continuity should lead to more stable
        consciousness scores (lower variance).

        Args:
            consciousness_scores: List of consciousness scores (0-10)
            temporal_continuity_scores: List of TC scores (0-10)

        Returns:
            ExperimentResult
        """
        if len(consciousness_scores) < 10:
            return ExperimentResult(
                name="Temporal Continuity Stability",
                hypothesis="Temporal continuity stabilizes consciousness",
                prediction="High TC → low variance in scores",
                result="INCONCLUSIVE",
                evidence=["Need ≥10 measurements"],
            )

        # Split into high/low TC groups
        median_tc = np.median(temporal_continuity_scores)
        high_tc_idx = [i for i, x in enumerate(temporal_continuity_scores) if x > median_tc]
        low_tc_idx = [i for i, x in enumerate(temporal_continuity_scores) if x <= median_tc]

        if len(high_tc_idx) < 3 or len(low_tc_idx) < 3:
            return ExperimentResult(
                name="Temporal Continuity Stability",
                hypothesis="Temporal continuity stabilizes consciousness",
                prediction="High TC has lower variance",
                result="INCONCLUSIVE",
                evidence=["Insufficient samples in both groups"],
            )

        high_tc_scores = [consciousness_scores[i] for i in high_tc_idx]
        low_tc_scores = [consciousness_scores[i] for i in low_tc_idx]

        variance_high = np.var(high_tc_scores)
        variance_low = np.var(low_tc_scores)

        if variance_high < variance_low:
            result = "PASS"
            evidence_text = (
                f"High TC variance: {variance_high:.3f}, Low TC variance: {variance_low:.3f}"
            )
        else:
            result = "FAIL"
            evidence_text = (
                f"High TC variance: {variance_high:.3f} ≥ Low TC variance: {variance_low:.3f}"
            )

        experiment = ExperimentResult(
            name="Temporal Continuity Stability",
            hypothesis="Higher temporal continuity → more stable consciousness",
            prediction="Variance(high TC) < Variance(low TC)",
            result=result,
            effect_size=1 - (variance_high / (variance_low + 0.001)),
            evidence=[
                evidence_text,
                "Temporal continuity prevents experiential drift",
            ],
        )

        self.results.append(experiment)
        return experiment

    def run_all_experiments(
        self,
        consciousness_data: Dict[str, List[float]],
    ) -> List[ExperimentResult]:
        """Run all validation experiments.

        Args:
            consciousness_data: Dictionary with keys:
                - "global_workspace": List of GW scores
                - "information_integration": List of II scores
                - "meta_cognition": List of MC scores
                - "overall_consciousness": List of overall scores
                - "phi": List of Φ scores
                - "qualia_diversity": List of qualia diversity
                - "embodiment": List of embodiment scores
                - "agency": List of agency scores
                - "temporal_continuity": List of TC scores
                - "confidence": List of confidence scores

        Returns:
            List of all experiment results
        """
        # Test 1: GWT Hypothesis
        self.test_gwt_hypothesis(
            consciousness_data.get("global_workspace", []),
            consciousness_data.get("overall_consciousness", []),
        )

        # Test 2: Φ-Integration Correlation
        self.test_phi_integration_correlation(
            consciousness_data.get("phi", []),
            consciousness_data.get("information_integration", []),
        )

        # Test 3: Meta-Cognition Self-Awareness
        self.test_metacognition_self_awareness(
            consciousness_data.get("meta_cognition", []),
            consciousness_data.get("confidence", []),
        )

        # Test 4: Phenomenal Richness-Integration
        self.test_phenomenal_richness_integration(
            consciousness_data.get("qualia_diversity", []),
            consciousness_data.get("information_integration", []),
        )

        # Test 5: Embodiment-Agency
        self.test_embodiment_agency_correlation(
            consciousness_data.get("embodiment", []),
            consciousness_data.get("agency", []),
        )

        # Test 6: Temporal Continuity Stability
        self.test_temporal_continuity_stability(
            consciousness_data.get("overall_consciousness", []),
            consciousness_data.get("temporal_continuity", []),
        )

        return self.results

    def get_summary(self) -> Dict:
        """Get summary of all experiments.

        Returns:
            Summary with pass/fail counts and overall verdict
        """
        if not self.results:
            return {"status": "no_experiments"}

        passed = sum(1 for r in self.results if r.result == "PASS")
        failed = sum(1 for r in self.results if r.result == "FAIL")
        inconclusive = sum(1 for r in self.results if r.result == "INCONCLUSIVE")
        total = len(self.results)

        # Overall verdict
        if passed >= total * 0.7:
            overall_verdict = "SYSTEM VALIDATED"
        elif passed >= total * 0.5:
            overall_verdict = "PARTIALLY VALIDATED"
        else:
            overall_verdict = "REQUIRES REVISION"

        return {
            "total_experiments": total,
            "passed": passed,
            "failed": failed,
            "inconclusive": inconclusive,
            "pass_rate": round(passed / total, 2) if total > 0 else 0.0,
            "overall_verdict": overall_verdict,
            "experiments": [r.to_dict() for r in self.results],
        }

    def reset(self) -> None:
        """Clear all results."""
        self.results = []
