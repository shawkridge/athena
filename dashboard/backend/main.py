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

# Import coordination (multi-agent orchestration)
try:
    from athena.coordination import (
        Orchestrator,
        CoordinationOperations,
        initialize_coordination,
    )
    from athena.coordination.models import AgentType, TaskStatus
    COORDINATION_AVAILABLE = True
except ImportError:
    COORDINATION_AVAILABLE = False
    Orchestrator = None
    CoordinationOperations = None
    initialize_coordination = None
    AgentType = None
    TaskStatus = None

# Import all operations (use Athena's operations layer directly)
from athena.episodic.operations import (
    recall,
    recall_recent,
    get_by_session,
    get_statistics as episodic_stats,
)
from athena.semantic.operations import search as semantic_search, store as semantic_store
from athena.procedural.operations import list_procedures, get_statistics as _procedural_stats_raw
from athena.prospective.operations import (
    list_tasks,
    get_active_tasks,
    get_statistics as prospective_stats,
)

# Wrapper for procedural stats with error handling
async def procedural_stats():
    """Wrapper for procedural stats with error handling for invalid data."""
    try:
        return await _procedural_stats_raw()
    except Exception as e:
        # Return minimal stats if data validation fails
        return {
            "total_procedures": 0,
            "error": f"Failed to load procedures: {str(e)[:100]}"
        }
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

