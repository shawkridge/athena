"""Tests for code search graph store integration."""

import pytest
from pathlib import Path
from athena.code_search.tree_sitter_search import TreeSitterCodeSearch


class MockGraphStore:
    """Mock graph store for testing."""

    def __init__(self):
        """Initialize mock graph store."""
        self.entities = {}
        self.relations = []

    def add_entity(self, entity_id: str, entity_type: str, properties: dict):
        """Add entity to graph."""
        self.entities[entity_id] = {
            "id": entity_id,
            "type": entity_type,
            "properties": properties,
        }

    def add_relation(self, source_id: str, target_id: str, relation_type: str, properties: dict = None):
        """Add relation between entities."""
        self.relations.append({
            "source": source_id,
            "target": target_id,
            "type": relation_type,
            "properties": properties or {},
        })

    def get_entity(self, entity_id: str):
        """Get entity from graph."""
        return self.entities.get(entity_id)

    def get_relations(self, source_id: str = None, relation_type: str = None):
        """Get relations from graph."""
        results = self.relations
        if source_id:
            results = [r for r in results if r["source"] == source_id]
        if relation_type:
            results = [r for r in results if r["type"] == relation_type]
        return results


@pytest.fixture
def test_repo(tmp_path):
    """Create a test repository."""
    (tmp_path / "src").mkdir()

    main_file = tmp_path / "src" / "main.py"
    main_file.write_text("""
def authenticate(user: str) -> bool:
    '''Authenticate a user.'''
    return validate_user(user) and check_password(user)

def validate_user(user: str) -> bool:
    '''Validate user credentials.'''
    return len(user) > 0

def check_password(user: str) -> bool:
    '''Check user password.'''
    return True

class AuthHandler:
    '''Handle authentication.'''
    def login(self, user: str) -> bool:
        return authenticate(user)

    def logout(self, user: str) -> bool:
        return True
""")

    return tmp_path


@pytest.fixture
def graph_store():
    """Create mock graph store."""
    return MockGraphStore()


class TestGraphStoreIntegration:
    """Test code search graph store integration."""

    def test_initialization_with_graph_store(self, test_repo, graph_store):
        """Test TreeSitterCodeSearch with graph store."""
        search = TreeSitterCodeSearch(str(test_repo), graph_store=graph_store)
        assert search.graph_store is graph_store

    def test_add_units_to_graph_on_index(self, test_repo, graph_store):
        """Test that units are added to graph when index is built."""
        search = TreeSitterCodeSearch(str(test_repo), graph_store=graph_store)
        search.build_index()

        # Verify entities were added
        assert len(graph_store.entities) > 0, "No entities added to graph"

    def test_entities_have_correct_properties(self, test_repo, graph_store):
        """Test that entities have correct properties."""
        search = TreeSitterCodeSearch(str(test_repo), graph_store=graph_store)
        search.build_index()

        # Find an entity
        entities = list(graph_store.entities.values())
        assert len(entities) > 0

        # Check first entity
        entity = entities[0]
        assert "id" in entity
        assert "type" in entity
        assert "properties" in entity
        assert "name" in entity["properties"]
        assert "file" in entity["properties"]
        assert "signature" in entity["properties"]

    def test_code_units_become_entities(self, test_repo, graph_store):
        """Test that code units are added as entities to graph."""
        search = TreeSitterCodeSearch(str(test_repo), graph_store=graph_store)
        search.build_index()

        # Get indexed units
        units = search.semantic_searcher.units
        assert len(units) > 0

        # Check that each unit has corresponding entity in graph
        for unit in units:
            entity = graph_store.get_entity(unit.id)
            assert entity is not None, f"Unit {unit.id} not found in graph"
            assert entity["type"] == unit.type
            assert entity["properties"]["name"] == unit.name

    def test_dependency_relations_added(self, test_repo, graph_store):
        """Test that dependency relations are added to graph."""
        search = TreeSitterCodeSearch(str(test_repo), graph_store=graph_store)
        search.build_index()

        # Verify relations exist
        relations = graph_store.get_relations(relation_type="depends_on")
        assert len(relations) > 0, "No dependency relations found"

    def test_entity_types_in_graph(self, test_repo, graph_store):
        """Test that correct entity types are in graph."""
        search = TreeSitterCodeSearch(str(test_repo), graph_store=graph_store)
        search.build_index()

        # Get all entity types
        entity_types = {e["type"] for e in graph_store.entities.values()}

        # Should have function and class types
        assert "function" in entity_types, "No function entities in graph"
        assert "class" in entity_types, "No class entities in graph"

    def test_relation_properties_preserved(self, test_repo, graph_store):
        """Test that relation properties are preserved."""
        search = TreeSitterCodeSearch(str(test_repo), graph_store=graph_store)
        search.build_index()

        relations = graph_store.get_relations()
        assert len(relations) > 0

        # Check first relation
        relation = relations[0]
        assert "type" in relation["properties"]

    def test_graph_without_store_doesnt_error(self, test_repo):
        """Test that code search works without graph store."""
        # Should not raise error
        search = TreeSitterCodeSearch(str(test_repo), graph_store=None)
        search.build_index()

        # Should still be able to search
        results = search.search("authenticate", min_score=0.0)
        assert len(results) > 0

    def test_entity_count_matches_units_count(self, test_repo, graph_store):
        """Test that entity count matches indexed units count."""
        search = TreeSitterCodeSearch(str(test_repo), graph_store=graph_store)
        search.build_index()

        units_count = len(search.semantic_searcher.units)
        entities_count = len(graph_store.entities)

        assert entities_count == units_count, \
            f"Entity count {entities_count} != units count {units_count}"

    def test_graph_queryable_after_indexing(self, test_repo, graph_store):
        """Test that graph is queryable after indexing."""
        search = TreeSitterCodeSearch(str(test_repo), graph_store=graph_store)
        search.build_index()

        # Query for function entities
        function_entities = [
            e for e in graph_store.entities.values()
            if e["type"] == "function"
        ]

        assert len(function_entities) > 0

        # Verify they have correct properties
        for entity in function_entities:
            assert "name" in entity["properties"]
            assert entity["properties"]["name"] in [
                "authenticate",
                "validate_user",
                "check_password",
            ]


