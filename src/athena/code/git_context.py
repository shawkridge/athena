"""Git-aware context management for analyzing changed files and diffs."""

import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FileChange:
    """Represents a file change in the repository."""

    filepath: str
    status: str  # "added", "modified", "deleted", "renamed"
    old_name: Optional[str] = None  # For renamed files
    lines_added: int = 0
    lines_deleted: int = 0
    insertions: int = 0
    deletions: int = 0


@dataclass
class FileDiff:
    """Represents a file diff with before/after content."""

    filepath: str
    status: str  # "added", "modified", "deleted"
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    diff_text: str = ""
    hunks: List[Dict[str, str]] = None  # List of diffs


class GitContext:
    """Manages git context for changed files and diffs."""

    def __init__(self, repo_path: str | Path = "."):
        """Initialize GitContext with repository path.

        Args:
            repo_path: Path to git repository (default: current directory)

        Raises:
            ValueError: If path is not a git repository
        """
        self.repo_path = Path(repo_path)

        # Verify it's a git repository
        if not (self.repo_path / ".git").exists():
            raise ValueError(f"{repo_path} is not a git repository")

    def get_changed_files(self, since: str = "HEAD~1") -> List[FileChange]:
        """Get list of files changed since a commit.

        Args:
            since: Git ref to compare against (default: "HEAD~1" = previous commit)

        Returns:
            List of FileChange objects with status and modification counts

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        try:
            # Get the commit range to use
            if since == "HEAD~1":
                # Compare current working directory with previous commit
                commit_range = "HEAD~1..HEAD"
            else:
                # Use specified commit range
                commit_range = f"{since}..HEAD"

            # Get changed files with stats
            cmd = [
                "git",
                "-C",
                str(self.repo_path),
                "diff",
                "--name-status",
                commit_range,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            changes = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("\t")
                status_char = parts[0]
                filepath = parts[1] if len(parts) > 1 else ""

                # Map git status codes to our names
                status_map = {
                    "A": "added",
                    "M": "modified",
                    "D": "deleted",
                    "R": "renamed",
                    "C": "copied",
                    "T": "type_changed",
                    "U": "unmerged",
                    "X": "unknown",
                }

                status = status_map.get(status_char, "unknown")
                old_name = parts[2] if status == "renamed" and len(parts) > 2 else None

                change = FileChange(
                    filepath=filepath,
                    status=status,
                    old_name=old_name,
                )

                # Get line statistics for each file
                stats_cmd = [
                    "git",
                    "-C",
                    str(self.repo_path),
                    "diff",
                    "--numstat",
                    f"{commit_range}",
                    "--",
                    filepath,
                ]
                stats_result = subprocess.run(stats_cmd, capture_output=True, text=True, check=True)

                if stats_result.stdout.strip():
                    stat_line = stats_result.stdout.strip().split("\n")[0]
                    stat_parts = stat_line.split("\t")
                    if len(stat_parts) >= 2:
                        try:
                            change.lines_added = int(stat_parts[0])
                            change.lines_deleted = int(stat_parts[1])
                        except ValueError:
                            pass

                changes.append(change)

            return changes

        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e.stderr}")
            return []

    def get_changed_diff(self, filepath: str, since: str = "HEAD~1") -> Optional[FileDiff]:
        """Get unified diff for a specific file.

        Args:
            filepath: Path to file relative to repo root
            since: Git ref to compare against (default: "HEAD~1")

        Returns:
            FileDiff with diff text and parsed hunks, or None if file not changed

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        try:
            if since == "HEAD~1":
                commit_range = "HEAD~1..HEAD"
            else:
                commit_range = f"{since}..HEAD"

            # Get the unified diff
            cmd = [
                "git",
                "-C",
                str(self.repo_path),
                "diff",
                "-U5",  # 5 lines of context
                commit_range,
                "--",
                filepath,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            if not result.stdout:
                # File might not have changed
                return None

            diff_text = result.stdout

            # Determine file status
            status_cmd = [
                "git",
                "-C",
                str(self.repo_path),
                "diff",
                "--name-status",
                commit_range,
                "--",
                filepath,
            ]
            status_result = subprocess.run(status_cmd, capture_output=True, text=True, check=True)

            status = "modified"
            if status_result.stdout.startswith("A"):
                status = "added"
            elif status_result.stdout.startswith("D"):
                status = "deleted"

            # Parse hunks from diff
            hunks = self._parse_hunks(diff_text)

            # Get actual file contents if available
            old_content = None
            new_content = None

            try:
                # Get old version (from previous commit)
                old_cmd = [
                    "git",
                    "-C",
                    str(self.repo_path),
                    "show",
                    f"{commit_range.split('..')[0]}:{filepath}",
                ]
                old_result = subprocess.run(old_cmd, capture_output=True, text=True)
                if old_result.returncode == 0:
                    old_content = old_result.stdout

                # Get new version
                new_path = self.repo_path / filepath
                if new_path.exists():
                    with open(new_path, "r", encoding="utf-8", errors="ignore") as f:
                        new_content = f.read()
            except Exception as e:
                logger.warning(f"Could not retrieve file contents for {filepath}: {e}")

            return FileDiff(
                filepath=filepath,
                status=status,
                old_content=old_content,
                new_content=new_content,
                diff_text=diff_text,
                hunks=hunks if hunks else [],
            )

        except subprocess.CalledProcessError as e:
            logger.error(f"Git diff command failed for {filepath}: {e.stderr}")
            return None

    def get_file_status(self, filepath: str) -> Optional[str]:
        """Get current status of a file (added/modified/deleted/untracked).

        Args:
            filepath: Path to file relative to repo root

        Returns:
            Status string or None if file not found in repo

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        try:
            # Check git status
            cmd = [
                "git",
                "-C",
                str(self.repo_path),
                "status",
                "--porcelain",
                filepath,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            if not result.stdout:
                return None

            status_codes = result.stdout.strip().split()[0]
            return status_codes

        except subprocess.CalledProcessError as e:
            logger.error(f"Git status command failed: {e.stderr}")
            return None

    def get_commit_history(self, filepath: str, limit: int = 10) -> List[Dict[str, str]]:
        """Get commit history for a file.

        Args:
            filepath: Path to file relative to repo root
            limit: Maximum number of commits to retrieve

        Returns:
            List of commit info dicts with hash, author, date, message

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        try:
            cmd = [
                "git",
                "-C",
                str(self.repo_path),
                "log",
                f"-{limit}",
                "--format=%H|%an|%ai|%s",
                "--",
                filepath,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            commits = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("|")
                if len(parts) >= 4:
                    commits.append(
                        {
                            "hash": parts[0],
                            "author": parts[1],
                            "date": parts[2],
                            "message": parts[3],
                        }
                    )

            return commits

        except subprocess.CalledProcessError as e:
            logger.error(f"Git log command failed: {e.stderr}")
            return []

    def get_changed_lines(
        self, filepath: str, since: str = "HEAD~1"
    ) -> Tuple[List[int], List[int]]:
        """Get line numbers that were added and deleted.

        Args:
            filepath: Path to file relative to repo root
            since: Git ref to compare against (default: "HEAD~1")

        Returns:
            Tuple of (added_lines, deleted_lines) as lists of line numbers

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        try:
            diff = self.get_changed_diff(filepath, since)
            if not diff:
                return [], []

            added_lines = []
            deleted_lines = []

            for hunk in diff.hunks:
                # Parse hunk header to get starting line numbers
                hunk_lines = hunk.get("lines", [])
                for i, line in enumerate(hunk_lines):
                    if line.startswith("+") and not line.startswith("+++"):
                        # Added line - get its line number
                        added_lines.append(i)
                    elif line.startswith("-") and not line.startswith("---"):
                        # Deleted line
                        deleted_lines.append(i)

            return added_lines, deleted_lines

        except Exception as e:
            logger.error(f"Could not get changed lines for {filepath}: {e}")
            return [], []

    def _parse_hunks(self, diff_text: str) -> List[Dict[str, any]]:
        """Parse unified diff text into hunks.

        Args:
            diff_text: Unified diff text from git diff

        Returns:
            List of hunks with line numbers and content
        """
        hunks = []
        current_hunk = None
        current_lines = []

        for line in diff_text.split("\n"):
            # Detect hunk header (@@ -x,y +a,b @@)
            if line.startswith("@@"):
                if current_hunk:
                    current_hunk["lines"] = current_lines
                    hunks.append(current_hunk)
                    current_lines = []

                # Parse hunk header
                import re

                match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
                if match:
                    current_hunk = {
                        "header": line,
                        "old_start": int(match.group(1)),
                        "old_lines": int(match.group(2)) if match.group(2) else 1,
                        "new_start": int(match.group(3)),
                        "new_lines": int(match.group(4)) if match.group(4) else 1,
                        "lines": [],
                    }
            elif current_hunk is not None:
                # Collect diff lines
                if line.startswith("+") or line.startswith("-") or line.startswith(" "):
                    current_lines.append(line)

        # Don't forget last hunk
        if current_hunk:
            current_hunk["lines"] = current_lines
            hunks.append(current_hunk)

        return hunks

    def get_related_files(self, filepath: str, distance: int = 2) -> List[Tuple[str, int]]:
        """Get files frequently changed together with given file.

        Args:
            filepath: Path to file relative to repo root
            distance: Number of commits to look back (default: 2)

        Returns:
            List of (filepath, co_occurrence_count) tuples, sorted by frequency

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        try:
            # Get commits that touched this file
            cmd = [
                "git",
                "-C",
                str(self.repo_path),
                "log",
                f"-{distance}",
                "--format=%H",
                "--",
                filepath,
            ]
            commit_result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            if not commit_result.stdout:
                return []

            commits = commit_result.stdout.strip().split("\n")

            # For each commit, get all files changed
            file_counts: Dict[str, int] = {}

            for commit in commits:
                if not commit:
                    continue

                files_cmd = [
                    "git",
                    "-C",
                    str(self.repo_path),
                    "show",
                    "--name-only",
                    "--pretty=",
                    commit,
                ]
                files_result = subprocess.run(files_cmd, capture_output=True, text=True, check=True)

                for changed_file in files_result.stdout.strip().split("\n"):
                    if changed_file and changed_file != filepath:
                        file_counts[changed_file] = file_counts.get(changed_file, 0) + 1

            # Sort by frequency
            related = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)
            return related

        except subprocess.CalledProcessError as e:
            logger.error(f"Could not get related files: {e.stderr}")
            return []

    def get_branch_info(self) -> Optional[str]:
        """Get current git branch name.

        Returns:
            Branch name or None if not on a branch

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        try:
            cmd = [
                "git",
                "-C",
                str(self.repo_path),
                "rev-parse",
                "--abbrev-ref",
                "HEAD",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout.strip() or None
        except subprocess.CalledProcessError:
            return None

    def get_unstaged_changes(self) -> List[FileChange]:
        """Get list of unstaged changes in working directory.

        Returns:
            List of FileChange objects for unstaged modifications

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        try:
            cmd = [
                "git",
                "-C",
                str(self.repo_path),
                "diff",
                "--name-status",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            changes = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("\t")
                status_char = parts[0]
                filepath = parts[1] if len(parts) > 1 else ""

                status_map = {
                    "A": "added",
                    "M": "modified",
                    "D": "deleted",
                    "R": "renamed",
                }

                change = FileChange(
                    filepath=filepath,
                    status=status_map.get(status_char, "unknown"),
                )
                changes.append(change)

            return changes

        except subprocess.CalledProcessError as e:
            logger.error(f"Git diff command failed: {e.stderr}")
            return []
