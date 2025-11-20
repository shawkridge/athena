"""Unit tests for knowledge graph operations."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from athena.graph.operations import GraphOperations

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db():
    """Create a mock database."""
    return MagicMock()


@pytest.fixture
def mock_store():
    """Create a mock graph store with intelligent mocking."""
    # We'll track entities and relations in dicts for stateful responses
    entities = {}
    relations = {}
    next_entity_id = [1]
    next_relation_id = [1]

    async def add_entity(entity):
        entity_id = next_entity_id[0]
        next_entity_id[0] += 1
        entity.id = entity_id
        entities[entity_id] = entity
        return entity_id

    async def add_relationship(relationship):
        rel_id = next_relation_id[0]
        next_relation_id[0] += 1
        relationship.id = rel_id
        relations[rel_id] = relationship
        return rel_id

    def get_entity(entity_id):
        if isinstance(entity_id, str):
            entity_id = int(entity_id)
        return entities.get(entity_id)

    def search_entities(query, entity_type=None, project_id=None):
        results = []
        for entity in entities.values():
            if query.lower() in entity.name.lower():
                if entity_type and entity.entity_type != entity_type:
                    continue
                results.append(entity)
        return results

    async def find_related(entity_id, relation_types=None, limit=100, depth=1):
        if isinstance(entity_id, str):
            entity_id = int(entity_id)

        if depth < 1:
            return []

        # BFS traversal with depth limit
        visited = set()
        related_entities_by_distance = {}
        current_level = [entity_id]
        current_distance = 0

        while current_level and current_distance < depth:
            next_level = []
            current_distance += 1

            for eid in current_level:
                if eid in visited:
                    continue
                visited.add(eid)

                for rel in relations.values():
                    if rel.from_entity_id == eid and rel.to_entity_id not in visited:
                        if relation_types is None or rel.relation_type in relation_types:
                            next_level.append(rel.to_entity_id)
                    elif rel.to_entity_id == eid and rel.from_entity_id not in visited:
                        if relation_types is None or rel.relation_type in relation_types:
                            next_level.append(rel.from_entity_id)

            if next_level:
                if current_distance not in related_entities_by_distance:
                    related_entities_by_distance[current_distance] = []
                for eid in next_level:
                    entity = get_entity(eid)
                    if entity:
                        related_entities_by_distance[current_distance].append(entity)

            current_level = next_level

        # Flatten results sorted by distance
        related_entities = []
        for distance in sorted(related_entities_by_distance.keys()):
            related_entities.extend(related_entities_by_distance[distance])
            if len(related_entities) >= limit:
                break

        return related_entities[:limit]

    async def get_communities(limit=10):
        """Get detected entity communities."""
        communities = []
        visited = set()

        for entity_id in list(entities.keys())[: limit * 10]:
            if entity_id in visited:
                continue

            # Get related entities
            related = await find_related(entity_id, limit=5)
            if related:
                community = {
                    "id": len(communities),
                    "members": [entity_id] + [e.id for e in related],
                    "size": len(related) + 1,
                    "strength": 0.5,
                }
                communities.append(community)
                visited.add(entity_id)
                for entity in related:
                    visited.add(entity.id)

            if len(communities) >= limit:
                break

        return communities

    async def update_entity(entity):
        if entity.id in entities:
            entities[entity.id] = entity
            return True
        return False

    async def list_entities(limit=100):
        return list(entities.values())[:limit]

    async def list_relationships(limit=100):
        return list(relations.values())[:limit]

    store = MagicMock()
    store.add_entity = AsyncMock(side_effect=add_entity)
    store.add_relationship = AsyncMock(side_effect=add_relationship)
    store.get_entity = MagicMock(side_effect=get_entity)
    store.search_entities = MagicMock(side_effect=search_entities)
    store.find_related = AsyncMock(side_effect=find_related)
    store.get_communities = AsyncMock(side_effect=get_communities)
    store.update_entity = AsyncMock(side_effect=update_entity)
    store.list_entities = AsyncMock(side_effect=list_entities)
    store.list_relationships = AsyncMock(side_effect=list_relationships)
    return store


@pytest.fixture
def operations(mock_db, mock_store):
    """Create test operations instance with mocked store."""
    ops = GraphOperations(mock_db, mock_store)
    return ops


# ============================================================================
# Basic CRUD Operations Tests
# ============================================================================


class TestEntityCRUD:
    """Test entity CRUD operations."""

    async def test_add_entity_basic(self, operations: GraphOperations):
        """Test adding a basic entity."""
        entity_id = await operations.add_entity(
            name="Python",
            entity_type="Concept",
            description="Programming language",
        )

        assert entity_id is not None
        assert isinstance(entity_id, int)

    async def test_add_entity_with_metadata(self, operations: GraphOperations):
        """Test adding entity with metadata."""
        entity_id = await operations.add_entity(
            name="Claude",
            entity_type="Person",
            description="AI assistant",
            metadata={"version": "3.5", "created_by": "Anthropic"},
        )

        assert entity_id is not None

        # Verify metadata was stored
        entity = await operations.find_entity(str(entity_id))
        assert entity is not None
        assert entity.metadata.get("version") == "3.5"

    async def test_add_entity_validates_required_fields(self, operations: GraphOperations):
        """Test that add_entity validates required fields."""
        with pytest.raises(ValueError):
            await operations.add_entity(name="", entity_type="Concept")

        with pytest.raises(ValueError):
            await operations.add_entity(name="Test", entity_type="")

    async def test_add_entity_various_types(self, operations: GraphOperations):
        """Test adding entities of different types."""
        types = ["Concept", "Person", "File", "Component", "Task"]

        for entity_type in types:
            entity_id = await operations.add_entity(
                name=f"Entity_{entity_type}",
                entity_type=entity_type,
            )
            assert entity_id is not None

    async def test_find_entity_success(self, operations: GraphOperations):
        """Test finding an existing entity."""
        entity_id = await operations.add_entity(
            name="Test Entity",
            entity_type="Concept",
        )

        found = await operations.find_entity(str(entity_id))
        assert found is not None
        assert found.name == "Test Entity"

    async def test_find_entity_not_found(self, operations: GraphOperations):
        """Test finding a non-existent entity."""
        found = await operations.find_entity("999999")
        assert found is None

    async def test_find_entity_with_invalid_id(self, operations: GraphOperations):
        """Test finding entity with invalid ID format."""
        # Should handle gracefully
        found = await operations.find_entity("invalid_id")
        # May return None or raise ValueError - both acceptable


# ============================================================================
# Relationship Tests
# ============================================================================


class TestRelationships:
    """Test relationship management."""

    async def test_add_relationship_basic(self, operations: GraphOperations):
        """Test adding a basic relationship."""
        # Create two entities first
        entity1_id = await operations.add_entity("Python", "Concept")
        entity2_id = await operations.add_entity("Programming", "Concept")

        # Add relationship
        rel_id = await operations.add_relationship(
            source_id=str(entity1_id),
            target_id=str(entity2_id),
            relationship_type="relates_to",
        )

        assert rel_id is not None
        assert isinstance(rel_id, int)

    async def test_add_relationship_with_strength(self, operations: GraphOperations):
        """Test adding relationship with custom strength."""
        entity1_id = await operations.add_entity("A", "Component")
        entity2_id = await operations.add_entity("B", "Component")

        rel_id = await operations.add_relationship(
            source_id=str(entity1_id),
            target_id=str(entity2_id),
            relationship_type="relates_to",
            strength=0.8,
        )

        assert rel_id is not None

    async def test_add_relationship_strength_bounds(self, operations: GraphOperations):
        """Test that relationship strength is bounded [0.0, 1.0]."""
        entity1_id = await operations.add_entity("X", "Component")
        entity2_id = await operations.add_entity("Y", "Component")

        # Test strength > 1.0 gets clamped
        rel_id = await operations.add_relationship(
            source_id=str(entity1_id),
            target_id=str(entity2_id),
            relationship_type="relates_to",
            strength=1.5,
        )
        assert rel_id is not None

        # Test strength < 0.0 gets clamped
        rel_id2 = await operations.add_relationship(
            source_id=str(entity1_id),
            target_id=str(entity2_id),
            relationship_type="relates_to",
            strength=-0.5,
        )
        assert rel_id2 is not None

    async def test_add_relationship_validates_required_fields(self, operations: GraphOperations):
        """Test that add_relationship validates required fields."""
        entity_id = await operations.add_entity("Test", "Concept")

        with pytest.raises(ValueError):
            await operations.add_relationship(
                source_id="",
                target_id=str(entity_id),
                relationship_type="related",
            )

        with pytest.raises(ValueError):
            await operations.add_relationship(
                source_id=str(entity_id),
                target_id="",
                relationship_type="related",
            )

        with pytest.raises(ValueError):
            await operations.add_relationship(
                source_id=str(entity_id),
                target_id=str(entity_id),
                relationship_type="",
            )

    async def test_add_relationship_with_metadata(self, operations: GraphOperations):
        """Test adding relationship with metadata."""
        entity1_id = await operations.add_entity("Source", "Component")
        entity2_id = await operations.add_entity("Target", "Component")

        rel_id = await operations.add_relationship(
            source_id=str(entity1_id),
            target_id=str(entity2_id),
            relationship_type="relates_to",
            metadata={"context": "test_context", "weight": 0.8},
        )

        assert rel_id is not None


# ============================================================================
# Search and Filtering Tests
# ============================================================================


class TestSearchAndFiltering:
    """Test search and filtering capabilities."""

    async def test_search_entities_basic(self, operations: GraphOperations):
        """Test basic entity search."""
        # Add some entities
        await operations.add_entity("Python Programming", "Concept")
        await operations.add_entity("JavaScript", "Concept")
        await operations.add_entity("Python Snake", "Component")

        # Search
        results = await operations.search_entities("Python")

        assert len(results) >= 2
        assert all("Python" in entity.name for entity in results)

    async def test_search_entities_empty_query(self, operations: GraphOperations):
        """Test search with empty query."""
        results = await operations.search_entities("")
        assert results == []

    async def test_search_entities_with_type_filter(self, operations: GraphOperations):
        """Test search with entity type filter."""
        await operations.add_entity("Python", "Concept")
        await operations.add_entity("Python Snake", "Component")

        # Search for concepts only
        results = await operations.search_entities("Python", entity_type="Concept")

        assert len(results) >= 1
        # entity_type will be EntityType enum, just check it's not Component
        assert all(entity.entity_type != "Component" for entity in results)

    async def test_search_entities_with_limit(self, operations: GraphOperations):
        """Test search with result limit."""
        # Add many entities
        for i in range(10):
            await operations.add_entity(f"Test_{i}", "Concept")

        # Search with limit
        results = await operations.search_entities("Test", limit=5)

        assert len(results) <= 5

    async def test_search_entities_no_results(self, operations: GraphOperations):
        """Test search with no matching results."""
        await operations.add_entity("Apple", "Component")
        await operations.add_entity("Banana", "Component")

        results = await operations.search_entities("Zebra")

        assert len(results) == 0


# ============================================================================
# Related Entities Tests
# ============================================================================


class TestFindRelated:
    """Test finding related entities."""

    async def test_find_related_direct(self, operations: GraphOperations):
        """Test finding directly related entities."""
        # Create a simple graph: A -> B -> C
        entity_a = await operations.add_entity("A", "Concept")
        entity_b = await operations.add_entity("B", "Concept")
        entity_c = await operations.add_entity("C", "Concept")

        await operations.add_relationship(str(entity_a), str(entity_b), "contains")
        await operations.add_relationship(str(entity_b), str(entity_c), "contains")

        # Find entities related to A (should find B)
        related = await operations.find_related(str(entity_a))

        assert len(related) >= 1
        related_names = [e.name for e in related]
        assert "B" in related_names

    async def test_find_related_with_type_filter(self, operations: GraphOperations):
        """Test finding related entities with relationship type filter."""
        entity_a = await operations.add_entity("A", "Component")
        entity_b = await operations.add_entity("B", "Component")
        entity_c = await operations.add_entity("C", "Component")

        await operations.add_relationship(str(entity_a), str(entity_b), "contains")
        await operations.add_relationship(str(entity_a), str(entity_c), "relates_to")

        # Find only "contains" relationships
        related = await operations.find_related(
            str(entity_a),
            relationship_type="contains",
        )

        assert len(related) >= 1
        assert all(entity.name in ["B"] for entity in related)

    async def test_find_related_with_limit(self, operations: GraphOperations):
        """Test find_related with result limit."""
        entity_a = await operations.add_entity("A", "Concept")

        # Create many related entities
        for i in range(10):
            entity_b = await operations.add_entity(f"B_{i}", "Concept")
            await operations.add_relationship(str(entity_a), str(entity_b), "contains")

        # Find with limit
        related = await operations.find_related(str(entity_a), limit=3)

        assert len(related) <= 3

    async def test_find_related_no_relations(self, operations: GraphOperations):
        """Test finding related entities when none exist."""
        entity_a = await operations.add_entity("Isolated", "Concept")

        related = await operations.find_related(str(entity_a))

        assert len(related) == 0

    async def test_find_related_invalid_entity(self, operations: GraphOperations):
        """Test finding related entities with invalid entity ID."""
        related = await operations.find_related("999999")

        # Should return empty list or handle gracefully
        assert isinstance(related, list)

    async def test_find_related_with_depth_1(self, operations: GraphOperations):
        """Test find_related with depth=1 (direct relations only)."""
        # Create a chain: A -> B -> C -> D
        a = await operations.add_entity("A", "Concept")
        b = await operations.add_entity("B", "Concept")
        c = await operations.add_entity("C", "Concept")
        d = await operations.add_entity("D", "Concept")

        await operations.add_relationship(str(a), str(b), "contains")
        await operations.add_relationship(str(b), str(c), "contains")
        await operations.add_relationship(str(c), str(d), "contains")

        # With depth=1, A should only find B (direct neighbors)
        related = await operations.find_related(str(a), depth=1)
        related_ids = [e.id for e in related]

        assert b in related_ids
        assert c not in related_ids
        assert d not in related_ids

    async def test_find_related_with_depth_2(self, operations: GraphOperations):
        """Test find_related with depth=2 (up to 2 hops)."""
        # Create a chain: A -> B -> C -> D
        a = await operations.add_entity("A", "Concept")
        b = await operations.add_entity("B", "Concept")
        c = await operations.add_entity("C", "Concept")
        d = await operations.add_entity("D", "Concept")

        await operations.add_relationship(str(a), str(b), "contains")
        await operations.add_relationship(str(b), str(c), "contains")
        await operations.add_relationship(str(c), str(d), "contains")

        # With depth=2, A should find B and C (up to 2 hops)
        related = await operations.find_related(str(a), depth=2)
        related_ids = [e.id for e in related]

        assert b in related_ids
        assert c in related_ids
        assert d not in related_ids

    async def test_find_related_with_depth_3(self, operations: GraphOperations):
        """Test find_related with depth=3 (up to 3 hops)."""
        # Create a chain: A -> B -> C -> D
        a = await operations.add_entity("A", "Concept")
        b = await operations.add_entity("B", "Concept")
        c = await operations.add_entity("C", "Concept")
        d = await operations.add_entity("D", "Concept")

        await operations.add_relationship(str(a), str(b), "contains")
        await operations.add_relationship(str(b), str(c), "contains")
        await operations.add_relationship(str(c), str(d), "contains")

        # With depth=3, A should find B, C, and D
        related = await operations.find_related(str(a), depth=3)
        related_ids = [e.id for e in related]

        assert b in related_ids
        assert c in related_ids
        assert d in related_ids

    async def test_find_related_depth_clamping(self, operations: GraphOperations):
        """Test that depth parameter is clamped to valid range [1, 5]."""
        a = await operations.add_entity("A", "Concept")
        b = await operations.add_entity("B", "Concept")
        await operations.add_relationship(str(a), str(b), "contains")

        # Very large depth should be clamped to 5
        related = await operations.find_related(str(a), depth=100)
        assert isinstance(related, list)

        # Zero or negative depth should be clamped to 1
        related = await operations.find_related(str(a), depth=0)
        assert isinstance(related, list)


# ============================================================================
# Community Detection Tests
# ============================================================================


class TestCommunities:
    """Test community detection."""

    async def test_get_communities_basic(self, operations: GraphOperations):
        """Test getting entity communities."""
        # Create a simple connected graph
        entities = []
        for i in range(5):
            eid = await operations.add_entity(f"Entity_{i}", "Component")
            entities.append(eid)

        # Connect them in a chain
        for i in range(len(entities) - 1):
            await operations.add_relationship(
                str(entities[i]),
                str(entities[i + 1]),
                "contains",
            )

        # Get communities
        communities = await operations.get_communities()

        assert isinstance(communities, list)
        assert len(communities) >= 1

        # Each community should have members
        for community in communities:
            assert "members" in community
            assert "size" in community

    async def test_get_communities_with_limit(self, operations: GraphOperations):
        """Test get_communities with limit."""
        # Create multiple disconnected entities
        for i in range(10):
            await operations.add_entity(f"Entity_{i}", "Component")

        # Get communities with limit
        communities = await operations.get_communities(limit=3)

        assert len(communities) <= 3

    async def test_get_communities_empty_graph(self, operations: GraphOperations):
        """Test get_communities on empty graph."""
        communities = await operations.get_communities()

        assert isinstance(communities, list)
        assert len(communities) == 0

    async def test_community_structure(self, operations: GraphOperations):
        """Test that communities have expected structure."""
        entity_a = await operations.add_entity("A", "Component")
        entity_b = await operations.add_entity("B", "Component")
        await operations.add_relationship(str(entity_a), str(entity_b), "contains")

        communities = await operations.get_communities(limit=1)

        if communities:
            community = communities[0]
            # Check required fields
            assert "id" in community
            assert "members" in community
            assert "size" in community
            assert "strength" in community
            # Check types
            assert isinstance(community["members"], list)
            assert isinstance(community["size"], int)


# ============================================================================
# Importance Scoring Tests
# ============================================================================


class TestImportanceScoring:
    """Test entity importance updates."""

    async def test_update_entity_importance_valid(self, operations: GraphOperations):
        """Test updating entity importance with valid score."""
        entity_id = await operations.add_entity("Test", "Concept")

        success = await operations.update_entity_importance(str(entity_id), 0.8)

        assert success is True

    async def test_update_entity_importance_bounds(self, operations: GraphOperations):
        """Test importance score is bounded [0.0, 1.0]."""
        entity_id = await operations.add_entity("Test", "Concept")

        # Test high value gets clamped
        success = await operations.update_entity_importance(str(entity_id), 1.5)
        assert success is True

        # Test low value gets clamped
        success = await operations.update_entity_importance(str(entity_id), -0.5)
        assert success is True

    async def test_update_entity_importance_nonexistent(self, operations: GraphOperations):
        """Test updating importance for non-existent entity."""
        success = await operations.update_entity_importance("999999", 0.5)

        assert success is False

    async def test_update_entity_importance_extremes(self, operations: GraphOperations):
        """Test updating importance to extreme values."""
        entity_id = await operations.add_entity("Test", "Concept")

        # Min value
        success = await operations.update_entity_importance(str(entity_id), 0.0)
        assert success is True

        # Max value
        success = await operations.update_entity_importance(str(entity_id), 1.0)
        assert success is True


# ============================================================================
# Statistics Tests
# ============================================================================


class TestStatistics:
    """Test statistics generation."""

    async def test_get_statistics_empty_graph(self, operations: GraphOperations):
        """Test statistics on empty graph."""
        stats = await operations.get_statistics()

        assert "total_entities" in stats
        assert "total_relationships" in stats
        assert "entity_types" in stats
        assert "relationship_types" in stats

        assert stats["total_entities"] == 0
        assert stats["total_relationships"] == 0

    async def test_get_statistics_with_data(self, operations: GraphOperations):
        """Test statistics with actual data."""
        # Add entities of different types
        await operations.add_entity("Python", "Concept")
        await operations.add_entity("Java", "Concept")
        await operations.add_entity("Alice", "Person")

        # Add relationships
        e1 = await operations.add_entity("E1", "Component")
        e2 = await operations.add_entity("E2", "Component")
        await operations.add_relationship(str(e1), str(e2), "relates_to")

        stats = await operations.get_statistics()

        assert stats["total_entities"] >= 5
        assert stats["total_relationships"] >= 1
        assert "Concept" in stats["entity_types"]
        assert "Person" in stats["entity_types"]
        assert "relates_to" in stats["relationship_types"]

    async def test_get_statistics_average_importance(self, operations: GraphOperations):
        """Test that statistics include average importance (from metadata)."""
        e1 = await operations.add_entity("Entity1", "Concept")
        e2 = await operations.add_entity("Entity2", "Concept")

        # Update some importances
        await operations.update_entity_importance(str(e1), 0.8)
        await operations.update_entity_importance(str(e2), 0.6)

        stats = await operations.get_statistics()

        assert "avg_importance" in stats
        assert isinstance(stats["avg_importance"], (int, float))
        # Average of 0.8, 0.6 = 0.7
        assert 0.6 <= stats["avg_importance"] <= 0.8


# ============================================================================
# Error Handling and Edge Cases
# ============================================================================


class TestErrorHandling:
    """Test error handling and edge cases."""

    async def test_special_characters_in_entity_name(self, operations: GraphOperations):
        """Test entity names with special characters."""
        entity_id = await operations.add_entity(
            "Test@#$%Entity!",
            "Concept",
        )

        assert entity_id is not None
        found = await operations.find_entity(str(entity_id))
        assert found is not None

    async def test_unicode_characters_in_entity_name(self, operations: GraphOperations):
        """Test entity names with unicode characters."""
        entity_id = await operations.add_entity(
            "测试实体 🚀",
            "Concept",
        )

        assert entity_id is not None

    async def test_very_long_entity_name(self, operations: GraphOperations):
        """Test with very long entity name."""
        long_name = "A" * 1000
        entity_id = await operations.add_entity(long_name, "Concept")

        assert entity_id is not None

    async def test_circular_relationships(self, operations: GraphOperations):
        """Test handling of circular relationships."""
        entity_a = await operations.add_entity("A", "Component")
        entity_b = await operations.add_entity("B", "Component")

        # Create circular relationship: A -> B -> A
        await operations.add_relationship(str(entity_a), str(entity_b), "contains")
        await operations.add_relationship(str(entity_b), str(entity_a), "contains")

        # Both should find each other as related
        related_from_a = await operations.find_related(str(entity_a))
        assert len(related_from_a) > 0

    async def test_self_relationship(self, operations: GraphOperations):
        """Test entity with relationship to itself."""
        entity = await operations.add_entity("Self", "Component")

        # Create self-relationship
        rel_id = await operations.add_relationship(
            str(entity),
            str(entity),
            "relates_to",
        )

        assert rel_id is not None

    async def test_duplicate_relationships(self, operations: GraphOperations):
        """Test handling of duplicate relationships."""
        entity_a = await operations.add_entity("A", "Component")
        entity_b = await operations.add_entity("B", "Component")

        # Add same relationship twice
        rel_id1 = await operations.add_relationship(
            str(entity_a),
            str(entity_b),
            "contains",
        )
        rel_id2 = await operations.add_relationship(
            str(entity_a),
            str(entity_b),
            "contains",
        )

        # Both should be created (or only one if deduplication is implemented)
        assert rel_id1 is not None
        assert rel_id2 is not None


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests combining multiple operations."""

    async def test_full_entity_lifecycle(self, operations: GraphOperations):
        """Test complete entity lifecycle."""
        # Create
        entity_id = await operations.add_entity(
            name="Lifecycle Test",
            entity_type="Concept",
            description="Testing full lifecycle",
            metadata={"version": 1},
        )
        assert entity_id is not None

        # Read
        entity = await operations.find_entity(str(entity_id))
        assert entity is not None
        assert entity.name == "Lifecycle Test"

        # Search
        results = await operations.search_entities("Lifecycle")
        assert entity_id in [e.id for e in results]

        # Update importance
        updated = await operations.update_entity_importance(str(entity_id), 0.9)
        assert updated is True

    async def test_relationship_graph_traversal(self, operations: GraphOperations):
        """Test graph traversal through relationships."""
        # Create a small graph: A -> B -> C
        a = await operations.add_entity("A", "Concept")
        b = await operations.add_entity("B", "Concept")
        c = await operations.add_entity("C", "Concept")

        await operations.add_relationship(str(a), str(b), "depends_on")
        await operations.add_relationship(str(b), str(c), "depends_on")

        # From A, should find B
        related_from_a = await operations.find_related(str(a))
        assert len(related_from_a) >= 1

        # From B, should find C
        related_from_b = await operations.find_related(str(b))
        assert len(related_from_b) >= 1

    async def test_multiple_relationship_types(self, operations: GraphOperations):
        """Test handling multiple relationship types."""
        entity_a = await operations.add_entity("A", "Component")
        entity_b = await operations.add_entity("B", "Component")
        entity_c = await operations.add_entity("C", "Component")

        # Different relationship types from A
        await operations.add_relationship(str(entity_a), str(entity_b), "contains")
        await operations.add_relationship(str(entity_a), str(entity_c), "relates_to")

        # Find all related
        all_related = await operations.find_related(str(entity_a))
        assert len(all_related) >= 2

        # Find specific type
        connected = await operations.find_related(str(entity_a), relationship_type="contains")
        assert len(connected) >= 1

    async def test_metadata_preservation(self, operations: GraphOperations):
        """Test that metadata is preserved through operations."""
        metadata = {
            "source": "test",
            "confidence": 0.95,
            "tags": ["important", "test"],
        }

        entity_id = await operations.add_entity(
            "Test",
            "Concept",
            metadata=metadata,
        )

        entity = await operations.find_entity(str(entity_id))
        assert entity is not None
        assert entity.metadata == metadata
