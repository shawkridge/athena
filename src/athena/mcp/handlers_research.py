"""Research handler methods for MCP server.

Extracted handler methods for research task orchestration and multi-agent coordination.
Manages research execution, finding storage, and agent status tracking.

This module logically groups handler methods by domain (research coordination).
Actual implementations delegate to research components (store, executor, coordinator).

Methods (5 handlers, ~350 lines):
- _handle_research_task: Create, execute, and query research tasks
- _handle_research_findings: Retrieve findings from completed research
- _handle_research_agent_status: Get individual agent execution status
- _handle_research_feedback: Submit user feedback for query refinement (Phase 3.2)
- _handle_research_config: Configure research execution parameters
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from mcp.types import TextContent

from .structured_result import StructuredResult, ResultStatus, PaginationMetadata
from ..research import (
    ResearchStore,
    ResearchTask,
    ResearchStatus,
    ResearchFinding,
    AgentProgress,
    AgentStatus,
    ResearchAgentExecutor,
    ResearchMemoryIntegrator,
)

logger = logging.getLogger(__name__)


class ResearchHandlersMixin:
    """Research handler methods (5 methods, ~350 lines).

    Extracted as part of Phase 3.1 research coordination implementation.
    Provides MCP tools for autonomous multi-agent research execution.

    Requires attributes:
    - research_store: ResearchStore instance
    - research_executor: ResearchAgentExecutor instance
    - research_memory_integrator: ResearchMemoryIntegrator instance (optional)
    - project_manager: ProjectManager instance
    """

    async def _handle_research_task(self, args: dict) -> list[TextContent]:
        """Handle research task operations.

        Supports operations:
        - create: Create a new research task
        - get_status: Get current task status
        - list_tasks: List all research tasks
        - cancel: Cancel a running task

        Args:
            args: Dictionary with keys:
                - operation (str): 'create', 'get_status', 'list_tasks', 'cancel'
                - topic (str, for create): Research topic/question
                - task_id (int, for get_status/cancel): Task identifier
                - project_id (int, optional): Project context

        Returns:
            List containing TextContent with operation result
        """
        try:
            operation = args.get("operation", "create").lower()

            if operation == "create":
                result = await self._research_create_task(args)
            elif operation == "get_status":
                result = await self._research_get_status(args)
            elif operation == "list_tasks":
                result = await self._research_list_tasks(args)
            elif operation == "cancel":
                result = await self._research_cancel_task(args)
            else:
                result = StructuredResult.error(
                    f"Unknown research operation: {operation}",
                    metadata={"operation": "research_task", "requested_op": operation},
                )

        except Exception as e:
            logger.error(f"Error in _handle_research_task: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "research_task"})

        return [result.as_text_content()]

    async def _research_create_task(self, args: dict) -> StructuredResult:
        """Create a new research task and spawn agent execution."""
        try:
            topic = args.get("topic", "")
            if not topic:
                return StructuredResult.error(
                    "Topic is required for research task creation",
                    metadata={"operation": "research_create"},
                )

            # Get project context
            project = await self.project_manager.get_or_create_project()

            # Create task in store
            task_id = self.research_store.create_task(
                topic=topic,
                project_id=project.id,
            )

            # Spawn background research execution
            asyncio.create_task(
                self.research_executor.execute_research(task_id, topic)
            )

            return StructuredResult.success(
                data={
                    "task_id": task_id,
                    "topic": topic,
                    "status": "RUNNING",
                    "project_id": project.id,
                },
                metadata={
                    "operation": "research_create",
                    "task_id": task_id,
                },
            )

        except Exception as e:
            logger.error(f"Error creating research task: {e}", exc_info=True)
            return StructuredResult.error(
                f"Failed to create research task: {str(e)}",
                metadata={"operation": "research_create"},
            )

    async def _research_get_status(self, args: dict) -> StructuredResult:
        """Get status of a research task."""
        try:
            task_id = args.get("task_id")
            if not task_id:
                return StructuredResult.error(
                    "task_id is required",
                    metadata={"operation": "research_status"},
                )

            # Get task from store
            task = self.research_store.get_task(task_id)
            if not task:
                return StructuredResult.error(
                    f"Research task {task_id} not found",
                    metadata={"operation": "research_status", "task_id": task_id},
                )

            # Get findings count
            findings = self.research_store.get_task_findings(task_id)

            # Get agent progress
            agent_progress = self.research_store.get_agent_progress(task_id)
            agent_statuses = [
                {
                    "agent_name": ap.agent_name,
                    "status": ap.status,
                    "findings_count": ap.findings_count,
                }
                for ap in agent_progress
            ]

            return StructuredResult.success(
                data={
                    "task_id": task_id,
                    "topic": task.topic,
                    "status": task.status,
                    "findings_count": len(findings),
                    "agent_statuses": agent_statuses,
                    "created_at": task.created_at,
                },
                metadata={
                    "operation": "research_status",
                    "task_id": task_id,
                    "status": task.status,
                },
            )

        except Exception as e:
            logger.error(f"Error getting research status: {e}", exc_info=True)
            return StructuredResult.error(
                f"Failed to get research status: {str(e)}",
                metadata={"operation": "research_status"},
            )

    async def _research_list_tasks(self, args: dict) -> StructuredResult:
        """List research tasks."""
        try:
            project = await self.project_manager.get_or_create_project()

            # Get tasks for project
            tasks = self.research_store.list_tasks(project_id=project.id)

            task_summaries = []
            for task in tasks:
                findings = self.research_store.get_task_findings(task.id)
                task_summaries.append({
                    "task_id": task.id,
                    "topic": task.topic,
                    "status": task.status,
                    "findings_count": len(findings),
                    "created_at": task.created_at,
                })

            return StructuredResult.success(
                data=task_summaries,
                metadata={
                    "operation": "research_list",
                    "project_id": project.id,
                    "task_count": len(tasks),
                },
                pagination=PaginationMetadata(
                    returned=len(task_summaries),
                    limit=100,
                ),
            )

        except Exception as e:
            logger.error(f"Error listing research tasks: {e}", exc_info=True)
            return StructuredResult.error(
                f"Failed to list research tasks: {str(e)}",
                metadata={"operation": "research_list"},
            )

    async def _research_cancel_task(self, args: dict) -> StructuredResult:
        """Cancel a research task."""
        try:
            task_id = args.get("task_id")
            if not task_id:
                return StructuredResult.error(
                    "task_id is required",
                    metadata={"operation": "research_cancel"},
                )

            # Update task status
            success = self.research_store.update_task_status(
                task_id,
                ResearchStatus.CANCELLED,
            )

            if not success:
                return StructuredResult.error(
                    f"Failed to cancel task {task_id}",
                    metadata={"operation": "research_cancel", "task_id": task_id},
                )

            return StructuredResult.success(
                data={
                    "task_id": task_id,
                    "status": "CANCELLED",
                },
                metadata={
                    "operation": "research_cancel",
                    "task_id": task_id,
                },
            )

        except Exception as e:
            logger.error(f"Error cancelling research task: {e}", exc_info=True)
            return StructuredResult.error(
                f"Failed to cancel research task: {str(e)}",
                metadata={"operation": "research_cancel"},
            )

    async def _handle_research_findings(self, args: dict) -> list[TextContent]:
        """Handle research findings retrieval and analysis.

        Retrieves findings from a completed research task, with optional
        filtering and aggregation.

        Args:
            args: Dictionary with keys:
                - task_id (int): Research task identifier
                - min_credibility (float, optional): Filter by credibility score
                - limit (int, optional): Max findings to return (default 50)

        Returns:
            List containing TextContent with findings data
        """
        try:
            task_id = args.get("task_id")
            if not task_id:
                result = StructuredResult.error(
                    "task_id is required",
                    metadata={"operation": "research_findings"},
                )
                return [result.as_text_content()]

            # Get findings
            findings = self.research_store.get_task_findings(task_id)

            # Apply credibility filter
            min_credibility = float(args.get("min_credibility", 0.0))
            filtered_findings = [
                f for f in findings
                if f.credibility_score >= min_credibility
            ]

            # Apply limit
            limit = min(int(args.get("limit", 50)), 100)
            limited_findings = filtered_findings[:limit]

            # Format findings
            finding_data = [
                {
                    "id": f.id,
                    "source": f.source,
                    "title": f.title,
                    "summary": f.summary,
                    "url": f.url,
                    "credibility_score": round(f.credibility_score, 2),
                    "created_at": f.created_at,
                }
                for f in limited_findings
            ]

            result = StructuredResult.success(
                data=finding_data,
                metadata={
                    "operation": "research_findings",
                    "task_id": task_id,
                    "total_findings": len(findings),
                    "returned": len(finding_data),
                    "min_credibility": min_credibility,
                },
                pagination=PaginationMetadata(
                    returned=len(finding_data),
                    limit=limit,
                    total=len(filtered_findings),
                ),
            )

        except Exception as e:
            logger.error(f"Error in _handle_research_findings: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "research_findings"})

        return [result.as_text_content()]

    async def _handle_research_agent_status(self, args: dict) -> list[TextContent]:
        """Handle agent status retrieval.

        Get execution status and metrics for individual research agents.

        Args:
            args: Dictionary with keys:
                - task_id (int): Research task identifier
                - agent_name (str, optional): Specific agent to query

        Returns:
            List containing TextContent with agent status data
        """
        try:
            task_id = args.get("task_id")
            if not task_id:
                result = StructuredResult.error(
                    "task_id is required",
                    metadata={"operation": "research_agent_status"},
                )
                return [result.as_text_content()]

            # Get agent progress
            agent_progress = self.research_store.get_agent_progress(task_id)

            # Filter by agent name if specified
            agent_name_filter = args.get("agent_name", "").lower()
            if agent_name_filter:
                agent_progress = [
                    ap for ap in agent_progress
                    if agent_name_filter in ap.agent_name.lower()
                ]

            # Format agent data
            agent_data = [
                {
                    "agent_name": ap.agent_name,
                    "status": ap.status,
                    "findings_count": ap.findings_count,
                    "started_at": ap.started_at,
                    "completed_at": ap.completed_at,
                    "error_message": ap.error_message,
                }
                for ap in agent_progress
            ]

            result = StructuredResult.success(
                data=agent_data,
                metadata={
                    "operation": "research_agent_status",
                    "task_id": task_id,
                    "agent_count": len(agent_data),
                },
                pagination=PaginationMetadata(
                    returned=len(agent_data),
                    limit=20,
                ),
            )

        except Exception as e:
            logger.error(f"Error in _handle_research_agent_status: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "research_agent_status"})

        return [result.as_text_content()]

    async def _handle_research_feedback(self, args: dict) -> list[TextContent]:
        """Handle research feedback submission (Phase 3.2).

        Submit user feedback to refine research direction, improve queries,
        or redirect agent focus.

        Args:
            args: Dictionary with keys:
                - task_id (int): Research task identifier
                - feedback_type (str): 'query_refinement', 'source_exclusion', 'agent_focus'
                - content (str): Feedback content
                - agent_name (str, optional): Target specific agent

        Returns:
            List containing TextContent with feedback acknowledgment
        """
        try:
            task_id = args.get("task_id")
            feedback_type = args.get("feedback_type", "query_refinement").lower()
            content = args.get("content", "")

            if not task_id or not content:
                result = StructuredResult.error(
                    "task_id and content are required",
                    metadata={"operation": "research_feedback"},
                )
                return [result.as_text_content()]

            # Store feedback for future analysis
            feedback_record = {
                "task_id": task_id,
                "feedback_type": feedback_type,
                "content": content,
                "agent_name": args.get("agent_name"),
                "timestamp": int(__import__("time").time()),
            }

            # TODO: Phase 3.2 - Route feedback to agents for query refinement
            # This is a placeholder for interactive refinement feature
            logger.info(f"Research feedback received: {feedback_record}")

            result = StructuredResult.success(
                data={
                    "task_id": task_id,
                    "feedback_type": feedback_type,
                    "status": "ACKNOWLEDGED",
                    "note": "Feedback recorded. Interactive refinement (Phase 3.2) coming soon.",
                },
                metadata={
                    "operation": "research_feedback",
                    "task_id": task_id,
                    "feedback_type": feedback_type,
                },
            )

        except Exception as e:
            logger.error(f"Error in _handle_research_feedback: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "research_feedback"})

        return [result.as_text_content()]

    async def _handle_research_config(self, args: dict) -> list[TextContent]:
        """Handle research configuration (execution parameters).

        Configure behavior for research tasks: timeouts, agent selection,
        quality thresholds, etc.

        Args:
            args: Dictionary with keys:
                - operation (str): 'get', 'set'
                - key (str, optional): Configuration key to get/set
                - value (Any, optional): Configuration value

        Returns:
            List containing TextContent with configuration state
        """
        try:
            operation = args.get("operation", "get").lower()

            if operation == "get":
                # Return current configuration
                config = {
                    "agent_timeout_seconds": 60,
                    "min_credibility_threshold": 0.5,
                    "max_findings_per_source": 50,
                    "enable_deduplication": True,
                    "enable_synthesis": True,
                }
                result = StructuredResult.success(
                    data=config,
                    metadata={
                        "operation": "research_config_get",
                    },
                )
            elif operation == "set":
                # TODO: Phase 3.2 - Implement persistent configuration storage
                key = args.get("key")
                value = args.get("value")
                result = StructuredResult.success(
                    data={
                        "key": key,
                        "value": value,
                        "status": "ACKNOWLEDGED",
                        "note": "Configuration updates (Phase 3.2) not yet implemented.",
                    },
                    metadata={
                        "operation": "research_config_set",
                        "key": key,
                    },
                )
            else:
                result = StructuredResult.error(
                    f"Unknown config operation: {operation}",
                    metadata={"operation": "research_config"},
                )

        except Exception as e:
            logger.error(f"Error in _handle_research_config: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "research_config"})

        return [result.as_text_content()]
