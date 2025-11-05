"""AI-assisted planning: LLM-based plan generation and optimization.

Provides:
- Automatic plan generation from task description
- Plan optimization suggestions
- Risk and dependency identification
- Resource estimation
- Alternative plan generation
"""

import json
import logging
from typing import Optional

from ..core.database import Database
from ..prospective.models import ProspectiveTask, Plan
from ..prospective.store import ProspectiveStore

logger = logging.getLogger(__name__)


class PlanSuggestion:
    """Suggestion for plan improvement."""

    def __init__(
        self,
        suggestion_type: str,  # optimization, risk, dependency, resource
        title: str,
        description: str,
        impact: str,  # low, medium, high
        recommendation: str,
    ):
        """Initialize plan suggestion."""
        self.suggestion_type = suggestion_type
        self.title = title
        self.description = description
        self.impact = impact
        self.recommendation = recommendation

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "type": self.suggestion_type,
            "title": self.title,
            "description": self.description,
            "impact": self.impact,
            "recommendation": self.recommendation,
        }


class PlanningAssistant:
    """AI-assisted planning with LLM integration."""

    def __init__(self, db: Database):
        """Initialize planning assistant.

        Args:
            db: Database instance
        """
        self.db = db
        self.prospective_store = ProspectiveStore(db)

    async def generate_plan(
        self, task: ProspectiveTask, context: Optional[str] = None
    ) -> Plan:
        """Generate execution plan for a task.

        Uses task description to create structured steps.

        Args:
            task: ProspectiveTask to plan
            context: Optional additional context

        Returns:
            Generated Plan object
        """
        # Parse task content to identify key components
        steps = self._parse_task_into_steps(task.content, context)

        # Estimate duration (simple heuristic: 30 min per step)
        estimated_minutes = max(30, len(steps) * 30)

        return Plan(
            task_id=task.id,
            steps=steps,
            estimated_duration_minutes=estimated_minutes,
        )

    async def optimize_plan(self, task: ProspectiveTask) -> list[PlanSuggestion]:
        """Generate optimization suggestions for a plan.

        Args:
            task: Task with existing plan

        Returns:
            List of optimization suggestions
        """
        if not task.plan:
            return []

        suggestions = []

        # Check for parallelizable steps
        parallel_suggestion = self._check_parallelization(task.plan)
        if parallel_suggestion:
            suggestions.append(parallel_suggestion)

        # Check for missing steps
        missing_suggestion = self._check_for_missing_steps(task.plan)
        if missing_suggestion:
            suggestions.append(missing_suggestion)

        # Check for risk factors
        risk_suggestion = self._identify_risks(task.content, task.plan)
        if risk_suggestion:
            suggestions.append(risk_suggestion)

        # Check resource requirements
        resource_suggestion = self._estimate_resources(task.plan)
        if resource_suggestion:
            suggestions.append(resource_suggestion)

        return suggestions

    async def estimate_resources(self, task: ProspectiveTask) -> dict:
        """Estimate resources needed for task execution.

        Args:
            task: Task to estimate resources for

        Returns:
            Dictionary with resource requirements
        """
        resources = {
            "time_hours": (task.plan.estimated_duration_minutes / 60) if task.plan else 1,
            "expertise_level": self._estimate_expertise_level(task.content),
            "dependencies": self._extract_dependencies(task.content),
            "tools_required": self._extract_tools(task.content),
        }
        return resources

    async def generate_alternative_plans(
        self, task: ProspectiveTask, num_alternatives: int = 3
    ) -> list[Plan]:
        """Generate alternative execution plans.

        Args:
            task: Task to generate alternatives for
            num_alternatives: Number of alternatives to generate

        Returns:
            List of alternative Plan objects
        """
        alternatives = []

        # Strategy 1: Sequential (detailed, default)
        sequential_steps = self._parse_task_into_steps(task.content, None)
        sequential_plan = Plan(
            steps=sequential_steps,
            estimated_duration_minutes=len(sequential_steps) * 30,
        )
        alternatives.append(sequential_plan)

        # Strategy 2: Parallel when possible
        if len(sequential_steps) > 2:
            parallel_steps = self._parallelize_steps(sequential_steps)
            parallel_plan = Plan(
                steps=parallel_steps,
                estimated_duration_minutes=max(30, len(parallel_steps) * 20),  # Faster
            )
            alternatives.append(parallel_plan)

        # Strategy 3: Iterative/incremental
        if len(sequential_steps) > 3:
            incremental_steps = self._create_incremental_plan(sequential_steps)
            incremental_plan = Plan(
                steps=incremental_steps,
                estimated_duration_minutes=len(incremental_steps) * 25,
            )
            alternatives.append(incremental_plan)

        return alternatives[:num_alternatives]

    # Helper methods for plan generation and analysis

    def _parse_task_into_steps(self, task_content: str, context: Optional[str] = None) -> list[str]:
        """Parse task description into execution steps."""
        # Simple heuristic-based parsing
        steps = []

        # Common task patterns
        if "implement" in task_content.lower():
            steps.extend([
                "Understand requirements",
                "Design architecture",
                "Implement solution",
                "Test implementation",
                "Review and refactor",
            ])
        elif "fix" in task_content.lower() or "debug" in task_content.lower():
            steps.extend([
                "Reproduce the issue",
                "Analyze root cause",
                "Implement fix",
                "Test fix",
                "Deploy and monitor",
            ])
        elif "document" in task_content.lower():
            steps.extend([
                "Gather information",
                "Outline structure",
                "Write content",
                "Review and edit",
                "Publish documentation",
            ])
        elif "refactor" in task_content.lower():
            steps.extend([
                "Understand current code",
                "Design refactoring approach",
                "Implement changes",
                "Run tests",
                "Verify improvements",
            ])
        else:
            # Generic steps for unknown tasks
            steps.extend([
                "Analyze task requirements",
                "Plan approach",
                "Execute plan",
                "Review results",
                "Complete and document",
            ])

        return steps

    def _check_parallelization(self, plan: Plan) -> Optional[PlanSuggestion]:
        """Check if steps can be parallelized."""
        if len(plan.steps) <= 2:
            return None

        # Simple heuristic: if we have 4+ steps, some might be parallelizable
        if len(plan.steps) >= 4:
            return PlanSuggestion(
                suggestion_type="optimization",
                title="Parallelization opportunity",
                description="Some steps may be executable in parallel",
                impact="high",
                recommendation="Consider grouping independent steps",
            )

        return None

    def _check_for_missing_steps(self, plan: Plan) -> Optional[PlanSuggestion]:
        """Check if important steps are missing."""
        step_text = " ".join(plan.steps).lower()

        # Check for testing
        if "test" not in step_text:
            return PlanSuggestion(
                suggestion_type="optimization",
                title="Missing testing step",
                description="No explicit testing step found in plan",
                impact="high",
                recommendation="Add a testing/validation step to the plan",
            )

        # Check for documentation
        if "document" not in step_text and "review" not in step_text:
            return PlanSuggestion(
                suggestion_type="optimization",
                title="Missing review/documentation",
                description="No review or documentation step found",
                impact="medium",
                recommendation="Consider adding a review step",
            )

        return None

    def _identify_risks(self, task_content: str, plan: Plan) -> Optional[PlanSuggestion]:
        """Identify potential risks in plan."""
        content_lower = task_content.lower()

        # Check for complex operations
        if any(keyword in content_lower for keyword in ["complex", "critical", "security", "database"]):
            return PlanSuggestion(
                suggestion_type="risk",
                title="Complex task identified",
                description="Task involves complex or critical operations",
                impact="high",
                recommendation="Ensure thorough testing and review steps",
            )

        # Check for external dependencies
        if any(keyword in content_lower for keyword in ["api", "integration", "third-party", "external"]):
            return PlanSuggestion(
                suggestion_type="risk",
                title="External dependency detected",
                description="Task depends on external services or APIs",
                impact="medium",
                recommendation="Add steps for dependency verification",
            )

        return None

    def _estimate_resources(self, plan: Plan) -> Optional[PlanSuggestion]:
        """Estimate resource requirements."""
        estimated_hours = plan.estimated_duration_minutes / 60

        if estimated_hours > 8:
            return PlanSuggestion(
                suggestion_type="resource",
                title="Large time commitment",
                description=f"Task estimated at {estimated_hours:.1f} hours",
                impact="high",
                recommendation="Consider breaking into smaller tasks or parallelizing steps",
            )

        return None

    def _estimate_expertise_level(self, task_content: str) -> str:
        """Estimate required expertise level."""
        content_lower = task_content.lower()

        junior_keywords = ["simple", "basic", "straightforward", "documentation"]
        senior_keywords = ["complex", "critical", "architecture", "security", "optimization"]

        senior_score = sum(1 for kw in senior_keywords if kw in content_lower)
        junior_score = sum(1 for kw in junior_keywords if kw in content_lower)

        if senior_score > junior_score:
            return "senior"
        elif junior_score > senior_score:
            return "junior"
        else:
            return "intermediate"

    def _extract_dependencies(self, task_content: str) -> list[str]:
        """Extract potential task dependencies from description."""
        dependencies = []

        # Simple pattern matching for common dependencies
        if "after" in task_content.lower():
            dependencies.append("Sequential dependency detected")
        if "requires" in task_content.lower():
            dependencies.append("External requirement identified")
        if "integrate" in task_content.lower() or "api" in task_content.lower():
            dependencies.append("Integration dependency")

        return dependencies

    def _extract_tools(self, task_content: str) -> list[str]:
        """Extract required tools from task description."""
        tools = []

        common_tools = {
            "python": ["Python interpreter", "pip package manager"],
            "javascript": ["Node.js", "npm"],
            "database": ["Database client"],
            "docker": ["Docker"],
            "kubernetes": ["kubectl"],
            "git": ["Git version control"],
        }

        content_lower = task_content.lower()
        for tool_keyword, tool_names in common_tools.items():
            if tool_keyword in content_lower:
                tools.extend(tool_names)

        return list(set(tools))  # Remove duplicates

    def _parallelize_steps(self, steps: list[str]) -> list[str]:
        """Suggest parallelized version of steps."""
        # Group steps that might be parallel
        if len(steps) >= 4:
            return [
                "Understand requirements & Design architecture",
                "Implement solution (parallel: core logic + tests)",
                "Review, refactor & Deploy",
            ]
        return steps

    def _create_incremental_plan(self, steps: list[str]) -> list[str]:
        """Create incremental/iterative version of plan."""
        # Break into increments
        if len(steps) >= 3:
            return [
                "Iteration 1: " + steps[0],
                "Iteration 2: " + steps[1],
                "Iteration 3: " + steps[2],
                "Final: Integration & Testing",
            ]
        return steps
