"""
Planner Agent

Decomposes high-level tasks into executable plans.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .base import AgentType, BaseAgent


class PlanStep(BaseModel):
    """Single step in an execution plan"""
    id: int
    description: str
    estimated_duration_ms: int
    estimated_resources: Dict[str, float] = Field(default_factory=dict)
    dependencies: List[int] = Field(default_factory=list)
    salience: float = 0.5
    risk_level: str = "low"
    success_criteria: str = ""
    preconditions: List[str] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "description": self.description,
            "estimated_duration_ms": self.estimated_duration_ms,
            "estimated_resources": self.estimated_resources,
            "dependencies": self.dependencies,
            "salience": self.salience,
            "risk_level": self.risk_level,
            "success_criteria": self.success_criteria,
            "preconditions": self.preconditions
        }


class ExecutionPlan(BaseModel):
    """Complete execution plan for a task"""
    id: Optional[int] = None
    task_id: Optional[int] = None
    task_description: str = ""
    steps: List[PlanStep] = Field(default_factory=list)
    estimated_total_duration_ms: int = 0
    estimated_total_resources: Dict[str, float] = Field(default_factory=dict)
    confidence: float = 0.0
    complexity: str = "simple"
    critical_path: List[int] = Field(default_factory=list)
    created_at: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_description": self.task_description,
            "steps": [s.to_dict() for s in self.steps],
            "estimated_total_duration_ms": self.estimated_total_duration_ms,
            "estimated_total_resources": self.estimated_total_resources,
            "confidence": self.confidence,
            "complexity": self.complexity,
            "critical_path": self.critical_path,
            "created_at": self.created_at
        }


class PlannerAgent(BaseAgent):
    """
    Planner Agent: Decomposes high-level tasks into executable plans.

    Responsibilities:
    - Query memory for similar tasks
    - Extract patterns from historical data
    - Generate execution steps
    - Estimate time and resources
    - Identify critical path
    - Add contingency plans
    """

    def __init__(self, db_path: str):
        """
        Initialize Planner agent.

        Args:
            db_path: Path to memory database
        """
        super().__init__(AgentType.PLANNER, db_path)
        self.plan_counter = 0

    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming messages.

        Args:
            message: Message payload

        Returns:
            Response payload
        """
        try:
            if message.get("action") == "decompose":
                return await self.decompose_task(
                    message.get("task", {}),
                    message.get("execution_id")
                )
            elif message.get("action") == "replan":
                return await self.replan_on_failure(
                    message.get("failure", {}),
                    message.get("execution_id")
                )
            else:
                return {
                    "status": "error",
                    "error": f"Unknown action: {message.get('action')}"
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    async def decompose_task(self, task: Dict[str, Any],
                            execution_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Break task into executable steps.

        Args:
            task: Task description
            execution_id: Execution ID for tracking

        Returns:
            Execution plan with steps
        """
        start_time = datetime.now()
        self.status = self.status.PROCESSING

        try:
            # 1. Extract task metadata
            task_id = task.get("id")
            task_desc = task.get("description", "")
            salience = task.get("salience", 0.5)

            # 2. Generate initial steps (simple heuristic-based approach)
            steps = await self._generate_steps(task_desc, salience)

            # 3. Identify dependencies
            dependencies = await self._identify_dependencies(steps)

            # 4. Estimate resources
            total_resources = await self._estimate_resources(steps)

            # 5. Compute step salience
            step_salience = await self._compute_step_salience(steps, salience)
            for step, sal in zip(steps, step_salience):
                step.salience = sal

            # 6. Identify critical path
            critical_path = await self._compute_critical_path(steps, dependencies)

            # 7. Assess complexity
            complexity = self._assess_complexity(steps)

            # 8. Compute overall confidence
            confidence = await self._compute_confidence(task, steps)

            # 9. Create plan
            self.plan_counter += 1
            plan = ExecutionPlan(
                id=self.plan_counter,
                task_id=task_id,
                task_description=task_desc,
                steps=steps,
                estimated_total_duration_ms=sum(s.estimated_duration_ms for s in steps),
                estimated_total_resources=total_resources,
                confidence=confidence,
                complexity=complexity,
                critical_path=critical_path,
                created_at=int(datetime.now().timestamp())
            )

            decision_time = (datetime.now() - start_time).total_seconds() * 1000
            self.record_decision(True, decision_time, confidence)
            self.status = self.status.IDLE

            return {
                "status": "success",
                "plan": plan.to_dict(),
                "confidence": confidence,
                "execution_id": execution_id
            }

        except Exception as e:
            decision_time = (datetime.now() - start_time).total_seconds() * 1000
            self.record_decision(False, decision_time, 0.0)
            self.status = self.status.ERROR

            return {
                "status": "error",
                "error": str(e),
                "execution_id": execution_id
            }

    async def make_decision(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a planning decision based on context.

        Args:
            context: Decision context

        Returns:
            Decision output with confidence score
        """
        task = context.get("task", {})
        return await self.decompose_task(task, context.get("execution_id"))

    async def replan_on_failure(self, failure: Dict[str, Any],
                               execution_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate recovery plan after failure.

        Args:
            failure: Failure description
            execution_id: Execution ID for tracking

        Returns:
            Adapted execution plan
        """
        # Placeholder: In full implementation, would analyze failure and generate recovery
        return {
            "status": "success",
            "plan": None,
            "message": "Replan not yet implemented",
            "execution_id": execution_id
        }

    async def _generate_steps(self, task_desc: str, salience: float) -> List[PlanStep]:
        """
        Generate initial execution steps.

        Args:
            task_desc: Task description
            salience: Task importance

        Returns:
            List of execution steps
        """
        # Simple heuristic: break into 4 typical phases
        steps = [
            PlanStep(
                id=1,
                description=f"Plan: {task_desc}",
                estimated_duration_ms=1800000,  # 30 min
                estimated_resources={"cpu": 10, "memory": 100},
                dependencies=[],
                risk_level="low",
                success_criteria="Plan document created"
            ),
            PlanStep(
                id=2,
                description=f"Implement: {task_desc}",
                estimated_duration_ms=3600000,  # 60 min
                estimated_resources={"cpu": 50, "memory": 500},
                dependencies=[1],
                risk_level="medium",
                success_criteria="Implementation complete and compilable"
            ),
            PlanStep(
                id=3,
                description=f"Test: {task_desc}",
                estimated_duration_ms=1800000,  # 30 min
                estimated_resources={"cpu": 30, "memory": 200},
                dependencies=[2],
                risk_level="low",
                success_criteria="All tests passing"
            ),
            PlanStep(
                id=4,
                description=f"Deploy: {task_desc}",
                estimated_duration_ms=600000,  # 10 min
                estimated_resources={"cpu": 20, "memory": 150},
                dependencies=[3],
                risk_level="high",
                success_criteria="Live in production"
            ),
        ]
        return steps

    async def _identify_dependencies(self, steps: List[PlanStep]) -> List[tuple]:
        """
        Determine step ordering constraints.

        Args:
            steps: List of steps

        Returns:
            List of (from_id, to_id) dependency tuples
        """
        dependencies = []
        for step in steps:
            for dep_id in step.dependencies:
                dependencies.append((dep_id, step.id))
        return dependencies

    async def _estimate_resources(self, steps: List[PlanStep]) -> Dict[str, float]:
        """
        Estimate total resource requirements.

        Args:
            steps: List of steps

        Returns:
            Aggregated resource dictionary
        """
        total = {}
        for step in steps:
            for resource, amount in step.estimated_resources.items():
                total[resource] = total.get(resource, 0) + amount
        return total

    async def _compute_step_salience(self, steps: List[PlanStep],
                                    task_salience: float) -> List[float]:
        """
        Compute salience for each step.

        Args:
            steps: List of steps
            task_salience: Overall task salience

        Returns:
            List of step salience scores
        """
        # Higher-salience tasks get uniform salience across steps
        # Risk level also affects salience
        salience_scores = []
        for step in steps:
            base = task_salience
            if step.risk_level == "high":
                base *= 1.2
            salience_scores.append(min(1.0, base))
        return salience_scores

    async def _compute_critical_path(self, steps: List[PlanStep],
                                    dependencies: List[tuple]) -> List[int]:
        """
        Find steps on critical path (longest duration path).

        Args:
            steps: List of steps
            dependencies: List of dependency tuples

        Returns:
            List of step IDs on critical path
        """
        # Simple algorithm: find longest sequential path
        # Create adjacency graph
        graph: Dict[int, List[int]] = {step.id: [] for step in steps}
        for from_id, to_id in dependencies:
            graph[from_id].append(to_id)

        # Find path with maximum duration
        max_path = []
        max_duration = 0

        def dfs(node_id: int, path: List[int], duration: int):
            nonlocal max_path, max_duration

            if duration > max_duration:
                max_duration = duration
                max_path = path.copy()

            for next_id in graph.get(node_id, []):
                next_step = next(s for s in steps if s.id == next_id)
                path.append(next_id)
                dfs(next_id, path, duration + next_step.estimated_duration_ms)
                path.pop()

        # Start DFS from steps with no dependencies
        for step in steps:
            if not step.dependencies:
                dfs(step.id, [step.id], step.estimated_duration_ms)

        return max_path

    def _assess_complexity(self, steps: List[PlanStep]) -> str:
        """
        Assess task complexity.

        Args:
            steps: List of steps

        Returns:
            Complexity level: simple, moderate, complex
        """
        num_steps = len(steps)
        has_high_risk = any(s.risk_level == "high" for s in steps)
        num_dependencies = sum(len(s.dependencies) for s in steps)

        if num_steps <= 2 and not has_high_risk:
            return "simple"
        elif num_steps <= 5 and num_dependencies <= 3:
            return "moderate"
        else:
            return "complex"

    async def _compute_confidence(self, task: Dict[str, Any],
                                 steps: List[PlanStep]) -> float:
        """
        Compute confidence in plan quality.

        Args:
            task: Original task
            steps: Generated steps

        Returns:
            Confidence score (0.0-1.0)
        """
        # Base confidence
        confidence = 0.85

        # Reduce for high-risk steps
        high_risk_count = sum(1 for s in steps if s.risk_level == "high")
        confidence -= high_risk_count * 0.05

        # Reduce for many dependencies
        num_dependencies = sum(len(s.dependencies) for s in steps)
        confidence -= min(0.1, num_dependencies * 0.02)

        return max(0.5, min(1.0, confidence))
