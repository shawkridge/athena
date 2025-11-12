"""Helper module for memory operations using filesystem API paradigm.

This module provides simple, synchronous wrappers for memory operations.
It uses the FilesystemAPIAdapter which implements the code execution paradigm:
- Discover operations via filesystem
- Read operation code before executing
- Execute locally (in sandbox)
- Return summaries (never full data)

All operations are suitable for hooks and achieve ~99% token reduction.
"""

import os
import json
import logging
from typing import Any, Dict, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Environment variables
ATHENA_SRC_PATH = os.environ.get('ATHENA_SRC_PATH', '/home/user/.work/athena/src')
DB_PATH = os.environ.get('ATHENA_DB_PATH', '~/.athena/memory.db')


def get_filesystem_adapter():
    """Initialize and return FilesystemAPIAdapter instance.

    Uses filesystem API for progressive disclosure and local execution.

    Returns:
        FilesystemAPIAdapter instance or None on failure
    """
    try:
        # Try to import from local module first
        from .filesystem_api_adapter import FilesystemAPIAdapter

        adapter = FilesystemAPIAdapter()
        logger.info("Successfully initialized FilesystemAPIAdapter")
        return adapter

    except Exception as e:
        logger.error(f"Failed to initialize FilesystemAPIAdapter: {str(e)}")
        import traceback
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        return None


def record_episodic_event(
    event_type: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[int]:
    """Record a memory using filesystem API paradigm.

    Executes episodic layer's record_event operation locally.
    Key: Returns event ID only, not full event object.

    Args:
        event_type: Type of event (e.g., "tool_execution", "task_completion", "action", "decision")
        content: Main content/description of the event
        metadata: Optional metadata dict

    Returns:
        Event ID if successful, None otherwise
    """
    try:
        adapter = get_filesystem_adapter()
        if not adapter:
            logger.error("Could not initialize FilesystemAPIAdapter")
            return None

        if metadata is None:
            metadata = {}

        # Prepare event data
        outcome = metadata.get("outcome", "unknown")

        # Execute record_event operation in episodic layer
        result = adapter.execute_operation(
            "episodic",
            "record_event",
            {
                "event_type": event_type,
                "content": content,
                "outcome": outcome,
                "context": metadata,
                "db_path": os.path.expanduser(DB_PATH)
            }
        )

        if result.get("status") == "success":
            event_id = result.get("result", {}).get("event_id")
            logger.debug(f"Recorded event as memory: {event_id}")
            return event_id
        else:
            logger.warning(f"Failed to record episodic event: {result.get('error')}")
            return None

    except Exception as e:
        logger.error(f"Failed to record episodic event: {str(e)}")
        import traceback
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        return None


def run_consolidation(strategy: str = 'balanced', days_back: int = 7) -> Dict[str, Any]:
    """Run consolidation on recent episodic events.

    Executes consolidation operation in consolidation layer locally.
    Key: Returns summary (counts, patterns extracted), not full consolidated data.

    Args:
        strategy: Consolidation strategy ('balanced', 'speed', 'quality', 'minimal')
        days_back: How many days of events to consolidate

    Returns:
        Consolidation summary dict (counts, metrics), or error dict if failed
    """
    try:
        adapter = get_filesystem_adapter()
        if not adapter:
            logger.error("Could not initialize FilesystemAPIAdapter")
            return {"status": "error", "message": "Adapter not available"}

        # Execute consolidation operation in consolidation layer
        result = adapter.execute_operation(
            "consolidation",
            "consolidate",
            {
                "strategy": strategy,
                "days_back": days_back,
                "db_path": os.path.expanduser(DB_PATH)
            }
        )

        if result.get("status") == "success":
            logger.info(f"Consolidation complete: strategy={strategy}, days_back={days_back}")
            return result.get("result", {})
        else:
            logger.warning(f"Consolidation failed: {result.get('error')}")
            return {"status": "error", "message": result.get("error")}

    except Exception as e:
        logger.error(f"Failed to run consolidation: {str(e)}")
        import traceback
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}


def search_memories(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """Search for memories matching query.

    Executes semantic search operation locally.
    Key: Returns summary (counts, IDs, metadata), not full memory objects.

    Args:
        query: Search query
        limit: Maximum number of results to return

    Returns:
        Search summary dict with result counts and metadata, None on error
    """
    try:
        adapter = get_filesystem_adapter()
        if not adapter:
            logger.error("Could not initialize FilesystemAPIAdapter")
            return None

        # Execute recall operation in semantic layer
        result = adapter.execute_operation(
            "semantic",
            "recall",
            {
                "query": query,
                "limit": limit,
                "db_path": os.path.expanduser(DB_PATH)
            }
        )

        if result.get("status") == "success":
            logger.debug(f"Memory search complete: query='{query}'")
            return result.get("result", {})
        else:
            logger.warning(f"Memory search failed: {result.get('error')}")
            return None

    except Exception as e:
        logger.error(f"Failed to search memories: {str(e)}")
        import traceback
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        return None


def store_memory(
    content: str,
    memory_type: str = "fact",
    tags: Optional[list] = None
) -> Optional[int]:
    """Store a new memory.

    Executes remember operation in semantic layer locally.
    Key: Returns memory ID only, not full memory object.

    Args:
        content: Memory content to store
        memory_type: Type of memory (fact, context, procedure, decision, etc)
        tags: Optional tags for categorization

    Returns:
        Memory ID if successful, None otherwise
    """
    try:
        adapter = get_filesystem_adapter()
        if not adapter:
            logger.error("Could not initialize FilesystemAPIAdapter")
            return None

        # Execute remember operation in semantic layer
        result = adapter.execute_operation(
            "semantic",
            "remember",
            {
                "content": content,
                "memory_type": memory_type,
                "tags": tags or [],
                "db_path": os.path.expanduser(DB_PATH)
            }
        )

        if result.get("status") == "success":
            memory_id = result.get("result", {}).get("memory_id")
            logger.debug(f"Stored memory: {memory_id} (type={memory_type})")
            return memory_id
        else:
            logger.warning(f"Failed to store memory: {result.get('error')}")
            return None

    except Exception as e:
        logger.error(f"Failed to store memory: {str(e)}")
        import traceback
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        return None


def get_memory_health() -> Optional[Dict[str, Any]]:
    """Get memory system health summary.

    Executes health check operation across layers.
    Key: Returns health metrics summary, not full system state.

    Returns:
        Health status dict with metrics, None on error
    """
    try:
        adapter = get_filesystem_adapter()
        if not adapter:
            logger.error("Could not initialize FilesystemAPIAdapter")
            return None

        # Execute cross-layer health check
        result = adapter.execute_cross_layer_operation(
            "health_check",
            {"db_path": os.path.expanduser(DB_PATH)}
        )

        if result.get("status") == "success":
            return result.get("result", {})
        else:
            logger.warning(f"Health check failed: {result.get('error')}")
            return None

    except Exception as e:
        logger.error(f"Failed to check memory health: {str(e)}")
        import traceback
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        return None
