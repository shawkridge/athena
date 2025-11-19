"""Operations exposed by memory flow system for use by other modules.

These functions provide the public API for memory flow management.
"""

from ..core.database import Database
from .router import MemoryFlowRouter


async def record_event_access(event_id: int, boost: float = 0.5) -> None:
    """Record that an event was accessed.

    Triggers:
    - Activation boost
    - RIF (Retrieval-Induced Forgetting) on similar items
    - Potential promotion to working memory
    - Tier capacity enforcement

    Args:
        event_id: ID of event being accessed
        boost: Activation boost amount (0.0-1.0)
    """
    db = Database()
    await db.initialize()
    router = MemoryFlowRouter(db)
    await router.record_event_access(event_id, boost=boost)


async def run_decay_cycle() -> dict[str, int]:
    """Run temporal decay cycle.

    Updates activation levels based on time elapsed and enforces
    tier capacity limits.

    Returns:
        Stats: {'decayed': N, 'demoted': N, 'archived': N}
    """
    db = Database()
    await db.initialize()
    router = MemoryFlowRouter(db)
    return await router.process_decay()


async def run_consolidation_cycle() -> dict[str, int]:
    """Run selective consolidation cycle.

    Promotes strong items (activation > 0.7) to semantic memory
    and decays weak items (activation < 0.4).

    Returns:
        Stats: {'promoted': N, 'maintained': N, 'decayed': N}
    """
    db = Database()
    await db.initialize()
    router = MemoryFlowRouter(db)
    return await router.run_consolidation_cycle()


async def run_temporal_clustering(promote_all: bool = False) -> dict[str, int]:
    """Run temporal clustering and consolidation.

    Groups items by temporal proximity and consolidates them together.

    Args:
        promote_all: If True, promote all clusters to semantic

    Returns:
        Stats: {'clustered': N, 'consolidated': N}
    """
    db = Database()
    await db.initialize()
    router = MemoryFlowRouter(db)
    return await router.run_temporal_clustering(promote_all=promote_all)


async def get_working_memory(limit: int = 7) -> list[dict]:
    """Get current working memory items (7±2 most active).

    Args:
        limit: Maximum items (default: 7 per Baddeley)

    Returns:
        List of working memory events
    """
    db = Database()
    await db.initialize()
    router = MemoryFlowRouter(db)
    return await router.get_working_memory(limit=limit)


async def search_hot_first(query: str, limit: int = 10) -> list[dict]:
    """Search memory hot-first: working → session → episodic.

    Args:
        query: Search query
        limit: Maximum results

    Returns:
        List of matching events
    """
    db = Database()
    await db.initialize()
    router = MemoryFlowRouter(db)
    return await router.search_hot_first(query, limit=limit)


async def get_consolidation_candidates(
    strength_threshold: float = 0.7,
) -> list[dict]:
    """Get events ready for consolidation to semantic memory.

    Args:
        strength_threshold: Minimum activation for consolidation

    Returns:
        List of candidate events
    """
    db = Database()
    await db.initialize()
    router = MemoryFlowRouter(db)
    return await router.get_consolidation_candidates(strength_threshold)


async def get_flow_health() -> dict:
    """Get overall memory flow health metrics.

    Returns:
        Dict with health indicators and warnings
    """
    db = Database()
    await db.initialize()
    router = MemoryFlowRouter(db)
    return await router.get_flow_health()


async def get_statistics(hours: int = 24) -> dict:
    """Get flow system statistics for a time period.

    Args:
        hours: Time window for statistics

    Returns:
        Dict with detailed metrics
    """
    db = Database()
    await db.initialize()
    router = MemoryFlowRouter(db)
    stats = await router.get_statistics(hours=hours)
    return stats.model_dump() if stats else {}
