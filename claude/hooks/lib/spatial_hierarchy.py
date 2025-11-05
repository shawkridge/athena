#!/usr/bin/env python3
"""
Spatial Hierarchy - Phase 5 Implementation

Decomposes file paths hierarchically for spatial grounding of episodic events.

Enables queries like:
- "What happened in src/auth?"
- "All events in project root"
- "Events in this directory and subdirectories"

Spatial nodes form a tree:
/home/user/project/src/auth/jwt.py
  ↓ decomposes into:
  /                           (level 0, root)
  /home                       (level 1)
  /home/user                  (level 2)
  /home/user/project          (level 3)
  /home/user/project/src      (level 4)
  /home/user/project/src/auth (level 5)
  jwt.py                      (filename, level 6)

Or relative paths:
src/auth/jwt.py
  ↓
src/                          (level 0, relative root)
src/auth/                     (level 1)
jwt.py                        (level 2, filename)
"""

import json
import logging
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import sqlite3

logger = logging.getLogger("spatial_hierarchy")


@dataclass
class SpatialNode:
    """
    Represents a single node in the spatial hierarchy.

    Attributes:
        id: Unique identifier
        path: Full path (absolute or relative)
        level: Depth in hierarchy (0=root, increases with depth)
        parent_path: Parent directory path
        node_type: "directory", "file", "root"
        is_leaf: True if no children (file or empty dir)
    """
    id: Optional[int] = None
    path: str = ""
    level: int = 0
    parent_path: Optional[str] = None
    node_type: str = "directory"  # "directory", "file", "root"
    is_leaf: bool = False

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}


class SpatialHierarchy:
    """
    Decomposes file paths into hierarchical nodes.

    Examples:
        >>> hierarchy = SpatialHierarchy()
        >>> nodes = hierarchy.decompose_path("/home/user/project/src/auth/jwt.py")
        >>> # Returns 7 nodes: /, /home, /home/user, ..., jwt.py
        >>>
        >>> nodes = hierarchy.decompose_path("src/auth/jwt.py", is_absolute=False)
        >>> # Returns 3 nodes: src, src/auth, jwt.py
    """

    def __init__(self, is_absolute: bool = True):
        """
        Initialize hierarchy processor.

        Args:
            is_absolute: True for absolute paths, False for relative paths
        """
        self.is_absolute = is_absolute

    def decompose_path(self, path: str, is_absolute: Optional[bool] = None) -> List[SpatialNode]:
        """
        Decompose a file path into hierarchical nodes.

        Args:
            path: File or directory path
            is_absolute: Override default (True=absolute, False=relative)

        Returns:
            List of SpatialNode objects from root to file/directory

        Examples:
            >>> hierarchy = SpatialHierarchy(is_absolute=True)
            >>> nodes = hierarchy.decompose_path("/home/user/src/auth.py")
            >>> nodes[0].path  # "/"
            >>> nodes[-1].path # "/home/user/src/auth.py"
            >>> len(nodes)     # 5
        """
        if is_absolute is None:
            is_absolute = self.is_absolute

        path = path.strip()
        if not path:
            return []

        nodes = []

        if is_absolute:
            nodes.append(SpatialNode(
                path="/",
                level=0,
                parent_path=None,
                node_type="root",
                is_leaf=False
            ))

            # Split path and build nodes
            parts = path.split("/")[1:]  # Skip first empty part
            current_path = ""

            for i, part in enumerate(parts):
                if not part:  # Skip empty parts
                    continue

                current_path = current_path + "/" + part if current_path else "/" + part
                is_file = i == len(parts) - 1 and "." in part

                nodes.append(SpatialNode(
                    path=current_path,
                    level=len(nodes),
                    parent_path=nodes[-1].path if nodes else None,
                    node_type="file" if is_file else "directory",
                    is_leaf=is_file
                ))
        else:
            # Relative path processing
            parts = path.split("/")
            current_path = ""

            for i, part in enumerate(parts):
                if not part:  # Skip empty parts
                    continue

                current_path = current_path + "/" + part if current_path else part
                is_file = i == len(parts) - 1 and "." in part

                nodes.append(SpatialNode(
                    path=current_path,
                    level=len(nodes),
                    parent_path=nodes[-1].path if nodes else None,
                    node_type="file" if is_file else "directory",
                    is_leaf=is_file
                ))

        return nodes

    def get_ancestors(self, path: str) -> List[str]:
        """
        Get all ancestor paths (parent directories).

        Args:
            path: File or directory path

        Returns:
            List of ancestor paths from root to immediate parent

        Examples:
            >>> hierarchy = SpatialHierarchy()
            >>> ancestors = hierarchy.get_ancestors("/home/user/src/auth.py")
            >>> ancestors
            ["/", "/home", "/home/user", "/home/user/src"]
        """
        nodes = self.decompose_path(path)
        if not nodes:
            return []

        # All nodes except the last one (the path itself)
        return [n.path for n in nodes[:-1]]

    def get_common_ancestor(self, path1: str, path2: str) -> Optional[str]:
        """
        Find the lowest common ancestor of two paths.

        Args:
            path1: First path
            path2: Second path

        Returns:
            Common ancestor path, or None if no common ancestor

        Examples:
            >>> hierarchy = SpatialHierarchy()
            >>> common = hierarchy.get_common_ancestor(
            ...     "/home/user/src/auth.py",
            ...     "/home/user/src/utils.py"
            ... )
            >>> common  # "/home/user/src"
        """
        ancestors1 = set(self.get_ancestors(path1))
        ancestors2 = set(self.get_ancestors(path2))

        common = ancestors1.intersection(ancestors2)
        if not common:
            return None

        # Return the deepest common ancestor
        return max(common, key=lambda p: len(p.split("/")))

    def is_under_path(self, file_path: str, directory_path: str) -> bool:
        """
        Check if a file is under a directory in the hierarchy.

        Args:
            file_path: File path to check
            directory_path: Directory path

        Returns:
            True if file_path is under directory_path

        Examples:
            >>> hierarchy = SpatialHierarchy()
            >>> hierarchy.is_under_path(
            ...     "/home/user/src/auth.py",
            ...     "/home/user/src"
            ... )  # True
            >>> hierarchy.is_under_path(
            ...     "/home/user/src/auth.py",
            ...     "/home/user/tests"
            ... )  # False
        """
        ancestors = self.get_ancestors(file_path)
        return directory_path in ancestors or file_path == directory_path


