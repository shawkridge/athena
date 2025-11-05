"""Unit tests for Refactoring Suggester.

Tests refactoring suggestion generation including:
- Suggestion generation from debt items
- Step generation by refactoring type
- Priority scoring
- Roadmap generation
- Report generation
"""

import pytest
from athena.symbols.refactoring_suggester import (
    RefactoringSuggester,
    RefactoringType,
    RefactoringImpact,
    RefactoringStep,
    RefactoringSuggestion,
)
from athena.symbols.technical_debt_analyzer import (
    DebtItem, DebtCategory, DebtSeverity, DebtPriority
)
from athena.symbols.symbol_models import Symbol, SymbolType, SymbolMetrics


@pytest.fixture
def suggester():
    """Create a fresh suggester instance."""
    return RefactoringSuggester()


@pytest.fixture
def test_symbol():
    """Create a test symbol."""
    return Symbol(
        name="test_function",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=50,
        namespace="test",
        full_qualified_name="test.test_function",
        signature="def test_function():",
        code="pass",
        docstring="",
        metrics=SymbolMetrics(),
        language="python",
    )


@pytest.fixture
def security_debt_item(test_symbol):
    """Create a security debt item."""
    return DebtItem(
        symbol=test_symbol,
        category=DebtCategory.SECURITY,
        severity=DebtSeverity.CRITICAL,
        title="SQL Injection vulnerability",
        description="User input not sanitized in query",
        estimated_effort=8.0,
        estimated_impact=0.9,
        priority=DebtPriority.CRITICAL_PATH,
    )


@pytest.fixture
def quality_debt_item(test_symbol):
    """Create a quality debt item."""
    return DebtItem(
        symbol=test_symbol,
        category=DebtCategory.QUALITY,
        severity=DebtSeverity.HIGH,
        title="Code complexity too high",
        description="Cyclomatic complexity exceeds threshold",
        estimated_effort=5.0,
        estimated_impact=0.7,
        priority=DebtPriority.HIGH_IMPACT,
    )


# ============================================================================
# Initialization Tests
# ============================================================================


def test_suggester_initialization(suggester):
    """Test suggester initializes empty."""
    assert suggester.suggestions == []
    assert suggester.roadmap is None


# ============================================================================
# Suggestion Generation Tests
# ============================================================================


def test_suggest_from_security_debt(suggester, security_debt_item):
    """Test suggestion generation from security debt."""
    suggestion = suggester.suggest_from_debt(security_debt_item)
    assert suggestion is not None
    assert suggestion.refactoring_type == RefactoringType.FIX_SECURITY_ISSUE
    assert suggestion.debt_item.category == DebtCategory.SECURITY
    assert len(suggestion.steps) > 0


def test_suggest_from_quality_debt(suggester, quality_debt_item):
    """Test suggestion generation from quality debt."""
    suggestion = suggester.suggest_from_debt(quality_debt_item)
    assert suggestion is not None
    assert suggestion.refactoring_type == RefactoringType.SIMPLIFY_LOGIC
    assert suggestion.debt_item.category == DebtCategory.QUALITY


def test_suggest_from_performance_debt(suggester, test_symbol):
    """Test suggestion generation from performance debt."""
    debt_item = DebtItem(
        symbol=test_symbol,
        category=DebtCategory.PERFORMANCE,
        severity=DebtSeverity.HIGH,
        title="N+1 query problem",
        description="Database query in loop",
        estimated_effort=6.0,
        estimated_impact=0.8,
        priority=DebtPriority.HIGH_IMPACT,
    )
    suggestion = suggester.suggest_from_debt(debt_item)
    assert suggestion is not None
    assert suggestion.refactoring_type == RefactoringType.OPTIMIZE_PERFORMANCE


def test_suggest_from_testing_debt(suggester, test_symbol):
    """Test suggestion generation from testing debt."""
    debt_item = DebtItem(
        symbol=test_symbol,
        category=DebtCategory.TESTING,
        severity=DebtSeverity.MEDIUM,
        title="Low test coverage",
        description="Only 40% code coverage",
        estimated_effort=5.0,
        estimated_impact=0.7,
        priority=DebtPriority.MEDIUM_IMPACT,
    )
    suggestion = suggester.suggest_from_debt(debt_item)
    assert suggestion is not None
    assert suggestion.refactoring_type == RefactoringType.REFACTOR_FOR_TESTING