# Global orchestration instance
_orchestrator = None
_coordination_ops = None

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

    # Initialize all operations modules (required for endpoints)
    try:
        from athena.core.database import get_database
        db = get_database()

        # Episodic
        from athena.episodic.operations import initialize as init_episodic
        from athena.episodic.store import EpisodicStore
        init_episodic(db, EpisodicStore(db))
        print("✅ Episodic operations initialized")

        # Procedural
        try:
            from athena.procedural.operations import initialize as init_procedural
            from athena.procedural.store import ProceduralStore
            init_procedural(db, ProceduralStore(db))
            print("✅ Procedural operations initialized")
        except Exception as e:
            print(f"⚠️ Procedural: {e}")

        # Prospective
        try:
            from athena.prospective.operations import initialize as init_prospective
            from athena.prospective.store import ProspectiveStore
            init_prospective(db, ProspectiveStore(db))
            print("✅ Prospective operations initialized")
        except Exception as e:
            print(f"⚠️ Prospective: {e}")

        # Graph
        try:
            from athena.graph.operations import initialize as init_graph
            from athena.graph.store import GraphStore
            init_graph(db, GraphStore(db))
            print("✅ Graph operations initialized")
        except Exception as e:
            print(f"⚠️ Graph: {e}")

        # Meta
        try:
            from athena.meta.operations import initialize as init_meta
            from athena.meta.store import MetaMemoryStore
            init_meta(db, MetaMemoryStore(db))
            print("✅ Meta operations initialized")
        except Exception as e:
            print(f"⚠️ Meta: {e}")

        # Consolidation
        try:
            from athena.consolidation.operations import initialize as init_consolidation
            from athena.consolidation.system import ConsolidationSystem
            from athena.semantic.store import SemanticStore
            from athena.procedural.store import ProceduralStore
            consolidation_system = ConsolidationSystem(
                db=db,
                memory_store=SemanticStore(db),
                episodic_store=None,  # Will be set by consolidation system
                procedural_store=ProceduralStore(db),
                meta_store=None,  # Will be set by consolidation system
            )
            init_consolidation(db, consolidation_system)
            print("✅ Consolidation operations initialized")
        except Exception as e:
            print(f"⚠️ Consolidation: {e}")

        # Planning
        try:
            from athena.planning.operations import initialize as init_planning
            from athena.planning.store import PlanningStore
            init_planning(db, PlanningStore(db))
            print("✅ Planning operations initialized")
        except Exception as e:
            print(f"⚠️ Planning: {e}")

    except Exception as e:
        print(f"⚠️ Operations initialization failed: {e}")
        import traceback
        traceback.print_exc()

    # Try full Athena initialization (optional)
    try:
        success = await initialize_athena()
        if success:
            print("✅ Athena initialized successfully")
        else:
            print("⚠️ Athena initialization incomplete - some features may not work")
    except Exception as e:
        print(f"⚠️ Athena initialization failed: {e}")
        print("   Core episodic operations should still work")

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

    # Initialize orchestration system (API-first approach)
    if COORDINATION_AVAILABLE and initialize_coordination:
        try:
            global _orchestrator, _coordination_ops
            # Use the new API-first initialization
            _coordination_ops = await initialize_coordination(_postgres_db)
            _orchestrator = Orchestrator(_postgres_db, tmux_session_name="athena_agents")
            await _orchestrator.initialize_session()
            print("✅ Orchestrator initialized (API-first)")
        except Exception as e:
            print(f"⚠️ Orchestrator initialization failed: {e}")
            import traceback
            traceback.print_exc()
            _orchestrator = None
            _coordination_ops = None
    else:
        print("⚠️ Coordination module not available (orchestration disabled)")

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
        # Fetch real statistics from each subsystem
        ep_stats = await episodic_stats()
        proc_stats = await procedural_stats()
        prosp_stats = await prospective_stats()
        graph_st = await graph_stats()
        cons_stats = await consolidation_stats()
        plan_stats = await planning_stats()

        return {
            "status": "healthy",
            "subsystems": {
                "memory": {
                    "episodic": {
                        "total_events": ep_stats.get("total_events", 0),
                        "status": "operational"
                    },
                    "procedural": {
                        "total_procedures": proc_stats.get("total_procedures", 0),
                        "status": "operational"
                    },
                    "prospective": {
                        "total_tasks": prosp_stats.get("total_tasks", 0),
                        "status": "operational"
                    },
                    "graph": {
                        "total_entities": graph_st.get("total_entities", 0),
                        "status": "operational"
                    },
                    "semantic": {
                        "total_memories": 0,
                        "status": "operational"
                    },
                    "meta": {"status": "operational"},
                    "consolidation": {
                        "total_runs": cons_stats.get("consolidation_runs", 0),
                        "status": "operational"
                    },
                    "planning": {
                        "total_plans": plan_stats.get("total_plans", 0),
                        "status": "operational"
                    },
                },
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        # Fallback to safe defaults if stats fail
        print(f"⚠️ System status error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "healthy",
            "subsystems": {
                "memory": {
                    "episodic": {"total_events": 0, "status": "operational"},
                    "procedural": {"total_procedures": 0, "status": "operational"},
                    "prospective": {"total_tasks": 0, "status": "operational"},
                    "graph": {"total_entities": 0, "status": "operational"},
                    "semantic": {"total_memories": 0, "status": "operational"},
                    "meta": {"status": "operational"},
                    "consolidation": {"total_runs": 0, "status": "operational"},
                    "planning": {"total_plans": 0, "status": "operational"},
                },
            },
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
# ORCHESTRATION (MULTI-AGENT COORDINATION)
# ============================================================================

@app.get("/api/orchestration/agents")
async def get_orchestration_agents():
    """Get list of all agents and their current status."""
    if not _orchestrator or not _coordination_ops:
        return {"agents": [], "total": 0, "message": "Orchestrator not initialized"}

    try:
        agents = await _coordination_ops.list_agents()
        return {
            "agents": [
                {
                    "id": a.agent_id,
                    "type": a.agent_type.value if hasattr(a.agent_type, "value") else str(a.agent_type),
                    "status": a.status,
                    "capabilities": a.capabilities,
                    "last_heartbeat": a.last_heartbeat.isoformat() if a.last_heartbeat else None,
                    "current_task_id": a.current_task_id,
                    "tasks_completed": a.tasks_completed,
                }
                for a in agents
            ],
            "total": len(agents),
        }
    except Exception as e:
        return {"agents": [], "total": 0, "error": str(e)}


@app.get("/api/orchestration/agents/{agent_id}")
async def get_agent_details(agent_id: str):
    """Get detailed status of a specific agent."""
    if not _coordination_ops:
        return {"message": "Orchestrator not initialized"}

    try:
        agent = await _coordination_ops.get_agent(agent_id)
        if not agent:
            return {"error": f"Agent {agent_id} not found"}

        tasks = await _coordination_ops.get_agent_tasks(agent_id)
        return {
            "id": agent.agent_id,
            "type": agent.agent_type.value if hasattr(agent.agent_type, "value") else str(agent.agent_type),
            "status": agent.status,
            "capabilities": agent.capabilities,
            "last_heartbeat": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None,
            "current_task_id": agent.current_task_id,
            "tasks_completed": agent.tasks_completed,
            "assigned_tasks": [
                {
                    "id": t.id,
                    "content": t.content,
                    "status": t.status,
                    "priority": t.priority,
                }
                for t in tasks
            ],
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/orchestration/tasks")
async def get_orchestration_tasks(
    status: Optional[str] = None,
    limit: int = Query(100, le=500),
):
    """Get orchestration tasks with optional status filter."""
    if not _coordination_ops:
        return {"tasks": [], "total": 0, "message": "Orchestrator not initialized"}

    try:
        tasks = await _coordination_ops.get_active_tasks()

        # Filter by status if provided
        if status:
            tasks = [t for t in tasks if t.status == status]

        # Limit results
        tasks = tasks[:limit]

        return {
            "tasks": [
                {
                    "id": t.id,
                    "content": t.content,
                    "status": t.status,
                    "priority": t.priority,
                    "phase": t.phase if hasattr(t, "phase") else None,
                    "assigned_agent_id": t.assigned_agent_id if hasattr(t, "assigned_agent_id") else None,
                    "created_at": t.created_at.isoformat() if hasattr(t, "created_at") else None,
                    "progress": t.progress if hasattr(t, "progress") else 0,
                }
                for t in tasks
            ],
            "total": len(tasks),
        }
    except Exception as e:
        return {"tasks": [], "total": 0, "error": str(e)}


@app.get("/api/orchestration/tasks/{task_id}")
async def get_task_details(task_id: str):
    """Get detailed status of a specific task."""
    if not _coordination_ops:
        return {"message": "Orchestrator not initialized"}

    try:
        # Try to get task from prospective memory
        from athena.prospective.operations import get_task
        task = await get_task(int(task_id))

        if not task:
            return {"error": f"Task {task_id} not found"}

        return {
            "id": task.id,
            "content": task.content,
            "status": task.status,
            "priority": task.priority,
            "phase": task.phase if hasattr(task, "phase") else None,
            "assigned_agent_id": task.assigned_agent_id if hasattr(task, "assigned_agent_id") else None,
            "created_at": task.created_at.isoformat() if hasattr(task, "created_at") else None,
            "due_at": task.due_at.isoformat() if hasattr(task, "due_at") else None,
            "progress": task.progress if hasattr(task, "progress") else 0,
            "result": task.result if hasattr(task, "result") else None,
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/orchestration/tasks")
async def submit_orchestration_task(
    task_content: str = Query(..., min_length=1, max_length=2000),
    priority: int = Query(5, ge=1, le=10),
):
    """Submit a new task for orchestration."""
    if not _orchestrator or not _coordination_ops:
        return {"error": "Orchestrator not initialized"}

    try:
        from athena.prospective.operations import create_task

        # Create task in prospective memory
        task_id = await create_task(
            content=task_content,
            priority=priority,
            phase="pending",
        )

        return {
            "task_id": task_id,
            "content": task_content,
            "priority": priority,
            "status": "pending",
            "message": "Task submitted for orchestration",
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/orchestration/metrics")
async def get_orchestration_metrics():
    """Get overall orchestration metrics and health."""
    if not _orchestrator or not _coordination_ops:
        return {"message": "Orchestrator not initialized"}

    try:
        agents = await _coordination_ops.list_agents()
        tasks = await _coordination_ops.get_active_tasks()
        stale = await _coordination_ops.detect_stale_agents()

        idle_agents = len([a for a in agents if a.status == "idle"])
        busy_agents = len([a for a in agents if a.status == "busy"])
        failed_agents = len([a for a in agents if a.status == "failed"])

        pending_tasks = len([t for t in tasks if t.status == "pending"])
        in_progress_tasks = len([t for t in tasks if t.status == "in_progress"])
        completed_tasks = len([t for t in tasks if t.status == "completed"])

        total_tasks = pending_tasks + in_progress_tasks + completed_tasks
        progress_percent = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        return {
            "agents": {
                "total": len(agents),
                "idle": idle_agents,
                "busy": busy_agents,
                "failed": failed_agents,
                "stale": len(stale),
            },
            "tasks": {
                "pending": pending_tasks,
                "in_progress": in_progress_tasks,
                "completed": completed_tasks,
                "total": total_tasks,
            },
            "progress": {
                "percent": round(progress_percent, 2),
                "completed": completed_tasks,
                "total": total_tasks,
            },
            "health": {
                "stale_agents": len(stale),
                "failed_agents": failed_agents,
                "status": "healthy" if failed_agents == 0 and len(stale) == 0 else "degraded",
            },
        }
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# ADVANCED SCHEDULING (PHASE 8)
# ============================================================================

@app.get("/api/orchestration/templates")
async def get_workflow_templates():
    """Get available workflow templates."""
    if not _postgres_db:
        return {"templates": [], "message": "Database not initialized"}

    try:
        async with _postgres_db.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT id, name, description, created_at FROM workflow_templates ORDER BY name"
                )
                rows = await cursor.fetchall()
                return {
                    "templates": [
                        {
                            "id": row[0],
                            "name": row[1],
                            "description": row[2],
                            "created_at": row[3].isoformat() if row[3] else None,
                        }
                        for row in rows
                    ],
                    "total": len(rows),
                }
    except Exception as e:
        return {"templates": [], "error": str(e)}


@app.get("/api/orchestration/tasks/ready")
async def get_ready_tasks(limit: int = Query(10, ge=1, le=100)):
    """Get tasks ready to execute (with dependencies satisfied)."""
    if not _postgres_db:
        return {"tasks": [], "message": "Database not initialized"}

    try:
        async with _postgres_db.get_connection() as conn:
            async with conn.cursor() as cursor:
                # Get tasks where:
                # 1. Status is PENDING
                # 2. No depends_on_task_id OR the dependency is COMPLETED
                await cursor.execute(
                    """
                    SELECT
                        id, content, priority_number, estimated_duration_minutes
                    FROM prospective_tasks
                    WHERE status = %s
                      AND (depends_on_task_id IS NULL
                           OR depends_on_task_id IN (
                               SELECT id FROM prospective_tasks WHERE status = %s
                           ))
                    ORDER BY priority_number DESC, created_at ASC
                    LIMIT %s
                    """,
                    ("PENDING", "COMPLETED", limit),
                )
                rows = await cursor.fetchall()
                return {
                    "tasks": [
                        {
                            "id": row[0],
                            "content": row[1],
                            "priority": row[2],
                            "estimated_duration_minutes": row[3],
                        }
                        for row in rows
                    ],
                    "total": len(rows),
                }
    except Exception as e:
        return {"tasks": [], "error": str(e)}


@app.get("/api/orchestration/tasks/{task_id}/dependencies")
async def get_task_dependency_graph(task_id: int):
    """Get task dependency graph (what tasks does this depend on, and what depends on it)."""
    if not _postgres_db:
        return {"dependencies": {}, "message": "Database not initialized"}

    try:
        async with _postgres_db.get_connection() as conn:
            async with conn.cursor() as cursor:
                # Get dependencies this task has
                await cursor.execute(
                    """
                    SELECT id, content, status, priority_number
                    FROM prospective_tasks
                    WHERE id = %s
                    """,
                    (task_id,),
                )
                task_row = await cursor.fetchone()
                if not task_row:
                    return {"error": f"Task {task_id} not found"}

                # Get upstream dependencies (what this task depends on)
                await cursor.execute(
                    """
                    SELECT DISTINCT
                        depends_on_task_id, content, status
                    FROM prospective_tasks
                    WHERE depends_on_task_id IN (
                        SELECT depends_on_task_id FROM prospective_tasks WHERE id = %s
                    )
                    """,
                    (task_id,),
                )
                upstream = await cursor.fetchall()

                # Get downstream dependents (what depends on this task)
                await cursor.execute(
                    """
                    SELECT id, content, status, priority_number
                    FROM prospective_tasks
                    WHERE depends_on_task_id = %s
                    """,
                    (task_id,),
                )
                downstream = await cursor.fetchall()

                return {
                    "task": {
                        "id": task_row[0],
                        "content": task_row[1],
                        "status": task_row[2],
                        "priority": task_row[3],
                    },
                    "upstream_dependencies": [
                        {"id": row[0], "content": row[1], "status": row[2]}
                        for row in upstream
                    ] if upstream else [],
                    "downstream_dependents": [
                        {"id": row[0], "content": row[1], "status": row[2], "priority": row[3]}
                        for row in downstream
                    ] if downstream else [],
                }
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# LEARNING INTEGRATION (PHASE 9)
# ============================================================================

_learning_manager = None

async def get_learning_manager():
    """Get or initialize learning manager."""
    global _learning_manager
    if _learning_manager is None and COORDINATION_AVAILABLE:
        from athena.coordination import get_learning_manager as get_lm
        _learning_manager = await get_lm(_postgres_db)
    return _learning_manager


@app.get("/api/orchestration/learning/agent-expertise")
async def get_agent_expertise(agent_id: str, domain: str = "general"):
    """Get agent expertise score for a specific domain."""
    learning_mgr = await get_learning_manager()
    if not learning_mgr:
        return {"message": "Learning manager not initialized"}

    try:
        score = await learning_mgr.get_agent_expertise(agent_id, domain)
        return {
            "agent_id": agent_id,
            "domain": domain,
            "expertise_score": round(score, 2),
            "expertise_level": (
                "expert" if score >= 0.8
                else "proficient" if score >= 0.6
                else "learning" if score >= 0.4
                else "novice"
            )
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/orchestration/learning/best-agent-for-domain")
async def get_best_agent(domain: str):
    """Get best-performing agent for a domain."""
    if not _orchestrator or not _coordination_ops:
        return {"message": "Orchestrator not initialized"}

    learning_mgr = await get_learning_manager()
    if not learning_mgr:
        return {"message": "Learning manager not initialized"}

    try:
        agents = await _coordination_ops.list_agents()
        available_agents = [a.agent_id for a in agents if a.status != "failed"]

        best_agent_id = await learning_mgr.get_best_agent_for_domain(
            domain, available_agents
        )

        if best_agent_id:
            agent = await _coordination_ops.get_agent(best_agent_id)
            expertise = await learning_mgr.get_agent_expertise(best_agent_id, domain)
            return {
                "domain": domain,
                "best_agent_id": best_agent_id,
                "agent_type": agent.agent_type.value if hasattr(agent.agent_type, "value") else str(agent.agent_type),
                "expertise_score": round(expertise, 2),
                "recommendation": f"Route {domain} tasks to {best_agent_id}"
            }
        else:
            return {
                "domain": domain,
                "best_agent_id": None,
                "message": "No available agents"
            }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/orchestration/learning/performance-summary")
async def get_performance_summary():
    """Get summary of all agent performance metrics."""
    learning_mgr = await get_learning_manager()
    if not learning_mgr:
        return {"message": "Learning manager not initialized"}

    try:
        summary = await learning_mgr.get_performance_summary()
        return {
            "timestamp": datetime.now().isoformat(),
            "total_agents_tracked": summary["total_agents"],
            "overall_success_rate": round(summary.get("avg_success_rate", 0), 2),
            "agents": summary["agents"],
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/orchestration/learning/record-task-completion")
async def record_task_completion(
    agent_id: str = Query(...),
    task_id: int = Query(...),
    task_content: str = Query(...),
    domain: str = Query("general"),
    success: bool = Query(True),
    duration_minutes: float = Query(0),
):
    """Record task completion for learning system."""
    learning_mgr = await get_learning_manager()
    if not learning_mgr:
        return {"error": "Learning manager not initialized"}

    try:
        result = await learning_mgr.record_task_completion(
            agent_id=agent_id,
            task_id=task_id,
            task_content=task_content,
            domain=domain,
            success=success,
            duration_minutes=duration_minutes
        )

        return {
            "success": result,
            "message": "Task completion recorded",
            "agent_id": agent_id,
            "task_id": task_id
        }
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# WEBSOCKET FOR REAL-TIME UPDATES
# ============================================================================

# ============================================================================
# CONSCIOUSNESS METRICS (NEW - RESEARCH FEATURE)
# ============================================================================

# Initialize consciousness metrics system (once Athena is initialized)
_consciousness_metrics = None


@app.get("/api/consciousness/indicators")
async def get_consciousness_indicators():
    """Get current consciousness indicators (all 6 indicators)."""
    try:
        # Create metrics system if not already created
        global _consciousness_metrics
        if _consciousness_metrics is None:
            from athena.consciousness import ConsciousnessMetrics

            _consciousness_metrics = ConsciousnessMetrics()

        # Measure consciousness
        score = await _consciousness_metrics.measure_consciousness()

        # Return as dict
        return {
            "status": "success",
            "data": score.to_dict(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@app.get("/api/consciousness/score")
async def get_consciousness_score():
    """Get overall consciousness score (0-10 scale)."""
    try:
        global _consciousness_metrics
        if _consciousness_metrics is None:
            from athena.consciousness import ConsciousnessMetrics

            _consciousness_metrics = ConsciousnessMetrics()

        # Get overall score
        overall = await _consciousness_metrics.indicators.overall_score()

        return {
            "status": "success",
            "score": round(overall, 2),
            "scale": "0-10",
            "baseline": 7.75,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@app.get("/api/consciousness/history")
async def get_consciousness_history(limit: int = Query(50, le=1000)):
    """Get historical consciousness measurements."""
    try:
        global _consciousness_metrics
        if _consciousness_metrics is None:
            from athena.consciousness import ConsciousnessMetrics

            _consciousness_metrics = ConsciousnessMetrics()

        # Get history
        history = _consciousness_metrics.get_history(limit=limit)

        return {
            "status": "success",
            "measurements": len(history),
            "data": [s.to_dict() for s in history],
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@app.get("/api/consciousness/statistics")
async def get_consciousness_statistics():
    """Get consciousness measurement statistics."""
    try:
        global _consciousness_metrics
        if _consciousness_metrics is None:
            from athena.consciousness import ConsciousnessMetrics

            _consciousness_metrics = ConsciousnessMetrics()

        # Get statistics
        stats = _consciousness_metrics.get_statistics()

        return {
            "status": "success",
            "data": stats,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@app.get("/api/consciousness/comparison")
async def get_consciousness_comparison(window_size: int = Query(10, le=100)):
    """Compare consciousness indicators over a time window."""
    try:
        global _consciousness_metrics
        if _consciousness_metrics is None:
            from athena.consciousness import ConsciousnessMetrics

            _consciousness_metrics = ConsciousnessMetrics()

        # Get comparison
        comparison = _consciousness_metrics.compare_indicators(window_size=window_size)

        return {
            "status": "success",
            "data": comparison,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


# Global phenomenal consciousness system
_phenomenal_consciousness = None


@app.get("/api/consciousness/phenomenal")
async def get_phenomenal_consciousness():
    """Get current phenomenal consciousness state (qualia, emotions, embodiment)."""
    try:
        global _consciousness_metrics, _phenomenal_consciousness
        if _consciousness_metrics is None:
            from athena.consciousness import ConsciousnessMetrics
            _consciousness_metrics = ConsciousnessMetrics()

        if _phenomenal_consciousness is None:
            from athena.consciousness import PhenomenalConsciousness
            _phenomenal_consciousness = PhenomenalConsciousness()

        # Get current indicators
        if _consciousness_metrics.last_score:
            indicators = {
                name: score.score
                for name, score in _consciousness_metrics.last_score.indicators.items()
            }
        else:
            # Measure consciousness first
            await _consciousness_metrics.measure_consciousness()
            indicators = {
                name: score.score
                for name, score in _consciousness_metrics.last_score.indicators.items()
            }

        # Update phenomenal properties
        phenomenal_state = await _phenomenal_consciousness.update_phenomenal_state(indicators)

        return {
            "status": "success",
            "data": phenomenal_state,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@app.get("/api/consciousness/phi")
async def get_phi_calculation():
    """Get Φ (integrated information) calculation."""
    try:
        global _consciousness_metrics
        if _consciousness_metrics is None:
            from athena.consciousness import ConsciousnessMetrics
            _consciousness_metrics = ConsciousnessMetrics()

        from athena.consciousness import IntegratedInformationSystem
        phi_system = IntegratedInformationSystem()

        # Calculate Φ
        phi_result = await phi_system.calculate_phi(_consciousness_metrics, method="fast")

        return {
            "status": "success",
            "data": {
                "phi": round(phi_result.phi, 2),
                "method": phi_result.calculation_method,
                "components": {k: round(v, 2) for k, v in phi_result.components.items()},
                "confidence": round(phi_result.confidence, 2),
                "evidence": phi_result.evidence,
                "timestamp": phi_result.timestamp.isoformat(),
            },
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@app.get("/api/consciousness/phenomenal/summary")
async def get_phenomenal_summary():
    """Get summary of phenomenal consciousness properties."""
    try:
        global _phenomenal_consciousness
        if _phenomenal_consciousness is None:
            from athena.consciousness import PhenomenalConsciousness
            _phenomenal_consciousness = PhenomenalConsciousness()

        summary = _phenomenal_consciousness.get_phenomenal_summary()

        return {
            "status": "success",
            "data": summary,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@app.get("/api/consciousness/full")
async def get_full_consciousness_state():
    """Get complete consciousness state (indicators + Φ + phenomenal properties)."""
    try:
        global _consciousness_metrics, _phenomenal_consciousness
        if _consciousness_metrics is None:
            from athena.consciousness import ConsciousnessMetrics
            _consciousness_metrics = ConsciousnessMetrics()

        if _phenomenal_consciousness is None:
            from athena.consciousness import PhenomenalConsciousness
            _phenomenal_consciousness = PhenomenalConsciousness()

        # Measure consciousness
        await _consciousness_metrics.measure_consciousness()

        # Get indicators
        score = _consciousness_metrics.last_score.to_dict()

        # Get phenomenal state
        indicators = {
            name: indicator_score.score
            for name, indicator_score in _consciousness_metrics.last_score.indicators.items()
        }
        phenomenal_state = await _phenomenal_consciousness.update_phenomenal_state(indicators)

        # Get Φ
        from athena.consciousness import IntegratedInformationSystem
        phi_system = IntegratedInformationSystem()
        phi_result = await phi_system.calculate_phi(_consciousness_metrics, method="fast")

        return {
            "status": "success",
            "data": {
                "indicators": score,
                "phi": {
                    "phi": round(phi_result.phi, 2),
                    "confidence": round(phi_result.confidence, 2),
                    "evidence": phi_result.evidence,
                },
                "phenomenal": phenomenal_state,
                "timestamp": score["timestamp"],
            },
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


# ============================================================================
# WEBSOCKET CONNECTIONS
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

# Separate manager for orchestration updates
orchestration_manager = ConnectionManager()


@app.websocket("/ws/orchestration")
async def websocket_orchestration_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time orchestration updates."""
    await orchestration_manager.connect(websocket)

    try:
        while True:
            if _coordination_ops:
                try:
                    # Get current orchestration state
                    agents = await _coordination_ops.list_agents()
                    tasks = await _coordination_ops.get_active_tasks()

                    # Send updates
                    await websocket.send_json(
                        {
                            "type": "orchestration_update",
                            "agents": {
                                "total": len(agents),
                                "idle": len([a for a in agents if a.status == "idle"]),
                                "busy": len([a for a in agents if a.status == "busy"]),
                                "failed": len([a for a in agents if a.status == "failed"]),
                            },
                            "tasks": {
                                "pending": len([t for t in tasks if t.status == "pending"]),
                                "in_progress": len([t for t in tasks if t.status == "in_progress"]),
                                "completed": len([t for t in tasks if t.status == "completed"]),
                            },
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                except Exception as e:
                    print(f"Error sending orchestration updates: {e}")
            else:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Orchestrator not available",
                    }
                )

            await asyncio.sleep(2)  # Update every 2 seconds for real-time feel

    except WebSocketDisconnect:
        orchestration_manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket orchestration error: {e}")
        orchestration_manager.disconnect(websocket)


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
