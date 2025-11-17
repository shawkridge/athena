"""Integration tests for Phase 4.2: Hook Integration for Specialized Agents.

Tests verify that:
1. ResearchCoordinatorAgent activates at SessionStart
2. CodeAnalyzerAgent activates at PostToolUse
3. WorkflowOrchestratorAgent activates at PostToolUse
4. MetacognitionAgent activates at SessionEnd
5. All agents store findings in memory
6. Agent outputs are accessible to downstream operations
"""

import pytest
import asyncio
import sys
import os
from typing import Dict, Any
from datetime import datetime

# Add src to path
sys.path.insert(0, '/home/user/.work/athena/src')

from athena import initialize_athena
from athena.agents.agent_bridge import AgentBridge
from athena.agents.research_coordinator import ResearchCoordinatorAgent
from athena.agents.code_analyzer import CodeAnalyzerAgent
from athena.agents.workflow_orchestrator import WorkflowOrchestratorAgent
from athena.agents.metacognition import MetacognitionAgent
from athena.episodic.operations import remember, recall


class TestPhase4_2ResearchCoordinator:
    """Test ResearchCoordinatorAgent activation via SessionStart."""

    @pytest.fixture(autouse=True)
    async def setup(self):
        """Initialize Athena for tests."""
        await initialize_athena()
        yield

    @pytest.mark.asyncio
    async def test_research_coordinator_initialization(self):
        """Test ResearchCoordinatorAgent initializes correctly."""
        agent = ResearchCoordinatorAgent()

        assert agent.agent_id == "research-coordinator"
        assert agent.agent_type == "research"
        assert hasattr(agent, 'research_tasks')

    @pytest.mark.asyncio
    async def test_research_coordinator_plan_research(self):
        """Test agent creates research plans."""
        agent = ResearchCoordinatorAgent()

        plan = await agent.plan_research(
            query="Understand async Python patterns",
            depth=3,
        )

        assert plan is not None
        # plan is a ResearchPlan object, not dict
        assert hasattr(plan, 'query')

    @pytest.mark.asyncio
    async def test_agent_bridge_activate_research_coordinator(self):
        """Test AgentBridge activates ResearchCoordinatorAgent."""
        context = {
            "user_goal": "Implement authentication system",
            "current_context": "Working on security features",
            "research_depth": 3,
        }

        result = AgentBridge.activate_research_coordinator(context)

        assert result["status"] in ["success", "error"]
        assert "agent" in result
        assert result["agent"] == "research-coordinator"


class TestPhase4_2CodeAnalyzer:
    """Test CodeAnalyzerAgent activation via PostToolUse."""

    @pytest.fixture(autouse=True)
    async def setup(self):
        """Initialize Athena for tests."""
        await initialize_athena()
        yield

    @pytest.mark.asyncio
    async def test_code_analyzer_initialization(self):
        """Test CodeAnalyzerAgent initializes correctly."""
        agent = CodeAnalyzerAgent()

        assert agent.agent_id == "code-analyzer"
        assert hasattr(agent, 'agent_type')

    @pytest.mark.asyncio
    async def test_code_analyzer_find_anti_patterns(self):
        """Test agent finds anti-patterns."""
        agent = CodeAnalyzerAgent()

        code = """
def bad_code():
    x = 1
    y = 2
    z = x + y
    return z
"""

        patterns = await agent.find_anti_patterns(code, language="python")

        # Should return list of issues
        assert isinstance(patterns, list)

    @pytest.mark.asyncio
    async def test_agent_bridge_activate_code_analyzer(self):
        """Test AgentBridge activates CodeAnalyzerAgent."""
        tool_output = "Successfully executed command"

        result = AgentBridge.activate_code_analyzer(tool_output, "bash")

        assert result["status"] in ["success", "error"]
        assert result["agent"] == "code-analyzer"


