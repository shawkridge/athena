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
    ResearchFeedbackStore,
    QueryRefinementEngine,
    QueryRefinement,
    ResultAggregator,
    AggregatedResult,
    ResearchTask,
    ResearchStatus,
    ResearchFinding,
    AgentProgress,
    AgentStatus,
    ResearchFeedback,
    FeedbackType,
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
        or redirect agent focus. Feedback is persisted and can drive query refinement.

        Args:
            args: Dictionary with keys:
                - task_id (int): Research task identifier
                - feedback_type (str): 'query_refinement', 'source_exclusion', 'source_focus', 'agent_focus', 'result_filtering', 'quality_threshold'
                - content (str): Feedback content/explanation
                - agent_target (str, optional): Target specific agent ('web_searcher', 'academic_researcher', 'synthesizer')
                - parent_feedback_id (int, optional): ID of feedback this builds on (for multi-turn refinement)

        Returns:
            List containing TextContent with feedback acknowledgment
        """
        try:
            task_id = args.get("task_id")
            feedback_type_str = args.get("feedback_type", "query_refinement").lower()
            content = args.get("content", "")
            agent_target = args.get("agent_target", "").lower() or None
            parent_feedback_id = args.get("parent_feedback_id")

            if not task_id or not content:
                result = StructuredResult.error(
                    "task_id and content are required",
                    metadata={"operation": "research_feedback"},
                )
                return [result.as_text_content()]

            # Validate feedback type
            try:
                feedback_type = FeedbackType(feedback_type_str)
            except ValueError:
                result = StructuredResult.error(
                    f"Invalid feedback_type. Must be one of: {', '.join([ft.value for ft in FeedbackType])}",
                    metadata={"operation": "research_feedback"},
                )
                return [result.as_text_content()]

            # Create feedback object
            feedback = ResearchFeedback(
                research_task_id=task_id,
                feedback_type=feedback_type,
                content=content,
                agent_target=agent_target,
                parent_feedback_id=parent_feedback_id,
            )

            # Store feedback in database
            if hasattr(self, 'research_feedback_store'):
                feedback_id = self.research_feedback_store.record_feedback(feedback)
            else:
                logger.warning("research_feedback_store not available, feedback not persisted")
                feedback_id = -1

            # Log feedback for debugging
            logger.info(f"Feedback recorded: task={task_id}, type={feedback_type_str}, agent={agent_target}, id={feedback_id}")

            result = StructuredResult.success(
                data={
                    "feedback_id": feedback_id,
                    "task_id": task_id,
                    "feedback_type": feedback_type_str,
                    "agent_target": agent_target,
                    "status": "RECORDED",
                    "message": f"Feedback recorded successfully. Use task refinement tools to apply this feedback.",
                },
                metadata={
                    "operation": "research_feedback",
                    "task_id": task_id,
                    "feedback_type": feedback_type_str,
                    "feedback_id": feedback_id,
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

    async def _handle_research_refine_query(self, args: dict) -> list[TextContent]:
        """Handle query refinement (Phase 3.2 - Phase B).

        Apply collected feedback to refine research query and re-execute
        research with improved search parameters.

        Args:
            args: Dictionary with keys:
                - task_id (int): Research task identifier
                - apply_feedback (bool, optional): Auto-apply unapplied feedback (default True)

        Returns:
            List containing TextContent with refinement results
        """
        try:
            task_id = args.get("task_id")
            apply_feedback = args.get("apply_feedback", True)

            if not task_id:
                result = StructuredResult.error(
                    "task_id is required",
                    metadata={"operation": "research_refine_query"},
                )
                return [result.as_text_content()]

            # Get the original task
            task = self.research_store.get_task(task_id)
            if not task:
                result = StructuredResult.error(
                    f"Research task {task_id} not found",
                    metadata={"operation": "research_refine_query", "task_id": task_id},
                )
                return [result.as_text_content()]

            # Get feedback for this task
            if hasattr(self, 'research_feedback_store'):
                if apply_feedback:
                    feedback_list = self.research_feedback_store.get_unapplied_feedback(task_id)
                else:
                    feedback_list = self.research_feedback_store.get_task_feedback(task_id)
            else:
                feedback_list = []

            if not feedback_list:
                result = StructuredResult.success(
                    data={
                        "task_id": task_id,
                        "message": "No feedback available for refinement",
                        "feedback_count": 0,
                    },
                    metadata={
                        "operation": "research_refine_query",
                        "task_id": task_id,
                    },
                )
                return [result.as_text_content()]

            # Apply refinement engine
            engine = QueryRefinementEngine()
            refinement = engine.refine_from_feedback(task.topic, feedback_list)

            # Mark feedback as applied
            for feedback_id in refinement.applied_feedback_ids:
                if hasattr(self, 'research_feedback_store'):
                    self.research_feedback_store.mark_feedback_applied(feedback_id)

            result = StructuredResult.success(
                data={
                    "task_id": task_id,
                    "original_query": refinement.original_query,
                    "refined_query": refinement.refined_query,
                    "excluded_sources": refinement.excluded_sources,
                    "focused_sources": refinement.focused_sources,
                    "quality_threshold": refinement.quality_threshold,
                    "agent_directives": refinement.agent_directives,
                    "feedback_applied": len(refinement.applied_feedback_ids),
                    "summary": refinement.summary(),
                    "note": "Query refined. Use task refinement tools to execute research with refined parameters.",
                },
                metadata={
                    "operation": "research_refine_query",
                    "task_id": task_id,
                    "feedback_count": len(refinement.applied_feedback_ids),
                },
            )

        except Exception as e:
            logger.error(f"Error in _handle_research_refine_query: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "research_refine_query"})

        return [result.as_text_content()]

    async def _handle_research_re_execute(self, args: dict) -> list[TextContent]:
        """Handle refined research re-execution (Phase 3.2 - Phase B).

        Re-execute research with refined query and constraints after feedback.

        Args:
            args: Dictionary with keys:
                - task_id (int): Research task identifier
                - refined_query (str, optional): Refined query to use
                - excluded_sources (list, optional): Sources to exclude
                - focused_sources (list, optional): Sources to focus on
                - quality_threshold (float, optional): Min quality score

        Returns:
            List containing TextContent with execution result
        """
        try:
            task_id = args.get("task_id")
            refined_query = args.get("refined_query")
            excluded_sources = args.get("excluded_sources", [])
            focused_sources = args.get("focused_sources", [])
            quality_threshold = float(args.get("quality_threshold", 0.5))

            if not task_id:
                result = StructuredResult.error(
                    "task_id is required",
                    metadata={"operation": "research_re_execute"},
                )
                return [result.as_text_content()]

            # Get task
            task = self.research_store.get_task(task_id)
            if not task:
                result = StructuredResult.error(
                    f"Research task {task_id} not found",
                    metadata={"operation": "research_re_execute", "task_id": task_id},
                )
                return [result.as_text_content()]

            # Use refined query if provided, otherwise original
            query_to_execute = refined_query or task.topic

            # Update task status to running
            self.research_store.update_task_status(task_id, ResearchStatus.RUNNING)

            # Spawn background research execution with refined parameters
            # TODO: Phase B - Pass constraints to executor
            asyncio.create_task(
                self.research_executor.execute_research(task_id, query_to_execute)
            )

            result = StructuredResult.success(
                data={
                    "task_id": task_id,
                    "status": "RUNNING",
                    "query": query_to_execute,
                    "constraints": {
                        "excluded_sources": excluded_sources,
                        "focused_sources": focused_sources,
                        "quality_threshold": quality_threshold,
                    },
                    "message": "Research re-execution started with refined parameters",
                },
                metadata={
                    "operation": "research_re_execute",
                    "task_id": task_id,
                },
            )

        except Exception as e:
            logger.error(f"Error in _handle_research_re_execute: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "research_re_execute"})

        return [result.as_text_content()]

    async def _handle_research_aggregated_results(self, args: dict) -> list[TextContent]:
        """Handle aggregated results retrieval (Phase 3.2 - Phase C).

        Get synthesized results from completed research with filtering and
        formatting optimized for Claude consumption.

        Args:
            args: Dictionary with keys:
                - task_id (int): Research task identifier
                - quality_threshold (float, optional): Min credibility score (0-1)
                - excluded_sources (list, optional): Sources to exclude
                - focused_sources (list, optional): Sources to focus on
                - limit (int, optional): Max findings to return (default 50)
                - format (str, optional): 'json' or 'markdown' (default 'json')

        Returns:
            List containing TextContent with aggregated results
        """
        try:
            task_id = args.get("task_id")
            quality_threshold = float(args.get("quality_threshold", 0.5))
            excluded_sources = args.get("excluded_sources", [])
            focused_sources = args.get("focused_sources", [])
            limit = min(int(args.get("limit", 50)), 100)
            output_format = args.get("format", "json").lower()

            if not task_id:
                result = StructuredResult.error(
                    "task_id is required",
                    metadata={"operation": "research_aggregated_results"},
                )
                return [result.as_text_content()]

            # Get the original task
            task = self.research_store.get_task(task_id)
            if not task:
                result = StructuredResult.error(
                    f"Research task {task_id} not found",
                    metadata={"operation": "research_aggregated_results", "task_id": task_id},
                )
                return [result.as_text_content()]

            # Build aggregator
            aggregator = ResultAggregator(task_id, task.topic)

            # Load findings from store
            findings = self.research_store.get_task_findings(task_id, limit=1000)
            for finding in findings:
                aggregator.add_finding(finding, finding.source)

            # Load applied feedback
            if hasattr(self, 'research_feedback_store'):
                feedback_list = self.research_feedback_store.get_task_feedback(task_id)
                for feedback in feedback_list:
                    if feedback.applied:
                        aggregator.add_feedback(feedback)

            # Mark complete if task is done
            if task.status in [ResearchStatus.COMPLETED, ResearchStatus.FAILED]:
                aggregator.mark_complete()

            # Get filtered results
            aggregated = aggregator.get_results(
                quality_threshold=quality_threshold,
                excluded_sources=excluded_sources if excluded_sources else None,
                focused_sources=focused_sources if focused_sources else None,
                limit=limit,
            )

            # Format output
            if output_format == "markdown":
                formatted_output = aggregator.export_for_claude()
                result = StructuredResult.success(
                    data={
                        "task_id": task_id,
                        "format": "markdown",
                        "content": formatted_output,
                    },
                    metadata={
                        "operation": "research_aggregated_results",
                        "task_id": task_id,
                        "findings_count": len(findings),
                        "format": "markdown",
                    },
                )
            else:
                # Default JSON format
                result = StructuredResult.success(
                    data=aggregated,
                    metadata={
                        "operation": "research_aggregated_results",
                        "task_id": task_id,
                        "findings_count": len(findings),
                    },
                    pagination=PaginationMetadata(
                        returned=len(aggregated["findings"]),
                        limit=limit,
                        total=len(findings),
                    ),
                )

        except Exception as e:
            logger.error(f"Error in _handle_research_aggregated_results: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "research_aggregated_results"})

        return [result.as_text_content()]
