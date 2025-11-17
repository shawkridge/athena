"""WorkflowOrchestratorAgent - Dynamic task routing and agent orchestration.

This agent manages complex workflows by classifying tasks, selecting appropriate
agents, resolving dependencies, and balancing workload. It acts as a coordinator
between specialized agents, ensuring tasks are routed efficiently and work is
distributed appropriately.

The agent integrates with:
- All other agents: Routes tasks to appropriate handlers
- MetacognitionAgent: Monitors overall system health and performance
- Memory system: Learns successful routing patterns
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# Import coordinator base class
from .coordinator import AgentCoordinator
from ..orchestration.adaptive_agent import AdaptiveAgent

# Import core memory operations
from ..episodic.operations import remember as remember_event
from ..memory.operations import store as store_fact

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of tasks that can be routed."""
    CODE_ANALYSIS = "code_analysis"
    RESEARCH = "research"
    MEMORY_MANAGEMENT = "memory_management"
    PATTERN_EXTRACTION = "pattern_extraction"
    SYSTEM_HEALTH = "system_health"
    WORKFLOW = "workflow"
    UNKNOWN = "unknown"


class AgentType(Enum):
    """Available agent types."""
    CODE_ANALYZER = "code-analyzer"
    RESEARCH_COORDINATOR = "research-coordinator"
    MEMORY_COORDINATOR = "memory-coordinator"
    PATTERN_EXTRACTOR = "pattern-extractor"
    METACOGNITION = "metacognition"
    WORKFLOW_ORCHESTRATOR = "workflow-orchestrator"


@dataclass
class TaskRoute:
    """Routing decision for a task."""
    task_id: str
    task_type: TaskType
    agent: AgentType
    confidence: float  # 0.0-1.0
    reasoning: str
    priority: int  # 1-10, higher = more urgent
    estimated_effort_hours: float
    dependencies: List[str] = None


@dataclass
class AgentLoad:
    """Represents current load on an agent."""
    agent: AgentType
    queued_tasks: int
    active_tasks: int
    avg_completion_time_ms: float
    success_rate: float  # 0.0-1.0
    health_status: str  # healthy, busy, overloaded


