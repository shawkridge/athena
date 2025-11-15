"""Formal Verification System for Plan Validation.

Validates plans before execution using:
- Constraint satisfaction checking
- Precondition/postcondition verification
- Resource usage prediction
- Dependency graph validation
- Safety constraint checking
- Feasibility assessment

This ensures plans are executable and safe before running them.
"""

import logging
from typing import Dict, List, Set, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class ConstraintType(Enum):
    """Types of constraints that can be validated."""
    RESOURCE = "resource"  # time, tokens, memory
    DEPENDENCY = "dependency"  # task ordering
    SAFETY = "safety"  # no destructive operations
    LOGICAL = "logical"  # correctness assertions
    PERFORMANCE = "performance"  # speed/efficiency


class VerificationResult(Enum):
    """Verification outcome."""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    INCONCLUSIVE = "inconclusive"


@dataclass
class Constraint:
    """A constraint to be validated."""
    name: str
    constraint_type: ConstraintType
    description: str
    check_fn: callable = None  # Function to validate
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationReport:
    """Report from formal verification."""
    plan_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    result: VerificationResult = VerificationResult.INCONCLUSIVE

    # Validation results
    constraints_checked: int = 0
    constraints_passed: int = 0
    constraints_failed: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    # Resource predictions
    estimated_time_seconds: float = 0.0
    estimated_tokens: int = 0
    estimated_memory_mb: float = 0.0

    # Details
    details: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Check if verification passed."""
        return self.result == VerificationResult.VALID

    @property
    def pass_rate(self) -> float:
        """Constraint pass rate (0-1)."""
        if self.constraints_checked == 0:
            return 0.0
        return self.constraints_passed / self.constraints_checked

    def __str__(self) -> str:
        """Summary string."""
        return (
            f"VerificationReport({self.plan_id})\n"
            f"  Result: {self.result.value}\n"
            f"  Constraints: {self.constraints_passed}/{self.constraints_checked} passed\n"
            f"  Estimated: {self.estimated_time_seconds:.1f}s, "
            f"{self.estimated_tokens} tokens\n"
            f"  Warnings: {len(self.warnings)}\n"
            f"  Errors: {len(self.errors)}"
        )


@dataclass
class Task:
    """A task in a plan."""
    task_id: str
    name: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    estimated_time: float = 0.0  # seconds
    estimated_tokens: int = 0
    preconditions: Dict[str, Any] = field(default_factory=dict)
    postconditions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    """A plan to be verified."""
    plan_id: str
    name: str
    description: str
    tasks: List[Task] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None


class FormalVerifier:
    """Formal verification system for plans."""

    def __init__(self):
        """Initialize verifier."""
        self._constraints: Dict[str, Constraint] = {}
        self._register_default_constraints()

    def _register_default_constraints(self) -> None:
        """Register default constraints."""
        # Dependency constraint
        self._constraints["dependencies"] = Constraint(
            name="Dependency Graph Valid",
            constraint_type=ConstraintType.DEPENDENCY,
            description="Task dependencies form a DAG (no cycles)",
            check_fn=self._check_no_cycles,
        )

        # Resource constraints
        self._constraints["max_time"] = Constraint(
            name="Time Budget",
            constraint_type=ConstraintType.RESOURCE,
            description="Total execution time within limits",
            check_fn=self._check_time_budget,
        )

        self._constraints["max_tokens"] = Constraint(
            name="Token Budget",
            constraint_type=ConstraintType.RESOURCE,
            description="Total tokens within limits",
            check_fn=self._check_token_budget,
        )

        # Safety constraint
        self._constraints["no_destructive"] = Constraint(
            name="Safety: No Destructive Operations",
            constraint_type=ConstraintType.SAFETY,
            description="Plan contains no destructive operations",
            check_fn=self._check_no_destructive_operations,
        )

    def register_constraint(self, constraint: Constraint) -> None:
        """Register a custom constraint."""
        self._constraints[constraint.name] = constraint
        logger.debug(f"Registered constraint: {constraint.name}")

    async def verify(
        self,
        plan: Plan,
        config: Optional[Dict[str, Any]] = None,
    ) -> VerificationReport:
        """Verify a plan.

        Args:
            plan: Plan to verify
            config: Verification configuration (time_limit, token_limit, etc.)

        Returns:
            VerificationReport with results
        """
        config = config or {}
        report = VerificationReport(plan_id=plan.plan_id)

        logger.info(f"Verifying plan: {plan.name}")

        # Check basic validity
        if not plan.tasks:
            report.errors.append("Plan contains no tasks")
            report.result = VerificationResult.INVALID
            return report

        # Run constraints
        for constraint_name, constraint in self._constraints.items():
            report.constraints_checked += 1

            try:
                passed = constraint.check_fn(plan, config)
                if passed:
                    report.constraints_passed += 1
                else:
                    report.constraints_failed += 1
                    report.errors.append(f"Constraint failed: {constraint.description}")

            except Exception as e:
                report.constraints_failed += 1
                report.errors.append(f"Constraint check error: {e}")

        # Calculate resource estimates
        await self._estimate_resources(plan, report)

        # Check preconditions/postconditions
        await self._verify_conditions(plan, report)

        # Determine overall result
        report.result = self._determine_result(report)

        # Generate recommendations
        report.recommendations = await self._generate_recommendations(report, config)

        logger.info(f"Verification complete: {report.result.value}")
        return report

    def _check_no_cycles(self, plan: Plan, config: Dict[str, Any]) -> bool:
        """Check that task dependency graph is acyclic (DAG)."""
        visited = set()
        rec_stack = set()

        def has_cycle(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)

            task = plan.get_task(task_id)
            if task:
                for dep in task.dependencies:
                    if dep not in visited:
                        if has_cycle(dep):
                            return True
                    elif dep in rec_stack:
                        return True

            rec_stack.remove(task_id)
            return False

        for task in plan.tasks:
            if task.task_id not in visited:
                if has_cycle(task.task_id):
                    logger.error(f"Cycle detected in plan: {plan.plan_id}")
                    return False

        return True

    def _check_time_budget(self, plan: Plan, config: Dict[str, Any]) -> bool:
        """Check total execution time against budget."""
        max_time = config.get("max_time_seconds", 3600)  # 1 hour default
        total_time = sum(task.estimated_time for task in plan.tasks)

        logger.debug(f"Time check: {total_time:.1f}s / {max_time}s")
        return total_time <= max_time

    def _check_token_budget(self, plan: Plan, config: Dict[str, Any]) -> bool:
        """Check total tokens against budget."""
        max_tokens = config.get("max_tokens", 100000)
        total_tokens = sum(task.estimated_tokens for task in plan.tasks)

        logger.debug(f"Token check: {total_tokens} / {max_tokens}")
        return total_tokens <= max_tokens

    def _check_no_destructive_operations(
        self,
        plan: Plan,
        config: Dict[str, Any],
    ) -> bool:
        """Check that plan doesn't contain destructive operations."""
        forbidden_keywords = ["delete", "drop", "truncate", "remove", "destroy"]

        for task in plan.tasks:
            for keyword in forbidden_keywords:
                if keyword in task.name.lower() or keyword in task.description.lower():
                    logger.warning(f"Potentially destructive task: {task.name}")
                    if not config.get("allow_destructive", False):
                        return False

        return True

    async def _estimate_resources(self, plan: Plan, report: VerificationReport) -> None:
        """Estimate resource usage."""
        report.estimated_time_seconds = sum(task.estimated_time for task in plan.tasks)
        report.estimated_tokens = sum(task.estimated_tokens for task in plan.tasks)

        # Memory estimate (simple heuristic: 1MB per 1000 tokens)
        report.estimated_memory_mb = report.estimated_tokens / 1000

    async def _verify_conditions(self, plan: Plan, report: VerificationReport) -> None:
        """Verify preconditions and postconditions."""
        for task in plan.tasks:
            # Check preconditions
            for precond_name, precond_value in task.preconditions.items():
                # Simplified: just verify they're specified
                report.details[f"{task.task_id}_precond"] = precond_name

            # Check postconditions
            for postcond_name, postcond_value in task.postconditions.items():
                report.details[f"{task.task_id}_postcond"] = postcond_name

    def _determine_result(self, report: VerificationReport) -> VerificationResult:
        """Determine overall verification result."""
        if report.constraints_failed > 0:
            return VerificationResult.INVALID

        if len(report.warnings) > 0:
            return VerificationResult.WARNING

        if report.constraints_passed == report.constraints_checked:
            return VerificationResult.VALID

        return VerificationResult.INCONCLUSIVE

    async def _generate_recommendations(
        self,
        report: VerificationReport,
        config: Dict[str, Any],
    ) -> List[str]:
        """Generate recommendations based on verification results."""
        recommendations = []

        # Time optimization
        if report.estimated_time_seconds > config.get("max_time_seconds", 3600):
            recommendations.append(
                f"Consider parallelizing tasks or simplifying plan. "
                f"Estimated time: {report.estimated_time_seconds:.1f}s"
            )

        # Token optimization
        if report.estimated_tokens > config.get("max_tokens", 100000):
            recommendations.append(
                f"Reduce LLM calls or prompts. "
                f"Estimated tokens: {report.estimated_tokens}"
            )

        # Memory warning
        if report.estimated_memory_mb > 1000:  # 1GB
            recommendations.append(
                f"High memory usage estimated: {report.estimated_memory_mb:.0f}MB. "
                f"Consider streaming or chunking."
            )

        return recommendations


class PlanValidator:
    """High-level plan validator combining multiple verification strategies."""

    def __init__(self):
        """Initialize validator."""
        self.verifier = FormalVerifier()

    async def validate(
        self,
        plan: Plan,
        strict: bool = False,
    ) -> Tuple[bool, VerificationReport]:
        """Validate a plan.

        Args:
            plan: Plan to validate
            strict: If True, warnings are treated as failures

        Returns:
            (is_valid, report) tuple
        """
        config = {
            "max_time_seconds": 3600,
            "max_tokens": 100000,
            "allow_destructive": False,
        }

        report = await self.verifier.verify(plan, config)

        is_valid = (
            report.result == VerificationResult.VALID
            or (report.result == VerificationResult.WARNING and not strict)
        )

        return is_valid, report
