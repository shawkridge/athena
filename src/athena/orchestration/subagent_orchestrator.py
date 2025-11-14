"""SubAgent orchestration for complex memory operations.

Implements the "SubAgents" pattern from the agentic diagram,
allowing specialized agents to handle different aspects of complex operations
in parallel with coordinated feedback.

Example: Consolidation operation spawns:
- Clustering SubAgent (temporal/semantic clustering)
- Validation SubAgent (pattern validation)
- Extraction SubAgent (pattern extraction)
- Integration SubAgent (knowledge graph integration)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Coroutine
from enum import Enum
from datetime import datetime
from abc import ABC, abstractmethod
import asyncio
import logging
import uuid

logger = logging.getLogger(__name__)


class SubAgentType(Enum):
    """Types of specialized subagents."""
    CLUSTERING = "clustering"           # Event clustering and segmentation
    VALIDATION = "validation"           # Pattern/output validation
    EXTRACTION = "extraction"           # Pattern and knowledge extraction
    INTEGRATION = "integration"         # Knowledge graph integration
    OPTIMIZATION = "optimization"       # Performance optimization
    REMEDIATION = "remediation"         # Fixing violations
    LEARNING = "learning"               # Learning from outcomes
    PLANNING = "planning"               # Plan generation and verification
    SYNTHESIS = "synthesis"             # Combining multiple sources


class AgentStatus(Enum):
    """Status of a subagent task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class SubAgentResult:
    """Result from a subagent task."""
    agent_id: str
    agent_type: SubAgentType
    status: AgentStatus
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    confidence: float = 1.0  # Confidence in result quality
    dependencies_satisfied: bool = True
    timestamp: datetime = field(default_factory=datetime.now)

    def is_success(self) -> bool:
        """Check if agent succeeded."""
        return self.status == AgentStatus.COMPLETED


@dataclass
class SubAgentTask:
    """A task for a subagent to execute."""
    task_id: str
    agent_type: SubAgentType
    operation_data: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)  # IDs of prerequisite tasks
    timeout_seconds: float = 30.0
    priority: int = 0  # Higher = more important
    context: Dict[str, Any] = field(default_factory=dict)


class SubAgent(ABC):
    """Base class for specialized agents."""

    def __init__(self, agent_type: SubAgentType):
        """Initialize subagent."""
        self.agent_type = agent_type
        self.agent_id = f"{agent_type.value}_{uuid.uuid4().hex[:8]}"
        self.task_count = 0
        self.success_count = 0
        self.failure_count = 0

    async def execute(self, task: SubAgentTask) -> SubAgentResult:
        """
        Execute a task.

        Must be overridden by subclasses.
        """
        self.task_count += 1

        try:
            start_time = datetime.now()

            # Execute with timeout
            result_data = await asyncio.wait_for(
                self._do_work(task),
                timeout=task.timeout_seconds
            )

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            self.success_count += 1

            return SubAgentResult(
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                status=AgentStatus.COMPLETED,
                output=result_data,
                execution_time_ms=execution_time,
                confidence=1.0,
            )

        except asyncio.TimeoutError:
            self.failure_count += 1
            return SubAgentResult(
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                status=AgentStatus.FAILED,
                error=f"Task timed out after {task.timeout_seconds}s",
            )

        except Exception as e:
            self.failure_count += 1
            return SubAgentResult(
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                status=AgentStatus.FAILED,
                error=str(e),
            )

    @abstractmethod
    async def _do_work(self, task: SubAgentTask) -> Dict[str, Any]:
        """
        Implement agent-specific work.

        Must be overridden by subclasses.
        """
        pass

    def get_success_rate(self) -> float:
        """Get success rate of this agent."""
        if self.task_count == 0:
            return 1.0
        return self.success_count / self.task_count


class ClusteringSubAgent(SubAgent):
    """Specialized agent for clustering events."""

    def __init__(self):
        super().__init__(SubAgentType.CLUSTERING)

    async def _do_work(self, task: SubAgentTask) -> Dict[str, Any]:
        """Cluster events."""
        events = task.operation_data.get("events", [])
        clustering_method = task.operation_data.get("method", "temporal")

        # Simulate clustering work
        await asyncio.sleep(0.1)

        return {
            "clusters": len(events) // 3 if events else 0,
            "method": clustering_method,
            "events_processed": len(events),
        }


