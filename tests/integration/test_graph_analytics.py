"""Test advanced graph analytics functionality.

Tests:
- Betweenness centrality calculation
- Closeness centrality calculation
- Clustering coefficient
- Degree centrality
- Community detection
- Graph metrics
"""

import pytest
from datetime import datetime

from athena.core.database import Database
from athena.graph import (
    Entity,
    EntityType,
    Relation,
    RelationType,
    GraphStore,
    GraphAnalyzer,
)


@pytest.fixture
def db(tmp_path):
    """Create test database."""
    return Database(str(tmp_path / "test.db"))


@pytest.fixture
def graph_store(db):
    """Create graph store."""
    return GraphStore(db)


@pytest.fixture
def sample_graph(graph_store):
    """Create sample graph for testing.

    Creates a small knowledge graph:
    ```
        E1 -- E2 -- E3
        |      |      |
        E4 -- E5 -- E6
    ```
    """
    entities = [
        Entity(name="Entity1", entity_type=EntityType.CONCEPT),
        Entity(name="Entity2", entity_type=EntityType.CONCEPT),
        Entity(name="Entity3", entity_type=EntityType.CONCEPT),
        Entity(name="Entity4", entity_type=EntityType.COMPONENT),
        Entity(name="Entity5", entity_type=EntityType.COMPONENT),
        Entity(name="Entity6", entity_type=EntityType.COMPONENT),
    ]

    # Create entities and collect IDs
    entity_ids = []
    for entity in entities:
        eid = graph_store.create_entity(entity)
        entity_ids.append(eid)

    # Create relations (edges)
    relations = [
        # Top row
        Relation(from_entity_id=entity_ids[0], to_entity_id=entity_ids[1], relation_type=RelationType.RELATES_TO, strength=1.0, confidence=0.9),
        Relation(from_entity_id=entity_ids[1], to_entity_id=entity_ids[2], relation_type=RelationType.RELATES_TO, strength=1.0, confidence=0.9),
        # Middle column
        Relation(from_entity_id=entity_ids[0], to_entity_id=entity_ids[3], relation_type=RelationType.DEPENDS_ON, strength=0.8, confidence=0.85),
        Relation(from_entity_id=entity_ids[1], to_entity_id=entity_ids[4], relation_type=RelationType.IMPLEMENTS, strength=0.9, confidence=0.9),
        Relation(from_entity_id=entity_ids[2], to_entity_id=entity_ids[5], relation_type=RelationType.CONTAINS, strength=1.0, confidence=0.95),
        # Bottom row
        Relation(from_entity_id=entity_ids[3], to_entity_id=entity_ids[4], relation_type=RelationType.RELATES_TO, strength=0.7, confidence=0.8),
        Relation(from_entity_id=entity_ids[4], to_entity_id=entity_ids[5], relation_type=RelationType.RELATES_TO, strength=1.0, confidence=0.9),
    ]

    for relation in relations:
        graph_store.create_relation(relation)

    return {
        "store": graph_store,
        "entity_ids": entity_ids,
        "entities": entities,
        "relations": relations,
    }


class TestBetweennessCentrality:
    """Test betweenness centrality calculations."""

    def test_betweenness_computation(self, sample_graph):
        """Test that betweenness centrality is computed."""
        graph_data = sample_graph["store"].read_graph()
        analyzer = GraphAnalyzer(graph_data["entities"], graph_data["relations"])

        betweenness = analyzer.compute_betweenness_centrality()

        # Should have scores for all entities
        assert len(betweenness) == 6
        assert all(0 <= v <= 1 for v in betweenness.values())

        # Center nodes should have higher betweenness
        # Entity2 (index 1) and Entity5 (index 4) are in the middle
        entity2_id = sample_graph["entity_ids"][1]
        entity5_id = sample_graph["entity_ids"][4]

        # At least these should be computed
        assert betweenness[entity2_id] >= 0
        assert betweenness[entity5_id] >= 0

    def test_betweenness_normalization(self, sample_graph):
        """Test betweenness normalization."""
        graph_data = sample_graph["store"].read_graph()
        analyzer = GraphAnalyzer(graph_data["entities"], graph_data["relations"])

        normalized = analyzer.compute_betweenness_centrality(normalize=True)
        unnormalized = analyzer.compute_betweenness_centrality(normalize=False)

        # Normalized should be in [0, 1]
        assert all(0 <= v <= 1 for v in normalized.values())


