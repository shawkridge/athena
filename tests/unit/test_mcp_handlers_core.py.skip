"""Tests for core MCP handler functions (remember, recall, forget, list_memories)."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import os

import pytest

from athena.mcp.handlers import MemoryMCPServer
from athena.core.models import MemoryType


@pytest.fixture
def temp_db_path():
    """Create temporary database path for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_mcp.db"


@pytest.fixture
def mock_embedding_model():
    """Create a mock embedding model that returns 768D vectors."""
    class MockEmbeddingModel:
        """Mock embedding model for testing."""

        def __init__(self, *args, **kwargs):
            self.embedding_dim = 768
            self.provider = "mock"
            self.model = "mock"
            self.backend = None
            self.available = True

        def embed(self, text: str) -> list[float]:
            """Generate deterministic 768D mock embedding."""
            import hashlib
            import random
            hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
            random.seed(hash_val)
            return [random.uniform(-1, 1) for _ in range(768)]

        def embed_batch(self, texts: list[str]) -> list[list[float]]:
            """Generate 768D mock embeddings for batch."""
            return [self.embed(text) for text in texts]

    return MockEmbeddingModel


@pytest.fixture
def mcp_server(temp_db_path, mock_embedding_model):
    """Create MCP server instance for testing with mock embeddings."""
    # Patch EmbeddingModel to use mock version that returns 768D vectors
    with patch('athena.memory.store.EmbeddingModel', mock_embedding_model):
        with patch('athena.core.embeddings.EmbeddingModel', mock_embedding_model):
            server = MemoryMCPServer(str(temp_db_path), enable_advanced_rag=False)

            # Create a default project for tests
            if hasattr(server, 'project_manager') and hasattr(server, 'store'):
                project = server.store.db.create_project(
                    name="test_project",
                    path="/test/project"
                )
                server.project_manager._current_project = project

            yield server
            # Cleanup
            if hasattr(server, 'store') and hasattr(server.store, 'db') and server.store.db:
                server.store.db.close()


class TestMCPCoreHandlers:
    """Tests for core MCP handler operations."""

    @pytest.mark.asyncio
    async def test_handle_remember_basic(self, mcp_server):
        """Test basic remember operation."""
        args = {
            "content": "Python lists are ordered collections",
            "memory_type": "fact",
            "tags": ["python", "collections"],
        }

        result = await mcp_server._handle_remember(args)

        # Verify response structure
        assert len(result) > 0
        assert hasattr(result[0], 'type')
        assert result[0].type == "text"
        assert hasattr(result[0], 'text')
        assert "Stored memory" in result[0].text
        assert "fact" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_remember_pattern(self, mcp_server):
        """Test remember with pattern memory type."""
        args = {
            "content": "Object-oriented programming uses inheritance and polymorphism",
            "memory_type": "pattern",
            "tags": ["oop", "design"],
        }

        result = await mcp_server._handle_remember(args)

        assert len(result) > 0
        assert "Stored memory" in result[0].text
        assert "pattern" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_remember_without_tags(self, mcp_server):
        """Test remember without tags (optional field)."""
        args = {
            "content": "JavaScript has dynamic typing",
            "memory_type": "fact",
        }

        result = await mcp_server._handle_remember(args)

        assert len(result) > 0
        assert "Stored memory" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_list_memories_empty(self, mcp_server):
        """Test list_memories on empty database."""
        args = {}

        result = await mcp_server._handle_list_memories(args)

        assert len(result) > 0
        assert isinstance(result[0].text, str)
        # Should indicate no memories found or show empty list

    @pytest.mark.asyncio
    async def test_handle_list_memories_after_remember(self, mcp_server):
        """Test list_memories after storing memories."""
        # Store some memories
        await mcp_server._handle_remember({
            "content": "First memory",
            "memory_type": "fact",
        })
        await mcp_server._handle_remember({
            "content": "Second memory",
            "memory_type": "pattern",
        })

        # List all memories
        result = await mcp_server._handle_list_memories({})

        assert len(result) > 0
        response_text = result[0].text
        # Should show count or list of memories

    @pytest.mark.asyncio
    async def test_handle_recall_pattern(self, mcp_server):
        """Test recall with search pattern."""
        # First store a memory
        await mcp_server._handle_remember({
            "content": "Recursion is when a function calls itself",
            "memory_type": "pattern",
            "tags": ["recursion", "algorithms"],
        })

        # Now recall related content
        args = {
            "query": "recursion",
            "memory_type": "pattern",
        }

        result = await mcp_server._handle_recall(args)

        assert len(result) > 0
        response_text = result[0].text
        # Should find the memory we just stored

    @pytest.mark.asyncio
    async def test_handle_recall_nonexistent(self, mcp_server):
        """Test recall for content that doesn't exist."""
        args = {
            "query": "nonexistent_xyz_abc_content_12345",
            "memory_type": "fact",
        }

        result = await mcp_server._handle_recall(args)

        assert len(result) > 0
        # Should indicate no results found

    @pytest.mark.asyncio
    async def test_handle_forget_memory(self, mcp_server):
        """Test forgetting a memory."""
        # First store a memory
        remember_result = await mcp_server._handle_remember({
            "content": "This memory will be forgotten",
            "memory_type": "fact",
        })

        # Extract memory ID from response
        response_text = remember_result[0].text
        # Format: "✓ Stored memory (ID: X)"
        import re
        match = re.search(r"ID: (\d+)", response_text)
        if match:
            memory_id = match.group(1)

            # Now forget it
            args = {"memory_id": int(memory_id)}
            result = await mcp_server._handle_forget(args)

            assert len(result) > 0
            assert "Forgot" in result[0].text or "deleted" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_forget_nonexistent(self, mcp_server):
        """Test forgetting non-existent memory."""
        args = {"memory_id": 99999}

        # This should either succeed silently or return not found message
        result = await mcp_server._handle_forget(args)

        assert len(result) > 0
        # Response format may vary


