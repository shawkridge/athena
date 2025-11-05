"""Database store for IDE context and state."""

import json
from typing import Optional

from ..core.database import Database
from ..core.base_store import BaseStore

from .models import (
    CursorPosition,
    FileOpenMode,
    GitChangeType,
    GitDiff,
    GitStatus,
    IDEActivity,
    IDEContextSnapshot,
    IDEFile,
)


class IDEContextStore(BaseStore):
    """Store for managing IDE context and state."""

    table_name = "ide_files"
    model_class = IDEFile

    def __init__(self, db: Database):
        """Initialize store with database connection."""
        super().__init__(db)
        self._ensure_schema()

    def _row_to_model(self, row) -> IDEFile:
        """Convert database row to IDEFile model.

        Args:
            row: Database row (sqlite3.Row or dict)

        Returns:
            IDEFile instance
        """
        # Convert Row to dict if needed
        row_dict = dict(row) if hasattr(row, 'keys') else row
        return self._row_to_ide_file(row_dict)

    def _ensure_schema(self):
        """Create database tables if they don't exist."""
        cursor = self.db.conn.cursor()

        # IDE files table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ide_files (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                is_open BOOLEAN DEFAULT 0,
                open_mode TEXT DEFAULT 'read_only',
                content_hash TEXT,
                line_count INTEGER,
                language TEXT,
                opened_at INTEGER,
                closed_at INTEGER,
                last_modified INTEGER,
                last_accessed INTEGER,
                is_dirty BOOLEAN DEFAULT 0,
                encoding TEXT DEFAULT 'utf-8',
                size_bytes INTEGER,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                UNIQUE(project_id, file_path)
            )
            """
        )

        # Cursor positions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cursor_positions (
                id INTEGER PRIMARY KEY,
                file_id INTEGER NOT NULL,
                line INTEGER NOT NULL,
                column INTEGER NOT NULL,
                selection_start_line INTEGER,
                selection_start_column INTEGER,
                selection_end_line INTEGER,
                selection_end_column INTEGER,
                selected_text TEXT,
                context_lines_before INTEGER DEFAULT 5,
                context_lines_after INTEGER DEFAULT 5,
                context TEXT,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY(file_id) REFERENCES ide_files(id)
            )
            """
        )

        # Git status table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS git_status (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                change_type TEXT NOT NULL,
                is_staged BOOLEAN DEFAULT 0,
                is_untracked BOOLEAN DEFAULT 0,
                is_conflicted BOOLEAN DEFAULT 0,
                conflict_details TEXT,
                lines_added INTEGER DEFAULT 0,
                lines_deleted INTEGER DEFAULT 0,
                lines_modified INTEGER DEFAULT 0,
                last_commit_hash TEXT,
                last_commit_author TEXT,
                last_commit_message TEXT,
                last_commit_date INTEGER,
                blame_lines TEXT NOT NULL DEFAULT '[]',
                checked_at INTEGER NOT NULL,
                UNIQUE(project_id, file_path)
            )
            """
        )

        # Git diffs table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS git_diffs (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                old_content TEXT,
                new_content TEXT,
                unified_diff TEXT,
                lines_added INTEGER NOT NULL,
                lines_deleted INTEGER NOT NULL,
                hunks TEXT NOT NULL DEFAULT '[]',
                change_type TEXT DEFAULT 'modified',
                captured_at INTEGER NOT NULL
            )
            """
        )

        # IDE context snapshots table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ide_context_snapshots (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                open_files TEXT NOT NULL DEFAULT '[]',
                open_file_count INTEGER DEFAULT 0,
                active_file TEXT,
                active_line INTEGER,
                active_column INTEGER,
                current_branch TEXT,
                uncommitted_changes INTEGER DEFAULT 0,
                untracked_files INTEGER DEFAULT 0,
                terminal_open BOOLEAN DEFAULT 0,
                terminal_cwd TEXT,
                debug_open BOOLEAN DEFAULT 0,
                test_explorer_open BOOLEAN DEFAULT 0,
                git_panel_open BOOLEAN DEFAULT 0,
                zoom_level REAL DEFAULT 1.0,
                theme TEXT,
                font_size INTEGER,
                captured_at INTEGER NOT NULL
            )
            """
        )

        # IDE activity table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ide_activity (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                cursor_position TEXT,
                selected_text TEXT,
                entity_id INTEGER,
                duration_seconds REAL,
                agent_triggered BOOLEAN DEFAULT 0,
                agent_id TEXT,
                timestamp INTEGER NOT NULL
            )
            """
        )

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ide_files_project ON ide_files(project_id)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_cursor_positions_file ON cursor_positions(file_id)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_git_status_project ON git_status(project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_git_diffs_project ON git_diffs(project_id)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_snapshots_session ON ide_context_snapshots(session_id)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_project ON ide_activity(project_id)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON ide_activity(timestamp)"
        )

        self.db.conn.commit()

    # IDEFile CRUD operations

    def create_or_update_file(self, file: IDEFile) -> IDEFile:
        """Create or update IDE file record."""
        existing = self.execute(
            "SELECT id FROM ide_files WHERE project_id = ? AND file_path = ?",
            (file.project_id, file.file_path),
            fetch_one=True
        )

        if existing:
            self.execute(
                """
                UPDATE ide_files SET
                    is_open = ?, open_mode = ?, content_hash = ?, line_count = ?,
                    language = ?, opened_at = ?, closed_at = ?, last_modified = ?,
                    last_accessed = ?, is_dirty = ?, encoding = ?, size_bytes = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    file.is_open,
                    file.open_mode,
                    file.content_hash,
                    file.line_count,
                    file.language,
                    int(file.opened_at.timestamp()) if file.opened_at else None,
                    int(file.closed_at.timestamp()) if file.closed_at else None,
                    int(file.last_modified.timestamp()) if file.last_modified else None,
                    int(file.last_accessed.timestamp()) if file.last_accessed else None,
                    file.is_dirty,
                    file.encoding,
                    file.size_bytes,
                    int(file.updated_at.timestamp()),
                    existing[0],
                ),
            )
            file.id = existing[0]
        else:
            cursor = self.execute(
                """
                INSERT INTO ide_files (
                    project_id, file_path, is_open, open_mode, content_hash,
                    line_count, language, opened_at, closed_at, last_modified,
                    last_accessed, is_dirty, encoding, size_bytes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    file.project_id,
                    file.file_path,
                    file.is_open,
                    file.open_mode,
                    file.content_hash,
                    file.line_count,
                    file.language,
                    int(file.opened_at.timestamp()) if file.opened_at else None,
                    int(file.closed_at.timestamp()) if file.closed_at else None,
                    int(file.last_modified.timestamp()) if file.last_modified else None,
                    int(file.last_accessed.timestamp()) if file.last_accessed else None,
                    file.is_dirty,
                    file.encoding,
                    file.size_bytes,
                    int(file.created_at.timestamp()),
                    int(file.updated_at.timestamp()),
                ),
            )
            file.id = cursor.lastrowid

        self.commit()
        return file

    def get_file(self, file_id: int) -> Optional[IDEFile]:
        """Get IDE file by ID."""
        row = self.execute("SELECT * FROM ide_files WHERE id = ?", (file_id,), fetch_one=True)
        return self._row_to_ide_file(row) if row else None

    def get_open_files(self, project_id: int) -> list[IDEFile]:
        """Get all open files in project."""
        rows = self.execute(
            "SELECT * FROM ide_files WHERE project_id = ? AND is_open = 1 ORDER BY opened_at DESC",
            (project_id,),
            fetch_all=True
        )
        return [self._row_to_ide_file(row) for row in rows]

    # Cursor position operations

    def record_cursor_position(self, position: CursorPosition) -> CursorPosition:
        """Record cursor position for a file."""
        cursor = self.execute(
            """
            INSERT INTO cursor_positions (
                file_id, line, column, selection_start_line, selection_start_column,
                selection_end_line, selection_end_column, selected_text,
                context_lines_before, context_lines_after, context, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                position.file_id,
                position.line,
                position.column,
                position.selection_start_line,
                position.selection_start_column,
                position.selection_end_line,
                position.selection_end_column,
                position.selected_text,
                position.context_lines_before,
                position.context_lines_after,
                position.context,
                int(position.timestamp.timestamp()),
            ),
        )
        self.commit()
        position.id = cursor.lastrowid
        return position

    def get_latest_cursor_position(self, file_id: int) -> Optional[CursorPosition]:
        """Get latest cursor position for file."""
        row = self.execute(
            "SELECT * FROM cursor_positions WHERE file_id = ? ORDER BY timestamp DESC, id DESC LIMIT 1",
            (file_id,),
            fetch_one=True
        )
        return self._row_to_cursor_position(row) if row else None

    # Git status operations

    def create_or_update_git_status(self, status: GitStatus) -> GitStatus:
        """Create or update git status for file."""
        existing = self.execute(
            "SELECT id FROM git_status WHERE project_id = ? AND file_path = ?",
            (status.project_id, status.file_path),
            fetch_one=True
        )

        if existing:
            self.execute(
                """
                UPDATE git_status SET
                    change_type = ?, is_staged = ?, is_untracked = ?, is_conflicted = ?,
                    conflict_details = ?, lines_added = ?, lines_deleted = ?,
                    lines_modified = ?, last_commit_hash = ?, last_commit_author = ?,
                    last_commit_message = ?, last_commit_date = ?, blame_lines = ?, checked_at = ?
                WHERE id = ?
                """,
                (
                    status.change_type,
                    status.is_staged,
                    status.is_untracked,
                    status.is_conflicted,
                    status.conflict_details,
                    status.lines_added,
                    status.lines_deleted,
                    status.lines_modified,
                    status.last_commit_hash,
                    status.last_commit_author,
                    status.last_commit_message,
                    int(status.last_commit_date.timestamp()) if status.last_commit_date else None,
                    json.dumps(status.blame_lines),
                    int(status.checked_at.timestamp()),
                    existing[0],
                ),
            )
            status.id = existing[0]
        else:
            cursor = self.execute(
                """
                INSERT INTO git_status (
                    project_id, file_path, change_type, is_staged, is_untracked,
                    is_conflicted, conflict_details, lines_added, lines_deleted,
                    lines_modified, last_commit_hash, last_commit_author,
                    last_commit_message, last_commit_date, blame_lines, checked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    status.project_id,
                    status.file_path,
                    status.change_type,
                    status.is_staged,
                    status.is_untracked,
                    status.is_conflicted,
                    status.conflict_details,
                    status.lines_added,
                    status.lines_deleted,
                    status.lines_modified,
                    status.last_commit_hash,
                    status.last_commit_author,
                    status.last_commit_message,
                    int(status.last_commit_date.timestamp()) if status.last_commit_date else None,
                    json.dumps(status.blame_lines),
                    int(status.checked_at.timestamp()),
                ),
            )
            status.id = cursor.lastrowid

        self.commit()
        return status

    def get_git_status(self, project_id: int, file_path: str) -> Optional[GitStatus]:
        """Get git status for file."""
        row = self.execute(
            "SELECT * FROM git_status WHERE project_id = ? AND file_path = ?",
            (project_id, file_path),
            fetch_one=True
        )
        return self._row_to_git_status(row) if row else None

    def get_changed_files(self, project_id: int) -> list[GitStatus]:
        """Get all files with changes."""
        rows = self.execute(
            "SELECT * FROM git_status WHERE project_id = ? AND (is_staged = 1 OR change_type != 'unmodified') ORDER BY file_path",
            (project_id,),
            fetch_all=True
        )
        return [self._row_to_git_status(row) for row in rows]

    # Git diff operations

    def create_git_diff(self, diff: GitDiff) -> GitDiff:
        """Record git diff for file."""
        cursor = self.execute(
            """
            INSERT INTO git_diffs (
                project_id, file_path, old_content, new_content, unified_diff,
                lines_added, lines_deleted, hunks, change_type, captured_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                diff.project_id,
                diff.file_path,
                diff.old_content,
                diff.new_content,
                diff.unified_diff,
                diff.lines_added,
                diff.lines_deleted,
                json.dumps(diff.hunks),
                diff.change_type,
                int(diff.captured_at.timestamp()),
            ),
        )
        self.commit()
        diff.id = cursor.lastrowid
        return diff

    def get_diffs_for_file(self, project_id: int, file_path: str, limit: int = 10) -> list[GitDiff]:
        """Get recent diffs for file."""
        rows = self.execute(
            "SELECT * FROM git_diffs WHERE project_id = ? AND file_path = ? ORDER BY captured_at DESC LIMIT ?",
            (project_id, file_path, limit),
            fetch_all=True
        )
        return [self._row_to_git_diff(row) for row in rows]

    # Context snapshot operations

    def create_context_snapshot(self, snapshot: IDEContextSnapshot) -> IDEContextSnapshot:
        """Create IDE context snapshot."""
        cursor = self.execute(
            """
            INSERT INTO ide_context_snapshots (
                project_id, session_id, open_files, open_file_count, active_file,
                active_line, active_column, current_branch, uncommitted_changes,
                untracked_files, terminal_open, terminal_cwd, debug_open,
                test_explorer_open, git_panel_open, zoom_level, theme, font_size,
                captured_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.project_id,
                snapshot.session_id,
                json.dumps(snapshot.open_files),
                snapshot.open_file_count,
                snapshot.active_file,
                snapshot.active_line,
                snapshot.active_column,
                snapshot.current_branch,
                snapshot.uncommitted_changes,
                snapshot.untracked_files,
                snapshot.terminal_open,
                snapshot.terminal_cwd,
                snapshot.debug_open,
                snapshot.test_explorer_open,
                snapshot.git_panel_open,
                snapshot.zoom_level,
                snapshot.theme,
                snapshot.font_size,
                int(snapshot.captured_at.timestamp()),
            ),
        )
        self.commit()
        snapshot.id = cursor.lastrowid
        return snapshot

    def get_latest_snapshot(self, project_id: int) -> Optional[IDEContextSnapshot]:
        """Get latest IDE context snapshot."""
        row = self.execute(
            "SELECT * FROM ide_context_snapshots WHERE project_id = ? ORDER BY captured_at DESC LIMIT 1",
            (project_id,),
            fetch_one=True
        )
        return self._row_to_context_snapshot(row) if row else None

    # Activity tracking

    def record_activity(self, activity: IDEActivity) -> IDEActivity:
        """Record IDE activity."""
        cursor = self.execute(
            """
            INSERT INTO ide_activity (
                project_id, file_path, activity_type, cursor_position,
                selected_text, entity_id, duration_seconds, agent_triggered,
                agent_id, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                activity.project_id,
                activity.file_path,
                activity.activity_type,
                activity.cursor_position,
                activity.selected_text,
                activity.entity_id,
                activity.duration_seconds,
                activity.agent_triggered,
                activity.agent_id,
                int(activity.timestamp.timestamp()),
            ),
        )
        self.commit()
        activity.id = cursor.lastrowid
        return activity

    def get_recent_activity(self, project_id: int, limit: int = 50) -> list[IDEActivity]:
        """Get recent activity in project."""
        rows = self.execute(
            "SELECT * FROM ide_activity WHERE project_id = ? ORDER BY timestamp DESC LIMIT ?",
            (project_id, limit),
            fetch_all=True
        )
        return [self._row_to_activity(row) for row in rows]

    # Helper methods

    def _row_to_ide_file(self, row) -> IDEFile:
        """Convert database row to IDEFile."""
        from datetime import datetime

        return IDEFile(
            id=row[0],
            project_id=row[1],
            file_path=row[2],
            is_open=bool(row[3]),
            open_mode=row[4],
            content_hash=row[5],
            line_count=row[6],
            language=row[7],
            opened_at=datetime.fromtimestamp(row[8]) if row[8] else None,
            closed_at=datetime.fromtimestamp(row[9]) if row[9] else None,
            last_modified=datetime.fromtimestamp(row[10]) if row[10] else None,
            last_accessed=datetime.fromtimestamp(row[11]) if row[11] else None,
            is_dirty=bool(row[12]),
            encoding=row[13],
            size_bytes=row[14],
            created_at=datetime.fromtimestamp(row[15]),
            updated_at=datetime.fromtimestamp(row[16]),
        )

    def _row_to_cursor_position(self, row) -> CursorPosition:
        """Convert database row to CursorPosition."""
        from datetime import datetime

        return CursorPosition(
            id=row[0],
            file_id=row[1],
            line=row[2],
            column=row[3],
            selection_start_line=row[4],
            selection_start_column=row[5],
            selection_end_line=row[6],
            selection_end_column=row[7],
            selected_text=row[8],
            context_lines_before=row[9],
            context_lines_after=row[10],
            context=row[11],
            timestamp=datetime.fromtimestamp(row[12]),
        )

    def _row_to_git_status(self, row) -> GitStatus:
        """Convert database row to GitStatus."""
        from datetime import datetime

        return GitStatus(
            id=row[0],
            project_id=row[1],
            file_path=row[2],
            change_type=row[3],
            is_staged=bool(row[4]),
            is_untracked=bool(row[5]),
            is_conflicted=bool(row[6]),
            conflict_details=row[7],
            lines_added=row[8],
            lines_deleted=row[9],
            lines_modified=row[10],
            last_commit_hash=row[11],
            last_commit_author=row[12],
            last_commit_message=row[13],
            last_commit_date=datetime.fromtimestamp(row[14]) if row[14] else None,
            blame_lines=json.loads(row[15]),
            checked_at=datetime.fromtimestamp(row[16]),
        )

    def _row_to_git_diff(self, row) -> GitDiff:
        """Convert database row to GitDiff."""
        from datetime import datetime

        return GitDiff(
            id=row[0],
            project_id=row[1],
            file_path=row[2],
            old_content=row[3],
            new_content=row[4],
            unified_diff=row[5],
            lines_added=row[6],
            lines_deleted=row[7],
            hunks=json.loads(row[8]),
            change_type=row[9],
            captured_at=datetime.fromtimestamp(row[10]),
        )

    def _row_to_context_snapshot(self, row) -> IDEContextSnapshot:
        """Convert database row to IDEContextSnapshot."""
        from datetime import datetime

        return IDEContextSnapshot(
            id=row[0],
            project_id=row[1],
            session_id=row[2],
            open_files=json.loads(row[3]),
            open_file_count=row[4],
            active_file=row[5],
            active_line=row[6],
            active_column=row[7],
            current_branch=row[8],
            uncommitted_changes=row[9],
            untracked_files=row[10],
            terminal_open=bool(row[11]),
            terminal_cwd=row[12],
            debug_open=bool(row[13]),
            test_explorer_open=bool(row[14]),
            git_panel_open=bool(row[15]),
            zoom_level=row[16],
            theme=row[17],
            font_size=row[18],
            captured_at=datetime.fromtimestamp(row[19]),
        )

    def _row_to_activity(self, row) -> IDEActivity:
        """Convert database row to IDEActivity."""
        from datetime import datetime

        return IDEActivity(
            id=row[0],
            project_id=row[1],
            file_path=row[2],
            activity_type=row[3],
            cursor_position=row[4],
            selected_text=row[5],
            entity_id=row[6],
            duration_seconds=row[7],
            agent_triggered=bool(row[8]),
            agent_id=row[9],
            timestamp=datetime.fromtimestamp(row[10]),
        )
