"""Tests for PostgreSQL database layer.

Requires PostgreSQL to be running with schema initialized.
Set ATHENA_POSTGRES_* environment variables to configure.

Test Scope:
- Connection pool initialization
- Schema creation (idempotent)
- CRUD operations for all 10 tables
- Hybrid search functionality
- Consolidation state machine
- Transaction support
"""

import pytest
import asyncio
from typing import AsyncGenerator
import os

# Skip tests if PostgreSQL not available
pytest.importorskip("psycopg")

from athena.core.database_postgres import PostgresDatabase


@pytest.fixture
async def postgres_db() -> AsyncGenerator[PostgresDatabase, None]:
    """Create PostgreSQL database instance.

    Configuration from environment:
    - ATHENA_POSTGRES_HOST (default: localhost)
    - ATHENA_POSTGRES_PORT (default: 5432)
    - ATHENA_POSTGRES_DBNAME (default: athena)
    - ATHENA_POSTGRES_USER (default: athena)
    - ATHENA_POSTGRES_PASSWORD (default: athena_dev)
    """

    db = PostgresDatabase(
        host=os.environ.get("ATHENA_POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("ATHENA_POSTGRES_PORT", "5432")),
        dbname=os.environ.get("ATHENA_POSTGRES_DBNAME", "athena"),
        user=os.environ.get("ATHENA_POSTGRES_USER", "athena"),
        password=os.environ.get("ATHENA_POSTGRES_PASSWORD", "athena_dev"),
    )

    # Initialize database
    await db.initialize()

    yield db

    # Cleanup
    await db.close()


class TestPostgresDatabaseSetup:
    """Test database initialization and schema creation."""

    @pytest.mark.asyncio
    async def test_initialize(self, postgres_db: PostgresDatabase):
        """Test database initialization."""
        assert postgres_db._initialized
        assert postgres_db._pool is not None

    @pytest.mark.asyncio
    async def test_get_connection(self, postgres_db: PostgresDatabase):
        """Test getting connection from pool."""
        async with postgres_db.get_connection() as conn:
            result = await conn.execute("SELECT 1")
            row = await result.fetchone()
            assert row[0] == 1

    @pytest.mark.asyncio
    async def test_schema_exists(self, postgres_db: PostgresDatabase):
        """Test that all schema tables exist."""
        async with postgres_db.get_connection() as conn:
            # Check for all 10 core tables
            tables = [
                "projects",
                "memory_vectors",
                "memory_relationships",
                "episodic_events",
                "prospective_goals",
                "prospective_tasks",
                "code_metadata",
                "code_dependencies",
                "planning_decisions",
                "planning_scenarios",
            ]

            for table in tables:
                result = await conn.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_name = %s
                    )
                    """,
                    (table,),
                )
                row = await result.fetchone()
                assert row[0], f"Table {table} does not exist"


class TestProjectOperations:
    """Test project CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_project(self, postgres_db: PostgresDatabase):
        """Test creating a project."""
        project = await postgres_db.create_project(
            name="test_project",
            path="/test/path",
            language="python",
            description="Test project",
        )

        assert project.id is not None
        assert project.name == "test_project"
        assert project.path == "/test/path"

    @pytest.mark.asyncio
    async def test_get_project_by_path(self, postgres_db: PostgresDatabase):
        """Test getting a project by path."""
        # Create project
        created_project = await postgres_db.create_project(
            name="test_project_2",
            path="/test/path2",
        )

        # Get by path
        retrieved_project = await postgres_db.get_project_by_path("/test/path2")

        assert retrieved_project is not None
        assert retrieved_project.id == created_project.id
        assert retrieved_project.name == "test_project_2"

    @pytest.mark.asyncio
    async def test_get_nonexistent_project(self, postgres_db: PostgresDatabase):
        """Test getting nonexistent project returns None."""
        project = await postgres_db.get_project_by_path("/nonexistent")
        assert project is None

    @pytest.mark.asyncio
    async def test_update_project_access(self, postgres_db: PostgresDatabase):
        """Test updating project access time."""
        # Create project
        project = await postgres_db.create_project(
            name="test_project_3",
            path="/test/path3",
        )

        # Update access
        await postgres_db.update_project_access(project.id)

        # Verify (would need to query to verify timestamp)
        retrieved = await postgres_db.get_project_by_path("/test/path3")
        assert retrieved is not None


