"""Integration tests for Week 1.3: Rules Engine + Suggestions Engine + Phase 7.

Tests the complete workflow of:
1. Creating rules from templates
2. Validating tasks against rules
3. Getting suggestions to fix violations
4. Overriding rules with justification
5. Integrating with Phase 7 plan optimization
"""

import pytest
from pathlib import Path
from datetime import datetime

from athena.core.database import Database
from athena.rules import RuleTemplates, create_project_rules, RulesEngine, SuggestionsEngine
from athena.rules.store import RulesStore
from athena.rules.models import Rule, RuleCategory, RuleType, SeverityLevel
from athena.prospective import ProspectiveStore
from athena.prospective.models import ProspectiveTask, TaskStatus, TaskPriority, TaskPhase, Plan


class TestWeek13RulesTemplates:
    """Test rule template generation and application."""

    def test_template_names_available(self):
        """Test that all template names are available."""
        names = RuleTemplates.get_template_names()
        assert len(names) == 7
        assert "quality_gates" in names
        assert "testing_requirements" in names
        assert "timeline_constraints" in names
        assert "resource_limits" in names
        assert "deployment_approval" in names
        assert "documentation_requirements" in names
        assert "security_compliance" in names

    def test_quality_gates_template(self):
        """Test quality gates template."""
        rules = RuleTemplates.quality_gates()
        assert len(rules) == 4
        assert all(r.category == RuleCategory.QUALITY for r in rules)
        names = [r.name for r in rules]
        assert "min_test_coverage" in names
        assert "max_cyclomatic_complexity" in names
        assert "code_review_required" in names

    def test_create_project_rules_all_templates(self, tmp_path):
        """Test creating rules for a project with all templates."""
        rules = create_project_rules(project_id=1)
        assert len(rules) > 0
        assert all(r.project_id == 1 for r in rules)

    def test_create_project_rules_specific_templates(self, tmp_path):
        """Test creating rules from specific templates."""
        templates = ["quality_gates", "testing_requirements"]
        rules = create_project_rules(project_id=1, template_names=templates)
        assert len(rules) == 7  # 4 + 3
        assert all(r.project_id == 1 for r in rules)

    def test_rule_conditions_are_strings(self):
        """Test that rule conditions are valid JSON-like strings."""
        rules = RuleTemplates.quality_gates()
        for rule in rules:
            assert isinstance(rule.condition, str)
            assert "{" in rule.condition  # Should be JSON-like


class TestWeek13RulesValidation:
    """Test task validation against rules."""

    def test_task_compliant_with_rules(self, tmp_path):
        """Test validating a compliant task."""
        db = Database(tmp_path / "test.db")
        store = RulesStore(db)
        engine = RulesEngine(db, store)

        # Create a simple rule
        rule = Rule(
            project_id=1,
            name="test_coverage_min",
            description="Min 80% test coverage",
            category=RuleCategory.QUALITY,
            rule_type=RuleType.THRESHOLD,
            condition='{"test_coverage": {"$gte": 80}}',
            severity=SeverityLevel.ERROR,
        )
        created_rule = store.create_rule(rule)

        # Validate task with context that passes the rule
        result = engine.validate_task(
            task_id=1,
            project_id=1,
            context={"test_coverage": 85},
        )
        assert result.is_compliant
        assert result.violation_count == 0

    def test_task_violates_rule(self, tmp_path):
        """Test validating a task that violates a rule."""
        db = Database(tmp_path / "test.db")
        store = RulesStore(db)
        engine = RulesEngine(db, store)

        # Create a rule
        rule = Rule(
            project_id=1,
            name="test_coverage_min",
            description="Min 80% test coverage",
            category=RuleCategory.QUALITY,
            rule_type=RuleType.THRESHOLD,
            condition='{"test_coverage": {"$gte": 80}}',
            severity=SeverityLevel.ERROR,
        )
        store.create_rule(rule)

        # Validate task with context that violates the rule
        result = engine.validate_task(
            task_id=1,
            project_id=1,
            context={"test_coverage": 50},
        )
        assert not result.is_compliant
        assert result.violation_count == 1
        assert len(result.violations) == 1
        assert "test_coverage" in result.violations[0]["rule_name"]

    def test_multiple_rule_violations(self, tmp_path):
        """Test validating against multiple rules."""
        db = Database(tmp_path / "test.db")
        store = RulesStore(db)
        engine = RulesEngine(db, store)

        # Create multiple rules
        rules = [
            Rule(
                project_id=1,
                name="test_coverage_min",
                description="Min 80%",
                category=RuleCategory.QUALITY,
                rule_type=RuleType.THRESHOLD,
                condition='{"test_coverage": {"$gte": 80}}',
                severity=SeverityLevel.ERROR,
            ),
            Rule(
                project_id=1,
                name="code_review_required",
                description="Code must be reviewed",
                category=RuleCategory.QUALITY,
                rule_type=RuleType.CONSTRAINT,
                condition='{"has_code_review": {"$eq": True}}',
                severity=SeverityLevel.ERROR,
            ),
        ]
        for rule in rules:
            store.create_rule(rule)

        # Validate task with violations on both rules
        result = engine.validate_task(
            task_id=1,
            project_id=1,
            context={"test_coverage": 50, "has_code_review": False},
        )
        assert not result.is_compliant
        assert result.violation_count == 2


