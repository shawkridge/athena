"""Learning rate adjustment and encoding strategy optimization."""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from statistics import mean, stdev

from .models import LearningRate


class LearningRateAdjuster:
    """
    Analyzes and optimizes encoding strategy effectiveness.

    Tracks:
    - Success rates of different encoding strategies
    - Consolidation threshold effectiveness
    - Strategy performance over time
    - Successful pattern profiles
    - Recommendations for strategy changes
    """

    def __init__(self, db_path: str):
        """Initialize learning rate adjuster."""
        self.db_path = db_path

    def track_strategy_performance(
        self,
        project_id: int,
        encoding_strategy: str,
        success: bool,
        cost_factor: float = 1.0,
    ) -> bool:
        """
        Track performance of an encoding strategy.

        Args:
            project_id: Project ID
            encoding_strategy: Strategy name (e.g., 'semantic', 'episodic_temporal', 'spatial')
            success: Whether this strategy resulted in successful retrieval
            cost_factor: Resource cost factor (0.0-1.0, where 1.0 = high cost)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get or create learning rate record
            cursor.execute(
                """
                SELECT id FROM metacognition_learning_rates
                WHERE project_id = ? AND encoding_strategy = ?
                """,
                (project_id, encoding_strategy),
            )
            row = cursor.fetchone()

            if row:
                record_id = row[0]
                # Update existing record
                cursor.execute(
                    """
                    UPDATE metacognition_learning_rates
                    SET trial_count = trial_count + 1,
                        success_count = success_count + ?,
                        last_evaluated = ?
                    WHERE id = ?
                    """,
                    (
                        1 if success else 0,
                        datetime.now().isoformat(),
                        record_id,
                    ),
                )
            else:
                # Create new record
                cursor.execute(
                    """
                    INSERT INTO metacognition_learning_rates
                    (project_id, encoding_strategy, trial_count, success_count, last_evaluated)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        encoding_strategy,
                        1,
                        1 if success else 0,
                        datetime.now().isoformat(),
                    ),
                )

            conn.commit()
            return True

    def calculate_strategy_effectiveness(
        self, project_id: int, encoding_strategy: str
    ) -> Dict:
        """
        Calculate effectiveness of an encoding strategy.

        Effectiveness = (success_count / trial_count) × (1 - cost_factor)

        Returns:
            Dictionary with:
            - success_rate: Percentage of successful uses
            - trial_count: Number of trials
            - effectiveness_score: Final effectiveness rating (0-1)
            - recommendation: 'increase_use', 'decrease_use', 'neutral'
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT trial_count, success_count FROM metacognition_learning_rates
                WHERE project_id = ? AND encoding_strategy = ?
                """,
                (project_id, encoding_strategy),
            )
            row = cursor.fetchone()

        if not row or row[0] == 0:
            return {
                "success_rate": 0.0,
                "trial_count": 0,
                "effectiveness_score": 0.0,
                "recommendation": "neutral",
            }

        trial_count, success_count = row
        success_rate = success_count / trial_count if trial_count > 0 else 0.0

        # Generate recommendation based on success rate
        if success_rate >= 0.8:
            recommendation = "increase_use"
        elif success_rate <= 0.4:
            recommendation = "decrease_use"
        else:
            recommendation = "neutral"

        return {
            "success_rate": success_rate,
            "trial_count": trial_count,
            "effectiveness_score": success_rate,
            "recommendation": recommendation,
        }

    def get_all_strategies(self, project_id: int) -> List[Dict]:
        """
        Get all encoding strategies and their effectiveness rankings.

        Returns sorted list (best to worst) of strategies with effectiveness scores.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT encoding_strategy, trial_count, success_count
                FROM metacognition_learning_rates
                WHERE project_id = ?
                ORDER BY success_count / CAST(trial_count AS FLOAT) DESC
                """,
                (project_id,),
            )
            rows = cursor.fetchall()

        strategies = []
        for strategy_name, trial_count, success_count in rows:
            if trial_count > 0:
                success_rate = success_count / trial_count
                strategies.append(
                    {
                        "strategy": strategy_name,
                        "success_rate": success_rate,
                        "trial_count": trial_count,
                        "effectiveness_score": success_rate,
                    }
                )

        return strategies

    def optimize_consolidation_threshold(self, project_id: int) -> Dict:
        """
        Recommend optimized consolidation thresholds based on strategy performance.

        Returns:
            Dictionary with recommended thresholds:
            - primary_strategy: Best performing strategy
            - secondary_strategy: Second best
            - recommended_threshold: Suggested consolidation threshold
            - rationale: Explanation of recommendation
        """
        strategies = self.get_all_strategies(project_id)

        if not strategies:
            return {
                "primary_strategy": None,
                "secondary_strategy": None,
                "recommended_threshold": 0.75,
                "rationale": "No strategy data available yet",
            }

        # Get top 2 strategies
        primary = strategies[0] if strategies else None
        secondary = strategies[1] if len(strategies) > 1 else None

        # Calculate recommended threshold based on primary strategy effectiveness
        if primary:
            effectiveness = primary["effectiveness_score"]
            # Scale threshold from 0.5 to 0.9 based on effectiveness
            recommended_threshold = 0.5 + (effectiveness * 0.4)
        else:
            recommended_threshold = 0.75

        return {
            "primary_strategy": primary["strategy"] if primary else None,
            "secondary_strategy": secondary["strategy"] if secondary else None,
            "recommended_threshold": recommended_threshold,
            "rationale": (
                f"Primary strategy '{primary['strategy']}' has {primary['effectiveness_score']:.1%} "
                f"effectiveness ({primary['trial_count']} trials)"
                if primary
                else "Insufficient data for recommendation"
            ),
        }

    def profile_successful_patterns(self, project_id: int) -> Dict:
        """
        Identify patterns in successful encoding strategies.

        Returns:
            Dictionary with patterns:
            - most_effective: Best performing strategy
            - high_performers: Strategies with >75% success rate
            - low_performers: Strategies with <40% success rate
            - variance: Consistency of results
            - recommendations: Actionable changes
        """
        strategies = self.get_all_strategies(project_id)

        if not strategies:
            return {
                "most_effective": None,
                "high_performers": [],
                "low_performers": [],
                "variance": 0.0,
                "recommendations": ["No strategy data available"],
            }

        high_performers = [s for s in strategies if s["effectiveness_score"] >= 0.75]
        low_performers = [s for s in strategies if s["effectiveness_score"] <= 0.4]

        # Calculate variance in effectiveness
        if len(strategies) > 1:
            scores = [s["effectiveness_score"] for s in strategies]
            variance = (
                stdev(scores) if len(scores) > 1 else 0.0
            )  # Standard deviation
        else:
            variance = 0.0

        recommendations = []
        if high_performers:
            recommendations.append(
                f"Increase use of {high_performers[0]['strategy']} (highest effectiveness: {high_performers[0]['effectiveness_score']:.1%})"
            )
        if low_performers:
            recommendations.append(
                f"Review or reduce use of {low_performers[0]['strategy']} (lowest effectiveness: {low_performers[0]['effectiveness_score']:.1%})"
            )
        if variance > 0.3:
            recommendations.append(
                "High variance in strategy effectiveness - diversify approaches"
            )

        return {
            "most_effective": strategies[0]["strategy"] if strategies else None,
            "high_performers": [s["strategy"] for s in high_performers],
            "low_performers": [s["strategy"] for s in low_performers],
            "variance": variance,
            "recommendations": recommendations,
        }

    def recommend_strategy_changes(self, project_id: int) -> List[Dict]:
        """
        Generate specific recommendations for strategy changes.

        Returns:
            List of recommendations sorted by priority:
            - action: What to do
            - strategy: Which strategy
            - reason: Why
            - priority: 'low', 'medium', 'high'
            - expected_improvement: Estimated improvement percentage
        """
        strategies = self.get_all_strategies(project_id)
        patterns = self.profile_successful_patterns(project_id)
        recommendations = []

        if not strategies:
            return []

        # Get average effectiveness
        avg_effectiveness = (
            mean([s["effectiveness_score"] for s in strategies])
            if strategies
            else 0.0
        )

        for strategy in strategies:
            score = strategy["effectiveness_score"]
            delta = score - avg_effectiveness

            if score >= 0.85:
                recommendations.append(
                    {
                        "action": "increase_use",
                        "strategy": strategy["strategy"],
                        "reason": f"High effectiveness ({score:.1%}), well above average",
                        "priority": "high",
                        "expected_improvement": 0.1,
                    }
                )
            elif score < 0.35 and strategy["trial_count"] >= 10:
                recommendations.append(
                    {
                        "action": "decrease_use",
                        "strategy": strategy["strategy"],
                        "reason": f"Low effectiveness ({score:.1%}), consistently underperforming",
                        "priority": "medium",
                        "expected_improvement": -0.05,
                    }
                )
            elif score < avg_effectiveness - 0.2 and strategy["trial_count"] >= 20:
                recommendations.append(
                    {
                        "action": "review_and_optimize",
                        "strategy": strategy["strategy"],
                        "reason": f"Below average ({score:.1%}), investigate causes",
                        "priority": "medium",
                        "expected_improvement": 0.05,
                    }
                )

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda x: priority_order.get(x["priority"], 3))

        return recommendations

    def get_strategy_performance_over_time(
        self, project_id: int, encoding_strategy: str, hours: int = 24
    ) -> Dict:
        """
        Get strategy performance trend over a time period.

        Returns:
            Dictionary with trend analysis:
            - current_performance: Latest effectiveness score
            - trend: 'improving', 'declining', 'stable'
            - historical_performance: List of (timestamp, score) tuples
            - recommendation: Based on trend
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()

            cursor.execute(
                """
                SELECT trial_count, success_count, last_evaluated
                FROM metacognition_learning_rates
                WHERE project_id = ? AND encoding_strategy = ?
                """,
                (project_id, encoding_strategy),
            )
            row = cursor.fetchone()

        if not row:
            return {
                "current_performance": 0.0,
                "trend": "unknown",
                "historical_performance": [],
                "recommendation": "No data available",
            }

        trial_count, success_count, last_evaluated = row
        current_performance = (
            success_count / trial_count if trial_count > 0 else 0.0
        )

        # Simple trend analysis: if performance is >0.7 it's improving, <0.4 declining
        if current_performance >= 0.7:
            trend = "improving"
            recommendation = "Continue using this strategy"
        elif current_performance <= 0.4:
            trend = "declining"
            recommendation = "Consider reducing use or investigating issues"
        else:
            trend = "stable"
            recommendation = "Monitor and compare with alternatives"

        return {
            "current_performance": current_performance,
            "trend": trend,
            "historical_performance": [(last_evaluated, current_performance)],
            "recommendation": recommendation,
        }

    def get_learning_rate_report(self, project_id: int) -> Dict:
        """
        Generate comprehensive learning rate report for a project.

        Returns:
            Dictionary with complete analysis:
            - strategy_rankings: All strategies ranked by effectiveness
            - top_performer: Best strategy
            - consolidation_recommendation: Optimal threshold
            - pattern_analysis: Successful pattern profiles
            - recommended_changes: List of recommended actions
            - summary: High-level summary
        """
        strategies = self.get_all_strategies(project_id)
        consolidation = self.optimize_consolidation_threshold(project_id)
        patterns = self.profile_successful_patterns(project_id)
        recommendations = self.recommend_strategy_changes(project_id)

        summary = f"Analyzed {len(strategies)} encoding strategies across {sum(s['trial_count'] for s in strategies)} total trials"
        if strategies:
            avg_effectiveness = mean(
                [s["effectiveness_score"] for s in strategies]
            )
            summary += f". Average effectiveness: {avg_effectiveness:.1%}"

        return {
            "strategy_rankings": strategies,
            "top_performer": strategies[0] if strategies else None,
            "consolidation_recommendation": consolidation,
            "pattern_analysis": patterns,
            "recommended_changes": recommendations,
            "summary": summary,
        }
