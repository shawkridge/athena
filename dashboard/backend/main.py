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

# Advanced subsystems
# Note: Some imports commented out for compatibility - will be re-enabled as needed
try:
    from athena.research import ResearchStore
except ImportError:
    ResearchStore = None
try:
    from athena.skills.library import SkillLibrary
    from athena.skills.executor import SkillExecutor
except ImportError:
    SkillLibrary = None
    SkillExecutor = None
try:
    from athena.code.indexer import CodeIndexer
except ImportError:
    CodeIndexer = None
try:
    from athena.execution.monitor import ExecutionMonitor
except ImportError:
    ExecutionMonitor = None
try:
    from athena.safety.store import SafetyCheckStore
except ImportError:
    SafetyCheckStore = None
try:
    from athena.performance.monitor import PerformanceMonitor
except ImportError:
    PerformanceMonitor = None
try:
    from athena.ide_context.store import IDEContextStore
except ImportError:
    IDEContextStore = None
try:
    from athena.working_memory import WorkingMemoryManager
except ImportError:
    WorkingMemoryManager = None
from athena.core.database_postgres import PostgresDatabase

# Global instances for advanced subsystems (initialized on startup)
_research_store = None
_skill_library = None
_skill_executor = None
_code_indexer = None
_execution_monitor = None
_safety_store = None
_performance_monitor = None
_ide_context_store = None
_working_memory = None
_postgres_db = None

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
    """Initialize Athena memory system and advanced subsystems."""
    global _research_store, _skill_library, _skill_executor, _code_indexer
    global _execution_monitor, _safety_store, _performance_monitor
    global _ide_context_store, _working_memory, _postgres_db

    print("🚀 Starting Athena Dashboard API...")
    print("📊 Initializing Athena memory system...")
    success = await initialize_athena()
    if success:
        print("✅ Athena initialized successfully")
    else:
        print("❌ Failed to initialize Athena - continuing with available features")

    # Initialize PostgreSQL database for advanced subsystems
    try:
        _postgres_db = PostgresDatabase()
        await _postgres_db.initialize()
        print("✅ PostgreSQL database initialized")

        # Initialize advanced subsystems (with fallback)
        if ResearchStore:
            _research_store = ResearchStore(_postgres_db.conn)
        if SkillLibrary:
            _skill_library = SkillLibrary(_postgres_db)
            _skill_executor = SkillExecutor(_skill_library)
        if CodeIndexer:
            _code_indexer = CodeIndexer(_postgres_db.conn)
        if ExecutionMonitor:
            _execution_monitor = ExecutionMonitor(_postgres_db.conn)
        if SafetyCheckStore:
            _safety_store = SafetyCheckStore(_postgres_db.conn)
        if PerformanceMonitor:
            _performance_monitor = PerformanceMonitor(_postgres_db)
        if IDEContextStore:
            _ide_context_store = IDEContextStore(_postgres_db.conn)
        if WorkingMemoryManager:
            _working_memory = WorkingMemoryManager(_postgres_db)

        print("✅ Advanced subsystems initialized (with fallbacks)")
    except Exception as e:
        print(f"⚠️ Some advanced subsystems failed to initialize: {e}")
        print("   Core memory operations will still work")

    print("🌐 API available at http://localhost:8000")
    print("📚 API docs at http://localhost:8000/docs")


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
# RESEARCH (Advanced Subsystem)
# ============================================================================

@app.get("/api/research/tasks")
async def get_research_tasks(status: Optional[str] = None, limit: int = Query(50, le=200)):
    """Get research tasks."""
    if not _research_store:
        return {"tasks": [], "total": 0, "message": "Research subsystem not initialized"}

    try:
        tasks = _research_store.list_tasks(status=status, limit=limit)
        return {
            "tasks": [
                {
                    "id": t.id,
                    "topic": t.topic,
                    "status": t.status.value if hasattr(t.status, "value") else str(t.status),
                    "created_at": t.created_at.isoformat() if hasattr(t, "created_at") else None,
                    "project_id": t.project_id if hasattr(t, "project_id") else None,
                }
                for t in tasks
            ],
            "total": len(tasks),
        }
    except Exception as e:
        return {"tasks": [], "total": 0, "error": str(e)}


@app.get("/api/research/statistics")
async def get_research_statistics():
    """Get research statistics."""
    if not _research_store:
        return {"total_tasks": 0, "active_tasks": 0, "completed_tasks": 0}

    try:
        all_tasks = _research_store.list_tasks(limit=1000)
        return {
            "total_tasks": len(all_tasks),
            "active_tasks": len([t for t in all_tasks if str(t.status) == "in_progress"]),
            "completed_tasks": len([t for t in all_tasks if str(t.status) == "completed"]),
            "pending_tasks": len([t for t in all_tasks if str(t.status) == "pending"]),
        }
    except Exception as e:
        return {"total_tasks": 0, "error": str(e)}


