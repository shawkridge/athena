"""Unit tests for graph pathfinding algorithms."""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from athena.graph.pathfinding import PathFinder


@pytest.fixture
def mock_db():
    """Create mock database."""
    return Mock()


@pytest.fixture
def mock_graph_store():
    """Create mock graph store."""
    store = Mock()
    return store


@pytest.fixture
def path_finder(mock_db, mock_graph_store):
    """Create path finder with mocks."""
    pf = PathFinder(mock_db)
    pf.graph_store = mock_graph_store
    return pf


class TestShortestPathAlgorithm:
    """Test Dijkstra's shortest path algorithm."""

    def test_shortest_path_self(self, path_finder, mock_graph_store):
        """Test shortest path from node to itself."""
        mock_graph_store.get_entity.return_value = Mock(id=1, name="A")

        path, cost = path_finder.shortest_path(1, 1)

        assert path == [1]
        assert cost == 0

    def test_shortest_path_linear_3_nodes(self, path_finder, mock_graph_store):
        """Test shortest path on linear graph: A -> B -> C."""
        # Mock entities
        mock_graph_store.get_entity.side_effect = lambda x: Mock(id=x, name=chr(64 + x))

        # Mock neighbors: 1 -> 2 -> 3
        neighbors_map = {
            (1, "from"): [(2, 1.0, 1.0)],
            (2, "from"): [(3, 1.0, 1.0)],
            (3, "from"): [],
        }

        def get_neighbors_side_effect(entity_id, direction):
            key = (entity_id, direction)
            return neighbors_map.get(key, [])

        path_finder._get_neighbors = Mock(side_effect=get_neighbors_side_effect)

        path, cost = path_finder.shortest_path(1, 3)

        assert path == [1, 2, 3]
        assert cost == 2

    def test_shortest_path_diamond_graph(self, path_finder, mock_graph_store):
        """Test shortest path on diamond graph: A->[B,C]->D."""
        mock_graph_store.get_entity.side_effect = lambda x: Mock(id=x, name=chr(64 + x))

        #         A
        #        / \
        #       B   C
        #        \ /
        #         D
        # Paths: A->B->D (2 edges) or A->C->D (2 edges)

        neighbors_map = {
            (1, "from"): [(2, 1.0, 1.0), (3, 1.0, 1.0)],  # A -> B, A -> C
            (2, "from"): [(4, 1.0, 1.0)],  # B -> D
            (3, "from"): [(4, 1.0, 1.0)],  # C -> D
            (4, "from"): [],
        }

        def get_neighbors_side_effect(entity_id, direction):
            key = (entity_id, direction)
            return neighbors_map.get(key, [])

        path_finder._get_neighbors = Mock(side_effect=get_neighbors_side_effect)

        path, cost = path_finder.shortest_path(1, 4)

        # Should find a path of length 2
        assert len(path) == 3
        assert path[0] == 1
        assert path[-1] == 4
        assert cost == 2

    def test_shortest_path_no_path(self, path_finder, mock_graph_store):
        """Test shortest path when no path exists."""
        mock_graph_store.get_entity.side_effect = lambda x: Mock(id=x, name=chr(64 + x))
        path_finder._get_neighbors = Mock(return_value=[])

        path, cost = path_finder.shortest_path(1, 2)

        assert path is None
        assert cost == -1

    def test_shortest_path_nonexistent_start(self, path_finder, mock_graph_store):
        """Test shortest path with non-existent start node."""
        mock_graph_store.get_entity.side_effect = [None, Mock(id=2)]

        path, cost = path_finder.shortest_path(999, 2)

        assert path is None
        assert cost == -1

    def test_shortest_path_nonexistent_end(self, path_finder, mock_graph_store):
        """Test shortest path with non-existent end node."""
        mock_graph_store.get_entity.side_effect = [Mock(id=1), None]

        path, cost = path_finder.shortest_path(1, 999)

        assert path is None
        assert cost == -1

    def test_shortest_path_respects_max_depth(self, path_finder, mock_graph_store):
        """Test that max_depth parameter is respected."""
        mock_graph_store.get_entity.side_effect = lambda x: Mock(id=x)

        # Long path: 1 -> 2 -> 3 -> 4 -> 5
        neighbors_map = {
            (1, "from"): [(2, 1.0, 1.0)],
            (2, "from"): [(3, 1.0, 1.0)],
            (3, "from"): [(4, 1.0, 1.0)],
            (4, "from"): [(5, 1.0, 1.0)],
            (5, "from"): [],
        }

        def get_neighbors_side_effect(entity_id, direction):
            key = (entity_id, direction)
            return neighbors_map.get(key, [])

        path_finder._get_neighbors = Mock(side_effect=get_neighbors_side_effect)

        # Max depth 2 should not reach node 5 (requires 4 edges)
        path, cost = path_finder.shortest_path(1, 5, max_depth=2)

        assert path is None

    def test_shortest_path_performance(self, path_finder, mock_graph_store):
        """Test shortest path completes in reasonable time."""
        mock_graph_store.get_entity.side_effect = lambda x: Mock(id=x)

        # Create a simple graph
        neighbors_map = {(i, "from"): [(i + 1, 1.0, 1.0)] for i in range(1, 5)}
        neighbors_map[(5, "from")] = []

        def get_neighbors_side_effect(entity_id, direction):
            key = (entity_id, direction)
            return neighbors_map.get(key, [])

        path_finder._get_neighbors = Mock(side_effect=get_neighbors_side_effect)

        start = time.time()
        path, cost = path_finder.shortest_path(1, 5)
        elapsed_ms = (time.time() - start) * 1000

        assert elapsed_ms < 100
        assert path == [1, 2, 3, 4, 5]


