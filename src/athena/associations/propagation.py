"""Activation propagation for spreading activation network.

Implements spreading activation algorithm where activation flows from
source nodes through associative links, decaying with distance.
"""

from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple

from ..core.database import Database
from .models import ActivatedNode
from .network import AssociationNetwork


class ActivationPropagation:
    """
    Spread activation through the association network.

    Activation starts at source nodes and spreads to connected nodes,
    decaying with each hop. Multiple activation sources sum together.

    Algorithm:
    1. Set source nodes to activation = 1.0
    2. For each hop (up to max_hops):
       - For each active node, spread activation to neighbors
       - New activation = current × link_strength × decay_factor
       - Sum activations if node already active
    3. Filter nodes below activation threshold
    4. Return activated nodes sorted by activation level
    """

    def __init__(self, db: Database, network: AssociationNetwork):
        """Initialize activation propagation.

        Args:
            db: Database connection
            network: Association network for link traversal
        """
        self.db = db
        self.network = network

    def propagate(
        self,
        source_memory_id: int,
        source_layer: str,
        project_id: int,
        max_hops: int = 3,
        decay_factor: float = 0.7,
        min_activation: float = 0.1,
    ) -> List[ActivatedNode]:
        """Propagate activation from a single source node.

        Args:
            source_memory_id: Source memory ID
            source_layer: Source memory layer
            project_id: Project ID
            max_hops: Maximum propagation distance (default 3)
            decay_factor: Activation decay per hop (default 0.7)
            min_activation: Minimum activation threshold (default 0.1)

        Returns:
            List of activated nodes sorted by activation level (descending)
        """
        return self.multi_source_propagate(
            source_ids=[(source_memory_id, source_layer)],
            source_weights=[1.0],
            project_id=project_id,
            max_hops=max_hops,
            decay_factor=decay_factor,
            min_activation=min_activation,
        )

    def multi_source_propagate(
        self,
        source_ids: List[Tuple[int, str]],
        source_weights: List[float],
        project_id: int,
        max_hops: int = 3,
        decay_factor: float = 0.7,
        min_activation: float = 0.1,
    ) -> List[ActivatedNode]:
        """Propagate activation from multiple source nodes.

        Activations from different sources sum together at shared nodes.

        Args:
            source_ids: List of (memory_id, layer) tuples
            source_weights: Initial activation weights for each source
            project_id: Project ID
            max_hops: Maximum propagation distance (default 3)
            decay_factor: Activation decay per hop (default 0.7)
            min_activation: Minimum activation threshold (default 0.1)

        Returns:
            List of activated nodes sorted by activation level (descending)
        """
        if len(source_ids) != len(source_weights):
            raise ValueError("source_ids and source_weights must have same length")

        if not 0.0 < decay_factor <= 1.0:
            raise ValueError("decay_factor must be between 0.0 and 1.0")

        if not 0.0 <= min_activation <= 1.0:
            raise ValueError("min_activation must be between 0.0 and 1.0")

        # Initialize activation levels: {(memory_id, layer): (activation, hop_distance)}
        activations: Dict[Tuple[int, str], Tuple[float, int]] = {}
        for (mem_id, layer), weight in zip(source_ids, source_weights):
            activations[(mem_id, layer)] = (weight, 0)

        # Track nodes to process at each hop
        current_wave = source_ids.copy()

        # Propagate for max_hops
        for hop in range(max_hops):
            next_wave = []

            for memory_id, layer in current_wave:
                current_activation, current_hop = activations[(memory_id, layer)]

                # Get neighbors
                neighbors = self.network.get_neighbors(
                    memory_id=memory_id,
                    layer=layer,
                    project_id=project_id,
                    min_strength=0.1,
                    max_results=50,  # Limit to prevent explosion
                )

                # Propagate to each neighbor
                for link in neighbors:
                    # Determine target node (handle bidirectional)
                    if link.from_memory_id == memory_id and link.from_layer == layer:
                        target_id = link.to_memory_id
                        target_layer = link.to_layer
                    else:
                        target_id = link.from_memory_id
                        target_layer = link.from_layer

                    # Calculate activation transfer
                    transferred = (
                        current_activation * link.link_strength * decay_factor
                    )

                    # Skip if below threshold
                    if transferred < min_activation:
                        continue

                    target_key = (target_id, target_layer)

                    # Sum activations if node already active, otherwise set
                    if target_key in activations:
                        existing_activation, existing_hop = activations[target_key]
                        # Sum activations, keep minimum hop distance
                        new_activation = existing_activation + transferred
                        new_hop = min(existing_hop, hop + 1)
                        activations[target_key] = (new_activation, new_hop)
                    else:
                        activations[target_key] = (transferred, hop + 1)
                        next_wave.append(target_key)

            current_wave = next_wave

            # Stop if no more nodes to process
            if not current_wave:
                break

        # Store activation state in database for debugging/inspection
        self._store_activation_state(activations, project_id)

        # Convert to ActivatedNode objects and sort
        nodes = []
        for (memory_id, layer), (activation, hop) in activations.items():
            if activation >= min_activation:
                nodes.append(
                    ActivatedNode(
                        memory_id=memory_id,
                        memory_layer=layer,
                        activation_level=min(1.0, activation),  # Cap at 1.0
                        hop_distance=hop,
                    )
                )

        # Sort by activation level (descending)
        nodes.sort(key=lambda n: n.activation_level, reverse=True)
        return nodes

    def get_activation_level(
        self, memory_id: int, layer: str, project_id: int
    ) -> float:
        """Get current activation level for a memory.

        Args:
            memory_id: Memory ID
            layer: Memory layer
            project_id: Project ID

        Returns:
            Current activation level (0.0-1.0)
        """
        with self.db.get_connection() as conn:
            result = conn.execute(
                """
                SELECT activation_level FROM activation_state
                WHERE project_id = ? AND memory_id = ? AND memory_layer = ?
                ORDER BY activated_at DESC
                LIMIT 1
                """,
                (project_id, memory_id, layer),
            ).fetchone()

            return result["activation_level"] if result else 0.0

    def decay_all_activations(self, project_id: int, decay_rate: float = 0.1) -> int:
        """Apply decay to all current activations.

        Simulates activation decay over time. Activations below 0.1 are removed.

        Args:
            project_id: Project ID
            decay_rate: Amount to decrease each activation (default 0.1)

        Returns:
            Number of activations decayed
        """
        if not 0.0 < decay_rate < 1.0:
            raise ValueError("decay_rate must be between 0.0 and 1.0")

        with self.db.get_connection() as conn:
            # Decay activations
            decay_cursor = conn.execute(
                """
                UPDATE activation_state
                SET activation_level = MAX(0.0, activation_level - ?)
                WHERE project_id = ?
                """,
                (decay_rate, project_id),
            )
            decay_count = decay_cursor.rowcount

            # Remove activations below threshold
            delete_cursor = conn.execute(
                """
                DELETE FROM activation_state
                WHERE project_id = ? AND activation_level < 0.1
                """,
                (project_id,),
            )
            delete_count = delete_cursor.rowcount
            conn.commit()

            # Return total count of affected rows (updated + deleted)
            return decay_count + delete_count

    def clear_activations(self, project_id: int) -> int:
        """Clear all activation state for a project.

        Args:
            project_id: Project ID

        Returns:
            Number of activations cleared
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM activation_state WHERE project_id = ?",
                (project_id,),
            )
            conn.commit()
            return cursor.rowcount

    def get_top_activated(
        self, project_id: int, limit: int = 20, min_activation: float = 0.1
    ) -> List[ActivatedNode]:
        """Get most activated memories in the network.

        Args:
            project_id: Project ID
            limit: Maximum number of results (default 20)
            min_activation: Minimum activation threshold (default 0.1)

        Returns:
            List of activated nodes sorted by activation level (descending)
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    memory_id, memory_layer, activation_level,
                    hop_distance, source_activation_id
                FROM activation_state
                WHERE project_id = ? AND activation_level >= ?
                ORDER BY activation_level DESC
                LIMIT ?
                """,
                (project_id, min_activation, limit),
            )

            nodes = []
            for row in cursor.fetchall():
                nodes.append(
                    ActivatedNode(
                        memory_id=row["memory_id"],
                        memory_layer=row["memory_layer"],
                        activation_level=row["activation_level"],
                        hop_distance=row["hop_distance"],
                        source_activation_id=row["source_activation_id"],
                    )
                )
            return nodes

    def _store_activation_state(
        self,
        activations: Dict[Tuple[int, str], Tuple[float, int]],
        project_id: int,
    ) -> None:
        """Store activation state in database.

        Args:
            activations: Dict of {(memory_id, layer): (activation, hop_distance)}
            project_id: Project ID
        """
        with self.db.get_connection() as conn:
            # Clear old activations first
            conn.execute(
                "DELETE FROM activation_state WHERE project_id = ?",
                (project_id,),
            )

            # Insert new activations
            for (memory_id, layer), (activation, hop) in activations.items():
                conn.execute(
                    """
                    INSERT INTO activation_state (
                        project_id, memory_id, memory_layer,
                        activation_level, hop_distance, activated_at
                    )
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (project_id, memory_id, layer, activation, hop),
                )
            conn.commit()
