"""Spatial hierarchy construction from file paths.

Converts flat file paths to hierarchical spatial knowledge graphs.
"""

from typing import List, Optional, Tuple

from .models import SpatialNode, SpatialRelation


def build_spatial_hierarchy(file_path: str) -> List[SpatialNode]:
    """
    Convert flat file path to hierarchical spatial nodes.

    Example:
        Input: "/home/user/projects/myapp/src/auth/middleware.py"
        Output: [
            SpatialNode(name="home", full_path="/home", depth=0, parent_path=None),
            SpatialNode(name="user", full_path="/home/user", depth=1, parent_path="/home"),
            ...
            SpatialNode(name="middleware.py", full_path="/home/.../middleware.py", depth=6, ...)
        ]

    Args:
        file_path: Absolute file path to convert

    Returns:
        List of spatial nodes from root to leaf
    """
    if not file_path:
        return []

    # Normalize path
    file_path = file_path.strip()
    if not file_path.startswith("/"):
        file_path = "/" + file_path

    # Split into components
    parts = [p for p in file_path.split("/") if p]

    if not parts:
        return []

    nodes = []
    current_path = ""

    for i, part in enumerate(parts):
        parent_path = current_path if current_path else None
        current_path = current_path + "/" + part

        # Determine node type (file vs directory)
        is_file = i == len(parts) - 1 and "." in part
        node_type = "file" if is_file else "directory"

        node = SpatialNode(
            name=part, full_path=current_path, depth=i, parent_path=parent_path, node_type=node_type
        )

        nodes.append(node)

    return nodes


def extract_spatial_relations(nodes: List[SpatialNode]) -> List[SpatialRelation]:
    """
    Extract parent-child and sibling relations from spatial nodes.

    Args:
        nodes: List of spatial nodes (typically from multiple paths)

    Returns:
        List of spatial relations
    """
    relations = []
    seen_relations = set()

    # Build parent-child relations
    for node in nodes:
        if node.parent_path:
            relation_key = (node.parent_path, node.full_path, "contains")

            if relation_key not in seen_relations:
                relations.append(
                    SpatialRelation(
                        from_path=node.parent_path,
                        to_path=node.full_path,
                        relation_type="contains",
                        strength=1.0,
                    )
                )
                seen_relations.add(relation_key)

    # Build sibling relations (nodes with same parent)
    nodes_by_parent = {}
    for node in nodes:
        parent = node.parent_path or "ROOT"
        if parent not in nodes_by_parent:
            nodes_by_parent[parent] = []
        nodes_by_parent[parent].append(node)

    for parent, siblings in nodes_by_parent.items():
        if len(siblings) > 1:
            # Create sibling relations
            for i, node1 in enumerate(siblings):
                for node2 in siblings[i + 1 :]:
                    relation_key = (node1.full_path, node2.full_path, "sibling")

                    if relation_key not in seen_relations:
                        relations.append(
                            SpatialRelation(
                                from_path=node1.full_path,
                                to_path=node2.full_path,
                                relation_type="sibling",
                                strength=0.8,  # Sibling relations slightly weaker
                            )
                        )
                        seen_relations.add(relation_key)

    return relations


def calculate_spatial_distance(path1: str, path2: str) -> int:
    """
    Calculate distance between two paths in the spatial hierarchy.

    Distance is the minimum number of hops in the tree:
    - Sibling: 2 hops (up to parent, down to sibling)
    - Parent-child: 1 hop
    - Cousins: 4 hops (up to grandparent, down through uncle to cousin)

    Args:
        path1: First file path
        path2: Second file path

    Returns:
        Number of hops between paths
    """
    parts1 = [p for p in path1.split("/") if p]
    parts2 = [p for p in path2.split("/") if p]

    # Find common prefix
    common_depth = 0
    for p1, p2 in zip(parts1, parts2):
        if p1 == p2:
            common_depth += 1
        else:
            break

    # Distance = (depth1 - common) + (depth2 - common)
    distance = (len(parts1) - common_depth) + (len(parts2) - common_depth)

    return distance


def get_spatial_neighbors(
    center_path: str, all_paths: List[str], max_distance: int = 2
) -> List[Tuple[str, int]]:
    """
    Get all paths within max_distance hops of center_path.

    Args:
        center_path: Path to center search around
        all_paths: All available paths to consider
        max_distance: Maximum distance (hops) to include

    Returns:
        List of (path, distance) tuples within max_distance
    """
    neighbors = []

    for path in all_paths:
        if path == center_path:
            neighbors.append((path, 0))
        else:
            distance = calculate_spatial_distance(center_path, path)
            if distance <= max_distance:
                neighbors.append((path, distance))

    # Sort by distance
    neighbors.sort(key=lambda x: x[1])

    return neighbors


def get_parent_path(path: str) -> Optional[str]:
    """Get parent path of a file path."""
    parts = [p for p in path.split("/") if p]
    if len(parts) <= 1:
        return None
    return "/" + "/".join(parts[:-1])


def get_ancestors(path: str) -> List[str]:
    """Get all ancestor paths from root to parent."""
    parts = [p for p in path.split("/") if p]
    ancestors = []

    for i in range(len(parts)):
        ancestor = "/" + "/".join(parts[: i + 1])
        if ancestor != path:
            ancestors.append(ancestor)

    return ancestors
