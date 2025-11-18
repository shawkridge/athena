"""Confidence scoring system for Phase 9.1."""

from typing import Optional

from athena.phase9.uncertainty.models import (
    ConfidenceInterval,
    ConfidenceLevel,
    ConfidenceScore,
    UncertaintyType,
)


class ConfidenceScorer:
    """Score confidence for tasks, predictions, and estimates."""

    # Confidence level thresholds
    VERY_LOW_THRESHOLD = 0.40
    LOW_THRESHOLD = 0.60
    MEDIUM_THRESHOLD = 0.75
    HIGH_THRESHOLD = 0.90

    @staticmethod
    def calculate_confidence_level(score: float) -> ConfidenceLevel:
        """Convert numeric confidence score to confidence level."""
        if score < ConfidenceScorer.VERY_LOW_THRESHOLD:
            return ConfidenceLevel.VERY_LOW
        elif score < ConfidenceScorer.LOW_THRESHOLD:
            return ConfidenceLevel.LOW
        elif score < ConfidenceScorer.MEDIUM_THRESHOLD:
            return ConfidenceLevel.MEDIUM
        elif score < ConfidenceScorer.HIGH_THRESHOLD:
            return ConfidenceLevel.HIGH
        else:
            return ConfidenceLevel.VERY_HIGH

    @staticmethod
    def score_estimate(
        task_id: int,
        estimate: float,
        historical_variance: float = 0.15,
        data_points: int = 10,
        estimate_complexity: float = 0.5,  # 0-1, higher = more complex
        external_factors: list[str] = None,
    ) -> ConfidenceScore:
        """Score confidence in a task estimate."""
        if external_factors is None:
            external_factors = []

        # Base score from inverse of variance
        base_score = max(0.0, 1.0 - min(historical_variance, 1.0))

        # Adjust for data availability (more data = higher confidence)
        data_factor = min(1.0, data_points / 20.0)  # Normalize to 20 points
        base_score *= 0.5 + 0.5 * data_factor

        # Adjust for complexity (more complex = lower confidence)
        base_score *= 1.0 - estimate_complexity * 0.3

        # Adjust for external factors (each factor reduces by ~10%)
        external_factor = max(0.5, 1.0 - len(external_factors) * 0.1)
        base_score *= external_factor

        final_score = max(0.0, min(1.0, base_score))

        # Determine uncertainty sources
        uncertainty_sources = []
        if historical_variance > 0.2:
            uncertainty_sources.append(UncertaintyType.EPISTEMIC)
        if external_factors:
            uncertainty_sources.append(UncertaintyType.ALEATORIC)
        if estimate_complexity > 0.7:
            uncertainty_sources.append(UncertaintyType.MODELING)

        # Contributing factors
        contributing_factors = {
            "variance_impact": 1.0 - min(historical_variance, 1.0),
            "data_availability": data_factor,
            "complexity_impact": 1.0 - estimate_complexity * 0.3,
            "external_factors": external_factor,
        }

        # Calculate bounds (confidence interval)
        std_error = estimate * historical_variance
        lower_bound = estimate - 1.96 * std_error  # 95% confidence
        upper_bound = estimate + 1.96 * std_error

        supporting_evidence = [
            f"Historical variance: {historical_variance:.1%}",
            f"Data points: {data_points}",
        ]

        contradicting_evidence = []
        if external_factors:
            contradicting_evidence.append(f"External factors: {', '.join(external_factors)}")
        if estimate_complexity > 0.7:
            contradicting_evidence.append("High complexity estimate")

        return ConfidenceScore(
            task_id=task_id,
            aspect="estimate",
            value=final_score,
            confidence_level=ConfidenceScorer.calculate_confidence_level(final_score),
            uncertainty_sources=uncertainty_sources,
            contributing_factors=contributing_factors,
            lower_bound=max(0, lower_bound),
            upper_bound=upper_bound,
            supporting_evidence=supporting_evidence,
            contradicting_evidence=contradicting_evidence,
        )

    @staticmethod
    def score_prediction(
        task_id: int,
        prediction: str,
        supporting_data: list[str] = None,
        conflicting_data: list[str] = None,
        historical_accuracy: float = 0.7,
        model_uncertainty: float = 0.15,
    ) -> ConfidenceScore:
        """Score confidence in a prediction."""
        if supporting_data is None:
            supporting_data = []
        if conflicting_data is None:
            conflicting_data = []

        # Base score from historical accuracy
        base_score = historical_accuracy

        # Adjust for supporting/conflicting data
        evidence_ratio = len(supporting_data) / max(1, len(supporting_data) + len(conflicting_data))
        base_score *= 0.5 + 0.5 * evidence_ratio

        # Adjust for model uncertainty
        base_score *= 1.0 - model_uncertainty * 0.3

        final_score = max(0.0, min(1.0, base_score))

        uncertainty_sources = [UncertaintyType.MODELING]
        if conflicting_data:
            uncertainty_sources.append(UncertaintyType.EPISTEMIC)

        contributing_factors = {
            "historical_accuracy": historical_accuracy,
            "evidence_ratio": evidence_ratio,
            "model_uncertainty": 1.0 - model_uncertainty * 0.3,
        }

        return ConfidenceScore(
            task_id=task_id,
            aspect="prediction",
            value=final_score,
            confidence_level=ConfidenceScorer.calculate_confidence_level(final_score),
            uncertainty_sources=uncertainty_sources,
            contributing_factors=contributing_factors,
            supporting_evidence=supporting_data,
            contradicting_evidence=conflicting_data,
        )

    @staticmethod
    def score_resource_estimate(
        task_id: int,
        required_skills: list[str],
        available_skills: list[str],
        tool_dependencies: list[str] = None,
        tools_available: list[str] = None,
    ) -> ConfidenceScore:
        """Score confidence in resource requirements."""
        if tool_dependencies is None:
            tool_dependencies = []
        if tools_available is None:
            tools_available = []

        # Score skill match
        matched_skills = len(set(required_skills) & set(available_skills))
        skill_match_ratio = matched_skills / max(1, len(required_skills))

        # Score tool availability
        available_tools = len(set(tool_dependencies) & set(tools_available))
        tool_match_ratio = available_tools / max(1, len(tool_dependencies))

        # Combined score
        base_score = 0.6 * skill_match_ratio + 0.4 * tool_match_ratio
        final_score = max(0.0, min(1.0, base_score))

        uncertainty_sources = []
        if matched_skills < len(required_skills):
            uncertainty_sources.append(UncertaintyType.EPISTEMIC)

        missing_skills = set(required_skills) - set(available_skills)
        missing_tools = set(tool_dependencies) - set(tools_available)

        contradicting_evidence = []
        if missing_skills:
            contradicting_evidence.append(f"Missing skills: {', '.join(missing_skills)}")
        if missing_tools:
            contradicting_evidence.append(f"Missing tools: {', '.join(missing_tools)}")

        return ConfidenceScore(
            task_id=task_id,
            aspect="resource",
            value=final_score,
            confidence_level=ConfidenceScorer.calculate_confidence_level(final_score),
            uncertainty_sources=uncertainty_sources,
            contributing_factors={
                "skill_match": skill_match_ratio,
                "tool_availability": tool_match_ratio,
            },
            supporting_evidence=[
                f"Skill match: {matched_skills}/{len(required_skills)}",
                f"Tool availability: {available_tools}/{len(tool_dependencies)}",
            ],
            contradicting_evidence=contradicting_evidence,
        )

    @staticmethod
    def score_timeline(
        task_id: int,
        estimated_duration: float,
        deadline_days: Optional[float] = None,
        dependency_count: int = 0,
        historical_delays: float = 0.0,  # % of tasks delayed
    ) -> ConfidenceScore:
        """Score confidence in timeline estimate."""
        base_score = 1.0 - (historical_delays * 0.5)

        if deadline_days:
            # Score based on slack (deadline vs estimate)
            estimate_days = estimated_duration / (8 * 60)  # Assuming 8-hour days
            slack_ratio = deadline_days / estimate_days if estimate_days > 0 else 1.0
            # More slack = higher confidence
            slack_score = min(1.0, slack_ratio / 2.0)  # 2x slack = max confidence
            base_score *= 0.7 + 0.3 * slack_score

        # More dependencies = less certainty
        dependency_factor = max(0.5, 1.0 - dependency_count * 0.1)
        base_score *= dependency_factor

        final_score = max(0.0, min(1.0, base_score))

        uncertainty_sources = []
        if dependency_count > 3:
            uncertainty_sources.append(UncertaintyType.EPISTEMIC)
        if historical_delays > 0.3:
            uncertainty_sources.append(UncertaintyType.ALEATORIC)

        contradicting_evidence = []
        if deadline_days and estimated_duration / (8 * 60) > deadline_days:
            contradicting_evidence.append("Insufficient time slack")
        if historical_delays > 0.3:
            contradicting_evidence.append(
                f"History of delays: {historical_delays:.0%} of tasks delayed"
            )

        return ConfidenceScore(
            task_id=task_id,
            aspect="timeline",
            value=final_score,
            confidence_level=ConfidenceScorer.calculate_confidence_level(final_score),
            uncertainty_sources=uncertainty_sources,
            contributing_factors={
                "historical_delays": 1.0 - historical_delays * 0.5,
                "time_slack": slack_score if deadline_days else 0.5,
                "dependencies": dependency_factor,
            },
            supporting_evidence=[
                f"Dependencies: {dependency_count}",
                f"Historical delays: {historical_delays:.0%}",
            ],
            contradicting_evidence=contradicting_evidence,
        )

    @staticmethod
    def generate_confidence_interval(
        estimate: float,
        variance: float,
        confidence_level: float = 0.95,
        method: str = "normal",
    ) -> ConfidenceInterval:
        """Generate confidence interval for estimate."""
        # Z-score for confidence level
        z_scores = {0.50: 0.674, 0.68: 1.0, 0.95: 1.96, 0.99: 2.576}
        z = z_scores.get(confidence_level, 1.96)

        # Standard error
        std_error = estimate * variance

        # Calculate bounds
        lower_bound = max(0, estimate - z * std_error)
        upper_bound = estimate + z * std_error

        return ConfidenceInterval(
            estimate=estimate,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            confidence_level=confidence_level,
            unit="minutes",
            method=method,
        )
