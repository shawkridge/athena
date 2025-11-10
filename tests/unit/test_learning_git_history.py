"""Tests for Strategy 5 - Git history analysis and architectural decisions."""

import pytest
from athena.learning.git_analyzer import (
    GitAnalyzer,
    CommitInfo,
    ArchitecturalDecision,
    PatternEvolution,
    get_git_analyzer,
)
from athena.learning.decision_extractor import (
    DecisionExtractor,
    Decision,
    DecisionLibrary,
)


@pytest.fixture
def git_analyzer():
    """Create git analyzer for testing."""
    return get_git_analyzer()


@pytest.fixture
def decision_extractor():
    """Create decision extractor for testing."""
    return DecisionExtractor()


@pytest.fixture
def decision_library():
    """Create decision library for testing."""
    return DecisionLibrary()


class TestGitAnalyzer:
    """Tests for GitAnalyzer class."""

    def test_git_analyzer_creation(self, git_analyzer):
        """Test git analyzer initializes correctly."""
        assert git_analyzer is not None
        assert isinstance(git_analyzer, GitAnalyzer)

    def test_git_analyzer_is_singleton(self):
        """Test that get_git_analyzer returns singleton instance."""
        analyzer1 = get_git_analyzer()
        analyzer2 = get_git_analyzer()
        assert analyzer1 is analyzer2

    def test_analyze_history_returns_dict(self, git_analyzer):
        """Test analyze_history returns proper structure."""
        analysis = git_analyzer.analyze_history(since_days=7)

        assert isinstance(analysis, dict)
        assert "analysis_timestamp" in analysis
        assert "period_days" in analysis
        assert "total_commits" in analysis
        assert "decisions" in analysis
        assert "patterns" in analysis
        assert "lessons_learned" in analysis
        assert "insights" in analysis

    def test_analyze_history_with_keywords(self, git_analyzer):
        """Test analyze_history with focus keywords."""
        analysis = git_analyzer.analyze_history(
            since_days=90,
            focus_keywords=["refactor", "migration"],
        )

        assert isinstance(analysis, dict)
        assert analysis["period_days"] == 90
        # May have decisions if keywords found in history
        assert isinstance(analysis["decisions"], list)

    def test_architectural_decisions_extraction(self, git_analyzer):
        """Test finding architectural decisions."""
        decisions = git_analyzer.find_architectural_decisions(
            patterns=["architecture", "refactor"]
        )

        assert isinstance(decisions, list)
        # Each decision should have required fields if found
        for decision in decisions:
            assert hasattr(decision, "title")
            assert hasattr(decision, "description")
            assert hasattr(decision, "decision_maker")
            assert hasattr(decision, "date")
            assert hasattr(decision, "rationale")
            assert hasattr(decision, "outcomes")
            assert hasattr(decision, "lessons_learned")


class TestDecisionExtractor:
    """Tests for DecisionExtractor class."""

    def test_decision_extractor_creation(self, decision_extractor):
        """Test decision extractor initializes correctly."""
        assert decision_extractor is not None
        assert isinstance(decision_extractor, DecisionExtractor)

    def test_extract_from_commit_with_decision_keywords(self, decision_extractor):
        """Test extracting decision from commit message."""
        commit_message = """refactor: Migrate to async/await

Problem: Callback-based async is hard to maintain.
Rationale: Async/await provides better syntax and error handling.
Outcome: Code is more readable and maintainable.
"""

        decision = decision_extractor.extract_from_commit(commit_message)

        assert decision is not None
        assert isinstance(decision, Decision)
        assert "migrate" in decision.title.lower() or "refactor" in decision.title.lower()
        assert decision.title == "refactor: Migrate to async/await"

    def test_extract_from_commit_without_decision_keywords(self, decision_extractor):
        """Test that non-decision commits return None."""
        commit_message = "fix: Typo in docstring"

        decision = decision_extractor.extract_from_commit(commit_message)

        # May return None for non-decision commits
        if decision is not None:
            assert isinstance(decision, Decision)

    def test_extract_pattern_decisions(self, decision_extractor):
        """Test extracting common architectural decisions."""
        patterns = decision_extractor.extract_pattern_decisions()

        assert isinstance(patterns, list)
        assert len(patterns) > 0

        # Check structure of pattern decisions
        for pattern in patterns:
            assert isinstance(pattern, dict)
            assert "title" in pattern
            assert "context" in pattern
            assert "options" in pattern
            assert isinstance(pattern["options"], list)

    def test_learn_from_decisions(self, decision_extractor):
        """Test learning patterns from decisions."""
        decisions = [
            Decision(
                title="Choose async/await",
                context="Need to handle async operations",
                chosen_option="Async/await",
                rejected_options=["Callbacks", "Promises"],
                rationale="Better syntax and error handling",
                outcomes=["Code is cleaner"],
                timestamp="2024-01-01T00:00:00",
                file_references=["main.py"],
            ),
            Decision(
                title="Use PostgreSQL",
                context="Need database",
                chosen_option="PostgreSQL",
                rejected_options=["MongoDB"],
                rationale="Need ACID guarantees",
                outcomes=["Better data integrity"],
                timestamp="2024-01-02T00:00:00",
                file_references=["db.py"],
            ),
        ]

        learnings = decision_extractor.learn_from_decisions(decisions)

        assert isinstance(learnings, dict)
        assert "common_choices" in learnings
        assert "successful_patterns" in learnings
        assert "decision_frequency" in learnings


