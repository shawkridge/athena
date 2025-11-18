"""Consolidation Operations - Direct Python API

This module provides clean async functions for consolidation operations.
Consolidation extracts patterns, procedures, and learnings from memories.

Functions can be imported and called directly by agents:
  from athena.consolidation.operations import consolidate, extract_patterns
  result = await consolidate(strategy="balanced")
  patterns = await extract_patterns(memory_limit=100)

No MCP protocol, no wrapper overhead. Just Python async functions.
"""

import logging
from typing import Any, Dict, List

from ..core.database import Database
from .system import ConsolidationSystem

logger = logging.getLogger(__name__)


class ConsolidationOperations:
    """Encapsulates all consolidation operations.

    This class is instantiated with a database and consolidation system,
    providing all operations as methods.
    """

    def __init__(self, db: Database, system: ConsolidationSystem):
        """Initialize with database and consolidation system.

        Args:
            db: Database instance
            system: ConsolidationSystem instance
        """
        self.db = db
        self.system = system
        self.logger = logger

    async def consolidate(
        self,
        strategy: str = "balanced",
        days_back: int = 7,
        limit: int | None = None,
    ) -> Dict[str, Any]:
        """Run consolidation on recent memories.

        Args:
            strategy: Consolidation strategy (balanced, aggressive, conservative)
            days_back: How many days of memories to consolidate
            limit: Optional limit on number of memories to process

        Returns:
            Consolidation results with patterns extracted
        """
        return await self.system.consolidate(
            strategy=strategy,
            days_back=days_back,
            limit=limit,
        )

    async def extract_patterns(
        self,
        memory_limit: int = 100,
        min_frequency: int = 2,
    ) -> List[Dict[str, Any]]:
        """Extract patterns from recent memories.

        Args:
            memory_limit: Maximum memories to analyze
            min_frequency: Minimum occurrences to consider a pattern

        Returns:
            List of extracted patterns
        """
        return await self.system.extract_patterns(
            memory_limit=memory_limit,
            min_frequency=min_frequency,
        )

    async def extract_procedures(
        self,
        memory_limit: int = 50,
        min_success_rate: float = 0.6,
    ) -> List[Dict[str, Any]]:
        """Extract reusable procedures from memories.

        Args:
            memory_limit: Maximum memories to analyze
            min_success_rate: Minimum success rate for procedures

        Returns:
            List of extracted procedures
        """
        return await self.system.extract_procedures(
            memory_limit=memory_limit,
            min_success_rate=min_success_rate,
        )

    async def get_consolidation_history(
        self,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get consolidation run history.

        Args:
            limit: Maximum runs to return

        Returns:
            List of consolidation runs
        """
        return await self.system.get_history(limit=limit)

    async def get_consolidation_metrics(self) -> Dict[str, Any]:
        """Get metrics about consolidation effectiveness.

        Returns:
            Consolidation metrics
        """
        return await self.system.get_metrics()

    async def get_statistics(self) -> Dict[str, Any]:
        """Get consolidation statistics.

        Returns:
            Dictionary with consolidation statistics
        """
        history = await self.get_consolidation_history(limit=100)
        metrics = await self.get_consolidation_metrics()

        return {
            "total_runs": len(history),
            "last_run": history[0] if history else None,
            "metrics": metrics,
        }


# Global singleton instance (lazy-initialized by manager)
_operations: ConsolidationOperations | None = None


def initialize(db: Database, system: ConsolidationSystem) -> None:
    """Initialize the global consolidation operations instance.

    Called by UnifiedMemoryManager during setup.

    Args:
        db: Database instance
        system: ConsolidationSystem instance
    """
    global _operations
    _operations = ConsolidationOperations(db, system)


def get_operations() -> ConsolidationOperations:
    """Get the global consolidation operations instance.

    Returns:
        ConsolidationOperations instance

    Raises:
        RuntimeError: If not initialized
    """
    if _operations is None:
        raise RuntimeError(
            "Consolidation operations not initialized. Call initialize(db, system) first."
        )
    return _operations


# Convenience functions that delegate to global instance
async def consolidate(
    strategy: str = "balanced",
    days_back: int = 7,
    limit: int | None = None,
) -> Dict[str, Any]:
    """Consolidate memories. See ConsolidationOperations.consolidate for details."""
    ops = get_operations()
    return await ops.consolidate(strategy=strategy, days_back=days_back, limit=limit)


async def extract_patterns(
    memory_limit: int = 100,
    min_frequency: int = 2,
) -> List[Dict[str, Any]]:
    """Extract patterns. See ConsolidationOperations.extract_patterns for details."""
    ops = get_operations()
    return await ops.extract_patterns(memory_limit=memory_limit, min_frequency=min_frequency)


async def extract_procedures(
    memory_limit: int = 50,
    min_success_rate: float = 0.6,
) -> List[Dict[str, Any]]:
    """Extract procedures. See ConsolidationOperations.extract_procedures for details."""
    ops = get_operations()
    return await ops.extract_procedures(
        memory_limit=memory_limit, min_success_rate=min_success_rate
    )


async def get_consolidation_history(limit: int = 10) -> List[Dict[str, Any]]:
    """Get consolidation history. See ConsolidationOperations.get_consolidation_history for details."""
    ops = get_operations()
    return await ops.get_consolidation_history(limit=limit)


async def get_consolidation_metrics() -> Dict[str, Any]:
    """Get metrics. See ConsolidationOperations.get_consolidation_metrics for details."""
    ops = get_operations()
    return await ops.get_consolidation_metrics()


async def get_statistics() -> Dict[str, Any]:
    """Get consolidation statistics. See ConsolidationOperations.get_statistics for details."""
    ops = get_operations()
    return await ops.get_statistics()
