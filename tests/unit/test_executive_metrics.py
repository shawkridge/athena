"""Tests for ExecutiveMetrics component."""

import pytest
import sqlite3
from datetime import datetime, timedelta, date

from athena.executive.metrics import ExecutiveMetrics
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

    # Create task_switches table
    db.conn.execute(
        """
        CREATE TABLE IF NOT EXISTS task_switches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            from_goal_id INTEGER,
            to_goal_id INTEGER,
            switch_cost_ms INTEGER,
            reason TEXT,
            switched_at TIMESTAMP,
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

    # Create executive_metrics table
    db.conn.execute(
        """
        CREATE TABLE IF NOT EXISTS executive_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            metric_date DATE DEFAULT CURRENT_DATE,
            total_goals INTEGER DEFAULT 0,
            completed_goals INTEGER DEFAULT 0,
            abandoned_goals INTEGER DEFAULT 0,
            average_switch_cost_ms REAL,
            total_switch_overhead_ms INTEGER,
            average_goal_completion_hours REAL,
            success_rate REAL,
            efficiency_score REAL,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
        """
    )

    db.conn.commit()
    return str(db_file)


@pytest.fixture
def metrics(db_path):
    """Create an ExecutiveMetrics instance."""
    return ExecutiveMetrics(db_path)


@pytest.fixture
def setup_goal(db_path):
    """Create a test goal."""

    def _create_goal(status="active", actual_hours=None):
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO executive_goals
                (project_id, goal_text, goal_type, status, actual_hours, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (1, "Test goal", "primary", status, actual_hours, datetime.now().isoformat()),
            )
            goal_id = cursor.lastrowid
            conn.commit()
            return goal_id

    return _create_goal


class TestSuccessRateCalculation:
    """Test success rate calculation."""

    def test_calculate_success_rate(self, metrics, setup_goal):
        """Success rate should be completed / (completed + abandoned + failed)."""
        # Create 5 completed, 2 abandoned, 1 failed goals
        for _ in range(5):
            setup_goal(status="completed")
        for _ in range(2):
            setup_goal(status="abandoned")
        for _ in range(1):
            setup_goal(status="failed")

        snapshot = metrics.calculate_metrics(project_id=1)

        assert snapshot.completed_goals == 5
        assert snapshot.abandoned_goals == 2
        assert snapshot.failed_goals == 1
        assert snapshot.success_rate == pytest.approx(5 / 8)  # 5 out of 8 terminal goals

    def test_success_rate_all_abandoned(self, metrics, setup_goal):
        """Success rate with all abandoned goals should be 0."""
        for _ in range(5):
            setup_goal(status="abandoned")

        snapshot = metrics.calculate_metrics(project_id=1)

        assert snapshot.success_rate == pytest.approx(0.0)

    def test_success_rate_all_completed(self, metrics, setup_goal):
        """Success rate with all completed goals should be 1.0."""
        for _ in range(5):
            setup_goal(status="completed")

        snapshot = metrics.calculate_metrics(project_id=1)

        assert snapshot.success_rate == pytest.approx(1.0)


class TestSwitchOverheadCalculation:
    """Test task switching overhead calculation."""

    def test_calculate_average_switch_overhead(self, metrics, db_path):
        """Average switch cost should be calculated correctly."""
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Create 3 task switches with costs 5ms, 10ms, 15ms
            for cost in [5, 10, 15]:
                cursor.execute(
                    """
                    INSERT INTO task_switches
                    (project_id, from_goal_id, to_goal_id, switch_cost_ms, reason, switched_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (1, 1, 2, cost, "test", datetime.now().isoformat()),
                )
            conn.commit()

        snapshot = metrics.calculate_metrics(project_id=1)

        assert snapshot.average_switch_cost_ms == pytest.approx(10.0)  # (5+10+15)/3
        assert snapshot.total_switch_overhead_ms == 30  # 5+10+15

    def test_zero_switches(self, metrics):
        """With no switches, overhead should be 0."""
        snapshot = metrics.calculate_metrics(project_id=1)

        assert snapshot.average_switch_cost_ms == 0.0
        assert snapshot.total_switch_overhead_ms == 0


class TestCompletionTimeDistribution:
    """Test goal completion time analysis."""

    def test_calculate_completion_time_distribution(self, metrics, setup_goal):
        """Completion times should be averaged."""
        # Create completed goals with different actual hours
        with sqlite3.connect(metrics.db_path) as conn:
            cursor = conn.cursor()

            for hours in [2.0, 3.0, 5.0]:
                cursor.execute(
                    """
                    INSERT INTO executive_goals
                    (project_id, goal_text, goal_type, status, actual_hours, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (1, f"Goal {hours}h", "primary", "completed", hours, datetime.now().isoformat()),
                )
            conn.commit()

        snapshot = metrics.calculate_metrics(project_id=1)

        assert snapshot.average_goal_completion_hours == pytest.approx((2.0 + 3.0 + 5.0) / 3)


class TestEfficiencyScore:
    """Test efficiency score calculation."""

    def test_calculate_efficiency_score(self, metrics, setup_goal):
        """Efficiency score should reflect completion rate and switch overhead."""
        # Create 8 completed, 2 abandoned goals
        for _ in range(8):
            setup_goal(status="completed")
        for _ in range(2):
            setup_goal(status="abandoned")

        snapshot = metrics.calculate_metrics(project_id=1)

        # Efficiency based on 80% completion rate (8 out of 10)
        assert 0 <= snapshot.efficiency_score <= 100
        assert snapshot.efficiency_score > 50  # With 80% completion, should be good

    def test_efficiency_score_zero_goals(self, metrics):
        """With no goals, efficiency should be 100 (perfect)."""
        snapshot = metrics.calculate_metrics(project_id=1)

        assert snapshot.efficiency_score == 100.0

    def test_efficiency_score_low_completion(self, metrics, setup_goal):
        """Low completion rate should lower efficiency."""
        for _ in range(1):
            setup_goal(status="completed")
        for _ in range(9):
            setup_goal(status="abandoned")

        snapshot = metrics.calculate_metrics(project_id=1)

        # Efficiency based on 10% completion rate (1 out of 10)
        assert snapshot.efficiency_score < 20


class TestMetricsTrend:
    """Test metrics tracking over time."""

    def test_metrics_over_time(self, metrics, setup_goal):
        """Metrics should be recorded and retrievable over time."""
        # Create initial goals and get snapshot
        for _ in range(3):
            setup_goal(status="completed")

        snapshot1 = metrics.calculate_metrics(project_id=1)

        # Create trend
        trend = metrics.get_metrics_trend(project_id=1, days=30)

        assert len(trend) >= 1
        assert trend[0].completed_goals == 3

    def test_strategy_effectiveness(self, metrics, db_path):
        """Should calculate strategy effectiveness from historical data."""
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Create a goal
            cursor.execute(
                """
                INSERT INTO executive_goals
                (project_id, goal_text, goal_type, status, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (1, "Test goal", "primary", "completed", datetime.now().isoformat()),
            )
            goal_id = cursor.lastrowid

            # Create recommendations with outcomes
            for outcome, hours in [
                ("success", 3.0),
                ("success", 2.5),
                ("failure", 5.0),
            ]:
                cursor.execute(
                    """
                    INSERT INTO strategy_recommendations
                    (goal_id, strategy_name, outcome, hours_actual)
                    VALUES (?, ?, ?, ?)
                    """,
                    (goal_id, "top_down", outcome, hours),
                )
            conn.commit()

        effectiveness = metrics.calculate_strategy_effectiveness(project_id=1, strategy_name="top_down")

        assert effectiveness is not None
        assert effectiveness["strategy"] == "top_down"
        assert effectiveness["total_used"] == 3
        assert effectiveness["success_count"] == 2
        assert effectiveness["failure_count"] == 1
        assert effectiveness["success_rate"] == pytest.approx(2 / 3)


class TestEfficiencyScoreRetrieval:
    """Test efficiency score retrieval."""

    def test_get_efficiency_score(self, metrics, setup_goal):
        """Should retrieve most recent efficiency score."""
        for _ in range(5):
            setup_goal(status="completed")

        metrics.calculate_metrics(project_id=1)
        score = metrics.get_efficiency_score(project_id=1)

        assert 0 <= score <= 100
        assert score > 50  # With all completed, should be good
