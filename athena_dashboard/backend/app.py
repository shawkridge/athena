"""FastAPI application for Athena monitoring dashboard."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from services import DataLoader, CacheManager, MetricsAggregator, AthenaHTTPLoader, StreamingService
from models.metrics import (
    DashboardOverview,
    HookMetrics,
    MemoryMetrics,
    CognitiveLoad,
    TaskMetrics,
    LearningMetrics,
)
from routes.websocket_routes import initialize_websocket_routes
from routes.api import api_router

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global instances
data_loader: DataLoader
cache_manager: CacheManager
metrics_aggregator: MetricsAggregator
streaming_service: StreamingService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    global data_loader, cache_manager, metrics_aggregator, streaming_service

    # Startup
    logger.info("Starting Athena Dashboard backend")

    # Initialize data loader (HTTP or direct database)
    if settings.USE_ATHENA_HTTP:
        logger.info(f"Using Athena HTTP API: {settings.ATHENA_HTTP_URL}")
        data_loader = AthenaHTTPLoader(athena_url=settings.ATHENA_HTTP_URL)
        if not data_loader.is_connected():
            logger.warning("Athena HTTP service unavailable, falling back to direct database access")
            data_loader = DataLoader()
            data_loader.connect()
    else:
        logger.info("Using direct database access")
        data_loader = DataLoader()
        data_loader.connect()

    cache_manager = CacheManager()
    metrics_aggregator = MetricsAggregator(data_loader, cache_manager)

    # Initialize streaming service
    streaming_service = StreamingService(athena_url=settings.ATHENA_HTTP_URL)
    logger.info("Streaming service initialized")

    yield

    # Shutdown
    logger.info("Shutting down Athena Dashboard backend")
    try:
        # Cleanup streaming service
        await streaming_service.cleanup()
        data_loader.close()
    except Exception as e:
        logger.error(f"Error closing resources: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Real-time monitoring dashboard for Athena memory system",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include main API router
app.include_router(api_router)
logger.info("Dashboard API routes registered")


# ============================================================================
# WEBSOCKET ROUTES (initialized in lifespan)
# ============================================================================

# The WebSocket router will be added in the startup event once streaming_service is initialized
def add_websocket_routes(app: FastAPI) -> None:
    """Add WebSocket routes to the app."""
    if settings.WEBSOCKET_ENABLED and streaming_service:
        ws_router = initialize_websocket_routes(streaming_service)
        app.include_router(ws_router)
        logger.info("WebSocket routes registered")


# ============================================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================================


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/info")
async def app_info() -> dict:
    """Get application info."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG,
        "cache_enabled": settings.CACHE_ENABLED,
        "websocket_enabled": settings.WEBSOCKET_ENABLED,
    }


# ============================================================================
# DASHBOARD ENDPOINTS
# ============================================================================


@app.get(f"{settings.API_PREFIX}/dashboard/overview", response_model=DashboardOverview)
async def get_overview() -> DashboardOverview:
    """Get complete dashboard overview.

    Returns:
        DashboardOverview with all metrics
    """
    try:
        return metrics_aggregator._compute_dashboard_overview()
    except Exception as e:
        logger.error(f"Failed to compute overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to compute metrics")


# ============================================================================
# HOOK METRICS ENDPOINTS
# ============================================================================


@app.get(f"{settings.API_PREFIX}/hooks/status", response_model=list[HookMetrics])
async def get_hooks_status() -> list[HookMetrics]:
    """Get status of all hooks.

    Returns:
        List of HookMetrics for all hooks
    """
    try:
        return metrics_aggregator._compute_hook_metrics()
    except Exception as e:
        logger.error(f"Failed to get hook metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch hook metrics")


@app.get(f"{settings.API_PREFIX}/hooks/{{hook_name}}/metrics", response_model=dict)
async def get_hook_metrics(hook_name: str) -> dict:
    """Get detailed metrics for specific hook.

    Args:
        hook_name: Name of the hook

    Returns:
        Detailed metrics for hook
    """
    try:
        metrics = metrics_aggregator._compute_hook_metrics()
        for m in metrics:
            if m.hook_name == hook_name:
                return m.model_dump()
        raise HTTPException(status_code=404, detail=f"Hook {hook_name} not found")
    except Exception as e:
        logger.error(f"Failed to get hook metrics for {hook_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch hook metrics")


# ============================================================================
# MEMORY METRICS ENDPOINTS
# ============================================================================


@app.get(f"{settings.API_PREFIX}/memory/health", response_model=MemoryMetrics)
async def get_memory_health() -> MemoryMetrics:
    """Get memory system health report.

    Returns:
        MemoryMetrics with quality and consolidation info
    """
    try:
        return metrics_aggregator._compute_memory_metrics()
    except Exception as e:
        logger.error(f"Failed to compute memory metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch memory metrics")


@app.get(f"{settings.API_PREFIX}/memory/consolidation", response_model=dict)
async def get_consolidation() -> dict:
    """Get consolidation pipeline status.

    Returns:
        Consolidation progress and metrics
    """
    try:
        progress = metrics_aggregator._compute_consolidation_progress()
        return progress.model_dump()
    except Exception as e:
        logger.error(f"Failed to get consolidation status: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch consolidation status")