# ============================================================================
# CODE INTELLIGENCE (Advanced Subsystem)
# ============================================================================

@app.get("/api/code/artifacts")
async def get_code_artifacts(limit: int = Query(50, le=200)):
    """Get code artifacts."""
    if not _code_indexer:
        return {"artifacts": [], "total": 0, "message": "Code indexer not initialized"}

    try:
        # Get indexed files (artifacts)
        artifacts = await _code_indexer.get_indexed_files(limit=limit)
        return {
            "artifacts": [
                {
                    "path": a.path if hasattr(a, "path") else str(a),
                    "language": a.language if hasattr(a, "language") else None,
                    "size": a.size if hasattr(a, "size") else None,
                    "indexed_at": a.indexed_at.isoformat() if hasattr(a, "indexed_at") else None,
                }
                for a in artifacts
            ],
            "total": len(artifacts),
        }
    except Exception as e:
        return {"artifacts": [], "total": 0, "error": str(e)}


@app.get("/api/code/statistics")
async def get_code_statistics():
    """Get code intelligence statistics."""
    if not _code_indexer:
        return {"total_files": 0, "total_symbols": 0}

    try:
        stats = await _code_indexer.get_statistics()
        return {
            "total_files": stats.get("total_files", 0),
            "total_symbols": stats.get("total_symbols", 0),
            "languages": stats.get("languages", {}),
        }
    except Exception as e:
        return {"total_files": 0, "total_symbols": 0, "error": str(e)}


# ============================================================================
# SKILLS & AGENTS (Advanced Subsystem)
# ============================================================================

@app.get("/api/skills/library")
async def get_skills(domain: Optional[str] = None, limit: int = Query(50, le=200)):
    """Get skills from library."""
    if not _skill_library:
        return {"skills": [], "total": 0, "message": "Skill library not initialized"}

    try:
        skills = await _skill_library.list_all(domain=domain, limit=limit)
        return {
            "skills": [
                {
                    "id": s.id,
                    "name": s.name,
                    "domain": s.metadata.domain.value if hasattr(s.metadata, "domain") else None,
                    "success_rate": s.metadata.success_rate if hasattr(s.metadata, "success_rate") else 0.0,
                    "usage_count": s.metadata.usage_count if hasattr(s.metadata, "usage_count") else 0,
                }
                for s in skills
            ],
            "total": len(skills),
        }
    except Exception as e:
        return {"skills": [], "total": 0, "error": str(e)}


@app.get("/api/skills/statistics")
async def get_skills_statistics():
    """Get skills statistics."""
    if not _skill_library:
        return {"total_skills": 0, "avg_success_rate": 0.0}

    try:
        skills = await _skill_library.list_all(limit=1000)
        total = len(skills)
        avg_rate = sum(s.metadata.success_rate for s in skills if hasattr(s.metadata, "success_rate")) / total if total > 0 else 0.0

        return {
            "total_skills": total,
            "avg_success_rate": avg_rate,
            "total_executions": sum(s.metadata.usage_count for s in skills if hasattr(s.metadata, "usage_count")),
        }
    except Exception as e:
        return {"total_skills": 0, "error": str(e)}


# ============================================================================
# CONTEXT AWARENESS (Advanced Subsystem)
# ============================================================================

@app.get("/api/context/ide")
async def get_ide_context(limit: int = Query(10, le=50)):
    """Get IDE context (recent file interactions)."""
    if not _ide_context_store:
        return {"contexts": [], "total": 0, "message": "IDE context store not initialized"}

    try:
        contexts = _ide_context_store.get_recent_contexts(limit=limit)
        return {
            "contexts": [
                {
                    "file_path": c.file_path if hasattr(c, "file_path") else None,
                    "last_accessed": c.last_accessed.isoformat() if hasattr(c, "last_accessed") else None,
                    "focus_duration": c.focus_duration if hasattr(c, "focus_duration") else 0,
                }
                for c in contexts
            ],
            "total": len(contexts),
        }
    except Exception as e:
        return {"contexts": [], "total": 0, "error": str(e)}


@app.get("/api/context/working-memory")
async def get_working_memory_items(limit: int = Query(7, le=20)):
    """Get working memory items."""
    if not _working_memory:
        return {"items": [], "total": 0, "message": "Working memory not initialized"}

    try:
        items = await _working_memory.get_active_items(limit=limit)
        return {
            "items": [
                {
                    "content": item.content if hasattr(item, "content") else str(item),
                    "importance": item.importance if hasattr(item, "importance") else 0.5,
                    "timestamp": item.timestamp.isoformat() if hasattr(item, "timestamp") else None,
                }
                for item in items
            ],
            "total": len(items),
        }
    except Exception as e:
        return {"items": [], "total": 0, "error": str(e)}