class TestWeek13SuggestionsEngine:
    """Test suggestion generation for rule violations."""

    def test_get_suggestions_no_violations(self, tmp_path):
        """Test getting suggestions when there are no violations."""
        db = Database(tmp_path / "test.db")
        store = RulesStore(db)
        engine = RulesEngine(db, store)
        suggestions_engine = SuggestionsEngine(engine)

        # Create a rule
        rule = Rule(
            project_id=1,
            name="test_coverage_min",
            description="Min 80%",
            category=RuleCategory.QUALITY,
            rule_type=RuleType.THRESHOLD,
            condition='{"test_coverage": {"$gte": 80}}',
            severity=SeverityLevel.ERROR,
        )
        store.create_rule(rule)

        # Validate compliant task
        result = engine.validate_task(1, 1, {"test_coverage": 85})
        suggestions = suggestions_engine.suggest_fixes(result.violations)
        assert len(suggestions) == 0

    def test_get_suggestions_with_violations(self, tmp_path):
        """Test getting suggestions for violations."""
        db = Database(tmp_path / "test.db")
        store = RulesStore(db)
        engine = RulesEngine(db, store)
        suggestions_engine = SuggestionsEngine(engine)

        # Create a rule
        rule = Rule(
            project_id=1,
            name="test_coverage_min",
            description="Min 80% test coverage",
            category=RuleCategory.QUALITY,
            rule_type=RuleType.THRESHOLD,
            condition='{"test_coverage": {"$gte": 80}}',
            severity=SeverityLevel.ERROR,
        )
        store.create_rule(rule)

        # Validate non-compliant task
        result = engine.validate_task(1, 1, {"test_coverage": 50})
        assert len(result.violations) > 0

        suggestions = suggestions_engine.suggest_fixes(result.violations)
        assert len(suggestions) > 0
        # Check that suggestions mention test coverage
        assert any("coverage" in s.lower() for s in suggestions)


