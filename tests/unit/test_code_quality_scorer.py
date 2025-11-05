"""Unit tests for Code Quality Scorer.

Tests comprehensive code quality assessment including:
- Quality scoring synthesis
- Component scoring
- Health checks
- Improvement recommendations
- Quality reporting
"""

import pytest
from athena.symbols.code_quality_scorer import (
    CodeQualityScorer,
    QualityRating,
    QualityMetric,
    ComponentScore,
)
from athena.symbols.symbol_models import Symbol, SymbolType, SymbolMetrics


@pytest.fixture
def scorer():
    """Create a fresh scorer instance."""
    return CodeQualityScorer()


@pytest.fixture
def clean_symbol():
    """Create a clean symbol with no issues."""
    return Symbol(
        name="clean_function",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=10,
        namespace="test",
        full_qualified_name="test.clean_function",
        signature="def clean_function():",
        code="return x + 1",
        docstring="Clean function.",
        metrics=SymbolMetrics(),
        language="python",
    )


@pytest.fixture
def problematic_symbol():
    """Create a symbol with multiple issues."""
    return Symbol(
        name="problematic_function",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=100,
        namespace="test",
        full_qualified_name="test.problematic_function",
        signature="def problematic_function():",
        code="",
        docstring="",
        metrics=SymbolMetrics(),
        language="python",
    )


# ============================================================================
# Initialization Tests
# ============================================================================


def test_scorer_initialization(scorer):
    """Test scorer initializes empty."""
    assert scorer.scores == []


# ============================================================================
# Quality Scoring Tests
# ============================================================================


def test_score_clean_symbol(scorer, clean_symbol):
    """Test scoring clean symbol."""
    score = scorer.score_symbol(
        clean_symbol,
        security_issues=0,
        performance_issues=0,
        code_smells=0,
        maintainability_score=90.0,
        testability_score=85.0,
        has_docstring=True
    )
    assert score is not None
    assert score.overall_score >= 80  # Should be excellent
    assert score.overall_rating == QualityRating.EXCELLENT


def test_score_problematic_symbol(scorer, problematic_symbol):
    """Test scoring problematic symbol."""
    score = scorer.score_symbol(
        problematic_symbol,
        security_issues=2,
        performance_issues=2,
        code_smells=4,
        maintainability_score=30.0,
        testability_score=35.0,
        has_docstring=False
    )
    assert score is not None
    assert score.overall_score < 50  # Should be critical or poor
    assert score.overall_rating in [QualityRating.POOR, QualityRating.CRITICAL]


def test_score_with_security_issues(scorer, clean_symbol):
    """Test quality score affected by security issues."""
    score_secure = scorer.score_symbol(clean_symbol, security_issues=0)
    scorer.scores = []
    score_insecure = scorer.score_symbol(clean_symbol, security_issues=2)

    assert score_secure.overall_score > score_insecure.overall_score


def test_score_with_performance_issues(scorer, clean_symbol):
    """Test quality score affected by performance issues."""
    score_fast = scorer.score_symbol(clean_symbol, performance_issues=0)
    scorer.scores = []
    score_slow = scorer.score_symbol(clean_symbol, performance_issues=3)

    assert score_fast.overall_score > score_slow.overall_score


def test_score_with_code_smells(scorer, clean_symbol):
    """Test quality score affected by code smells."""
    score_clean = scorer.score_symbol(clean_symbol, code_smells=0)
    scorer.scores = []
    score_smelly = scorer.score_symbol(clean_symbol, code_smells=5)

    assert score_clean.overall_score > score_smelly.overall_score


def test_score_with_low_maintainability(scorer, clean_symbol):
    """Test quality score affected by maintainability."""
    score_good = scorer.score_symbol(clean_symbol, maintainability_score=85.0)
    scorer.scores = []
    score_bad = scorer.score_symbol(clean_symbol, maintainability_score=25.0)

    assert score_good.overall_score > score_bad.overall_score


def test_score_with_low_testability(scorer, clean_symbol):
    """Test quality score affected by testability."""
    score_testable = scorer.score_symbol(clean_symbol, testability_score=80.0)
    scorer.scores = []
    score_untestable = scorer.score_symbol(clean_symbol, testability_score=20.0)

    assert score_testable.overall_score > score_untestable.overall_score


