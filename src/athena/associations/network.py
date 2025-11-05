"""Association network for spreading activation.

Stores and manages associative links between memories across all layers.
Links represent semantic, temporal, causal, or similarity relationships.
"""

from datetime import datetime
from typing import List, Optional, Tuple

from ..core.database import Database
from .models import AssociationLink, LinkType, NetworkNode


class AssociationNetwork:
    """
    Manage associative links between memories.

    The association network stores bidirectional links between memories,
    enabling spreading activation retrieval. Links are weighted by strength
    (0.0-1.0) and can be of different types (semantic, temporal, causal, similarity).

    Link strength increases with co-occurrence and decreases over time without use.
    """

    def __init__(self, db: Database):
        """Initialize association network.

        Args:
            db: Database connection
        """
        self.db = db

    def create_link(
        self,
        project_id: int,
        from_memory_id: int,
        to_memory_id: int,
        from_layer: str,
        to_layer: str,
        link_type: LinkType = LinkType.SEMANTIC,
        initial_strength: float = 0.5,
    ) -> int:
        """Create a new associative link between two memories.

        If link already exists, increment co_occurrence_count instead.

        Args:
            project_id: Project ID
            from_memory_id: Source memory ID
            to_memory_id: Target memory ID
            from_layer: Source memory layer
            to_layer: Target memory layer
            link_type: Type of association (semantic/temporal/causal/similarity)
            initial_strength: Initial link strength (0.0-1.0)

        Returns:
            Link ID
        """
        if not 0.0 <= initial_strength <= 1.0:
            raise ValueError("Link strength must be between 0.0 and 1.0")

        if from_memory_id == to_memory_id and from_layer == to_layer:
            raise ValueError("Cannot create self-link")

        with self.db.get_connection() as conn:
            # Check if link already exists
            existing = conn.execute(
                """
                SELECT id, co_occurrence_count FROM association_links
                WHERE project_id = ?
                AND from_memory_id = ? AND to_memory_id = ?
                AND from_layer = ? AND to_layer = ?
                """,
                (project_id, from_memory_id, to_memory_id, from_layer, to_layer),
            ).fetchone()

            if existing:
                # Link exists, increment co-occurrence and strengthen
                link_id = existing["id"]
                new_count = existing["co_occurrence_count"] + 1
                conn.execute(
                    """
                    UPDATE association_links
                    SET co_occurrence_count = ?,
                        last_strengthened = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (new_count, link_id),
                )
                conn.commit()
                return link_id

            # Create new link
            cursor = conn.execute(
                """
                INSERT INTO association_links (
                    project_id, from_memory_id, to_memory_id,
                    from_layer, to_layer, link_strength,
                    link_type, co_occurrence_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    project_id,
                    from_memory_id,
                    to_memory_id,
                    from_layer,
                    to_layer,
                    initial_strength,
                    link_type.value,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def strengthen_link(self, link_id: int, amount: float = 0.1) -> float:
        """Strengthen an existing link.

        Increases link strength (capped at 1.0) and updates last_strengthened timestamp.

        Args:
            link_id: Link ID to strengthen
            amount: Amount to increase strength (default 0.1)

        Returns:
            New link strength

        Raises:
            ValueError: If link not found
        """
        if amount < 0:
            raise ValueError("Strengthen amount must be positive")

        with self.db.get_connection() as conn:
            # Get current strength
            result = conn.execute(
                "SELECT link_strength FROM association_links WHERE id = ?",
                (link_id,),
            ).fetchone()

            if not result:
                raise ValueError(f"Link {link_id} not found")

            current_strength = result["link_strength"]
            new_strength = min(1.0, current_strength + amount)

            conn.execute(
                """
                UPDATE association_links
                SET link_strength = ?,
                    last_strengthened = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (new_strength, link_id),
            )
            conn.commit()
            return new_strength

    def weaken_link(self, link_id: int, amount: float = 0.05) -> float:
        """Weaken an existing link.

        Decreases link strength (floored at 0.0). Links with strength < 0.1
        are considered inactive but not deleted.

        Args:
            link_id: Link ID to weaken
            amount: Amount to decrease strength (default 0.05)

        Returns:
            New link strength

        Raises:
            ValueError: If link not found
        """
        if amount < 0:
            raise ValueError("Weaken amount must be positive")

        with self.db.get_connection() as conn:
            result = conn.execute(
                "SELECT link_strength FROM association_links WHERE id = ?",
                (link_id,),
            ).fetchone()

            if not result:
                raise ValueError(f"Link {link_id} not found")

            current_strength = result["link_strength"]
            new_strength = max(0.0, current_strength - amount)

            conn.execute(
                "UPDATE association_links SET link_strength = ? WHERE id = ?",
                (new_strength, link_id),
            )
            conn.commit()
            return new_strength

    def get_neighbors(
        self,
        memory_id: int,
        layer: str,
        project_id: int,
        min_strength: float = 0.1,
        max_results: int = 20,
    ) -> List[AssociationLink]:
        """Get neighboring memories connected by associative links.

        Returns both outgoing and incoming links (bidirectional).

        Args:
            memory_id: Memory ID to find neighbors for
            layer: Memory layer
            project_id: Project ID
            min_strength: Minimum link strength threshold (default 0.1)
            max_results: Maximum number of neighbors to return (default 20)

        Returns:
            List of association links sorted by strength (descending)
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    id, project_id, from_memory_id, to_memory_id,
                    from_layer, to_layer, link_strength, co_occurrence_count,
                    created_at, last_strengthened, link_type
                FROM association_links
                WHERE project_id = ?
                AND link_strength >= ?
                AND (
                    (from_memory_id = ? AND from_layer = ?)
                    OR (to_memory_id = ? AND to_layer = ?)
                )
                ORDER BY link_strength DESC
                LIMIT ?
                """,
                (project_id, min_strength, memory_id, layer, memory_id, layer, max_results),
            )

            links = []
            for row in cursor.fetchall():
                links.append(
                    AssociationLink(
                        id=row["id"],
                        project_id=row["project_id"],
                        from_memory_id=row["from_memory_id"],
                        to_memory_id=row["to_memory_id"],
                        from_layer=row["from_layer"],
                        to_layer=row["to_layer"],
                        link_strength=row["link_strength"],
                        co_occurrence_count=row["co_occurrence_count"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        last_strengthened=datetime.fromisoformat(row["last_strengthened"]),
                        link_type=LinkType(row["link_type"]),
                    )
                )
            return links

    def find_path(
        self,
        from_memory_id: int,
        from_layer: str,
        to_memory_id: int,
        to_layer: str,
        project_id: int,
        max_depth: int = 5,
        min_strength: float = 0.1,
    ) -> Optional[List[AssociationLink]]:
        """Find shortest path between two memories using BFS.

        Args:
            from_memory_id: Source memory ID
            from_layer: Source memory layer
            to_memory_id: Target memory ID
            to_layer: Target memory layer
            project_id: Project ID
            max_depth: Maximum path length (default 5)
            min_strength: Minimum link strength threshold (default 0.1)

        Returns:
            List of links forming the path, or None if no path found
        """
        if from_memory_id == to_memory_id and from_layer == to_layer:
            return []  # Same node, path length 0

        # BFS to find shortest path
        visited = set()
        queue = [((from_memory_id, from_layer), [])]  # (node, path)

        while queue:
            (current_id, current_layer), path = queue.pop(0)

            if len(path) >= max_depth:
                continue

            if (current_id, current_layer) in visited:
                continue

            visited.add((current_id, current_layer))

            # Get neighbors
            neighbors = self.get_neighbors(
                current_id, current_layer, project_id, min_strength
            )

            for link in neighbors:
                # Determine next node (handle bidirectional links)
                if link.from_memory_id == current_id and link.from_layer == current_layer:
                    next_id = link.to_memory_id
                    next_layer = link.to_layer
                else:
                    next_id = link.from_memory_id
                    next_layer = link.from_layer

                new_path = path + [link]

                # Check if we reached target
                if next_id == to_memory_id and next_layer == to_layer:
                    return new_path

                # Add to queue if not visited
                if (next_id, next_layer) not in visited:
                    queue.append(((next_id, next_layer), new_path))

        return None  # No path found

    def get_link_count(self, project_id: int, min_strength: float = 0.1) -> int:
        """Get count of active links in the network.

        Args:
            project_id: Project ID
            min_strength: Minimum link strength threshold (default 0.1)

        Returns:
            Number of links with strength >= min_strength
        """
        with self.db.get_connection() as conn:
            result = conn.execute(
                """
                SELECT COUNT(*) as count FROM association_links
                WHERE project_id = ? AND link_strength >= ?
                """,
                (project_id, min_strength),
            ).fetchone()
            return result["count"] if result else 0

    def prune_weak_links(
        self, project_id: int, strength_threshold: float = 0.1
    ) -> int:
        """Remove links below strength threshold.

        Args:
            project_id: Project ID
            strength_threshold: Links below this strength are removed (default 0.1)

        Returns:
            Number of links pruned
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                DELETE FROM association_links
                WHERE project_id = ? AND link_strength < ?
                """,
                (project_id, strength_threshold),
            )
            conn.commit()
            return cursor.rowcount

    def decay_all_links(self, project_id: int, decay_rate: float = 0.05) -> int:
        """Apply decay to all links in the network.

        Simulates forgetting by weakening unused links over time.

        Args:
            project_id: Project ID
            decay_rate: Amount to decrease each link (default 0.05)

        Returns:
            Number of links decayed
        """
        if not 0.0 < decay_rate < 1.0:
            raise ValueError("Decay rate must be between 0.0 and 1.0")

        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE association_links
                SET link_strength = MAX(0.0, link_strength - ?)
                WHERE project_id = ?
                """,
                (decay_rate, project_id),
            )
            conn.commit()
            return cursor.rowcount