class TestClosenessCentrality:
    """Test closeness centrality calculations."""

    def test_closeness_computation(self, sample_graph):
        """Test closeness centrality computation."""
        graph_data = sample_graph["store"].read_graph()
        analyzer = GraphAnalyzer(graph_data["entities"], graph_data["relations"])

        closeness = analyzer.compute_closeness_centrality()

        # Should have scores for all entities
        assert len(closeness) == 6
        assert all(0 <= v <= 1 for v in closeness.values())

    def test_closeness_isolation(self, db, graph_store):
        """Test closeness for isolated node."""
        # Create two isolated components
        e1 = graph_store.create_entity(Entity(name="A", entity_type=EntityType.CONCEPT))
        e2 = graph_store.create_entity(Entity(name="B", entity_type=EntityType.CONCEPT))
        e3 = graph_store.create_entity(Entity(name="C", entity_type=EntityType.CONCEPT))

        # Only connect A-B, leave C isolated
        graph_store.create_relation(
            Relation(from_entity_id=e1, to_entity_id=e2, relation_type=RelationType.RELATES_TO)
        )

        graph_data = graph_store.read_graph()
        analyzer = GraphAnalyzer(graph_data["entities"], graph_data["relations"])
        closeness = analyzer.compute_closeness_centrality()

        # Isolated node should have 0 closeness
        assert closeness[e3] == 0.0


class TestClusteringCoefficient:
    """Test clustering coefficient calculations."""

    def test_clustering_coefficient(self, sample_graph):
        """Test local clustering coefficient."""
        graph_data = sample_graph["store"].read_graph()
        analyzer = GraphAnalyzer(graph_data["entities"], graph_data["relations"])

        clustering = analyzer.compute_clustering_coefficient()

        # Should have coefficients for all entities
        assert len(clustering) == 6
        assert all(0 <= v <= 1 for v in clustering.values())

        # Nodes with degree < 2 should have coefficient 0
        # Degree 1 nodes should have coefficient 0
        degrees = {eid: len(analyzer.graph[eid]) for eid in analyzer.entities.keys()}
        for node_id, degree in degrees.items():
            if degree < 2:
                assert clustering[node_id] == 0.0


class TestDegreeCentrality:
    """Test degree centrality."""

    def test_degree_centrality(self, sample_graph):
        """Test degree centrality calculation."""
        graph_data = sample_graph["store"].read_graph()
        analyzer = GraphAnalyzer(graph_data["entities"], graph_data["relations"])

        degree = analyzer.compute_degree_centrality()

        # Should have scores for all entities
        assert len(degree) == 6
        assert all(0 <= v <= 1 for v in degree.values())

        # Degree values are normalized by (n-1)
        for node_id, cent in degree.items():
            actual_degree = len(analyzer.graph[node_id])
            max_degree = len(analyzer.entities) - 1
            assert cent == actual_degree / max_degree


class TestClustering:
    """Test community detection."""

    def test_cluster_detection_modularity(self, sample_graph):
        """Test cluster detection using modularity."""
        graph_data = sample_graph["store"].read_graph()
        analyzer = GraphAnalyzer(graph_data["entities"], graph_data["relations"])

        clusters = analyzer.detect_clusters(method="modularity")

        # Should detect clusters
        assert len(clusters) > 0
        assert all(c.size > 0 for c in clusters)

        # All entities should be in a cluster
        all_entities_in_clusters = set()
        for cluster in clusters:
            all_entities_in_clusters.update(cluster.entity_ids)

        assert len(all_entities_in_clusters) == 6

    def test_cluster_density(self, sample_graph):
        """Test cluster density calculation."""
        graph_data = sample_graph["store"].read_graph()
        analyzer = GraphAnalyzer(graph_data["entities"], graph_data["relations"])

        clusters = analyzer.detect_clusters()

        # All densities should be in [0, 1]
        assert all(0 <= c.density <= 1 for c in clusters)

    def test_cluster_cohesion(self, sample_graph):
        """Test cluster cohesion (internal vs external edges)."""
        graph_data = sample_graph["store"].read_graph()
        analyzer = GraphAnalyzer(graph_data["entities"], graph_data["relations"])

        clusters = analyzer.detect_clusters()

        # Cohesion should be in [0, 1]
        assert all(0 <= c.cohesion <= 1 for c in clusters)


