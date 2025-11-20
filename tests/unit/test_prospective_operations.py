"""Unit tests for prospective memory operations."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from athena.prospective.operations import ProspectiveOperations
from athena.prospective.models import ProspectiveTask

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db():
    """Create a mock database."""
    return MagicMock()


@pytest.fixture
def mock_store():
    """Create a mock prospective store with intelligent mocking."""
    # Track tasks in a dict for stateful responses
    tasks = {}
    next_id = [1]  # Use list to allow modification in nested functions

    async def store_task(task):
        task_id = next_id[0]
        next_id[0] += 1
        if task.id is None:
            task.id = task_id
        tasks[task.id] = task
        return task.id

    async def get_task(task_id):
        # Convert string ID to int if needed
        task_id_int = int(task_id) if isinstance(task_id, str) else task_id
        return tasks.get(task_id_int)

    async def list_tasks(**kwargs):
        status = kwargs.get("status")
        limit = kwargs.get("limit", 20)
        all_tasks = list(tasks.values())

        if status:
            all_tasks = [t for t in all_tasks if t.status == status]

        return all_tasks[:limit]

    async def update_task(task):
        if task.id and task.id in tasks:
            tasks[task.id] = task
        return task

    async def delete_task(task_id):
        # Convert string ID to int if needed
        task_id_int = int(task_id) if isinstance(task_id, str) else task_id
        if task_id_int in tasks:
            del tasks[task_id_int]
            return True
        return False

    store = MagicMock()
    store.store = AsyncMock(side_effect=store_task)
    store.get = AsyncMock(side_effect=get_task)
    store.list = AsyncMock(side_effect=list_tasks)
    store.update = AsyncMock(side_effect=update_task)
    store.delete = AsyncMock(side_effect=delete_task)
    return store


@pytest.fixture
def operations(mock_db, mock_store):
    """Create test operations instance with mocked store."""
    ops = ProspectiveOperations(mock_db, mock_store)
    return ops


class TestProspectiveOperations:
    """Test prospective memory operations."""

    async def test_create_task(self, operations: ProspectiveOperations):
        """Test creating a task."""
        task_id = await operations.create_task(
            title="Implement feature X",
            description="Add new authentication system",
            priority=8,
            status="pending",
        )

        assert task_id is not None
        assert isinstance(task_id, str)
        assert int(task_id) > 0

    async def test_create_task_with_due_date(self, operations: ProspectiveOperations):
        """Test creating task with due date."""
        due_date = datetime.now() + timedelta(days=5)

        task_id = await operations.create_task(
            title="Complete report",
            description="Quarterly report",
            due_date=due_date,
            priority=9,
        )

        task = await operations.get_task(task_id)
        assert task is not None
        assert task.due_date is not None

    async def test_create_task_invalid_input(self, operations: ProspectiveOperations):
        """Test creating task with invalid input."""
        with pytest.raises(ValueError):
            await operations.create_task(title="")

    async def test_create_task_priority_clamping(self, operations: ProspectiveOperations):
        """Test priority clamping to 1-10 range."""
        # Test with excessive priority
        task_id = await operations.create_task(
            title="Test priority",
            priority=15,
        )

        task = await operations.get_task(task_id)
        assert task.priority == 10  # Should be clamped to 10

        # Test with negative priority
        task_id2 = await operations.create_task(
            title="Test negative priority",
            priority=-5,
        )

        task2 = await operations.get_task(task_id2)
        assert task2.priority == 1  # Should be clamped to 1

    async def test_list_tasks(self, operations: ProspectiveOperations):
        """Test listing tasks."""
        # Create multiple tasks
        for i in range(3):
            await operations.create_task(
                title=f"Task {i}",
                priority=i + 5,
            )

        tasks = await operations.list_tasks(limit=10)
        assert len(tasks) >= 3
        assert all(isinstance(t, ProspectiveTask) for t in tasks)

    async def test_list_tasks_with_limit(self, operations: ProspectiveOperations):
        """Test list respects limit parameter."""
        for i in range(5):
            await operations.create_task(title=f"Task {i}")

        tasks = await operations.list_tasks(limit=2)
        assert len(tasks) <= 2

    async def test_list_tasks_by_status(self, operations: ProspectiveOperations):
        """Test filtering tasks by status."""
        # Create tasks with different statuses
        task1_id = await operations.create_task(
            title="Pending task",
            status="pending",
        )

        task2_id = await operations.create_task(
            title="Completed task",
            status="completed",
        )

        # List pending tasks
        pending = await operations.list_tasks(status="pending")
        assert any(t.id == int(task1_id) for t in pending)

        # List completed tasks
        completed = await operations.list_tasks(status="completed")
        assert any(t.id == int(task2_id) for t in completed)

    async def test_get_task(self, operations: ProspectiveOperations):
        """Test getting a specific task."""
        task_id = await operations.create_task(
            title="Get test",
            description="Test getting task",
        )

        task = await operations.get_task(task_id)
        assert task is not None
        assert task.id == int(task_id)
        assert task.title == "Get test"

    async def test_get_nonexistent_task(self, operations: ProspectiveOperations):
        """Test getting nonexistent task returns None."""
        # Clear all tasks
        tasks = await operations.list_tasks(limit=10000)
        for t in tasks:
            if t.id:
                await operations.store.delete(t.id)

        result = await operations.get_task("99999")
        assert result is None

    async def test_update_task_status(self, operations: ProspectiveOperations):
        """Test updating task status."""
        task_id = await operations.create_task(
            title="Status update test",
            status="pending",
        )

        success = await operations.update_task_status(task_id, "active")
        assert success is True

        updated_task = await operations.get_task(task_id)
        assert updated_task.status == "active"

    async def test_update_task_status_to_completed(self, operations: ProspectiveOperations):
        """Test updating task to completed sets completion time."""
        task_id = await operations.create_task(
            title="Complete test",
            status="pending",
        )

        success = await operations.update_task_status(task_id, "completed")
        assert success is True

        updated_task = await operations.get_task(task_id)
        assert updated_task.status == "completed"
        assert updated_task.completed_at is not None

    async def test_update_nonexistent_task(self, operations: ProspectiveOperations):
        """Test updating nonexistent task fails gracefully."""
        success = await operations.update_task_status("99999", "completed")
        assert success is False

    async def test_get_active_tasks(self, operations: ProspectiveOperations):
        """Test getting active (pending/active) tasks."""
        # Create pending tasks
        for i in range(3):
            await operations.create_task(
                title=f"Pending task {i}",
                status="pending",
                priority=5 + i,
            )

        # Create active tasks
        for i in range(2):
            await operations.create_task(
                title=f"Active task {i}",
                status="active",
                priority=8 + i,
            )

        # Create completed task (should not be included)
        await operations.create_task(
            title="Completed task",
            status="completed",
        )

        active_tasks = await operations.get_active_tasks(limit=10)
        assert len(active_tasks) >= 5
        assert all(t.status in ["pending", "active"] for t in active_tasks)

    async def test_get_active_tasks_sorted_by_priority(self, operations: ProspectiveOperations):
        """Test active tasks are sorted by priority (high first)."""
        # Create tasks with different priorities
        await operations.create_task(title="Low priority", priority=2, status="pending")
        await operations.create_task(title="Medium priority", priority=5, status="pending")
        await operations.create_task(title="High priority", priority=9, status="in_progress")

        active = await operations.get_active_tasks(limit=10)

        # Should be sorted high to low
        if len(active) >= 2:
            assert active[0].priority >= active[1].priority

    async def test_get_overdue_tasks(self, operations: ProspectiveOperations):
        """Test getting overdue tasks."""
        past_date = datetime.now() - timedelta(days=2)
        future_date = datetime.now() + timedelta(days=5)

        # Create overdue task
        await operations.create_task(
            title="Overdue task",
            due_date=past_date,
            status="pending",
        )

        # Create on-time task
        await operations.create_task(
            title="On-time task",
            due_date=future_date,
            status="pending",
        )

        overdue = await operations.get_overdue_tasks(limit=10)
        assert len(overdue) >= 1
        assert any(t.title == "Overdue task" for t in overdue)

    async def test_get_overdue_tasks_ignores_completed(self, operations: ProspectiveOperations):
        """Test overdue calculation only includes pending tasks."""
        past_date = datetime.now() - timedelta(days=1)

        await operations.create_task(
            title="Completed overdue",
            due_date=past_date,
            status="completed",
        )

        overdue = await operations.get_overdue_tasks(limit=10)

        # Completed tasks should not be in overdue list
        # (they might appear if the filter is on pending only)
        assert not any(t.title == "Completed overdue" and t.status == "completed" for t in overdue)

    async def test_get_statistics(self, operations: ProspectiveOperations):
        """Test getting task statistics."""
        # Create tasks with different statuses
        for i in range(3):
            await operations.create_task(title=f"Pending {i}", status="pending")

        for i in range(2):
            await operations.create_task(title=f"Active {i}", status="in_progress")

        for i in range(1):
            await operations.create_task(title=f"Done {i}", status="completed")

        stats = await operations.get_statistics()

        assert "total_pending" in stats
        assert "total_in_progress" in stats
        assert "total_completed" in stats
        assert "total_tasks" in stats
        assert "completion_rate" in stats

        assert stats["total_pending"] >= 3
        assert stats["total_in_progress"] >= 2
        assert stats["total_completed"] >= 1
        assert stats["total_tasks"] >= 6

    async def test_statistics_completion_rate(self, operations: ProspectiveOperations):
        """Test completion rate calculation."""
        # Clear all tasks first
        tasks = await operations.list_tasks(limit=10000)
        for t in tasks:
            if t.id:
                await operations.store.delete(t.id)

        # Create 4 total tasks: 1 completed, 3 pending
        await operations.create_task(title="Done", status="completed")
        for i in range(3):
            await operations.create_task(title=f"Pending {i}", status="pending")

        stats = await operations.get_statistics()

        # Completion rate should be 1/4 = 0.25
        expected_rate = 1.0 / 4.0
        assert abs(stats["completion_rate"] - expected_rate) < 0.01

    async def test_statistics_empty(self, operations: ProspectiveOperations):
        """Test statistics with no tasks."""
        # Delete all tasks
        tasks = await operations.list_tasks(limit=10000)
        for t in tasks:
            if t.id:
                await operations.store.delete(t.id)

        stats = await operations.get_statistics()

        assert stats["total_pending"] == 0
        assert stats["total_in_progress"] == 0
        assert stats["total_completed"] == 0
        assert stats["total_tasks"] == 0
        assert stats["completion_rate"] == 0.0

    async def test_task_with_project_id(self, operations: ProspectiveOperations):
        """Test creating task with project ID."""
        task_id = await operations.create_task(
            title="Project task",
            project_id=42,
        )

        task = await operations.get_task(task_id)
        assert task.project_id == 42

    async def test_task_timestamps(self, operations: ProspectiveOperations):
        """Test task timestamp creation."""
        before = datetime.now()

        task_id = await operations.create_task(title="Timestamp test")

        task = await operations.get_task(task_id)
        after = datetime.now()

        assert task.created_at is not None
        assert before <= task.created_at <= after

    async def test_task_default_status(self, operations: ProspectiveOperations):
        """Test task has pending status by default."""
        task_id = await operations.create_task(title="Default status")

        task = await operations.get_task(task_id)
        assert task.status == "pending"

    async def test_task_default_priority(self, operations: ProspectiveOperations):
        """Test task has priority 5 by default."""
        task_id = await operations.create_task(title="Default priority")

        task = await operations.get_task(task_id)
        assert task.priority == 5
