"""Git-aware code analyzer that prioritizes changed files."""

import logging
from pathlib import Path
from typing import List, Optional, Dict

from .git_context import GitContext
from .enhanced_parser import EnhancedCodeParser
from .models import CodeElement

logger = logging.getLogger(__name__)


class GitAwareAnalyzer:
    """Analyzes code with awareness of git changes for context prioritization."""

    def __init__(self, repo_path: str | Path = "."):
        """Initialize the git-aware analyzer.

        Args:
            repo_path: Path to git repository

        Raises:
            ValueError: If path is not a git repository
        """
        self.repo_path = Path(repo_path)
        self.git = GitContext(repo_path)
        self.parser = EnhancedCodeParser()
        self.changed_files_cache: Optional[Dict] = None

    def analyze_changes(self, since: str = "HEAD~1") -> Dict[str, List[CodeElement]]:
        """Analyze all changed files and parse their contents.

        Args:
            since: Git ref to compare against (default: "HEAD~1")

        Returns:
            Dict mapping filepath to list of CodeElement objects

        Raises:
            ValueError: If git operations fail
        """
        try:
            # Get changed files
            changes = self.git.get_changed_files(since)

            result = {}
            for change in changes:
                filepath = str(self.repo_path / change.filepath)

                # Skip deleted files
                if change.status == "deleted":
                    logger.debug(f"Skipping deleted file: {change.filepath}")
                    continue

                try:
                    # Parse the changed file
                    elements = self.parser.parse_file(filepath)
                    result[change.filepath] = elements

                    logger.debug(f"Analyzed {change.filepath}: {len(elements)} elements")
                except Exception as e:
                    logger.warning(f"Failed to parse {change.filepath}: {e}")

            return result

        except Exception as e:
            logger.error(f"Failed to analyze changes: {e}")
            raise

    def get_prioritized_context(
        self, since: str = "HEAD~1", include_related: bool = True
    ) -> List[str]:
        """Get a prioritized list of files to include in context.

        Prioritizes:
        1. Changed files (highest priority)
        2. Related files (frequently changed together)
        3. Files with high impact changes (more additions/deletions)

        Args:
            since: Git ref to compare against
            include_related: If True, include related files in priority

        Returns:
            List of filepaths sorted by priority

        Raises:
            ValueError: If git operations fail
        """
        try:
            changes = self.git.get_changed_files(since)

            # Sort by impact (lines changed)
            sorted_changes = sorted(
                changes,
                key=lambda c: (c.lines_added + c.lines_deleted),
                reverse=True,
            )

            prioritized = []

            for change in sorted_changes:
                if change.status == "deleted":
                    continue

                prioritized.append(change.filepath)

                # Optionally add related files
                if include_related:
                    related = self.git.get_related_files(change.filepath, distance=5)
                    for related_file, _ in related:
                        if related_file not in prioritized:
                            prioritized.append(related_file)

            return prioritized

        except Exception as e:
            logger.error(f"Failed to get prioritized context: {e}")
            raise

    def get_diff_context(self, filepath: str, since: str = "HEAD~1") -> Optional[str]:
        """Get diff and context information for a file.

        Args:
            filepath: Path to file relative to repo root
            since: Git ref to compare against

        Returns:
            Formatted diff context string, or None if file not changed

        Raises:
            ValueError: If git operations fail
        """
        try:
            diff = self.git.get_changed_diff(filepath, since)

            if not diff:
                return None

            # Build context string
            lines = [
                f"=== File: {filepath} ===",
                f"Status: {diff.status}",
                "",
                "--- Diff ---",
                diff.diff_text,
                "",
            ]

            if diff.hunks:
                lines.append(f"--- Hunks: {len(diff.hunks)} ---")
                for i, hunk in enumerate(diff.hunks, 1):
                    lines.append(f"Hunk {i}: {hunk.get('header', '')}")
                    lines.append(
                        f"  Old lines: {hunk.get('old_start', '')}-{hunk.get('old_lines', '')}"
                    )
                    lines.append(
                        f"  New lines: {hunk.get('new_start', '')}-{hunk.get('new_lines', '')}"
                    )

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Failed to get diff context for {filepath}: {e}")
            return None

    def get_change_summary(self, since: str = "HEAD~1") -> Dict[str, any]:
        """Get a summary of all changes.

        Args:
            since: Git ref to compare against

        Returns:
            Dict with summary statistics

        Raises:
            ValueError: If git operations fail
        """
        try:
            changes = self.git.get_changed_files(since)

            summary = {
                "total_files_changed": len(changes),
                "added_files": len([c for c in changes if c.status == "added"]),
                "modified_files": len([c for c in changes if c.status == "modified"]),
                "deleted_files": len([c for c in changes if c.status == "deleted"]),
                "total_lines_added": sum(c.lines_added for c in changes),
                "total_lines_deleted": sum(c.lines_deleted for c in changes),
                "files_by_impact": [],
            }

            # Top files by impact
            sorted_changes = sorted(
                changes,
                key=lambda c: (c.lines_added + c.lines_deleted),
                reverse=True,
            )

            for change in sorted_changes[:10]:  # Top 10
                summary["files_by_impact"].append(
                    {
                        "filepath": change.filepath,
                        "status": change.status,
                        "lines_added": change.lines_added,
                        "lines_deleted": change.lines_deleted,
                    }
                )

            return summary

        except Exception as e:
            logger.error(f"Failed to get change summary: {e}")
            raise

    def get_changed_elements(self, since: str = "HEAD~1") -> List[CodeElement]:
        """Get all CodeElements from changed files.

        Args:
            since: Git ref to compare against

        Returns:
            List of CodeElement objects from changed files

        Raises:
            ValueError: If git operations fail
        """
        try:
            analyzed = self.analyze_changes(since)
            elements = []

            for filepath, file_elements in analyzed.items():
                elements.extend(file_elements)

            # Sort by file priority
            prioritized = self.get_prioritized_context(since, include_related=False)
            priority_map = {f: i for i, f in enumerate(prioritized)}

            elements.sort(key=lambda e: (priority_map.get(e.file_path, 9999), e.start_line))

            return elements

        except Exception as e:
            logger.error(f"Failed to get changed elements: {e}")
            raise

    def get_commit_history_for_changes(
        self, since: str = "HEAD~1", limit: int = 5
    ) -> Dict[str, List[Dict]]:
        """Get commit history for all changed files.

        Args:
            since: Git ref to compare against
            limit: Number of commits to retrieve per file

        Returns:
            Dict mapping filepath to list of commits

        Raises:
            ValueError: If git operations fail
        """
        try:
            changes = self.git.get_changed_files(since)
            result = {}

            for change in changes:
                if change.status == "deleted":
                    continue

                commits = self.git.get_commit_history(change.filepath, limit)
                result[change.filepath] = commits

            return result

        except Exception as e:
            logger.error(f"Failed to get commit history: {e}")
            raise

    def get_file_impact_score(self, filepath: str, since: str = "HEAD~1") -> float:
        """Calculate impact score for a file (0-1).

        Considers:
        - Lines changed
        - Type of change (added vs modified)
        - Related files affected

        Args:
            filepath: Path to file relative to repo root
            since: Git ref to compare against

        Returns:
            Impact score from 0 (no impact) to 1 (high impact)

        Raises:
            ValueError: If git operations fail
        """
        try:
            changes = self.git.get_changed_files(since)
            target_change = next((c for c in changes if c.filepath == filepath), None)

            if not target_change:
                return 0.0

            # Base score on lines changed
            total_changes = target_change.lines_added + target_change.lines_deleted
            change_score = min(total_changes / 100, 1.0)  # Normalize to 0-1

            # Boost for added files
            status_boost = 1.2 if target_change.status == "added" else 1.0

            # Check if many files are related
            related = self.git.get_related_files(filepath, distance=3)
            related_boost = min(len(related) / 5, 1.0) * 0.3  # Up to 0.3 boost

            score = change_score * status_boost + related_boost
            return min(score, 1.0)

        except Exception as e:
            logger.error(f"Failed to calculate impact score for {filepath}: {e}")
            return 0.0


def create_git_aware_analyzer(repo_path: str | Path = ".") -> GitAwareAnalyzer:
    """Factory function to create a GitAwareAnalyzer.

    Args:
        repo_path: Path to git repository

    Returns:
        GitAwareAnalyzer instance

    Raises:
        ValueError: If path is not a git repository
    """
    return GitAwareAnalyzer(repo_path)