def test_score_without_documentation(scorer, clean_symbol):
    """Test quality score affected by documentation."""
    score_documented = scorer.score_symbol(clean_symbol, has_docstring=True)
    scorer.scores = []
    score_undocumented = scorer.score_symbol(clean_symbol, has_docstring=False)

    assert score_documented.overall_score > score_undocumented.overall_score


# ============================================================================
# Rating Tests
# ============================================================================


def test_excellent_rating(scorer, clean_symbol):
    """Test excellent quality rating."""
    score = scorer.score_symbol(
        clean_symbol,
        security_issues=0,
        performance_issues=0,
        code_smells=0,
        maintainability_score=90.0,
        testability_score=90.0,
        has_docstring=True
    )
    assert score.overall_rating == QualityRating.EXCELLENT


def test_good_rating(scorer, clean_symbol):
    """Test good quality rating."""
    score = scorer.score_symbol(
        clean_symbol,
        security_issues=0,
        performance_issues=0,
        code_smells=1,
        maintainability_score=75.0,
        testability_score=75.0,
        has_docstring=True
    )
    assert score.overall_rating in [QualityRating.GOOD, QualityRating.EXCELLENT]


def test_fair_rating(scorer, clean_symbol):
    """Test fair quality rating."""
    score = scorer.score_symbol(
        clean_symbol,
        security_issues=1,
        performance_issues=1,
        code_smells=2,
        maintainability_score=60.0,
        testability_score=60.0,
        has_docstring=True
    )
    assert score.overall_rating in [QualityRating.FAIR, QualityRating.GOOD]


def test_poor_rating(scorer, clean_symbol):
    """Test poor quality rating."""
    score = scorer.score_symbol(
        clean_symbol,
        security_issues=2,
        performance_issues=2,
        code_smells=4,
        maintainability_score=45.0,
        testability_score=45.0,
        has_docstring=False
    )
    assert score.overall_rating in [QualityRating.POOR, QualityRating.FAIR]


def test_critical_rating(scorer, problematic_symbol):
    """Test critical quality rating."""
    score = scorer.score_symbol(
        problematic_symbol,
        security_issues=5,
        performance_issues=4,
        code_smells=8,
        maintainability_score=15.0,
        testability_score=15.0,
        has_docstring=False
    )
    assert score.overall_rating == QualityRating.CRITICAL


# ============================================================================
# Component Score Tests
# ============================================================================


def test_has_component_scores(scorer, clean_symbol):
    """Test that score includes component scores."""
    score = scorer.score_symbol(clean_symbol)
    assert len(score.component_scores) > 0
    assert all(isinstance(cs, ComponentScore) for cs in score.component_scores)


def test_component_count(scorer, clean_symbol):
    """Test correct number of components."""
    score = scorer.score_symbol(clean_symbol)
    # Should have 6 components: security, performance, quality, documentation, maintainability, testability
    assert len(score.component_scores) >= 6


def test_component_has_weight(scorer, clean_symbol):
    """Test component scores have weights."""
    score = scorer.score_symbol(clean_symbol)
    for component in score.component_scores:
        assert component.weight > 0
        assert component.weight <= 1.0


def test_component_weights_sum_to_one(scorer, clean_symbol):
    """Test that component weights sum to approximately 1.0."""
    score = scorer.score_symbol(clean_symbol)
    total_weight = sum(cs.weight for cs in score.component_scores)
    assert abs(total_weight - 1.0) < 0.01  # Allow small floating point error


# ============================================================================
# Issues Count Tests
# ============================================================================


def test_issue_counting(scorer, clean_symbol):
    """Test issue counting."""
    score = scorer.score_symbol(
        clean_symbol,
        security_issues=2,
        performance_issues=1,
        code_smells=3,
        has_docstring=False
    )
    assert score.total_issues >= 6  # 2 + 1 + 3 + missing doc
    assert score.critical_issues >= 0


def test_critical_issues_counting(scorer, clean_symbol):
    """Test critical issues are counted."""
    score = scorer.score_symbol(
        clean_symbol,
        security_issues=3,  # Should increase critical count
        performance_issues=2,
        code_smells=5
    )
    assert score.critical_issues > 0


# ============================================================================
# Health Check Tests
# ============================================================================


def test_has_health_checks(scorer, clean_symbol):
    """Test that score includes health checks."""
    score = scorer.score_symbol(clean_symbol)
    assert len(score.health_checks) > 0


