"""
Integration tests for Orchestrator multi-agent system.

Tests the orchestrator with realistic scenarios.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

from athena.coordination.models import (
    Agent, AgentType, AgentStatus, Task, TaskStatus, TaskPriority
)
from athena.coordination.orchestrator import Orchestrator


# ============================================================================
# BASIC ORCHESTRATOR TESTS
# ============================================================================


class TestOrchestratorBasics:
    """Test basic orchestrator functionality."""

    def test_orchestrator_creates_with_id(self):
        """Test orchestrator is created with unique ID."""
        orch1 = Orchestrator(Mock())
        orch2 = Orchestrator(Mock())

        assert orch1.orchestrator_id is not None
        assert orch2.orchestrator_id is not None
        assert orch1.orchestrator_id != orch2.orchestrator_id
        assert orch1.orchestrator_id.startswith("orchestrator_")

    def test_orchestrator_starts_empty(self):
        """Test orchestrator starts with no active agents."""
        orch = Orchestrator(Mock())

        assert orch.active_agents == {}
        assert orch.state is None
        assert orch._should_run is False

    def test_context_token_limit_configurable(self):
        """Test context token limit is configurable."""
        orch = Orchestrator(Mock(), context_token_limit=100000)
        assert orch.context_token_limit == 100000

        orch2 = Orchestrator(Mock(), context_token_limit=50000)
        assert orch2.context_token_limit == 50000


# ============================================================================
# AGENT TYPE DETECTION
# ============================================================================


class TestAgentTypeDetection:
    """Test agent type determination from task requirements."""

    def test_get_orchestrator(self):
        """Test we can create an orchestrator."""
        orch = Orchestrator(Mock())
        assert orch is not None

    def test_agent_type_enum_complete(self):
        """Test all agent types are defined."""
        expected_types = [
            'research', 'analysis', 'synthesis', 'validation',
            'optimization', 'documentation', 'code_review',
            'debugging', 'testing'
        ]

        actual_types = [t.value for t in AgentType]

        for expected in expected_types:
            assert expected in actual_types, f"Missing agent type: {expected}"

    def test_agent_type_values_unique(self):
        """Test all agent type values are unique."""
        values = [t.value for t in AgentType]
        assert len(values) == len(set(values)), "Agent type values are not unique"


# ============================================================================
# AGENT SPAWNING
# ============================================================================


class TestAgentSpawning:
    """Test agent spawning and lifecycle."""

    @pytest.mark.asyncio
    async def test_spawn_agent_without_tmux(self):
        """Test agent spawning gracefully handles missing tmux."""
        orch = Orchestrator(Mock())

        # Disable tmux
        with patch('athena.coordination.orchestrator.LIBTMUX_AVAILABLE', False):
            # Should not crash even without tmux
            await orch.initialize_session()
            assert True  # If we get here, it didn't crash

    def test_agent_status_tracking(self):
        """Test agent status values are valid."""
        statuses = [s.value for s in AgentStatus]
        assert 'idle' in statuses
        assert 'busy' in statuses
        assert 'failed' in statuses
        assert 'offline' in statuses


# ============================================================================
# TASK MANAGEMENT
# ============================================================================


class TestTaskManagement:
    """Test task creation and status management."""

    def test_create_valid_task(self):
        """Test creating a valid task."""
        task = Task(
            task_id="test_task_1",
            title="Test task",
            description="A test task",
            status=TaskStatus.PENDING,
            priority=TaskPriority.MEDIUM
        )

        assert task.task_id == "test_task_1"
        assert task.title == "Test task"
        assert task.status == TaskStatus.PENDING
        assert task.is_pending()
        assert not task.is_active()
        assert not task.is_completed()

    def test_task_status_transitions(self):
        """Test task status can transition properly."""
        task = Task(
            task_id="test_1",
            title="Task",
            description="Description"
        )

        assert task.status == TaskStatus.PENDING

        task.status = TaskStatus.IN_PROGRESS
        assert task.is_active()
        assert not task.is_completed()

        task.status = TaskStatus.COMPLETED
        assert task.is_completed()
        assert not task.is_active()

    def test_task_priority_levels(self):
        """Test all priority levels exist."""
        priorities = [p.value for p in TaskPriority]
        assert 'CRITICAL' in priorities
        assert 'HIGH' in priorities
        assert 'MEDIUM' in priorities
        assert 'LOW' in priorities


# ============================================================================
# ORCHESTRATION STATE
# ============================================================================


class TestOrchestrationState:
    """Test orchestration state management."""

    def test_create_valid_agent(self):
        """Test creating a valid agent."""
        agent = Agent(
            agent_id="agent_001",
            agent_type=AgentType.ANALYSIS,
            capabilities=["code_analysis", "pattern_detection"],
            status=AgentStatus.IDLE
        )

        assert agent.agent_id == "agent_001"
        assert agent.agent_type == AgentType.ANALYSIS
        assert len(agent.capabilities) == 2
        assert agent.status == AgentStatus.IDLE

    def test_agent_capability_assignment(self):
        """Test agents can have capabilities assigned."""
        agent = Agent(
            agent_id="test_agent",
            agent_type=AgentType.RESEARCH
        )

        # Should support empty capabilities
        assert agent.capabilities == []

        agent.capabilities = ["web_search", "documentation"]
        assert "web_search" in agent.capabilities
        assert len(agent.capabilities) == 2


# ============================================================================
# REAL-WORLD SCENARIO TESTS
# ============================================================================


class TestRealWorldScenarios:
    """Test realistic orchestration scenarios."""

    def test_code_review_scenario_agents(self):
        """Test agents needed for code review scenario."""
        # A code review would need these agents
        needed_types = {AgentType.ANALYSIS, AgentType.CODE_REVIEW, AgentType.TESTING}

        for agent_type in needed_types:
            assert agent_type in AgentType  # All exist

    def test_documentation_scenario_agents(self):
        """Test agents needed for documentation scenario."""
        # Documentation might need these agents
        needed_types = {
            AgentType.ANALYSIS,
            AgentType.DOCUMENTATION,
            AgentType.SYNTHESIS,
            AgentType.VALIDATION
        }

        for agent_type in needed_types:
            assert agent_type in AgentType

    def test_research_scenario_agents(self):
        """Test agents needed for research scenario."""
        needed_types = {
            AgentType.RESEARCH,
            AgentType.SYNTHESIS,
            AgentType.VALIDATION
        }

        for agent_type in needed_types:
            assert agent_type in AgentType

    @pytest.mark.asyncio
    async def test_orchestrator_initialization_flow(self):
        """Test complete orchestrator initialization."""
        orch = Orchestrator(Mock(), tmux_session_name="test")

        # Initialize without tmux (to avoid dependencies)
        with patch('athena.coordination.orchestrator.LIBTMUX_AVAILABLE', False):
            result = await orch.initialize_session()
            assert result is True


# ============================================================================
# CLEANUP & SHUTDOWN
# ============================================================================


class TestCleanup:
    """Test cleanup and shutdown."""

    @pytest.mark.asyncio
    async def test_orchestrator_cleanup(self):
        """Test orchestrator can be cleaned up."""
        orch = Orchestrator(Mock())
        orch.active_agents = {
            "agent_1": Mock(agent_id="agent_1"),
            "agent_2": Mock(agent_id="agent_2"),
        }

        # Should handle cleanup without crashing
        try:
            await orch.cleanup()
            assert True  # Success
        except Exception as e:
            pytest.fail(f"Cleanup failed with: {e}")

    @pytest.mark.asyncio
    async def test_orchestrator_with_no_agents_cleanup(self):
        """Test cleanup works even with no active agents."""
        orch = Orchestrator(Mock())

        # Should not crash
        await orch.cleanup()
        assert orch._should_run is False


# ============================================================================
# MODEL CONSISTENCY
# ============================================================================


class TestModelConsistency:
    """Test that models are internally consistent."""

    def test_task_status_enum_complete(self):
        """Test all required task statuses exist."""
        statuses = [s.value for s in TaskStatus]
        assert 'PENDING' in statuses
        assert 'IN_PROGRESS' in statuses
        assert 'COMPLETED' in statuses
        assert 'FAILED' in statuses

    def test_agent_type_count(self):
        """Test correct number of agent types."""
        agent_types = list(AgentType)
        # Should have at least 8 agent types
        assert len(agent_types) >= 8

    def test_agent_and_task_independence(self):
        """Test agents and tasks are independent models."""
        agent = Agent(
            agent_id="a1",
            agent_type=AgentType.ANALYSIS
        )

        task = Task(
            task_id="t1",
            title="Task",
            description="Desc"
        )

        # Should be completely independent
        assert agent.agent_id != task.task_id
        assert type(agent).__name__ != type(task).__name__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
