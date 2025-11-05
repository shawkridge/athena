"""Phase 2: Milestone-Based Progress Tracking Integration Tests

Tests the milestone functionality:
1. Creating tasks with milestones
2. Tracking milestone progress
3. Detecting milestone delays
4. Auto-triggering replanning on delays
"""

import pytest
from pathlib import Path

from athena.core.database import Database
from athena.prospective.models import ProspectiveTask, TaskPhase, TaskPriority, TaskStatus
from athena.prospective.milestones import Milestone, CheckpointType, MilestoneProgress
from athena.prospective.store import ProspectiveStore
from athena.integration.milestone_tracker import MilestoneTracker


@pytest.fixture
def temp_db(tmp_path: Path) -> Database:
    """Create temporary database for testing."""
    db = Database(tmp_path / "test.db")
    return db


@pytest.fixture
def prospective_store(temp_db: Database) -> ProspectiveStore:
    """Create prospective store."""
    return ProspectiveStore(temp_db)


@pytest.fixture
def milestone_tracker(temp_db: Database) -> MilestoneTracker:
    """Create milestone tracker."""
    return MilestoneTracker(temp_db)


class TestMilestoneModels:
    """Test milestone data models."""

    def test_create_milestone(self):
        """Test creating a milestone."""
        milestone = Milestone(
            name="Implement core functionality",
            description="Implement the main feature",
            order=1,
            completion_percentage=0.25,
            estimated_minutes=30,
            checkpoint_type=CheckpointType.FEATURE_COMPLETE,
            status="pending",
        )

        assert milestone.name == "Implement core functionality"
        assert milestone.order == 1
        assert milestone.completion_percentage == 0.25
        assert milestone.is_delayed is False

    def test_milestone_percentages(self):
        """Test milestone completion percentages."""
        milestones = [
            Milestone(
                name=f"Milestone {i}",
                order=i,
                completion_percentage=0.25,
                estimated_minutes=30,
                status="pending",
            )
            for i in range(1, 5)
        ]

        total = sum(m.completion_percentage for m in milestones)
        assert total == 1.0  # Should sum to 100%

    def test_milestone_with_checkpoint_types(self):
        """Test different checkpoint types."""
        checkpoint_types = [
            CheckpointType.TEST_PASS,
            CheckpointType.REVIEW_APPROVED,
            CheckpointType.FEATURE_COMPLETE,
            CheckpointType.DOCUMENTATION_COMPLETE,
        ]

        for checkpoint_type in checkpoint_types:
            milestone = Milestone(
                name=f"Milestone with {checkpoint_type}",
                order=1,
                completion_percentage=0.25,
                estimated_minutes=30,
                checkpoint_type=checkpoint_type,
                status="pending",
            )
            assert milestone.checkpoint_type == checkpoint_type