class TestMemoryVectorOperations:
    """Test memory vector CRUD operations."""

    @pytest.fixture
    async def project_id(self, postgres_db: PostgresDatabase) -> int:
        """Create a test project."""
        project = await postgres_db.create_project(
            name="memory_test_project",
            path="/memory/test",
        )
        return project.id

    @pytest.mark.asyncio
    async def test_store_memory(self, postgres_db: PostgresDatabase, project_id: int):
        """Test storing a memory vector."""
        # Create a simple 768-dimensional embedding
        embedding = [0.1] * 768

        memory_id = await postgres_db.store_memory(
            project_id=project_id,
            content="Test memory content",
            embedding=embedding,
            memory_type="fact",
            domain="memory",
            tags=["test", "unit"],
        )

        assert memory_id is not None
        assert isinstance(memory_id, int)

    @pytest.mark.asyncio
    async def test_get_memory(self, postgres_db: PostgresDatabase, project_id: int):
        """Test retrieving a memory."""
        # Store memory
        embedding = [0.1] * 768
        memory_id = await postgres_db.store_memory(
            project_id=project_id,
            content="Test memory for retrieval",
            embedding=embedding,
            memory_type="fact",
            domain="memory",
        )

        # Retrieve
        memory = await postgres_db.get_memory(memory_id)

        assert memory is not None
        assert memory["id"] == memory_id
        assert memory["content"] == "Test memory for retrieval"
        assert memory["memory_type"] == "fact"

    @pytest.mark.asyncio
    async def test_delete_memory(self, postgres_db: PostgresDatabase, project_id: int):
        """Test deleting a memory."""
        # Store memory
        embedding = [0.1] * 768
        memory_id = await postgres_db.store_memory(
            project_id=project_id,
            content="Memory to delete",
            embedding=embedding,
            memory_type="fact",
        )

        # Delete
        result = await postgres_db.delete_memory(memory_id)
        assert result is True

        # Verify deleted
        memory = await postgres_db.get_memory(memory_id)
        assert memory is None

    @pytest.mark.asyncio
    async def test_update_access_stats(self, postgres_db: PostgresDatabase, project_id: int):
        """Test updating access statistics."""
        # Store memory
        embedding = [0.1] * 768
        memory_id = await postgres_db.store_memory(
            project_id=project_id,
            content="Memory for access tracking",
            embedding=embedding,
            memory_type="fact",
        )

        # Update access
        await postgres_db.update_access_stats(memory_id)

        # Retrieve and check access_count increased
        memory = await postgres_db.get_memory(memory_id)
        assert memory is not None
        assert memory["access_count"] == 1


class TestHybridSearch:
    """Test hybrid search functionality."""

    @pytest.fixture
    async def project_with_memories(self, postgres_db: PostgresDatabase):
        """Create project with test memories."""
        project = await postgres_db.create_project(
            name="search_test_project",
            path="/search/test",
        )

        # Create test memories with different content
        embeddings = [
            ([0.1] * 768, "machine learning optimization techniques"),
            ([0.2] * 768, "neural networks and deep learning"),
            ([0.3] * 768, "database indexing and query optimization"),
            ([0.4] * 768, "Python programming best practices"),
            ([0.5] * 768, "PostgreSQL vector search with pgvector"),
        ]

        for embedding, content in embeddings:
            await postgres_db.store_memory(
                project_id=project.id,
                content=content,
                embedding=embedding,
                memory_type="fact",
                domain="memory",
                tags=["test"],
            )

        return project.id

    @pytest.mark.asyncio
    async def test_semantic_search(
        self,
        postgres_db: PostgresDatabase,
        project_with_memories: int,
    ):
        """Test semantic search functionality."""
        # Search for memories similar to embedding about optimization
        query_embedding = [0.15] * 768

        results = await postgres_db.semantic_search(
            project_id=project_with_memories,
            embedding=query_embedding,
            limit=10,
            threshold=0.0,  # Get all results for testing
        )

        # Should find some results
        assert len(results) > 0
        assert all("semantic_similarity" in r for r in results)
        assert all(r["semantic_similarity"] >= 0.0 for r in results)

    @pytest.mark.asyncio
    async def test_hybrid_search(
        self,
        postgres_db: PostgresDatabase,
        project_with_memories: int,
    ):
        """Test hybrid search combining semantic + keyword."""
        query_embedding = [0.15] * 768
        query_text = "optimization techniques"

        results = await postgres_db.hybrid_search(
            project_id=project_with_memories,
            embedding=query_embedding,
            query_text=query_text,
            limit=5,
            semantic_weight=0.7,
            keyword_weight=0.3,
        )

        # Should find results combining semantic and keyword signals
        assert len(results) > 0
        assert all("hybrid_score" in r for r in results)
        assert all("semantic_similarity" in r for r in results)


class TestConsolidationOperations:
    """Test consolidation state machine."""

    @pytest.fixture
    async def project_id(self, postgres_db: PostgresDatabase) -> int:
        """Create test project."""
        project = await postgres_db.create_project(
            name="consolidation_test",
            path="/consolidation/test",
        )
        return project.id

    @pytest.mark.asyncio
    async def test_update_consolidation_state(
        self,
        postgres_db: PostgresDatabase,
        project_id: int,
    ):
        """Test updating consolidation state."""
        # Create memory (starts unconsolidated)
        embedding = [0.1] * 768
        memory_id = await postgres_db.store_memory(
            project_id=project_id,
            content="Memory for consolidation",
            embedding=embedding,
            memory_type="fact",
        )

        memory = await postgres_db.get_memory(memory_id)
        assert memory["consolidation_state"] == "unconsolidated"

        # Transition through states
        await postgres_db.update_consolidation_state(memory_id, "consolidating")
        memory = await postgres_db.get_memory(memory_id)
        assert memory["consolidation_state"] == "consolidating"

        await postgres_db.update_consolidation_state(memory_id, "consolidated")
        memory = await postgres_db.get_memory(memory_id)
        assert memory["consolidation_state"] == "consolidated"
        assert memory["created_at"] is not None  # Has timestamp

    @pytest.mark.asyncio
    async def test_get_reconsolidation_window(
        self,
        postgres_db: PostgresDatabase,
        project_id: int,
    ):
        """Test getting memories in reconsolidation window."""
        # Create and mark memory as labile
        embedding = [0.1] * 768
        memory_id = await postgres_db.store_memory(
            project_id=project_id,
            content="Labile memory",
            embedding=embedding,
            memory_type="fact",
        )

        # Manually transition to labile (would be done by consolidation system)
        await postgres_db.update_consolidation_state(memory_id, "labile")

        # Get reconsolidation window (should be empty since we just created it)
        # In real use, memories would be older
        results = await postgres_db.get_reconsolidation_window(
            project_id=project_id,
            window_minutes=60,
        )

        # Results format is correct even if empty
        assert isinstance(results, list)


