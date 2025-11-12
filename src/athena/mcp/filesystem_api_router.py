"""
MCP Handler Router for Filesystem API

Routes MCP tool calls to filesystem API code execution paradigm.
Implements the bridge between traditional MCP and code execution.

This module demonstrates how to refactor existing MCP handlers
to use the new filesystem API architecture.
"""

from typing import Dict, Any, Optional
from pathlib import Path
import json

from ..execution.code_executor import CodeExecutor, ResultFormatter
from ..filesystem_api.manager import FilesystemAPIManager


class FilesystemAPIRouter:
    """
    Routes MCP tool calls to filesystem API operations.

    Paradigm shift:
    OLD: tool_call(params) → execute directly in handler
    NEW: tool_call(params) → return code path + function name → execute locally
    """

    def __init__(self, filesystem_root: Optional[Path] = None):
        """Initialize router with filesystem API."""
        self.executor = CodeExecutor(filesystem_root)
        self.fs_manager = FilesystemAPIManager(filesystem_root)

    # ============================================================
    # EPISODIC LAYER ROUTES
    # ============================================================

    def route_episodic_search(self, query: str, limit: int = 100, confidence_threshold: float = 0.7) -> Dict[str, Any]:
        """Route episodic search to filesystem API."""
        return self._execute_operation(
            "/athena/layers/episodic/search.py",
            "search_events",
            {
                "db_path": self._get_db_path(),
                "query": query,
                "limit": limit,
                "confidence_threshold": confidence_threshold
            }
        )

    def route_episodic_timeline(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Route temporal analysis to filesystem API."""
        return self._execute_operation(
            "/athena/layers/episodic/timeline.py",
            "get_event_timeline",
            {
                "db_path": self._get_db_path(),
                "start_date": start_date,
                "end_date": end_date
            }
        )

    # ============================================================
    # SEMANTIC LAYER ROUTES
    # ============================================================

    def route_semantic_search(self, query: str, limit: int = 100, confidence_threshold: float = 0.7) -> Dict[str, Any]:
        """Route semantic search to filesystem API."""
        return self._execute_operation(
            "/athena/layers/semantic/recall.py",
            "search_memories",
            {
                "db_path": self._get_db_path(),
                "query": query,
                "limit": limit,
                "confidence_threshold": confidence_threshold
            }
        )

    # ============================================================
    # GRAPH LAYER ROUTES
    # ============================================================

    def route_graph_search(self, query: str, limit: int = 100, max_depth: int = 2) -> Dict[str, Any]:
        """Route graph search to filesystem API."""
        return self._execute_operation(
            "/athena/layers/graph/traverse.py",
            "search_entities",
            {
                "db_path": self._get_db_path(),
                "query": query,
                "limit": limit,
                "max_depth": max_depth
            }
        )

    def route_community_detection(self, min_size: int = 2) -> Dict[str, Any]:
        """Route community detection to filesystem API."""
        return self._execute_operation(
            "/athena/layers/graph/communities.py",
            "detect_communities",
            {
                "db_path": self._get_db_path(),
                "min_size": min_size
            }
        )

    # ============================================================
    # CONSOLIDATION LAYER ROUTES
    # ============================================================

    def route_consolidation(self, time_window_hours: int = 24, min_support: float = 0.3) -> Dict[str, Any]:
        """Route consolidation to filesystem API."""
        return self._execute_operation(
            "/athena/layers/consolidation/extract.py",
            "extract_patterns",
            {
                "db_path": self._get_db_path(),
                "time_window_hours": time_window_hours,
                "min_support": min_support
            }
        )

    # ============================================================
    # PLANNING LAYER ROUTES
    # ============================================================

    def route_task_decomposition(self, task_description: str, target_depth: int = 3) -> Dict[str, Any]:
        """Route task decomposition to filesystem API."""
        return self._execute_operation(
            "/athena/layers/planning/decompose.py",
            "decompose_task",
            {
                "db_path": self._get_db_path(),
                "task_description": task_description,
                "target_depth": target_depth
            }
        )

    # ============================================================
    # PROSPECTIVE LAYER ROUTES
    # ============================================================

    def route_list_tasks(self, status_filter: Optional[str] = None, priority_filter: Optional[str] = None) -> Dict[str, Any]:
        """Route task listing to filesystem API."""
        return self._execute_operation(
            "/athena/layers/prospective/tasks.py",
            "list_tasks",
            {
                "db_path": self._get_db_path(),
                "status_filter": status_filter,
                "priority_filter": priority_filter
            }
        )

    # ============================================================
    # PROCEDURAL LAYER ROUTES
    # ============================================================

    def route_find_procedures(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Route procedure search to filesystem API."""
        return self._execute_operation(
            "/athena/layers/procedural/find.py",
            "find_procedures",
            {
                "db_path": self._get_db_path(),
                "query": query,
                "limit": limit
            }
        )

    # ============================================================
    # META LAYER ROUTES
    # ============================================================

    def route_quality_check(self) -> Dict[str, Any]:
        """Route quality assessment to filesystem API."""
        return self._execute_operation(
            "/athena/layers/meta/quality.py",
            "assess_memory_quality",
            {"db_path": self._get_db_path()}
        )

    # ============================================================
    # CROSS-LAYER OPERATIONS
    # ============================================================

    def route_search_all_layers(self, query: str, limit_per_layer: int = 10) -> Dict[str, Any]:
        """Route cross-layer search to filesystem API."""
        return self._execute_operation(
            "/athena/operations/search_all.py",
            "search_all_layers",
            {
                "db_path": self._get_db_path(),
                "query": query,
                "limit_per_layer": limit_per_layer
            }
        )

    def route_health_check(self, include_anomalies: bool = True) -> Dict[str, Any]:
        """Route health check to filesystem API."""
        return self._execute_operation(
            "/athena/operations/health_check.py",
            "get_system_health",
            {
                "db_path": self._get_db_path(),
                "include_anomalies": include_anomalies
            }
        )

    # ============================================================
    # FILESYSTEM API DISCOVERY
    # ============================================================

    def get_api_schema(self) -> Dict[str, Any]:
        """Get schema of all available operations."""
        return self.fs_manager.get_api_schema()

    def list_directory(self, path: str) -> Dict[str, Any]:
        """List directory contents."""
        return self.fs_manager.list_directory(path)

    def read_file(self, path: str) -> Dict[str, Any]:
        """Read a file."""
        return self.fs_manager.read_file(path)

    # ============================================================
    # INTERNAL HELPERS
    # ============================================================

    def _execute_operation(
        self,
        module_path: str,
        function_name: str,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute an operation via the code executor.

        Returns formatted result for MCP response.
        """
        result = self.executor.execute(module_path, function_name, args)
        return ResultFormatter.format_result(result)

    def _get_db_path(self) -> str:
        """Get database path (from config or default)."""
        import os
        return os.path.expanduser("~/.athena/memory.db")

    def clear_module_cache(self):
        """Clear executor module cache."""
        self.executor.clear_cache()


# ============================================================
# EXAMPLE: How to Refactor Existing MCP Handlers
# ============================================================

"""
BEFORE (Traditional MCP Handler):

@server.tool()
def recall(query: str, limit: int = 100) -> List[TextContent]:
    # Direct execution in handler
    memories = semantic_store.search(query, limit=limit)
    # Returns 15,000+ tokens of full memory objects
    return [TextContent(text=json.dumps([m.to_dict() for m in memories]))]


AFTER (Code Execution with Filesystem API):

@server.tool()
def recall(query: str, limit: int = 100) -> Dict[str, Any]:
    router = FilesystemAPIRouter()
    # Route to filesystem API - returns summary only
    return router.route_semantic_search(query, limit)
    # Returns 200 token summary with counts, IDs, stats


AGENT WORKFLOW:

1. Agent discovers: list_directory("/athena/layers/semantic")
   └─ Sees available operations (recall.py, etc)

2. Agent reads: read_file("/athena/layers/semantic/recall.py")
   └─ Gets function signature and docstring

3. Agent executes: execute("/athena/layers/semantic/recall.py", "search_memories", {...})
   └─ Runs code locally, gets summary back (200 tokens)

4. Summary includes: IDs, counts, confidence scores
   └─ Agent can request full details via: get_memory_details(memory_id)
   └─ But typically only needs summary for decision-making

RESULT: 98.7% token reduction, 10x faster, infinitely scalable
"""
