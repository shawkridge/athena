"""Athena Memory System - 8-Layer neuroscience-inspired memory for AI agents

Direct Python API for all memory operations. No MCP protocol, no server process needed.

Quick start:
    from athena import remember, recall, store, search
    event_id = await remember("content", tags=["tag"])
    results = await recall("query", limit=10)

All 8 memory layers available through clean direct imports:
- Episodic: Events with timestamps (remember, recall)
- Semantic: Facts and knowledge (store, search)
- Procedural: Reusable workflows (extract_procedure, list_procedures)
- Prospective: Tasks and goals (create_task, list_tasks)
- Knowledge Graph: Entities and relationships (add_entity, find_related)
- Meta-Memory: Quality and expertise (rate_memory, get_expertise)
- Consolidation: Pattern extraction (consolidate, extract_patterns)
- Planning: Task decomposition (create_plan, validate_plan)
"""

__version__ = "1.0.0"

# Export public API
from .api import (
    # Initialization
    initialize_athena,
    # Episodic operations
    remember,
    recall,
    recall_recent,
    episodic_get_by_session,
    episodic_get_by_tags,
    episodic_get_by_time_range,
    episodic_get_statistics,
    # Semantic operations
    store,
    search,
    # Procedural operations
    extract_procedure,
    list_procedures,
    get_procedure,
    search_procedures,
    get_procedures_by_tags,
    update_procedure_success,
    procedural_get_statistics,
    # Prospective operations
    create_task,
    list_tasks,
    get_task,
    update_task_status,
    get_active_tasks,
    get_overdue_tasks,
    prospective_get_statistics,
    # Graph operations
    add_entity,
    add_relationship,
    find_entity,
    search_entities,
    find_related,
    get_communities,
    update_entity_importance,
    graph_get_statistics,
    # Meta operations
    rate_memory,
    get_expertise,
    get_memory_quality,
    get_cognitive_load,
    update_cognitive_load,
    meta_get_statistics,
    # Consolidation operations
    consolidate,
    extract_patterns,
    extract_procedures,
    get_consolidation_history,
    get_consolidation_metrics,
    consolidation_get_statistics,
    # Planning operations
    create_plan,
    validate_plan,
    get_plan,
    list_plans,
    estimate_effort,
    update_plan_status,
    planning_get_statistics,
)

__all__ = [
    # Initialization
    "initialize_athena",
    # Operations
    "remember",
    "recall",
    "recall_recent",
    "episodic_get_by_session",
    "episodic_get_by_tags",
    "episodic_get_by_time_range",
    "episodic_get_statistics",
    "store",
    "search",
    "extract_procedure",
    "list_procedures",
    "get_procedure",
    "search_procedures",
    "get_procedures_by_tags",
    "update_procedure_success",
    "procedural_get_statistics",
    "create_task",
    "list_tasks",
    "get_task",
    "update_task_status",
    "get_active_tasks",
    "get_overdue_tasks",
    "prospective_get_statistics",
    "add_entity",
    "add_relationship",
    "find_entity",
    "search_entities",
    "find_related",
    "get_communities",
    "update_entity_importance",
    "graph_get_statistics",
    "rate_memory",
    "get_expertise",
    "get_memory_quality",
    "get_cognitive_load",
    "update_cognitive_load",
    "meta_get_statistics",
    "consolidate",
    "extract_patterns",
    "extract_procedures",
    "get_consolidation_history",
    "get_consolidation_metrics",
    "consolidation_get_statistics",
    "create_plan",
    "validate_plan",
    "get_plan",
    "list_plans",
    "estimate_effort",
    "update_plan_status",
    "planning_get_statistics",
]