class SpatialStore:
    """
    Stores and queries spatial nodes in a database.

    Provides:
    - Persistent storage of spatial hierarchy
    - Fast queries by path prefix
    - Ancestor/descendant relationships
    - Integration with episodic events
    """

    def __init__(self, db_path: str):
        """
        Initialize spatial store.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.hierarchy = SpatialHierarchy(is_absolute=True)
        self._ensure_schema()

    def _ensure_schema(self):
        """Create tables if they don't exist."""
        cursor = self.conn.cursor()

        # Spatial nodes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS spatial_nodes (
                id INTEGER PRIMARY KEY,
                path TEXT UNIQUE NOT NULL,
                level INTEGER NOT NULL,
                parent_path TEXT,
                node_type TEXT NOT NULL DEFAULT 'directory',
                is_leaf BOOLEAN DEFAULT FALSE,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(parent_path) REFERENCES spatial_nodes(path)
            )
        """)

        # Index for fast queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_spatial_path_prefix
            ON spatial_nodes(path)
        """)

        # Link episodic events to spatial nodes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_spatial_links (
                event_id INTEGER NOT NULL,
                spatial_node_id INTEGER NOT NULL,
                link_type TEXT DEFAULT 'primary',
                PRIMARY KEY(event_id, spatial_node_id),
                FOREIGN KEY(spatial_node_id) REFERENCES spatial_nodes(id)
            )
        """)

        self.conn.commit()

    def create_hierarchy(self, path: str) -> List[SpatialNode]:
        """
        Create hierarchical nodes for a path and store them.

        Args:
            path: File or directory path

        Returns:
            List of created SpatialNode objects
        """
        nodes = self.hierarchy.decompose_path(path)
        import time

        cursor = self.conn.cursor()
        created = []

        for node in nodes:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO spatial_nodes
                    (path, level, parent_path, node_type, is_leaf, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    node.path,
                    node.level,
                    node.parent_path,
                    node.node_type,
                    node.is_leaf,
                    int(time.time())
                ))

                # Get the ID
                cursor.execute("SELECT id FROM spatial_nodes WHERE path = ?", (node.path,))
                result = cursor.fetchone()
                if result:
                    node.id = result[0]
                    created.append(node)
            except sqlite3.IntegrityError:
                # Node already exists, fetch it
                cursor.execute("SELECT id FROM spatial_nodes WHERE path = ?", (node.path,))
                result = cursor.fetchone()
                if result:
                    node.id = result[0]
                    created.append(node)

        self.conn.commit()
        return created

    def get_node(self, path: str) -> Optional[SpatialNode]:
        """Get a spatial node by path."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, path, level, parent_path, node_type, is_leaf
            FROM spatial_nodes WHERE path = ?
        """, (path,))

        row = cursor.fetchone()
        if not row:
            return None

        return SpatialNode(
            id=row[0],
            path=row[1],
            level=row[2],
            parent_path=row[3],
            node_type=row[4],
            is_leaf=row[5]
        )

    def get_children(self, parent_path: str) -> List[SpatialNode]:
        """Get all direct children of a path."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, path, level, parent_path, node_type, is_leaf
            FROM spatial_nodes
            WHERE parent_path = ?
            ORDER BY level, path
        """, (parent_path,))

        nodes = []
        for row in cursor.fetchall():
            nodes.append(SpatialNode(
                id=row[0],
                path=row[1],
                level=row[2],
                parent_path=row[3],
                node_type=row[4],
                is_leaf=row[5]
            ))

        return nodes

    def get_descendants(self, parent_path: str) -> List[SpatialNode]:
        """Get all descendants of a path (recursive)."""
        cursor = self.conn.cursor()

        # Get all nodes under this path (by prefix matching)
        cursor.execute("""
            SELECT id, path, level, parent_path, node_type, is_leaf
            FROM spatial_nodes
            WHERE path LIKE ?
            ORDER BY level, path
        """, (parent_path + "%",))

        nodes = []
        for row in cursor.fetchall():
            # Exclude the parent itself
            if row[1] != parent_path:
                nodes.append(SpatialNode(
                    id=row[0],
                    path=row[1],
                    level=row[2],
                    parent_path=row[3],
                    node_type=row[4],
                    is_leaf=row[5]
                ))

        return nodes

    def link_event_to_spatial(self, event_id: int, path: str, link_type: str = "primary"):
        """
        Link an episodic event to spatial nodes in its path hierarchy.

        Args:
            event_id: ID of episodic event
            path: File or directory path
            link_type: Type of link ("primary", "secondary", etc.)
        """
        # Create hierarchy for this path
        nodes = self.create_hierarchy(path)

        cursor = self.conn.cursor()
        for node in nodes:
            if node.id:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO event_spatial_links
                        (event_id, spatial_node_id, link_type)
                        VALUES (?, ?, ?)
                    """, (event_id, node.id, link_type))
                except sqlite3.IntegrityError:
                    pass  # Already linked

        self.conn.commit()

    def get_events_in_spatial(self, path: str) -> List[int]:
        """
        Get all events in a spatial node (directory or file).

        Args:
            path: Directory or file path

        Returns:
            List of event IDs
        """
        node = self.get_node(path)
        if not node or not node.id:
            return []

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT event_id FROM event_spatial_links
            WHERE spatial_node_id = ?
            ORDER BY event_id DESC
        """, (node.id,))

        return [row[0] for row in cursor.fetchall()]

    def get_events_under_spatial(self, directory_path: str) -> List[int]:
        """
        Get all events under a directory (including subdirectories).

        Args:
            directory_path: Directory path

        Returns:
            List of event IDs
        """
        descendants = self.get_descendants(directory_path)
        node = self.get_node(directory_path)

        all_nodes = [node] if node else []
        all_nodes.extend(descendants)

        node_ids = [n.id for n in all_nodes if n and n.id]
        if not node_ids:
            return []

        cursor = self.conn.cursor()
        placeholders = ",".join("?" * len(node_ids))
        cursor.execute(f"""
            SELECT DISTINCT event_id FROM event_spatial_links
            WHERE spatial_node_id IN ({placeholders})
            ORDER BY event_id DESC
        """, node_ids)

        return [row[0] for row in cursor.fetchall()]

    def close(self):
        """Close database connection."""
        self.conn.close()


def main():
    """CLI interface for spatial hierarchy."""
    import argparse

    parser = argparse.ArgumentParser(description="Spatial Hierarchy Tool")
    parser.add_argument("--decompose", help="Decompose a path")
    parser.add_argument("--ancestors", help="Get ancestors of a path")
    parser.add_argument("--common", nargs=2, help="Find common ancestor")
    parser.add_argument("--is-under", nargs=2, help="Check if file is under directory")

    args = parser.parse_args()

    hierarchy = SpatialHierarchy()

    if args.decompose:
        nodes = hierarchy.decompose_path(args.decompose)
        print(f"Decomposing: {args.decompose}")
        for node in nodes:
            print(f"  Level {node.level}: {node.path} ({node.node_type})")

    elif args.ancestors:
        ancestors = hierarchy.get_ancestors(args.ancestors)
        print(f"Ancestors of {args.ancestors}:")
        for ancestor in ancestors:
            print(f"  - {ancestor}")

    elif args.common:
        common = hierarchy.get_common_ancestor(args.common[0], args.common[1])
        print(f"Common ancestor of:")
        print(f"  {args.common[0]}")
        print(f"  {args.common[1]}")
        print(f"Result: {common}")

    elif args.is_under:
        result = hierarchy.is_under_path(args.is_under[0], args.is_under[1])
        print(f"Is '{args.is_under[0]}' under '{args.is_under[1]}'? {result}")


if __name__ == "__main__":
    main()
