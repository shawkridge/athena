"""Tests for association network."""

import pytest

from athena.associations.network import AssociationNetwork
from athena.associations.models import LinkType
from athena.core.database import Database


pytest.importorskip("psycopg")
@pytest.fixture
def db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))

    # Create test project
    db.create_project("test-project", str(tmp_path))

    # Create association_links table (Phase 2)
    db.conn.execute(
        """
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
        """
    )
    db.conn.commit()

    return db


@pytest.fixture
def network(db):
    """Create association network."""
    return AssociationNetwork(db)


def test_create_link(network):
    """Test creating a new associative link."""
    link_id = network.create_link(
        project_id=1,
        from_memory_id=100,
        to_memory_id=200,
        from_layer="semantic",
        to_layer="semantic",
        link_type=LinkType.SEMANTIC,
        initial_strength=0.6,
    )

    assert link_id > 0

    # Verify link created
    neighbors = network.get_neighbors(100, "semantic", 1)
    assert len(neighbors) == 1
    assert neighbors[0].to_memory_id == 200
    assert neighbors[0].link_strength == 0.6


def test_create_duplicate_link_increments_count(network):
    """Test creating duplicate link increments co-occurrence count."""
    # Create first link
    link_id1 = network.create_link(
        project_id=1,
        from_memory_id=100,
        to_memory_id=200,
        from_layer="semantic",
        to_layer="semantic",
    )

    # Create duplicate link
    link_id2 = network.create_link(
        project_id=1,
        from_memory_id=100,
        to_memory_id=200,
        from_layer="semantic",
        to_layer="semantic",
    )

    # Should return same link ID
    assert link_id1 == link_id2

    # Check co-occurrence count increased
    neighbors = network.get_neighbors(100, "semantic", 1)
    assert neighbors[0].co_occurrence_count == 2


def test_self_link_rejected(network):
    """Test that self-links are rejected."""
    with pytest.raises(ValueError, match="Cannot create self-link"):
        network.create_link(
            project_id=1,
            from_memory_id=100,
            to_memory_id=100,
            from_layer="semantic",
            to_layer="semantic",
        )


def test_strengthen_link(network):
    """Test strengthening an existing link."""
    # Create link
    link_id = network.create_link(
        project_id=1,
        from_memory_id=100,
        to_memory_id=200,
        from_layer="semantic",
        to_layer="semantic",
        initial_strength=0.5,
    )

    # Strengthen link
    new_strength = network.strengthen_link(link_id, amount=0.2)
    assert new_strength == 0.7

    # Verify updated
    neighbors = network.get_neighbors(100, "semantic", 1)
    assert neighbors[0].link_strength == 0.7


def test_strengthen_link_capped_at_one(network):
    """Test that link strength is capped at 1.0."""
    link_id = network.create_link(
        project_id=1,
        from_memory_id=100,
        to_memory_id=200,
        from_layer="semantic",
        to_layer="semantic",
        initial_strength=0.9,
    )

    new_strength = network.strengthen_link(link_id, amount=0.5)
    assert new_strength == 1.0


def test_weaken_link(network):
    """Test weakening an existing link."""
    link_id = network.create_link(
        project_id=1,
        from_memory_id=100,
        to_memory_id=200,
        from_layer="semantic",
        to_layer="semantic",
        initial_strength=0.7,
    )

    new_strength = network.weaken_link(link_id, amount=0.3)
    assert abs(new_strength - 0.4) < 0.001  # Floating point tolerance

    neighbors = network.get_neighbors(100, "semantic", 1)
    assert abs(neighbors[0].link_strength - 0.4) < 0.001


def test_weaken_link_floored_at_zero(network):
    """Test that link strength is floored at 0.0."""
    link_id = network.create_link(
        project_id=1,
        from_memory_id=100,
        to_memory_id=200,
        from_layer="semantic",
        to_layer="semantic",
        initial_strength=0.2,
    )

    new_strength = network.weaken_link(link_id, amount=0.5)
    assert new_strength == 0.0


def test_get_neighbors_bidirectional(network):
    """Test getting neighbors returns both incoming and outgoing links."""
    # Create A → B
    network.create_link(
        project_id=1,
        from_memory_id=100,
        to_memory_id=200,
        from_layer="semantic",
        to_layer="semantic",
    )

    # Create C → A
    network.create_link(
        project_id=1,
        from_memory_id=300,
        to_memory_id=100,
        from_layer="semantic",
        to_layer="semantic",
    )

    # Get neighbors of A (should include both B and C)
    neighbors = network.get_neighbors(100, "semantic", 1)
    assert len(neighbors) == 2

    neighbor_ids = {n.from_memory_id if n.from_memory_id != 100 else n.to_memory_id for n in neighbors}
    assert neighbor_ids == {200, 300}


