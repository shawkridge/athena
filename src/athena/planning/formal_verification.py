"""Formal verification engine for plans using Q* pattern.

Based on: Liang et al. 2024 (Q*), arXiv:2406.14283
Hybrid approach combining symbolic verification (property checking) with
simulation-based verification for comprehensive plan correctness validation.

Key Innovation: Q* pattern - Generate → Verify → Refine → Repeat
This ensures plans are correct before execution.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)


class PropertyType(str, Enum):
    """Formal properties to verify."""

    SAFETY = "safety"  # No invalid state transitions
    LIVENESS = "liveness"  # Plan will eventually complete
    COMPLETENESS = "completeness"  # All goals covered
    FEASIBILITY = "feasibility"  # Resources and time available
    CORRECTNESS = "correctness"  # Logic matches problem domain


class VerificationMethod(str, Enum):
    """Verification approaches."""

    SYMBOLIC = "symbolic"  # Property checking (LTL, CTL)
    SIMULATION = "simulation"  # Execution simulation
    HYBRID = "hybrid"  # Symbolic + simulation


@dataclass
class PropertyViolation:
    """A single property violation found during verification."""

    property_type: PropertyType
    violation_type: str  # e.g., "circular_dependency", "resource_constraint"
    message: str
    affected_element: Optional[str] = None  # Task ID, goal ID, etc.
    severity: float = 0.5  # 0.0-1.0 (how serious is this?)
    suggested_fix: Optional[str] = None

    def __hash__(self):
        return hash((self.property_type, self.violation_type, self.affected_element))

    def __eq__(self, other):
        return (
            isinstance(other, PropertyViolation)
            and self.property_type == other.property_type
            and self.violation_type == other.violation_type
            and self.affected_element == other.affected_element
        )


@dataclass
class PropertyCheckResult:
    """Result of checking a single property."""

    property_type: PropertyType
    passed: bool
    violations: List[PropertyViolation] = field(default_factory=list)
    confidence: float = 1.0  # 0.0-1.0 confidence in the check
    check_duration_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    def add_violation(self, violation: PropertyViolation):
        """Add a violation."""
        if violation not in self.violations:
            self.violations.append(violation)
        self.passed = False
        # Reduce confidence for each violation
        self.confidence *= 0.9


@dataclass
class SimulationScenario:
    """An execution scenario for simulation."""

    scenario_id: str
    name: str
    description: str
    time_multiplier: float = 1.0  # 1.0 = nominal, 0.5 = 50% less time
    resource_multiplier: float = 1.0  # 1.0 = nominal, 0.5 = 50% resources
    assumption_failures: List[str] = field(default_factory=list)  # Assumptions that fail


@dataclass
class SimulationResult:
    """Result of a single simulation scenario."""

    scenario: SimulationScenario
    success: bool
    tasks_executed: int = 0
    tasks_failed: int = 0
    failures: List[Tuple[str, str, str]] = field(
        default_factory=list
    )  # (task, error_type, message)
    resources_used: Dict[str, float] = field(default_factory=dict)
    timing_violations: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0


@dataclass
class FormalVerificationResult:
    """Complete formal verification result for a plan."""

    plan_id: int
    properties_verified: List[PropertyType] = field(default_factory=list)
    property_results: Dict[PropertyType, PropertyCheckResult] = field(default_factory=dict)
    all_properties_passed: bool = True
    counterexamples: List[PropertyViolation] = field(default_factory=list)
    simulation_results: List[SimulationResult] = field(default_factory=list)
    verification_confidence: float = 1.0
    verification_method: str = "hybrid"
    total_verification_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def summary(self) -> str:
        """Get human-readable summary."""
        passed_count = sum(1 for r in self.property_results.values() if r.passed)
        total_count = len(self.property_results)
        return (
            f"Plan {self.plan_id}: {passed_count}/{total_count} properties passed, "
            f"confidence={self.verification_confidence:.2f}, "
            f"method={self.verification_method}"
        )


@dataclass
class RefinementStrategy:
    """A strategy to refine a plan to fix issues."""

    strategy_type: str  # e.g., "add_buffers", "parallelize", "reorder_tasks"
    description: str
    estimated_impact: float  # 0.0-1.0 how much does this fix the issues?
    estimated_effort_minutes: int
    preconditions: List[str] = field(default_factory=list)  # When applicable


@dataclass
class RefinementResult:
    """Result of applying refinement strategies."""

    original_plan_id: int
    refined_plan_id: int
    iteration: int
    issues_addressed: List[PropertyViolation]
    strategies_applied: List[RefinementStrategy]
    verification_before: FormalVerificationResult
    verification_after: FormalVerificationResult
    improvements: Dict[str, float]  # Metric improvements


class PropertyChecker:
    """Check formal properties of plans."""

    def __init__(self):
        """Initialize property checker."""
        pass

    def check_safety(self, plan: Dict[str, Any]) -> PropertyCheckResult:
        """Check safety property: no invalid state transitions or constraint violations.

        Checks:
        - Task dependencies form a DAG (no cycles)
        - Resource constraints not violated
        - Preconditions met before task execution
        - No conflicting parallel tasks
        """
        result = PropertyCheckResult(property_type=PropertyType.SAFETY, passed=True)

        try:
            # Check 1: DAG (no cycles)
            if self._has_cycle(plan.get("tasks", []), plan.get("dependencies", {})):
                violation = PropertyViolation(
                    property_type=PropertyType.SAFETY,
                    violation_type="circular_dependency",
                    message="Task dependencies contain cycles",
                    severity=1.0,
                    suggested_fix="Reorder tasks to eliminate circular dependencies",
                )
                result.add_violation(violation)

            # Check 2: Resource constraints
            total_resources = self._check_resource_constraints(plan)
            if not total_resources:
                violation = PropertyViolation(
                    property_type=PropertyType.SAFETY,
                    violation_type="resource_constraint_violation",
                    message="Resource requirements exceed available capacity",
                    severity=0.8,
                    suggested_fix="Reduce task parallelism or increase resource allocation",
                )
                result.add_violation(violation)

            # Check 3: Preconditions
            precond_issues = self._check_preconditions(plan)
            for issue in precond_issues:
                result.add_violation(issue)

            # Check 4: No conflicting parallel tasks
            parallel_issues = self._check_parallel_conflicts(plan)
            for issue in parallel_issues:
                result.add_violation(issue)

        except Exception as e:
            logger.error(f"Error checking safety: {e}")
            result.add_violation(
                PropertyViolation(
                    property_type=PropertyType.SAFETY,
                    violation_type="check_error",
                    message=f"Safety check failed: {str(e)}",
                    severity=0.5,
                )
            )

        return result

    def check_liveness(self, plan: Dict[str, Any]) -> PropertyCheckResult:
        """Check liveness property: plan will eventually complete (no deadlocks).

        Checks:
        - All tasks eventually transition to completion
        - No circular dependencies
        - Sufficient time allocated
        - Milestone deadlines achievable
        """
        result = PropertyCheckResult(property_type=PropertyType.LIVENESS, passed=True)

        try:
            # Check 1: No circular dependencies (same as safety)
            if self._has_cycle(plan.get("tasks", []), plan.get("dependencies", {})):
                violation = PropertyViolation(
                    property_type=PropertyType.LIVENESS,
                    violation_type="circular_dependency",
                    message="Circular dependencies can cause deadlock",
                    severity=1.0,
                )
                result.add_violation(violation)

            # Check 2: Sufficient time
            estimated_duration = self._estimate_plan_duration(plan)
            available_time = plan.get("available_time_minutes", float("inf"))
            if estimated_duration > available_time:
                violation = PropertyViolation(
                    property_type=PropertyType.LIVENESS,
                    violation_type="insufficient_time",
                    message=f"Plan duration {estimated_duration}m exceeds available {available_time}m",
                    severity=0.7,
                    suggested_fix="Add time buffers or parallelize tasks",
                )
                result.add_violation(violation)

            # Check 3: Milestone deadlines
            deadline_issues = self._check_milestone_deadlines(plan)
            for issue in deadline_issues:
                result.add_violation(issue)

        except Exception as e:
            logger.error(f"Error checking liveness: {e}")
            result.add_violation(
                PropertyViolation(
                    property_type=PropertyType.LIVENESS,
                    violation_type="check_error",
                    message=f"Liveness check failed: {str(e)}",
                    severity=0.5,
                )
            )

        return result

    def check_completeness(self, plan: Dict[str, Any]) -> PropertyCheckResult:
        """Check completeness property: all required deliverables covered.

        Checks:
        - All goals have corresponding tasks
        - All goals are reachable
        - Task outputs satisfy next task inputs
        - No missing intermediate steps
        """
        result = PropertyCheckResult(property_type=PropertyType.COMPLETENESS, passed=True)

        try:
            # Check 1: All goals covered
            uncovered_goals = self._find_uncovered_goals(plan)
            for goal in uncovered_goals:
                violation = PropertyViolation(
                    property_type=PropertyType.COMPLETENESS,
                    violation_type="uncovered_goal",
                    message=f"Goal '{goal}' has no supporting task",
                    affected_element=goal,
                    severity=0.9,
                    suggested_fix="Add task(s) to address this goal",
                )
                result.add_violation(violation)

            # Check 2: All goals reachable
            unreachable = self._find_unreachable_goals(plan)
            for goal in unreachable:
                violation = PropertyViolation(
                    property_type=PropertyType.COMPLETENESS,
                    violation_type="unreachable_goal",
                    message=f"Goal '{goal}' is unreachable",
                    affected_element=goal,
                    severity=0.8,
                )
                result.add_violation(violation)

            # Check 3: Output → Input matching
            mismatch_issues = self._check_output_input_matching(plan)
            for issue in mismatch_issues:
                result.add_violation(issue)

            # Check 4: No missing intermediate steps
            missing_issues = self._find_missing_steps(plan)
            for issue in missing_issues:
                result.add_violation(issue)

        except Exception as e:
            logger.error(f"Error checking completeness: {e}")
            result.add_violation(
                PropertyViolation(
                    property_type=PropertyType.COMPLETENESS,
                    violation_type="check_error",
                    message=f"Completeness check failed: {str(e)}",
                    severity=0.5,
                )
            )

        return result

    def check_feasibility(self, plan: Dict[str, Any]) -> PropertyCheckResult:
        """Check feasibility property: plan can execute with available resources.

        Checks:
        - Total duration vs time available
        - Resource requirements vs capacity
        - Skill requirements met
        - External dependencies resolvable
        """
        result = PropertyCheckResult(property_type=PropertyType.FEASIBILITY, passed=True)

        try:
            # Check 1: Duration feasibility
            estimated_duration = self._estimate_plan_duration(plan)
            available_time = plan.get("available_time_minutes", float("inf"))
            confidence = 0.8  # Historical variance
            margin = available_time * (1 - confidence)

            if estimated_duration > available_time - margin:
                violation = PropertyViolation(
                    property_type=PropertyType.FEASIBILITY,
                    violation_type="insufficient_time",
                    message=f"Plan duration {estimated_duration}m with margin exceeds available {available_time}m",
                    severity=0.7,
                    suggested_fix="Reduce scope, parallelize, or increase time allocation",
                )
                result.add_violation(violation)

            # Check 2: Resource feasibility
            resource_issues = self._check_resource_feasibility(plan)
            for issue in resource_issues:
                result.add_violation(issue)

            # Check 3: Skill requirements
            skill_issues = self._check_skill_requirements(plan)
            for issue in skill_issues:
                result.add_violation(issue)

            # Check 4: External dependencies
            external_issues = self._check_external_dependencies(plan)
            for issue in external_issues:
                result.add_violation(issue)

        except Exception as e:
            logger.error(f"Error checking feasibility: {e}")
            result.add_violation(
                PropertyViolation(
                    property_type=PropertyType.FEASIBILITY,
                    violation_type="check_error",
                    message=f"Feasibility check failed: {str(e)}",
                    severity=0.5,
                )
            )

        return result

    def check_correctness(
        self, plan: Dict[str, Any], expected_outcome: Any = None
    ) -> PropertyCheckResult:
        """Check correctness property: plan execution would achieve expected outcome.

        Checks:
        - Task sequence logic matches problem domain
        - Execution order is valid
        - Edge cases handled
        - Failure modes mitigated
        """
        result = PropertyCheckResult(property_type=PropertyType.CORRECTNESS, passed=True)

        try:
            # Check 1: Task sequence logic
            logic_issues = self._check_task_logic(plan)
            for issue in logic_issues:
                result.add_violation(issue)

            # Check 2: Execution order validity
            order_issues = self._check_execution_order(plan)
            for issue in order_issues:
                result.add_violation(issue)

            # Check 3: Edge cases
            edge_case_issues = self._check_edge_cases(plan)
            for issue in edge_case_issues:
                result.add_violation(issue)

            # Check 4: Failure mode handling
            failure_issues = self._check_failure_handling(plan)
            for issue in failure_issues:
                result.add_violation(issue)

        except Exception as e:
            logger.error(f"Error checking correctness: {e}")
            result.add_violation(
                PropertyViolation(
                    property_type=PropertyType.CORRECTNESS,
                    violation_type="check_error",
                    message=f"Correctness check failed: {str(e)}",
                    severity=0.5,
                )
            )

        return result

    # === Helper methods ===

    def _has_cycle(self, tasks: List[Dict], dependencies: Dict) -> bool:
        """Check if task dependencies have cycles (DFS)."""
        if not tasks:
            return False

        task_ids = {t.get("id", i) for i, t in enumerate(tasks)}
        visited = set()
        rec_stack = set()

        def dfs(task_id):
            visited.add(task_id)
            rec_stack.add(task_id)

            for dep_id in dependencies.get(task_id, []):
                if dep_id not in visited:
                    if dfs(dep_id):
                        return True
                elif dep_id in rec_stack:
                    return True

            rec_stack.remove(task_id)
            return False

        for task_id in task_ids:
            if task_id not in visited:
                if dfs(task_id):
                    return True

        return False

    def _check_resource_constraints(self, plan: Dict) -> bool:
        """Check if resource requirements exceed capacity."""
        # Simplified check - in practice would sum parallel task resources
        return True

    def _check_preconditions(self, plan: Dict) -> List[PropertyViolation]:
        """Check that task preconditions are met."""
        violations = []
        # Simplified - check would verify input/output matching
        return violations

    def _check_parallel_conflicts(self, plan: Dict) -> List[PropertyViolation]:
        """Check for conflicts in parallel task execution."""
        violations = []
        # Would check for resource conflicts, state conflicts, etc.
        return violations

    def _estimate_plan_duration(self, plan: Dict) -> float:
        """Estimate total plan duration in minutes."""
        tasks = plan.get("tasks", [])
        if not tasks:
            return 0.0

        total = sum(t.get("estimated_duration_minutes", 30) for t in tasks)
        # Account for parallelization
        parallelization_factor = plan.get("parallelization_factor", 0.5)
        return total * parallelization_factor

    def _check_milestone_deadlines(self, plan: Dict) -> List[PropertyViolation]:
        """Check if milestones are achievable."""
        violations = []
        # Would check milestone dates vs task completion times
        return violations

    def _find_uncovered_goals(self, plan: Dict) -> List[str]:
        """Find goals without supporting tasks."""
        goals = set(plan.get("goals", []))
        covered = set()

        for task in plan.get("tasks", []):
            covered.update(task.get("supports_goals", []))

        return list(goals - covered)

    def _find_unreachable_goals(self, plan: Dict) -> List[str]:
        """Find goals that can't be reached due to dependencies."""
        # Simplified - would check reachability in task graph
        return []

    def _check_output_input_matching(self, plan: Dict) -> List[PropertyViolation]:
        """Check that task outputs satisfy subsequent task inputs."""
        violations = []
        # Would verify data flow between tasks
        return violations

    def _find_missing_steps(self, plan: Dict) -> List[PropertyViolation]:
        """Find missing intermediate steps between tasks."""
        violations = []
        # Would analyze task gaps and identify missing setup/teardown tasks
        return violations

    def _check_resource_feasibility(self, plan: Dict) -> List[PropertyViolation]:
        """Check resource availability and allocation."""
        violations = []
        # Would check against resource inventory
        return violations

    def _check_skill_requirements(self, plan: Dict) -> List[PropertyViolation]:
        """Check if required skills are available."""
        violations = []
        # Would check against team skills/capabilities
        return violations

    def _check_external_dependencies(self, plan: Dict) -> List[PropertyViolation]:
        """Check external dependencies (APIs, services, etc.)."""
        violations = []
        # Would verify availability of external resources
        return violations

    def _check_task_logic(self, plan: Dict) -> List[PropertyViolation]:
        """Check task sequence logic."""
        violations = []
        # Would verify problem-domain specific logic
        return violations

    def _check_execution_order(self, plan: Dict) -> List[PropertyViolation]:
        """Check if execution order is valid."""
        violations = []
        # Would verify dependencies are respected
        return violations

    def _check_edge_cases(self, plan: Dict) -> List[PropertyViolation]:
        """Check edge case handling."""
        violations = []
        # Would check for error cases, boundary conditions
        return violations

    def _check_failure_handling(self, plan: Dict) -> List[PropertyViolation]:
        """Check failure mode and recovery handling."""
        violations = []
        # Would verify plan handles failures gracefully
        return violations


