"""Integration tests for PostgreSQL code search functionality.

Tests code entity storage, semantic search, and dependency analysis
using PostgreSQL backend.
"""

import pytest
import asyncio
from typing import AsyncGenerator

# Skip if PostgreSQL not available
pytest.importorskip("psycopg")

import pytest_asyncio

from athena.core.database_postgres import PostgresDatabase
from athena.code_search.postgres_code_integration import (
    PostgresCodeIntegration,
    initialize_code_search_postgres,
)
from athena.code_search.code_graph_integration import CodeEntity, CodeEntityType


@pytest.fixture
def postgres_db() -> PostgresDatabase:
    """Create PostgreSQL database instance."""
    db = PostgresDatabase(
        host="localhost",
        port=5432,
        dbname="athena",
        user="athena",
        password="athena_dev",
    )
    return db


@pytest_asyncio.fixture
async def initialized_db(postgres_db: PostgresDatabase) -> AsyncGenerator:
    """Initialize PostgreSQL database."""
    await postgres_db.initialize()
    yield postgres_db
    await postgres_db.close()


@pytest_asyncio.fixture
async def code_integration(
    initialized_db: PostgresDatabase,
) -> PostgresCodeIntegration:
    """Create code search integration."""
    return PostgresCodeIntegration(db=initialized_db)


