"""
Planning Orchestrator Agent

Autonomous sub-agent for plan management, decomposition, validation, and adaptive replanning.
Manages complex plans: decomposing, validating, executing, monitoring, and adapting.
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class PlanningStage(Enum):
    """Stages in the planning lifecycle"""
    ANALYZE = "analyze"
    DECOMPOSE = "decompose"
    VALIDATE = "validate"
    CREATE_GOALS = "create_goals"
    SUGGEST_STRATEGY = "suggest_strategy"
    REPORT = "report"
    MONITOR = "monitor"
    ADAPT = "adapt"


class ReplannTrigger(Enum):
    """Triggers for adaptive replanning"""
    DURATION_EXCEEDED = "duration_exceeded"
    QUALITY_DEGRADATION = "quality_degradation"
    BLOCKER_ENCOUNTERED = "blocker_encountered"
    ASSUMPTION_VIOLATED = "assumption_violated"
    MILESTONE_MISSED = "milestone_missed"
    RESOURCE_CONSTRAINT = "resource_constraint"


@dataclass
class PlanAnalysis:
    """Analysis of a task/plan"""
    task_description: str
    complexity: int  # 1-10
    scope_days: int
    num_phases: int
    critical_path_days: float
    resource_needs: Dict[str, int]
    risk_level: str
    recommended_strategy: str


@dataclass
class DecomposedPlan:
    """Decomposed plan structure"""
    phases: List[Dict[str, Any]]
    total_tasks: int
    critical_path: List[str]
    total_duration_days: int
    dependencies: Dict[str, List[str]]


class PlanningOrchestrator:
    """
    Autonomous orchestrator for planning complex work.

    Capabilities:
    - Analyzes task complexity and scope
    - Decomposes into hierarchical phases
    - Validates using 3-level checks
    - Creates goals and tasks
    - Suggests execution strategies
    - Monitors progress and adapts
    """

    def __init__(self, database, mcp_client):
        """Initialize the planning orchestrator

        Args:
            database: Database connection for goal/task storage
            mcp_client: MCP client for tool operations
        """
        self.db = database
        self.mcp = mcp_client
        self.current_plan = None
        self.monitoring_enabled = False

    async def orchestrate_planning(self, task_description: str, complexity: int = 5) -> Dict[str, Any]:
        """
        Main orchestration workflow for complex planning.

        Args:
            task_description: Description of the task/plan to manage
            complexity: Estimated complexity (1-10)

        Returns:
            Complete planning result with goal, tasks, and strategy
        """
        result = {
            "task": task_description,
            "stages": {},
            "success": False,
            "errors": []
        }

        try:
            # Stage 1: Analyze the work
            analysis = await self._analyze_task(task_description, complexity)
            result["stages"]["analyze"] = analysis.__dict__

            # Stage 2: Decompose into plan
            decomposed = await self._decompose_plan(task_description, complexity)
            result["stages"]["decompose"] = {
                "total_tasks": decomposed.total_tasks,
                "total_duration_days": decomposed.total_duration_days,
                "num_phases": len(decomposed.phases),
                "critical_path_length": sum(
                    p.get("duration", 0) for p in decomposed.phases
                    if p.get("on_critical_path", False)
                )
            }

            # Stage 3: Validate the plan
            validation = await self._validate_plan(decomposed)
            result["stages"]["validate"] = validation

            # Stage 4: Create goals and tasks
            goal_tasks = await self._create_goals_and_tasks(task_description, decomposed, analysis)
            result["stages"]["create_goals"] = goal_tasks

            # Stage 5: Suggest strategy
            strategy = await self._suggest_strategy(task_description, complexity, analysis.scope_days)
            result["stages"]["suggest_strategy"] = strategy

            # Stage 6: Report to user
            result["report"] = await self._generate_report(
                analysis, decomposed, validation, goal_tasks, strategy
            )

            # Store the plan for monitoring
            self.current_plan = {
                "task": task_description,
                "decomposition": decomposed,
                "validation": validation,
                "goal_id": goal_tasks.get("goal_id"),
                "task_ids": goal_tasks.get("task_ids", [])
            }

            result["success"] = True
            self.monitoring_enabled = True

        except Exception as e:
            result["success"] = False
            result["errors"].append(str(e))
            result["error_type"] = type(e).__name__

        return result

    async def _analyze_task(self, description: str, complexity: int) -> PlanAnalysis:
        """Analyze task for scope and complexity"""
        # In production, this would use NLP and domain analysis
        # For now, we return structured analysis

        complexity = max(1, min(10, complexity))

        # Estimate scope based on complexity
        scope_days_estimate = {
            1: 1, 2: 2, 3: 3, 4: 5, 5: 7,
            6: 10, 7: 14, 8: 21, 9: 28, 10: 40
        }

        num_phases = (complexity // 3) + 1  # 1 phase per 3 complexity points
        resource_needs = {
            "engineers": max(1, complexity // 3),
            "hours": scope_days_estimate[complexity] * 8
        }

        risk_mapping = {
            (1, 3): "Low",
            (4, 5): "Medium",
            (6, 8): "High",
            (9, 10): "Critical"
        }
        risk_level = next(
            v for (min_c, max_c), v in risk_mapping.items()
            if min_c <= complexity <= max_c
        )

        return PlanAnalysis(
            task_description=description,
            complexity=complexity,
            scope_days=scope_days_estimate[complexity],
            num_phases=num_phases,
            critical_path_days=scope_days_estimate[complexity] * 0.6,
            resource_needs=resource_needs,
            risk_level=risk_level,
            recommended_strategy="parallel" if complexity >= 6 else "sequential"
        )

    async def _decompose_plan(self, description: str, complexity: int) -> DecomposedPlan:
        """Decompose task into hierarchical phases and tasks"""
        # Call MCP: decompose_hierarchically
        result = await self.mcp.call_operation(
            "planning_tools",
            "decompose_hierarchically",
            {
                "task_description": description,
                "complexity": complexity,
                "include_estimates": True
            }
        )

        phases = result.get("phases", [])
        tasks = result.get("tasks", [])
        dependencies = result.get("dependencies", {})

        return DecomposedPlan(
            phases=phases,
            total_tasks=len(tasks),
            critical_path=result.get("critical_path", []),
            total_duration_days=result.get("total_duration_days", 0),
            dependencies=dependencies
        )

    async def _validate_plan(self, plan: DecomposedPlan) -> Dict[str, Any]:
        """Validate plan using 3-level validation"""
        # Call MCP: validate_plan_comprehensive
        result = await self.mcp.call_operation(
            "phase6_planning_tools",
            "validate_plan_comprehensive",
            {
                "phases": plan.phases,
                "total_tasks": plan.total_tasks,
                "dependencies": plan.dependencies
            }
        )

        return {
            "is_valid": result.get("is_valid", True),
            "level": result.get("level", "GOOD"),
            "confidence": result.get("confidence", 0),
            "issues_found": len(result.get("issues", [])),
            "warnings": len(result.get("warnings", [])),
            "recommendations": result.get("recommendations", [])
        }

    async def _create_goals_and_tasks(self, description: str, plan: DecomposedPlan, analysis: PlanAnalysis) -> Dict[str, Any]:
        """Create goal and tasks in database"""
        # Call MCP: set_goal
        goal_result = await self.mcp.call_operation(
            "task_management_tools",
            "set_goal",
            {
                "content": description,
                "priority": min(10, (analysis.complexity + 4) // 2),
                "task_ids": []  # Will be populated
            }
        )

        goal_id = goal_result.get("goal_id")
        task_ids = []

        # Create tasks for each phase
        for phase in plan.phases:
            task_result = await self.mcp.call_operation(
                "task_management_tools",
                "create_task",
                {
                    "content": phase.get("name", "Phase task"),
                    "goal_id": goal_id,
                    "estimated_hours": phase.get("duration", 0)
                }
            )
            if task_result.get("success"):
                task_ids.append(task_result.get("task_id"))

        return {
            "goal_id": goal_id,
            "goal_created": goal_result.get("success", False),
            "task_ids": task_ids,
            "tasks_created": len(task_ids)
        }

    async def _suggest_strategy(self, description: str, complexity: int, available_days: int) -> Dict[str, Any]:
        """Suggest execution strategy"""
        # Call MCP: suggest_planning_strategy
        result = await self.mcp.call_operation(
            "planning_tools",
            "suggest_planning_strategy",
            {
                "task_description": description,
                "complexity": complexity,
                "time_available": available_days
            }
        )

        return {
            "recommended_approach": result.get("approach", "sequential"),
            "parallelization_possible": result.get("can_parallelize", False),
            "risk_mitigation": result.get("risk_mitigation", []),
            "resource_allocation": result.get("resource_allocation", {}),
            "communication_plan": result.get("communication_plan", "")
        }

    async def _generate_report(self, analysis: PlanAnalysis, decomposed: DecomposedPlan,
                              validation: Dict, goals: Dict, strategy: Dict) -> str:
        """Generate human-readable planning report"""
        return f"""
