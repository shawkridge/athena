"""Unit tests for Phase 9 SuggestionsEngine."""

import pytest
import json
from athena.core.database import Database
from athena.rules.models import (
    Rule, RuleValidationResult, RuleCategory, RuleType, SeverityLevel
)
from athena.rules.store import RulesStore
from athena.rules.engine import RulesEngine
from athena.rules.suggestions import SuggestionsEngine


@pytest.fixture
def db(tmp_path):
    """Create temporary database for testing."""
    db = Database(str(tmp_path / "test.db"))
    # Create rules schema
    cursor = db.conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS project_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            rule_type TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'warning',
            condition TEXT NOT NULL,
            exception_condition TEXT,
            auto_block BOOLEAN DEFAULT 1,
            can_override BOOLEAN DEFAULT 1,
            override_requires_approval BOOLEAN DEFAULT 0,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            created_by TEXT DEFAULT 'system',
            enabled BOOLEAN DEFAULT 1,
            tags TEXT DEFAULT '[]',
            related_rules TEXT DEFAULT '[]',
            documentation_url TEXT,
            UNIQUE(project_id, name)
        );
        CREATE INDEX IF NOT EXISTS idx_project_rules_project ON project_rules(project_id);
        CREATE INDEX IF NOT EXISTS idx_project_rules_category ON project_rules(category);
        CREATE INDEX IF NOT EXISTS idx_project_rules_enabled ON project_rules(enabled);

        CREATE TABLE IF NOT EXISTS rule_validation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id INTEGER NOT NULL,
            project_id INTEGER NOT NULL,
            task_id INTEGER,
            is_violation BOOLEAN DEFAULT 0,
            context TEXT,
            created_at INTEGER NOT NULL,
            FOREIGN KEY (rule_id) REFERENCES project_rules(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_validation_history_project ON rule_validation_history(project_id);

        CREATE TABLE IF NOT EXISTS rule_overrides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            rule_id INTEGER NOT NULL,
            task_id INTEGER,
            overridden_at INTEGER NOT NULL,
            overridden_by TEXT NOT NULL,
            justification TEXT NOT NULL,
            approved_by TEXT,
            approval_at INTEGER,
            expires_at INTEGER,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (rule_id) REFERENCES project_rules(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS rule_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            rules TEXT NOT NULL,
            usage_count INTEGER DEFAULT 0,
            created_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS project_rule_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL UNIQUE,
            default_severity TEXT DEFAULT 'warning',
            allow_overrides BOOLEAN DEFAULT 1,
            enforcement_level TEXT DEFAULT 'strict',
            created_at INTEGER NOT NULL
        );
    """)
    db.conn.commit()
    return db


@pytest.fixture
def store(db):
    """Create RulesStore instance."""
    return RulesStore(db)


@pytest.fixture
def engine(db, store):
    """Create RulesEngine instance."""
    return RulesEngine(db, store)


@pytest.fixture
def suggestions_engine(engine):
    """Create SuggestionsEngine instance."""
    return SuggestionsEngine(engine)


@pytest.fixture
def test_project_id():
    """Test project ID."""
    return 1


class TestSuggestionsEngineFixSuggestions:
    """Test SuggestionsEngine.suggest_fixes() method."""

    def test_suggest_fixes_code_quality_coverage(self, suggestions_engine):
        """Test fix suggestions for test coverage violation."""
        violations = [
            {
                "rule_id": 1,
                "rule_name": "Test Coverage Minimum",
                "category": "code_quality",
                "type": "coverage",
                "severity": "warning",
                "message": "Test coverage below 80%",
            }
        ]

        fixes = suggestions_engine.suggest_fixes(violations)

        assert len(fixes) > 0
        assert any("coverage" in fix.lower() for fix in fixes)
        assert any("pytest" in fix.lower() for fix in fixes)

    def test_suggest_fixes_code_quality_function_length(self, suggestions_engine):
        """Test fix suggestions for function length violation."""
        violations = [
            {
                "rule_id": 1,
                "rule_name": "Function Length Maximum",
                "category": "code_quality",
                "type": "length",
                "severity": "warning",
                "message": "Function exceeds max length",
            }
        ]

        fixes = suggestions_engine.suggest_fixes(violations)

        assert len(fixes) > 0
        assert any("refactor" in fix.lower() or "split" in fix.lower() for fix in fixes)

    def test_suggest_fixes_security_sql_injection(self, suggestions_engine):
        """Test fix suggestions for SQL injection vulnerability."""
        violations = [
            {
                "rule_id": 1,
                "rule_name": "SQL Injection Prevention",
                "category": "security",
                "type": "injection",
                "severity": "critical",
                "message": "User input not parameterized",
            }
        ]

        fixes = suggestions_engine.suggest_fixes(violations)

        assert len(fixes) > 0
        assert any("parameterized" in fix.lower() or "prepared" in fix.lower() for fix in fixes)

    def test_suggest_fixes_security_secrets(self, suggestions_engine):
        """Test fix suggestions for hardcoded secrets."""
        violations = [
            {
                "rule_id": 1,
                "rule_name": "No Hardcoded Secrets",
                "category": "security",
                "type": "secret",
                "severity": "critical",
                "message": "API key found in code",
            }
        ]

        fixes = suggestions_engine.suggest_fixes(violations)

        assert len(fixes) > 0
        assert any("environment" in fix.lower() for fix in fixes)

    def test_suggest_fixes_performance_query(self, suggestions_engine):
        """Test fix suggestions for query performance."""
        violations = [
            {
                "rule_id": 1,
                "rule_name": "Query Performance",
                "category": "performance",
                "type": "database",
                "severity": "warning",
                "message": "Slow database query detected",
            }
        ]

        fixes = suggestions_engine.suggest_fixes(violations)

        assert len(fixes) > 0
        assert any("index" in fix.lower() or "optimize" in fix.lower() for fix in fixes)

    def test_suggest_fixes_documentation_docstring(self, suggestions_engine):
        """Test fix suggestions for missing docstrings."""
        violations = [
            {
                "rule_id": 1,
                "rule_name": "Function Documentation",
                "category": "documentation",
                "type": "comment",
                "severity": "info",
                "message": "Function missing docstring",
            }
        ]

        fixes = suggestions_engine.suggest_fixes(violations)

        assert len(fixes) > 0
        assert any("docstring" in fix.lower() for fix in fixes)

    def test_suggest_fixes_process_review(self, suggestions_engine):
        """Test fix suggestions for missing code review."""
        violations = [
            {
                "rule_id": 1,
                "rule_name": "Code Review Required",
                "category": "process",
                "type": "approval",
                "severity": "error",
                "message": "Pull request not approved",
            }
        ]

        fixes = suggestions_engine.suggest_fixes(violations)

        assert len(fixes) > 0
        assert any("review" in fix.lower() for fix in fixes)

    def test_suggest_fixes_resource_duration(self, suggestions_engine):
        """Test fix suggestions for duration constraint."""
        violations = [
            {
                "rule_id": 1,
                "rule_name": "Task Duration Limit",
                "category": "resource",
                "type": "duration",
                "severity": "warning",
                "message": "Task duration exceeds limit",
            }
        ]

        fixes = suggestions_engine.suggest_fixes(violations)

        assert len(fixes) > 0
        assert any("break" in fix.lower() or "split" in fix.lower() for fix in fixes)

    def test_suggest_fixes_deployment(self, suggestions_engine):
        """Test fix suggestions for deployment process."""
        violations = [
            {
                "rule_id": 1,
                "rule_name": "Staging Deployment",
                "category": "deployment",
                "type": "environment",
                "severity": "error",
                "message": "Must deploy to staging first",
            }
        ]

        fixes = suggestions_engine.suggest_fixes(violations)

        assert len(fixes) > 0
        assert any("staging" in fix.lower() for fix in fixes)

    def test_suggest_fixes_multiple_violations(self, suggestions_engine):
        """Test fix suggestions for multiple violations."""
        violations = [
            {
                "rule_id": 1,
                "rule_name": "Test Coverage",
                "category": "code_quality",
                "type": "coverage",
                "severity": "warning",
                "message": "Coverage too low",
            },
            {
                "rule_id": 2,
                "rule_name": "Code Review",
                "category": "process",
                "type": "approval",
                "severity": "error",
                "message": "No approval",
            },
        ]

        fixes = suggestions_engine.suggest_fixes(violations)

        assert len(fixes) >= 2


class TestSuggestionsEngineCompliantPlan:
    """Test SuggestionsEngine.suggest_compliant_plan() method."""

    def test_suggest_compliant_plan_duration_violations(self, suggestions_engine):
        """Test plan suggestions for duration violations."""
        violations = [
            {
                "rule_id": 1,
                "rule_name": "Max Task Duration",
                "category": "resource",
                "type": "duration",
                "message": "Task duration too long",
            }
        ]

        plan = {
            "steps": [{"name": "Step 1"}],
            "duration": 480,
        }

        suggestions = suggestions_engine.suggest_compliant_plan(violations, plan)

        assert len(suggestions) > 0
        assert any("split" in s.lower() or "subtask" in s.lower() for s in suggestions)

    def test_suggest_compliant_plan_parallel_violations(self, suggestions_engine):
        """Test plan suggestions for parallelization violations."""
        violations = [
            {
                "rule_id": 1,
                "rule_name": "Parallel Task Limit",
                "category": "resource",
                "type": "concurrent",
                "message": "Too many parallel tasks",
            }
        ]

        suggestions = suggestions_engine.suggest_compliant_plan(violations)

        assert len(suggestions) > 0
        assert any("parallel" in s.lower() or "sequential" in s.lower() for s in suggestions)

    def test_suggest_compliant_plan_dependency_violations(self, suggestions_engine):
        """Test plan suggestions for dependency violations."""
        violations = [
            {
                "rule_id": 1,
                "rule_name": "Missing Dependencies",
                "category": "resource",
                "type": "prerequisite",
                "message": "Unresolved dependencies",
            }
        ]

        suggestions = suggestions_engine.suggest_compliant_plan(violations)

        assert len(suggestions) > 0
        assert any("depend" in s.lower() or "prerequisite" in s.lower() for s in suggestions)

    def test_suggest_compliant_plan_resource_violations(self, suggestions_engine):
        """Test plan suggestions for resource violations."""
        violations = [
            {
                "rule_id": 1,
                "rule_name": "Person Capacity",
                "category": "resource",
                "type": "capacity",
                "message": "Person overloaded",
            }
        ]

        suggestions = suggestions_engine.suggest_compliant_plan(violations)

        assert len(suggestions) > 0
        assert any("distribute" in s.lower() or "balance" in s.lower() for s in suggestions)

    def test_suggest_compliant_plan_with_original_plan(self, suggestions_engine):
        """Test plan suggestions include specific recommendations."""
        violations = [
            {
                "rule_id": 1,
                "rule_name": "Max Duration Per Step",
                "category": "resource",
                "type": "duration",
                "message": "Step duration too long",
            }
        ]

        plan = {
            "steps": [
                {"name": "Step 1"},
                {"name": "Step 2"},
                {"name": "Step 3"},
            ],
            "duration": 300,
        }

        suggestions = suggestions_engine.suggest_compliant_plan(violations, plan)

        # Should include specific duration target
        assert any("minute" in s.lower() or "duration" in s.lower() for s in suggestions)


class TestSuggestionsEngineRuleAdjustments:
    """Test SuggestionsEngine.suggest_rule_adjustments() method."""

    def test_suggest_rule_adjustments_no_violations(self, suggestions_engine):
        """Test adjustment suggestions for rule with no violations."""
        suggestions = suggestions_engine.suggest_rule_adjustments(0, "Test Rule")

        assert len(suggestions) > 0
        assert any(s.get("type") == "monitor" for s in suggestions)

    def test_suggest_rule_adjustments_low_violations(self, suggestions_engine):
        """Test adjustment suggestions for rule with few violations."""
        suggestions = suggestions_engine.suggest_rule_adjustments(2, "Test Rule")

        assert len(suggestions) > 0
        assert any(s.get("type") == "maintain" for s in suggestions)

    def test_suggest_rule_adjustments_medium_violations(self, suggestions_engine):
        """Test adjustment suggestions for rule with moderate violations."""
        suggestions = suggestions_engine.suggest_rule_adjustments(4, "Test Rule")

        assert len(suggestions) > 0
        assert any(s.get("type") == "review" for s in suggestions)

    def test_suggest_rule_adjustments_high_violations(self, suggestions_engine):
        """Test adjustment suggestions for rule with many violations."""
        suggestions = suggestions_engine.suggest_rule_adjustments(7, "Test Rule")

        assert len(suggestions) > 0
        assert any(s.get("type") == "adjust" for s in suggestions)

    def test_suggest_rule_adjustments_very_high_violations(self, suggestions_engine):
        """Test adjustment suggestions for rule with very frequent violations."""
        suggestions = suggestions_engine.suggest_rule_adjustments(15, "Test Rule")

        assert len(suggestions) > 0
        assert any(s.get("type") == "relax" for s in suggestions)
        # Should include priority
        assert any(s.get("priority") == "high" for s in suggestions)

    def test_suggest_rule_adjustments_include_examples(self, suggestions_engine):
        """Test that high-violation suggestions include examples."""
        suggestions = suggestions_engine.suggest_rule_adjustments(15, "Test Rule")

        # Find adjust/relax suggestion
        relax = [s for s in suggestions if s.get("type") == "relax"]
        assert len(relax) > 0
        assert "examples" in relax[0]


class TestSuggestionsEngineComprehensiveReport:
    """Test SuggestionsEngine.generate_comprehensive_report() method."""

    def test_generate_comprehensive_report_compliant(self, suggestions_engine):
        """Test generating report for compliant task."""
        validation = RuleValidationResult(
            task_id=1,
            project_id=1,
            is_compliant=True,
            violation_count=0,
            warning_count=0,
            violations=[],
            suggestions=[],
            blocking_violations=[],
        )

        report = suggestions_engine.generate_comprehensive_report(validation)

        assert report["compliance_status"] == "PASS"
        assert report["is_compliant"] is True
        assert report["can_execute"] is True
        assert report["summary"]["total_violations"] == 0

    def test_generate_comprehensive_report_non_compliant(self, suggestions_engine):
        """Test generating report for non-compliant task."""
        violations = [
            {
                "rule_id": 1,
                "rule_name": "Test rule",
                "category": "code_quality",
                "type": "coverage",
                "severity": "error",
                "message": "Coverage too low",
                "suggestion": "Increase coverage",
            }
        ]

        validation = RuleValidationResult(
            task_id=1,
            project_id=1,
            is_compliant=False,
            violation_count=1,
            warning_count=0,
            violations=violations,
            suggestions=[],
            blocking_violations=[1],
        )

        report = suggestions_engine.generate_comprehensive_report(validation)

        assert report["compliance_status"] == "FAIL"
        assert report["is_compliant"] is False
        assert report["can_execute"] is False
        assert report["summary"]["total_violations"] == 1
        assert "fixes" in report["suggestions"]
        assert "plan_modifications" in report["suggestions"]

    def test_generate_comprehensive_report_structure(self, suggestions_engine):
        """Test report has expected structure."""
        validation = RuleValidationResult(
            task_id=1,
            project_id=1,
            is_compliant=True,
            violation_count=0,
            warning_count=0,
            violations=[],
            suggestions=[],
            blocking_violations=[],
        )

        report = suggestions_engine.generate_comprehensive_report(validation)

        # Check required fields
        assert "task_id" in report
        assert "project_id" in report
        assert "is_compliant" in report
        assert "summary" in report
        assert "violations" in report
        assert "suggestions" in report
        assert "compliance_status" in report
        assert "can_execute" in report

        # Check summary structure
        assert "total_violations" in report["summary"]
        assert "warnings" in report["summary"]
        assert "blocking_violations" in report["summary"]

    def test_generate_comprehensive_report_with_warnings(self, suggestions_engine):
        """Test report correctly handles warnings."""
        violations = [
            {
                "rule_id": 1,
                "rule_name": "Coverage",
                "category": "code_quality",
                "type": "coverage",
                "severity": "warning",
                "message": "Coverage below preferred",
                "suggestion": "Increase coverage",
            }
        ]

        validation = RuleValidationResult(
            task_id=1,
            project_id=1,
            is_compliant=True,
            violation_count=1,
            warning_count=1,
            violations=violations,
            suggestions=[],
            blocking_violations=[],
        )

        report = suggestions_engine.generate_comprehensive_report(validation)

        assert report["is_compliant"] is True
        assert report["can_execute"] is True
        assert report["summary"]["warnings"] == 1