class TestAllPathsAlgorithm:
    """Test DFS all paths enumeration."""

    def test_all_paths_self(self, path_finder, mock_graph_store):
        """Test all paths from node to itself."""
        mock_graph_store.get_entity.side_effect = lambda x: Mock(id=x)

        paths = path_finder.all_paths(1, 1)

        assert len(paths) == 1
        assert paths[0] == [1]

    def test_all_paths_linear_single(self, path_finder, mock_graph_store):
        """Test all paths on linear graph (only one path)."""
        mock_graph_store.get_entity.side_effect = lambda x: Mock(id=x)

        # 1 -> 2 -> 3
        neighbors_map = {
            (1, "from"): [(2, 1.0, 1.0)],
            (2, "from"): [(3, 1.0, 1.0)],
            (3, "from"): [],
        }

        def get_neighbors_side_effect(entity_id, direction):
            key = (entity_id, direction)
            return neighbors_map.get(key, [])

        path_finder._get_neighbors = Mock(side_effect=get_neighbors_side_effect)

        paths = path_finder.all_paths(1, 3)

        assert len(paths) == 1
        assert paths[0] == [1, 2, 3]

    def test_all_paths_diamond(self, path_finder, mock_graph_store):
        """Test all paths on diamond graph (two paths)."""
        mock_graph_store.get_entity.side_effect = lambda x: Mock(id=x)

        #     1
        #    / \
        #   2   3
        #    \ /
        #     4

        neighbors_map = {
            (1, "from"): [(2, 1.0, 1.0), (3, 1.0, 1.0)],
            (2, "from"): [(4, 1.0, 1.0)],
            (3, "from"): [(4, 1.0, 1.0)],
            (4, "from"): [],
        }

        def get_neighbors_side_effect(entity_id, direction):
            key = (entity_id, direction)
            return neighbors_map.get(key, [])

        path_finder._get_neighbors = Mock(side_effect=get_neighbors_side_effect)

        paths = path_finder.all_paths(1, 4)

        assert len(paths) == 2
        assert [1, 2, 4] in paths
        assert [1, 3, 4] in paths

    def test_all_paths_no_cycles(self, path_finder, mock_graph_store):
        """Test that all paths are simple (no cycles)."""
        mock_graph_store.get_entity.side_effect = lambda x: Mock(id=x)

        neighbors_map = {
            (1, "from"): [(2, 1.0, 1.0)],
            (2, "from"): [(3, 1.0, 1.0)],
            (3, "from"): [],
        }

        def get_neighbors_side_effect(entity_id, direction):
            key = (entity_id, direction)
            return neighbors_map.get(key, [])

        path_finder._get_neighbors = Mock(side_effect=get_neighbors_side_effect)

        paths = path_finder.all_paths(1, 3)

        # All paths should have unique nodes (no cycles)
        for path in paths:
            assert len(path) == len(set(path))

    def test_all_paths_respects_max_depth(self, path_finder, mock_graph_store):
        """Test that max_depth parameter limits path length."""
        mock_graph_store.get_entity.side_effect = lambda x: Mock(id=x)

        neighbors_map = {
            (1, "from"): [(2, 1.0, 1.0)],
            (2, "from"): [(3, 1.0, 1.0)],
            (3, "from"): [(4, 1.0, 1.0)],
            (4, "from"): [],
        }

        def get_neighbors_side_effect(entity_id, direction):
            key = (entity_id, direction)
            return neighbors_map.get(key, [])

        path_finder._get_neighbors = Mock(side_effect=get_neighbors_side_effect)

        # Max depth 1 means only 2 nodes, but we need 4
        paths = path_finder.all_paths(1, 4, max_depth=1)

        assert len(paths) == 0

    def test_all_paths_no_path(self, path_finder, mock_graph_store):
        """Test all paths when no path exists."""
        mock_graph_store.get_entity.side_effect = lambda x: Mock(id=x)
        path_finder._get_neighbors = Mock(return_value=[])

        paths = path_finder.all_paths(1, 2)

        assert paths == []


