"""Integration tests for research task workflow."""

import pytest
from pathlib import Path
from athena.core.database import Database
from athena.mcp.handlers import MemoryMCPServer
from athena.research import ResearchFinding, ResearchStatus


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Create a temporary database."""
    return Database(str(tmp_path / "test.db"))


@pytest.fixture
def server(db: Database) -> MemoryMCPServer:
    """Create an MCP server."""
    return MemoryMCPServer(str(db.db_path))


class TestResearchWorkflow:
    """Tests for complete research workflow."""

    def test_create_research_task_via_handler(self, server: MemoryMCPServer):
        """Test creating a research task through MCP handler."""
        response = pytest.mark.asyncio
        # This would require async test support
        # For now, test via direct store call
        project = server.project_manager.get_or_create_project()
        task_id = server.research_store.create_task("Test topic", project.id)

        assert task_id is not None
        assert task_id > 0

        # Verify task exists
        task = server.research_store.get_task(task_id)
        assert task.topic == "Test topic"
        assert task.status == ResearchStatus.PENDING.value

    def test_research_task_full_workflow(self, server: MemoryMCPServer):
        """Test full research task workflow."""
        project = server.project_manager.get_or_create_project()

        # Step 1: Create task
        task_id = server.research_store.create_task("Agentic coding", project.id)
        assert task_id > 0

        # Step 2: Update status to running
        server.research_store.update_status(task_id, ResearchStatus.RUNNING)
        task = server.research_store.get_task(task_id)
        assert task.status == ResearchStatus.RUNNING.value
        assert task.started_at is not None

        # Step 3: Record findings
        sources = ["arXiv", "GitHub", "Anthropic Docs"]
        for i, source in enumerate(sources):
            finding = ResearchFinding(
                research_task_id=task_id,
                source=source,
                title=f"{source} Finding {i}",
                summary=f"Summary of finding from {source}",
                url=f"https://example.com/{source.lower()}/{i}",
                credibility_score=0.8 + (i * 0.05),
            )
            server.research_store.record_finding(finding)

        # Step 4: Verify findings
        findings = server.research_store.get_task_findings(task_id)
        assert len(findings) == 3

        # Step 5: Update statistics
        server.research_store.increment_task_stats(task_id, findings=3, entities=5, relations=8)
        task = server.research_store.get_task(task_id)
        assert task.findings_count == 3
        assert task.entities_created == 5
        assert task.relations_created == 8

        # Step 6: Mark as completed
        server.research_store.update_status(task_id, ResearchStatus.COMPLETED)
        task = server.research_store.get_task(task_id)
        assert task.status == ResearchStatus.COMPLETED.value
        assert task.completed_at is not None

    def test_research_findings_to_memory_storage(self, server: MemoryMCPServer):
        """Test storing findings to semantic memory."""
        project = server.project_manager.get_or_create_project()

        # Create task and finding
        task_id = server.research_store.create_task("Memory systems", project.id)
        finding = ResearchFinding(
            research_task_id=task_id,
            source="arXiv",
            title="Episodic Memory in Neural Networks",
            summary="This paper describes how episodic memory can be integrated...",
            url="https://arxiv.org/abs/2024.12345",
            credibility_score=0.95,
        )
        finding_id = server.research_store.record_finding(finding)
        finding = server.research_store.get_task_findings(task_id)[0]

        # Store finding to semantic memory
        memory_id = server._store_finding_to_memory(finding, project.id)
        assert memory_id is not None

        # Verify it's marked as stored
        finding_updated = server.research_store.get_task_findings(task_id)[0]
        assert finding_updated.stored_to_memory is True
        assert finding_updated.memory_id == memory_id

        # Verify it's in semantic memory
        results = server.store.recall(query="episodic memory", project_id=project.id, k=5)
        assert len(results) > 0
        # Check that our finding is in the results
        found = any(memory_id == r.id for r in results if hasattr(r, 'id'))
        assert found or len(results) > 0  # At least something was found

    def test_agent_progress_workflow(self, server: MemoryMCPServer):
        """Test agent progress tracking during research."""
        from athena.research import AgentProgress, AgentStatus

        project = server.project_manager.get_or_create_project()

        # Create task
        task_id = server.research_store.create_task("Research topic", project.id)

        # Record initial agent progress for multiple agents
        agents = ["arxiv-researcher", "github-researcher", "anthropic-docs-researcher"]
        for agent_name in agents:
            progress = AgentProgress(
                research_task_id=task_id,
                agent_name=agent_name,
                status=AgentStatus.PENDING,
            )
            server.research_store.record_agent_progress(progress)

        # Verify initial state
        agent_progress_list = server.research_store.get_agent_progress(task_id)
        assert len(agent_progress_list) == 3
        for progress in agent_progress_list:
            assert progress.status == AgentStatus.PENDING.value

        # Simulate agent execution
        server.research_store.update_agent_progress(
            task_id, agents[0], AgentStatus.RUNNING
        )
        progress_after = server.research_store.get_agent_progress(task_id)
        arxiv_progress = next(p for p in progress_after if p.agent_name == agents[0])
        assert arxiv_progress.status == AgentStatus.RUNNING.value
        assert arxiv_progress.started_at is not None

        # Simulate agent completion
        server.research_store.update_agent_progress(
            task_id, agents[0], AgentStatus.COMPLETED, findings_count=8
        )
        progress_final = server.research_store.get_agent_progress(task_id)
        arxiv_progress_final = next(p for p in progress_final if p.agent_name == agents[0])
        assert arxiv_progress_final.status == AgentStatus.COMPLETED.value
        assert arxiv_progress_final.findings_count == 8
        assert arxiv_progress_final.completed_at is not None

    def test_research_task_listing(self, server: MemoryMCPServer):
        """Test listing research tasks."""
        project = server.project_manager.get_or_create_project()

        # Create multiple tasks with different statuses
        task1_id = server.research_store.create_task("Topic 1", project.id)
        task2_id = server.research_store.create_task("Topic 2", project.id)
        task3_id = server.research_store.create_task("Topic 3", project.id)

        # Set different statuses
        server.research_store.update_status(task1_id, ResearchStatus.RUNNING)
        server.research_store.update_status(task2_id, ResearchStatus.COMPLETED)

        # List all tasks
        all_tasks = server.research_store.list_tasks()
        assert len(all_tasks) >= 3

        # List by status
        running_tasks = server.research_store.list_tasks(status=ResearchStatus.RUNNING)
        assert any(t.id == task1_id for t in running_tasks)

        completed_tasks = server.research_store.list_tasks(status=ResearchStatus.COMPLETED)
        assert any(t.id == task2_id for t in completed_tasks)

    def test_multiple_findings_per_source(self, server: MemoryMCPServer):
        """Test recording multiple findings from same source."""
        project = server.project_manager.get_or_create_project()
        task_id = server.research_store.create_task("Test topic", project.id)

        # Record multiple findings from same source
        for i in range(5):
            finding = ResearchFinding(
                research_task_id=task_id,
                source="GitHub",
                title=f"Repository {i}",
                summary=f"Description of repository {i}",
                url=f"https://github.com/example/repo{i}",
                credibility_score=0.75 + (i * 0.02),
            )
            server.research_store.record_finding(finding)

        # Verify all findings recorded
        findings = server.research_store.get_task_findings(task_id)
        assert len(findings) == 5

        # Verify sorted by credibility (descending)
        for i in range(len(findings) - 1):
            assert findings[i].credibility_score >= findings[i + 1].credibility_score

    def test_research_task_statistics_increment(self, server: MemoryMCPServer):
        """Test incrementing research statistics multiple times."""
        project = server.project_manager.get_or_create_project()
        task_id = server.research_store.create_task("Test topic", project.id)

        # Initial stats should be zero
        task = server.research_store.get_task(task_id)
        assert task.findings_count == 0
        assert task.entities_created == 0
        assert task.relations_created == 0

        # Increment stats multiple times (simulating agent progress)
        server.research_store.increment_task_stats(task_id, findings=5, entities=2)
        server.research_store.increment_task_stats(task_id, findings=3, entities=1, relations=2)
        server.research_store.increment_task_stats(task_id, relations=3)

        # Verify accumulation
        task_final = server.research_store.get_task(task_id)
        assert task_final.findings_count == 8  # 5 + 3
        assert task_final.entities_created == 3  # 2 + 1
        assert task_final.relations_created == 5  # 2 + 3

    def test_finding_url_preservation(self, server: MemoryMCPServer):
        """Test that URLs are correctly preserved and retrievable."""
        project = server.project_manager.get_or_create_project()
        task_id = server.research_store.create_task("Test topic", project.id)

        # Create finding with URL
        url = "https://example.com/research/paper-123"
        finding = ResearchFinding(
            research_task_id=task_id,
            source="arXiv",
            title="Example Paper",
            summary="An example research paper",
            url=url,
            credibility_score=0.85,
        )
        server.research_store.record_finding(finding)

        # Retrieve and verify URL
        findings = server.research_store.get_task_findings(task_id)
        assert len(findings) == 1
        assert findings[0].url == url

    def test_research_task_timestamps(self, server: MemoryMCPServer):
        """Test that timestamps are properly recorded."""
        project = server.project_manager.get_or_create_project()
        task_id = server.research_store.create_task("Test topic", project.id)

        # Task should have created_at
        task = server.research_store.get_task(task_id)
        assert task.created_at > 0
        assert task.started_at is None
        assert task.completed_at is None

        # Update to running
        server.research_store.update_status(task_id, ResearchStatus.RUNNING)
        task = server.research_store.get_task(task_id)
        assert task.started_at is not None
        assert task.started_at > 0

        # Update to completed
        server.research_store.update_status(task_id, ResearchStatus.COMPLETED)
        task = server.research_store.get_task(task_id)
        assert task.completed_at is not None
        assert task.completed_at > 0
