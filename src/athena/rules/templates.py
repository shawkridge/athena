"""Pre-configured rule templates for common project patterns (Phase 9).

Provides templates for:
- Code Quality gates
- Testing requirements
- Timeline constraints
- Resource limits
- Deployment approval
- Documentation requirements
"""

from typing import List
from .models import Rule, RuleCategory, RuleType, SeverityLevel


class RuleTemplates:
    """Factory for creating pre-configured rule templates."""

    @staticmethod
    def quality_gates() -> List[Rule]:
        """Quality gates template: enforce code quality standards."""
        return [
            Rule(
                project_id=0,  # Template, no specific project
                name="min_test_coverage",
                description="Minimum 80% test coverage required before deployment",
                category=RuleCategory.QUALITY,
                rule_type=RuleType.THRESHOLD,
                condition='{"test_coverage": {"$gte": 80}}',
                severity=SeverityLevel.ERROR,
                auto_block=True,
                can_override=True,
                override_requires_approval=True,
                tags=["quality", "testing", "deployment"],
            ),
            Rule(
                project_id=0,
                name="max_cyclomatic_complexity",
                description="Functions must have cyclomatic complexity < 10",
                category=RuleCategory.QUALITY,
                rule_type=RuleType.THRESHOLD,
                condition='{"cyclomatic_complexity": {"$lt": 10}}',
                severity=SeverityLevel.WARNING,
                auto_block=False,
                can_override=True,
                tags=["quality", "complexity"],
            ),
            Rule(
                project_id=0,
                name="max_function_length",
                description="Functions must be less than 50 lines",
                category=RuleCategory.QUALITY,
                rule_type=RuleType.THRESHOLD,
                condition='{"function_length": {"$lt": 50}}',
                severity=SeverityLevel.INFO,
                auto_block=False,
                can_override=True,
                tags=["quality", "maintainability"],
            ),
            Rule(
                project_id=0,
                name="code_review_required",
                description="Code must be reviewed before merge",
                category=RuleCategory.QUALITY,
                rule_type=RuleType.APPROVAL,
                condition='{"has_review": {"$eq": True}}',
                severity=SeverityLevel.CRITICAL,
                auto_block=True,
                can_override=False,
                tags=["quality", "process"],
            ),
        ]

    @staticmethod
    def testing_requirements() -> List[Rule]:
        """Testing requirements template: enforce testing standards."""
        return [
            Rule(
                project_id=0,
                name="unit_tests_required",
                description="Unit tests required for all new code",
                category=RuleCategory.QUALITY,
                rule_type=RuleType.CONSTRAINT,
                condition='{"unit_tests_count": {"$gt": 0}}',
                severity=SeverityLevel.ERROR,
                auto_block=True,
                can_override=True,
                override_requires_approval=True,
                tags=["testing", "quality"],
            ),
            Rule(
                project_id=0,
                name="integration_tests_critical_paths",
                description="Integration tests required for critical paths",
                category=RuleCategory.QUALITY,
                rule_type=RuleType.CONSTRAINT,
                condition='{"has_integration_tests": {"$eq": True}}',
                exception_condition='{"is_critical_path": {"$eq": False}}',
                severity=SeverityLevel.WARNING,
                auto_block=False,
                can_override=True,
                tags=["testing", "quality"],
            ),
            Rule(
                project_id=0,
                name="all_tests_passing",
                description="All tests must pass before deployment",
                category=RuleCategory.QUALITY,
                rule_type=RuleType.CONSTRAINT,
                condition='{"tests_passing": {"$eq": True}}',
                severity=SeverityLevel.CRITICAL,
                auto_block=True,
                can_override=False,
                tags=["testing", "deployment"],
            ),
        ]

    @staticmethod
    def timeline_constraints() -> List[Rule]:
        """Timeline constraints template: enforce deadline adherence."""
        return [
            Rule(
                project_id=0,
                name="deadline_not_exceeded",
                description="Task duration must not exceed estimated time by >20%",
                category=RuleCategory.PROCESS,
                rule_type=RuleType.THRESHOLD,
                condition='{"duration_variance": {"$lte": 20}}',
                severity=SeverityLevel.WARNING,
                auto_block=False,
                can_override=True,
                tags=["timeline", "estimation"],
            ),
            Rule(
                project_id=0,
                name="milestone_on_track",
                description="Milestone must be on track to completion",
                category=RuleCategory.PROCESS,
                rule_type=RuleType.CONSTRAINT,
                condition='{"milestone_progress": {"$gte": 50}}',
                severity=SeverityLevel.WARNING,
                auto_block=False,
                can_override=True,
                tags=["timeline", "tracking"],
            ),
            Rule(
                project_id=0,
                name="no_critical_path_delays",
                description="Tasks on critical path must not be delayed",
                category=RuleCategory.PROCESS,
                rule_type=RuleType.CONSTRAINT,
                condition='{"is_on_schedule": {"$eq": True}}',
                exception_condition='{"is_on_critical_path": {"$eq": False}}',
                severity=SeverityLevel.ERROR,
                auto_block=True,
                can_override=True,
                override_requires_approval=True,
                tags=["timeline", "critical-path"],
            ),
        ]

    @staticmethod
    def resource_limits() -> List[Rule]:
        """Resource limits template: enforce resource constraints."""
        return [
            Rule(
                project_id=0,
                name="max_parallel_tasks",
                description="Maximum 3 concurrent critical tasks per person",
                category=RuleCategory.RESOURCE,
                rule_type=RuleType.THRESHOLD,
                condition='{"concurrent_critical_tasks": {"$lte": 3}}',
                severity=SeverityLevel.WARNING,
                auto_block=False,
                can_override=True,
                tags=["resource", "allocation"],
            ),
            Rule(
                project_id=0,
                name="skills_match_required",
                description="Task owner must have required skill level",
                category=RuleCategory.RESOURCE,
                rule_type=RuleType.CONSTRAINT,
                condition='{"skills_match": {"$eq": True}}',
                severity=SeverityLevel.ERROR,
                auto_block=True,
                can_override=True,
                override_requires_approval=True,
                tags=["resource", "allocation"],
            ),
            Rule(
                project_id=0,
                name="tool_availability",
                description="All required tools must be available",
                category=RuleCategory.RESOURCE,
                rule_type=RuleType.CONSTRAINT,
                condition='{"tools_available": {"$eq": True}}',
                severity=SeverityLevel.ERROR,
                auto_block=True,
                can_override=False,
                tags=["resource", "dependencies"],
            ),
        ]

    @staticmethod
    def deployment_approval() -> List[Rule]:
        """Deployment approval template: enforce deployment controls."""
        return [
            Rule(
                project_id=0,
                name="security_review_before_deploy",
                description="Security review required before production deployment",
                category=RuleCategory.DEPLOYMENT,
                rule_type=RuleType.APPROVAL,
                condition='{"security_reviewed": {"$eq": True}}',
                exception_condition='{"is_dev_environment": {"$eq": True}}',
                severity=SeverityLevel.CRITICAL,
                auto_block=True,
                can_override=False,
                tags=["deployment", "security"],
            ),
            Rule(
                project_id=0,
                name="staging_tested",
                description="Changes must be tested in staging environment",
                category=RuleCategory.DEPLOYMENT,
                rule_type=RuleType.CONSTRAINT,
                condition='{"staging_tests_passed": {"$eq": True}}',
                severity=SeverityLevel.CRITICAL,
                auto_block=True,
                can_override=True,
                override_requires_approval=True,
                tags=["deployment", "testing"],
            ),
            Rule(
                project_id=0,
                name="rollback_plan_required",
                description="Rollback plan must exist for production changes",
                category=RuleCategory.DEPLOYMENT,
                rule_type=RuleType.CONSTRAINT,
                condition='{"has_rollback_plan": {"$eq": True}}',
                exception_condition='{"is_non_breaking_change": {"$eq": True}}',
                severity=SeverityLevel.WARNING,
                auto_block=False,
                can_override=True,
                tags=["deployment", "reliability"],
            ),
        ]

    @staticmethod
    def documentation_requirements() -> List[Rule]:
        """Documentation requirements template: enforce documentation standards."""
        return [
            Rule(
                project_id=0,
                name="api_documentation",
                description="Public APIs must be documented",
                category=RuleCategory.QUALITY,
                rule_type=RuleType.CONSTRAINT,
                condition='{"api_documented": {"$eq": True}}',
                severity=SeverityLevel.ERROR,
                auto_block=False,
                can_override=True,
                tags=["documentation", "api"],
            ),
            Rule(
                project_id=0,
                name="breaking_changes_documented",
                description="Breaking changes must be documented",
                category=RuleCategory.QUALITY,
                rule_type=RuleType.CONSTRAINT,
                condition='{"breaking_changes_documented": {"$eq": True}}',
                exception_condition='{"has_breaking_changes": {"$eq": False}}',
                severity=SeverityLevel.WARNING,
                auto_block=False,
                can_override=True,
                tags=["documentation", "communication"],
            ),
            Rule(
                project_id=0,
                name="readme_updated",
                description="README must be updated for significant changes",
                category=RuleCategory.QUALITY,
                rule_type=RuleType.CONSTRAINT,
                condition='{"readme_updated": {"$eq": True}}',
                severity=SeverityLevel.INFO,
                auto_block=False,
                can_override=True,
                tags=["documentation", "project-info"],
            ),
        ]

    @staticmethod
    def security_compliance() -> List[Rule]:
        """Security compliance template: enforce security standards."""
        return [
            Rule(
                project_id=0,
                name="no_hardcoded_secrets",
                description="No hardcoded secrets or credentials",
                category=RuleCategory.SECURITY,
                rule_type=RuleType.CONSTRAINT,
                condition='{"has_hardcoded_secrets": {"$eq": False}}',
                severity=SeverityLevel.CRITICAL,
                auto_block=True,
                can_override=False,
                tags=["security", "credentials"],
            ),
            Rule(
                project_id=0,
                name="dependency_scan_passed",
                description="Dependency security scan must pass",
                category=RuleCategory.SECURITY,
                rule_type=RuleType.CONSTRAINT,
                condition='{"dependency_scan_passed": {"$eq": True}}',
                severity=SeverityLevel.ERROR,
                auto_block=True,
                can_override=True,
                override_requires_approval=True,
                tags=["security", "dependencies"],
            ),
            Rule(
                project_id=0,
                name="no_sql_injection_risk",
                description="Code must not be vulnerable to SQL injection",
                category=RuleCategory.SECURITY,
                rule_type=RuleType.CONSTRAINT,
                condition='{"sql_injection_risk": {"$eq": False}}',
                severity=SeverityLevel.CRITICAL,
                auto_block=True,
                can_override=False,
                tags=["security", "code-review"],
            ),
        ]

    @staticmethod
    def all_templates() -> dict:
        """Get all available templates as a dictionary."""
        return {
            "quality_gates": RuleTemplates.quality_gates(),
            "testing_requirements": RuleTemplates.testing_requirements(),
            "timeline_constraints": RuleTemplates.timeline_constraints(),
            "resource_limits": RuleTemplates.resource_limits(),
            "deployment_approval": RuleTemplates.deployment_approval(),
            "documentation_requirements": RuleTemplates.documentation_requirements(),
            "security_compliance": RuleTemplates.security_compliance(),
        }

    @staticmethod
    def get_template_names() -> List[str]:
        """Get list of available template names."""
        return list(RuleTemplates.all_templates().keys())


def create_project_rules(project_id: int, template_names: List[str] = None) -> List[Rule]:
    """Create rules for a project from templates.

    Args:
        project_id: Project ID to assign rules to
        template_names: List of template names to use.
                       If None, uses all templates.

    Returns:
        List of Rule objects configured for the project
    """
    if template_names is None:
        template_names = RuleTemplates.get_template_names()

    all_templates = RuleTemplates.all_templates()
    project_rules = []

    for name in template_names:
        if name not in all_templates:
            continue

        for rule in all_templates[name]:
            # Create a copy of the rule with the project ID set
            rule_dict = rule.model_dump()
            rule_dict["project_id"] = project_id
            project_rules.append(Rule(**rule_dict))

    return project_rules
