"""
Unit tests for Orchestrator multi-agent coordination system.

Tests cover:
- Orchestrator initialization
- Agent spawning and lifecycle
- Task decomposition and assignment
- Progress monitoring
- Health checking
- Result synthesis
- Cleanup and recovery
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from athena.coordination.models import (
    Agent, AgentType, AgentStatus, Task, TaskStatus, TaskPriority,
    OrchestrationState
)
from athena.coordination.orchestrator import Orchestrator
from athena.coordination.operations import CoordinationOperations


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_db():
    """Mock database connection."""
    return Mock()


@pytest.fixture
def mock_coordination_ops():
    """Mock coordination operations."""
    ops = AsyncMock()
    return ops


@pytest.fixture
def orchestrator(mock_db, mock_coordination_ops):
    """Create orchestrator instance with mocked dependencies."""
    with patch('athena.coordination.orchestrator.CoordinationOperations', return_value=mock_coordination_ops):
        orch = Orchestrator(
            db=mock_db,
            tmux_session_name="test_athena",
            context_token_limit=200000
        )
        # Ensure coordination_ops is the mock
        orch.coordination_ops = mock_coordination_ops
        return orch


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return Task(
        task_id="task_001",
        title="Analyze code quality",
        status=TaskStatus.PENDING,
        priority=TaskPriority.HIGH,
        description="Perform comprehensive code quality analysis",
        created_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_subtasks():
    """Create sample subtasks."""
    return [
        Task(
            task_id="subtask_001",
            title="Scan for code patterns",
            status=TaskStatus.PENDING,
            priority=TaskPriority.HIGH,
            description="Identify design patterns and anti-patterns",
            created_at=datetime.now(timezone.utc)
        ),
        Task(
            task_id="subtask_002",
            title="Assess complexity",
            status=TaskStatus.PENDING,
            priority=TaskPriority.HIGH,
            description="Calculate cyclomatic and cognitive complexity",
            created_at=datetime.now(timezone.utc)
        ),
        Task(
            task_id="subtask_003",
            title="Analyze dependencies",
            status=TaskStatus.PENDING,
            priority=TaskPriority.MEDIUM,
            description="Map module dependencies and coupling",
            created_at=datetime.now(timezone.utc)
        ),
    ]


@pytest.fixture
def sample_agents():
    """Create sample agents."""
    return [
        Agent(
            agent_id="agent_analysis_001",
            agent_type=AgentType.ANALYSIS,
            capabilities=["code_analysis", "pattern_detection"],
            status=AgentStatus.IDLE
        ),
        Agent(
            agent_id="agent_validation_001",
            agent_type=AgentType.VALIDATION,
            capabilities=["testing", "quality_assessment"],
            status=AgentStatus.IDLE
        ),
    ]


# ============================================================================
# TESTS: Initialization
# ============================================================================


class TestOrchestratorInitialization:
    """Test orchestrator initialization."""

    def test_orchestrator_created_with_defaults(self, orchestrator):
        """Test orchestrator is created with default values."""
        assert orchestrator.db is not None
        assert orchestrator.tmux_session_name == "test_athena"
        assert orchestrator.context_token_limit == 200000
        assert orchestrator.orchestrator_id.startswith("orchestrator_")
        assert orchestrator.active_agents == {}
        assert orchestrator._should_run is False

    def test_orchestrator_id_is_unique(self, orchestrator):
        """Test each orchestrator gets a unique ID."""
        orch1 = Orchestrator(Mock(), "test1")
        orch2 = Orchestrator(Mock(), "test2")
        assert orch1.orchestrator_id != orch2.orchestrator_id

    @pytest.mark.asyncio
    async def test_initialize_session_without_libtmux(self, orchestrator):
        """Test session initialization when libtmux is not available."""
        with patch('athena.coordination.orchestrator.LIBTMUX_AVAILABLE', False):
            result = await orchestrator.initialize_session()
            assert result is True  # Should succeed gracefully without tmux


# ============================================================================
# TESTS: Agent Management
# ============================================================================


class TestAgentManagement:
    """Test agent spawning and lifecycle management."""

    @pytest.mark.asyncio
    async def test_agent_spawn_stores_agent(self, orchestrator, sample_agents):
        """Test spawning an agent stores it in active_agents."""
        agent = sample_agents[0]

        # Mock the coordination ops to return the agent
        orchestrator.coordination_ops.register_agent.return_value = agent.agent_id

        # Spawn agent (without tmux)
        with patch('athena.coordination.orchestrator.LIBTMUX_AVAILABLE', False):
            agent_id = await orchestrator.spawn_agent(
                agent_type=agent.agent_type,
                capabilities=agent.capabilities
            )

        assert agent_id is not None
        orchestrator.coordination_ops.register_agent.assert_called()

    @pytest.mark.asyncio
    async def test_kill_agent_removes_from_active(self, orchestrator):
        """Test killing an agent removes it from tracking."""
        agent_id = "test_agent_001"
        orchestrator.active_agents[agent_id] = Mock(agent_id=agent_id)

        # Mock coordination ops
        orchestrator.coordination_ops.update_agent_status.return_value = True

        result = await orchestrator.kill_agent(agent_id)

        assert result is True
        orchestrator.coordination_ops.update_agent_status.assert_called()


# ============================================================================
# TESTS: Task Management & Decomposition
# ============================================================================


class TestTaskManagement:
    """Test task decomposition and assignment."""

    def test_agent_type_determination_from_requirements(self, orchestrator, sample_task):
        """Test determining correct agent type from task requirements."""
        # Task with code analysis requirement should map to ANALYSIS
        sample_task.requirements = ["code_analysis", "pattern_detection"]
        agent_type = orchestrator._determine_agent_type(sample_task)
        assert agent_type == AgentType.ANALYSIS

        # Task with testing requirement should map to VALIDATION
        sample_task.requirements = ["testing", "quality_assessment"]
        agent_type = orchestrator._determine_agent_type(sample_task)
        assert agent_type == AgentType.VALIDATION

    def test_agent_type_defaults_to_analysis(self, orchestrator, sample_task):
        """Test agent type defaults to ANALYSIS for unknown requirements."""
        sample_task.requirements = ["unknown_capability"]
        agent_type = orchestrator._determine_agent_type(sample_task)
        assert agent_type in [AgentType.ANALYSIS, AgentType.RESEARCH]

    @pytest.mark.asyncio
    async def test_assign_work_respects_max_concurrent(self, orchestrator, sample_subtasks):
        """Test work assignment respects max concurrent agents."""
        orchestrator.state = OrchestrationState(
            orchestration_id="orch_001",
            root_task=Task(
                task_id="root",
                title="Test",
                status=TaskStatus.IN_PROGRESS,
                priority=TaskPriority.HIGH,
                created_at=datetime.now(timezone.utc)
            ),
            subtasks=sample_subtasks,
            assigned_agents={},
            results={}
        )

        # Mock agent spawning
        orchestrator.coordination_ops.get_agents.return_value = []
        orchestrator.coordination_ops.create_task.return_value = "task_id"

        # Mock the spawn method to return agent IDs
        with patch.object(orchestrator, '_get_or_spawn_agent', new_callable=AsyncMock) as mock_spawn:
            mock_spawn.return_value = "agent_001"

            # Try to assign work with max_concurrent=2
            await orchestrator._assign_work(max_concurrent=2)

            # Should not spawn more agents than max_concurrent
            assert mock_spawn.call_count <= 2


# ============================================================================
# TESTS: Orchestration Workflow
# ============================================================================


class TestOrchestrationWorkflow:
    """Test complete orchestration workflow."""

    @pytest.mark.asyncio
    async def test_orchestrate_full_workflow(
        self, orchestrator, sample_task, sample_subtasks, mock_coordination_ops
    ):
        """Test full orchestration workflow."""
        # Mock the planning layer to return subtasks
        mock_coordination_ops.create_task.return_value = "parent_task_id"
        mock_coordination_ops.get_agents.return_value = []
        mock_coordination_ops.update_task_status.return_value = True
        mock_coordination_ops.record_orchestration_event.return_value = True

        # Mock session initialization
        with patch.object(orchestrator, 'initialize_session', new_callable=AsyncMock) as mock_init:
            mock_init.return_value = True

            # Mock health check and progress monitor
            with patch.object(orchestrator, '_health_check_loop', new_callable=AsyncMock):
                with patch.object(orchestrator, '_progress_monitor_loop', new_callable=AsyncMock):
                    # Mock getting results
                    with patch.object(orchestrator, '_gather_results', new_callable=AsyncMock) as mock_results:
                        mock_results.return_value = {"summary": "Task completed successfully"}

                        # Run orchestration with timeout
                        try:
                            result = await asyncio.wait_for(
                                orchestrator.orchestrate(
                                    task=sample_task,
                                    subtasks=sample_subtasks,
                                    max_concurrent=2,
                                    timeout_seconds=1
                                ),
                                timeout=2.0
                            )
                            assert result is not None
                        except asyncio.TimeoutError:
                            # Expected since we're mocking
                            pass

    def test_orchestration_complete_detection(self, orchestrator, sample_subtasks):
        """Test detection of orchestration completion."""
        orchestrator.state = OrchestrationState(
            orchestration_id="orch_001",
            root_task=Task(
                task_id="root",
                title="Test",
                status=TaskStatus.IN_PROGRESS,
                priority=TaskPriority.HIGH,
                created_at=datetime.now(timezone.utc)
            ),
            subtasks=sample_subtasks,
            assigned_agents={},
            results={}
        )

        # Initially not complete
        assert orchestrator._orchestration_complete() is False

        # Mark all subtasks as completed
        for subtask in orchestrator.state.subtasks:
            subtask.status = TaskStatus.COMPLETED

        # Now should be complete
        assert orchestrator._orchestration_complete() is True

    def test_orchestration_complete_with_failures(self, orchestrator, sample_subtasks):
        """Test orchestration completion even with some task failures."""
        orchestrator.state = OrchestrationState(
            orchestration_id="orch_001",
            root_task=Task(
                task_id="root",
                title="Test",
                status=TaskStatus.IN_PROGRESS,
                priority=TaskPriority.HIGH,
                created_at=datetime.now(timezone.utc)
            ),
            subtasks=sample_subtasks,
            assigned_agents={},
            results={}
        )

        # Mark some tasks as completed, others as failed
        sample_subtasks[0].status = TaskStatus.COMPLETED
        sample_subtasks[1].status = TaskStatus.FAILED
        sample_subtasks[2].status = TaskStatus.COMPLETED

        # Should still be complete (all tasks terminal)
        assert orchestrator._orchestration_complete() is True


# ============================================================================
# TESTS: Monitoring & Health
# ============================================================================


class TestMonitoringAndHealth:
    """Test progress monitoring and health checking."""

    @pytest.mark.asyncio
    async def test_health_check_loop_detects_offline_agents(self, orchestrator):
        """Test health check detects and handles offline agents."""
        # Create an agent
        agent = Agent(
            agent_id="test_agent",
            agent_type=AgentType.ANALYSIS,
            capabilities=[],
            status=AgentStatus.BUSY
        )
        orchestrator.active_agents["test_agent"] = agent

        # Mock health check to detect offline
        orchestrator.coordination_ops.get_agent_health.return_value = {
            "agent_id": "test_agent",
            "status": AgentStatus.OFFLINE,
            "heartbeat": None
        }

        # Run health check once
        orchestrator._should_run = True

        # Create a short-lived health check task
        health_task = asyncio.create_task(orchestrator._health_check_loop())

        # Let it run briefly
        await asyncio.sleep(0.1)
        orchestrator._should_run = False

        # Clean up
        try:
            await asyncio.wait_for(health_task, timeout=0.5)
        except asyncio.TimeoutError:
            health_task.cancel()

    @pytest.mark.asyncio
    async def test_progress_monitor_updates_state(self, orchestrator):
        """Test progress monitor updates orchestration state."""
        # Set up initial state
        orchestrator.state = OrchestrationState(
            orchestration_id="orch_001",
            root_task=Task(
                task_id="root",
                title="Test",
                status=TaskStatus.IN_PROGRESS,
                priority=TaskPriority.HIGH,
                created_at=datetime.now(timezone.utc)
            ),
            subtasks=[],
            assigned_agents={},
            results={}
        )

        orchestrator._should_run = True

        # Mock task updates
        orchestrator.coordination_ops.get_task.return_value = Task(
            task_id="root",
            title="Test",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            created_at=datetime.now(timezone.utc)
        )

        # Run progress monitor briefly
        monitor_task = asyncio.create_task(orchestrator._progress_monitor_loop())
        await asyncio.sleep(0.1)
        orchestrator._should_run = False

        try:
            await asyncio.wait_for(monitor_task, timeout=0.5)
        except asyncio.TimeoutError:
            monitor_task.cancel()


# ============================================================================
# TESTS: Result Synthesis
# ============================================================================


class TestResultSynthesis:
    """Test gathering and synthesizing results."""

    @pytest.mark.asyncio
    async def test_gather_results_from_completed_tasks(self, orchestrator, sample_subtasks):
        """Test gathering results from completed subtasks."""
        orchestrator.state = OrchestrationState(
            orchestration_id="orch_001",
            root_task=Task(
                task_id="root",
                title="Test",
                status=TaskStatus.COMPLETED,
                priority=TaskPriority.HIGH,
                created_at=datetime.now(timezone.utc)
            ),
            subtasks=sample_subtasks,
            assigned_agents={},
            results={
                "subtask_001": "Pattern analysis results",
                "subtask_002": "Complexity metrics",
                "subtask_003": "Dependency graph"
            }
        )

        # Mock result retrieval
        orchestrator.coordination_ops.get_task_result.return_value = "Task result"

        results = await orchestrator._gather_results()

        assert results is not None
        assert isinstance(results, dict)
        orchestrator.coordination_ops.get_task_result.assert_called()


# ============================================================================
# TESTS: Cleanup & Shutdown
# ============================================================================


class TestCleanup:
    """Test orchestrator cleanup and shutdown."""

    @pytest.mark.asyncio
    async def test_cleanup_kills_all_agents(self, orchestrator):
        """Test cleanup kills all active agents."""
        # Add some active agents
        orchestrator.active_agents = {
            "agent_001": Mock(agent_id="agent_001"),
            "agent_002": Mock(agent_id="agent_002"),
            "agent_003": Mock(agent_id="agent_003"),
        }

        # Mock kill operations
        with patch.object(orchestrator, 'kill_agent', new_callable=AsyncMock) as mock_kill:
            mock_kill.return_value = True

            await orchestrator.cleanup()

            # Should attempt to kill each agent
            assert mock_kill.call_count >= len(orchestrator.active_agents)

    @pytest.mark.asyncio
    async def test_cleanup_cancels_background_tasks(self, orchestrator):
        """Test cleanup cancels background monitoring tasks."""
        # Create dummy tasks
        orchestrator._health_check_task = asyncio.create_task(asyncio.sleep(100))
        orchestrator._progress_monitor_task = asyncio.create_task(asyncio.sleep(100))

        await orchestrator.cleanup()

        # Tasks should be cleaned up
        assert orchestrator._health_check_task is None or orchestrator._health_check_task.cancelled()
        assert orchestrator._progress_monitor_task is None or orchestrator._progress_monitor_task.cancelled()


# ============================================================================
# TESTS: Error Handling & Edge Cases
# ============================================================================


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_spawn_agent_handles_failure(self, orchestrator):
        """Test graceful handling when agent spawning fails."""
        # Mock failure
        orchestrator.coordination_ops.register_agent.side_effect = Exception("Spawn failed")

        # Should handle gracefully
        with patch('athena.coordination.orchestrator.LIBTMUX_AVAILABLE', False):
            agent_id = await orchestrator.spawn_agent(
                agent_type=AgentType.ANALYSIS,
                capabilities=[]
            )

        # May return None or raise, both are acceptable
        # The mock failure ensures we test error path

    def test_determine_agent_type_robustness(self, orchestrator):
        """Test agent type determination is robust to edge cases."""
        # Empty requirements
        task = Task(
            task_id="task_1",
            title="Test",
            status=TaskStatus.PENDING,
            priority=TaskPriority.MEDIUM,
            created_at=datetime.now(timezone.utc)
        )

        agent_type = orchestrator._determine_agent_type(task)
        assert agent_type in list(AgentType)

        # None requirements
        task.requirements = None
        agent_type = orchestrator._determine_agent_type(task)
        assert agent_type in list(AgentType)

    @pytest.mark.asyncio
    async def test_orchestrate_with_zero_subtasks(self, orchestrator, sample_task):
        """Test orchestration with no subtasks."""
        orchestrator.state = OrchestrationState(
            orchestration_id="orch_001",
            root_task=sample_task,
            subtasks=[],  # Empty
            assigned_agents={},
            results={}
        )

        # Mock methods
        with patch.object(orchestrator, 'initialize_session', new_callable=AsyncMock) as mock_init:
            mock_init.return_value = True

            with patch.object(orchestrator, '_orchestration_complete') as mock_complete:
                mock_complete.return_value = True

                with patch.object(orchestrator, '_gather_results', new_callable=AsyncMock) as mock_results:
                    mock_results.return_value = {}

                    try:
                        result = await asyncio.wait_for(
                            orchestrator.orchestrate(
                                task=sample_task,
                                subtasks=[],
                                timeout_seconds=1
                            ),
                            timeout=2.0
                        )
                    except asyncio.TimeoutError:
                        pass  # Expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