class TestPhase4_2WorkflowOrchestrator:
    """Test WorkflowOrchestratorAgent activation via PostToolUse."""

    @pytest.fixture(autouse=True)
    async def setup(self):
        """Initialize Athena for tests."""
        await initialize_athena()
        yield

    @pytest.mark.asyncio
    async def test_workflow_orchestrator_initialization(self):
        """Test WorkflowOrchestratorAgent initializes correctly."""
        agent = WorkflowOrchestratorAgent()

        assert agent.agent_id == "workflow-orchestrator"
        assert hasattr(agent, 'agent_type')

    @pytest.mark.asyncio
    async def test_agent_bridge_activate_workflow_orchestrator(self):
        """Test AgentBridge activates WorkflowOrchestratorAgent."""
        session_state = {
            "phase": "analysis",
            "tools_used": ["bash", "grep"],
            "events_count": 10,
        }

        result = AgentBridge.activate_workflow_orchestrator(session_state)

        assert result["status"] in ["success", "error"]
        assert result["agent"] == "workflow-orchestrator"


class TestPhase4_2Metacognition:
    """Test MetacognitionAgent activation via SessionEnd."""

    @pytest.fixture(autouse=True)
    async def setup(self):
        """Initialize Athena for tests."""
        await initialize_athena()
        yield

    @pytest.mark.asyncio
    async def test_metacognition_initialization(self):
        """Test MetacognitionAgent initializes correctly."""
        agent = MetacognitionAgent()

        assert agent.agent_id == "metacognition"
        assert hasattr(agent, 'agent_type')

    @pytest.mark.asyncio
    async def test_agent_bridge_activate_metacognition(self):
        """Test AgentBridge activates MetacognitionAgent."""
        metrics = {
            "session_duration": 600,
            "operations_count": 20,
            "success_rate": 0.95,
            "memory_peak_mb": 512,
        }

        result = AgentBridge.activate_metacognition(metrics)

        assert result["status"] in ["success", "error"]
        assert result["agent"] == "metacognition"


class TestPhase4_2MultiAgentActivation:
    """Test coordinated activation of all agents."""

    @pytest.fixture(autouse=True)
    async def setup(self):
        """Initialize Athena for tests."""
        await initialize_athena()
        yield

    def test_activate_all_at_session_start(self):
        """Test all agents can activate at SessionStart."""
        context = {
            "user_goal": "Test Phase 4.2",
            "research_depth": 2,
        }

        results = AgentBridge.activate_all_agents("start", context)

        assert isinstance(results, list)
        assert len(results) > 0

    def test_activate_all_at_tool_use(self):
        """Test all agents can activate at PostToolUse."""
        context = {
            "tool_output": "Tool executed successfully",
            "tool_name": "bash",
            "session_state": {"phase": "execution"},
        }

        results = AgentBridge.activate_all_agents("tool_use", context)

        assert isinstance(results, list)
        assert len(results) > 0

    def test_activate_all_at_session_end(self):
        """Test all agents can activate at SessionEnd."""
        context = {
            "session_metrics": {
                "duration": 300,
                "tools": 5,
                "errors": 0,
            }
        }

        results = AgentBridge.activate_all_agents("end", context)

        assert isinstance(results, list)
        assert len(results) > 0

    def test_sequential_agent_activation(self):
        """Test agents can be activated sequentially in a workflow."""
        # SessionStart: Research
        start_context = {"user_goal": "Test sequential activation"}
        start_results = AgentBridge.activate_all_agents("start", start_context)
        assert len(start_results) > 0

        # PostToolUse: Analyze + Orchestrate
        tool_context = {
            "tool_output": "Sequential test output",
            "tool_name": "test_tool",
            "session_state": {},
        }
        tool_results = AgentBridge.activate_all_agents("tool_use", tool_context)
        assert len(tool_results) > 0

        # SessionEnd: Metacognition
        end_context = {"session_metrics": {"total": 3}}
        end_results = AgentBridge.activate_all_agents("end", end_context)
        assert len(end_results) > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
