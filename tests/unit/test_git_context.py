"""Unit tests for git_context module."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from athena.code.git_context import GitContext, FileChange, FileDiff


class TestGitContextInitialization:
    """Test GitContext initialization."""

    def test_init_with_valid_git_repo(self, tmp_path):
        """Test initializing with a valid git repository."""
        # Create a git repo
        subprocess.run(["git", "init"], cwd=tmp_path, check=True)

        # Should not raise
        git = GitContext(tmp_path)
        assert git.repo_path == tmp_path

    def test_init_with_invalid_path_raises_error(self, tmp_path):
        """Test that initialization fails with non-git directory."""
        with pytest.raises(ValueError, match="is not a git repository"):
            GitContext(tmp_path)

    def test_init_with_string_path(self, tmp_path):
        """Test initialization with string path."""
        subprocess.run(["git", "init"], cwd=tmp_path, check=True)

        git = GitContext(str(tmp_path))
        assert git.repo_path == tmp_path


class TestGetChangedFiles:
    """Test get_changed_files method."""

    @pytest.fixture
    def git_repo_with_changes(self, tmp_path):
        """Create a git repo with one commit and changes."""
        # Initialize repo
        subprocess.run(["git", "init"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            check=True,
        )

        # Create initial file and commit
        file1 = tmp_path / "file1.py"
        file1.write_text("print('hello')\n")
        subprocess.run(["git", "add", "file1.py"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=tmp_path,
            check=True,
        )

        # Make changes: modify file1, add file2, delete file1
        file1.write_text("print('hello world')\nprint('more')\n")
        file2 = tmp_path / "file2.py"
        file2.write_text("print('new file')\n")
        file3 = tmp_path / "file3.py"
        file3.write_text("to delete\n")

        subprocess.run(["git", "add", "file2.py"], cwd=tmp_path, check=True)
        subprocess.run(["git", "add", "file3.py"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-m", "Add files"], cwd=tmp_path, check=True)

        file1.write_text("print('modified again')\n")
        subprocess.run(["git", "add", "file1.py"], cwd=tmp_path, check=True)
        file3.unlink()
        subprocess.run(["git", "rm", "file3.py"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "More changes"],
            cwd=tmp_path,
            check=True,
        )

        return tmp_path

    def test_get_changed_files_since_head_minus_1(self, git_repo_with_changes):
        """Test getting changed files since HEAD~1."""
        git = GitContext(git_repo_with_changes)
        changes = git.get_changed_files(since="HEAD~1")

        # Should have 2 files changed: file1 (modified), file3 (deleted)
        assert len(changes) > 0
        filepaths = [c.filepath for c in changes]
        assert "file1.py" in filepaths

    def test_changed_files_have_correct_status(self, git_repo_with_changes):
        """Test that changed files have correct status."""
        git = GitContext(git_repo_with_changes)
        changes = git.get_changed_files(since="HEAD~1")

        changes_dict = {c.filepath: c for c in changes}
        assert "file1.py" in changes_dict
        assert changes_dict["file1.py"].status == "modified"

    def test_get_changed_files_with_stats(self, git_repo_with_changes):
        """Test that line statistics are populated."""
        git = GitContext(git_repo_with_changes)
        changes = git.get_changed_files(since="HEAD~1")

        # Modified file should have line stats
        file1_change = next((c for c in changes if c.filepath == "file1.py"), None)
        assert file1_change is not None
        assert file1_change.lines_added > 0

    def test_get_changed_files_empty_when_no_changes(self, tmp_path):
        """Test empty list when no changes since last commit."""
        subprocess.run(["git", "init"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            check=True,
        )

        file1 = tmp_path / "file.py"
        file1.write_text("code")
        subprocess.run(["git", "add", "file.py"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "Empty"],
            cwd=tmp_path,
            check=True,
        )

        git = GitContext(tmp_path)
        changes = git.get_changed_files(since="HEAD~1")

        # No actual file changes in the empty commit
        assert len(changes) == 0


class TestGetChangedDiff:
    """Test get_changed_diff method."""

    @pytest.fixture
    def git_repo_with_diff(self, tmp_path):
        """Create a git repo with a modified file."""
        subprocess.run(["git", "init"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            check=True,
        )

        # Create initial file
        file1 = tmp_path / "example.py"
        file1.write_text("def hello():\n    print('hello')\n")
        subprocess.run(["git", "add", "example.py"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=tmp_path,
            check=True,
        )

        # Modify the file
        file1.write_text(
            "def hello():\n    print('hello world')\n\ndef goodbye():\n    print('bye')\n"
        )
        subprocess.run(["git", "add", "example.py"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add goodbye"],
            cwd=tmp_path,
            check=True,
        )

        return tmp_path

    def test_get_changed_diff_returns_diff(self, git_repo_with_diff):
        """Test that get_changed_diff returns diff text."""
        git = GitContext(git_repo_with_diff)
        diff = git.get_changed_diff("example.py", since="HEAD~1")

        assert diff is not None
        assert diff.filepath == "example.py"
        assert diff.status == "modified"
        assert len(diff.diff_text) > 0

    def test_diff_contains_hunks(self, git_repo_with_diff):
        """Test that diff is parsed into hunks."""
        git = GitContext(git_repo_with_diff)
        diff = git.get_changed_diff("example.py", since="HEAD~1")

        assert diff is not None
        assert len(diff.hunks) > 0
        assert diff.hunks[0].get("header") is not None

    def test_diff_has_content(self, git_repo_with_diff):
        """Test that old and new content are retrieved."""
        git = GitContext(git_repo_with_diff)
        diff = git.get_changed_diff("example.py", since="HEAD~1")

        assert diff is not None
        assert diff.old_content is not None
        assert diff.new_content is not None
        assert "hello world" in diff.new_content

    def test_diff_returns_diff_for_added_file(self, git_repo_with_diff):
        """Test that diff returns FileDiff for newly added files."""
        git = GitContext(git_repo_with_diff)

        # Create another file and commit it
        other_file = git_repo_with_diff / "other.py"
        other_file.write_text("other code")
        subprocess.run(["git", "add", "other.py"], cwd=git_repo_with_diff, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add other"],
            cwd=git_repo_with_diff,
            check=True,
        )

        # Now it should be in HEAD~1 and marked as added
        diff = git.get_changed_diff("other.py", since="HEAD~1")
        assert diff is not None
        assert diff.status == "added"


class TestGetFileStatus:
    """Test get_file_status method."""

    def test_get_status_modified_file(self, tmp_path):
        """Test getting status of modified file."""
        subprocess.run(["git", "init"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            check=True,
        )

        file1 = tmp_path / "file.py"
        file1.write_text("original")
        subprocess.run(["git", "add", "file.py"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=tmp_path,
            check=True,
        )

        file1.write_text("modified")

        git = GitContext(tmp_path)
        status = git.get_file_status("file.py")

        # Should indicate modification
        assert status is not None
        assert "M" in status

    def test_get_status_nonexistent_file(self, tmp_path):
        """Test getting status of file not in repo."""
        subprocess.run(["git", "init"], cwd=tmp_path, check=True)

        git = GitContext(tmp_path)
        status = git.get_file_status("nonexistent.py")

        assert status is None


class TestGetCommitHistory:
    """Test get_commit_history method."""

    @pytest.fixture
    def git_repo_with_history(self, tmp_path):
        """Create repo with multiple commits touching a file."""
        subprocess.run(["git", "init"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            check=True,
        )

        file1 = tmp_path / "file.py"

        # Create 3 commits
        for i in range(3):
            file1.write_text(f"version {i}\n")
            subprocess.run(["git", "add", "file.py"], cwd=tmp_path, check=True)
            subprocess.run(
                ["git", "commit", "-m", f"Update {i}"],
                cwd=tmp_path,
                check=True,
            )

        return tmp_path

    def test_get_commit_history_returns_commits(self, git_repo_with_history):
        """Test that commit history is retrieved."""
        git = GitContext(git_repo_with_history)
        commits = git.get_commit_history("file.py", limit=10)

        assert len(commits) > 0
        assert commits[0].get("hash") is not None
        assert commits[0].get("author") is not None
        assert commits[0].get("message") is not None

    def test_commit_history_respects_limit(self, git_repo_with_history):
        """Test that limit parameter is respected."""
        git = GitContext(git_repo_with_history)
        commits = git.get_commit_history("file.py", limit=2)

        assert len(commits) <= 2


class TestParseHunks:
    """Test _parse_hunks method."""

    def test_parse_single_hunk(self):
        """Test parsing a single hunk."""
        diff_text = """@@ -1,3 +1,4 @@
 line1
