"""Tests for Phase 2 MCP tool underlying functionality (Association Network, Priming, Propagation, Hebbian)."""

import pytest
from datetime import datetime, timezone
from athena.core.database import Database
from athena.associations.network import AssociationNetwork
from athena.associations.models import LinkType
from athena.associations.priming import TemporalPriming
from athena.associations.propagation import ActivationPropagation
from athena.learning.hebbian import HebbianLearner


@pytest.fixture
def db(tmp_path):
    """Create test database with Phase 2 schema."""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    db.create_project("test-project", str(tmp_path))

    # Create Phase 2 schema
    db.conn.execute("""
        CREATE TABLE IF NOT EXISTS association_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            from_memory_id INTEGER NOT NULL,
            to_memory_id INTEGER NOT NULL,
            from_layer TEXT NOT NULL,
            to_layer TEXT NOT NULL,
            link_strength REAL DEFAULT 0.5 CHECK (link_strength >= 0.0 AND link_strength <= 1.0),
            co_occurrence_count INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_strengthened TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            link_type TEXT DEFAULT 'semantic' CHECK (link_type IN ('semantic', 'temporal', 'causal', 'similarity')),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)
    db.conn.commit()
    return db


@pytest.fixture
def network(db):
    """Create association network."""
    return AssociationNetwork(db)


@pytest.fixture
def propagation(db, network):
    """Create activation propagation."""
    return ActivationPropagation(db, network)


@pytest.fixture
def hebbian(db, network):
    """Create Hebbian learner."""
    return HebbianLearner(db, network)


@pytest.fixture
def priming(db):
    """Create temporal priming."""
    return TemporalPriming(db)


def test_get_associations_no_links(network):
    """Test get_neighbors with no links (MCP tool get_associations foundation)."""
    neighbors = network.get_neighbors(100, "semantic", 1, min_strength=0.1)
    assert len(neighbors) == 0


def test_get_associations_with_links(network):
    """Test get_neighbors with existing links (MCP tool get_associations foundation)."""
    # Create link for MCP tool foundation
    network.create_link(
        project_id=1,
        from_memory_id=100,
        to_memory_id=200,
        from_layer="semantic",
        to_layer="semantic",
        link_type=LinkType.SEMANTIC,
        initial_strength=0.8
    )

    neighbors = network.get_neighbors(100, "semantic", 1, min_strength=0.1)
    assert len(neighbors) == 1
    assert neighbors[0].to_memory_id == 200
    assert neighbors[0].link_strength == 0.8


def test_strengthen_association_foundation(network):
    """Test strengthen_link (MCP tool strengthen_association foundation)."""
    link_id = network.create_link(
        project_id=1,
        from_memory_id=100,
        to_memory_id=200,
        from_layer="semantic",
        to_layer="semantic",
        link_type=LinkType.SEMANTIC,
        initial_strength=0.5
    )

    # Strengthen it
    new_strength = network.strengthen_link(link_id, 0.2)
    assert abs(new_strength - 0.7) < 0.001


def test_find_memory_path_foundation(network):
    """Test find_path (MCP tool find_memory_path foundation)."""
    # Create a path: 100 -> 200 -> 300
    network.create_link(
        project_id=1,
        from_memory_id=100,
        to_memory_id=200,
        from_layer="semantic",
        to_layer="semantic",
        link_type=LinkType.SEMANTIC,
        initial_strength=0.8
    )

    network.create_link(
        project_id=1,
        from_memory_id=200,
        to_memory_id=300,
        from_layer="semantic",
        to_layer="semantic",
        link_type=LinkType.SEMANTIC,
        initial_strength=0.8
    )

    path = network.find_path(100, "semantic", 300, "semantic", 1, max_depth=3)
    # Should find path: 100 -> 200 -> 300
    assert path is not None
    if path:
        # Path is a list of AssociationLink objects
        assert len(path) >= 1


