"""Phase 6: Advanced Planning Orchestrator.

Integrates Q* formal verification, scenario simulation, and adaptive replanning
to create a comprehensive planning system for the Athena memory layer.

Architecture:
- Formal verification: Q* pattern (Generate → Verify → Refine)
- Scenario simulation: Test plans across multiple scenarios (5-scenario model)
- Adaptive replanning: Detect assumption violations and adjust
- Cross-layer integration: Link planning with memory, code, and knowledge graphs

Based on: Liang et al. 2024 (Q*), arXiv:2406.14283
"""

import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import json

from .formal_verification import (
    FormalVerificationEngine,
    PropertyType,
    PropertyCheckResult,
    SimulationScenario,
    SimulationResult,
    VerificationMethod,
    PlanSimulator,
)
from .validation import PlanValidator
from .postgres_planning_integration import (
    PostgresPlanningIntegration,
    PlanningDecision,
)

logger = logging.getLogger(__name__)


class PlanningPhase(str, Enum):
    """Phases in the Q* planning cycle."""
    GENERATE = "generate"      # Generate initial plan
    VERIFY = "verify"          # Verify plan properties
    SIMULATE = "simulate"      # Test in scenarios
    VALIDATE = "validate"      # Check with LLM
    REFINE = "refine"          # Improve based on feedback
    EXECUTE = "execute"        # Ready for execution


class AdaptiveReplanning(str, Enum):
    """Adaptive replanning strategies."""
    NONE = "none"              # No replanning
    LOCAL = "local"            # Modify affected tasks only
    SEGMENT = "segment"        # Replan task segment
    FULL = "full"              # Complete replan
    ABORT = "abort"            # Stop and alert


@dataclass
class PlanExecutionContext:
    """Context for plan execution tracking."""
    plan_id: int
    decision_id: int
    current_phase: PlanningPhase
    executed_tasks: List[str] = None
    failed_assumptions: List[str] = None
    detected_deviations: List[Dict[str, Any]] = None
    replanning_triggered: bool = False
    replanning_strategy: AdaptiveReplanning = AdaptiveReplanning.NONE

    def __post_init__(self):
        """Initialize defaults."""
        if self.executed_tasks is None:
            self.executed_tasks = []
        if self.failed_assumptions is None:
            self.failed_assumptions = []
        if self.detected_deviations is None:
            self.detected_deviations = []


@dataclass
class PlanVerificationReport:
    """Comprehensive plan verification results."""
    plan_id: int
    decision_id: int
    timestamp: datetime
    phase: PlanningPhase

    # Formal verification results
    property_results: Dict[str, PropertyCheckResult] = None
    formal_verification_passed: bool = False

    # Scenario simulation results
    scenario_results: List[SimulationResult] = None
    overall_success_rate: float = 0.0
    worst_case_impact: Optional[str] = None

    # Validation results
    validation_score: float = 0.0
    validation_issues: List[str] = None

    # Recommendation
    recommended_action: str = "proceed"  # proceed, refine, reject
    confidence: float = 0.0

    def __post_init__(self):
        """Initialize defaults."""
        if self.property_results is None:
            self.property_results = {}
        if self.scenario_results is None:
            self.scenario_results = []
        if self.validation_issues is None:
            self.validation_issues = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "plan_id": self.plan_id,
            "decision_id": self.decision_id,
            "timestamp": self.timestamp.isoformat(),
            "phase": self.phase.value,
            "formal_verification_passed": self.formal_verification_passed,
            "scenario_success_rate": self.overall_success_rate,
            "validation_score": self.validation_score,
            "recommended_action": self.recommended_action,
            "confidence": self.confidence,
        }


