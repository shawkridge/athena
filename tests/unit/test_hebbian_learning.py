"""Tests for Hebbian learning."""

from datetime import datetime, timedelta

import pytest

from athena.learning.hebbian import HebbianLearner
from athena.associations.network import AssociationNetwork
from athena.core.database import Database


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

    # Create memory_access_log table
    db.conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memory_access_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            memory_id INTEGER NOT NULL,
            memory_layer TEXT NOT NULL,
            accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            activation_level REAL DEFAULT 1.0,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
        """
    )

    # Create hebbian_stats table
    db.conn.execute(
        """
        CREATE TABLE IF NOT EXISTS hebbian_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL UNIQUE,
            total_accesses INTEGER DEFAULT 0,
            links_created INTEGER DEFAULT 0,
            links_strengthened INTEGER DEFAULT 0,
            links_weakened INTEGER DEFAULT 0,
            avg_link_strength REAL DEFAULT 0.0,
            last_learning_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
def hebbian(db, network):
    """Create Hebbian learner."""
    return HebbianLearner(db, network, learning_rate=0.1, window_seconds=60)


def test_log_access(hebbian):
    """Test logging memory access."""
    access_id = hebbian.log_access(
        memory_id=100,
        layer="semantic",
        project_id=1,
        activation_level=0.8,
    )

    assert access_id > 0


def test_co_occurrence_detection(hebbian):
    """Test detecting co-occurring memory accesses."""
    # Log two accesses within window
    hebbian.log_access(100, "semantic", 1, activation_level=1.0)
    hebbian.log_access(200, "semantic", 1, activation_level=1.0)

    # Detect and strengthen
    strengthened = hebbian.detect_and_strengthen(1)

    # Should create one association (100 → 200)
    assert strengthened == 1


def test_hebbian_strengthening_formula(hebbian, network):
    """Test Hebbian learning formula: Δw = η × (a_pre × a_post) × (1 - w)."""
    # Log accesses with specific activations
    hebbian.log_access(100, "semantic", 1, activation_level=0.8)
    hebbian.log_access(200, "semantic", 1, activation_level=0.6)

    # Apply learning
    hebbian.detect_and_strengthen(1)

    # Get created link
    neighbors = network.get_neighbors(100, "semantic", 1, min_strength=0.0)
    assert len(neighbors) > 0

    link = neighbors[0]

    # Expected strength: η × a_pre × a_post × (1 - 0) × temporal_factor
    # With learning_rate=0.1, a_pre=0.8, a_post=0.6, temporal_factor~1.0 (immediate)
    # Expected: 0.1 × 0.8 × 0.6 × 1.0 × 1.0 = 0.048
    assert 0.04 <= link.link_strength <= 0.06


def test_asymmetric_link_creation(hebbian, network):
    """Test that A→B is created (asymmetric, not B→A)."""
    # A accessed before B
    hebbian.log_access(100, "semantic", 1)
    hebbian.log_access(200, "semantic", 1)

    hebbian.detect_and_strengthen(1)

    # Should have A → B
    neighbors_a = network.get_neighbors(100, "semantic", 1, min_strength=0.0)
    assert any(n.to_memory_id == 200 for n in neighbors_a)