def test_get_neighbors_min_strength(network):
    """Test filtering neighbors by minimum strength."""
    # Create strong link
    network.create_link(
        project_id=1,
        from_memory_id=100,
        to_memory_id=200,
        from_layer="semantic",
        to_layer="semantic",
        initial_strength=0.8,
    )

    # Create weak link
    network.create_link(
        project_id=1,
        from_memory_id=100,
        to_memory_id=300,
        from_layer="semantic",
        to_layer="semantic",
        initial_strength=0.2,
    )

    # Get neighbors with min strength 0.5
    neighbors = network.get_neighbors(100, "semantic", 1, min_strength=0.5)
    assert len(neighbors) == 1
    assert neighbors[0].to_memory_id == 200


def test_find_path_direct(network):
    """Test finding direct path between two memories."""
    # Create A → B
    network.create_link(
        project_id=1,
        from_memory_id=100,
        to_memory_id=200,
        from_layer="semantic",
        to_layer="semantic",
    )

    path = network.find_path(100, "semantic", 200, "semantic", 1)
    assert path is not None
    assert len(path) == 1
    assert path[0].from_memory_id == 100
    assert path[0].to_memory_id == 200


def test_find_path_multi_hop(network):
    """Test finding multi-hop path."""
    # Create chain: A → B → C
    network.create_link(
        project_id=1,
        from_memory_id=100,
        to_memory_id=200,
        from_layer="semantic",
        to_layer="semantic",
    )
    network.create_link(
        project_id=1,
        from_memory_id=200,
        to_memory_id=300,
        from_layer="semantic",
        to_layer="semantic",
    )

    path = network.find_path(100, "semantic", 300, "semantic", 1)
    assert path is not None
    assert len(path) == 2


def test_find_path_no_path(network):
    """Test that no path returns None."""
    # Create isolated link
    network.create_link(
        project_id=1,
        from_memory_id=100,
        to_memory_id=200,
        from_layer="semantic",
        to_layer="semantic",
    )

    # Try to find path to unconnected node
    path = network.find_path(100, "semantic", 999, "semantic", 1)
    assert path is None


def test_find_path_same_node(network):
    """Test finding path to same node returns empty path."""
    path = network.find_path(100, "semantic", 100, "semantic", 1)
    assert path == []


def test_get_link_count(network):
    """Test counting active links."""
    # Create links
    network.create_link(1, 100, 200, "semantic", "semantic", initial_strength=0.8)
    network.create_link(1, 200, 300, "semantic", "semantic", initial_strength=0.6)
    network.create_link(1, 300, 400, "semantic", "semantic", initial_strength=0.05)  # Below threshold

    # Count with default min strength (0.1)
    count = network.get_link_count(1)
    assert count == 2  # Only first two above threshold


def test_prune_weak_links(network):
    """Test pruning weak links."""
    # Create links
    network.create_link(1, 100, 200, "semantic", "semantic", initial_strength=0.8)
    network.create_link(1, 200, 300, "semantic", "semantic", initial_strength=0.3)
    network.create_link(1, 300, 400, "semantic", "semantic", initial_strength=0.05)

    # Prune links below 0.3
    pruned = network.prune_weak_links(1, strength_threshold=0.3)
    assert pruned == 1  # Only the 0.05 link pruned

    # Verify remaining links
    count = network.get_link_count(1, min_strength=0.0)
    assert count == 2


def test_decay_all_links(network):
    """Test applying decay to all links."""
    # Create links
    network.create_link(1, 100, 200, "semantic", "semantic", initial_strength=0.8)
    network.create_link(1, 200, 300, "semantic", "semantic", initial_strength=0.5)

    # Apply decay
    decayed = network.decay_all_links(1, decay_rate=0.2)
    assert decayed == 2

    # Verify strengths reduced
    neighbors1 = network.get_neighbors(100, "semantic", 1, min_strength=0.0)
    neighbors2 = network.get_neighbors(200, "semantic", 1, min_strength=0.0)

    # neighbors1 should have the decayed 100->200 link (0.8 - 0.2 = 0.6)
    assert abs(neighbors1[0].link_strength - 0.6) < 0.001  # 0.8 - 0.2

    # neighbors2 has both incoming (100->200, 0.6) and outgoing (200->300, 0.3)
    # Sorted by strength: [0.6, 0.3]
    # Find the outgoing link (to_memory_id=300)
    outgoing_link = next(n for n in neighbors2 if n.to_memory_id == 300)
    assert abs(outgoing_link.link_strength - 0.3) < 0.001  # 0.5 - 0.2
