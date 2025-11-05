"""Unit tests for RulesStore in Phase 9."""

import pytest
import sys
from pathlib import Path
from athena.core.database import Database

# Add migrations to path
migrations_path = Path(__file__).parent.parent.parent / "migrations"
sys.path.insert(0, str(migrations_path))

from runner import MigrationRunner
from athena.rules.store import RulesStore
from athena.rules.models import (
    Rule,
    RuleCategory,
    RuleType,
    SeverityLevel,
    RuleTemplate,
    RuleOverride,
    ProjectRuleConfig,
)


@pytest.fixture
def test_db(tmp_path):
    """Create test database with schema."""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))

    # Run migration to create schema
    migrations_dir = Path(__file__).parent.parent.parent / "migrations"
    migration_file = migrations_dir / "006_phase9_rules_schema.sql"

    runner = MigrationRunner(str(db_path))
    runner.apply_migration(str(migration_file))

    return db


@pytest.fixture
def store(test_db):
    """Create RulesStore instance."""
    return RulesStore(test_db)


class TestRulesStoreCreate:
    """Test creating rules."""

    def test_create_rule(self, store):
        """Test creating a rule."""
        rule = Rule(
            project_id=1,
            name="test_rule",
            description="Test rule",
            category=RuleCategory.SECURITY,
            rule_type=RuleType.CONSTRAINT,
            condition='{"field": "value"}',
        )

        created = store.create_rule(rule)
        assert created.id is not None
        assert created.project_id == 1
        assert created.name == "test_rule"

    def test_create_rule_with_all_fields(self, store):
        """Test creating rule with all fields."""
        rule = Rule(
            project_id=1,
            name="complete_rule",
            description="Complete rule",
            category=RuleCategory.DEPLOYMENT,
            rule_type=RuleType.APPROVAL,
            severity=SeverityLevel.CRITICAL,
            condition="condition",
            exception_condition="exception",
            created_by="test_user",
            enabled=False,
            auto_block=False,
            can_override=False,
            override_requires_approval=True,
            tags=["important", "security"],
            related_rules=[1, 2],
            documentation_url="https://example.com",
        )

        created = store.create_rule(rule)
        assert created.id is not None
        assert created.severity == SeverityLevel.CRITICAL
        assert created.tags == ["important", "security"]
        assert created.related_rules == [1, 2]

    def test_create_duplicate_rule_fails(self, store):
        """Test creating duplicate rule fails."""
        rule1 = Rule(
            project_id=1,
            name="duplicate",
            description="First",
            category=RuleCategory.QUALITY,
            rule_type=RuleType.THRESHOLD,
            condition="condition1",
        )

        store.create_rule(rule1)

        # Try to create rule with same project_id and name
        rule2 = Rule(
            project_id=1,
            name="duplicate",
            description="Second",
            category=RuleCategory.SECURITY,
            rule_type=RuleType.CONSTRAINT,
            condition="condition2",
        )

        with pytest.raises(ValueError):
            store.create_rule(rule2)

    def test_create_rule_same_name_different_project(self, store):
        """Test creating rule with same name in different project."""
        rule1 = Rule(
            project_id=1,
            name="rule",
            description="Project 1",
            category=RuleCategory.SECURITY,
            rule_type=RuleType.CONSTRAINT,
            condition="condition",
        )

        rule2 = Rule(
            project_id=2,
            name="rule",
            description="Project 2",
            category=RuleCategory.SECURITY,
            rule_type=RuleType.CONSTRAINT,
            condition="condition",
        )

        created1 = store.create_rule(rule1)
        created2 = store.create_rule(rule2)

        assert created1.id != created2.id
        assert created1.project_id == 1
        assert created2.project_id == 2


