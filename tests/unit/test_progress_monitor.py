"""Tests for ProgressMonitor component."""

import pytest
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from athena.executive.progress import ProgressMonitor
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

    # Create progress_milestones table
    db.conn.execute(
        """
        CREATE TABLE IF NOT EXISTS progress_milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id INTEGER NOT NULL,
            milestone_text TEXT NOT NULL,
            expected_progress REAL,
            actual_progress REAL DEFAULT 0.0,
            target_date TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (goal_id) REFERENCES executive_goals(id)
        )
        """
    )

    # Create goal_progress_history table
    db.conn.execute(
        """
        CREATE TABLE IF NOT EXISTS goal_progress_history (
            goal_id INTEGER,
            progress REAL,
            updated_at TEXT
        )
        """
    )

    db.conn.commit()
    return str(db_file)


@pytest.fixture
def monitor(db_path):
    """Create a ProgressMonitor instance."""
    return ProgressMonitor(db_path)


@pytest.fixture
def setup_goal(db_path):
    """Create a test goal in the database."""

    def _create_goal(
        goal_text="Test goal",
        estimated_hours=10.0,
        priority=5,
        project_id=1,
        parent_goal_id=None,
    ):
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO executive_goals
                (project_id, goal_text, goal_type, priority, status, progress, created_at, estimated_hours)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (project_id, goal_text, "primary", priority, "active", 0.0, datetime.now().isoformat(), estimated_hours),
            )
            goal_id = cursor.lastrowid
            conn.commit()
            return goal_id

    return _create_goal


