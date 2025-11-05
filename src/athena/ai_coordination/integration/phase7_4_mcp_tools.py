"""Phase 7.4 MCP tools for Recall & Reuse.

Provides MCP tool handlers for Phase 7.4 integration:
- smart_recall_for_problem: Retrieve relevant knowledge
- get_procedure_candidates: Find usable procedures
- suggest_plan_enhancements: Improve action cycle plans
"""

from typing import Optional

from athena.ai_coordination.integration.smart_recall import SmartRecall
from athena.ai_coordination.integration.action_cycle_enhancer import ActionCycleEnhancer
from athena.ai_coordination.integration.prospective_integration import ProspectiveIntegration, ProspectiveTask


class Phase74MCPTools:
    """MCP tool handlers for Phase 7.4 Recall & Reuse."""

    def __init__(
        self,
        smart_recall: SmartRecall,
        action_enhancer: ActionCycleEnhancer,
        prospective: ProspectiveIntegration
    ):
        """Initialize Phase 7.4 MCP tools.

        Args:
            smart_recall: SmartRecall instance
            action_enhancer: ActionCycleEnhancer instance
            prospective: ProspectiveIntegration instance
        """
        self.recall = smart_recall
        self.enhancer = action_enhancer
        self.prospective = prospective

    def smart_recall_for_problem(
        self,
        problem_description: str,
        problem_type: Optional[str] = None,
        max_results: int = 10
    ) -> dict:
        """Recall relevant knowledge for a problem.

        Uses Memory-MCP to find similar problems, procedures, and code patterns.

        Args:
            problem_description: Description of the problem
            problem_type: Optional type (bug, feature, optimization)
            max_results: Maximum results to return

        Returns:
            Dict with retrieved knowledge
        """
        try:
            result = self.recall.recall_for_problem(
                problem_description,
                problem_type,
                max_results
            )

            return {
                "status": "success",
                "recall_id": result["recall_id"],
                "problem_type": problem_type,
                "total_results": result["total_results"],
                "procedures": result["procedures"],
                "patterns": result["patterns"],
                "code_examples": result["code_examples"],
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def get_procedure_candidates(
        self,
        goal_type: str,
        min_success_rate: float = 0.6
    ) -> dict:
        """Get procedure candidates for a goal type.

        Args:
            goal_type: Type of goal
            min_success_rate: Minimum success rate (0.0-1.0)

        Returns:
            Dict with procedure candidates
        """
        try:
            if min_success_rate < 0.0 or min_success_rate > 1.0:
                return {
                    "status": "error",
                    "error": "Success rate must be between 0.0 and 1.0",
                }

            candidates = self.recall.get_procedure_candidates(
                goal_type,
                min_success_rate
            )

            return {
                "status": "success",
                "goal_type": goal_type,
                "min_success_rate": min_success_rate,
                "candidate_count": len(candidates),
                "candidates": candidates,
            }
        except Exception as e:
            return {
                "status": "error",
                "goal_type": goal_type,
                "error": str(e),
            }

    def suggest_plan_enhancements(
        self,
        cycle_id: str,
        goal_description: str,
        plan_steps: list[str]
    ) -> dict:
        """Suggest enhancements to an action cycle plan.

        Args:
            cycle_id: ActionCycle ID
            goal_description: Goal description
            plan_steps: List of planned steps

        Returns:
            Dict with enhancement suggestions
        """
        try:
            result = self.enhancer.analyze_plan(
                cycle_id,
                goal_description,
                plan_steps
            )

            return {
                "status": "success",
                "cycle_id": cycle_id,
                "goal_description": goal_description,
                "plan_steps": len(plan_steps),
                "suggested_enhancements": result["suggested_enhancements"],
                "enhancement_count": result["enhancement_count"],
            }
        except Exception as e:
            return {
                "status": "error",
                "cycle_id": cycle_id,
                "error": str(e),
            }

    def record_reuse_outcome(
        self,
        recall_id: int,
        solution_id: int,
        solution_type: str,
        goal_id: str,
        outcome: str,
        effectiveness: float
    ) -> dict:
        """Record outcome of reusing a recalled solution.

        Args:
            recall_id: Recall operation ID
            solution_id: Solution ID (procedure, pattern, example)
            solution_type: Type of solution
            goal_id: Goal it was used for
            outcome: Outcome (success, partial, failure)
            effectiveness: Effectiveness score (0.0-1.0)

        Returns:
            Dict with recording result
        """
        try:
            if outcome not in ["success", "partial", "failure"]:
                return {
                    "status": "error",
                    "error": "Outcome must be 'success', 'partial', or 'failure'",
                }

            if effectiveness < 0.0 or effectiveness > 1.0:
                return {
                    "status": "error",
                    "error": "Effectiveness must be between 0.0 and 1.0",
                }

            reuse_id = self.recall.record_reuse(
                recall_id,
                solution_id,
                solution_type,
                goal_id,
                outcome,
                effectiveness
            )

            return {
                "status": "success",
                "reuse_id": reuse_id,
                "recall_id": recall_id,
                "outcome": outcome,
                "effectiveness": effectiveness,
            }
        except Exception as e:
            return {
                "status": "error",
                "recall_id": recall_id,
                "error": str(e),
            }

    def get_enhancement_effectiveness(self) -> dict:
        """Get effectiveness metrics for applied enhancements.

        Returns:
            Dict with effectiveness metrics
        """
        try:
            metrics = self.enhancer.get_enhancement_effectiveness()
            return {
                "status": "success",
                "metrics": metrics,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def create_prospective_task(
        self,
        task_content: str,
        priority: str,
        trigger_type: str,
        trigger_value: str,
        source_pattern_id: int,
        estimated_effort_hours: float
    ) -> dict:
        """Create a prospective task from a pattern.

        Args:
            task_content: Task description
            priority: Priority (low, medium, high, critical)
            trigger_type: Trigger type (time, event, context, file)
            trigger_value: Trigger value
            source_pattern_id: Source pattern ID
            estimated_effort_hours: Estimated effort

        Returns:
            Dict with task creation result
        """
        try:
            if priority not in ["low", "medium", "high", "critical"]:
                return {
                    "status": "error",
                    "error": "Invalid priority level",
                }

            task = ProspectiveTask(
                task_content,
                priority,
                trigger_type,
                trigger_value,
                source_pattern_id,
                estimated_effort_hours
            )

            task_id = self.prospective.create_prospective_task(task)

            return {
                "status": "success",
                "task_id": task_id,
                "task_content": task_content,
                "priority": priority,
                "trigger_type": trigger_type,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def get_pending_prospective_tasks(self) -> dict:
        """Get all pending prospective tasks.

        Returns:
            Dict with pending tasks
        """
        try:
            tasks = self.prospective.get_pending_tasks()
            return {
                "status": "success",
                "task_count": len(tasks),
                "tasks": tasks,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def get_recall_metrics(self) -> dict:
        """Get overall recall and reuse metrics.

        Returns:
            Dict with metrics
        """
        try:
            metrics = self.recall.get_recall_metrics()
            return {
                "status": "success",
                "metrics": metrics,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }
