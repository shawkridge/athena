"""Tests for web research agents and orchestrator."""

import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.fixture
def research_orchestrator():
    """Create research orchestrator for testing."""
    from athena.research.research_orchestrator import (
        ResearchOrchestrator,
        ResearchMode,
    )
    return ResearchOrchestrator(mode=ResearchMode.MOCK_ONLY)


@pytest.mark.asyncio
async def test_orchestrator_init(research_orchestrator):
    """Test orchestrator initialization."""
    assert research_orchestrator.mode.value == "mock_only"
    assert research_orchestrator.timeout == 30
    assert len(research_orchestrator.mock_agents) > 0


@pytest.mark.asyncio
async def test_orchestrator_mock_research(research_orchestrator):
    """Test research with mock agents."""
    results = await research_orchestrator.research(
        "async patterns",
        use_real=False,
        use_mock=True,
        parallel=True,
    )

    assert isinstance(results, dict)
    assert len(results) > 0
    # Check that we got findings from mock agents
    for agent_name, findings in results.items():
        assert isinstance(findings, list)
        if findings:
            finding = findings[0]
            assert "title" in finding
            assert "summary" in finding
            assert "credibility" in finding


@pytest.mark.asyncio
async def test_orchestrator_timeout_handling(research_orchestrator):
    """Test orchestrator handles timeouts gracefully."""
    research_orchestrator.timeout = 0.001  # Very short timeout

    results = await research_orchestrator.research(
        "test topic",
        use_real=False,
        use_mock=True,
        parallel=True,
    )

    # Should still return a dict, possibly with empty findings
    assert isinstance(results, dict)


@pytest.mark.asyncio
async def test_orchestrator_stats():
    """Test orchestrator statistics."""
    from athena.research.research_orchestrator import (
        ResearchOrchestrator,
        ResearchMode,
    )

    orchestrator = ResearchOrchestrator(mode=ResearchMode.MOCK_ONLY)
    stats = orchestrator.get_agent_stats()

    assert "mode" in stats
    assert "total_agents" in stats
    assert "mock_agents_available" in stats
    assert stats["mode"] == "mock_only"


@pytest.mark.asyncio
async def test_research_modes():
    """Test different research modes."""
    from athena.research.research_orchestrator import (
        ResearchOrchestrator,
        ResearchMode,
    )

    modes = [
        ResearchMode.MOCK_ONLY,
        ResearchMode.OFFLINE,
    ]

    for mode in modes:
        orchestrator = ResearchOrchestrator(mode=mode)
        assert orchestrator.mode == mode
        results = await orchestrator.research("test topic")
        assert isinstance(results, dict)


@pytest.mark.asyncio
async def test_parallel_vs_sequential():
    """Test parallel vs sequential research execution."""
    from athena.research.research_orchestrator import (
        ResearchOrchestrator,
        ResearchMode,
    )

    orchestrator = ResearchOrchestrator(mode=ResearchMode.MOCK_ONLY)

    # Parallel execution
    parallel_results = await orchestrator.research(
        "test topic",
        use_real=False,
        use_mock=True,
        parallel=True,
    )

    # Sequential execution
    sequential_results = await orchestrator.research(
        "test topic",
        use_real=False,
        use_mock=True,
        parallel=False,
    )

    # Should get results from both
    assert isinstance(parallel_results, dict)
    assert isinstance(sequential_results, dict)


def test_web_research_agents_exist():
    """Test that web research agents are defined."""
    try:
        from athena.research.web_research import WEB_RESEARCH_AGENTS
        assert len(WEB_RESEARCH_AGENTS) > 0
        expected_agents = [
            "websearch-researcher",
            "github-code-researcher",
            "docs-researcher",
            "stackoverflow-researcher",
            "papers-researcher",
            "best-practices-researcher",
        ]
        for agent_name in expected_agents:
            assert agent_name in WEB_RESEARCH_AGENTS
    except ImportError:
        pytest.skip("Web research module not available")


@pytest.mark.asyncio
async def test_research_coordinator():
    """Test research coordinator integration."""
    from athena.research.research_orchestrator import execute_research, ResearchMode

    # Use mock mode for testing
    results = await execute_research(
        "async patterns",
        mode=ResearchMode.MOCK_ONLY,
        use_real=False,
        use_mock=True,
    )

    assert isinstance(results, dict)


def test_mock_agents_still_work():
    """Ensure mock agents still function (backward compatibility)."""
    from athena.research.agents import RESEARCH_AGENTS

    assert len(RESEARCH_AGENTS) > 0
    assert "arxiv-researcher" in RESEARCH_AGENTS
    assert "github-researcher" in RESEARCH_AGENTS


@pytest.mark.asyncio
async def test_mixed_mode_research():
    """Test hybrid mode with both real and mock agents."""
    from athena.research.research_orchestrator import (
        ResearchOrchestrator,
        ResearchMode,
    )

    orchestrator = ResearchOrchestrator(mode=ResearchMode.HYBRID)

    results = await orchestrator.research(
        "test topic",
        use_real=True,
        use_mock=True,
        parallel=True,
    )

    assert isinstance(results, dict)
    # In hybrid mode, should have mock agents at minimum
    assert len(results) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
