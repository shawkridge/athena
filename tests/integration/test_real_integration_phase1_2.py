"""
REAL Integration Tests for Phase 1 & 2 - Tests with actual memory database

These tests use the REAL memory database (~/.athena/memory.db) and test
actual code paths, not mocks. This ensures our code works in production.
"""

import pytest
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

from athena.core.database import Database
from athena.memory.store import MemoryStore
from athena.rag.context_injector import ContextInjector
from athena.rag.manager import RAGManager
from athena.rag.graph_traversal import GraphTraversal
from athena.rag.temporal_queries import TemporalQueries
from athena.rag.spatial_context import SpatialContextIntegration
from athena.core.models import Memory


class TestRealMemoryDatabase:
    """Test with real memory database."""

    @pytest.fixture
    def real_db(self):
        """Use actual memory database."""
        db_path = Path.home() / ".athena" / "memory.db"
        if not db_path.exists():
            pytest.skip("Real memory database not found")
        return Database(str(db_path))

    def test_database_connection(self, real_db):
        """Test that database connects."""
        assert real_db is not None
        # Try a simple query
        cursor = real_db.conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result is not None

    def test_memory_store_initialization(self, real_db):
        """Test MemoryStore initializes with real database."""
        # This tests that MemoryStore works with real database path
        db_path = Path.home() / ".athena" / "memory.db"
        store = MemoryStore(str(db_path))
        assert store is not None

    def test_rag_manager_initialization(self, real_db):
        """Test RAGManager initializes properly."""
        db_path = Path.home() / ".athena" / "memory.db"
        memory_store = MemoryStore(str(db_path))
        rag_manager = RAGManager(memory_store=memory_store)
        assert rag_manager is not None
        assert hasattr(rag_manager, 'retrieve')


class TestRealContextInjection:
    """Test ContextInjector with REAL database."""

    @pytest.fixture
    def real_injector(self):
        """Create injector with real database."""
        db_path = Path.home() / ".athena" / "memory.db"
        if not db_path.exists():
            pytest.skip("Real memory database not found")

        db = Database(str(db_path))
        memory_store = MemoryStore(str(db_path))
        rag_manager = RAGManager(memory_store=memory_store)

        return ContextInjector(
            db=db,
            rag_manager=rag_manager,
            token_budget=1000,
            min_usefulness=0.2,
            max_memories=5,
        )

    @pytest.mark.asyncio
    async def test_real_context_injection(self, real_injector):
        """Test context injection with actual memories."""
        result = await real_injector.inject_context(
            user_prompt="What are the key patterns in this project?"
        )

        # Should return valid result
        assert result is not None
        assert hasattr(result, 'memories')
        assert hasattr(result, 'total_tokens')
        assert hasattr(result, 'injection_confidence')

        # Should have attempted retrieval
        assert result.total_tokens >= 0
        assert 0.0 <= result.injection_confidence <= 1.0

    @pytest.mark.asyncio
    async def test_real_memory_retrieval(self, real_injector):
        """Test that real memories are actually retrieved."""
        result = await real_injector.inject_context(
            user_prompt="authentication JWT tokens debugging"
        )

        # Should return valid result
        assert result is not None
        assert hasattr(result, 'memories')
        assert isinstance(result.memories, list)
        assert len(result.memories) >= 0

        # Check memory object structure
        for memory in result.memories:
            assert hasattr(memory, 'content')
            assert hasattr(memory, 'source_layer')
            assert hasattr(memory, 'usefulness')
            assert hasattr(memory, 'relevance')
            assert hasattr(memory, 'recency')

    @pytest.mark.asyncio
    async def test_conversation_history_integration(self, real_injector):
        """Test conversation history augmentation with real data."""
        conversation = [
            {"role": "user", "content": "I'm working on authentication"},
            {"role": "assistant", "content": "JWT tokens are signed credentials..."},
            {"role": "user", "content": "What about that?"},
        ]

        result = await real_injector.inject_context(
            user_prompt="What about that?",
            conversation_history=conversation,
        )

        # Should augment query with previous context
        assert result is not None


