"""TodoWrite ↔ Athena Planning Integration Layer

This module provides bidirectional synchronization between Claude Code's TodoWrite
task tracking and Athena's sophisticated planning system.

TodoWrite represents the user-facing, simple task tracking (what am I doing now?).
Athena Planning represents sophisticated planning with phases, validation, and learning.

The mapping layer enables:
- TodoWrite → Athena Planning: Convert simple todos to rich plans
- Athena → TodoWrite: Summarize sophisticated plans as simple todos
- Status/Priority Translation: Map between TodoWrite's 3 states and Athena's rich models

Usage:
    # Convert a TodoWrite item to an Athena plan
    todo_item = {"content": "Implement feature X", "status": "in_progress", "activeForm": "Implementing feature X"}
    plan = await convert_todo_to_plan(todo_item, project_id=1)

    # Convert an Athena plan back to TodoWrite format
    athena_plan = await get_plan(plan_id)
    todo = convert_plan_to_todo(athena_plan)
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# STATUS & PRIORITY MAPPINGS
# ============================================================================


class TodoWriteStatus(str, Enum):
    """TodoWrite uses 3 states."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class AthenaTaskStatus(str, Enum):
    """Athena planning uses richer status."""

    PENDING = "pending"
    PLANNING = "planning"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Priority mapping: TodoWrite doesn't have explicit priority, Athena uses 1-10
class PriorityLevel(int, Enum):
    """Unified priority scale (1-10)."""

    CRITICAL = 10
    VERY_HIGH = 9
    HIGH = 8
    HIGH_MEDIUM = 7
    MEDIUM = 5
    LOW_MEDIUM = 3
    LOW = 2
    VERY_LOW = 1


# ============================================================================
# CONVERSION FUNCTIONS
# ============================================================================


async def convert_todo_to_plan(
    todo_item: Dict[str, Any],
    project_id: int,
    auto_phase: bool = True,
) -> Dict[str, Any]:
    """Convert a TodoWrite item to an Athena Plan.

    Args:
        todo_item: TodoWrite todo {content, status, activeForm}
        project_id: Project ID for the plan
        auto_phase: Whether to auto-assign planning phase based on status

    Returns:
        Plan dict ready for Athena storage
    """
    if not todo_item or "content" not in todo_item:
        raise ValueError("Invalid todo_item: must have 'content' field")

    todo_status = todo_item.get("status", "pending")
    content = todo_item.get("content", "")
    active_form = todo_item.get("activeForm", content)

    # Determine planning phase based on TodoWrite status
    phase = _determine_phase_from_todo_status(todo_status) if auto_phase else 1

    # Convert TodoWrite status to Athena status
    athena_status = _map_todowrite_to_athena_status(todo_status)

    # Extract priority hint from content (if any)
    priority = _extract_priority_hint(content)

    plan = {
        "goal": content,
        "description": active_form,  # activeForm gives us what we're currently doing
        "status": athena_status,
        "phase": phase,
        "priority": priority,
        "project_id": project_id,
        "created_at": datetime.now().isoformat(),
        "source": "todowrite",  # Track that this came from TodoWrite
        "tags": ["todowrite"],
        "steps": _generate_default_steps(content, phase),
        "assumptions": [],
        "risks": [],
        "original_todo": todo_item,  # Store original for reverse mapping
    }

    return plan


