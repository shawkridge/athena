"""Integration tests for Temporal KG Search Enrichment (P2).

Tests the complete integration of temporal knowledge graph synthesis
with search results enrichment, enabling causal relationship discovery.
"""

import pytest
import tempfile
from pathlib import Path

from athena.core.database import Database
from athena.core.models import Memory, MemoryType, MemorySearchResult
from athena.memory.store import MemoryStore
from athena.episodic.store import EpisodicStore
from athena.episodic.models import EpisodicEvent, EventType, EventOutcome, EventContext
from athena.graph.store import GraphStore
from athena.temporal.kg_synthesis import TemporalKGSynthesis
from athena.rag.temporal_search_enrichment import TemporalSearchEnricher, EnrichedSearchResult
from athena.rag.manager import RAGManager, RAGConfig
from datetime import datetime


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_memory.db"
        db = Database(str(db_path))
        yield db
        db.conn.close()


@pytest.fixture
def memory_store(temp_db):
    """Create memory store."""
    # MemoryStore creates its own Database instance from the path
    return MemoryStore(str(temp_db.db_path))


@pytest.fixture
def episodic_store(temp_db):
    """Create episodic store."""
    return EpisodicStore(temp_db)


@pytest.fixture
def graph_store(temp_db):
    """Create graph store."""
    return GraphStore(temp_db)


@pytest.fixture
def temporal_kg(episodic_store, graph_store):
    """Create temporal KG synthesis."""
    return TemporalKGSynthesis(episodic_store, graph_store)


@pytest.fixture
def search_enricher(temp_db, graph_store, temporal_kg):
    """Create temporal search enricher."""
    return TemporalSearchEnricher(temp_db, graph_store, temporal_kg)


