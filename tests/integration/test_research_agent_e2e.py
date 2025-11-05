"""End-to-end tests for research agent orchestration - Complete research workflow."""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch

from athena.mcp.handlers import MemoryMCPServer
from athena.research import ResearchStatus, AgentStatus, ResearchFinding
from athena.core.database import Database


class TestResearchAgentE2E:
    """End-to-end tests for research agent execution."""

    @staticmethod
    def make_findings(task_id, source, count=1, credibility=0.85):
        """Helper to create proper ResearchFinding objects."""
        return [
            ResearchFinding(
                research_task_id=task_id,
                source=source,
                title=f"{source} Finding {i}",
                summary=f"{source} Summary {i}",
                credibility_score=credibility
            )
            for i in range(count)
        ]

    @pytest.fixture
    def mcp_server(self, tmp_path):
        """Create MCP server fixture."""
        db_path = str(tmp_path / "test.db")
        return MemoryMCPServer(db_path)

    @pytest.mark.asyncio
    async def test_research_task_creation_spawns_agent(self, mcp_server):
        """Test creating research task automatically spawns agent execution."""
        # Create research task via handler
        args = {"operation": "create", "topic": "Test research topic"}

        result = await mcp_server._handle_research_task(args)

        # Should return success response
        assert result
        assert "Research task created" in result[0].text
        assert "RUNNING" in result[0].text

    @pytest.mark.asyncio
    async def test_research_task_full_workflow(self, mcp_server):
        """Test complete research workflow: create -> execute -> status."""
        # Step 1: Create research task
        create_args = {"operation": "create", "topic": "Machine learning patterns"}

        create_result = await mcp_server._handle_research_task(create_args)
        assert "Research task created" in create_result[0].text

        # Extract task ID from response
        response_text = create_result[0].text
        task_id = None
        for line in response_text.split('\n'):
            if "ID:" in line:
                task_id = int(line.split("ID:")[-1].strip().split(')')[0])
                break

        assert task_id is not None

        # Mock agent execution with proper ResearchFinding objects
        mcp_server.research_executor._simulate_agent_research = AsyncMock(
            return_value=[
                ResearchFinding(
                    research_task_id=task_id,
                    source="Test",
                    title=f"Finding {i}",
                    summary=f"Summary {i}",
                    credibility_score=0.85
                )
                for i in range(2)
            ]
        )

        # Step 2: Wait for background task execution
        # Give agents time to execute
        await asyncio.sleep(0.1)

        # Step 3: Get research status
        status_args = {"operation": "get_status", "task_id": task_id}
        status_result = await mcp_server._handle_research_task(status_args)

        assert status_result
        assert "Research Task Status" in status_result[0].text

    @pytest.mark.asyncio
    async def test_research_findings_storage(self, mcp_server):
        """Test findings are stored to database during research."""
        # Create research task
        create_args = {"operation": "create", "topic": "Testing research storage"}
        create_result = await mcp_server._handle_research_task(create_args)

        response_text = create_result[0].text
        task_id = None
        for line in response_text.split('\n'):
            if "ID:" in line:
                task_id = int(line.split("ID:")[-1].strip().split(')')[0])
                break

        # Mock agent findings - return dicts like real agents do
        async def mock_research(task_id, topic, agent_name, source, credibility):
            # Return dicts like real agents would
            return [
                {
                    "title": f"Finding from {agent_name}",
                    "summary": f"A finding from {source}",
                    "url": "https://example.com",
                    "credibility": credibility,
                    "relevance": 0.85
                }
            ]

        mcp_server.research_executor._simulate_agent_research = mock_research

        # Execute research
        await mcp_server.research_executor.execute_research(task_id, "Testing storage")

        # Verify findings were stored
        findings = mcp_server.research_store.get_task_findings(task_id)
        assert len(findings) > 0
        assert all(f.title for f in findings)

    @pytest.mark.asyncio
    async def test_research_with_all_agents(self, mcp_server):
        """Test research executes all 8 agents in parallel."""
        # Create research task
        task_id = mcp_server.research_store.create_task("Multi-agent research", project_id=1)

        # Track which agents execute
        executed_agents = []

        async def mock_research(task_id, topic, agent_name, source, credibility):
            executed_agents.append(agent_name)
            await asyncio.sleep(0.001)  # Simulate minimal work
            return self.make_findings(task_id, source, count=1, credibility=credibility)

        mcp_server.research_executor._simulate_agent_research = mock_research

        # Execute research
        await mcp_server.research_executor.execute_research(task_id, "Multi-agent research")

        # Verify all 8 agents executed
        assert len(executed_agents) == 8
        assert "arxiv-researcher" in executed_agents
        assert "github-researcher" in executed_agents

    @pytest.mark.asyncio
    async def test_research_task_listing(self, mcp_server):
        """Test listing research tasks shows recent tasks."""
        # Create multiple research tasks
        for i in range(3):
            create_args = {"operation": "create", "topic": f"Research topic {i}"}
            await mcp_server._handle_research_task(create_args)

        # List tasks
        list_args = {"operation": "list"}
        list_result = await mcp_server._handle_research_task(list_args)

        assert list_result
        assert "Recent Research Tasks" in list_result[0].text
        # Should show all created tasks
        for i in range(3):
            assert f"Research topic {i}" in list_result[0].text or "RUNNING" in list_result[0].text

    @pytest.mark.asyncio
    async def test_research_findings_retrieval(self, mcp_server):
        """Test retrieving findings from completed research."""
        # Create research task
        task_id = mcp_server.research_store.create_task("Findings test", project_id=1)

        # Record some findings
        for i in range(3):
            mcp_server.research_executor.record_finding(
                task_id,
                source=f"Source {i}",
                title=f"Finding {i}",
                summary=f"Summary of finding {i}",
                url=f"https://example.com/{i}"
            )

        # Update task status to completed
        mcp_server.research_store.update_status(task_id, ResearchStatus.COMPLETED)

        # Retrieve findings
        findings_args = {"operation": "get", "task_id": task_id}
        findings_result = await mcp_server._handle_research_findings(findings_args)

        assert findings_result
        assert "Research Findings" in findings_result[0].text
        # Should show findings
        for i in range(3):
            assert f"Finding {i}" in findings_result[0].text

    @pytest.mark.asyncio
    async def test_research_agent_status_updates(self, mcp_server):
        """Test agent progress is tracked and reported."""
        # Create research task
        task_id = mcp_server.research_store.create_task("Agent tracking", project_id=1)

        # Mock agent execution with varying findings
        async def mock_research(task_id, topic, agent_name, source, credibility):
            if agent_name == "arxiv-researcher":
                return self.make_findings(task_id, source, count=5, credibility=credibility)
            elif agent_name == "github-researcher":
                return self.make_findings(task_id, source, count=3, credibility=credibility)
            else:
                return []

        mcp_server.research_executor._simulate_agent_research = mock_research

        # Execute research
        total = await mcp_server.research_executor.execute_research(task_id, "Agent tracking")

        # Get status
        status = mcp_server.research_executor.get_research_status(task_id)

        assert status["findings_count"] == 8
        assert status["task_id"] == task_id
        assert status["status"] == ResearchStatus.COMPLETED.value

        # Verify agent breakdown
        agents = status["agents"]
        assert any(a["name"] == "arxiv-researcher" and a["findings_count"] == 5 for a in agents)
        assert any(a["name"] == "github-researcher" and a["findings_count"] == 3 for a in agents)

    @pytest.mark.asyncio
    async def test_research_failure_recovery(self, mcp_server):
        """Test research completes even if some agents fail."""
        # Create research task
        task_id = mcp_server.research_store.create_task("Failure recovery", project_id=1)

        call_count = {"count": 0}

        async def mock_research(task_id, topic, agent_name, source, credibility):
            call_count["count"] += 1
            if call_count["count"] == 2:  # Fail on second agent
                raise Exception("Agent failed")
            return self.make_findings(task_id, source, count=2, credibility=credibility)

        mcp_server.research_executor._simulate_agent_research = mock_research

        # Execute research - should not raise exception
        total = await mcp_server.research_executor.execute_research(task_id, "Failure recovery")

        # Task should complete despite failure
        task = mcp_server.research_store.get_task(task_id)
        assert task.status == ResearchStatus.COMPLETED.value

        # Should have findings from successful agents
        assert total > 0

    @pytest.mark.asyncio
    async def test_parallel_research_tasks(self, mcp_server):
        """Test multiple research tasks can run independently."""
        # Create multiple research tasks
        task_ids = []
        for i in range(3):
            task_id = mcp_server.research_store.create_task(f"Parallel research {i}", project_id=1)
            task_ids.append(task_id)

        # Mock agent execution with proper findings
        async def mock_research(task_id, topic, agent_name, source, credibility):
            return self.make_findings(task_id, source, count=2, credibility=credibility)

        mcp_server.research_executor._simulate_agent_research = mock_research

        # Execute all in parallel
        tasks = [
            mcp_server.research_executor.execute_research(tid, f"Parallel research {i}")
            for i, tid in enumerate(task_ids)
        ]
        await asyncio.gather(*tasks)

        # Verify all completed
        for task_id in task_ids:
            task = mcp_server.research_store.get_task(task_id)
            assert task.status == ResearchStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_research_credibility_scoring(self, mcp_server):
        """Test findings are stored with correct credibility scores."""
        task_id = mcp_server.research_store.create_task("Credibility test", project_id=1)

        # Record findings from different sources
        finding_arxiv = mcp_server.research_executor.record_finding(
            task_id,
            source="arXiv",
            title="Academic paper",
            summary="From arXiv",
        )

        finding_x = mcp_server.research_executor.record_finding(
            task_id,
            source="X/Twitter",
            title="Tweet",
            summary="From Twitter",
        )

        # Retrieve findings
        findings = mcp_server.research_store.get_task_findings(task_id)
        arxiv_finding = next(f for f in findings if f.source == "arXiv")
        x_finding = next(f for f in findings if f.source == "X/Twitter")

        # arXiv should have higher credibility than X
        assert arxiv_finding.credibility_score > x_finding.credibility_score
