"""Tests for working memory semantic tagging (Gap 4: WM Semantic Tagging)."""

from pathlib import Path

import pytest

from athena.core.database import Database
from athena.mcp.handlers import MemoryMCPServer


@pytest.fixture
def mcp_server(tmp_path):
    """Create an MCP server for testing."""
    db_path = tmp_path / "test.db"
    server = MemoryMCPServer(str(db_path))
    return server


def test_extract_semantic_tags_database_domain(mcp_server):
    """Test detection of database domain."""
    result = mcp_server.extract_semantic_tags(
        "Need to optimize the SQL table schema migration"
    )

    assert result["domain"] == "database"
    assert "domain:database" in result["tags"]


def test_extract_semantic_tags_api_domain(mcp_server):
    """Test detection of API domain."""
    result = mcp_server.extract_semantic_tags(
        "Implement REST endpoint for user data requests"
    )

    assert result["domain"] == "api"
    assert "domain:api" in result["tags"]


def test_extract_semantic_tags_ui_domain(mcp_server):
    """Test detection of UI domain."""
    result = mcp_server.extract_semantic_tags(
        "Fix React component layout CSS issues in button styling"
    )

    assert result["domain"] == "ui"
    assert "domain:ui" in result["tags"]


def test_extract_semantic_tags_testing_domain(mcp_server):
    """Test detection of testing domain."""
    result = mcp_server.extract_semantic_tags(
        "Write unit tests for user registration using Jest"
    )

    assert result["domain"] == "testing"
    assert "domain:testing" in result["tags"]


def test_extract_semantic_tags_ml_domain(mcp_server):
    """Test detection of ML domain."""
    result = mcp_server.extract_semantic_tags(
        "Train the LLM model for better inference speed"
    )

    assert result["domain"] == "ml"
    assert "domain:ml" in result["tags"]


def test_extract_semantic_tags_procedure_type(mcp_server):
    """Test detection of procedure type."""
    result = mcp_server.extract_semantic_tags(
        "How to set up Docker for deployment: steps are..."
    )

    assert result["type"] == "procedure"
    assert "type:procedure" in result["tags"]


def test_extract_semantic_tags_decision_type(mcp_server):
    """Test detection of decision type."""
    result = mcp_server.extract_semantic_tags(
        "Decided to use GraphQL instead of REST for API architecture"
    )

    assert result["type"] == "decision"
    assert "type:decision" in result["tags"]


def test_extract_semantic_tags_task_type(mcp_server):
    """Test detection of task type."""
    result = mcp_server.extract_semantic_tags(
        "Task: Implement authentication feature in src/auth/"
    )

    assert result["type"] == "task"
    assert "type:task" in result["tags"]


def test_extract_semantic_tags_temporal_future(mcp_server):
    """Test detection of future temporal markers."""
    result = mcp_server.extract_semantic_tags(
        "Next week I need to implement the database migration"
    )

    assert "temporal:future" in result["tags"]


def test_extract_semantic_tags_temporal_past(mcp_server):
    """Test detection of past temporal markers."""
    result = mcp_server.extract_semantic_tags(
        "Yesterday we decided to refactor the authentication system"
    )

    assert "temporal:past" in result["tags"]


def test_extract_semantic_tags_code_reference(mcp_server):
    """Test detection of code references."""
    result = mcp_server.extract_semantic_tags(
        "Fix the bug in src/auth/jwt.py function login()"
    )

    assert "reference:code" in result["tags"]


def test_extract_semantic_tags_api_reference(mcp_server):
    """Test detection of API references."""
    result = mcp_server.extract_semantic_tags(
        "Add new endpoint for /api/users/profile request handling"
    )

    assert "reference:api" in result["tags"]


def test_extract_semantic_tags_config_reference(mcp_server):
    """Test detection of config file references."""
    result = mcp_server.extract_semantic_tags(
        "Update the config in docker-compose.yaml"
    )

    assert "reference:config" in result["tags"]


def test_extract_semantic_tags_high_priority(mcp_server):
    """Test detection of high priority items."""
    result = mcp_server.extract_semantic_tags(
        "CRITICAL: Fix the broken authentication bug ASAP"
    )

    assert "priority:high" in result["tags"]


def test_extract_semantic_tags_low_priority(mcp_server):
    """Test detection of low priority items."""
    result = mcp_server.extract_semantic_tags(
        "Nice to have: Future optimization for query performance"
    )

    assert "priority:low" in result["tags"]


def test_extract_semantic_tags_multiple_references(mcp_server):
    """Test detection of multiple reference types."""
    result = mcp_server.extract_semantic_tags(
        "Implement API endpoint in src/api/routes.py and update config.yaml"
    )

    # Should have multiple references
    assert len([t for t in result["tags"] if t.startswith("reference:")]) > 1


def test_extract_semantic_tags_context_structure(mcp_server):
    """Test structure of returned context."""
    result = mcp_server.extract_semantic_tags(
        "Fix critical JWT auth bug in src/auth/jwt.py"
    )

    assert "context" in result
    assert "has_code_refs" in result["context"]
    assert "has_api_refs" in result["context"]
    assert "is_temporal" in result["context"]
    assert "priority" in result["context"]

    # Check values
    assert result["context"]["has_code_refs"] == True
    assert result["context"]["priority"] == "high"


def test_extract_semantic_tags_default_values(mcp_server):
    """Test default values for non-specific content."""
    result = mcp_server.extract_semantic_tags(
        "This is a generic note with no specific domain"
    )

    assert result["domain"] == "general"
    assert result["type"] == "fact"
    assert "type:fact" in result["tags"]
    assert "priority" in result["context"]  # Should have priority field


def test_extract_semantic_tags_deployment_domain(mcp_server):
    """Test detection of deployment domain."""
    result = mcp_server.extract_semantic_tags(
        "Deploy Docker container to Kubernetes with CI/CD pipeline"
    )

    assert result["domain"] == "deployment"
    assert "domain:deployment" in result["tags"]


def test_extract_semantic_tags_security_domain(mcp_server):
    """Test detection of security domain."""
    result = mcp_server.extract_semantic_tags(
        "Add signature verification for encrypted messages"
    )

    assert result["domain"] == "security"
    assert "domain:security" in result["tags"]


def test_extract_semantic_tags_performance_domain(mcp_server):
    """Test detection of performance domain."""
    result = mcp_server.extract_semantic_tags(
        "Improve throughput and cache hit rates"
    )

    assert result["domain"] == "performance"
    assert "domain:performance" in result["tags"]


def test_extract_semantic_tags_compound_query(mcp_server):
    """Test detection in compound/complex queries."""
    result = mcp_server.extract_semantic_tags(
        "URGENT: Add HTTPS/JWT auth endpoint for API, integrate with DB migration"
    )

    # Should detect domain (first match)
    assert result["domain"] in ["security", "api", "database", "authentication"]
    # Should detect priority
    assert "priority:high" in result["tags"]
    # Should detect type
    assert "type:task" in result["tags"]


def test_extract_semantic_tags_all_tags_present(mcp_server):
    """Test that semantic tags dict has all required keys."""
    result = mcp_server.extract_semantic_tags("Test content")

    assert "domain" in result
    assert "type" in result
    assert "tags" in result
    assert "context" in result
    assert isinstance(result["tags"], list)
    assert isinstance(result["context"], dict)