class ValidationSubAgent(SubAgent):
    """Specialized agent for validation."""

    def __init__(self):
        super().__init__(SubAgentType.VALIDATION)

    async def _do_work(self, task: SubAgentTask) -> Dict[str, Any]:
        """Validate patterns."""
        patterns = task.operation_data.get("patterns", [])

        # Simulate validation work
        await asyncio.sleep(0.05)

        return {
            "patterns_validated": len(patterns),
            "valid_count": len(patterns),
            "invalid_count": 0,
        }


class ExtractionSubAgent(SubAgent):
    """Specialized agent for pattern extraction."""

    def __init__(self):
        super().__init__(SubAgentType.EXTRACTION)

    async def _do_work(self, task: SubAgentTask) -> Dict[str, Any]:
        """Extract patterns."""
        clusters = task.operation_data.get("clusters", [])

        # Simulate extraction work
        await asyncio.sleep(0.1)

        return {
            "clusters_processed": len(clusters),
            "patterns_extracted": len(clusters) * 2,
        }


class IntegrationSubAgent(SubAgent):
    """Specialized agent for knowledge graph integration."""

    def __init__(self):
        super().__init__(SubAgentType.INTEGRATION)

    async def _do_work(self, task: SubAgentTask) -> Dict[str, Any]:
        """Integrate with knowledge graph."""
        patterns = task.operation_data.get("patterns", [])

        # Simulate integration work
        await asyncio.sleep(0.1)

        return {
            "patterns_integrated": len(patterns),
            "relationships_created": len(patterns) * 3,
        }


