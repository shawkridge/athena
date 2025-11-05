"""Tests for meta-memory quality tracking and domain analysis."""

from datetime import datetime, timedelta

import pytest

from athena.core.database import Database
from athena.episodic.models import EpisodicEvent, EventContext, EventType
from athena.episodic.store import EpisodicStore
from athena.meta.analysis import analyze_domain_coverage, detect_knowledge_gaps
from athena.meta.models import DomainCoverage, ExpertiseLevel, KnowledgeTransfer, MemoryQuality
from athena.meta.store import MetaMemoryStore
from athena.procedural.models import Procedure, ProcedureCategory
from athena.procedural.store import ProceduralStore


@pytest.fixture
def db():
    """Create in-memory database."""
    return Database(":memory:")


@pytest.fixture
def meta_store(db):
    """Create meta-memory store."""
    return MetaMemoryStore(db)


@pytest.fixture
def episodic_store(db):
    """Create episodic store."""
    return EpisodicStore(db)


@pytest.fixture
def procedural_store(db):
    """Create procedural store."""
    return ProceduralStore(db)


def test_record_memory_access(meta_store):
    """Test recording memory access."""
    # Record accesses
    meta_store.record_access(1, "semantic", useful=True)
    meta_store.record_access(1, "semantic", useful=False)
    meta_store.record_access(1, "semantic", useful=True)

    # Get quality
    quality = meta_store.get_quality(1, "semantic")

    assert quality is not None
    assert quality.memory_id == 1
    assert quality.memory_layer == "semantic"
    assert quality.access_count == 3
    assert quality.useful_count == 2
    assert quality.usefulness_score == pytest.approx(2.0 / 3.0)


def test_update_confidence(meta_store):
    """Test updating memory confidence."""
    meta_store.update_confidence(1, "episodic", 0.75)

    quality = meta_store.get_quality(1, "episodic")
    assert quality is not None
    assert quality.confidence == 0.75


def test_get_low_quality_memories(meta_store):
    """Test retrieving low-quality memories."""
    # Create memories with varying quality
    for i in range(1, 11):
        for _ in range(10):  # 10 accesses each
            useful = i > 5  # First 5 have low quality
            meta_store.record_access(i, "semantic", useful=useful)

    # Get low-quality memories
    low_quality = meta_store.get_low_quality_memories(threshold=0.5, limit=10)

    # Should get memories 1-5 (usefulness_score = 0.0)
    assert len(low_quality) == 5
    assert all(q.usefulness_score == 0.0 for q in low_quality)


def test_domain_coverage_creation(meta_store):
    """Test creating and retrieving domain coverage."""
    domain = DomainCoverage(
        domain="react",
        category="technology",
        memory_count=10,
        episodic_count=25,
        procedural_count=3,
        avg_confidence=0.85,
        avg_usefulness=0.75,
        expertise_level=ExpertiseLevel.INTERMEDIATE,
    )

    domain_id = meta_store.create_domain(domain)
    assert domain_id > 0

    # Retrieve
    retrieved = meta_store.get_domain("react")
    assert retrieved is not None
    assert retrieved.domain == "react"
    assert retrieved.memory_count == 10
    assert retrieved.expertise_level == ExpertiseLevel.INTERMEDIATE


def test_domain_coverage_update(meta_store):
    """Test updating existing domain coverage."""
    # Create initial domain
    domain1 = DomainCoverage(
        domain="python",
        category="technology",
        memory_count=5,
        expertise_level=ExpertiseLevel.BEGINNER,
    )
    meta_store.create_domain(domain1)

    # Update with more data
    domain2 = DomainCoverage(
        domain="python",
        category="technology",
        memory_count=25,
        expertise_level=ExpertiseLevel.ADVANCED,
    )
    meta_store.create_domain(domain2)

    # Should have updated
    retrieved = meta_store.get_domain("python")
    assert retrieved.memory_count == 25
    assert retrieved.expertise_level == ExpertiseLevel.ADVANCED


def test_list_domains_by_category(meta_store):
    """Test listing domains with category filter."""
    # Create multiple domains
    domains = [
        DomainCoverage(domain="react", category="technology", memory_count=10),
        DomainCoverage(domain="vue", category="technology", memory_count=5),
        DomainCoverage(domain="testing", category="pattern", memory_count=8),
        DomainCoverage(domain="sql", category="database", memory_count=12),
    ]

    for domain in domains:
        meta_store.create_domain(domain)

    # List technology domains
    tech_domains = meta_store.list_domains(category="technology")
    assert len(tech_domains) == 2
    assert all(d.category == "technology" for d in tech_domains)
    # Ordered by memory_count DESC
    assert tech_domains[0].domain == "react"


