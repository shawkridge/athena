"""Graph pathfinding algorithms for knowledge graph traversal."""

import heapq
import time
from typing import Optional, Tuple, List, Set

from ..core.database import Database
from .models import Entity, Relation
from .store import GraphStore


class PathFinder:
    """Pathfinding algorithms for knowledge graph traversal.

    Provides three main algorithms:
    - Dijkstra: Shortest path by edge count
    - DFS: All simple paths (no cycles)
    - A*: Weighted path by relation strength
    """

    def __init__(self, db: Database):
        """Initialize PathFinder.

        Args:
            db: Database instance
        """
        self.db = db
        self.graph_store = GraphStore(db)
        self._relation_cache = {}
        self._entity_cache = {}

    def _get_neighbors(self, entity_id: int, direction: str = "from") -> List[Tuple[int, float, float]]:
        """Get neighbors and edge weights for an entity.

        Args:
            entity_id: Entity ID
            direction: 'from' (outgoing), 'to' (incoming), or 'both'

        Returns:
            List of (neighbor_id, strength, confidence) tuples
        """
        # Check cache first
        cache_key = (entity_id, direction)
        if cache_key in self._relation_cache:
            return self._relation_cache[cache_key]

        try:
            relations = self.graph_store.get_entity_relations(entity_id, direction=direction)
        except (ValueError, TypeError, KeyError, AttributeError, IndexError):
            # If entity doesn't exist or query fails, return empty list
            neighbors = []
            self._relation_cache[cache_key] = neighbors
            return neighbors

        neighbors = []

        for relation, related_entity in relations:
            if direction == "from":
                neighbor_id = relation.to_entity_id
            elif direction == "to":
                neighbor_id = relation.from_entity_id
            else:  # both
                # For bidirectional, follow the relation
                neighbor_id = (
                    relation.to_entity_id
                    if relation.from_entity_id == entity_id
                    else relation.from_entity_id
                )

            neighbors.append((neighbor_id, relation.strength, relation.confidence))

        # Cache the result
        self._relation_cache[cache_key] = neighbors
        return neighbors

    def shortest_path(
        self, from_id: int, to_id: int, max_depth: int = 100
    ) -> Tuple[Optional[List[int]], int]:
        """Find shortest path using Dijkstra's algorithm.

        Returns minimum number of edges between two entities.

        Args:
            from_id: Start entity ID
            to_id: End entity ID
            max_depth: Maximum path depth to explore

        Returns:
            Tuple of (path as list of IDs, cost as number of edges).
            Returns (None, -1) if no path exists.
        """
        if from_id == to_id:
            return [from_id], 0

        # Validate entities exist
        if not self.graph_store.get_entity(from_id):
            return None, -1
        if not self.graph_store.get_entity(to_id):
            return None, -1

        # Dijkstra's algorithm: minimize edge count
        visited = set()
        distances = {from_id: 0}
        parents = {from_id: None}
        heap = [(0, from_id)]  # (distance, node)

        while heap:
            current_distance, current = heapq.heappop(heap)

            if current in visited:
                continue

            if current == to_id:
                # Reconstruct path
                path = []
                node = to_id
                while node is not None:
                    path.append(node)
                    node = parents[node]
                path.reverse()
                return path, current_distance

            if current_distance > max_depth:
                break

            visited.add(current)

            # Explore outgoing edges
            neighbors = self._get_neighbors(current, direction="from")
            for neighbor_id, _, _ in neighbors:
                if neighbor_id not in visited:
                    new_distance = current_distance + 1
                    if neighbor_id not in distances or new_distance < distances[neighbor_id]:
                        distances[neighbor_id] = new_distance
                        parents[neighbor_id] = current
                        heapq.heappush(heap, (new_distance, neighbor_id))

        # No path found
        return None, -1

    def all_paths(
        self, from_id: int, to_id: int, max_depth: int = 10
    ) -> List[List[int]]:
        """Find all simple paths using DFS with cycle detection.

        Returns all paths without cycles between two entities.

        Args:
            from_id: Start entity ID
            to_id: End entity ID
            max_depth: Maximum path depth to explore

        Returns:
            List of paths, each path is a list of entity IDs.
            Empty list if no paths exist.
        """
        if from_id == to_id:
            return [[from_id]]

        # Validate entities exist
        if not self.graph_store.get_entity(from_id):
            return []
        if not self.graph_store.get_entity(to_id):
            return []

        paths = []
        visited = set()

        def dfs(current: int, target: int, path: List[int], visited: Set[int], depth: int):
            """Depth-first search helper function.

            Args:
                current: Current entity ID
                target: Target entity ID
                path: Current path
                visited: Set of visited nodes (for cycle detection)
                depth: Current depth
            """
            if depth > max_depth:
                return

            if current == target:
                paths.append(path.copy())
                return

            visited.add(current)

            # Explore outgoing edges
            neighbors = self._get_neighbors(current, direction="from")
            for neighbor_id, _, _ in neighbors:
                if neighbor_id not in visited:
                    path.append(neighbor_id)
                    dfs(neighbor_id, target, path, visited.copy(), depth + 1)
                    path.pop()

        dfs(from_id, to_id, [from_id], visited, 0)
        return paths

    def weighted_path(
        self, from_id: int, to_id: int, max_depth: int = 100
    ) -> Tuple[Optional[List[int]], float]:
        """Find path minimizing edge weight using A* algorithm.

        Uses relation strength and confidence as cost (lower is better).
        Higher strength = lower cost (prefer strong relations).

        Args:
            from_id: Start entity ID
            to_id: End entity ID
            max_depth: Maximum path depth to explore

        Returns:
            Tuple of (path as list of IDs, total cost as float).
            Returns (None, -1.0) if no path exists.
        """
        if from_id == to_id:
            return [from_id], 0.0

        # Validate entities exist
        if not self.graph_store.get_entity(from_id):
            return None, -1.0
        if not self.graph_store.get_entity(to_id):
            return None, -1.0

        # A* algorithm: minimize total weight (1/strength * confidence penalty)
        visited = set()
        g_scores = {from_id: 0.0}  # Cost from start
        parents = {from_id: None}
        heap = [(0.0, from_id)]  # (f_score, node)

        while heap:
            _, current = heapq.heappop(heap)

            if current in visited:
                continue

            if current == to_id:
                # Reconstruct path
                path = []
                node = to_id
                while node is not None:
                    path.append(node)
                    node = parents[node]
                path.reverse()
                return path, g_scores[to_id]

            if g_scores[current] > max_depth:
                break

            visited.add(current)

            # Explore outgoing edges with weights
            neighbors = self._get_neighbors(current, direction="from")
            for neighbor_id, strength, confidence in neighbors:
                if neighbor_id not in visited:
                    # Cost = (1/strength) * confidence_penalty
                    # Higher strength = lower cost (prefer strong relations)
                    # Higher confidence = lower cost (prefer confident relations)
                    edge_cost = (1.0 / max(strength, 0.1)) * (2.0 - confidence)
                    new_g_score = g_scores[current] + edge_cost

                    if neighbor_id not in g_scores or new_g_score < g_scores[neighbor_id]:
                        g_scores[neighbor_id] = new_g_score
                        parents[neighbor_id] = current
                        # For A*, f = g + h. Simple heuristic: 0 (Dijkstra variant)
                        heapq.heappush(heap, (new_g_score, neighbor_id))

        # No path found
        return None, -1.0

    def get_path_details(self, path: List[int]) -> List[Tuple[int, str, float, float]]:
        """Get detailed information about a path.

        Args:
            path: List of entity IDs forming a path

        Returns:
            List of (entity_id, entity_name, relation_strength, relation_confidence)
        """
        if not path or len(path) < 1:
            return []

        details = []
        for i, entity_id in enumerate(path):
            entity = self.graph_store.get_entity(entity_id)
            if entity:
                if i == len(path) - 1:
                    # Last node, no outgoing relation
                    details.append((entity_id, entity.name, 0.0, 0.0))
                else:
                    # Get relation to next node
                    next_id = path[i + 1]
                    neighbors = self._get_neighbors(entity_id, direction="from")
                    for neighbor_id, strength, confidence in neighbors:
                        if neighbor_id == next_id:
                            details.append((entity_id, entity.name, strength, confidence))
                            break

        return details

    def clear_cache(self):
        """Clear internal caches for memory efficiency."""
        self._relation_cache.clear()
        self._entity_cache.clear()

    def benchmark_paths(
        self, from_id: int, to_id: int, max_depth: int = 10
    ) -> dict:
        """Benchmark all three algorithms.

        Args:
            from_id: Start entity ID
            to_id: End entity ID
            max_depth: Maximum path depth

        Returns:
            Dict with timing and result info for each algorithm
        """
        results = {}

        # Dijkstra
        start = time.time()
        dijkstra_path, dijkstra_cost = self.shortest_path(from_id, to_id, max_depth)
        dijkstra_time = (time.time() - start) * 1000  # milliseconds
        results["dijkstra"] = {
            "path": dijkstra_path,
            "cost": dijkstra_cost,
            "time_ms": dijkstra_time,
            "path_length": len(dijkstra_path) if dijkstra_path else 0,
        }

        # DFS
        start = time.time()
        dfs_paths = self.all_paths(from_id, to_id, max_depth)
        dfs_time = (time.time() - start) * 1000
        results["dfs"] = {
            "paths": dfs_paths,
            "count": len(dfs_paths),
            "time_ms": dfs_time,
            "avg_length": sum(len(p) for p in dfs_paths) / len(dfs_paths) if dfs_paths else 0,
        }

        # A*
        start = time.time()
        astar_path, astar_cost = self.weighted_path(from_id, to_id, max_depth)
        astar_time = (time.time() - start) * 1000
        results["astar"] = {
            "path": astar_path,
            "cost": astar_cost,
            "time_ms": astar_time,
            "path_length": len(astar_path) if astar_path else 0,
        }

        return results