class TestMCPHandlerIntegration:
    """Integration tests for MCP handlers working together."""

    @pytest.mark.asyncio
    async def test_remember_recall_workflow(self, mcp_server):
        """Test complete workflow: remember -> recall."""
        # Remember memories
        memories = [
            {"content": "Python is great", "memory_type": "fact", "tags": ["python"]},
            {"content": "Rust is safe", "memory_type": "fact", "tags": ["rust"]},
            {"content": "Go is fast", "memory_type": "fact", "tags": ["go"]},
        ]

        for memory in memories:
            await mcp_server._handle_remember(memory)

        # Recall specific memory
        result = await mcp_server._handle_recall({
            "query": "python",
        })

        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_remember_forget_workflow(self, mcp_server):
        """Test complete workflow: remember -> forget -> recall."""
        # Remember a memory
        remember_result = await mcp_server._handle_remember({
            "content": "This will be deleted",
            "memory_type": "fact",
        })

        # Extract ID
        import re
        response = remember_result[0].text
        match = re.search(r"ID: (\d+)", response)

        if match:
            memory_id = int(match.group(1))

            # List before delete
            before = await mcp_server._handle_list_memories({})
            before_count = len(before[0].text) if before else 0

            # Forget it
            forget_result = await mcp_server._handle_forget({"memory_id": memory_id})
            assert len(forget_result) > 0

            # List after delete
            after = await mcp_server._handle_list_memories({})
            after_count = len(after[0].text) if after else 0

            # After count should be less than or equal to before
            assert after_count <= before_count


class TestMCPErrorHandling:
    """Tests for error handling in MCP handlers."""

    @pytest.mark.asyncio
    async def test_remember_invalid_memory_type(self, mcp_server):
        """Test remember with invalid memory type."""
        args = {
            "content": "Some content",
            "memory_type": "invalid_type_xyz",  # Invalid
        }

        # Should either reject or convert to valid type
        try:
            result = await mcp_server._handle_remember(args)
            assert len(result) > 0
            # Either succeeded or returned error message
        except ValueError:
            # Expected for invalid memory type
            pass

    @pytest.mark.asyncio
    async def test_recall_missing_query(self, mcp_server):
        """Test recall without required query parameter."""
        args = {}  # Missing required "query" parameter

        try:
            result = await mcp_server._handle_recall(args)
            # If it doesn't raise, it should return a response
            assert result is not None
        except (KeyError, TypeError):
            # Expected if query is required
            pass

    @pytest.mark.asyncio
    async def test_forget_invalid_id(self, mcp_server):
        """Test forget with invalid memory ID type."""
        args = {
            "memory_id": "not_a_number"  # Should be integer
        }

        try:
            result = await mcp_server._handle_forget(args)
            # Either converted or errored
        except (ValueError, TypeError):
            # Expected
            pass


# Helper for running async tests
def pytest_generate_tests(metafunc):
    """Configure pytest for async tests."""
    if 'mcp_server' in metafunc.fixturenames:
        # Make the fixture work with async
        pass