def test_security_health_check(scorer, clean_symbol):
    """Test security health check."""
    score = scorer.score_symbol(clean_symbol, security_issues=0)
    security_checks = [h for h in score.health_checks if h.check_name == "Security"]
    assert len(security_checks) > 0
    assert security_checks[0].passed == True


def test_documentation_health_check(scorer, clean_symbol):
    """Test documentation health check."""
    score = scorer.score_symbol(clean_symbol, has_docstring=False)
    doc_checks = [h for h in score.health_checks if h.check_name == "Documentation"]
    assert len(doc_checks) > 0
    assert doc_checks[0].passed == False


def test_health_check_has_recommendation(scorer, clean_symbol):
    """Test health checks include recommendations."""
    score = scorer.score_symbol(clean_symbol, security_issues=2)
    for check in score.health_checks:
        assert len(check.recommendation) > 0


# ============================================================================
# Improvement Recommendation Tests
# ============================================================================


def test_has_improvement_recommendations(scorer, clean_symbol):
    """Test that score includes improvement recommendations."""
    score = scorer.score_symbol(clean_symbol, security_issues=1)
    assert len(score.improvements) > 0


def test_improvement_recommendations_ordered(scorer, problematic_symbol):
    """Test improvements are prioritized."""
    score = scorer.score_symbol(
        problematic_symbol,
        security_issues=2,
        performance_issues=2,
        code_smells=4,
        maintainability_score=30.0,
        testability_score=30.0,
        has_docstring=False
    )
    priorities = [imp.priority for imp in score.improvements]
    assert priorities == sorted(priorities)


def test_improvement_has_effort(scorer, clean_symbol):
    """Test improvements include effort estimates."""
    score = scorer.score_symbol(clean_symbol, security_issues=1)
    for imp in score.improvements:
        assert len(imp.estimated_effort) > 0


def test_improvement_has_impact(scorer, clean_symbol):
    """Test improvements include impact estimates."""
    score = scorer.score_symbol(clean_symbol, security_issues=1)
    for imp in score.improvements:
        assert len(imp.expected_impact) > 0


# ============================================================================
# Strengths and Weaknesses Tests
# ============================================================================


def test_identifies_strengths(scorer, clean_symbol):
    """Test identification of strengths."""
    score = scorer.score_symbol(
        clean_symbol,
        security_issues=0,
        maintainability_score=90.0,
        testability_score=90.0
    )
    assert len(score.strengths) > 0


def test_identifies_weaknesses(scorer, clean_symbol):
    """Test identification of weaknesses."""
    score = scorer.score_symbol(
        clean_symbol,
        security_issues=2,
        maintainability_score=25.0,
        testability_score=25.0
    )
    assert len(score.weaknesses) > 0


# ============================================================================
# Multiple Symbol Tests
# ============================================================================


def test_score_all(scorer, clean_symbol, problematic_symbol):
    """Test scoring multiple symbols."""
    scores = scorer.score_all([
        (clean_symbol, 0, 0, 0, 85.0, 85.0, True),
        (problematic_symbol, 3, 3, 5, 30.0, 30.0, False),
    ])
    assert len(scores) == 2
    assert scores[0].overall_score > scores[1].overall_score


# ============================================================================
# Report Generation Tests
# ============================================================================


def test_report_no_assessment(scorer):
    """Test report with no assessment."""
    report = scorer.get_quality_report()
    assert report["status"] == "no_assessment"


def test_report_with_assessment(scorer, clean_symbol):
    """Test report generation."""
    scorer.score_symbol(clean_symbol)
    report = scorer.get_quality_report()

    assert report["status"] == "assessed"
    assert report["total_symbols"] == 1
    assert "average_quality_score" in report
    assert "average_quality_rating" in report
    assert "total_issues" in report
    assert "critical_issues" in report


def test_report_includes_highest_quality(scorer, clean_symbol, problematic_symbol):
    """Test report includes highest quality symbols."""
    scorer.score_all([
        (clean_symbol, 0, 0, 0, 85.0, 85.0, True),
        (problematic_symbol, 3, 3, 5, 30.0, 30.0, False),
    ])
    report = scorer.get_quality_report()

    assert len(report["highest_quality"]) > 0
    assert report["highest_quality"][0]["symbol"] == "clean_function"


