"""Tests for GraphRAG community detection with Leiden clustering."""

import pytest
import tempfile
from pathlib import Path
from collections import defaultdict

from athena.core.database import Database
from athena.graph.communities import (
    LeidenClustering,
    CommunityAnalyzer,
    Community,
    CommunityHierarchy,
)
from athena.graph.models import Entity, Relation, EntityType, RelationType


@pytest.fixture
def db():
    """Create temporary test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        database = Database(str(db_path))
        yield database


class TestLeidenClustering:
    """Test Leiden clustering algorithm."""

    def test_simple_two_communities(self):
        """Test detecting two well-separated communities."""
        # Create graph with two clear communities
        # Community A: 0-1-2
        # Community B: 3-4-5
        graph = {
            0: {1, 2},
            1: {0, 2},
            2: {0, 1},
            3: {4, 5},
            4: {3, 5},
            5: {3, 4},
        }

        leiden = LeidenClustering(graph, seed=42)
        partition = leiden.detect_communities(min_community_size=1)

        # Should have 2 communities
        communities = set(partition.values())
        assert len(communities) == 2

        # Check that nodes in same community are separated from other community
        comm_0 = partition[0]
        assert partition[1] == comm_0
        assert partition[2] == comm_0

        comm_3 = partition[3]
        assert partition[4] == comm_3
        assert partition[5] == comm_3
        assert comm_0 != comm_3

    def test_single_community(self):
        """Test when all nodes should be in one community."""
        # Fully connected graph
        graph = {
            0: {1, 2},
            1: {0, 2},
            2: {0, 1},
        }

        leiden = LeidenClustering(graph)
        partition = leiden.detect_communities()

        communities = set(partition.values())
        assert len(communities) == 1

    def test_modularity_computation(self):
        """Test modularity calculation."""
        graph = {
            0: {1, 2},
            1: {0, 2},
            2: {0, 1},
            3: {4, 5},
            4: {3, 5},
            5: {3, 4},
        }

        leiden = LeidenClustering(graph)

        # Good partition
        good_partition = {0: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1}
        good_modularity = leiden._compute_modularity(good_partition)

        # Bad partition (random assignment)
        bad_partition = {0: 0, 1: 1, 2: 0, 3: 1, 4: 0, 5: 1}
        bad_modularity = leiden._compute_modularity(bad_partition)

        # Good partition should have higher modularity
        assert good_modularity > bad_modularity

    def test_disconnected_components(self):
        """Test handling of disconnected graph components."""
        # Two isolated components
        graph = {
            0: {1},
            1: {0},
            2: {3},
            3: {2},
        }

        leiden = LeidenClustering(graph)
        partition = leiden.detect_communities(min_community_size=1)

        # Should separate into 2 communities minimum
        communities = set(partition.values())
        assert len(communities) >= 2

    def test_star_topology(self):
        """Test star graph (one central hub)."""
        # Central node connected to all others
        graph = {
            0: {1, 2, 3, 4},
            1: {0},
            2: {0},
            3: {0},
            4: {0},
        }

        leiden = LeidenClustering(graph)
        partition = leiden.detect_communities()

        # Hub might be in own community or grouped with others
        # Just verify it produces a partition
        communities = set(partition.values())
        assert len(communities) >= 1

    def test_small_community_merging(self):
        """Test merging of small communities."""
        graph = {
            0: {1, 2},
            1: {0, 2},
            2: {0, 1},
            3: {},  # Isolated node
        }

        leiden = LeidenClustering(graph)
        partition = leiden.detect_communities(min_community_size=2)

        # Isolated node (community size 1) should be merged
        small_communities = defaultdict(int)
        for comm_id in partition.values():
            small_communities[comm_id] += 1

        # No community should be size 1
        assert min(small_communities.values()) >= 2


class TestCommunityDetection:
    """Test community detection on knowledge graph."""

    def test_detect_communities(self, db):
        """Test detecting communities in knowledge graph."""
        # Create test entities
        entities = [
            Entity(id=1, name="Authentication", entity_type=EntityType.CONCEPT, project_id=1),
            Entity(id=2, name="JWT", entity_type=EntityType.COMPONENT, project_id=1),
            Entity(id=3, name="OAuth2", entity_type=EntityType.CONCEPT, project_id=1),
            Entity(id=4, name="Database", entity_type=EntityType.COMPONENT, project_id=1),
            Entity(id=5, name="SQL", entity_type=EntityType.CONCEPT, project_id=1),
            Entity(id=6, name="Indexing", entity_type=EntityType.PATTERN, project_id=1),
        ]

        # Create relations
        relations = [
            Relation(id=1, from_entity_id=1, to_entity_id=2, relation_type=RelationType.IMPLEMENTS, project_id=1),
            Relation(id=2, from_entity_id=1, to_entity_id=3, relation_type=RelationType.RELATES_TO, project_id=1),
            Relation(id=3, from_entity_id=2, to_entity_id=3, relation_type=RelationType.RELATES_TO, project_id=1),
            Relation(id=4, from_entity_id=4, to_entity_id=5, relation_type=RelationType.IMPLEMENTS, project_id=1),
            Relation(id=5, from_entity_id=4, to_entity_id=6, relation_type=RelationType.RELATES_TO, project_id=1),
            Relation(id=6, from_entity_id=5, to_entity_id=6, relation_type=RelationType.RELATES_TO, project_id=1),
        ]

        analyzer = CommunityAnalyzer(db)
        communities = analyzer.analyze_with_leiden(entities, relations, project_id=1)

        # Should detect at least 2 communities (auth cluster vs database cluster)
        assert len(communities) >= 2

        # Get all entity IDs per community
        entity_communities = {comm.id: set(comm.entity_ids) for comm in communities.values()}

        # Auth entities should group together
        auth_entities = {1, 2, 3}
        db_entities = {4, 5, 6}

        # Find which communities contain which entities
        for comm_entities in entity_communities.values():
            if comm_entities & auth_entities:
                # This community has auth entities
                assert len(comm_entities & auth_entities) >= 2

    def test_community_metrics(self, db):
        """Test community density and connectivity metrics."""
        entities = [
            Entity(id=1, name="Node1", entity_type=EntityType.CONCEPT, project_id=1),
            Entity(id=2, name="Node2", entity_type=EntityType.CONCEPT, project_id=1),
            Entity(id=3, name="Node3", entity_type=EntityType.CONCEPT, project_id=1),
        ]

        # Fully connected triangle
        relations = [
            Relation(id=1, from_entity_id=1, to_entity_id=2, relation_type=RelationType.RELATES_TO, project_id=1),
            Relation(id=2, from_entity_id=2, to_entity_id=3, relation_type=RelationType.RELATES_TO, project_id=1),
            Relation(id=3, from_entity_id=1, to_entity_id=3, relation_type=RelationType.RELATES_TO, project_id=1),
        ]

        analyzer = CommunityAnalyzer(db)
        communities = analyzer.analyze_with_leiden(entities, relations, project_id=1)

        # Should have high density (fully connected)
        for community in communities.values():
            assert community.density > 0.5  # At least 50% connected


class TestCommunityHierarchy:
    """Test hierarchical organization of communities."""

    def test_build_hierarchy(self, db):
        """Test building community hierarchy."""
        entities = [
            Entity(id=i, name=f"Entity{i}", entity_type=EntityType.CONCEPT, project_id=1)
            for i in range(1, 7)
        ]

        relations = [
            Relation(id=i, from_entity_id=i, to_entity_id=i+1, relation_type=RelationType.RELATES_TO, project_id=1)
            for i in range(1, 6)
        ]

        analyzer = CommunityAnalyzer(db)
        flat_communities = analyzer.analyze_with_leiden(entities, relations, project_id=1)
        hierarchy = analyzer.build_hierarchy(flat_communities)

        assert hierarchy is not None
        assert len(hierarchy.root_communities) > 0

    def test_multi_level_query(self, db):
        """Test querying communities at different levels."""
        entities = [
            Entity(id=i, name=f"Entity{i}", entity_type=EntityType.CONCEPT, project_id=1)
            for i in range(1, 7)
        ]

        relations = [
            Relation(id=i, from_entity_id=i, to_entity_id=i+1, relation_type=RelationType.RELATES_TO, project_id=1)
            for i in range(1, 6)
        ]

        analyzer = CommunityAnalyzer(db)
        communities = analyzer.analyze_with_leiden(entities, relations, project_id=1)

        # Query at level 0 (granular)
        level_0_results = analyzer.multi_level_query("test query", communities, level=0)

        assert len(level_0_results) > 0
        assert all(c.level == 0 for c in level_0_results)


class TestCommunityIntegration:
    """Integration tests for GraphRAG communities."""

    def test_full_community_analysis_workflow(self, db):
        """Test complete community analysis workflow."""
        # Create knowledge graph
        entities = [
            Entity(id=1, name="UserAuth", entity_type=EntityType.COMPONENT, project_id=1),
            Entity(id=2, name="JWT", entity_type=EntityType.COMPONENT, project_id=1),
            Entity(id=3, name="Session", entity_type=EntityType.COMPONENT, project_id=1),
            Entity(id=4, name="Database", entity_type=EntityType.COMPONENT, project_id=1),
            Entity(id=5, name="Cache", entity_type=EntityType.COMPONENT, project_id=1),
        ]

        relations = [
            Relation(id=1, from_entity_id=1, to_entity_id=2, relation_type=RelationType.IMPLEMENTS, project_id=1),
            Relation(id=2, from_entity_id=1, to_entity_id=3, relation_type=RelationType.IMPLEMENTS, project_id=1),
            Relation(id=3, from_entity_id=4, to_entity_id=5, relation_type=RelationType.IMPLEMENTS, project_id=1),
        ]

        analyzer = CommunityAnalyzer(db)

        # Analyze with Leiden
        communities = analyzer.analyze_with_leiden(entities, relations, project_id=1)

        # Verify results
        assert len(communities) >= 1
        for community in communities.values():
            assert community.size > 0
            assert community.internal_edges >= 0
            assert 0 <= community.density <= 1
            assert len(community.entity_names) == community.size
            assert len(community.summary) > 0

    def test_large_graph_performance(self, db):
        """Test performance on larger graphs."""
        # Create larger graph
        num_nodes = 50
        entities = [
            Entity(id=i, name=f"Node{i}", entity_type=EntityType.CONCEPT, project_id=1)
            for i in range(1, num_nodes + 1)
        ]

        # Create sparse relations (avoid full graph)
        relations = []
        rel_id = 1
        for i in range(1, num_nodes):
            # Each node connects to next few nodes
            for j in range(i+1, min(i+4, num_nodes+1)):
                relations.append(
                    Relation(id=rel_id, from_entity_id=i, to_entity_id=j, relation_type=RelationType.RELATES_TO, project_id=1)
                )
                rel_id += 1

        analyzer = CommunityAnalyzer(db)

        # Should complete without timeout
        communities = analyzer.analyze_with_leiden(entities, relations, project_id=1)

        assert len(communities) >= 1
        total_nodes = sum(c.size for c in communities.values())
        assert total_nodes == num_nodes
