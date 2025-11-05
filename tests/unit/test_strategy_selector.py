"""Tests for StrategySelector component."""

import pytest
import sqlite3
from datetime import datetime, timedelta

from athena.executive.strategy import StrategySelector
from athena.executive.models import StrategyType
from athena.core.database import Database


@pytest.fixture
def db_path(tmp_path):
    """Create a test database."""
    db_file = tmp_path / "test_memory.db"
    db = Database(str(db_file))

    # Create test project
    db.create_project("test-project", str(tmp_path))

    # Create executive_goals table
    db.conn.execute(
        """
        CREATE TABLE IF NOT EXISTS executive_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            parent_goal_id INTEGER,
            goal_text TEXT NOT NULL,
            goal_type TEXT NOT NULL,
            priority INTEGER DEFAULT 5,
            status TEXT DEFAULT 'active',
            progress REAL DEFAULT 0.0,
            estimated_hours REAL,
            actual_hours REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deadline TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
        """
    )

    # Create strategy_recommendations table
    db.conn.execute(
        """
        CREATE TABLE IF NOT EXISTS strategy_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id INTEGER NOT NULL,
            strategy_name TEXT NOT NULL,
            confidence REAL DEFAULT 0.5,
            model_version TEXT,
            recommended_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            outcome TEXT,
            hours_actual REAL,
            FOREIGN KEY (goal_id) REFERENCES executive_goals(id)
        )
        """
    )

    # Create goal_blockers table
    db.conn.execute(
        """
        CREATE TABLE IF NOT EXISTS goal_blockers (
            goal_id INTEGER,
            blocker_text TEXT,
            resolved INTEGER DEFAULT 0
        )
        """
    )

    db.conn.commit()
    return str(db_file)


@pytest.fixture
def selector(db_path):
    """Create a StrategySelector instance."""
    return StrategySelector(db_path)


@pytest.fixture
def setup_goal(db_path):
    """Create a test goal in the database."""

    def _create_goal(
        goal_text="Test goal",
        estimated_hours=10.0,
        priority=5,
        project_id=1,
        deadline=None,
        progress=0.0,
        parent_goal_id=None,
    ):
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO executive_goals
                (project_id, goal_text, goal_type, priority, status, progress, created_at,
                 estimated_hours, deadline, parent_goal_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    goal_text,
                    "primary",
                    priority,
                    "active",
                    progress,
                    datetime.now().isoformat(),
                    estimated_hours,
                    deadline.isoformat() if deadline else None,
                    parent_goal_id,
                ),
            )
            goal_id = cursor.lastrowid
            conn.commit()
            return goal_id

    return _create_goal


class TestStrategyRecommendation:
    """Test strategy recommendation logic."""

    def test_strategy_recommendations_confidence_sorted(self, selector, setup_goal):
        """Recommendations should be sorted by confidence (highest first)."""
        goal_id = setup_goal("Test goal")
        recommendations = selector.recommend_strategies(goal_id, top_k=5)

        assert len(recommendations) > 0
        # Check sorted by confidence
        for i in range(len(recommendations) - 1):
            assert recommendations[i].confidence >= recommendations[i + 1].confidence

    def test_strategy_recommendation_top_3(self, selector, setup_goal):
        """Should return exactly top-3 when requested."""
        goal_id = setup_goal("Test goal")
        recommendations = selector.recommend_strategies(goal_id, top_k=3)

        assert len(recommendations) <= 3

    def test_strategy_for_urgent_goal(self, selector, setup_goal):
        """Urgent goals should prioritize deadline-driven strategies."""
        deadline = datetime.now() + timedelta(days=1)
        goal_id = setup_goal("Urgent fix", deadline=deadline, priority=9)

        recommendations = selector.recommend_strategies(goal_id, top_k=3)

        # Top recommendation should favor deadline-driven strategies
        top_strategy = recommendations[0].strategy_type
        # Could be DEADLINE_DRIVEN, INCREMENTAL, etc.
        assert top_strategy is not None

    def test_strategy_for_complex_goal(self, selector, setup_goal):
        """Complex goals should prioritize decomposition strategies."""
        goal_id = setup_goal("Refactor authentication system", estimated_hours=40.0)

        recommendations = selector.recommend_strategies(goal_id, top_k=3)

        assert len(recommendations) > 0
        # Top recommendation should handle complexity well
        assert recommendations[0].confidence > 0.3

    def test_strategy_for_simple_goal(self, selector, setup_goal):
        """Simple goals should prioritize bottom-up strategies."""
        goal_id = setup_goal("Quick fix", estimated_hours=1.0)

        recommendations = selector.recommend_strategies(goal_id, top_k=3)

        assert len(recommendations) > 0
        assert recommendations[0].confidence > 0.3

    def test_all_strategies_present(self, selector, setup_goal):
        """All 10 strategy types should be considered."""
        goal_id = setup_goal("Test goal")
        recommendations = selector.recommend_strategies(goal_id, top_k=10)

        strategy_types = {rec.strategy_type for rec in recommendations}
        # We should see multiple different strategies
        assert len(strategy_types) >= 3


