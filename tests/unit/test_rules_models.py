"""Unit tests for Phase 9 Rules Engine models."""

import pytest
from athena.rules.models import (
    Rule,
    RuleCategory,
    RuleType,
    SeverityLevel,
    RuleTemplate,
    RuleValidationResult,
    RuleOverride,
    ProjectRuleConfig,
)


class TestRuleModel:
    """Test Rule model."""

    def test_create_rule_with_defaults(self):
        """Test creating rule with default values."""
        rule = Rule(
            project_id=1,
            name="test_rule",
            description="Test rule",
            category=RuleCategory.CODING_STANDARD,
            rule_type=RuleType.CONSTRAINT,
            condition='{"field": "value"}',
        )

        assert rule.project_id == 1
        assert rule.name == "test_rule"
        assert rule.severity == SeverityLevel.WARNING
        assert rule.enabled is True
        assert rule.auto_block is True
        assert rule.can_override is True
        assert rule.id is None

    def test_rule_serialization(self):
        """Test rule serialization to dict."""
        rule = Rule(
            project_id=1,
            name="test_rule",
            description="Test rule",
            category=RuleCategory.SECURITY,
            rule_type=RuleType.CONSTRAINT,
            condition='{"field": "value"}',
            severity=SeverityLevel.CRITICAL,
            tags=["important", "security"],
        )

        data = rule.model_dump()
        assert data["project_id"] == 1
        assert data["name"] == "test_rule"
        assert data["severity"] == "critical"
        assert data["tags"] == ["important", "security"]

    def test_rule_with_exception_condition(self):
        """Test rule with exception condition."""
        rule = Rule(
            project_id=1,
            name="deployment_rule",
            description="No Friday deploys",
            category=RuleCategory.DEPLOYMENT,
            rule_type=RuleType.SCHEDULE,
            condition='{"day_of_week": 5}',
            exception_condition='{"environment": "test"}',
            severity=SeverityLevel.ERROR,
        )

        assert rule.exception_condition == '{"environment": "test"}'

    def test_rule_with_related_rules(self):
        """Test rule with related rules."""
        rule = Rule(
            project_id=1,
            name="parent_rule",
            description="Parent rule",
            category=RuleCategory.PROCESS,
            rule_type=RuleType.CONSTRAINT,
            condition="condition",
            related_rules=[2, 3, 4],
        )

        assert rule.related_rules == [2, 3, 4]

    def test_rule_all_categories(self):
        """Test all rule categories."""
        categories = [
            RuleCategory.CODING_STANDARD,
            RuleCategory.PROCESS,
            RuleCategory.SECURITY,
            RuleCategory.DEPLOYMENT,
            RuleCategory.RESOURCE,
            RuleCategory.QUALITY,
            RuleCategory.CUSTOM,
        ]

        for category in categories:
            rule = Rule(
                project_id=1,
                name=f"rule_{category}",
                description="Test",
                category=category,
                rule_type=RuleType.CONSTRAINT,
                condition="condition",
            )
            assert rule.category == category

    def test_rule_all_types(self):
        """Test all rule types."""
        types = [
            RuleType.CONSTRAINT,
            RuleType.PATTERN,
            RuleType.THRESHOLD,
            RuleType.APPROVAL,
            RuleType.SCHEDULE,
            RuleType.DEPENDENCY,
            RuleType.CUSTOM,
        ]

        for rule_type in types:
            rule = Rule(
                project_id=1,
                name=f"rule_{rule_type}",
                description="Test",
                category=RuleCategory.CUSTOM,
                rule_type=rule_type,
                condition="condition",
            )
            assert rule.rule_type == rule_type

    def test_rule_all_severities(self):
        """Test all severity levels."""
        severities = [
            SeverityLevel.INFO,
            SeverityLevel.WARNING,
            SeverityLevel.ERROR,
            SeverityLevel.CRITICAL,
        ]

        for severity in severities:
            rule = Rule(
                project_id=1,
                name=f"rule_{severity}",
                description="Test",
                category=RuleCategory.CUSTOM,
                rule_type=RuleType.CONSTRAINT,
                condition="condition",
                severity=severity,
            )
            assert rule.severity == severity


