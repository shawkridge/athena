"""Phase 3a handlers: Task Dependencies + Metadata management.

Exposes Phase 3a capabilities through MCP for Claude Code.
Part of the Athena memory system - prospective layer.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from mcp.types import TextContent

from .structured_result import StructuredResult, ResultStatus, create_paginated_result
from ..prospective.dependencies import DependencyStore
from ..prospective.metadata import MetadataStore

logger = logging.getLogger(__name__)


class Phase3aHandlersMixin:
    """Phase 3a handler methods for Task Dependencies + Metadata.

    Exposed through MCP server to Claude Code.
    Provides task dependency management and metadata enrichment.

    Methods:
    - _handle_create_task_dependency: Create task dependency
    - _handle_list_task_dependencies: List dependencies
    - _handle_check_task_blocked: Check if task is blocked
    - _handle_get_unblocked_tasks: Get ready-to-work tasks
    - _handle_set_task_metadata: Set effort, complexity, tags
    - _handle_record_task_effort: Record actual effort spent
    - _handle_get_task_metadata: Get full task metadata
    - _handle_get_project_analytics: Get project-wide analytics
    - _handle_mark_task_complete: Mark complete with Phase 3a integration
    """

    async def _handle_create_task_dependency(self, args: dict) -> list[TextContent]:
        """Create a task dependency (A blocks B).

        Args:
            from_task_id: Task that must complete first
            to_task_id: Task that is blocked
            dependency_type: Type of dependency (default: 'blocks')

        Returns:
            Result indicating success/failure
        """
        try:
            project = self.project_manager.get_or_create_project()
            from_task_id = args.get("from_task_id")
            to_task_id = args.get("to_task_id")
            dependency_type = args.get("dependency_type", "blocks")

            if not from_task_id or not to_task_id:
                return StructuredResult(
                    status=ResultStatus.ERROR,
                    data={"error": "from_task_id and to_task_id required"},
                ).to_mcp()

            dep_store = DependencyStore(self.db)
            dep_id = dep_store.create_dependency(
                project.id, from_task_id, to_task_id, dependency_type
            )

            if dep_id:
                return StructuredResult(
                    status=ResultStatus.SUCCESS,
                    data={
                        "dependency_id": dep_id,
                        "from_task_id": from_task_id,
                        "to_task_id": to_task_id,
                        "dependency_type": dependency_type,
                        "message": f"Task {from_task_id} blocks Task {to_task_id}",
                    },
                ).to_mcp()
            else:
                return StructuredResult(
                    status=ResultStatus.WARNING,
                    data={"message": "Dependency already exists or failed to create"},
                ).to_mcp()

        except Exception as e:
            logger.error(f"Error creating dependency: {e}")
            return StructuredResult(
                status=ResultStatus.ERROR,
                data={"error": str(e)},
            ).to_mcp()

    async def _handle_check_task_blocked(self, args: dict) -> list[TextContent]:
        """Check if a task is blocked by incomplete dependencies.

        Args:
            task_id: Task ID to check

        Returns:
            Blocking status and list of blocking task IDs
        """
        try:
            project = self.project_manager.get_or_create_project()
            task_id = args.get("task_id")

            if not task_id:
                return StructuredResult(
                    status=ResultStatus.ERROR,
                    data={"error": "task_id required"},
                ).to_mcp()

            dep_store = DependencyStore(self.db)
            is_blocked, blocking_ids = dep_store.is_task_blocked(project.id, task_id)

            data = {
                "task_id": task_id,
                "is_blocked": is_blocked,
                "blocking_task_ids": blocking_ids,
            }

            if is_blocked:
                blocking_tasks = dep_store.get_blocking_tasks(project.id, task_id)
                data["blocking_tasks"] = blocking_tasks or []

            return StructuredResult(
                status=ResultStatus.SUCCESS,
                data=data,
            ).to_mcp()

        except Exception as e:
            logger.error(f"Error checking task blocked: {e}")
            return StructuredResult(
                status=ResultStatus.ERROR,
                data={"error": str(e)},
            ).to_mcp()

    async def _handle_get_unblocked_tasks(self, args: dict) -> list[TextContent]:
        """Get list of unblocked tasks (ready to work on).

        Args:
            statuses: Filter by status (optional, default: ['pending', 'in_progress'])
            limit: Max tasks to return (default: 10)

        Returns:
            List of unblocked tasks
        """
        try:
            project = self.project_manager.get_or_create_project()
            statuses = args.get("statuses", ["pending", "in_progress"])
            limit = args.get("limit", 10)

            dep_store = DependencyStore(self.db)
            unblocked = dep_store.get_unblocked_tasks(project.id, statuses, limit)

            return StructuredResult(
                status=ResultStatus.SUCCESS,
                data={
                    "unblocked_tasks": unblocked or [],
                    "count": len(unblocked or []),
                },
            ).to_mcp()

        except Exception as e:
            logger.error(f"Error getting unblocked tasks: {e}")
            return StructuredResult(
                status=ResultStatus.ERROR,
                data={"error": str(e)},
            ).to_mcp()

    async def _handle_set_task_metadata(self, args: dict) -> list[TextContent]:
        """Set task metadata (effort estimate, complexity, priority, tags).

        Args:
            task_id: Task ID
            effort_estimate: Estimated minutes (optional)
            complexity_score: 1-10 complexity (optional)
            priority_score: 1-10 priority (optional)
            tags: List of tags (optional)

        Returns:
            Updated metadata
        """
        try:
            project = self.project_manager.get_or_create_project()
            task_id = args.get("task_id")

            if not task_id:
                return StructuredResult(
                    status=ResultStatus.ERROR,
                    data={"error": "task_id required"},
                ).to_mcp()

            meta_store = MetadataStore(self.db)
            success = meta_store.set_metadata(
                project.id,
                task_id,
                effort_estimate=args.get("effort_estimate"),
                complexity_score=args.get("complexity_score"),
                priority_score=args.get("priority_score"),
                tags=args.get("tags"),
            )

            if success:
                metadata = meta_store.get_task_metadata(project.id, task_id)
                return StructuredResult(
                    status=ResultStatus.SUCCESS,
                    data=metadata,
                ).to_mcp()
            else:
                return StructuredResult(
                    status=ResultStatus.ERROR,
                    data={"error": "Failed to set metadata"},
                ).to_mcp()

        except Exception as e:
            logger.error(f"Error setting metadata: {e}")
            return StructuredResult(
                status=ResultStatus.ERROR,
                data={"error": str(e)},
            ).to_mcp()

    async def _handle_record_task_effort(self, args: dict) -> list[TextContent]:
        """Record actual effort spent on a task.

        Args:
            task_id: Task ID
            actual_minutes: Actual time spent in minutes

        Returns:
            Recorded effort and accuracy info
        """
        try:
            project = self.project_manager.get_or_create_project()
            task_id = args.get("task_id")
            actual_minutes = args.get("actual_minutes")

            if not task_id or actual_minutes is None:
                return StructuredResult(
                    status=ResultStatus.ERROR,
                    data={"error": "task_id and actual_minutes required"},
                ).to_mcp()

            meta_store = MetadataStore(self.db)
            success = meta_store.record_actual_effort(project.id, task_id, actual_minutes)

            if success:
                metadata = meta_store.get_task_metadata(project.id, task_id)
                return StructuredResult(
                    status=ResultStatus.SUCCESS,
                    data=metadata,
                ).to_mcp()
            else:
                return StructuredResult(
                    status=ResultStatus.ERROR,
                    data={"error": "Failed to record effort"},
                ).to_mcp()

        except Exception as e:
            logger.error(f"Error recording effort: {e}")
            return StructuredResult(
                status=ResultStatus.ERROR,
                data={"error": str(e)},
            ).to_mcp()

    async def _handle_get_task_metadata(self, args: dict) -> list[TextContent]:
        """Get all metadata for a task.

        Args:
            task_id: Task ID

        Returns:
            Full task metadata including effort, complexity, accuracy
        """
        try:
            project = self.project_manager.get_or_create_project()
            task_id = args.get("task_id")

            if not task_id:
                return StructuredResult(
                    status=ResultStatus.ERROR,
                    data={"error": "task_id required"},
                ).to_mcp()

            meta_store = MetadataStore(self.db)
            metadata = meta_store.get_task_metadata(project.id, task_id)

            if metadata:
                return StructuredResult(
                    status=ResultStatus.SUCCESS,
                    data=metadata,
                ).to_mcp()
            else:
                return StructuredResult(
                    status=ResultStatus.WARNING,
                    data={"message": "Task not found or no metadata"},
                ).to_mcp()

        except Exception as e:
            logger.error(f"Error getting metadata: {e}")
            return StructuredResult(
                status=ResultStatus.ERROR,
                data={"error": str(e)},
            ).to_mcp()

    async def _handle_get_project_analytics(self, args: dict) -> list[TextContent]:
        """Get project-wide analytics (effort, complexity, accuracy).

        Args:
            None (uses current project)

        Returns:
            Project analytics including aggregate data
        """
        try:
            project = self.project_manager.get_or_create_project()

            meta_store = MetadataStore(self.db)
            analytics = meta_store.get_project_analytics(project.id)

            return StructuredResult(
                status=ResultStatus.SUCCESS,
                data=analytics,
            ).to_mcp()

        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            return StructuredResult(
                status=ResultStatus.ERROR,
                data={"error": str(e)},
            ).to_mcp()

    async def _handle_mark_task_complete_with_dependencies(self, args: dict) -> list[TextContent]:
        """Mark task complete with Phase 3a integration.

        Automatically:
        - Unblocks dependent tasks
        - Records completion timestamp
        - Updates metadata

        Args:
            task_id: Task ID to mark complete

        Returns:
            Updated task info with dependency/metadata details
        """
        try:
            project = self.project_manager.get_or_create_project()
            task_id = args.get("task_id")

            if not task_id:
                return StructuredResult(
                    status=ResultStatus.ERROR,
                    data={"error": "task_id required"},
                ).to_mcp()

            # Mark task complete
            result = self.prospective_store.update_task_status(
                task_id, "completed"
            )

            if result:
                # Record completion timestamp
                meta_store = MetadataStore(self.db)
                meta_store.set_completed_timestamp(project.id, task_id)

                # Unblock dependent tasks
                dep_store = DependencyStore(self.db)
                unblock_result = dep_store.get_blocked_tasks(project.id, task_id)
                newly_unblocked = []

                if unblock_result:
                    for blocked_task_id in unblock_result:
                        is_blocked, _ = dep_store.is_task_blocked(project.id, blocked_task_id)
                        if not is_blocked:
                            newly_unblocked.append(blocked_task_id)

                # Get full task context
                task = self.prospective_store.get_task(task_id)
                metadata = meta_store.get_task_metadata(project.id, task_id)

                return StructuredResult(
                    status=ResultStatus.SUCCESS,
                    data={
                        "task_id": task_id,
                        "status": "completed",
                        "newly_unblocked": newly_unblocked,
                        "completed_at": metadata.get("completed_at") if metadata else None,
                        "metadata": metadata,
                    },
                ).to_mcp()
            else:
                return StructuredResult(
                    status=ResultStatus.ERROR,
                    data={"error": "Failed to mark task complete"},
                ).to_mcp()

        except Exception as e:
            logger.error(f"Error marking task complete: {e}")
            return StructuredResult(
                status=ResultStatus.ERROR,
                data={"error": str(e)},
            ).to_mcp()
