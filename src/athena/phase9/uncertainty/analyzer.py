"""Uncertainty analysis system for Phase 9.1."""

from typing import Optional

from athena.phase9.uncertainty.models import (
    ConfidenceCalibration,
    ConfidenceTrendAnalysis,
    PlanAlternative,
    UncertaintyBreakdown,
    UncertaintyType,
)
from athena.phase9.uncertainty.scorer import ConfidenceScorer
from athena.phase9.uncertainty.store import UncertaintyStore


class UncertaintyAnalyzer:
    """Analyze and break down uncertainty in tasks and plans."""

    def __init__(self, store: UncertaintyStore):
        """Initialize analyzer with store."""
        self.store = store

    def analyze_uncertainty(
        self,
        task_id: int,
        estimate: float,
        external_factors: list[str] = None,
        data_points: int = 10,
        historical_variance: float = 0.15,
    ) -> UncertaintyBreakdown:
        """Analyze uncertainty sources and breakdown."""
        if external_factors is None:
            external_factors = []

        # Calculate total uncertainty (0-1 scale)
        total_uncertainty = min(1.0, historical_variance + len(external_factors) * 0.05)

        # Separate epistemic (reducible) and aleatoric (irreducible)
        # Epistemic: can be reduced with more data/analysis
        epistemic = min(0.5, historical_variance)  # Up to 50% reducible

        # Aleatoric: inherent randomness
        aleatoric = total_uncertainty - epistemic

        # Uncertainty sources breakdown
        uncertainty_sources = {}

        if historical_variance > 0.1:
            uncertainty_sources["estimation_variance"] = {
                "type": "epistemic",
                "value": historical_variance,
                "explanation": f"Historical variance in estimates: {historical_variance:.0%}",
                "reducibility": 0.7,
            }

        if len(external_factors) > 0:
            uncertainty_sources["external_factors"] = {
                "type": "aleatoric",
                "value": len(external_factors) * 0.05,
                "explanation": f"External factors: {', '.join(external_factors)}",
                "reducibility": 0.3,
            }

        # Data availability
        if data_points < 10:
            uncertainty_sources["insufficient_data"] = {
                "type": "epistemic",
                "value": (10 - data_points) / 100,
                "explanation": f"Only {data_points} historical data points",
                "reducibility": 0.9,
            }

        # Mitigations
        mitigations = []
        if "estimation_variance" in uncertainty_sources:
            mitigations.append(
                "Collect more historical data from similar tasks to reduce estimation variance"
            )
        if "insufficient_data" in uncertainty_sources:
            mitigations.append("Complete more similar tasks to build better estimates")
        if external_factors:
            mitigations.append(f"Monitor and prepare for external factors: {', '.join(external_factors)}")

        breakdown = UncertaintyBreakdown(
            task_id=task_id,
            total_uncertainty=total_uncertainty,
            uncertainty_sources=uncertainty_sources,
            reducible_uncertainty=epistemic,
            irreducible_uncertainty=aleatoric,
            mitigations=mitigations,
        )

        return self.store.create_uncertainty_breakdown(breakdown)

    def generate_alternative_plans(
        self,
        task_id: int,
        base_estimate: float,
        available_approaches: list[str] = None,
    ) -> list[PlanAlternative]:
        """Generate alternative plans with different confidence levels."""
        if available_approaches is None:
            available_approaches = ["sequential", "parallel", "iterative"]

        plans = []

        # Sequential: slower, more predictable (high confidence, longer duration)
        sequential_plan = PlanAlternative(
            task_id=task_id,
            plan_type="sequential",
            steps=[f"Step {i+1}: Execute component {i+1}" for i in range(3)],
            estimated_duration_minutes=int(base_estimate * 1.2),
            confidence_score=0.85,
            risk_factors=["Long timeline", "Potential bottlenecks"],
            parallelizable_steps=0,
            uncertainty_sources=["modeling"],
            rank=1,
        )
        plans.append(sequential_plan)

        # Parallel: faster, higher risk (medium confidence, shorter duration)
        parallel_plan = PlanAlternative(
            task_id=task_id,
            plan_type="parallel",
            steps=[
                "Step 1: Start parallel subtasks",
                "Step 2: Merge results",
                "Step 3: Integration testing",
            ],
            estimated_duration_minutes=int(base_estimate * 0.7),
            confidence_score=0.65,
            risk_factors=["Parallel coordination", "Resource conflicts", "Integration issues"],
            parallelizable_steps=3,
            uncertainty_sources=["aleatoric", "modeling"],
            rank=3,
        )
        plans.append(parallel_plan)

        # Iterative: moderate pace, adaptable (medium-high confidence)
        iterative_plan = PlanAlternative(
            task_id=task_id,
            plan_type="iterative",
            steps=[
                "Iteration 1: MVP (40% scope)",
                "Iteration 2: Add features (30% scope)",
                "Iteration 3: Polish (30% scope)",
            ],
            estimated_duration_minutes=int(base_estimate * 0.9),
            confidence_score=0.75,
            risk_factors=["Scope creep", "Requirement changes"],
            parallelizable_steps=0,
            uncertainty_sources=["epistemic"],
            rank=2,
        )
        plans.append(iterative_plan)

        # Hybrid: combines best of sequential + parallel
        hybrid_plan = PlanAlternative(
            task_id=task_id,
            plan_type="hybrid",
            steps=[
                "Phase 1: Design (sequential)",
                "Phase 2: Parallel implementation",
                "Phase 3: Integration (sequential)",
                "Phase 4: Testing (parallel)",
            ],
            estimated_duration_minutes=int(base_estimate * 0.85),
            confidence_score=0.78,
            risk_factors=["Phase transition complexity"],
            parallelizable_steps=2,
            uncertainty_sources=["modeling"],
            rank=2,
        )
        plans.append(hybrid_plan)

        # Save all plans
        saved_plans = []
        for plan in plans:
            saved_plans.append(self.store.create_plan_alternative(plan))

        return sorted(saved_plans, key=lambda p: p.confidence_score, reverse=True)

    def analyze_calibration(
        self, project_id: int, aspect: str, days_back: int = 30
    ) -> ConfidenceTrendAnalysis:
        """Analyze how well confidence predictions match reality."""
        calibration_data = self.store.get_calibration_data(project_id, aspect)

        if not calibration_data:
            # Return neutral trend if no data
            return ConfidenceTrendAnalysis(
                project_id=project_id,
                aspect=aspect,
                average_confidence=0.5,
                confidence_trend="stable",
                trend_strength=0.0,
                sample_size=0,
                period_days=days_back,
                recommendations=[
                    "Collect more confidence predictions to establish baseline",
                    "Track actual outcomes against predictions",
                ],
            )

        # Calculate statistics
        total_predictions = len(calibration_data)
        correct_predictions = sum(1 for c in calibration_data if c.actual_outcome)
        accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0.5

        avg_confidence = sum(c.predicted_confidence for c in calibration_data) / total_predictions

        # Identify over/underconfidence
        overconfident = 0
        underconfident = 0
        for calib in calibration_data:
            if calib.actual_outcome and calib.predicted_confidence < 0.5:
                underconfident += 1
            elif not calib.actual_outcome and calib.predicted_confidence > 0.5:
                overconfident += 1

        overconfidence_ratio = overconfident / total_predictions if total_predictions > 0 else 0
        underconfidence_ratio = underconfident / total_predictions if total_predictions > 0 else 0

        # Determine trend
        if total_predictions >= 10:
            recent = calibration_data[:10]
            older = calibration_data[10:20]
            recent_accuracy = (
                sum(1 for c in recent if c.actual_outcome) / len(recent) if recent else 0.5
            )
            older_accuracy = sum(1 for c in older if c.actual_outcome) / len(older) if older else 0.5
            trend_delta = recent_accuracy - older_accuracy
        else:
            trend_delta = 0

        if trend_delta > 0.05:
            confidence_trend = "increasing"
            trend_strength = min(1.0, trend_delta * 2)
        elif trend_delta < -0.05:
            confidence_trend = "decreasing"
            trend_strength = min(1.0, abs(trend_delta) * 2)
        else:
            confidence_trend = "stable"
            trend_strength = 0.0

        # Recommendations
        recommendations = []
        if overconfidence_ratio > 0.3:
            recommendations.append(
                "You tend to be overconfident. Reduce confidence scores by 10-15%"
            )
        if underconfidence_ratio > 0.3:
            recommendations.append(
                "You tend to be underconfident. Confidence scores could be higher"
            )
        if avg_confidence < 0.6:
            recommendations.append("Overall confidence is low. Consider collecting more data")

        trend = ConfidenceTrendAnalysis(
            project_id=project_id,
            aspect=aspect,
            average_confidence=avg_confidence,
            confidence_trend=confidence_trend,
            trend_strength=trend_strength,
            overconfidence_ratio=overconfidence_ratio,
            underconfidence_ratio=underconfidence_ratio,
            recommendations=recommendations,
            sample_size=total_predictions,
            period_days=days_back,
        )

        return self.store.save_trend_analysis(trend)

    def record_confidence_outcome(
        self,
        project_id: int,
        aspect: str,
        predicted_confidence: float,
        actual_outcome: bool,
    ) -> ConfidenceCalibration:
        """Record the outcome of a confidence prediction for calibration."""
        calibration_error = None
        if actual_outcome:
            # If outcome happened, higher confidence = lower error
            calibration_error = 1.0 - predicted_confidence
        else:
            # If outcome didn't happen, higher confidence = higher error
            calibration_error = predicted_confidence

        calibration = ConfidenceCalibration(
            project_id=project_id,
            aspect=aspect,
            predicted_confidence=predicted_confidence,
            actual_outcome=actual_outcome,
            calibration_error=calibration_error,
            sample_count=1,
        )

        return self.store.record_calibration(calibration)

    def compare_plan_alternatives(
        self, plans: list[PlanAlternative]
    ) -> dict:
        """Compare alternative plans."""
        if not plans:
            return {}

        best_confidence = max(p.confidence_score for p in plans)
        fastest = min(p.estimated_duration_minutes for p in plans)
        slowest = max(p.estimated_duration_minutes for p in plans)

        comparison = {
            "total_alternatives": len(plans),
            "best_confidence": best_confidence,
            "best_confidence_plan": next(p for p in plans if p.confidence_score == best_confidence).plan_type,
            "fastest_plan": next(
                p for p in plans if p.estimated_duration_minutes == fastest
            ).plan_type,
            "slowest_plan": next(
                p for p in plans if p.estimated_duration_minutes == slowest
            ).plan_type,
            "time_range": {
                "min_minutes": fastest,
                "max_minutes": slowest,
                "difference_minutes": slowest - fastest,
            },
            "risk_assessment": self._assess_plan_risks(plans),
        }

        return comparison

    @staticmethod
    def _assess_plan_risks(plans: list[PlanAlternative]) -> dict:
        """Assess risks across plan alternatives."""
        all_risks = set()
        for plan in plans:
            all_risks.update(plan.risk_factors)

        risk_frequency = {}
        for risk in all_risks:
            frequency = sum(1 for p in plans if risk in p.risk_factors)
            risk_frequency[risk] = {
                "frequency": frequency,
                "percentage": frequency / len(plans) * 100,
                "common": frequency > len(plans) / 2,
            }

        return {
            "unique_risks": len(all_risks),
            "common_risks": [r for r, d in risk_frequency.items() if d["common"]],
            "risk_frequency": risk_frequency,
        }