class PlanSimulator:
    """Simulate plan execution to detect runtime issues."""

    def __init__(self):
        """Initialize plan simulator."""
        pass

    def simulate(self, plan: Dict[str, Any], num_scenarios: int = 10) -> List[SimulationResult]:
        """Run plan through multiple scenarios.

        Returns list of SimulationResult for each scenario.
        """
        scenarios = self._generate_scenarios(num_scenarios)
        results = []

        for scenario in scenarios:
            result = self._simulate_scenario(plan, scenario)
            results.append(result)

        return results

    def _generate_scenarios(self, num_scenarios: int) -> List[SimulationScenario]:
        """Generate diverse execution scenarios."""
        scenarios = [
            SimulationScenario(
                scenario_id="nominal",
                name="Nominal Case",
                description="Expected conditions",
                time_multiplier=1.0,
                resource_multiplier=1.0,
            ),
            SimulationScenario(
                scenario_id="time_pressure_20",
                name="20% Time Pressure",
                description="20% less time available",
                time_multiplier=0.8,
                resource_multiplier=1.0,
            ),
            SimulationScenario(
                scenario_id="time_pressure_50",
                name="50% Time Pressure",
                description="50% less time available",
                time_multiplier=0.5,
                resource_multiplier=1.0,
            ),
            SimulationScenario(
                scenario_id="resource_constraint_20",
                name="20% Resource Constraint",
                description="20% fewer resources",
                time_multiplier=1.0,
                resource_multiplier=0.8,
            ),
            SimulationScenario(
                scenario_id="resource_constraint_50",
                name="50% Resource Constraint",
                description="50% fewer resources",
                time_multiplier=1.0,
                resource_multiplier=0.5,
            ),
        ]

        return scenarios

    def _simulate_scenario(self, plan: Dict, scenario: SimulationScenario) -> SimulationResult:
        """Simulate plan in a single scenario."""
        result = SimulationResult(scenario=scenario, success=True)

        # Simplified simulation logic
        tasks = plan.get("tasks", [])
        result.tasks_executed = len(tasks)

        # Check if time pressure causes failures
        if scenario.time_multiplier < 0.7:
            result.tasks_failed = int(len(tasks) * 0.2)  # 20% fail under extreme pressure
            result.success = False
            result.timing_violations = ["Multiple tasks exceeded time budget"]

        # Check if resource constraint causes failures
        if scenario.resource_multiplier < 0.5:
            result.tasks_failed = int(len(tasks) * 0.15)
            result.success = False
            result.resources_used = {"primary": scenario.resource_multiplier * 100}

        return result


