"""Manager for IDE context tracking and integration."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from athena.core.database import Database

logger = logging.getLogger(__name__)

from .git_tracker import GitTracker
from .models import (
    CursorPosition,
    FileOpenMode,
    IDEActivity,
    IDEContextSnapshot,
    IDEFile,
)
from .store import IDEContextStore


class IDEContextManager:
    """High-level manager for IDE context and state."""

    def __init__(self, db: Database, repo_path: str):
        """Initialize manager with database and repository path.

        Args:
            db: Database connection
            repo_path: Path to project/repository root
        """
        self.db = db
        self.repo_path = repo_path
        self.store = IDEContextStore(db)
        self.git = GitTracker(repo_path)

    # File management

    def open_file(
        self,
        project_id: int,
        file_path: str,
        mode: FileOpenMode = FileOpenMode.READ_WRITE,
    ) -> IDEFile:
        """Record file being opened in IDE.

        Args:
            project_id: Project ID
            file_path: Path to file
            mode: Open mode (read-only, read-write, preview)

        Returns:
            IDEFile record
        """
        try:
            size = Path(file_path).stat().st_size if Path(file_path).exists() else None
            line_count = None
            if Path(file_path).exists():
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    line_count = len(f.readlines())
        except (OSError, IOError, UnicodeDecodeError) as e:
            logger.debug(f"Failed to read file metadata for {file_path}: {e}")
            size = None
            line_count = None

        file = IDEFile(
            project_id=project_id,
            file_path=file_path,
            is_open=True,
            open_mode=mode,
            opened_at=datetime.now(),
            last_accessed=datetime.now(),
            line_count=line_count,
            size_bytes=size,
            language=Path(file_path).suffix[1:] if Path(file_path).suffix else None,
        )

        return self.store.create_or_update_file(file)

    def close_file(self, project_id: int, file_path: str) -> IDEFile:
        """Record file being closed in IDE.

        Args:
            project_id: Project ID
            file_path: Path to file

        Returns:
            Updated IDEFile record
        """
        # Get existing file
        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT id FROM ide_files WHERE project_id = ? AND file_path = ?",
            (project_id, file_path),
        )
        result = cursor.fetchone()

        if result:
            file = self.store.get_file(result[0])
            if file:
                file.is_open = False
                file.closed_at = datetime.now()
                return self.store.create_or_update_file(file)

        return IDEFile(
            project_id=project_id, file_path=file_path, is_open=False, closed_at=datetime.now()
        )

    def get_open_files(self, project_id: int) -> list[IDEFile]:
        """Get all open files in project.

        Args:
            project_id: Project ID

        Returns:
            List of open IDEFile objects
        """
        return self.store.get_open_files(project_id)

    def mark_file_dirty(self, file_id: int):
        """Mark file as having unsaved changes.

        Args:
            file_id: ID of file
        """
        file = self.store.get_file(file_id)
        if file:
            file.is_dirty = True
            file.last_modified = datetime.now()
            self.store.create_or_update_file(file)

    def mark_file_clean(self, file_id: int):
        """Mark file as saved (no unsaved changes).

        Args:
            file_id: ID of file
        """
        file = self.store.get_file(file_id)
        if file:
            file.is_dirty = False
            self.store.create_or_update_file(file)

    # Cursor and selection tracking

    def record_cursor_position(
        self,
        file_id: int,
        line: int,
        column: int,
        selected_text: Optional[str] = None,
        context: Optional[str] = None,
    ) -> CursorPosition:
        """Record cursor position in file.

        Args:
            file_id: ID of file
            line: Line number (1-indexed)
            column: Column number (0-indexed)
            selected_text: Text selected by cursor (if any)
            context: Code context around cursor

        Returns:
            CursorPosition record
        """
        position = CursorPosition(
            file_id=file_id,
            line=line,
            column=column,
            selected_text=selected_text,
            context=context,
        )
        return self.store.record_cursor_position(position)

    def get_latest_cursor_position(self, file_id: int) -> Optional[CursorPosition]:
        """Get latest recorded cursor position for file.

        Args:
            file_id: ID of file

        Returns:
            Latest CursorPosition or None
        """
        return self.store.get_latest_cursor_position(file_id)

    # Git integration

    def update_git_status(self, project_id: int, file_path: str) -> Optional[dict]:
        """Update and store git status for file.

        Args:
            project_id: Project ID
            file_path: Path to file

        Returns:
            Dictionary with git status info
        """
        git_status = self.git.get_file_status(file_path)
        if not git_status:
            return None

        git_status.project_id = project_id
        stored_status = self.store.create_or_update_git_status(git_status)

        return {
            "file": file_path,
            "change_type": stored_status.change_type,
            "is_staged": stored_status.is_staged,
            "is_untracked": stored_status.is_untracked,
            "lines_added": stored_status.lines_added,
            "lines_deleted": stored_status.lines_deleted,
        }

    def update_git_diff(self, project_id: int, file_path: str) -> Optional[dict]:
        """Capture and store git diff for file.

        Args:
            project_id: Project ID
            file_path: Path to file

        Returns:
            Dictionary with diff info
        """
        git_diff = self.git.get_file_diff(file_path)
        if not git_diff:
            return None

        git_diff.project_id = project_id
        stored_diff = self.store.create_git_diff(git_diff)

        return {
            "file": file_path,
            "lines_added": stored_diff.lines_added,
            "lines_deleted": stored_diff.lines_deleted,
        }

    def get_changed_files(self, project_id: int) -> list[dict]:
        """Get all files with uncommitted changes.

        Args:
            project_id: Project ID

        Returns:
            List of changed files with status
        """
        changed_files = self.git.get_changed_files()
        changed_untracked = self.git.get_untracked_files()

        results = []

        for file_path in changed_files:
            status = self.git.get_file_status(file_path)
            if status:
                results.append(
                    {
                        "file": file_path,
                        "type": status.change_type,
                        "staged": status.is_staged,
                        "tracked": True,
                    }
                )

        for file_path in changed_untracked:
            results.append(
                {
                    "file": file_path,
                    "type": "untracked",
                    "staged": False,
                    "tracked": False,
                }
            )

        return results

    def get_current_branch(self) -> Optional[str]:
        """Get current git branch.

        Returns:
            Branch name or None
        """
        return self.git.get_current_branch()

    # IDE context snapshots

    def create_context_snapshot(self, project_id: int, session_id: str) -> IDEContextSnapshot:
        """Create snapshot of current IDE state.

        Args:
            project_id: Project ID
            session_id: Unique session identifier

        Returns:
            IDEContextSnapshot record
        """
        # Get open files
        open_files = self.store.get_open_files(project_id)
        open_file_paths = [f.file_path for f in open_files]

        # Get active file (most recently accessed)
        active_file = None
        active_line = None
        active_column = None
        if open_files:
            active = max(open_files, key=lambda f: f.last_accessed or f.opened_at)
            active_file = active.file_path
            latest_cursor = self.store.get_latest_cursor_position(active.id)
            if latest_cursor:
                active_line = latest_cursor.line
                active_column = latest_cursor.column

        # Get git state
        changed_files = self.get_changed_files(project_id)
        uncommitted = sum(1 for f in changed_files if f["tracked"])
        untracked = sum(1 for f in changed_files if not f["tracked"])

        snapshot = IDEContextSnapshot(
            project_id=project_id,
            session_id=session_id,
            open_files=open_file_paths,
            open_file_count=len(open_file_paths),
            active_file=active_file,
            active_line=active_line,
            active_column=active_column,
            current_branch=self.git.get_current_branch(),
            uncommitted_changes=uncommitted,
            untracked_files=untracked,
        )

        return self.store.create_context_snapshot(snapshot)

    def get_latest_snapshot(self, project_id: int) -> Optional[IDEContextSnapshot]:
        """Get latest IDE context snapshot.

        Args:
            project_id: Project ID

        Returns:
            Latest IDEContextSnapshot or None
        """
        return self.store.get_latest_snapshot(project_id)

    # Activity tracking

    def record_activity(
        self,
        project_id: int,
        file_path: str,
        activity_type: str,
        agent_id: Optional[str] = None,
    ) -> IDEActivity:
        """Record IDE activity.

        Args:
            project_id: Project ID
            file_path: File involved in activity
            activity_type: Type (save, open, close, edit, refactor, test, debug)
            agent_id: Agent ID if agent triggered activity

        Returns:
            IDEActivity record
        """
        activity = IDEActivity(
            project_id=project_id,
            file_path=file_path,
            activity_type=activity_type,
            agent_triggered=agent_id is not None,
            agent_id=agent_id,
        )
        return self.store.record_activity(activity)

    def get_recent_activity(self, project_id: int, limit: int = 50) -> list[IDEActivity]:
        """Get recent IDE activity.

        Args:
            project_id: Project ID
            limit: Maximum number of records to return

        Returns:
            List of recent IDEActivity records
        """
        return self.store.get_recent_activity(project_id, limit)

    # Analysis methods

    def get_ide_context_summary(self, project_id: int) -> dict:
        """Get summary of IDE state.

        Args:
            project_id: Project ID

        Returns:
            Dictionary with IDE context summary
        """
        open_files = self.store.get_open_files(project_id)
        changed_files = self.get_changed_files(project_id)
        latest_snapshot = self.get_latest_snapshot(project_id)

        return {
            "open_files": len(open_files),
            "open_file_list": [f.file_path for f in open_files],
            "dirty_files": len([f for f in open_files if f.is_dirty]),
            "changed_files": len(changed_files),
            "uncommitted_changes": sum(1 for f in changed_files if f.get("tracked", True)),
            "untracked_files": sum(1 for f in changed_files if not f.get("tracked", True)),
            "current_branch": self.git.get_current_branch(),
            "last_snapshot": latest_snapshot.captured_at if latest_snapshot else None,
        }

    def suggest_next_file(self, project_id: int) -> Optional[str]:
        """Suggest which file agent should work on next.

        Returns recommendation based on:
        - Files with unsaved changes
        - Files with conflicts
        - Most recently modified

        Args:
            project_id: Project ID

        Returns:
            Path to recommended file or None
        """
        # Prefer dirty files (unsaved changes)
        open_files = self.store.get_open_files(project_id)
        dirty = [f for f in open_files if f.is_dirty]
        if dirty:
            return dirty[0].file_path

        # Prefer files with git changes
        changed = self.get_changed_files(project_id)
        if changed:
            return changed[0]["file"]

        # Return most recently accessed
        if open_files:
            most_recent = max(open_files, key=lambda f: f.last_accessed or f.opened_at)
            return most_recent.file_path

        return None