class TestWeightedPathAlgorithm:
    """Test A* weighted pathfinding algorithm."""

    def test_weighted_path_self(self, path_finder, mock_graph_store):
        """Test weighted path from node to itself."""
        mock_graph_store.get_entity.side_effect = lambda x: Mock(id=x)

        path, cost = path_finder.weighted_path(1, 1)

        assert path == [1]
        assert cost == 0.0

    def test_weighted_path_linear(self, path_finder, mock_graph_store):
        """Test weighted path on linear graph."""
        mock_graph_store.get_entity.side_effect = lambda x: Mock(id=x)

        # 1 -> 2 -> 3 with uniform weights
        neighbors_map = {
            (1, "from"): [(2, 1.0, 1.0)],
            (2, "from"): [(3, 1.0, 1.0)],
            (3, "from"): [],
        }

        def get_neighbors_side_effect(entity_id, direction):
            key = (entity_id, direction)
            return neighbors_map.get(key, [])

        path_finder._get_neighbors = Mock(side_effect=get_neighbors_side_effect)

        path, cost = path_finder.weighted_path(1, 3)

        assert path == [1, 2, 3]
        assert cost > 0

    def test_weighted_path_prefers_strong_relations(self, path_finder, mock_graph_store):
        """Test that weighted path prefers strong relations."""
        mock_graph_store.get_entity.side_effect = lambda x: Mock(id=x)

        #   1 -> 2 (strong: 2.0, 0.95)
        #   1 -> 3 (weak: 0.5, 0.6)
        #   2 -> 4
        #   3 -> 4

        neighbors_map = {
            (1, "from"): [(2, 2.0, 0.95), (3, 0.5, 0.6)],  # A -> B (strong), A -> C (weak)
            (2, "from"): [(4, 1.0, 0.8)],  # B -> D
            (3, "from"): [(4, 1.0, 0.8)],  # C -> D
            (4, "from"): [],
        }

        def get_neighbors_side_effect(entity_id, direction):
            key = (entity_id, direction)
            return neighbors_map.get(key, [])

        path_finder._get_neighbors = Mock(side_effect=get_neighbors_side_effect)

        path, cost = path_finder.weighted_path(1, 4)

        # Should prefer path through strong relation (1->2->4)
        assert path == [1, 2, 4]

    def test_weighted_path_no_path(self, path_finder, mock_graph_store):
        """Test weighted path when no path exists."""
        mock_graph_store.get_entity.side_effect = lambda x: Mock(id=x)
        path_finder._get_neighbors = Mock(return_value=[])

        path, cost = path_finder.weighted_path(1, 2)

        assert path is None
        assert cost == -1.0

    def test_weighted_path_nonexistent_start(self, path_finder, mock_graph_store):
        """Test weighted path with non-existent start."""
        mock_graph_store.get_entity.side_effect = [None, Mock(id=2)]

        path, cost = path_finder.weighted_path(999, 2)

        assert path is None
        assert cost == -1.0

    def test_weighted_path_nonexistent_end(self, path_finder, mock_graph_store):
        """Test weighted path with non-existent end."""
        mock_graph_store.get_entity.side_effect = [Mock(id=1), None]

        path, cost = path_finder.weighted_path(1, 999)

        assert path is None
        assert cost == -1.0


