"""Planning Operations - Direct Python API

This module provides clean async functions for planning operations.
Planning handles task decomposition, validation, and execution strategies.

Functions can be imported and called directly by agents:
  from athena.planning.operations import create_plan, validate_plan
  plan = await create_plan("Implement feature X", depth=3)
  validation = await validate_plan(plan)

No MCP protocol, no wrapper overhead. Just Python async functions.
"""

import logging
from typing import Any, Dict, List, Optional

from ..core.database import Database
from .store import PlanningStore

logger = logging.getLogger(__name__)


class PlanningOperations:
    """Encapsulates all planning operations.

    This class is instantiated with a database and planning store,
    providing all operations as methods.
    """

    def __init__(self, db: Database, store: PlanningStore):
        """Initialize with database and planning store.

        Args:
            db: Database instance
            store: PlanningStore instance
        """
        self.db = db
        self.store = store
        self.logger = logger

    async def create_plan(
        self,
        goal: str,
        description: str = "",
        depth: int = 3,
        tags: List[str] | None = None,
    ) -> Dict[str, Any]:
        """Create a plan for a goal.

        Args:
            goal: Goal to plan for
            description: Additional context
            depth: Planning depth (1-5)
            tags: Optional tags

        Returns:
            Plan object with hierarchy
        """
        if not goal:
            raise ValueError("goal is required")

        depth = max(1, min(5, depth))

        plan = {
            "goal": goal,
            "description": description,
            "depth": depth,
            "tags": tags or [],
            "steps": [],
            "assumptions": [],
            "risks": [],
        }

        return await self.store.store_plan(plan)

    async def validate_plan(
        self,
        plan_id: str,
    ) -> Dict[str, Any]:
        """Validate a plan using formal verification.

        Args:
            plan_id: Plan ID to validate

        Returns:
            Validation results
        """
        plan = await self.store.get_plan(plan_id)
        if not plan:
            return {"valid": False, "error": "Plan not found"}

        return await self.store.validate_plan(plan_id)

    async def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get a plan by ID.

        Args:
            plan_id: Plan ID

        Returns:
            Plan object or None if not found
        """
        return await self.store.get_plan(plan_id)

    async def list_plans(
        self,
        limit: int = 20,
        status: str | None = None,
    ) -> List[Dict[str, Any]]:
        """List plans, optionally filtered by status.

        Args:
            limit: Maximum plans to return
            status: Optional status filter (pending, in_progress, completed, cancelled)

        Returns:
            List of plans
        """
        return await self.store.list_plans(limit=limit, status=status)

    async def estimate_effort(
        self,
        plan_id: str,
    ) -> Dict[str, Any]:
        """Estimate effort for a plan.

        Args:
            plan_id: Plan ID

        Returns:
            Effort estimate
        """
        plan = await self.store.get_plan(plan_id)
        if not plan:
            return {"estimate": 0, "error": "Plan not found"}

        return await self.store.estimate_effort(plan_id)

    async def update_plan_status(
        self,
        plan_id: str,
        status: str,
    ) -> bool:
        """Update plan status.

        Args:
            plan_id: Plan ID
            status: New status (pending, in_progress, completed, cancelled)

        Returns:
            True if updated successfully
        """
        return await self.store.update_plan_status(plan_id, status)

    async def get_statistics(self) -> Dict[str, Any]:
        """Get planning statistics.

        Returns:
            Dictionary with planning statistics
        """
        plans = await self.store.list_plans(limit=10000)

        if not plans:
            return {
                "total_plans": 0,
                "total_steps": 0,
                "avg_depth": 0.0,
            }

        return {
            "total_plans": len(plans),
            "total_steps": sum(len(p.get("steps", [])) for p in plans),
            "avg_depth": sum(p.get("depth", 1) for p in plans) / len(plans),
            "by_status": {
                "pending": len([p for p in plans if p.get("status") == "pending"]),
                "in_progress": len([p for p in plans if p.get("status") == "in_progress"]),
                "completed": len([p for p in plans if p.get("status") == "completed"]),
            },
        }


# Global singleton instance (lazy-initialized by manager)
_operations: PlanningOperations | None = None


def initialize(db: Database, store: PlanningStore) -> None:
    """Initialize the global planning operations instance.

    Called by UnifiedMemoryManager during setup.

    Args:
        db: Database instance
        store: PlanningStore instance
    """
    global _operations
    _operations = PlanningOperations(db, store)


def get_operations() -> PlanningOperations:
    """Get the global planning operations instance.

    Returns:
        PlanningOperations instance

    Raises:
        RuntimeError: If not initialized
    """
    if _operations is None:
        raise RuntimeError("Planning operations not initialized. Call initialize(db, store) first.")
    return _operations


# Convenience functions that delegate to global instance
async def create_plan(
    goal: str,
    description: str = "",
    depth: int = 3,
    tags: List[str] | None = None,
) -> Dict[str, Any]:
    """Create plan. See PlanningOperations.create_plan for details."""
    ops = get_operations()
    return await ops.create_plan(goal=goal, description=description, depth=depth, tags=tags)


async def validate_plan(plan_id: str) -> Dict[str, Any]:
    """Validate plan. See PlanningOperations.validate_plan for details."""
    ops = get_operations()
    return await ops.validate_plan(plan_id)


async def get_plan(plan_id: str) -> Optional[Dict[str, Any]]:
    """Get plan. See PlanningOperations.get_plan for details."""
    ops = get_operations()
    return await ops.get_plan(plan_id)


async def list_plans(limit: int = 20, status: str | None = None) -> List[Dict[str, Any]]:
    """List plans. See PlanningOperations.list_plans for details."""
    ops = get_operations()
    return await ops.list_plans(limit=limit, status=status)


async def estimate_effort(plan_id: str) -> Dict[str, Any]:
    """Estimate effort. See PlanningOperations.estimate_effort for details."""
    ops = get_operations()
    return await ops.estimate_effort(plan_id)


async def update_plan_status(plan_id: str, status: str) -> bool:
    """Update plan status. See PlanningOperations.update_plan_status for details."""
    ops = get_operations()
    return await ops.update_plan_status(plan_id, status)


async def get_statistics() -> Dict[str, Any]:
    """Get planning statistics. See PlanningOperations.get_statistics for details."""
    ops = get_operations()
    return await ops.get_statistics()