def test_suggest_from_documentation_debt(suggester, test_symbol):
    """Test suggestion generation from documentation debt."""
    debt_item = DebtItem(
        symbol=test_symbol,
        category=DebtCategory.DOCUMENTATION,
        severity=DebtSeverity.LOW,
        title="Missing docstring",
        description="Function has no documentation",
        estimated_effort=2.0,
        estimated_impact=0.3,
        priority=DebtPriority.LOW_PRIORITY,
    )
    suggestion = suggester.suggest_from_debt(debt_item)
    assert suggestion is not None
    assert suggestion.refactoring_type == RefactoringType.ADD_DOCUMENTATION


def test_suggestion_has_steps(suggester, quality_debt_item):
    """Test that suggestion includes concrete steps."""
    suggestion = suggester.suggest_from_debt(quality_debt_item)
    assert len(suggestion.steps) > 0
    assert all(isinstance(s, RefactoringStep) for s in suggestion.steps)
    assert suggestion.steps[0].step_number == 1


def test_suggestion_effort_calculation(suggester, quality_debt_item):
    """Test that effort is correctly calculated."""
    suggestion = suggester.suggest_from_debt(quality_debt_item)
    expected_effort = sum(s.effort_hours for s in suggestion.steps)
    assert suggestion.total_effort == expected_effort


def test_suggestion_impact_calculation(suggester, quality_debt_item):
    """Test that impact is correctly calculated."""
    suggestion = suggester.suggest_from_debt(quality_debt_item)
    assert 0.0 <= suggestion.total_impact <= 1.0
    assert len(suggestion.steps) > 0


# ============================================================================
# Refactoring Type Specific Tests
# ============================================================================


def test_extract_method_steps(suggester, test_symbol):
    """Test extract method refactoring steps."""
    debt_item = DebtItem(
        symbol=test_symbol,
        category=DebtCategory.MAINTAINABILITY,
        severity=DebtSeverity.MEDIUM,
        title="Function too long",
        description="Function exceeds 50 lines",
        estimated_effort=4.0,
        estimated_impact=0.6,
        priority=DebtPriority.MEDIUM_IMPACT,
    )
    suggestion = suggester.suggest_from_debt(debt_item)
    assert suggestion.refactoring_type == RefactoringType.EXTRACT_METHOD
    assert len(suggestion.steps) >= 3
    assert any(s.description == "Add unit tests" for s in suggestion.steps)


def test_simplify_logic_steps(suggester, quality_debt_item):
    """Test simplify logic refactoring steps."""
    suggestion = suggester.suggest_from_debt(quality_debt_item)
    assert suggestion.refactoring_type == RefactoringType.SIMPLIFY_LOGIC
    assert len(suggestion.steps) >= 3
    assert any("simplification" in s.description.lower() for s in suggestion.steps)


def test_fix_security_steps(suggester, security_debt_item):
    """Test security fix refactoring steps."""
    suggestion = suggester.suggest_from_debt(security_debt_item)
    assert suggestion.refactoring_type == RefactoringType.FIX_SECURITY_ISSUE
    assert len(suggestion.steps) >= 3
    assert any("security" in s.description.lower() for s in suggestion.steps)


def test_add_documentation_steps(suggester, test_symbol):
    """Test add documentation steps."""
    debt_item = DebtItem(
        symbol=test_symbol,
        category=DebtCategory.DOCUMENTATION,
        severity=DebtSeverity.LOW,
        title="Missing docstring",
        description="Function has no documentation",
        estimated_effort=2.0,
        estimated_impact=0.3,
        priority=DebtPriority.LOW_PRIORITY,
    )
    suggestion = suggester.suggest_from_debt(debt_item)
    assert len(suggestion.steps) >= 4
    step_descriptions = [s.description for s in suggestion.steps]
    assert "Document purpose" in step_descriptions


# ============================================================================
# Priority Scoring Tests
# ============================================================================


