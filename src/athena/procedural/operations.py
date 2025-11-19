"""Procedural Memory Operations - Direct Python API

This module provides clean async functions for procedural memory operations.
Procedural memory stores reusable workflows, patterns, and procedures.

Functions can be imported and called directly by agents:
  from athena.procedural.operations import extract_procedure, list_procedures
  procedure_id = await extract_procedure("code review workflow", steps=[...])
  procedures = await list_procedures(limit=10)

No MCP protocol, no wrapper overhead. Just Python async functions.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..core.database import Database
from .store import ProceduralStore
from .models import Procedure

logger = logging.getLogger(__name__)


class ProceduralOperations:
    """Encapsulates all procedural memory operations.

    This class is instantiated with a database and procedural store,
    providing all operations as methods.
    """

    def __init__(self, db: Database, store: ProceduralStore):
        """Initialize with database and procedural store.

        Args:
            db: Database instance
            store: ProceduralStore instance
        """
        self.db = db
        self.store = store
        self.logger = logger

    async def extract_procedure(
        self,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        tags: List[str] | None = None,
        success_rate: float = 0.5,
        source: str = "agent",
    ) -> int:
        """Extract and store a reusable procedure.

        Args:
            name: Procedure name
            description: What the procedure does
            steps: List of steps (each step is a dict with action, params, conditions)
            tags: Tags for categorization (not stored in current schema)
            success_rate: Success rate of this procedure (0.0-1.0)
            source: Source identifier

        Returns:
            Procedure ID
        """
        if not name or not description or not steps:
            raise ValueError("name, description, and steps are required")

        success_rate = max(0.0, min(1.0, success_rate))

        procedure = Procedure(
            name=name,
            description=description,
            steps=steps,
            success_rate=success_rate,
            created_at=datetime.now(),
            last_used=None,
            usage_count=0,
            created_by=source,  # Store source as created_by
        )

        # store() returns a Procedure with ID set
        stored_proc = await self.store.store(procedure)
        return stored_proc.id or 0

    async def list_procedures(
        self,
        limit: int = 20,
        tags: List[str] | None = None,
        min_success_rate: float = 0.0,
    ) -> List[Procedure]:
        """List procedures, optionally filtered.

        Args:
            limit: Maximum procedures to return
            tags: Optional tag filters (not supported in current schema)
            min_success_rate: Minimum success rate threshold (applied after retrieval)

        Returns:
            List of procedures
        """
        # Get procedures from store
        procedures = await self.store.list(limit=limit)

        # Filter by success rate if specified
        if min_success_rate > 0.0:
            procedures = [p for p in procedures if p.success_rate >= min_success_rate]

        return procedures

    async def get_procedure(
        self,
        procedure_id: str | int,
    ) -> Optional[Procedure]:
        """Get a specific procedure by ID.

        Args:
            procedure_id: Procedure ID

        Returns:
            Procedure object or None if not found
        """
        # Convert string ID to int if needed
        pid = int(procedure_id) if isinstance(procedure_id, str) else procedure_id
        return await self.store.get(pid)

    async def search_procedures(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Procedure]:
        """Search procedures by name or description.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            Matching procedures
        """
        if not query:
            return []

        return await self.store.search(query, limit=limit)

    async def get_procedures_by_tags(
        self,
        tags: List[str],
        limit: int = 20,
    ) -> List[Procedure]:
        """Get procedures matching tags.

        Note: Tags are not stored in the current database schema.
        This method is deprecated and returns an empty list.

        Args:
            tags: Tags to match (not supported)
            limit: Maximum procedures to return

        Returns:
            Empty list (tags not supported in current schema)
        """
        # Tags are not supported in the current schema
        return []

    async def update_procedure_success(
        self,
        procedure_id: str | int,
        success: bool,
    ) -> bool:
        """Update procedure success rate and use count.

        Args:
            procedure_id: Procedure ID
            success: Whether the procedure succeeded

        Returns:
            True if updated successfully
        """
        # Convert string ID to int if needed
        pid = int(procedure_id) if isinstance(procedure_id, str) else procedure_id
        procedure = await self.store.get(pid)
        if not procedure:
            return False

        # Update success rate (exponential moving average)
        old_success = procedure.success_rate
        old_count = procedure.usage_count  # Use usage_count (not use_count)
        new_count = old_count + 1
        new_success = (old_success * old_count + (1.0 if success else 0.0)) / new_count

        procedure.success_rate = new_success
        procedure.usage_count = new_count
        procedure.last_used = datetime.now()

        await self.store.update(procedure)
        return True

    async def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about procedures.

        Returns:
            Dictionary with procedure statistics
        """
        procedures = await self.store.list(limit=10000)

        if not procedures:
            return {
                "total_procedures": 0,
                "avg_success_rate": 0.0,
                "avg_use_count": 0,
            }

        success_rates = [p.success_rate for p in procedures if p.success_rate is not None]
        usage_counts = [p.usage_count for p in procedures]

        return {
            "total_procedures": len(procedures),
            "avg_success_rate": sum(success_rates) / len(success_rates) if success_rates else 0.0,
            "total_uses": sum(usage_counts),
            "avg_uses_per_procedure": sum(usage_counts) / len(procedures) if procedures else 0,
            "most_used": max((p for p in procedures), key=lambda p: p.usage_count, default=None),
        }


