"""Automatic procedure creation from learning patterns.

Extracts reusable procedures from consolidated patterns and lessons learned,
creating new procedural templates that can be reused in future planning.

This completes the learning loop: ExecutionTrace → Pattern → Procedure → Reuse
"""

import json
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from athena.core.database import Database


class ProcedureCandidate:
    """A candidate procedure extracted from learning."""

    def __init__(
        self,
        name: str,
        category: str,
        description: str,
        trigger_pattern: str,
        template: str,
        confidence: float = 0.5,
        success_rate: float = 0.0
    ):
        """Initialize procedure candidate.

        Args:
            name: Procedure name
            category: Category (git, code_template, refactoring, debugging, deployment, testing)
            description: Human-readable description
            trigger_pattern: Pattern that triggers this procedure
            template: Procedure template/steps
            confidence: Confidence in effectiveness (0.0-1.0)
            success_rate: Historical success rate (0.0-1.0)
        """
        self.name = name
        self.category = category
        self.description = description
        self.trigger_pattern = trigger_pattern
        self.template = template
        self.confidence = min(confidence, 1.0)
        self.success_rate = min(success_rate, 1.0)

    def to_dict(self) -> dict:
        """Convert to dict."""
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "trigger_pattern": self.trigger_pattern,
            "template": self.template,
            "confidence": self.confidence,
            "success_rate": self.success_rate,
        }


