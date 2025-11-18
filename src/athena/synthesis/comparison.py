"""Comparison framework for evaluating and comparing solution approaches."""

import logging
from typing import List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ComparisonResult:
    """Result of comparing two approaches."""

    approach_a: str
    approach_b: str
    winner: str  # Which one is "better" overall
    dimensions: Dict[str, Dict[str, Any]]  # Per-dimension comparison
    trade_offs: List[Dict[str, str]]  # Trade-offs identified
    recommendation: str  # Why choose one over the other
    neutral_factors: List[str]  # Factors that don't differentiate


class ComparisonFramework:
    """Framework for comparing solution approaches."""

    def compare_approaches(
        self,
        approach_a: Dict[str, Any],
        approach_b: Dict[str, Any],
        weights: Dict[str, float] = None,
        context: Dict[str, Any] = None,
    ) -> ComparisonResult:
        """Compare two solution approaches.

        Args:
            approach_a: First approach
            approach_b: Second approach
            weights: Weights for different dimensions
            context: Additional context for comparison

        Returns:
            ComparisonResult with detailed analysis
        """
        logger.info(f"Comparing {approach_a.get('name')} vs {approach_b.get('name')}")

        # Default weights if not provided
        if not weights:
            weights = self._get_default_weights()

        # Per-dimension comparison
        dimensions = self._compare_dimensions(approach_a, approach_b, context)

        # Identify trade-offs
        trade_offs = self._identify_trade_offs(approach_a, approach_b, dimensions)

        # Determine winner based on weights
        score_a = self._calculate_score(approach_a, dimensions, weights)
        score_b = self._calculate_score(approach_b, dimensions, weights)

        winner = approach_a.get("name") if score_a > score_b else approach_b.get("name")

        # Generate recommendation
        recommendation = self._generate_recommendation(
            approach_a,
            approach_b,
            score_a,
            score_b,
            trade_offs,
            context,
        )

        # Find neutral factors
        neutral_factors = self._find_neutral_factors(approach_a, approach_b, dimensions)

        return ComparisonResult(
            approach_a=approach_a.get("name", "Approach A"),
            approach_b=approach_b.get("name", "Approach B"),
            winner=winner,
            dimensions=dimensions,
            trade_offs=trade_offs,
            recommendation=recommendation,
            neutral_factors=neutral_factors,
        )

    def compare_all(
        self,
        approaches: List[Dict[str, Any]],
        weights: Dict[str, float] = None,
    ) -> Dict[str, Any]:
        """Compare all approaches against each other.

        Args:
            approaches: List of approaches to compare
            weights: Weights for dimensions

        Returns:
            Comprehensive comparison results
        """
        logger.info(f"Comparing {len(approaches)} approaches")

        # Pairwise comparisons
        comparisons = []
        for i, approach_a in enumerate(approaches):
            for approach_b in approaches[i + 1 :]:
                comparison = self.compare_approaches(
                    approach_a,
                    approach_b,
                    weights=weights,
                )
                comparisons.append(comparison)

        # Score each approach against all others
        scores = {}
        for approach in approaches:
            approach_name = approach.get("name")
            wins = len([c for c in comparisons if c.winner == approach_name])
            scores[approach_name] = {
                "wins": wins,
                "rank": 0,  # Will be calculated
                "wins_pct": wins / max(len(approaches) - 1, 1),
            }

        # Rank approaches
        ranked = sorted(
            scores.items(),
            key=lambda x: x[1]["wins"],
            reverse=True,
        )
        for rank, (name, score) in enumerate(ranked, 1):
            score["rank"] = rank

        return {
            "total_approaches": len(approaches),
            "pairwise_comparisons": [
                {
                    "approach_a": c.approach_a,
                    "approach_b": c.approach_b,
                    "winner": c.winner,
                    "trade_offs": c.trade_offs,
                }
                for c in comparisons
            ],
            "rankings": scores,
            "best_overall": ranked[0][0] if ranked else None,
        }

    def rank_by_criteria(
        self,
        approaches: List[Dict[str, Any]],
        priority_dimensions: List[str],
    ) -> Dict[str, Any]:
        """Rank approaches by specific priority dimensions.

        Args:
            approaches: List of approaches
            priority_dimensions: Which dimensions matter most

        Returns:
            Ranking by priority dimensions
        """
        rankings = {}

        for dimension in priority_dimensions:
            ranked = sorted(
                approaches,
                key=lambda a: a.get("scores", {}).get(dimension, 0),
                reverse=True,
            )

            rankings[dimension] = [
                {
                    "rank": i + 1,
                    "name": a.get("name"),
                    "score": a.get("scores", {}).get(dimension, 0),
                }
                for i, a in enumerate(ranked)
            ]

        return rankings

    def find_dominant(self, approaches: List[Dict[str, Any]]) -> List[str]:
        """Find Pareto-dominant approaches (not dominated by any other).

        Args:
            approaches: List of approaches

        Returns:
            List of dominant approach names
        """
        dominant = []

        for approach_a in approaches:
            is_dominated = False

            for approach_b in approaches:
                if approach_a == approach_b:
                    continue

                # Check if B dominates A (better in all dimensions)
                scores_a = approach_a.get("scores", {})
                scores_b = approach_b.get("scores", {})

                all_better = all(scores_b.get(k, 0) >= scores_a.get(k, 0) for k in scores_a.keys())
                any_strictly_better = any(
                    scores_b.get(k, 0) > scores_a.get(k, 0) for k in scores_a.keys()
                )

                if all_better and any_strictly_better:
                    is_dominated = True
                    break

            if not is_dominated:
                dominant.append(approach_a.get("name"))

        return dominant

    def _compare_dimensions(
        self,
        approach_a: Dict[str, Any],
        approach_b: Dict[str, Any],
        context: Dict[str, Any] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Compare approaches across all dimensions."""
        dimensions = {}

        # Key dimensions to compare
        comparison_dims = [
            "simplicity",
            "performance",
            "scalability",
            "maintainability",
            "reliability",
            "cost",
        ]

        scores_a = approach_a.get("scores", {})
        scores_b = approach_b.get("scores", {})

        for dim in comparison_dims:
            score_a = scores_a.get(dim, 0.5)
            score_b = scores_b.get(dim, 0.5)
            diff = score_b - score_a

            dimensions[dim] = {
                "approach_a_score": score_a,
                "approach_b_score": score_b,
                "difference": diff,
                "winner": (
                    approach_b.get("name")
                    if diff > 0.1
                    else (approach_a.get("name") if diff < -0.1 else "tie")
                ),
                "analysis": self._analyze_dimension(dim, score_a, score_b),
            }

        return dimensions

    def _analyze_dimension(self, dimension: str, score_a: float, score_b: float) -> str:
        """Generate analysis text for a dimension."""
        if abs(score_a - score_b) < 0.1:
            return "Both approaches perform similarly"

        advantage = "Approach B" if score_b > score_a else "Approach A"
        percentage = abs(score_b - score_a) * 100

        analysis_map = {
            "simplicity": f"{advantage} is {percentage:.0f}% simpler to implement",
            "performance": f"{advantage} has {percentage:.0f}% better performance",
            "scalability": f"{advantage} scales {percentage:.0f}% better",
            "maintainability": f"{advantage} is {percentage:.0f}% more maintainable",
            "reliability": f"{advantage} is {percentage:.0f}% more reliable",
            "cost": f"{advantage} costs {percentage:.0f}% less",
        }

        return analysis_map.get(dimension, f"Difference of {percentage:.0f}%")

    def _identify_trade_offs(
        self,
        approach_a: Dict[str, Any],
        approach_b: Dict[str, Any],
        dimensions: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        """Identify trade-offs between approaches."""
        trade_offs = []

        for dim, comparison in dimensions.items():
            diff = comparison["difference"]

            # Significant difference = trade-off
            if abs(diff) > 0.2:
                if diff > 0:
                    trade_offs.append(
                        {
                            "advantage": approach_b.get("name"),
                            "dimension": dim,
                            "description": comparison["analysis"],
                        }
                    )
                else:
                    trade_offs.append(
                        {
                            "advantage": approach_a.get("name"),
                            "dimension": dim,
                            "description": comparison["analysis"],
                        }
                    )

        return trade_offs

    def _calculate_score(
        self,
        approach: Dict[str, Any],
        dimensions: Dict[str, Dict[str, Any]],
        weights: Dict[str, float],
    ) -> float:
        """Calculate weighted score for an approach."""
        scores = approach.get("scores", {})
        total = 0.0

        for dim, weight in weights.items():
            score = scores.get(dim, 0.5)
            # Cost is inverted (lower is better)
            if dim == "cost":
                score = 1.0 - score
            total += score * weight

        return total

    def _generate_recommendation(
        self,
        approach_a: Dict[str, Any],
        approach_b: Dict[str, Any],
        score_a: float,
        score_b: float,
        trade_offs: List[Dict[str, str]],
        context: Dict[str, Any] = None,
    ) -> str:
        """Generate recommendation text."""
        winner = approach_b.get("name") if score_b > score_a else approach_a.get("name")
        loser = approach_a.get("name") if score_b > score_a else approach_b.get("name")
        score_diff = abs(score_b - score_a)

        if score_diff < 0.1:
            return (
                "Both approaches are roughly equivalent. Choice depends on "
                "team preference and specific constraints."
            )
        elif score_diff < 0.2:
            return (
                f"Slight edge to {winner} due to better balance across dimensions. "
                f"However, {loser} may be better if team has specific expertise."
            )
        else:
            return (
                f"Recommend {winner}: significantly better overall score. "
                f"{loser} has advantages in specific areas but {winner} is the safer choice."
            )

    def _find_neutral_factors(
        self,
        approach_a: Dict[str, Any],
        approach_b: Dict[str, Any],
        dimensions: Dict[str, Dict[str, Any]],
    ) -> List[str]:
        """Find factors that don't differentiate approaches."""
        neutral = []

        for dim, comparison in dimensions.items():
            if comparison["winner"] == "tie":
                neutral.append(dim)

        return neutral

    def _get_default_weights(self) -> Dict[str, float]:
        """Get default dimension weights."""
        return {
            "simplicity": 0.2,
            "performance": 0.2,
            "scalability": 0.2,
            "maintainability": 0.2,
            "reliability": 0.15,
            "cost": 0.05,
        }

    def explain_choice(
        self,
        chosen: Dict[str, Any],
        alternatives: List[Dict[str, Any]],
    ) -> str:
        """Generate explanation for why a solution was chosen."""
        explanation = f"We chose '{chosen.get('name')}' because:\n\n"

        strengths = [f"- {k}: {v:.0%}" for k, v in chosen.get("scores", {}).items() if v > 0.7]

        if strengths:
            explanation += "**Strengths:**\n" + "\n".join(strengths) + "\n\n"

        # Compare to alternatives
        if alternatives:
            explanation += "**vs Alternatives:**\n"
            for alt in alternatives:
                explanation += (
                    f"- Better than '{alt.get('name')}' in {self._get_better_dims(chosen, alt)}\n"
                )

        return explanation

    def _get_better_dims(self, chosen: Dict[str, Any], alternative: Dict[str, Any]) -> str:
        """Get dimensions where chosen is better."""
        chosen_scores = chosen.get("scores", {})
        alt_scores = alternative.get("scores", {})

        better = [dim for dim, score in chosen_scores.items() if score > alt_scores.get(dim, 0.5)]

        return ", ".join(better) if better else "similar areas"