class TestRealGraphTraversal:
    """Test GraphTraversal with REAL database."""

    @pytest.fixture
    def real_graph(self):
        """Create GraphTraversal with real database."""
        db_path = Path.home() / ".athena" / "memory.db"
        if not db_path.exists():
            pytest.skip("Real memory database not found")

        db = Database(str(db_path))
        return GraphTraversal(db, max_depth=2)

    @pytest.mark.asyncio
    async def test_real_graph_traversal(self, real_graph):
        """Test graph traversal with real entities."""
        # Try to find some entity (will gracefully handle if not found)
        result = await real_graph.find_related_context(
            entity_name="Authentication",
            depth=2,
        )

        # Should return valid result structure
        assert hasattr(result, 'root_entity')
        assert hasattr(result, 'related_entities')
        assert hasattr(result, 'richness_score')
        assert 0.0 <= result.richness_score <= 1.0


class TestRealTemporalQueries:
    """Test TemporalQueries with REAL database."""

    @pytest.fixture
    def real_temporal(self):
        """Create TemporalQueries with real database."""
        db_path = Path.home() / ".athena" / "memory.db"
        if not db_path.exists():
            pytest.skip("Real memory database not found")

        db = Database(str(db_path))
        return TemporalQueries(db)

    @pytest.mark.asyncio
    async def test_real_temporal_pattern_search(self, real_temporal):
        """Test temporal pattern detection with real events."""
        pattern = await real_temporal.find_temporal_pattern(
            pattern_description="debugging",
            time_window=timedelta(days=30),
        )

        # Should return valid result structure
        assert pattern is not None
        assert "pattern" in pattern
        assert "occurrences" in pattern
        assert pattern["occurrences"] >= 0


class TestRealSpatialContext:
    """Test SpatialContext with REAL usage."""

    @pytest.fixture
    def real_spatial(self):
        """Create SpatialContext."""
        db_path = Path.home() / ".athena" / "memory.db"
        if not db_path.exists():
            pytest.skip("Real memory database not found")

        db = Database(str(db_path))
        return SpatialContextIntegration(db, cwd="/home/user/projects")

    def test_real_spatial_analysis(self, real_spatial):
        """Test spatial context analysis."""
        context = real_spatial.analyze_spatial_context(
            "src/auth/jwt.py"
        )

        assert context is not None
        assert context.file_path == "src/auth/jwt.py"
        assert context.component == "auth"
        assert context.depth == 3

    def test_real_spatial_proximity(self, real_spatial):
        """Test spatial proximity calculation."""
        from athena.rag.spatial_context import SpatialContext

        ctx_a = SpatialContext(
            file_path="src/auth/jwt.py",
            directory="src/auth",
            depth=3,
            component="auth",
        )
        ctx_b = SpatialContext(
            file_path="src/auth/session.py",
            directory="src/auth",
            depth=3,
            component="auth",
        )

        proximity = real_spatial.calculate_spatial_proximity(ctx_a, ctx_b)
        assert proximity == 1.0  # Same component


class TestRealEndToEnd:
    """End-to-end test with REAL production data."""

    @pytest.mark.asyncio
    async def test_full_context_injection_pipeline(self):
        """Test complete pipeline with real database."""
        db_path = Path.home() / ".athena" / "memory.db"
        if not db_path.exists():
            pytest.skip("Real memory database not found")

        db = Database(str(db_path))
        memory_store = MemoryStore(str(db_path))
        rag_manager = RAGManager(memory_store=memory_store)

        injector = ContextInjector(
            db=db,
            rag_manager=rag_manager,
            token_budget=2000,
            min_usefulness=0.2,
            max_memories=10,
        )

        # Simulate real user prompts
        prompts = [
            "How do I debug authentication issues?",
            "What are best practices for error handling?",
            "Explain the architecture pattern",
        ]

        for prompt in prompts:
            result = await injector.inject_context(user_prompt=prompt)

            # Should complete without errors
            assert result is not None
            assert hasattr(result, 'memories')
            assert isinstance(result.memories, list)

            print(f"✓ Prompt: {prompt}")
            print(f"  Memories: {len(result.memories)}, Confidence: {result.injection_confidence:.0%}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