class TestRulesStoreRead:
    """Test reading rules."""

    def test_get_rule(self, store):
        """Test getting rule by ID."""
        rule = Rule(
            project_id=1,
            name="test_rule",
            description="Test",
            category=RuleCategory.SECURITY,
            rule_type=RuleType.CONSTRAINT,
            condition="condition",
        )

        created = store.create_rule(rule)
        retrieved = store.get_rule(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "test_rule"

    def test_get_nonexistent_rule(self, store):
        """Test getting nonexistent rule."""
        retrieved = store.get_rule(999)
        assert retrieved is None

    def test_list_rules(self, store):
        """Test listing all rules for project."""
        rule1 = Rule(
            project_id=1,
            name="rule1",
            description="Test 1",
            category=RuleCategory.SECURITY,
            rule_type=RuleType.CONSTRAINT,
            condition="condition1",
        )

        rule2 = Rule(
            project_id=1,
            name="rule2",
            description="Test 2",
            category=RuleCategory.QUALITY,
            rule_type=RuleType.THRESHOLD,
            condition="condition2",
        )

        rule3 = Rule(
            project_id=2,
            name="rule3",
            description="Test 3",
            category=RuleCategory.SECURITY,
            rule_type=RuleType.CONSTRAINT,
            condition="condition3",
        )

        store.create_rule(rule1)
        store.create_rule(rule2)
        store.create_rule(rule3)

        rules = store.list_rules(1)
        assert len(rules) == 2
        assert all(r.project_id == 1 for r in rules)

    def test_list_rules_enabled_only(self, store):
        """Test listing only enabled rules."""
        rule1 = Rule(
            project_id=1,
            name="rule1",
            description="Test 1",
            category=RuleCategory.SECURITY,
            rule_type=RuleType.CONSTRAINT,
            condition="condition1",
            enabled=True,
        )

        rule2 = Rule(
            project_id=1,
            name="rule2",
            description="Test 2",
            category=RuleCategory.SECURITY,
            rule_type=RuleType.CONSTRAINT,
            condition="condition2",
            enabled=False,
        )

        store.create_rule(rule1)
        store.create_rule(rule2)

        enabled_rules = store.list_rules(1, enabled_only=True)
        assert len(enabled_rules) == 1
        assert enabled_rules[0].name == "rule1"

        all_rules = store.list_rules(1, enabled_only=False)
        assert len(all_rules) == 2

    def test_list_rules_by_category(self, store):
        """Test listing rules by category."""
        rule1 = Rule(
            project_id=1,
            name="rule1",
            description="Test 1",
            category=RuleCategory.SECURITY,
            rule_type=RuleType.CONSTRAINT,
            condition="condition1",
        )

        rule2 = Rule(
            project_id=1,
            name="rule2",
            description="Test 2",
            category=RuleCategory.QUALITY,
            rule_type=RuleType.THRESHOLD,
            condition="condition2",
        )

        store.create_rule(rule1)
        store.create_rule(rule2)

        security_rules = store.list_rules_by_category(1, RuleCategory.SECURITY)
        assert len(security_rules) == 1
        assert security_rules[0].category == RuleCategory.SECURITY


class TestRulesStoreUpdate:
    """Test updating rules."""

    def test_update_rule(self, store):
        """Test updating a rule."""
        rule = Rule(
            project_id=1,
            name="original",
            description="Original",
            category=RuleCategory.SECURITY,
            rule_type=RuleType.CONSTRAINT,
            condition="condition1",
        )

        created = store.create_rule(rule)
        created.description = "Updated"
        created.condition = "condition2"

        success = store.update_rule(created)
        assert success is True

        retrieved = store.get_rule(created.id)
        assert retrieved.description == "Updated"
        assert retrieved.condition == "condition2"

    def test_update_nonexistent_rule(self, store):
        """Test updating nonexistent rule."""
        rule = Rule(
            project_id=1,
            name="test",
            description="Test",
            category=RuleCategory.SECURITY,
            rule_type=RuleType.CONSTRAINT,
            condition="condition",
            id=999,
        )

        success = store.update_rule(rule)
        assert success is False

    def test_update_rule_without_id_fails(self, store):
        """Test updating rule without ID fails."""
        rule = Rule(
            project_id=1,
            name="test",
            description="Test",
            category=RuleCategory.SECURITY,
            rule_type=RuleType.CONSTRAINT,
            condition="condition",
        )

        with pytest.raises(ValueError):
            store.update_rule(rule)


class TestRulesStoreDelete:
    """Test deleting rules."""

    def test_delete_rule(self, store):
        """Test soft-deleting a rule."""
        rule = Rule(
            project_id=1,
            name="test_rule",
            description="Test",
            category=RuleCategory.SECURITY,
            rule_type=RuleType.CONSTRAINT,
            condition="condition",
        )

        created = store.create_rule(rule)
        success = store.delete_rule(created.id)
        assert success is True

        # Rule should no longer be in enabled_only list
        rules = store.list_rules(1, enabled_only=True)
        assert len(rules) == 0

        # But should still exist in database (soft delete)
        retrieved = store.get_rule(created.id)
        assert retrieved is not None
        assert retrieved.enabled is False

    def test_delete_nonexistent_rule(self, store):
        """Test deleting nonexistent rule."""
        success = store.delete_rule(999)
        assert success is False


class TestProjectRuleConfig:
    """Test project rule configuration."""

    def test_create_rule_config(self, store):
        """Test creating rule config."""
        config = ProjectRuleConfig(project_id=1)
        created = store.create_or_update_rule_config(config)

        assert created.id is not None
        assert created.project_id == 1
        assert created.enforcement_level == SeverityLevel.WARNING

    def test_get_rule_config(self, store):
        """Test getting rule config."""
        config = ProjectRuleConfig(project_id=1)
        store.create_or_update_rule_config(config)

        retrieved = store.get_rule_config(1)
        assert retrieved is not None
        assert retrieved.project_id == 1

    def test_get_nonexistent_config(self, store):
        """Test getting nonexistent config."""
        retrieved = store.get_rule_config(999)
        assert retrieved is None

    def test_update_rule_config(self, store):
        """Test updating rule config."""
        config = ProjectRuleConfig(
            project_id=1,
            enforcement_level=SeverityLevel.WARNING,
        )
        created = store.create_or_update_rule_config(config)

        config.enforcement_level = SeverityLevel.ERROR
        updated = store.create_or_update_rule_config(config)

        assert updated.id == created.id
        retrieved = store.get_rule_config(1)
        assert retrieved.enforcement_level == SeverityLevel.ERROR


class TestRuleOverrides:
    """Test rule overrides."""

    def test_create_override(self, store):
        """Test creating override."""
        override = RuleOverride(
            project_id=1,
            rule_id=1,
            task_id=1,
            overridden_by="user",
            justification="Test override",
        )

        created = store.record_override(override)
        assert created.id is not None
        assert created.status == "active"

    def test_get_active_overrides(self, store):
        """Test getting active overrides."""
        override1 = RuleOverride(
            project_id=1,
            rule_id=1,
            task_id=1,
            overridden_by="user1",
            justification="Override 1",
        )

        override2 = RuleOverride(
            project_id=1,
            rule_id=2,
            task_id=1,
            overridden_by="user2",
            justification="Override 2",
            status="expired",
        )

        store.record_override(override1)
        store.record_override(override2)

        active = store.get_active_overrides(1)
        assert len(active) == 1
        assert active[0].rule_id == 1

    def test_expire_override(self, store):
        """Test expiring override."""
        override = RuleOverride(
            project_id=1,
            rule_id=1,
            task_id=1,
            overridden_by="user",
            justification="Override",
        )

        created = store.record_override(override)
        success = store.expire_override(created.id)
        assert success is True

        retrieved = store.get_active_overrides(1)
        assert len(retrieved) == 0


class TestRuleTemplates:
    """Test rule templates."""

    def test_create_template(self, store):
        """Test creating template."""
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
            description="Web service template",
            category="web_api",
            rules=rules,
        )

        created = store.create_template(template)
        assert created.id is not None
        assert created.name == "WebService"

    def test_get_template(self, store):
        """Test getting template."""
        rules = [
            Rule(
                project_id=1,
                name="rule1",
                description="Rule 1",
                category=RuleCategory.SECURITY,
                rule_type=RuleType.CONSTRAINT,
                condition="condition",
            )
        ]

        template = RuleTemplate(
            name="WebService",
            description="Template",
            category="web_api",
            rules=rules,
        )

        created = store.create_template(template)
        retrieved = store.get_template(created.id)

        assert retrieved is not None
        assert retrieved.name == "WebService"
        assert len(retrieved.rules) == 1

    def test_list_templates(self, store):
        """Test listing templates."""
        template1 = RuleTemplate(
            name="WebService",
            description="Web template",
            category="web_api",
            rules=[],
        )

        template2 = RuleTemplate(
            name="DataPipeline",
            description="Data template",
            category="data_pipeline",
            rules=[],
        )

        store.create_template(template1)
        store.create_template(template2)

        templates = store.list_templates()
        assert len(templates) == 2

    def test_list_templates_by_category(self, store):
        """Test listing templates by category."""
        template1 = RuleTemplate(
            name="WebService",
            description="Web template",
            category="web_api",
            rules=[],
        )

        template2 = RuleTemplate(
            name="DataPipeline",
            description="Data template",
            category="data_pipeline",
            rules=[],
        )

        store.create_template(template1)
        store.create_template(template2)

        web_templates = store.list_templates("web_api")
        assert len(web_templates) == 1
        assert web_templates[0].name == "WebService"
