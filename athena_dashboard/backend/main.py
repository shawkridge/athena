"""
Athena Dashboard Backend - Clean Architecture

Single FastAPI application with 8 focused endpoints:
1. /api/memory/episodic - Episodic memory layer
2. /api/memory/semantic - Semantic memory layer
3. /api/memory/procedural - Procedural memory layer
4. /api/memory/prospective - Prospective memory layer
5. /api/memory/graph - Knowledge graph layer
6. /api/memory/meta - Meta-memory layer
7. /api/system/health - System health & consolidation
8. /api/tasks - Task operations (subset of prospective)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from typing import Any
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import routes
from routes.memory import router as memory_router
from routes.system import router as system_router
from routes.tasks import router as tasks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    logger.info("Starting Athena Dashboard Backend")
    yield
    logger.info("Shutting down Athena Dashboard Backend")


app = FastAPI(
    title="Athena Dashboard API",
    description="Clean, focused API for Athena memory system monitoring",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global error handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )


# Include routers
app.include_router(memory_router, prefix="/api/memory", tags=["memory"])
app.include_router(system_router, prefix="/api/system", tags=["system"])
app.include_router(tasks_router, prefix="/api/tasks", tags=["tasks"])


# Health check endpoint
@app.get("/health")
async def health_check():
    """Simple health check for monitoring."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
