"""Advanced graph analytics for knowledge graph analysis.

Implements:
- Betweenness centrality: Measures importance of nodes in shortest paths
- Graph clustering: Detects communities and groups of related entities
- Clustering coefficient: Measures local density of connections
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque
import math

from .models import Entity, Relation


@dataclass
class CentralityScore:
    """Centrality metrics for an entity."""
    entity_id: int
    entity_name: str
    betweenness: float  # 0-1 scale, higher = more important
    closeness: float    # 0-1 scale, avg distance to other nodes
    degree: int         # Number of connections
    importance: float   # Combined importance score


@dataclass
class Cluster:
    """A cluster of related entities."""
    id: int
    entity_ids: List[int]
    entity_names: List[str]
    density: float      # 0-1 scale, connectivity within cluster
    size: int
    internal_edges: int
    external_edges: int
    cohesion: float     # Internal vs external connectivity


@dataclass
class GraphAnalytics:
    """Graph analytics for knowledge graph."""
    total_entities: int
    total_edges: int
    density: float
    average_degree: float
    clustering_coefficient: float
    diameter: int
    top_centralities: List[CentralityScore]
    clusters: List[Cluster]
    isolated_entities: List[int]


class GraphAnalyzer:
    """Analyzes knowledge graph structure and importance."""

    def __init__(self, entities: List[Entity], relations: List[Relation]):
        """Initialize analyzer with graph data.

        Args:
            entities: List of entities (nodes)
            relations: List of relations (edges)
        """
        self.entities = {e.id: e for e in entities}
        self.relations = relations

        # Build adjacency structure
        self.graph: Dict[int, Set[int]] = defaultdict(set)
        self.weighted_graph: Dict[int, Dict[int, float]] = defaultdict(dict)

        for rel in relations:
            # Bidirectional edges (treat knowledge graph as undirected)
            self.graph[rel.from_entity_id].add(rel.to_entity_id)
            self.graph[rel.to_entity_id].add(rel.from_entity_id)

            # Store weights (strength values)
            weight = rel.strength * rel.confidence
            self.weighted_graph[rel.from_entity_id][rel.to_entity_id] = weight
            self.weighted_graph[rel.to_entity_id][rel.from_entity_id] = weight

    def compute_betweenness_centrality(self, normalize: bool = True) -> Dict[int, float]:
        """Compute betweenness centrality for all nodes.

        Betweenness centrality measures how often a node lies on shortest paths
        between other nodes. Higher values indicate more important nodes.

        Args:
            normalize: Whether to normalize to 0-1 scale

        Returns:
            Dictionary mapping entity_id to centrality score
        """
        betweenness: Dict[int, float] = {node: 0 for node in self.entities.keys()}

        # For each node as source
        for s in self.entities.keys():
            # BFS to find shortest paths
            stack: List[int] = []
            paths: Dict[int, List[List[int]]] = defaultdict(list)
            sigma: Dict[int, int] = defaultdict(int)  # Number of shortest paths

            sigma[s] = 1
            queue = deque([s])
            distance: Dict[int, int] = {s: 0}

            while queue:
                v = queue.popleft()
                stack.append(v)

                for w in self.graph[v]:
                    # First time seeing w?
                    if w not in distance:
                        distance[w] = distance[v] + 1
                        queue.append(w)

                    # Is v on shortest path to w?
                    if distance[w] == distance[v] + 1:
                        sigma[w] += sigma[v]
                        paths[w].append(v)

            # Accumulate betweenness scores
            delta: Dict[int, float] = defaultdict(float)

            # Process in reverse order
            while stack:
                w = stack.pop()
                for v in paths[w]:
                    delta[v] += (sigma[v] / sigma[w]) * (1 + delta[w])
                if w != s:
                    betweenness[w] += delta[w]

        # Normalize
        if normalize and len(self.entities) > 2:
            normalizer = 2.0 / ((len(self.entities) - 1) * (len(self.entities) - 2))
            betweenness = {k: v * normalizer for k, v in betweenness.items()}

        return betweenness

    def compute_closeness_centrality(self, normalize: bool = True) -> Dict[int, float]:
        """Compute closeness centrality for all nodes.

        Closeness measures how close a node is to all other nodes on average.
        Higher values indicate more central nodes.

        Args:
            normalize: Whether to normalize to 0-1 scale

        Returns:
            Dictionary mapping entity_id to closeness score
        """
        closeness: Dict[int, float] = {}
        n = len(self.entities)

        for s in self.entities.keys():
            # BFS to compute shortest distances
            distances: Dict[int, int] = {s: 0}
            queue = deque([s])

            while queue:
                v = queue.popleft()
                for w in self.graph[v]:
                    if w not in distances:
                        distances[w] = distances[v] + 1
                        queue.append(w)

            # Average distance to reachable nodes
            total_distance = sum(distances.values())
            reachable = len(distances) - 1  # Excluding self

            if reachable == 0:
                closeness[s] = 0.0
            else:
                # Closeness = reachable / total distance
                c = reachable / total_distance if total_distance > 0 else 0
                if normalize:
                    c = c * (n - 1) / (n - 1)  # Normalize to 0-1
                closeness[s] = c

        return closeness

    def compute_clustering_coefficient(self) -> Dict[int, float]:
        """Compute local clustering coefficient for all nodes.

        Clustering coefficient measures how close the neighbors of a node are
        to forming a complete graph. Range: 0-1.

        Returns:
            Dictionary mapping entity_id to clustering coefficient
        """
        clustering: Dict[int, float] = {}

        for node in self.entities.keys():
            neighbors = self.graph[node]
            degree = len(neighbors)

            if degree < 2:
                clustering[node] = 0.0
            else:
                # Count edges between neighbors
                edges_between_neighbors = 0
                for n1 in neighbors:
                    for n2 in neighbors:
                        if n1 < n2 and n2 in self.graph[n1]:
                            edges_between_neighbors += 1

                # Possible edges between k neighbors
                possible_edges = degree * (degree - 1) / 2
                clustering[node] = edges_between_neighbors / possible_edges if possible_edges > 0 else 0.0

        return clustering

    def compute_degree_centrality(self) -> Dict[int, float]:
        """Compute normalized degree centrality for all nodes.

        Returns:
            Dictionary mapping entity_id to degree centrality (0-1)
        """
        n = len(self.entities)
        if n <= 1:
            return {node: 0.0 for node in self.entities.keys()}

        degree_centrality: Dict[int, float] = {}
        for node in self.entities.keys():
            degree = len(self.graph[node])
            degree_centrality[node] = degree / (n - 1)  # Normalize by max possible degree

        return degree_centrality

    def detect_clusters(self, method: str = "modularity") -> List[Cluster]:
        """Detect communities/clusters in the graph.

        Uses Louvain-style modularity optimization for community detection.

        Args:
            method: Detection method ("modularity" or "density")

        Returns:
            List of detected clusters
        """
        if method == "modularity":
            return self._detect_clusters_modularity()
        else:
            return self._detect_clusters_density()

    def _detect_clusters_modularity(self) -> List[Cluster]:
        """Detect clusters using modularity optimization."""
        # Initialize: each node is its own cluster
        clusters: Dict[int, Set[int]] = {node: {node} for node in self.entities.keys()}

        # Iteratively merge clusters to maximize modularity
        improved = True
        iteration = 0
        max_iterations = 100

        while improved and iteration < max_iterations:
            improved = False
            iteration += 1

            # Try merging each pair of adjacent clusters
            nodes_to_check = list(self.entities.keys())

            for node in nodes_to_check:
                current_cluster = clusters[node]

                # Find neighboring clusters
                neighbor_clusters: Set[int] = set()
                for n in current_cluster:
                    for neighbor in self.graph[n]:
                        neighbor_cluster_id = None
                        for cid, members in clusters.items():
                            if neighbor in members:
                                neighbor_cluster_id = cid
                                break
                        if neighbor_cluster_id and neighbor_cluster_id != node:
                            neighbor_clusters.add(neighbor_cluster_id)

                # Try merging with each neighbor
                for neighbor_cluster_id in neighbor_clusters:
                    neighbor_cluster = clusters[neighbor_cluster_id]

                    # Compute modularity change
                    modularity_before = self._compute_modularity_contribution(
                        current_cluster
                    ) + self._compute_modularity_contribution(neighbor_cluster)

                    merged = current_cluster | neighbor_cluster
                    modularity_after = self._compute_modularity_contribution(merged)

                    if modularity_after > modularity_before:
                        # Merge clusters
                        clusters[node] = merged
                        del clusters[neighbor_cluster_id]
                        for member in merged:
                            clusters[member] = merged
                        improved = True
                        break

        # Convert to Cluster objects
        unique_clusters: Dict[frozenset, Cluster] = {}

        for cluster_set in set(frozenset(c) for c in clusters.values()):
            cluster_list = list(cluster_set)
            cluster_id = len(unique_clusters)

            entity_names = [self.entities[eid].name for eid in cluster_list]
            density = self._compute_cluster_density(cluster_list)
            internal_edges = self._count_internal_edges(cluster_list)
            external_edges = self._count_external_edges(cluster_list)

            cohesion = (
                (internal_edges / (internal_edges + external_edges))
                if (internal_edges + external_edges) > 0
                else 0.0
            )

            unique_clusters[cluster_set] = Cluster(
                id=cluster_id,
                entity_ids=cluster_list,
                entity_names=entity_names,
                density=density,
                size=len(cluster_list),
                internal_edges=internal_edges,
                external_edges=external_edges,
                cohesion=cohesion,
            )

        return list(unique_clusters.values())

    def _detect_clusters_density(self) -> List[Cluster]:
        """Detect clusters based on local density (simpler method)."""
        visited: Set[int] = set()
        clusters: List[Cluster] = []

        for start_node in self.entities.keys():
            if start_node in visited:
                continue

            # BFS to find connected component
            cluster_members: Set[int] = set()
            queue = deque([start_node])

            while queue:
                node = queue.popleft()
                if node in visited:
                    continue

                visited.add(node)
                cluster_members.add(node)

                for neighbor in self.graph[node]:
                    if neighbor not in visited:
                        queue.append(neighbor)

            if cluster_members:
                cluster_id = len(clusters)
                entity_names = [self.entities[eid].name for eid in cluster_members]
                density = self._compute_cluster_density(list(cluster_members))
                internal_edges = self._count_internal_edges(list(cluster_members))
                external_edges = self._count_external_edges(list(cluster_members))

                cohesion = (
                    (internal_edges / (internal_edges + external_edges))
                    if (internal_edges + external_edges) > 0
                    else 0.0
                )

                clusters.append(Cluster(
                    id=cluster_id,
                    entity_ids=list(cluster_members),
                    entity_names=entity_names,
                    density=density,
                    size=len(cluster_members),
                    internal_edges=internal_edges,
                    external_edges=external_edges,
                    cohesion=cohesion,
                ))

        return clusters

    def _compute_modularity_contribution(self, cluster: Set[int]) -> float:
        """Compute modularity contribution of a cluster."""
        if len(cluster) <= 1:
            return 0.0

        internal_edges = 0.0
        external_edges = 0.0

        for node in cluster:
            for neighbor in self.graph[node]:
                if neighbor in cluster and neighbor != node:
                    internal_edges += 1
                elif neighbor not in cluster:
                    external_edges += 1

        internal_edges /= 2  # Each edge counted twice
        total_edges = internal_edges + external_edges / 2

        if total_edges == 0:
            return 0.0

        # Modularity = (edges_within - expected_edges) / total_edges
        expected = (len(cluster) * (len(cluster) - 1)) / 2
        return (internal_edges - expected) / total_edges if total_edges > 0 else 0.0

    def _compute_cluster_density(self, cluster_members: List[int]) -> float:
        """Compute density of a cluster (0-1)."""
        n = len(cluster_members)
        if n <= 1:
            return 0.0

        edges = 0
        for i in range(len(cluster_members)):
            for j in range(i + 1, len(cluster_members)):
                if cluster_members[j] in self.graph[cluster_members[i]]:
                    edges += 1

        possible_edges = n * (n - 1) / 2
        return edges / possible_edges if possible_edges > 0 else 0.0

    def _count_internal_edges(self, cluster_members: List[int]) -> int:
        """Count edges within cluster."""
        cluster_set = set(cluster_members)
        edges = 0

        for node in cluster_members:
            for neighbor in self.graph[node]:
                if neighbor in cluster_set and neighbor > node:
                    edges += 1

        return edges

    def _count_external_edges(self, cluster_members: List[int]) -> int:
        """Count edges from cluster to outside."""
        cluster_set = set(cluster_members)
        edges = 0

        for node in cluster_members:
            for neighbor in self.graph[node]:
                if neighbor not in cluster_set:
                    edges += 1

        return edges

    def compute_shortest_path(self, start_id: int, end_id: int) -> Optional[List[int]]:
        """Compute shortest path between two entities.

        Args:
            start_id: Starting entity ID
            end_id: Ending entity ID

        Returns:
            List of entity IDs representing shortest path, or None if no path
        """
        if start_id not in self.entities or end_id not in self.entities:
            return None

        if start_id == end_id:
            return [start_id]

        # BFS
        queue = deque([(start_id, [start_id])])
        visited: Set[int] = {start_id}

        while queue:
            node, path = queue.popleft()

            for neighbor in self.graph[node]:
                if neighbor == end_id:
                    return path + [neighbor]

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None

    def compute_graph_diameter(self) -> int:
        """Compute diameter of the graph (longest shortest path).

        Returns:
            Diameter value, or 0 if graph is empty or disconnected
        """
        if len(self.entities) <= 1:
            return 0

        max_distance = 0

        for start_id in list(self.entities.keys())[:min(10, len(self.entities))]:
            # Sample 10 nodes max to avoid O(n^2) computation
            for end_id in self.entities.keys():
                path = self.compute_shortest_path(start_id, end_id)
                if path:
                    distance = len(path) - 1
                    max_distance = max(max_distance, distance)

        return max_distance

    def find_isolated_entities(self) -> List[int]:
        """Find entities with no connections.

        Returns:
            List of isolated entity IDs
        """
        return [node for node in self.entities.keys() if len(self.graph[node]) == 0]

    def compute_all_analytics(self, top_k: int = 10) -> GraphAnalytics:
        """Compute comprehensive graph analytics.

        Args:
            top_k: Number of top centrality scores to return

        Returns:
            GraphAnalytics object with all metrics
        """
        # Basic metrics
        n = len(self.entities)
        m = len(self.relations)  # Count relations as provided
        # For density: each relation represents a bidirectional edge in the undirected graph
        density = (2 * m) / (n * (n - 1)) if n > 1 else 0.0
        avg_degree = (2 * m) / n if n > 0 else 0.0

        # Centrality measures
        betweenness = self.compute_betweenness_centrality()
        closeness = self.compute_closeness_centrality()
        degree = self.compute_degree_centrality()
        clustering_coeff = self.compute_clustering_coefficient()

        # Average clustering coefficient
        avg_clustering = (
            sum(clustering_coeff.values()) / len(clustering_coeff)
            if clustering_coeff
            else 0.0
        )

        # Top centrality scores
        combined_scores = []
        for entity_id in self.entities.keys():
            # Combine metrics: 50% betweenness, 30% degree, 20% closeness
            importance = (
                0.5 * betweenness.get(entity_id, 0.0) +
                0.3 * degree.get(entity_id, 0.0) +
                0.2 * closeness.get(entity_id, 0.0)
            )

            combined_scores.append(CentralityScore(
                entity_id=entity_id,
                entity_name=self.entities[entity_id].name,
                betweenness=betweenness.get(entity_id, 0.0),
                closeness=closeness.get(entity_id, 0.0),
                degree=len(self.graph[entity_id]),
                importance=importance,
            ))

        # Sort by importance and get top K
        combined_scores.sort(key=lambda x: x.importance, reverse=True)
        top_centralities = combined_scores[:top_k]

        # Clustering
        clusters = self.detect_clusters()

        # Isolated entities
        isolated = self.find_isolated_entities()

        # Diameter
        diameter = self.compute_graph_diameter()

        return GraphAnalytics(
            total_entities=n,
            total_edges=int(m),
            density=min(density, 1.0),
            average_degree=avg_degree,
            clustering_coefficient=avg_clustering,
            diameter=diameter,
            top_centralities=top_centralities,
            clusters=clusters,
            isolated_entities=isolated,
        )

