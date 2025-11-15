"""
Knowledge graph consolidation orchestrator.

Automatically triggers and coordinates knowledge graph consolidation
following Anthropic's MCP code execution pattern:
- Uses MCP tools rather than direct function calls
- Orchestrates multi-stage consolidation
- Tracks consolidation state and history
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class ConsolidationOrchestrator:
    """Orchestrates automatic knowledge graph consolidation."""

    def __init__(self, memory_manager, consolidation_tools):
        """Initialize orchestrator.

        Args:
            memory_manager: UnifiedMemoryManager instance
            consolidation_tools: ConsolidationTools instance (MCP tools)
        """
        self.memory_manager = memory_manager
        self.tools = consolidation_tools
        self.is_running = False

    async def start_background_consolidation(self):
        """Start background consolidation worker.

        Continuously monitors for consolidation triggers and executes
        consolidation using MCP tools.
        """
        self.is_running = True
        logger.info("Starting background consolidation worker")

        while self.is_running:
            try:
                # Get projects that need consolidation
                projects = self._get_projects_needing_consolidation()

                for project in projects:
                    try:
                        await self._consolidate_project(project["id"])
                    except Exception as e:
                        logger.error(f"Error consolidating project {project['id']}: {e}")

                # Check every 5 minutes
                await asyncio.sleep(300)

            except Exception as e:
                logger.error(f"Error in consolidation loop: {e}")
                await asyncio.sleep(60)  # Wait before retry

    async def _consolidate_project(self, project_id: int):
        """Consolidate a single project using MCP tools.

        Following Anthropic's pattern:
        1. Use high-level MCP tools (not direct functions)
        2. Batch operations for efficiency
        3. Track results

        Args:
            project_id: Project to consolidate
        """
        logger.info(f"Starting consolidation for project {project_id}")

        try:
            # Call the high-level consolidation tool
            # This tool itself calls the other MCP tools
            result = self.tools.perform_full_consolidation(
                project_id=project_id,
                include_code_analysis=False  # Code analysis can be expensive
            )

            # Log consolidation result
            self._log_consolidation(project_id, result)

            if result.get("success"):
                logger.info(
                    f"Consolidation successful for project {project_id}: "
                    f"{result.get('total_entities_created', 0)} entities, "
                    f"{result.get('total_relationships_created', 0)} relationships"
                )
            else:
                logger.warning(
                    f"Consolidation had issues for project {project_id}: "
                    f"{result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(f"Error consolidating project {project_id}: {e}")

    def _get_projects_needing_consolidation(self) -> list:
        """Get projects that need consolidation based on triggers.

        Uses consolidation trigger system to determine which projects
        have recent activity requiring consolidation.

        Returns:
            List of project dicts
        """
        try:
            # Get all projects
            projects = self.memory_manager.db.query(
                "SELECT id, name FROM projects ORDER BY id"
            )

            # Filter to projects with recent episodic events
            projects_to_consolidate = []

            for project in projects:
                # Check if project has recent events
                recent_events = self.memory_manager.db.query(
                    """
                    SELECT COUNT(*) as count FROM episodic_events
                    WHERE project_id = %s AND created_at > %s
                    """,
                    (project["id"], int((datetime.now() - timedelta(hours=1)).timestamp()))
                )

                if recent_events and recent_events[0].get("count", 0) >= 3:
                    projects_to_consolidate.append(project)
                    logger.debug(f"Project {project['id']} has recent events, marking for consolidation")

            return projects_to_consolidate

        except Exception as e:
            logger.error(f"Error getting projects for consolidation: {e}")
            return []

    def _log_consolidation(self, project_id: int, result: Dict[str, Any]):
        """Log consolidation result to database.

        Args:
            project_id: Project ID
            result: Consolidation result dict
        """
        try:
            # Store consolidation log
            self.memory_manager.db.execute(
                """
                INSERT INTO consolidation_runs (
                    project_id, status, entities_created,
                    relationships_created, duration_seconds, result_json, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    project_id,
                    "success" if result.get("success") else "failed",
                    result.get("total_entities_created", 0),
                    result.get("total_relationships_created", 0),
                    result.get("duration_seconds", 0),
                    json.dumps(result),
                    int(datetime.now().timestamp())
                )
            )
        except Exception as e:
            logger.debug(f"Could not log consolidation: {e}")

    def stop_background_consolidation(self):
        """Stop background consolidation worker."""
        self.is_running = False
        logger.info("Stopping background consolidation worker")


class SessionEndConsolidationTrigger:
    """Triggers consolidation at end of session."""

    def __init__(self, orchestrator: ConsolidationOrchestrator):
        """Initialize trigger.

        Args:
            orchestrator: ConsolidationOrchestrator instance
        """
        self.orchestrator = orchestrator

    async def on_session_end(self, session_id: str, project_id: int):
        """Trigger consolidation when session ends.

        Args:
            session_id: Session ID
            project_id: Project ID
        """
        logger.info(f"Session {session_id} ended for project {project_id}, triggering consolidation")

        try:
            await self.orchestrator._consolidate_project(project_id)
        except Exception as e:
            logger.error(f"Error consolidating on session end: {e}")


def create_and_start_consolidator(memory_manager, consolidation_tools) -> ConsolidationOrchestrator:
    """Create and start consolidation orchestrator.

    Args:
        memory_manager: UnifiedMemoryManager instance
        consolidation_tools: ConsolidationTools instance

    Returns:
        ConsolidationOrchestrator instance
    """
    orchestrator = ConsolidationOrchestrator(memory_manager, consolidation_tools)

    # Start background worker in event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Event loop already running, schedule as task
            asyncio.create_task(orchestrator.start_background_consolidation())
        else:
            # No event loop, create background thread
            import threading
            thread = threading.Thread(
                target=lambda: asyncio.run(
                    orchestrator.start_background_consolidation()
                ),
                daemon=True
            )
            thread.start()
    except RuntimeError:
        # No event loop in current thread, create new one
        import threading
        thread = threading.Thread(
            target=lambda: asyncio.run(
                orchestrator.start_background_consolidation()
            ),
            daemon=True
        )
        thread.start()

    logger.info("Consolidation orchestrator started")
    return orchestrator
