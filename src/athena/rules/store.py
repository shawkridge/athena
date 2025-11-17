"""Database operations for Phase 9 Project Rules Engine."""

import logging
from typing import Optional, List, Dict, Any
from athena.core.database import Database
from athena.core.base_store import BaseStore
from .models import Rule, RuleTemplate, RuleOverride, ProjectRuleConfig

logger = logging.getLogger(__name__)


class RulesStore(BaseStore):
    """Handles all database operations for rules."""

    table_name = "project_rules"
    model_class = Rule

    def __init__(self, db: Database):
        """Initialize RulesStore.

        Args:
            db: Database instance
        """
        super().__init__(db)
    def _row_to_model(self, row: Dict[str, Any]) -> Optional[Rule]:
        """Convert database row to Rule model.

        RulesStore manages multiple models, so this dispatcher returns the primary model.
        """
        if not row or "name" not in row:
            return None
        return self._row_to_rule_dict(row)

    def _ensure_schema(self):
        """Ensure all required tables exist."""
        cursor = self.db.get_cursor()

        # Check if tables already exist
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema='public' AND table_name='project_rules'
        """)
        if cursor.fetchone() is None:
            logger.warning(
                "project_rules table not found. "
                "Run migrations with: python -m athena.migrations.runner <db_path>"
            )

    def create_rule(self, rule: Rule) -> Rule:
        """Create new rule.

        Args:
            rule: Rule to create

        Returns:
            Rule with ID populated

        Raises:
            ValueError: If rule with same name already exists for project
        """
        try:
            result = self.execute("""
                INSERT INTO project_rules (
                    project_id, name, description, category, rule_type, severity,
                    condition, exception_condition, created_at, updated_at,
                    created_by, enabled, auto_block, can_override,
                    override_requires_approval, tags, related_rules, documentation_url
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                rule.project_id,
                rule.name,
                rule.description,
                rule.category,
                rule.rule_type,
                rule.severity,
                rule.condition,
                rule.exception_condition,
                rule.created_at,
                rule.updated_at,
                rule.created_by,
                int(rule.enabled),
                int(rule.auto_block),
                int(rule.can_override),
                int(rule.override_requires_approval),
                self.serialize_json(rule.tags),
                self.serialize_json(rule.related_rules),
                rule.documentation_url,
            ), fetch_one=True)

            self.commit()
            rule.id = result[0] if result else None
            return rule

        except Exception as e:
            raise ValueError(f"Failed to create rule: {e}") from e

    def update_rule(self, rule: Rule) -> bool:
        """Update existing rule.

        Args:
            rule: Rule to update (must have id)

        Returns:
            True if updated, False if not found
        """
        if rule.id is None:
            raise ValueError("Rule must have ID to update")

        try:
            cursor = self.execute("""
                UPDATE project_rules SET
                    name = ?, description = ?, category = ?, rule_type = ?,
                    severity = ?, condition = ?, exception_condition = ?,
                    updated_at = ?, created_by = ?, enabled = ?,
                    auto_block = ?, can_override = ?,
                    override_requires_approval = ?, tags = ?,
                    related_rules = ?, documentation_url = ?
                WHERE id = ? AND project_id = ?
            """, (
                rule.name,
                rule.description,
                rule.category,
                rule.rule_type,
                rule.severity,
                rule.condition,
                rule.exception_condition,
                rule.updated_at,
                rule.created_by,
                int(rule.enabled),
                int(rule.auto_block),
                int(rule.can_override),
                int(rule.override_requires_approval),
                self.serialize_json(rule.tags),
                self.serialize_json(rule.related_rules),
                rule.documentation_url,
                rule.id,
                rule.project_id,
            ))

            self.commit()
            return cursor.rowcount > 0

        except Exception as e:
            raise ValueError(f"Failed to update rule: {e}") from e

    def get_rule(self, rule_id: int) -> Optional[Rule]:
        """Get single rule by ID.

        Args:
            rule_id: Rule ID

        Returns:
            Rule or None if not found
        """
        row = self.execute("""
            SELECT id, project_id, name, description, category, rule_type,
                   severity, condition, exception_condition, created_at, updated_at,
                   created_by, enabled, auto_block, can_override,
                   override_requires_approval, tags, related_rules, documentation_url
            FROM project_rules
            WHERE id = ?
        """, (rule_id,), fetch_one=True)

        if row is None:
            return None

        col_names = ["id", "project_id", "name", "description", "category", "rule_type", "severity", "condition", "exception_condition", "created_at", "updated_at", "created_by", "enabled", "auto_block", "can_override", "override_requires_approval", "tags", "related_rules", "documentation_url"]
        return self._row_to_rule_dict(dict(zip(col_names, row)))

    def list_rules(self, project_id: int, enabled_only: bool = True) -> List[Rule]:
        """Get all rules for project.

        Args:
            project_id: Project ID
            enabled_only: If True, only return enabled rules

        Returns:
            List of Rule objects
        """
        query = """
            SELECT id, project_id, name, description, category, rule_type,
                   severity, condition, exception_condition, created_at, updated_at,
                   created_by, enabled, auto_block, can_override,
                   override_requires_approval, tags, related_rules, documentation_url
            FROM project_rules
            WHERE project_id = ?
        """
        params = [project_id]

        if enabled_only:
            query += " AND enabled = 1"

        query += " ORDER BY category, name"

        rows = self.execute(query, params, fetch_all=True)
        col_names = ["id", "project_id", "name", "description", "category", "rule_type", "severity", "condition", "exception_condition", "created_at", "updated_at", "created_by", "enabled", "auto_block", "can_override", "override_requires_approval", "tags", "related_rules", "documentation_url"]
        return [self._row_to_rule_dict(dict(zip(col_names, row))) for row in (rows or [])]

    def list_rules_by_category(self, project_id: int, category: str) -> List[Rule]:
        """Get rules filtered by category.

        Args:
            project_id: Project ID
            category: Rule category

        Returns:
            List of Rule objects
        """
        rows = self.execute("""
            SELECT id, project_id, name, description, category, rule_type,
                   severity, condition, exception_condition, created_at, updated_at,
                   created_by, enabled, auto_block, can_override,
                   override_requires_approval, tags, related_rules, documentation_url
            FROM project_rules
            WHERE project_id = ? AND category = ? AND enabled = 1
            ORDER BY severity DESC, name
        """, (project_id, category), fetch_all=True)

        col_names = ["id", "project_id", "name", "description", "category", "rule_type", "severity", "condition", "exception_condition", "created_at", "updated_at", "created_by", "enabled", "auto_block", "can_override", "override_requires_approval", "tags", "related_rules", "documentation_url"]
        return [self._row_to_rule_dict(dict(zip(col_names, row))) for row in (rows or [])]

    def delete_rule(self, rule_id: int) -> bool:
        """Soft-delete rule (set enabled = 0).

        Args:
            rule_id: Rule ID

        Returns:
            True if deleted, False if not found
        """
        cursor = self.execute("""
            UPDATE project_rules SET enabled = 0 WHERE id = ?
        """, (rule_id,))

        self.commit()
        return cursor.rowcount > 0

    def get_rule_config(self, project_id: int) -> Optional[ProjectRuleConfig]:
        """Get project's rule enforcement config.

        Args:
            project_id: Project ID

        Returns:
            ProjectRuleConfig or None if not found
        """
        row = self.execute("""
            SELECT id, project_id, enforcement_level,
                   auto_suggest_compliant_alternatives, auto_block_violations,
                   require_approval_for_override, min_approvers, approval_ttl_hours,
                   notify_on_violation, notify_channels,
                   auto_generate_rules_from_patterns,
                   confidence_threshold_for_auto_rules, created_at, updated_at
            FROM project_rule_config
            WHERE project_id = ?
        """, (project_id,), fetch_one=True)

        if row is None:
            return None

        col_names = ["id", "project_id", "enforcement_level", "auto_suggest_compliant_alternatives",
                     "auto_block_violations", "require_approval_for_override", "min_approvers",
                     "approval_ttl_hours", "notify_on_violation", "notify_channels",
                     "auto_generate_rules_from_patterns", "confidence_threshold_for_auto_rules",
                     "created_at", "updated_at"]
        return self._row_to_config(dict(zip(col_names, row)))

    def create_or_update_rule_config(self, config: ProjectRuleConfig) -> ProjectRuleConfig:
        """Create or update project rule configuration.

        Args:
            config: ProjectRuleConfig

        Returns:
            Updated config with ID
        """
        try:
            existing = self.get_rule_config(config.project_id)

            if existing:
                self.execute("""
                    UPDATE project_rule_config SET
                        enforcement_level = ?, auto_suggest_compliant_alternatives = ?,
                        auto_block_violations = ?, require_approval_for_override = ?,
                        min_approvers = ?, approval_ttl_hours = ?,
                        notify_on_violation = ?, notify_channels = ?,
                        auto_generate_rules_from_patterns = ?,
                        confidence_threshold_for_auto_rules = ?, updated_at = ?
                    WHERE project_id = ?
                """, (
                    config.enforcement_level,
                    int(config.auto_suggest_compliant_alternatives),
                    int(config.auto_block_violations),
                    int(config.require_approval_for_override),
                    config.min_approvers,
                    config.approval_ttl_hours,
                    int(config.notify_on_violation),
                    self.serialize_json(config.notify_channels),
                    int(config.auto_generate_rules_from_patterns),
                    config.confidence_threshold_for_auto_rules,
                    config.updated_at,
                    config.project_id,
                ))
                config.id = existing.id
            else:
                result = self.execute("""
                    INSERT INTO project_rule_config (
                        project_id, enforcement_level,
                        auto_suggest_compliant_alternatives, auto_block_violations,
                        require_approval_for_override, min_approvers,
                        approval_ttl_hours, notify_on_violation, notify_channels,
                        auto_generate_rules_from_patterns,
                        confidence_threshold_for_auto_rules, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    config.project_id,
                    config.enforcement_level,
                    int(config.auto_suggest_compliant_alternatives),
                    int(config.auto_block_violations),
                    int(config.require_approval_for_override),
                    config.min_approvers,
                    config.approval_ttl_hours,
                    int(config.notify_on_violation),
                    self.serialize_json(config.notify_channels),
                    int(config.auto_generate_rules_from_patterns),
                    config.confidence_threshold_for_auto_rules,
                    config.created_at,
                    config.updated_at,
                ), fetch_one=True)
                config.id = result[0] if result else None

            self.commit()
            return config

        except Exception as e:
            raise ValueError(f"Failed to create/update rule config: {e}") from e

    def record_override(self, override: RuleOverride) -> RuleOverride:
        """Record a rule override with justification.

        Args:
            override: RuleOverride to record

        Returns:
            Override with ID populated
        """
        try:
            result = self.execute("""
                INSERT INTO rule_overrides (
                    project_id, rule_id, task_id, overridden_at,
                    overridden_by, justification, approved_by,
                    approval_at, expires_at, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                override.project_id,
                override.rule_id,
                override.task_id,
                override.overridden_at,
                override.overridden_by,
                override.justification,
                override.approved_by,
                override.approval_at,
                override.expires_at,
                override.status,
            ), fetch_one=True)

            self.commit()
            override.id = result[0] if result else None
            return override

        except Exception as e:
            raise ValueError(f"Failed to record override: {e}") from e

    def get_active_overrides(self, task_id: int) -> List[RuleOverride]:
        """Get active overrides for a task.

        Args:
            task_id: Task ID

        Returns:
            List of active RuleOverride objects
        """
        rows = self.execute("""
            SELECT id, project_id, rule_id, task_id, overridden_at,
                   overridden_by, justification, approved_by,
                   approval_at, expires_at, status
            FROM rule_overrides
            WHERE task_id = ? AND status = 'active'
            ORDER BY overridden_at DESC
        """, (task_id,), fetch_all=True)

        col_names = ["id", "project_id", "rule_id", "task_id", "overridden_at",
                     "overridden_by", "justification", "approved_by", "approval_at",
                     "expires_at", "status"]
        return [self._row_to_override(dict(zip(col_names, row))) for row in (rows or [])]

    def expire_override(self, override_id: int) -> bool:
        """Expire/revoke an override.

        Args:
            override_id: Override ID

        Returns:
            True if expired, False if not found
        """
        cursor = self.execute("""
            UPDATE rule_overrides SET status = 'expired' WHERE id = ?
        """, (override_id,))

        self.commit()
        return cursor.rowcount > 0

    def create_template(self, template: RuleTemplate) -> RuleTemplate:
        """Create reusable rule template.

        Args:
            template: RuleTemplate to create

        Returns:
            Template with ID populated
        """
        try:
            result = self.execute("""
                INSERT INTO rule_templates (
                    name, description, category, rules, usage_count, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                template.name,
                template.description,
                template.category,
                self.serialize_json([rule.model_dump() for rule in template.rules]),
                template.usage_count,
                template.created_at,
            ), fetch_one=True)

            self.commit()
            template.id = result[0] if result else None
            return template

        except Exception as e:
            raise ValueError(f"Failed to create template: {e}") from e

    def get_template(self, template_id: int) -> Optional[RuleTemplate]:
        """Get rule template by ID.

        Args:
            template_id: Template ID

        Returns:
            RuleTemplate or None if not found
        """
        row = self.execute("""
            SELECT id, name, description, category, rules, usage_count, created_at
            FROM rule_templates
            WHERE id = ?
        """, (template_id,), fetch_one=True)

        if row is None:
            return None

        col_names = ["id", "name", "description", "category", "rules", "usage_count", "created_at"]
        return self._row_to_template(dict(zip(col_names, row)))

    def list_templates(self, category: Optional[str] = None) -> List[RuleTemplate]:
        """List all rule templates.

        Args:
            category: Filter by category (optional)

        Returns:
            List of RuleTemplate objects
        """
        query = """
            SELECT id, name, description, category, rules, usage_count, created_at
            FROM rule_templates
        """
        params = []

        if category:
            query += " WHERE category = ?"
            params.append(category)
            query += " ORDER BY name"
        else:
            query += " ORDER BY category, name"

        rows = self.execute(query, params, fetch_all=True)
        col_names = ["id", "name", "description", "category", "rules", "usage_count", "created_at"]
        return [self._row_to_template(dict(zip(col_names, row))) for row in (rows or [])]

    def _row_to_rule_dict(self, row: Dict[str, Any]) -> Rule:
        """Convert database row dict to Rule object."""
        import json
        from athena.core.error_handling import safe_json_loads

        # Handle tags and related_rules as lists
        tags_json = row.get("tags")
        tags = safe_json_loads(tags_json, []) if tags_json else []
        if not isinstance(tags, list):
            tags = []

        related_rules_json = row.get("related_rules")
        related_rules = safe_json_loads(related_rules_json, []) if related_rules_json else []
        if not isinstance(related_rules, list):
            related_rules = []

        return Rule(
            id=row.get("id"),
            project_id=row.get("project_id"),
            name=row.get("name"),
            description=row.get("description"),
            category=row.get("category"),
            rule_type=row.get("rule_type"),
            severity=row.get("severity"),
            condition=row.get("condition"),
            exception_condition=row.get("exception_condition"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
            created_by=row.get("created_by"),
            enabled=bool(row.get("enabled", False)),
            auto_block=bool(row.get("auto_block", False)),
            can_override=bool(row.get("can_override", False)),
            override_requires_approval=bool(row.get("override_requires_approval", False)),
            tags=tags,
            related_rules=related_rules,
            documentation_url=row.get("documentation_url"),
        )

    def _row_to_config(self, row: Dict[str, Any]) -> ProjectRuleConfig:
        """Convert database row dict to ProjectRuleConfig object."""
        from athena.core.error_handling import safe_json_loads

        # Handle notify_channels as list
        notify_channels_json = row.get("notify_channels")
        notify_channels = safe_json_loads(notify_channels_json, []) if notify_channels_json else []
        if not isinstance(notify_channels, list):
            notify_channels = []

        return ProjectRuleConfig(
            id=row.get("id"),
            project_id=row.get("project_id"),
            enforcement_level=row.get("enforcement_level"),
            auto_suggest_compliant_alternatives=bool(row.get("auto_suggest_compliant_alternatives", False)),
            auto_block_violations=bool(row.get("auto_block_violations", False)),
            require_approval_for_override=bool(row.get("require_approval_for_override", False)),
            min_approvers=row.get("min_approvers"),
            approval_ttl_hours=row.get("approval_ttl_hours"),
            notify_on_violation=bool(row.get("notify_on_violation", False)),
            notify_channels=notify_channels,
            auto_generate_rules_from_patterns=bool(row.get("auto_generate_rules_from_patterns", False)),
            confidence_threshold_for_auto_rules=row.get("confidence_threshold_for_auto_rules"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def _row_to_override(self, row: Dict[str, Any]) -> RuleOverride:
        """Convert database row dict to RuleOverride object."""
        return RuleOverride(
            id=row.get("id"),
            project_id=row.get("project_id"),
            rule_id=row.get("rule_id"),
            task_id=row.get("task_id"),
            overridden_at=row.get("overridden_at"),
            overridden_by=row.get("overridden_by"),
            justification=row.get("justification"),
            approved_by=row.get("approved_by"),
            approval_at=row.get("approval_at"),
            expires_at=row.get("expires_at"),
            status=row.get("status"),
        )

    def _row_to_template(self, row: Dict[str, Any]) -> RuleTemplate:
        """Convert database row dict to RuleTemplate object."""
        from athena.core.error_handling import safe_json_loads

        # Handle rules as list
        rules_json = row.get("rules")
        rules_data = safe_json_loads(rules_json, []) if rules_json else []
        if not isinstance(rules_data, list):
            rules_data = []

        rules = [Rule(**rule_dict) for rule_dict in rules_data]

        return RuleTemplate(
            id=row.get("id"),
            name=row.get("name"),
            description=row.get("description"),
            category=row.get("category"),
            rules=rules,
            usage_count=row.get("usage_count"),
            created_at=row.get("created_at"),
        )