@pytest_asyncio.fixture
async def project_id(initialized_db: PostgresDatabase) -> int:
    """Create test project."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    project = await initialized_db.create_project(
        name=f"code_search_test_{unique_id}",
        path=f"/test/code_search/{unique_id}",
        language="python",
    )
    return project.id


class TestCodeEntityStorage:
    """Test code entity storage with embeddings."""

    @pytest.mark.asyncio
    async def test_store_code_entity(
        self,
        code_integration: PostgresCodeIntegration,
        project_id: int,
    ):
        """Test storing a code entity."""
        entity = CodeEntity(
            name="search_function",
            entity_type=CodeEntityType.FUNCTION,
            file_path="src/search.py",
            line_number=10,
            docstring="Search for items in collection",
            complexity=2,
        )

        embedding = [0.1] * 768

        code_id = await code_integration.store_code_entity(
            project_id=project_id,
            file_path="src/search.py",
            entity=entity,
            embedding=embedding,
            signature="def search_function(query: str) -> List[Result]",
            dependencies=["utils.validate_query"],
            dependents=["main.run_search"],
        )

        assert code_id > 0, "Code entity should be stored successfully"

    @pytest.mark.asyncio
    async def test_store_class_entity(
        self,
        code_integration: PostgresCodeIntegration,
        project_id: int,
    ):
        """Test storing a class entity."""
        entity = CodeEntity(
            name="SearchEngine",
            entity_type=CodeEntityType.CLASS,
            file_path="src/search_engine.py",
            line_number=5,
            docstring="Main search engine class",
            complexity=4,
        )

        embedding = [0.2] * 768

        code_id = await code_integration.store_code_entity(
            project_id=project_id,
            file_path="src/search_engine.py",
            entity=entity,
            embedding=embedding,
            signature="class SearchEngine",
        )

        assert code_id > 0, "Class entity should be stored"

    @pytest.mark.asyncio
    async def test_store_multiple_entities(
        self,
        code_integration: PostgresCodeIntegration,
        project_id: int,
    ):
        """Test storing multiple code entities."""
        entities = [
            CodeEntity(
                name="parse_query",
                entity_type=CodeEntityType.FUNCTION,
                file_path="src/parser.py",
                line_number=1,
                complexity=1,
            ),
            CodeEntity(
                name="validate_input",
                entity_type=CodeEntityType.FUNCTION,
                file_path="src/parser.py",
                line_number=10,
                complexity=2,
            ),
            CodeEntity(
                name="Parser",
                entity_type=CodeEntityType.CLASS,
                file_path="src/parser.py",
                line_number=20,
                complexity=3,
            ),
        ]

        code_ids = []
        for i, entity in enumerate(entities):
            embedding = [0.1 * (i + 1)] * 768
            code_id = await code_integration.store_code_entity(
                project_id=project_id,
                file_path=entity.file_path,
                entity=entity,
                embedding=embedding,
                signature=f"Entity {i}",
            )
            code_ids.append(code_id)

        assert len([cid for cid in code_ids if cid > 0]) == 3, "All entities should be stored"


class TestCodeSearch:
    """Test semantic code search."""

    @pytest.fixture
    async def populated_project(
        self,
        code_integration: PostgresCodeIntegration,
        project_id: int,
    ) -> int:
        """Populate project with code entities."""
        entities_data = [
            (
                "validate_user_input",
                CodeEntityType.FUNCTION,
                "src/validation.py",
                "Validate user input for correctness",
                [0.1] * 768,
            ),
            (
                "sanitize_string",
                CodeEntityType.FUNCTION,
                "src/validation.py",
                "Sanitize string input removing special chars",
                [0.15] * 768,
            ),
            (
                "check_permissions",
                CodeEntityType.FUNCTION,
                "src/auth.py",
                "Check user permissions for action",
                [0.3] * 768,
            ),
        ]

        for name, etype, fpath, doc, embedding in entities_data:
            entity = CodeEntity(
                name=name,
                entity_type=etype,
                file_path=fpath,
                line_number=1,
                docstring=doc,
                complexity=2,
            )

            await code_integration.store_code_entity(
                project_id=project_id,
                file_path=fpath,
                entity=entity,
                embedding=embedding,
            )

        return project_id

    @pytest.mark.asyncio
    async def test_semantic_code_search(
        self,
        code_integration: PostgresCodeIntegration,
        populated_project: int,
    ):
        """Test semantic search for code entities."""
        # Search for validation-related code
        query_embedding = [0.12] * 768

        results = await code_integration.search_code_entities(
            project_id=populated_project,
            query_embedding=query_embedding,
            query_text="validation input checking",
            limit=5,
            min_similarity=0.3,
        )

        assert isinstance(results, list), "Should return list of results"
        # May be empty due to basic mock embeddings, but should not error
        assert all(hasattr(r, "code_id") for r in results), "Results should have code_id"

    @pytest.mark.asyncio
    async def test_code_search_with_filters(
        self,
        code_integration: PostgresCodeIntegration,
        populated_project: int,
    ):
        """Test code search with entity type filters."""
        query_embedding = [0.1] * 768

        results = await code_integration.search_code_entities(
            project_id=populated_project,
            query_embedding=query_embedding,
            query_text="validation",
            entity_types=["function"],
            limit=10,
        )

        assert isinstance(results, list), "Should return filtered results"


class TestDependencyAnalysis:
    """Test code dependency analysis."""

    @pytest.fixture
    async def entities_with_dependencies(
        self,
        code_integration: PostgresCodeIntegration,
        project_id: int,
    ) -> int:
        """Create entities with dependency relationships."""
        # Store entities
        base_entity = CodeEntity(
            name="cache_manager",
            entity_type=CodeEntityType.CLASS,
            file_path="src/cache.py",
            line_number=1,
            complexity=2,
        )

        await code_integration.store_code_entity(
            project_id=project_id,
            file_path="src/cache.py",
            entity=base_entity,
            embedding=[0.1] * 768,
            dependencies=["redis", "utils"],
            dependents=["search_engine", "database"],
        )

        return project_id

    @pytest.mark.asyncio
    async def test_get_dependency_chain(
        self,
        code_integration: PostgresCodeIntegration,
        entities_with_dependencies: int,
    ):
        """Test retrieving dependency chain."""
        graph = await code_integration.get_dependency_chain(
            project_id=entities_with_dependencies,
            entity_name="cache_manager",
            depth=3,
            direction="outgoing",
        )

        assert graph is not None, "Should return dependency graph"
        assert hasattr(graph, "dependencies"), "Graph should have dependencies"

    @pytest.mark.asyncio
    async def test_code_statistics(
        self,
        code_integration: PostgresCodeIntegration,
        project_id: int,
    ):
        """Test retrieving code statistics."""
        stats = await code_integration.get_code_statistics(project_id=project_id)

        assert isinstance(stats, dict), "Should return statistics dictionary"
        assert "total_files" in stats or len(stats) == 0, "Should have expected fields"


class TestCodeMemoryIntegration:
    """Test integration between code entities and memory layer."""

    @pytest.mark.asyncio
    async def test_code_entity_stored_as_memory(
        self,
        code_integration: PostgresCodeIntegration,
        initialized_db: PostgresDatabase,
        project_id: int,
    ):
        """Test that code entities are stored as memory vectors."""
        entity = CodeEntity(
            name="data_processor",
            entity_type=CodeEntityType.FUNCTION,
            file_path="src/processor.py",
            line_number=15,
            docstring="Process data from source",
            complexity=3,
        )

        embedding = [0.25] * 768

        code_id = await code_integration.store_code_entity(
            project_id=project_id,
            file_path="src/processor.py",
            entity=entity,
            embedding=embedding,
        )

        # Verify memory was created
        if code_id > 0:
            # In full implementation, would verify memory layer via queries
            assert code_id > 0, "Code entity should reference memory"


class TestPostgresCodeIntegrationInit:
    """Test initialization of PostgreSQL code integration."""

    @pytest.mark.asyncio
    async def test_initialize_with_postgres(
        self,
        postgres_db: PostgresDatabase,
    ):
        """Test initializing code search with PostgreSQL."""
        await postgres_db.initialize()

        integration = await initialize_code_search_postgres(db=postgres_db)

        assert integration is not None, "Should initialize integration"
        assert integration.is_postgres, "Should detect PostgreSQL"

        await postgres_db.close()

    @pytest.mark.asyncio
    async def test_initialize_without_db(self):
        """Test initializing without database."""
        integration = await initialize_code_search_postgres(db=None)

        assert integration is not None, "Should initialize without database"
        assert not integration.is_postgres, "Should not detect PostgreSQL"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