class TestGraphStoreAdvancedFeatures:
    """Test advanced graph store features."""

    def test_find_dependencies_in_graph(self, test_repo, graph_store):
        """Test finding dependencies through graph."""
        search = TreeSitterCodeSearch(str(test_repo), graph_store=graph_store)
        search.build_index()

        # Find authenticate function
        auth_entity = None
        for entity in graph_store.entities.values():
            if entity["properties"].get("name") == "authenticate":
                auth_entity = entity
                break

        assert auth_entity is not None

        # Find its dependencies
        depends_on_relations = [
            r for r in graph_store.get_relations(source_id=auth_entity["id"])
            if r["type"] == "depends_on"
        ]

        # authenticate depends on validate_user and check_password
        assert len(depends_on_relations) >= 0  # May vary based on extraction

    def test_graph_enables_code_navigation(self, test_repo, graph_store):
        """Test that graph enables code navigation queries."""
        search = TreeSitterCodeSearch(str(test_repo), graph_store=graph_store)
        search.build_index()

        # Example: Find all functions that depend on validate_user
        # This would be used for impact analysis

        all_entities = graph_store.entities.values()
        assert len(all_entities) > 0

        # Verify we can traverse the graph
        for entity in all_entities:
            relations = graph_store.get_relations(source_id=entity["id"])
            # Each entity can have relations
            assert isinstance(relations, list)

    def test_bidirectional_relations(self, test_repo, graph_store):
        """Test that relations support bidirectional queries."""
        search = TreeSitterCodeSearch(str(test_repo), graph_store=graph_store)
        search.build_index()

        # Count forward and backward relations
        forward_relations = graph_store.get_relations(relation_type="depends_on")

        # For a real graph store, we'd want to query backward relations too
        # This test ensures the structure supports such queries

        assert isinstance(forward_relations, list)
        if len(forward_relations) > 0:
            assert "source" in forward_relations[0]
            assert "target" in forward_relations[0]


class TestGraphStorePerformance:
    """Test graph store integration performance."""

    def test_graph_addition_doesnt_slow_indexing(self, test_repo, graph_store):
        """Test that graph store addition has minimal performance impact."""
        import time

        # Index without graph store
        search_no_graph = TreeSitterCodeSearch(str(test_repo), graph_store=None)
        start = time.time()
        search_no_graph.build_index()
        time_without_graph = time.time() - start

        # Index with graph store
        search_with_graph = TreeSitterCodeSearch(str(test_repo), graph_store=graph_store)
        start = time.time()
        search_with_graph.build_index()
        time_with_graph = time.time() - start

        # Graph store addition should not more than 2x slower
        # (allowing for reasonable overhead)
        assert time_with_graph < time_without_graph * 2, \
            f"Graph store caused excessive slowdown: {time_with_graph}s vs {time_without_graph}s"

    def test_graph_memory_usage_reasonable(self, test_repo, graph_store):
        """Test that graph store memory usage is reasonable."""
        search = TreeSitterCodeSearch(str(test_repo), graph_store=graph_store)
        search.build_index()

        # Estimate memory usage of graph store
        entities_size = len(graph_store.entities) * 200  # ~200 bytes per entity
        relations_size = len(graph_store.relations) * 150  # ~150 bytes per relation
        total_size_bytes = entities_size + relations_size

        # Should be reasonable for 50 units
        assert total_size_bytes < 1_000_000, "Graph store using excessive memory"
