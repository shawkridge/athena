"""Unit Tests for Git Worktree Helper

Tests git worktree detection, path handling, and isolation mechanisms.
"""

import pytest
import os
import tempfile
import subprocess
from pathlib import Path


class TestGitWorktreeHelper:
    """Test suite for GitWorktreeHelper class."""

    @pytest.fixture
    def git_repo(self, tmp_path):
        """Create a temporary git repository."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Initialize repo
        subprocess.run(
            ["git", "init"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Configure git user (required for commits)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create initial commit
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "initial"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        return repo_path

    def test_main_worktree_detection(self, git_repo):
        """Test detection of main repository (not a worktree)."""
        # Import here to ensure sys.path is set up
        import sys
        sys.path.insert(0, "/home/user/.claude/hooks/lib")
        from git_worktree_helper import GitWorktreeHelper

        helper = GitWorktreeHelper()
        info = helper.get_worktree_info(str(git_repo))

        assert info["is_main_worktree"] is True
        assert info["is_worktree"] is False
        assert info["worktree_path"] == str(git_repo.resolve())
        assert info["main_worktree_path"] == str(git_repo.resolve())
        assert info["worktree_branch"] == "master" or info["worktree_branch"] == "main"

    def test_worktree_detection(self, git_repo):
        """Test detection of git worktree."""
        import sys
        sys.path.insert(0, "/home/user/.claude/hooks/lib")
        from git_worktree_helper import GitWorktreeHelper

        # Create a worktree
        worktree_path = git_repo.parent / "worktree_feature"
        subprocess.run(
            ["git", "worktree", "add", str(worktree_path), "-b", "feature/test"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        try:
            helper = GitWorktreeHelper()
            info = helper.get_worktree_info(str(worktree_path))

            assert info["is_worktree"] is True
            assert info["is_main_worktree"] is False
            assert info["worktree_path"] == str(worktree_path.resolve())
            assert info["worktree_branch"] == "feature/test"
            assert info["main_worktree_path"] == str(git_repo.resolve())
        finally:
            # Cleanup worktree
            subprocess.run(
                ["git", "worktree", "remove", str(worktree_path)],
                cwd=git_repo,
                check=True,
                capture_output=True,
            )

    def test_non_git_directory(self, tmp_path):
        """Test behavior in non-git directory."""
        import sys
        sys.path.insert(0, "/home/user/.claude/hooks/lib")
        from git_worktree_helper import GitWorktreeHelper

        non_git_dir = tmp_path / "not_a_repo"
        non_git_dir.mkdir()

        helper = GitWorktreeHelper()
        info = helper.get_worktree_info(str(non_git_dir))

        assert info["is_worktree"] is False
        assert info["worktree_path"] is None
        assert info["worktree_branch"] is None

    def test_get_isolation_key_git_repo(self, git_repo):
        """Test isolation key for git repository."""
        import sys
        sys.path.insert(0, "/home/user/.claude/hooks/lib")
        from git_worktree_helper import GitWorktreeHelper

        helper = GitWorktreeHelper()
        key = helper.get_isolation_key(str(git_repo))

        # Should return the git root path
        assert key == str(git_repo.resolve())

    def test_get_isolation_key_non_git(self, tmp_path):
        """Test isolation key for non-git directory."""
        import sys
        sys.path.insert(0, "/home/user/.claude/hooks/lib")
        from git_worktree_helper import GitWorktreeHelper

        non_git_dir = tmp_path / "not_a_repo"
        non_git_dir.mkdir()

        helper = GitWorktreeHelper()
        key = helper.get_isolation_key(str(non_git_dir))

        # Should return absolute path to directory
        assert key == str(non_git_dir.resolve())

    def test_is_same_project(self, git_repo):
        """Test project comparison across worktrees."""
        import sys
        sys.path.insert(0, "/home/user/.claude/hooks/lib")
        from git_worktree_helper import GitWorktreeHelper

        # Create a worktree
        worktree_path = git_repo.parent / "worktree_feature"
        subprocess.run(
            ["git", "worktree", "add", str(worktree_path), "-b", "feature/test"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        try:
            helper = GitWorktreeHelper()

            # Main repo and worktree should be same project
            assert helper.is_same_project(str(git_repo), str(worktree_path)) is True

            # Non-git dirs shouldn't match anything
            non_git = git_repo.parent / "not_a_repo"
            non_git.mkdir()
            assert helper.is_same_project(str(git_repo), str(non_git)) is False
        finally:
            # Cleanup
            subprocess.run(
                ["git", "worktree", "remove", str(worktree_path)],
                cwd=git_repo,
                check=True,
                capture_output=True,
            )

    def test_list_worktrees(self, git_repo):
        """Test listing all worktrees in a repository."""
        import sys
        sys.path.insert(0, "/home/user/.claude/hooks/lib")
        from git_worktree_helper import GitWorktreeHelper

        # Create multiple worktrees
        worktree1 = git_repo.parent / "worktree1"
        worktree2 = git_repo.parent / "worktree2"

        subprocess.run(
            ["git", "worktree", "add", str(worktree1), "-b", "feature/one"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "worktree", "add", str(worktree2), "-b", "feature/two"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        try:
            helper = GitWorktreeHelper()
            worktrees = helper.list_worktrees(str(git_repo))

            # Should include main repo + 2 worktrees = 3 total
            assert len(worktrees) >= 3

            # Check worktree paths are included
            paths = [wt["path"] for wt in worktrees]
            assert str(git_repo) in paths
            assert str(worktree1) in paths
            assert str(worktree2) in paths

        finally:
            # Cleanup
            subprocess.run(
                ["git", "worktree", "remove", str(worktree1)],
                cwd=git_repo,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "worktree", "remove", str(worktree2)],
                cwd=git_repo,
                check=True,
                capture_output=True,
            )


class TestWorktreeIntegration:
    """Integration tests for worktree-aware systems."""

    def test_todowrite_isolation_by_worktree(self):
        """Test that todos are isolated per worktree."""
        # This test would require a real database setup
        # Marking as placeholder for now
        pytest.skip("Requires database setup")

    def test_memory_cross_worktree_access(self):
        """Test that memories are accessible across worktrees but prioritized locally."""
        # This test would require a real database and memory system
        # Marking as placeholder for now
        pytest.skip("Requires database setup")

    def test_session_start_worktree_context(self):
        """Test that session-start properly displays worktree context."""
        # This test would require running the actual session-start.sh hook
        # Marking as placeholder for now
        pytest.skip("Requires hook execution environment")
