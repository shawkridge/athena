"""Backward compatibility adapter for migrated tools.

This module provides a compatibility layer that maps old monolithic handler
calls to new modular tool implementations. It enables zero-downtime migration
from handlers.py to the new modular tool architecture.

All wrapper functions follow the original API while delegating to new tools.
"""
import asyncio
import logging
from typing import Any, Dict, Optional

from athena.tools import get_loader, get_registry

logger = logging.getLogger(__name__)

# Global tool loader for compatibility wrappers
_loader = get_loader()
_registry = get_registry()


def _call_tool(tool_key: str, **kwargs) -> Dict[str, Any]:
    """Call a tool synchronously from async context.

    Args:
        tool_key: Tool identifier (e.g., "memory.recall")
        **kwargs: Tool parameters

    Returns:
        Tool result or error response
    """
    try:
        tool = _loader.load_tool(tool_key)
        if not tool:
            return {"error": f"Tool '{tool_key}' not found", "status": "error"}

        # Run async execute in current event loop
        result = asyncio.run(tool.execute(**kwargs))
        return result
    except Exception as e:
        logger.error(f"Error calling tool {tool_key}: {e}")
        return {"error": str(e), "status": "error"}


# ============================================================================
# Memory Tool Wrappers (3 tools)
# ============================================================================

def memory_recall(query: str, query_type: str = "auto", limit: int = 10,
                  include_metadata: bool = False, min_relevance: float = 0.0,
                  **kwargs) -> Dict[str, Any]:
    """Backward compatible wrapper for memory_recall.

    Old API: self.server.tool() decorated method
    New API: RecallMemoryTool.execute()
    """
    return _call_tool("memory.recall",
                     query=query,
                     query_type=query_type,
                     limit=limit,
                     include_metadata=include_metadata,
                     min_relevance=min_relevance,
                     **kwargs)


def memory_store(content: str, memory_type: str = "auto", tags: Optional[list] = None,
                 importance: float = 0.5, context: Optional[dict] = None,
                 relationships: Optional[list] = None, **kwargs) -> Dict[str, Any]:
    """Backward compatible wrapper for memory_store.

    Old API: self.server.tool() decorated method
    New API: StoreMemoryTool.execute()
    """
    return _call_tool("memory.store",
                     content=content,
                     memory_type=memory_type,
                     tags=tags or [],
                     importance=importance,
                     context=context or {},
                     relationships=relationships or [],
                     **kwargs)


def memory_health(include_detailed_stats: bool = False,
                  include_quality_metrics: bool = False,
                  check_database: bool = False, **kwargs) -> Dict[str, Any]:
    """Backward compatible wrapper for memory_health.

    Old API: self.server.tool() decorated method
    New API: HealthCheckTool.execute()
    """
    return _call_tool("memory.health",
                     include_detailed_stats=include_detailed_stats,
                     include_quality_metrics=include_quality_metrics,
                     check_database=check_database,
                     **kwargs)


# ============================================================================
# Consolidation Tool Wrappers (2 tools)
# ============================================================================

def consolidation_start(strategy: str = "balanced", max_events: int = 10000,
                       uncertainty_threshold: float = 0.5,
                       dry_run: bool = False, **kwargs) -> Dict[str, Any]:
    """Backward compatible wrapper for consolidation_start.

    Old API: self.server.tool() decorated method
    New API: StartConsolidationTool.execute()
    """
    return _call_tool("consolidation.start",
                     strategy=strategy,
                     max_events=max_events,
                     uncertainty_threshold=uncertainty_threshold,
                     dry_run=dry_run,
                     **kwargs)


def consolidation_extract(pattern_type: str = "all", min_frequency: int = 3,
                         max_patterns: int = 100,
                         confidence_threshold: float = 0.6, **kwargs) -> Dict[str, Any]:
    """Backward compatible wrapper for consolidation_extract.

    Old API: self.server.tool() decorated method
    New API: ExtractPatternsTool.execute()
    """
    return _call_tool("consolidation.extract",
                     pattern_type=pattern_type,
                     min_frequency=min_frequency,
                     max_patterns=max_patterns,
                     confidence_threshold=confidence_threshold,
                     **kwargs)


# ============================================================================
# Planning Tool Wrappers (2 tools)
# ============================================================================

def planning_verify(plan: Dict[str, Any],
                   check_properties: Optional[list] = None,
                   include_stress_test: bool = True,
                   detail_level: str = "standard", **kwargs) -> Dict[str, Any]:
    """Backward compatible wrapper for planning_verify.

    Old API: self.server.tool() decorated method
    New API: VerifyPlanTool.execute()
    """
    return _call_tool("planning.verify",
                     plan=plan,
                     check_properties=check_properties or ["optimality", "completeness"],
                     include_stress_test=include_stress_test,
                     detail_level=detail_level,
                     **kwargs)