class WorkflowOrchestratorAgent(AgentCoordinator, AdaptiveAgent):
    """Dynamic task routing and agent orchestration.

    Manages workflow by:
    - Classifying incoming tasks
    - Selecting appropriate agents
    - Resolving task dependencies
    - Balancing workload across agents
    - Monitoring agent performance
    """

    # Task classification rules
    TASK_CLASSIFIERS = {
        "code": {
            "keywords": ["code", "analysis", "review", "refactor", "optimize", "bug"],
            "type": TaskType.CODE_ANALYSIS,
            "agent": AgentType.CODE_ANALYZER,
            "confidence": 0.9,
        },
        "research": {
            "keywords": ["research", "investigate", "learn", "understand", "discover"],
            "type": TaskType.RESEARCH,
            "agent": AgentType.RESEARCH_COORDINATOR,
            "confidence": 0.85,
        },
        "memory": {
            "keywords": ["remember", "recall", "memory", "memorize", "forget"],
            "type": TaskType.MEMORY_MANAGEMENT,
            "agent": AgentType.MEMORY_COORDINATOR,
            "confidence": 0.8,
        },
        "pattern": {
            "keywords": ["pattern", "extract", "learn", "consolidate", "procedure"],
            "type": TaskType.PATTERN_EXTRACTION,
            "agent": AgentType.PATTERN_EXTRACTOR,
            "confidence": 0.85,
        },
        "health": {
            "keywords": ["health", "status", "metrics", "performance", "monitor"],
            "type": TaskType.SYSTEM_HEALTH,
            "agent": AgentType.METACOGNITION,
            "confidence": 0.9,
        },
    }

    def __init__(self):
        """Initialize the Workflow Orchestrator Agent."""
        super().__init__(
            agent_id="workflow-orchestrator",
            agent_type="orchestrator",
        )
        self.tasks_routed = 0
        self.agents_spawned = 0
        self.agent_loads: Dict[AgentType, AgentLoad] = {}
        self._initialize_agent_loads()

    async def classify_task(self, task_description: str) -> Tuple[TaskType, float]:
        """Classify a task to determine best agent.

        Args:
            task_description: Description of the task

        Returns:
            Tuple of (task_type, confidence)
        """
        logger.info(f"Classifying task: {task_description[:100]}")

        desc_lower = task_description.lower()
        best_match = None
        best_confidence = 0.0

        # Check each classifier
        for classifier_name, classifier in self.TASK_CLASSIFIERS.items():
            # Count keyword matches
            matches = sum(
                1 for keyword in classifier["keywords"]
                if keyword in desc_lower
            )

            if matches > 0:
                # Confidence based on number of matches
                confidence = min(0.95, classifier["confidence"] * (1 + matches * 0.1))

                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = classifier["type"]

        # Default to unknown if no match
        if not best_match:
            best_match = TaskType.UNKNOWN
            best_confidence = 0.3

        logger.info(f"Task classified as: {best_match.value} (confidence: {best_confidence:.2%})")
        return best_match, best_confidence

    async def select_agent(
        self,
        task_type: TaskType,
    ) -> Tuple[AgentType, float]:
        """Select best agent for task type.

        Args:
            task_type: Type of task to route

        Returns:
            Tuple of (agent, confidence)
        """
        logger.info(f"Selecting agent for task type: {task_type.value}")

        # Find classifier for this task type
        for classifier in self.TASK_CLASSIFIERS.values():
            if classifier["type"] == task_type:
                agent = AgentType[classifier["agent"].name]
                confidence = classifier["confidence"]

                # Adjust confidence based on agent load
                load = self.agent_loads.get(agent)
                if load:
                    if load.health_status == "overloaded":
                        confidence *= 0.7  # Reduce confidence if overloaded
                    elif load.health_status == "busy":
                        confidence *= 0.85

                logger.info(f"Selected agent: {agent.value} (confidence: {confidence:.2%})")
                return agent, confidence

        # Default selection
        logger.warning(f"No specific agent found for {task_type.value}, using default")
        return AgentType.WORKFLOW_ORCHESTRATOR, 0.5

    async def resolve_dependencies(
        self,
        task_id: str,
        dependencies: Optional[List[str]] = None,
    ) -> List[str]:
        """Resolve task dependencies and return ordered task list.

        Args:
            task_id: Main task ID
            dependencies: List of task IDs this task depends on

        Returns:
            Ordered list of tasks to execute
        """
        logger.info(f"Resolving dependencies for task: {task_id}")

        if not dependencies:
            return [task_id]

        # Topological sort of dependencies
        ordered = []
        visited = set()

        def visit(task):
            if task in visited:
                return
            visited.add(task)

            # Add dependencies first
            if task in (dependencies or {}):
                for dep in dependencies.get(task, []):
                    visit(dep)

            ordered.append(task)

        visit(task_id)

        logger.info(f"Task order resolved: {' → '.join(ordered)}")
        return ordered

    async def balance_workload(self) -> Dict[str, Any]:
        """Monitor and balance agent workload.

        Returns:
            Workload balancing decisions
        """
        logger.info("Balancing agent workload")

        decisions = {
            "timestamp": datetime.utcnow().isoformat(),
            "load_distribution": {},
            "recommendations": [],
            "rebalancing_actions": [],
        }

        try:
            # Calculate overall load
            total_tasks = sum(
                load.queued_tasks + load.active_tasks
                for load in self.agent_loads.values()
            )

            if total_tasks == 0:
                decisions["status"] = "idle"
                return decisions

            # Identify overloaded and underloaded agents
            avg_load = total_tasks / len(self.agent_loads)
            overloaded = []
            underloaded = []

            for agent, load in self.agent_loads.items():
                current_load = load.queued_tasks + load.active_tasks
                decisions["load_distribution"][agent.value] = current_load

                if current_load > avg_load * 1.5:
                    overloaded.append((agent, current_load))
                elif current_load < avg_load * 0.5:
                    underloaded.append((agent, current_load))

            # Generate recommendations
            if overloaded:
                for agent, load in overloaded:
                    decisions["recommendations"].append({
                        "agent": agent.value,
                        "status": "overloaded",
                        "current_load": load,
                        "recommendation": f"Consider delegating tasks from {agent.value}",
                    })

            if underloaded:
                for agent, load in underloaded:
                    decisions["recommendations"].append({
                        "agent": agent.value,
                        "status": "underutilized",
                        "current_load": load,
                        "recommendation": f"Can handle more tasks from {agent.value}",
                    })

            decisions["status"] = "balanced" if not (overloaded and underloaded) else "rebalancing"
            logger.info(f"Workload analysis: {len(overloaded)} overloaded, {len(underloaded)} underloaded")

        except Exception as e:
            logger.error(f"Error balancing workload: {e}")
            decisions["error"] = str(e)

        return decisions

    async def route_task(
        self,
        task_description: str,
        priority: int = 5,
        dependencies: Optional[List[str]] = None,
    ) -> TaskRoute:
        """Route a task to the appropriate agent.

        Args:
            task_description: Description of the task
            priority: Priority level (1-10, higher = more urgent)
            dependencies: Optional list of task dependencies

        Returns:
            TaskRoute with routing decision
        """
        logger.info(f"Routing task with priority {priority}")
        self.tasks_routed += 1

        try:
            # Classify task
            task_type, type_confidence = await self.classify_task(task_description)

            # Select agent
            agent, agent_confidence = await self.select_agent(task_type)

            # Resolve dependencies
            ordered_tasks = await self.resolve_dependencies(
                f"task-{self.tasks_routed}",
                {f"task-{self.tasks_routed}": dependencies or []}
            )

            # Create routing decision
            route = TaskRoute(
                task_id=f"task-{self.tasks_routed}",
                task_type=task_type,
                agent=agent,
                confidence=min(type_confidence, agent_confidence),
                reasoning=f"Task matched {task_type.value} patterns, routing to {agent.value}",
                priority=priority,
                estimated_effort_hours=self._estimate_effort(task_type),
                dependencies=dependencies or [],
            )

            # Store routing decision
            await store_fact(
                content=f"Task routed: {task_type.value} → {agent.value}",
                topics=["routing", "orchestration", task_type.value],
            )

            logger.info(f"Task routed to {agent.value} (confidence: {route.confidence:.2%})")

        except Exception as e:
            logger.error(f"Error routing task: {e}")
            route = TaskRoute(
                task_id=f"task-{self.tasks_routed}",
                task_type=TaskType.UNKNOWN,
                agent=AgentType.WORKFLOW_ORCHESTRATOR,
                confidence=0.0,
                reasoning=f"Error during routing: {str(e)}",
                priority=priority,
                estimated_effort_hours=1.0,
            )

        return route

    # Private helper methods

    def _initialize_agent_loads(self):
        """Initialize load tracking for all agents."""
        for agent_type in AgentType:
            self.agent_loads[agent_type] = AgentLoad(
                agent=agent_type,
                queued_tasks=0,
                active_tasks=0,
                avg_completion_time_ms=0.0,
                success_rate=0.9,
                health_status="healthy",
            )

    def _estimate_effort(self, task_type: TaskType) -> float:
        """Estimate effort for a task type in hours."""
        estimates = {
            TaskType.CODE_ANALYSIS: 0.5,
            TaskType.RESEARCH: 2.0,
            TaskType.MEMORY_MANAGEMENT: 0.1,
            TaskType.PATTERN_EXTRACTION: 1.0,
            TaskType.SYSTEM_HEALTH: 0.2,
            TaskType.WORKFLOW: 0.5,
            TaskType.UNKNOWN: 1.0,
        }
        return estimates.get(task_type, 1.0)
