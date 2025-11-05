"""Plan Builder - Convenience wrapper for complete planning workflow.

Chains together generate → optimize → estimate_resources in one operation
for seamless planning experience.

Automatically detects project from working directory.
"""

from typing import Optional, Dict, Any
from ..integration.planning_assistant import PlanningAssistant
from ..prospective.store import ProspectiveStore
from ..core.database import Database
from ..core.project_detector import detect_project_id, get_project_name


class PlanBuilder:
    """Convenience wrapper for complete planning workflow.

    Executes: generate → optimize → estimate_resources in sequence.
    """

    def __init__(self, db: Database, project_id: Optional[int] = None):
        """Initialize plan builder.

        Args:
            db: Database connection
            project_id: Project ID (auto-detected from cwd if not provided)
        """
        self.db = db
        self.store = ProspectiveStore(db)
        self.assistant = PlanningAssistant(db)

        # Auto-detect project from working directory if not provided
        if project_id is None:
            project_id = detect_project_id()

        self.project_id = project_id
        self.project_name = get_project_name(project_id) if project_id else "Unknown"

    async def build_plan(
        self,
        task_id: int,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build complete plan from task (generate → optimize → resources).

        Args:
            task_id: Task to plan
            description: Optional task description for context

        Returns:
            Dictionary with complete plan details:
            {
                "task_id": int,
                "description": str,
                "plan": { ... },
                "optimizations": { ... },
                "resources": { ... },
                "summary": str,
                "status": "ready" | "review_needed" | "blocked"
            }
        """
        # Get task
        task = self.store.get_task(task_id)
        if not task:
            return {"error": f"Task {task_id} not found", "status": "error"}

        # Override description if provided
        if description:
            task.content = description

        result = {
            "task_id": task_id,
            "description": task.content,
            "steps": [],
            "optimizations": [],
            "resources": {},
            "status": "ready",
            "recommendations": [],
        }

        try:
            # STEP 1: Generate Plan
            plan = await self.assistant.generate_plan(task)
            result["plan"] = self._format_plan(plan)
            result["steps"] = self._extract_steps(plan)

            # STEP 2: Optimize Plan
            optimizations = await self.assistant.optimize_plan(task)
            result["optimizations"] = self._format_optimizations(optimizations)

            # STEP 3: Estimate Resources
            resources = await self.assistant.estimate_resources(task)
            result["resources"] = self._format_resources(resources)

            # STEP 4: Assess Overall Status
            result["status"] = self._assess_status(result)
            result["summary"] = self._generate_summary(result)

            return result

        except Exception as e:
            return {
                "error": f"Planning failed: {e}",
                "status": "error",
                "task_id": task_id,
            }

    def _format_plan(self, plan) -> Dict[str, Any]:
        """Format generated plan for output.

        Args:
            plan: Generated plan object/dict

        Returns:
            Formatted plan dictionary
        """
        if isinstance(plan, dict):
            return {
                "strategy": plan.get("strategy", "sequential"),
                "estimated_duration": plan.get("estimated_duration", 0),
                "steps": plan.get("steps", []),
                "complexity": plan.get("complexity", "medium"),
            }
        else:
            return {
                "strategy": getattr(plan, "strategy", "sequential"),
                "estimated_duration": getattr(
                    plan, "estimated_duration", 0
                ),
                "steps": getattr(plan, "steps", []),
                "complexity": getattr(plan, "complexity", "medium"),
            }

    def _extract_steps(self, plan) -> list:
        """Extract execution steps from plan.

        Args:
            plan: Generated plan

        Returns:
            List of step descriptions
        """
        if isinstance(plan, dict):
            steps = plan.get("steps", [])
        else:
            steps = getattr(plan, "steps", [])

        # Format steps as readable list
        formatted = []
        for i, step in enumerate(steps, 1):
            if isinstance(step, dict):
                formatted.append(
                    f"{i}. {step.get('description', step)} "
                    f"({step.get('duration_minutes', '?')} min)"
                )
            else:
                formatted.append(f"{i}. {step}")

        return formatted if formatted else ["1. Execute task"]

    def _format_optimizations(self, optimizations) -> Dict[str, Any]:
        """Format optimization suggestions.

        Args:
            optimizations: Optimization results

        Returns:
            Formatted optimizations dictionary
        """
        if not optimizations:
            return {
                "parallelization": [],
                "risks": [],
                "recommendations": [],
            }

        if isinstance(optimizations, dict):
            return {
                "parallelization": optimizations.get("parallelization", []),
                "risks": optimizations.get("risks", []),
                "recommendations": optimizations.get("recommendations", []),
                "time_savings": optimizations.get("time_savings", "0%"),
            }
        else:
            return {
                "parallelization": getattr(
                    optimizations, "parallelization", []
                ),
                "risks": getattr(optimizations, "risks", []),
                "recommendations": getattr(
                    optimizations, "recommendations", []
                ),
                "time_savings": getattr(
                    optimizations, "time_savings", "0%"
                ),
            }

    def _format_resources(self, resources) -> Dict[str, Any]:
        """Format resource estimates.

        Args:
            resources: Resource estimates

        Returns:
            Formatted resources dictionary
        """
        if isinstance(resources, dict):
            return {
                "time_hours": resources.get("time_hours", 0),
                "expertise_level": resources.get("expertise_level", "medium"),
                "tools_required": resources.get("tools_required", []),
                "dependencies": resources.get("dependencies", []),
                "capacity_available": resources.get("capacity_available", True),
            }
        else:
            return {
                "time_hours": getattr(resources, "time_hours", 0),
                "expertise_level": getattr(
                    resources, "expertise_level", "medium"
                ),
                "tools_required": getattr(
                    resources, "tools_required", []
                ),
                "dependencies": getattr(resources, "dependencies", []),
                "capacity_available": getattr(
                    resources, "capacity_available", True
                ),
            }

    def _assess_status(self, result: Dict[str, Any]) -> str:
        """Assess overall plan status.

        Args:
            result: Planning result

        Returns:
            Status: "ready", "review_needed", or "blocked"
        """
        # Check for blockers
        resources = result.get("resources", {})
        if not resources.get("capacity_available", True):
            return "blocked"

        # Check for multiple risks
        optimizations = result.get("optimizations", {})
        risks = optimizations.get("risks", [])
        if len(risks) > 2:
            return "review_needed"

        # Check duration estimate
        time_hours = resources.get("time_hours", 0)
        if time_hours > 8:
            return "review_needed"

        return "ready"

    def _generate_summary(self, result: Dict[str, Any]) -> str:
        """Generate human-readable summary.

        Args:
            result: Planning result

        Returns:
            Summary string
        """
        status = result.get("status", "unknown")
        description = result.get("description", "Task")
        steps = result.get("steps", [])
        time_hours = result.get("resources", {}).get("time_hours", 0)
        risks = result.get("optimizations", {}).get("risks", [])

        summary_parts = []
        summary_parts.append(f"Plan for: {description}")
        summary_parts.append(f"Steps: {len(steps)}")
        summary_parts.append(f"Duration: {time_hours:.1f} hours")

        if risks:
            summary_parts.append(f"Risks: {len(risks)} identified")

        if status == "blocked":
            summary_parts.append("⚠️ Status: BLOCKED - Address capacity issues")
        elif status == "review_needed":
            summary_parts.append("⚠️ Status: REVIEW RECOMMENDED")
        else:
            summary_parts.append("✓ Status: READY TO EXECUTE")

        return " | ".join(summary_parts)

    async def build_quick_plan(
        self, description: str, project_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Build plan from description text (no task ID required).

        Args:
            description: Task description text
            project_id: Project context (auto-detected if not provided)

        Returns:
            Complete plan dictionary
        """
        # Use provided project_id or fall back to auto-detected
        if project_id is None:
            project_id = self.project_id

        if project_id is None:
            return {
                "error": "Could not detect project from working directory. Set PROJECT_ID environment variable or configure ~/.athena/projects.json",
                "status": "error",
            }

        # Create task from description
        from ..prospective.models import ProspectiveTask, TaskPriority

        task = ProspectiveTask(
            content=description,
            priority=TaskPriority.MEDIUM,
            project_id=project_id,
        )

        try:
            saved_task = self.store.create_task(task)
            if saved_task and saved_task.id:
                result = await self.build_plan(
                    saved_task.id, description=description
                )
                # Add project info to result
                result["project_id"] = project_id
                result["project_name"] = get_project_name(project_id) or "Unknown"
                return result
            else:
                return {
                    "error": "Failed to create task",
                    "status": "error",
                }
        except Exception as e:
            return {
                "error": f"Quick planning failed: {e}",
                "status": "error",
            }
