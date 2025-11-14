"""Storage and retrieval for code context."""

import json
import time
from datetime import datetime, timedelta
from typing import Optional

from ..core.database import Database
from .code_context import (
    CodeContext,
    DependencyType,
    FileDependency,
    FileInfo,
    FileRole,
    IssueStatus,
    IssueSeverity,
    KnownIssue,
    RecentChange,
)


class CodeContextStore:
    """Manages code context for tasks.

    Provides:
    - Create and retrieve code contexts for tasks
    - Track relevant files with relevance scoring
    - Manage file dependencies
    - Track recent changes
    - Track known issues
    - Context expiration and refresh
    """

    def __init__(self, db: Database):
        """Initialize store with database connection.

        Args:
            db: Database instance
        """
        self.db = db
    def _ensure_schema(self) -> None:
        """Create tables if they don't exist."""
        cursor = self.db.get_cursor()

        # Code contexts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS code_contexts (
                id SERIAL PRIMARY KEY,
                goal_id TEXT,
                task_id TEXT,
                session_id TEXT NOT NULL,
                architecture_notes TEXT,
                created_at INTEGER NOT NULL,
                expires_at INTEGER,
                last_refreshed INTEGER,
                consolidation_status TEXT DEFAULT 'unconsolidated',
                consolidated_at INTEGER
            )
        """)

        # Relevant files table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS code_context_files (
                id SERIAL PRIMARY KEY,
                context_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                relevance REAL DEFAULT 0.5,
                file_role TEXT DEFAULT 'implementation',
                lines_changed INTEGER DEFAULT 0,
                last_modified INTEGER,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (context_id) REFERENCES code_contexts(id)
            )
        """)

        # Dependencies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS code_dependencies (
                id SERIAL PRIMARY KEY,
                context_id INTEGER NOT NULL,
                from_file TEXT NOT NULL,
                to_file TEXT NOT NULL,
                dependency_type TEXT NOT NULL,
                description TEXT,
                strength REAL DEFAULT 0.5,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (context_id) REFERENCES code_contexts(id)
            )
        """)

        # Recent changes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS code_recent_changes (
                id SERIAL PRIMARY KEY,
                context_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                change_timestamp INTEGER NOT NULL,
                change_summary TEXT NOT NULL,
                author TEXT,
                session_id TEXT,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (context_id) REFERENCES code_contexts(id)
            )
        """)

        # Known issues table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS code_known_issues (
                id SERIAL PRIMARY KEY,
                context_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                issue TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                found_at INTEGER NOT NULL,
                resolution_notes TEXT,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (context_id) REFERENCES code_contexts(id)
            )
        """)

        # Indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_code_contexts_task
            ON code_contexts(task_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_code_contexts_goal
            ON code_contexts(goal_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_code_contexts_session
            ON code_contexts(session_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_code_context_files_context
            ON code_context_files(context_id, relevance DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_code_context_files_path
            ON code_context_files(file_path)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_code_dependencies_context
            ON code_dependencies(context_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_code_dependencies_files
            ON code_dependencies(from_file, to_file)
        """)

        # commit handled by cursor context

    def create_context(
        self,
        session_id: str,
        goal_id: Optional[str] = None,
        task_id: Optional[str] = None,
        architecture_notes: Optional[str] = None,
        expires_in_hours: int = 24,
    ) -> int:
        """Create a new code context.

        Args:
            session_id: Session ID
            goal_id: Optional goal ID
            task_id: Optional task ID
            architecture_notes: Optional architecture notes
            expires_in_hours: Hours until context expires

        Returns:
            ID of created context
        """
        cursor = self.db.get_cursor()
        now = int(time.time() * 1000)  # Milliseconds
        expires_at = now + (expires_in_hours * 3600 * 1000)

        cursor.execute("""
            INSERT INTO code_contexts
            (goal_id, task_id, session_id, architecture_notes, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (goal_id, task_id, session_id, architecture_notes, now, expires_at))

        # commit handled by cursor context
        return cursor.lastrowid

    def get_context(self, context_id: int) -> Optional[CodeContext]:
        """Retrieve a code context.

        Args:
            context_id: Context ID

        Returns:
            CodeContext or None if not found
        """
        cursor = self.db.get_cursor()
        cursor.execute("SELECT * FROM code_contexts WHERE id = ?", (context_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_context(row)

    def get_context_for_task(self, task_id: str) -> Optional[CodeContext]:
        """Get code context for a task.

        Args:
            task_id: Task ID (UUID as string)

        Returns:
            CodeContext or None
        """
        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT * FROM code_contexts WHERE task_id = ? ORDER BY created_at DESC LIMIT 1",
            (task_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_context(row)

    def get_context_for_goal(self, goal_id: str) -> list[CodeContext]:
        """Get all code contexts for a goal.

        Args:
            goal_id: Goal ID (UUID as string)

        Returns:
            List of CodeContexts
        """
        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT * FROM code_contexts WHERE goal_id = ? ORDER BY created_at DESC",
            (goal_id,)
        )
        return [self._row_to_context(row) for row in cursor.fetchall()]

    def add_relevant_file(
        self,
        context_id: int,
        file_path: str,
        relevance: float = 0.5,
        role: FileRole = FileRole.IMPLEMENTATION,
        lines_changed: int = 0,
        last_modified: Optional[datetime] = None,
    ) -> int:
        """Add a relevant file to context.

        Args:
            context_id: Context ID
            file_path: Relative file path
            relevance: Relevance score (0.0-1.0)
            role: Role of file in task
            lines_changed: Lines changed in this task
            last_modified: Last modification timestamp

        Returns:
            ID of file entry
        """
        cursor = self.db.get_cursor()
        now = int(time.time() * 1000)
        role_value = role.value if hasattr(role, "value") else role

        last_mod_ms = None
        if last_modified:
            last_mod_ms = int(last_modified.timestamp() * 1000)

        cursor.execute("""
            INSERT INTO code_context_files
            (context_id, file_path, relevance, file_role, lines_changed, last_modified, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (context_id, file_path, relevance, role_value, lines_changed, last_mod_ms, now))

        # commit handled by cursor context
        return cursor.lastrowid

    def get_relevant_files(
        self,
        context_id: int,
        min_relevance: float = 0.0,
    ) -> list[FileInfo]:
        """Get relevant files for context.

        Args:
            context_id: Context ID
            min_relevance: Minimum relevance threshold (0.0-1.0)

        Returns:
            List of FileInfo sorted by relevance descending
        """
        cursor = self.db.get_cursor()
        cursor.execute("""
            SELECT file_path, relevance, file_role, lines_changed, last_modified
            FROM code_context_files
            WHERE context_id = ? AND relevance >= ?
            ORDER BY relevance DESC
        """, (context_id, min_relevance))

        files = []
        for row in cursor.fetchall():
            path, relevance, role, lines_changed, last_mod = row
            last_modified = None
            if last_mod:
                last_modified = datetime.fromtimestamp(last_mod / 1000)

            files.append(FileInfo(
                path=path,
                relevance=relevance,
                role=FileRole(role),
                lines_changed=lines_changed,
                last_modified=last_modified,
            ))
        return files

    def add_dependency(
        self,
        context_id: int,
        from_file: str,
        to_file: str,
        dependency_type: DependencyType,
        description: Optional[str] = None,
        strength: float = 0.5,
    ) -> int:
        """Add a dependency between files.

        Args:
            context_id: Context ID
            from_file: Source file path
            to_file: Target file path
            dependency_type: Type of dependency
            description: Optional description
            strength: Dependency strength (0.0-1.0)

        Returns:
            ID of dependency entry
        """
        cursor = self.db.get_cursor()
        now = int(time.time() * 1000)
        dep_type_value = dependency_type.value if hasattr(dependency_type, "value") else dependency_type

        cursor.execute("""
            INSERT INTO code_dependencies
            (context_id, from_file, to_file, dependency_type, description, strength, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (context_id, from_file, to_file, dep_type_value, description, strength, now))

        # commit handled by cursor context
        return cursor.lastrowid

    def get_dependencies(self, context_id: int) -> list[FileDependency]:
        """Get all dependencies in context.

        Args:
            context_id: Context ID

        Returns:
            List of FileDependencies
        """
        cursor = self.db.get_cursor()
        cursor.execute("""
            SELECT from_file, to_file, dependency_type, description, strength
            FROM code_dependencies
            WHERE context_id = ?
            ORDER BY strength DESC
        """, (context_id,))

        deps = []
        for row in cursor.fetchall():
            from_file, to_file, dep_type, description, strength = row
            deps.append(FileDependency(
                from_file=from_file,
                to_file=to_file,
                dependency_type=DependencyType(dep_type),
                description=description,
                strength=strength,
            ))
        return deps

    def get_dependencies_for_file(self, context_id: int, file_path: str) -> list[FileDependency]:
        """Get dependencies involving a specific file.

        Args:
            context_id: Context ID
            file_path: File path to query

        Returns:
            List of dependencies (both to and from the file)
        """
        cursor = self.db.get_cursor()
        cursor.execute("""
            SELECT from_file, to_file, dependency_type, description, strength
            FROM code_dependencies
            WHERE context_id = ? AND (from_file = ? OR to_file = ?)
            ORDER BY strength DESC
        """, (context_id, file_path, file_path))

        deps = []
        for row in cursor.fetchall():
            from_file, to_file, dep_type, description, strength = row
            deps.append(FileDependency(
                from_file=from_file,
                to_file=to_file,
                dependency_type=DependencyType(dep_type),
                description=description,
                strength=strength,
            ))
        return deps

    def add_recent_change(
        self,
        context_id: int,
        file_path: str,
        change_summary: str,
        timestamp: Optional[datetime] = None,
        author: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> int:
        """Add a recent change to context.

        Args:
            context_id: Context ID
            file_path: File path
            change_summary: Summary of change
            timestamp: Timestamp of change (defaults to now)
            author: Author of change
            session_id: Session ID that made change

        Returns:
            ID of change entry
        """
        cursor = self.db.get_cursor()
        now = int(time.time() * 1000)

        if timestamp is None:
            timestamp = datetime.now()
        change_ts = int(timestamp.timestamp() * 1000)

        cursor.execute("""
            INSERT INTO code_recent_changes
            (context_id, file_path, change_timestamp, change_summary, author, session_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (context_id, file_path, change_ts, change_summary, author, session_id, now))

        # commit handled by cursor context
        return cursor.lastrowid

    def get_recent_changes(self, context_id: int, limit: int = 20) -> list[RecentChange]:
        """Get recent changes in context.

        Args:
            context_id: Context ID
            limit: Maximum number to return

        Returns:
            List of recent changes sorted by timestamp descending
        """
        cursor = self.db.get_cursor()
        cursor.execute("""
            SELECT file_path, change_timestamp, change_summary, author, session_id
            FROM code_recent_changes
            WHERE context_id = ?
            ORDER BY change_timestamp DESC
            LIMIT ?
        """, (context_id, limit))

        changes = []
        for row in cursor.fetchall():
            path, change_ts, summary, author, session_id = row
            changes.append(RecentChange(
                file_path=path,
                timestamp=datetime.fromtimestamp(change_ts / 1000),
                change_summary=summary,
                author=author,
                session_id=session_id,
            ))
        return changes

    def add_known_issue(
        self,
        context_id: int,
        file_path: str,
        issue: str,
        severity: IssueSeverity,
        status: IssueStatus = IssueStatus.OPEN,
        found_at: Optional[datetime] = None,
        resolution_notes: Optional[str] = None,
    ) -> int:
        """Add a known issue to context.

        Args:
            context_id: Context ID
            file_path: File path with issue
            issue: Issue description
            severity: Issue severity
            status: Issue status
            found_at: When issue was found (defaults to now)
            resolution_notes: Optional resolution notes

        Returns:
            ID of issue entry
        """
        cursor = self.db.get_cursor()
        now = int(time.time() * 1000)

        if found_at is None:
            found_at = datetime.now()
        found_ts = int(found_at.timestamp() * 1000)

        severity_value = severity.value if hasattr(severity, "value") else severity
        status_value = status.value if hasattr(status, "value") else status

        cursor.execute("""
            INSERT INTO code_known_issues
            (context_id, file_path, issue, severity, status, found_at, resolution_notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (context_id, file_path, issue, severity_value, status_value, found_ts, resolution_notes, now))

        # commit handled by cursor context
        return cursor.lastrowid

    def get_known_issues(
        self,
        context_id: int,
        status_filter: Optional[IssueStatus] = None,
    ) -> list[KnownIssue]:
        """Get known issues in context.

        Args:
            context_id: Context ID
            status_filter: Optional status filter

        Returns:
            List of known issues
        """
        cursor = self.db.get_cursor()

        if status_filter:
            status_value = status_filter.value if hasattr(status_filter, "value") else status_filter
            cursor.execute("""
                SELECT file_path, issue, severity, status, found_at, resolution_notes
                FROM code_known_issues
                WHERE context_id = ? AND status = ?
                ORDER BY severity DESC, found_at DESC
            """, (context_id, status_value))
        else:
            cursor.execute("""
                SELECT file_path, issue, severity, status, found_at, resolution_notes
                FROM code_known_issues
                WHERE context_id = ?
                ORDER BY severity DESC, found_at DESC
            """, (context_id,))

        issues = []
        for row in cursor.fetchall():
            path, issue, severity, status, found_ts, notes = row
            issues.append(KnownIssue(
                file_path=path,
                issue=issue,
                severity=IssueSeverity(severity),
                status=IssueStatus(status),
                found_at=datetime.fromtimestamp(found_ts / 1000),
                resolution_notes=notes,
            ))
        return issues

    def is_context_stale(self, context_id: int) -> bool:
        """Check if context has expired.

        Args:
            context_id: Context ID

        Returns:
            True if context is expired, False otherwise
        """
        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT expires_at FROM code_contexts WHERE id = ?",
            (context_id,)
        )
        row = cursor.fetchone()
        if not row or row[0] is None:
            return False

        expires_at = row[0]
        now = int(time.time() * 1000)
        return now > expires_at

    def refresh_context(
        self,
        context_id: int,
        expires_in_hours: int = 24,
    ) -> None:
        """Refresh context expiration.

        Args:
            context_id: Context ID
            expires_in_hours: New expiration window
        """
        cursor = self.db.get_cursor()
        now = int(time.time() * 1000)
        expires_at = now + (expires_in_hours * 3600 * 1000)

        cursor.execute("""
            UPDATE code_contexts
            SET expires_at = ?, last_refreshed = ?
            WHERE id = ?
        """, (expires_at, now, context_id))

        # commit handled by cursor context

    def mark_consolidated(self, context_id: int) -> None:
        """Mark a code context as consolidated.

        Args:
            context_id: Context ID
        """
        cursor = self.db.get_cursor()
        now = int(time.time() * 1000)
        cursor.execute("""
            UPDATE code_contexts
            SET consolidation_status = 'consolidated', consolidated_at = ?
            WHERE id = ?
        """, (now, context_id))
        # commit handled by cursor context

    def get_unconsolidated_contexts(
        self,
        goal_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[CodeContext]:
        """Get unconsolidated code contexts.

        Args:
            goal_id: Optional filter by goal
            limit: Maximum number to return

        Returns:
            List of unconsolidated CodeContexts
        """
        cursor = self.db.get_cursor()

        if goal_id:
            cursor.execute("""
                SELECT * FROM code_contexts
                WHERE consolidation_status = 'unconsolidated' AND goal_id = ?
                ORDER BY created_at ASC
                LIMIT ?
            """, (goal_id, limit))
        else:
            cursor.execute("""
                SELECT * FROM code_contexts
                WHERE consolidation_status = 'unconsolidated'
                ORDER BY created_at ASC
                LIMIT ?
            """, (limit,))

        return [self._row_to_context(row) for row in cursor.fetchall()]

    def _row_to_context(self, row: tuple) -> CodeContext:
        """Convert database row to CodeContext object.

        Args:
            row: Database row tuple

        Returns:
            CodeContext instance
        """
        (
            id_,
            goal_id,
            task_id,
            session_id,
            architecture_notes,
            created_at,
            expires_at,
            last_refreshed,
            consolidation_status,
            consolidated_at,
        ) = row

        # Retrieve related data
        cursor = self.db.get_cursor()

        # Get relevant files
        cursor.execute(
            "SELECT file_path, relevance, file_role, lines_changed, last_modified FROM code_context_files WHERE context_id = ? ORDER BY relevance DESC",
            (id_,)
        )
        relevant_files = []
        for file_row in cursor.fetchall():
            path, relevance, role, lines_changed, last_mod = file_row
            last_modified = None
            if last_mod:
                last_modified = datetime.fromtimestamp(last_mod / 1000)
            relevant_files.append(FileInfo(
                path=path,
                relevance=relevance,
                role=FileRole(role),
                lines_changed=lines_changed,
                last_modified=last_modified,
            ))

        # Get dependencies
        cursor.execute(
            "SELECT from_file, to_file, dependency_type, description, strength FROM code_dependencies WHERE context_id = ? ORDER BY strength DESC",
            (id_,)
        )
        dependencies = []
        for dep_row in cursor.fetchall():
            from_file, to_file, dep_type, description, strength = dep_row
            dependencies.append(FileDependency(
                from_file=from_file,
                to_file=to_file,
                dependency_type=DependencyType(dep_type),
                description=description,
                strength=strength,
            ))

        # Get recent changes
        cursor.execute(
            "SELECT file_path, change_timestamp, change_summary, author, session_id FROM code_recent_changes WHERE context_id = ? ORDER BY change_timestamp DESC LIMIT 20",
            (id_,)
        )
        recent_changes = []
        for change_row in cursor.fetchall():
            path, change_ts, summary, author, session_id = change_row
            recent_changes.append(RecentChange(
                file_path=path,
                timestamp=datetime.fromtimestamp(change_ts / 1000),
                change_summary=summary,
                author=author,
                session_id=session_id,
            ))

        # Get known issues
        cursor.execute(
            "SELECT file_path, issue, severity, status, found_at, resolution_notes FROM code_known_issues WHERE context_id = ? ORDER BY severity DESC",
            (id_,)
        )
        known_issues = []
        for issue_row in cursor.fetchall():
            path, issue, severity, status, found_ts, notes = issue_row
            known_issues.append(KnownIssue(
                file_path=path,
                issue=issue,
                severity=IssueSeverity(severity),
                status=IssueStatus(status),
                found_at=datetime.fromtimestamp(found_ts / 1000),
                resolution_notes=notes,
            ))

        return CodeContext(
            id=id_,
            goal_id=goal_id,
            task_id=task_id,
            relevant_files=relevant_files,
            dependencies=dependencies,
            architecture_notes=architecture_notes,
            recent_changes=recent_changes,
            known_issues=known_issues,
            session_id=session_id,
            created_at=datetime.fromtimestamp(created_at / 1000),
            expires_at=datetime.fromtimestamp(expires_at / 1000) if expires_at else None,
            last_refreshed=datetime.fromtimestamp(last_refreshed / 1000) if last_refreshed else None,
            consolidation_status=consolidation_status,
            consolidated_at=datetime.fromtimestamp(consolidated_at / 1000) if consolidated_at else None,
        )
