"""Tests for LearningRateAdjuster component."""

import sqlite3
from pathlib import Path
from datetime import datetime

import pytest

from athena.metacognition.learning import LearningRateAdjuster


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary database."""
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    cursor = conn.cursor()

    # Create learning rates table
    cursor.execute(
        """
        CREATE TABLE metacognition_learning_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            encoding_strategy TEXT NOT NULL,
            success_rate REAL,
            trial_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            last_evaluated TIMESTAMP,
            recommendation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()
    return str(db)


@pytest.fixture
def adjuster(db_path):
    """Create LearningRateAdjuster instance."""
    return LearningRateAdjuster(db_path)


class TestStrategyPerformanceTracking:
    """Test strategy performance tracking."""

    def test_track_strategy_success(self, adjuster, db_path):
        """Test tracking successful strategy use."""
        assert adjuster.track_strategy_performance(
            project_id=1, encoding_strategy="semantic", success=True
        )

        # Verify in database
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT trial_count, success_count
                FROM metacognition_learning_rates
                WHERE project_id = 1 AND encoding_strategy = 'semantic'
                """
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == 1  # trial_count
        assert row[1] == 1  # success_count

    def test_track_strategy_failure(self, adjuster, db_path):
        """Test tracking failed strategy use."""
        assert adjuster.track_strategy_performance(
            project_id=1, encoding_strategy="semantic", success=False
        )

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT trial_count, success_count
                FROM metacognition_learning_rates
                WHERE project_id = 1 AND encoding_strategy = 'semantic'
                """
            )
            row = cursor.fetchone()

        assert row[0] == 1  # trial_count
        assert row[1] == 0  # success_count

    def test_track_multiple_trials(self, adjuster, db_path):
        """Test tracking multiple trials accumulate."""
        # Track multiple successes
        for _ in range(8):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="episodic", success=True
            )

        # Track multiple failures
        for _ in range(2):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="episodic", success=False
            )

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT trial_count, success_count
                FROM metacognition_learning_rates
                WHERE project_id = 1 AND encoding_strategy = 'episodic'
                """
            )
            row = cursor.fetchone()

        assert row[0] == 10  # total trials
        assert row[1] == 8  # successes


class TestStrategyEffectiveness:
    """Test effectiveness calculation."""

    def test_effectiveness_perfect_success(self, adjuster):
        """Test effectiveness with perfect success rate."""
        for _ in range(10):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="spatial", success=True
            )

        effectiveness = adjuster.calculate_strategy_effectiveness(
            project_id=1, encoding_strategy="spatial"
        )

        assert effectiveness["success_rate"] == 1.0
        assert effectiveness["effectiveness_score"] == 1.0
        assert effectiveness["recommendation"] == "increase_use"

    def test_effectiveness_partial_success(self, adjuster):
        """Test effectiveness with partial success rate."""
        # 7 successes, 3 failures = 70% success rate
        for _ in range(7):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="hybrid", success=True
            )
        for _ in range(3):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="hybrid", success=False
            )

        effectiveness = adjuster.calculate_strategy_effectiveness(
            project_id=1, encoding_strategy="hybrid"
        )

        assert effectiveness["success_rate"] == 0.7
        assert effectiveness["trial_count"] == 10
        assert effectiveness["recommendation"] == "neutral"

    def test_effectiveness_low_success(self, adjuster):
        """Test effectiveness with low success rate."""
        # 3 successes, 7 failures = 30% success rate
        for _ in range(3):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="temporal", success=True
            )
        for _ in range(7):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="temporal", success=False
            )

        effectiveness = adjuster.calculate_strategy_effectiveness(
            project_id=1, encoding_strategy="temporal"
        )

        assert effectiveness["success_rate"] == 0.3
        assert effectiveness["recommendation"] == "decrease_use"

    def test_effectiveness_nonexistent_strategy(self, adjuster):
        """Test effectiveness for strategy with no data."""
        effectiveness = adjuster.calculate_strategy_effectiveness(
            project_id=999, encoding_strategy="nonexistent"
        )

        assert effectiveness["success_rate"] == 0.0
        assert effectiveness["trial_count"] == 0
        assert effectiveness["recommendation"] == "neutral"


class TestStrategyRanking:
    """Test strategy performance rankings."""

    def test_get_all_strategies_ranked(self, adjuster):
        """Test getting all strategies ranked by effectiveness."""
        # Strategy A: 90% effectiveness
        for _ in range(9):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="strategy_a", success=True
            )
        adjuster.track_strategy_performance(
            project_id=1, encoding_strategy="strategy_a", success=False
        )

        # Strategy B: 60% effectiveness
        for _ in range(6):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="strategy_b", success=True
            )
        for _ in range(4):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="strategy_b", success=False
            )

        # Strategy C: 40% effectiveness
        for _ in range(4):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="strategy_c", success=True
            )
        for _ in range(6):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="strategy_c", success=False
            )

        strategies = adjuster.get_all_strategies(project_id=1)

        assert len(strategies) == 3
        assert strategies[0]["strategy"] == "strategy_a"
        assert strategies[0]["success_rate"] == 0.9
        assert strategies[1]["strategy"] == "strategy_b"
        assert strategies[2]["strategy"] == "strategy_c"


class TestConsolidationOptimization:
    """Test consolidation threshold optimization."""

    def test_optimize_threshold_with_data(self, adjuster):
        """Test consolidation threshold optimization."""
        # Set up high-effectiveness strategy
        for _ in range(90):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="best", success=True
            )
        for _ in range(10):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="best", success=False
            )

        optimization = adjuster.optimize_consolidation_threshold(project_id=1)

        assert optimization["primary_strategy"] == "best"
        assert 0.5 <= optimization["recommended_threshold"] <= 0.9
        assert "best" in optimization["rationale"]

    def test_optimize_threshold_no_data(self, adjuster):
        """Test consolidation threshold with no data."""
        optimization = adjuster.optimize_consolidation_threshold(project_id=999)

        assert optimization["primary_strategy"] is None
        assert optimization["recommended_threshold"] == 0.75


class TestPatternProfiling:
    """Test successful pattern profiling."""

    def test_profile_successful_patterns(self, adjuster):
        """Test identifying successful patterns."""
        # High performers (>75%)
        for _ in range(8):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="good_strategy", success=True
            )
        adjuster.track_strategy_performance(
            project_id=1, encoding_strategy="good_strategy", success=False
        )

        # Low performers (<40%)
        for _ in range(3):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="bad_strategy", success=True
            )
        for _ in range(7):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="bad_strategy", success=False
            )

        patterns = adjuster.profile_successful_patterns(project_id=1)

        assert patterns["most_effective"] is not None
        assert "good_strategy" in patterns["high_performers"]
        assert "bad_strategy" in patterns["low_performers"]
        assert len(patterns["recommendations"]) > 0

    def test_profile_empty_project(self, adjuster):
        """Test pattern profiling on empty project."""
        patterns = adjuster.profile_successful_patterns(project_id=999)

        assert patterns["most_effective"] is None
        assert patterns["high_performers"] == []
        assert patterns["low_performers"] == []


class TestStrategyRecommendations:
    """Test strategy change recommendations."""

    def test_recommend_high_effectiveness_strategy(self, adjuster):
        """Test recommendation for high-effectiveness strategy."""
        # Create a highly effective strategy
        for _ in range(85):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="excellent", success=True
            )
        for _ in range(15):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="excellent", success=False
            )

        recommendations = adjuster.recommend_strategy_changes(project_id=1)

        # Should recommend increasing use
        increase_recs = [r for r in recommendations if r["action"] == "increase_use"]
        assert len(increase_recs) > 0

    def test_recommend_low_effectiveness_strategy(self, adjuster):
        """Test recommendation for low-effectiveness strategy."""
        # Create a poorly effective strategy (many trials)
        for _ in range(3):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="poor", success=True
            )
        for _ in range(17):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="poor", success=False
            )

        recommendations = adjuster.recommend_strategy_changes(project_id=1)

        # Should recommend decreasing use
        decrease_recs = [r for r in recommendations if r["action"] == "decrease_use"]
        assert len(decrease_recs) > 0

    def test_recommendations_sorted_by_priority(self, adjuster):
        """Test recommendations are sorted by priority."""
        recommendations = adjuster.recommend_strategy_changes(project_id=1)

        # Verify recommendations are sorted by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        priorities = [priority_order.get(r["priority"], 3) for r in recommendations]
        assert priorities == sorted(priorities)


class TestPerformanceTrending:
    """Test performance trend analysis."""

    def test_strategy_performance_over_time(self, adjuster):
        """Test strategy performance trending."""
        # Track strategy performance - 50% = neutral/stable
        for _ in range(5):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="trending", success=True
            )
        for _ in range(5):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="trending", success=False
            )

        trend = adjuster.get_strategy_performance_over_time(
            project_id=1, encoding_strategy="trending"
        )

        assert trend["current_performance"] == 0.5
        assert trend["trend"] == "stable"
        assert "Monitor and compare" in trend["recommendation"]

    def test_improving_trend(self, adjuster):
        """Test identifying improving trend."""
        # High effectiveness strategy
        for _ in range(8):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="improving", success=True
            )
        for _ in range(2):
            adjuster.track_strategy_performance(
                project_id=1, encoding_strategy="improving", success=False
            )

        trend = adjuster.get_strategy_performance_over_time(
            project_id=1, encoding_strategy="improving"
        )

        assert trend["trend"] == "improving"


class TestComprehensiveReport:
    """Test comprehensive learning rate report generation."""

    def test_learning_rate_report(self, adjuster):
        """Test generating comprehensive report."""
        # Set up multiple strategies
        for i in range(3):
            strategy = f"strategy_{i}"
            success_rate = 0.9 - (i * 0.2)  # 90%, 70%, 50%
            successes = int(success_rate * 10)

            for _ in range(successes):
                adjuster.track_strategy_performance(
                    project_id=1, encoding_strategy=strategy, success=True
                )
            for _ in range(10 - successes):
                adjuster.track_strategy_performance(
                    project_id=1, encoding_strategy=strategy, success=False
                )

        report = adjuster.get_learning_rate_report(project_id=1)

        assert "strategy_rankings" in report
        assert "top_performer" in report
        assert "consolidation_recommendation" in report
        assert "pattern_analysis" in report
        assert "recommended_changes" in report
        assert "summary" in report
        assert len(report["strategy_rankings"]) == 3
        assert report["top_performer"]["strategy"] == "strategy_0"
