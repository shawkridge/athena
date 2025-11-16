"""
Fixtures and configuration for Phase 2.5 integration tests.

Provides:
- Test database setup/teardown
- MCP server mock/real instance
- Test data factories
- Memory management utilities
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock

from athena.core.database import Database
from athena.memory.store import MemoryStore
from athena.episodic.store import EpisodicStore
from athena.procedural.store import ProceduralStore
from athena.prospective.store import ProspectiveStore
from athena.graph.store import GraphStore
from athena.manager import UnifiedMemoryManager


@pytest.fixture(autouse=True)
def disable_llm_features_for_tests():
    """Disable LLM features for all tests.

    LLM calls (to local servers or APIs) are disabled in tests to:
    - Avoid external dependencies
    - Speed up test execution
    - Use deterministic fallback validation
    - Allow tests to run without LLM services
    """
    os.environ["ENABLE_LLM_FEATURES"] = "false"
    yield
    # Cleanup if needed
    if "ENABLE_LLM_FEATURES" in os.environ:
        del os.environ["ENABLE_LLM_FEATURES"]


@pytest.fixture
def temp_db_path():
    """Create temporary database for test isolation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_memory.db"
        yield db_path
        # Cleanup handled by tempfile


@pytest.fixture
def test_database(temp_db_path):
    """Initialize test database with schema."""
    db = Database(str(temp_db_path))
    db.init_schema()
    yield db
    db.close()


@pytest.fixture
def test_memory_store(test_database):
    """Initialize test memory store."""
    return MemoryStore(test_database.db_path)


@pytest.fixture
def test_episodic_store(test_database):
    """Initialize test episodic store."""
    return EpisodicStore(test_database)


@pytest.fixture
def test_semantic_store(test_database):
    """Initialize test semantic store."""
    return SemanticStore(test_database)


@pytest.fixture
def test_procedural_store(test_database):
    """Initialize test procedural store."""
    return ProceduralStore(test_database)


@pytest.fixture
def test_prospective_store(test_database):
    """Initialize test prospective store."""
    return ProspectiveStore(test_database)


@pytest.fixture
def test_graph_store(test_database):
    """Initialize test knowledge graph store."""
    return GraphStore(test_database)


@pytest.fixture
def unified_manager(test_memory_store):
    """Initialize unified memory manager for tests."""
    return UnifiedMemoryManager(test_memory_store)


# Test data factories

@pytest.fixture
def sample_memory():
    """Create sample semantic memory for tests."""
    return {
        "content": "JWT token implementation pattern: Sign with RS256, validate on each request",
        "memory_type": "pattern",
        "tags": ["authentication", "JWT", "security"]
    }


@pytest.fixture
def sample_event():
    """Create sample episodic event for tests."""
    return {
        "content": "Implemented JWT signing mechanism",
        "event_type": "action",
        "outcome": "success",
    }


@pytest.fixture
def sample_task():
    """Create sample task for tests."""
    return {
        "content": "Implement JWT token validation",
        "active_form": "Implementing JWT token validation",
        "status": "pending",
        "priority": "high",
    }


@pytest.fixture
def sample_goal():
    """Create sample goal for tests."""
    return {
        "goal_text": "Modernize authentication system using JWT",
        "priority": 9,
    }


@pytest.fixture
def sample_procedure():
    """Create sample workflow procedure for tests."""
    return {
        "name": "jwt-token-implementation",
        "category": "code_template",
        "template": """
        1. Design decision: Signing algorithm
        2. Implement token signing
        3. Implement token validation
        4. Write tests
        5. Document approach
        """,
        "description": "Workflow for implementing JWT tokens",
    }


@pytest.fixture
def sample_entity():
    """Create sample knowledge graph entity."""
    return {
        "name": "JWT Token Implementation",
        "entity_type": "pattern",
        "observations": ["Implemented on 2025-10-22", "Used in production"]
    }


@pytest.fixture
def sample_relation():
    """Create sample knowledge graph relation."""
    return {
        "from_entity": "JWT Token Implementation",
        "to_entity": "RS256 Signing",
        "relation_type": "uses"
    }


# Mock fixtures

@pytest.fixture
def mock_mcp_server():
    """Create mock MCP server for tests."""
    mock_server = MagicMock()

    # Mock tool methods
    mock_server.call_tool.return_value = {"result": "success"}
    mock_server.list_tools.return_value = [
        {"name": "smart_retrieve", "description": "Search memory"},
        {"name": "remember", "description": "Store memory"},
        {"name": "run_consolidation", "description": "Consolidate"},
        # ... add more tools as needed
    ]

    return mock_server


# Session-level fixtures for performance

@pytest.fixture(scope="session")
def session_db_path():
    """Create database for entire test session."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "session_test_memory.db"
        yield db_path


@pytest.fixture(scope="session")
def session_database(session_db_path):
    """Initialize session-level test database."""
    db = Database(str(session_db_path))
    db.init_schema()
    yield db
    db.close()


# Test markers

def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "commands: mark test as command integration test"
    )
    config.addinivalue_line(
        "markers", "skills: mark test as skill integration test"
    )
    config.addinivalue_line(
        "markers", "agents: mark test as agent integration test"
    )
    config.addinivalue_line(
        "markers", "hooks: mark test as hook integration test"
    )
    config.addinivalue_line(
        "markers", "coverage: mark test as tool coverage test"
    )


# Helper functions

def create_test_memory(manager, **kwargs):
    """Helper: Create test memory with defaults."""
    defaults = {
        "content": "Test memory",
        "memory_type": "fact",
    }
    defaults.update(kwargs)
    return manager.remember(**defaults)


def create_test_event(store, **kwargs):
    """Helper: Create test episodic event."""
    defaults = {
        "content": "Test event",
        "event_type": "action",
        "outcome": "success",
    }
    defaults.update(kwargs)
    return store.record_event(**defaults)


def create_test_task(manager, **kwargs):
    """Helper: Create test task."""
    defaults = {
        "content": "Test task",
        "active_form": "Testing task",
        "status": "pending",
    }
    defaults.update(kwargs)
    return manager.create_task(**defaults)


def create_test_entity(store, **kwargs):
    """Helper: Create test entity."""
    defaults = {
        "name": "Test Entity",
        "entity_type": "concept",
    }
    defaults.update(kwargs)
    return store.create_entity(**defaults)
