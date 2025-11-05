"""Integration tests for git-aware temporal chains with episodic events.

Tests the complete flow from code changes → git commits → episodic events → temporal chains.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

from athena.core.database import Database
from athena.episodic.store import EpisodicStore
from athena.episodic.models import (
    EpisodicEvent,
    EventType,
    EventOutcome,
    EventContext,
    CodeEventType,
)
from athena.temporal.git_store import GitStore
from athena.temporal.git_retrieval import GitTemporalRetrieval
from athena.temporal.git_models import (
    GitMetadata,
    GitCommitEvent,
    GitFileChange,
    GitChangeType,
    RegressionAnalysis,
    RegressionType,
)
from athena.spatial.store import SpatialStore


@pytest.fixture
def db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test.db"
    return Database(str(db_path))


@pytest.fixture
def episodic_store(db):
    """Create episodic store."""
    return EpisodicStore(db)


@pytest.fixture
def git_store(db):
    """Create git store."""
    return GitStore(db)


@pytest.fixture
def git_retrieval(db):
    """Create git retrieval."""
    return GitTemporalRetrieval(db)


@pytest.fixture
def spatial_store(db):
    """Create spatial store."""
    return SpatialStore(db)


class TestCodeEventToGitFlow:
    """Test flow from code events to git commits."""

    def test_code_edit_creates_episodic_event(self, episodic_store):
        """Test that code edits create episodic events."""
        event = EpisodicEvent(
            project_id=1,
            session_id="test-session",
            event_type=EventType.FILE_CHANGE,
            content="Modified src/auth.py - added login timeout check",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(
                files=["src/auth.py"],
                task="Fix authentication timeout",
                phase="Implementation",
            ),
            files_changed=1,
            lines_added=15,
            lines_deleted=5,
        )

        event_id = episodic_store.create(event)
        retrieved = episodic_store.get(event_id)

        assert retrieved is not None
        assert retrieved.event_type == EventType.FILE_CHANGE
        assert "auth.py" in retrieved.content

    def test_code_event_links_to_git_commit(self, episodic_store, git_store):
        """Test linking episodic code event to git commit."""
        # Step 1: Create episodic event for code change
        episode = EpisodicEvent(
            project_id=1,
            session_id="test-session",
            event_type=EventType.FILE_CHANGE,
            content="Implemented login timeout",
            context=EventContext(files=["src/auth.py"]),
            lines_added=20,
            lines_deleted=5,
        )
        episode_id = episodic_store.create(episode)

        # Step 2: Create corresponding git commit (linked to episode)
        metadata = GitMetadata(
            commit_hash="abc123def456",
            commit_message="Implement login timeout",
            author="Alice",
            branch="main",
            files_changed=1,
            insertions=20,
            deletions=5,
        )

        commit_id = git_store.create_commit(metadata, event_id=episode_id)

        # Step 3: Verify linkage
        commit = git_store.get_commit("abc123def456")
        assert commit["event_id"] == episode_id

    def test_refactoring_event_to_symbol_changes(self, episodic_store, spatial_store):
        """Test refactoring events affecting code symbols."""
        # Create refactoring event
        event = EpisodicEvent(
            project_id=1,
            session_id="test-session",
            event_type=EventType.REFACTORING,
            content="Extract authenticate method from AuthHandler",
            context=EventContext(files=["src/auth.py"]),
            lines_added=50,
            lines_deleted=30,
        )

        event_id = episodic_store.create(event)

        # The refactoring would affect multiple symbols
        # This would be captured in spatial hierarchy
        retrieved = episodic_store.get(event_id)
        assert retrieved.event_type == EventType.REFACTORING


class TestRegressionDetectionFlow:
    """Test regression detection and tracking flow."""

    def test_test_failure_creates_regression_analysis(
        self, episodic_store, git_store, git_retrieval
    ):
        """Test detecting regression from test failure."""
        # Step 1: Create initial good commit
        good_metadata = GitMetadata(
            commit_hash="good_commit",
            commit_message="Initial feature",
            author="Alice",
            branch="main",
            insertions=100,
        )
        git_store.create_commit(good_metadata)

        # Step 2: Create suspicious commit
        bad_metadata = GitMetadata(
            commit_hash="bad_commit",
            commit_message="Optimize performance",
            author="Bob",
            branch="main",
            insertions=50,
            deletions=30,
        )
        git_store.create_commit(bad_metadata)

        # Step 3: Create test failure event
        test_event = EpisodicEvent(
            project_id=1,
            session_id="test-session",
            event_type=EventType.TEST_RUN,
            content="Test suite failure: LoginTest::test_timeout_handling",
            outcome=EventOutcome.FAILURE,
            context=EventContext(files=["tests/test_auth.py"]),
        )
        test_event_id = episodic_store.create(test_event)

        # Step 4: Analyze and record regression
        regression = RegressionAnalysis(
            regression_type=RegressionType.TEST_FAILURE,
            regression_description="Login timeout test now fails",
            introducing_commit="bad_commit",
            discovered_commit="bad_commit",  # Found immediately
            discovered_event_id=test_event_id,
            affected_files=["src/auth.py"],
            impact_estimate=0.7,
            confidence=0.8,
        )

        regression_id = git_store.record_regression(regression)

        # Step 5: Query regression timeline
        timeline = git_retrieval.trace_regression_timeline("bad_commit")
        assert timeline["regressions_found"] > 0

    def test_performance_degradation_detection(
        self, episodic_store, git_store, git_retrieval
    ):
        """Test detecting performance regressions."""
        # Create performance profile event
        profile_event = EpisodicEvent(
            project_id=1,
            session_id="perf-test",
            event_type=EventType.ACTION,
            content="Performance regression: login now takes 500ms (was 50ms)",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(task="Performance monitoring"),
            duration_ms=500,
        )

        profile_event_id = episodic_store.create(profile_event)

        # Record commit that caused degradation
        metadata = GitMetadata(
            commit_hash="perf_commit",
            commit_message="Add extra validation layers",
            author="Carol",
            branch="main",
            insertions=200,
        )
        git_store.create_commit(metadata)

        # Record regression
        regression = RegressionAnalysis(
            regression_type=RegressionType.PERFORMANCE_DEGRADATION,
            regression_description="Login performance degraded 10x",
            introducing_commit="perf_commit",
            discovered_commit="perf_commit",
            discovered_event_id=profile_event_id,
            impact_estimate=0.95,  # High impact
            confidence=0.85,
        )

        git_store.record_regression(regression)

        # Verify high-risk detection
        high_risk = git_retrieval.find_high_risk_commits(limit=10)
        commit_hashes = [c["commit_hash"] for c in high_risk]
        assert "perf_commit" in commit_hashes


class TestAuthorMetricsTracking:
    """Test tracking author metrics and patterns."""

    def test_author_regression_pattern_detection(self, git_store, git_retrieval):
        """Test detecting regression patterns by author."""
        # Create multiple commits by Alice
        for i in range(5):
            metadata = GitMetadata(
                commit_hash=f"alice_commit_{i}",
                commit_message=f"Feature {i}",
                author="Alice",
                branch="main",
            )
            git_store.create_commit(metadata)

        # Create 2 regressions from Alice's commits
        for i in range(2):
            regression = RegressionAnalysis(
                regression_type=RegressionType.BUG_INTRODUCTION,
                regression_description=f"Bug from commit {i}",
                introducing_commit=f"alice_commit_{i}",
                discovered_commit="test_commit",
            )
            git_store.record_regression(regression)

        # Analyze Alice's risk
        risk = git_retrieval.analyze_author_risk("Alice")

        assert risk["author"] == "Alice"
        assert risk["total_commits"] == 5
        assert risk["regressions_introduced"] == 2
        assert risk["regression_rate"] == 0.4  # 2 out of 5

    def test_author_specialization_tracking(self, git_store):
        """Test tracking author specialization."""
        # Create commits touching different files
        files_touched = {
            "auth": 10,  # 10 commits to auth
            "api": 3,    # 3 commits to api
            "ui": 1,     # 1 commit to ui
        }

        metrics_data = {
            "commits_count": sum(files_touched.values()),
            "files_changed_total": len(files_touched),
            "insertions_total": 500,
            "deletions_total": 100,
            "most_frequent_file_patterns": ["src/auth*"],
            "specialization": "authentication",
        }

        from athena.temporal.git_models import AuthorMetrics

        metrics = AuthorMetrics(
            author="Dan",
            **metrics_data,
        )

        git_store.update_author_metrics(metrics)
        retrieved = git_store.get_author_metrics("Dan")

        assert retrieved["specialization"] == "authentication"
        assert len(retrieved["most_frequent_file_patterns"]) > 0


class TestTemporalChainIntegration:
    """Test temporal chain integration with git events."""

    def test_temporal_linking_across_commits(self, git_store, git_retrieval):
        """Test creating temporal links between commits."""
        # Create commit sequence
        timestamps = []
        for i in range(3):
            metadata = GitMetadata(
                commit_hash=f"commit_{i}",
                commit_message=f"Step {i}",
                author="Alice",
                branch="main",
                committed_timestamp=datetime.now() + timedelta(hours=i),
            )
            git_store.create_commit(metadata)
            timestamps.append(metadata.committed_timestamp)

        # Create temporal relations
        from athena.temporal.git_models import GitTemporalRelation

        relation = GitTemporalRelation(
            from_commit="commit_0",
            to_commit="commit_1",
            relation_type="precedes",
            strength=0.95,
            distance_commits=0,
            time_delta_seconds=3600,
        )

        git_store.create_temporal_relation(relation)

        # Verify relation
        relations = git_store.get_temporal_relations_from("commit_0")
        assert len(relations) > 0
        assert relations[0]["to_commit"] == "commit_1"

    def test_bugfix_chain_reconstruction(self, episodic_store, git_store, git_retrieval):
        """Test reconstructing complete bug-fix chain."""
        # Timeline: bug introduced → discovered → fixed

        # 1. Introduce bug
        intro_event = EpisodicEvent(
            project_id=1,
            session_id="session1",
            event_type=EventType.FILE_CHANGE,
            content="Added new feature",
            context=EventContext(files=["src/feature.py"]),
            lines_added=100,
        )
        intro_event_id = episodic_store.create(intro_event)

        intro_metadata = GitMetadata(
            commit_hash="intro_commit",
            commit_message="Add feature X",
            author="Alice",
            branch="main",
            committed_timestamp=datetime.now(),
        )
        git_store.create_commit(intro_metadata, event_id=intro_event_id)

        # 2. Discover bug
        discover_event = EpisodicEvent(
            project_id=1,
            session_id="session2",
            event_type=EventType.ERROR,
            content="Feature X crashes on edge case",
            outcome=EventOutcome.FAILURE,
            context=EventContext(files=["src/feature.py"]),
        )
        discover_event_id = episodic_store.create(discover_event)

        # 3. Record regression
        regression = RegressionAnalysis(
            regression_type=RegressionType.FEATURE_BREAKAGE,
            regression_description="Feature X crashes",
            introducing_commit="intro_commit",
            discovered_commit="intro_commit",
            discovered_event_id=discover_event_id,
            affected_files=["src/feature.py"],
            impact_estimate=0.9,
        )
        git_store.record_regression(regression)

        # 4. Fix bug
        fix_event = EpisodicEvent(
            project_id=1,
            session_id="session3",
            event_type=EventType.FILE_CHANGE,
            content="Fixed edge case in feature X",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(files=["src/feature.py"]),
            lines_added=20,
            lines_deleted=5,
        )
        episodic_store.create(fix_event)

        fix_metadata = GitMetadata(
            commit_hash="fix_commit",
            commit_message="Fix feature X edge case",
            author="Bob",
            branch="main",
        )
        git_store.create_commit(fix_metadata)

        # Update regression with fix
        regressions = git_store.get_regressions_by_commit("intro_commit")
        assert len(regressions) > 0

        # 5. Query complete timeline
        timeline = git_retrieval.trace_regression_timeline("intro_commit")
        assert timeline["regressions_found"] > 0

        # Timeline should show: intro -> discover -> (fix)
        assert timeline["timeline"][0]["introduced"] is not None


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_multi_author_regression_investigation(
        self, episodic_store, git_store, git_retrieval
    ):
        """Test investigating regression across multiple authors."""
        # Setup: Multiple authors, one introduces bug, another fixes it

        # Create Alice's commits
        for i in range(3):
            meta = GitMetadata(
                commit_hash=f"alice_{i}",
                commit_message=f"Alice work {i}",
                author="Alice",
                branch="main",
            )
            git_store.create_commit(meta)

        # Create Bob's commits
        for i in range(3):
            meta = GitMetadata(
                commit_hash=f"bob_{i}",
                commit_message=f"Bob work {i}",
                author="Bob",
                branch="main",
            )
            git_store.create_commit(meta)

        # Record regression from Alice
        regression = RegressionAnalysis(
            regression_type=RegressionType.BUG_INTRODUCTION,
            regression_description="Null pointer exception",
            introducing_commit="alice_1",
            discovered_commit="alice_2",
            impact_estimate=0.8,
        )
        git_store.record_regression(regression)

        # Analyze both authors
        alice_risk = git_retrieval.analyze_author_risk("Alice")
        bob_risk = git_retrieval.analyze_author_risk("Bob")

        assert alice_risk["regressions_introduced"] > 0
        assert bob_risk["regressions_introduced"] == 0

    def test_file_regression_tracking(self, git_store, git_retrieval):
        """Test tracking regressions by file."""
        # Create multiple commits touching same file
        critical_file = "src/core.py"

        for i in range(5):
            meta = GitMetadata(
                commit_hash=f"commit_{i}",
                commit_message=f"Change {i}",
                author="Dev",
                branch="main",
            )

            commit_id = git_store.create_commit(meta)

            # Add file change
            change = GitFileChange(
                file_path=critical_file,
                change_type=GitChangeType.MODIFIED,
                insertions=10 * (i + 1),
            )
            git_store.add_file_change(commit_id, change)

        # Record regressions for some commits
        for i in [1, 3]:
            regression = RegressionAnalysis(
                regression_type=RegressionType.BUG_INTRODUCTION,
                regression_description=f"Bug in change {i}",
                introducing_commit=f"commit_{i}",
                discovered_commit=f"commit_{i + 1}",
                affected_files=[critical_file],
            )
            git_store.record_regression(regression)

        # Query file history
        history = git_retrieval.get_file_history(critical_file)

        assert history["file_path"] == critical_file
        assert history["total_commits"] == 5
        assert len(history["related_regressions"]) > 0
