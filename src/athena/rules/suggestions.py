"""Suggestion generation for rule violations in Phase 9."""

import logging
from typing import List, Dict, Any, Optional
from .models import RuleValidationResult
from .engine import RulesEngine

logger = logging.getLogger(__name__)


class SuggestionsEngine:
    """Generate suggestions to make tasks/plans compliant with rules.

    Provides context-aware suggestions for fixing violations, modifying plans,
    and adjusting rules based on recurring violations.
    """

    def __init__(self, engine: Optional[RulesEngine] = None):
        """Initialize SuggestionsEngine.

        Args:
            engine: Optional RulesEngine instance for fetching rule details
        """
        self.engine = engine
        logger.debug("SuggestionsEngine initialized")

    def suggest_fixes(self, violations: List[Dict], task: Any = None) -> List[str]:
        """Generate actionable suggestions to fix violations.

        Analyzes violation details and generates context-aware, actionable fixes
        based on rule category, type, and severity.

        Args:
            violations: List of violation dicts with rule details
            task: Optional task object for additional context

        Returns:
            List of suggestion strings
        """
        suggestions = []

        for violation in violations:
            rule_name = violation.get("rule_name", "Unknown")
            category = violation.get("category", "").lower()
            rule_type = violation.get("type", "").lower()
            message = violation.get("message", "")
            severity = violation.get("severity", "").lower()

            logger.debug(f"Generating fix suggestions for rule: {rule_name} (category: {category})")

            # Category-based suggestions
            if category == "code_quality":
                suggestions.extend(self._suggest_code_quality_fix(rule_name, rule_type, message))
            elif category == "security":
                suggestions.extend(self._suggest_security_fix(rule_name, rule_type, message))
            elif category == "performance":
                suggestions.extend(self._suggest_performance_fix(rule_name, rule_type, message))
            elif category == "documentation":
                suggestions.extend(self._suggest_documentation_fix(rule_name, rule_type, message))
            elif category == "process":
                suggestions.extend(self._suggest_process_fix(rule_name, rule_type, message))
            elif category == "resource":
                suggestions.extend(self._suggest_resource_fix(rule_name, rule_type, message))
            elif category == "deployment":
                suggestions.extend(self._suggest_deployment_fix(rule_name, rule_type, message))
            else:
                # Fallback: rule-name based suggestions
                suggestions.extend(self._suggest_generic_fix(rule_name, message))

        logger.debug(f"Generated {len(suggestions)} fix suggestions")
        return suggestions

    def _suggest_code_quality_fix(self, rule_name: str, rule_type: str, message: str) -> List[str]:
        """Generate suggestions for code quality violations."""
        fixes = []

        if "test_coverage" in rule_name.lower() or "coverage" in rule_type:
            fixes.append("Increase test coverage: Add unit tests for untested code paths")
            fixes.append("Run coverage tool to identify gaps: pytest --cov")
            fixes.append("Target coverage threshold: 80% minimum")
        elif "function_length" in rule_name.lower() or "length" in rule_type:
            fixes.append("Refactor: Split function into smaller, single-responsibility functions")
            fixes.append("Extract helper methods for complex logic blocks")
            fixes.append("Target: Keep functions <30 lines")
        elif "complexity" in rule_name.lower() or "cyclomatic" in rule_type:
            fixes.append("Reduce cyclomatic complexity: Simplify conditional logic")
            fixes.append("Extract conditionals into separate functions")
            fixes.append("Use guard clauses instead of nested if-else")
        elif "naming" in rule_name.lower():
            fixes.append("Rename variables to be more descriptive")
            fixes.append("Follow naming conventions: snake_case for functions, UPPER_CASE for constants")
        else:
            fixes.append(f"Address code quality issue: {message}")

        return fixes

    def _suggest_security_fix(self, rule_name: str, rule_type: str, message: str) -> List[str]:
        """Generate suggestions for security violations."""
        fixes = []

        if "sql" in rule_name.lower() or "injection" in rule_type:
            fixes.append("Use parameterized queries to prevent SQL injection")
            fixes.append("Validate all user input before use")
            fixes.append("Use ORM or prepared statements")
        elif "authentication" in rule_name.lower() or "auth" in rule_type:
            fixes.append("Implement proper authentication mechanism")
            fixes.append("Use established auth libraries (JWT, OAuth)")
            fixes.append("Enforce secure password policies")
        elif "encryption" in rule_name.lower() or "crypto" in rule_type:
            fixes.append("Encrypt sensitive data at rest and in transit")
            fixes.append("Use industry-standard encryption (AES-256, TLS 1.3)")
            fixes.append("Securely manage encryption keys")
        elif "secret" in rule_name.lower():
            fixes.append("Remove secrets from code: use environment variables")
            fixes.append("Scan code for API keys, tokens, passwords")
            fixes.append("Use secrets management tool (HashiCorp Vault, AWS Secrets Manager)")
        else:
            fixes.append(f"Address security concern: {message}")

        return fixes

    def _suggest_performance_fix(self, rule_name: str, rule_type: str, message: str) -> List[str]:
        """Generate suggestions for performance violations."""
        fixes = []

        if "query" in rule_name.lower() or "database" in rule_type:
            fixes.append("Optimize database queries: Use indexes, avoid N+1 queries")
            fixes.append("Add database indexes on frequently queried columns")
            fixes.append("Profile queries with EXPLAIN ANALYZE")
        elif "memory" in rule_name.lower():
            fixes.append("Reduce memory footprint: Optimize data structures")
            fixes.append("Avoid loading entire datasets into memory")
            fixes.append("Use streaming/pagination for large datasets")
        elif "timeout" in rule_name.lower() or "latency" in rule_type:
            fixes.append("Reduce operation latency: Optimize algorithms")
            fixes.append("Consider caching frequently used results")
            fixes.append("Profile code to identify bottlenecks")
        else:
            fixes.append(f"Improve performance: {message}")

        return fixes

    def _suggest_documentation_fix(self, rule_name: str, rule_type: str, message: str) -> List[str]:
        """Generate suggestions for documentation violations."""
        fixes = []

        if "docstring" in rule_name.lower() or "comment" in rule_type:
            fixes.append("Add docstring to function/class describing purpose")
            fixes.append("Document parameters and return values")
            fixes.append("Follow docstring format (Google, NumPy, or Sphinx)")
        elif "readme" in rule_name.lower():
            fixes.append("Create/update README.md with project overview")
            fixes.append("Add setup, usage, and contribution instructions")
        elif "changelog" in rule_name.lower():
            fixes.append("Add entry to CHANGELOG describing changes")
            fixes.append("Follow semantic versioning: MAJOR.MINOR.PATCH")
        else:
            fixes.append(f"Improve documentation: {message}")

        return fixes

    def _suggest_process_fix(self, rule_name: str, rule_type: str, message: str) -> List[str]:
        """Generate suggestions for process violations."""
        fixes = []

        if "review" in rule_name.lower() or "approval" in rule_type:
            fixes.append("Request code review before merging")
            fixes.append("Ensure PR has minimum 1-2 approvals")
            fixes.append("Address reviewer comments")
        elif "test" in rule_name.lower():
            fixes.append("Run all tests and ensure they pass")
            fixes.append("Add new tests for new functionality")
            fixes.append("Target >80% code coverage")
        elif "branch" in rule_name.lower():
            fixes.append("Use feature branches: feature/description")
            fixes.append("Merge via pull request with code review")
        else:
            fixes.append(f"Follow process guidelines: {message}")

        return fixes

    def _suggest_resource_fix(self, rule_name: str, rule_type: str, message: str) -> List[str]:
        """Generate suggestions for resource constraint violations."""
        fixes = []

        if "time" in rule_name.lower() or "duration" in rule_type:
            fixes.append("Reduce task duration: break into smaller subtasks")
            fixes.append("Parallelize independent steps")
            fixes.append("Remove non-critical tasks")
        elif "person" in rule_name.lower() or "team" in rule_type:
            fixes.append("Distribute tasks across team members")
            fixes.append("Avoid overloading single person")
            fixes.append("Cross-train team members")
        elif "memory" in rule_name.lower():
            fixes.append("Reduce memory requirements: optimize algorithms")
            fixes.append("Use streaming/pagination")
        else:
            fixes.append(f"Address resource constraint: {message}")

        return fixes

    def _suggest_deployment_fix(self, rule_name: str, rule_type: str, message: str) -> List[str]:
        """Generate suggestions for deployment violations."""
        fixes = []

        if "staging" in rule_name.lower():
            fixes.append("Deploy to staging environment first")
            fixes.append("Test in staging before production")
        elif "rollback" in rule_name.lower():
            fixes.append("Ensure rollback plan is in place")
            fixes.append("Document rollback procedures")
        elif "notification" in rule_name.lower():
            fixes.append("Notify relevant teams before deployment")
            fixes.append("Post deployment notifications in Slack/Teams")
        else:
            fixes.append(f"Follow deployment process: {message}")

        return fixes

    def _suggest_generic_fix(self, rule_name: str, message: str) -> List[str]:
        """Generate generic suggestions for unknown rule types."""
        return [f"Address: {message} (Rule: {rule_name})"]

    def suggest_compliant_plan(self, violations: List[Dict], original_plan: Any = None) -> List[str]:
        """Generate alternative plan suggestions that comply with rules.

        Analyzes violations and suggests plan restructuring to achieve compliance.

        Args:
            violations: List of violations
            original_plan: Optional original plan object with 'steps', 'duration', 'parallel_tasks'

        Returns:
            List of plan modification suggestions
        """
        suggestions = []

        # Group violations by type for better suggestions
        duration_violations = []
        parallel_violations = []
        dependency_violations = []
        resource_violations = []
        other_violations = []

        for violation in violations:
            rule_name = violation.get("rule_name", "Unknown").lower()

            if "duration" in rule_name or "timeout" in rule_name:
                duration_violations.append(violation)
            elif "parallel" in rule_name or "concurrent" in rule_name:
                parallel_violations.append(violation)
            elif "depend" in rule_name or "prerequisite" in rule_name:
                dependency_violations.append(violation)
            elif "resource" in rule_name or "capacity" in rule_name:
                resource_violations.append(violation)
            else:
                other_violations.append(violation)

        # Generate plan-level suggestions based on violation types
        if duration_violations:
            suggestions.append("Plan Restructuring: Split long-running tasks into smaller subtasks with shorter durations")
            suggestions.append("Add intermediate checkpoints to break down execution timeline")
            if original_plan:
                total_duration = original_plan.get("duration", 0)
                num_steps = len(original_plan.get("steps", []))
                suggested_duration = total_duration // (num_steps + 1)
                suggestions.append(f"Target: Reduce step duration to ~{suggested_duration} minutes")

        if parallel_violations:
            suggestions.append("Parallelization: Reduce number of parallel tasks to respect resource limits")
            suggestions.append("Identify sequential dependencies that can be separated")
            suggestions.append("Use serial execution for critical paths, parallel for independent tasks")

        if dependency_violations:
            suggestions.append("Dependency Resolution: Ensure all prerequisite tasks complete before dependent tasks")
            suggestions.append("Add explicit ordering constraints in plan")
            suggestions.append("Identify critical path dependencies")

        if resource_violations:
            suggestions.append("Resource Allocation: Distribute tasks across team members to balance load")
            suggestions.append("Avoid concentrating multiple critical tasks on one person")
            suggestions.append("Schedule resource-intensive tasks during off-peak hours")

        for violation in other_violations:
            rule_name = violation.get("rule_name", "Unknown")
            suggestions.append(f"Plan Adjustment: Restructure to address '{rule_name}' constraint")

        logger.debug(f"Generated {len(suggestions)} compliant plan suggestions")
        return suggestions

    def suggest_rule_adjustments(self, violations_count: int, rule_name: str) -> List[Dict]:
        """Suggest rule modifications for recurring violations.

        Analyzes violation frequency and suggests rule adjustments based on patterns.
        High-frequency violations may indicate overly strict rules.

        Args:
            violations_count: Number of times rule violated in observation period
            rule_name: Name of the rule

        Returns:
            List of adjustment suggestions (each is a dict with type, reason, recommendation)
        """
        suggestions = []

        logger.debug(f"Analyzing rule adjustments for '{rule_name}' with {violations_count} violations")

        if violations_count == 0:
            suggestions.append({
                "type": "monitor",
                "reason": f"Rule '{rule_name}' has no recent violations",
                "recommendation": "Continue monitoring rule effectiveness",
                "priority": "low",
            })
        elif violations_count < 3:
            suggestions.append({
                "type": "maintain",
                "reason": f"Rule '{rule_name}' violated {violations_count} times",
                "recommendation": "Rule is working as intended. Maintain current threshold.",
                "priority": "low",
            })
        elif violations_count < 5:
            suggestions.append({
                "type": "review",
                "reason": f"Rule '{rule_name}' violated {violations_count} times",
                "recommendation": "Review rule to ensure it's aligned with team capacity",
                "priority": "medium",
            })
        elif violations_count < 10:
            suggestions.append({
                "type": "adjust",
                "reason": f"Rule '{rule_name}' violated {violations_count} times",
                "recommendation": "Consider adjusting rule threshold or conditions slightly",
                "priority": "medium",
                "examples": [
                    "If duration-based: increase max duration by 10-20%",
                    "If threshold-based: relax the constraint by 1 level",
                    "Add exception conditions for edge cases",
                ],
            })
        else:  # >= 10
            suggestions.append({
                "type": "relax",
                "reason": f"Rule '{rule_name}' violated {violations_count} times (frequent violations)",
                "recommendation": "Rule appears overly strict. Recommend significant adjustment or removal",
                "priority": "high",
                "examples": [
                    "Increase threshold by 25-50%",
                    "Make rule informational instead of blocking",
                    "Add broad exception conditions",
                    "Consider removing rule if fundamentally misaligned",
                ],
            })

        # Add general recommendation
        suggestions.append({
            "type": "analysis",
            "reason": "Regular violation pattern analysis",
            "recommendation": f"Review team capacity and rule alignment. Current violation rate: {violations_count} in observation period",
            "priority": "medium",
        })

        logger.debug(f"Generated {len(suggestions)} rule adjustment suggestions")
        return suggestions

    def generate_comprehensive_report(self, validation: "RuleValidationResult") -> Dict[str, Any]:
        """Generate comprehensive compliance report with all suggestions.

        Args:
            validation: RuleValidationResult from engine validation

        Returns:
            Dict with compliance status, violations, and all suggestions
        """
        logger.debug(f"Generating comprehensive compliance report for task {validation.task_id}")

        # Get fix suggestions
        fix_suggestions = self.suggest_fixes(validation.violations)

        # Get plan suggestions (pass as list of violation dicts)
        plan_suggestions = self.suggest_compliant_plan(validation.violations)

        report = {
            "task_id": validation.task_id,
            "project_id": validation.project_id,
            "is_compliant": validation.is_compliant,
            "summary": {
                "total_violations": validation.violation_count,
                "warnings": validation.warning_count,
                "blocking_violations": len(validation.blocking_violations),
            },
            "violations": validation.violations,
            "suggestions": {
                "fixes": fix_suggestions,
                "plan_modifications": plan_suggestions,
            },
            "compliance_status": "PASS" if validation.is_compliant else "FAIL",
            "can_execute": validation.is_compliant,
        }

        logger.info(
            f"Compliance report generated: {report['compliance_status']}, "
            f"violations={validation.violation_count}, blocking={len(validation.blocking_violations)}"
        )

        return report
