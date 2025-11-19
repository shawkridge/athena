"""Athena Dashboard API - FastAPI Backend

This backend provides REST API endpoints for the Athena dashboard.
It imports and uses Athena operations directly (no database bypass).

All operations are async and use Athena's existing operations layer.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime

# Add Athena to Python path
athena_root = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(athena_root))

# Import Athena initialization
from athena import initialize_athena

# Import all operations (use Athena's operations layer directly)
from athena.episodic.operations import (
    recall,
    recall_recent,
    get_by_session,
    get_statistics as episodic_stats,
)
from athena.semantic.operations import search as semantic_search, store as semantic_store
from athena.procedural.operations import list_procedures, get_statistics as procedural_stats
from athena.prospective.operations import (
    list_tasks,
    get_active_tasks,
    get_statistics as prospective_stats,
)
from athena.graph.operations import (
    search_entities,
    find_related,
    get_statistics as graph_stats,
)
from athena.meta.operations import get_statistics as meta_stats
from athena.consolidation.operations import (
    get_consolidation_history,
    get_statistics as consolidation_stats,
)
from athena.planning.operations import list_plans, get_statistics as planning_stats

app = FastAPI(
    title="Athena Dashboard API",
    description="Real-time API for Athena Memory System Dashboard - All Subsystems",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Athena on startup
@app.on_event("startup")
async def startup_event():
    """Initialize Athena memory system."""
    print("🚀 Starting Athena Dashboard API...")
    print("📊 Initializing Athena memory system...")
    success = await initialize_athena()
    if success:
        print("✅ Athena initialized successfully")
        print("🌐 API available at http://localhost:8000")
        print("📚 API docs at http://localhost:8000/docs")
    else:
        print("❌ Failed to initialize Athena")


# ============================================================================
# SYSTEM HEALTH & OVERVIEW
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "athena-dashboard-api",
        "version": "1.0.0",
    }


@app.get("/api/system/status")
async def system_status():
    """Get overall system status across all subsystems."""
    try:
        # Gather stats from all layers
        episodic = await episodic_stats()
        procedural = await procedural_stats()
        prospective = await prospective_stats()
        graph = await graph_stats()
        meta = await meta_stats()
        consolidation = await consolidation_stats()
        planning = await planning_stats()

        return {
            "status": "healthy",
            "subsystems": {
                "memory": {
                    "episodic": episodic,
                    "procedural": procedural,
                    "prospective": prospective,
                    "graph": graph,
                    "meta": meta,
                    "consolidation": consolidation,
                    "planning": planning,
                },
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# ============================================================================
# EPISODIC MEMORY (LAYER 1)
# ============================================================================

@app.get("/api/episodic/statistics")
async def get_episodic_statistics(session_id: Optional[str] = None):
    """Get episodic memory statistics."""
    return await episodic_stats(session_id=session_id)


@app.get("/api/episodic/events")
async def get_episodic_events(
    limit: int = Query(100, le=1000),
    session_id: Optional[str] = None,
    project_id: int = 1,
):
    """Get episodic events with pagination."""
    # Note: project_id parameter kept for future multi-project support
    # Currently Athena's recall() doesn't accept project_id, uses default project
    events = await recall(
        query="*",  # All events
        limit=limit,
        session_id=session_id,
    )

    # Convert to dict for JSON serialization
    return {
        "events": [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat(),
                "event_type": e.event_type,
                "content": e.content,
                "importance_score": e.importance_score,
                "session_id": e.session_id,
                "lifecycle_status": e.lifecycle_status,
                "consolidation_score": e.consolidation_score,
            }
            for e in events
        ],
        "total": len(events),
        "limit": limit,
    }


@app.get("/api/episodic/recent")
async def get_recent_events(limit: int = Query(10, le=100)):
    """Get most recent episodic events."""
    events = await recall_recent(limit=limit)

    return {
        "events": [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat(),
                "event_type": e.event_type,
                "content": e.content[:200],  # Truncate for overview
                "importance_score": e.importance_score,
            }
            for e in events
        ],
        "total": len(events),
    }


# ============================================================================
# SEMANTIC MEMORY (LAYER 2)
# ============================================================================

@app.get("/api/semantic/search")
async def search_semantic_memories(
    query: str = Query(..., min_length=1),
    limit: int = Query(10, le=100),
):
    """Search semantic memories."""
    results = await semantic_search(query=query, limit=limit)

    return {
        "results": [
            {
                "id": r.id,
                "content": r.content,
                "memory_type": r.memory_type if hasattr(r, "memory_type") else None,
                "usefulness_score": r.usefulness_score
                if hasattr(r, "usefulness_score")
                else None,
            }
            for r in results
        ],
        "total": len(results),
        "query": query,
    }


# ============================================================================
# PROCEDURAL MEMORY (LAYER 3)
# ============================================================================

@app.get("/api/procedural/statistics")
async def get_procedural_statistics():
    """Get procedural memory statistics."""
    return await procedural_stats()


@app.get("/api/procedural/procedures")
async def get_procedures(
    limit: int = Query(100, le=500),
    category: Optional[str] = None,
):
    """Get procedures."""
    procedures = await list_procedures(limit=limit)

    # Filter by category if provided
    if category:
        procedures = [p for p in procedures if p.category == category]

    return {
        "procedures": [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "success_rate": p.success_rate,
                "usage_count": p.usage_count,
                "last_used": p.last_used.isoformat() if p.last_used else None,
            }
            for p in procedures
        ],
        "total": len(procedures),
    }


# ============================================================================
# PROSPECTIVE MEMORY (LAYER 4)
# ============================================================================

@app.get("/api/prospective/statistics")
async def get_prospective_statistics():
    """Get prospective memory statistics."""
    return await prospective_stats()


@app.get("/api/prospective/tasks")
async def get_tasks(
    status: Optional[str] = None,
    limit: int = Query(100, le=500),
):
    """Get tasks."""
    if status == "active":
        tasks = await get_active_tasks(limit=limit)
    else:
        tasks = await list_tasks(limit=limit)

    return {
        "tasks": [
            {
                "id": t.id,
                "content": t.content,
                "status": t.status,
                "priority": t.priority,
                "phase": t.phase,
                "created_at": t.created_at.isoformat(),
                "due_at": t.due_at.isoformat() if t.due_at else None,
            }
            for t in tasks
        ],
        "total": len(tasks),
    }


# ============================================================================
# KNOWLEDGE GRAPH (LAYER 5)
# ============================================================================

@app.get("/api/graph/statistics")
async def get_graph_statistics():
    """Get knowledge graph statistics."""
    return await graph_stats()


@app.get("/api/graph/entities")
async def get_entities(
    entity_type: Optional[str] = None,
    limit: int = Query(100, le=500),
):
    """Get graph entities."""
    entities = await search_entities(
        query="*",
        entity_type=entity_type,
        limit=limit,
    )

    return {
        "entities": [
            {
                "id": e.id,
                "name": e.name,
                "entity_type": e.entity_type,
                "source": e.source,
            }
            for e in entities
        ],
        "total": len(entities),
    }


@app.get("/api/graph/entities/{entity_id}/related")
async def get_entity_relations(entity_id: int, limit: int = Query(50, le=200)):
    """Get related entities for a specific entity."""
    related = await find_related(entity_id=entity_id, limit=limit)

    return {
        "entity_id": entity_id,
        "related": [
            {
                "id": r.id,
                "name": r.name,
                "entity_type": r.entity_type,
                "relation_type": r.relation_type if hasattr(r, "relation_type") else None,
            }
            for r in related
        ],
        "total": len(related),
    }


# ============================================================================
# META-MEMORY (LAYER 6)
# ============================================================================

@app.get("/api/meta/statistics")
async def get_meta_statistics():
    """Get meta-memory statistics."""
    return await meta_stats()


# ============================================================================
# CONSOLIDATION (LAYER 7)
# ============================================================================

@app.get("/api/consolidation/statistics")
async def get_consolidation_statistics():
    """Get consolidation statistics."""
    return await consolidation_stats()


@app.get("/api/consolidation/history")
async def get_consolidation_run_history(limit: int = Query(20, le=100)):
    """Get consolidation run history."""
    history = await get_consolidation_history(limit=limit)

    return {
        "runs": [
            {
                "id": h.id if hasattr(h, "id") else None,
                "started_at": h.started_at.isoformat() if hasattr(h, "started_at") else None,
                "status": h.status if hasattr(h, "status") else None,
                "patterns_extracted": h.patterns_extracted
                if hasattr(h, "patterns_extracted")
                else None,
            }
            for h in history
        ],
        "total": len(history),
    }


# ============================================================================
# PLANNING (LAYER 8)
# ============================================================================

@app.get("/api/planning/statistics")
async def get_planning_statistics():
    """Get planning statistics."""
    return await planning_stats()


@app.get("/api/planning/plans")
async def get_plans(limit: int = Query(50, le=200)):
    """Get plans."""
    plans = await list_plans(limit=limit)

    return {
        "plans": [
            {
                "id": p.id if hasattr(p, "id") else None,
                "name": p.name if hasattr(p, "name") else None,
                "status": p.status if hasattr(p, "status") else None,
            }
            for p in plans
        ],
        "total": len(plans),
    }


# ============================================================================
# WEBSOCKET FOR REAL-TIME UPDATES
# ============================================================================

class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"❌ WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections[:]:  # Copy list to avoid modification during iteration
            try:
                await connection.send_json(message)
            except:
                self.disconnect(connection)


manager = ConnectionManager()


@app.websocket("/ws/live-updates")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)

    try:
        while True:
            # Send statistics every 10 seconds
            try:
                stats = await episodic_stats()
                await websocket.send_json(
                    {
                        "type": "statistics_update",
                        "layer": "episodic",
                        "data": stats,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            except Exception as e:
                print(f"Error sending stats: {e}")

            await asyncio.sleep(10)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Athena Dashboard API...")
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info",
    )
