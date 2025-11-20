"""Athena Memory System - Public API

This module provides the primary entry point for using Athena.
All memory operations are available through clean direct imports.

Simple usage:
    from athena import remember, recall, initialize_athena

    # Initialize once at startup (or first use)
    await initialize_athena()

    # Then use operations directly
    event_id = await remember("User asked about timeline", tags=["meeting"])
    results = await recall("timeline", limit=5)

All operations are direct Python async functions with zero protocol overhead.
Perfect for AI agents, scripts, and applications that need to remember things.
"""

# Re-export all operations for convenient importing
from athena.episodic.operations import (
    get_by_session as episodic_get_by_session,
    get_by_tags as episodic_get_by_tags,
    get_by_time_range as episodic_get_by_time_range,
    get_statistics as episodic_get_statistics,
    recall,
    recall_recent,
    remember,
)
from athena.semantic.operations import search, store
from athena.procedural.operations import (
    extract_procedure,
    get_procedures_by_tags,
    get_procedure,
    get_statistics as procedural_get_statistics,
    list_procedures,
    search_procedures,
    update_procedure_success,
)
from athena.prospective.operations import (
    create_task,
    get_active_tasks,
    get_overdue_tasks,
    get_statistics as prospective_get_statistics,
    get_task,
    list_tasks,
    update_task_status,
)
from athena.graph.operations import (
    add_entity,
    add_relationship,
    find_entity,
    find_related,
    get_communities,
    get_statistics as graph_get_statistics,
    search_entities,
    update_entity_importance,
)
from athena.meta.operations import (
    get_cognitive_load,
    get_expertise,
    get_memory_quality,
    get_statistics as meta_get_statistics,
    rate_memory,
    update_cognitive_load,
)
from athena.consolidation.operations import (
    consolidate,
    extract_patterns,
    extract_procedures,
    get_consolidation_history,
    get_consolidation_metrics,
    get_statistics as consolidation_get_statistics,
)
from athena.planning.operations import (
    create_plan,
    estimate_effort,
    get_plan,
    get_statistics as planning_get_statistics,
    list_plans,
    update_plan_status,
    validate_plan,
)

__all__ = [
    # Initialization
    "initialize_athena",
    # Episodic operations
    "remember",
    "recall",
    "recall_recent",
    "episodic_get_by_session",
    "episodic_get_by_tags",
    "episodic_get_by_time_range",
    "episodic_get_statistics",
    # Semantic operations
    "store",
    "search",
    # Procedural operations
    "extract_procedure",
    "list_procedures",
    "get_procedure",
    "search_procedures",
    "get_procedures_by_tags",
    "update_procedure_success",
    "procedural_get_statistics",
    # Prospective operations
    "create_task",
    "list_tasks",
    "get_task",
    "update_task_status",
    "get_active_tasks",
    "get_overdue_tasks",
    "prospective_get_statistics",
    # Graph operations
    "add_entity",
    "add_relationship",
    "find_entity",
    "search_entities",
    "find_related",
    "get_communities",
    "update_entity_importance",
    "graph_get_statistics",
    # Meta operations
    "rate_memory",
    "get_expertise",
    "get_memory_quality",
    "get_cognitive_load",
    "update_cognitive_load",
    "meta_get_statistics",
    # Consolidation operations
    "consolidate",
    "extract_patterns",
    "extract_procedures",
    "get_consolidation_history",
    "get_consolidation_metrics",
    "consolidation_get_statistics",
    # Planning operations
    "create_plan",
    "validate_plan",
    "get_plan",
    "list_plans",
    "estimate_effort",
    "update_plan_status",
    "planning_get_statistics",
]