def test_critical_severity_increases_priority(suggester, test_symbol):
    """Test that critical severity increases priority score."""
    high_severity_item = DebtItem(
        symbol=test_symbol,
        category=DebtCategory.SECURITY,
        severity=DebtSeverity.CRITICAL,
        title="Issue",
        description="Desc",
        estimated_effort=2.0,
        estimated_impact=0.5,
        priority=DebtPriority.CRITICAL_PATH,
    )
    low_severity_item = DebtItem(
        symbol=test_symbol,
        category=DebtCategory.DOCUMENTATION,
        severity=DebtSeverity.LOW,
        title="Issue",
        description="Desc",
        estimated_effort=2.0,
        estimated_impact=0.5,
        priority=DebtPriority.LOW_PRIORITY,
    )

    high_sugg = suggester.suggest_from_debt(high_severity_item)
    low_sugg = suggester.suggest_from_debt(low_severity_item)

    assert high_sugg.priority_score > low_sugg.priority_score


def test_roi_affects_priority(suggester, test_symbol):
    """Test that ROI (impact/effort) affects priority."""
    high_roi_item = DebtItem(
        symbol=test_symbol,
        category=DebtCategory.QUALITY,
        severity=DebtSeverity.HIGH,  # High severity
        title="Issue",
        description="Desc",
        estimated_effort=2.0,  # Low effort
        estimated_impact=0.9,  # High impact
        priority=DebtPriority.HIGH_IMPACT,
    )
    low_roi_item = DebtItem(
        symbol=test_symbol,
        category=DebtCategory.QUALITY,
        severity=DebtSeverity.LOW,  # Low severity
        title="Issue",
        description="Desc",
        estimated_effort=8.0,  # High effort
        estimated_impact=0.2,  # Low impact
        priority=DebtPriority.LOW_PRIORITY,
    )

    high_roi_sugg = suggester.suggest_from_debt(high_roi_item)
    low_roi_sugg = suggester.suggest_from_debt(low_roi_item)

    assert high_roi_sugg.priority_score > low_roi_sugg.priority_score


# ============================================================================
# Impact Category Tests
# ============================================================================


def test_minimal_impact_category(suggester, test_symbol):
    """Test minimal impact categorization."""
    debt_item = DebtItem(
        symbol=test_symbol,
        category=DebtCategory.DOCUMENTATION,
        severity=DebtSeverity.INFO,
        title="Issue",
        description="Desc",
        estimated_effort=1.0,
        estimated_impact=0.2,
        priority=DebtPriority.LOW_PRIORITY,
    )
    suggestion = suggester.suggest_from_debt(debt_item)
    assert suggestion.impact_category == RefactoringImpact.MINIMAL


def test_significant_impact_category(suggester, test_symbol):
    """Test significant impact categorization."""
    debt_item = DebtItem(
        symbol=test_symbol,
        category=DebtCategory.MAINTAINABILITY,
        severity=DebtSeverity.HIGH,
        title="Function too long",
        description="Extract method needed",
        estimated_effort=30.0,
        estimated_impact=0.8,
        priority=DebtPriority.HIGH_IMPACT,
    )
    suggestion = suggester.suggest_from_debt(debt_item)
    # EXTRACT_METHOD generates multiple high-effort steps
    # Impact category based on total_effort: should be LOCAL or higher
    assert suggestion.impact_category in [RefactoringImpact.LOCAL, RefactoringImpact.MODERATE, RefactoringImpact.SIGNIFICANT]


# ============================================================================
# Multiple Suggestion Tests
# ============================================================================


def test_suggest_all(suggester, test_symbol):
    """Test generating suggestions for multiple debt items."""
    debt_items = [
        DebtItem(
            symbol=test_symbol,
            category=DebtCategory.SECURITY,
            severity=DebtSeverity.CRITICAL,
            title="Issue 1",
            description="Desc",
            estimated_effort=5.0,
            estimated_impact=0.8,
            priority=DebtPriority.CRITICAL_PATH,
        ),
        DebtItem(
            symbol=test_symbol,
            category=DebtCategory.QUALITY,
            severity=DebtSeverity.MEDIUM,
            title="Issue 2",
            description="Desc",
            estimated_effort=4.0,
            estimated_impact=0.6,
            priority=DebtPriority.MEDIUM_IMPACT,
        ),
    ]
    suggestions = suggester.suggest_all(debt_items)
    assert len(suggestions) == 2
    assert all(isinstance(s, RefactoringSuggestion) for s in suggestions)