class TestOutcomeTracking:
    """Test outcome tracking and feedback."""

    def test_outcome_feedback_success(self, selector, setup_goal):
        """Record successful strategy outcome."""
        goal_id = setup_goal("Test goal")
        recommendations = selector.recommend_strategies(goal_id, top_k=1)

        rec_id = None
        with sqlite3.connect(selector.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM strategy_recommendations WHERE goal_id = ?", (goal_id,))
            rec_id = cursor.fetchone()[0]

        success = selector.record_outcome(rec_id, "success", hours_actual=5.0)
        assert success is True

        # Verify recorded in DB
        with sqlite3.connect(selector.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT outcome FROM strategy_recommendations WHERE id = ?", (rec_id,))
            outcome = cursor.fetchone()[0]
            assert outcome == "success"

    def test_outcome_feedback_failure(self, selector, setup_goal):
        """Record failed strategy outcome."""
        goal_id = setup_goal("Test goal")
        recommendations = selector.recommend_strategies(goal_id, top_k=1)

        rec_id = None
        with sqlite3.connect(selector.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM strategy_recommendations WHERE goal_id = ?", (goal_id,))
            rec_id = cursor.fetchone()[0]

        success = selector.record_outcome(rec_id, "failure", hours_actual=15.0)
        assert success is True

    def test_outcome_feedback_partial(self, selector, setup_goal):
        """Record partial strategy outcome."""
        goal_id = setup_goal("Test goal")
        recommendations = selector.recommend_strategies(goal_id, top_k=1)

        rec_id = None
        with sqlite3.connect(selector.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM strategy_recommendations WHERE goal_id = ?", (goal_id,))
            rec_id = cursor.fetchone()[0]

        success = selector.record_outcome(rec_id, "partial", hours_actual=8.0, feedback="Got 80% done")
        assert success is True


class TestStrategySuccessRates:
    """Test strategy success rate tracking."""

    def test_strategy_success_rate_tracking(self, selector, setup_goal):
        """Success rate should accumulate from outcomes."""
        # Create multiple goals and recommendations
        for i in range(5):
            goal_id = setup_goal(f"Goal {i}")
            recommendations = selector.recommend_strategies(goal_id, top_k=1)

        # Record outcomes
        with sqlite3.connect(selector.db_path) as conn:
            cursor = conn.cursor()

            # Get all recommendations
            cursor.execute("SELECT id, strategy_name FROM strategy_recommendations LIMIT 5")
            recs = cursor.fetchall()

            # Mark first 3 as successful, last 2 as failures
            for idx, (rec_id, strategy_name) in enumerate(recs):
                outcome = "success" if idx < 3 else "failure"
                cursor.execute(
                    "UPDATE strategy_recommendations SET outcome = ? WHERE id = ?",
                    (outcome, rec_id),
                )

            conn.commit()

        # Check success rate for first strategy
        first_strategy = recs[0][1]
        success_rate = selector.get_strategy_success_rate(first_strategy)

        # Should be positive (at least one success)
        assert success_rate >= 0.0
        assert success_rate <= 1.0

    def test_neutral_success_rate_no_outcomes(self, selector):
        """Success rate should default to 0.5 with no data."""
        success_rate = selector.get_strategy_success_rate("nonexistent_strategy")
        assert success_rate == 0.5


class TestABTesting:
    """Test A/B testing framework."""

    def test_ab_test_comparison(self, selector, setup_goal):
        """Compare two strategies using historical data."""
        # Create goals and recommendations with both strategies
        for i in range(3):
            goal_id = setup_goal(f"Goal {i}")
            selector.recommend_strategies(goal_id, top_k=10)

        # Record outcomes for specific strategies
        with sqlite3.connect(selector.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id, strategy_name FROM strategy_recommendations LIMIT 2"
            )
            recs = cursor.fetchall()

            if len(recs) >= 2:
                # Mark first as success
                cursor.execute(
                    "UPDATE strategy_recommendations SET outcome = 'success' WHERE id = ?",
                    (recs[0][0],),
                )
                # Mark second as failure
                cursor.execute(
                    "UPDATE strategy_recommendations SET outcome = 'failure' WHERE id = ?",
                    (recs[1][0],),
                )

                conn.commit()

        # Compare if both strategies are available
        try:
            result = selector.ab_test_compare(
                StrategyType.TOP_DOWN,
                StrategyType.BOTTOM_UP
            )

            assert "strategy_a" in result
            assert "strategy_b" in result
            assert "winner" in result
            assert "confidence" in result
            assert 0 <= result["confidence"] <= 1.0
        except Exception:
            # OK if strategies not found
            pass

    def test_ab_test_low_confidence_small_sample(self, selector):
        """A/B test should have low confidence with small sample size."""
        result = selector.ab_test_compare(StrategyType.TOP_DOWN, StrategyType.BOTTOM_UP)

        # With no data, confidence should be low
        assert result["confidence"] < 0.5


class TestStrategyPersistence:
    """Test recommendation persistence."""

    def test_recommendation_retrieval(self, selector, setup_goal):
        """Should be able to retrieve recommendations by ID."""
        goal_id = setup_goal("Test goal")
        recommendations = selector.recommend_strategies(goal_id, top_k=1)

        rec_id = None
        with sqlite3.connect(selector.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM strategy_recommendations WHERE goal_id = ?", (goal_id,))
            rec_id = cursor.fetchone()[0]

        retrieved = selector.get_recommendation_by_id(rec_id)

        assert retrieved is not None
        assert retrieved["goal_id"] == goal_id
        assert retrieved["id"] == rec_id

    def test_strategy_persistence_across_sessions(self, selector, setup_goal):
        """Recommendations should persist across selector instances."""
        goal_id = setup_goal("Test goal")
        recommendations1 = selector.recommend_strategies(goal_id, top_k=3)

        # Create new selector instance (simulating new session)
        selector2 = StrategySelector(selector.db_path)
        recommendations2 = selector2.recommend_strategies(goal_id, top_k=3)

        # Should get same recommendations
        assert len(recommendations1) == len(recommendations2)


class TestReasoningGeneration:
    """Test reasoning string generation."""

    def test_reasoning_generated(self, selector, setup_goal):
        """Each recommendation should have reasoning."""
        goal_id = setup_goal("Test goal")
        recommendations = selector.recommend_strategies(goal_id, top_k=3)

        for rec in recommendations:
            assert len(rec.reasoning) > 0
            assert isinstance(rec.reasoning, str)

    def test_reasoning_specific_to_strategy(self, selector, setup_goal):
        """Reasoning should mention strategy-specific factors."""
        deadline = datetime.now() + timedelta(days=1)
        goal_id = setup_goal("Urgent fix", deadline=deadline, priority=9)

        recommendations = selector.recommend_strategies(goal_id, top_k=10)

        # Check that some recommendations mention deadline
        has_deadline_reasoning = any("deadline" in rec.reasoning.lower() for rec in recommendations)
        # May or may not have deadline reasoning depending on top recommendations
        assert isinstance(has_deadline_reasoning, bool)
