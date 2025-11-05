"""Storage for session snapshots and resumption support."""

import json
import time
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from ..core.database import Database
from ..core.base_store import BaseStore
from .session_continuity import (
    ActionCycleSnapshot,
    CodeContextSnapshot,
    ExecutionTraceSnapshot,
    ProjectContextSnapshot,
    ResumptionRecommendation,
    SessionMetadata,
    SessionSnapshot,
    SessionStatus,
)


class SessionContinuityStore(BaseStore[SessionSnapshot]):
    """Manages session snapshots and resumption operations.

    Provides:
    - Save complete session state (project, cycles, code context, execution history)
    - Load and restore session snapshots
    - Get resumption recommendations
    - Track session metadata for quick lookup
    - Version management for compatibility
    """

    table_name = "session_snapshots"
    model_class = SessionSnapshot

    def __init__(self, db: Database):
        """Initialize store with database connection.

        Args:
            db: Database instance
        """
        super().__init__(db)
        self._ensure_schema()

    def _row_to_model(self, row: Dict[str, Any]) -> SessionSnapshot:
        """Convert database row to SessionSnapshot model.

        Args:
            row: Database row as dict

        Returns:
            SessionSnapshot instance
        """
        # Deserialize nested models from JSON
        project_snapshot = ProjectContextSnapshot.model_validate_json(row["project_snapshot_json"])
        active_cycle = None
        if row.get("active_cycle_snapshot_json"):
            active_cycle = ActionCycleSnapshot.model_validate_json(row["active_cycle_snapshot_json"])
        code_context = None
        if row.get("code_context_snapshot_json"):
            code_context = CodeContextSnapshot.model_validate_json(row["code_context_snapshot_json"])
        executions = []
        if row.get("recent_executions_json"):
            exec_dicts = self.deserialize_json(row["recent_executions_json"], [])
            executions = [ExecutionTraceSnapshot.model_validate(e) for e in exec_dicts]
        recommendation = ResumptionRecommendation.model_validate_json(row["resumption_recommendation_json"])
        goals = self.deserialize_json(row.get("goals_at_snapshot_time_json"), [])

        return SessionSnapshot(
            snapshot_id=row["snapshot_id"],
            session_id=row["session_id"],
            version=row.get("version", 1),
            status=SessionStatus(row["status"]),
            created_at=self.from_timestamp(row["created_at"]),
            created_by=row.get("created_by", "user"),
            project_snapshot=project_snapshot,
            active_cycle_snapshot=active_cycle,
            code_context_snapshot=code_context,
            recent_executions=executions,
            resumption_recommendation=recommendation,
            goals_at_snapshot=goals,
            time_in_session_seconds=row.get("time_in_session_seconds", 0),
            primary_objective=row.get("primary_objective"),
            notes=row.get("notes"),
        )

    def _ensure_schema(self) -> None:
        """Create tables if they don't exist."""
        cursor = self.db.conn.cursor()

        # Session snapshots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id TEXT UNIQUE NOT NULL,
                session_id TEXT NOT NULL,
                version INTEGER DEFAULT 1,
                status TEXT DEFAULT 'paused',
                created_at INTEGER NOT NULL,
                created_by TEXT DEFAULT 'user',
                project_snapshot_json TEXT NOT NULL,
                active_cycle_snapshot_json TEXT,
                code_context_snapshot_json TEXT,
                recent_executions_json TEXT,
                resumption_recommendation_json TEXT NOT NULL,
                goals_at_snapshot_time_json TEXT,
                time_in_session_seconds INTEGER DEFAULT 0,
                primary_objective TEXT,
                notes TEXT,
                consolidated_at INTEGER
            )
        """)

        # Session metadata table (for quick lookup)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id TEXT UNIQUE NOT NULL,
                project_id TEXT NOT NULL,
                project_name TEXT NOT NULL,
                status TEXT DEFAULT 'paused',
                created_at INTEGER NOT NULL,
                active_goal_count INTEGER DEFAULT 0,
                active_cycle_id INTEGER,
                resumption_reason TEXT NOT NULL,
                time_since_last_activity_minutes INTEGER DEFAULT 0,
                FOREIGN KEY (snapshot_id) REFERENCES session_snapshots(snapshot_id)
            )
        """)

        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_snapshots_snapshot_id
            ON session_snapshots(snapshot_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_snapshots_session_id
            ON session_snapshots(session_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_metadata_project_id
            ON session_metadata(project_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_metadata_created_at
            ON session_metadata(created_at DESC)
        """)

        self.db.conn.commit()

    def save_session(
        self,
        session_id: str,
        project_snapshot: ProjectContextSnapshot,
        active_cycle_snapshot: Optional[ActionCycleSnapshot] = None,
        code_context_snapshot: Optional[CodeContextSnapshot] = None,
        recent_executions: Optional[list[ExecutionTraceSnapshot]] = None,
        resumption_recommendation: Optional[ResumptionRecommendation] = None,
        goals_at_snapshot: Optional[list[str]] = None,
        time_in_session_seconds: int = 0,
        primary_objective: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> SessionSnapshot:
        """Save a complete session snapshot.

        Args:
            session_id: Unique session identifier
            project_snapshot: Current project context snapshot
            active_cycle_snapshot: Currently active action cycle (if any)
            code_context_snapshot: Task-scoped code context (if any)
            recent_executions: Recent execution traces (last 10-20)
            resumption_recommendation: Guidance for resuming
            goals_at_snapshot: List of active goals
            time_in_session_seconds: How long this session has run
            primary_objective: What the primary goal is
            notes: User-provided context

        Returns:
            SessionSnapshot: The saved snapshot with ID
        """
        if resumption_recommendation is None:
            resumption_recommendation = ResumptionRecommendation(
                recommended_next_action="Resume normal work flow",
                reason="No specific recommendation",
            )

        snapshot_id = str(uuid4())
        now_timestamp = int(time.time())

        # Create the snapshot object
        snapshot = SessionSnapshot(
            snapshot_id=snapshot_id,
            session_id=session_id,
            version=1,
            status=SessionStatus.PAUSED,
            created_at=datetime.fromtimestamp(now_timestamp),
            project_snapshot=project_snapshot,
            active_cycle_snapshot=active_cycle_snapshot,
            code_context_snapshot=code_context_snapshot,
            recent_executions=recent_executions or [],
            resumption_recommendation=resumption_recommendation,
            goals_at_snapshot=goals_at_snapshot or [],
            time_in_session_seconds=time_in_session_seconds,
            primary_objective=primary_objective,
            notes=notes,
        )

        # Serialize nested models
        project_json = project_snapshot.model_dump_json()
        cycle_json = active_cycle_snapshot.model_dump_json() if active_cycle_snapshot else None
        code_json = code_context_snapshot.model_dump_json() if code_context_snapshot else None
        executions_json = self.serialize_json(
            [e.model_dump(mode="json") for e in (recent_executions or [])]
        )
        recommendation_json = resumption_recommendation.model_dump_json()
        goals_json = self.serialize_json(goals_at_snapshot or [])

        # Insert into session_snapshots (using BaseStore.execute())
        self.execute(
            """
            INSERT INTO session_snapshots (
                snapshot_id, session_id, version, status, created_at, created_by,
                project_snapshot_json, active_cycle_snapshot_json, code_context_snapshot_json,
                recent_executions_json, resumption_recommendation_json,
                goals_at_snapshot_time_json, time_in_session_seconds,
                primary_objective, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                session_id,
                1,
                SessionStatus.PAUSED.value,
                now_timestamp,
                "user",
                project_json,
                cycle_json,
                code_json,
                executions_json,
                recommendation_json,
                goals_json,
                time_in_session_seconds,
                primary_objective,
                notes,
            ),
        )

        # Create metadata entry (using BaseStore.execute())
        self.execute(
            """
            INSERT INTO session_metadata (
                snapshot_id, project_id, project_name, status, created_at,
                active_goal_count, active_cycle_id, resumption_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                project_snapshot.project_id,
                project_snapshot.project_name,
                SessionStatus.PAUSED.value,
                now_timestamp,
                len(goals_at_snapshot or []),
                active_cycle_snapshot.cycle_id if active_cycle_snapshot else None,
                "session_pause",
            ),
        )

        self.commit()
        return snapshot

    def load_session(self, snapshot_id: str) -> Optional[SessionSnapshot]:
        """Load a session snapshot by ID.

        Args:
            snapshot_id: Unique snapshot identifier

        Returns:
            SessionSnapshot if found, None otherwise
        """
        row = self.execute(
            """
            SELECT
                snapshot_id, session_id, version, status, created_at, created_by,
                project_snapshot_json, active_cycle_snapshot_json, code_context_snapshot_json,
                recent_executions_json, resumption_recommendation_json,
                goals_at_snapshot_time_json, time_in_session_seconds,
                primary_objective, notes
            FROM session_snapshots WHERE snapshot_id = ?
            """,
            (snapshot_id,),
            fetch_one=True
        )
        if not row:
            return None

        # Use _row_to_model() helper from BaseStore
        return self._row_to_model(row)

    def get_resumption_hints(self, snapshot_id: str) -> Optional[ResumptionRecommendation]:
        """Get resumption recommendations for a snapshot.

        Args:
            snapshot_id: Snapshot to get hints for

        Returns:
            ResumptionRecommendation if found, None otherwise
        """
        row = self.execute(
            """
            SELECT resumption_recommendation_json FROM session_snapshots
            WHERE snapshot_id = ?
            """,
            (snapshot_id,),
            fetch_one=True
        )
        if not row or not row[0]:
            return None

        return ResumptionRecommendation.model_validate_json(row[0])

    def list_sessions(
        self, project_id: Optional[str] = None, limit: int = 10
    ) -> list[SessionMetadata]:
        """List saved session metadata.

        Args:
            project_id: Filter by project (optional)
            limit: Maximum number to return

        Returns:
            List of SessionMetadata objects
        """
        if project_id:
            rows = self.execute(
                """
                SELECT
                    id, snapshot_id, project_id, project_name, status, created_at,
                    active_goal_count, active_cycle_id, resumption_reason,
                    time_since_last_activity_minutes
                FROM session_metadata
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (project_id, limit),
                fetch_all=True
            )
        else:
            rows = self.execute(
                """
                SELECT
                    id, snapshot_id, project_id, project_name, status, created_at,
                    active_goal_count, active_cycle_id, resumption_reason,
                    time_since_last_activity_minutes
                FROM session_metadata
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
                fetch_all=True
            )

        results = []
        for row in rows:
            metadata = SessionMetadata(
                id=row[0],
                snapshot_id=row[1],
                project_id=row[2],
                project_name=row[3],
                status=SessionStatus(row[4]),
                created_at=self.from_timestamp(row[5]),
                active_goal_count=row[6],
                active_cycle_id=row[7],
                resumption_reason=row[8],
                time_since_last_activity_minutes=row[9],
            )
            results.append(metadata)

        return results

    def get_latest_session(self, session_id: str) -> Optional[SessionSnapshot]:
        """Get the most recent snapshot for a session.

        Args:
            session_id: Session identifier

        Returns:
            Most recent SessionSnapshot if found, None otherwise
        """
        row = self.execute(
            """
            SELECT snapshot_id FROM session_snapshots
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (session_id,),
            fetch_one=True
        )
        if not row:
            return None

        return self.load_session(row[0])

    def mark_session_resumed(self, snapshot_id: str) -> bool:
        """Mark a snapshot as resumed (update status).

        Args:
            snapshot_id: Snapshot that was resumed

        Returns:
            True if updated successfully
        """
        now_timestamp = int(time.time())
        cursor = self.execute(
            """
            UPDATE session_snapshots
            SET status = ?, consolidated_at = ?
            WHERE snapshot_id = ?
            """,
            (SessionStatus.RESUMED.value, now_timestamp, snapshot_id),
        )
        self.execute(
            """
            UPDATE session_metadata
            SET status = ?
            WHERE snapshot_id = ?
            """,
            (SessionStatus.RESUMED.value, snapshot_id),
        )
        self.commit()
        return cursor.rowcount > 0

    def delete_session(self, snapshot_id: str) -> bool:
        """Delete a session snapshot and its metadata.

        Args:
            snapshot_id: Snapshot to delete

        Returns:
            True if deleted successfully
        """
        self.execute("DELETE FROM session_metadata WHERE snapshot_id = ?", (snapshot_id,))
        cursor = self.execute("DELETE FROM session_snapshots WHERE snapshot_id = ?", (snapshot_id,))
        self.commit()
        return cursor.rowcount > 0
