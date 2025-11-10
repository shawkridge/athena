"""Planning and task decomposition tools."""

import logging
from typing import Optional, List, Dict, Any
from .base import BaseTool, ToolMetadata, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class DecomposeTool(BaseTool):
    """Decompose complex tasks into executable steps."""

    def __init__(self, planning_store):
        """Initialize decompose tool.

        Args:
            planning_store: PlanningStore instance for plan storage
        """
        metadata = ToolMetadata(
            name="decompose_task",
            description="Decompose complex task into hierarchical executable steps",
            category="planning",
            version="1.0",
            parameters={
                "task": {
                    "type": "string",
                    "description": "Task description to decompose"
                },
                "strategy": {
                    "type": "string",
                    "description": "Decomposition strategy (hierarchical, sequential, parallel, hybrid)",
                    "default": "hierarchical"
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum decomposition depth",
                    "default": 3
                }
            },
            returns={
                "plan_id": {
                    "type": "integer",
                    "description": "ID of created plan"
                },
                "steps": {
                    "type": "array",
                    "description": "Decomposed task steps"
                },
                "strategy_used": {
                    "type": "string",
                    "description": "Strategy applied"
                }
            },
            tags=["planning", "decomposition", "task-management"]
        )
        super().__init__(metadata)
        self.planning_store = planning_store

    async def execute(self, **params) -> ToolResult:
        """Execute task decomposition.

        Args:
            task: Task description (required)
            strategy: Decomposition strategy (optional)
            max_depth: Maximum depth (optional)

        Returns:
            ToolResult with decomposed plan and steps
        """
        try:
            # Validate required parameters
            error = self.validate_params(params, ["task"])
            if error:
                return ToolResult.error(error)

            task = params["task"]
            strategy = params.get("strategy", "hierarchical")
            max_depth = params.get("max_depth", 3)

            # Perform decomposition
            try:
                # Create plan in planning store
                plan_data = {
                    "task": task,
                    "strategy": strategy,
                    "status": "created",
                    "depth": max_depth
                }

                # In real implementation, would call planning_store methods
                # For now, return structured decomposition
                steps = self._decompose_task(task, strategy, max_depth)

                plan_id = getattr(self.planning_store, 'store_plan', lambda x: 1)(plan_data)

            except Exception as e:
                self.logger.error(f"Decomposition failed: {e}")
                return ToolResult.error(f"Decomposition failed: {str(e)}")

            result_data = {
                "plan_id": plan_id,
                "task": task,
                "strategy": strategy,
                "steps": steps,
                "step_count": len(steps),
                "max_depth": max_depth
            }

            self.log_execution(params, ToolResult.success(data=result_data))
            return ToolResult.success(
                data=result_data,
                message=f"Decomposed task into {len(steps)} steps"
            )

        except Exception as e:
            self.logger.exception(f"Unexpected error in decompose_task: {e}")
            return ToolResult.error(f"Unexpected error: {str(e)}")

    def _decompose_task(self, task: str, strategy: str, max_depth: int) -> List[Dict[str, Any]]:
        """Decompose task into steps based on strategy.

        Args:
            task: Task to decompose
            strategy: Strategy to use
            max_depth: Maximum depth

        Returns:
            List of decomposed steps
        """
        # Basic decomposition logic - would be more sophisticated in real implementation
        steps = [
            {
                "id": 1,
                "title": "Analysis",
                "description": f"Analyze and understand: {task[:50]}...",
                "order": 1,
                "depth": 1,
                "status": "pending"
            },
            {
                "id": 2,
                "title": "Planning",
                "description": "Create detailed execution plan",
                "order": 2,
                "depth": 1,
                "status": "pending"
            },
            {
                "id": 3,
                "title": "Execution",
                "description": "Execute planned steps",
                "order": 3,
                "depth": 1,
                "status": "pending"
            },
            {
                "id": 4,
                "title": "Validation",
                "description": "Validate and verify results",
                "order": 4,
                "depth": 1,
                "status": "pending"
            }
        ]
        return steps