def convert_plan_to_todo(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Convert an Athena Plan back to TodoWrite format.

    Args:
        plan: Athena plan dict

    Returns:
        TodoWrite todo dict {content, status, activeForm}
    """
    if not plan or "goal" not in plan:
        raise ValueError("Invalid plan: must have 'goal' field")

    # If this plan was created from a TodoWrite, use original
    if "original_todo" in plan and plan.get("source") == "todowrite":
        original = plan["original_todo"]
        # Update status based on plan's current state
        original["status"] = _map_athena_to_todowrite_status(plan.get("status", "pending"))
        return original

    # Convert Athena status to TodoWrite status
    todowrite_status = _map_athena_to_todowrite_status(plan.get("status", "pending"))

    # Determine activeForm from description or goal
    active_form = plan.get("description", "") or plan.get("goal", "")

    todo = {
        "content": plan.get("goal", ""),
        "status": todowrite_status,
        "activeForm": active_form,
    }

    return todo


# ============================================================================
# STATUS MAPPING FUNCTIONS
# ============================================================================


def _map_todowrite_to_athena_status(todo_status: str) -> str:
    """Map TodoWrite status to Athena status.

    TodoWrite → Athena mapping:
    - pending → pending (not started)
    - in_progress → in_progress (currently working)
    - completed → completed (done)
    """
    mapping = {
        TodoWriteStatus.PENDING.value: AthenaTaskStatus.PENDING.value,
        TodoWriteStatus.IN_PROGRESS.value: AthenaTaskStatus.IN_PROGRESS.value,
        TodoWriteStatus.COMPLETED.value: AthenaTaskStatus.COMPLETED.value,
    }

    return mapping.get(todo_status, AthenaTaskStatus.PENDING.value)


def _map_athena_to_todowrite_status(athena_status: str) -> str:
    """Map Athena status back to TodoWrite status.

    Athena → TodoWrite mapping:
    - planning, ready, blocked → in_progress (work is happening)
    - in_progress → in_progress
    - completed → completed
    - failed, cancelled → completed (terminal states collapse)
    - pending → pending
    """
    mapping = {
        # Athena states that map to TodoWrite states
        AthenaTaskStatus.PENDING.value: TodoWriteStatus.PENDING.value,
        AthenaTaskStatus.PLANNING.value: TodoWriteStatus.IN_PROGRESS.value,
        AthenaTaskStatus.READY.value: TodoWriteStatus.IN_PROGRESS.value,
        AthenaTaskStatus.IN_PROGRESS.value: TodoWriteStatus.IN_PROGRESS.value,
        AthenaTaskStatus.BLOCKED.value: TodoWriteStatus.IN_PROGRESS.value,
        AthenaTaskStatus.COMPLETED.value: TodoWriteStatus.COMPLETED.value,
        AthenaTaskStatus.FAILED.value: TodoWriteStatus.COMPLETED.value,
        AthenaTaskStatus.CANCELLED.value: TodoWriteStatus.COMPLETED.value,
    }

    return mapping.get(athena_status, TodoWriteStatus.PENDING.value)


# ============================================================================
# PHASE DETERMINATION
# ============================================================================


def _determine_phase_from_todo_status(todo_status: str) -> int:
    """Determine Athena planning phase from TodoWrite status.

    Phase 1: Planning (pending → planning)
    Phase 2: Ready (ready for execution)
    Phase 3: Execution (in_progress)
    Phase 4: Validation (checking results)
    Phase 5: Complete (completed)
    Phase 6: Learning (optional advanced planning)

    Args:
        todo_status: TodoWrite status string

    Returns:
        Phase number (1-6)
    """
    phase_mapping = {
        TodoWriteStatus.PENDING.value: 1,  # Planning phase
        TodoWriteStatus.IN_PROGRESS.value: 3,  # Execution phase
        TodoWriteStatus.COMPLETED.value: 5,  # Complete phase
    }

    return phase_mapping.get(todo_status, 1)


# ============================================================================
# PRIORITY EXTRACTION
# ============================================================================


def _extract_priority_hint(content: str) -> int:
    """Extract priority hints from todo content.

    Looks for keywords like:
    - CRITICAL, URGENT, BLOCKING → 9-10
    - HIGH PRIORITY → 7-8
    - IMPORTANT → 6-7
    - Default → 5 (medium)
    - LOW PRIORITY → 2-3

    Args:
        content: Todo content string

    Returns:
        Priority score (1-10)
    """
    content_upper = content.upper()

    if any(word in content_upper for word in ["CRITICAL", "URGENT", "BLOCKING"]):
        return 9
    elif any(word in content_upper for word in ["HIGH PRIORITY", "HIGH-PRIORITY"]):
        return 7
    elif any(word in content_upper for word in ["IMPORTANT"]):
        return 6
    elif any(word in content_upper for word in ["LOW PRIORITY", "LOW-PRIORITY", "FIX LATER"]):
        return 2
    else:
        return 5  # Default medium priority


# ============================================================================
# DEFAULT STEP GENERATION
# ============================================================================


def _generate_default_steps(content: str, phase: int) -> List[Dict[str, Any]]:
    """Generate default steps based on todo content and phase.

    Args:
        content: Goal/content string
        phase: Planning phase (1-6)

    Returns:
        List of step dicts
    """
    steps = []

    if phase == 1:  # Planning phase
        steps = [
            {"step": 1, "description": "Analyze requirements", "status": "pending"},
            {"step": 2, "description": "Identify dependencies", "status": "pending"},
            {"step": 3, "description": "Create detailed plan", "status": "pending"},
        ]
    elif phase == 3:  # Execution phase
        steps = [
            {"step": 1, "description": "Implement main feature", "status": "pending"},
            {"step": 2, "description": "Write tests", "status": "pending"},
            {"step": 3, "description": "Code review", "status": "pending"},
        ]
    elif phase == 5:  # Complete phase
        steps = [
            {"step": 1, "description": "Final verification", "status": "completed"},
            {"step": 2, "description": "Documentation", "status": "completed"},
        ]

    return steps


# ============================================================================
# BATCH CONVERSION
# ============================================================================


async def convert_todo_list_to_plans(
    todos: List[Dict[str, Any]],
    project_id: int,
) -> List[Dict[str, Any]]:
    """Convert a list of TodoWrite items to Athena plans.

    Args:
        todos: List of TodoWrite todo items
        project_id: Project ID for the plans

    Returns:
        List of Athena plan dicts
    """
    plans = []
    for todo in todos:
        try:
            plan = await convert_todo_to_plan(todo, project_id)
            plans.append(plan)
        except ValueError as e:
            logger.warning(f"Failed to convert todo: {e}")
            continue

    return plans


def convert_plan_list_to_todos(plans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert a list of Athena plans back to TodoWrite format.

    Args:
        plans: List of Athena plan dicts

    Returns:
        List of TodoWrite todo dicts
    """
    todos = []
    for plan in plans:
        try:
            todo = convert_plan_to_todo(plan)
            todos.append(todo)
        except ValueError as e:
            logger.warning(f"Failed to convert plan: {e}")
            continue

    return todos


# ============================================================================
# SYNC STATE TRACKING
# ============================================================================


class SyncMetadata:
    """Metadata about sync state between TodoWrite and Athena."""

    def __init__(self):
        self.last_sync: Optional[datetime] = None
        self.todo_to_plan_mapping: Dict[str, str] = {}  # todo_id → plan_id
        self.plan_to_todo_mapping: Dict[str, str] = {}  # plan_id → todo_id
        self.pending_sync: List[str] = []  # IDs of items pending sync

    def map_todo_to_plan(self, todo_id: str, plan_id: str) -> None:
        """Record mapping from todo to plan."""
        self.todo_to_plan_mapping[todo_id] = plan_id
        if todo_id in self.pending_sync:
            self.pending_sync.remove(todo_id)

    def map_plan_to_todo(self, plan_id: str, todo_id: str) -> None:
        """Record mapping from plan to todo."""
        self.plan_to_todo_mapping[plan_id] = todo_id
        if plan_id in self.pending_sync:
            self.pending_sync.remove(plan_id)

    def mark_pending_sync(self, item_id: str) -> None:
        """Mark an item as pending sync."""
        if item_id not in self.pending_sync:
            self.pending_sync.append(item_id)

    def update_sync_time(self) -> None:
        """Update last sync time."""
        self.last_sync = datetime.now()


# Global sync metadata instance
_sync_metadata = SyncMetadata()


def get_sync_metadata() -> SyncMetadata:
    """Get the global sync metadata."""
    return _sync_metadata


# ============================================================================
# CONFLICT RESOLUTION
# ============================================================================


def detect_sync_conflict(
    todo: Dict[str, Any],
    plan: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Detect if a todo and plan are out of sync.

    Returns:
        (has_conflict, conflict_description)
    """
    todo_status = todo.get("status", "pending")
    athena_status = plan.get("status", "pending")
    mapped_status = _map_athena_to_todowrite_status(athena_status)

    if todo_status != mapped_status:
        return True, f"Status mismatch: todo={todo_status}, plan={athena_status}"

    # Check if content differs significantly
    todo_content = todo.get("content", "").lower().strip()
    plan_goal = plan.get("goal", "").lower().strip()

    if todo_content != plan_goal:
        if len(todo_content) > 0 and len(plan_goal) > 0:
            if todo_content not in plan_goal and plan_goal not in todo_content:
                return True, "Content mismatch: todo != plan goal"

    return False, None


async def resolve_sync_conflict(
    todo: Dict[str, Any],
    plan: Dict[str, Any],
    prefer: str = "plan",  # "todo" or "plan"
) -> Dict[str, Any]:
    """Resolve a sync conflict by choosing the authoritative source.

    Args:
        todo: TodoWrite todo item
        plan: Athena plan dict
        prefer: Which source to prefer ("todo" or "plan")

    Returns:
        Resolved state dict with both todo and plan updated
    """
    if prefer == "todo":
        # Todo wins: update plan from todo
        return {
            "todo": todo,
            "plan": await convert_todo_to_plan(todo, plan.get("project_id", 1)),
            "resolution": "todo_wins",
        }
    else:
        # Plan wins: update todo from plan
        return {
            "todo": convert_plan_to_todo(plan),
            "plan": plan,
            "resolution": "plan_wins",
        }


# ============================================================================
# SUMMARY STATISTICS
# ============================================================================


async def get_sync_statistics() -> Dict[str, Any]:
    """Get statistics about the TodoWrite ↔ Athena sync system.

    Returns:
        Dictionary with sync metrics
    """
    metadata = get_sync_metadata()

    return {
        "last_sync": metadata.last_sync.isoformat() if metadata.last_sync else None,
        "todo_to_plan_mappings": len(metadata.todo_to_plan_mapping),
        "plan_to_todo_mappings": len(metadata.plan_to_todo_mapping),
        "pending_sync_count": len(metadata.pending_sync),
        "total_tracked_items": (
            len(metadata.todo_to_plan_mapping) + len(metadata.plan_to_todo_mapping)
        ),
    }
