"""Lightweight inference planning for resource-constrained environments.

Provides efficient task decomposition and execution planning without expensive
LLM calls. Optimized for:
- Edge devices (limited compute)
- Mobile environments
- Local-only inference
- High-throughput scenarios (minimize latency)

Strategies:
- Rule-based decomposition (no LLM)
- Heuristic task ordering
- Resource-aware scheduling
- Incremental execution
- Early termination on confidence
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ExecutionStrategy(str, Enum):
    """Execution strategies for lightweight planning."""

    GREEDY = "greedy"  # Execute highest-priority tasks first
    INCREMENTAL = "incremental"  # Execute in order, stop when confident
    PARALLEL = "parallel"  # Execute independent tasks concurrently
    LAZY = "lazy"  # Execute only when needed
    STREAMING = "streaming"  # Stream results as available


class ResourceConstraint(str, Enum):
    """Resource constraints in environment."""

    CPU_LIMITED = "cpu_limited"  # Limited compute (e.g., mobile)
    MEMORY_LIMITED = "memory_limited"  # Limited RAM
    NETWORK_LATENCY = "network_latency"  # High latency (e.g., satellite)
    BANDWIDTH_LIMITED = "bandwidth_limited"  # Limited download/upload
    ENERGY_LIMITED = "energy_limited"  # Battery-powered device


@dataclass
class ResourceEstimate:
    """Estimated resource requirements for operation."""

    operation: str
    estimated_tokens: int
    estimated_latency_ms: float
    estimated_cost_dollars: float
    memory_mb: float = 0.0
    cpu_percent: float = 0.0

    def is_feasible_in_budget(
        self,
        max_tokens: Optional[int] = None,
        max_latency_ms: Optional[float] = None,
        max_cost: Optional[float] = None,
        max_memory_mb: Optional[float] = None,
    ) -> bool:
        """Check if operation fits within budget constraints.

        Args:
            max_tokens: Maximum tokens allowed
            max_latency_ms: Maximum latency in milliseconds
            max_cost: Maximum cost in dollars
            max_memory_mb: Maximum memory in MB

        Returns:
            True if operation is feasible
        """
        if max_tokens is not None and self.estimated_tokens > max_tokens:
            return False
        if max_latency_ms is not None and self.estimated_latency_ms > max_latency_ms:
            return False
        if max_cost is not None and self.estimated_cost_dollars > max_cost:
            return False
        if max_memory_mb is not None and self.memory_mb > max_memory_mb:
            return False

        return True


@dataclass
class LightweightTask:
    """Single task in lightweight execution plan."""

    task_id: str
    description: str
    priority: int  # 0-100 (higher = more important)
    required_inputs: list[str] = field(default_factory=list)
    estimated_tokens: int = 100
    estimated_latency_ms: float = 100.0

    # Execution properties
    is_critical: bool = False  # Cannot skip
    can_stream: bool = True  # Results can be streamed incrementally
    can_parallelize: bool = True  # Can run concurrently with others


@dataclass
class ExecutionPlan:
    """Plan for executing tasks in lightweight environment."""

    plan_id: str
    strategy: ExecutionStrategy
    tasks: list[LightweightTask] = field(default_factory=list)
    total_estimated_tokens: int = 0
    total_estimated_latency_ms: float = 0.0
    total_estimated_cost: float = 0.0

    # Execution metadata
    constraints: list[ResourceConstraint] = field(default_factory=list)
    confidence_threshold: float = 0.7  # Stop when confidence reached

    def add_task(self, task: LightweightTask):
        """Add task to plan."""
        self.tasks.append(task)
        self.total_estimated_tokens += task.estimated_tokens
        self.total_estimated_latency_ms += task.estimated_latency_ms


@dataclass
class PlanningConstraints:
    """Constraints for execution planning."""

    max_total_tokens: Optional[int] = 10000
    max_latency_ms: Optional[float] = 5000.0  # 5 seconds
    max_cost_dollars: Optional[float] = 0.10
    max_memory_mb: Optional[float] = 256.0
    min_confidence_threshold: float = 0.7

    resource_constraints: list[ResourceConstraint] = field(default_factory=list)


class LightweightPlanner:
    """Plans task execution for resource-constrained environments."""

    def __init__(self, constraints: Optional[PlanningConstraints] = None):
        """Initialize planner.

        Args:
            constraints: Resource constraints (uses defaults if not provided)
        """
        self.constraints = constraints or PlanningConstraints()
        self.task_library: dict[str, LightweightTask] = {}

    def register_task(self, task: LightweightTask):
        """Register task in library.

        Args:
            task: Task to register
        """
        self.task_library[task.task_id] = task
        logger.debug(f"Registered task: {task.task_id}")

    def estimate_resource_usage(
        self, task: LightweightTask
    ) -> ResourceEstimate:
        """Estimate resources needed for task.

        Args:
            task: Task to estimate

        Returns:
            Resource estimate
        """
        # Simple heuristics (no LLM needed)
        # These can be enhanced with real profiling data

        # Token estimate: based on description length
        token_estimate = max(100, len(task.description) // 4)

        # Latency: based on task complexity
        # Simple heuristic: priority * 10ms
        latency_estimate = task.estimated_latency_ms

        # Cost: based on tokens (assume $0.000001 per token)
        cost_estimate = token_estimate * 0.000001

        # Memory: estimate based on task type
        memory_estimate = 16.0  # Base memory

        # CPU: simple estimate
        cpu_estimate = task.priority / 100.0 * 50  # 0-50% CPU

        return ResourceEstimate(
            operation=task.task_id,
            estimated_tokens=token_estimate,
            estimated_latency_ms=latency_estimate,
            estimated_cost_dollars=cost_estimate,
            memory_mb=memory_estimate,
            cpu_percent=cpu_estimate,
        )

    def create_plan(
        self,
        task_ids: list[str],
        strategy: ExecutionStrategy = ExecutionStrategy.INCREMENTAL,
        dependencies: Optional[dict[str, list[str]]] = None,
    ) -> ExecutionPlan:
        """Create execution plan for tasks.

        Args:
            task_ids: IDs of tasks to execute
            strategy: Execution strategy
            dependencies: Task dependencies (dict of task_id -> [required_task_ids])

        Returns:
            Execution plan
        """
        plan = ExecutionPlan(
            plan_id=f"plan_{hash(str(task_ids)) % 1000000}",
            strategy=strategy,
            constraints=self.constraints.resource_constraints,
            confidence_threshold=self.constraints.min_confidence_threshold,
        )

        # Resolve dependencies
        ordered_tasks = self._topological_sort(task_ids, dependencies or {})

        # Filter for feasibility
        for task_id in ordered_tasks:
            if task_id not in self.task_library:
                logger.warning(f"Task {task_id} not found in library")
                continue

            task = self.task_library[task_id]
            estimate = self.estimate_resource_usage(task)

            # Check if task fits in budget
            if estimate.is_feasible_in_budget(
                max_tokens=self.constraints.max_total_tokens,
                max_latency_ms=self.constraints.max_latency_ms,
                max_cost=self.constraints.max_cost_dollars,
                max_memory_mb=self.constraints.max_memory_mb,
            ):
                plan.add_task(task)
            else:
                logger.debug(f"Task {task_id} exceeds resource constraints")

                # For critical tasks, include anyway
                if task.is_critical:
                    plan.add_task(task)
                    logger.warning(
                        f"Including critical task {task_id} despite constraint violation"
                    )

        # Sort tasks according to strategy
        plan.tasks = self._apply_strategy(plan.tasks, strategy)

        return plan

    def _topological_sort(
        self, task_ids: list[str], dependencies: dict[str, list[str]]
    ) -> list[str]:
        """Sort tasks by dependencies.

        Args:
            task_ids: Task IDs to sort
            dependencies: Dependency map

        Returns:
            Topologically sorted task IDs
        """
        # Simple topological sort (Kahn's algorithm)
        sorted_tasks = []
        completed = set()

        max_iterations = len(task_ids) + 1
        iterations = 0

        while len(sorted_tasks) < len(task_ids) and iterations < max_iterations:
            iterations += 1

            for task_id in task_ids:
                if task_id in completed:
                    continue

                # Check if dependencies are met
                required = dependencies.get(task_id, [])
                if all(req in completed for req in required):
                    sorted_tasks.append(task_id)
                    completed.add(task_id)

        # Add any remaining tasks (in case of cycles)
        for task_id in task_ids:
            if task_id not in sorted_tasks:
                sorted_tasks.append(task_id)

        return sorted_tasks

    def _apply_strategy(
        self, tasks: list[LightweightTask], strategy: ExecutionStrategy
    ) -> list[LightweightTask]:
        """Sort tasks according to execution strategy.

        Args:
            tasks: Tasks to sort
            strategy: Execution strategy

        Returns:
            Sorted tasks
        """
        if strategy == ExecutionStrategy.GREEDY:
            # Sort by priority (descending)
            return sorted(tasks, key=lambda t: t.priority, reverse=True)

        elif strategy == ExecutionStrategy.INCREMENTAL:
            # Sort by priority, but only include critical ones
            critical = [t for t in tasks if t.is_critical]
            non_critical = [t for t in tasks if not t.is_critical]

            critical.sort(key=lambda t: t.priority, reverse=True)
            non_critical.sort(key=lambda t: t.priority, reverse=True)

            return critical + non_critical

        elif strategy == ExecutionStrategy.PARALLEL:
            # Group parallelizable tasks
            parallelizable = [t for t in tasks if t.can_parallelize]
            sequential = [t for t in tasks if not t.can_parallelize]

            return parallelizable + sequential

        elif strategy == ExecutionStrategy.LAZY:
            # Defer non-critical tasks
            critical = [t for t in tasks if t.is_critical]
            non_critical = [t for t in tasks if not t.is_critical]

            return critical + non_critical

        else:  # STREAMING
            # Prioritize streamable tasks
            streamable = [t for t in tasks if t.can_stream]
            non_streamable = [t for t in tasks if not t.can_stream]

            return streamable + non_streamable

    def get_optimization_suggestions(self, plan: ExecutionPlan) -> list[str]:
        """Get suggestions to optimize plan.

        Args:
            plan: Execution plan to optimize

        Returns:
            List of optimization suggestions
        """
        suggestions = []

        # Check token budget
        if self.constraints.max_total_tokens:
            if plan.total_estimated_tokens > self.constraints.max_total_tokens:
                pct_over = (
                    plan.total_estimated_tokens / self.constraints.max_total_tokens - 1
                )
                suggestions.append(
                    f"Plan exceeds token budget by {pct_over:.0%}. "
                    f"Consider reducing task scope or using inference mode."
                )

        # Check latency budget
        if self.constraints.max_latency_ms:
            if plan.total_estimated_latency_ms > self.constraints.max_latency_ms:
                pct_over = (
                    plan.total_estimated_latency_ms / self.constraints.max_latency_ms - 1
                )
                suggestions.append(
                    f"Plan exceeds latency budget by {pct_over:.0%}. "
                    f"Consider using parallel execution or streaming results."
                )

        # Check for optimization opportunities
        parallelizable = sum(1 for t in plan.tasks if t.can_parallelize)
        if parallelizable > 1 and plan.strategy != ExecutionStrategy.PARALLEL:
            suggestions.append(
                f"{parallelizable} tasks can be parallelized. "
                f"Consider switching to PARALLEL strategy."
            )

        streamable = sum(1 for t in plan.tasks if t.can_stream)
        if streamable > 1 and plan.strategy != ExecutionStrategy.STREAMING:
            suggestions.append(
                f"{streamable} tasks support streaming. "
                f"Consider switching to STREAMING strategy for better UX."
            )

        # Check for CPU-constrained environments
        if ResourceConstraint.CPU_LIMITED in self.constraints.resource_constraints:
            high_cpu_tasks = [t for t in plan.tasks if t.priority > 70]
            if high_cpu_tasks:
                suggestions.append(
                    f"Environment is CPU-limited. Consider deferring "
                    f"{len(high_cpu_tasks)} high-priority tasks."
                )

        return suggestions

    def summary_report(self, plan: ExecutionPlan) -> str:
        """Generate execution plan summary.

        Args:
            plan: Execution plan

        Returns:
            Human-readable summary
        """
        suggestions = self.get_optimization_suggestions(plan)

        lines = [
            "=" * 60,
            "LIGHTWEIGHT EXECUTION PLAN",
            "=" * 60,
            "",
            f"Plan ID: {plan.plan_id}",
            f"Strategy: {plan.strategy.value}",
            f"Tasks: {len(plan.tasks)}",
            "",
            "RESOURCE ESTIMATES",
            "-" * 60,
            f"Total Tokens: {plan.total_estimated_tokens:,}",
            f"Total Latency: {plan.total_estimated_latency_ms:.0f}ms",
            f"Total Cost: ${plan.total_estimated_cost:.6f}",
            "",
            "BUDGET STATUS",
            "-" * 60,
        ]

        # Check constraints
        if self.constraints.max_total_tokens:
            usage_pct = (
                plan.total_estimated_tokens / self.constraints.max_total_tokens * 100
            )
            status = "✓" if usage_pct <= 100 else "✗"
            lines.append(
                f"{status} Tokens: {plan.total_estimated_tokens:,} "
                f"/ {self.constraints.max_total_tokens:,} ({usage_pct:.0f}%)"
            )

        if self.constraints.max_latency_ms:
            usage_pct = (
                plan.total_estimated_latency_ms / self.constraints.max_latency_ms * 100
            )
            status = "✓" if usage_pct <= 100 else "✗"
            lines.append(
                f"{status} Latency: {plan.total_estimated_latency_ms:.0f}ms "
                f"/ {self.constraints.max_latency_ms:.0f}ms ({usage_pct:.0f}%)"
            )

        if suggestions:
            lines.extend(["", "OPTIMIZATION SUGGESTIONS", "-" * 60])
            for i, suggestion in enumerate(suggestions[:3], 1):
                lines.append(f"{i}. {suggestion}")

        lines.extend(
            [
                "",
                "EXECUTION ORDER",
                "-" * 60,
            ]
        )

        for i, task in enumerate(plan.tasks, 1):
            lines.append(
                f"{i}. {task.description} "
                f"(priority: {task.priority}, tokens: {task.estimated_tokens})"
            )

        return "\n".join(lines)