def test_temporal_decay_factor(hebbian, network, db):
    """Test that temporal proximity affects link strength."""
    # Create two pairs: one immediate, one delayed

    # Pair 1: Immediate (strong temporal factor)
    hebbian.log_access(100, "semantic", 1, activation_level=1.0)
    hebbian.log_access(200, "semantic", 1, activation_level=1.0)

    # Pair 2: Delayed (weaker temporal factor)
    now = datetime.now()
    delayed_time = now - timedelta(seconds=50)  # Near end of window
    with db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO memory_access_log (
                project_id, memory_id, memory_layer,
                accessed_at, activation_level
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (1, 300, "semantic", delayed_time.isoformat(), 1.0),
        )
        conn.execute(
            """
            INSERT INTO memory_access_log (
                project_id, memory_id, memory_layer,
                accessed_at, activation_level
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (1, 400, "semantic", now.isoformat(), 1.0),
        )
        conn.commit()

    hebbian.detect_and_strengthen(1)

    # Get strengths
    link1 = network.get_neighbors(100, "semantic", 1, min_strength=0.0)[0]
    link2 = network.get_neighbors(300, "semantic", 1, min_strength=0.0)[0]

    # Immediate link should be stronger
    assert link1.link_strength > link2.link_strength


def test_no_self_associations(hebbian, network):
    """Test that self-associations are not created."""
    # Log same memory twice
    hebbian.log_access(100, "semantic", 1)
    hebbian.log_access(100, "semantic", 1)

    hebbian.detect_and_strengthen(1)

    # Should create no links
    neighbors = network.get_neighbors(100, "semantic", 1, min_strength=0.0)
    assert all(n.to_memory_id != 100 for n in neighbors)


def test_co_occurrence_window_respected(hebbian, network, db):
    """Test that accesses outside window don't strengthen links."""
    # Log two accesses outside window (70 seconds apart, window is 60)
    now = datetime.now()
    old_time = now - timedelta(seconds=70)

    with db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO memory_access_log (
                project_id, memory_id, memory_layer,
                accessed_at, activation_level
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (1, 100, "semantic", old_time.isoformat(), 1.0),
        )
        conn.execute(
            """
            INSERT INTO memory_access_log (
                project_id, memory_id, memory_layer,
                accessed_at, activation_level
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (1, 200, "semantic", now.isoformat(), 1.0),
        )
        conn.commit()

    strengthened = hebbian.detect_and_strengthen(1)

    # Should create no associations (outside window)
    assert strengthened == 0


def test_repeated_co_occurrence_strengthens(hebbian, network):
    """Test that repeated co-occurrence strengthens existing link."""
    # First co-occurrence
    hebbian.log_access(100, "semantic", 1)
    hebbian.log_access(200, "semantic", 1)
    hebbian.detect_and_strengthen(1)

    initial_strength = network.get_neighbors(100, "semantic", 1, min_strength=0.0)[0].link_strength

    # Second co-occurrence
    hebbian.log_access(100, "semantic", 1)
    hebbian.log_access(200, "semantic", 1)
    hebbian.detect_and_strengthen(1)

    new_strength = network.get_neighbors(100, "semantic", 1, min_strength=0.0)[0].link_strength

    # Strength should increase
    assert new_strength > initial_strength


def test_apply_decay(hebbian, network):
    """Test applying decay to unused links."""
    # Create link
    network.create_link(1, 100, 200, "semantic", "semantic", initial_strength=0.5)

    # Apply decay
    decayed = hebbian.apply_decay(1, decay_rate=0.1)
    assert decayed > 0

    # Verify strength reduced
    link = network.get_neighbors(100, "semantic", 1, min_strength=0.0)[0]
    assert link.link_strength == 0.4  # 0.5 - 0.1


def test_get_stats(hebbian):
    """Test getting learning statistics."""
    stats = hebbian.get_stats(1)

    assert stats.project_id == 1
    assert stats.total_accesses >= 0
    assert stats.links_created >= 0
    assert stats.links_strengthened >= 0


def test_stats_updated_after_learning(hebbian):
    """Test that stats are updated after learning."""
    initial_stats = hebbian.get_stats(1)

    # Perform learning
    hebbian.log_access(100, "semantic", 1)
    hebbian.log_access(200, "semantic", 1)
    hebbian.detect_and_strengthen(1)

    new_stats = hebbian.get_stats(1)

    # Stats should be updated
    assert new_stats.total_accesses > initial_stats.total_accesses
    assert new_stats.links_strengthened > initial_stats.links_strengthened


def test_clear_old_accesses(hebbian, db):
    """Test clearing old access logs."""
    # Create old access (8 days ago)
    old_time = datetime.now() - timedelta(days=8)
    with db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO memory_access_log (
                project_id, memory_id, memory_layer,
                accessed_at, activation_level
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (1, 100, "semantic", old_time.isoformat(), 1.0),
        )
        conn.commit()

    # Create recent access
    hebbian.log_access(200, "semantic", 1)

    # Clear accesses older than 7 days
    cleared = hebbian.clear_old_accesses(1, days=7)

    assert cleared == 1  # Only old access cleared


def test_multi_memory_learning(hebbian, network):
    """Test learning with multiple memories in window."""
    # Log accesses: A, B, C all within window
    hebbian.log_access(100, "semantic", 1)
    hebbian.log_access(200, "semantic", 1)
    hebbian.log_access(300, "semantic", 1)

    strengthened = hebbian.detect_and_strengthen(1)

    # Should create multiple associations:
    # A→B, A→C, B→C
    assert strengthened == 3


def test_learning_rate_validation(db, network):
    """Test that invalid learning rate raises error."""
    with pytest.raises(ValueError, match="learning_rate must be between"):
        HebbianLearner(db, network, learning_rate=1.5)

    with pytest.raises(ValueError, match="learning_rate must be between"):
        HebbianLearner(db, network, learning_rate=-0.1)


def test_window_validation(db, network):
    """Test that invalid window raises error."""
    with pytest.raises(ValueError, match="window_seconds must be non-negative"):
        HebbianLearner(db, network, window_seconds=-10)