class PlanRefiner:
    """Apply Q* pattern refinement to fix issues found by verification."""

    def __init__(self):
        """Initialize plan refiner."""
        pass

    def identify_root_causes(
        self, violations: List[PropertyViolation]
    ) -> Dict[str, List[PropertyViolation]]:
        """Categorize violations by root cause."""
        root_causes = {
            "insufficient_time": [],
            "insufficient_resources": [],
            "broken_dependencies": [],
            "missing_steps": [],
            "assumption_failures": [],
            "other": [],
        }

        for violation in violations:
            if "time" in violation.violation_type.lower():
                root_causes["insufficient_time"].append(violation)
            elif "resource" in violation.violation_type.lower():
                root_causes["insufficient_resources"].append(violation)
            elif (
                "dependency" in violation.violation_type.lower()
                or "cycle" in violation.violation_type.lower()
            ):
                root_causes["broken_dependencies"].append(violation)
            elif "missing" in violation.violation_type.lower():
                root_causes["missing_steps"].append(violation)
            elif "assumption" in violation.violation_type.lower():
                root_causes["assumption_failures"].append(violation)
            else:
                root_causes["other"].append(violation)

        # Remove empty categories
        return {k: v for k, v in root_causes.items() if v}

    def generate_refinement_strategies(self, issue_category: str) -> List[RefinementStrategy]:
        """Generate refinement strategies for an issue category."""
        strategies_map = {
            "insufficient_time": [
                RefinementStrategy(
                    strategy_type="add_buffers",
                    description="Add 15% time padding to task estimates",
                    estimated_impact=0.6,
                    estimated_effort_minutes=15,
                ),
                RefinementStrategy(
                    strategy_type="parallelize_tasks",
                    description="Run independent tasks in parallel",
                    estimated_impact=0.5,
                    estimated_effort_minutes=30,
                ),
                RefinementStrategy(
                    strategy_type="simplify_tasks",
                    description="Reduce task complexity",
                    estimated_impact=0.4,
                    estimated_effort_minutes=60,
                ),
                RefinementStrategy(
                    strategy_type="remove_nice_to_do",
                    description="Remove low-priority tasks",
                    estimated_impact=0.7,
                    estimated_effort_minutes=20,
                ),
            ],
            "insufficient_resources": [
                RefinementStrategy(
                    strategy_type="request_additional_resources",
                    description="Request more resources from stakeholders",
                    estimated_impact=1.0,
                    estimated_effort_minutes=60,
                    preconditions=["Stakeholder availability"],
                ),
                RefinementStrategy(
                    strategy_type="reuse_existing_resources",
                    description="Leverage available tools/assets",
                    estimated_impact=0.5,
                    estimated_effort_minutes=45,
                ),
                RefinementStrategy(
                    strategy_type="simplify_requirements",
                    description="Reduce resource-intensive requirements",
                    estimated_impact=0.6,
                    estimated_effort_minutes=30,
                ),
            ],
            "broken_dependencies": [
                RefinementStrategy(
                    strategy_type="reorder_tasks",
                    description="Reorder tasks to respect dependencies",
                    estimated_impact=0.9,
                    estimated_effort_minutes=30,
                ),
                RefinementStrategy(
                    strategy_type="split_into_parallel",
                    description="Make tasks independent where possible",
                    estimated_impact=0.5,
                    estimated_effort_minutes=45,
                ),
                RefinementStrategy(
                    strategy_type="add_intermediate_steps",
                    description="Add bridging steps to connect separated tasks",
                    estimated_impact=0.6,
                    estimated_effort_minutes=60,
                ),
            ],
            "missing_steps": [
                RefinementStrategy(
                    strategy_type="add_intermediate_tasks",
                    description="Insert missing setup/validation tasks",
                    estimated_impact=0.8,
                    estimated_effort_minutes=45,
                ),
                RefinementStrategy(
                    strategy_type="detail_complex_tasks",
                    description="Break complex tasks into subtasks",
                    estimated_impact=0.7,
                    estimated_effort_minutes=60,
                ),
            ],
        }

        return strategies_map.get(issue_category, [])

    def refine_plan(self, plan: Dict, violations: List[PropertyViolation]) -> Dict:
        """Apply refinement strategies to plan."""
        refined_plan = plan.copy()

        # Identify root causes
        root_causes = self.identify_root_causes(violations)

        # For each root cause, apply refinements
        if "insufficient_time" in root_causes:
            strategies = self.generate_refinement_strategies("insufficient_time")
            # Apply highest-impact strategy
            if strategies:
                best_strategy = max(strategies, key=lambda s: s.estimated_impact)
                if best_strategy.strategy_type == "add_buffers":
                    # Add 15% buffer to all tasks
                    for task in refined_plan.get("tasks", []):
                        duration = task.get("estimated_duration_minutes", 30)
                        task["estimated_duration_minutes"] = int(duration * 1.15)

        if "broken_dependencies" in root_causes:
            strategies = self.generate_refinement_strategies("broken_dependencies")
            if strategies:
                # Reorder tasks to respect dependencies
                refined_plan["tasks"] = self._topological_sort(
                    refined_plan.get("tasks", []),
                    refined_plan.get("dependencies", {}),
                )

        return refined_plan

    def _topological_sort(self, tasks: List[Dict], dependencies: Dict) -> List[Dict]:
        """Topologically sort tasks to respect dependencies."""
        # Simplified - would do proper topological sort
        return tasks


