"""Architectural constraint tracking and validation.

This module tracks architectural constraints that must be satisfied and provides
validation mechanisms to ensure compliance.
"""

import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from ..core.database import Database
from ..core.base_store import BaseStore
from .models import ArchitecturalConstraint, ConstraintType

logger = logging.getLogger(__name__)


class ConstraintTracker(BaseStore[ArchitecturalConstraint]):
    """Track and validate architectural constraints."""

    table_name = "architectural_constraints"
    model_class = ArchitecturalConstraint

    def __init__(self, db: Optional[Database] = None):
        """Initialize constraint tracker.

        Args:
            db: Database instance (uses singleton if not provided)
        """
        super().__init__(db)
        self._ensure_schema()

    def _ensure_schema(self):
        """Create constraints table if it doesn't exist."""
        # Skip for PostgreSQL async databases
        if not hasattr(self.db, 'conn'):
            logger.debug("PostgreSQL async database detected, skipping schema creation")
            return

        cursor = self.db.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS architectural_constraints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                type TEXT NOT NULL,

                -- Constraint details
                description TEXT NOT NULL,
                rationale TEXT NOT NULL,

                -- Validation
                validation_criteria TEXT NOT NULL,
                is_hard_constraint INTEGER NOT NULL DEFAULT 1,
                priority INTEGER NOT NULL DEFAULT 5,

                -- Scope
                applies_to TEXT,  -- JSON array

                -- Status
                is_satisfied INTEGER NOT NULL DEFAULT 0,
                verification_date REAL,
                verification_notes TEXT,

                -- Related
                related_adrs TEXT,  -- JSON array
                tags TEXT,          -- JSON array

                -- Metadata
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)

        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_constraint_project
            ON architectural_constraints(project_id, priority DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_constraint_type
            ON architectural_constraints(type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_constraint_satisfied
            ON architectural_constraints(is_satisfied, is_hard_constraint)
        """)

        self.db.conn.commit()
        logger.info("Constraint tracker schema initialized")

    def _row_to_model(self, row: Dict[str, Any]) -> ArchitecturalConstraint:
        """Convert database row to ArchitecturalConstraint model.

        Args:
            row: Database row as dict

        Returns:
            ArchitecturalConstraint instance
        """
        row_dict = row if isinstance(row, dict) else dict(row)

        # Parse JSON fields
        applies_to = self._safe_json_loads(row_dict.get("applies_to"), [])
        related_adrs = self._safe_json_loads(row_dict.get("related_adrs"), [])
        tags = self._safe_json_loads(row_dict.get("tags"), [])

        return ArchitecturalConstraint(
            id=row_dict.get("id"),
            project_id=row_dict.get("project_id"),
            type=ConstraintType(row_dict.get("type")) if row_dict.get("type") else ConstraintType.TECHNICAL,
            description=row_dict.get("description"),
            rationale=row_dict.get("rationale"),
            validation_criteria=row_dict.get("validation_criteria"),
            is_hard_constraint=bool(row_dict.get("is_hard_constraint", True)),
            priority=row_dict.get("priority", 5),
            applies_to=applies_to,
            is_satisfied=bool(row_dict.get("is_satisfied", False)),
            verification_date=datetime.fromtimestamp(row_dict.get("verification_date")) if row_dict.get("verification_date") else None,
            verification_notes=row_dict.get("verification_notes"),
            related_adrs=related_adrs,
            tags=tags,
            created_at=datetime.fromtimestamp(row_dict.get("created_at")) if row_dict.get("created_at") else datetime.now(),
            updated_at=datetime.fromtimestamp(row_dict.get("updated_at")) if row_dict.get("updated_at") else datetime.now(),
        )

    def _safe_json_loads(self, data: Any, default: Any = None) -> Any:
        """Safely load JSON data with fallback."""
        if not data:
            return default
        try:
            return json.loads(data) if isinstance(data, str) else data
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Failed to parse JSON: {data}")
            return default

    def add_constraint(self, constraint: ArchitecturalConstraint) -> int:
        """Add a new architectural constraint.

        Args:
            constraint: Constraint to add

        Returns:
            ID of added constraint
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO architectural_constraints (
                project_id, type, description, rationale,
                validation_criteria, is_hard_constraint, priority,
                applies_to, is_satisfied, verification_date, verification_notes,
                related_adrs, tags, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            constraint.project_id,
            constraint.type.value,
            constraint.description,
            constraint.rationale,
            constraint.validation_criteria,
            1 if constraint.is_hard_constraint else 0,
            constraint.priority,
            json.dumps(constraint.applies_to),
            1 if constraint.is_satisfied else 0,
            constraint.verification_date.timestamp() if constraint.verification_date else None,
            constraint.verification_notes,
            json.dumps(constraint.related_adrs),
            json.dumps(constraint.tags),
            constraint.created_at.timestamp(),
            constraint.updated_at.timestamp(),
        ))
        self.db.conn.commit()

        constraint_id = cursor.lastrowid
        logger.info(f"Added constraint {constraint_id}: {constraint.description[:50]}")
        return constraint_id

    def get(self, constraint_id: int) -> Optional[ArchitecturalConstraint]:
        """Get constraint by ID.

        Args:
            constraint_id: Constraint ID

        Returns:
            Constraint or None if not found
        """
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM architectural_constraints WHERE id = ?", (constraint_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_model(row)

    def list_by_project(
        self,
        project_id: int,
        constraint_type: Optional[ConstraintType] = None,
        only_unsatisfied: bool = False
    ) -> List[ArchitecturalConstraint]:
        """List constraints for a project.

        Args:
            project_id: Project ID
            constraint_type: Filter by type (optional)
            only_unsatisfied: Only return unsatisfied constraints

        Returns:
            List of constraints
        """
        cursor = self.db.conn.cursor()

        if constraint_type and only_unsatisfied:
            cursor.execute("""
                SELECT * FROM architectural_constraints
                WHERE project_id = ? AND type = ? AND is_satisfied = 0
                ORDER BY priority DESC
            """, (project_id, constraint_type.value))
        elif constraint_type:
            cursor.execute("""
                SELECT * FROM architectural_constraints
                WHERE project_id = ? AND type = ?
                ORDER BY priority DESC
            """, (project_id, constraint_type.value))
        elif only_unsatisfied:
            cursor.execute("""
                SELECT * FROM architectural_constraints
                WHERE project_id = ? AND is_satisfied = 0
                ORDER BY priority DESC
            """, (project_id,))
        else:
            cursor.execute("""
                SELECT * FROM architectural_constraints
                WHERE project_id = ?
                ORDER BY priority DESC
            """, (project_id,))

        rows = cursor.fetchall()
        return [self._row_to_model(row) for row in rows]

    def get_hard_constraints(self, project_id: int) -> List[ArchitecturalConstraint]:
        """Get all hard constraints (must satisfy) for a project.

        Args:
            project_id: Project ID

        Returns:
            List of hard constraints
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM architectural_constraints
            WHERE project_id = ? AND is_hard_constraint = 1
            ORDER BY priority DESC
        """, (project_id,))

        rows = cursor.fetchall()
        return [self._row_to_model(row) for row in rows]

    def verify_constraint(
        self,
        constraint_id: int,
        is_satisfied: bool,
        notes: Optional[str] = None
    ) -> None:
        """Mark a constraint as verified.

        Args:
            constraint_id: Constraint ID
            is_satisfied: Whether the constraint is satisfied
            notes: Verification notes (optional)
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            UPDATE architectural_constraints
            SET is_satisfied = ?,
                verification_date = ?,
                verification_notes = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            1 if is_satisfied else 0,
            datetime.now().timestamp(),
            notes,
            datetime.now().timestamp(),
            constraint_id,
        ))
        self.db.conn.commit()
        logger.info(f"Verified constraint {constraint_id}: {'satisfied' if is_satisfied else 'not satisfied'}")

    def get_unsatisfied_hard_constraints(self, project_id: int) -> List[ArchitecturalConstraint]:
        """Get all unsatisfied hard constraints (blockers).

        Args:
            project_id: Project ID

        Returns:
            List of unsatisfied hard constraints
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM architectural_constraints
            WHERE project_id = ? AND is_hard_constraint = 1 AND is_satisfied = 0
            ORDER BY priority DESC
        """, (project_id,))

        rows = cursor.fetchall()
        return [self._row_to_model(row) for row in rows]

    def get_constraints_for_component(
        self,
        project_id: int,
        component: str
    ) -> List[ArchitecturalConstraint]:
        """Get constraints applicable to a specific component.

        Args:
            project_id: Project ID
            component: Component name

        Returns:
            Applicable constraints
        """
        # Get all constraints for project
        all_constraints = self.list_by_project(project_id)

        # Filter by component
        applicable = []
        for constraint in all_constraints:
            if component in constraint.applies_to or not constraint.applies_to:
                applicable.append(constraint)

        # Sort by priority
        applicable.sort(key=lambda c: c.priority, reverse=True)

        return applicable