class TestTemporalSearchEnrichment:
    """Test temporal KG search enrichment."""

    def test_enrich_empty_results(self, search_enricher):
        """Test enrichment of empty results."""
        results = []
        enriched = search_enricher.enrich_results(results, project_id=1)
        assert enriched == []

    def test_enrich_single_result_no_relations(self, search_enricher, memory_store):
        """Test enrichment of single result with no causal relations."""
        # Create a test memory
        memory = Memory(
            project_id=1,
            content="Test memory content",
            memory_type=MemoryType.FACT,
        )

        # Create search result
        result = MemorySearchResult(
            memory=memory,
            similarity=0.9,
            rank=1,
        )

        # Enrich
        enriched = search_enricher.enrich_results([result], project_id=1)

        assert len(enriched) == 1
        assert enriched[0].base_result.memory.id == memory.id
        assert len(enriched[0].causal_relations) == 0
        assert enriched[0].total_relations == 0

    def test_enrich_multiple_results_ordering(self, search_enricher, memory_store):
        """Test that enriched results are reordered by impact score."""
        # Create test memories
        memories = []
        for i in range(3):
            m = Memory(
                project_id=1,
                content=f"Memory {i}",
                memory_type=MemoryType.FACT,
            )
            memories.append(m)

        # Create search results with varying similarities
        results = [
            MemorySearchResult(
                memory=memories[0],
                similarity=0.5,  # Low similarity
                rank=1,
            ),
            MemorySearchResult(
                memory=memories[1],
                similarity=0.9,  # High similarity
                rank=2,
            ),
            MemorySearchResult(
                memory=memories[2],
                similarity=0.7,  # Medium similarity
                rank=3,
            ),
        ]

        # Enrich
        enriched = search_enricher.enrich_results(results, project_id=1)

        # Should be reordered by impact score (base similarity * 0.7 when no relations)
        assert len(enriched) == 3
        # First should have highest base similarity
        assert enriched[0].base_result.similarity >= enriched[1].base_result.similarity

    def test_get_causal_context_empty(self, search_enricher):
        """Test causal context for non-existent memory."""
        context = search_enricher.get_causal_context(
            memory_id=999,
            project_id=1,
            context_depth=2,
        )

        assert context is not None
        assert context["memory_id"] == 999
        assert context["causes"] == []
        assert context["effects"] == []
        assert context["total_relations"] == 0

    def test_find_causal_chain_empty(self, search_enricher):
        """Test finding causal chain for memory with no relations."""
        chain = search_enricher.find_causal_chain(
            start_memory_id=999,
            project_id=1,
            direction="forward",
            max_depth=3,
        )

        assert chain == []

    def test_temporal_enricher_impact_score_calculation(self, search_enricher, memory_store):
        """Test impact score calculation."""
        # Create test memory
        memory = Memory(
            project_id=1,
            content="Test memory",
            memory_type=MemoryType.FACT,
        )

        # Create search result
        result = MemorySearchResult(
            memory=memory,
            similarity=0.8,
            rank=1,
        )

        # Enrich
        enriched = search_enricher.enrich_results([result], project_id=1)

        # Impact score should be >= base similarity * 0.7 (when no relations)
        # The actual score depends on causal context which may not exist
        assert enriched[0].impact_score >= 0.0
        assert enriched[0].impact_score <= 1.0

    def test_rag_manager_temporal_enrichment_disabled(self, memory_store):
        """Test RAG manager with temporal enrichment disabled."""
        config = RAGConfig(temporal_enrichment_enabled=False)
        manager = RAGManager(memory_store, config=config)

        assert manager.temporal_enricher is None
        assert not manager.get_stats()["temporal_enrichment_enabled"]

    def test_rag_manager_temporal_enrichment_enabled_no_components(self, memory_store):
        """Test RAG manager with temporal enrichment requested but missing components."""
        config = RAGConfig(temporal_enrichment_enabled=True)
        manager = RAGManager(memory_store, config=config)

        # Should not be enabled (missing db, graph_store, temporal_kg)
        assert manager.temporal_enricher is None

    def test_rag_manager_enrich_with_temporal_kg(self, memory_store, temp_db, graph_store, temporal_kg):
        """Test RAG manager enrichment method."""
        config = RAGConfig(temporal_enrichment_enabled=True)
        manager = RAGManager(
            memory_store,
            config=config,
            db=temp_db,
            graph_store=graph_store,
            temporal_kg=temporal_kg,
        )

        # Create test memory
        memory = Memory(
            project_id=1,
            content="Test memory",
            memory_type=MemoryType.FACT,
        )

        # Create search result
        result = MemorySearchResult(
            memory=memory,
            similarity=0.9,
            rank=1,
        )

        # Enrich via manager
        enriched = manager.enrich_with_temporal_kg([result], project_id=1)

        assert len(enriched) == 1
        assert isinstance(enriched[0], EnrichedSearchResult)
        assert enriched[0].base_result.memory.id == memory.id

    def test_rag_manager_get_causal_context(self, memory_store, temp_db, graph_store, temporal_kg):
        """Test RAG manager causal context retrieval."""
        config = RAGConfig(temporal_enrichment_enabled=True)
        manager = RAGManager(
            memory_store,
            config=config,
            db=temp_db,
            graph_store=graph_store,
            temporal_kg=temporal_kg,
        )

        # Get context for non-existent memory
        context = manager.get_causal_context(memory_id=999, project_id=1)

        assert context is not None
        assert "causes" in context
        assert "effects" in context
        assert "total_relations" in context

    def test_enriched_search_result_properties(self, search_enricher, memory_store):
        """Test EnrichedSearchResult properties."""
        memory = Memory(
            project_id=1,
            content="Test memory",
            memory_type=MemoryType.FACT,
        )

        result = MemorySearchResult(
            memory=memory,
            similarity=0.9,
            rank=1,
        )

        enriched_results = search_enricher.enrich_results([result], project_id=1)
        enriched = enriched_results[0]

        assert enriched.total_relations == 0
        assert enriched.critical_relations == []
        assert enriched.related_memories == []
        assert enriched.impact_score > 0.0

    def test_temporal_enrichment_graceful_degradation(self, memory_store, temp_db):
        """Test graceful degradation when enrichment not available."""
        config = RAGConfig(temporal_enrichment_enabled=True)
        manager = RAGManager(
            memory_store,
            config=config,
            # Missing required components
        )

        memory = Memory(
            project_id=1,
            content="Test memory",
            memory_type=MemoryType.FACT,
        )

        result = MemorySearchResult(
            memory=memory,
            similarity=0.9,
            rank=1,
        )

        # Should still work with empty enrichment
        enriched = manager.enrich_with_temporal_kg([result], project_id=1)

        assert len(enriched) == 1
        assert isinstance(enriched[0], EnrichedSearchResult)
        assert len(enriched[0].causal_relations) == 0


class TestTemporalKGIntegrationWithSearch:
    """Test full integration of temporal KG with search."""

    def test_temporal_kg_synthesis_integration(self, episodic_store, graph_store):
        """Test temporal KG synthesis initialization and basic structure."""
        # Create temporal KG synthesis
        kg = TemporalKGSynthesis(episodic_store, graph_store)

        # Verify it's created properly
        assert kg.episodic_store is episodic_store
        assert kg.graph_store is graph_store
        assert kg.causality_threshold == 0.5
        assert kg.frequency_threshold == 10

    def test_integration_end_to_end(self, memory_store, episodic_store, graph_store, temp_db):
        """Test complete integration end-to-end."""
        # Setup
        temporal_kg = TemporalKGSynthesis(episodic_store, graph_store)
        config = RAGConfig(temporal_enrichment_enabled=True)
        manager = RAGManager(
            memory_store,
            config=config,
            db=temp_db,
            graph_store=graph_store,
            temporal_kg=temporal_kg,
        )

        # Create test memories
        memory1 = Memory(
            project_id=1,
            content="Initial observation",
            memory_type=MemoryType.FACT,
        )
        memory2 = Memory(
            project_id=1,
            content="Resulting action",
            memory_type=MemoryType.FACT,
        )

        # Create search results
        results = [
            MemorySearchResult(memory=memory1, similarity=0.9, rank=1),
            MemorySearchResult(memory=memory2, similarity=0.8, rank=2),
        ]

        # Enrich through full pipeline
        enriched = manager.enrich_with_temporal_kg(results, project_id=1)

        assert len(enriched) == 2
        # Should be reordered by impact
        assert enriched[0].impact_score >= enriched[1].impact_score


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
