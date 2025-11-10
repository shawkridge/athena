"""Core memory tools (recall, remember, forget, optimize)."""

import logging
from typing import Optional, List
from .base import BaseTool, ToolMetadata, ToolResult, ToolStatus
from ..rate_limiter import MCPRateLimiter

logger = logging.getLogger(__name__)


class RecallTool(BaseTool):
    """Search and retrieve memories using semantic search."""

    def __init__(self, memory_store, project_manager):
        """Initialize recall tool.

        Args:
            memory_store: MemoryStore instance for database access
            project_manager: ProjectManager instance for project context
        """
        metadata = ToolMetadata(
            name="recall",
            description="Search and retrieve relevant memories using semantic similarity",
            category="memory",
            version="1.0",
            parameters={
                "query": {
                    "type": "string",
                    "description": "Search query to find relevant memories"
                },
                "k": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5)",
                    "default": 5
                },
                "memory_types": {
                    "type": "array",
                    "description": "Filter by memory types (optional)",
                    "default": None
                }
            },
            returns={
                "memories": {
                    "type": "array",
                    "description": "List of relevant memories with similarity scores"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of memories found"
                }
            },
            tags=["search", "query", "semantic"]
        )
        super().__init__(metadata)
        self.memory_store = memory_store
        self.project_manager = project_manager

    async def execute(self, **params) -> ToolResult:
        """Execute recall operation.

        Args:
            query: Search query string (required)
            k: Number of results (optional, default 5)
            memory_types: Filter by memory types (optional)

        Returns:
            ToolResult with memories and metadata
        """
        try:
            # Validate required parameters
            error = self.validate_params(params, ["query"])
            if error:
                return ToolResult.error(error)

            query = params["query"]
            k = params.get("k", 5)

            # Get current project
            try:
                project = self.project_manager.require_project()
                project_id = project.id
            except Exception as e:
                return ToolResult.error(f"Project error: {str(e)}")

            # Parse memory types filter if provided
            memory_types = None
            if params.get("memory_types"):
                try:
                    from athena.core.models import MemoryType
                    memory_types = [MemoryType(mt) for mt in params["memory_types"]]
                except Exception as e:
                    self.logger.warning(f"Invalid memory_types: {e}")

            # Perform semantic search
            try:
                results = self.memory_store.recall_with_reranking(
                    query=query,
                    project_id=project_id,
                    k=k
                )
            except Exception as e:
                self.logger.error(f"Search failed: {e}")
                return ToolResult.error(f"Search failed: {str(e)}")

            # Format results
            if not results:
                return ToolResult.success(
                    data={
                        "memories": [],
                        "count": 0,
                        "message": "No relevant memories found."
                    },
                    message="No memories found for query"
                )

            # Convert results to dictionary format
            memories_data = []
            for result in results:
                memory_type = (
                    result.memory.memory_type
                    if isinstance(result.memory.memory_type, str)
                    else result.memory.memory_type.value
                )
                memories_data.append({
                    "id": result.memory.id,
                    "type": memory_type,
                    "content": result.memory.content,
                    "similarity": round(result.similarity, 3),
                    "tags": result.memory.tags or [],
                    "created_at": result.memory.created_at.isoformat() if hasattr(result.memory, 'created_at') else None
                })

            result_data = {
                "memories": memories_data,
                "count": len(memories_data),
                "query": query
            }

            self.log_execution(params, ToolResult.success(data=result_data))
            return ToolResult.success(
                data=result_data,
                message=f"Found {len(memories_data)} relevant memories"
            )

        except Exception as e:
            self.logger.exception(f"Unexpected error in recall: {e}")
            return ToolResult.error(f"Unexpected error: {str(e)}")


class RememberTool(BaseTool):
    """Store and remember new memories."""

    def __init__(self, memory_store, project_manager):
        """Initialize remember tool.

        Args:
            memory_store: MemoryStore instance for database access
            project_manager: ProjectManager instance for project context
        """
        metadata = ToolMetadata(
            name="remember",
            description="Store and remember new memories with optional tags and metadata",
            category="memory",
            version="1.0",
            parameters={
                "content": {
                    "type": "string",
                    "description": "Memory content to store"
                },
                "memory_type": {
                    "type": "string",
                    "description": "Type of memory (e.g., 'semantic', 'episodic')",
                    "default": "semantic"
                },
                "tags": {
                    "type": "array",
                    "description": "Tags for categorizing the memory",
                    "default": []
                },
                "metadata": {
                    "type": "object",
                    "description": "Additional metadata",
                    "default": {}
                }
            },
            returns={
                "memory_id": {
                    "type": "integer",
                    "description": "ID of the stored memory"
                },
                "message": {
                    "type": "string",
                    "description": "Confirmation message"
                }
            },
            tags=["store", "create", "write"]
        )
        super().__init__(metadata)
        self.memory_store = memory_store
        self.project_manager = project_manager

    async def execute(self, **params) -> ToolResult:
        """Execute remember operation.

        Args:
            content: Memory content to store (required)
            memory_type: Type of memory (optional, default 'semantic')
            tags: Tags for memory (optional)
            metadata: Additional metadata (optional)

        Returns:
            ToolResult with memory_id
        """
        try:
            # Validate required parameters
            error = self.validate_params(params, ["content"])
            if error:
                return ToolResult.error(error)

            # Get current project
            try:
                project = self.project_manager.require_project()
                project_id = project.id
            except Exception as e:
                return ToolResult.error(f"Project error: {str(e)}")

            # Prepare memory data
            memory_data = {
                "content": params["content"],
                "project_id": project_id,
                "memory_type": params.get("memory_type", "semantic"),
                "tags": params.get("tags", []),
            }

            # Store memory
            try:
                memory_id = self.memory_store.store_memory(
                    content=memory_data["content"],
                    project_id=project_id,
                    memory_type=memory_data["memory_type"],
                    tags=memory_data.get("tags", [])
                )
            except Exception as e:
                self.logger.error(f"Storage failed: {e}")
                return ToolResult.error(f"Storage failed: {str(e)}")

            result_data = {
                "memory_id": memory_id,
                "content": memory_data["content"],
                "memory_type": memory_data["memory_type"],
                "project_id": project_id
            }

            self.log_execution(params, ToolResult.success(data=result_data))
            return ToolResult.success(
                data=result_data,
                message=f"Memory stored successfully (ID: {memory_id})"
            )

        except Exception as e:
            self.logger.exception(f"Unexpected error in remember: {e}")
            return ToolResult.error(f"Unexpected error: {str(e)}")


