"""Test advanced graph analytics with direct model construction.

Bypasses database layer to focus on testing analytics algorithms directly.
"""

import pytest
from datetime import datetime

from athena.graph import (
    Entity,
    EntityType,
    Relation,
    RelationType,
    GraphAnalyzer,
)


@pytest.fixture
def sample_graph_entities():
    """Create sample entities directly."""
    return [
        Entity(id=1, name="Entity1", entity_type=EntityType.CONCEPT, created_at=datetime.now(), updated_at=datetime.now()),
        Entity(id=2, name="Entity2", entity_type=EntityType.CONCEPT, created_at=datetime.now(), updated_at=datetime.now()),
        Entity(id=3, name="Entity3", entity_type=EntityType.CONCEPT, created_at=datetime.now(), updated_at=datetime.now()),
        Entity(id=4, name="Entity4", entity_type=EntityType.COMPONENT, created_at=datetime.now(), updated_at=datetime.now()),
        Entity(id=5, name="Entity5", entity_type=EntityType.COMPONENT, created_at=datetime.now(), updated_at=datetime.now()),
        Entity(id=6, name="Entity6", entity_type=EntityType.COMPONENT, created_at=datetime.now(), updated_at=datetime.now()),
    ]


@pytest.fixture
def sample_graph_relations():
    """Create sample relations directly.

    Creates grid:
    ```
        E1 -- E2 -- E3
        |      |      |
        E4 -- E5 -- E6
    ```
    """
    return [
        # Top row
        Relation(from_entity_id=1, to_entity_id=2, relation_type=RelationType.RELATES_TO, strength=1.0, confidence=0.9, created_at=datetime.now()),
        Relation(from_entity_id=2, to_entity_id=3, relation_type=RelationType.RELATES_TO, strength=1.0, confidence=0.9, created_at=datetime.now()),
        # Middle column
        Relation(from_entity_id=1, to_entity_id=4, relation_type=RelationType.DEPENDS_ON, strength=0.8, confidence=0.85, created_at=datetime.now()),
        Relation(from_entity_id=2, to_entity_id=5, relation_type=RelationType.IMPLEMENTS, strength=0.9, confidence=0.9, created_at=datetime.now()),
        Relation(from_entity_id=3, to_entity_id=6, relation_type=RelationType.CONTAINS, strength=1.0, confidence=0.95, created_at=datetime.now()),
        # Bottom row
        Relation(from_entity_id=4, to_entity_id=5, relation_type=RelationType.RELATES_TO, strength=0.7, confidence=0.8, created_at=datetime.now()),
        Relation(from_entity_id=5, to_entity_id=6, relation_type=RelationType.RELATES_TO, strength=1.0, confidence=0.9, created_at=datetime.now()),
    ]


class TestBetweennessCentrality:
    """Test betweenness centrality calculations."""

    def test_betweenness_computation(self, sample_graph_entities, sample_graph_relations):
        """Test that betweenness centrality is computed."""
        analyzer = GraphAnalyzer(sample_graph_entities, sample_graph_relations)
        betweenness = analyzer.compute_betweenness_centrality()

        # Should have scores for all entities
        assert len(betweenness) == 6
        assert all(0 <= v <= 1 for v in betweenness.values())

        # Center nodes (2 and 5) should have high betweenness
        assert betweenness[2] > 0
        assert betweenness[5] > 0

    def test_betweenness_normalization(self, sample_graph_entities, sample_graph_relations):
        """Test betweenness normalization."""
        analyzer = GraphAnalyzer(sample_graph_entities, sample_graph_relations)

        normalized = analyzer.compute_betweenness_centrality(normalize=True)
        unnormalized = analyzer.compute_betweenness_centrality(normalize=False)

        # Normalized should be in [0, 1]
        assert all(0 <= v <= 1 for v in normalized.values())
        # Unnormalized may exceed 1
        assert any(v >= normalized[k] for k, v in unnormalized.items())


class TestClosenessCentrality:
    """Test closeness centrality calculations."""

    def test_closeness_computation(self, sample_graph_entities, sample_graph_relations):
        """Test closeness centrality computation."""
        analyzer = GraphAnalyzer(sample_graph_entities, sample_graph_relations)
        closeness = analyzer.compute_closeness_centrality()

        # Should have scores for all entities
        assert len(closeness) == 6
        assert all(0 <= v <= 1 for v in closeness.values())

    def test_closeness_isolation(self):
        """Test closeness for isolated node."""
        entities = [
            Entity(id=1, name="A", entity_type=EntityType.CONCEPT, created_at=datetime.now(), updated_at=datetime.now()),
            Entity(id=2, name="B", entity_type=EntityType.CONCEPT, created_at=datetime.now(), updated_at=datetime.now()),
            Entity(id=3, name="C", entity_type=EntityType.CONCEPT, created_at=datetime.now(), updated_at=datetime.now()),
        ]

        relations = [
            Relation(from_entity_id=1, to_entity_id=2, relation_type=RelationType.RELATES_TO, created_at=datetime.now()),
        ]

        analyzer = GraphAnalyzer(entities, relations)
        closeness = analyzer.compute_closeness_centrality()

        # Isolated node should have 0 closeness
        assert closeness[3] == 0.0