class ProcedureAutoCreator:
    """Automatically creates procedures from learned patterns.

    Purpose:
    - Extract procedures from consolidated patterns
    - Create procedure entries in Memory-MCP
    - Link procedures to source patterns
    - Track procedure effectiveness over time
    """

    def __init__(self, db: "Database"):
        """Initialize ProcedureAutoCreator.

        Args:
            db: Database connection
        """
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self):
        """Create procedure creation tracking tables."""
        cursor = self.db.get_cursor()

        # Table: Procedure creation log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS procedure_creations (
                id INTEGER PRIMARY KEY,
                procedure_name TEXT NOT NULL,
                category TEXT NOT NULL,
                source_pattern_id INTEGER,
                source_lesson_id INTEGER,
                confidence REAL,
                created_at INTEGER NOT NULL,
                first_use_at INTEGER,
                total_uses INTEGER DEFAULT 0,
                successful_uses INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.0
            )
        """)

        # Table: Procedure usage tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS procedure_usage (
                id INTEGER PRIMARY KEY,
                procedure_id INTEGER NOT NULL,
                used_in_session TEXT NOT NULL,
                used_for_goal TEXT,
                outcome TEXT NOT NULL,  -- success, failure, partial
                effectiveness REAL,     -- how effective was it
                recorded_at INTEGER NOT NULL,
                FOREIGN KEY (procedure_id) REFERENCES procedure_creations(id)
            )
        """)

        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_procedure_creations_name
            ON procedure_creations(procedure_name)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_procedure_creations_category
            ON procedure_creations(category)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_procedure_usage_procedure
            ON procedure_usage(procedure_id)
        """)

        # commit handled by cursor context

    def create_procedure_from_pattern(
        self,
        pattern_id: int,
        pattern_name: str,
        pattern_description: str,
        success_rate: float,
        lessons: list[str]
    ) -> Optional[int]:
        """Create procedure from consolidated pattern.

        Args:
            pattern_id: ID of source pattern
            pattern_name: Name of pattern
            pattern_description: Description
            success_rate: Success rate of pattern (0.0-1.0)
            lessons: Lessons learned from pattern

        Returns:
            Procedure creation ID, or None if skipped
        """
        # Only create procedures from high-confidence patterns
        if success_rate < 0.6:
            return None

        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp() * 1000)

        # Determine category based on pattern name
        category = self._infer_category(pattern_name)

        # Build template from lessons
        template = "\n".join([f"- {lesson}" for lesson in lessons])

        cursor.execute("""
            INSERT INTO procedure_creations
            (procedure_name, category, source_pattern_id, confidence,
             created_at, success_rate)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            pattern_name,
            category,
            pattern_id,
            success_rate,
            now,
            success_rate
        ))

        procedure_id = cursor.lastrowid
        # commit handled by cursor context
        return procedure_id

    def create_procedure_from_lesson(
        self,
        lesson_id: int,
        lesson_text: str,
        context: Optional[str] = None
    ) -> Optional[int]:
        """Create procedure directly from a lesson learned.

        Args:
            lesson_id: ID of lesson learned
            lesson_text: The lesson text
            context: Optional context about when this applies

        Returns:
            Procedure creation ID, or None if skipped
        """
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp() * 1000)

        # Extract procedure name from lesson
        procedure_name = self._extract_procedure_name(lesson_text)
        if not procedure_name:
            return None

        category = self._infer_category(procedure_name)

        cursor.execute("""
            INSERT INTO procedure_creations
            (procedure_name, category, source_lesson_id, confidence,
             created_at, success_rate)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            procedure_name,
            category,
            lesson_id,
            0.7,  # Default confidence for lesson-derived procedures
            now,
            0.5   # Start with neutral success rate
        ))

        procedure_id = cursor.lastrowid
        # commit handled by cursor context
        return procedure_id

    def record_procedure_usage(
        self,
        procedure_id: int,
        session_id: str,
        goal_id: Optional[str],
        outcome: str,  # success, failure, partial
        effectiveness: Optional[float] = None
    ) -> int:
        """Record usage of a procedure.

        Args:
            procedure_id: Procedure creation ID
            session_id: Session it was used in
            goal_id: Optional goal it was used for
            outcome: Usage outcome
            effectiveness: Optional effectiveness rating (0.0-1.0)

        Returns:
            Usage record ID
        """
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp() * 1000)

        cursor.execute("""
            INSERT INTO procedure_usage
            (procedure_id, used_in_session, used_for_goal, outcome,
             effectiveness, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            procedure_id,
            session_id,
            goal_id,
            outcome,
            effectiveness,
            now
        ))

        usage_id = cursor.lastrowid

        # Update procedure statistics
        self._update_procedure_stats(procedure_id)

        # commit handled by cursor context
        return usage_id

    def _update_procedure_stats(self, procedure_id: int):
        """Update success rate and usage stats for a procedure.

        Args:
            procedure_id: Procedure creation ID
        """
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp() * 1000)

        # Count uses
        cursor.execute("""
            SELECT COUNT(*), SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END)
            FROM procedure_usage
            WHERE procedure_id = ?
        """, (procedure_id,))

        row = cursor.fetchone()
        total_uses = row[0] or 0
        successful_uses = row[1] or 0

        success_rate = (successful_uses / total_uses) if total_uses > 0 else 0.5

        # Update procedure
        cursor.execute("""
            UPDATE procedure_creations
            SET total_uses = ?, successful_uses = ?, success_rate = ?,
                first_use_at = COALESCE(first_use_at, ?)
            WHERE id = ?
        """, (total_uses, successful_uses, success_rate, now, procedure_id))

    def get_procedure(self, procedure_id: int) -> Optional[dict]:
        """Get procedure details.

        Args:
            procedure_id: Procedure creation ID

        Returns:
            Procedure dict or None
        """
        cursor = self.db.get_cursor()

        cursor.execute("""
            SELECT id, procedure_name, category, confidence,
                   created_at, total_uses, successful_uses, success_rate
            FROM procedure_creations
            WHERE id = ?
        """, (procedure_id,))

        row = cursor.fetchone()
        if not row:
            return None

        return {
            "id": row[0],
            "name": row[1],
            "category": row[2],
            "confidence": row[3],
            "created_at": row[4],
            "total_uses": row[5],
            "successful_uses": row[6],
            "success_rate": row[7],
        }

    def get_procedures_by_category(self, category: str) -> list[dict]:
        """Get procedures in a category.

        Args:
            category: Procedure category

        Returns:
            List of procedure dicts
        """
        cursor = self.db.get_cursor()

        cursor.execute("""
            SELECT id, procedure_name, confidence, success_rate, total_uses
            FROM procedure_creations
            WHERE category = ?
            ORDER BY success_rate DESC
        """, (category,))

        procedures = []
        for row in cursor.fetchall():
            procedures.append({
                "id": row[0],
                "name": row[1],
                "confidence": row[2],
                "success_rate": row[3],
                "total_uses": row[4],
            })

        return procedures

    def get_creation_metrics(self) -> dict:
        """Get overall procedure creation metrics.

        Returns:
            Metrics dict
        """
        cursor = self.db.get_cursor()

        # Total procedures created
        cursor.execute("SELECT COUNT(*) FROM procedure_creations")
        total_created = cursor.fetchone()[0]

        # By category
        cursor.execute("""
            SELECT category, COUNT(*), AVG(success_rate)
            FROM procedure_creations
            GROUP BY category
        """)

        by_category = {}
        for row in cursor.fetchall():
            by_category[row[0]] = {
                "count": row[1],
                "average_success_rate": row[2],
            }

        # Usage metrics
        cursor.execute("""
            SELECT COUNT(*), SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END)
            FROM procedure_usage
        """)

        row = cursor.fetchone()
        total_uses = row[0] or 0
        successful_uses = row[1] or 0
        overall_success_rate = (successful_uses / total_uses) if total_uses > 0 else 0

        return {
            "total_procedures_created": total_created,
            "procedures_by_category": by_category,
            "total_procedure_uses": total_uses,
            "successful_uses": successful_uses,
            "overall_success_rate": overall_success_rate,
        }

    def _infer_category(self, name: str) -> str:
        """Infer procedure category from name.

        Args:
            name: Procedure name

        Returns:
            Category string
        """
        name_lower = name.lower()

        if any(x in name_lower for x in ["git", "commit", "push", "branch"]):
            return "git"
        elif any(x in name_lower for x in ["debug", "error", "fix", "troubleshoot"]):
            return "debugging"
        elif any(x in name_lower for x in ["test", "check", "verify", "assert"]):
            return "testing"
        elif any(x in name_lower for x in ["refactor", "clean", "reorganize"]):
            return "refactoring"
        elif any(x in name_lower for x in ["deploy", "release", "build"]):
            return "deployment"
        else:
            return "code_template"

    def _extract_procedure_name(self, lesson_text: str) -> Optional[str]:
        """Extract procedure name from lesson text.

        Args:
            lesson_text: Lesson text

        Returns:
            Extracted name or None
        """
        # Look for pattern like "Procedure: name" or "Use pattern: name"
        if ":" in lesson_text:
            parts = lesson_text.split(":")
            if len(parts) >= 2:
                return parts[1].strip().title()

        # Otherwise use first few words
        words = lesson_text.split()[:3]
        return "_".join(words).title() if words else None
