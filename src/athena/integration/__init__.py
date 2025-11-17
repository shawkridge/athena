"""Athena Integration Module

Provides integration between Athena and external systems like Claude Code's TodoWrite.

This module contains:
- todowrite_sync: Bidirectional sync between TodoWrite and Athena planning
- database_sync: Database persistence layer for synced plans
- sync_operations: High-level sync operations and workflows
"""

# Phase 1: Mapping layer
from .todowrite_sync import (
    convert_todo_to_plan,
    convert_plan_to_todo,
    convert_todo_list_to_plans,
    convert_plan_list_to_todos,
    detect_sync_conflict,
    resolve_sync_conflict,
    get_sync_metadata,
    get_sync_statistics,
    SyncMetadata,
    TodoWriteStatus,
    AthenaTaskStatus,
    PriorityLevel,
)

# Phase 2: Database layer
from .database_sync import (
    TodoWritePlanStore,
    initialize as initialize_database_store,
    get_store as get_database_store,
)

# Phase 2: Sync operations
from .sync_operations import (
    sync_todo_to_database,
    sync_todo_status_change,
    detect_database_conflicts,
    resolve_database_conflict,
    get_completed_plans,
    get_active_plans,
    get_sync_summary,
    cleanup_completed_plans,
    export_plans_as_todos,
)

__all__ = [
    # Phase 1: Mapping
    "convert_todo_to_plan",
    "convert_plan_to_todo",
    "convert_todo_list_to_plans",
    "convert_plan_list_to_todos",
    "detect_sync_conflict",
    "resolve_sync_conflict",
    "get_sync_metadata",
    "get_sync_statistics",
    "SyncMetadata",
    "TodoWriteStatus",
    "AthenaTaskStatus",
    "PriorityLevel",
    # Phase 2: Database
    "TodoWritePlanStore",
    "initialize_database_store",
    "get_database_store",
    # Phase 2: Operations
    "sync_todo_to_database",
    "sync_todo_status_change",
    "detect_database_conflicts",
    "resolve_database_conflict",
    "get_completed_plans",
    "get_active_plans",
    "get_sync_summary",
    "cleanup_completed_plans",
    "export_plans_as_todos",
]