@app.get(f"{settings.API_PREFIX}/memory/gaps", response_model=list[dict])
async def get_knowledge_gaps() -> list[dict]:
    """Get identified knowledge gaps.

    Returns:
        List of knowledge gaps with severity
    """
    try:
        gaps = data_loader.get_knowledge_gaps()
        return gaps
    except Exception as e:
        logger.error(f"Failed to get knowledge gaps: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch knowledge gaps")


@app.get(f"{settings.API_PREFIX}/memory/domains", response_model=dict)
async def get_domain_coverage() -> dict:
    """Get domain expertise coverage.

    Returns:
        Coverage percentage per domain
    """
    try:
        coverage = data_loader.get_domain_coverage()
        return coverage
    except Exception as e:
        logger.error(f"Failed to get domain coverage: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch domain coverage")


# ============================================================================
# COGNITIVE LOAD ENDPOINTS
# ============================================================================


@app.get(f"{settings.API_PREFIX}/load/current", response_model=CognitiveLoad)
async def get_current_load() -> CognitiveLoad:
    """Get current cognitive load.

    Returns:
        Current working memory status
    """
    try:
        return metrics_aggregator._compute_cognitive_load()
    except Exception as e:
        logger.error(f"Failed to compute cognitive load: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch cognitive load")


@app.get(f"{settings.API_PREFIX}/load/history", response_model=list[dict])
async def get_load_history(hours: int = 24) -> list[dict]:
    """Get historical cognitive load data.

    Args:
        hours: Hours lookback

    Returns:
        List of load data points
    """
    try:
        # Would compute from episodic events
        return []
    except Exception as e:
        logger.error(f"Failed to get load history: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch load history")


# ============================================================================
# TASK & PROJECT ENDPOINTS
# ============================================================================


@app.get(f"{settings.API_PREFIX}/projects", response_model=dict)
async def get_projects() -> dict:
    """Get all projects with status.

    Returns:
        Dictionary with project list and stats
    """
    try:
        projects = []  # Would fetch from database
        stats = data_loader.get_project_stats()
        return {
            "projects": projects,
            "total": stats.get("project_count", 0),
            "completed": stats.get("completed_count", 0),
            "avg_progress": stats.get("avg_progress", 0),
        }
    except Exception as e:
        logger.error(f"Failed to get projects: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch projects")


@app.get(f"{settings.API_PREFIX}/goals", response_model=list[dict])
async def get_goals(project_id: int = None) -> list[dict]:
    """Get active goals.

    Args:
        project_id: Optional project filter

    Returns:
        List of active goals
    """
    try:
        goals = data_loader.get_active_goals()
        if project_id:
            goals = [g for g in goals if g.get("project_id") == project_id]
        return goals
    except Exception as e:
        logger.error(f"Failed to get goals: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch goals")


@app.get(f"{settings.API_PREFIX}/tasks", response_model=list[dict])
async def get_tasks(project_id: int = None) -> list[dict]:
    """Get active tasks.

    Args:
        project_id: Optional project filter

    Returns:
        List of active tasks
    """
    try:
        tasks = data_loader.get_active_tasks()
        if project_id:
            tasks = [t for t in tasks if t.get("project_id") == project_id]
        return tasks
    except Exception as e:
        logger.error(f"Failed to get tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch tasks")


# ============================================================================
# LEARNING & ANALYTICS ENDPOINTS
# ============================================================================


@app.get(f"{settings.API_PREFIX}/learning/strategies", response_model=dict)
async def get_strategy_effectiveness() -> dict:
    """Get strategy effectiveness analysis.

    Returns:
        Strategy metrics and comparisons
    """
    try:
        # Would compute from consolidation history
        return {
            "strategies": [],
            "top_strategy": None,
            "improvement_trend": 0.0,
        }
    except Exception as e:
        logger.error(f"Failed to get strategy effectiveness: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch strategy data")


@app.get(f"{settings.API_PREFIX}/learning/procedures", response_model=list[dict])
async def get_top_procedures(limit: int = 10) -> list[dict]:
    """Get top procedures by effectiveness.

    Args:
        limit: Number of procedures to return

    Returns:
        List of top procedures
    """
    try:
        procedures = data_loader.get_top_procedures(limit=limit)
        return procedures
    except Exception as e:
        logger.error(f"Failed to get procedures: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch procedures")


# ============================================================================
# ERROR HANDLERS
# ============================================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "timestamp": datetime.utcnow().isoformat()},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


# ============================================================================
# STARTUP EVENTS
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("Athena Dashboard backend started")
    logger.info(f"CORS origins: {settings.CORS_ORIGINS}")
    logger.info(f"Cache enabled: {settings.CACHE_ENABLED}")
    logger.info(f"WebSocket enabled: {settings.WEBSOCKET_ENABLED}")

    # Add WebSocket routes if enabled
    if settings.WEBSOCKET_ENABLED:
        add_websocket_routes(app)


if __name__ == "__main__":
    from datetime import datetime
    import uvicorn

    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
    )
