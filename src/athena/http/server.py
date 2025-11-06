"""Athena HTTP Server - Exposes MCP operations as REST API."""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
import uvicorn

from .models import OperationRequest, OperationResponse, HealthResponse, InfoResponse, ErrorDetail
from ..mcp.handlers import MemoryMCPServer
from ..manager import UnifiedMemoryManager
from .mcp_mount import get_mcp_mount

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
ATHENA_VERSION = "1.0.0"
START_TIME = time.time()
DATABASE_PATH = Path.home() / ".athena" / "memory.db"


class AthenaHTTPServer:
    """HTTP wrapper for Athena MCP server."""

    def __init__(self, host: str = "0.0.0.0", port: int = 3000, debug: bool = False):
        """Initialize HTTP server."""
        self.host = host
        self.port = port
        self.debug = debug
        self.app = FastAPI(
            title="Athena Memory System API",
            description="HTTP interface to Athena's 8-layer neuroscience-inspired memory system",
            version=ATHENA_VERSION,
            docs_url="/docs",
            redoc_url="/redoc",
            openapi_url="/openapi.json",
        )

        # Initialize MCP server
        self.mcp_server = None
        self.manager = None

        # Setup middleware
        self._setup_middleware()

        # Setup routes
        self._setup_routes()

        # Mount MCP protocol endpoint at /mcp
        try:
            mcp_app = get_mcp_mount()
            # mcp_app is a Starlette app with MCP Streamable HTTP transport
            self.app.mount("/mcp", mcp_app)
            logger.info("✓ MCP protocol endpoint mounted at /mcp")
        except Exception as e:
            logger.error(f"Failed to mount MCP endpoint: {e}")
            logger.warning("MCP protocol endpoint not available, REST API only")

    def _setup_middleware(self):
        """Setup CORS and other middleware."""
        # CORS - allow localhost and Docker network
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:*", "http://127.0.0.1:*", "http://host.docker.internal:*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Request/response logging middleware
        @self.app.middleware("http")
        async def log_middleware(request: Request, call_next):
            """Log request and response."""
            start_time = time.time()
            request_id = request.headers.get("X-Request-ID", "unknown")

            try:
                response = await call_next(request)
                process_time = time.time() - start_time

                logger.info(
                    f"[{request_id}] {request.method} {request.url.path} "
                    f"- Status: {response.status_code} - Time: {process_time:.3f}s"
                )
                response.headers["X-Process-Time"] = str(process_time)
                return response
            except Exception as e:
                process_time = time.time() - start_time
                logger.error(
                    f"[{request_id}] {request.method} {request.url.path} "
                    f"- Error: {str(e)} - Time: {process_time:.3f}s"
                )
                raise

        # Error handling middleware
        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            """Handle general exceptions."""
            logger.error(f"Unhandled exception: {exc}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": str(exc),
                    "operation": request.url.path,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

    def _setup_routes(self):
        """Setup API routes."""

        # Health check
        @self.app.get("/health", response_model=HealthResponse, tags=["Health"])
        async def health_check():
            """Check service health."""
            try:
                uptime = time.time() - START_TIME
                db_size = 0.0

                if DATABASE_PATH.exists():
                    db_size = DATABASE_PATH.stat().st_size / (1024 * 1024)  # Convert to MB

                return HealthResponse(
                    status="healthy",
                    version=ATHENA_VERSION,
                    uptime_seconds=uptime,
                    database_size_mb=db_size,
                    operations_count=228,
                )
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                raise HTTPException(status_code=503, detail=str(e))

        # Info endpoint
        @self.app.get("/info", response_model=InfoResponse, tags=["Info"])
        async def info():
            """Get API information."""
            return InfoResponse(
                name="Athena Memory System API",
                version=ATHENA_VERSION,
                description="HTTP interface to Athena's neuroscience-inspired memory system",
                documentation_url="/docs",
                supported_operations=list(self._get_all_operations().keys()),
            )

        # Generic operation endpoint
        @self.app.post("/api/operation", response_model=OperationResponse, tags=["Operations"])
        async def execute_operation(request_data: OperationRequest):
            """Execute any Athena operation via HTTP."""
            start_time = time.time()

            try:
                operation = request_data.operation
                params = request_data.params

                logger.info(f"Executing operation: {operation} with params: {params}")

                # Execute operation
                result = await self._execute_operation(operation, params)

                execution_time = (time.time() - start_time) * 1000  # Convert to ms

                return OperationResponse(
                    success=True,
                    data=result,
                    error=None,
                    operation=operation,
                    execution_time_ms=execution_time,
                )
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                logger.error(f"Operation failed: {e}", exc_info=True)
                raise HTTPException(status_code=400, detail=str(e))

        # Memory operations
        @self.app.post("/api/memory/recall", response_model=OperationResponse, tags=["Memory"])
        async def recall(query: str, k: int = 5, memory_type: Optional[str] = None):
            """Recall memories matching query."""
            return await self._wrap_operation(
                "recall",
                {"query": query, "k": k, **({"memory_type": memory_type} if memory_type else {})}
            )

        @self.app.post("/api/memory/remember", response_model=OperationResponse, tags=["Memory"])
        async def remember(
            content: str,
            memory_type: str = "fact",
            tags: list = None,
            importance: Optional[float] = None,
        ):
            """Remember new knowledge."""
            params = {
                "content": content,
                "memory_type": memory_type,
                **({"tags": tags} if tags else {}),
                **({"importance": importance} if importance else {}),
            }
            return await self._wrap_operation("remember", params)

        @self.app.post("/api/memory/forget", response_model=OperationResponse, tags=["Memory"])
        async def forget(memory_id: int):
            """Forget a memory."""
            return await self._wrap_operation("forget", {"memory_id": memory_id})

        @self.app.get("/api/memory/health", response_model=OperationResponse, tags=["Memory"])
        async def memory_health():
            """Get memory system health."""
            return await self._wrap_operation("get_memory_quality_summary", {})

        # Consolidation operations
        @self.app.post("/api/consolidation/run", response_model=OperationResponse, tags=["Consolidation"])
        async def consolidate(
            strategy: str = "balanced",
            days_back: Optional[int] = None,
            dry_run: bool = False,
        ):
            """Run consolidation with specified strategy."""
            params = {"strategy": strategy, "dry_run": dry_run}
            if days_back:
                params["days_back"] = days_back
            return await self._wrap_operation("run_consolidation", params)

        @self.app.post("/api/consolidation/schedule", response_model=OperationResponse, tags=["Consolidation"])
        async def schedule_consolidation(strategy: str = "balanced"):
            """Schedule consolidation."""
            return await self._wrap_operation("schedule_consolidation", {"strategy": strategy})

        # Task/Goal operations
        @self.app.post("/api/tasks/create", response_model=OperationResponse, tags=["Tasks"])
        async def create_task(content: str, priority: str = "medium", project_id: Optional[int] = None):
            """Create a new task."""
            params = {"content": content, "priority": priority}
            if project_id:
                params["project_id"] = project_id
            return await self._wrap_operation("create_task", params)

        @self.app.get("/api/tasks/list", response_model=OperationResponse, tags=["Tasks"])
        async def list_tasks(project_id: Optional[int] = None):
            """List all tasks."""
            params = {}
            if project_id:
                params["project_id"] = project_id
            return await self._wrap_operation("list_tasks", params)

        @self.app.post("/api/goals/set", response_model=OperationResponse, tags=["Goals"])
        async def set_goal(content: str, priority: str = "medium"):
            """Set a new goal."""
            return await self._wrap_operation("set_goal", {"content": content, "priority": priority})

        @self.app.get("/api/goals/active", response_model=OperationResponse, tags=["Goals"])
        async def get_active_goals():
            """Get active goals."""
            return await self._wrap_operation("get_active_goals", {})

        # Planning operations
        @self.app.post("/api/planning/validate", response_model=OperationResponse, tags=["Planning"])
        async def validate_plan(task_id: int):
            """Validate a plan."""
            return await self._wrap_operation("validate_plan", {"task_id": task_id})

        @self.app.post("/api/planning/decompose", response_model=OperationResponse, tags=["Planning"])
        async def decompose_task(task_description: str, strategy: str = "hierarchical"):
            """Decompose task into steps."""
            return await self._wrap_operation(
                "decompose_with_strategy",
                {"task_description": task_description, "strategy": strategy}
            )

        # Graph operations
        @self.app.post("/api/graph/create-entity", response_model=OperationResponse, tags=["Graph"])
        async def create_entity(name: str, entity_type: str):
            """Create knowledge graph entity."""
            return await self._wrap_operation(
                "create_entity",
                {"name": name, "entity_type": entity_type}
            )

        @self.app.get("/api/graph/search", response_model=OperationResponse, tags=["Graph"])
        async def search_graph(query: str, max_results: int = 10):
            """Search knowledge graph."""
            return await self._wrap_operation(
                "search_graph",
                {"query": query, "max_results": max_results}
            )

        logger.info("Routes setup complete")

    async def _wrap_operation(self, operation: str, params: Dict[str, Any]) -> OperationResponse:
        """Wrap operation execution with timing and error handling."""
        start_time = time.time()
        try:
            result = await self._execute_operation(operation, params)
            execution_time = (time.time() - start_time) * 1000

            return OperationResponse(
                success=True,
                data=result,
                error=None,
                operation=operation,
                execution_time_ms=execution_time,
            )
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Operation {operation} failed: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=str(e))

    async def _execute_operation(self, operation: str, params: Dict[str, Any]) -> Any:
        """Execute an MCP operation."""
        if not self.mcp_server:
            raise RuntimeError("MCP server not initialized. Call startup() first.")

        # Route operation to appropriate handler
        try:
            # Try manager method first (if available)
            if self.manager:
                method = getattr(self.manager, operation, None)
                if method and callable(method):
                    if asyncio.iscoroutinefunction(method):
                        return await method(**params)
                    else:
                        return method(**params)

            # Try MCP server handler - these expect args as a dict parameter
            handler_method = getattr(self.mcp_server, f"_handle_{operation}", None)
            if handler_method and callable(handler_method):
                # MCP handlers expect args: dict pattern
                if asyncio.iscoroutinefunction(handler_method):
                    return await handler_method(params)
                else:
                    return handler_method(params)

            raise ValueError(f"Operation '{operation}' not found")
        except Exception as e:
            logger.error(f"Failed to execute operation {operation}: {e}", exc_info=True)
            raise

    def _get_all_operations(self) -> Dict[str, str]:
        """Get all supported operations."""
        # This would be expanded to return all operations from the router
        return {
            "recall": "Search memories",
            "remember": "Store new memory",
            "forget": "Delete memory",
            "consolidate": "Run consolidation",
            "create_task": "Create task",
            "set_goal": "Set goal",
            # ... many more
        }

    async def startup(self):
        """Initialize on startup."""
        try:
            logger.info("Initializing Athena HTTP Server...")

            # Initialize MCP server (which will handle manager initialization internally)
            db_path = str(Path.home() / ".athena" / "memory.db")
            self.mcp_server = MemoryMCPServer(db_path=db_path)
            logger.info("MCP server initialized")

            # For now, use MCP server's internal manager if available
            if hasattr(self.mcp_server, 'manager'):
                self.manager = self.mcp_server.manager
            else:
                # Fallback: manager is optional for HTTP server
                self.manager = None
                logger.warning("MCP server does not have manager, operating in minimal mode")

            logger.info("Athena HTTP Server startup complete")
        except Exception as e:
            logger.error(f"Startup failed: {e}", exc_info=True)
            raise

    async def shutdown(self):
        """Cleanup on shutdown."""
        logger.info("Shutting down Athena HTTP Server...")

    def run(self):
        """Start the HTTP server."""
        logger.info(f"Starting Athena HTTP Server on {self.host}:{self.port}")

        # Setup startup/shutdown
        self.app.add_event_handler("startup", self.startup)
        self.app.add_event_handler("shutdown", self.shutdown)

        # Run server
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
            reload=self.debug,
        )


def create_app() -> FastAPI:
    """Create FastAPI application."""
    server = AthenaHTTPServer()
    return server.app


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Athena HTTP Server")
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=3000, help="Server port")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    args = parser.parse_args()

    server = AthenaHTTPServer(host=args.host, port=args.port, debug=args.debug)
    server.run()


if __name__ == "__main__":
    main()
