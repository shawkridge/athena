"""
Unified test client for benchmarking.

Wraps underlying Memory-MCP stores to provide a consistent interface for testing.
"""

from pathlib import Path
from athena.memory.store import MemoryStore
from athena.integration import IntegratedEpisodicStore
from athena.spatial.store import SpatialStore
from athena.manager import UnifiedMemoryManager
from athena.procedural.store import ProceduralStore
from athena.prospective.store import ProspectiveStore
from athena.graph.store import GraphStore
from athena.meta.store import MetaMemoryStore
from athena.consolidation.system import ConsolidationSystem
from athena.projects import ProjectManager


class MemoryTestClient:
    """Unified test client for memory-mcp benchmarking."""

    def __init__(self, db_path: str | Path, use_memory_mcp: bool = False):
        """Initialize test client.

        Args:
            db_path: Path to SQLite database
            use_memory_mcp: If True, use IntegratedEpisodicStore + full system.
                           If False, use basic MemoryStore (vector only).
        """
        self.db_path = db_path
        self.use_memory_mcp = use_memory_mcp

        if use_memory_mcp:
            # Full memory-mcp system
            self.store = MemoryStore(str(db_path))
            self.project_manager = ProjectManager(self.store)

            self.spatial_store = SpatialStore(self.store.db)
            self.episodic_store = IntegratedEpisodicStore(
                self.store.db,
                spatial_store=self.spatial_store,
                auto_spatial=True,
                auto_temporal=True,
                temporal_batch_size=10
            )
            self.procedural_store = ProceduralStore(self.store.db)
            self.prospective_store = ProspectiveStore(self.store.db)
            self.graph_store = GraphStore(self.store.db)
            self.meta_store = MetaMemoryStore(self.store.db)
            self.consolidation_system = ConsolidationSystem(
                self.store.db,
                self.store,
                self.episodic_store.episodic_store,
                self.procedural_store,
                self.meta_store
            )

            self.manager = UnifiedMemoryManager(
                semantic=self.store,
                episodic=self.episodic_store,
                procedural=self.procedural_store,
                prospective=self.prospective_store,
                graph=self.graph_store,
                meta=self.meta_store,
                consolidation=self.consolidation_system,
                project_manager=self.project_manager,
                enable_advanced_rag=False
            )
        else:
            # Baseline: vector DB only
            self.store = MemoryStore(str(db_path))
            self.episodic_store = None
            self.manager = None

    def record_event(self, content: str, context: dict = None) -> None:
        """Record an event (use episodic memory if available)."""
        if self.use_memory_mcp and self.episodic_store:
            # Convert context to proper format
            from athena.episodic.models import EventContext
            ctx = EventContext(
                files=context.get("files", []) if context else [],
                phase=context.get("phase") if context else None,
                task=context.get("task") if context else None
            )
            self.episodic_store.record_event(
                content=content,
                context=ctx,
                event_type="action"
            )
        else:
            # Baseline: just remember as semantic memory
            self.store.remember(content, memory_type="fact")

    def smart_retrieve(self, query: str, k: int = 5) -> list:
        """Retrieve memories with advanced RAG if available."""
        if self.use_memory_mcp and self.manager:
            try:
                results = self.manager.smart_retrieve(query, k=k)
                return results if results else []
            except Exception:
                # Fallback to basic retrieval
                return self.store.recall(query, k=k)
        else:
            # Baseline: vector search only
            results = self.store.recall(query, k=k)
            return results if results else []

    def remember(self, content: str, memory_type: str = "fact") -> None:
        """Remember a fact in semantic memory."""
        self.store.remember(content, memory_type=memory_type)

    def recall(self, query: str, k: int = 5) -> list:
        """Recall memories using semantic search."""
        results = self.store.recall(query, k=k)
        return results if results else []

    def optimize(self) -> None:
        """Optimize memory (consolidate if available)."""
        if self.use_memory_mcp and hasattr(self.episodic_store, 'optimize'):
            try:
                self.episodic_store.optimize()
            except Exception:
                pass
        if self.store and hasattr(self.store, 'optimize'):
            try:
                self.store.optimize()
            except Exception:
                pass
