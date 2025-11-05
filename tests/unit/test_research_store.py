"""Tests for research task storage and orchestration."""

import pytest
from pathlib import Path
from athena.core.database import Database
from athena.research import (
    ResearchStore,
    ResearchTask,
    ResearchStatus,
    ResearchFinding,
    AgentStatus,
    AgentProgress,
)


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Create a temporary database for testing."""
    return Database(str(tmp_path / "test.db"))


@pytest.fixture
def store(db: Database) -> ResearchStore:
    """Create a research store."""
    return ResearchStore(db)


class TestResearchStore:
    """Tests for ResearchStore."""

    def test_create_task(self, store: ResearchStore):
        """Test creating a research task."""
        task_id = store.create_task("Test research topic", project_id=None)
        assert task_id is not None
        assert task_id > 0

    def test_get_task(self, store: ResearchStore):
        """Test retrieving a research task."""
        # Create a task
        task_id = store.create_task("Test research topic", project_id=None)

        # Retrieve it
        task = store.get_task(task_id)
        assert task is not None
        assert task.id == task_id
        assert task.topic == "Test research topic"
        assert task.status == ResearchStatus.PENDING.value

    def test_get_nonexistent_task(self, store: ResearchStore):
        """Test retrieving a nonexistent task returns None."""
        task = store.get_task(999)
        assert task is None

    def test_update_status(self, store: ResearchStore):
        """Test updating task status."""
        task_id = store.create_task("Test topic")

        # Update to running
        success = store.update_status(task_id, ResearchStatus.RUNNING)
        assert success

        # Verify status changed
        task = store.get_task(task_id)
        assert task.status == ResearchStatus.RUNNING.value
        assert task.started_at is not None

    def test_update_status_to_completed(self, store: ResearchStore):
        """Test updating task status to completed."""
        task_id = store.create_task("Test topic")

        # Update to completed
        success = store.update_status(task_id, ResearchStatus.COMPLETED)
        assert success

        # Verify status and timestamps
        task = store.get_task(task_id)
        assert task.status == ResearchStatus.COMPLETED.value
        assert task.completed_at is not None

    def test_record_finding(self, store: ResearchStore):
        """Test recording a research finding."""
        task_id = store.create_task("Test topic")

        finding = ResearchFinding(
            research_task_id=task_id,
            source="arXiv",
            title="Test Paper",
            summary="A test paper summary",
            credibility_score=0.85,
        )

        finding_id = store.record_finding(finding)
        assert finding_id is not None
        assert finding_id > 0

    def test_get_task_findings(self, store: ResearchStore):
        """Test retrieving findings for a task."""
        task_id = store.create_task("Test topic")

        # Record multiple findings
        for i in range(3):
            finding = ResearchFinding(
                research_task_id=task_id,
                source="arXiv",
                title=f"Paper {i}",
                summary=f"Summary {i}",
                credibility_score=0.8 + (i * 0.05),
            )
            store.record_finding(finding)

        # Retrieve findings
        findings = store.get_task_findings(task_id)
        assert len(findings) == 3

        # Verify they're sorted by credibility (descending)
        assert findings[0].credibility_score >= findings[1].credibility_score
        assert findings[1].credibility_score >= findings[2].credibility_score

    def test_increment_task_stats(self, store: ResearchStore):
        """Test incrementing task statistics."""
        task_id = store.create_task("Test topic")

        # Increment stats
        success = store.increment_task_stats(
            task_id, findings=5, entities=3, relations=2
        )
        assert success

        # Verify stats
        task = store.get_task(task_id)
        assert task.findings_count == 5
        assert task.entities_created == 3
        assert task.relations_created == 2

    def test_increment_multiple_times(self, store: ResearchStore):
        """Test incrementing stats multiple times."""
        task_id = store.create_task("Test topic")

        store.increment_task_stats(task_id, findings=2, entities=1)
        store.increment_task_stats(task_id, findings=3, entities=2)

        task = store.get_task(task_id)
        assert task.findings_count == 5
        assert task.entities_created == 3

    def test_record_agent_progress(self, store: ResearchStore):
        """Test recording agent progress."""
        task_id = store.create_task("Test topic")

        progress = AgentProgress(
            research_task_id=task_id,
            agent_name="arxiv-researcher",
            status=AgentStatus.RUNNING,
        )

        progress_id = store.record_agent_progress(progress)
        assert progress_id is not None
        assert progress_id > 0

    def test_update_agent_progress(self, store: ResearchStore):
        """Test updating agent progress."""
        task_id = store.create_task("Test topic")

        # Record initial progress
        progress = AgentProgress(
            research_task_id=task_id,
            agent_name="arxiv-researcher",
            status=AgentStatus.PENDING,
        )
        store.record_agent_progress(progress)

        # Update progress
        success = store.update_agent_progress(
            task_id, "arxiv-researcher", AgentStatus.COMPLETED, findings_count=5
        )
        assert success

        # Verify update
        agent_progress_list = store.get_agent_progress(task_id)
        assert len(agent_progress_list) > 0
        agent_prog = agent_progress_list[0]
        assert agent_prog.agent_name == "arxiv-researcher"
        assert agent_prog.status == AgentStatus.COMPLETED.value
        assert agent_prog.findings_count == 5

    def test_get_agent_progress(self, store: ResearchStore):
        """Test retrieving agent progress."""
        task_id = store.create_task("Test topic")

        # Record progress for multiple agents
        for agent_name in ["arxiv-researcher", "github-researcher", "techblogs-researcher"]:
            progress = AgentProgress(
                research_task_id=task_id,
                agent_name=agent_name,
                status=AgentStatus.PENDING,
            )
            store.record_agent_progress(progress)

        # Retrieve progress
        agent_progress_list = store.get_agent_progress(task_id)
        assert len(agent_progress_list) == 3

        agent_names = [p.agent_name for p in agent_progress_list]
        assert "arxiv-researcher" in agent_names
        assert "github-researcher" in agent_names
        assert "techblogs-researcher" in agent_names

    def test_list_tasks(self, store: ResearchStore):
        """Test listing research tasks."""
        # Create multiple tasks
        for i in range(5):
            store.create_task(f"Research topic {i}")

        # List tasks
        tasks = store.list_tasks()
        assert len(tasks) == 5

    def test_list_tasks_by_status(self, store: ResearchStore):
        """Test listing tasks filtered by status."""
        # Create tasks with different statuses
        task1 = store.create_task("Topic 1")
        task2 = store.create_task("Topic 2")
        task3 = store.create_task("Topic 3")

        store.update_status(task1, ResearchStatus.RUNNING)
        store.update_status(task2, ResearchStatus.COMPLETED)

        # List running tasks
        running_tasks = store.list_tasks(status=ResearchStatus.RUNNING)
        assert len(running_tasks) == 1
        assert running_tasks[0].id == task1

        # List completed tasks
        completed_tasks = store.list_tasks(status=ResearchStatus.COMPLETED)
        assert len(completed_tasks) == 1
        assert completed_tasks[0].id == task2

        # List pending tasks
        pending_tasks = store.list_tasks(status=ResearchStatus.PENDING)
        assert len(pending_tasks) == 1
        assert pending_tasks[0].id == task3

    def test_update_finding_memory_status(self, store: ResearchStore):
        """Test marking finding as stored to memory."""
        task_id = store.create_task("Test topic")

        # Record a finding
        finding = ResearchFinding(
            research_task_id=task_id,
            source="arXiv",
            title="Test Paper",
            summary="A test paper summary",
        )
        finding_id = store.record_finding(finding)

        # Mark as stored to memory
        success = store.update_finding_memory_status(finding_id, memory_id=123)
        assert success

        # Verify update
        findings = store.get_task_findings(task_id)
        assert findings[0].stored_to_memory is True
        assert findings[0].memory_id == 123

    def test_task_with_url(self, store: ResearchStore):
        """Test recording findings with URLs."""
        task_id = store.create_task("Test topic")

        finding = ResearchFinding(
            research_task_id=task_id,
            source="GitHub",
            title="Repository",
            summary="A test repository",
            url="https://github.com/example/repo",
            credibility_score=0.9,
        )

        finding_id = store.record_finding(finding)
        assert finding_id > 0

        # Verify URL is preserved
        findings = store.get_task_findings(task_id)
        assert findings[0].url == "https://github.com/example/repo"

    def test_default_values(self, store: ResearchStore):
        """Test that default values are properly set."""
        task_id = store.create_task("Test topic")
        task = store.get_task(task_id)

        # Verify defaults
        assert task.status == ResearchStatus.PENDING.value
        assert task.findings_count == 0
        assert task.entities_created == 0
        assert task.relations_created == 0
        assert task.notes == ""
        assert task.agent_results == {}
        assert task.started_at is None
        assert task.completed_at is None

    def test_concurrent_findings(self, store: ResearchStore):
        """Test handling multiple findings from different sources."""
        task_id = store.create_task("Test topic")

        sources = ["arXiv", "GitHub", "Papers with Code", "HackerNews", "Medium"]
        for i, source in enumerate(sources):
            finding = ResearchFinding(
                research_task_id=task_id,
                source=source,
                title=f"{source} Finding {i}",
                summary=f"Finding from {source}",
                credibility_score=0.5 + (i * 0.1),
            )
            store.record_finding(finding)

        # Verify all findings were recorded
        findings = store.get_task_findings(task_id)
        assert len(findings) == 5

        # Verify sources are diverse
        sources_found = set(f.source for f in findings)
        assert sources_found == set(sources)