class TestRuleTemplate:
    """Test RuleTemplate model."""

    def test_create_template_with_rules(self):
        """Test creating template with rules."""
        rules = [
            Rule(
                project_id=1,
                name="rule1",
                description="Rule 1",
                category=RuleCategory.SECURITY,
                rule_type=RuleType.CONSTRAINT,
                condition="condition1",
            ),
            Rule(
                project_id=1,
                name="rule2",
                description="Rule 2",
                category=RuleCategory.QUALITY,
                rule_type=RuleType.THRESHOLD,
                condition="condition2",
            ),
        ]

        template = RuleTemplate(
            name="WebService",
            description="Rules for web services",
            category="web_api",
            rules=rules,
        )

        assert template.name == "WebService"
        assert len(template.rules) == 2
        assert template.usage_count == 0

    def test_template_serialization(self):
        """Test template serialization."""
        rules = [
            Rule(
                project_id=1,
                name="rule1",
                description="Rule 1",
                category=RuleCategory.SECURITY,
                rule_type=RuleType.CONSTRAINT,
                condition="condition1",
            )
        ]

        template = RuleTemplate(
            name="WebService",
            description="Template",
            category="web_api",
            rules=rules,
        )

        data = template.model_dump()
        assert data["name"] == "WebService"
        assert len(data["rules"]) == 1


class TestRuleValidationResult:
    """Test RuleValidationResult model."""

    def test_compliant_result(self):
        """Test creating compliant validation result."""
        result = RuleValidationResult(
            task_id=1,
            project_id=1,
            is_compliant=True,
            violation_count=0,
            warning_count=0,
        )

        assert result.is_compliant is True
        assert result.violation_count == 0
        assert len(result.violations) == 0
        assert len(result.blocking_violations) == 0

    def test_violation_result(self):
        """Test creating violation result."""
        violations = [
            {
                "rule_id": 1,
                "rule_name": "test_rule",
                "severity": "error",
                "message": "Test violation",
            }
        ]

        result = RuleValidationResult(
            task_id=1,
            project_id=1,
            is_compliant=False,
            violation_count=1,
            warning_count=0,
            violations=violations,
            blocking_violations=[1],
        )

        assert result.is_compliant is False
        assert result.violation_count == 1
        assert len(result.blocking_violations) == 1


class TestRuleOverride:
    """Test RuleOverride model."""

    def test_create_override(self):
        """Test creating rule override."""
        override = RuleOverride(
            project_id=1,
            rule_id=1,
            task_id=1,
            overridden_by="user@example.com",
            justification="Test override",
        )

        assert override.status == "active"
        assert override.approved_by is None
        assert override.expires_at is None

    def test_override_with_approval(self):
        """Test override with approval."""
        import time

        override = RuleOverride(
            project_id=1,
            rule_id=1,
            task_id=1,
            overridden_by="user1",
            justification="Override",
            approved_by="user2",
            approval_at=int(time.time()),
        )

        assert override.approved_by == "user2"
        assert override.approval_at is not None


class TestProjectRuleConfig:
    """Test ProjectRuleConfig model."""

    def test_create_config_with_defaults(self):
        """Test creating config with defaults."""
        config = ProjectRuleConfig(project_id=1)

        assert config.project_id == 1
        assert config.enforcement_level == SeverityLevel.WARNING
        assert config.auto_suggest_compliant_alternatives is True
        assert config.auto_block_violations is False
        assert config.require_approval_for_override is False
        assert config.min_approvers == 1
        assert config.approval_ttl_hours == 24
        assert config.notify_on_violation is True

    def test_config_with_custom_settings(self):
        """Test config with custom settings."""
        config = ProjectRuleConfig(
            project_id=1,
            enforcement_level=SeverityLevel.ERROR,
            auto_block_violations=True,
            require_approval_for_override=True,
            min_approvers=2,
            notify_channels=["slack", "email"],
        )

        assert config.enforcement_level == SeverityLevel.ERROR
        assert config.auto_block_violations is True
        assert config.min_approvers == 2
        assert config.notify_channels == ["slack", "email"]


class TestEnumValues:
    """Test enum value serialization."""

    def test_enum_values_in_dict(self):
        """Test that enums serialize to string values."""
        rule = Rule(
            project_id=1,
            name="test",
            description="test",
            category=RuleCategory.SECURITY,
            rule_type=RuleType.CONSTRAINT,
            condition="condition",
            severity=SeverityLevel.ERROR,
        )

        data = rule.model_dump()
        # Should serialize to string values
        assert isinstance(data["category"], str)
        assert isinstance(data["rule_type"], str)
        assert isinstance(data["severity"], str)
