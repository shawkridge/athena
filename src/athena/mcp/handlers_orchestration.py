"""MCP handlers for orchestration operations.

Exposes task queue, agent registry, and routing as MCP tools.
Implements 30+ operations for multi-agent coordination.
"""

from typing import Optional, List, Dict, Any

from ..orchestration.task_queue import TaskQueue
from ..orchestration.agent_registry import AgentRegistry
from ..orchestration.capability_router import CapabilityRouter
from ..orchestration.models import Task, TaskStatus


class OrchestrationHandlers:
    """MCP handlers for orchestration operations."""

    def __init__(
        self,
        task_queue: TaskQueue,
        registry: AgentRegistry,
        router: CapabilityRouter,
    ):
        """Initialize handlers.

        Args:
            task_queue: TaskQueue instance
            registry: AgentRegistry instance
            router: CapabilityRouter instance
        """
        self.queue = task_queue
        self.registry = registry
        self.router = router

    def register_tools(self, server):
        """Register all orchestration tools with MCP server.

        Args:
            server: MCP server instance
        """

        # ========== Task Management (8 tools) ==========

        @server.tool()
        def orchestration_create_task(
            content: str,
            task_type: str,
            priority: str = "medium",
            requirements: Optional[List[str]] = None,
            dependencies: Optional[List[str]] = None,
        ) -> Dict[str, Any]:
            """Create a new task in the queue.

            Args:
                content: Task description/prompt
                task_type: Type of task (research, analysis, synthesis, etc.)
                priority: Task priority (low, medium, high)
                requirements: Required agent capabilities
                dependencies: Task IDs this task depends on

            Returns:
                Dict with task_id and status
            """
            task_id = self.queue.create_task(
                content, task_type, priority, requirements, dependencies
            )

            return {
                "task_id": task_id,
                "status": "pending",
                "message": f"Task created: {task_id}",
            }

        @server.tool()
        def orchestration_poll_tasks(
            agent_id: Optional[str] = None,
            status: str = "pending",
            limit: int = 10,
        ) -> Dict[str, Any]:
            """Poll for pending/assigned tasks.

            Args:
                agent_id: If specified, only tasks assigned to this agent
                status: Task status to poll (pending, assigned, running)
                limit: Max tasks to return

            Returns:
                Dict with list of tasks
            """
            tasks = self.queue.poll_tasks(agent_id, status, limit)

            return {
                "count": len(tasks),
                "tasks": [
                    {
                        "id": t.id,
                        "content": t.content,
                        "type": t.task_type,
                        "priority": t.priority.value,
                        "requirements": t.requirements,
                        "status": t.status.value,
                    }
                    for t in tasks
                ],
            }

        @server.tool()
        def orchestration_assign_task(task_id: str, agent_id: str) -> Dict[str, Any]:
            """Assign task to specific agent.

            Args:
                task_id: Task UUID
                agent_id: Agent ID

            Returns:
                Dict with assignment status
            """
            try:
                self.queue.assign_task(task_id, agent_id)
                return {
                    "task_id": task_id,
                    "assigned_to": agent_id,
                    "status": "assigned",
                    "message": f"Task {task_id} assigned to {agent_id}",
                }
            except ValueError as e:
                return {"error": str(e)}

        @server.tool()
        def orchestration_start_task(task_id: str) -> Dict[str, Any]:
            """Mark task as running.

            Args:
                task_id: Task UUID

            Returns:
                Dict with task status
            """
            try:
                self.queue.start_task(task_id)
                return {
                    "task_id": task_id,
                    "status": "running",
                    "message": f"Task {task_id} started",
                }
            except Exception as e:
                return {"error": str(e)}

        @server.tool()
        def orchestration_complete_task(
            task_id: str, result: str, metrics: Optional[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
            """Mark task as completed.

            Args:
                task_id: Task UUID
                result: Task result/output
                metrics: Execution metrics (duration_ms, rows_processed, etc.)

            Returns:
                Dict with task completion status
            """
            try:
                self.queue.complete_task(task_id, result, metrics)
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "message": f"Task {task_id} completed",
                }
            except Exception as e:
                return {"error": str(e)}

        @server.tool()
        def orchestration_fail_task(
            task_id: str, error: str, should_retry: bool = True
        ) -> Dict[str, Any]:
            """Mark task as failed.

            Args:
                task_id: Task UUID
                error: Error message
                should_retry: Whether to retry the task

            Returns:
                Dict with failure status
            """
            try:
                self.queue.fail_task(task_id, error, should_retry)
                status = "pending" if should_retry else "failed"
                return {
                    "task_id": task_id,
                    "status": status,
                    "message": f"Task {task_id} marked as {status}",
                }
            except Exception as e:
                return {"error": str(e)}

        @server.tool()
        def orchestration_get_task_status(task_id: str) -> Dict[str, Any]:
            """Get current task status.

            Args:
                task_id: Task UUID

            Returns:
                Dict with task details
            """
            task = self.queue.get_task_status(task_id)

            if not task:
                return {"error": f"Task {task_id} not found"}

            return {
                "id": task.id,
                "content": task.content,
                "type": task.task_type,
                "status": task.status.value,
                "priority": task.priority.value,
                "assigned_to": task.assigned_to,
                "requirements": task.requirements,
                "duration_ms": task.execution_duration_ms,
            }

        @server.tool()
        def orchestration_query_tasks(
            status: Optional[str] = None,
            agent_id: Optional[str] = None,
            task_type: Optional[str] = None,
            limit: int = 50,
        ) -> Dict[str, Any]:
            """Query tasks with filters.

            Args:
                status: Filter by status (pending, assigned, running, completed, failed)
                agent_id: Filter by assigned agent
                task_type: Filter by task type
                limit: Max results

            Returns:
                Dict with matching tasks
            """
            filters = {}
            if status:
                filters["status"] = status
            if agent_id:
                filters["agent_id"] = agent_id
            if task_type:
                filters["task_type"] = task_type

            tasks = self.queue.query_tasks(filters)[:limit]

            return {
                "count": len(tasks),
                "tasks": [
                    {
                        "id": t.id,
                        "type": t.task_type,
                        "status": t.status.value,
                        "priority": t.priority.value,
                        "assigned_to": t.assigned_to,
                    }
                    for t in tasks
                ],
            }

        # ========== Agent Management (5 tools) ==========

        @server.tool()
        def orchestration_register_agent(
            agent_id: str,
            capabilities: List[str],
            max_concurrent: int = 5,
        ) -> Dict[str, Any]:
            """Register agent with capabilities.

            Args:
                agent_id: Unique agent identifier
                capabilities: List of skill/capability names
                max_concurrent: Max concurrent tasks

            Returns:
                Dict with registration status
            """
            try:
                self.registry.register_agent(
                    agent_id,
                    capabilities,
                    {"max_concurrent_tasks": max_concurrent},
                )
                return {
                    "agent_id": agent_id,
                    "capabilities": capabilities,
                    "registered": True,
                    "message": f"Agent {agent_id} registered",
                }
            except ValueError as e:
                return {"error": str(e)}

        @server.tool()
        def orchestration_update_agent_performance(
            agent_id: str,
            success: bool,
            duration_ms: int,
            metrics: Optional[Dict[str, Any]] = None,
        ) -> Dict[str, Any]:
            """Update agent performance metrics.

            Args:
                agent_id: Agent ID
                success: Whether task succeeded
                duration_ms: Execution duration
                metrics: Additional metrics

            Returns:
                Dict with update status
            """
            try:
                self.registry.update_agent_performance(
                    agent_id, success, duration_ms, metrics
                )
                return {
                    "agent_id": agent_id,
                    "updated": True,
                    "message": f"Metrics updated for {agent_id}",
                }
            except Exception as e:
                return {"error": str(e)}

        @server.tool()
        def orchestration_get_agent_health(
            agent_id: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Get agent health status.

            Args:
                agent_id: Agent ID (None for all agents)

            Returns:
                Dict with health metrics
            """
            if agent_id:
                health = self.registry.get_agent_health(agent_id)
                return {
                    "agent_id": agent_id,
                    **health,
                }
            else:
                stats = self.registry.get_agent_statistics()
                return {
                    "total_agents": stats.total_agents,
                    "avg_success_rate": stats.avg_success_rate,
                    "skill_distribution": stats.skill_distribution,
                }

        @server.tool()
        def orchestration_find_capable_agents(
            requirements: List[str],
        ) -> Dict[str, Any]:
            """Find agents with required capabilities.

            Args:
                requirements: List of required skills

            Returns:
                Dict with list of capable agents
            """
            agents = self.registry.get_agents_by_capability(requirements)

            agent_details = [
                {
                    "id": agent_id,
                    "health": self.registry.get_agent_health(agent_id),
                }
                for agent_id in agents
            ]

            return {
                "requirements": requirements,
                "capable_agents": agent_details,
                "count": len(agents),
            }

        @server.tool()
        def orchestration_deregister_agent(agent_id: str) -> Dict[str, Any]:
            """Remove agent from registry.

            Args:
                agent_id: Agent ID

            Returns:
                Dict with deregistration status
            """
            try:
                self.registry.deregister_agent(agent_id)
                return {
                    "agent_id": agent_id,
                    "deregistered": True,
                    "message": f"Agent {agent_id} deregistered",
                }
            except Exception as e:
                return {"error": str(e)}

        # ========== Routing (2 tools) ==========

        @server.tool()
        def orchestration_route_task(
            task_id: str,
            exclude_agents: Optional[List[str]] = None,
        ) -> Dict[str, Any]:
            """Route task to best capable agent.

            Args:
                task_id: Task UUID
                exclude_agents: Agents to exclude from routing

            Returns:
                Dict with selected agent or error
            """
            task = self.queue.get_task_status(task_id)
            if not task:
                return {"error": f"Task {task_id} not found"}

            agent = self.router.route_task(task, exclude_agents)

            if agent:
                return {
                    "task_id": task_id,
                    "selected_agent": agent,
                    "routed": True,
                }
            else:
                return {
                    "task_id": task_id,
                    "error": "No capable or available agent found",
                    "routed": False,
                }

        @server.tool()
        def orchestration_get_routing_stats() -> Dict[str, Any]:
            """Get routing statistics.

            Returns:
                Dict with routing performance metrics
            """
            stats = self.router.get_routing_statistics()
            return stats

        # ========== Monitoring (3 tools) ==========

        @server.tool()
        def orchestration_get_queue_metrics() -> Dict[str, Any]:
            """Get task queue metrics.

            Returns:
                Dict with queue statistics
            """
            stats = self.queue.get_queue_statistics()

            return {
                "pending": stats.pending_count,
                "assigned": stats.assigned_count,
                "running": stats.running_count,
                "completed": stats.completed_count,
                "failed": stats.failed_count,
                "success_rate": stats.success_rate,
                "avg_execution_ms": stats.avg_execution_time_ms,
                "total": stats.total_count(),
            }

        @server.tool()
        def orchestration_get_health() -> Dict[str, Any]:
            """Get overall orchestration health.

            Returns:
                Dict with system health metrics
            """
            queue_stats = self.queue.get_queue_statistics()
            agent_stats = self.registry.get_agent_statistics()
            routing_stats = self.router.get_routing_statistics()

            return {
                "queue": {
                    "total_tasks": queue_stats.total_count(),
                    "active_tasks": queue_stats.active_count(),
                    "success_rate": queue_stats.success_rate,
                },
                "agents": {
                    "total_agents": agent_stats.total_agents,
                    "avg_success_rate": agent_stats.avg_success_rate,
                },
                "routing": {
                    "assignment_rate": routing_stats.get("assignment_rate", 0),
                },
                "status": "healthy"
                if queue_stats.success_rate > 0.8 and agent_stats.total_agents > 0
                else "degraded",
            }

        @server.tool()
        def orchestration_get_recommendations() -> Dict[str, Any]:
            """Get optimization recommendations.

            Returns:
                Dict with recommendations
            """
            recommendations = []

            # Check for overloaded agents
            if self.router.should_rebalance():
                recommendations.append(
                    "Load imbalance detected. Consider rebalancing tasks."
                )

            # Check queue depth
            queue_stats = self.queue.get_queue_statistics()
            if queue_stats.pending_count > 100:
                recommendations.append(
                    f"Large pending queue ({queue_stats.pending_count}). "
                    "Consider adding more agents."
                )

            # Check success rate
            if queue_stats.success_rate < 0.8:
                recommendations.append(
                    f"Low success rate ({queue_stats.success_rate:.1%}). "
                    "Review failed tasks."
                )

            return {
                "recommendations": recommendations,
                "count": len(recommendations),
            }
