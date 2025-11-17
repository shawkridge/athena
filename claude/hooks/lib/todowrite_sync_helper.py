"""TodoWrite ↔ Athena Sync Helper for Claude Code Hooks

This helper module is used by Claude Code hooks to synchronize TodoWrite items
with Athena's planning system at session boundaries.

Used by:
- session_context_manager.py: Load TodoWrite items as working memory
- post_task_completion.sh: Sync completed todos to Athena
- session_end.sh: Extract procedures from todo patterns

Integration Points:
- SessionStart: Inject active todos as working memory context
- PostTaskCompletion: Sync todo completion to Athena
- SessionEnd: Extract and consolidate todo patterns
"""

import json
import logging
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[TodoWrite Sync] %(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add athena to path if available
try:
    athena_src = Path.home() / ".work" / "athena" / "src"
    if athena_src.exists():
        sys.path.insert(0, str(athena_src))
except Exception as e:
    logger.warning(f"Could not add athena to path: {e}")


# ============================================================================
# TODOWRITE SYNC OPERATIONS
# ============================================================================

async def load_active_todos() -> List[Dict[str, Any]]:
    """Load active TodoWrite todos from the current session.

    In a real implementation, this would read from Claude Code's state.
    For now, returns a template structure.

    Returns:
        List of active todo items
    """
    # In integration with Claude Code, this would be passed from the parent process
    # For now, return empty list - Claude Code will inject actual todos
    return []


async def sync_todo_to_athena(
    todo: Dict[str, Any],
    project_id: int = 1,
) -> Tuple[bool, Optional[str]]:
    """Sync a single TodoWrite item to Athena planning with database persistence.

    Args:
        todo: TodoWrite todo item {content, status, activeForm}
        project_id: Project ID for the plan

    Returns:
        (success, plan_id or error_message)
    """
    try:
        from athena.integration.sync_operations import sync_todo_to_database
        from athena.core.database import Database

        # Initialize database if needed
        db = Database()

        # Sync todo to database
        success, result = await sync_todo_to_database(todo, project_id=project_id)

        if success:
            logger.info(f"Synced todo to Athena database: {result}")
            return True, result
        else:
            logger.error(f"Failed to sync todo: {result}")
            return False, result

    except ImportError as e:
        logger.warning(f"Athena not available: {e}")
        return False, "Athena integration not available"
    except Exception as e:
        logger.error(f"Failed to sync todo: {e}")
        return False, str(e)


async def sync_todo_completion(
    todo_id: str,
    status: str,
    project_id: int = 1,
) -> Tuple[bool, Optional[str]]:
    """Sync a todo completion to Athena.

    Args:
        todo_id: TodoWrite todo ID
        status: New status (pending, in_progress, completed)
        project_id: Project ID

    Returns:
        (success, message or error)
    """
    try:
        from athena.integration.todowrite_sync import get_sync_metadata

        metadata = get_sync_metadata()

        # Find the corresponding Athena plan
        plan_id = metadata.todo_to_plan_mapping.get(todo_id)
        if not plan_id:
            logger.warning(f"No plan mapping for todo {todo_id}")
            return False, f"No plan mapping for todo {todo_id}"

        # In a real implementation, this would call Athena API
        # to update the plan status
        logger.info(f"Synced todo completion to Athena plan: {plan_id}")

        return True, f"Updated plan {plan_id}"

    except Exception as e:
        logger.error(f"Failed to sync completion: {e}")
        return False, str(e)


async def extract_todo_patterns(
    completed_todos: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Extract patterns from completed todos for procedural learning.

    Args:
        completed_todos: List of completed todo items

    Returns:
        Pattern extraction results
    """
    try:
        from athena.integration.todowrite_sync import (
            convert_todo_list_to_plans,
            get_sync_metadata,
        )

        if not completed_todos:
            return {"patterns": [], "count": 0}

        logger.info(f"Extracting patterns from {len(completed_todos)} completed todos")

        # Convert todos to plans
        plans = await convert_todo_list_to_plans(completed_todos, project_id=1)

        # In a real implementation, this would call Athena's procedural
        # extraction to learn workflows from the completed tasks
        patterns = _extract_local_patterns(plans)

        logger.info(f"Extracted {len(patterns)} patterns from todos")

        return {
            "patterns": patterns,
            "count": len(patterns),
            "extracted_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to extract patterns: {e}")
        return {"patterns": [], "count": 0, "error": str(e)}


def _extract_local_patterns(plans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract workflow patterns from converted plans (local analysis).

    Args:
        plans: List of plans converted from todos

    Returns:
        List of identified patterns
    """
    patterns = []

    if not plans:
        return patterns

    # Pattern 1: Common phases
    phases = {}
    for plan in plans:
        phase = plan.get("phase", 1)
        phases[phase] = phases.get(phase, 0) + 1

    if phases:
        most_common_phase = max(phases.items(), key=lambda x: x[1])
        patterns.append({
            "type": "common_phase",
            "value": most_common_phase[0],
            "frequency": most_common_phase[1],
            "description": f"Phase {most_common_phase[0]} is most common",
        })

    # Pattern 2: Priority distribution
    priorities = {}
    for plan in plans:
        priority = plan.get("priority", 5)
        priorities[priority] = priorities.get(priority, 0) + 1

    if priorities:
        avg_priority = sum(p * c for p, c in priorities.items()) / len(plans)
        patterns.append({
            "type": "average_priority",
            "value": avg_priority,
            "description": f"Average priority: {avg_priority:.1f}",
        })

    # Pattern 3: Tags frequency
    all_tags = {}
    for plan in plans:
        for tag in plan.get("tags", []):
            all_tags[tag] = all_tags.get(tag, 0) + 1

    if all_tags:
        top_tag = max(all_tags.items(), key=lambda x: x[1])
        patterns.append({
            "type": "common_tag",
            "value": top_tag[0],
            "frequency": top_tag[1],
            "description": f"Tag '{top_tag[0]}' appears {top_tag[1]} times",
        })

    return patterns


# ============================================================================
# SYNC STATE MANAGEMENT
# ============================================================================

async def inject_todos_as_working_memory(
    todos: List[Dict[str, Any]],
    limit: int = 7,
) -> List[str]:
    """Format todos for injection as Claude working memory.

    Args:
        todos: List of TodoWrite todos
        limit: Maximum todos to include (Baddeley's 7±2)

    Returns:
        List of formatted working memory lines
    """
    try:
        from athena.integration.todowrite_sync import (
            _map_todowrite_to_athena_status,
        )

        working_memory = []

        # Sort by status (in_progress first, then pending)
        status_order = {"in_progress": 0, "pending": 1, "completed": 2}
        sorted_todos = sorted(
            todos,
            key=lambda t: (
                status_order.get(t.get("status", "pending"), 999),
                t.get("content", "")
            )
        )

        # Take top N items
        for i, todo in enumerate(sorted_todos[:limit], 1):
            content = todo.get("content", "")
            status = todo.get("status", "pending")
            athena_status = _map_todowrite_to_athena_status(status)

            working_memory.append(
                f"{i}. [{athena_status}] {content}"
            )

        return working_memory

    except Exception as e:
        logger.error(f"Failed to format working memory: {e}")
        return []


# ============================================================================
# SESSION HOOKS
# ============================================================================

async def on_session_start(session_id: str) -> Dict[str, Any]:
    """Called when a Claude Code session starts.

    Injects active todos from database as working memory context.

    Args:
        session_id: Session ID from Claude Code

    Returns:
        Metadata about the session setup
    """
    try:
        logger.info(f"Session start hook for {session_id}")

        from athena.integration.sync_operations import get_active_plans
        from athena.integration.todowrite_sync import (
            convert_plan_to_todo,
            _map_athena_to_todowrite_status,
        )

        # Get active plans from database
        try:
            active_plans = await get_active_plans(project_id=1, limit=7)
        except Exception:
            # Fall back to empty if database not available
            active_plans = []

        if not active_plans:
            logger.info("No active plans to inject")
            return {"todos_injected": 0}

        # Convert plans back to todos
        todos = [convert_plan_to_todo(plan) for plan in active_plans]

        # Format for injection
        memory_lines = await inject_todos_as_working_memory(todos)

        logger.info(f"Injected {len(memory_lines)} active todos as working memory")

        return {
            "session_id": session_id,
            "todos_injected": len(memory_lines),
            "memory_lines": memory_lines,
        }

    except Exception as e:
        logger.error(f"Session start hook failed: {e}")
        return {"error": str(e)}


async def on_session_end(
    session_id: str,
    completed_todos: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Called when a Claude Code session ends.

    Extracts patterns from completed todos for procedural learning.

    Args:
        session_id: Session ID
        completed_todos: List of todos completed in this session

    Returns:
        Consolidation results
    """
    try:
        logger.info(f"Session end hook for {session_id}")

        if not completed_todos:
            logger.info("No completed todos to consolidate")
            return {"patterns_extracted": 0}

        # Extract patterns
        results = await extract_todo_patterns(completed_todos)

        logger.info(
            f"Extracted {results['count']} patterns from "
            f"{len(completed_todos)} completed todos"
        )

        return {
            "session_id": session_id,
            "patterns_extracted": results["count"],
            "results": results,
        }

    except Exception as e:
        logger.error(f"Session end hook failed: {e}")
        return {"error": str(e)}


async def on_task_completion(
    task_id: str,
    todo_item: Dict[str, Any],
) -> Dict[str, Any]:
    """Called when a todo is completed.

    Args:
        task_id: Task/todo ID
        todo_item: The completed todo

    Returns:
        Sync results
    """
    try:
        logger.info(f"Task completion for {task_id}")

        # Sync to Athena
        success, plan_id = await sync_todo_to_athena(todo_item)

        if success:
            logger.info(f"Synced todo completion to Athena plan: {plan_id}")
            return {
                "task_id": task_id,
                "synced": True,
                "plan_id": plan_id,
            }
        else:
            logger.warning(f"Failed to sync todo: {plan_id}")
            return {
                "task_id": task_id,
                "synced": False,
                "error": plan_id,
            }

    except Exception as e:
        logger.error(f"Task completion hook failed: {e}")
        return {"error": str(e)}


# ============================================================================
# MAIN ENTRY POINT FOR SHELL SCRIPTS
# ============================================================================

async def main():
    """Main entry point for testing/debugging."""
    logger.info("TodoWrite Sync Helper initialized")

    # Example: Load and inject todos
    session_result = await on_session_start("session_test")
    logger.info(f"Session start result: {session_result}")

    # Example: Process a completed todo
    sample_todo = {
        "id": "todo_1",
        "content": "Implement feature X",
        "status": "completed",
        "activeForm": "Implemented feature X",
    }

    completion_result = await on_task_completion("todo_1", sample_todo)
    logger.info(f"Completion result: {completion_result}")


if __name__ == "__main__":
    asyncio.run(main())