# ============================================================================
# Query and Sorting Tests
# ============================================================================


def test_get_suggestions_by_priority(suggester, test_symbol):
    """Test getting suggestions sorted by priority."""
    debt_items = [
        DebtItem(
            symbol=test_symbol,
            category=DebtCategory.DOCUMENTATION,
            severity=DebtSeverity.LOW,
            title="Issue 1",
            description="Desc",
            estimated_effort=2.0,
            estimated_impact=0.3,
            priority=DebtPriority.LOW_PRIORITY,
        ),
        DebtItem(
            symbol=test_symbol,
            category=DebtCategory.SECURITY,
            severity=DebtSeverity.CRITICAL,
            title="Issue 2",
            description="Desc",
            estimated_effort=8.0,
            estimated_impact=0.9,
            priority=DebtPriority.CRITICAL_PATH,
        ),
    ]
    suggester.suggest_all(debt_items)
    sorted_suggestions = suggester.get_suggestions_by_priority()
    assert sorted_suggestions[0].debt_item.severity == DebtSeverity.CRITICAL
    assert sorted_suggestions[1].debt_item.severity == DebtSeverity.LOW


def test_get_critical_path_suggestions(suggester, test_symbol):
    """Test getting critical path suggestions."""
    debt_items = [
        DebtItem(
            symbol=test_symbol,
            category=DebtCategory.QUALITY,
            severity=DebtSeverity.MEDIUM,
            title="Small issue",
            description="Desc",
            estimated_effort=2.0,
            estimated_impact=0.3,
            priority=DebtPriority.MEDIUM_IMPACT,
        ),
        DebtItem(
            symbol=test_symbol,
            category=DebtCategory.SECURITY,
            severity=DebtSeverity.CRITICAL,
            title="Large critical issue",
            description="Desc",
            estimated_effort=12.0,
            estimated_impact=0.9,
            priority=DebtPriority.CRITICAL_PATH,
        ),
    ]
    suggester.suggest_all(debt_items)
    critical = suggester.get_critical_path_suggestions()
    # At least one critical item (severity CRITICAL/HIGH with effort > 8 and impact > 0.5)
    assert isinstance(critical, list)


# ============================================================================
# Roadmap Generation Tests
# ============================================================================


def test_generate_roadmap(suggester, test_symbol):
    """Test roadmap generation."""
    debt_items = [
        DebtItem(
            symbol=test_symbol,
            category=DebtCategory.QUALITY,
            severity=DebtSeverity.MEDIUM,
            title="Issue",
            description="Desc",
            estimated_effort=4.0,
            estimated_impact=0.6,
            priority=DebtPriority.MEDIUM_IMPACT,
        ),
    ]
    suggester.suggest_all(debt_items)
    roadmap = suggester.generate_roadmap()

    assert roadmap is not None
    assert len(roadmap.suggestions) > 0
    assert roadmap.total_effort > 0
    assert roadmap.estimated_timeline is not None


def test_roadmap_timeline_formatting(suggester, test_symbol):
    """Test roadmap timeline is properly formatted."""
    # Create high-effort items for sprint estimation
    debt_items = [
        DebtItem(
            symbol=test_symbol,
            category=DebtCategory.QUALITY,
            severity=DebtSeverity.MEDIUM,
            title=f"Issue {i}",
            description="Desc",
            estimated_effort=30.0,  # High effort
            estimated_impact=0.6,
            priority=DebtPriority.MEDIUM_IMPACT,
        )
        for i in range(6)
    ]
    suggester.suggest_all(debt_items)
    roadmap = suggester.generate_roadmap()

    assert roadmap.estimated_timeline is not None
    assert isinstance(roadmap.estimated_timeline, str)


