"""Unit tests for spatial hierarchy system."""

import pytest
from datetime import datetime

from athena.spatial.hierarchy import (
    build_spatial_hierarchy,
    calculate_spatial_distance,
    extract_spatial_relations,
    get_ancestors,
    get_parent_path,
    get_spatial_neighbors,
)
from athena.spatial.models import SpatialNode


class TestSpatialHierarchy:
    """Test spatial hierarchy construction."""

    def test_build_hierarchy_simple_path(self):
        """Test building hierarchy from simple path."""
        path = "/home/user/project"
        nodes = build_spatial_hierarchy(path)

        assert len(nodes) == 3
        assert nodes[0].name == "home"
        assert nodes[0].full_path == "/home"
        assert nodes[0].depth == 0
        assert nodes[0].parent_path is None

        assert nodes[1].name == "user"
        assert nodes[1].full_path == "/home/user"
        assert nodes[1].depth == 1
        assert nodes[1].parent_path == "/home"

        assert nodes[2].name == "project"
        assert nodes[2].full_path == "/home/user/project"
        assert nodes[2].depth == 2
        assert nodes[2].parent_path == "/home/user"

    def test_build_hierarchy_file_path(self):
        """Test building hierarchy with file at end."""
        path = "/project/src/auth/middleware.py"
        nodes = build_spatial_hierarchy(path)

        assert len(nodes) == 4
        assert nodes[-1].name == "middleware.py"
        assert nodes[-1].node_type == "file"
        assert nodes[-2].node_type == "directory"

    def test_build_hierarchy_empty_path(self):
        """Test empty path handling."""
        nodes = build_spatial_hierarchy("")
        assert nodes == []

    def test_build_hierarchy_normalizes_path(self):
        """Test path normalization."""
        # Path without leading slash
        nodes1 = build_spatial_hierarchy("home/user")
        assert nodes1[0].full_path == "/home"

        # Path with trailing slash
        nodes2 = build_spatial_hierarchy("/home/user/")
        assert len(nodes2) == 2

    def test_extract_relations_parent_child(self):
        """Test parent-child relation extraction."""
        nodes = [
            SpatialNode("home", "/home", 0, None),
            SpatialNode("user", "/home/user", 1, "/home"),
            SpatialNode("project", "/home/user/project", 2, "/home/user"),
        ]

        relations = extract_spatial_relations(nodes)

        # Should have 2 parent-child relations
        contains_relations = [r for r in relations if r.relation_type == 'contains']
        assert len(contains_relations) == 2

        assert any(
            r.from_path == "/home" and r.to_path == "/home/user"
            for r in contains_relations
        )
        assert any(
            r.from_path == "/home/user" and r.to_path == "/home/user/project"
            for r in contains_relations
        )

    def test_extract_relations_siblings(self):
        """Test sibling relation extraction."""
        nodes = [
            SpatialNode("parent", "/parent", 0, None),
            SpatialNode("child1", "/parent/child1", 1, "/parent"),
            SpatialNode("child2", "/parent/child2", 1, "/parent"),
            SpatialNode("child3", "/parent/child3", 1, "/parent"),
        ]

        relations = extract_spatial_relations(nodes)

        sibling_relations = [r for r in relations if r.relation_type == 'sibling']

        # 3 children = 3 sibling pairs: (1,2), (1,3), (2,3)
        assert len(sibling_relations) == 3

        assert any(
            (r.from_path == "/parent/child1" and r.to_path == "/parent/child2")
            or (r.from_path == "/parent/child2" and r.to_path == "/parent/child1")
            for r in sibling_relations
        )


class TestSpatialDistance:
    """Test spatial distance calculations."""

    def test_distance_same_path(self):
        """Test distance to same path is 0."""
        dist = calculate_spatial_distance("/home/user", "/home/user")
        assert dist == 0

    def test_distance_parent_child(self):
        """Test distance between parent and child is 1."""
        dist = calculate_spatial_distance("/home/user", "/home/user/project")
        assert dist == 1

    def test_distance_siblings(self):
        """Test distance between siblings is 2."""
        dist = calculate_spatial_distance("/home/user/proj1", "/home/user/proj2")
        assert dist == 2

    def test_distance_cousins(self):
        """Test distance between cousins is 4."""
        dist = calculate_spatial_distance(
            "/home/user1/project",
            "/home/user2/project"
        )
        assert dist == 4

    def test_distance_very_different_paths(self):
        """Test distance between unrelated paths."""
        dist = calculate_spatial_distance("/home/user/a/b/c", "/var/log/x/y")
        assert dist > 5  # Large distance


class TestSpatialNeighbors:
    """Test spatial neighbor finding."""

    def test_get_spatial_neighbors_immediate(self):
        """Test finding immediate neighbors."""
        center = "/home/user/project"
        all_paths = [
            "/home/user/project",
            "/home/user/project/src",  # Child (distance 1)
            "/home/user",  # Parent (distance 1)
            "/home/user/other",  # Sibling (distance 2)
            "/home/other/project",  # Cousin (distance 4)
        ]

        neighbors = get_spatial_neighbors(center, all_paths, max_distance=2)

        # Should include center, child, parent, sibling (not cousin)
        paths = [n[0] for n in neighbors]
        assert len(paths) == 4
        assert center in paths
        assert "/home/user/project/src" in paths
        assert "/home/user" in paths
        assert "/home/user/other" in paths
        assert "/home/other/project" not in paths

    def test_get_spatial_neighbors_sorted_by_distance(self):
        """Test neighbors are sorted by distance."""
        center = "/home/user/project"
        all_paths = [
            "/home/user/project",
            "/home/user/project/src",  # Distance 1
            "/home/user",  # Distance 1
            "/home/user/other",  # Distance 2
        ]

        neighbors = get_spatial_neighbors(center, all_paths, max_distance=2)

        # Should be sorted by distance
        distances = [n[1] for n in neighbors]
        assert distances == sorted(distances)


class TestPathUtilities:
    """Test path utility functions."""

    def test_get_parent_path(self):
        """Test getting parent path."""
        assert get_parent_path("/home/user/project") == "/home/user"
        assert get_parent_path("/home/user") == "/home"
        assert get_parent_path("/home") is None

    def test_get_ancestors(self):
        """Test getting all ancestor paths."""
        ancestors = get_ancestors("/home/user/project/src")

        assert len(ancestors) == 3
        assert "/home" in ancestors
        assert "/home/user" in ancestors
        assert "/home/user/project" in ancestors
        assert "/home/user/project/src" not in ancestors  # Not its own ancestor

    def test_get_ancestors_root(self):
        """Test getting ancestors of root-level path."""
        ancestors = get_ancestors("/home")
        assert ancestors == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