class TestClusteringCoefficient:
    """Test clustering coefficient calculations."""

    def test_clustering_coefficient(self, sample_graph_entities, sample_graph_relations):
        """Test local clustering coefficient."""
        analyzer = GraphAnalyzer(sample_graph_entities, sample_graph_relations)
        clustering = analyzer.compute_clustering_coefficient()

        # Should have coefficients for all entities
        assert len(clustering) == 6
        assert all(0 <= v <= 1 for v in clustering.values())

        # Nodes with degree < 2 should have coefficient 0
        for node_id in analyzer.entities.keys():
            if len(analyzer.graph[node_id]) < 2:
                assert clustering[node_id] == 0.0


class TestDegreeCentrality:
    """Test degree centrality."""

    def test_degree_centrality(self, sample_graph_entities, sample_graph_relations):
        """Test degree centrality calculation."""
        analyzer = GraphAnalyzer(sample_graph_entities, sample_graph_relations)
        degree = analyzer.compute_degree_centrality()

        # Should have scores for all entities
        assert len(degree) == 6
        assert all(0 <= v <= 1 for v in degree.values())

        # Degree values are normalized by (n-1)
        for node_id in analyzer.entities.keys():
            actual_degree = len(analyzer.graph[node_id])
            max_degree = len(analyzer.entities) - 1
            expected = actual_degree / max_degree
            assert abs(degree[node_id] - expected) < 1e-10


class TestClustering:
    """Test community detection."""

    def test_cluster_detection_modularity(self, sample_graph_entities, sample_graph_relations):
        """Test cluster detection using modularity."""
        analyzer = GraphAnalyzer(sample_graph_entities, sample_graph_relations)
        clusters = analyzer.detect_clusters(method="modularity")

        # Should detect clusters
        assert len(clusters) > 0
        assert all(c.size > 0 for c in clusters)

        # All entities should be in a cluster
        all_entities_in_clusters = set()
        for cluster in clusters:
            all_entities_in_clusters.update(cluster.entity_ids)

        assert len(all_entities_in_clusters) == 6

    def test_cluster_detection_density(self, sample_graph_entities, sample_graph_relations):
        """Test cluster detection using density method."""
        analyzer = GraphAnalyzer(sample_graph_entities, sample_graph_relations)
        clusters = analyzer.detect_clusters(method="density")

        # Should detect connected components
        assert len(clusters) > 0

        # All entities should be in a cluster
        all_entities_in_clusters = set()
        for cluster in clusters:
            all_entities_in_clusters.update(cluster.entity_ids)

        assert len(all_entities_in_clusters) == 6

    def test_cluster_density_values(self, sample_graph_entities, sample_graph_relations):
        """Test cluster density calculation."""
        analyzer = GraphAnalyzer(sample_graph_entities, sample_graph_relations)
        clusters = analyzer.detect_clusters()

        # All densities should be in [0, 1]
        assert all(0 <= c.density <= 1 for c in clusters)

    def test_cluster_cohesion(self, sample_graph_entities, sample_graph_relations):
        """Test cluster cohesion (internal vs external edges)."""
        analyzer = GraphAnalyzer(sample_graph_entities, sample_graph_relations)
        clusters = analyzer.detect_clusters()

        # Cohesion should be in [0, 1]
        assert all(0 <= c.cohesion <= 1 for c in clusters)


