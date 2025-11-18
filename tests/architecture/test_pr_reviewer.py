"""Tests for PR reviewer."""

from pathlib import Path

import pytest

from athena.architecture.pr_reviewer import (
    PRReview,
    PRReviewer,
    ReviewAction,
    ReviewComment,
)
from athena.architecture.fitness import Severity


@pytest.fixture
def sample_review():
    """Create a sample PR review."""
    return PRReview(
        pr_number=123,
        action=ReviewAction.COMMENT,
        summary="Found 2 issues",
        fitness_passed=5,
        fitness_failed=2,
        fitness_violations=3,
    )


def test_review_comment_github_format():
    """Test converting review comment to GitHub format."""
    comment = ReviewComment(
        file_path="src/api/users.py",
        line_number=15,
        body="This violates the repository pattern",
        severity=Severity.ERROR,
    )

    github_format = comment.to_github_format()

    assert github_format["path"] == "src/api/users.py"
    assert github_format["line"] == 15
    assert github_format["body"] == "This violates the repository pattern"


def test_review_comment_without_line_number():
    """Test review comment without line number."""
    comment = ReviewComment(
        file_path="docs/ADR-012.md",
        line_number=None,
        body="ADR impact analysis",
        severity=Severity.INFO,
    )

    github_format = comment.to_github_format()

    assert github_format["path"] == "docs/ADR-012.md"
    assert "line" not in github_format or github_format.get("line") is None


def test_pr_review_to_github_format(sample_review):
    """Test converting PR review to GitHub format."""
    sample_review.comments = [
        ReviewComment(
            file_path="test.py",
            line_number=10,
            body="Test comment",
            severity=Severity.WARNING,
        )
    ]

    github_review = sample_review.to_github_review()

    assert "event" in github_review
    assert "body" in github_review
    assert "comments" in github_review
    assert github_review["event"] == "COMMENT"
    assert len(github_review["comments"]) == 1


def test_review_with_adr_changes(sample_review):
    """Test review with ADR changes detected."""
    sample_review.adr_changes_detected = [12, 15]
    sample_review.high_risk_changes = ["ADR-12: HIGH risk"]

    github_review = sample_review.to_github_review()
    body = github_review["body"]

    assert "ADR Changes Detected" in body
    assert "ADR-12" in body
    assert "ADR-15" in body
    assert "High-Risk Changes" in body


def test_review_action_determination():
    """Test different review actions."""
    # Approve
    review_approve = PRReview(
        pr_number=1, action=ReviewAction.APPROVE, summary="All good"
    )
    assert review_approve.action == ReviewAction.APPROVE

    # Comment
    review_comment = PRReview(
        pr_number=2, action=ReviewAction.COMMENT, summary="Some warnings"
    )
    assert review_comment.action == ReviewAction.COMMENT

    # Request changes
    review_block = PRReview(
        pr_number=3, action=ReviewAction.REQUEST_CHANGES, summary="Critical issues"
    )
    assert review_block.action == ReviewAction.REQUEST_CHANGES


@pytest.mark.skip(reason="Requires database connection")
def test_pr_reviewer_initialization():
    """Test PR reviewer initialization."""
    from athena.core.database import get_database

    db = get_database()
    reviewer = PRReviewer(db, Path.cwd())

    assert reviewer.db is not None
    assert reviewer.fitness_checker is not None
    assert reviewer.impact_analyzer is not None


def test_detect_adr_changes():
    """Test ADR change detection."""
    reviewer = PRReviewer(None, Path.cwd())

    # Test various ADR file patterns
    changed_files = [
        "docs/adr/001-use-postgres.md",
        "docs/ADR-012-auth-strategy.md",
        "architecture/decisions/015.md",
        "src/api/users.py",  # Not an ADR
    ]

    adr_ids = reviewer._detect_adr_changes(changed_files)

    assert 1 in adr_ids
    assert 12 in adr_ids
    assert 15 in adr_ids
    assert len(adr_ids) == 3


def test_detect_constraint_changes():
    """Test constraint change detection."""
    reviewer = PRReviewer(None, Path.cwd())

    changed_files = [
        "src/architecture/constraints.py",
        "tests/architecture/test_fitness_functions.py",
        "src/api/users.py",  # Not a constraint file
    ]

    constraint_files = reviewer._detect_constraint_changes(changed_files)

    assert "src/architecture/constraints.py" in constraint_files
    assert "tests/architecture/test_fitness_functions.py" in constraint_files
    assert len(constraint_files) == 2


