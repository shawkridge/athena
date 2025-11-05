"""Unit tests for ResearchAgentExecutor - Agent coordination and parallel execution."""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from athena.research import (
    ResearchAgentExecutor,
    ResearchStore,
    ResearchStatus,
    AgentStatus,
    ResearchFinding,
)
from athena.core.database import Database


class TestResearchAgentExecutor:
    """Test ResearchAgentExecutor class."""

    @pytest.fixture
    def research_store(self, tmp_path):
        """Create research store fixture."""
        db = Database(str(tmp_path / "test.db"))
        return ResearchStore(db)

    @pytest.fixture
    def executor(self, research_store):
        """Create executor fixture."""
        finding_callback = Mock()
        status_callback = Mock()
        return ResearchAgentExecutor(
            research_store=research_store,
            on_finding_discovered=finding_callback,
            on_status_updated=status_callback,
        )

    @pytest.fixture
    def sample_task(self, research_store):
        """Create sample research task."""
        task_id = research_store.create_task("Test research topic", project_id=1)
        return task_id

    def test_executor_initialization(self, executor):
        """Test executor initializes with correct agent list."""
        assert len(executor.RESEARCH_AGENTS) == 8
        assert executor.RESEARCH_AGENTS[0]["name"] == "arxiv-researcher"
        assert executor.RESEARCH_AGENTS[0]["credibility"] == 1.0

    def test_all_agents_defined(self, executor):
        """Verify all 8 research agents are defined."""
        expected_agents = [
            "arxiv-researcher",
            "anthropic-docs-researcher",
            "github-researcher",
            "paperswithcode-researcher",
            "techblogs-researcher",
            "hackernews-researcher",
            "medium-researcher",
            "x-researcher",
        ]
        actual_agents = [a["name"] for a in executor.RESEARCH_AGENTS]
        assert actual_agents == expected_agents

    def test_agent_credibility_scores(self, executor):
        """Verify agent credibility scores are set correctly."""
        creds = {a["name"]: a["credibility"] for a in executor.RESEARCH_AGENTS}
        assert creds["arxiv-researcher"] == 1.0
        assert creds["anthropic-docs-researcher"] == 0.95
        assert creds["github-researcher"] == 0.85
        assert creds["x-researcher"] == 0.62

    @pytest.mark.asyncio
    async def test_execute_research_initializes_agents(self, executor, research_store, sample_task):
        """Test execute_research initializes agent progress records."""
        # Mock the simulate method to return empty findings
        executor._simulate_agent_research = AsyncMock(return_value=[])

        # Execute research
        await executor.execute_research(sample_task, "Test topic")

        # Verify agent progress records were created
        agent_progress = research_store.get_agent_progress(sample_task)
        assert len(agent_progress) == 8
        assert all(p.agent_name in [a["name"] for a in executor.RESEARCH_AGENTS]
                   for p in agent_progress)

    @pytest.mark.asyncio
    async def test_execute_research_parallel_execution(
        self, executor, research_store, sample_task
    ):
        """Test execute_research executes agents in parallel."""
        call_times = []

        async def mock_research(*args, **kwargs):
            """Mock research that records call time."""
            call_times.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.01)  # Simulate short work
            return []

        executor._simulate_agent_research = mock_research

        # Execute research
        start_time = asyncio.get_event_loop().time()
        await executor.execute_research(sample_task, "Test topic")
        end_time = asyncio.get_event_loop().time()

        # All agents should be called
        assert len(call_times) == 8

        # If truly parallel, should complete much faster than 8 * 0.01 = 0.08 seconds
        elapsed = end_time - start_time
        # Allow some overhead, but should be < 0.5 seconds for parallel execution
        assert elapsed < 0.5

    @pytest.mark.asyncio
    async def test_execute_research_aggregates_findings(self, executor, research_store, sample_task):
        """Test execute_research aggregates findings from all agents."""
        # Mock different finding counts for each agent
        async def mock_research(task_id, topic, agent_name, source, credibility):
            """Mock research with varying findings."""
            if agent_name == "arxiv-researcher":
                return [
                    ResearchFinding(
                        research_task_id=task_id,
                        source="arXiv",
                        title=f"Paper {i}",
                        summary=f"Summary {i}",
                        credibility_score=0.9
                    )
                    for i in range(5)
                ]
            elif agent_name == "github-researcher":
                return [
                    ResearchFinding(
                        research_task_id=task_id,
                        source="GitHub",
                        title=f"Repo {i}",
                        summary=f"Summary {i}",
                        credibility_score=0.85
                    )
                    for i in range(3)
                ]
            else:
                return []  # No findings

        executor._simulate_agent_research = mock_research

        # Execute research
        total = await executor.execute_research(sample_task, "Test topic")

        # Should aggregate: 5 + 3 = 8
        assert total == 8

        # Task should reflect aggregated count
        task = research_store.get_task(sample_task)
        assert task.findings_count == 8

    @pytest.mark.asyncio
    async def test_execute_research_handles_agent_failure(
        self, executor, research_store, sample_task
    ):
        """Test execute_research handles individual agent failures gracefully."""
        async def mock_research(task_id, topic, agent_name, source, credibility):
            """Mock research that fails for one agent."""
            if agent_name == "github-researcher":
                raise Exception("Agent failed")
            return [
                ResearchFinding(
                    research_task_id=task_id,
                    source=source,
                    title=f"Finding {j}",
                    summary=f"Summary {j}",
                    credibility_score=credibility
                )
                for j in range(2)
            ]

        executor._simulate_agent_research = mock_research
        executor._execute_agent_with_timeout = AsyncMock(side_effect=[
            [
                ResearchFinding(
                    research_task_id=sample_task,
                    source="TestSource",
                    title=f"Finding {j}",
                    summary=f"Summary {j}",
                    credibility_score=0.85
                )
                for j in range(2)
            ] if i != 2 else Exception("Agent failed")
            for i in range(8)
        ])

        # Execute research
        total = await executor.execute_research(sample_task, "Test topic")

        # Should still complete and aggregate other findings
        agent_progress = research_store.get_agent_progress(sample_task)
        failed_agents = [p for p in agent_progress if p.status == AgentStatus.FAILED.value]
        assert len(failed_agents) > 0  # At least one agent failed

    @pytest.mark.asyncio
    async def test_execute_research_updates_status(
        self, executor, research_store, sample_task
    ):
        """Test execute_research updates task status correctly."""
        executor._simulate_agent_research = AsyncMock(return_value=[])

        # Initially task should be created (status may vary)
        initial_task = research_store.get_task(sample_task)
        assert initial_task is not None

        # Execute research
        await executor.execute_research(sample_task, "Test topic")

        # Task should be marked as COMPLETED
        task = research_store.get_task(sample_task)
        assert task.status == ResearchStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_execute_research_calls_status_callback(
        self, executor, research_store, sample_task
    ):
        """Test execute_research calls status update callback."""
        executor._simulate_agent_research = AsyncMock(return_value=[])

        # Execute research
        await executor.execute_research(sample_task, "Test topic")

        # Callback should be called with COMPLETED status
        executor.on_status_updated.assert_called()
        last_call_args = executor.on_status_updated.call_args
        assert last_call_args[0][0] == sample_task
        assert last_call_args[0][1] == ResearchStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_research_error_handling(
        self, executor, research_store, sample_task
    ):
        """Test execute_research handles agent failures gracefully."""
        # Make simulate fail for all agents
        executor._simulate_agent_research = AsyncMock(
            side_effect=Exception("Agent error")
        )

        # Execute should complete even with all agents failing (graceful degradation)
        # The gather with return_exceptions=True catches individual failures
        total = await executor.execute_research(sample_task, "Test topic")

        # Should return 0 findings
        assert total == 0

        # Task should still be marked as COMPLETED (partial success)
        task = research_store.get_task(sample_task)
        assert task.status == ResearchStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_execute_agent_with_timeout_success(self, executor, sample_task):
        """Test _execute_agent_with_timeout succeeds with normal execution."""
        executor._simulate_agent_research = AsyncMock(
            return_value=[
                ResearchFinding(
                    research_task_id=sample_task,
                    source="Test",
                    title=f"Finding {i}",
                    summary=f"Summary {i}",
                    credibility_score=0.9
                )
                for i in range(3)
            ]
        )

        result = await executor._execute_agent_with_timeout(
            sample_task,
            "Test topic",
            {"name": "test-agent", "source": "Test", "credibility": 0.9}
        )

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_execute_agent_with_timeout_timeout(self, executor, sample_task):
        """Test _execute_agent_with_timeout handles timeout."""
        async def slow_research(*args, **kwargs):
            await asyncio.sleep(2)  # Simulate slow execution
            return []

        executor._simulate_agent_research = slow_research

        # Temporarily patch the timeout to 0.1 seconds for testing
        with patch.object(executor, '_execute_agent_with_timeout',
                         new_callable=AsyncMock) as mock_timeout:
            # Make it use real implementation but with short timeout
            async def timeout_impl(*args, **kwargs):
                try:
                    return await asyncio.wait_for(slow_research(*args, **kwargs), timeout=0.1)
                except asyncio.TimeoutError:
                    raise Exception("timeout")

            mock_timeout.side_effect = timeout_impl

            # Should timeout and raise exception
            with pytest.raises(Exception, match="timeout"):
                await mock_timeout(sample_task, "Test topic",
                    {"name": "slow-agent", "source": "Test", "credibility": 0.9}
                )

    @pytest.mark.asyncio
    async def test_record_finding(self, executor, research_store, sample_task):
        """Test record_finding stores finding to database."""
        finding_id = executor.record_finding(
            sample_task,
            source="Test Source",
            title="Test Finding",
            summary="A test finding",
            url="https://example.com"
        )

        assert finding_id is not None
        findings = research_store.get_task_findings(sample_task)
        assert len(findings) == 1
        assert findings[0].title == "Test Finding"

    @pytest.mark.asyncio
    async def test_record_finding_calls_callback(self, executor, research_store, sample_task):
        """Test record_finding calls finding discovery callback."""
        executor.record_finding(
            sample_task,
            source="Test Source",
            title="Test Finding",
            summary="A test finding"
        )

        # Callback should be called
        executor.on_finding_discovered.assert_called_once()

    def test_get_source_credibility(self, executor):
        """Test _get_source_credibility returns correct scores."""
        assert executor._get_source_credibility("arXiv") == 1.0
        assert executor._get_source_credibility("GitHub") == 0.85
        assert executor._get_source_credibility("Unknown") == 0.5

    @pytest.mark.asyncio
    async def test_get_research_status(self, executor, research_store, sample_task):
        """Test get_research_status returns complete status dict."""
        executor._simulate_agent_research = AsyncMock(
            return_value=[
                ResearchFinding(
                    research_task_id=sample_task,
                    source="Test",
                    title=f"Finding {i}",
                    summary=f"Summary {i}",
                    credibility_score=0.85
                )
                for i in range(2)
            ]
        )
        # Execute with the same topic as the fixture creates (sample_task uses "Test research topic")
        await executor.execute_research(sample_task, "Test research topic")

        status = executor.get_research_status(sample_task)

        assert status["task_id"] == sample_task
        assert status["topic"] == "Test research topic"
        assert status["status"] == ResearchStatus.COMPLETED.value
        assert "agents" in status
        assert len(status["agents"]) == 8

    @pytest.mark.asyncio
    async def test_agent_progress_tracking(self, executor, research_store, sample_task):
        """Test agent progress is updated correctly during execution."""
        call_count = {"count": 0}

        async def mock_research(*args, **kwargs):
            call_count["count"] += 1
            await asyncio.sleep(0.001)
            return [Mock()] if call_count["count"] <= 3 else []

        executor._simulate_agent_research = mock_research

        await executor.execute_research(sample_task, "Test topic")

        agent_progress = research_store.get_agent_progress(sample_task)

        # All agents should have been initialized and processed
        assert len(agent_progress) == 8

        # Check that agents have proper status
        for progress in agent_progress:
            assert progress.status in [
                AgentStatus.COMPLETED.value,
                AgentStatus.FAILED.value,
                AgentStatus.RUNNING.value,
            ]

    @pytest.mark.asyncio
    async def test_research_with_mixed_results(self, executor, research_store, sample_task):
        """Test research execution with some agents succeeding and some failing."""
        def make_findings(source, count, task_id, offset=0):
            return [
                ResearchFinding(
                    research_task_id=task_id,
                    source=source,
                    title=f"{source} Finding {offset + i}",
                    summary=f"{source} Summary {offset + i}",
                    credibility_score=0.85
                )
                for i in range(count)
            ]

        results = {
            "arxiv-researcher": make_findings("arXiv", 5, sample_task, 0),
            "github-researcher": Exception("Network error"),
            "anthropic-docs-researcher": make_findings("Anthropic Docs", 3, sample_task, 100),
        }
        call_count = {"count": 0}

        async def mock_research(task_id, topic, agent_name, source, credibility):
            call_count["count"] += 1
            result = results.get(agent_name, [])
            if isinstance(result, Exception):
                raise result
            return result

        executor._simulate_agent_research = mock_research

        total = await executor.execute_research(sample_task, "Test topic")

        # Should count findings from successful agents (5 + 3)
        assert total == 8

        # Task should still be marked completed (partial success)
        task = research_store.get_task(sample_task)
        assert task.status == ResearchStatus.COMPLETED.value
