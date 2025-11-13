"""Attention budget and working memory management."""

from datetime import datetime, timedelta
from typing import Optional, List

from ..core.database import Database
from ..core.base_store import BaseStore
from .models import AttentionItem, WorkingMemory, AttentionBudget


class AttentionManager(BaseStore):
    """Manages attention resources, working memory (7±2), and salience tracking."""

    table_name = "attention_items"
    model_class = AttentionItem

    def __init__(self, db: Database):
        """Initialize attention manager.

        Args:
            db: Database instance
        """
        super().__init__(db)
        self._init_schema()

    def _row_to_model(self, row) -> AttentionItem:
        """Convert database row to AttentionItem (required by BaseStore).

        Args:
            row: Database row

        Returns:
            AttentionItem instance
        """
        return self._row_to_attention_item(row)

    def _init_schema(self):
        """Create schema for attention tables (idempotent)."""
        # Attention items table
        self.execute("""
            CREATE TABLE IF NOT EXISTS attention_items (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                item_type VARCHAR(50) NOT NULL,
                item_id INTEGER NOT NULL,

                salience_score REAL DEFAULT 0.5,
                importance REAL DEFAULT 0.5,
                relevance REAL DEFAULT 0.5,
                recency REAL DEFAULT 0.5,

                last_accessed TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                activation_level REAL DEFAULT 0.0,

                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                context TEXT DEFAULT '',

                UNIQUE(project_id, item_type, item_id)
            )
        """)

        # Working memory table
        self.execute("""
            CREATE TABLE IF NOT EXISTS working_memory (
                id SERIAL PRIMARY KEY,
                project_id INTEGER UNIQUE NOT NULL,

                capacity INTEGER DEFAULT 7,
                capacity_variance INTEGER DEFAULT 2,
                current_load INTEGER DEFAULT 0,
                cognitive_load REAL DEFAULT 0.0,

                active_items TEXT DEFAULT '[]',
                total_slots_used INTEGER DEFAULT 0,

                overflow_threshold REAL DEFAULT 0.85,
                overflow_items TEXT DEFAULT '[]',

                last_consolidated TIMESTAMP,
                consolidation_interval_hours INTEGER DEFAULT 8,

                item_decay_rate REAL DEFAULT 0.1,
                refresh_threshold REAL DEFAULT 0.3,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Attention budget table
        self.execute("""
            CREATE TABLE IF NOT EXISTS attention_budgets (
                id SERIAL PRIMARY KEY,
                project_id INTEGER UNIQUE NOT NULL,

                current_focus VARCHAR(50) NOT NULL,
                focus_allocation TEXT DEFAULT '{}',

                current_focus_level REAL DEFAULT 0.0,
                context_switches INTEGER DEFAULT 0,
                context_switch_cost REAL DEFAULT 0.0,

                mental_energy REAL DEFAULT 1.0,
                fatigue_level REAL DEFAULT 0.0,
                optimal_session_length_minutes INTEGER DEFAULT 90,

                distraction_sources TEXT DEFAULT '[]',
                distraction_level REAL DEFAULT 0.0,

                session_start TIMESTAMP,
                session_end TIMESTAMP,
                total_focused_time_minutes INTEGER DEFAULT 0,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Indices for performance
        self.execute(
            "CREATE INDEX IF NOT EXISTS idx_attention_items_project ON attention_items(project_id)"
        )
        self.execute(
            "CREATE INDEX IF NOT EXISTS idx_attention_items_salience ON attention_items(salience_score DESC)"
        )
        self.execute(
            "CREATE INDEX IF NOT EXISTS idx_attention_items_activation ON attention_items(activation_level DESC)"
        )

    def add_attention_item(
        self,
        project_id: int,
        item_type: str,
        item_id: int,
        importance: float = 0.5,
        relevance: float = 0.5,
        context: str = "",
    ) -> int:
        """Add an item to attention (working memory).

        Args:
            project_id: Project ID
            item_type: Type of item (goal, task, entity, memory, observation)
            item_id: ID in respective layer
            importance: Importance score (0-1)
            relevance: Relevance score (0-1)
            context: Why this item is in focus

        Returns:
            Attention item ID
        """
        # Check if item already in focus
        existing = self.db.execute(
            """
            SELECT id FROM attention_items
            WHERE project_id = %s AND item_type = %s AND item_id = %s
            """,
            (project_id, item_type, item_id),
            fetch_one=True,
        )

        if existing:
            # Update existing item
            self._update_activation(existing[0])
            return existing[0]

        # Compute initial salience (recency=1.0 for new items)
        salience = self._compute_salience(
            recency=1.0, importance=importance, relevance=relevance
        )

        cursor = self.db.execute(
            """
            INSERT INTO attention_items (
                project_id, item_type, item_id,
                importance, relevance, salience_score, recency,
                activation_level, context, last_accessed, access_count
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, 1)
            RETURNING id
            """,
            (
                project_id,
                item_type,
                item_id,
                importance,
                relevance,
                salience,
                1.0,
                1.0,  # New items have full activation
                context,
            ),
        )

        item_id_new = cursor.fetchone()[0] if cursor else None
        self._enforce_working_memory_constraint(project_id)
        return item_id_new

    def get_attention_items(
        self, project_id: int, limit: int = 50, min_salience: float = 0.0
    ) -> List[AttentionItem]:
        """Get items in attention, ordered by salience.

        Args:
            project_id: Project ID
            limit: Maximum items to return
            min_salience: Minimum salience threshold

        Returns:
            List of attention items
        """
        rows = self.db.execute(
            """
            SELECT id, project_id, item_type, item_id,
                   salience_score, importance, relevance, recency,
                   last_accessed, access_count, activation_level,
                   added_at, context
            FROM attention_items
            WHERE project_id = %s AND salience_score >= %s
            ORDER BY salience_score DESC, activation_level DESC
            LIMIT %s
            """,
            (project_id, min_salience, limit),
            fetch_all=True,
        )

        items = []
        for row in rows:
            items.append(self._row_to_attention_item(row))
        return items

    def remove_attention_item(self, item_id: int) -> bool:
        """Remove item from attention.

        Args:
            item_id: Attention item ID

        Returns:
            True if removed, False if not found
        """
        cursor = self.db.execute(
            "DELETE FROM attention_items WHERE id = %s", (item_id,)
        )
        return cursor.rowcount > 0 if cursor else False

    def update_item_salience(
        self,
        item_id: int,
        importance: Optional[float] = None,
        relevance: Optional[float] = None,
    ) -> bool:
        """Update salience scores for an item.

        Args:
            item_id: Attention item ID
            importance: New importance (0-1)
            relevance: New relevance (0-1)

        Returns:
            True if updated
        """
        # Get current item
        row = self.db.execute(
            "SELECT recency, importance, relevance FROM attention_items WHERE id = %s",
            (item_id,),
            fetch_one=True,
        )

        if not row:
            return False

        current_recency = row[0]
        new_importance = importance if importance is not None else row[1]
        new_relevance = relevance if relevance is not None else row[2]

        # Recompute salience
        new_salience = self._compute_salience(
            recency=current_recency, importance=new_importance, relevance=new_relevance
        )

        self.db.execute(
            """
            UPDATE attention_items
            SET importance = %s, relevance = %s, salience_score = %s
            WHERE id = %s
            """,
            (new_importance, new_relevance, new_salience, item_id),
        )

        return True

    def get_working_memory(self, project_id: int) -> Optional[WorkingMemory]:
        """Get working memory state for a project.

        Args:
            project_id: Project ID

        Returns:
            WorkingMemory or None if not exists
        """
        row = self.db.execute(
            """
            SELECT id, project_id, capacity, capacity_variance, current_load,
                   cognitive_load, active_items, total_slots_used,
                   overflow_threshold, overflow_items, last_consolidated,
                   consolidation_interval_hours, item_decay_rate, refresh_threshold,
                   created_at, last_updated
            FROM working_memory
            WHERE project_id = %s
            """,
            (project_id,),
            fetch_one=True,
        )

        return self._row_to_working_memory(row) if row else None

    def create_working_memory(self, project_id: int) -> WorkingMemory:
        """Create working memory for a project.

        Args:
            project_id: Project ID

        Returns:
            New WorkingMemory
        """
        self.db.execute(
            """
            INSERT INTO working_memory (project_id, capacity, capacity_variance)
            VALUES (%s, 7, 2)
            """,
            (project_id,),
        )

        return self.get_working_memory(project_id)

    def get_attention_budget(self, project_id: int) -> Optional[AttentionBudget]:
        """Get attention budget for a project.

        Args:
            project_id: Project ID

        Returns:
            AttentionBudget or None if not exists
        """
        row = self.db.execute(
            """
            SELECT id, project_id, current_focus, focus_allocation,
                   current_focus_level, context_switches, context_switch_cost,
                   mental_energy, fatigue_level, optimal_session_length_minutes,
                   distraction_sources, distraction_level,
                   session_start, session_end, total_focused_time_minutes,
                   created_at, last_updated
            FROM attention_budgets
            WHERE project_id = %s
            """,
            (project_id,),
            fetch_one=True,
        )

        return self._row_to_attention_budget(row) if row else None

    def create_attention_budget(
        self, project_id: int, current_focus: str = "coding"
    ) -> AttentionBudget:
        """Create attention budget for a project.

        Args:
            project_id: Project ID
            current_focus: Initial focus area

        Returns:
            New AttentionBudget
        """
        self.db.execute(
            """
            INSERT INTO attention_budgets (project_id, current_focus)
            VALUES (%s, %s)
            """,
            (project_id, current_focus),
        )

        return self.get_attention_budget(project_id)

    def set_focus(self, project_id: int, focus_area: str, level: float) -> bool:
        """Set current focus area and level.

        Args:
            project_id: Project ID
            focus_area: Focus area name
            level: Focus level (0-1)

        Returns:
            True if updated
        """
        budget = self.get_attention_budget(project_id)
        if not budget:
            self.create_attention_budget(project_id, focus_area)
            budget = self.get_attention_budget(project_id)

        self.db.execute(
            """
            UPDATE attention_budgets
            SET current_focus = %s, current_focus_level = %s, last_updated = CURRENT_TIMESTAMP
            WHERE project_id = %s
            """,
            (focus_area, level, project_id),
        )

        return True

    def record_context_switch(self, project_id: int, cost: float = 0.1) -> int:
        """Record a context switch and its productivity cost.

        Args:
            project_id: Project ID
            cost: Productivity cost (0-1)

        Returns:
            New switch count
        """
        budget = self.get_attention_budget(project_id)
        if not budget:
            self.create_attention_budget(project_id)

        self.db.execute(
            """
            UPDATE attention_budgets
            SET context_switches = context_switches + 1,
                context_switch_cost = context_switch_cost + %s,
                last_updated = CURRENT_TIMESTAMP
            WHERE project_id = %s
            """,
            (cost, project_id),
        )

        return budget.context_switches + 1 if budget else 1

    def update_mental_energy(self, project_id: int, energy: float) -> bool:
        """Update mental energy level (decreases with activity).

        Args:
            project_id: Project ID
            energy: Energy level (0-1)

        Returns:
            True if updated
        """
        self.db.execute(
            """
            UPDATE attention_budgets
            SET mental_energy = %s, last_updated = CURRENT_TIMESTAMP
            WHERE project_id = %s
            """,
            (max(0.0, min(1.0, energy)), project_id),
        )

        return True

    def _enforce_working_memory_constraint(self, project_id: int):
        """Enforce 7±2 working memory constraint (drop lowest salience items if over).

        Args:
            project_id: Project ID
        """
        wm = self.get_working_memory(project_id)
        if not wm:
            self.create_working_memory(project_id)
            wm = self.get_working_memory(project_id)

        # Get current item count
        items = self.get_attention_items(project_id, limit=20)
        current_count = len(items)

        # Maximum capacity (7 + 2)
        max_capacity = wm.capacity + wm.capacity_variance

        if current_count > max_capacity:
            # Drop lowest salience items
            to_drop = current_count - max_capacity
            items_sorted = sorted(items, key=lambda x: x.salience_score)

            for i in range(to_drop):
                self.remove_attention_item(items_sorted[i].id)

            # Update working memory
            self.db.execute(
                """
                UPDATE working_memory
                SET current_load = %s, cognitive_load = %s,
                    last_updated = CURRENT_TIMESTAMP
                WHERE project_id = %s
                """,
                (
                    max_capacity,
                    max_capacity / max(1, wm.capacity),
                    project_id,
                ),
            )

    def _update_activation(self, item_id: int, amount: float = 0.1):
        """Increase activation level for an item.

        Args:
            item_id: Attention item ID
            amount: Amount to increase (0-1)
        """
        self.db.execute(
            """
            UPDATE attention_items
            SET activation_level = MIN(1.0, activation_level + %s),
                last_accessed = CURRENT_TIMESTAMP,
                access_count = access_count + 1
            WHERE id = %s
            """,
            (amount, item_id),
        )

    def _compute_salience(
        self, recency: float, importance: float, relevance: float
    ) -> float:
        """Compute salience score from components.

        Args:
            recency: Recency factor (0-1)
            importance: Importance factor (0-1)
            relevance: Relevance factor (0-1)

        Returns:
            Salience score (0-1)
        """
        # Weighted combination: 40% recency, 35% importance, 25% relevance
        return 0.4 * recency + 0.35 * importance + 0.25 * relevance

    def _row_to_attention_item(self, row) -> AttentionItem:
        """Convert database row to AttentionItem."""
        return AttentionItem(
            id=row[0],
            project_id=row[1],
            item_type=row[2],
            item_id=row[3],
            salience_score=row[4],
            importance=row[5],
            relevance=row[6],
            recency=row[7],
            last_accessed=row[8],
            access_count=row[9],
            activation_level=row[10],
            added_at=row[11],
            context=row[12],
        )

    def _row_to_working_memory(self, row) -> WorkingMemory:
        """Convert database row to WorkingMemory."""
        import json

        return WorkingMemory(
            id=row[0],
            project_id=row[1],
            capacity=row[2],
            capacity_variance=row[3],
            current_load=row[4],
            cognitive_load=row[5],
            active_items=json.loads(row[6]) if row[6] else [],
            total_slots_used=row[7],
            overflow_threshold=row[8],
            overflow_items=json.loads(row[9]) if row[9] else [],
            last_consolidated=row[10],
            consolidation_interval_hours=row[11],
            item_decay_rate=row[12],
            refresh_threshold=row[13],
            created_at=row[14],
            last_updated=row[15],
        )

    def _row_to_attention_budget(self, row) -> AttentionBudget:
        """Convert database row to AttentionBudget."""
        import json

        return AttentionBudget(
            id=row[0],
            project_id=row[1],
            current_focus=row[2],
            focus_allocation=json.loads(row[3]) if row[3] else {},
            current_focus_level=row[4],
            context_switches=row[5],
            context_switch_cost=row[6],
            mental_energy=row[7],
            fatigue_level=row[8],
            optimal_session_length_minutes=row[9],
            distraction_sources=json.loads(row[10]) if row[10] else [],
            distraction_level=row[11],
            session_start=row[12],
            session_end=row[13],
            total_focused_time_minutes=row[14],
        )

    def apply_importance_decay(
        self, project_id: int, decay_rate: float = 0.05, days_threshold: int = 30
    ) -> dict:
        """Apply exponential decay to importance of old, unused items.

        This implements spaced repetition-style decay: items not accessed recently
        have their importance gradually reduced. This helps the system focus on
        current and recently-used knowledge.

        Args:
            project_id: Project ID
            decay_rate: Exponential decay rate (0.05 = 5% per day, default)
            days_threshold: Only decay items older than this (default 30 days)

        Returns:
            Dictionary with decay statistics:
            - items_decayed: Count of items affected
            - avg_decay_amount: Average importance reduction
            - items_with_zero_importance: Count of items reaching zero importance
            - timestamp: When decay was applied
        """
        from datetime import datetime, timedelta

        # Calculate decay threshold
        threshold_date = datetime.now() - timedelta(days=days_threshold)

        # Get all old, unused items
        old_items = self.db.execute(
            """
            SELECT id, importance, last_accessed
            FROM attention_items
            WHERE project_id = %s
              AND last_accessed < %s
            ORDER BY last_accessed ASC
            """,
            (project_id, threshold_date),
            fetch_all=True,
        )

        if not old_items:
            return {
                "items_decayed": 0,
                "avg_decay_amount": 0.0,
                "items_with_zero_importance": 0,
                "timestamp": datetime.now().isoformat(),
            }

        items_decayed = 0
        total_decay = 0.0
        items_zeroed = 0

        for item_id, importance, last_accessed in old_items:
            # Calculate days since last access
            days_inactive = (datetime.now() - last_accessed).days

            # Apply exponential decay: new_importance = old * e^(-decay_rate * days)
            import math

            decay_factor = math.exp(-decay_rate * days_inactive)
            new_importance = max(0.0, importance * decay_factor)
            decay_amount = importance - new_importance

            if new_importance == 0.0:
                items_zeroed += 1

            # Update importance and recalculate salience
            recency_factor = max(0.0, 1.0 - (days_inactive / 365.0))
            new_salience = self._compute_salience(
                recency=recency_factor, importance=new_importance, relevance=0.5
            )

            self.db.execute(
                """
                UPDATE attention_items
                SET importance = %s,
                    recency = %s,
                    salience_score = %s,
                    last_updated = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (new_importance, recency_factor, new_salience, item_id),
            )

            items_decayed += 1
            total_decay += decay_amount

        avg_decay = total_decay / items_decayed if items_decayed > 0 else 0.0

        return {
            "items_decayed": items_decayed,
            "avg_decay_amount": round(avg_decay, 4),
            "items_with_zero_importance": items_zeroed,
            "timestamp": datetime.now().isoformat(),
        }