# ============================================================================
# EXECUTION MONITORING (Advanced Subsystem)
# ============================================================================

@app.get("/api/execution/tasks")
async def get_execution_tasks(status: Optional[str] = None, limit: int = Query(50, le=200)):
    """Get execution tasks."""
    if not _execution_monitor:
        return {"tasks": [], "total": 0, "message": "Execution monitor not initialized"}

    try:
        tasks = _execution_monitor.get_tasks(status=status, limit=limit)
        return {
            "tasks": [
                {
                    "id": t.id if hasattr(t, "id") else None,
                    "name": t.name if hasattr(t, "name") else None,
                    "status": t.status if hasattr(t, "status") else None,
                    "started_at": t.started_at.isoformat() if hasattr(t, "started_at") else None,
                }
                for t in tasks
            ],
            "total": len(tasks),
        }
    except Exception as e:
        return {"tasks": [], "total": 0, "error": str(e)}


@app.get("/api/execution/statistics")
async def get_execution_statistics():
    """Get execution statistics."""
    if not _execution_monitor:
        return {"total_tasks": 0, "active_tasks": 0, "success_rate": 0.0}

    try:
        stats = _execution_monitor.get_statistics()
        return {
            "total_tasks": stats.get("total_tasks", 0),
            "active_tasks": stats.get("active_tasks", 0),
            "completed_tasks": stats.get("completed_tasks", 0),
            "success_rate": stats.get("success_rate", 0.0),
        }
    except Exception as e:
        return {"total_tasks": 0, "error": str(e)}


# ============================================================================
# SAFETY VALIDATION (Advanced Subsystem)
# ============================================================================

@app.get("/api/safety/validations")
async def get_safety_validations(limit: int = Query(50, le=200)):
    """Get safety validations."""
    if not _safety_store:
        return {"validations": [], "total": 0, "message": "Safety store not initialized"}

    try:
        checks = _safety_store.get_recent_checks(limit=limit)
        return {
            "validations": [
                {
                    "id": c.id if hasattr(c, "id") else None,
                    "check_type": c.check_type if hasattr(c, "check_type") else None,
                    "passed": c.passed if hasattr(c, "passed") else None,
                    "created_at": c.created_at.isoformat() if hasattr(c, "created_at") else None,
                }
                for c in checks
            ],
            "total": len(checks),
        }
    except Exception as e:
        return {"validations": [], "total": 0, "error": str(e)}


@app.get("/api/safety/statistics")
async def get_safety_statistics():
    """Get safety statistics."""
    if not _safety_store:
        return {"total_checks": 0, "passed": 0, "failed": 0}

    try:
        stats = _safety_store.get_statistics()
        return {
            "total_checks": stats.get("total_checks", 0),
            "passed": stats.get("passed", 0),
            "failed": stats.get("failed", 0),
            "safety_score": stats.get("safety_score", 0.0),
        }
    except Exception as e:
        return {"total_checks": 0, "error": str(e)}


# ============================================================================
# PERFORMANCE METRICS (Advanced Subsystem)
# ============================================================================

@app.get("/api/performance/metrics")
async def get_performance_metrics(limit: int = Query(100, le=500)):
    """Get performance metrics."""
    if not _performance_monitor:
        return {"metrics": [], "total": 0, "message": "Performance monitor not initialized"}

    try:
        metrics = await _performance_monitor.get_recent_metrics(limit=limit)
        return {
            "metrics": [
                {
                    "operation": m.operation if hasattr(m, "operation") else None,
                    "duration_ms": m.duration_ms if hasattr(m, "duration_ms") else None,
                    "timestamp": m.timestamp.isoformat() if hasattr(m, "timestamp") else None,
                }
                for m in metrics
            ],
            "total": len(metrics),
        }
    except Exception as e:
        return {"metrics": [], "total": 0, "error": str(e)}


@app.get("/api/performance/statistics")
async def get_performance_statistics():
    """Get performance statistics."""
    if not _performance_monitor:
        return {"avg_response_time": 0, "throughput": 0}

    try:
        stats = await _performance_monitor.get_statistics()
        return {
            "avg_response_time": stats.get("avg_response_time", 0),
            "p95_response_time": stats.get("p95_response_time", 0),
            "throughput": stats.get("throughput", 0),
            "total_operations": stats.get("total_operations", 0),
        }
    except Exception as e:
        return {"avg_response_time": 0, "error": str(e)}


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
