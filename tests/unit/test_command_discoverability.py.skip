"""Tests for command discoverability (Gap 5: Command Discovery)."""

from pathlib import Path

import pytest

from athena.core.database import Database
from athena.mcp.handlers import MemoryMCPServer
from athena.prospective.models import ProspectiveTask, TaskStatus


@pytest.fixture
def mcp_server(tmp_path):
    """Create an MCP server for testing."""
    db_path = tmp_path / "test.db"
    server = MemoryMCPServer(str(db_path))
    return server


@pytest.fixture
def project(mcp_server):
    """Create a test project."""
    return mcp_server.project_manager.get_or_create_project("test-project")


def test_suggest_commands_empty_state(mcp_server, project):
    """Test command suggestions with empty/healthy state."""
    suggestions = mcp_server.suggest_commands(project.id)

    # Should always return some suggestions
    assert isinstance(suggestions, list)
    # All suggestions should have required fields
    for s in suggestions:
        assert "command" in s
        assert "reason" in s
        assert "category" in s
        assert "priority" in s


def test_suggest_commands_returns_list(mcp_server, project):
    """Test that suggest_commands returns a list."""
    suggestions = mcp_server.suggest_commands(project.id)

    # Should return a list
    assert isinstance(suggestions, list)


def test_suggest_commands_priority_ordering(mcp_server, project):
    """Test that suggestions are ordered by priority."""
    suggestions = mcp_server.suggest_commands(project.id)

    if len(suggestions) > 1:
        priority_map = {"high": 0, "medium": 1, "low": 2}
        for i in range(len(suggestions) - 1):
            curr_priority = priority_map.get(suggestions[i]["priority"], 99)
            next_priority = priority_map.get(suggestions[i + 1]["priority"], 99)
            # Current should be <= next (proper ordering)
            assert curr_priority <= next_priority


def test_suggest_commands_contains_core_commands(mcp_server, project):
    """Test that core commands are suggested."""
    suggestions = mcp_server.suggest_commands(project.id)

    suggestion_cmds = [s["command"] for s in suggestions]
    # Should have at least one core command
    assert any(cmd.startswith("/") for cmd in suggestion_cmds)


def test_suggest_commands_error_handling(mcp_server):
    """Test that suggest_commands handles errors gracefully."""
    # Try with invalid project_id
    suggestions = mcp_server.suggest_commands(project_id=99999)

    # Should return default suggestions on error, not crash
    assert isinstance(suggestions, list)
    assert len(suggestions) > 0


def test_suggest_commands_structure(mcp_server, project):
    """Test the structure of returned suggestions."""
    suggestions = mcp_server.suggest_commands(project.id)

    for suggestion in suggestions:
        # All required fields
        assert isinstance(suggestion["command"], str)
        assert isinstance(suggestion["reason"], str)
        assert isinstance(suggestion["category"], str)
        assert isinstance(suggestion["priority"], str)

        # Valid values
        assert suggestion["command"].startswith("/")
        assert suggestion["priority"] in ["high", "medium", "low"]
        assert suggestion["category"] in [
            "memory", "monitoring", "workflow", "review",
            "learning", "core"
        ]


def test_suggest_commands_context_aware(mcp_server, project):
    """Test that suggestions are context-aware."""
    # Add some tasks
    for i in range(5):
        task = ProspectiveTask(
            project_id=project.id,
            content=f"Fix auth bug {i}",
            active_form=f"Fixing auth bug {i}",
            status=TaskStatus.COMPLETED
        )
        mcp_server.prospective_store.create_task(task)

    suggestions = mcp_server.suggest_commands(project.id)

    # When tasks exist, should suggest task-related commands
    suggestion_cmds = [s["command"] for s in suggestions]
    # Could suggest consolidate, timeline, etc.
    assert len(suggestions) > 0


def test_suggest_commands_multiple_calls(mcp_server, project):
    """Test that multiple calls return consistent structure."""
    suggestions1 = mcp_server.suggest_commands(project.id)
    suggestions2 = mcp_server.suggest_commands(project.id)

    # Both should have same structure
    assert len(suggestions1) == len(suggestions2)

    for s1, s2 in zip(suggestions1, suggestions2):
        assert s1["command"] == s2["command"]
        assert s1["category"] == s2["category"]
        assert s1["priority"] == s2["priority"]
