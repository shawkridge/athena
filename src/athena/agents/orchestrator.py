"""
Agent Orchestrator

Coordinates all agents and manages execution flow.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import AgentType, BaseAgent
from .message_bus import Message, MessageBus, MessageType


class AgentOrchestrator:
    """
    Orchestrates collaboration between agents.

    Responsibilities:
    - Initialize and manage agent lifecycle
    - Route messages through message bus
    - Track execution history
    - Coordinate multi-agent workflows
    """

    def __init__(self, db_path: str):
        """
        Initialize orchestrator.

        Args:
            db_path: Path to memory database
        """
        self.db_path = db_path
        self.message_bus = MessageBus()
        self.agents: Dict[AgentType, BaseAgent] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self._running = False
        self._execution_counter = 0

    async def initialize(self) -> None:
        """Initialize orchestrator and all agents"""
        await self.message_bus.initialize()
        self._running = True

        # Initialize all registered agents
        for agent in self.agents.values():
            await agent.initialize()
            # Subscribe agent to its message type
            await self.message_bus.subscribe(
                agent.agent_type.value,
                agent.process_message
            )

    async def shutdown(self) -> None:
        """Graceful shutdown of all agents and bus"""
        self._running = False

        # Shutdown all agents
        for agent in self.agents.values():
            await agent.shutdown()

        # Shutdown message bus
        await self.message_bus.shutdown()

    def register_agent(self, agent: BaseAgent) -> None:
        """
        Register an agent with orchestrator.

        Args:
            agent: Agent instance to register
        """
        self.agents[agent.agent_type] = agent

    async def decompose_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Request Planner to decompose task.

        Args:
            task: Task description with metadata

        Returns:
            Plan returned by Planner agent
        """
        if AgentType.PLANNER not in self.agents:
            return {
                "status": "error",
                "error": "Planner agent not registered"
            }

        self._execution_counter += 1

        message = Message(
            sender="orchestrator",
            recipient=AgentType.PLANNER.value,
            message_type=MessageType.REQUEST,
            payload={
                "action": "decompose",
                "task": task,
                "execution_id": self._execution_counter
            },
            priority=task.get("salience", 0.5),
            response_expected=True
        )

        result = await self.message_bus.send_request(message)
        self.execution_history.append({
            "execution_id": self._execution_counter,
            "action": "decompose_task",
            "input": task,
            "output": result,
            "timestamp": datetime.now().isoformat()
        })

        return result

    async def execute_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Request Executor to run plan.

        Args:
            plan: Execution plan

        Returns:
            Execution result returned by Executor
        """
        if AgentType.EXECUTOR not in self.agents:
            return {
                "status": "error",
                "error": "Executor agent not registered"
            }

        self._execution_counter += 1

        message = Message(
            sender="orchestrator",
            recipient=AgentType.EXECUTOR.value,
            message_type=MessageType.REQUEST,
            payload={
                "action": "execute",
                "plan": plan,
                "execution_id": self._execution_counter
            },
            priority=plan.get("salience", 0.5),
            response_expected=True
        )

        result = await self.message_bus.send_request(message)
        self.execution_history.append({
            "execution_id": self._execution_counter,
            "action": "execute_plan",
            "input": plan,
            "output": result,
            "timestamp": datetime.now().isoformat()
        })

        return result

    async def full_workflow(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute full workflow: Decompose → Execute.

        Args:
            task: High-level task description

        Returns:
            Complete workflow result
        """
        start_time = datetime.now()

        # Step 1: Decompose task
        decompose_result = await self.decompose_task(task)
        if decompose_result.get("status") == "error":
            return {
                "status": "error",
                "error": f"Decomposition failed: {decompose_result.get('error')}",
                "duration_ms": (datetime.now() - start_time).total_seconds() * 1000
            }

        plan = decompose_result.get("plan")
        plan_confidence = decompose_result.get("confidence", 0.0)

        if plan_confidence < 0.5:
            return {
                "status": "warning",
                "error": f"Plan confidence low ({plan_confidence:.2%}), proceeding anyway",
                "plan": plan,
                "duration_ms": (datetime.now() - start_time).total_seconds() * 1000
            }

        # Step 2: Execute plan
        execution_result = await self.execute_plan(plan)
        if execution_result.get("status") == "error":
            return {
                "status": "error",
                "error": f"Execution failed: {execution_result.get('error')}",
                "plan": plan,
                "duration_ms": (datetime.now() - start_time).total_seconds() * 1000
            }

        return {
            "status": "success",
            "task": task,
            "plan": plan,
            "execution": execution_result,
            "total_duration_ms": (datetime.now() - start_time).total_seconds() * 1000
        }

    async def get_agent_status(self, agent_type: Optional[AgentType] = None) -> Dict[str, Any]:
        """
        Get status of one or all agents.

        Args:
            agent_type: Specific agent type, or None for all

        Returns:
            Status report(s)
        """
        if agent_type:
            if agent_type in self.agents:
                return await self.agents[agent_type].heartbeat()
            return {"error": f"Unknown agent type: {agent_type}"}

        statuses = {}
        for atype, agent in self.agents.items():
            statuses[atype.value] = await agent.heartbeat()

        return {
            "orchestrator_status": "running" if self._running else "stopped",
            "agents": statuses,
            "execution_counter": self._execution_counter,
            "message_bus_stats": self.message_bus.get_queue_stats()
        }

    async def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent execution history.

        Args:
            limit: Maximum entries to return

        Returns:
            Recent execution history
        """
        return self.execution_history[-limit:]

    async def get_message_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get message bus activity log.

        Args:
            limit: Maximum messages to return

        Returns:
            Recent message activity
        """
        return self.message_bus.get_recent_messages(limit)

    def is_healthy(self) -> bool:
        """
        Check if orchestrator is healthy.

        Returns:
            True if all agents are healthy
        """
        if not self._running:
            return False

        for agent in self.agents.values():
            if not agent.is_healthy():
                return False

        return True

    def __repr__(self) -> str:
        agent_count = len(self.agents)
        healthy = sum(1 for a in self.agents.values() if a.is_healthy())
        return (
            f"AgentOrchestrator(agents={agent_count}, healthy={healthy}, "
            f"executions={self._execution_counter})"
        )