-line2
+line2_modified
+line2_new
 line3
"""
        git = GitContext.__new__(GitContext)
        hunks = git._parse_hunks(diff_text)

        assert len(hunks) == 1
        assert hunks[0]["old_start"] == 1
        assert hunks[0]["old_lines"] == 3
        assert hunks[0]["new_start"] == 1
        assert hunks[0]["new_lines"] == 4

    def test_parse_multiple_hunks(self):
        """Test parsing multiple hunks."""
        diff_text = """@@ -1,3 +1,3 @@
 line1
-line2
+line2_new
 line3
@@ -10,2 +10,3 @@
 line10
+line10_new
 line11
"""
        git = GitContext.__new__(GitContext)
        hunks = git._parse_hunks(diff_text)

        assert len(hunks) == 2
        assert hunks[0]["old_start"] == 1
        assert hunks[1]["old_start"] == 10

    def test_parse_hunk_with_context_lines(self):
        """Test that hunk includes context and change lines."""
        diff_text = """@@ -1,5 +1,5 @@
 context1
-removed
+added
 context2
 context3
"""
        git = GitContext.__new__(GitContext)
        hunks = git._parse_hunks(diff_text)

        assert len(hunks) == 1
        lines = hunks[0]["lines"]
        assert any(line.startswith(" context1") for line in lines)
        assert any(line.startswith("-removed") for line in lines)
        assert any(line.startswith("+added") for line in lines)


class TestGetRelatedFiles:
    """Test get_related_files method."""

    @pytest.fixture
    def git_repo_with_related_files(self, tmp_path):
        """Create repo where files are changed together."""
        subprocess.run(["git", "init"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            check=True,
        )

        # Create 3 files and modify them together multiple times
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file3 = tmp_path / "file3.py"

        for i in range(2):
            file1.write_text(f"file1 v{i}")
            file2.write_text(f"file2 v{i}")
            file3.write_text(f"file3 v{i}")

            for f in [file1, file2, file3]:
                subprocess.run(["git", "add", f.name], cwd=tmp_path, check=True)

            subprocess.run(
                ["git", "commit", "-m", f"Batch {i}"],
                cwd=tmp_path,
                check=True,
            )

        return tmp_path

    def test_get_related_files_returns_list(self, git_repo_with_related_files):
        """Test that related files are returned."""
        git = GitContext(git_repo_with_related_files)
        related = git.get_related_files("file1.py", distance=5)

        assert isinstance(related, list)
        # Should find file2 and file3 as related
        related_files = [f[0] for f in related]
        assert "file2.py" in related_files or "file3.py" in related_files

    def test_related_files_sorted_by_frequency(self, git_repo_with_related_files):
        """Test that related files are sorted by co-occurrence."""
        git = GitContext(git_repo_with_related_files)
        related = git.get_related_files("file1.py", distance=5)

        # Should be sorted by frequency (second element in tuple)
        if len(related) > 1:
            for i in range(len(related) - 1):
                assert related[i][1] >= related[i + 1][1]


class TestGetBranchInfo:
    """Test get_branch_info method."""

    def test_get_current_branch(self, tmp_path):
        """Test getting current branch name."""
        subprocess.run(["git", "init"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            check=True,
        )

        # Create initial commit
        (tmp_path / "file.txt").write_text("content")
        subprocess.run(["git", "add", "file.txt"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=tmp_path,
            check=True,
        )

        git = GitContext(tmp_path)
        branch = git.get_branch_info()

        assert branch in ["master", "main"]  # Default branch name


class TestGetUnstagedChanges:
    """Test get_unstaged_changes method."""

    def test_get_unstaged_modifications(self, tmp_path):
        """Test getting unstaged changes."""
        subprocess.run(["git", "init"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            check=True,
        )

        file1 = tmp_path / "file.py"
        file1.write_text("original")
        subprocess.run(["git", "add", "file.py"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=tmp_path,
            check=True,
        )

        # Make unstaged change
        file1.write_text("modified but not staged")

        git = GitContext(tmp_path)
        changes = git.get_unstaged_changes()

        assert len(changes) > 0
        assert changes[0].filepath == "file.py"
        assert changes[0].status == "modified"

    def test_no_unstaged_changes_returns_empty(self, tmp_path):
        """Test empty list when no unstaged changes."""
        subprocess.run(["git", "init"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            check=True,
        )

        file1 = tmp_path / "file.py"
        file1.write_text("content")
        subprocess.run(["git", "add", "file.py"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=tmp_path,
            check=True,
        )

        git = GitContext(tmp_path)
        changes = git.get_unstaged_changes()

        assert len(changes) == 0


class TestFileChange:
    """Test FileChange dataclass."""

    def test_file_change_creation(self):
        """Test creating FileChange instance."""
        change = FileChange(
            filepath="path/to/file.py",
            status="modified",
            lines_added=10,
            lines_deleted=2,
        )

        assert change.filepath == "path/to/file.py"
        assert change.status == "modified"
        assert change.lines_added == 10
        assert change.lines_deleted == 2


class TestFileDiff:
    """Test FileDiff dataclass."""

    def test_file_diff_creation(self):
        """Test creating FileDiff instance."""
        diff = FileDiff(
            filepath="file.py",
            status="modified",
            old_content="old",
            new_content="new",
            diff_text="diff text",
        )

        assert diff.filepath == "file.py"
        assert diff.status == "modified"
        assert diff.old_content == "old"
        assert diff.new_content == "new"
