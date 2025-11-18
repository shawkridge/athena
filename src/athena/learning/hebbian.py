"""Hebbian learning for automatic association strengthening.

"Neurons that fire together, wire together" - Donald Hebb (1949)

Automatically strengthens associations between memories that are accessed
together or within a short time window.
"""

from datetime import datetime, timedelta
from typing import List, Tuple

from ..core.database import Database
from ..associations.network import AssociationNetwork
from ..associations.models import LinkType
from .models import AccessRecord, HebbianStats


class HebbianLearner:
    """
    Automatic association learning through co-occurrence detection.

    Learning Rules:
    1. Co-occurrence window: 5-60 seconds
    2. Strength update: Δw = η × (a_pre × a_post) × (1 - w)
       where η = learning rate (default 0.1)
             a_pre = activation of first memory
             a_post = activation of second memory
             w = current link strength
    3. Asymmetric strengthening: A→B stronger than B→A if A accessed first
    4. Unused links decay over time
    """

    def __init__(
        self,
        db: Database,
        network: AssociationNetwork,
        learning_rate: float = 0.1,
        window_seconds: int = 60,
    ):
        """Initialize Hebbian learner.

        Args:
            db: Database connection
            network: Association network for link management
            learning_rate: Learning rate η (default 0.1)
            window_seconds: Co-occurrence window in seconds (default 60)
        """
        self.db = db
        self.network = network
        self.learning_rate = learning_rate
        self.window_seconds = window_seconds

        if not 0.0 < learning_rate <= 1.0:
            raise ValueError("learning_rate must be between 0.0 and 1.0")

        if window_seconds < 0:
            raise ValueError("window_seconds must be non-negative")

    def log_access(
        self,
        memory_id: int,
        layer: str,
        project_id: int,
        activation_level: float = 1.0,
    ) -> int:
        """Log memory access for co-occurrence detection.

        Args:
            memory_id: Memory ID accessed
            layer: Memory layer
            project_id: Project ID
            activation_level: Current activation (default 1.0)

        Returns:
            Access record ID
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO memory_access_log (
                    project_id, memory_id, memory_layer, activation_level
                )
                VALUES (?, ?, ?, ?)
                """,
                (project_id, memory_id, layer, activation_level),
            )
            conn.commit()
            return cursor.lastrowid

    def detect_and_strengthen(self, project_id: int) -> int:
        """Detect co-occurring accesses and strengthen associations.

        Looks for memory accesses within the co-occurrence window and
        applies Hebbian learning to strengthen associations.

        Args:
            project_id: Project ID

        Returns:
            Number of associations strengthened/created
        """
        # Get recent accesses within window
        accesses = self._get_recent_accesses(project_id)

        if len(accesses) < 2:
            return 0  # Need at least 2 accesses to form association

        strengthened_count = 0

        # Process each pair of accesses
        for i, access_pre in enumerate(accesses):
            for access_post in accesses[i + 1 :]:
                # Calculate time difference
                time_diff = (access_post.accessed_at - access_pre.accessed_at).total_seconds()

                if time_diff > self.window_seconds:
                    break  # Outside co-occurrence window

                # Skip self-associations
                if (
                    access_pre.memory_id == access_post.memory_id
                    and access_pre.memory_layer == access_post.memory_layer
                ):
                    continue

                # Apply Hebbian learning
                self._strengthen_association(
                    project_id=project_id,
                    memory_pre=(access_pre.memory_id, access_pre.memory_layer),
                    memory_post=(access_post.memory_id, access_post.memory_layer),
                    activation_pre=access_pre.activation_level,
                    activation_post=access_post.activation_level,
                    time_diff=time_diff,
                )
                strengthened_count += 1

        # Update stats
        self._update_stats(project_id, len(accesses), strengthened_count)

        return strengthened_count

    def apply_decay(self, project_id: int, decay_rate: float = 0.05) -> int:
        """Apply decay to unused links.

        Links that haven't been strengthened recently gradually weaken.

        Args:
            project_id: Project ID
            decay_rate: Decay rate (default 0.05)

        Returns:
            Number of links decayed
        """
        return self.network.decay_all_links(project_id, decay_rate)

    def get_stats(self, project_id: int) -> HebbianStats:
        """Get learning statistics for a project.

        Args:
            project_id: Project ID

        Returns:
            Hebbian learning statistics
        """
        with self.db.get_connection() as conn:
            result = conn.execute(
                """
                SELECT
                    id, project_id, total_accesses, links_created,
                    links_strengthened, links_weakened, avg_link_strength,
                    last_learning_at
                FROM hebbian_stats
                WHERE project_id = ?
                ORDER BY last_learning_at DESC
                LIMIT 1
                """,
                (project_id,),
            ).fetchone()

            if not result:
                # Initialize stats
                cursor = conn.execute(
                    """
                    INSERT INTO hebbian_stats (
                        project_id, total_accesses, links_created,
                        links_strengthened, links_weakened, avg_link_strength
                    )
                    VALUES (?, 0, 0, 0, 0, 0.0)
                    """,
                    (project_id,),
                )
                conn.commit()

                return HebbianStats(
                    id=cursor.lastrowid,
                    project_id=project_id,
                    total_accesses=0,
                    links_created=0,
                    links_strengthened=0,
                    links_weakened=0,
                    avg_link_strength=0.0,
                    last_learning_at=datetime.now(),
                )

            return HebbianStats(
                id=result["id"],
                project_id=result["project_id"],
                total_accesses=result["total_accesses"],
                links_created=result["links_created"],
                links_strengthened=result["links_strengthened"],
                links_weakened=result["links_weakened"],
                avg_link_strength=result["avg_link_strength"],
                last_learning_at=datetime.fromisoformat(result["last_learning_at"]),
            )

    def clear_old_accesses(self, project_id: int, days: int = 7) -> int:
        """Clear access logs older than specified days.

        Args:
            project_id: Project ID
            days: Age threshold in days (default 7)

        Returns:
            Number of access records cleared
        """
        from datetime import timezone

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                DELETE FROM memory_access_log
                WHERE project_id = ? AND accessed_at < ?
                """,
                (project_id, cutoff.isoformat()),
            )
            conn.commit()
            return cursor.rowcount

    def _get_recent_accesses(self, project_id: int, limit: int = 100) -> List[AccessRecord]:
        """Get recent memory accesses within co-occurrence window.

        Args:
            project_id: Project ID
            limit: Maximum number of accesses to retrieve (default 100)

        Returns:
            List of access records sorted by time (ascending)
        """
        from datetime import timezone

        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.window_seconds)
        # Normalize to SQLite format (space instead of T, no timezone)
        cutoff_str = cutoff.isoformat().replace("T", " ").split("+")[0]

        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, project_id, memory_id, memory_layer,
                       accessed_at, activation_level
                FROM memory_access_log
                WHERE project_id = ? AND accessed_at >= ?
                ORDER BY accessed_at ASC
                LIMIT ?
                """,
                (project_id, cutoff_str, limit),
            )

            accesses = []
            for row in cursor.fetchall():
                accesses.append(
                    AccessRecord(
                        id=row["id"],
                        project_id=row["project_id"],
                        memory_id=row["memory_id"],
                        memory_layer=row["memory_layer"],
                        accessed_at=datetime.fromisoformat(row["accessed_at"]),
                        activation_level=row["activation_level"],
                    )
                )
            return accesses

    def _strengthen_association(
        self,
        project_id: int,
        memory_pre: Tuple[int, str],
        memory_post: Tuple[int, str],
        activation_pre: float,
        activation_post: float,
        time_diff: float,
    ) -> None:
        """Apply Hebbian learning to strengthen association.

        Δw = η × (a_pre × a_post) × (1 - w) × temporal_factor

        Args:
            project_id: Project ID
            memory_pre: (memory_id, layer) of first access
            memory_post: (memory_id, layer) of second access
            activation_pre: Activation of first memory
            activation_post: Activation of second memory
            time_diff: Time difference in seconds
        """
        # Calculate temporal decay factor (closer in time = stronger)
        # Decays from 1.0 at 0 seconds to 0.5 at window_seconds
        temporal_factor = 1.0 - (time_diff / self.window_seconds) * 0.5

        # Get or create link (A → B direction, asymmetric)
        with self.db.get_connection() as conn:
            existing = conn.execute(
                """
                SELECT id, link_strength FROM association_links
                WHERE project_id = ?
                AND from_memory_id = ? AND from_layer = ?
                AND to_memory_id = ? AND to_layer = ?
                """,
                (
                    project_id,
                    memory_pre[0],
                    memory_pre[1],
                    memory_post[0],
                    memory_post[1],
                ),
            ).fetchone()

            if existing:
                # Strengthen existing link
                current_strength = existing["link_strength"]
                delta_w = (
                    self.learning_rate
                    * activation_pre
                    * activation_post
                    * (1.0 - current_strength)
                    * temporal_factor
                )
                new_strength = min(1.0, current_strength + delta_w)

                conn.execute(
                    """
                    UPDATE association_links
                    SET link_strength = ?,
                        co_occurrence_count = co_occurrence_count + 1,
                        last_strengthened = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (new_strength, existing["id"]),
                )
            else:
                # Create new link
                initial_strength = (
                    self.learning_rate * activation_pre * activation_post * temporal_factor
                )
                self.network.create_link(
                    project_id=project_id,
                    from_memory_id=memory_pre[0],
                    to_memory_id=memory_post[0],
                    from_layer=memory_pre[1],
                    to_layer=memory_post[1],
                    link_type=LinkType.TEMPORAL,
                    initial_strength=initial_strength,
                )

            conn.commit()

    def _update_stats(self, project_id: int, access_count: int, strengthened_count: int) -> None:
        """Update Hebbian learning statistics.

        Args:
            project_id: Project ID
            access_count: Number of accesses processed
            strengthened_count: Number of associations strengthened
        """
        with self.db.get_connection() as conn:
            # Calculate average link strength
            avg_result = conn.execute(
                """
                SELECT AVG(link_strength) as avg FROM association_links
                WHERE project_id = ?
                """,
                (project_id,),
            ).fetchone()
            avg_strength = avg_result["avg"] if avg_result["avg"] else 0.0

            # Check if stats exist
            existing = conn.execute(
                """
                SELECT id FROM hebbian_stats
                WHERE project_id = ?
                LIMIT 1
                """,
                (project_id,),
            ).fetchone()

            if existing:
                # Update existing stats
                conn.execute(
                    """
                    UPDATE hebbian_stats
                    SET total_accesses = total_accesses + ?,
                        links_strengthened = links_strengthened + ?,
                        avg_link_strength = ?,
                        last_learning_at = CURRENT_TIMESTAMP
                    WHERE project_id = ?
                    """,
                    (access_count, strengthened_count, avg_strength, project_id),
                )
            else:
                # Insert new stats
                conn.execute(
                    """
                    INSERT INTO hebbian_stats (
                        project_id, total_accesses, links_strengthened,
                        avg_link_strength, last_learning_at
                    )
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (project_id, access_count, strengthened_count, avg_strength),
                )
            conn.commit()