class SubAgentOrchestrator:
    """Orchestrate multiple subagents for complex operations."""

    def __init__(self):
        """Initialize orchestrator."""
        self.agents: Dict[SubAgentType, SubAgent] = {
            SubAgentType.CLUSTERING: ClusteringSubAgent(),
            SubAgentType.VALIDATION: ValidationSubAgent(),
            SubAgentType.EXTRACTION: ExtractionSubAgent(),
            SubAgentType.INTEGRATION: IntegrationSubAgent(),
        }
        self.results: Dict[str, SubAgentResult] = {}
        self.task_graph: Dict[str, SubAgentTask] = {}

    def register_agent(self, agent: SubAgent) -> None:
        """Register a new subagent."""
        self.agents[agent.agent_type] = agent

    async def execute_parallel(
        self,
        tasks: List[SubAgentTask],
        enable_feedback_loop: bool = True
    ) -> Dict[str, SubAgentResult]:
        """
        Execute multiple subagent tasks in parallel.

        Args:
            tasks: List of tasks to execute
            enable_feedback_loop: Whether to coordinate results across agents

        Returns:
            Mapping of task IDs to results
        """
        # Build dependency graph
        self.task_graph = {task.task_id: task for task in tasks}

        # Sort by priority (higher first)
        tasks = sorted(tasks, key=lambda t: t.priority, reverse=True)

        # Execute respecting dependencies
        completed = {}

        while len(completed) < len(tasks):
            # Find tasks with all dependencies satisfied
            ready_tasks = [
                t for t in tasks
                if t.task_id not in completed and all(
                    dep_id in completed for dep_id in t.dependencies
                )
            ]

            if not ready_tasks:
                logger.warning("Circular dependency detected in task graph")
                break

            # Execute ready tasks in parallel
            execution_tasks = [
                self._execute_task(task)
                for task in ready_tasks
            ]

            # Wait for all to complete
            results = await asyncio.gather(*execution_tasks, return_exceptions=True)

            # Store results
            for task, result in zip(ready_tasks, results):
                if isinstance(result, Exception):
                    self.results[task.task_id] = SubAgentResult(
                        agent_id="unknown",
                        agent_type=task.agent_type,
                        status=AgentStatus.FAILED,
                        error=str(result),
                    )
                else:
                    self.results[task.task_id] = result

                completed[task.task_id] = result

            # Apply feedback loop if enabled
            if enable_feedback_loop:
                self._apply_feedback_coordination(tasks, completed)

        return self.results

    async def _execute_task(self, task: SubAgentTask) -> SubAgentResult:
        """Execute a single task."""
        if task.agent_type not in self.agents:
            return SubAgentResult(
                agent_id="unknown",
                agent_type=task.agent_type,
                status=AgentStatus.FAILED,
                error=f"No agent registered for type {task.agent_type.value}",
            )

        agent = self.agents[task.agent_type]

        return await agent.execute(task)

    def _apply_feedback_coordination(
        self,
        tasks: List[SubAgentTask],
        completed: Dict[str, SubAgentResult]
    ) -> None:
        """
        Apply feedback from completed tasks to pending tasks.

        This implements the feedback loop from the diagram.
        """
        for task in tasks:
            if task.task_id in completed:
                result = completed[task.task_id]

                # Pass output from this task to dependent tasks
                for dep_task in tasks:
                    if task.task_id in dep_task.dependencies:
                        # Inject result as context for dependent task
                        dep_task.context[f"output_{task.task_id}"] = result.output

    def get_orchestration_insights(self) -> Dict[str, Any]:
        """Get insights from orchestration results."""
        insights = {
            "total_results": len(self.results),
            "successful": sum(1 for r in self.results.values() if r.is_success()),
            "failed": sum(1 for r in self.results.values() if not r.is_success()),
            "agent_health": {},
            "coordination_effectiveness": 0.0,
        }

        # Agent health
        for agent_type, agent in self.agents.items():
            insights["agent_health"][agent_type.value] = {
                "success_rate": agent.get_success_rate(),
                "task_count": agent.task_count,
            }

        # Coordination effectiveness: measure how feedback helped
        insights["coordination_effectiveness"] = self._measure_coordination_effectiveness()

        return insights

    def _measure_coordination_effectiveness(self) -> float:
        """Measure how effective feedback coordination was."""
        if not self.results:
            return 0.0

        # Effectiveness: % of dependent tasks that benefited from prior results
        task_ids = list(self.task_graph.keys())
        tasks_with_deps = [
            t for t in self.task_graph.values()
            if t.dependencies
        ]

        if not tasks_with_deps:
            return 1.0

        benefited = sum(
            1 for t in tasks_with_deps
            if all(dep_id in self.results for dep_id in t.dependencies)
        )

        return benefited / len(tasks_with_deps)

    async def execute_operation(
        self,
        operation_type: str,
        operation_data: Dict[str, Any],
        subagent_types: Optional[List[SubAgentType]] = None
    ) -> Dict[str, Any]:
        """
        Execute a complex operation using subagents.

        Example:
        ```
        result = await orchestrator.execute_operation(
            "consolidate",
            {"events": events},
            [SubAgentType.CLUSTERING, SubAgentType.EXTRACTION, SubAgentType.VALIDATION]
        )
        ```
        """
        subagent_types = subagent_types or list(self.agents.keys())

        # Build task graph for operation
        tasks = []
        base_priority = 100

        for i, agent_type in enumerate(subagent_types):
            task = SubAgentTask(
                task_id=f"{operation_type}_{agent_type.value}_{uuid.uuid4().hex[:4]}",
                agent_type=agent_type,
                operation_data=operation_data.copy(),
                dependencies=[],  # Build dependencies below
                timeout_seconds=30.0,
                priority=base_priority - i,
            )
            tasks.append(task)

        # Execute and aggregate results
        results = await self.execute_parallel(tasks)

        # Aggregate outputs
        aggregated = {
            "operation_type": operation_type,
            "subagent_results": {
                task_id: result.output
                for task_id, result in results.items()
                if result.is_success()
            },
            "failed_agents": [
                task_id
                for task_id, result in results.items()
                if not result.is_success()
            ],
            "coordination_insights": self.get_orchestration_insights(),
        }

        return aggregated
