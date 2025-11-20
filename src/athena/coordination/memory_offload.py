"""
Memory Offloading for Orchestrator State

Allows orchestrator to offload its coordination state to Athena memory,
enabling lean context usage even in long sessions.

Pattern:
1. Orchestrator detects context usage is high (>80%)
2. Saves current state to episodic_events as checkpoint
3. Reloads minimal context (just IDs and status)
4. After /clear, reloads full state from memory
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from .models import OrchestrationState

logger = logging.getLogger(__name__)


class MemoryOffloadManager:
    """Manages offloading/loading of orchestrator state to/from memory."""

    def __init__(self, db, athena_manager):
        """
        Initialize offload manager.

        Args:
            db: Database connection
            athena_manager: Unified memory manager instance
        """
        self.db = db
        self.athena = athena_manager

    async def checkpoint_orchestration_state(
        self, state: OrchestrationState, reason: str = "periodic"
    ) -> bool:
        """
        Save orchestration state to memory as checkpoint.

        Args:
            state: Current orchestration state
            reason: Why checkpoint is being created

        Returns:
            True if checkpointed successfully
        """
        try:
            # Prepare compact state for memory
            checkpoint = {
                "orchestrator_id": state.orchestrator_id,
                "parent_task_id": state.parent_task_id,
                "decomposed_subtasks": state.decomposed_subtasks,
                "active_agents": state.active_agents,
                "completed_tasks": state.completed_tasks,
                "failed_tasks": state.failed_tasks,
                "blocked_tasks": state.blocked_tasks,
                "context_tokens_used": state.context_tokens_used,
                "progress_pct": state.progress_percentage(),
                "checkpoint_reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Store checkpoint in episodic memory
            # Would use athena.remember() here
            checkpoint_json = json.dumps(checkpoint)

            # Also store in database for quick retrieval
            await self.db.execute(
                """
                INSERT INTO episodic_events
                (project_id, event_type, content, timestamp, importance_score,
                 consolidation_status)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                1,  # project_id (default)
                "orchestration_checkpoint",
                checkpoint_json,
                int(datetime.now(timezone.utc).timestamp() * 1000),
                0.95,  # High importance
                "unconsolidated",
            )

            logger.info(
                f"Checkpointed orchestration state: {state.progress_percentage():.0f}% complete, "
                f"reason={reason}"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to checkpoint state: {e}")
            return False

    async def restore_orchestration_state(
        self, parent_task_id: str
    ) -> Optional[OrchestrationState]:
        """
        Restore orchestration state from memory.

        Called after /clear to resume orchestration.

        Args:
            parent_task_id: ID of parent task being orchestrated

        Returns:
            Restored OrchestrationState or None if not found
        """
        try:
            # Query for most recent checkpoint
            row = await self.db.fetch_one(
                """
                SELECT content FROM episodic_events
                WHERE event_type = %s
                AND content LIKE %s
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                "orchestration_checkpoint",
                f'%"{parent_task_id}"%',
            )

            if not row:
                logger.warning(f"No checkpoint found for task {parent_task_id}")
                return None

            # Parse checkpoint JSON
            checkpoint = json.loads(row["content"])

            # Reconstruct state
            state = OrchestrationState(
                orchestrator_id=checkpoint["orchestrator_id"],
                parent_task_id=checkpoint["parent_task_id"],
                decomposed_subtasks=checkpoint["decomposed_subtasks"],
                active_agents=checkpoint["active_agents"],
                completed_tasks=checkpoint["completed_tasks"],
                failed_tasks=checkpoint["failed_tasks"],
                blocked_tasks=checkpoint["blocked_tasks"],
                context_tokens_used=checkpoint["context_tokens_used"],
            )

            logger.info(
                f"Restored orchestration state: {state.progress_percentage():.0f}% complete, "
                f"{len(state.completed_tasks)} tasks done"
            )

            return state

        except Exception as e:
            logger.error(f"Failed to restore state: {e}")
            return None

    async def get_minimal_context(
        self, state: OrchestrationState
    ) -> Dict[str, Any]:
        """
        Get minimal context for orchestrator (for lean context usage).

        Returns only essential info: task IDs, status, agent IDs.
        Full details queried on-demand from database.

        Args:
            state: Current orchestration state

        Returns:
            Minimal context dict
        """
        return {
            "orchestrator_id": state.orchestrator_id,
            "parent_task_id": state.parent_task_id,
            "stats": {
                "total_subtasks": len(state.decomposed_subtasks),
                "completed": len(state.completed_tasks),
                "failed": len(state.failed_tasks),
                "in_progress": len(state.active_agents),
                "progress_pct": state.progress_percentage(),
            },
            "active_agents": state.active_agents[:3],  # Just IDs of active agents
            "last_checkpoint": state.last_checkpoint.isoformat()
            if state.last_checkpoint
            else None,
        }

    async def estimate_context_tokens(self, state: OrchestrationState) -> int:
        """
        Estimate context tokens used by orchestration state.

        Rough estimation based on number of items and complexity.

        Args:
            state: Current state

        Returns:
            Estimated token count
        """
        # Rough estimation:
        # - Base orchestrator context: 10K tokens
        # - Per agent: 200 tokens
        # - Per task: 100 tokens
        # - Per finding/result: 500 tokens

        tokens = 10000  # Base

        tokens += len(state.active_agents) * 200
        tokens += len(state.decomposed_subtasks) * 100
        tokens += len(state.completed_tasks) * 150  # Include results

        return tokens

    def should_offload_context(self, state: OrchestrationState) -> bool:
        """
        Check if orchestrator should offload context (>80% full).

        Args:
            state: Current state

        Returns:
            True if should offload
        """
        return state.context_tokens_used > (state.context_tokens_limit * 0.8)

    async def offload_and_resume(
        self, state: OrchestrationState, athena_manager
    ) -> bool:
        """
        Offload context and resume lean operation.

        Called when context is too full. Orchestrator saves state,
        clears local context, reloads minimal state, continues.

        Args:
            state: Current state
            athena_manager: Memory manager for storing state

        Returns:
            True if successful
        """
        logger.info("Context 80% full; offloading to memory...")

        try:
            # 1. Checkpoint full state to memory
            if not await self.checkpoint_orchestration_state(
                state, reason="context_offload"
            ):
                logger.error("Failed to checkpoint before offload")
                return False

            # 2. Update state to reflect minimal context
            # In real implementation, would clear local copies here
            state.context_tokens_used = 0
            state.last_checkpoint = datetime.now(timezone.utc)

            # 3. Log for user
            logger.info(
                "Context offloaded to memory. You can now run /clear if needed. "
                "Orchestration state will be restored automatically."
            )

            return True

        except Exception as e:
            logger.error(f"Error during context offload: {e}")
            return False


class OrchestrationContextManager:
    """Context manager for lean orchestration in long sessions."""

    def __init__(self, orchestrator_id: str, db, athena_manager):
        """Initialize context manager."""
        self.orchestrator_id = orchestrator_id
        self.db = db
        self.athena = athena_manager
        self.offload_mgr = MemoryOffloadManager(db, athena_manager)

    async def get_context_budget_remaining(
        self, current_tokens: int, limit: int = 200000
    ) -> int:
        """Get remaining context tokens for orchestration."""
        return max(0, limit - current_tokens)

    async def warn_if_context_full(
        self, current_tokens: int, limit: int = 200000, threshold: float = 0.7
    ) -> Optional[str]:
        """
        Return warning message if context is getting full.

        Args:
            current_tokens: Current token usage
            limit: Context window limit
            threshold: Threshold percentage (0-1) for warning

        Returns:
            Warning message or None if under threshold
        """
        usage_pct = current_tokens / limit

        if usage_pct > threshold:
            remaining = int(limit - current_tokens)
            pct_str = f"{usage_pct * 100:.0f}%"
            return (
                f"⚠️  Context {pct_str} full ({remaining} tokens remaining). "
                f"Consider running `/clear` or reduce task complexity."
            )

        return None

    async def auto_offload_if_needed(
        self, state: OrchestrationState
    ) -> bool:
        """
        Automatically offload context if threshold exceeded.

        Args:
            state: Current orchestration state

        Returns:
            True if offload was performed
        """
        if self.offload_mgr.should_offload_context(state):
            return await self.offload_mgr.offload_and_resume(state, self.athena)

        return False