PLANNING COMPLETE!
{'='*60}

Task: {analysis.task_description}

Analysis:
  • Complexity: {analysis.complexity}/10 ({analysis.risk_level} risk)
  • Estimated duration: {analysis.scope_days} days
  • Phases: {analysis.num_phases}
  • Resource needs: {analysis.resource_needs.get('engineers', 1)} engineers, {analysis.resource_needs.get('hours', 0)} hours

Decomposition:
  • Total tasks: {decomposed.total_tasks}
  • Critical path: {decomposed.critical_path_days} days
  • Dependencies: {len(decomposed.dependencies)} unique dependencies

Validation:
  • Status: {'VALID ✓' if validation['is_valid'] else 'NEEDS REVIEW'}
  • Confidence: {validation['confidence']}/100
  • Issues: {validation['issues_found']}
  • Warnings: {validation['warnings']}

Goals & Tasks Created:
  • Goal ID: {goals.get('goal_id')}
  • Tasks created: {goals.get('tasks_created')}

Recommended Strategy:
  • Approach: {strategy.get('recommended_approach')}
  • Parallelization: {'Possible' if strategy.get('parallelization_possible') else 'Sequential only'}
  • Risk mitigations: {len(strategy.get('risk_mitigation', []))} identified

NEXT STEPS:
  1. Review plan validation
  2. Assign tasks to team members
  3. Start first phase
  4. Enable progress monitoring