class TestTaskAndGoalOperations:
    """Test task and goal creation."""

    @pytest.fixture
    async def project_id(self, postgres_db: PostgresDatabase) -> int:
        """Create test project."""
        project = await postgres_db.create_project(
            name="task_test_project",
            path="/task/test",
        )
        return project.id

    @pytest.mark.asyncio
    async def test_create_task(self, postgres_db: PostgresDatabase, project_id: int):
        """Test creating a task."""
        task_id = await postgres_db.create_task(
            project_id=project_id,
            title="Test Task",
            description="A test task",
            priority=8,
            status="pending",
        )

        assert task_id is not None
        assert isinstance(task_id, int)

    @pytest.mark.asyncio
    async def test_create_goal(self, postgres_db: PostgresDatabase, project_id: int):
        """Test creating a goal."""
        goal_id = await postgres_db.create_goal(
            project_id=project_id,
            name="Test Goal",
            description="A test goal",
            priority=9,
        )

        assert goal_id is not None
        assert isinstance(goal_id, int)


class TestEpisodicEventOperations:
    """Test episodic event storage."""

    @pytest.fixture
    async def project_id(self, postgres_db: PostgresDatabase) -> int:
        """Create test project."""
        project = await postgres_db.create_project(
            name="episodic_test_project",
            path="/episodic/test",
        )
        return project.id

    @pytest.mark.asyncio
    async def test_store_episodic_event(self, postgres_db: PostgresDatabase, project_id: int):
        """Test storing an episodic event."""
        import time

        event_id = await postgres_db.store_episodic_event(
            project_id=project_id,
            session_id="test_session_123",
            timestamp=int(time.time() * 1000),
            event_type="learning",
            content="Learned about pgvector",
            context_cwd="/home/user/projects",
            learned="PostgreSQL pgvector is efficient",
            confidence=0.9,
        )

        assert event_id is not None
        assert isinstance(event_id, int)


class TestCodeMetadataOperations:
    """Test code metadata storage."""

    @pytest.fixture
    async def project_and_memory(self, postgres_db: PostgresDatabase):
        """Create project with test memory for code entity."""
        project = await postgres_db.create_project(
            name="code_test_project",
            path="/code/test",
        )

        embedding = [0.1] * 768
        memory_id = await postgres_db.store_memory(
            project_id=project.id,
            content="def search_function(): pass",
            embedding=embedding,
            memory_type="code_snippet",
            domain="code-analysis",
        )

        return project.id, memory_id

    @pytest.mark.asyncio
    async def test_store_code_entity(
        self,
        postgres_db: PostgresDatabase,
        project_and_memory: tuple,
    ):
        """Test storing code entity metadata."""
        project_id, memory_id = project_and_memory

        code_id = await postgres_db.store_code_entity(
            project_id=project_id,
            memory_vector_id=memory_id,
            file_path="src/search.py",
            entity_name="search_function",
            entity_type="function",
            language="python",
            signature="def search_function(query: str) -> List[Result]",
            docstring="Search for matching results",
            semantic_hash="abc123def456",
            cyclomatic_complexity=3,
            lines_of_code=15,
        )

        assert code_id is not None
        assert isinstance(code_id, int)


class TestTransactionSupport:
    """Test transaction context manager."""

    @pytest.mark.asyncio
    async def test_transaction_context(self, postgres_db: PostgresDatabase):
        """Test transaction context manager."""
        project = await postgres_db.create_project(
            name="transaction_test",
            path="/transaction/test",
        )

        # Operations within transaction should be atomic
        async with postgres_db.transaction() as conn:
            # Would fail if transaction not working properly
            result = await conn.execute("SELECT %s", (project.id,))
            row = await result.fetchone()
            assert row[0] == project.id


@pytest.mark.asyncio
async def test_postgres_backend_available():
    """Test that PostgreSQL backend is available."""
    from athena.core.database_factory import DatabaseFactory

    available = DatabaseFactory.get_available_backends()
    assert "postgres" in available or "postgresql" in available


if __name__ == "__main__":
    # Run with: pytest tests/integration/test_postgres_database.py -v
    pytest.main([__file__, "-v"])
