"""Public API for IDE context integration."""

from typing import Optional

from athena.core.database import Database, get_database

from .manager import IDEContextManager
from .models import FileOpenMode


class IDEContextAPI:
    """Public API for IDE context access."""

    def __init__(self, db: Optional[Database] = None, repo_path: str = "."):
        """Initialize IDE context API.

        Args:
            db: Database instance (default: uses global singleton from get_database())
            repo_path: Path to project/repository root

        Migration Note (Nov 12, 2025):
            Changed from db_path parameter to db parameter for consistency with
            centralized database access pattern. The singleton ensures all
            components share a single connection pool.
        """
        # Use singleton if not provided (centralized database access)
        self.db = db or get_database()
        self.manager = IDEContextManager(self.db, repo_path)

    # File management convenience methods

    def file_opened(self, project_id: int, file_path: str) -> dict:
        """Record file opened in IDE.

        Args:
            project_id: Project ID
            file_path: Path to file

        Returns:
            Dictionary with file info
        """
        file = self.manager.open_file(project_id, file_path)
        return {
            "file": file.file_path,
            "is_open": file.is_open,
            "lines": file.line_count,
            "size": file.size_bytes,
        }

    def file_closed(self, project_id: int, file_path: str) -> dict:
        """Record file closed in IDE.

        Args:
            project_id: Project ID
            file_path: Path to file

        Returns:
            Dictionary with file info
        """
        file = self.manager.close_file(project_id, file_path)
        return {"file": file.file_path, "is_open": file.is_open}

    def file_saved(self, project_id: int, file_path: str):
        """Record file saved.

        Args:
            project_id: Project ID
            file_path: Path to file
        """
        cursor_result = self.manager.db.conn.cursor()
        cursor_result.execute(
            "SELECT id FROM ide_files WHERE project_id = ? AND file_path = ?",
            (project_id, file_path),
        )
        result = cursor_result.fetchone()
        if result:
            self.manager.mark_file_clean(result[0])

    def file_modified(self, project_id: int, file_path: str):
        """Record file modified (unsaved changes).

        Args:
            project_id: Project ID
            file_path: Path to file
        """
        cursor_result = self.manager.db.conn.cursor()
        cursor_result.execute(
            "SELECT id FROM ide_files WHERE project_id = ? AND file_path = ?",
            (project_id, file_path),
        )
        result = cursor_result.fetchone()
        if result:
            self.manager.mark_file_dirty(result[0])

    def get_open_files(self, project_id: int) -> list[dict]:
        """Get list of open files.

        Args:
            project_id: Project ID

        Returns:
            List of open file information
        """
        open_files = self.manager.get_open_files(project_id)
        return [
            {
                "file": f.file_path,
                "lines": f.line_count,
                "dirty": f.is_dirty,
                "opened_at": f.opened_at.isoformat() if f.opened_at else None,
            }
            for f in open_files
        ]

    # Cursor and selection

    def cursor_position(
        self,
        project_id: int,
        file_path: str,
        line: int,
        column: int,
        selected_text: Optional[str] = None,
    ):
        """Record cursor position.

        Args:
            project_id: Project ID
            file_path: Path to file
            line: Line number (1-indexed)
            column: Column number (0-indexed)
            selected_text: Selected text (if any)
        """
        # Get file ID
        cursor_result = self.manager.db.conn.cursor()
        cursor_result.execute(
            "SELECT id FROM ide_files WHERE project_id = ? AND file_path = ?",
            (project_id, file_path),
        )
        result = cursor_result.fetchone()
        if result:
            file_id = result[0]
            self.manager.record_cursor_position(file_id, line, column, selected_text)

    def get_cursor_position(self, project_id: int, file_path: str) -> Optional[dict]:
        """Get latest cursor position.

        Args:
            project_id: Project ID
            file_path: Path to file

        Returns:
            Cursor position or None
        """
        cursor_result = self.manager.db.conn.cursor()
        cursor_result.execute(
            "SELECT id FROM ide_files WHERE project_id = ? AND file_path = ?",
            (project_id, file_path),
        )
        result = cursor_result.fetchone()
        if not result:
            return None

        position = self.manager.get_latest_cursor_position(result[0])
        if not position:
            return None

        return {
            "line": position.line,
            "column": position.column,
            "selected_text": position.selected_text,
            "context": position.context,
        }

    # Git integration

    def get_git_status(self, project_id: int) -> dict:
        """Get git status for project.

        Args:
            project_id: Project ID

        Returns:
            Dictionary with git status
        """
        changed = self.manager.get_changed_files(project_id)

        return {
            "branch": self.manager.get_current_branch(),
            "changed_files": len([f for f in changed if f.get("tracked", True)]),
            "untracked_files": len([f for f in changed if not f.get("tracked", True)]),
            "files": changed,
        }

    def get_file_git_status(self, project_id: int, file_path: str) -> Optional[dict]:
        """Get git status for specific file.

        Args:
            project_id: Project ID
            file_path: Path to file

        Returns:
            File git status or None
        """
        return self.manager.update_git_status(project_id, file_path)

    def get_file_diff(self, project_id: int, file_path: str) -> Optional[dict]:
        """Get git diff for file.

        Args:
            project_id: Project ID
            file_path: Path to file

        Returns:
            Diff information or None
        """
        return self.manager.update_git_diff(project_id, file_path)

    # IDE state snapshots

    def take_snapshot(self, project_id: int, session_id: str) -> dict:
        """Take snapshot of IDE state.

        Args:
            project_id: Project ID
            session_id: Session identifier

        Returns:
            Snapshot information
        """
        snapshot = self.manager.create_context_snapshot(project_id, session_id)
        return {
            "open_files": snapshot.open_file_count,
            "files": snapshot.open_files,
            "active_file": snapshot.active_file,
            "branch": snapshot.current_branch,
            "changes": snapshot.uncommitted_changes,
            "untracked": snapshot.untracked_files,
        }

    def get_context_summary(self, project_id: int) -> dict:
        """Get summary of IDE context.

        Args:
            project_id: Project ID

        Returns:
            IDE context summary
        """
        return self.manager.get_ide_context_summary(project_id)

    # Activity tracking

    def record_activity(
        self,
        project_id: int,
        file_path: str,
        activity_type: str,
        agent_id: Optional[str] = None,
    ):
        """Record IDE activity.

        Args:
            project_id: Project ID
            file_path: File path
            activity_type: Activity type (save, edit, refactor, etc)
            agent_id: Agent ID if applicable
        """
        self.manager.record_activity(project_id, file_path, activity_type, agent_id)

    def get_recent_activity(self, project_id: int, limit: int = 20) -> list[dict]:
        """Get recent IDE activity.

        Args:
            project_id: Project ID
            limit: Max records

        Returns:
            List of recent activities
        """
        activities = self.manager.get_recent_activity(project_id, limit)
        return [
            {
                "file": a.file_path,
                "type": a.activity_type,
                "agent": a.agent_id,
                "time": a.timestamp.isoformat(),
            }
            for a in activities
        ]

    # Suggestions

    def next_file_suggestion(self, project_id: int) -> Optional[dict]:
        """Get suggestion for next file to work on.

        Args:
            project_id: Project ID

        Returns:
            Suggested file path or None
        """
        suggested = self.manager.suggest_next_file(project_id)
        if not suggested:
            return None

        git_status = self.manager.update_git_status(project_id, suggested)
        return {
            "file": suggested,
            "reason": "has_unsaved_changes" if git_status else "recent_change",
            "git_status": git_status,
        }