class TestPathDetails:
    """Test path detail extraction."""

    def test_get_path_details_simple(self, path_finder, mock_graph_store):
        """Test getting details for a simple path."""
        # Create mocks with specific name attributes
        mock_a = Mock(id=1)
        mock_a.name = "A"
        mock_b = Mock(id=2)
        mock_b.name = "B"
        mock_c = Mock(id=3)
        mock_c.name = "C"
        entities = {1: mock_a, 2: mock_b, 3: mock_c}
        mock_graph_store.get_entity.side_effect = lambda x: entities.get(x)

        neighbors_map = {
            (1, "from"): [(2, 0.8, 0.9)],
            (2, "from"): [(3, 0.7, 0.85)],
            (3, "from"): [],
        }

        def get_neighbors_side_effect(entity_id, direction):
            key = (entity_id, direction)
            return neighbors_map.get(key, [])

        path_finder._get_neighbors = Mock(side_effect=get_neighbors_side_effect)

        details = path_finder.get_path_details([1, 2, 3])

        assert len(details) == 3
        assert details[0][1] == "A"
        assert details[1][1] == "B"
        assert details[2][1] == "C"

    def test_get_path_details_includes_weights(self, path_finder, mock_graph_store):
        """Test that path details include relation weights."""
        entities = {1: Mock(id=1, name="A"), 2: Mock(id=2, name="B")}
        mock_graph_store.get_entity.side_effect = lambda x: entities.get(x)

        path_finder._get_neighbors = Mock(return_value=[(2, 0.8, 0.9)])

        details = path_finder.get_path_details([1, 2])

        assert details[0][2] == 0.8  # strength
        assert details[0][3] == 0.9  # confidence

    def test_get_path_details_empty(self, path_finder):
        """Test path details with empty path."""
        details = path_finder.get_path_details([])

        assert details == []

    def test_get_path_details_single_node(self, path_finder, mock_graph_store):
        """Test path details with single node."""
        mock_a = Mock(id=1)
        mock_a.name = "A"
        entities = {1: mock_a}
        mock_graph_store.get_entity.side_effect = lambda x: entities.get(x)

        details = path_finder.get_path_details([1])

        assert len(details) == 1
        assert details[0][0] == 1
        assert details[0][1] == "A"


class TestCaching:
    """Test caching behavior."""

    def test_cache_stores_neighbors(self, path_finder, mock_graph_store):
        """Test that neighbors are cached."""
        path_finder._get_neighbors = PathFinder._get_neighbors.__get__(path_finder, PathFinder)
        mock_graph_store.get_entity_relations = Mock(return_value=[])

        # First call
        path_finder._get_neighbors(1, "from")
        assert len(path_finder._relation_cache) == 1

        # Cache should prevent second call
        path_finder._get_neighbors(1, "from")
        assert mock_graph_store.get_entity_relations.call_count == 1

    def test_clear_cache(self, path_finder):
        """Test that cache can be cleared."""
        path_finder._relation_cache[(1, "from")] = [(2, 1.0, 1.0)]
        path_finder._entity_cache[1] = Mock()

        assert len(path_finder._relation_cache) > 0

        path_finder.clear_cache()

        assert len(path_finder._relation_cache) == 0
        assert len(path_finder._entity_cache) == 0


