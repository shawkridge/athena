"""Helper module for direct Python memory access."""

import os
import json
import logging
from typing import Any, Dict, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def get_memory_manager():
    """Initialize and return UnifiedMemoryManager instance.

    Handles all the complexity of setting up the manager with proper
    database backends and all layers.

    Returns:
        UnifiedMemoryManager instance or None on failure
    """
    try:
        # Add athena to path
        import sys
        sys.path.insert(0, '/home/user/.work/athena/src')

        from pathlib import Path
        from athena.memory.store import MemoryStore
        from athena.projects.manager import ProjectManager
        from athena.episodic.store import EpisodicStore
        from athena.procedural.store import ProceduralStore
        from athena.prospective.store import ProspectiveStore
        from athena.graph.store import GraphStore
        from athena.meta.store import MetaMemoryStore
        from athena.consolidation.system import ConsolidationSystem
        from athena.manager import UnifiedMemoryManager

        # Initialize semantic store (provides database)
        store = MemoryStore(backend='postgres')
        db = store.db

        # Initialize project manager
        project_manager = ProjectManager(store)

        # Initialize all stores
        episodic_store = EpisodicStore(db)
        procedural_store = ProceduralStore(db)
        prospective_store = ProspectiveStore(db)
        graph_store = GraphStore(db)
        meta_store = MetaMemoryStore(db)

        # ConsolidationSystem needs the stores as arguments
        consolidation_system = ConsolidationSystem(
            db=db,
            memory_store=store,
            episodic_store=episodic_store,
            procedural_store=procedural_store,
            meta_store=meta_store
        )

        # Create unified manager
        manager = UnifiedMemoryManager(
            semantic=store,
            episodic=episodic_store,
            procedural=procedural_store,
            prospective=prospective_store,
            graph=graph_store,
            meta=meta_store,
            consolidation=consolidation_system,
            project_manager=project_manager,
            enable_advanced_rag=False  # Disable RAG to keep it simple for hooks
        )

        return manager

    except Exception as e:
        logger.error(f"Failed to initialize memory manager: {str(e)}")
        return None


def record_episodic_event(
    event_type: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[int]:
    """Record an episodic event to memory.

    Args:
        event_type: Type of event (e.g., "tool_execution", "task_completion")
        content: Main content/description of the event
        metadata: Optional metadata dict

    Returns:
        Event ID if successful, None otherwise
    """
    try:
        manager = get_memory_manager()
        if not manager:
            logger.error("Could not initialize memory manager")
            return None

        # Create the event via the episodic store directly
        if metadata is None:
            metadata = {}

        # Get or create default project for memory
        default_project = manager.project_manager.get_or_create_project_sync("default")
        project_id = default_project.id if default_project else 1

        # Use episodic store's record_event method
        from athena.episodic.models import EpisodicEvent, EventType, EventContext
        import uuid

        # Map event type string to EventType enum
        try:
            # Try to get the enum value, default to ACTION
            event_enum = EventType[event_type.upper()] if hasattr(EventType, event_type.upper()) else EventType.ACTION
        except (KeyError, AttributeError):
            event_enum = EventType.ACTION

        # Create an episodic event model with required fields
        event = EpisodicEvent(
            event_type=event_enum,
            content=content,
            context=EventContext(),
            metadata=metadata,
            project_id=project_id,
            session_id=str(uuid.uuid4())  # Generate a unique session ID for this event
        )

        result = manager.episodic.record_event(event)
        return result

    except Exception as e:
        logger.error(f"Failed to record episodic event: {str(e)}")
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
        manager = get_memory_manager()
        if not manager:
            logger.error("Could not initialize memory manager")
            return False

        # Run consolidation
        result = manager.consolidate(strategy=strategy, days_back=days_back)

        logger.info(f"Consolidation completed: {result}")
        return True

    except Exception as e:
        logger.error(f"Failed to run consolidation: {str(e)}")
        return False
