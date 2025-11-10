"""Orchestration layer - coordination of complex multi-agent operations.

Phase 1-2 Implementation: Task queue coordination system
Phase 3+: Pattern learning and hierarchical scaling

Key components:
- TaskQueue: Task lifecycle in episodic memory
- AgentRegistry: Agent capabilities in knowledge graph
- CapabilityRouter: Skill-based task routing
- SubAgentOrchestrator: Parallel specialization (existing)
- EventBus: Pub-sub for events (Phase 2)
- OrchestrationManager: Unified coordinator (Phase 3)

Example::

    from athena.orchestration import TaskQueue, AgentRegistry, CapabilityRouter

    # Register agent
    registry.register_agent("researcher", ["python", "web"])

    # Create and route task
    task_id = queue.create_task("Research asyncio", "research",
                               requirements=["python"])
    agent = router.route_task({"requirements": ["python"]})

    # Execute workflow
    queue.assign_task(task_id, agent)
    queue.complete_task(task_id, result, metrics)
"""

# Phase 1-2: New task coordination
from .models import Task, Agent, TaskStatus, RoutingDecision
from .task_queue import TaskQueue
from .agent_registry import AgentRegistry
from .capability_router import CapabilityRouter

# Phase 1+: Existing subagent coordination
from .subagent_orchestrator import (
    SubAgentOrchestrator,
    SubAgent,
    SubAgentTask,
    SubAgentResult,
    SubAgentType,
    AgentStatus,
    ClusteringSubAgent,
    ValidationSubAgent,
    ExtractionSubAgent,
    IntegrationSubAgent,
)

__all__ = [
    # Phase 1-2: Task coordination
    "Task",
    "Agent",
    "TaskStatus",
    "RoutingDecision",
    "TaskQueue",
    "AgentRegistry",
    "CapabilityRouter",
    # Phase 1+: SubAgent coordination
    "SubAgentOrchestrator",
    "SubAgent",
    "SubAgentTask",
    "SubAgentResult",
    "SubAgentType",
    "AgentStatus",
    "ClusteringSubAgent",
    "ValidationSubAgent",
    "ExtractionSubAgent",
    "IntegrationSubAgent",
]