class ForgetTool(BaseTool):
    """Delete and forget memories."""

    def __init__(self, memory_store, project_manager):
        """Initialize forget tool.

        Args:
            memory_store: MemoryStore instance for database access
            project_manager: ProjectManager instance for project context
        """
        metadata = ToolMetadata(
            name="forget",
            description="Delete and forget memories by ID or query",
            category="memory",
            version="1.0",
            parameters={
                "memory_id": {
                    "type": "integer",
                    "description": "ID of memory to delete",
                    "default": None
                },
                "query": {
                    "type": "string",
                    "description": "Query to find memories to delete",
                    "default": None
                }
            },
            returns={
                "deleted_count": {
                    "type": "integer",
                    "description": "Number of memories deleted"
                },
                "message": {
                    "type": "string",
                    "description": "Confirmation message"
                }
            },
            tags=["delete", "remove"]
        )
        super().__init__(metadata)
        self.memory_store = memory_store
        self.project_manager = project_manager

    async def execute(self, **params) -> ToolResult:
        """Execute forget operation.

        Args:
            memory_id: Memory ID to delete (optional)
            query: Query to find memories (optional)

        Returns:
            ToolResult with deleted count
        """
        try:
            memory_id = params.get("memory_id")
            query = params.get("query")

            # Validate: at least one parameter required
            if not memory_id and not query:
                return ToolResult.error(
                    "Must provide either 'memory_id' or 'query' parameter"
                )

            deleted_count = 0

            if memory_id:
                # Delete specific memory by ID
                try:
                    deleted = self.memory_store.forget(memory_id)
                    deleted_count = 1 if deleted else 0
                except Exception as e:
                    self.logger.error(f"Delete by ID failed: {e}")
                    return ToolResult.error(f"Delete failed: {str(e)}")
            else:
                # Query-based forget not directly supported
                # Return informative error
                return ToolResult.error(
                    "Query-based forget not yet supported. Please provide 'memory_id' parameter"
                )

            result_data = {
                "deleted_count": deleted_count,
                "memory_id": memory_id
            }

            self.log_execution(params, ToolResult.success(data=result_data))
            return ToolResult.success(
                data=result_data,
                message=f"Deleted {deleted_count} memory/memories" if deleted_count > 0 else "No memories deleted"
            )

        except Exception as e:
            self.logger.exception(f"Unexpected error in forget: {e}")
            return ToolResult.error(f"Unexpected error: {str(e)}")


class OptimizeTool(BaseTool):
    """Optimize memory storage by pruning low-value memories."""

    def __init__(self, memory_store, project_manager):
        """Initialize optimize tool.

        Args:
            memory_store: MemoryStore instance for database access
            project_manager: ProjectManager instance for project context
        """
        metadata = ToolMetadata(
            name="optimize",
            description="Optimize memory storage by pruning low-value memories",
            category="memory",
            version="1.0",
            parameters={
                "dry_run": {
                    "type": "boolean",
                    "description": "Simulate optimization without making changes",
                    "default": True
                }
            },
            returns={
                "before_count": {
                    "type": "integer",
                    "description": "Memory count before optimization"
                },
                "after_count": {
                    "type": "integer",
                    "description": "Memory count after optimization"
                },
                "pruned": {
                    "type": "integer",
                    "description": "Number of memories pruned"
                }
            },
            tags=["maintenance", "cleanup", "optimization"]
        )
        super().__init__(metadata)
        self.memory_store = memory_store
        self.project_manager = project_manager

    async def execute(self, **params) -> ToolResult:
        """Execute optimize operation.

        Args:
            dry_run: Simulate without making changes (optional, default True)

        Returns:
            ToolResult with optimization stats
        """
        try:
            # Get current project
            try:
                project = self.project_manager.require_project()
                project_id = project.id
            except Exception as e:
                return ToolResult.error(f"Project error: {str(e)}")

            dry_run = params.get("dry_run", True)

            # Run optimization
            try:
                stats = self.memory_store.optimize(
                    project_id=project_id,
                    dry_run=dry_run
                )
            except Exception as e:
                self.logger.error(f"Optimization failed: {e}")
                return ToolResult.error(f"Optimization failed: {str(e)}")

            result_data = {
                "before_count": stats.get("before_count", 0),
                "after_count": stats.get("after_count", 0),
                "pruned": stats.get("pruned", 0),
                "dry_run": dry_run,
                "avg_score_before": stats.get("avg_score_before", 0),
                "avg_score_after": stats.get("avg_score_after", 0)
            }

            self.log_execution(params, ToolResult.success(data=result_data))
            return ToolResult.success(
                data=result_data,
                message=f"Optimization {'simulation' if dry_run else 'completed'}: "
                        f"Pruned {stats.get('pruned', 0)} memories"
            )

        except Exception as e:
            self.logger.exception(f"Unexpected error in optimize: {e}")
            return ToolResult.error(f"Unexpected error: {str(e)}")
