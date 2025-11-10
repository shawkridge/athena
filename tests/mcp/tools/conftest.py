"""Pytest fixtures for MCP tools testing."""

import pytest
from pathlib import Path
from athena.core.database import Database
from athena.memory import MemoryStore
from athena.mcp.tools.registry import ToolRegistry


@pytest.fixture
def db_path(tmp_path):
    """Create temporary database path."""
    return str(tmp_path / "test.db")


@pytest.fixture
def db(db_path):
    """Create test database."""
    database = Database(db_path)
    database.init_schema()
    return database


@pytest.fixture
def memory_store(db):
    """Create memory store with test database."""
    return MemoryStore(str(db.db_path))


@pytest.fixture
def tool_registry():
    """Create empty tool registry for testing."""
    return ToolRegistry()


@pytest.fixture
def memory_manager(db):
    """Create unified memory manager for testing."""
    from athena.manager import UnifiedMemoryManager
    return UnifiedMemoryManager(str(db.db_path))
