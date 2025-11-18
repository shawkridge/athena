"""Confidence-aware planning integration.

Wires uncertainty analysis to planning system to provide:
- Confidence scores for each plan step
- Confidence intervals for duration estimates
- Risk level assessment based on confidence
- Adaptive recommendations
"""

import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Dict

from ..core.database import Database
from ..prospective.models import Plan
from ..phase9.uncertainty.analyzer import UncertaintyAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class ConfidentStep:
    """A plan step with confidence information."""

    content: str
    substeps: List[str] = field(default_factory=list)
    estimated_duration: int = 0
    confidence_score: float = 0.5  # 0-1
    confidence_interval: Tuple[float, float] = (0, 0)  # (lower, upper)
    risk_level: str = "medium"  # low, medium, high, critical
    uncertainty_factors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "content": self.content,
            "substeps": self.substeps,
            "estimated_duration": self.estimated_duration,
            "confidence_score": round(self.confidence_score, 3),
            "confidence_interval": (
                round(self.confidence_interval[0], 1),
                round(self.confidence_interval[1], 1),
            ),
            "risk_level": self.risk_level,
            "uncertainty_factors": self.uncertainty_factors,
        }


@dataclass
class ConfidentPlan:
    """A plan with confidence scoring across all steps."""

    plan_id: int
    task_id: int
    steps: List[ConfidentStep] = field(default_factory=list)
    overall_confidence: float = 0.5
    overall_risk: str = "medium"
    recommendation: str = ""
    confidence_intervals: Dict[str, Tuple[float, float]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "plan_id": self.plan_id,
            "task_id": self.task_id,
            "steps": [s.to_dict() for s in self.steps],
            "overall_confidence": round(self.overall_confidence, 3),
            "overall_risk": self.overall_risk,
            "recommendation": self.recommendation,
            "confidence_intervals": {
                k: (round(v[0], 1), round(v[1], 1)) for k, v in self.confidence_intervals.items()
            },
        }


