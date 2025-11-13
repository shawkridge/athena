"""Memory core handler methods for MCP server."""

import json
import logging
from typing import Any, Dict, List, Optional
from mcp.types import TextContent

from .structured_result import StructuredResult, ResultStatus, PaginationMetadata
from ..core.models import MemoryType

logger = logging.getLogger(__name__)


class MemoryCoreHandlersMixin:
    """Memory core handler methods (6 methods, ~240 lines).

    Extracted from monolithic handlers.py as part of Phase 2 refactoring.
    Provides core memory CRUD operations: remember, recall, forget, list,
    optimize, and cross-project search.

    Methods:
    - _handle_remember: Store a new memory with metadata and tags
    - _handle_recall: Retrieve memories by semantic search with reranking
    - _handle_forget: Delete a memory by ID
    - _handle_list_memories: List all memories with optional filters
    - _handle_optimize: Optimize memory storage (prune low-value items)
    - _handle_search_projects: Search across all projects
    """

    async def _handle_remember(self, args: dict) -> list[TextContent]:
        """Handle remember tool call.

        Store a new memory with content, metadata, memory type, and tags.
        Associates memory with current project.

        Args:
            args: Dictionary with keys:
                - content (str): Memory content
                - memory_type (str): Type of memory (FACT, PATTERN, DECISION, etc.)
                - tags (list, optional): Tags for categorization

        Returns:
            List containing TextContent with operation result
        """
        try:
            project = await self.project_manager.get_or_create_project()

            memory_id = await self.store.remember(
                content=args["content"],
                memory_type=MemoryType(args["memory_type"]),
                project_id=project.id,
                tags=args.get("tags", []),
            )

            result = StructuredResult.success(
                data={"memory_id": memory_id, "project_name": project.name},
                metadata={
                    "operation": "remember",
                    "memory_type": args["memory_type"],
                    "project_id": project.id,
                },
            )
        except Exception as e:
            logger.error(f"Error in _handle_remember: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "remember"})

        return [result.as_text_content()]

    async def _handle_recall(self, args: dict) -> list[TextContent]:
        """Handle recall tool call.

        Retrieve memories by semantic search with optional reranking.
        Returns formatted results with similarity scores.

        Args:
            args: Dictionary with keys:
                - query (str): Search query
                - k (int, optional): Number of results (default 5, max 100)
                - memory_types (list, optional): Filter by memory types

        Returns:
            List containing optimized TextContent with semantic_search schema
        """
        try:
            project = await self.project_manager.require_project()

            memory_types = None
            if "memory_types" in args and args["memory_types"]:
                memory_types = [MemoryType(mt) for mt in args["memory_types"]]

            k = min(int(args.get("k", 5)), 100)
            results = self.store.recall_with_reranking(
                query=args["query"], project_id=project.id, k=k
            )

            # Format results for response
            formatted_results = []
            for result in results:
                memory_type = result.memory.memory_type if isinstance(result.memory.memory_type, str) else result.memory.memory_type.value
                formatted_results.append({
                    "memory_id": result.memory.id,
                    "type": memory_type,
                    "similarity": round(result.similarity, 2),
                    "content": result.memory.content,
                    "tags": result.memory.tags or [],
                })

            result = StructuredResult.success(
                data=formatted_results,
                metadata={
                    "operation": "recall",
                    "query": args["query"],
                    "project_id": project.id,
                    "schema": "semantic_search",  # TOON hint
                },
                pagination=PaginationMetadata(
                    returned=len(formatted_results),
                    limit=k,
                    has_more=len(formatted_results) == k,
                ),
            )
        except Exception as e:
            logger.error(f"Error in _handle_recall: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "recall"})

        # Use TOON optimization for recall results (40-60% token savings)
        return [result.as_optimized_content(schema_name="semantic_search")]

    async def _handle_forget(self, args: dict) -> list[TextContent]:
        """Handle forget tool call.

        Delete a specific memory by ID. Also supports query-based deletion
        (though currently returns error asking for memory ID).

        Args:
            args: Dictionary with keys:
                - memory_id (str, optional): ID of memory to delete
                - query (str, optional): Query for deletion (not yet supported)

        Returns:
            List containing TextContent with operation result
        """
        try:
            memory_id = args.get("memory_id")
            query = args.get("query")

            if not memory_id and not query:
                result = StructuredResult.error(
                    "Must provide either 'memory_id' or 'query' parameter",
                    metadata={"operation": "forget"}
                )
            elif memory_id:
                # Delete specific memory by ID
                deleted = self.store.forget(memory_id)
                if deleted:
                    result = StructuredResult.success(
                        data={"deleted_id": memory_id},
                        metadata={"operation": "forget"}
                    )
                else:
                    result = StructuredResult.error(
                        f"Memory {memory_id} not found",
                        metadata={"operation": "forget"}
                    )
            else:
                # If no memory_id provided, just return error asking for ID
                result = StructuredResult.error(
                    "Query-based forget not supported. Please provide 'memory_id' parameter",
                    metadata={"operation": "forget"}
                )
        except Exception as e:
            logger.error(f"Error in _handle_forget: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "forget"})

        return [result.as_text_content()]

    async def _handle_list_memories(self, args: dict) -> list[TextContent]:
        """Handle list_memories tool call.

        List all memories for current project with optional filtering
        and sorting. Supports pagination.

        Args:
            args: Dictionary with keys:
                - limit (int, optional): Number of results (default 20)
                - sort_by (str, optional): Sort field - 'useful' (default), 'recent', etc.

        Returns:
            List containing optimized TextContent with memory schema
        """
        try:
            project = await self.project_manager.require_project()
            limit = args.get("limit", 20)
            sort_by = args.get("sort_by", "useful")

            memories = self.store.list_memories(
                project_id=project.id, limit=limit, sort_by=sort_by
            )

            if not memories:
                result = StructuredResult.success(
                    data=[],
                    metadata={
                        "operation": "list_memories",
                        "schema": "memory",
                        "sort_by": sort_by,
                    }
                )
            else:
                # Format memories for structured response
                formatted_memories = []
                for memory in memories:
                    memory_type = memory.memory_type if isinstance(memory.memory_type, str) else memory.memory_type.value
                    formatted_memories.append({
                        "id": memory.id,
                        "type": memory_type,
                        "content": memory.content[:100],
                        "usefulness_score": round(memory.usefulness_score, 2),
                        "tags": memory.tags or [],
                    })

                result = StructuredResult.success(
                    data=formatted_memories,
                    metadata={
                        "operation": "list_memories",
                        "schema": "memory",
                        "project": project.name,
                        "sort_by": sort_by,
                        "count": len(formatted_memories),
                    },
                    pagination=PaginationMetadata(
                        returned=len(formatted_memories),
                        limit=limit,
                    )
                )
        except Exception as e:
            logger.error(f"Error in _handle_list_memories: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "list_memories"})

        return [result.as_optimized_content(schema_name="memory")]

    async def _handle_optimize(self, args: dict) -> list[TextContent]:
        """Handle optimize tool call.

        Optimize memory storage by removing low-value memories and
        consolidating space. Can run in dry-run mode to simulate.

        Args:
            args: Dictionary with keys:
                - dry_run (bool, optional): If True, simulate without modifying

        Returns:
            List containing TextContent with optimization statistics
        """
        try:
            project = await self.project_manager.require_project()

            stats = self.store.optimize(project_id=project.id, dry_run=args.get("dry_run", False))

            response = f"Optimization {'simulation' if stats['dry_run'] else 'complete'}:\n"
            response += f"  Before: {stats['before_count']} memories (avg score: {stats['avg_score_before']})\n"
            response += f"  After:  {stats['after_count']} memories (avg score: {stats['avg_score_after']})\n"
            response += f"  Pruned: {stats['pruned']} low-value memories\n"

            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error in _handle_optimize: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Optimization failed: {str(e)}")]

    async def _handle_search_projects(self, args: dict) -> list[TextContent]:
        """Handle search_projects tool call.

        Search across all projects in memory system. Useful for finding
        related memories from other projects or cross-project analysis.

        Args:
            args: Dictionary with keys:
                - query (str): Search query
                - k (int, optional): Number of results (default 5, max 100)
                - exclude_current (bool, optional): Exclude current project

        Returns:
            List containing optimized TextContent with semantic_search schema
        """
        try:
            k = min(int(args.get("k", 5)), 100)
            exclude_id = None
            if args.get("exclude_current", False):
                current = self.project_manager.detect_current_project()
                if current:
                    exclude_id = current.id

            results = self.store.search_across_projects(
                query=args["query"], exclude_project_id=exclude_id, k=k
            )

            if not results:
                result = StructuredResult.success(
                    data=[],
                    metadata={
                        "operation": "search_projects",
                        "schema": "semantic_search",
                        "query": args["query"],
                        "exclude_current": args.get("exclude_current", False),
                    },
                    pagination=PaginationMetadata(
                        returned=0,
                        limit=k,
                    )
                )
            else:
                # Format results for structured response
                formatted_results = []
                for search_result in results:
                    # Get project info
                    cursor = self.store.db.conn.cursor()
                    cursor.execute("SELECT name FROM projects WHERE id = ?", (search_result.memory.project_id,))
                    row = cursor.fetchone()
                    project_name = row[0] if row else "Unknown"

                    # memory_type is already a string due to use_enum_values = True
                    memory_type = search_result.memory.memory_type if isinstance(search_result.memory.memory_type, str) else search_result.memory.memory_type.value

                    formatted_results.append({
                        "project": project_name,
                        "memory_type": memory_type.upper(),
                        "content": search_result.memory.content[:200],
                        "usefulness_score": round(search_result.memory.usefulness_score, 2) if hasattr(search_result.memory, 'usefulness_score') else 0.0,
                    })

                result = StructuredResult.success(
                    data=formatted_results,
                    metadata={
                        "operation": "search_projects",
                        "schema": "semantic_search",
                        "query": args["query"],
                        "exclude_current": args.get("exclude_current", False),
                        "count": len(formatted_results),
                    },
                    pagination=PaginationMetadata(
                        returned=len(formatted_results),
                        limit=k,
                    )
                )
        except Exception as e:
            logger.error(f"Error in _handle_search_projects: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "search_projects"})

        return [result.as_optimized_content(schema_name="semantic_search")]
