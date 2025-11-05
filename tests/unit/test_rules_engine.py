"""Unit tests for Rules Engine.

Tests rule enforcement including:
- Rule definition and management
- Rule checking against symbols
- Violation tracking
- Severity-based filtering
- Fix suggestions
- Report generation
"""

import pytest
from athena.symbols.rules_engine import (
    RulesEngine,
    Rule,
    RuleViolation,
    RuleSeverity,
    RuleAction,
)
from athena.symbols.symbol_models import Symbol, SymbolType, SymbolMetrics


@pytest.fixture
def engine():
    """Create a fresh rules engine."""
    return RulesEngine()


@pytest.fixture
def test_symbol():
    """Create a test symbol."""
    return Symbol(
        name="test_func",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=10,
        line_end=20,
        namespace="",
        full_qualified_name="test.test_func",
        signature="def test_func():",
        code="",
        docstring="",
        metrics=SymbolMetrics(),
    )


@pytest.fixture
def naming_rule():
    """Create a naming convention rule."""
    def check_snake_case(symbol, context):
        """Check if name is snake_case."""
        return not all(c.islower() or c == '_' or c.isdigit() for c in symbol.name)

    return Rule(
        id="naming_001",
        name="Snake Case Naming",
        description="Function names must be snake_case",
        category="naming",
        severity=RuleSeverity.WARNING,
        action=RuleAction.WARN,
        condition=check_snake_case,
        message_template="Function {symbol} should be snake_case",
        fix_suggestion="Rename to lowercase with underscores",
    )


@pytest.fixture
def documentation_rule():
    """Create a documentation rule."""
    def check_docstring(symbol, context):
        """Check if symbol has docstring."""
        return symbol.docstring == ""

    return Rule(
        id="docs_001",
        name="Missing Docstring",
        description="All functions must have docstrings",
        category="documentation",
        severity=RuleSeverity.ERROR,
        action=RuleAction.SUGGEST_FIX,
        condition=check_docstring,
        message_template="Function {symbol} is missing docstring",
        fix_suggestion="Add docstring documentation",
    )


# ============================================================================
# Initialization Tests
# ============================================================================


def test_engine_initialization(engine):
    """Test engine initializes empty."""
    assert engine.rules == {}
    assert engine.violations == []


# ============================================================================
# Rule Management Tests
# ============================================================================


def test_add_rule(engine, naming_rule):
    """Test adding a rule."""
    engine.add_rule(naming_rule)

    assert len(engine.rules) == 1
    assert "naming_001" in engine.rules
    assert engine.rules["naming_001"].name == "Snake Case Naming"


def test_add_multiple_rules(engine, naming_rule, documentation_rule):
    """Test adding multiple rules."""
    engine.add_rule(naming_rule)
    engine.add_rule(documentation_rule)

    assert len(engine.rules) == 2
    assert "naming_001" in engine.rules
    assert "docs_001" in engine.rules


def test_remove_rule(engine, naming_rule):
    """Test removing a rule."""
    engine.add_rule(naming_rule)
    result = engine.remove_rule("naming_001")

    assert result is True
    assert len(engine.rules) == 0


def test_remove_nonexistent_rule(engine):
    """Test removing non-existent rule."""
    result = engine.remove_rule("nonexistent")

    assert result is False


# ============================================================================
# Rule Enable/Disable Tests
# ============================================================================


def test_disable_rule(engine, naming_rule):
    """Test disabling a rule."""
    engine.add_rule(naming_rule)
    result = engine.disable_rule("naming_001")

    assert result is True
    assert engine.rules["naming_001"].enabled is False


def test_enable_rule(engine, naming_rule):
    """Test enabling a rule."""
    engine.add_rule(naming_rule)
    engine.disable_rule("naming_001")
    result = engine.enable_rule("naming_001")

    assert result is True
    assert engine.rules["naming_001"].enabled is True


def test_enable_nonexistent_rule(engine):
    """Test enabling non-existent rule."""
    result = engine.enable_rule("nonexistent")

    assert result is False


# ============================================================================
# Single Symbol Check Tests
# ============================================================================


def test_check_symbol_no_violations(engine, test_symbol):
    """Test checking symbol with no violations."""
    def pass_condition(symbol, context):
        return False

    rule = Rule(
        id="test_001",
        name="Test Rule",
        description="Test",
        category="test",
        severity=RuleSeverity.WARNING,
        action=RuleAction.WARN,
        condition=pass_condition,
        message_template="Test violation",
    )

    engine.add_rule(rule)
    violations = engine.check_symbol(test_symbol)

    assert len(violations) == 0


def test_check_symbol_with_violation(engine, test_symbol):
    """Test checking symbol with violation."""
    def fail_condition(symbol, context):
        return True

    rule = Rule(
        id="test_001",
        name="Test Rule",
        description="Test",
        category="test",
        severity=RuleSeverity.ERROR,
        action=RuleAction.WARN,
        condition=fail_condition,
        message_template="Symbol {symbol} failed test",
    )

    engine.add_rule(rule)
    violations = engine.check_symbol(test_symbol)

    assert len(violations) == 1
    assert violations[0].rule_id == "test_001"
    assert violations[0].symbol_name == "test_func"


