"""Core rules validation engine for Phase 9."""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from athena.core.database import Database
from .models import Rule, RuleValidationResult, RuleOverride
from .store import RulesStore
from .condition_evaluator import ConditionEvaluator

logger = logging.getLogger(__name__)


class RulesEngine:
    """Core rules validation and enforcement engine.

    Handles rule evaluation, violation detection, override management,
    and compliance checking for tasks and plans.
    """

    def __init__(self, db: Database, store: RulesStore = None):
        """Initialize RulesEngine.

        Args:
            db: Database instance
            store: RulesStore instance (created if not provided)
        """
        self.db = db
        self.store = store or RulesStore(db)
        self.evaluator = ConditionEvaluator()
        logger.debug("RulesEngine initialized")

    def validate_task(self, task_id: int, project_id: int, context: Dict[str, Any] = None) -> RuleValidationResult:
        """Validate task against all project rules.

        Checks each rule's condition, handles exceptions, applies overrides,
        and categorizes violations by severity.

        Args:
            task_id: Task ID to validate
            project_id: Project ID
            context: Additional context for rule evaluation (enriched with defaults)

        Returns:
            RuleValidationResult with detailed validation results
        """
        context = context or {}
        context.setdefault("task_id", task_id)
        context.setdefault("project_id", project_id)

        # Get all active rules for project
        rules = self.store.list_rules(project_id, enabled_only=True)
        logger.debug(f"Validating task {task_id} against {len(rules)} rules")

        violations = []
        blocking_violations = []
        suggestions = []
        warning_count = 0
        info_count = 0

        for rule in rules:
            # Check if this rule has an active override for this task
            active_overrides = self.store.get_active_overrides(task_id)
            # Filter to just this rule's overrides
            rule_overrides = [o for o in active_overrides if o.rule_id == rule.id]
            if rule_overrides:
                logger.debug(f"Rule {rule.id} has active override(s), skipping")
                continue

            # Evaluate rule condition
            try:
                if not self.evaluator.evaluate(rule.condition, context):
                    # Condition is False - requirement not met
                    # Check exception condition
                    if rule.exception_condition:
                        if self.evaluator.evaluate(rule.exception_condition, context):
                            # Exception applies, rule doesn't
                            logger.debug(f"Rule {rule.id} exception applies, skipping")
                            continue

                    # No exception, record violation
                    violation = {
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "category": rule.category,
                        "type": rule.rule_type,
                        "severity": rule.severity,
                        "message": rule.description,
                        "suggestion": f"Address: {rule.description}",
                    }

                    violations.append(violation)

                    # Categorize by severity
                    if rule.severity == "critical":
                        blocking_violations.append(rule.id)
                    elif rule.severity == "error":
                        if rule.auto_block:
                            blocking_violations.append(rule.id)
                    elif rule.severity == "warning":
                        warning_count += 1
                    else:  # info
                        info_count += 1

                    logger.debug(f"Rule {rule.id} violation detected: {rule.name}")

            except Exception as e:
                logger.error(f"Error evaluating rule {rule.id}: {e}")
                # Treat evaluation errors as validation errors
                violation = {
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "category": rule.category,
                    "severity": "error",
                    "message": f"Rule evaluation error: {str(e)}",
                    "suggestion": "Check rule condition syntax",
                }
                violations.append(violation)
                blocking_violations.append(rule.id)

        is_compliant = len(blocking_violations) == 0

        result = RuleValidationResult(
            task_id=task_id,
            project_id=project_id,
            is_compliant=is_compliant,
            violation_count=len(violations),
            warning_count=warning_count,
            violations=violations,
            suggestions=suggestions,
            blocking_violations=blocking_violations,
        )

        logger.info(
            f"Task {task_id} validation: compliant={is_compliant}, "
            f"violations={len(violations)}, warnings={warning_count}, blocking={len(blocking_violations)}"
        )

        return result

    def can_execute(self, task_id: int, project_id: int, context: Dict[str, Any] = None) -> Tuple[bool, str]:
        """Quick check: can task execute?

        Returns True if task is compliant (no blocking violations).
        Returns False with reason if blocking violations exist.

        Args:
            task_id: Task ID
            project_id: Project ID
            context: Additional context for rule evaluation

        Returns:
            Tuple of (can_execute: bool, reason: str)
        """
        validation = self.validate_task(task_id, project_id, context)

        if validation.is_compliant:
            if validation.warning_count > 0:
                return True, f"Compliant ({validation.warning_count} warnings)"
            else:
                return True, "All rules satisfied"

        if validation.blocking_violations:
            # Get names of blocking rules
            blocking_names = [
                v["rule_name"]
                for v in validation.violations
                if v["rule_id"] in validation.blocking_violations
            ]
            reason = f"Blocking violations: {', '.join(blocking_names)}"
            return False, reason

        # Should not reach here, but handle it
        return True, f"{validation.warning_count} warnings, 0 blocks"

    def get_violations(self, task_id: int, project_id: int, context: Dict[str, Any] = None) -> List[Dict]:
        """List all violations for a task.

        Args:
            task_id: Task ID
            project_id: Project ID
            context: Additional context for rule evaluation

        Returns:
            List of violations
        """
        validation = self.validate_task(task_id, project_id, context)
        return validation.violations

    def get_blocking_violations(self, task_id: int, project_id: int, context: Dict[str, Any] = None) -> List[Dict]:
        """Get violations that block execution.

        Args:
            task_id: Task ID
            project_id: Project ID
            context: Additional context for rule evaluation

        Returns:
            List of blocking violations
        """
        validation = self.validate_task(task_id, project_id, context)
        return [v for v in validation.violations if v["rule_id"] in validation.blocking_violations]

    def validate_plan(self, plan: Dict[str, Any], project_id: int) -> RuleValidationResult:
        """Validate an entire execution plan against rules.

        Validates each step of the plan and aggregates violations.

        Args:
            plan: Plan dict with 'steps' array, each containing task details
            project_id: Project ID

        Returns:
            Aggregated RuleValidationResult for the plan
        """
        steps = plan.get("steps", [])
        logger.debug(f"Validating plan with {len(steps)} steps")

        all_violations = []
        blocking_violations = set()
        warning_count = 0

        for i, step in enumerate(steps):
            step_context = {
                "step_index": i,
                "step_name": step.get("name", f"Step {i+1}"),
                "step_type": step.get("type", "task"),
            }
            # Add all step fields to context
            step_context.update(step)

            # Validate this step
            validation = self.validate_task(
                step.get("task_id", -1),
                project_id,
                step_context
            )

            all_violations.extend(validation.violations)
            blocking_violations.update(validation.blocking_violations)
            warning_count += validation.warning_count

        is_compliant = len(blocking_violations) == 0

        result = RuleValidationResult(
            task_id=-1,  # Plan-level validation
            project_id=project_id,
            is_compliant=is_compliant,
            violation_count=len(all_violations),
            warning_count=warning_count,
            violations=all_violations,
            suggestions=[],
            blocking_violations=list(blocking_violations),
        )

        logger.info(
            f"Plan validation: compliant={is_compliant}, "
            f"violations={len(all_violations)}, warnings={warning_count}"
        )

        return result

    def get_rule_by_id(self, rule_id: int) -> Optional[Rule]:
        """Get a specific rule by ID.

        Args:
            rule_id: Rule ID

        Returns:
            Rule object or None if not found
        """
        return self.store.get_rule(rule_id)

    def get_rules_by_category(self, project_id: int, category: str) -> List[Rule]:
        """Get all rules in a specific category for a project.

        Args:
            project_id: Project ID
            category: Rule category (code_quality, security, performance, etc.)

        Returns:
            List of rules in the category
        """
        return self.store.list_rules_by_category(project_id, category)

    def check_override_eligibility(self, rule_id: int, project_id: int, task_id: int = None) -> Tuple[bool, str]:
        """Check if a rule can be overridden.

        Args:
            rule_id: Rule ID
            project_id: Project ID
            task_id: Optional task ID to check for existing overrides

        Returns:
            Tuple of (can_override: bool, reason: str)
        """
        rule = self.store.get_rule(rule_id)
        if not rule:
            return False, f"Rule {rule_id} not found"

        if not rule.can_override:
            return False, f"Rule '{rule.name}' does not allow overrides"

        # If task_id provided, check for existing active override
        if task_id:
            active_overrides = self.store.get_active_overrides(task_id)
            if any(o.rule_id == rule_id for o in active_overrides):
                return False, f"Rule '{rule.name}' already has an active override for this task"

        return True, f"Rule '{rule.name}' can be overridden"

    def record_violation_history(self, task_id: int, project_id: int, validation: RuleValidationResult) -> None:
        """Record validation results in rule violation history.

        Args:
            task_id: Task ID
            project_id: Project ID
            validation: RuleValidationResult from validation
        """
        for violation in validation.violations:
            try:
                cursor = self.db.get_cursor()
                cursor.execute(
                    """
                    INSERT INTO rule_validation_history
                    (rule_id, project_id, task_id, is_violation, context, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        violation["rule_id"],
                        project_id,
                        task_id,
                        True,
                        None,
                        int(datetime.now().timestamp()),
                    ),
                )
                # commit handled by cursor context
                logger.debug(f"Recorded violation history for rule {violation['rule_id']}")
            except Exception as e:
                logger.error(f"Error recording violation history: {e}")

    def get_violation_stats(self, project_id: int, days_back: int = 30) -> Dict[str, Any]:
        """Get violation statistics for a project over time period.

        Args:
            project_id: Project ID
            days_back: Number of days to look back (default 30)

        Returns:
            Dict with violation statistics
        """
        cutoff_time = int((datetime.now() - timedelta(days=days_back)).timestamp())

        try:
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                SELECT rule_id, COUNT(*) as violation_count
                FROM rule_validation_history
                WHERE project_id = ? AND is_violation = 1 AND created_at > ?
                GROUP BY rule_id
                ORDER BY violation_count DESC
                """,
                (project_id, cutoff_time),
            )
            rows = cursor.fetchall()

            stats = {
                "total_violations": sum(row[1] for row in rows),
                "rules_violated": len(rows),
                "top_violations": [
                    {
                        "rule_id": row[0],
                        "count": row[1],
                        "rule": self.store.get_rule(row[0]),
                    }
                    for row in rows[:5]
                ],
            }

            return stats
        except Exception as e:
            logger.error(f"Error getting violation stats: {e}")
            return {"error": str(e)}