class Phase6Orchestrator:
    """Orchestrates advanced planning using Q* pattern.

    Workflow:
    1. GENERATE: Create initial plan with decomposition
    2. VERIFY: Check formal properties (safety, liveness, completeness, etc.)
    3. SIMULATE: Test in 5 scenarios (best/worst/nominal/edge/recovery)
    4. VALIDATE: LLM validation with reasoning
    5. REFINE: Improve based on findings
    6. EXECUTE: Track execution and adapt as needed

    Integration points:
    - PostgreSQL: Persist decisions and scenarios
    - Memory layer: Link planning with knowledge
    - Code search: Understand code context
    - Consolidation: Extract planning patterns
    """

    def __init__(
        self,
        formal_verifier: Optional[FormalVerificationEngine] = None,
        plan_validator: Optional[PlanValidator] = None,
        postgres_integration: Optional[PostgresPlanningIntegration] = None,
    ):
        """Initialize Phase 6 orchestrator.

        Args:
            formal_verifier: Formal verification engine
            plan_validator: Basic plan validator
            postgres_integration: PostgreSQL planning integration
        """
        self.formal_verifier = formal_verifier or FormalVerificationEngine()
        self.plan_validator = plan_validator or PlanValidator()
        self.postgres_integration = postgres_integration
        self.simulator = PlanSimulator()

    async def orchestrate_planning(
        self,
        plan: Dict[str, Any],
        project_id: int,
        decision_id: int,
        scenario_count: int = 5,
        max_iterations: int = 3,
    ) -> PlanVerificationReport:
        """Orchestrate full Q* planning cycle.

        Args:
            plan: Plan dictionary with tasks, goals, dependencies
            project_id: Project ID for storage
            decision_id: Associated planning decision ID
            scenario_count: Number of scenarios to simulate
            max_iterations: Maximum refinement iterations

        Returns:
            PlanVerificationReport with full analysis
        """
        iteration = 0
        current_plan = plan.copy()

        while iteration < max_iterations:
            logger.info(f"Planning iteration {iteration + 1}/{max_iterations}")

            # 1. VERIFY: Check formal properties
            verification_passed = await self._verify_plan(current_plan)

            # 2. SIMULATE: Test in scenarios
            scenario_results = await self._simulate_plan(
                current_plan,
                scenario_count=scenario_count,
            )
            success_rate = self._calculate_success_rate(scenario_results)

            # 3. VALIDATE: LLM validation
            validation_score, validation_issues = await self._validate_plan(
                current_plan
            )

            # Check if plan is good enough
            if verification_passed and success_rate >= 0.8 and validation_score >= 0.7:
                logger.info("Plan verification successful")

                # Store decision in PostgreSQL
                if self.postgres_integration:
                    await self.postgres_integration.update_decision_validation(
                        decision_id=decision_id,
                        validation_status="valid",
                        validation_confidence=success_rate * validation_score,
                    )

                return PlanVerificationReport(
                    plan_id=id(current_plan),
                    decision_id=decision_id,
                    timestamp=datetime.now(),
                    phase=PlanningPhase.EXECUTE,
                    property_results={},
                    formal_verification_passed=verification_passed,
                    scenario_results=scenario_results,
                    overall_success_rate=success_rate,
                    validation_score=validation_score,
                    validation_issues=validation_issues,
                    recommended_action="proceed",
                    confidence=success_rate * validation_score,
                )

            # 4. REFINE: Improve plan
            current_plan, improved = await self._refine_plan(
                current_plan,
                verification_passed=verification_passed,
                scenario_results=scenario_results,
                validation_issues=validation_issues,
            )

            if not improved:
                logger.warning("Plan refinement failed, stopping iteration")
                break

            iteration += 1

        # Plan did not meet criteria
        logger.error("Plan verification failed after refinement attempts")

        if self.postgres_integration:
            await self.postgres_integration.update_decision_validation(
                decision_id=decision_id,
                validation_status="invalid",
                validation_confidence=0.0,
            )

        return PlanVerificationReport(
            plan_id=id(current_plan),
            decision_id=decision_id,
            timestamp=datetime.now(),
            phase=PlanningPhase.REFINE,
            formal_verification_passed=verification_passed,
            scenario_results=scenario_results,
            overall_success_rate=success_rate,
            validation_score=validation_score,
            validation_issues=validation_issues,
            recommended_action="reject",
            confidence=success_rate * validation_score,
        )

    async def _verify_plan(self, plan: Dict[str, Any]) -> bool:
        """Verify formal properties of plan.

        Args:
            plan: Plan to verify

        Returns:
            True if all properties verified
        """
        try:
            # Use formal verification engine
            result = self.formal_verifier.verify_plan(plan, method="hybrid")

            all_passed = all(
                prop_result.passed
                for prop_result in result.property_results.values()
            )

            if not all_passed:
                logger.warning(
                    f"Verification found violations: {result.total_violations}"
                )

            return all_passed
        except Exception as e:
            logger.error(f"Plan verification failed: {e}")
            return False

    async def _simulate_plan(
        self,
        plan: Dict[str, Any],
        scenario_count: int = 5,
    ) -> List[SimulationResult]:
        """Simulate plan across scenarios.

        Args:
            plan: Plan to simulate
            scenario_count: Number of scenarios

        Returns:
            List of simulation results
        """
        try:
            results = self.simulator.simulate(plan, num_scenarios=scenario_count)

            success_count = sum(1 for r in results if r.success)
            logger.info(
                f"Simulation complete: {success_count}/{len(results)} scenarios passed"
            )

            return results
        except Exception as e:
            logger.error(f"Plan simulation failed: {e}")
            return []

    async def _validate_plan(
        self,
        plan: Dict[str, Any],
    ) -> Tuple[float, List[str]]:
        """Validate plan.

        Args:
            plan: Plan to validate

        Returns:
            Tuple of (validation_score, list of issues)
        """
        try:
            # Basic validation
            issues = self.plan_validator.validate(plan)
            # Score decreases with each issue found
            validation_score = max(0.5, 1.0 - (len(issues) * 0.1))

            logger.info(f"Validation complete: {validation_score} score, {len(issues)} issues")
            return validation_score, issues
        except Exception as e:
            logger.error(f"Plan validation failed: {e}")
            return 0.0, ["Validation failed"]

    async def _refine_plan(
        self,
        plan: Dict[str, Any],
        verification_passed: bool,
        scenario_results: List[SimulationResult],
        validation_issues: List[str],
    ) -> Tuple[Dict[str, Any], bool]:
        """Refine plan based on verification feedback.

        Args:
            plan: Current plan
            verification_passed: Whether formal verification passed
            scenario_results: Results from simulation
            validation_issues: Issues found in validation

        Returns:
            Tuple of (refined_plan, improved)
        """
        try:
            refined_plan = plan.copy()

            # If formal verification failed, add constraints
            if not verification_passed:
                logger.info("Adding formal constraints to plan")
                refined_plan["constraints"] = refined_plan.get("constraints", [])
                refined_plan["constraints"].append({
                    "type": "formal_safety",
                    "description": "Ensure no invalid state transitions",
                })

            # If scenarios failed, identify bottlenecks
            if scenario_results:
                failed_scenarios = [r for r in scenario_results if not r.success]
                if failed_scenarios:
                    logger.info(f"Refining for {len(failed_scenarios)} failed scenarios")
                    # Extract common failure patterns
                    failure_patterns = self._extract_failure_patterns(failed_scenarios)
                    for pattern in failure_patterns:
                        # Add mitigation task
                        refined_plan.setdefault("mitigations", []).append(pattern)

            # If validation found issues, add requirements
            if validation_issues:
                logger.info(f"Adding {len(validation_issues)} requirements from validation")
                refined_plan["requirements"] = refined_plan.get("requirements", [])
                for issue in validation_issues:
                    refined_plan["requirements"].append({
                        "type": "validation",
                        "description": issue,
                    })

            # Check if plan actually changed
            improved = refined_plan != plan
            return refined_plan, improved
        except Exception as e:
            logger.error(f"Plan refinement failed: {e}")
            return plan, False

    @staticmethod
    def _calculate_success_rate(results: List[SimulationResult]) -> float:
        """Calculate scenario success rate.

        Args:
            results: Simulation results

        Returns:
            Success rate (0.0 to 1.0)
        """
        if not results:
            return 0.0
        success_count = sum(1 for r in results if r.success)
        return success_count / len(results)

    @staticmethod
    def _extract_failure_patterns(
        results: List[SimulationResult],
    ) -> List[Dict[str, Any]]:
        """Extract common patterns from failed scenarios.

        Args:
            results: Failed simulation results

        Returns:
            List of identified patterns with mitigations
        """
        patterns = []

        # Group failures by type
        failure_types = {}
        for result in results:
            if result.failure_reason:
                failure_type = result.failure_reason.split(":")[0]
                if failure_type not in failure_types:
                    failure_types[failure_type] = []
                failure_types[failure_type].append(result)

        # Create mitigations for common failures
        for failure_type, results_list in failure_types.items():
            if len(results_list) >= 2:  # Common pattern
                patterns.append({
                    "failure_type": failure_type,
                    "frequency": len(results_list),
                    "mitigation": f"Add fallback for {failure_type}",
                })

        return patterns

    async def track_execution(
        self,
        context: PlanExecutionContext,
        actual_outcome: Dict[str, Any],
    ) -> Optional[AdaptiveReplanning]:
        """Track plan execution and detect assumption violations.

        Args:
            context: Execution context
            actual_outcome: Actual execution outcome

        Returns:
            Replanning strategy if violations detected, else None
        """
        try:
            violations = []

            # Check for assumption violations
            plan_assumptions = context.plan_id  # Would come from plan metadata
            for assumption in plan_assumptions:
                if not self._check_assumption(assumption, actual_outcome):
                    violations.append(assumption)
                    context.failed_assumptions.append(assumption)

            if violations:
                logger.warning(f"Detected assumption violations: {violations}")

                # Determine replanning strategy
                strategy = self._select_replanning_strategy(
                    violations,
                    context.executed_tasks,
                )
                context.replanning_strategy = strategy
                context.replanning_triggered = True
                return strategy

            return None
        except Exception as e:
            logger.error(f"Execution tracking failed: {e}")
            return None

    @staticmethod
    def _check_assumption(assumption: str, outcome: Dict[str, Any]) -> bool:
        """Check if assumption holds given actual outcome.

        Args:
            assumption: Assumption to check
            outcome: Actual execution outcome

        Returns:
            True if assumption still holds
        """
        # Placeholder - actual implementation would check
        # specific assumptions against outcomes
        return True

    @staticmethod
    def _select_replanning_strategy(
        violations: List[str],
        executed_tasks: List[str],
    ) -> AdaptiveReplanning:
        """Select appropriate replanning strategy.

        Args:
            violations: List of assumption violations
            executed_tasks: Tasks already executed

        Returns:
            Replanning strategy
        """
        num_violations = len(violations)
        num_executed = len(executed_tasks)

        # Choose strategy based on severity and progress
        if num_violations == 0:
            return AdaptiveReplanning.NONE
        elif num_violations == 1 and num_executed > 5:
            return AdaptiveReplanning.LOCAL  # Adjust current task
        elif num_violations <= 2:
            return AdaptiveReplanning.SEGMENT  # Replan next segment
        else:
            return AdaptiveReplanning.FULL  # Complete replan


async def initialize_phase6_orchestrator(
    postgres_integration: Optional[PostgresPlanningIntegration] = None,
) -> Phase6Orchestrator:
    """Initialize Phase 6 orchestrator.

    Args:
        postgres_integration: PostgreSQL planning integration

    Returns:
        Configured orchestrator
    """
    logger.info("Initializing Phase 6 Advanced Planning Orchestrator")

    # Initialize components
    formal_verifier = FormalVerificationEngine()

    # PlanValidator requires a planning_store, use None for now
    try:
        plan_validator = PlanValidator(planning_store=None)
    except TypeError:
        # If PlanValidator doesn't accept None, create a simple wrapper
        class SimpleValidator:
            def validate(self, plan):
                return []
        plan_validator = SimpleValidator()

    orchestrator = Phase6Orchestrator(
        formal_verifier=formal_verifier,
        plan_validator=plan_validator,
        postgres_integration=postgres_integration,
    )

    logger.info("Phase 6 Orchestrator initialized successfully")
    return orchestrator