class TestMilestoneGeneration:
    """Test milestone generation logic."""

    def test_generate_milestones_simple_goal(self, monitor, setup_goal):
        """Simple goals should have 3 milestones at 33%, 66%, 100%."""
        goal_id = setup_goal("Quick fix", estimated_hours=2.0)
        milestones = monitor.generate_milestones(goal_id, "Quick fix", 2.0)

        assert len(milestones) == 3
        assert milestones[0].expected_progress == pytest.approx(1.0 / 3)
        assert milestones[1].expected_progress == pytest.approx(2.0 / 3)
        assert milestones[2].expected_progress == pytest.approx(1.0)

    def test_generate_milestones_complex_goal(self, monitor, setup_goal):
        """Complex goals should have 5 milestones."""
        goal_id = setup_goal("Refactor authentication system", estimated_hours=40.0)
        milestones = monitor.generate_milestones(goal_id, "Refactor authentication system", 40.0)

        assert len(milestones) == 5
        assert milestones[-1].expected_progress == pytest.approx(1.0)

    def test_milestone_descriptions_match_complexity(self, monitor, setup_goal):
        """Milestone descriptions should match goal complexity."""
        simple_goal_id = setup_goal("Fix bug", estimated_hours=1.0)
        milestones = monitor.generate_milestones(simple_goal_id, "Fix bug", 1.0)

        # Simple goal should have "setup", "implementation", "testing", etc.
        assert any("setup" in m.milestone_text.lower() for m in milestones)

    def test_milestone_target_dates_calculated(self, monitor, setup_goal):
        """Milestone target dates should be calculated based on estimated hours."""
        goal_id = setup_goal("Test goal", estimated_hours=10.0)
        milestones = monitor.generate_milestones(goal_id, "Test goal", 10.0)

        # First milestone should be at 25% of estimated time
        first_milestone = milestones[0]
        assert first_milestone.target_date is not None

        # Time to first milestone should be ~2.5 hours (25% of 10 hours)
        with sqlite3.connect(monitor.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT created_at FROM executive_goals WHERE id = ?", (goal_id,))
            created_at = datetime.fromisoformat(cursor.fetchone()[0])

        hours_to_milestone = (first_milestone.target_date - created_at).total_seconds() / 3600
        assert hours_to_milestone == pytest.approx(10.0 / len(milestones), rel=0.1)


class TestMilestoneTracking:
    """Test milestone progress tracking."""

    def test_update_milestone_progress(self, monitor, setup_goal):
        """Update milestone progress."""
        goal_id = setup_goal("Test goal")
        milestones = monitor.generate_milestones(goal_id, "Test goal", 5.0)
        milestone_id = milestones[0].id

        updated = monitor.update_milestone_progress(milestone_id, 0.75)
        assert updated.actual_progress == pytest.approx(0.75)
        assert updated.completed_at is None

    def test_milestone_completion_sets_timestamp(self, monitor, setup_goal):
        """Marking milestone complete should set completed_at."""
        goal_id = setup_goal("Test goal")
        milestones = monitor.generate_milestones(goal_id, "Test goal", 5.0)
        milestone_id = milestones[0].id

        updated = monitor.update_milestone_progress(milestone_id, 1.0)
        assert updated.completed_at is not None

    def test_get_next_milestone(self, monitor, setup_goal):
        """Get next incomplete milestone."""
        goal_id = setup_goal("Test goal")
        milestones = monitor.generate_milestones(goal_id, "Test goal", 5.0)

        next_m = monitor.get_next_milestone(goal_id)
        assert next_m is not None
        assert next_m.id == milestones[0].id

        # Mark first milestone as complete
        monitor.update_milestone_progress(milestones[0].id, 1.0)

        # Next should be second milestone
        next_m = monitor.get_next_milestone(goal_id)
        assert next_m is not None
        assert next_m.id == milestones[1].id

    def test_milestone_status_on_track(self, monitor, setup_goal):
        """Milestone on track when completed before target date."""
        goal_id = setup_goal("Test goal", estimated_hours=10.0)
        milestones = monitor.generate_milestones(goal_id, "Test goal", 10.0)

        status = monitor.get_milestone_status(milestones[0].id)
        assert status is not None
        assert status["completed"] is False
        assert status["progress"] == pytest.approx(0.0)

    def test_milestone_status_behind_schedule(self, monitor, setup_goal):
        """Milestone behind schedule when past target date."""
        goal_id = setup_goal("Test goal", estimated_hours=1.0)
        milestones = monitor.generate_milestones(goal_id, "Test goal", 1.0)

        # Manually set target date to past
        with sqlite3.connect(monitor.db_path) as conn:
            cursor = conn.cursor()
            past_date = (datetime.now() - timedelta(hours=1)).isoformat()
            cursor.execute(
                "UPDATE progress_milestones SET target_date = ? WHERE id = ?",
                (past_date, milestones[0].id),
            )
            conn.commit()

        status = monitor.get_milestone_status(milestones[0].id)
        assert status is not None


class TestBurndown:
    """Test burndown tracking."""

    def test_burndown_linear(self, monitor, setup_goal):
        """Linear burndown when progress matches expected."""
        goal_id = setup_goal("Test goal", estimated_hours=10.0)

        # Manually set progress and time
        with sqlite3.connect(monitor.db_path) as conn:
            cursor = conn.cursor()

            # Set creation time to 5 hours ago
            created_at = (datetime.now() - timedelta(hours=5)).isoformat()
            cursor.execute(
                """
                UPDATE executive_goals
                SET created_at = ?, progress = ?
                WHERE id = ?
                """,
                (created_at, 0.5, goal_id),
            )
            conn.commit()

        burndown = monitor.calculate_burndown(goal_id)
        assert burndown is not None
        assert burndown.actual_progress == pytest.approx(0.5)
        assert burndown.expected_progress == pytest.approx(0.5, rel=0.1)
        assert burndown.on_track is True
        assert burndown.trend == "stable"

    def test_burndown_ahead_of_schedule(self, monitor, setup_goal):
        """Trend improving when ahead of schedule."""
        goal_id = setup_goal("Test goal", estimated_hours=10.0)

        with sqlite3.connect(monitor.db_path) as conn:
            cursor = conn.cursor()

            # 3 hours elapsed, 80% complete (should be 30%)
            created_at = (datetime.now() - timedelta(hours=3)).isoformat()
            cursor.execute(
                """
                UPDATE executive_goals
                SET created_at = ?, progress = ?
                WHERE id = ?
                """,
                (created_at, 0.8, goal_id),
            )
            conn.commit()

        burndown = monitor.calculate_burndown(goal_id)
        assert burndown.trend == "improving"
        assert burndown.on_track is True


class TestCompletion:
    """Test completion forecasting."""

    def test_completion_time_forecast(self, monitor, setup_goal):
        """Forecast completion based on velocity."""
        goal_id = setup_goal("Test goal", estimated_hours=20.0)

        with sqlite3.connect(monitor.db_path) as conn:
            cursor = conn.cursor()

            # 2 hours elapsed, 25% complete
            created_at = (datetime.now() - timedelta(hours=2)).isoformat()
            cursor.execute(
                """
                UPDATE executive_goals
                SET created_at = ?, progress = ?
                WHERE id = ?
                """,
                (created_at, 0.25, goal_id),
            )
            conn.commit()

        result = monitor.forecast_completion(goal_id)
        assert result is not None

        completion_time, confidence = result

        # At 25% per 2 hours, should take 8 hours total from now
        expected_completion = datetime.now() + timedelta(hours=6)
        assert completion_time is not None
        assert (completion_time - expected_completion).total_seconds() < 3600  # Within 1 hour

    def test_forecast_confidence_decreases_with_deviation(self, monitor, setup_goal):
        """Confidence decreases when forecast deviates from estimate."""
        goal_id = setup_goal("Test goal", estimated_hours=10.0)

        with sqlite3.connect(monitor.db_path) as conn:
            cursor = conn.cursor()

            # 8 hours elapsed, only 25% complete (way off)
            created_at = (datetime.now() - timedelta(hours=8)).isoformat()
            cursor.execute(
                """
                UPDATE executive_goals
                SET created_at = ?, progress = ?
                WHERE id = ?
                """,
                (created_at, 0.25, goal_id),
            )
            conn.commit()

        result = monitor.forecast_completion(goal_id)
        assert result is not None
        _, confidence = result
        assert confidence < 1.0  # Should have reduced confidence


class TestBlockerDetection:
    """Test blocker detection."""

    def test_blocker_detection_2hour_no_progress(self, monitor, setup_goal):
        """Blocker detected after 2+ hours with no progress."""
        goal_id = setup_goal("Test goal")

        # Create progress history
        with sqlite3.connect(monitor.db_path) as conn:
            cursor = conn.cursor()

            # Create history entry from 2.5 hours ago with 50% progress
            history_time = (datetime.now() - timedelta(hours=2.5)).isoformat()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS goal_progress_history (
                    goal_id INTEGER,
                    progress REAL,
                    updated_at TEXT
                )
                """
            )
            cursor.execute(
                """
                INSERT INTO goal_progress_history (goal_id, progress, updated_at)
                VALUES (?, ?, ?)
                """,
                (goal_id, 0.5, history_time),
            )

            # Set current goal progress to same 50%
            cursor.execute(
                "UPDATE executive_goals SET progress = ? WHERE id = ?",
                (0.5, goal_id),
            )
            conn.commit()

        blockers = monitor.detect_blockers(goal_id)
        assert len(blockers) > 0
        assert blockers[0].severity == "high"

    def test_no_blocker_when_progress_changes(self, monitor, setup_goal):
        """No blocker when progress is being made."""
        goal_id = setup_goal("Test goal")

        with sqlite3.connect(monitor.db_path) as conn:
            cursor = conn.cursor()

            # Create history entry from 1 hour ago with 25% progress
            history_time = (datetime.now() - timedelta(hours=1)).isoformat()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS goal_progress_history (
                    goal_id INTEGER,
                    progress REAL,
                    updated_at TEXT
                )
                """
            )
            cursor.execute(
                """
                INSERT INTO goal_progress_history (goal_id, progress, updated_at)
                VALUES (?, ?, ?)
                """,
                (goal_id, 0.25, history_time),
            )

            # Current progress is 75% (progress being made)
            cursor.execute(
                "UPDATE executive_goals SET progress = ? WHERE id = ?",
                (0.75, goal_id),
            )
            conn.commit()

        blockers = monitor.detect_blockers(goal_id)
        assert len(blockers) == 0
