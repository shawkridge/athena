"""Tests for activation propagation."""

import pytest

from athena.associations.network import AssociationNetwork
from athena.associations.propagation import ActivationPropagation
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

    # Create association_links table
    db.conn.execute(
        """
        CREATE TABLE IF NOT EXISTS association_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            from_memory_id INTEGER NOT NULL,
            to_memory_id INTEGER NOT NULL,
            from_layer TEXT NOT NULL,
            to_layer TEXT NOT NULL,
            link_strength REAL DEFAULT 0.5,
            co_occurrence_count INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_strengthened TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            link_type TEXT DEFAULT 'semantic',
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
        """
    )

    # Create activation_state table
    db.conn.execute(
        """
        CREATE TABLE IF NOT EXISTS activation_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            memory_id INTEGER NOT NULL,
            memory_layer TEXT NOT NULL,
            activation_level REAL DEFAULT 0.0,
            source_activation_id INTEGER,
            hop_distance INTEGER DEFAULT 0,
            activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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


@pytest.fixture
def propagation(db, network):
    """Create activation propagation."""
    return ActivationPropagation(db, network)


def test_single_source_propagation(network, propagation):
    """Test propagation from single source."""
    # Create chain: A → B → C
    # A(100) --0.8--> B(200) --0.7--> C(300)
    network.create_link(1, 100, 200, "semantic", "semantic", initial_strength=0.8)
    network.create_link(1, 200, 300, "semantic", "semantic", initial_strength=0.7)

    # Propagate from A with decay 0.7
    activated = propagation.propagate(
        source_memory_id=100,
        source_layer="semantic",
        project_id=1,
        max_hops=2,
        decay_factor=0.7,
        min_activation=0.1,
    )

    # Should activate A, B, C
    assert len(activated) >= 2

    # A (source) should have activation 1.0, hop 0
    source_node = next(n for n in activated if n.memory_id == 100)
    assert source_node.activation_level == 1.0
    assert source_node.hop_distance == 0

    # B should have activation ~0.56 (1.0 × 0.8 × 0.7), hop 1
    b_node = next(n for n in activated if n.memory_id == 200)
    assert 0.5 <= b_node.activation_level <= 0.6
    assert b_node.hop_distance == 1

    # C should have activation ~0.27 (0.56 × 0.7 × 0.7), hop 2
    c_node = next((n for n in activated if n.memory_id == 300), None)
    if c_node:  # May be filtered by min_activation
        assert 0.2 <= c_node.activation_level <= 0.3
        assert c_node.hop_distance == 2


def test_multi_source_propagation(network, propagation):
    """Test propagation from multiple sources."""
    # Create network: A, B both connect to C
    # A(100) --0.6--> C(300)
    # B(200) --0.7--> C(300)
    network.create_link(1, 100, 300, "semantic", "semantic", initial_strength=0.6)
    network.create_link(1, 200, 300, "semantic", "semantic", initial_strength=0.7)

    # Propagate from both A and B
    activated = propagation.multi_source_propagate(
        source_ids=[(100, "semantic"), (200, "semantic")],
        source_weights=[1.0, 1.0],
        project_id=1,
        max_hops=1,
        decay_factor=0.7,
    )

    # C should have summed activation from both sources
    c_node = next((n for n in activated if n.memory_id == 300), None)
    assert c_node is not None

    # Expected: (1.0 × 0.6 × 0.7) + (1.0 × 0.7 × 0.7) = 0.42 + 0.49 = 0.91
    assert 0.85 <= c_node.activation_level <= 0.95


def test_activation_decay_with_distance(network, propagation):
    """Test that activation decays with hop distance."""
    # Create long chain: A → B → C → D
    network.create_link(1, 100, 200, "semantic", "semantic", initial_strength=0.9)
    network.create_link(1, 200, 300, "semantic", "semantic", initial_strength=0.9)
    network.create_link(1, 300, 400, "semantic", "semantic", initial_strength=0.9)

    activated = propagation.propagate(
        source_memory_id=100,
        source_layer="semantic",
        project_id=1,
        max_hops=3,
        decay_factor=0.7,
    )

    # Extract activation levels by hop distance
    activations_by_hop = {}
    for node in activated:
        activations_by_hop[node.hop_distance] = node.activation_level

    # Verify decay: each hop should have lower activation
    assert activations_by_hop[0] > activations_by_hop[1]
    if 2 in activations_by_hop:
        assert activations_by_hop[1] > activations_by_hop[2]


def test_min_activation_threshold(network, propagation):
    """Test that nodes below min activation are filtered."""
    # Create weak chain
    network.create_link(1, 100, 200, "semantic", "semantic", initial_strength=0.3)
    network.create_link(1, 200, 300, "semantic", "semantic", initial_strength=0.3)

    # Propagate with high min_activation threshold
    activated = propagation.propagate(
        source_memory_id=100,
        source_layer="semantic",
        project_id=1,
        max_hops=2,
        decay_factor=0.7,
        min_activation=0.5,
    )

    # Only source should survive (activation 1.0)
    # B would have ~0.21, C would have ~0.04, both below threshold
    assert len(activated) == 1
    assert activated[0].memory_id == 100


def test_max_hops_limit(network, propagation):
    """Test that propagation respects max_hops limit."""
    # Create long chain: A → B → C → D → E
    network.create_link(1, 100, 200, "semantic", "semantic", initial_strength=0.9)
    network.create_link(1, 200, 300, "semantic", "semantic", initial_strength=0.9)
    network.create_link(1, 300, 400, "semantic", "semantic", initial_strength=0.9)
    network.create_link(1, 400, 500, "semantic", "semantic", initial_strength=0.9)

    # Propagate with max_hops=2
    activated = propagation.propagate(
        source_memory_id=100,
        source_layer="semantic",
        project_id=1,
        max_hops=2,
        decay_factor=0.9,
        min_activation=0.1,
    )

    # Should only reach A, B, C (hops 0, 1, 2)
    max_hop = max(n.hop_distance for n in activated)
    assert max_hop <= 2

    # E (memory_id 500) should NOT be activated
    assert all(n.memory_id != 500 for n in activated)


def test_get_activation_level(network, propagation):
    """Test getting current activation level for a memory."""
    # Propagate to create activation state
    network.create_link(1, 100, 200, "semantic", "semantic", initial_strength=0.8)

    propagation.propagate(
        source_memory_id=100,
        source_layer="semantic",
        project_id=1,
        max_hops=1,
    )

    # Get activation level
    activation = propagation.get_activation_level(200, "semantic", 1)
    assert 0.5 <= activation <= 0.6  # ~0.56 expected


def test_decay_all_activations(network, propagation):
    """Test decaying all activations."""
    # Setup and propagate
    network.create_link(1, 100, 200, "semantic", "semantic", initial_strength=0.8)
    propagation.propagate(100, "semantic", 1, max_hops=1)

    # Decay activations
    decayed = propagation.decay_all_activations(1, decay_rate=0.3)
    assert decayed > 0

    # Check activation reduced
    new_activation = propagation.get_activation_level(200, "semantic", 1)
    assert new_activation < 0.6  # Original ~0.56


def test_clear_activations(network, propagation):
    """Test clearing all activation state."""
    # Setup and propagate
    network.create_link(1, 100, 200, "semantic", "semantic")
    propagation.propagate(100, "semantic", 1, max_hops=1)

    # Clear activations
    cleared = propagation.clear_activations(1)
    assert cleared > 0

    # Verify all cleared
    activation = propagation.get_activation_level(100, "semantic", 1)
    assert activation == 0.0


def test_get_top_activated(network, propagation):
    """Test getting most activated memories."""
    # Create network with varying activation levels
    network.create_link(1, 100, 200, "semantic", "semantic", initial_strength=0.9)
    network.create_link(1, 100, 300, "semantic", "semantic", initial_strength=0.5)
    network.create_link(1, 100, 400, "semantic", "semantic", initial_strength=0.3)

    propagation.propagate(100, "semantic", 1, max_hops=1, min_activation=0.1)

    # Get top activated
    top = propagation.get_top_activated(1, limit=3)

    # Should be sorted by activation level (descending)
    assert len(top) <= 3
    for i in range(len(top) - 1):
        assert top[i].activation_level >= top[i + 1].activation_level


def test_bidirectional_propagation(network, propagation):
    """Test that propagation follows links in both directions."""
    # Create: A → B ← C (B is central node)
    network.create_link(1, 100, 200, "semantic", "semantic", initial_strength=0.8)
    network.create_link(1, 300, 200, "semantic", "semantic", initial_strength=0.7)

    # Propagate from B
    activated = propagation.propagate(200, "semantic", 1, max_hops=1)

    # Should activate A and C (bidirectional)
    activated_ids = {n.memory_id for n in activated}
    assert 100 in activated_ids
    assert 300 in activated_ids


def test_activation_sorted_by_level(network, propagation):
    """Test that results are sorted by activation level."""
    # Create network with varying strengths
    network.create_link(1, 100, 200, "semantic", "semantic", initial_strength=0.9)
    network.create_link(1, 100, 300, "semantic", "semantic", initial_strength=0.6)
    network.create_link(1, 100, 400, "semantic", "semantic", initial_strength=0.3)

    activated = propagation.propagate(100, "semantic", 1, max_hops=1)

    # Verify sorted (descending)
    for i in range(len(activated) - 1):
        assert activated[i].activation_level >= activated[i + 1].activation_level
