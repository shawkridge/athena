"""Planning Optimizer Agent - Pre-execution plan validation and optimization.

Phase 5-8 Agent: Validates plans before execution and suggests optimizations
including parallelization, risk identification, and resource requirements.
"""

from typing import Optional
from dataclasses import dataclass
from ..prospective.store import ProspectiveStore
from ..integration.planning_assistant import PlanningAssistant
from ..core.database import Database


@dataclass
class PlanOptimization:
    """Optimization result for a task plan."""

    task_id: int
    has_parallelization: bool
    parallelizable_steps: list[int]  # Step indices that can run in parallel
    identified_risks: list[str]
    missing_dependencies: list[str]
    resource_requirements: dict
    recommended_sequencing: list[str]
    estimated_duration_hours: float
    required_expertise_level: str


class PlanningOptimizerAgent:
    """Autonomous agent for pre-execution plan optimization.

    Validates plans before tasks enter execution phase and suggests
    optimizations including parallelization, risk identification, and
    resource estimation.
    """

    def __init__(self, db: Database):
        """Initialize planning optimizer agent.

        Args:
            db: Database connection for accessing task data
        """
        self.db = db
        self.store = ProspectiveStore(db)
        self.assistant = PlanningAssistant(db)

    async def validate_and_optimize(self, task_id: int) -> PlanOptimization:
        """Validate task plan and suggest optimizations.

        Args:
            task_id: Task to optimize

        Returns:
            PlanOptimization with suggestions and resource estimates
        """
        # Get the task
        task = self.store.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Generate optimization suggestions
        suggestions = await self.assistant.optimize_plan(task)

        # Estimate resources
        resources = await self.assistant.estimate_resources(task)

        # Extract parallelizable steps
        parallelizable_steps = []
        if suggestions:
            for i, suggestion in enumerate(suggestions):
                if hasattr(suggestion, "suggestion_type") and (
                    suggestion.suggestion_type == "parallelization"
                    or "parallel" in str(suggestion).lower()
                ):
                    parallelizable_steps.append(i)

        # Extract risks and dependencies
        identified_risks = []
        missing_dependencies = []

        if suggestions:
            for suggestion in suggestions:
                if hasattr(suggestion, "suggestion_type"):
                    if suggestion.suggestion_type == "risk":
                        if hasattr(suggestion, "recommendation"):
                            identified_risks.append(suggestion.recommendation)
                    elif suggestion.suggestion_type == "dependency":
                        if hasattr(suggestion, "recommendation"):
                            missing_dependencies.append(
                                suggestion.recommendation
                            )

        # Build resource requirements
        resource_requirements = {
            "time_hours": resources.get("time_hours", 0)
            if isinstance(resources, dict)
            else getattr(resources, "time_hours", 0),
            "expertise_level": resources.get("expertise_level", "medium")
            if isinstance(resources, dict)
            else getattr(resources, "expertise_level", "medium"),
            "tools_required": resources.get("tools_required", [])
            if isinstance(resources, dict)
            else getattr(resources, "tools_required", []),
            "dependencies": resources.get("dependencies", [])
            if isinstance(resources, dict)
            else getattr(resources, "dependencies", []),
        }

        # Generate recommended sequencing
        recommended_sequencing = self._generate_sequencing(
            task, parallelizable_steps
        )

        # Estimate total duration
        estimated_duration = resource_requirements.get("time_hours", 0)

        return PlanOptimization(
            task_id=task_id,
            has_parallelization=len(parallelizable_steps) > 0,
            parallelizable_steps=parallelizable_steps,
            identified_risks=identified_risks[:5],  # Top 5 risks
            missing_dependencies=missing_dependencies[:5],  # Top 5 deps
            resource_requirements=resource_requirements,
            recommended_sequencing=recommended_sequencing,
            estimated_duration_hours=estimated_duration,
            required_expertise_level=resource_requirements.get(
                "expertise_level", "medium"
            ),
        )

    def _generate_sequencing(
        self, task, parallelizable_steps: list[int]
    ) -> list[str]:
        """Generate recommended step sequencing.

        Args:
            task: Task with plan
            parallelizable_steps: Indices of parallelizable steps

        Returns:
            List of sequencing recommendations
        """
        recommendations = []

        # Check for parallelization opportunities
        if parallelizable_steps:
            recommendations.append(
                f"Steps {parallelizable_steps} can run in parallel to reduce duration"
            )

        # Check for dependency order
        if hasattr(task, "blocked_reason") and task.blocked_reason:
            recommendations.append(
                f"Resolve blocker first: {task.blocked_reason}"
            )

        # Add progressive validation strategy
        if hasattr(task, "phase") and str(task.phase).upper() == "PLANNING":
            recommendations.append(
                "Validate assumptions with stakeholder before PLAN_READY"
            )

        # Add risk mitigation
        if (
            hasattr(task, "priority")
            and str(task.priority).upper() == "CRITICAL"
        ):
            recommendations.append(
                "Critical priority: Consider having backup person available"
            )

        # Default recommendations
        if not recommendations:
            recommendations.append("Proceed with sequential execution")
            recommendations.append("Validate each step completion before next")

        return recommendations

    async def should_block_execution(self, task_id: int) -> bool:
        """Check if execution should be blocked pending optimization.

        Args:
            task_id: Task to check

        Returns:
            True if optimization issues require resolution before execution
        """
        try:
            optimization = await self.validate_and_optimize(task_id)

            # Block if multiple risks identified
            if len(optimization.identified_risks) >= 2:
                return True

            # Block if critical dependencies missing
            if "critical" in str(optimization.missing_dependencies).lower():
                return True

            # Block if estimated duration seems wrong
            task = self.store.get_task(task_id)
            if (
                task
                and hasattr(task, "estimated_duration_minutes")
                and task.estimated_duration_minutes
            ):
                estimated_hours = task.estimated_duration_minutes / 60
                actual_estimated = optimization.estimated_duration_hours
                if actual_estimated > estimated_hours * 1.5:  # More than 50%
                    return True

            return False
        except Exception:
            return False

    async def get_alternative_plans(
        self, task_id: int, strategy: str = "parallel"
    ) -> list[dict]:
        """Generate alternative execution strategies.

        Args:
            task_id: Task to plan
            strategy: 'parallel', 'sequential', or 'iterative'

        Returns:
            List of alternative plan dictionaries
        """
        task = self.store.get_task(task_id)
        if not task:
            return []

        alternatives = []

        # Generate sequential plan
        sequential_plan = await self.assistant.generate_plan(task)
        alternatives.append(
            {
                "strategy": "sequential",
                "description": "Execute steps in order, fully complete each step",
                "estimated_duration_hours": (
                    sequential_plan.get("estimated_duration")
                    if isinstance(sequential_plan, dict)
                    else getattr(
                        sequential_plan, "estimated_duration", 0
                    )
                ),
                "risk_level": "low",
                "best_for": "Complex tasks with strict dependencies",
            }
        )

        # Generate parallel plan
        optimization = await self.validate_and_optimize(task_id)
        if optimization.has_parallelization:
            alternatives.append(
                {
                    "strategy": "parallel",
                    "description": f"Run steps {optimization.parallelizable_steps} in parallel",
                    "estimated_duration_hours": optimization.estimated_duration_hours
                    * 0.7,  # 30% speedup
                    "risk_level": "medium",
                    "best_for": "Time-sensitive tasks with parallelizable steps",
                }
            )

        # Generate iterative/incremental plan
        alternatives.append(
            {
                "strategy": "iterative",
                "description": "Build incrementally, get feedback after each iteration",
                "estimated_duration_hours": optimization.estimated_duration_hours
                * 1.2,  # 20% longer
                "risk_level": "low",
                "best_for": "Novel tasks requiring continuous validation",
            }
        )

        return alternatives