def planning_simulate(plan: Dict[str, Any], scenario_type: str = "nominal",
                     num_simulations: int = 5,
                     track_metrics: Optional[list] = None, **kwargs) -> Dict[str, Any]:
    """Backward compatible wrapper for planning_simulate.

    Old API: self.server.tool() decorated method
    New API: SimulatePlanTool.execute()
    """
    return _call_tool("planning.simulate",
                     plan=plan,
                     scenario_type=scenario_type,
                     num_simulations=num_simulations,
                     track_metrics=track_metrics or ["success_rate", "execution_time"],
                     **kwargs)


# ============================================================================
# Graph Tool Wrappers (2 tools)
# ============================================================================

def graph_query(query: str, query_type: str = "entity_search",
               max_results: int = 10, include_metadata: bool = False,
               **kwargs) -> Dict[str, Any]:
    """Backward compatible wrapper for graph_query.

    Old API: self.server.tool() decorated method
    New API: QueryGraphTool.execute()
    """
    return _call_tool("graph.query",
                     query=query,
                     query_type=query_type,
                     max_results=max_results,
                     include_metadata=include_metadata,
                     **kwargs)


def graph_analyze(analysis_type: str = "statistics",
                 entity_id: Optional[str] = None,
                 community_level: int = 1, **kwargs) -> Dict[str, Any]:
    """Backward compatible wrapper for graph_analyze.

    Old API: self.server.tool() decorated method
    New API: AnalyzeGraphTool.execute()
    """
    return _call_tool("graph.analyze",
                     analysis_type=analysis_type,
                     entity_id=entity_id,
                     community_level=community_level,
                     **kwargs)


# ============================================================================
# Retrieval Tool Wrappers (1 tool)
# ============================================================================

def retrieval_hybrid(query: str, strategy: str = "hybrid",
                    max_results: int = 10, min_relevance: float = 0.3,
                    context_length: int = 500, **kwargs) -> Dict[str, Any]:
    """Backward compatible wrapper for retrieval_hybrid.

    Old API: self.server.tool() decorated method
    New API: HybridSearchTool.execute()
    """
    return _call_tool("retrieval.hybrid",
                     query=query,
                     strategy=strategy,
                     max_results=max_results,
                     min_relevance=min_relevance,
                     context_length=context_length,
                     **kwargs)


# ============================================================================
# Tool Registration & Discovery
# ============================================================================

def register_all_tools() -> None:
    """Register all modular tools in the global registry.

    This function should be called during MCP server initialization
    to ensure all tools are available for discovery and execution.
    """
    from athena.tools.memory.recall import RecallMemoryTool
    from athena.tools.memory.store import StoreMemoryTool
    from athena.tools.memory.health import HealthCheckTool
    from athena.tools.consolidation.start import StartConsolidationTool
    from athena.tools.consolidation.extract import ExtractPatternsTool
    from athena.tools.planning.verify import VerifyPlanTool
    from athena.tools.planning.simulate import SimulatePlanTool
    from athena.tools.graph.query import QueryGraphTool
    from athena.tools.graph.analyze import AnalyzeGraphTool
    from athena.tools.retrieval.hybrid import HybridSearchTool

    registry = _registry

    # Memory tools
    registry.register("memory.recall", RecallMemoryTool, category="memory")
    registry.register("memory.store", StoreMemoryTool, category="memory")
    registry.register("memory.health", HealthCheckTool, category="memory")

    # Consolidation tools
    registry.register("consolidation.start", StartConsolidationTool, category="consolidation")
    registry.register("consolidation.extract", ExtractPatternsTool, category="consolidation")

    # Planning tools
    registry.register("planning.verify", VerifyPlanTool, category="planning")
    registry.register("planning.simulate", SimulatePlanTool, category="planning")

    # Graph tools
    registry.register("graph.query", QueryGraphTool, category="graph")
    registry.register("graph.analyze", AnalyzeGraphTool, category="graph")

    # Retrieval tools
    registry.register("retrieval.hybrid", HybridSearchTool, category="retrieval")

    logger.info("Registered all 10 modular tools in global registry")


def get_tool_status() -> Dict[str, Any]:
    """Get status of all modular tools.

    Returns:
        Dictionary with registration and availability status
    """
    registry = _registry
    stats = registry.get_stats()

    return {
        "total_tools": stats["total_tools"],
        "total_categories": stats["total_categories"],
        "categories_breakdown": stats.get("categories_breakdown", {}),
        "status": "ready" if stats["total_tools"] >= 10 else "incomplete"
    }