def test_check_risk_patterns():
    """Test risk pattern detection."""
    reviewer = PRReviewer(None, Path.cwd())

    review = PRReview(pr_number=1, action=ReviewAction.APPROVE, summary="")

    # Test with risk keywords in PR description
    reviewer._check_risk_patterns(
        changed_files=["src/api/users.py"],
        pr_description="Breaking change: rewrite authentication",
        review=review,
    )

    assert len(review.high_risk_changes) > 0
    assert any("breaking" in change.lower() for change in review.high_risk_changes)


def test_check_risk_patterns_core_files():
    """Test risk detection for core file changes."""
    reviewer = PRReviewer(None, Path.cwd())

    review = PRReview(pr_number=1, action=ReviewAction.APPROVE, summary="")

    # Test with core files
    reviewer._check_risk_patterns(
        changed_files=["src/core/database.py", "src/config.py"],
        pr_description="Update database connection",
        review=review,
    )

    assert len(review.high_risk_changes) >= 2  # Both core files flagged


def test_review_summary_generation():
    """Test summary generation for different outcomes."""
    reviewer = PRReviewer(None, Path.cwd())

    # Approve
    review_approve = PRReview(pr_number=1, action=ReviewAction.APPROVE, summary="")
    reviewer._generate_summary(review_approve)
    assert "passed" in review_approve.summary.lower()

    # Comment
    review_comment = PRReview(pr_number=2, action=ReviewAction.COMMENT, summary="")
    review_comment.comments = [
        ReviewComment("test.py", 1, "test", Severity.WARNING) for _ in range(3)
    ]
    reviewer._generate_summary(review_comment)
    assert "3" in review_comment.summary
    assert "recommendation" in review_comment.summary.lower()

    # Request changes
    review_block = PRReview(
        pr_number=3, action=ReviewAction.REQUEST_CHANGES, summary=""
    )
    review_block.fitness_failed = 2
    reviewer._generate_summary(review_block)
    assert "critical" in review_block.summary.lower()
    assert "2" in review_block.summary


def test_empty_review():
    """Test review with no issues."""
    review = PRReview(
        pr_number=1,
        action=ReviewAction.APPROVE,
        summary="All checks passed",
        fitness_passed=10,
        fitness_failed=0,
        fitness_violations=0,
    )

    github_review = review.to_github_review()
    assert github_review["event"] == "APPROVE"
    assert len(review.comments) == 0


def test_review_with_blast_radius_warnings():
    """Test review with blast radius warnings."""
    review = PRReview(
        pr_number=1,
        action=ReviewAction.COMMENT,
        summary="High blast radius",
        blast_radius_warnings=["ADR-12 affects 45% of system"],
    )

    github_review = review.to_github_review()
    body = github_review["body"]

    assert "Blast Radius" in body
    assert "45%" in body


def test_multiple_severity_comments():
    """Test review with mixed severity comments."""
    review = PRReview(pr_number=1, action=ReviewAction.COMMENT, summary="Mixed issues")

    review.comments = [
        ReviewComment("file1.py", 10, "Error", Severity.ERROR),
        ReviewComment("file2.py", 20, "Warning", Severity.WARNING),
        ReviewComment("file3.py", 30, "Info", Severity.INFO),
    ]

    github_review = review.to_github_review()

    assert len(github_review["comments"]) == 3


@pytest.mark.skip(reason="Requires GitHub token")
def test_post_github_review():
    """Test posting review to GitHub (integration test)."""
    import os

    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        pytest.skip("GITHUB_TOKEN not set")

    # This would require actual GitHub API call
    # Skip in unit tests
    pass


def test_review_action_enum():
    """Test ReviewAction enum values."""
    assert ReviewAction.APPROVE.value == "approve"
    assert ReviewAction.COMMENT.value == "comment"
    assert ReviewAction.REQUEST_CHANGES.value == "request_changes"


def test_review_comment_severity_mapping():
    """Test that severity is preserved in comments."""
    comment_error = ReviewComment("test.py", 1, "Error", Severity.ERROR)
    comment_warning = ReviewComment("test.py", 2, "Warning", Severity.WARNING)
    comment_info = ReviewComment("test.py", 3, "Info", Severity.INFO)

    assert comment_error.severity == Severity.ERROR
    assert comment_warning.severity == Severity.WARNING
    assert comment_info.severity == Severity.INFO
