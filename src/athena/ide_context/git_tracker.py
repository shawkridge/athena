"""Git integration for IDE context tracking."""

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import GitChangeType, GitDiff, GitStatus


class GitTracker:
    """Track git state and changes."""

    def __init__(self, repo_path: str):
        """Initialize git tracker for repository.

        Args:
            repo_path: Path to git repository root
        """
        self.repo_path = Path(repo_path)
        self.is_git_repo = (self.repo_path / ".git").exists()

    def get_current_branch(self) -> Optional[str]:
        """Get current git branch name."""
        if not self.is_git_repo:
            return None

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except (subprocess.SubprocessError, OSError, ValueError):
            return None

    def get_file_status(self, file_path: str) -> Optional[GitStatus]:
        """Get git status for a file."""
        if not self.is_git_repo:
            return None

        try:
            # Get relative path from repo root
            rel_path = Path(file_path).relative_to(self.repo_path)

            # Get git status
            result = subprocess.run(
                ["git", "status", "--porcelain", str(rel_path)],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0 or not result.stdout.strip():
                return None

            status_line = result.stdout.strip()
            change_type = self._parse_status_code(status_line[0:2])

            # Get diff stats
            diff_result = subprocess.run(
                ["git", "diff", "--numstat", str(rel_path)],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )

            lines_added = 0
            lines_deleted = 0
            if diff_result.returncode == 0 and diff_result.stdout.strip():
                parts = diff_result.stdout.strip().split("\t")
                lines_added = int(parts[0]) if parts[0].isdigit() else 0
                lines_deleted = int(parts[1]) if parts[1].isdigit() else 0

            # Get last commit info
            commit_result = subprocess.run(
                ["git", "log", "-1", "--pretty=format:%H|%an|%s|%ai", "--", str(rel_path)],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )

            last_commit_hash = None
            last_commit_author = None
            last_commit_message = None
            last_commit_date = None

            if commit_result.returncode == 0 and commit_result.stdout.strip():
                parts = commit_result.stdout.strip().split("|")
                if len(parts) >= 4:
                    last_commit_hash = parts[0]
                    last_commit_author = parts[1]
                    last_commit_message = parts[2]
                    last_commit_date = datetime.fromisoformat(parts[3].replace(" ", "T"))

            return GitStatus(
                file_path=file_path,
                project_id=0,  # Will be set by manager
                change_type=change_type,
                is_staged=status_line[0] != " ",
                is_untracked=status_line[0:2] == "??",
                lines_added=lines_added,
                lines_deleted=lines_deleted,
                last_commit_hash=last_commit_hash,
                last_commit_author=last_commit_author,
                last_commit_message=last_commit_message,
                last_commit_date=last_commit_date,
            )
        except (subprocess.SubprocessError, OSError, ValueError, IndexError) as e:
            print(f"Error getting git status for {file_path}: {e}")
            return None

    def get_file_diff(self, file_path: str) -> Optional[GitDiff]:
        """Get unified diff for a file."""
        if not self.is_git_repo:
            return None

        try:
            rel_path = Path(file_path).relative_to(self.repo_path)

            # Get unified diff
            result = subprocess.run(
                ["git", "diff", "-U3", str(rel_path)],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                return None

            unified_diff = result.stdout

            # Get stat
            stat_result = subprocess.run(
                ["git", "diff", "--numstat", str(rel_path)],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )

            lines_added = 0
            lines_deleted = 0
            if stat_result.returncode == 0 and stat_result.stdout.strip():
                parts = stat_result.stdout.strip().split("\t")
                lines_added = int(parts[0]) if parts[0].isdigit() else 0
                lines_deleted = int(parts[1]) if parts[1].isdigit() else 0

            return GitDiff(
                file_path=file_path,
                project_id=0,  # Will be set by manager
                unified_diff=unified_diff,
                lines_added=lines_added,
                lines_deleted=lines_deleted,
                change_type=GitChangeType.MODIFIED,
            )
        except (subprocess.SubprocessError, OSError, ValueError, IndexError) as e:
            print(f"Error getting git diff for {file_path}: {e}")
            return None

    def get_changed_files(self) -> list[str]:
        """Get all files with uncommitted changes."""
        if not self.is_git_repo:
            return []

        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                return []

            files = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    file_path = line[3:].strip()
                    files.append(str(self.repo_path / file_path))

            return files
        except (subprocess.SubprocessError, OSError, ValueError):
            return []

    def get_untracked_files(self) -> list[str]:
        """Get untracked files."""
        if not self.is_git_repo:
            return []

        try:
            result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                return []

            return [
                str(self.repo_path / f.strip())
                for f in result.stdout.strip().split("\n")
                if f.strip()
            ]
        except (subprocess.SubprocessError, OSError, ValueError):
            return []

    def is_file_tracked(self, file_path: str) -> bool:
        """Check if file is tracked by git."""
        if not self.is_git_repo:
            return False

        try:
            rel_path = Path(file_path).relative_to(self.repo_path)
            result = subprocess.run(
                ["git", "ls-files", "--error-unmatch", str(rel_path)],
                cwd=self.repo_path,
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, OSError, ValueError):
            return False

    @staticmethod
    def _parse_status_code(code: str) -> GitChangeType:
        """Parse git status code to change type."""
        code = code.strip()
        if code in ("A", "AM"):
            return GitChangeType.ADDED
        elif code in ("D", "DM"):
            return GitChangeType.DELETED
        elif code == "R":
            return GitChangeType.RENAMED
        elif code == "C":
            return GitChangeType.COPIED
        elif code == "U":
            return GitChangeType.UNMERGED
        else:
            return GitChangeType.MODIFIED