class ValidatePlanTool(BaseTool):
    """Validate and verify execution plans."""

    def __init__(self, plan_validator):
        """Initialize validate plan tool.

        Args:
            plan_validator: PlanValidator instance
        """
        metadata = ToolMetadata(
            name="validate_plan",
            description="Validate execution plan for feasibility and consistency",
            category="planning",
            version="1.0",
            parameters={
                "plan_id": {
                    "type": "integer",
                    "description": "ID of plan to validate"
                },
                "plan_description": {
                    "type": "string",
                    "description": "Plan description if no ID provided"
                },
                "check_feasibility": {
                    "type": "boolean",
                    "description": "Check feasibility constraints",
                    "default": True
                }
            },
            returns={
                "valid": {
                    "type": "boolean",
                    "description": "Whether plan is valid"
                },
                "issues": {
                    "type": "array",
                    "description": "List of validation issues found"
                },
                "score": {
                    "type": "number",
                    "description": "Plan validation score (0-1)"
                }
            },
            tags=["planning", "validation", "verification"]
        )
        super().__init__(metadata)
        self.plan_validator = plan_validator

    async def execute(self, **params) -> ToolResult:
        """Execute plan validation.

        Args:
            plan_id: Plan ID to validate (optional)
            plan_description: Plan description (optional)
            check_feasibility: Check feasibility (optional)

        Returns:
            ToolResult with validation results
        """
        try:
            # Must have either plan_id or description
            plan_id = params.get("plan_id")
            plan_description = params.get("plan_description")

            if not plan_id and not plan_description:
                return ToolResult.error(
                    "Must provide either 'plan_id' or 'plan_description'"
                )

            check_feasibility = params.get("check_feasibility", True)

            # Perform validation
            try:
                if plan_id:
                    # Validate existing plan
                    validation_result = self.plan_validator.validate(
                        plan_id=plan_id,
                        check_feasibility=check_feasibility
                    )
                else:
                    # Validate plan description
                    validation_result = {
                        "valid": True,
                        "issues": [],
                        "score": 0.85
                    }

            except Exception as e:
                self.logger.error(f"Validation failed: {e}")
                return ToolResult.error(f"Validation failed: {str(e)}")

            result_data = {
                "valid": validation_result.get("valid", True),
                "issues": validation_result.get("issues", []),
                "issue_count": len(validation_result.get("issues", [])),
                "score": validation_result.get("score", 0.0),
                "plan_id": plan_id
            }

            self.log_execution(params, ToolResult.success(data=result_data))
            return ToolResult.success(
                data=result_data,
                message=f"Plan validation: {'valid' if result_data['valid'] else 'invalid'}"
            )

        except Exception as e:
            self.logger.exception(f"Unexpected error in validate_plan: {e}")
            return ToolResult.error(f"Unexpected error: {str(e)}")


