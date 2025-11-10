"""Example patterns for integrating TOON format into MCP handlers.

This module shows best practices for adding TOON serialization to handlers.
Handlers can follow these patterns to enable token-efficient responses.

Example patterns:
1. Serialize search results
2. Serialize knowledge graph queries
3. Serialize procedural memory
4. Serialize system metrics
"""

import json
import logging
from typing import Any, List, Optional

from mcp.types import TextContent

from athena.serialization.integration import TOONIntegrator
from athena.serialization.metrics import get_metrics_collector

logger = logging.getLogger(__name__)


# ============================================================================
# PATTERN 1: Semantic Search Results Handler
# ============================================================================


async def handle_semantic_search_with_toon(
    server: Any,
    query: str,
    limit: int = 10,
) -> List[TextContent]:
    """Example handler: Semantic search with TOON encoding.

    Shows how to wrap search results for token efficiency.

    Args:
        server: MCP server instance
        query: Search query
        limit: Result limit

    Returns:
        TextContent with TOON or JSON-encoded results
    """
    try:
        # Perform search (existing logic)
        if not hasattr(server, "_rag_manager"):
            from ..rag.manager import RAGManager

            server._rag_manager = RAGManager(server.store.db)

        results = server._rag_manager.retrieve(query=query, limit=limit, strategy="auto")

        # Convert to response format
        result_dicts = [
            {
                "rank": i + 1,
                "score": r.get("relevance_score", 0.0),
                "id": r.get("id", i),
                "text_preview": r.get("text", "")[:100],
                "source_type": r.get("source_type", "memory"),
                "timestamp": r.get("timestamp", ""),
            }
            for i, r in enumerate(results) if results
        ]

        # Use TOON integration to serialize
        response_text = TOONIntegrator.serialize_search_results(
            result_dicts,
            limit=limit,
        )

        return [TextContent(type="text", text=response_text)]

    except Exception as e:
        logger.error(f"Error in semantic search: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ============================================================================
# PATTERN 2: Knowledge Graph Entities Handler
# ============================================================================


async def handle_graph_entities_with_toon(
    server: Any,
    entity_filter: Optional[str] = None,
    limit: int = 20,
) -> List[TextContent]:
    """Example handler: Knowledge graph entities with TOON encoding.

    Shows how to serialize entity batch queries.

    Args:
        server: MCP server instance
        entity_filter: Optional filter for entity type
        limit: Result limit

    Returns:
        TextContent with TOON or JSON-encoded entities
    """
    try:
        # Initialize graph store
        if not hasattr(server, "_graph_store"):
            from ..graph.store import KnowledgeGraphStore

            server._graph_store = KnowledgeGraphStore(server.store.db)

        # Query entities
        entities = server._graph_store.list_entities(limit=limit)

        # Filter if needed
        if entity_filter:
            entities = [e for e in entities if e.get("type") == entity_filter]

        # Format for response
        entity_dicts = [
            {
                "id": e.get("id", 0),
                "type": e.get("type", "unknown"),
                "name": e.get("name", ""),
                "domain": e.get("domain", "general"),
                "salience": e.get("salience", 0.5),
                "community_id": e.get("community_id"),
            }
            for e in entities
        ]

        # Serialize with TOON
        response_text = TOONIntegrator.serialize_knowledge_graph_entities(
            entity_dicts,
        )

        return [TextContent(type="text", text=response_text)]

    except Exception as e:
        logger.error(f"Error in graph entities: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ============================================================================
# PATTERN 3: Procedural Memory Handler
# ============================================================================


async def handle_procedures_with_toon(
    server: Any,
    category: Optional[str] = None,
    limit: int = 50,
) -> List[TextContent]:
    """Example handler: Procedural memory with TOON encoding.

    Shows how to serialize procedure listings.

    Args:
        server: MCP server instance
        category: Optional category filter
        limit: Result limit

    Returns:
        TextContent with TOON or JSON-encoded procedures
    """
    try:
        # Initialize procedural store
        if not hasattr(server, "_procedural_store"):
            from ..procedural.store import ProcedureStore

            server._procedural_store = ProcedureStore(server.store.db)

        # Query procedures
        procedures = server._procedural_store.list_procedures(limit=limit)

        # Filter if needed
        if category:
            procedures = [p for p in procedures if p.get("category") == category]

        # Format for response
        procedure_dicts = [
            {
                "id": p.get("id", 0),
                "name": p.get("name", ""),
                "category": p.get("category", "general"),
                "steps_count": p.get("steps_count", 0),
                "effectiveness_score": p.get("effectiveness_score", 0.5),
                "uses_count": p.get("uses_count", 0),
                "last_used": p.get("last_used", ""),
            }
            for p in procedures
        ]

        # Serialize with TOON
        response_text = TOONIntegrator.serialize_procedures(procedure_dicts)

        return [TextContent(type="text", text=response_text)]

    except Exception as e:
        logger.error(f"Error in procedures: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ============================================================================
# PATTERN 4: System Metrics/Health Handler
# ============================================================================


async def handle_health_with_toon(
    server: Any,
) -> List[TextContent]:
    """Example handler: System health metrics with TOON encoding.

    Shows how to serialize system metrics.

    Args:
        server: MCP server instance

    Returns:
        TextContent with TOON or JSON-encoded metrics
    """
    try:
        # Gather metrics (simplified example)
        metrics = {
            "layers": [
                {
                    "layer_name": "episodic",
                    "event_count": 8128,
                    "quality_score": 0.87,
                    "compression_ratio": 0.92,
                },
                {
                    "layer_name": "semantic",
                    "event_count": 3456,
                    "quality_score": 0.91,
                    "compression_ratio": 0.88,
                },
                {
                    "layer_name": "procedural",
                    "event_count": 101,
                    "quality_score": 0.79,
                    "compression_ratio": 0.95,
                },
            ]
        }

        # Serialize with TOON
        response_text = TOONIntegrator.serialize_metrics(metrics)

        return [TextContent(type="text", text=response_text)]

    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ============================================================================
# PATTERN 5: Generic Batch Data Handler
# ============================================================================


async def handle_batch_data_with_toon(
    server: Any,
    data_type: str,
    data_items: list,
) -> List[TextContent]:
    """Generic pattern for batching any data with TOON.

    Shows how to use TOONIntegrator for custom data types.

    Args:
        server: MCP server instance
        data_type: Type of data (for schema mapping)
        data_items: List of data items to serialize

    Returns:
        TextContent with TOON or JSON-encoded data
    """
    try:
        # Wrap in container
        data = {f"{data_type}": data_items, "count": len(data_items)}

        # Serialize with schema hint
        response_text = TOONIntegrator.serialize(
            data,
            schema_name=data_type,
        )

        return [TextContent(type="text", text=response_text)]

    except Exception as e:
        logger.error(f"Error in batch data handler: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ============================================================================
# METRICS REPORTING
# ============================================================================


async def handle_toon_metrics_report(
    server: Any,
) -> List[TextContent]:
    """Handler to report TOON serialization metrics.

    Returns a performance report on TOON encoding.

    Args:
        server: MCP server instance

    Returns:
        TextContent with metrics report
    """
    try:
        collector = get_metrics_collector()
        report = collector.get_performance_report()

        return [TextContent(type="text", text=report)]

    except Exception as e:
        logger.error(f"Error generating metrics report: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ============================================================================
# FORMAT STATUS HANDLER
# ============================================================================


async def handle_toon_format_status(
    server: Any,
) -> List[TextContent]:
    """Handler to report TOON format configuration status.

    Returns the current TOON format configuration and availability.

    Args:
        server: MCP server instance

    Returns:
        TextContent with format status
    """
    try:
        info = TOONIntegrator.get_format_info()

        status_text = """**TOON Format Status**

Configuration:
"""
        for key, value in info.items():
            status_text += f"  {key}: {value}\n"

        return [TextContent(type="text", text=status_text)]

    except Exception as e:
        logger.error(f"Error getting format status: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ============================================================================
# INTEGRATION GUIDE
# ============================================================================
"""
To integrate TOON into existing handlers, follow these steps:

1. Import TOONIntegrator:
   from athena.serialization.integration import TOONIntegrator

2. Replace JSON serialization:
   OLD:
       response_text = json.dumps(results)
       return [TextContent(type="text", text=response_text)]

   NEW:
       response_text = TOONIntegrator.serialize_search_results(results)
       return [TextContent(type="text", text=response_text)]

3. For custom data types, use the generic method:
   response_text = TOONIntegrator.serialize(
       data,
       schema_name="your_schema_name"
   )

4. Enable TOON via environment:
   export ENABLE_TOON_FORMAT=true

5. Monitor performance:
   from athena.serialization.metrics import get_metrics_collector
   collector = get_metrics_collector()
   print(collector.get_performance_report())

Key Benefits:
  - Automatic format selection (TOON vs JSON)
  - Transparent fallback to JSON on error
  - Metrics collection for monitoring
  - No changes to handler logic, only serialization
  - Token savings: 30-60% on typical queries
"""
