"""Architecture Decision Record (ADR) storage and retrieval.

This module provides storage and querying capabilities for Architecture Decision Records,
enabling teams to maintain a persistent history of architectural decisions.
"""

import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from ..core.database import Database
from ..core.base_store import BaseStore
from .models import ArchitecturalDecisionRecord, DecisionStatus

logger = logging.getLogger(__name__)


class ADRStore(BaseStore[ArchitecturalDecisionRecord]):
    """Store and manage Architecture Decision Records."""

    table_name = "architecture_decisions"
    model_class = ArchitecturalDecisionRecord

    def __init__(self, db: Optional[Database] = None):
        """Initialize ADR store.

        Args:
            db: Database instance (uses singleton if not provided)
        """
        super().__init__(db)
        self._ensure_schema()

    def _ensure_schema(self):
        """Create ADR table if it doesn't exist."""
        # Skip for PostgreSQL async databases (schema managed centrally)
        if not hasattr(self.db, 'conn'):
            logger.debug("PostgreSQL async database detected, skipping schema creation")
            return

        cursor = self.db.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS architecture_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'proposed',

                -- Core content
                context TEXT NOT NULL,
                decision TEXT NOT NULL,
                rationale TEXT NOT NULL,

                -- Alternatives and consequences (JSON arrays)
                alternatives TEXT,
                consequences TEXT,

                -- Metadata
                author TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                superseded_by INTEGER,

                -- Related (JSON arrays)
                related_patterns TEXT,
                related_constraints TEXT,
                tags TEXT,

                -- Tracking
                implementation_status TEXT DEFAULT 'not_started',
                effectiveness_score REAL,

                FOREIGN KEY (superseded_by) REFERENCES architecture_decisions(id)
            )
        """)

        # Indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_adr_project
            ON architecture_decisions(project_id, created_at DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_adr_status
            ON architecture_decisions(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_adr_effectiveness
            ON architecture_decisions(effectiveness_score DESC)
        """)

        self.db.conn.commit()
        logger.info("ADR schema initialized")

    def _row_to_model(self, row: Dict[str, Any]) -> ArchitecturalDecisionRecord:
        """Convert database row to ADR model.

        Args:
            row: Database row as dict

        Returns:
            ArchitecturalDecisionRecord instance
        """
        row_dict = row if isinstance(row, dict) else dict(row)

        # Parse JSON fields
        alternatives = self._safe_json_loads(row_dict.get("alternatives"), [])
        consequences = self._safe_json_loads(row_dict.get("consequences"), [])
        related_patterns = self._safe_json_loads(row_dict.get("related_patterns"), [])
        related_constraints = self._safe_json_loads(row_dict.get("related_constraints"), [])
        tags = self._safe_json_loads(row_dict.get("tags"), [])

        return ArchitecturalDecisionRecord(
            id=row_dict.get("id"),
            project_id=row_dict.get("project_id"),
            title=row_dict.get("title"),
            status=DecisionStatus(row_dict.get("status")) if row_dict.get("status") else DecisionStatus.PROPOSED,
            context=row_dict.get("context"),
            decision=row_dict.get("decision"),
            rationale=row_dict.get("rationale"),
            alternatives=alternatives,
            consequences=consequences,
            author=row_dict.get("author"),
            created_at=datetime.fromtimestamp(row_dict.get("created_at")) if row_dict.get("created_at") else datetime.now(),
            updated_at=datetime.fromtimestamp(row_dict.get("updated_at")) if row_dict.get("updated_at") else datetime.now(),
            superseded_by=row_dict.get("superseded_by"),
            related_patterns=related_patterns,
            related_constraints=related_constraints,
            tags=tags,
            implementation_status=row_dict.get("implementation_status", "not_started"),
            effectiveness_score=row_dict.get("effectiveness_score"),
        )

    def _safe_json_loads(self, data: Any, default: Any = None) -> Any:
        """Safely load JSON data with fallback.

        Args:
            data: JSON string or None
            default: Default value if parsing fails

        Returns:
            Parsed data or default
        """
        if not data:
            return default
        try:
            return json.loads(data) if isinstance(data, str) else data
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Failed to parse JSON: {data}")
            return default

    def create(self, adr: ArchitecturalDecisionRecord) -> int:
        """Create a new ADR.

        Args:
            adr: ADR to create

        Returns:
            ID of created ADR
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO architecture_decisions (
                project_id, title, status, context, decision, rationale,
                alternatives, consequences, author, created_at, updated_at,
                superseded_by, related_patterns, related_constraints, tags,
                implementation_status, effectiveness_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            adr.project_id,
            adr.title,
            adr.status.value,
            adr.context,
            adr.decision,
            adr.rationale,
            json.dumps(adr.alternatives),
            json.dumps(adr.consequences),
            adr.author,
            adr.created_at.timestamp(),
            adr.updated_at.timestamp(),
            adr.superseded_by,
            json.dumps(adr.related_patterns),
            json.dumps(adr.related_constraints),
            json.dumps(adr.tags),
            adr.implementation_status,
            adr.effectiveness_score,
        ))
        self.db.conn.commit()

        adr_id = cursor.lastrowid
        logger.info(f"Created ADR {adr_id}: {adr.title}")
        return adr_id

    def get(self, adr_id: int) -> Optional[ArchitecturalDecisionRecord]:
        """Get ADR by ID.

        Args:
            adr_id: ADR ID

        Returns:
            ADR or None if not found
        """
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM architecture_decisions WHERE id = ?", (adr_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_model(row)

    def list_by_project(
        self,
        project_id: int,
        status: Optional[DecisionStatus] = None,
        limit: int = 100
    ) -> List[ArchitecturalDecisionRecord]:
        """List ADRs for a project.

        Args:
            project_id: Project ID
            status: Filter by status (optional)
            limit: Maximum number to return

        Returns:
            List of ADRs
        """
        cursor = self.db.conn.cursor()

        if status:
            cursor.execute("""
                SELECT * FROM architecture_decisions
                WHERE project_id = ? AND status = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (project_id, status.value, limit))
        else:
            cursor.execute("""
                SELECT * FROM architecture_decisions
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (project_id, limit))

        rows = cursor.fetchall()
        return [self._row_to_model(row) for row in rows]

    def search_by_tags(self, project_id: int, tags: List[str], limit: int = 50) -> List[ArchitecturalDecisionRecord]:
        """Search ADRs by tags.

        Args:
            project_id: Project ID
            tags: Tags to search for
            limit: Maximum results

        Returns:
            Matching ADRs
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM architecture_decisions
            WHERE project_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (project_id, limit))

        rows = cursor.fetchall()
        adrs = [self._row_to_model(row) for row in rows]

        # Filter by tags (since JSON search in SQLite is limited)
        matching = []
        for adr in adrs:
            if any(tag in adr.tags for tag in tags):
                matching.append(adr)

        return matching

    def supersede(self, old_adr_id: int, new_adr_id: int) -> None:
        """Mark an ADR as superseded by another.

        Args:
            old_adr_id: ADR being superseded
            new_adr_id: ADR that supersedes it
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            UPDATE architecture_decisions
            SET status = ?, superseded_by = ?, updated_at = ?
            WHERE id = ?
        """, (DecisionStatus.SUPERSEDED.value, new_adr_id, datetime.now().timestamp(), old_adr_id))
        self.db.conn.commit()
        logger.info(f"ADR {old_adr_id} superseded by ADR {new_adr_id}")

    def update_effectiveness(self, adr_id: int, score: float) -> None:
        """Update effectiveness score for an ADR.

        Args:
            adr_id: ADR ID
            score: Effectiveness score (0-1)
        """
        if not 0 <= score <= 1:
            raise ValueError("Effectiveness score must be between 0 and 1")

        cursor = self.db.conn.cursor()
        cursor.execute("""
            UPDATE architecture_decisions
            SET effectiveness_score = ?, updated_at = ?
            WHERE id = ?
        """, (score, datetime.now().timestamp(), adr_id))
        self.db.conn.commit()
        logger.info(f"Updated ADR {adr_id} effectiveness to {score}")

    def get_active_decisions(self, project_id: int) -> List[ArchitecturalDecisionRecord]:
        """Get all currently active (accepted) decisions for a project.

        Args:
            project_id: Project ID

        Returns:
            List of accepted ADRs
        """
        return self.list_by_project(project_id, status=DecisionStatus.ACCEPTED)

    def get_recent(self, project_id: int, days: int = 30, limit: int = 10) -> List[ArchitecturalDecisionRecord]:
        """Get recent ADRs from the last N days.

        Args:
            project_id: Project ID
            days: Number of days to look back
            limit: Maximum results

        Returns:
            Recent ADRs
        """
        since = datetime.now().timestamp() - (days * 24 * 60 * 60)

        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM architecture_decisions
            WHERE project_id = ? AND created_at >= ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (project_id, since, limit))

        rows = cursor.fetchall()
        return [self._row_to_model(row) for row in rows]
