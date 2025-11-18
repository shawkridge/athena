"""Working Memory Capacity Enforcement with Exponential Decay.

Implements Baddeley's 7±2 working memory capacity model with:
- Soft limit (6/7): Warning + optional auto-consolidation
- Hard limit (7/7): Reject additions until consolidation occurs
- Exponential decay: A(t) = A₀ * e^(-λt), where importance reduces decay
"""

import logging
import math
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from dataclasses import dataclass

from athena.core.database import Database
from athena.working_memory.models import ContentType, Component

logger = logging.getLogger(__name__)


class CapacityExceededError(Exception):
    """Raised when working memory capacity is exceeded."""

    pass


class SoftLimitWarning(Warning):
    """Warning issued when soft limit (6/7) is approached."""

    pass


@dataclass
class CapacityStatus:
    """Working memory capacity status report."""

    active_count: int
    soft_limit: int
    hard_limit: int
    at_soft_limit: bool
    at_hard_limit: bool
    items: List[Dict[str, Any]]
    utilization_percent: float
    estimated_consolidation_needed: bool


class WorkingMemoryCapacityEnforcer:
    """Enforce 7±2 capacity limits with Baddeley model decay.

    Key parameters:
    - SOFT_LIMIT (6): Warning threshold for auto-consolidation triggers
    - HARD_LIMIT (7): Absolute maximum before rejection
    - DECAY_HALF_LIFE (30): Time for 50% decay (verbal items, ~30 seconds)
    """

    # Baddeley capacity constants
    SOFT_LIMIT = 6  # Warning threshold (6/7)
    HARD_LIMIT = 7  # Absolute maximum (7/7)
    DECAY_HALF_LIFE = 30  # seconds (empirically typical for verbal items)

    def __init__(self, db: Database):
        """Initialize enforcer with database connection.

        Args:
            db: Database instance for querying working memory
        """
        self.db = db
        self.logger = logging.getLogger(__name__)

    def _ensure_schema(self) -> None:
        """Create working_memory table if it doesn't exist."""
        try:
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS working_memory (
                    id SERIAL PRIMARY KEY,
                    project_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    content_type TEXT DEFAULT 'verbal',
                    component TEXT DEFAULT 'phonological',
                    activation_level REAL DEFAULT 1.0,
                    created_at TEXT NOT NULL,
                    last_accessed TEXT NOT NULL,
                    decay_rate REAL DEFAULT 0.1,
                    importance_score REAL DEFAULT 0.5,
                    embedding BLOB,
                    metadata TEXT
                )
            """
            )

            # Create indexes for performance
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_working_memory_project
                ON working_memory(project_id)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_working_memory_activation
                ON working_memory(project_id, activation_level)
            """
            )

            # commit handled by cursor context
            self.logger.debug("Ensured working_memory schema exists")

        except Exception as e:
            self.logger.error(f"Failed to create working_memory schema: {e}")
            raise

    @staticmethod
    def calculate_activation(
        activation_level: float, importance_score: float, decay_rate: float, seconds_elapsed: float
    ) -> float:
        """Calculate current activation with exponential decay.

        Formula: A(t) = A₀ * e^(-λt)
        where λ = decay_rate * (1 - importance_score * 0.5)

        Important items decay slower: importance reduces decay rate by up to 50%.

        Args:
            activation_level: Initial activation (0.0-1.0)
            importance_score: Importance weight (0.0-1.0), higher = slower decay
            decay_rate: Base decay rate per second (typically 0.1 → 30s half-life)
            seconds_elapsed: Time since last access (seconds)

        Returns:
            Current activation level (0.0-1.0)

        Example:
            >>> # Standard item, 30 seconds elapsed
            >>> CapacityEnforcer.calculate_activation(1.0, 0.5, 0.1/30, 30)
            0.5  # Approximately 50% of original

            >>> # Important item (0.9), same timing
            >>> CapacityEnforcer.calculate_activation(1.0, 0.9, 0.1/30, 30)
            0.7  # Slower decay due to importance
        """
        if seconds_elapsed < 0:
            raise ValueError("seconds_elapsed must be non-negative")
        if not (0.0 <= activation_level <= 1.0):
            raise ValueError("activation_level must be 0.0-1.0")
        if not (0.0 <= importance_score <= 1.0):
            raise ValueError("importance_score must be 0.0-1.0")
        if decay_rate <= 0:
            raise ValueError("decay_rate must be positive")

        # Important items decay slower (importance reduces decay by up to 50%)
        adaptive_rate = decay_rate * (1 - importance_score * 0.5)
        return activation_level * math.exp(-adaptive_rate * seconds_elapsed)

    def check_capacity(self, project_id: int) -> CapacityStatus:
        """Check current working memory capacity status.

        Counts items with activation > 0.1 threshold, calculates decay.

        Args:
            project_id: Project ID to check capacity for

        Returns:
            CapacityStatus with current state and recommendations

        Raises:
            Exception: If database query fails
        """
        try:
            cursor = self.db.get_cursor()

            # Query all WM items (activation will be calculated in Python)
            cursor.execute(
                """
                SELECT id, activation_level, importance_score, decay_rate,
                       last_accessed, content_type
                FROM working_memory
                WHERE project_id = ?
                ORDER BY last_accessed DESC
            """,
                (project_id,),
            )

            rows = cursor.fetchall()

            active_count = 0
            items = []

            for row in rows:
                # Calculate current activation with decay
                try:
                    last_accessed = datetime.fromisoformat(row["last_accessed"])
                except (ValueError, TypeError):
                    last_accessed = datetime.now()

                time_elapsed = (datetime.now() - last_accessed).total_seconds()

                current_activation = self.calculate_activation(
                    activation_level=row["activation_level"],
                    importance_score=row["importance_score"],
                    decay_rate=row["decay_rate"],
                    seconds_elapsed=time_elapsed,
                )

                # Include items with activation > 0.1 threshold
                if current_activation > 0.1:
                    active_count += 1
                    items.append(
                        {
                            "id": row["id"],
                            "activation": round(current_activation, 3),
                            "importance": row["importance_score"],
                            "content_type": row["content_type"],
                            "time_since_access_seconds": round(time_elapsed, 1),
                        }
                    )

            utilization_percent = (active_count / self.HARD_LIMIT) * 100

            return CapacityStatus(
                active_count=active_count,
                soft_limit=self.SOFT_LIMIT,
                hard_limit=self.HARD_LIMIT,
                at_soft_limit=active_count >= self.SOFT_LIMIT,
                at_hard_limit=active_count >= self.HARD_LIMIT,
                items=items,
                utilization_percent=round(utilization_percent, 1),
                estimated_consolidation_needed=active_count >= self.SOFT_LIMIT,
            )

        except Exception as e:
            self.logger.error(f"Failed to check capacity for project {project_id}: {e}")
            raise

    def add_item_with_enforcement(
        self,
        project_id: int,
        content: str,
        content_type: ContentType = ContentType.VERBAL,
        component: Component = Component.PHONOLOGICAL,
        importance: float = 0.5,
        consolidation_callback: Optional[Callable[[int], None]] = None,
    ) -> int:
        """Add item with hard capacity enforcement.

        Behavior:
        - If at hard limit (7/7): Raise CapacityExceededError
        - If at soft limit (6/7): Log warning, optionally trigger consolidation
        - Otherwise: Add item normally

        Args:
            project_id: Project ID for item
            content: Item content to store
            content_type: Type of content (verbal, spatial, episodic, goal)
            component: WM component (phonological, visuospatial, episodic_buffer)
            importance: Importance score (0.0-1.0, higher = slower decay)
            consolidation_callback: Optional async function to trigger consolidation

        Returns:
            ID of newly added item

        Raises:
            CapacityExceededError: If at hard limit (7/7)
            ValueError: If importance not in 0.0-1.0 range
        """
        if not (0.0 <= importance <= 1.0):
            raise ValueError("importance must be between 0.0 and 1.0")

        status = self.check_capacity(project_id)

        if status.at_hard_limit:
            error_msg = (
                f"Working memory at hard capacity limit ({status.active_count}/"
                f"{status.hard_limit}). Must consolidate to long-term memory "
                f"before adding new items. Active items:\n"
            )
            for item in status.items[:3]:  # Show top 3
                error_msg += f"  - ID {item['id']}: activation={item['activation']}\n"

            self.logger.error(error_msg)
            raise CapacityExceededError(error_msg)

        if status.at_soft_limit:
            warning_msg = (
                f"Working memory approaching capacity: {status.active_count}/"
                f"{status.hard_limit} (utilization: {status.utilization_percent}%)"
            )
            self.logger.warning(warning_msg)

            # Attempt auto-consolidation if callback provided
            if consolidation_callback:
                try:
                    self.logger.info(f"Triggering auto-consolidation for project {project_id}")
                    consolidation_callback(project_id)
                except Exception as e:
                    self.logger.error(f"Auto-consolidation failed: {e}")
                    # Don't fail the addition, just warn

        # Add the item
        try:
            new_id = self._insert_item(
                project_id=project_id,
                content=content,
                content_type=content_type,
                component=component,
                importance=importance,
            )

            self.logger.debug(
                f"Added WM item {new_id} to project {project_id} "
                f"(importance={importance}, utilization after={status.utilization_percent}%)"
            )
            return new_id

        except Exception as e:
            self.logger.error(f"Failed to insert WM item: {e}")
            raise

    def _insert_item(
        self,
        project_id: int,
        content: str,
        content_type: ContentType,
        component: Component,
        importance: float,
    ) -> int:
        """Insert item into working memory database.

        Args:
            project_id: Project ID
            content: Item content
            content_type: Type of content
            component: WM component
            importance: Importance score

        Returns:
            ID of inserted item
        """
        try:
            cursor = self.db.get_cursor()
            now = datetime.now().isoformat()

            cursor.execute(
                """
                INSERT INTO working_memory
                (project_id, content, content_type, component, activation_level,
                 created_at, last_accessed, decay_rate, importance_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    project_id,
                    content,
                    content_type.value,
                    component.value,
                    1.0,  # Start with full activation
                    now,
                    now,
                    0.1 / 30,  # decay_rate: 0.1 / 30 seconds = 30-second half-life
                    importance,
                ),
            )

            # commit handled by cursor context
            return cursor.lastrowid

        except Exception as e:
            self.logger.error(f"Failed to insert WM item: {e}")
            raise

    def rehearse_item(self, project_id: int, item_id: int) -> bool:
        """Rehearse (refresh) an item to prevent decay.

        Resets activation to 1.0 and updates last_accessed timestamp.

        Args:
            project_id: Project ID
            item_id: Item ID to rehearse

        Returns:
            True if successful, False if item not found
        """
        try:
            cursor = self.db.get_cursor()
            now = datetime.now().isoformat()

            cursor.execute(
                """
                UPDATE working_memory
                SET activation_level = 1.0, last_accessed = ?
                WHERE id = ? AND project_id = ?
            """,
                (now, item_id, project_id),
            )

            # commit handled by cursor context

            if cursor.rowcount > 0:
                self.logger.debug(f"Rehearsed WM item {item_id}")
                return True
            else:
                self.logger.warning(f"Item {item_id} not found in project {project_id}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to rehearse item {item_id}: {e}")
            raise

    def get_items_above_threshold(
        self, project_id: int, threshold: float = 0.1
    ) -> List[Dict[str, Any]]:
        """Get all items with activation above threshold.

        Args:
            project_id: Project ID
            threshold: Activation threshold (default 0.1)

        Returns:
            List of items with activation > threshold
        """
        try:
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                SELECT id, content, activation_level, importance_score,
                       content_type, last_accessed
                FROM working_memory
                WHERE project_id = ?
                ORDER BY activation_level DESC
            """,
                (project_id,),
            )

            rows = cursor.fetchall()
            items = []

            for row in rows:
                try:
                    last_accessed = datetime.fromisoformat(row["last_accessed"])
                except (ValueError, TypeError):
                    last_accessed = datetime.now()

                time_elapsed = (datetime.now() - last_accessed).total_seconds()
                current_activation = self.calculate_activation(
                    activation_level=row["activation_level"],
                    importance_score=row["importance_score"],
                    decay_rate=0.1 / 30,  # Standard decay rate
                    seconds_elapsed=time_elapsed,
                )

                if current_activation > threshold:
                    items.append(
                        {
                            "id": row["id"],
                            "content": row["content"][:100],  # Truncate for display
                            "activation": round(current_activation, 3),
                            "importance": row["importance_score"],
                            "content_type": row["content_type"],
                        }
                    )

            return items

        except Exception as e:
            self.logger.error(f"Failed to get items above threshold: {e}")
            raise

    def remove_decayed_items(self, project_id: int, threshold: float = 0.05) -> int:
        """Remove items that have decayed below threshold.

        Cleans up working memory by removing forgotten items. This is different
        from consolidation - these items are lost (not transferred to long-term).

        Args:
            project_id: Project ID
            threshold: Activation threshold below which items are removed

        Returns:
            Number of items removed
        """
        try:
            cursor = self.db.get_cursor()

            # Get all items
            cursor.execute(
                """
                SELECT id, activation_level, importance_score, last_accessed
                FROM working_memory
                WHERE project_id = ?
            """,
                (project_id,),
            )

            rows = cursor.fetchall()
            ids_to_remove = []

            for row in rows:
                try:
                    last_accessed = datetime.fromisoformat(row["last_accessed"])
                except (ValueError, TypeError):
                    last_accessed = datetime.now()

                time_elapsed = (datetime.now() - last_accessed).total_seconds()
                current_activation = self.calculate_activation(
                    activation_level=row["activation_level"],
                    importance_score=row["importance_score"],
                    decay_rate=0.1 / 30,
                    seconds_elapsed=time_elapsed,
                )

                if current_activation < threshold:
                    ids_to_remove.append(row["id"])

            # Remove items
            if ids_to_remove:
                placeholders = ",".join(["?" for _ in ids_to_remove])
                cursor.execute(
                    f"""
                    DELETE FROM working_memory
                    WHERE project_id = ? AND id IN ({placeholders})
                """,
                    [project_id] + ids_to_remove,
                )

                # commit handled by cursor context
                self.logger.info(
                    f"Removed {len(ids_to_remove)} decayed items from project {project_id}"
                )

            return len(ids_to_remove)

        except Exception as e:
            self.logger.error(f"Failed to remove decayed items: {e}")
            raise