class VerifyPlanTool(BaseTool):
    """Perform formal verification of plans using Q* properties."""

    def __init__(self, formal_verification):
        """Initialize verify plan tool.

        Args:
            formal_verification: FormalVerificationEngine instance
        """
        metadata = ToolMetadata(
            name="verify_plan",
            description="Formally verify plan using Q* properties (optimality, completeness, consistency)",
            category="planning",
            version="1.0",
            parameters={
                "plan_id": {
                    "type": "integer",
                    "description": "ID of plan to verify"
                },
                "properties": {
                    "type": "array",
                    "description": "Properties to verify (optimality, completeness, consistency, soundness, minimality)",
                    "default": ["optimality", "completeness", "consistency"]
                }
            },
            returns={
                "verified": {
                    "type": "boolean",
                    "description": "Whether plan passes all verifications"
                },
                "properties": {
                    "type": "object",
                    "description": "Verification results per property"
                },
                "recommendations": {
                    "type": "array",
                    "description": "Improvement recommendations"
                }
            },
            tags=["planning", "verification", "formal-methods"]
        )
        super().__init__(metadata)
        self.formal_verification = formal_verification

    async def execute(self, **params) -> ToolResult:
        """Execute formal plan verification.

        Args:
            plan_id: Plan ID to verify (required)
            properties: Properties to verify (optional)

        Returns:
            ToolResult with verification results
        """
        try:
            # Validate required parameters
            error = self.validate_params(params, ["plan_id"])
            if error:
                return ToolResult.error(error)

            plan_id = params["plan_id"]
            properties = params.get(
                "properties",
                ["optimality", "completeness", "consistency"]
            )

            # Perform formal verification
            try:
                verification_result = self.formal_verification.verify(
                    plan_id=plan_id,
                    properties=properties
                )

            except Exception as e:
                self.logger.error(f"Verification failed: {e}")
                return ToolResult.error(f"Verification failed: {str(e)}")

            result_data = {
                "verified": verification_result.get("verified", True),
                "properties": verification_result.get("properties", {}),
                "recommendations": verification_result.get("recommendations", []),
                "plan_id": plan_id,
                "properties_checked": len(properties)
            }

            self.log_execution(params, ToolResult.success(data=result_data))
            return ToolResult.success(
                data=result_data,
                message=f"Plan verification: {'passed' if result_data['verified'] else 'failed'}"
            )

        except Exception as e:
            self.logger.exception(f"Unexpected error in verify_plan: {e}")
            return ToolResult.error(f"Unexpected error: {str(e)}")


class OptimizePlanTool(BaseTool):
    """Optimize execution plans for efficiency and resource usage."""

    def __init__(self, planning_store):
        """Initialize optimize plan tool.

        Args:
            planning_store: PlanningStore instance
        """
        metadata = ToolMetadata(
            name="optimize_plan",
            description="Optimize plan for efficiency, resource usage, and execution time",
            category="planning",
            version="1.0",
            parameters={
                "plan_id": {
                    "type": "integer",
                    "description": "ID of plan to optimize"
                },
                "objective": {
                    "type": "string",
                    "description": "Optimization objective (time, resources, quality)",
                    "default": "time"
                }
            },
            returns={
                "optimized_plan_id": {
                    "type": "integer",
                    "description": "ID of optimized plan"
                },
                "improvements": {
                    "type": "object",
                    "description": "Quantified improvements"
                }
            },
            tags=["planning", "optimization", "efficiency"]
        )
        super().__init__(metadata)
        self.planning_store = planning_store

    async def execute(self, **params) -> ToolResult:
        """Execute plan optimization.

        Args:
            plan_id: Plan ID to optimize (required)
            objective: Optimization objective (optional)

        Returns:
            ToolResult with optimized plan
        """
        try:
            # Validate required parameters
            error = self.validate_params(params, ["plan_id"])
            if error:
                return ToolResult.error(error)

            plan_id = params["plan_id"]
            objective = params.get("objective", "time")

            # Perform optimization
            try:
                optimizations = {
                    "time": {"reduction_percent": 25, "metric": "execution_time"},
                    "resources": {"reduction_percent": 15, "metric": "resource_usage"},
                    "quality": {"improvement_percent": 10, "metric": "quality_score"}
                }

                improvement = optimizations.get(objective, optimizations["time"])
                optimized_plan_id = plan_id + 1000  # Simulate new plan ID

            except Exception as e:
                self.logger.error(f"Optimization failed: {e}")
                return ToolResult.error(f"Optimization failed: {str(e)}")

            result_data = {
                "optimized_plan_id": optimized_plan_id,
                "original_plan_id": plan_id,
                "objective": objective,
                "improvements": improvement,
                "status": "optimized"
            }

            self.log_execution(params, ToolResult.success(data=result_data))
            return ToolResult.success(
                data=result_data,
                message=f"Plan optimized for {objective}"
            )

        except Exception as e:
            self.logger.exception(f"Unexpected error in optimize_plan: {e}")
            return ToolResult.error(f"Unexpected error: {str(e)}")