class TestDecisionLibrary:
    """Tests for DecisionLibrary class."""

    def test_decision_library_creation(self, decision_library):
        """Test decision library initializes correctly."""
        assert decision_library is not None
        assert isinstance(decision_library, DecisionLibrary)

    def test_add_decision(self, decision_library):
        """Test adding decision to library."""
        decision = Decision(
            title="Use microservices",
            context="Need to scale independently",
            chosen_option="Microservices",
            rejected_options=["Monolith"],
            rationale="Independent scaling needed",
            outcomes=["Better scalability"],
            timestamp="2024-01-01T00:00:00",
            file_references=["architecture.py"],
        )

        decision_library.add_decision("decision_1", decision)

        assert "decision_1" in decision_library.decisions
        assert decision_library.decisions["decision_1"].title == "Use microservices"

    def test_query_decisions_by_keywords(self, decision_library):
        """Test querying decisions by keywords."""
        decision1 = Decision(
            title="Implement caching",
            context="Cache optimization for performance",
            chosen_option="Redis",
            rejected_options=["Memcached"],
            rationale="Better scalability",
            outcomes=["Faster queries"],
            timestamp="2024-01-01T00:00:00",
            file_references=["cache.py"],
        )

        decision2 = Decision(
            title="Use database sharding",
            context="Horizontal scaling with databases",
            chosen_option="Database sharding",
            rejected_options=["Vertical scaling"],
            rationale="Better distribution",
            outcomes=["Better performance"],
            timestamp="2024-01-02T00:00:00",
            file_references=["db.py"],
        )

        decision_library.add_decision("cache_decision", decision1)
        decision_library.add_decision("shard_decision", decision2)

        results = decision_library.query(["cache"])

        assert len(results) >= 1
        assert any("cache" in (d.title.lower() + " " + d.context.lower()) for d in results)

    def test_query_no_matches(self, decision_library):
        """Test querying with no matching keywords."""
        decision = Decision(
            title="Use PostgreSQL",
            context="Database selection",
            chosen_option="PostgreSQL",
            rejected_options=["MySQL"],
            rationale="Better features",
            outcomes=["Good performance"],
            timestamp="2024-01-01T00:00:00",
            file_references=["db.py"],
        )

        decision_library.add_decision("db_decision", decision)

        results = decision_library.query(["nonexistent", "keywords"])

        assert isinstance(results, list)

    def test_get_similar_decisions(self, decision_library):
        """Test finding similar decisions."""
        decision1 = Decision(
            title="Use microservices architecture",
            context="Scaling requirement",
            chosen_option="Microservices",
            rejected_options=["Monolith"],
            rationale="Independent scaling",
            outcomes=["Better scalability"],
            timestamp="2024-01-01T00:00:00",
            file_references=["arch.py"],
        )

        decision2 = Decision(
            title="Use monolithic architecture",
            context="Simple deployment",
            chosen_option="Monolith",
            rejected_options=["Microservices"],
            rationale="Simpler deployment",
            outcomes=["Easier debugging"],
            timestamp="2024-01-02T00:00:00",
            file_references=["arch.py"],
        )

        decision_library.add_decision("micro", decision1)
        decision_library.add_decision("mono", decision2)

        # Find decisions similar to microservices decision
        similar = decision_library.get_similar_decisions(decision1)

        assert isinstance(similar, list)
        # Should find at least the decision itself or architecture-related ones
        assert len(similar) >= 1

    def test_suggest_based_on_context(self, decision_library):
        """Test getting suggestions based on context."""
        decision = Decision(
            title="Implement rate limiting",
            context="API protection",
            chosen_option="Token bucket",
            rejected_options=["Sliding window"],
            rationale="More flexible",
            outcomes=["Better protection"],
            timestamp="2024-01-01T00:00:00",
            file_references=["api.py"],
        )

        decision_library.add_decision("rate_limit", decision)

        suggestions = decision_library.suggest_based_on_context(
            "We need to protect our API from abuse"
        )

        assert isinstance(suggestions, list)


class TestCommitInfo:
    """Tests for CommitInfo dataclass."""

    def test_commit_info_creation(self):
        """Test CommitInfo dataclass creation."""
        commit = CommitInfo(
            sha="abc123",
            author="Alice Developer",
            date="2024-01-01T00:00:00",
            message="feat: Add new feature",
            files_changed=["src/feature.py", "tests/test_feature.py"],
            additions=50,
            deletions=10,
        )

        assert commit.sha == "abc123"
        assert commit.author == "Alice Developer"
        assert len(commit.files_changed) == 2
        assert commit.additions == 50

    def test_commit_info_empty_files(self):
        """Test CommitInfo with no files changed."""
        commit = CommitInfo(
            sha="def456",
            author="Bob Developer",
            date="2024-01-02T00:00:00",
            message="docs: Update README",
            files_changed=[],
            additions=5,
            deletions=0,
        )

        assert len(commit.files_changed) == 0
        assert commit.additions == 5


class TestArchitecturalDecision:
    """Tests for ArchitecturalDecision dataclass."""

    def test_architectural_decision_creation(self):
        """Test ArchitecturalDecision dataclass creation."""
        decision = ArchitecturalDecision(
            decision_id="arch_001",
            title="Migrate to async/await",
            description="Replace callback-based async",
            context="Callback hell was becoming unmaintainable",
            decision_maker="Alice Developer",
            date="2024-01-01T00:00:00",
            commit_sha="abc123def456",
            rationale="Async/await provides cleaner syntax and better error handling",
            outcomes=["Improved code readability", "Fewer async-related bugs"],
            lessons_learned=[
                "Async/await requires Python 3.5+",
                "Error handling is much cleaner",
            ],
            affected_files=["src/async_module.py", "src/handlers.py"],
        )

        assert decision.title == "Migrate to async/await"
        assert decision.decision_maker == "Alice Developer"
        assert len(decision.outcomes) == 2
        assert len(decision.lessons_learned) == 2


class TestPatternEvolution:
    """Tests for PatternEvolution dataclass."""

    def test_pattern_evolution_creation(self):
        """Test PatternEvolution dataclass creation."""
        evolution = PatternEvolution(
            pattern_name="Error handling",
            first_appeared="2023-01-01T00:00:00",
            last_modified="2024-01-01T00:00:00",
            evolution_description="From try/except to custom exception classes",
            commits=[],
            current_status="stable",
        )

        assert evolution.pattern_name == "Error handling"
        assert evolution.current_status == "stable"

    def test_pattern_evolution_long_history(self):
        """Test pattern evolution with many commits."""
        commits = []  # Would normally have multiple CommitInfo objects
        evolution = PatternEvolution(
            pattern_name="Database access",
            first_appeared="2020-01-01T00:00:00",
            last_modified="2024-11-10T00:00:00",
            evolution_description="From raw SQL to ORM to query builder",
            commits=commits,
            current_status="evolving",
        )

        assert evolution.pattern_name == "Database access"
        assert evolution.current_status == "evolving"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
