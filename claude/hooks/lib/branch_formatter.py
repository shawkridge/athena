"""Branch Name Formatter

Converts git branch names to human-readable display formats for UI contexts.
Handles normalization, feature extraction, and special character handling.

Examples:
  "feature/user-authentication" → "user-authentication" or "User Authentication"
  "fix/critical-bug-in-parser" → "critical-bug-in-parser" or "Critical Bug In Parser"
  "main" → "main" or "Main"
  "develop" → "develop" or "Develop"
"""

import re
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class BranchFormatter:
    """Format git branch names for human-readable display."""

    # Common branch prefixes that can be stripped
    BRANCH_PREFIXES = [
        "feature/",
        "feat/",
        "fix/",
        "bugfix/",
        "hotfix/",
        "release/",
        "rel/",
        "chore/",
        "docs/",
        "style/",
        "refactor/",
        "perf/",
        "ci/",
        "test/",
        "wip/",  # Work in progress
    ]

    # System branches that should not be formatted
    SYSTEM_BRANCHES = {"main", "master", "develop", "development", "staging", "prod", "production"}

    @staticmethod
    def normalize_branch_name(branch_name: str) -> str:
        """Remove common prefixes from branch name.

        Args:
            branch_name: Full git branch name (e.g., "feature/user-auth")

        Returns:
            Normalized name without prefix (e.g., "user-auth")

        Examples:
            >>> BranchFormatter.normalize_branch_name("feature/user-auth")
            "user-auth"
            >>> BranchFormatter.normalize_branch_name("fix/memory-leak")
            "memory-leak"
            >>> BranchFormatter.normalize_branch_name("main")
            "main"
        """
        if not branch_name:
            return branch_name

        # Check if it's a system branch (don't normalize)
        if branch_name.lower() in BranchFormatter.SYSTEM_BRANCHES:
            return branch_name

        # Try removing each known prefix (case-insensitive)
        lower_branch = branch_name.lower()
        for prefix in BranchFormatter.BRANCH_PREFIXES:
            if lower_branch.startswith(prefix):
                return branch_name[len(prefix) :]

        # No known prefix found, return as-is
        return branch_name

    @staticmethod
    def format_for_display(
        branch_name: str,
        style: str = "title",
        include_prefix: bool = False,
    ) -> str:
        """Format branch name for UI display.

        Args:
            branch_name: Full git branch name
            style: Format style - "title" (title case), "lower" (lowercase), "upper" (UPPERCASE)
            include_prefix: If True, keep the type prefix (e.g., "Feature: User Auth")

        Returns:
            Formatted branch name for display

        Examples:
            >>> BranchFormatter.format_for_display("feature/user-authentication", style="title")
            "User Authentication"
            >>> BranchFormatter.format_for_display("fix/memory-leak", style="lower")
            "memory leak"
            >>> BranchFormatter.format_for_display("feature/user-auth", include_prefix=True)
            "Feature: User Auth"
        """
        if not branch_name:
            return ""

        # Extract type and name if it has a recognized prefix
        branch_type = None
        normalized = branch_name

        lower_branch = branch_name.lower()
        for prefix in BranchFormatter.BRANCH_PREFIXES:
            if lower_branch.startswith(prefix):
                # Extract type (e.g., "feature" from "feature/")
                branch_type = prefix.rstrip("/")
                normalized = branch_name[len(prefix) :]
                break

        # Convert hyphens/underscores to spaces for display
        display_name = re.sub(r"[-_]+", " ", normalized)

        # Apply style formatting
        if style == "title":
            display_name = BranchFormatter._title_case(display_name)
        elif style == "upper":
            display_name = display_name.upper()
        elif style == "lower":
            display_name = display_name.lower()
        # "mixed" and others are left as-is after space conversion

        # Add prefix back if requested
        if include_prefix and branch_type:
            branch_type_display = BranchFormatter._title_case(branch_type)
            return f"{branch_type_display}: {display_name}"

        return display_name

    @staticmethod
    def extract_feature_name(branch_name: str, max_words: int = 2) -> str:
        """Extract the core feature name from a branch.

        Useful for creating short labels. Takes first N words of normalized name.

        Args:
            branch_name: Full git branch name
            max_words: Maximum words to include in extracted name

        Returns:
            Short feature name (first N words)

        Examples:
            >>> BranchFormatter.extract_feature_name("feature/user-authentication-system")
            "User Authentication"
            >>> BranchFormatter.extract_feature_name("fix/critical-memory-leak-in-parser", max_words=2)
            "Critical Memory"
        """
        # Normalize first
        normalized = BranchFormatter.normalize_branch_name(branch_name)

        # Convert hyphens to spaces
        words = re.split(r"[-_\s]+", normalized)

        # Filter out empty strings
        words = [w for w in words if w]

        # Take first N words
        selected = words[:max_words]

        # Join and title case
        result = " ".join(selected)
        return BranchFormatter._title_case(result)

    @staticmethod
    def get_worktree_label(
        branch_name: Optional[str] = None,
        worktree_path: Optional[str] = None,
        format_style: str = "title",
    ) -> str:
        """Get a display label for a worktree.

        Prefers formatted branch name over worktree path.

        Args:
            branch_name: Git branch name (preferred)
            worktree_path: Full worktree path (fallback)
            format_style: How to format the branch name

        Returns:
            Human-readable worktree label for display

        Examples:
            >>> BranchFormatter.get_worktree_label(branch_name="feature/user-auth")
            "User Auth"
            >>> BranchFormatter.get_worktree_label(worktree_path="/home/user/.work/athena-feature-auth")
            "athena-feature-auth"
        """
        if branch_name:
            # Use formatted branch name (short version)
            return BranchFormatter.extract_feature_name(branch_name, max_words=2)

        if worktree_path:
            # Fallback: extract worktree directory name
            import os
            dirname = os.path.basename(worktree_path.rstrip("/"))
            # Remove "athena-" prefix if present
            if dirname.startswith("athena-"):
                dirname = dirname[7:]  # Remove "athena-"
            return dirname

        return "main"

    @staticmethod
    def _title_case(text: str) -> str:
        """Convert text to title case, handling hyphenated words.

        Args:
            text: Text to convert

        Returns:
            Title-cased text

        Examples:
            >>> BranchFormatter._title_case("user authentication")
            "User Authentication"
            >>> BranchFormatter._title_case("user-authentication")
            "User Authentication"
        """
        # Split on hyphens and spaces
        words = re.split(r"([-\s]+)", text.lower())

        # Capitalize first letter of non-separator words
        result = []
        for word in words:
            if re.match(r"[-\s]+", word):
                # Keep separators as-is
                result.append(word)
            elif word:
                # Capitalize first letter
                result.append(word[0].upper() + word[1:] if len(word) > 1 else word.upper())

        return "".join(result)

    @staticmethod
    def get_branch_statistics(branches: list[str]) -> Dict[str, int]:
        """Analyze branch naming patterns in a list of branches.

        Useful for understanding naming conventions in a project.

        Args:
            branches: List of branch names

        Returns:
            Dict with type counts and statistics

        Examples:
            >>> stats = BranchFormatter.get_branch_statistics([
            ...     "feature/auth", "feature/payments", "fix/memory-leak", "main"
            ... ])
            >>> stats["feature"]
            2
            >>> stats["fix"]
            1
        """
        stats = {}

        for branch in branches:
            # Find matching prefix
            found_type = None
            lower_branch = branch.lower()

            for prefix in BranchFormatter.BRANCH_PREFIXES:
                if lower_branch.startswith(prefix):
                    found_type = prefix.rstrip("/")
                    break

            # Count system branches
            if branch.lower() in BranchFormatter.SYSTEM_BRANCHES:
                found_type = "system"
            elif not found_type:
                found_type = "other"

            # Increment counter
            stats[found_type] = stats.get(found_type, 0) + 1

        return stats
