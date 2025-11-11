"""Helper module for direct Python memory access via MemoryStore.

This module provides simple, synchronous wrappers for memory operations.
It uses the MemoryStore synchronous API which is suitable for hooks.
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


def get_memory_store():
    """Initialize and return MemoryStore instance.

    Uses the synchronous API which is suitable for hooks.

    Returns:
        MemoryStore instance or None on failure
    """
    try:
        # Add athena to path
        import sys
        if ATHENA_SRC_PATH not in sys.path:
            sys.path.insert(0, ATHENA_SRC_PATH)

        from athena.memory.store import MemoryStore

        # Initialize memory store with PostgreSQL backend
        store = MemoryStore()
        logger.info("Successfully initialized memory store")
        return store

    except Exception as e:
        logger.error(f"Failed to initialize memory store: {str(e)}")
        import traceback
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        return None


def record_episodic_event(
    event_type: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[int]:
    """Record a memory using the synchronous API.

    Args:
        event_type: Type of event (e.g., "tool_execution", "task_completion")
        content: Main content/description of the event
        metadata: Optional metadata dict

    Returns:
        Memory ID if successful, None otherwise
    """
    try:
        store = get_memory_store()
        if not store:
            logger.error("Could not initialize memory store")
            return None

        if metadata is None:
            metadata = {}

        # Store the memory using the synchronous API
        # Use default project (ID = 1)
        from athena.core.models import MemoryType

        # Map event type to a MemoryType
        memory_type = MemoryType.FACT  # Default to FACT for hook events

        # Prepare content with event type metadata
        full_content = f"[{event_type}] {content}"

        # Store the memory
        memory_id = store.remember_sync(
            content=full_content,
            memory_type=memory_type,
            project_id=1,
            tags=[event_type, "hook"]
        )

        if memory_id:
            logger.debug(f"Recorded event as memory: {memory_id}")

        return memory_id

    except Exception as e:
        logger.error(f"Failed to record episodic event: {str(e)}")
        import traceback
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        return None


def run_consolidation(strategy: str = 'balanced', days_back: int = 7) -> bool:
    """Run consolidation on recent episodic events.

    Args:
        strategy: Consolidation strategy ('balanced', 'speed', 'quality')
        days_back: How many days of events to consolidate

    Returns:
        True if successful, False otherwise
    """
    try:
        store = get_memory_store()
        if not store:
            logger.error("Could not initialize memory store")
            return False

        # Consolidation is not yet exposed via the simple API
        # This is a placeholder for future integration
        logger.info(f"Consolidation requested: strategy={strategy}, days_back={days_back}")
        logger.info("Note: Consolidation via hooks is queued for Phase 7")
        return True

    except Exception as e:
        logger.error(f"Failed to run consolidation: {str(e)}")
        import traceback
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        return False