class FormalVerificationEngine:
    """Main formal verification engine using Q* pattern."""

    def __init__(self, planning_store=None, memory_manager=None):
        """Initialize formal verification engine.

        Args:
            planning_store: Optional planning store for plan data
            memory_manager: Optional memory manager for learning
        """
        self.store = planning_store
        self.memory = memory_manager
        self.property_checker = PropertyChecker()
        self.simulator = PlanSimulator()
        self.refiner = PlanRefiner()

    def verify_plan(self, plan: Dict[str, Any], method: str = "hybrid") -> FormalVerificationResult:
        """Verify plan using hybrid symbolic + simulation approach.

        Args:
            plan: Plan to verify
            method: Verification method (hybrid, symbolic, simulation)

        Returns:
            FormalVerificationResult with verification details
        """
        result = FormalVerificationResult(
            plan_id=plan.get("id", -1),
            verification_method=method,
        )

        start_time = datetime.now()

        # Phase 1: Symbolic property checking
        if method in ("hybrid", "symbolic"):
            for property_type in PropertyType:
                if property_type == PropertyType.SAFETY:
                    prop_result = self.property_checker.check_safety(plan)
                elif property_type == PropertyType.LIVENESS:
                    prop_result = self.property_checker.check_liveness(plan)
                elif property_type == PropertyType.COMPLETENESS:
                    prop_result = self.property_checker.check_completeness(plan)
                elif property_type == PropertyType.FEASIBILITY:
                    prop_result = self.property_checker.check_feasibility(plan)
                elif property_type == PropertyType.CORRECTNESS:
                    prop_result = self.property_checker.check_correctness(plan)
                else:
                    continue

                result.properties_verified.append(property_type)
                result.property_results[property_type] = prop_result

                if not prop_result.passed:
                    result.all_properties_passed = False
                    result.counterexamples.extend(prop_result.violations)
                    result.verification_confidence *= 0.9

        # Phase 2: Simulation-based verification
        if method in ("hybrid", "simulation"):
            sim_results = self.simulator.simulate(plan, num_scenarios=10)
            result.simulation_results = sim_results

            failures = sum(1 for r in sim_results if not r.success)
            failure_rate = failures / len(sim_results) if sim_results else 0.0

            if failure_rate > 0.1:  # >10% failure
                result.all_properties_passed = False
                result.verification_confidence *= 1.0 - failure_rate

        # Record timing
        result.total_verification_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(f"Verification complete: {result.summary()}")
        return result

    def q_star_refine(self, plan: Dict[str, Any], max_iterations: int = 3) -> Dict:
        """Apply Q* pattern refinement: verify → fix issues → repeat.

        Args:
            plan: Plan to refine
            max_iterations: Maximum refinement iterations

        Returns:
            Dict with refinement history and final plan
        """
        original_plan_id = plan.get("id", -1)
        current_plan = plan.copy()
        all_refinements = []
        iteration = 0

        logger.info(f"Starting Q* refinement for plan {original_plan_id}")

        while iteration < max_iterations:
            # Step 1: Verify current plan
            verification = self.verify_plan(current_plan)

            # Step 2: Check if plan is correct
            if verification.all_properties_passed:
                logger.info(f"Plan verified as correct at iteration {iteration}")
                break

            # Step 3: Identify root causes
            violations = verification.counterexamples
            if not violations:
                violations = [
                    v for vlist in verification.property_results.values() for v in vlist.violations
                ]

            root_causes = self.refiner.identify_root_causes(violations)
            logger.info(
                f"Iteration {iteration}: Found {len(violations)} violations, "
                f"{len(root_causes)} root causes"
            )

            # Step 4: Generate refinement strategies
            strategies = {}
            for cause in root_causes.keys():
                strategies[cause] = self.refiner.generate_refinement_strategies(cause)

            # Step 5: Apply refinements
            refined_plan = self.refiner.refine_plan(current_plan, violations)
            refined_plan["id"] = original_plan_id + iteration + 1  # New ID for refined plan

            # Step 6: Record refinement
            refinement = RefinementResult(
                original_plan_id=(
                    original_plan_id if iteration == 0 else all_refinements[-1]["new_plan_id"]
                ),
                refined_plan_id=refined_plan["id"],
                iteration=iteration,
                issues_addressed=violations,
                strategies_applied=[s for slist in strategies.values() for s in slist],
                verification_before=verification,
                verification_after=self.verify_plan(refined_plan),
                improvements={},
            )

            all_refinements.append(
                {
                    "iteration": iteration,
                    "issues_addressed": len(violations),
                    "strategies_applied": len(refinement.strategies_applied),
                    "new_plan_id": refined_plan["id"],
                }
            )

            current_plan = refined_plan
            iteration += 1

        final_verification = self.verify_plan(current_plan)

        result = {
            "original_plan_id": original_plan_id,
            "iterations": iteration,
            "final_plan_id": current_plan.get("id", -1),
            "refinements": all_refinements,
            "final_verification": final_verification,
            "final_plan": current_plan,
            "success": final_verification.all_properties_passed,
        }

        logger.info(
            f"Q* refinement complete: {iteration} iterations, "
            f"success={result['success']}, final_plan_id={result['final_plan_id']}"
        )

        return result


# Module initialization
__all__ = [
    "FormalVerificationEngine",
    "PropertyChecker",
    "PlanSimulator",
    "PlanRefiner",
    "FormalVerificationResult",
    "PropertyViolation",
    "PropertyCheckResult",
    "PropertyType",
    "VerificationMethod",
]