def test_knowledge_transfer_recording(meta_store):
    """Test recording knowledge transfer."""
    transfer = KnowledgeTransfer(
        from_project_id=1,
        to_project_id=2,
        knowledge_item_id=42,
        knowledge_layer="procedural",
        applicability_score=0.85,
    )

    transfer_id = meta_store.record_transfer(transfer)
    assert transfer_id > 0

    # Retrieve transfers
    transfers = meta_store.get_transfers(from_project_id=1)
    assert len(transfers) == 1
    assert transfers[0].to_project_id == 2
    assert transfers[0].applicability_score == 0.85


def test_analyze_domain_coverage_integration(
    db, episodic_store, procedural_store, meta_store
):
    """Test domain coverage analysis across memory layers."""
    project_id = 1

    # Create episodic events with react mentions
    for i in range(5):
        event = EpisodicEvent(
            project_id=project_id,
            session_id="test",
            event_type=EventType.FILE_CHANGE,
            content=f"Modified React component {i}",
            timestamp=datetime.now() - timedelta(days=i),
        )
        episodic_store.record_event(event)

    # Create procedure related to react
    proc = Procedure(
        name="react_component_workflow",
        category=ProcedureCategory.ARCHITECTURE,
        description="How to create React components",
        template="1. Define props\n2. Implement render\n3. Add tests",
    )
    procedural_store.create_procedure(proc)

    # Analyze coverage
    coverage = analyze_domain_coverage(
        project_id, episodic_store, procedural_store, meta_store
    )

    # Should find react domain
    react_coverage = [c for c in coverage if c.domain == "react"]
    assert len(react_coverage) == 1

    react = react_coverage[0]
    assert react.episodic_count == 5
    assert react.procedural_count == 1
    assert react.expertise_level in [ExpertiseLevel.BEGINNER, ExpertiseLevel.INTERMEDIATE]


def test_detect_knowledge_gaps_low_memory(db, episodic_store, meta_store):
    """Test gap detection for low memory count."""
    domain = DomainCoverage(
        domain="graphql",
        category="technology",
        memory_count=2,  # Very low
        episodic_count=1,
        avg_confidence=0.9,
    )

    gaps = detect_knowledge_gaps(domain, episodic_store, project_id=1)

    assert len(gaps) > 0
    assert any("Limited knowledge" in gap for gap in gaps)


def test_detect_knowledge_gaps_low_confidence(db, episodic_store, meta_store):
    """Test gap detection for low confidence."""
    domain = DomainCoverage(
        domain="kubernetes",
        category="infrastructure",
        memory_count=10,
        avg_confidence=0.3,  # Low confidence
    )

    gaps = detect_knowledge_gaps(domain, episodic_store, project_id=1)

    assert any("Low confidence" in gap for gap in gaps)


def test_detect_knowledge_gaps_no_procedures(db, episodic_store, meta_store):
    """Test gap detection for missing procedural knowledge."""
    domain = DomainCoverage(
        domain="testing",
        category="pattern",
        memory_count=8,
        episodic_count=15,  # Lots of experience
        procedural_count=0,  # But no learned procedures
        avg_confidence=0.7,
    )

    gaps = detect_knowledge_gaps(domain, episodic_store, project_id=1)

    assert any("No learned procedures" in gap for gap in gaps)


def test_detect_knowledge_gaps_high_error_rate(db, episodic_store, meta_store):
    """Test gap detection for high error rates."""
    project_id = 1

    # Create events with high failure rate
    for i in range(10):
        event = EpisodicEvent(
            project_id=project_id,
            session_id="test",
            event_type=EventType.ACTION,
            content="docker deploy application",
            outcome="failure" if i < 7 else "success",  # 70% failure rate
            timestamp=datetime.now() - timedelta(hours=i),
        )
        episodic_store.record_event(event)

    domain = DomainCoverage(
        domain="docker",
        category="infrastructure",
        memory_count=5,
        episodic_count=10,
        avg_confidence=0.6,
    )

    gaps = detect_knowledge_gaps(domain, episodic_store, project_id)

    assert any("High error rate" in gap for gap in gaps)


def test_quality_layer_filtering(meta_store):
    """Test filtering quality metrics by layer."""
    # Record accesses to different layers
    meta_store.record_access(1, "semantic", useful=True)
    meta_store.record_access(2, "episodic", useful=False)
    meta_store.record_access(3, "procedural", useful=True)

    # Get low quality for specific layer
    low_episodic = meta_store.get_low_quality_memories(memory_layer="episodic", threshold=0.5)

    # Should only get episodic memories
    assert all(q.memory_layer == "episodic" for q in low_episodic)