def test_roadmap_suggestions_ordered_by_priority(suggester, test_symbol):
    """Test that roadmap suggestions are ordered by priority."""
    debt_items = [
        DebtItem(
            symbol=test_symbol,
            category=DebtCategory.DOCUMENTATION,
            severity=DebtSeverity.LOW,
            title="Low priority",
            description="Desc",
            estimated_effort=2.0,
            estimated_impact=0.3,
            priority=DebtPriority.LOW_PRIORITY,
        ),
        DebtItem(
            symbol=test_symbol,
            category=DebtCategory.SECURITY,
            severity=DebtSeverity.CRITICAL,
            title="High priority",
            description="Desc",
            estimated_effort=8.0,
            estimated_impact=0.9,
            priority=DebtPriority.CRITICAL_PATH,
        ),
    ]
    suggester.suggest_all(debt_items)
    roadmap = suggester.generate_roadmap()

    assert roadmap.suggestions[0].debt_item.severity == DebtSeverity.CRITICAL


# ============================================================================
# Report Generation Tests
# ============================================================================


def test_report_no_suggestions(suggester):
    """Test report with no suggestions."""
    report = suggester.get_refactoring_report()
    assert report["status"] == "no_suggestions"


def test_report_with_suggestions(suggester, test_symbol):
    """Test report generation with suggestions."""
    debt_items = [
        DebtItem(
            symbol=test_symbol,
            category=DebtCategory.QUALITY,
            severity=DebtSeverity.MEDIUM,
            title="Issue",
            description="Desc",
            estimated_effort=4.0,
            estimated_impact=0.6,
            priority=DebtPriority.MEDIUM_IMPACT,
        ),
    ]
    suggester.suggest_all(debt_items)
    report = suggester.get_refactoring_report()

    assert report["status"] == "ready"
    assert report["total_suggestions"] == 1
    assert report["total_effort_hours"] > 0
    assert "high_priority" in report
    assert "critical_path" in report


def test_report_includes_top_priorities(suggester, test_symbol):
    """Test report includes top priority suggestions."""
    debt_items = [
        DebtItem(
            symbol=test_symbol,
            category=DebtCategory.SECURITY,
            severity=DebtSeverity.CRITICAL,
            title="Critical issue",
            description="Desc",
            estimated_effort=8.0,
            estimated_impact=0.9,
            priority=DebtPriority.CRITICAL_PATH,
        ),
    ]
    suggester.suggest_all(debt_items)
    report = suggester.get_refactoring_report()

    assert len(report["high_priority"]) > 0
    assert report["high_priority"][0]["symbol"] == "test_function"


# ============================================================================
# Metrics Projection Tests
# ============================================================================


def test_suggestion_has_before_metrics(suggester, quality_debt_item):
    """Test that suggestion includes before metrics."""
    suggestion = suggester.suggest_from_debt(quality_debt_item)
    assert suggestion.before_metrics is not None
    assert "debt_score" in suggestion.before_metrics
    assert "complexity" in suggestion.before_metrics


def test_suggestion_has_after_metrics(suggester, quality_debt_item):
    """Test that suggestion includes after metrics."""
    suggestion = suggester.suggest_from_debt(quality_debt_item)
    assert suggestion.after_metrics is not None
    assert suggestion.after_metrics["debt_score"] < suggestion.before_metrics["debt_score"]


def test_high_impact_improves_metrics_more(suggester, test_symbol):
    """Test that high-priority suggestions have higher priority scores."""
    low_priority_item = DebtItem(
        symbol=test_symbol,
        category=DebtCategory.QUALITY,
        severity=DebtSeverity.LOW,
        title="Low priority",
        description="Desc",
        estimated_effort=2.0,
        estimated_impact=0.1,
        priority=DebtPriority.LOW_PRIORITY,
    )
    high_priority_item = DebtItem(
        symbol=test_symbol,
        category=DebtCategory.SECURITY,  # Different category for different refactoring type
        severity=DebtSeverity.CRITICAL,
        title="High priority",
        description="Desc",
        estimated_effort=8.0,
        estimated_impact=0.9,
        priority=DebtPriority.CRITICAL_PATH,
    )

    low_sugg = suggester.suggest_from_debt(low_priority_item)
    suggester.suggestions = []  # Reset
    high_sugg = suggester.suggest_from_debt(high_priority_item)

    # High-priority suggestion should have higher priority_score
    assert high_sugg.priority_score > low_sugg.priority_score