class ConfidencePlanner:
    """Integrates confidence analysis with planning."""

    def __init__(self, db: Database):
        """Initialize confidence planner.

        Args:
            db: Database instance
        """
        self.db = db
        self.uncertainty_analyzer = UncertaintyAnalyzer(db)

    def add_confidence_to_plan(self, plan: Plan) -> ConfidentPlan:
        """Add confidence information to an existing plan.

        Args:
            plan: Base plan from PlanningAssistant

        Returns:
            ConfidentPlan with confidence scores
        """
        confident_steps = []

        # Process each step
        for step in plan.steps:
            confident_step = self._build_confident_step(step, plan)
            confident_steps.append(confident_step)

        # Calculate overall metrics
        overall_confidence = self._compute_overall_confidence(confident_steps)
        overall_risk = self._compute_risk_level(overall_confidence)
        recommendation = self._generate_recommendation(overall_confidence)
        confidence_intervals = self._extract_confidence_intervals(confident_steps)

        confident_plan = ConfidentPlan(
            plan_id=plan.id,
            task_id=plan.task_id,
            steps=confident_steps,
            overall_confidence=overall_confidence,
            overall_risk=overall_risk,
            recommendation=recommendation,
            confidence_intervals=confidence_intervals,
        )

        return confident_plan

    def _build_confident_step(self, step: str, plan: Plan) -> ConfidentStep:
        """Build a confident step from base step.

        Args:
            step: Step content
            plan: Parent plan for context

        Returns:
            ConfidentStep with confidence information
        """
        # Extract uncertainty factors
        uncertainty_factors = self._extract_uncertainty_factors(step)

        # Compute base confidence (heuristic)
        confidence = self._compute_step_confidence(step, uncertainty_factors)

        # Adjust duration based on confidence
        base_duration = 30  # Default 30 min per step
        confidence_interval = self._compute_confidence_interval(
            base_duration, confidence, len(uncertainty_factors)
        )

        # Compute risk level
        risk_level = self._compute_risk_level(confidence)

        return ConfidentStep(
            content=step,
            substeps=[],
            estimated_duration=base_duration,
            confidence_score=confidence,
            confidence_interval=confidence_interval,
            risk_level=risk_level,
            uncertainty_factors=uncertainty_factors,
        )

    def _extract_uncertainty_factors(self, step: str) -> List[str]:
        """Extract uncertainty factors from step description.

        Looks for keywords indicating uncertainty:
        - "maybe", "might", "could", "possibly" -> uncertainty
        - "complex", "novel", "unfamiliar" -> epistemic uncertainty
        - "depends on", "external" -> aleatoric uncertainty

        Args:
            step: Step description

        Returns:
            List of identified uncertainty factors
        """
        factors = []
        step_lower = step.lower()

        # Epistemic uncertainties (lack of knowledge)
        epistemic_keywords = {
            "complex": "Complex task - knowledge uncertainty",
            "novel": "Novel approach - untested",
            "unfamiliar": "Unfamiliar technology - learning curve",
            "unclear": "Unclear requirements - ambiguity",
            "research": "Research required - exploratory",
            "experiment": "Experimental approach - unknown outcome",
            "prototype": "Prototype - unvalidated design",
        }

        for keyword, factor in epistemic_keywords.items():
            if keyword in step_lower:
                factors.append(factor)

        # Aleatoric uncertainties (external variability)
        aleatoric_keywords = {
            "depends on": "Depends on external factors",
            "external": "External dependencies",
            "third-party": "Third-party integration risk",
            "network": "Network/connectivity risk",
            "api": "API reliability risk",
            "performance": "Performance variability",
        }

        for keyword, factor in aleatoric_keywords.items():
            if keyword in step_lower:
                factors.append(factor)

        return factors

    def _compute_step_confidence(self, step: str, uncertainty_factors: List[str]) -> float:
        """Compute confidence score for a step.

        Base confidence is reduced by uncertainty factors.
        Each factor reduces confidence by 10%.

        Args:
            step: Step description
            uncertainty_factors: List of identified uncertainties

        Returns:
            Confidence score 0-1
        """
        # Start with medium confidence
        base_confidence = 0.7

        # Reduce by each uncertainty factor
        confidence = base_confidence
        for _ in uncertainty_factors:
            confidence *= 0.85  # Each factor reduces by 15%

        # Ensure bounds
        return max(0.1, min(0.95, confidence))

    def _compute_confidence_interval(
        self, estimate: float, confidence: float, num_factors: int
    ) -> Tuple[float, float]:
        """Compute 95% confidence interval for duration estimate.

        Args:
            estimate: Point estimate in minutes
            confidence: Confidence score 0-1
            num_factors: Number of uncertainty factors

        Returns:
            Tuple of (lower_bound, upper_bound) in minutes
        """
        # Std dev proportional to (1 - confidence) and num_factors
        uncertainty = (1.0 - confidence) * (1.0 + num_factors * 0.2)
        std_dev = estimate * uncertainty

        # 95% CI = 1.96 standard deviations
        margin = 1.96 * std_dev

        lower = max(estimate * 0.5, estimate - margin)  # At least 50% of estimate
        upper = estimate + margin

        return (lower, upper)

    def _compute_risk_level(self, confidence: float) -> str:
        """Compute risk level from confidence.

        Args:
            confidence: Confidence score 0-1

        Returns:
            Risk level: "low", "medium", "high", or "critical"
        """
        if confidence > 0.8:
            return "low"
        elif confidence > 0.6:
            return "medium"
        elif confidence > 0.4:
            return "high"
        else:
            return "critical"

    def _compute_overall_confidence(self, steps: List[ConfidentStep]) -> float:
        """Compute overall plan confidence from step confidences.

        Uses average, weighted slightly toward low-confidence steps.

        Args:
            steps: List of plan steps

        Returns:
            Overall confidence score 0-1
        """
        if not steps:
            return 0.5

        confidences = [s.confidence_score for s in steps]

        # Weight lower scores more heavily (risk-averse)
        weighted_sum = sum(c**1.2 for c in confidences)  # Exponent > 1 favors lower values
        return weighted_sum / len(confidences)

    def _generate_recommendation(self, confidence: float) -> str:
        """Generate recommendation based on confidence.

        Args:
            confidence: Overall confidence score 0-1

        Returns:
            Actionable recommendation string
        """
        if confidence > 0.8:
            return "✅ Proceed with confidence - plan is well-understood"
        elif confidence > 0.6:
            return "⚠️ Proceed with caution - consider 20% time buffer and contingency planning"
        elif confidence > 0.4:
            return "⛔ High uncertainty - split into smaller tasks and validate assumptions first"
        else:
            return "🚫 Too uncertain - gather more information, prototype, or seek expert advice"

    def _extract_confidence_intervals(
        self, steps: List[ConfidentStep]
    ) -> Dict[str, Tuple[float, float]]:
        """Extract confidence intervals keyed by step content.

        Args:
            steps: List of confident steps

        Returns:
            Dict mapping step content to (lower, upper) duration bounds
        """
        intervals = {}
        for i, step in enumerate(steps):
            key = f"Step {i+1}: {step.content[:40]}..."
            intervals[key] = step.confidence_interval

        return intervals