class TestGraphMetrics:
    """Test graph-level metrics."""

    def test_shortest_path(self, sample_graph_entities, sample_graph_relations):
        """Test shortest path computation."""
        analyzer = GraphAnalyzer(sample_graph_entities, sample_graph_relations)

        # Path from E1 to E6
        path = analyzer.compute_shortest_path(1, 6)
        assert path is not None
        assert len(path) > 1
        assert path[0] == 1
        assert path[-1] == 6

    def test_shortest_path_same_node(self, sample_graph_entities, sample_graph_relations):
        """Test shortest path from node to itself."""
        analyzer = GraphAnalyzer(sample_graph_entities, sample_graph_relations)

        path = analyzer.compute_shortest_path(1, 1)
        assert path == [1]

    def test_shortest_path_no_path(self):
        """Test shortest path when nodes are disconnected."""
        entities = [
            Entity(id=1, name="A", entity_type=EntityType.CONCEPT, created_at=datetime.now(), updated_at=datetime.now()),
            Entity(id=2, name="B", entity_type=EntityType.CONCEPT, created_at=datetime.now(), updated_at=datetime.now()),
            Entity(id=3, name="C", entity_type=EntityType.CONCEPT, created_at=datetime.now(), updated_at=datetime.now()),
        ]

        relations = [
            Relation(from_entity_id=1, to_entity_id=2, relation_type=RelationType.RELATES_TO, created_at=datetime.now()),
        ]

        analyzer = GraphAnalyzer(entities, relations)

        # No path from C to A
        path = analyzer.compute_shortest_path(3, 1)
        assert path is None

    def test_isolated_entities(self):
        """Test detection of isolated entities."""
        entities = [
            Entity(id=1, name="A", entity_type=EntityType.CONCEPT, created_at=datetime.now(), updated_at=datetime.now()),
            Entity(id=2, name="B", entity_type=EntityType.CONCEPT, created_at=datetime.now(), updated_at=datetime.now()),
            Entity(id=3, name="C", entity_type=EntityType.CONCEPT, created_at=datetime.now(), updated_at=datetime.now()),
        ]

        relations = [
            Relation(from_entity_id=1, to_entity_id=2, relation_type=RelationType.RELATES_TO, created_at=datetime.now()),
        ]

        analyzer = GraphAnalyzer(entities, relations)
        isolated = analyzer.find_isolated_entities()

        assert 3 in isolated
        assert 1 not in isolated
        assert 2 not in isolated

    def test_graph_diameter(self, sample_graph_entities, sample_graph_relations):
        """Test graph diameter calculation."""
        analyzer = GraphAnalyzer(sample_graph_entities, sample_graph_relations)

        diameter = analyzer.compute_graph_diameter()
        assert diameter > 0  # Should have finite diameter