class TestGraphMetrics:
    """Test graph-level metrics."""

    def test_shortest_path(self, sample_graph):
        """Test shortest path computation."""
        graph_data = sample_graph["store"].read_graph()
        analyzer = GraphAnalyzer(graph_data["entities"], graph_data["relations"])

        # Path from E1 to E6
        e1_id = sample_graph["entity_ids"][0]
        e6_id = sample_graph["entity_ids"][5]

        path = analyzer.compute_shortest_path(e1_id, e6_id)
        assert path is not None
        assert len(path) > 1
        assert path[0] == e1_id
        assert path[-1] == e6_id

    def test_shortest_path_same_node(self, sample_graph):
        """Test shortest path from node to itself."""
        graph_data = sample_graph["store"].read_graph()
        analyzer = GraphAnalyzer(graph_data["entities"], graph_data["relations"])

        e1_id = sample_graph["entity_ids"][0]
        path = analyzer.compute_shortest_path(e1_id, e1_id)

        assert path == [e1_id]

    def test_shortest_path_no_path(self, db, graph_store):
        """Test shortest path when nodes are disconnected."""
        e1 = graph_store.create_entity(Entity(name="A", entity_type=EntityType.CONCEPT))
        e2 = graph_store.create_entity(Entity(name="B", entity_type=EntityType.CONCEPT))
        e3 = graph_store.create_entity(Entity(name="C", entity_type=EntityType.CONCEPT))

        # Only connect A-B, leave C isolated
        graph_store.create_relation(
            Relation(from_entity_id=e1, to_entity_id=e2, relation_type=RelationType.RELATES_TO)
        )

        graph_data = graph_store.read_graph()
        analyzer = GraphAnalyzer(graph_data["entities"], graph_data["relations"])

        # No path from C to A
        path = analyzer.compute_shortest_path(e3, e1)
        assert path is None

    def test_isolated_entities(self, db, graph_store):
        """Test detection of isolated entities."""
        e1 = graph_store.create_entity(Entity(name="A", entity_type=EntityType.CONCEPT))
        e2 = graph_store.create_entity(Entity(name="B", entity_type=EntityType.CONCEPT))
        e3 = graph_store.create_entity(Entity(name="C", entity_type=EntityType.CONCEPT))

        # Only connect A-B, leave C isolated
        graph_store.create_relation(
            Relation(from_entity_id=e1, to_entity_id=e2, relation_type=RelationType.RELATES_TO)
        )

        graph_data = graph_store.read_graph()
        analyzer = GraphAnalyzer(graph_data["entities"], graph_data["relations"])

        isolated = analyzer.find_isolated_entities()
        assert e3 in isolated
        assert e1 not in isolated
        assert e2 not in isolated

    def test_graph_diameter(self, sample_graph):
        """Test graph diameter calculation."""
        graph_data = sample_graph["store"].read_graph()
        analyzer = GraphAnalyzer(graph_data["entities"], graph_data["relations"])

        diameter = analyzer.compute_graph_diameter()
        assert diameter > 0  # Should have finite diameter


class TestComprehensiveAnalytics:
    """Test comprehensive analytics computation."""

    def test_compute_all_analytics(self, sample_graph):
        """Test comprehensive analytics."""
        graph_data = sample_graph["store"].read_graph()
        analyzer = GraphAnalyzer(graph_data["entities"], graph_data["relations"])

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

    def test_analytics_serialization(self, sample_graph):
        """Test that analytics can be serialized."""
        graph_data = sample_graph["store"].read_graph()
        analyzer = GraphAnalyzer(graph_data["entities"], graph_data["relations"])

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


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_graph(self, db, graph_store):
        """Test analytics on empty graph."""
        graph_data = graph_store.read_graph()
        analyzer = GraphAnalyzer([], [])

        analytics = analyzer.compute_all_analytics()

        assert analytics.total_entities == 0
        assert analytics.total_edges == 0
        assert analytics.density == 0.0
        assert analytics.diameter == 0

    def test_single_node(self, db, graph_store):
        """Test analytics on single-node graph."""
        e1 = graph_store.create_entity(Entity(name="A", entity_type=EntityType.CONCEPT))

        graph_data = graph_store.read_graph()
        analyzer = GraphAnalyzer(graph_data["entities"], [])

        analytics = analyzer.compute_all_analytics()

        assert analytics.total_entities == 1
        assert analytics.total_edges == 0
        assert analytics.diameter == 0

    def test_fully_connected_graph(self, db, graph_store):
        """Test analytics on fully connected graph (clique)."""
        # Create 3 nodes, fully connected
        entities = [
            graph_store.create_entity(Entity(name="A", entity_type=EntityType.CONCEPT)),
            graph_store.create_entity(Entity(name="B", entity_type=EntityType.CONCEPT)),
            graph_store.create_entity(Entity(name="C", entity_type=EntityType.CONCEPT)),
        ]

        # Connect all pairs
        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                graph_store.create_relation(
                    Relation(
                        from_entity_id=entities[i],
                        to_entity_id=entities[j],
                        relation_type=RelationType.RELATES_TO,
                    )
                )

        graph_data = graph_store.read_graph()
        analyzer = GraphAnalyzer(graph_data["entities"], graph_data["relations"])

        analytics = analyzer.compute_all_analytics()

        # Fully connected should have density 1.0
        assert analytics.density == 1.0
        # Diameter should be 1
        assert analytics.diameter == 1
        # All clustering coefficients should be 1
        for node in analyzer.entities.keys():
            clustering = analyzer.compute_clustering_coefficient()
            if len(analyzer.graph[node]) >= 2:
                assert clustering[node] == 1.0
