"""Memory core handler methods for MCP server."""

import json
import logging
from typing import Any, Dict, List, Optional
from mcp.types import TextContent

from .structured_result import StructuredResult, ResultStatus, PaginationMetadata
from .filesystem_api_integration import get_integration
from ..core.models import MemoryType

logger = logging.getLogger(__name__)
integration = get_integration()


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

    async def _handle_get_embedding_model_version(self, args: dict) -> list[TextContent]:
        """Get current embedding model version information.

        This operation returns the version and metadata of the embedding model currently
        in use. Useful for tracking which model generated embeddings and detecting when
        embeddings need to be refreshed due to model changes.

        Returns:
            Model name, version, provider, and metadata
        """
        try:
            from ..core.embeddings import EmbeddingModel

            # Create embedder to get version info
            embedder = EmbeddingModel()

            model_info = embedder.get_model_info()

            response = "📊 Embedding Model Information:\n\n"
            response += f"Version: {model_info['version']}\n"
            response += f"Provider: {model_info['provider']}\n"
            response += f"Backend: {model_info['backend']}\n"
            response += f"Dimension: {model_info['embedding_dim']}D\n\n"

            if model_info['metadata']:
                response += "📋 Raw Metadata:\n"
                for key, value in model_info['metadata'].items():
                    response += f"  {key}: {value}\n"

            response += "\n💡 Use this information to:\n"
            response += "  • Detect when embeddings need refreshing (version changes)\n"
            response += "  • Compare embeddings from different model versions\n"
            response += "  • Track which model generated specific embeddings\n"

            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error getting embedding model version: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_detect_embedding_drift(self, args: dict) -> list[TextContent]:
        """Detect embeddings that are out of sync with current model version.

        Quick Win #4: Identifies embeddings that don't match the current
        embedding model version (e.g., from old model), which may need refreshing.

        Args:
            limit: Maximum memories to scan (default 1000)

        Returns:
            Drift detection report with:
            - Health status (healthy/degraded/critical)
            - Stale memory count
            - Refresh cost estimate
            - Action recommendations
        """
        try:
            from ..memory.search import EmbeddingDriftDetector
            from ..core.embeddings import EmbeddingModel

            project = self.project_manager.get_or_create_project()

            # Create embedder and drift detector
            embedder = EmbeddingModel()
            drift_detector = EmbeddingDriftDetector(self.db, embedder)

            limit = int(args.get("limit", 1000))

            # Get health report
            report = drift_detector.get_embedding_health_report(project.id, limit)

            # Format response
            response = f"📊 Embedding Health Report:\n\n"
            response += f"Status: {report['health_status'].upper()}\n"
            response += f"{report['summary']}\n\n"

            # Drift info
            response += f"📋 Drift Analysis:\n"
            response += f"  Current Version: {report['drift_info'].get('current_version', 'unknown')}\n"
            response += f"  Total Scanned: {report['drift_info'].get('total_scanned', 0)}\n"
            response += f"  Stale Embeddings: {report['drift_info'].get('stale_memories', 0)}\n"
            response += f"  Stale Ratio: {report['drift_info'].get('stale_ratio', 0)*100:.1f}%\n\n"

            # Refresh cost
            cost = report.get('refresh_cost', {})
            if cost.get('stale_memory_count', 0) > 0:
                response += f"⏱️ Refresh Cost:\n"
                response += f"  Time to refresh: {cost.get('total_time_minutes', 0):.1f} minutes\n"
                response += f"  Recommended batch size: {cost.get('recommended_batch_size', 0)}\n"
                if cost.get('notes'):
                    response += f"  Notes:\n"
                    for note in cost['notes']:
                        response += f"    • {note}\n"
                response += "\n"

            # Action plan
            response += f"📋 Action Plan:\n"
            for action in report.get('action_plan', []):
                response += f"  • {action}\n"

            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error detecting embedding drift: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]
