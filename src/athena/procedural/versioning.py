"""Procedure versioning and rollback system."""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any

from ..core.database import Database


@dataclass
class ProcedureVersion:
    """Track procedure versions for comparison and rollback."""

    id: Optional[int] = None
    procedure_id: int = 0
    version: int = 0
    created_at: datetime = None
    extracted_from: List[int] = None  # episodic event IDs that led to this version
    effectiveness_score: float = 0.0  # 0.0-1.0
    tags: List[str] = None
    active: bool = False
    rollback_to: Optional[int] = None
    procedure_snapshot: Optional[Dict[str, Any]] = None  # Full procedure data

    def __post_init__(self):
        """Initialize default values."""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.extracted_from is None:
            self.extracted_from = []
        if self.tags is None:
            self.tags = []

    def is_better_than(self, other: "ProcedureVersion") -> bool:
        """Compare effectiveness of two versions."""
        return self.effectiveness_score > other.effectiveness_score


class ProcedureVersionStore:
    """Manage procedure versions with versioning, comparison, and rollback."""

    def __init__(self, db: Database):
        """Initialize version store.

        Args:
            db: Database instance
        """
        self.db = db

    def create_version(
        self,
        procedure_id: int,
        extracted_from: List[int] = None,
        effectiveness_score: float = 0.0,
        tags: List[str] = None,
        procedure_snapshot: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Create new procedure version.

        Args:
            procedure_id: ID of the procedure
            extracted_from: List of episodic event IDs
            effectiveness_score: Score 0.0-1.0
            tags: Tags for categorization
            procedure_snapshot: Full procedure data for rollback

        Returns:
            New version number
        """
        # Get next version number
        cursor = self.db.execute(
            "SELECT MAX(version) FROM procedure_versions WHERE procedure_id = ?",
            (procedure_id,),
        )
        row = cursor.fetchone()
        max_version = row[0] if row and row[0] else 0
        new_version = max_version + 1

        # Store version
        self.db.execute(
            """
            INSERT INTO procedure_versions
            (procedure_id, version, extracted_from, effectiveness_score, tags, active, procedure_snapshot)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                procedure_id,
                new_version,
                json.dumps(extracted_from or []),
                effectiveness_score,
                json.dumps(tags or []),
                True,  # New version is active
                json.dumps(procedure_snapshot) if procedure_snapshot else None,
            ),
        )

        # Deactivate previous versions
        self.db.execute(
            "UPDATE procedure_versions SET active = FALSE WHERE procedure_id = ? AND version < ?",
            (procedure_id, new_version),
        )

        self.db.commit()
        return new_version

    def get_version(self, procedure_id: int, version: int) -> Optional[ProcedureVersion]:
        """Get specific procedure version.

        Args:
            procedure_id: ID of the procedure
            version: Version number

        Returns:
            ProcedureVersion or None if not found
        """
        cursor = self.db.execute(
            """SELECT id, procedure_id, version, created_at, extracted_from,
                      effectiveness_score, tags, active, rollback_to, procedure_snapshot
               FROM procedure_versions
               WHERE procedure_id = ? AND version = ?""",
            (procedure_id, version),
        )
        row = cursor.fetchone()
        if not row:
            return None

        return ProcedureVersion(
            id=row[0],
            procedure_id=row[1],
            version=row[2],
            created_at=datetime.fromisoformat(row[3]) if row[3] else datetime.now(),
            extracted_from=json.loads(row[4]) if row[4] else [],
            effectiveness_score=row[5],
            tags=json.loads(row[6]) if row[6] else [],
            active=bool(row[7]),
            rollback_to=row[8],
            procedure_snapshot=json.loads(row[9]) if row[9] else None,
        )

    def get_active_version(self, procedure_id: int) -> Optional[ProcedureVersion]:
        """Get the active version of a procedure.

        Args:
            procedure_id: ID of the procedure

        Returns:
            Active ProcedureVersion or None
        """
        cursor = self.db.execute(
            """SELECT id, procedure_id, version, created_at, extracted_from,
                      effectiveness_score, tags, active, rollback_to, procedure_snapshot
               FROM procedure_versions
               WHERE procedure_id = ? AND active = TRUE
               ORDER BY version DESC
               LIMIT 1""",
            (procedure_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        return ProcedureVersion(
            id=row[0],
            procedure_id=row[1],
            version=row[2],
            created_at=datetime.fromisoformat(row[3]) if row[3] else datetime.now(),
            extracted_from=json.loads(row[4]) if row[4] else [],
            effectiveness_score=row[5],
            tags=json.loads(row[6]) if row[6] else [],
            active=bool(row[7]),
            rollback_to=row[8],
            procedure_snapshot=json.loads(row[9]) if row[9] else None,
        )

    def compare_versions(self, procedure_id: int, v1: int, v2: int) -> Dict[str, Any]:
        """Compare two procedure versions.

        Args:
            procedure_id: ID of the procedure
            v1: First version number
            v2: Second version number

        Returns:
            Comparison dict with effectiveness scores and winner
        """
        version1 = self.get_version(procedure_id, v1)
        version2 = self.get_version(procedure_id, v2)

        if not version1 or not version2:
            return {"error": "Version not found"}

        winner = v1 if version1.effectiveness_score > version2.effectiveness_score else v2

        return {
            "v1": {
                "version": v1,
                "effectiveness": round(version1.effectiveness_score, 4),
                "created_at": version1.created_at.isoformat(),
                "tags": version1.tags,
            },
            "v2": {
                "version": v2,
                "effectiveness": round(version2.effectiveness_score, 4),
                "created_at": version2.created_at.isoformat(),
                "tags": version2.tags,
            },
            "winner": winner,
            "improvement": round(
                abs(version1.effectiveness_score - version2.effectiveness_score), 4
            ),
        }

    def rollback(self, procedure_id: int, to_version: int) -> Dict[str, Any]:
        """Rollback procedure to specific version.

        Args:
            procedure_id: ID of the procedure
            to_version: Version number to rollback to

        Returns:
            Status dict
        """
        version = self.get_version(procedure_id, to_version)
        if not version:
            return {"error": "Version not found"}

        # Mark all as inactive
        self.db.execute(
            "UPDATE procedure_versions SET active = FALSE WHERE procedure_id = ?",
            (procedure_id,),
        )

        # Activate target version
        self.db.execute(
            "UPDATE procedure_versions SET active = TRUE WHERE procedure_id = ? AND version = ?",
            (procedure_id, to_version),
        )

        self.db.commit()

        return {
            "status": "success",
            "procedure_id": procedure_id,
            "rolled_back_to_version": to_version,
        }

    def list_versions(self, procedure_id: int) -> List[Dict[str, Any]]:
        """List all versions for a procedure.

        Args:
            procedure_id: ID of the procedure

        Returns:
            List of version dicts
        """
        cursor = self.db.execute(
            """SELECT version, created_at, effectiveness_score, active, tags
               FROM procedure_versions
               WHERE procedure_id = ?
               ORDER BY version DESC""",
            (procedure_id,),
        )

        return [
            {
                "version": row[0],
                "created_at": row[1],
                "effectiveness_score": round(row[2], 4),
                "active": bool(row[3]),
                "tags": json.loads(row[4]) if row[4] else [],
            }
            for row in cursor.fetchall()
        ]

    def update_effectiveness(
        self, procedure_id: int, version: int, effectiveness_score: float
    ) -> bool:
        """Update effectiveness score of a version.

        Args:
            procedure_id: ID of the procedure
            version: Version number
            effectiveness_score: New score 0.0-1.0

        Returns:
            True if updated, False if not found
        """
        cursor = self.db.execute(
            "SELECT id FROM procedure_versions WHERE procedure_id = ? AND version = ?",
            (procedure_id, version),
        )
        if not cursor.fetchone():
            return False

        self.db.execute(
            "UPDATE procedure_versions SET effectiveness_score = ? WHERE procedure_id = ? AND version = ?",
            (effectiveness_score, procedure_id, version),
        )
        self.db.commit()
        return True

    def delete_old_versions(self, procedure_id: int, keep_count: int = 10) -> int:
        """Delete old versions, keeping the most recent N.

        Args:
            procedure_id: ID of the procedure
            keep_count: Number of recent versions to keep

        Returns:
            Number of deleted versions
        """
        cursor = self.db.execute(
            """SELECT version FROM procedure_versions
               WHERE procedure_id = ?
               ORDER BY version DESC
               LIMIT 1 OFFSET ?""",
            (procedure_id, keep_count),
        )
        row = cursor.fetchone()
        if not row:
            return 0

        min_version_to_keep = row[0]

        cursor = self.db.execute(
            "DELETE FROM procedure_versions WHERE procedure_id = ? AND version < ?",
            (procedure_id, min_version_to_keep),
        )
        self.db.commit()
        return cursor.rowcount