"""

    async def monitor_progress(self) -> Dict[str, Any]:
        """Monitor plan execution and detect deviations"""
        if not self.current_plan:
            return {"error": "No plan currently being monitored"}

        # Check goal progress
        goal_id = self.current_plan["goal_id"]

        # This would call monitoring_tools to track actual vs. predicted
        result = {
            "goal_id": goal_id,
            "task_ids": self.current_plan["task_ids"],
            "status": "monitoring_active",
            "deviations": [],
            "alerts": []
        }

        return result

    async def trigger_replanning(self, trigger_type: str, reason: str) -> Dict[str, Any]:
        """Trigger adaptive replanning based on deviation"""
        if not self.current_plan:
            return {"error": "No plan currently being managed"}

        # Call MCP: trigger_adaptive_replanning
        result = await self.mcp.call_operation(
            "phase6_planning_tools",
            "trigger_adaptive_replanning",
            {
                "task_id": self.current_plan["goal_id"],
                "trigger_type": trigger_type,
                "trigger_reason": reason
            }
        )

        return {
            "replanning_triggered": True,
            "trigger_type": trigger_type,
            "reason": reason,
            "new_strategy": result.get("new_strategy"),
            "timeline_impact": result.get("timeline_impact"),
            "recommendations": result.get("recommendations", [])
        }
