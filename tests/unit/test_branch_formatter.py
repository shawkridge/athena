"""Unit Tests for Branch Formatter

Tests branch name normalization, formatting, and display utilities.
"""

import sys

sys.path.insert(0, "/home/user/.claude/hooks/lib")

from branch_formatter import BranchFormatter


class TestBranchNormalization:
    """Test branch name normalization."""

    def test_normalize_feature_prefix(self):
        """Test removal of feature/ prefix."""
        assert BranchFormatter.normalize_branch_name("feature/user-auth") == "user-auth"
        assert BranchFormatter.normalize_branch_name("feat/payments") == "payments"

    def test_normalize_fix_prefix(self):
        """Test removal of fix/ prefix."""
        assert BranchFormatter.normalize_branch_name("fix/memory-leak") == "memory-leak"
        assert BranchFormatter.normalize_branch_name("bugfix/crash") == "crash"

    def test_normalize_system_branches(self):
        """Test that system branches are not modified."""
        assert BranchFormatter.normalize_branch_name("main") == "main"
        assert BranchFormatter.normalize_branch_name("master") == "master"
        assert BranchFormatter.normalize_branch_name("develop") == "develop"

    def test_normalize_no_prefix(self):
        """Test branches without recognized prefix."""
        assert BranchFormatter.normalize_branch_name("my-feature") == "my-feature"
        assert BranchFormatter.normalize_branch_name("bugfix123") == "bugfix123"

    def test_normalize_case_insensitive(self):
        """Test case-insensitive prefix matching."""
        assert BranchFormatter.normalize_branch_name("Feature/auth") == "auth"
        assert BranchFormatter.normalize_branch_name("FIX/bug") == "bug"


class TestBranchFormatting:
    """Test branch name display formatting."""

    def test_format_title_case(self):
        """Test title case formatting."""
        result = BranchFormatter.format_for_display("feature/user-authentication", style="title")
        assert result == "User Authentication"

    def test_format_lowercase(self):
        """Test lowercase formatting."""
        result = BranchFormatter.format_for_display("feature/user-auth", style="lower")
        assert result == "user auth"

    def test_format_uppercase(self):
        """Test uppercase formatting."""
        result = BranchFormatter.format_for_display("fix/memory-leak", style="upper")
        assert result == "MEMORY LEAK"

    def test_format_with_prefix(self):
        """Test formatting with type prefix."""
        result = BranchFormatter.format_for_display(
            "feature/user-auth",
            style="title",
            include_prefix=True,
        )
        assert result == "Feature: User Auth"

    def test_format_underscore_to_space(self):
        """Test that underscores are converted to spaces."""
        result = BranchFormatter.format_for_display("feature/user_authentication", style="title")
        assert result == "User Authentication"

    def test_format_system_branch(self):
        """Test formatting system branches."""
        result = BranchFormatter.format_for_display("main", style="title")
        assert result == "Main"


class TestFeatureExtraction:
    """Test extracting short feature names."""

    def test_extract_two_words(self):
        """Test extracting first two words."""
        result = BranchFormatter.extract_feature_name("feature/user-authentication-system")
        assert result == "User Authentication"

    def test_extract_one_word(self):
        """Test extracting single word."""
        result = BranchFormatter.extract_feature_name("fix/critical-memory-leak", max_words=1)
        assert result == "Critical"

    def test_extract_with_underscores(self):
        """Test extraction handles underscores."""
        result = BranchFormatter.extract_feature_name("feature/user_auth_system", max_words=2)
        assert result == "User Auth"


class TestWorktreeLabel:
    """Test worktree label generation."""

    def test_label_from_branch(self):
        """Test generating label from branch name."""
        result = BranchFormatter.get_worktree_label(branch_name="feature/user-auth")
        assert result == "User Auth"

    def test_label_from_path(self):
        """Test generating label from worktree path."""
        result = BranchFormatter.get_worktree_label(
            worktree_path="/home/user/.work/athena-feature-auth"
        )
        assert "auth" in result.lower()

    def test_label_branch_preferred(self):
        """Test that branch name is preferred over path."""
        result = BranchFormatter.get_worktree_label(
            branch_name="feature/payments",
            worktree_path="/home/user/.work/athena-feature-auth",
        )
        assert result == "Payments"

    def test_label_default(self):
        """Test default label when nothing provided."""
        result = BranchFormatter.get_worktree_label()
        assert result == "main"


class TestBranchStatistics:
    """Test branch naming pattern analysis."""

    def test_stats_with_mixed_branches(self):
        """Test statistics on mixed branch types."""
        branches = [
            "feature/auth",
            "feature/payments",
            "fix/memory-leak",
            "main",
            "develop",
        ]
        stats = BranchFormatter.get_branch_statistics(branches)

        assert stats["feature"] == 2
        assert stats["fix"] == 1
        assert stats["system"] == 2

    def test_stats_with_unrecognized(self):
        """Test statistics with unrecognized prefixes."""
        branches = ["my-branch", "random-feature"]
        stats = BranchFormatter.get_branch_statistics(branches)

        assert stats["other"] == 2


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_string(self):
        """Test handling empty string."""
        assert BranchFormatter.normalize_branch_name("") == ""
        assert BranchFormatter.format_for_display("") == ""

    def test_none_value(self):
        """Test handling None values."""
        assert BranchFormatter.normalize_branch_name(None) == None

    def test_multiple_consecutive_separators(self):
        """Test handling multiple separators."""
        result = BranchFormatter.format_for_display("feature/user---auth---system", style="title")
        # Should collapse multiple separators
        assert "Auth" in result and "User" in result

    def test_special_characters(self):
        """Test handling special characters in branch names."""
        result = BranchFormatter.format_for_display("feature/user-auth-2024", style="title")
        assert "User" in result and "Auth" in result