"""Quick reference guide for using Athena operations.

### Store & Retrieve Events
    from athena import remember, recall
    event_id = await remember("User did something", tags=["work"])
    memories = await recall("work activities", limit=10)

### Store & Search Facts
    from athena import store, search
    fact_id = await store("Python is dynamically typed", topics=["programming"])
    facts = await search("programming", limit=5)

### Extract & Track Procedures
    from athena import extract_procedure, list_procedures
    proc_id = await extract_procedure("code review", description="...", steps=[...])
    procedures = await list_procedures(limit=10)

### Create & Manage Tasks
    from athena import create_task, list_tasks, get_active_tasks
    task_id = await create_task("Implement feature X", priority=8)
    active = await get_active_tasks(limit=5)

### Build Knowledge Graph
    from athena import add_entity, add_relationship, find_related
    entity_id = await add_entity("Python", entity_type="language")
    rel_id = await add_relationship(entity_id, other_id, "is_similar_to")
    related = await find_related(entity_id, limit=10)

### Track Quality & Expertise
    from athena import rate_memory, get_expertise
    await rate_memory(memory_id, quality=0.9, confidence=0.95)
    expertise = await get_expertise(topic="coding")

### Extract Patterns & Consolidate
    from athena import consolidate, extract_patterns
    result = await consolidate(strategy="balanced")
    patterns = await extract_patterns(memory_limit=100)

### Plan & Decompose Tasks
    from athena import create_plan, validate_plan
    plan = await create_plan("Build feature", depth=3)
    validation = await validate_plan(plan["id"])

All operations are direct async functions—zero protocol overhead, no server process.
Just import and call. See src/athena/[layer]/operations.py for full documentation.
"""

# Global initialization flag
_initialized = False


async def initialize_athena() -> bool:
    """Initialize all Athena layers (safe to call multiple times).

    This initializes the database connection and all memory layers.
    Safe to call multiple times - idempotent.

    Returns:
        True if initialization was successful, False otherwise.

    Usage:
        await initialize_athena()
        event_id = await remember("content", tags=["tag"])
    """
    global _initialized

    if _initialized:
        # Even if initialized, ensure TodoWritePlanStore is set up
        from athena.integration.database_sync import get_store, initialize as init_todowrite_store
        from athena.core.database import Database

        try:
            get_store()  # Check if store exists
        except RuntimeError:
            # Store not initialized, re-initialize it
            db = Database()
            await db.initialize()
            init_todowrite_store(db)
        return True

    try:
        # Import and initialize all layer stores
        from athena.core.database import Database
        from athena.episodic.store import EpisodicStore
        from athena.semantic.store import SemanticStore
        from athena.procedural.store import ProceduralStore
        from athena.prospective.store import ProspectiveStore
        from athena.graph.store import GraphStore
        from athena.meta.store import MetaMemoryStore
        from athena.consolidation.system import ConsolidationSystem

        # Import each layer's operations module for initialization
        from athena.episodic import operations as episodic_ops
        from athena.semantic import operations as semantic_ops
        from athena.procedural import operations as procedural_ops
        from athena.prospective import operations as prospective_ops
        from athena.graph import operations as graph_ops
        from athena.meta import operations as meta_ops
        from athena.consolidation import operations as consolidation_ops
        from athena.planning import operations as planning_ops

        # Create database instance and initialize schema
        db = Database()
        await db.initialize()

        # Create stores (no .initialize() call needed - schema created above)
        from athena.planning.store import PlanningStore
        from athena.integration.database_sync import initialize as init_todowrite_store

        episodic_store = EpisodicStore(db)
        semantic_store = SemanticStore(db)
        procedural_store = ProceduralStore(db)
        prospective_store = ProspectiveStore(db)
        graph_store = GraphStore(db)
        meta_store = MetaMemoryStore(db)
        planning_store = PlanningStore(db)

        # Initialize TodoWrite integration
        init_todowrite_store(db)

        # Initialize operations modules with their stores
        episodic_ops.initialize(db, episodic_store)
        semantic_ops.initialize(db, semantic_store)
        procedural_ops.initialize(db, procedural_store)
        prospective_ops.initialize(db, prospective_store)
        graph_ops.initialize(db, graph_store)
        meta_ops.initialize(db, meta_store)

        # ConsolidationSystem requires multiple stores
        consolidation_system = ConsolidationSystem(
            db=db,
            memory_store=semantic_store,
            episodic_store=episodic_store,
            procedural_store=procedural_store,
            meta_store=meta_store,
        )
        consolidation_ops.initialize(db, consolidation_system)
        planning_ops.initialize(db, planning_store)

        _initialized = True
        return True

    except Exception as e:
        print(f"Error initializing Athena: {e}")
        import traceback

        traceback.print_exc()
        return False