class TestComprehensiveAnalytics:
    """Test comprehensive analytics computation."""

    def test_compute_all_analytics(self, sample_graph_entities, sample_graph_relations):
        """Test comprehensive analytics."""
        analyzer = GraphAnalyzer(sample_graph_entities, sample_graph_relations)
        analytics = analyzer.compute_all_analytics(top_k=3)

        # Check all fields present
        assert analytics.total_entities == 6
        assert analytics.total_edges == 7
        assert 0 <= analytics.density <= 1
        assert analytics.average_degree > 0
        assert 0 <= analytics.clustering_coefficient <= 1
        assert analytics.diameter >= 0
        assert len(analytics.top_centralities) <= 3
        assert len(analytics.clusters) > 0

        # Check centrality scores
        for score in analytics.top_centralities:
            assert 0 <= score.betweenness <= 1
            assert 0 <= score.closeness <= 1
            assert 0 <= score.importance <= 1
            assert score.degree >= 0
            assert len(score.entity_name) > 0

    def test_analytics_contains_hub_nodes(self, sample_graph_entities, sample_graph_relations):
        """Test that analytics identifies hub nodes."""
        analyzer = GraphAnalyzer(sample_graph_entities, sample_graph_relations)
        analytics = analyzer.compute_all_analytics(top_k=6)

        # Node 2 and 5 are hubs (degree 3 each)
        node2_found = any(s.entity_id == 2 for s in analytics.top_centralities)
        node5_found = any(s.entity_id == 5 for s in analytics.top_centralities)

        # At least one hub should be in top centralities
        assert node2_found or node5_found

    def test_analytics_serialization(self, sample_graph_entities, sample_graph_relations):
        """Test that analytics can be serialized."""
        analyzer = GraphAnalyzer(sample_graph_entities, sample_graph_relations)
        analytics = analyzer.compute_all_analytics()

        # Convert to dict (simulating serialization)
        data = {
            "total_entities": analytics.total_entities,
            "total_edges": analytics.total_edges,
            "density": analytics.density,
            "average_degree": analytics.average_degree,
            "clustering_coefficient": analytics.clustering_coefficient,
            "diameter": analytics.diameter,
            "top_centralities": [
                {
                    "entity_id": s.entity_id,
                    "entity_name": s.entity_name,
                    "betweenness": s.betweenness,
                    "closeness": s.closeness,
                    "degree": s.degree,
                    "importance": s.importance,
                }
                for s in analytics.top_centralities
            ],
            "clusters": [
                {
                    "id": c.id,
                    "size": c.size,
                    "density": c.density,
                    "cohesion": c.cohesion,
                }
                for c in analytics.clusters
            ],
            "isolated_entities": analytics.isolated_entities,
        }

        # Should be serializable to dict
        assert data["total_entities"] == 6
        assert isinstance(data["top_centralities"], list)
        assert isinstance(data["clusters"], list)


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_graph(self):
        """Test analytics on empty graph."""
        analyzer = GraphAnalyzer([], [])
        analytics = analyzer.compute_all_analytics()

        assert analytics.total_entities == 0
        assert analytics.total_edges == 0
        assert analytics.density == 0.0
        assert analytics.diameter == 0

    def test_single_node(self):
        """Test analytics on single-node graph."""
        entities = [
            Entity(id=1, name="A", entity_type=EntityType.CONCEPT, created_at=datetime.now(), updated_at=datetime.now()),
        ]

        analyzer = GraphAnalyzer(entities, [])
        analytics = analyzer.compute_all_analytics()

        assert analytics.total_entities == 1
        assert analytics.total_edges == 0
        assert analytics.diameter == 0
        assert len(analytics.isolated_entities) == 1

    def test_two_disconnected_components(self):
        """Test analytics on disconnected graph."""
        entities = [
            Entity(id=1, name="A", entity_type=EntityType.CONCEPT, created_at=datetime.now(), updated_at=datetime.now()),
            Entity(id=2, name="B", entity_type=EntityType.CONCEPT, created_at=datetime.now(), updated_at=datetime.now()),
            Entity(id=3, name="C", entity_type=EntityType.CONCEPT, created_at=datetime.now(), updated_at=datetime.now()),
            Entity(id=4, name="D", entity_type=EntityType.CONCEPT, created_at=datetime.now(), updated_at=datetime.now()),
        ]

        relations = [
            Relation(from_entity_id=1, to_entity_id=2, relation_type=RelationType.RELATES_TO, created_at=datetime.now()),
            Relation(from_entity_id=3, to_entity_id=4, relation_type=RelationType.RELATES_TO, created_at=datetime.now()),
        ]

        analyzer = GraphAnalyzer(entities, relations)
        analytics = analyzer.compute_all_analytics()

        # Should detect multiple clusters
        assert len(analytics.clusters) > 1

    def test_fully_connected_graph(self):
        """Test analytics on fully connected graph (clique)."""
        # Create 3 nodes, fully connected
        entities = [
            Entity(id=1, name="A", entity_type=EntityType.CONCEPT, created_at=datetime.now(), updated_at=datetime.now()),
            Entity(id=2, name="B", entity_type=EntityType.CONCEPT, created_at=datetime.now(), updated_at=datetime.now()),
            Entity(id=3, name="C", entity_type=EntityType.CONCEPT, created_at=datetime.now(), updated_at=datetime.now()),
        ]

        relations = [
            Relation(from_entity_id=1, to_entity_id=2, relation_type=RelationType.RELATES_TO, created_at=datetime.now()),
            Relation(from_entity_id=1, to_entity_id=3, relation_type=RelationType.RELATES_TO, created_at=datetime.now()),
            Relation(from_entity_id=2, to_entity_id=3, relation_type=RelationType.RELATES_TO, created_at=datetime.now()),
        ]

        analyzer = GraphAnalyzer(entities, relations)
        analytics = analyzer.compute_all_analytics()

        # Fully connected should have density 1.0
        assert analytics.density == 1.0
        # Diameter should be 1
        assert analytics.diameter == 1
        # All clustering coefficients should be 1
        clustering = analyzer.compute_clustering_coefficient()
        for node in analyzer.entities.keys():
            if len(analyzer.graph[node]) >= 2:
                assert clustering[node] == 1.0

    def test_linear_graph(self):
        """Test analytics on linear graph (chain)."""
        entities = [
            Entity(id=i, name=f"Node{i}", entity_type=EntityType.CONCEPT, created_at=datetime.now(), updated_at=datetime.now())
            for i in range(1, 6)
        ]

        relations = [
            Relation(from_entity_id=i, to_entity_id=i+1, relation_type=RelationType.RELATES_TO, created_at=datetime.now())
            for i in range(1, 5)
        ]

        analyzer = GraphAnalyzer(entities, relations)
        analytics = analyzer.compute_all_analytics()

        # Diameter should be length - 1
        assert analytics.diameter == 4
        # Density: (2 * 4 edges) / (5 * 4 possible) = 8 / 20 = 0.4
        assert analytics.density == 0.4
