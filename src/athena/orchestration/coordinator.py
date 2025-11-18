"""Agent coordination and DAG execution system.

Enables complex multi-agent workflows with dependency management,
parallel execution, and result composition.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Callable, Any

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class AgentTask:
    """Definition of a task to be executed by an agent."""

    id: str
    agent_name: str  # Name of agent to execute
    task_type: str  # Type of task (research, analyze, synthesize, etc.)
    input_data: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class ExecutionPlan:
    """Plan for executing a set of tasks."""

    plan_id: str
    project_id: int
    tasks: Dict[str, AgentTask] = field(default_factory=dict)
    execution_order: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    results: Dict[str, Dict] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)


class AgentOrchestrator:
    """Orchestrates execution of agent tasks with dependency management."""

    def __init__(self, agents: Dict[str, Callable], db=None):
        """Initialize orchestrator with available agents.

        Args:
            agents: Dict mapping agent names to callable functions/methods
            db: Optional database connection for persistence
        """
        self.agents = agents
        self.db = db
        self.executions: Dict[str, ExecutionPlan] = {}

    def create_plan(self, plan_id: str, project_id: int) -> ExecutionPlan:
        """Create a new execution plan."""
        plan = ExecutionPlan(plan_id=plan_id, project_id=project_id)
        self.executions[plan_id] = plan
        return plan

    def add_task(self, plan_id: str, task: AgentTask) -> None:
        """Add a task to an execution plan."""
        if plan_id not in self.executions:
            raise ValueError(f"Plan {plan_id} not found")

        self.executions[plan_id].tasks[task.id] = task

    def _validate_dag(self, plan: ExecutionPlan) -> bool:
        """Validate that the DAG has no cycles."""
        visited = set()
        rec_stack = set()

        def has_cycle(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)

            task = plan.tasks.get(task_id)
            if not task:
                return False

            for dep in task.dependencies:
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True

            rec_stack.remove(task_id)
            return False

        for task_id in plan.tasks:
            if task_id not in visited:
                if has_cycle(task_id):
                    return False

        return True

    def _get_ready_tasks(self, plan: ExecutionPlan, executed: set) -> List[str]:
        """Get tasks ready to execute (all dependencies satisfied)."""
        ready = []

        for task_id, task in plan.tasks.items():
            if task.status == TaskStatus.PENDING:
                # Check if all dependencies are executed
                if all(dep in executed for dep in task.dependencies):
                    ready.append(task_id)

        return ready

    async def execute_plan(self, plan_id: str) -> ExecutionPlan:
        """Execute a plan's tasks respecting dependencies.

        Returns:
            Updated ExecutionPlan with results
        """
        plan = self.executions.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        # Validate DAG
        if not self._validate_dag(plan):
            plan.status = TaskStatus.FAILED
            return plan

        plan.status = TaskStatus.RUNNING
        plan.started_at = datetime.now()

        executed = set()
        failed_tasks = set()

        while executed | failed_tasks != set(plan.tasks.keys()):
            # Get tasks ready to run
            ready = self._get_ready_tasks(plan, executed)

            if not ready and executed | failed_tasks != set(plan.tasks.keys()):
                # Stalled - some tasks blocked by failed dependencies
                for task_id, task in plan.tasks.items():
                    if task.status == TaskStatus.PENDING:
                        # Check if any dependency failed
                        for dep in task.dependencies:
                            if dep in failed_tasks:
                                task.status = TaskStatus.BLOCKED
                                plan.errors[task_id] = f"Dependency {dep} failed"
                                failed_tasks.add(task_id)
                                break
                break

            if not ready:
                break

            # Execute ready tasks in parallel
            tasks_to_run = [plan.tasks[task_id] for task_id in ready]
            results = await asyncio.gather(
                *[self._execute_task(task) for task in tasks_to_run], return_exceptions=True
            )

            # Process results
            for task_id, result in zip(ready, results):
                if isinstance(result, Exception):
                    plan.tasks[task_id].status = TaskStatus.FAILED
                    plan.tasks[task_id].error = str(result)
                    plan.errors[task_id] = str(result)
                    failed_tasks.add(task_id)
                else:
                    plan.tasks[task_id].status = TaskStatus.COMPLETED
                    plan.tasks[task_id].result = result
                    plan.results[task_id] = result
                    executed.add(task_id)

        # Set final status
        if failed_tasks:
            plan.status = TaskStatus.FAILED
        else:
            plan.status = TaskStatus.COMPLETED

        plan.completed_at = datetime.now()
        return plan

    async def _execute_task(self, task: AgentTask) -> Dict:
        """Execute a single task using its agent."""
        if task.agent_name not in self.agents:
            raise ValueError(f"Agent {task.agent_name} not found")

        agent = self.agents[task.agent_name]
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        try:
            # Call agent with task input
            if asyncio.iscoroutinefunction(agent):
                result = await agent(**task.input_data)
            else:
                result = agent(**task.input_data)

            task.completed_at = datetime.now()
            return result

        except Exception as e:
            task.error = str(e)
            task.completed_at = datetime.now()
            raise


class DAGBuilder:
    """Helper to build task DAGs with fluent interface."""

    def __init__(self, plan_id: str, project_id: int):
        self.plan_id = plan_id
        self.project_id = project_id
        self.tasks: Dict[str, AgentTask] = {}
        self.next_id = 0

    def add_research_tasks(self, query: str, agents: List[str]) -> List[str]:
        """Add research tasks for multiple agents in parallel.

        Returns:
            List of task IDs for dependency chaining
        """
        task_ids = []

        for agent in agents:
            task_id = f"research_{self.next_id}"
            task = AgentTask(
                id=task_id, agent_name=agent, task_type="research", input_data={"query": query}
            )
            self.tasks[task_id] = task
            task_ids.append(task_id)
            self.next_id += 1

        return task_ids

    def add_analysis_task(self, depends_on: List[str], analysis_type: str = "synthesis") -> str:
        """Add analysis task depending on prior tasks.

        Args:
            depends_on: List of task IDs this depends on
            analysis_type: Type of analysis (synthesis, comparison, etc.)

        Returns:
            Task ID for further chaining
        """
        task_id = f"analyze_{self.next_id}"
        task = AgentTask(
            id=task_id,
            agent_name="analyzer",
            task_type=analysis_type,
            input_data={},  # Will use results from dependencies
            dependencies=depends_on,
        )
        self.tasks[task_id] = task
        self.next_id += 1
        return task_id

    def add_consolidation_task(self, depends_on: List[str]) -> str:
        """Add consolidation task for results.

        Args:
            depends_on: List of task IDs to consolidate

        Returns:
            Task ID
        """
        task_id = f"consolidate_{self.next_id}"
        task = AgentTask(
            id=task_id,
            agent_name="consolidator",
            task_type="consolidation",
            input_data={},
            dependencies=depends_on,
        )
        self.tasks[task_id] = task
        self.next_id += 1
        return task_id

    def build(self) -> ExecutionPlan:
        """Build execution plan from tasks."""
        plan = ExecutionPlan(plan_id=self.plan_id, project_id=self.project_id, tasks=self.tasks)
        return plan


class WorkflowBuilder:
    """High-level workflow builder for common patterns."""

    @staticmethod
    def create_research_workflow(
        query: str, agents: List[str], with_analysis: bool = True, with_consolidation: bool = True
    ) -> ExecutionPlan:
        """Create a standard research workflow.

        Args:
            query: Research query
            agents: List of agent names
            with_analysis: Whether to add analysis phase
            with_consolidation: Whether to add consolidation phase

        Returns:
            ExecutionPlan ready to execute
        """
        builder = DAGBuilder("research_workflow", project_id=0)

        # Phase 1: Parallel research
        research_tasks = builder.add_research_tasks(query, agents)

        if with_analysis:
            # Phase 2: Analysis
            analysis_task = builder.add_analysis_task(research_tasks, "synthesis")
            final_task = analysis_task
        else:
            final_task = None

        if with_consolidation and final_task:
            # Phase 3: Consolidation
            builder.add_consolidation_task([final_task])

        return builder.build()
