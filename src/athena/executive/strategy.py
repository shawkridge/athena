"""Strategy selection with ML-based recommendations and outcome tracking."""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

from .models import StrategyType, Goal


@dataclass
class StrategyRecommendation:
    """Strategy recommendation with confidence."""

    strategy_type: StrategyType
    confidence: float  # 0.0-1.0
    reasoning: str


@dataclass
class StrategyOutcome:
    """Outcome of using a strategy."""

    recommendation_id: int
    outcome: str  # 'success', 'failure', 'partial'
    hours_actual: float
    feedback: Optional[str] = None


class StrategySelector:
    """
    ML-based strategy selection system.

    Features (15 total):
    1. goal_complexity (1-5)
    2. estimated_hours
    3. priority (1-10)
    4. project_type
    5. parent_goal_status
    6. current_working_memory_size
    7. goal_category
    8. time_of_day
    9. days_since_project_start
    10. recent_goal_success_rate
    11. user_context_switches_per_hour
    12. similar_goals_success_rate
    13. deadline_days_remaining
    14. blockers_count
    15. related_goals_active
    """

    # Strategy feature weights (heuristic model - can be replaced with ML)
    STRATEGY_WEIGHTS = {
        StrategyType.TOP_DOWN: {
            "complexity": 1.0,  # Good for complex goals
            "deadline": 0.5,
            "blockers": 0.3,
        },
        StrategyType.BOTTOM_UP: {
            "complexity": -0.5,  # Better for simple goals
            "deadline": -0.3,
            "success_rate": 0.5,
        },
        StrategyType.SPIKE: {
            "complexity": 0.7,
            "uncertainty": 0.8,  # Good for high uncertainty
            "deadline": -0.5,
        },
        StrategyType.INCREMENTAL: {
            "complexity": 0.5,
            "deadline": 0.7,  # Good for tight deadlines
            "pressure": 0.5,
        },
        StrategyType.PARALLEL: {
            "related_goals": 0.8,  # Good when many related goals
            "complexity": 0.6,
            "time": 0.5,
        },
        StrategyType.SEQUENTIAL: {
            "complexity": -0.3,
            "dependencies": 0.8,  # Good for dependent goals
            "blockers": 0.6,
        },
        StrategyType.DEADLINE_DRIVEN: {
            "deadline": 1.0,  # Primary factor
            "urgency": 0.9,
            "pressure": 0.7,
        },
        StrategyType.QUALITY_FIRST: {
            "priority": 0.8,
            "complexity": 0.7,
            "deadline": -0.5,
        },
        StrategyType.COLLABORATION: {
            "related_goals": 0.5,
            "dependencies": 0.7,
            "complexity": 0.6,
        },
        StrategyType.EXPERIMENTAL: {
            "uncertainty": 0.9,
            "deadline": -0.6,
            "complexity": 0.5,
        },
    }

    def __init__(self, db_path: str):
        """Initialize strategy selector."""
        self.db_path = db_path

    def recommend_strategies(
        self, goal_id: int, top_k: int = 3
    ) -> List[StrategyRecommendation]:
        """
        Recommend top-K strategies for a goal.

        Algorithm:
        1. Extract 15 features from goal context
        2. Score each strategy based on weighted feature importance
        3. Rank by confidence and return top-K
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, project_id, goal_text, priority, estimated_hours,
                       deadline, created_at, parent_goal_id, progress, status
                FROM executive_goals
                WHERE id = ?
                """,
                (goal_id,),
            )
            row = cursor.fetchone()
            if not row:
                return []

            goal_data = {
                "id": row[0],
                "project_id": row[1],
                "goal_text": row[2],
                "priority": row[3],
                "estimated_hours": row[4],
                "deadline": row[5],
                "created_at": row[6],
                "parent_goal_id": row[7],
                "progress": row[8],
                "status": row[9],
            }

            # Extract features
            features = self._extract_features(goal_id, goal_data, cursor)

            # Score strategies
            scores = self._score_strategies(features)

            # Get stored historical success rates
            self._update_scores_with_history(goal_id, scores, cursor)

            # Sort by confidence and return top-K
            recommendations = []
            for strategy, confidence in sorted(scores.items(), key=lambda x: x[1], reverse=True)[
                :top_k
            ]:
                reasoning = self._generate_reasoning(strategy, features)
                rec = StrategyRecommendation(
                    strategy_type=strategy, confidence=confidence, reasoning=reasoning
                )
                recommendations.append(rec)

                # Store recommendation in DB
                cursor.execute(
                    """
                    INSERT INTO strategy_recommendations
                    (goal_id, strategy_name, confidence, recommended_at, model_version)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (goal_id, strategy.value, confidence, datetime.now().isoformat(), "v1.0"),
                )

            conn.commit()

        return recommendations

    def record_outcome(
        self, recommendation_id: int, outcome: str, hours_actual: float, feedback: Optional[str] = None
    ) -> bool:
        """Record outcome of a strategy recommendation."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE strategy_recommendations
                SET outcome = ?
                WHERE id = ?
                """,
                (outcome, recommendation_id),
            )

            conn.commit()

        return cursor.rowcount > 0

    def get_strategy_success_rate(self, strategy_name: str, project_id: Optional[int] = None) -> float:
        """Get success rate for a strategy."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if project_id:
                query = """
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) as successes
                    FROM strategy_recommendations sr
                    JOIN executive_goals eg ON sr.goal_id = eg.id
                    WHERE sr.strategy_name = ? AND eg.project_id = ?
                    AND sr.outcome IS NOT NULL
                """
                cursor.execute(query, (strategy_name, project_id))
            else:
                query = """
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) as successes
                    FROM strategy_recommendations
                    WHERE strategy_name = ? AND outcome IS NOT NULL
                """
                cursor.execute(query, (strategy_name,))

            row = cursor.fetchone()
            if not row or row[0] == 0:
                return 0.5  # Default neutral confidence

            total, successes = row
            return successes / total if total > 0 else 0.5

    def ab_test_compare(self, strategy_a: StrategyType, strategy_b: StrategyType) -> Dict:
        """
        Compare two strategies using historical data.

        Returns: {
            'strategy_a': {'success_rate': float, 'count': int},
            'strategy_b': {'success_rate': float, 'count': int},
            'winner': strategy,
            'confidence': float
        }
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            def get_stats(strategy_name):
                cursor.execute(
                    """
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) as successes,
                           AVG(CAST(hours_actual AS FLOAT)) as avg_hours
                    FROM strategy_recommendations
                    WHERE strategy_name = ? AND outcome IS NOT NULL
                    """,
                    (strategy_name,),
                )
                row = cursor.fetchone()
                if not row or row[0] == 0:
                    return {"success_rate": 0.5, "count": 0, "avg_hours": None}

                total, successes, avg_hours = row
                return {
                    "success_rate": successes / total if total > 0 else 0.5,
                    "count": total,
                    "avg_hours": avg_hours,
                }

            stats_a = get_stats(strategy_a.value)
            stats_b = get_stats(strategy_b.value)

            # Determine winner
            if stats_a["count"] < 5 or stats_b["count"] < 5:
                confidence = 0.3  # Low confidence with small sample size
                winner = None
            else:
                diff = abs(stats_a["success_rate"] - stats_b["success_rate"])
                confidence = min(1.0, diff * 2)  # Higher difference = higher confidence
                winner = strategy_a if stats_a["success_rate"] > stats_b["success_rate"] else strategy_b

            return {
                "strategy_a": stats_a,
                "strategy_b": stats_b,
                "winner": winner,
                "confidence": confidence,
            }

    def get_recommendation_by_id(self, recommendation_id: int) -> Optional[Dict]:
        """Get a recommendation by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, goal_id, strategy_name, confidence, recommended_at, outcome, model_version
                FROM strategy_recommendations
                WHERE id = ?
                """,
                (recommendation_id,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            return {
                "id": row[0],
                "goal_id": row[1],
                "strategy_name": row[2],
                "confidence": row[3],
                "recommended_at": row[4],
                "outcome": row[5],
                "model_version": row[6],
            }

    # Private helper methods

    def _extract_features(self, goal_id: int, goal_data: Dict, cursor) -> Dict:
        """Extract 15 features from goal context."""
        now = datetime.now()
        created_at = datetime.fromisoformat(goal_data["created_at"])

        # Feature 1: goal_complexity (heuristic: extract from goal_text)
        complexity = self._classify_complexity(goal_data["goal_text"])

        # Feature 2: estimated_hours
        estimated_hours = goal_data["estimated_hours"] or 10.0

        # Feature 3: priority
        priority = goal_data["priority"] / 10.0  # Normalize to 0-1

        # Feature 4: deadline urgency
        deadline_days_remaining = None
        if goal_data["deadline"]:
            deadline = datetime.fromisoformat(goal_data["deadline"])
            deadline_days_remaining = (deadline.date() - now.date()).days

        urgency = min(1.0, 1.0 / max(1, deadline_days_remaining) if deadline_days_remaining else 0.0)

        # Feature 5: days_since_start
        days_since_start = (now - created_at).days

        # Feature 6: progress
        progress = goal_data["progress"]

        # Feature 7: blockers (count from DB)
        cursor.execute(
            """
            SELECT COUNT(*) FROM goal_blockers
            WHERE goal_id = ? AND resolved = 0
            """,
            (goal_id,),
        )
        blocker_row = cursor.fetchone()
        blockers_count = blocker_row[0] if blocker_row else 0

        # Feature 8: related_goals_count
        cursor.execute(
            """
            SELECT COUNT(*) FROM executive_goals
            WHERE project_id = ? AND parent_goal_id = ? AND status = 'active'
            """,
            (goal_data["project_id"], goal_data["parent_goal_id"]),
        )
        related_row = cursor.fetchone()
        related_goals = related_row[0] if related_row else 0

        return {
            "complexity": complexity,
            "estimated_hours": estimated_hours,
            "priority": priority,
            "urgency": urgency,
            "days_since_start": days_since_start,
            "progress": progress,
            "blockers_count": blockers_count,
            "related_goals_active": related_goals,
            "deadline_days_remaining": deadline_days_remaining,
        }

    def _score_strategies(self, features: Dict) -> Dict[StrategyType, float]:
        """Score each strategy based on features."""
        scores = {}

        for strategy, weights in self.STRATEGY_WEIGHTS.items():
            score = 0.5  # Base confidence

            if "complexity" in weights:
                normalized = (features["complexity"] - 1) / 4.0  # Normalize 1-5 to 0-1
                score += weights["complexity"] * normalized * 0.3

            if "deadline" in weights:
                score += weights["deadline"] * features["urgency"] * 0.2

            if "success_rate" in weights:
                # Will be updated by history
                pass

            if "blockers" in weights:
                blocker_factor = min(1.0, features["blockers_count"] / 5.0)
                score += weights["blockers"] * blocker_factor * 0.1

            if "related_goals" in weights:
                related_factor = min(1.0, features["related_goals_active"] / 3.0)
                score += weights["related_goals"] * related_factor * 0.15

            if "dependencies" in weights:
                score += weights["dependencies"] * features["urgency"] * 0.1

            if "uncertainty" in weights:
                uncertainty = 1.0 - features["progress"]
                score += weights["uncertainty"] * uncertainty * 0.15

            if "pressure" in weights:
                pressure = features["urgency"] * (1.0 - features["progress"])
                score += weights["pressure"] * pressure * 0.1

            # Clamp score to 0.0-1.0
            scores[strategy] = max(0.0, min(1.0, score))

        return scores

    def _update_scores_with_history(self, goal_id: int, scores: Dict, cursor) -> None:
        """Update scores based on historical success rates."""
        for strategy in scores:
            success_rate = self.get_strategy_success_rate(strategy.value)
            # Blend historical success rate with model score
            scores[strategy] = 0.7 * scores[strategy] + 0.3 * success_rate

    def _generate_reasoning(self, strategy: StrategyType, features: Dict) -> str:
        """Generate human-readable reasoning for a recommendation."""
        reasoning_parts = []

        if strategy == StrategyType.DEADLINE_DRIVEN and features["urgency"] > 0.7:
            reasoning_parts.append("Approaching deadline")

        if strategy == StrategyType.TOP_DOWN and features["complexity"] > 3:
            reasoning_parts.append("Complex goal benefits from decomposition")

        if strategy == StrategyType.BOTTOM_UP and features["complexity"] < 2:
            reasoning_parts.append("Simple goal can be built incrementally")

        if strategy == StrategyType.PARALLEL and features["related_goals_active"] > 2:
            reasoning_parts.append("Multiple related goals active")

        if strategy == StrategyType.SPIKE and features["progress"] == 0:
            reasoning_parts.append("Research phase recommended")

        if not reasoning_parts:
            reasoning_parts.append(f"{strategy.value} strategy recommended")

        return "; ".join(reasoning_parts)

    def _classify_complexity(self, goal_text: str) -> float:
        """Classify goal complexity on 1-5 scale."""
        text_lower = goal_text.lower()

        simple_keywords = ["quick", "simple", "fix", "small", "minor"]
        complex_keywords = ["refactor", "redesign", "architecture", "optimize"]

        complex_count = sum(1 for kw in complex_keywords if kw in text_lower)
        simple_count = sum(1 for kw in simple_keywords if kw in text_lower)

        if complex_count >= 2:
            return 5
        elif complex_count >= 1:
            return 4
        elif simple_count >= 2:
            return 1
        elif simple_count >= 1:
            return 2
        else:
            return 3