class TestMilestoneTracker:
    """Test milestone tracking functionality."""

    def test_calculate_overall_progress(self, milestone_tracker):
        """Test calculating overall progress from milestones."""
        milestones = [
            Milestone(
                name="Milestone 1",
                order=1,
                completion_percentage=0.25,
                estimated_minutes=30,
                status="completed",
            ),
            Milestone(
                name="Milestone 2",
                order=2,
                completion_percentage=0.25,
                estimated_minutes=30,
                status="completed",
            ),
            Milestone(
                name="Milestone 3",
                order=3,
                completion_percentage=0.25,
                estimated_minutes=30,
                status="in_progress",
            ),
            Milestone(
                name="Milestone 4",
                order=4,
                completion_percentage=0.25,
                estimated_minutes=30,
                status="pending",
            ),
        ]

        progress = milestone_tracker.calculate_overall_progress(milestones)
        assert progress == 50.0  # 2 out of 4 milestones completed

    def test_estimate_remaining_time(self, milestone_tracker):
        """Test estimating remaining time."""
        milestones = [
            Milestone(
                name="Milestone 1",
                order=1,
                completion_percentage=0.25,
                estimated_minutes=30,
                status="completed",
            ),
            Milestone(
                name="Milestone 2",
                order=2,
                completion_percentage=0.25,
                estimated_minutes=30,
                status="in_progress",
            ),
            Milestone(
                name="Milestone 3",
                order=3,
                completion_percentage=0.25,
                estimated_minutes=30,
                status="pending",
            ),
            Milestone(
                name="Milestone 4",
                order=4,
                completion_percentage=0.25,
                estimated_minutes=30,
                status="pending",
            ),
        ]

        remaining = milestone_tracker.estimate_remaining_time(milestones)
        # Milestone 2 (in progress), 3, and 4 remaining
        assert remaining == 90.0  # 3 * 30 minutes

    def test_get_milestone_summary(self, milestone_tracker):
        """Test getting milestone summary."""
        milestones = [
            Milestone(
                name="Milestone 1",
                order=1,
                completion_percentage=0.25,
                estimated_minutes=30,
                status="completed",
                actual_minutes=35,
                is_delayed=True,
                delay_percent=16.7,
            ),
            Milestone(
                name="Milestone 2",
                order=2,
                completion_percentage=0.25,
                estimated_minutes=30,
                status="in_progress",
                actual_minutes=25,
            ),
            Milestone(
                name="Milestone 3",
                order=3,
                completion_percentage=0.25,
                estimated_minutes=30,
                status="pending",
            ),
            Milestone(
                name="Milestone 4",
                order=4,
                completion_percentage=0.25,
                estimated_minutes=30,
                status="pending",
            ),
        ]

        summary = milestone_tracker.get_milestone_summary(milestones)

        assert summary["total_milestones"] == 4
        assert summary["completed"] == 1
        assert summary["in_progress"] == 1
        assert summary["pending"] == 2
        assert summary["total_estimated_minutes"] == 120
        assert summary["total_actual_minutes"] == 60.0
        assert summary["delayed_count"] == 1
        assert summary["overall_progress_percent"] == 25.0

    def test_delay_detection(self, milestone_tracker):
        """Test detecting milestone delays."""
        milestone = Milestone(
            name="Test milestone",
            order=1,
            completion_percentage=0.25,
            estimated_minutes=30,
            status="pending",
        )

        # Test on-time
        result = asyncio.run(
            milestone_tracker.detect_milestone_delay(
                task_id=1, milestone=milestone, actual_minutes=25
            )
        )
        assert result["is_delayed"] is False

        # Test slight delay
        result = asyncio.run(
            milestone_tracker.detect_milestone_delay(
                task_id=1, milestone=milestone, actual_minutes=40
            )
        )
        assert result["is_delayed"] is True
        assert result["delay_percent"] == pytest.approx(33.3, rel=1)
        assert result["should_trigger_replan"] is False

        # Test significant delay (>50%)
        result = asyncio.run(
            milestone_tracker.detect_milestone_delay(
                task_id=1, milestone=milestone, actual_minutes=50
            )
        )
        assert result["is_delayed"] is True
        assert result["delay_percent"] == pytest.approx(66.7, rel=1)
        assert result["should_trigger_replan"] is True


class TestMilestoneWorkflow:
    """Test complete milestone workflow."""

    def test_full_milestone_workflow(self, prospective_store):
        """Test creating and tracking milestones through task workflow."""
        # 1. Create task
        task = ProspectiveTask(
            project_id=1,
            content="Implement feature with milestones",
            active_form="Implementing feature",
            priority=TaskPriority.HIGH,
            phase=TaskPhase.PLANNING,
        )
        task_id = prospective_store.create_task(task)

        # 2. Create milestones
        milestones = [
            Milestone(
                name="Design",
                order=1,
                completion_percentage=0.25,
                estimated_minutes=30,
                checkpoint_type=CheckpointType.REVIEW_APPROVED,
                status="pending",
            ),
            Milestone(
                name="Implementation",
                order=2,
                completion_percentage=0.50,
                estimated_minutes=60,
                checkpoint_type=CheckpointType.FEATURE_COMPLETE,
                status="pending",
            ),
            Milestone(
                name="Testing",
                order=3,
                completion_percentage=0.15,
                estimated_minutes=20,
                checkpoint_type=CheckpointType.TEST_PASS,
                status="pending",
            ),
            Milestone(
                name="Documentation",
                order=4,
                completion_percentage=0.10,
                estimated_minutes=15,
                checkpoint_type=CheckpointType.DOCUMENTATION_COMPLETE,
                status="pending",
            ),
        ]

        # Verify percentages sum to 100%
        total_pct = sum(m.completion_percentage for m in milestones)
        assert total_pct == 1.0

        # 3. Mark milestones as they complete
        milestone_tracker = MilestoneTracker(prospective_store.db)

        # Design phase complete
        milestones[0].status = "completed"
        milestones[1].status = "in_progress"

        progress = milestone_tracker.calculate_overall_progress(milestones)
        assert progress == 25.0

        # Implementation and testing complete
        milestones[1].status = "completed"
        milestones[2].status = "completed"
        milestones[3].status = "in_progress"

        progress = milestone_tracker.calculate_overall_progress(milestones)
        assert progress == 90.0

        # Final milestone complete
        milestones[3].status = "completed"

        progress = milestone_tracker.calculate_overall_progress(milestones)
        assert progress == 100.0

        # Summary should show all complete
        summary = milestone_tracker.get_milestone_summary(milestones)
        assert summary["completed"] == 4
        assert summary["pending"] == 0
        assert summary["overall_progress_percent"] == 100.0


# Import asyncio for async test support
import asyncio
