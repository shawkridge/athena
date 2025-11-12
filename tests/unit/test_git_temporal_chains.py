"""Unit tests for git-aware temporal chains.

Tests the complete git integration including:
- Git commit storage and retrieval
- Regression analysis and tracking
- Author metrics collection
- Temporal linking between commits

NOTE: Requires PostgreSQL backend.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

# Skip all tests if PostgreSQL not available
pytest.importorskip("psycopg")

from athena.core.database import Database
from athena.temporal.git_store import GitStore
from athena.temporal.git_retrieval import GitTemporalRetrieval
from athena.temporal.git_models import (
    GitMetadata,
    GitCommitEvent,
    GitFileChange,
    GitChangeType,
    RegressionAnalysis,
    RegressionType,
    AuthorMetrics,
    GitTemporalRelation,
    BranchMetrics,
)


@pytest.fixture
def db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test.db"
    return Database(str(db_path))


@pytest.fixture
def git_store(db):
    """Create git store with schema."""
    return GitStore(db)


@pytest.fixture
def git_retrieval(db):
    """Create git retrieval interface."""
    return GitTemporalRetrieval(db)


class TestGitModels:
    """Test git model validation."""

    def test_git_metadata_creation(self):
        """Test creating git metadata."""
        metadata = GitMetadata(
            commit_hash="abc123def456",
            commit_message="Fix authentication bug",
            author="Alice Developer",
            author_email="alice@example.com",
            branch="main",
            files_changed=3,
            insertions=50,
            deletions=20,
        )

        assert metadata.commit_hash == "abc123def456"
        assert metadata.author == "Alice Developer"
        assert metadata.files_changed == 3

    def test_git_metadata_validation(self):
        """Test git metadata validation."""
        with pytest.raises(ValueError):
            GitMetadata(
                commit_hash="",  # Invalid empty hash
                commit_message="Test",
                author="Test",
            )

        with pytest.raises(ValueError):
            GitMetadata(
                commit_hash="abc123",
                commit_message="Test",
                author="Test",
                files_changed=-1,  # Invalid negative
            )

    def test_git_file_change_creation(self):
        """Test creating file changes."""
        change = GitFileChange(
            file_path="src/auth.py",
            change_type=GitChangeType.MODIFIED,
            insertions=10,
            deletions=5,
        )

        assert change.file_path == "src/auth.py"
        assert change.change_type == GitChangeType.MODIFIED

    def test_regression_analysis_creation(self):
        """Test creating regression analysis."""
        regression = RegressionAnalysis(
            regression_type=RegressionType.BUG_INTRODUCTION,
            regression_description="Login timeout issues",
            introducing_commit="abc123",
            discovered_commit="def456",
            impact_estimate=0.8,
            confidence=0.9,
        )

        assert regression.regression_type == RegressionType.BUG_INTRODUCTION
        assert regression.impact_estimate == 0.8


class TestGitStore:
    """Test git store operations."""

    def test_create_commit(self, git_store):
        """Test storing a commit."""
        metadata = GitMetadata(
            commit_hash="abc123def456",
            commit_message="Fix auth bug",
            author="Alice",
            branch="main",
            files_changed=2,
            insertions=30,
            deletions=10,
        )

        commit_id = git_store.create_commit(metadata)
        assert commit_id > 0

    def test_get_commit(self, git_store):
        """Test retrieving a commit."""
        metadata = GitMetadata(
            commit_hash="abc123def456",
            commit_message="Fix auth bug",
            author="Alice",
            branch="main",
        )

        git_store.create_commit(metadata)
        commit = git_store.get_commit("abc123def456")

        assert commit is not None
        assert commit["author"] == "Alice"
        assert commit["commit_message"] == "Fix auth bug"

    def test_add_file_changes(self, git_store):
        """Test adding file changes to commit."""
        metadata = GitMetadata(
            commit_hash="abc123",
            commit_message="Test",
            author="Test",
            branch="main",
        )

        commit_id = git_store.create_commit(metadata)

        # Add multiple file changes
        change1 = GitFileChange(
            file_path="src/auth.py",
            change_type=GitChangeType.MODIFIED,
            insertions=20,
            deletions=5,
        )

        change2 = GitFileChange(
            file_path="src/jwt.py",
            change_type=GitChangeType.ADDED,
            insertions=100,
            deletions=0,
        )

        file_id1 = git_store.add_file_change(commit_id, change1)
        file_id2 = git_store.add_file_change(commit_id, change2)

        assert file_id1 > 0
        assert file_id2 > 0

    def test_create_commit_event(self, git_store):
        """Test creating full commit event with file changes."""
        metadata = GitMetadata(
            commit_hash="abc123",
            commit_message="Test commit",
            author="Alice",
            branch="main",
        )

        file_change = GitFileChange(
            file_path="src/main.py",
            change_type=GitChangeType.MODIFIED,
            insertions=50,
            deletions=20,
        )

        event = GitCommitEvent(
            git_metadata=metadata,
            file_changes=[file_change],
        )

        commit_id, file_ids = git_store.create_commit_event(event)
        assert commit_id > 0
        assert len(file_ids) == 1

    def test_get_commits_by_author(self, git_store):
        """Test querying commits by author."""
        # Create commits from different authors
        for i, author in enumerate(["Alice", "Bob", "Alice"]):
            metadata = GitMetadata(
                commit_hash=f"hash{i}",
                commit_message=f"Commit {i}",
                author=author,
                branch="main",
            )
            git_store.create_commit(metadata)

        commits = git_store.get_commits_by_author("Alice", limit=10)
        assert len(commits) == 2

    def test_get_commits_by_file(self, git_store):
        """Test querying commits that touched a file."""
        # Create commits with file changes
        for i in range(3):
            metadata = GitMetadata(
                commit_hash=f"hash{i}",
                commit_message=f"Commit {i}",
                author="Alice",
                branch="main",
            )

            commit_id = git_store.create_commit(metadata)

            # First commit touches file1
            # Second touches file2
            # Third touches file1 again
            file_path = "file1.py" if i != 1 else "file2.py"

            change = GitFileChange(
                file_path=file_path,
                change_type=GitChangeType.MODIFIED,
            )
            git_store.add_file_change(commit_id, change)

        commits = git_store.get_commits_by_file("file1.py")
        assert len(commits) == 2

    def test_record_regression(self, git_store):
        """Test recording regression analysis."""
        regression = RegressionAnalysis(
            regression_type=RegressionType.BUG_INTRODUCTION,
            regression_description="Login timeout",
            introducing_commit="bad_commit",
            discovered_commit="found_commit",
            impact_estimate=0.8,
            confidence=0.9,
        )

        regression_id = git_store.record_regression(regression)
        assert regression_id > 0

    def test_get_regressions_by_commit(self, git_store):
        """Test retrieving regressions by introducing commit."""
        # Record multiple regressions
        for i in range(3):
            regression = RegressionAnalysis(
                regression_type=RegressionType.BUG_INTRODUCTION,
                regression_description=f"Bug {i}",
                introducing_commit="bad_commit",
                discovered_commit=f"found_{i}",
            )
            git_store.record_regression(regression)

        regressions = git_store.get_regressions_by_commit("bad_commit")
        assert len(regressions) == 3

    def test_update_author_metrics(self, git_store):
        """Test updating author metrics."""
        metrics = AuthorMetrics(
            author="Alice",
            email="alice@example.com",
            commits_count=42,
            insertions_total=1000,
            deletions_total=200,
            regressions_introduced=2,
            regressions_fixed=1,
        )

        metrics_id = git_store.update_author_metrics(metrics)
        assert metrics_id > 0

    def test_get_author_metrics(self, git_store):
        """Test retrieving author metrics."""
        metrics = AuthorMetrics(
            author="Alice",
            commits_count=50,
            regressions_introduced=5,
        )

        git_store.update_author_metrics(metrics)
        retrieved = git_store.get_author_metrics("Alice")

        assert retrieved is not None
        assert retrieved["author"] == "Alice"
        assert retrieved["commits_count"] == 50

    def test_create_temporal_relation(self, git_store):
        """Test creating temporal relation between commits."""
        relation = GitTemporalRelation(
            from_commit="commit1",
            to_commit="commit2",
            relation_type="introduces_regression",
            strength=0.95,
            distance_commits=5,
            file_overlap=0.3,
        )

        relation_id = git_store.create_temporal_relation(relation)
        assert relation_id > 0

    def test_get_temporal_relations(self, git_store):
        """Test retrieving temporal relations from a commit."""
        # Create multiple relations
        for i in range(3):
            relation = GitTemporalRelation(
                from_commit="source",
                to_commit=f"target{i}",
                relation_type="introduces_regression",
                strength=0.9,
            )
            git_store.create_temporal_relation(relation)

        relations = git_store.get_temporal_relations_from("source")
        assert len(relations) == 3

    def test_update_branch_metrics(self, git_store):
        """Test updating branch metrics."""
        metrics = BranchMetrics(
            branch_name="feature/auth",
            is_main=False,
            commits_ahead_of_main=5,
            commits_behind_main=2,
        )

        metrics_id = git_store.update_branch_metrics(metrics)
        assert metrics_id > 0

    def test_get_branch_metrics(self, git_store):
        """Test retrieving branch metrics."""
        metrics = BranchMetrics(
            branch_name="feature/auth",
            commits_ahead_of_main=10,
        )

        git_store.update_branch_metrics(metrics)
        retrieved = git_store.get_branch_metrics("feature/auth")

        assert retrieved is not None
        assert retrieved["commits_ahead_of_main"] == 10


class TestGitRetrieval:
    """Test git retrieval and analysis."""

    def _setup_regression_scenario(self, git_retrieval):
        """Helper to set up a regression scenario."""
        git_store = git_retrieval.store

        # Create introducing commit
        intro_metadata = GitMetadata(
            commit_hash="intro_commit",
            commit_message="Add new feature",
            author="Alice",
            branch="main",
            insertions=100,
            deletions=10,
        )
        git_store.create_commit(intro_metadata)

        # Create discovering commit (later)
        discovered_metadata = GitMetadata(
            commit_hash="discovered_commit",
            commit_message="Found the bug",
            author="Bob",
            branch="main",
            insertions=20,
            deletions=0,
        )
        git_store.create_commit(discovered_metadata)

        # Record regression
        regression = RegressionAnalysis(
            regression_type=RegressionType.BUG_INTRODUCTION,
            regression_description="Feature is broken",
            introducing_commit="intro_commit",
            discovered_commit="discovered_commit",
            impact_estimate=0.8,
            confidence=0.9,
        )
        git_store.record_regression(regression)

        return git_retrieval

    def test_when_was_introduced(self, git_retrieval):
        """Test when_was_introduced query."""
        git_retrieval = self._setup_regression_scenario(git_retrieval)

        result = git_retrieval.when_was_introduced("intro_commit")
        assert result is not None
        assert result["author"] == "Alice"

    def test_who_introduced_regression(self, git_retrieval):
        """Test who_introduced_regression query."""
        git_retrieval = self._setup_regression_scenario(git_retrieval)

        result = git_retrieval.who_introduced_regression("intro_commit")
        assert result is not None
        assert result["author"] == "Alice"

    def test_trace_regression_timeline(self, git_retrieval):
        """Test regression timeline tracing."""
        git_retrieval = self._setup_regression_scenario(git_retrieval)

        result = git_retrieval.trace_regression_timeline("intro_commit")
        assert result["regressions_found"] > 0
        assert len(result["timeline"]) > 0

    def test_get_regression_statistics(self, git_retrieval):
        """Test regression statistics."""
        git_retrieval = self._setup_regression_scenario(git_retrieval)

        stats = git_retrieval.get_regression_statistics()
        assert stats["total_regressions"] > 0

    def test_find_high_risk_commits(self, git_retrieval):
        """Test finding high-risk commits."""
        git_retrieval = self._setup_regression_scenario(git_retrieval)

        high_risk = git_retrieval.find_high_risk_commits(limit=10)
        # Should find at least the intro commit
        assert len(high_risk) > 0

    def test_analyze_author_risk(self, git_retrieval):
        """Test author risk analysis."""
        git_retrieval = self._setup_regression_scenario(git_retrieval)

        result = git_retrieval.analyze_author_risk("Alice")
        assert result["author"] == "Alice"
        assert result["total_commits"] > 0


class TestGitIntegration:
    """Integration tests for git temporal chains."""

    def test_complete_workflow(self, git_store, git_retrieval):
        """Test complete git workflow."""
        # Step 1: Create commits
        metadata1 = GitMetadata(
            commit_hash="abc123",
            commit_message="Add feature",
            author="Alice",
            branch="main",
            insertions=100,
            deletions=0,
        )
        commit1_id = git_store.create_commit(metadata1)

        # Step 2: Add file changes
        change = GitFileChange(
            file_path="src/feature.py",
            change_type=GitChangeType.ADDED,
            insertions=100,
        )
        git_store.add_file_change(commit1_id, change)

        # Step 3: Later discover regression
        metadata2 = GitMetadata(
            commit_hash="def456",
            commit_message="Report bug",
            author="Bob",
            branch="main",
        )
        git_store.create_commit(metadata2)

        # Step 4: Record regression
        regression = RegressionAnalysis(
            regression_type=RegressionType.FEATURE_BREAKAGE,
            regression_description="Feature broken",
            introducing_commit="abc123",
            discovered_commit="def456",
            affected_files=["src/feature.py"],
        )
        git_store.record_regression(regression)

        # Step 5: Query results
        when = git_retrieval.when_was_introduced("abc123")
        assert when is not None

        who = git_retrieval.who_introduced_regression("abc123")
        assert who["author"] == "Alice"

        file_history = git_retrieval.get_file_history("src/feature.py")
        assert file_history["file_path"] == "src/feature.py"
        assert len(file_history["related_regressions"]) > 0