# Global singleton instance (lazy-initialized by manager)
_operations: ProceduralOperations | None = None


def initialize(db: Database, store: ProceduralStore) -> None:
    """Initialize the global procedural operations instance.

    Called by UnifiedMemoryManager during setup.

    Args:
        db: Database instance
        store: ProceduralStore instance
    """
    global _operations
    _operations = ProceduralOperations(db, store)


def get_operations() -> ProceduralOperations:
    """Get the global procedural operations instance.

    Returns:
        ProceduralOperations instance

    Raises:
        RuntimeError: If not initialized
    """
    if _operations is None:
        raise RuntimeError(
            "Procedural operations not initialized. " "Call initialize(db, store) first."
        )
    return _operations


# Convenience functions that delegate to global instance
async def extract_procedure(
    name: str,
    description: str,
    steps: List[Dict[str, Any]],
    tags: List[str] | None = None,
    success_rate: float = 0.5,
    source: str = "agent",
) -> int:
    """Extract and store a procedure. See ProceduralOperations.extract_procedure for details."""
    ops = get_operations()
    return await ops.extract_procedure(
        name=name,
        description=description,
        steps=steps,
        tags=tags,
        success_rate=success_rate,
        source=source,
    )


async def list_procedures(
    limit: int = 20,
    tags: List[str] | None = None,
    min_success_rate: float = 0.0,
) -> List[Procedure]:
    """List procedures. See ProceduralOperations.list_procedures for details."""
    ops = get_operations()
    return await ops.list_procedures(limit=limit, tags=tags, min_success_rate=min_success_rate)


async def get_procedure(procedure_id: str | int) -> Optional[Procedure]:
    """Get a procedure. See ProceduralOperations.get_procedure for details."""
    ops = get_operations()
    return await ops.get_procedure(procedure_id)


async def search_procedures(query: str, limit: int = 10) -> List[Procedure]:
    """Search procedures. See ProceduralOperations.search_procedures for details."""
    ops = get_operations()
    return await ops.search_procedures(query=query, limit=limit)


async def get_procedures_by_tags(tags: List[str], limit: int = 20) -> List[Procedure]:
    """Get procedures by tags. See ProceduralOperations.get_procedures_by_tags for details."""
    ops = get_operations()
    return await ops.get_procedures_by_tags(tags=tags, limit=limit)


async def update_procedure_success(procedure_id: str | int, success: bool) -> bool:
    """Update procedure success. See ProceduralOperations.update_procedure_success for details."""
    ops = get_operations()
    return await ops.update_procedure_success(procedure_id=procedure_id, success=success)


async def get_statistics() -> Dict[str, Any]:
    """Get procedure statistics. See ProceduralOperations.get_statistics for details."""
    ops = get_operations()
    return await ops.get_statistics()
