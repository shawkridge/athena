"""Storage and retrieval for project context."""

import json
import time
from datetime import datetime
from typing import Optional

from ..core.database import Database
from .project_context import Decision, ErrorPattern, ProjectContext, ProjectPhase


class ProjectContextStore:
    """Manages centralized project state.

    Provides:
    - Get/create project context
    - Update project phase and current goal
    - Track decisions made
    - Track error patterns and mitigations
    """

    def __init__(self, db: Database):
        """Initialize store with database connection.

        Args:
            db: Database instance
        """
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create tables if they don't exist."""
        cursor = self.db.conn.cursor()

        # Project contexts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_contexts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                current_phase TEXT NOT NULL DEFAULT 'planning',
                current_goal_id TEXT,
                architecture_json TEXT,
                completed_goal_count INTEGER DEFAULT 0,
                in_progress_goal_count INTEGER DEFAULT 0,
                blocked_goal_count INTEGER DEFAULT 0,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)

        # Decisions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                reasoning TEXT,
                alternatives_json TEXT,
                impact TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (project_id) REFERENCES project_contexts(project_id) ON DELETE CASCADE
            )
        """)

        # Error patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                error_type TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                last_seen INTEGER NOT NULL,
                mitigation TEXT,
                resolved BOOLEAN DEFAULT 0,
                FOREIGN KEY (project_id) REFERENCES project_contexts(project_id) ON DELETE CASCADE
            )
        """)

        # Indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_project_errors_type
            ON project_errors(project_id, error_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_project_decisions_created
            ON project_decisions(project_id, created_at DESC)
        """)

        self.db.conn.commit()

    def get_or_create(self, project_id: str, name: str, description: str = "") -> ProjectContext:
        """Get existing project context or create new one.

        Args:
            project_id: Unique project identifier
            name: Project name
            description: Project description

        Returns:
            ProjectContext instance
        """
        cursor = self.db.conn.cursor()

        # Try to get existing
        cursor.execute(
            "SELECT * FROM project_contexts WHERE project_id = ?",
            (project_id,)
        )
        row = cursor.fetchone()

        if row:
            return self._row_to_context(row)

        # Create new
        now = int(time.time() * 1000)  # Milliseconds for better precision
        cursor.execute("""
            INSERT INTO project_contexts
            (project_id, name, description, current_phase, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (project_id, name, description, ProjectPhase.PLANNING.value, now, now))

        self.db.conn.commit()

        cursor.execute(
            "SELECT * FROM project_contexts WHERE project_id = ?",
            (project_id,)
        )
        row = cursor.fetchone()
        return self._row_to_context(row)

    def get_context(self, project_id: str) -> Optional[ProjectContext]:
        """Retrieve project context.

        Args:
            project_id: Project identifier

        Returns:
            ProjectContext or None if not found
        """
        cursor = self.db.conn.cursor()
        cursor.execute(
            "SELECT * FROM project_contexts WHERE project_id = ?",
            (project_id,)
        )
        row = cursor.fetchone()
        return self._row_to_context(row) if row else None

    def update_phase(self, project_id: str, phase: ProjectPhase) -> None:
        """Update project phase.

        Args:
            project_id: Project identifier
            phase: New phase
        """
        cursor = self.db.conn.cursor()
        now = int(time.time() * 1000)  # Milliseconds for better precision

        cursor.execute("""
            UPDATE project_contexts
            SET current_phase = ?, updated_at = ?
            WHERE project_id = ?
        """, (phase.value, now, project_id))

        self.db.conn.commit()

    def update_goal(self, project_id: str, goal_id: Optional[str]) -> None:
        """Update current goal.

        Args:
            project_id: Project identifier
            goal_id: UUID of current goal, or None to clear
        """
        cursor = self.db.conn.cursor()
        now = int(time.time() * 1000)  # Milliseconds for better precision

        cursor.execute("""
            UPDATE project_contexts
            SET current_goal_id = ?, updated_at = ?
            WHERE project_id = ?
        """, (goal_id, now, project_id))

        self.db.conn.commit()

    def update_progress(
        self,
        project_id: str,
        completed: Optional[int] = None,
        in_progress: Optional[int] = None,
        blocked: Optional[int] = None,
    ) -> None:
        """Update goal progress counts.

        Args:
            project_id: Project identifier
            completed: Number of completed goals
            in_progress: Number of in-progress goals
            blocked: Number of blocked goals
        """
        cursor = self.db.conn.cursor()
        now = int(time.time() * 1000)  # Milliseconds for better precision

        updates = ["updated_at = ?"]
        params = [now]

        if completed is not None:
            updates.append("completed_goal_count = ?")
            params.append(completed)
        if in_progress is not None:
            updates.append("in_progress_goal_count = ?")
            params.append(in_progress)
        if blocked is not None:
            updates.append("blocked_goal_count = ?")
            params.append(blocked)

        params.append(project_id)

        cursor.execute(
            f"UPDATE project_contexts SET {', '.join(updates)} WHERE project_id = ?",
            params
        )

        self.db.conn.commit()

    def update_architecture(self, project_id: str, architecture: dict) -> None:
        """Update architecture documentation.

        Args:
            project_id: Project identifier
            architecture: Architecture dict (modules, entry_points, dependencies, etc.)
        """
        cursor = self.db.conn.cursor()
        now = int(time.time() * 1000)  # Milliseconds for better precision

        cursor.execute("""
            UPDATE project_contexts
            SET architecture_json = ?, updated_at = ?
            WHERE project_id = ?
        """, (json.dumps(architecture), now, project_id))

        self.db.conn.commit()

    def add_decision(self, decision: Decision) -> int:
        """Record a decision made in the project.

        Args:
            decision: Decision to record

        Returns:
            ID of inserted decision
        """
        cursor = self.db.conn.cursor()
        now = int(time.time() * 1000)  # Milliseconds for better precision

        cursor.execute("""
            INSERT INTO project_decisions
            (project_id, decision, reasoning, alternatives_json, impact, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            decision.project_id,
            decision.decision,
            decision.reasoning,
            json.dumps(decision.alternatives_considered),
            decision.impact,
            now
        ))

        self.db.conn.commit()
        return cursor.lastrowid

    def get_decisions(self, project_id: str, limit: int = 20) -> list[Decision]:
        """Get recent decisions for project.

        Args:
            project_id: Project identifier
            limit: Max decisions to return

        Returns:
            List of Decision instances
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM project_decisions
            WHERE project_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (project_id, limit))

        return [self._row_to_decision(row) for row in cursor.fetchall()]

    def track_error(self, error: ErrorPattern) -> None:
        """Track an error pattern.

        Args:
            error: ErrorPattern to track
        """
        cursor = self.db.conn.cursor()

        # Check if error already exists
        cursor.execute("""
            SELECT id FROM project_errors
            WHERE project_id = ? AND error_type = ?
        """, (error.project_id, error.error_type))

        existing = cursor.fetchone()

        if existing:
            # Update existing error
            now = int(time.time())
            cursor.execute("""
                UPDATE project_errors
                SET frequency = frequency + 1, last_seen = ?, mitigation = ?, resolved = ?
                WHERE id = ?
            """, (now, error.mitigation, error.resolved, existing[0]))
        else:
            # Create new error entry
            now = int(time.time())
            cursor.execute("""
                INSERT INTO project_errors
                (project_id, error_type, frequency, last_seen, mitigation, resolved)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                error.project_id,
                error.error_type,
                error.frequency,
                now,
                error.mitigation,
                error.resolved
            ))

        self.db.conn.commit()

    def get_error_patterns(self, project_id: str, unresolved_only: bool = True) -> list[ErrorPattern]:
        """Get error patterns for project.

        Args:
            project_id: Project identifier
            unresolved_only: If True, only return unresolved errors

        Returns:
            List of ErrorPattern instances
        """
        cursor = self.db.conn.cursor()

        if unresolved_only:
            cursor.execute("""
                SELECT * FROM project_errors
                WHERE project_id = ? AND resolved = 0
                ORDER BY frequency DESC
            """, (project_id,))
        else:
            cursor.execute("""
                SELECT * FROM project_errors
                WHERE project_id = ?
                ORDER BY frequency DESC
            """, (project_id,))

        return [self._row_to_error(row) for row in cursor.fetchall()]

    def mark_error_resolved(self, error_id: int) -> None:
        """Mark an error pattern as resolved.

        Args:
            error_id: ID of error to mark resolved
        """
        cursor = self.db.conn.cursor()

        cursor.execute("""
            UPDATE project_errors
            SET resolved = 1
            WHERE id = ?
        """, (error_id,))

        self.db.conn.commit()

    def _row_to_context(self, row: tuple) -> ProjectContext:
        """Convert database row to ProjectContext.

        Args:
            row: Database row tuple

        Returns:
            ProjectContext instance
        """
        return ProjectContext(
            id=row[0],
            project_id=row[1],
            name=row[2],
            description=row[3],
            current_phase=row[4],
            current_goal_id=row[5],
            architecture=json.loads(row[6]) if row[6] else None,
            completed_goal_count=row[7],
            in_progress_goal_count=row[8],
            blocked_goal_count=row[9],
            created_at=datetime.fromtimestamp(row[10] / 1000),  # Convert milliseconds to seconds
            updated_at=datetime.fromtimestamp(row[11] / 1000),  # Convert milliseconds to seconds
        )

    def _row_to_decision(self, row: tuple) -> Decision:
        """Convert database row to Decision.

        Args:
            row: Database row tuple

        Returns:
            Decision instance
        """
        return Decision(
            id=row[0],
            project_id=row[1],
            decision=row[2],
            reasoning=row[3],
            alternatives_considered=json.loads(row[4]) if row[4] else [],
            impact=row[5],
            created_at=datetime.fromtimestamp(row[6] / 1000),  # Convert milliseconds to seconds
        )

    def _row_to_error(self, row: tuple) -> ErrorPattern:
        """Convert database row to ErrorPattern.

        Args:
            row: Database row tuple

        Returns:
            ErrorPattern instance
        """
        return ErrorPattern(
            id=row[0],
            project_id=row[1],
            error_type=row[2],
            frequency=row[3],
            last_seen=datetime.fromtimestamp(row[4] / 1000),  # Convert milliseconds to seconds
            mitigation=row[5],
            resolved=bool(row[6]),
        )