def test_disabled_rule_not_checked(engine, test_symbol):
    """Test that disabled rules are not checked."""
    def fail_condition(symbol, context):
        return True

    rule = Rule(
        id="test_001",
        name="Test Rule",
        description="Test",
        category="test",
        severity=RuleSeverity.WARNING,
        action=RuleAction.WARN,
        condition=fail_condition,
        message_template="Test violation",
        enabled=False,
    )

    engine.add_rule(rule)
    violations = engine.check_symbol(test_symbol)

    assert len(violations) == 0


# ============================================================================
# Multiple Symbol Check Tests
# ============================================================================


def test_check_multiple_symbols(engine):
    """Test checking multiple symbols."""
    symbols = {
        "func1": Symbol(
            name="func1",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=1,
            line_end=10,
            namespace="",
            full_qualified_name="test.func1",
            signature="def func1():",
            code="",
            docstring="",
            metrics=SymbolMetrics(),
        ),
        "func2": Symbol(
            name="func2",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=20,
            line_end=30,
            namespace="",
            full_qualified_name="test.func2",
            signature="def func2():",
            code="",
            docstring="",
            metrics=SymbolMetrics(),
        ),
    }

    def fail_condition(symbol, context):
        return True

    rule = Rule(
        id="test_001",
        name="Test Rule",
        description="Test",
        category="test",
        severity=RuleSeverity.WARNING,
        action=RuleAction.WARN,
        condition=fail_condition,
        message_template="Symbol {symbol} failed",
    )

    engine.add_rule(rule)
    result = engine.check_symbols(symbols)

    assert result.violation_count == 2
    assert not result.passed


# ============================================================================
# Violation Filtering Tests
# ============================================================================


def test_get_violations_by_severity(engine, test_symbol):
    """Test filtering violations by severity."""
    rules = []
    for i, severity in enumerate([RuleSeverity.WARNING, RuleSeverity.ERROR, RuleSeverity.CRITICAL]):
        def fail_condition(symbol, context):
            return True

        rule = Rule(
            id=f"rule_{i}",
            name=f"Rule {i}",
            description="Test",
            category="test",
            severity=severity,
            action=RuleAction.WARN,
            condition=fail_condition,
            message_template="Test violation",
        )
        engine.add_rule(rule)
        engine.check_symbol(test_symbol)

    critical_violations = engine.get_violations_by_severity(RuleSeverity.CRITICAL)
    assert len(critical_violations) == 1
    assert critical_violations[0].severity == RuleSeverity.CRITICAL


def test_get_violations_by_rule(engine, test_symbol):
    """Test filtering violations by rule."""
    def fail_condition(symbol, context):
        return True

    rule1 = Rule(
        id="rule_1",
        name="Rule 1",
        description="Test",
        category="test",
        severity=RuleSeverity.WARNING,
        action=RuleAction.WARN,
        condition=fail_condition,
        message_template="Test 1",
    )
    rule2 = Rule(
        id="rule_2",
        name="Rule 2",
        description="Test",
        category="test",
        severity=RuleSeverity.WARNING,
        action=RuleAction.WARN,
        condition=fail_condition,
        message_template="Test 2",
    )

    engine.add_rule(rule1)
    engine.add_rule(rule2)
    engine.check_symbol(test_symbol)

    rule1_violations = engine.get_violations_by_rule("rule_1")
    assert len(rule1_violations) == 1
    assert rule1_violations[0].rule_id == "rule_1"


def test_get_violations_by_symbol(engine):
    """Test filtering violations by symbol."""
    symbols = {
        "func1": Symbol(
            name="func1",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=1,
            line_end=10,
            namespace="",
            full_qualified_name="test.func1",
            signature="def func1():",
            code="",
            docstring="",
            metrics=SymbolMetrics(),
        ),
        "func2": Symbol(
            name="func2",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=20,
            line_end=30,
            namespace="",
            full_qualified_name="test.func2",
            signature="def func2():",
            code="",
            docstring="",
            metrics=SymbolMetrics(),
        ),
    }

    def fail_condition(symbol, context):
        return True

    rule = Rule(
        id="test_001",
        name="Test Rule",
        description="Test",
        category="test",
        severity=RuleSeverity.WARNING,
        action=RuleAction.WARN,
        condition=fail_condition,
        message_template="Test violation",
    )

    engine.add_rule(rule)
    engine.check_symbols(symbols)

    func1_violations = engine.get_violations_by_symbol("func1")
    assert len(func1_violations) == 1
    assert func1_violations[0].symbol_name == "func1"


# ============================================================================
# Violation Management Tests
# ============================================================================


def test_clear_violations(engine, test_symbol):
    """Test clearing violations."""
    def fail_condition(symbol, context):
        return True

    rule = Rule(
        id="test_001",
        name="Test Rule",
        description="Test",
        category="test",
        severity=RuleSeverity.WARNING,
        action=RuleAction.WARN,
        condition=fail_condition,
        message_template="Test violation",
    )

    engine.add_rule(rule)
    engine.check_symbol(test_symbol)
    assert len(engine.violations) > 0

    engine.clear_violations()
    assert len(engine.violations) == 0


