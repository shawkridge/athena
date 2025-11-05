"""Integration tests for manager meta-memory queries."""

import pytest
from datetime import datetime

from athena.core.database import Database
from athena.core.models import MemoryType
from athena.memory.store import MemoryStore
from athena.projects.manager import ProjectManager
from athena.episodic.store import EpisodicStore
from athena.procedural.store import ProceduralStore
from athena.prospective.store import ProspectiveStore
from athena.graph.store import GraphStore
from athena.meta.store import MetaMemoryStore
from athena.meta.models import DomainCoverage, ExpertiseLevel
from athena.consolidation.system import ConsolidationSystem
from athena.manager import UnifiedMemoryManager


@pytest.fixture
def test_manager(tmp_path):
    """Create test manager with all stores."""
    db_path = tmp_path / "test.db"
    db = Database(db_path)

    # Initialize all stores
    semantic_store = MemoryStore(db_path)
    project_manager = ProjectManager(semantic_store)
    episodic_store = EpisodicStore(db)
    procedural_store = ProceduralStore(db)
    prospective_store = ProspectiveStore(db)
    graph_store = GraphStore(db)
    meta_store = MetaMemoryStore(db)
    consolidation = ConsolidationSystem(
        db, semantic_store, episodic_store, procedural_store, meta_store
    )

    # Create manager
    manager = UnifiedMemoryManager(
        semantic=semantic_store,
        episodic=episodic_store,
        procedural=procedural_store,
        prospective=prospective_store,
        graph=graph_store,
        meta=meta_store,
        consolidation=consolidation,
        project_manager=project_manager,
    )

    # Create test project
    project_manager.get_or_create_project()

    return manager


def test_meta_memory_query_no_crash(test_manager):
    """Verify meta-memory queries don't crash with AttributeError."""
    # This should not raise AttributeError about get_domain_coverage
    result = test_manager.retrieve("what do we know about python")

    # Should return meta results (even if empty)
    assert isinstance(result, dict)


def test_meta_memory_with_domain_coverage(test_manager):
    """Test meta-memory query with actual domain coverage data."""
    # Add domain coverage
    coverage = DomainCoverage(
        domain="python",
        category="programming",
        memory_count=5,
        episodic_count=3,
        procedural_count=1,
        entity_count=2,
        avg_confidence=0.9,
        avg_usefulness=0.85,
        last_updated=datetime.now(),
        gaps=[],
        strength_areas=["typing", "async"],
        first_encounter=datetime.now(),
        expertise_level=ExpertiseLevel.INTERMEDIATE
    )

    test_manager.meta.create_domain(coverage)

    # Query for this domain
    result = test_manager.retrieve("what do we know about python")

    assert 'meta' in result
    meta = result['meta']
    assert meta['domain'] == 'python'
    assert meta['memory_count'] == 5
    assert meta['expertise_level'] == 'intermediate'


def test_meta_memory_list_all_domains(test_manager):
    """Test listing all domain coverages."""
    # Add multiple domains
    for domain_name in ['python', 'javascript', 'rust']:
        coverage = DomainCoverage(
            domain=domain_name,
            category="programming",
            memory_count=10,
            episodic_count=5,
            procedural_count=2,
            entity_count=3,
            avg_confidence=0.8,
            avg_usefulness=0.75,
            last_updated=datetime.now(),
            gaps=[],
            strength_areas=[],
            first_encounter=datetime.now(),
            expertise_level=ExpertiseLevel.BEGINNER
        )
        test_manager.meta.create_domain(coverage)

    # Query without specific domain
    result = test_manager.retrieve("what do we know")

    assert 'meta' in result
    meta = result['meta']
    assert 'domains' in meta
    assert len(meta['domains']) == 3

    domain_names = [d['domain'] for d in meta['domains']]
    assert 'python' in domain_names
    assert 'javascript' in domain_names
    assert 'rust' in domain_names


def test_manager_meta_query_method_directly(test_manager):
    """Test _query_meta method directly."""
    # Add test coverage
    coverage = DomainCoverage(
        domain="testing",
        category="development",
        memory_count=3,
        episodic_count=2,
        procedural_count=1,
        entity_count=0,
        avg_confidence=0.95,
        avg_usefulness=0.90,
        last_updated=datetime.now(),
        gaps=["performance"],
        strength_areas=["unit-tests"],
        first_encounter=datetime.now(),
        expertise_level=ExpertiseLevel.ADVANCED
    )

    test_manager.meta.create_domain(coverage)

    # Call _query_meta directly
    result = test_manager._query_meta("what about testing", {})

    assert result is not None
    assert result['domain'] == 'testing'
    assert result['expertise_level'] == 'advanced'
    assert result['memory_count'] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