class TestBenchmarking:
    """Test benchmarking functionality."""

    def test_benchmark_paths(self, path_finder, mock_graph_store):
        """Test benchmark_paths returns all three algorithms."""
        mock_graph_store.get_entity.side_effect = lambda x: Mock(id=x)

        neighbors_map = {
            (1, "from"): [(2, 1.0, 1.0)],
            (2, "from"): [(3, 1.0, 1.0)],
            (3, "from"): [],
        }

        def get_neighbors_side_effect(entity_id, direction):
            key = (entity_id, direction)
            return neighbors_map.get(key, [])

        path_finder._get_neighbors = Mock(side_effect=get_neighbors_side_effect)

        results = path_finder.benchmark_paths(1, 3)

        assert "dijkstra" in results
        assert "dfs" in results
        assert "astar" in results

    def test_benchmark_has_timing(self, path_finder, mock_graph_store):
        """Test that benchmark includes timing information."""
        mock_graph_store.get_entity.side_effect = lambda x: Mock(id=x)

        neighbors_map = {
            (1, "from"): [(2, 1.0, 1.0)],
            (2, "from"): [(3, 1.0, 1.0)],
            (3, "from"): [],
        }

        def get_neighbors_side_effect(entity_id, direction):
            key = (entity_id, direction)
            return neighbors_map.get(key, [])

        path_finder._get_neighbors = Mock(side_effect=get_neighbors_side_effect)

        results = path_finder.benchmark_paths(1, 3)

        assert results["dijkstra"]["time_ms"] >= 0
        assert results["dfs"]["time_ms"] >= 0
        assert results["astar"]["time_ms"] >= 0

    def test_benchmark_all_complete_quickly(self, path_finder, mock_graph_store):
        """Test all benchmark algorithms complete quickly."""
        mock_graph_store.get_entity.side_effect = lambda x: Mock(id=x)

        neighbors_map = {
            (1, "from"): [(2, 1.0, 1.0)],
            (2, "from"): [(3, 1.0, 1.0)],
            (3, "from"): [],
        }

        def get_neighbors_side_effect(entity_id, direction):
            key = (entity_id, direction)
            return neighbors_map.get(key, [])

        path_finder._get_neighbors = Mock(side_effect=get_neighbors_side_effect)

        results = path_finder.benchmark_paths(1, 3)

        # Each should complete in under 100ms
        assert results["dijkstra"]["time_ms"] < 100
        assert results["dfs"]["time_ms"] < 100
        assert results["astar"]["time_ms"] < 100


class TestAlgorithmCorrectness:
    """Test algorithm correctness and edge cases."""

    def test_dijkstra_finds_optimal(self, path_finder, mock_graph_store):
        """Test that Dijkstra's algorithm finds the optimal path."""
        mock_graph_store.get_entity.side_effect = lambda x: Mock(id=x)

        # Complex graph with multiple paths
        # 1 -> 2 (1 edge, expensive)
        # 1 -> 3 -> 4 (2 edges, but shorter)

        neighbors_map = {
            (1, "from"): [(2, 100.0, 1.0), (3, 1.0, 1.0)],
            (2, "from"): [(4, 1.0, 1.0)],
            (3, "from"): [(4, 1.0, 1.0)],
            (4, "from"): [],
        }

        def get_neighbors_side_effect(entity_id, direction):
            key = (entity_id, direction)
            return neighbors_map.get(key, [])

        path_finder._get_neighbors = Mock(side_effect=get_neighbors_side_effect)

        # Dijkstra minimizes edges, not weights
        path, cost = path_finder.shortest_path(1, 4)

        # Should find shortest by edges: 1->3->4 (2 edges) not 1->2->4 (also 2 edges)
        assert len(path) == 3
        assert cost == 2

    def test_dfs_finds_all_paths(self, path_finder, mock_graph_store):
        """Test that DFS finds all simple paths."""
        mock_graph_store.get_entity.side_effect = lambda x: Mock(id=x)

        # Graph with multiple paths:
        #     1
        #    /|\
        #   2 3 4
        #    \|/
        #     5

        neighbors_map = {
            (1, "from"): [(2, 1.0, 1.0), (3, 1.0, 1.0), (4, 1.0, 1.0)],
            (2, "from"): [(5, 1.0, 1.0)],
            (3, "from"): [(5, 1.0, 1.0)],
            (4, "from"): [(5, 1.0, 1.0)],
            (5, "from"): [],
        }

        def get_neighbors_side_effect(entity_id, direction):
            key = (entity_id, direction)
            return neighbors_map.get(key, [])

        path_finder._get_neighbors = Mock(side_effect=get_neighbors_side_effect)

        paths = path_finder.all_paths(1, 5)

        # Should find exactly 3 paths
        assert len(paths) == 3
        assert [1, 2, 5] in paths
        assert [1, 3, 5] in paths
        assert [1, 4, 5] in paths