class TestWeek13RuleOverrides:
    """Test rule override functionality."""

    def test_override_rule(self, tmp_path):
        """Test overriding a rule violation."""
        db = Database(tmp_path / "test.db")
        store = RulesStore(db)
        engine = RulesEngine(db, store)

        # Create a rule with override allowed
        rule = Rule(
            project_id=1,
            name="test_coverage_min",
            description="Min 80%",
            category=RuleCategory.QUALITY,
            rule_type=RuleType.THRESHOLD,
            condition='{"test_coverage": {"$gte": 80}}',
            severity=SeverityLevel.ERROR,
            can_override=True,
        )
        created_rule = store.create_rule(rule)

        # Validate without override (should fail)
        result = engine.validate_task(1, 1, {"test_coverage": 50})
        assert not result.is_compliant

        # Create override
        from src.memory_mcp.rules.models import RuleOverride
        override = RuleOverride(
            project_id=1,
            rule_id=created_rule.id,
            task_id=1,
            overridden_by="test_user",
            justification="Approved by product team",
        )
        store.create_override(override)

        # Validate with override (should pass)
        result = engine.validate_task(1, 1, {"test_coverage": 50})
        assert result.is_compliant


class TestWeek13Phase7Integration:
    """Test integration with Phase 7 planning."""

    def test_optimize_plan_with_rule_validation(self, tmp_path):
        """Test that optimize_plan includes rule validation."""
        db = Database(tmp_path / "test.db")
        store = RulesStore(db)
        engine = RulesEngine(db, store)

        # Create a rule
        rule = Rule(
            project_id=1,
            name="test_coverage_min",
            description="Min 80%",
            category=RuleCategory.QUALITY,
            rule_type=RuleType.THRESHOLD,
            condition='{"test_coverage": {"$gte": 80}}',
            severity=SeverityLevel.ERROR,
        )
        store.create_rule(rule)

        # Validate with low test coverage
        result = engine.validate_task(1, 1, {"test_coverage": 50})

        # Verify rule violation is detected
        assert not result.is_compliant
        assert result.violation_count > 0


class TestWeek13EndToEnd:
    """End-to-end workflow tests."""

    def test_complete_workflow_quality_gates(self, tmp_path):
        """Test complete workflow: rules -> validation -> suggestions -> override."""
        db = Database(tmp_path / "test.db")

        # Step 1: Create rules from template
        quality_rules = RuleTemplates.quality_gates()
        assert len(quality_rules) > 0

        # Step 2: Store rules
        store = RulesStore(db)
        test_coverage_rule = next(
            r for r in quality_rules if r.name == "min_test_coverage"
        )
        test_coverage_rule.project_id = 1
        created_rule = store.create(test_coverage_rule)

        # Step 3: Validate task
        engine = RulesEngine(db, store)
        result = engine.validate_task(1, 1, {"test_coverage": 75})
        assert not result.is_compliant
        assert result.violation_count == 1

        # Step 4: Get suggestions
        suggestions_engine = SuggestionsEngine(engine)
        suggestions = suggestions_engine.suggest_fixes(result.violations)
        assert len(suggestions) > 0

        # Step 5: Override rule
        from src.memory_mcp.rules.models import RuleOverride
        override = RuleOverride(
            project_id=1,
            rule_id=created_rule.id,
            task_id=1,
            overridden_by="developer",
            justification="Legacy code, gradually improving coverage",
        )
        store.create_override(override)

        # Step 6: Validate again (should pass with override)
        result = engine.validate_task(1, 1, {"test_coverage": 75})
        assert result.is_compliant

    def test_template_deployment_workflow(self, tmp_path):
        """Test deployment approval template workflow."""
        db = Database(tmp_path / "test.db")
        store = RulesStore(db)

        # Get deployment rules
        deploy_rules = RuleTemplates.deployment_approval()
        assert len(deploy_rules) > 0

        # Create deployment rules
        for rule in deploy_rules:
            rule.project_id = 1
            store.create_rule(rule)

        # Validate pre-deployment
        engine = RulesEngine(db, store)
        result = engine.validate_task(
            1, 1,
            {
                "security_reviewed": False,
                "staging_tests_passed": False,
                "has_rollback_plan": False,
            }
        )

        # Should have violations
        assert not result.is_compliant
        assert result.violation_count > 0

        # Suggest fixes
        suggestions_engine = SuggestionsEngine(engine)
        suggestions = suggestions_engine.suggest_fixes(result.violations)
        assert len(suggestions) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