def test_report_includes_lowest_quality(scorer, clean_symbol, problematic_symbol):
    """Test report includes lowest quality symbols."""
    scorer.score_all([
        (clean_symbol, 0, 0, 0, 85.0, 85.0, True),
        (problematic_symbol, 3, 3, 5, 30.0, 30.0, False),
    ])
    report = scorer.get_quality_report()

    assert len(report["lowest_quality"]) > 0
    assert report["lowest_quality"][0]["symbol"] == "problematic_function"


def test_report_includes_improvements(scorer, clean_symbol):
    """Test report includes improvement recommendations."""
    scorer.score_symbol(clean_symbol, security_issues=1)
    report = scorer.get_quality_report()

    assert "top_improvements" in report
    assert len(report["top_improvements"]) > 0


def test_report_includes_quality_breakdown(scorer, clean_symbol, problematic_symbol):
    """Test report includes quality rating breakdown."""
    scorer.score_all([
        (clean_symbol, 0, 0, 0, 85.0, 85.0, True),
        (problematic_symbol, 3, 3, 5, 30.0, 30.0, False),
    ])
    report = scorer.get_quality_report()

    assert "quality_breakdown" in report
    assert isinstance(report["quality_breakdown"], dict)


# ============================================================================
# Weighted Score Tests
# ============================================================================


def test_weighted_score_calculation(scorer, clean_symbol):
    """Test that overall score is weighted average of components."""
    score = scorer.score_symbol(clean_symbol, security_issues=1)

    # Calculate expected score from components
    expected = sum(cs.score * cs.weight for cs in score.component_scores)
    assert abs(score.overall_score - expected) < 0.1  # Allow small floating point error


# ============================================================================
# Edge Cases
# ============================================================================


def test_score_with_all_zeros(scorer, clean_symbol):
    """Test scoring with all metrics at zero."""
    score = scorer.score_symbol(
        clean_symbol,
        security_issues=0,
        performance_issues=0,
        code_smells=0,
        maintainability_score=0.0,
        testability_score=0.0,
        has_docstring=False
    )
    # With zero maintainability and testability, should be critical or poor
    assert score.overall_rating in [QualityRating.CRITICAL, QualityRating.POOR, QualityRating.FAIR]


def test_score_with_perfect_metrics(scorer, clean_symbol):
    """Test scoring with perfect metrics."""
    score = scorer.score_symbol(
        clean_symbol,
        security_issues=0,
        performance_issues=0,
        code_smells=0,
        maintainability_score=100.0,
        testability_score=100.0,
        has_docstring=True
    )
    assert score.overall_rating == QualityRating.EXCELLENT


def test_score_with_mixed_metrics(scorer, clean_symbol):
    """Test scoring with mixed quality metrics."""
    score = scorer.score_symbol(
        clean_symbol,
        security_issues=1,
        performance_issues=0,
        code_smells=2,
        maintainability_score=65.0,
        testability_score=70.0,
        has_docstring=True
    )
    # Should be somewhere in the middle
    assert 40 < score.overall_score < 80
    assert score.overall_rating in [QualityRating.FAIR, QualityRating.GOOD]


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_workflow(scorer):
    """Test complete quality assessment workflow."""
    symbols = [
        Symbol(
            name="func1",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=1,
            line_end=20,
            namespace="",
            full_qualified_name="func1",
            signature="def func1():",
            code="",
            docstring="Test",
            metrics=SymbolMetrics(),
        ),
        Symbol(
            name="func2",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=50,
            line_end=150,
            namespace="",
            full_qualified_name="func2",
            signature="def func2():",
            code="",
            docstring="",
            metrics=SymbolMetrics(),
        ),
    ]

    # Score all
    scores = scorer.score_all([
        (symbols[0], 0, 0, 0, 85.0, 85.0, True),
        (symbols[1], 2, 2, 4, 35.0, 40.0, False),
    ])
    assert len(scores) == 2
    assert scores[0].overall_score > scores[1].overall_score

    # Generate report
    report = scorer.get_quality_report()
    assert report["status"] == "assessed"
    assert len(report["highest_quality"]) > 0
    assert len(report["lowest_quality"]) > 0
    assert len(report["top_improvements"]) > 0
    assert "quality_breakdown" in report