# ============================================================================
# Enforcement Report Tests
# ============================================================================


def test_get_enforcement_report(engine, test_symbol):
    """Test enforcement report generation."""
    def fail_condition(symbol, context):
        return True

    rule = Rule(
        id="test_001",
        name="Test Rule",
        description="Test",
        category="test",
        severity=RuleSeverity.ERROR,
        action=RuleAction.WARN,
        condition=fail_condition,
        message_template="Test violation",
    )

    engine.add_rule(rule)
    engine.check_symbol(test_symbol)
    report = engine.get_enforcement_report(total_symbols=10)

    assert report.total_symbols == 10
    assert report.total_rules == 1
    assert report.error_violations == 1
    assert report.symbols_with_violations == 1


def test_enforcement_pass_rate(engine):
    """Test pass rate calculation."""
    symbols = {}
    for i in range(1, 6):  # Start from 1 to avoid line_start=0
        symbols[f"func{i}"] = Symbol(
            name=f"func{i}",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=i * 10,
            line_end=i * 10 + 10,
            namespace="",
            full_qualified_name=f"test.func{i}",
            signature=f"def func{i}():",
            code="",
            docstring="",
            metrics=SymbolMetrics(),
        )

    def violation_if_even(symbol, context):
        index = int(symbol.name[-1])
        return index % 2 == 0

    rule = Rule(
        id="test_001",
        name="Test Rule",
        description="Test",
        category="test",
        severity=RuleSeverity.WARNING,
        action=RuleAction.WARN,
        condition=violation_if_even,
        message_template="Test violation",
    )

    engine.add_rule(rule)
    engine.check_symbols(symbols)
    report = engine.get_enforcement_report(total_symbols=5)

    assert report.pass_rate > 0.0
    assert report.pass_rate <= 1.0


# ============================================================================
# Fix Suggestions Tests
# ============================================================================


def test_suggest_fixes(engine, test_symbol):
    """Test fix suggestion retrieval."""
    def fail_condition(symbol, context):
        return True

    rule = Rule(
        id="test_001",
        name="Test Rule",
        description="Test",
        category="test",
        severity=RuleSeverity.WARNING,
        action=RuleAction.SUGGEST_FIX,
        condition=fail_condition,
        message_template="Test violation",
        fix_suggestion="Apply this fix",
    )

    engine.add_rule(rule)
    engine.check_symbol(test_symbol)
    suggestions = engine.suggest_fixes()

    assert len(suggestions) > 0
    assert suggestions[0][1] == "Apply this fix"


# ============================================================================
# Rule Statistics Tests
# ============================================================================


def test_get_rule_statistics(engine, test_symbol):
    """Test rule statistics."""
    def fail_condition(symbol, context):
        return True

    for i in range(3):
        rule = Rule(
            id=f"rule_{i}",
            name=f"Rule {i}",
            description="Test",
            category="test",
            severity=RuleSeverity.WARNING,
            action=RuleAction.WARN,
            condition=fail_condition,
            message_template="Test violation",
        )
        engine.add_rule(rule)

    engine.check_symbol(test_symbol)
    stats = engine.get_rule_statistics()

    assert stats["total_rules"] == 3
    assert stats["enabled_rules"] == 3
    assert stats["total_violations"] == 3


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_enforcement_workflow(engine):
    """Test complete enforcement workflow."""
    # Create rules
    def naming_violation(symbol, context):
        return any(c.isupper() for c in symbol.name)

    def docs_violation(symbol, context):
        return symbol.docstring == ""

    naming_rule = Rule(
        id="naming_001",
        name="Naming Rule",
        description="Check naming",
        category="naming",
        severity=RuleSeverity.WARNING,
        action=RuleAction.WARN,
        condition=naming_violation,
        message_template="Naming violation in {symbol}",
    )

    docs_rule = Rule(
        id="docs_001",
        name="Docs Rule",
        description="Check docs",
        category="documentation",
        severity=RuleSeverity.ERROR,
        action=RuleAction.SUGGEST_FIX,
        condition=docs_violation,
        message_template="Missing docs in {symbol}",
        fix_suggestion="Add docstring",
    )

    # Add rules
    engine.add_rule(naming_rule)
    engine.add_rule(docs_rule)
    assert len(engine.rules) == 2

    # Create symbols
    symbols = {
        "testFunc": Symbol(
            name="testFunc",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=1,
            line_end=10,
            namespace="",
            full_qualified_name="test.testFunc",
            signature="def testFunc():",
            code="",
            docstring="",
            metrics=SymbolMetrics(),
        ),
    }

    # Check symbols
    result = engine.check_symbols(symbols)
    assert result.violation_count >= 1

    # Get report
    report = engine.get_enforcement_report(total_symbols=1)
    assert report.total_rules == 2
    assert len(report.violations) >= 1
