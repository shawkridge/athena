"""Athena Memory System - Public API

This module provides the primary entry point for using Athena.
All memory operations are available through clean direct imports.

Simple usage:
    from athena.episodic.operations import remember, recall
    from athena.semantic.operations import store, search

    event_id = await remember("User asked about timeline", tags=["meeting"])
    results = await recall("timeline", limit=5)

All operations are direct Python async functions with zero protocol overhead.
Perfect for AI agents, scripts, and applications that need to remember things.
"""

# Re-export all operations for convenient importing
from .episodic.operations import (
    get_by_session as episodic_get_by_session,
    get_by_tags as episodic_get_by_tags,
    get_by_time_range as episodic_get_by_time_range,
    get_statistics as episodic_get_statistics,
    recall,
    recall_recent,
    remember,
)
from .semantic.operations import search, store
from .procedural.operations import (
    extract_procedure,
    get_procedures_by_tags,
    get_procedure,
    get_statistics as procedural_get_statistics,
    list_procedures,
    search_procedures,
    update_procedure_success,
)
from .prospective.operations import (
    create_task,
    get_active_tasks,
    get_overdue_tasks,
    get_statistics as prospective_get_statistics,
    get_task,
    list_tasks,
    update_task_status,
)
from .graph.operations import (
    add_entity,
    add_relationship,
    find_entity,
    find_related,
    get_communities,
    get_statistics as graph_get_statistics,
    search_entities,
    update_entity_importance,
)
from .meta.operations import (
    get_cognitive_load,
    get_expertise,
    get_memory_quality,
    get_statistics as meta_get_statistics,
    rate_memory,
    update_cognitive_load,
)
from .consolidation.operations import (
    consolidate,
    extract_patterns,
    extract_procedures,
    get_consolidation_history,
    get_consolidation_metrics,
    get_statistics as consolidation_get_statistics,
)
from .planning.operations import (
    create_plan,
    estimate_effort,
    get_plan,
    get_statistics as planning_get_statistics,
    list_plans,
    update_plan_status,
    validate_plan,
)

__all__ = [
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


# Quick reference guide
"""
## Quick Reference

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

All operations work directly—no protocol overhead, no server process needed.
Just import and call.
"""
