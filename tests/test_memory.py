"""Test basic memory operations."""

import tempfile
from pathlib import Path

import pytest

from athena.core.models import MemoryType
from athena.memory import MemoryStore


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_memory.db"
        yield db_path


def test_create_project(temp_db):
    """Test project creation."""
    store = MemoryStore(temp_db)

    project = store.create_project("test-project", "/home/user/test-project")

    assert project.id is not None
    assert project.name == "test-project"
    assert project.path == "/home/user/test-project"
    assert project.memory_count == 0

    store.close()


def test_get_project_by_path(temp_db):
    """Test project lookup by path."""
    store = MemoryStore(temp_db)

    # Create project
    created = store.create_project("test-project", "/home/user/test-project")

    # Find by exact path
    found = store.get_project_by_path("/home/user/test-project")
    assert found is not None
    assert found.id == created.id

    # Find by subdirectory path
    found_sub = store.get_project_by_path("/home/user/test-project/src/module")
    assert found_sub is not None
    assert found_sub.id == created.id

    # Not found
    not_found = store.get_project_by_path("/home/user/other-project")
    assert not_found is None

    store.close()


def test_remember_basic(temp_db):
    """Test storing a memory without embeddings."""
    store = MemoryStore(temp_db)

    # Create project
    project = store.create_project("test", "/tmp/test")

    # Store memory (will fail if Ollama not running)
    try:
        memory_id = store.remember(
            content="This is a test memory",
            memory_type=MemoryType.FACT,
            project_id=project.id,
            tags=["test"],
        )

        assert memory_id > 0

        # List memories
        memories = store.list_memories(project.id)
        assert len(memories) == 1
        assert memories[0].content == "This is a test memory"
        assert memories[0].memory_type == MemoryType.FACT
        assert memories[0].tags == ["test"]

    except RuntimeError as e:
        if "not available" in str(e):
            pytest.skip("Ollama not available for testing")
        raise

    store.close()


def test_forget_memory(temp_db):
    """Test deleting a memory."""
    store = MemoryStore(temp_db)

    project = store.create_project("test", "/tmp/test")

    try:
        # Store memory
        memory_id = store.remember(
            content="Memory to delete",
            memory_type=MemoryType.CONTEXT,
            project_id=project.id,
        )

        # Delete it
        deleted = store.forget(memory_id)
        assert deleted is True

        # Verify it's gone
        memories = store.list_memories(project.id)
        assert len(memories) == 0

        # Try deleting again
        deleted_again = store.forget(memory_id)
        assert deleted_again is False

    except RuntimeError as e:
        if "not available" in str(e):
            pytest.skip("Ollama not available for testing")
        raise

    store.close()