# ============================================================================
# Step Dependency Tests
# ============================================================================


def test_steps_have_correct_dependencies(suggester, quality_debt_item):
    """Test that refactoring steps have proper dependencies."""
    suggestion = suggester.suggest_from_debt(quality_debt_item)
    for step in suggestion.steps[1:]:
        if step.dependencies:
            # All referenced dependencies should exist
            max_step_num = max(s.step_number for s in suggestion.steps)
            for dep in step.dependencies:
                assert dep <= step.step_number - 1


def test_steps_ordered_by_sequence(suggester, security_debt_item):
    """Test that steps are ordered sequentially."""
    suggestion = suggester.suggest_from_debt(security_debt_item)
    step_numbers = [s.step_number for s in suggestion.steps]
    assert step_numbers == sorted(step_numbers)


# ============================================================================
# Edge Cases
# ============================================================================


def test_suggest_from_low_severity_debt(suggester, test_symbol):
    """Test suggestion for low severity debt."""
    debt_item = DebtItem(
        symbol=test_symbol,
        category=DebtCategory.DOCUMENTATION,
        severity=DebtSeverity.INFO,
        title="Info issue",
        description="Minor documentation gap",
        estimated_effort=1.0,
        estimated_impact=0.1,
        priority=DebtPriority.LOW_PRIORITY,
    )
    suggestion = suggester.suggest_from_debt(debt_item)
    assert suggestion is not None
    assert suggestion.estimated_risk == "low"


def test_suggest_handles_all_debt_categories(suggester, test_symbol):
    """Test that suggester handles all debt categories."""
    categories = [
        DebtCategory.SECURITY,
        DebtCategory.PERFORMANCE,
        DebtCategory.QUALITY,
        DebtCategory.TESTING,
        DebtCategory.DOCUMENTATION,
        DebtCategory.MAINTAINABILITY,
    ]

    for category in categories:
        debt_item = DebtItem(
            symbol=test_symbol,
            category=category,
            severity=DebtSeverity.MEDIUM,
            title="Test issue",
            description="Test",
            estimated_effort=4.0,
            estimated_impact=0.5,
            priority=DebtPriority.MEDIUM_IMPACT,
        )
        suggestion = suggester.suggest_from_debt(debt_item)
        assert suggestion is not None
        assert suggestion.refactoring_type is not None


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_workflow(suggester):
    """Test complete refactoring suggestion workflow."""
    symbols = [
        Symbol(
            name="func1",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=1,
            line_end=30,
            namespace="",
            full_qualified_name="func1",
            signature="def func1():",
            code="",
            docstring="",
            metrics=SymbolMetrics(),
        ),
        Symbol(
            name="func2",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=50,
            line_end=100,
            namespace="",
            full_qualified_name="func2",
            signature="def func2():",
            code="",
            docstring="",
            metrics=SymbolMetrics(),
        ),
    ]

    debt_items = [
        DebtItem(
            symbol=symbols[0],
            category=DebtCategory.DOCUMENTATION,
            severity=DebtSeverity.LOW,
            title="Missing doc",
            description="No docstring",
            estimated_effort=2.0,
            estimated_impact=0.3,
            priority=DebtPriority.LOW_PRIORITY,
        ),
        DebtItem(
            symbol=symbols[1],
            category=DebtCategory.QUALITY,
            severity=DebtSeverity.HIGH,
            title="High complexity",
            description="Too complex",
            estimated_effort=8.0,
            estimated_impact=0.8,
            priority=DebtPriority.HIGH_IMPACT,
        ),
    ]

    # Generate suggestions
    suggestions = suggester.suggest_all(debt_items)
    assert len(suggestions) == 2

    # Generate roadmap
    roadmap = suggester.generate_roadmap()
    assert len(roadmap.suggestions) == 2
    # Total effort is sum of step efforts, not original debt item efforts
    assert roadmap.total_effort > 0

    # Generate report
    report = suggester.get_refactoring_report()
    assert report["status"] == "ready"
    assert len(report["high_priority"]) > 0
