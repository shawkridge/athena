"""
Central Executive: Attention control and goal management.

Responsibilities:
- Manage active goals (create, suspend, resume, complete)
- Allocate attention to working memory components
- Monitor capacity constraints (7±2 items - Miller's law)
- Decide when to consolidate to long-term memory
- Coordinate between phonological loop, visuospatial sketchpad, and episodic buffer
"""

from typing import List, Optional, Union, Any
from datetime import datetime, timedelta
import json

from ..core.database import Database
from ..core.embeddings import EmbeddingModel
from .models import Goal, GoalType, GoalStatus, WorkingMemoryItem, Component
from .saliency import SaliencyCalculator, saliency_to_focus_type, saliency_to_recommendation


class CentralExecutive:
    """
    Central Executive component of Baddeley's Working Memory model.

    Controls attention and manages goals across the cognitive system.
    """

    def __init__(self, db: Any, embedder: EmbeddingModel):
        # Accept either Database instance (SQLite or Postgres) or path string
        if isinstance(db, str):
            self.db = Database(db)
        else:
            # Already a database object (SQLite or Postgres)
            self.db = db
        self.embedder = embedder
        self.max_wm_capacity = 7  # Miller's law: 7±2 items
        # Initialize saliency calculator for auto-focus
        self.saliency_calc = SaliencyCalculator(self.db)
        self._init_schema()

    def _init_schema(self):
        """Ensure schema exists (for testing/standalone use)."""
        # For PostgreSQL async databases, skip sync schema initialization
        if not hasattr(self.db, 'conn'):
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"CentralExecutive: PostgreSQL async database detected. Schema management handled by _init_schema().")
            return

        # Schema should already exist from migration, but create if needed for tests
        with self.db.conn:
            # Check if active_goals table exists
            result = self.db.conn.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='active_goals'
            """).fetchone()

            if not result:
                # Create table for testing/standalone use
                self.db.conn.execute("""
                    CREATE TABLE IF NOT EXISTS active_goals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id INTEGER NOT NULL,
                        goal_text TEXT NOT NULL,
                        goal_type TEXT NOT NULL DEFAULT 'primary',
                        parent_goal_id INTEGER,
                        status TEXT NOT NULL DEFAULT 'active',
                        priority INTEGER DEFAULT 5,
                        deadline TIMESTAMP,
                        completion_criteria TEXT,
                        metadata JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (project_id) REFERENCES projects (id),
                        FOREIGN KEY (parent_goal_id) REFERENCES active_goals (id)
                    )
                """)
                # commit handled by cursor context

    # ========================================================================
    # Goal Management
    # ========================================================================

    def set_goal(
        self,
        project_id: int,
        goal_text: str,
        goal_type: GoalType | str = "primary",
        parent_goal_id: Optional[int] = None,
        priority: int = 5,
        deadline: Optional[datetime] = None,
        completion_criteria: Optional[str] = None
    ) -> Goal:
        """
        Set a new active goal.

        Args:
            project_id: Project identifier
            goal_text: Description of the goal
            goal_type: PRIMARY, SUBGOAL, or MAINTENANCE (enum or string)
            parent_goal_id: Parent goal ID for hierarchical goals
            priority: Priority (1-10, higher = more important)
            deadline: Optional deadline
            completion_criteria: Optional success criteria

        Returns:
            Created Goal object
        """
        # Convert goal_type to string if it's an enum
        goal_type_str = goal_type.value if isinstance(goal_type, GoalType) else goal_type

        with self.db.conn:
            cursor = self.db.conn.execute("""
                INSERT INTO active_goals
                (project_id, goal_text, goal_type, parent_goal_id, priority,
                 deadline, completion_criteria, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project_id,
                goal_text,
                goal_type_str,
                parent_goal_id,
                priority,
                deadline.isoformat() if deadline else None,
                completion_criteria,
                json.dumps({})
            ))

            goal_id = cursor.lastrowid

            # Fetch created goal
            return self.get_goal(goal_id)

    def get_goal(self, goal_id: int) -> Goal:
        """Get goal by ID."""
        with self.db.conn:
            row = self.db.conn.execute("""
                SELECT * FROM active_goals WHERE id = ?
            """, (goal_id,)).fetchone()

            if not row:
                raise ValueError(f"Goal {goal_id} not found")

            return self._row_to_goal(row)

    def get_active_goals(
        self,
        project_id: int,
        include_subgoals: bool = True,
        status_filter: Optional[GoalStatus] = None
    ) -> List[Goal]:
        """
        Get all active goals for project, sorted by priority.

        Args:
            project_id: Project identifier
            include_subgoals: Include subgoals in results
            status_filter: Filter by status (default: all statuses)

        Returns:
            List of goals sorted by priority (highest first)
        """
        with self.db.conn:
            query = """
                SELECT * FROM active_goals
                WHERE project_id = ?
            """
            params = [project_id]

            if not include_subgoals:
                query += " AND goal_type = ?"
                params.append(GoalType.PRIMARY.value)

            if status_filter:
                query += " AND status = ?"
                params.append(status_filter.value)

            query += " ORDER BY priority DESC, created_at ASC"

            rows = self.db.conn.execute(query, params).fetchall()
            return [self._row_to_goal(row) for row in rows]

    def update_goal_progress(
        self,
        goal_id: int,
        progress: float,
        status: Optional[GoalStatus] = None
    ):
        """
        Update goal completion progress.

        Args:
            goal_id: Goal identifier
            progress: Progress (0.0 to 1.0)
            status: Optional new status
        """
        progress = max(0.0, min(1.0, progress))

        with self.db.conn:
            if status:
                self.db.conn.execute("""
                    UPDATE active_goals
                    SET progress = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (progress, status.value, goal_id))
            else:
                self.db.conn.execute("""
                    UPDATE active_goals
                    SET progress = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (progress, goal_id))

            # Auto-complete if progress reaches 1.0
            if progress >= 1.0:
                self.db.conn.execute("""
                    UPDATE active_goals
                    SET status = ?
                    WHERE id = ? AND status = ?
                """, (GoalStatus.COMPLETED.value, goal_id, GoalStatus.ACTIVE.value))

    def complete_goal(self, goal_id: int, cascade_to_children: bool = False):
        """
        Mark goal as completed.

        Args:
            goal_id: Goal identifier
            cascade_to_children: Also complete child goals
        """
        with self.db.conn:
            self.db.conn.execute("""
                UPDATE active_goals
                SET status = ?, progress = 1.0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (GoalStatus.COMPLETED.value, goal_id))

            if cascade_to_children:
                self.db.conn.execute("""
                    UPDATE active_goals
                    SET status = ?, progress = 1.0, updated_at = CURRENT_TIMESTAMP
                    WHERE parent_goal_id = ?
                """, (GoalStatus.COMPLETED.value, goal_id))

    def suspend_goal(self, goal_id: int):
        """Temporarily suspend goal (can be resumed later)."""
        with self.db.conn:
            self.db.conn.execute("""
                UPDATE active_goals
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (GoalStatus.SUSPENDED.value, goal_id))

    def resume_goal(self, goal_id: int):
        """Resume suspended goal."""
        with self.db.conn:
            self.db.conn.execute("""
                UPDATE active_goals
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (GoalStatus.ACTIVE.value, goal_id))

    def update_goal_status(self, goal_id: int, status: str):
        """Update goal status (active, suspended, completed, blocked)."""
        with self.db.conn:
            self.db.conn.execute("""
                UPDATE active_goals SET status = ?, updated_at = datetime('now')
                WHERE id = ?
            """, (status, goal_id))

    def get_subgoals(self, parent_goal_id: int) -> List[Goal]:
        """Get all subgoals of a parent goal."""
        with self.db.conn:
            rows = self.db.conn.execute("""
                SELECT * FROM active_goals
                WHERE parent_goal_id = ?
                ORDER BY priority DESC
            """, (parent_goal_id,)).fetchall()
            return [self._row_to_goal(row) for row in rows]

    def get_goal_hierarchy(self, project_id: int) -> List[dict]:
        """
        Get goal hierarchy with parent-child relationships.

        Returns:
            List of goals with depth and path information
        """
        with self.db.conn:
            rows = self.db.conn.execute("""
                SELECT * FROM v_goals_hierarchy
                WHERE project_id = ?
                ORDER BY depth, priority DESC
            """, (project_id,)).fetchall()

            return [dict(row) for row in rows]

    # ========================================================================
    # Capacity Management
    # ========================================================================

    def check_capacity(self, project_id: int) -> bool:
        """
        Check if working memory is at capacity.

        Returns:
            True if at capacity (7±2 items), False otherwise
        """
        return self.is_at_capacity(project_id)

    def is_at_capacity(self, project_id: int) -> bool:
        """Check if working memory is at capacity (7±2 items)."""
        capacity = self.get_capacity_status(project_id)
        return capacity['at_capacity']

    def get_capacity_status(self, project_id: int) -> dict:
        """Get current capacity status across all WM components."""
        with self.db.conn:
            count = self.db.conn.execute("""
                SELECT COUNT(*) FROM working_memory WHERE project_id = ?
            """, (project_id,)).fetchone()[0]
            return {
                'count': count,
                'max_capacity': self.max_wm_capacity,
                'available': self.max_wm_capacity - count,
                'at_capacity': count >= self.max_wm_capacity
            }

    def trigger_consolidation(self, project_id: int, count: int = 3):
        """
        Consolidate least important items when capacity reached.

        Args:
            project_id: Project identifier
            count: Number of items to consolidate (default: 3)
        """
        if not self.is_at_capacity(project_id):
            return

        # Get least active items
        with self.db.conn:
            rows = self.db.conn.execute("""
                SELECT id, content, content_type, component,
                       current_activation, importance_score
                FROM v_working_memory_current
                WHERE project_id = ?
                ORDER BY current_activation ASC, importance_score ASC
                LIMIT ?
            """, (project_id, count)).fetchall()

            consolidated_ids = []
            for row in rows:
                # Mark for consolidation (actual consolidation handled by router)
                item_id = row['id']

                # Delete from working memory
                self.db.conn.execute("""
                    DELETE FROM working_memory WHERE id = ?
                """, (item_id,))

                consolidated_ids.append(item_id)

            return consolidated_ids

    # ========================================================================
    # Attention Allocation
    # ========================================================================

    def set_attention_focus(
        self,
        project_id: int,
        focus_target: str,
        focus_type: str = "memory",
        weight: float = 1.0
    ):
        """
        Set attention focus.

        Args:
            project_id: Project identifier
            focus_target: What to focus on (memory ID, file path, etc.)
            focus_type: Type of focus (memory, file, concept, task, problem)
            weight: Attention weight (multiplier for activation)
        """
        with self.db.conn:
            # Clear previous focus
            self.db.conn.execute("""
                DELETE FROM attention_focus WHERE project_id = ?
            """, (project_id,))

            # Set new focus
            self.db.conn.execute("""
                INSERT INTO attention_focus
                (project_id, focus_target, focus_type, attention_weight)
                VALUES (?, ?, ?, ?)
            """, (project_id, focus_target, focus_type, weight))

    def allocate_attention(self, project_id: int, goal_id: int, weight: float = 0.8):
        """Allocate attention to a specific goal."""
        with self.db.conn:
            self.db.conn.execute("""
                INSERT OR REPLACE INTO attention_focus
                (project_id, goal_id, attention_weight, focused_at)
                VALUES (?, ?, ?, datetime('now'))
            """, (project_id, goal_id, weight))

    def get_attention_focus(self, project_id: int) -> List:
        """Get current attention focus."""
        from types import SimpleNamespace
        with self.db.conn:
            rows = self.db.conn.execute("""
                SELECT goal_id, attention_weight FROM attention_focus
                WHERE project_id = ?
                ORDER BY focused_at DESC
            """, (project_id,)).fetchall()
            return [SimpleNamespace(**dict(row)) for row in rows]

    # ========================================================================
    # Automatic Saliency Detection (Research-Backed Attention Management)
    # ========================================================================

    def compute_memory_saliency(
        self,
        memory_id: int,
        layer: str,
        project_id: int,
        current_goal: Optional[str] = None,
        context_events: Optional[List[int]] = None,
    ) -> dict:
        """Compute saliency score for a memory using multi-factor model.

        Factors:
        1. Frequency: How often accessed (30% weight)
        2. Recency: How recently accessed (30% weight)
        3. Task Relevance: Relevance to current goal (25% weight)
        4. Surprise Value: How novel/unexpected (15% weight)

        Research: Kumar et al. 2023, Baddeley 2000, StreamingLLM ICLR 2024

        Args:
            memory_id: Memory to evaluate
            layer: Memory layer (semantic, episodic, procedural)
            project_id: Project context
            current_goal: Current task/goal (for relevance)
            context_events: Recent event IDs (for surprise)

        Returns:
            Dict with saliency score and focus recommendation
        """
        saliency = self.saliency_calc.compute_saliency(
            memory_id,
            layer,
            project_id,
            current_goal=current_goal,
            context_recent_events=context_events,
        )

        return {
            "memory_id": memory_id,
            "layer": layer,
            "saliency": saliency,
            "focus_type": saliency_to_focus_type(saliency),
            "recommendation": saliency_to_recommendation(saliency),
        }

    def auto_focus_top_memories(
        self,
        project_id: int,
        layer: str = "semantic",
        top_k: int = 5,
        current_goal: Optional[str] = None,
        context_events: Optional[List[int]] = None,
    ) -> List[dict]:
        """Automatically compute saliency and focus on top-k memories.

        This implements automatic attention allocation based on saliency scores,
        reducing cognitive load and improving retrieval relevance.

        Args:
            project_id: Project context
            layer: Memory layer to focus on
            top_k: Number of top memories to focus on
            current_goal: Current task/goal
            context_events: Recent context events

        Returns:
            List of top-k memories with saliency scores and focus types
        """
        with self.db.conn:
            # Get all memories in layer for project
            rows = self.db.conn.execute(f"""
                SELECT id FROM memories
                WHERE project_id = ?
                LIMIT 100
            """, (project_id,)).fetchall()

            memory_ids = [row[0] for row in rows]

            if not memory_ids:
                return []

            # Compute saliency for each memory
            saliency_scores = []
            for memory_id in memory_ids:
                try:
                    saliency = self.compute_memory_saliency(
                        memory_id,
                        layer,
                        project_id,
                        current_goal=current_goal,
                        context_events=context_events,
                    )
                    saliency_scores.append(saliency)
                except Exception:
                    # Skip if saliency computation fails
                    continue

            # Sort by saliency (descending)
            saliency_scores.sort(key=lambda x: x["saliency"], reverse=True)

            # Auto-set focus for top-k with appropriate weights
            for i, item in enumerate(saliency_scores[:top_k]):
                # Weight decays with rank (top item gets highest weight)
                weight = max(0.3, 1.0 - (i * 0.1))
                self.set_attention_focus(
                    project_id,
                    str(item["memory_id"]),
                    focus_type=item["focus_type"],
                    weight=weight,
                )

            return saliency_scores[:top_k]

    def get_saliency_scores_batch(
        self,
        memory_ids: List[int],
        layer: str,
        project_id: int,
        current_goal: Optional[str] = None,
        context_events: Optional[List[int]] = None,
    ) -> List[dict]:
        """Compute saliency scores for multiple memories.

        Efficient batch processing of saliency computation.

        Args:
            memory_ids: List of memory IDs to score
            layer: Memory layer
            project_id: Project context
            current_goal: Current task/goal
            context_events: Recent context events

        Returns:
            List of saliency results for each memory
        """
        results = []
        for memory_id in memory_ids:
            try:
                result = self.compute_memory_saliency(
                    memory_id,
                    layer,
                    project_id,
                    current_goal=current_goal,
                    context_events=context_events,
                )
                results.append(result)
            except Exception:
                # Include failed items with neutral score
                results.append({
                    "memory_id": memory_id,
                    "layer": layer,
                    "saliency": 0.5,
                    "focus_type": "background",
                    "recommendation": "BACKGROUND: Could not compute saliency",
                })

        return results

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _row_to_goal(self, row) -> Goal:
        """Convert database row to Goal object."""
        return Goal(
            id=row['id'],
            project_id=row['project_id'],
            goal_text=row['goal_text'],
            goal_type=GoalType(row['goal_type']),
            parent_goal_id=row['parent_goal_id'],
            priority=row['priority'],
            status=GoalStatus(row['status']),
            progress=row['progress'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            deadline=datetime.fromisoformat(row['deadline']) if row['deadline'] else None,
            completion_criteria=row['completion_criteria'],
            metadata=json.loads(row['metadata']) if row['metadata'] else None
        )

    def get_statistics(self, project_id: int) -> dict:
        """Get working memory statistics."""
        with self.db.conn:
            # Capacity stats
            capacity = self.check_capacity(project_id)

            # Goal stats
            goal_stats = self.db.conn.execute("""
                SELECT status, COUNT(*) as count
                FROM active_goals
                WHERE project_id = ?
                GROUP BY status
            """, (project_id,)).fetchall()

            goal_counts = {row['status']: row['count'] for row in goal_stats}

            # Component distribution
            component_stats = self.db.conn.execute("""
                SELECT component, COUNT(*) as count
                FROM working_memory
                WHERE project_id = ?
                GROUP BY component
            """, (project_id,)).fetchall()

            component_counts = {row['component']: row['count'] for row in component_stats}

            return {
                'capacity': capacity,
                'goals': goal_counts,
                'components': component_counts
            }
