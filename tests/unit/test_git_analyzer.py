"""Unit tests for git_analyzer module."""

import subprocess
import tempfile
from pathlib import Path

import pytest

from athena.code.git_analyzer import GitAwareAnalyzer, create_git_aware_analyzer


class TestGitAwareAnalyzerInitialization:
    """Test GitAwareAnalyzer initialization."""

    def test_init_with_valid_git_repo(self, tmp_path):
        """Test initializing with a valid git repository."""
        subprocess.run(["git", "init"], cwd=tmp_path, check=True)

        analyzer = GitAwareAnalyzer(tmp_path)
        assert analyzer.repo_path == tmp_path
        assert analyzer.git is not None
        assert analyzer.parser is not None

    def test_init_with_invalid_path_raises_error(self, tmp_path):
        """Test that initialization fails with non-git directory."""
        with pytest.raises(ValueError, match="is not a git repository"):
            GitAwareAnalyzer(tmp_path)

    def test_factory_function(self, tmp_path):
        """Test the factory function creates analyzer."""
        subprocess.run(["git", "init"], cwd=tmp_path, check=True)

        analyzer = create_git_aware_analyzer(tmp_path)
        assert isinstance(analyzer, GitAwareAnalyzer)


class TestAnalyzeChanges:
    """Test analyze_changes method."""

    @pytest.fixture
    def git_repo_with_python_changes(self, tmp_path):
        """Create a git repo with Python file changes."""
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
        file1 = tmp_path / "module1.py"
        file1.write_text("def hello():\n    print('hello')\n")
        subprocess.run(["git", "add", "module1.py"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=tmp_path,
            check=True,
        )

        # Modify the file
        file1.write_text(
            "def hello():\n    print('hello world')\n\ndef goodbye():\n    print('bye')\n"
        )
        subprocess.run(["git", "add", "module1.py"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add goodbye"],
            cwd=tmp_path,
            check=True,
        )

        return tmp_path

    def test_analyze_changes_returns_dict(self, git_repo_with_python_changes):
        """Test that analyze_changes returns a dict."""
        analyzer = GitAwareAnalyzer(git_repo_with_python_changes)
        result = analyzer.analyze_changes(since="HEAD~1")

        assert isinstance(result, dict)

    def test_analyze_changes_includes_changed_file(self, git_repo_with_python_changes):
        """Test that changed files are included in results."""
        analyzer = GitAwareAnalyzer(git_repo_with_python_changes)
        result = analyzer.analyze_changes(since="HEAD~1")

        assert "module1.py" in result
        assert len(result["module1.py"]) > 0


class TestGetPrioritizedContext:
    """Test get_prioritized_context method."""

    @pytest.fixture
    def git_repo_with_multiple_changes(self, tmp_path):
        """Create a git repo with multiple changed files."""
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

        # Create and commit initial files
        for i in range(3):
            file = tmp_path / f"file{i}.py"
            file.write_text(f"# File {i}\n")
            subprocess.run(["git", "add", f"file{i}.py"], cwd=tmp_path, check=True)

        subprocess.run(
            ["git", "commit", "-m", "Initial files"],
            cwd=tmp_path,
            check=True,
        )

        # Modify files with different impact
        (tmp_path / "file0.py").write_text("# File 0\n" + "x = 1\n" * 50)  # 50 lines
        (tmp_path / "file1.py").write_text("# File 1\n" + "x = 1\n" * 5)   # 5 lines
        (tmp_path / "file2.py").write_text("# File 2\n")                    # 1 line

        for i in range(3):
            subprocess.run(["git", "add", f"file{i}.py"], cwd=tmp_path, check=True)

        subprocess.run(
            ["git", "commit", "-m", "Modify files"],
            cwd=tmp_path,
            check=True,
        )

        return tmp_path

    def test_get_prioritized_context_returns_list(
        self, git_repo_with_multiple_changes
    ):
        """Test that get_prioritized_context returns a list."""
        analyzer = GitAwareAnalyzer(git_repo_with_multiple_changes)
        result = analyzer.get_prioritized_context(since="HEAD~1")

        assert isinstance(result, list)
        assert len(result) > 0

    def test_prioritized_context_includes_changed_files(
        self, git_repo_with_multiple_changes
    ):
        """Test that all changed files are included."""
        analyzer = GitAwareAnalyzer(git_repo_with_multiple_changes)
        result = analyzer.get_prioritized_context(since="HEAD~1")

        assert "file0.py" in result
        assert "file1.py" in result
        assert "file2.py" in result

    def test_prioritized_context_ordered_by_impact(
        self, git_repo_with_multiple_changes
    ):
        """Test that files are ordered by impact (lines changed)."""
        analyzer = GitAwareAnalyzer(git_repo_with_multiple_changes)
        result = analyzer.get_prioritized_context(since="HEAD~1", include_related=False)

        # file0.py and file1.py should be in the list
        assert "file0.py" in result
        assert "file1.py" in result
        # file0 has 50 additions, file1 has 5, so file0 should come first
        if len(result) >= 2:
            assert result.index("file0.py") < result.index("file1.py")


class TestGetDiffContext:
    """Test get_diff_context method."""

    @pytest.fixture
    def git_repo_with_diff(self, tmp_path):
        """Create a git repo with changes."""
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

        file1 = tmp_path / "code.py"
        file1.write_text("def hello():\n    pass\n")
        subprocess.run(["git", "add", "code.py"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=tmp_path,
            check=True,
        )

        file1.write_text("def hello():\n    print('hello')\n")
        subprocess.run(["git", "add", "code.py"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add print"],
            cwd=tmp_path,
            check=True,
        )

        return tmp_path

    def test_get_diff_context_returns_string(self, git_repo_with_diff):
        """Test that get_diff_context returns a string."""
        analyzer = GitAwareAnalyzer(git_repo_with_diff)
        result = analyzer.get_diff_context("code.py", since="HEAD~1")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_diff_context_includes_diff_text(self, git_repo_with_diff):
        """Test that diff context includes diff text."""
        analyzer = GitAwareAnalyzer(git_repo_with_diff)
        result = analyzer.get_diff_context("code.py", since="HEAD~1")

        assert "code.py" in result
        assert "Diff" in result

    def test_diff_context_returns_diff_for_added_file(self, git_repo_with_diff):
        """Test that newly added files return diff context."""
        analyzer = GitAwareAnalyzer(git_repo_with_diff)

        # Create a file and commit it - it will be in the diff for HEAD~1
        other_file = git_repo_with_diff / "other.py"
        other_file.write_text("other code")
        subprocess.run(["git", "add", "other.py"], cwd=git_repo_with_diff, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add other"],
            cwd=git_repo_with_diff,
            check=True,
        )

        # other.py will now be in the diff for HEAD~1
        result = analyzer.get_diff_context("other.py", since="HEAD~1")
        assert result is not None
        assert "other.py" in result


class TestGetChangeSummary:
    """Test get_change_summary method."""

    @pytest.fixture
    def git_repo_with_changes(self, tmp_path):
        """Create a git repo with various changes."""
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

        # Initial files
        (tmp_path / "file1.py").write_text("code")
        subprocess.run(["git", "add", "file1.py"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=tmp_path,
            check=True,
        )

        # Add new file
        (tmp_path / "file2.py").write_text("new file\n")
        # Modify existing
        (tmp_path / "file1.py").write_text("modified\nmore\n")

        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add and modify"],
            cwd=tmp_path,
            check=True,
        )

        return tmp_path

    def test_get_change_summary_returns_dict(self, git_repo_with_changes):
        """Test that get_change_summary returns a dict."""
        analyzer = GitAwareAnalyzer(git_repo_with_changes)
        result = analyzer.get_change_summary(since="HEAD~1")

        assert isinstance(result, dict)

    def test_change_summary_has_required_fields(self, git_repo_with_changes):
        """Test that summary includes required fields."""
        analyzer = GitAwareAnalyzer(git_repo_with_changes)
        result = analyzer.get_change_summary(since="HEAD~1")

        assert "total_files_changed" in result
        assert "added_files" in result
        assert "modified_files" in result
        assert "deleted_files" in result
        assert "total_lines_added" in result
        assert "total_lines_deleted" in result
        assert "files_by_impact" in result

    def test_change_summary_counts_correct(self, git_repo_with_changes):
        """Test that file counts are correct."""
        analyzer = GitAwareAnalyzer(git_repo_with_changes)
        result = analyzer.get_change_summary(since="HEAD~1")

        assert result["total_files_changed"] == 2
        assert result["added_files"] >= 1
        assert result["modified_files"] >= 1


class TestGetChangedElements:
    """Test get_changed_elements method."""

    @pytest.fixture
    def git_repo_with_code_changes(self, tmp_path):
        """Create a git repo with Python code changes."""
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

        file1 = tmp_path / "lib.py"
        file1.write_text("def func1():\n    pass\n")
        subprocess.run(["git", "add", "lib.py"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=tmp_path,
            check=True,
        )

        file1.write_text(
            "def func1():\n    pass\n\ndef func2():\n    return 42\n"
        )
        subprocess.run(["git", "add", "lib.py"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add func2"],
            cwd=tmp_path,
            check=True,
        )

        return tmp_path

    def test_get_changed_elements_returns_list(self, git_repo_with_code_changes):
        """Test that get_changed_elements returns a list."""
        analyzer = GitAwareAnalyzer(git_repo_with_code_changes)
        result = analyzer.get_changed_elements(since="HEAD~1")

        assert isinstance(result, list)

    def test_changed_elements_sorted_by_priority(self, git_repo_with_code_changes):
        """Test that elements are sorted by file priority."""
        analyzer = GitAwareAnalyzer(git_repo_with_code_changes)
        result = analyzer.get_changed_elements(since="HEAD~1")

        # All elements should come from lib.py
        for element in result:
            assert element.file_path.endswith("lib.py")


class TestGetCommitHistoryForChanges:
    """Test get_commit_history_for_changes method."""

    @pytest.fixture
    def git_repo_with_history(self, tmp_path):
        """Create a git repo with commit history."""
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

        for i in range(3):
            file1.write_text(f"version {i}\n")
            subprocess.run(["git", "add", "file.py"], cwd=tmp_path, check=True)
            subprocess.run(
                ["git", "commit", "-m", f"Version {i}"],
                cwd=tmp_path,
                check=True,
            )

        return tmp_path

    def test_get_commit_history_for_changes_returns_dict(self, git_repo_with_history):
        """Test that method returns a dict."""
        analyzer = GitAwareAnalyzer(git_repo_with_history)
        result = analyzer.get_commit_history_for_changes(since="HEAD~1")

        assert isinstance(result, dict)

    def test_commit_history_includes_changed_files(self, git_repo_with_history):
        """Test that changed files are in the result."""
        analyzer = GitAwareAnalyzer(git_repo_with_history)
        result = analyzer.get_commit_history_for_changes(since="HEAD~1")

        assert "file.py" in result


class TestGetFileImpactScore:
    """Test get_file_impact_score method."""

    @pytest.fixture
    def git_repo_for_scoring(self, tmp_path):
        """Create a git repo for impact scoring."""
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

        # Create initial files
        (tmp_path / "large.py").write_text("code\n")
        (tmp_path / "small.py").write_text("x\n")

        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=tmp_path,
            check=True,
        )

        # Modify files with different impact
        (tmp_path / "large.py").write_text("code\n" + "x = 1\n" * 50)
        (tmp_path / "small.py").write_text("x\n" + "y = 2\n")

        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Modify"],
            cwd=tmp_path,
            check=True,
        )

        return tmp_path

    def test_impact_score_returns_float(self, git_repo_for_scoring):
        """Test that impact score returns a float."""
        analyzer = GitAwareAnalyzer(git_repo_for_scoring)
        score = analyzer.get_file_impact_score("large.py", since="HEAD~1")

        assert isinstance(score, float)
        assert 0 <= score <= 1

    def test_impact_score_higher_for_larger_changes(self, git_repo_for_scoring):
        """Test that larger changes have higher scores."""
        analyzer = GitAwareAnalyzer(git_repo_for_scoring)

        large_score = analyzer.get_file_impact_score("large.py", since="HEAD~1")
        small_score = analyzer.get_file_impact_score("small.py", since="HEAD~1")

        assert large_score > small_score

    def test_impact_score_nonzero_for_newly_added_file(self, git_repo_for_scoring):
        """Test that newly added files have nonzero impact score."""
        analyzer = GitAwareAnalyzer(git_repo_for_scoring)

        # Create a new file and commit it
        other_file = git_repo_for_scoring / "other.py"
        other_file.write_text("other")
        subprocess.run(["git", "add", "other.py"], cwd=git_repo_for_scoring, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add other"],
            cwd=git_repo_for_scoring,
            check=True,
        )

        # Newly added files should have some impact score
        score = analyzer.get_file_impact_score("other.py", since="HEAD~1")
        assert score > 0.0
