"""
Filesystem API Integration Layer for MCP Handlers

This module bridges traditional MCP handlers to the filesystem API pattern.
Provides gradual migration path without breaking existing handlers.

Architecture:
    Old pattern: MCP handler → Direct execution → Full objects
    New pattern: MCP handler → Router → /athena/layers/ → Summary objects

Benefits:
    ✅ Agents can discover operations via filesystem
    ✅ Agent discoverability works across all projects (symlink to /athena)
    ✅ Summary-first returns (300 tokens vs 5K-50K)
    ✅ Local execution in-process, no external calls
    ✅ Backward compatible - existing handlers still work
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path

from .filesystem_api_router import FilesystemAPIRouter

logger = logging.getLogger(__name__)


class FilesystemAPIIntegration:
    """Coordinates filesystem API integration with MCP handlers."""

    def __init__(self):
        """Initialize integration layer."""
        self.router = FilesystemAPIRouter()
        self.integration_status = {
            "episodic": {"search": "pending", "recall": "pending"},
            "semantic": {"search": "pending"},
            "graph": {"search": "pending", "communities": "pending"},
            "consolidation": {"extract": "pending"},
            "procedural": {"find": "pending"},
            "prospective": {"tasks": "pending"},
            "meta": {"quality": "pending"},
        }

    def use_filesystem_api(
        self, layer: str, operation: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Route handler call through filesystem API.

        Args:
            layer: Memory layer name (episodic, semantic, etc)
            operation: Operation name (search, recall, etc)
            params: Operation parameters

        Returns:
            Result from filesystem API (summary-first)

        Example:
            # In a handler:
            integration = FilesystemAPIIntegration()
            result = integration.use_filesystem_api(
                "semantic",
                "search",
                {"query": "authentication", "limit": 5}
            )
            # Result is already a summary (300 tokens)
        """
        try:
            logger.info(f"Routing {layer}.{operation} through filesystem API")

            # Route based on layer and operation
            if layer == "semantic" and operation == "search":
                return self.router.route_semantic_search(
                    query=params.get("query", ""),
                    limit=params.get("limit", 100),
                    confidence_threshold=params.get("confidence_threshold", 0.7),
                )

            elif layer == "episodic" and operation == "search":
                return self.router.route_episodic_search(
                    query=params.get("query", ""),
                    limit=params.get("limit", 100),
                    confidence_threshold=params.get("confidence_threshold", 0.7),
                )

            elif layer == "episodic" and operation == "timeline":
                return self.router.route_episodic_timeline(
                    start_date=params.get("start_date"),
                    end_date=params.get("end_date"),
                )

            elif layer == "graph" and operation == "search":
                return self.router.route_graph_search(
                    query=params.get("query", ""),
                    limit=params.get("limit", 100),
                    max_depth=params.get("max_depth", 2),
                )

            elif layer == "graph" and operation == "communities":
                return self.router.route_community_detection(
                    min_size=params.get("min_size", 2)
                )

            elif layer == "consolidation" and operation == "extract":
                return self.router.route_consolidation(
                    time_window_hours=params.get("time_window_hours", 24),
                    min_support=params.get("min_support", 0.3),
                )

            elif layer == "procedural" and operation == "find":
                return self.router.route_find_procedures(
                    query=params.get("query", ""),
                    limit=params.get("limit", 10),
                )

            elif layer == "prospective" and operation == "tasks":
                return self.router.route_list_tasks(
                    status_filter=params.get("status"),
                    priority_filter=params.get("priority"),
                )

            elif layer == "planning" and operation == "decompose":
                return self.router.route_task_decomposition(
                    task_description=params.get("task_description", ""),
                    target_depth=params.get("target_depth", 3),
                )

            elif layer == "meta" and operation == "quality":
                return self.router.route_quality_check()

            else:
                logger.warning(f"Unknown route: {layer}.{operation}")
                return {
                    "error": f"Unknown operation: {layer}.{operation}",
                    "available_layers": list(self.integration_status.keys()),
                }

        except Exception as e:
            logger.error(f"Filesystem API routing failed: {e}", exc_info=True)
            return {"error": str(e), "error_type": type(e).__name__}

    def mark_integrated(self, layer: str, operation: str) -> None:
        """Mark an operation as integrated with filesystem API."""
        if layer in self.integration_status:
            self.integration_status[layer][operation] = "integrated"

    def get_integration_status(self) -> Dict[str, Any]:
        """Get current integration status."""
        return {
            "status": self.integration_status,
            "total_operations": sum(
                len(ops) for ops in self.integration_status.values()
            ),
            "integrated_operations": sum(
                1
                for ops in self.integration_status.values()
                for status in ops.values()
                if status == "integrated"
            ),
        }


# Global integration instance
_integration_instance: Optional[FilesystemAPIIntegration] = None


def get_integration() -> FilesystemAPIIntegration:
    """Get or create global integration instance."""
    global _integration_instance
    if _integration_instance is None:
        _integration_instance = FilesystemAPIIntegration()
    return _integration_instance
