"""Tests for attention inhibition system."""

import time
from datetime import datetime, timedelta

import pytest

from athena.attention.inhibition import AttentionInhibition
from athena.attention.models import InhibitionType
from athena.core.database import Database


@pytest.fixture
def db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))

    # Database already initializes schema in __init__ including projects table
    # Create a test project
    db.create_project("test-project", str(tmp_path))

    # Create attention_inhibition table (Phase 2)
    db.conn.execute(
        """
        CREATE TABLE IF NOT EXISTS attention_inhibition (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            memory_id INTEGER NOT NULL,
            memory_layer TEXT NOT NULL,
            inhibition_strength REAL DEFAULT 0.5 CHECK (inhibition_strength >= 0.0 AND inhibition_strength <= 1.0),
            inhibition_type TEXT CHECK (inhibition_type IN ('proactive', 'retroactive', 'selective')),
            reason TEXT,
            inhibited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
        """
    )
    db.conn.commit()

    return db


@pytest.fixture
def inhibition(db):
    """Create inhibition manager."""
    return AttentionInhibition(db)


def test_inhibit_memory(inhibition):
    """Test basic memory inhibition."""
    inhibition_id = inhibition.inhibit(
        project_id=1,
        memory_id=100,
        memory_layer="semantic",
        strength=0.7,
        inhibition_type=InhibitionType.SELECTIVE,
        reason="Test suppression"
    )

    assert inhibition_id > 0
    assert inhibition.is_inhibited(100, "semantic", 1, threshold=0.3)


def test_inhibition_strength_decay(inhibition):
    """Test that inhibition strength decays exponentially over time."""
    # Inhibit with strength 0.8
    inhibition.inhibit(
        project_id=1,
        memory_id=100,
        memory_layer="semantic",
        strength=0.8,
        inhibition_type=InhibitionType.SELECTIVE
    )

    # Initial strength should be close to 0.8
    initial_strength = inhibition.get_inhibition_strength(100, "semantic", 1)
    assert 0.75 <= initial_strength <= 0.85  # Allow for tiny time drift

    # Mock time passage by directly updating inhibited_at
    past_time = datetime.now() - timedelta(seconds=1800)  # 30 min ago (1 half-life)
    inhibition.db.conn.execute(
        "UPDATE attention_inhibition SET inhibited_at = ? WHERE memory_id = ?",
        (past_time, 100)
    )
    inhibition.db.conn.commit()

    # After 1 half-life (30 min), strength should be ~0.4 (0.8 * 0.5)
    decayed_strength = inhibition.get_inhibition_strength(100, "semantic", 1)
    assert 0.35 <= decayed_strength <= 0.45


def test_inhibition_types(inhibition):
    """Test different inhibition types."""
    # Proactive inhibition
    id1 = inhibition.inhibit(
        project_id=1,
        memory_id=100,
        memory_layer="semantic",
        strength=0.6,
        inhibition_type=InhibitionType.PROACTIVE,
        reason="Old memory interfering with new learning"
    )

    # Retroactive inhibition
    id2 = inhibition.inhibit(
        project_id=1,
        memory_id=101,
        memory_layer="semantic",
        strength=0.5,
        inhibition_type=InhibitionType.RETROACTIVE,
        reason="New learning suppressing old"
    )

    # Selective inhibition
    id3 = inhibition.inhibit(
        project_id=1,
        memory_id=102,
        memory_layer="semantic",
        strength=0.7,
        inhibition_type=InhibitionType.SELECTIVE,
        reason="User-directed suppression"
    )

    assert id1 > 0 and id2 > 0 and id3 > 0

    # All should be inhibited
    assert inhibition.is_inhibited(100, "semantic", 1)
    assert inhibition.is_inhibited(101, "semantic", 1)
    assert inhibition.is_inhibited(102, "semantic", 1)


def test_release_inhibition(inhibition):
    """Test releasing an inhibition."""
    inhibition_id = inhibition.inhibit(
        project_id=1,
        memory_id=100,
        memory_layer="semantic",
        strength=0.8
    )

    assert inhibition.is_inhibited(100, "semantic", 1)

    # Release inhibition
    success = inhibition.release_inhibition(inhibition_id)
    assert success is True

    # Should no longer be inhibited
    assert not inhibition.is_inhibited(100, "semantic", 1)


def test_release_memory_all_inhibitions(inhibition):
    """Test releasing all inhibitions for a memory."""
    # Add multiple inhibitions for same memory
    inhibition.inhibit(project_id=1, memory_id=100, memory_layer="semantic", strength=0.5)
    inhibition.inhibit(project_id=1, memory_id=100, memory_layer="semantic", strength=0.3)
    inhibition.inhibit(project_id=1, memory_id=100, memory_layer="semantic", strength=0.4)

    assert inhibition.is_inhibited(100, "semantic", 1)

    # Release all inhibitions for this memory
    count = inhibition.release_memory(1, 100, "semantic")
    assert count == 3

    # Should no longer be inhibited
    assert not inhibition.is_inhibited(100, "semantic", 1)


def test_inhibition_threshold(inhibition):
    """Test inhibition threshold filtering."""
    # Weak inhibition
    inhibition.inhibit(project_id=1, memory_id=100, memory_layer="semantic", strength=0.2)

    # Should be inhibited with low threshold
    assert inhibition.is_inhibited(100, "semantic", 1, threshold=0.1)

    # Should NOT be inhibited with high threshold
    assert not inhibition.is_inhibited(100, "semantic", 1, threshold=0.5)


def test_multiple_inhibitions_sum(inhibition):
    """Test that multiple inhibitions on same memory sum together."""
    # Add multiple weak inhibitions
    inhibition.inhibit(project_id=1, memory_id=100, memory_layer="semantic", strength=0.3)
    inhibition.inhibit(project_id=1, memory_id=100, memory_layer="semantic", strength=0.3)
    inhibition.inhibit(project_id=1, memory_id=100, memory_layer="semantic", strength=0.3)

    # Total strength should be ~0.9 (capped at 1.0)
    total_strength = inhibition.get_inhibition_strength(100, "semantic", 1)
    assert 0.85 <= total_strength <= 0.95


def test_inhibition_expiration(inhibition):
    """Test explicit inhibition expiration."""
    # Inhibit with 1 second expiration
    inhibition.inhibit(
        project_id=1,
        memory_id=100,
        memory_layer="semantic",
        strength=0.8,
        duration_seconds=1
    )

    assert inhibition.is_inhibited(100, "semantic", 1)

    # Wait for expiration
    time.sleep(1.1)

    # Should no longer be inhibited (expired)
    assert not inhibition.is_inhibited(100, "semantic", 1)


def test_decay_inhibitions(inhibition):
    """Test automatic removal of decayed inhibitions."""
    # Add inhibition
    inhibition.inhibit(
        project_id=1,
        memory_id=100,
        memory_layer="semantic",
        strength=0.5
    )

    # Manually set to very old (should decay to near zero)
    past_time = datetime.now() - timedelta(hours=10)  # Very old
    inhibition.db.conn.execute(
        "UPDATE attention_inhibition SET inhibited_at = ? WHERE memory_id = ?",
        (past_time, 100)
    )
    inhibition.db.conn.commit()

    # Decay should remove it
    removed = inhibition.decay_inhibitions(project_id=1, min_strength=0.01)
    assert removed == 1

    # Should no longer be inhibited
    assert not inhibition.is_inhibited(100, "semantic", 1)


def test_get_inhibited_memories(inhibition):
    """Test retrieving all inhibited memories."""
    # Add several inhibitions
    inhibition.inhibit(project_id=1, memory_id=100, memory_layer="semantic", strength=0.8)
    inhibition.inhibit(project_id=1, memory_id=101, memory_layer="episodic", strength=0.6)
    inhibition.inhibit(project_id=1, memory_id=102, memory_layer="semantic", strength=0.1)  # Weak

    # Get inhibited memories above threshold
    inhibited = inhibition.get_inhibited_memories(project_id=1, min_strength=0.3)

    # Should get 2 memories (100 and 101), not 102 (too weak)
    assert len(inhibited) == 2
    memory_ids = {rec.memory_id for rec in inhibited}
    assert memory_ids == {100, 101}


def test_get_all_inhibitions(inhibition):
    """Test retrieving all inhibition records."""
    # Add several inhibitions
    inhibition.inhibit(project_id=1, memory_id=100, memory_layer="semantic", strength=0.8)
    inhibition.inhibit(project_id=1, memory_id=101, memory_layer="episodic", strength=0.6)

    # Add expired inhibition
    inhibition.inhibit(
        project_id=1,
        memory_id=102,
        memory_layer="semantic",
        strength=0.5,
        duration_seconds=-1  # Already expired
    )

    # Get all (including expired)
    all_inhibitions = inhibition.get_all_inhibitions(project_id=1)
    assert len(all_inhibitions) == 3


def test_inhibition_strength_clamping(inhibition):
    """Test that inhibition strength is clamped to 0.0-1.0."""
    # Try to set strength > 1.0
    inhibition.inhibit(project_id=1, memory_id=100, memory_layer="semantic", strength=1.5)
    strength = inhibition.get_inhibition_strength(100, "semantic", 1)
    assert strength <= 1.0

    # Try to set strength < 0.0
    inhibition.inhibit(project_id=1, memory_id=101, memory_layer="semantic", strength=-0.5)
    strength = inhibition.get_inhibition_strength(101, "semantic", 1)
    assert strength >= 0.0


def test_inhibition_different_layers(inhibition):
    """Test that inhibitions are layer-specific."""
    # Inhibit in semantic layer
    inhibition.inhibit(project_id=1, memory_id=100, memory_layer="semantic", strength=0.8)

    # Same memory_id in different layer should NOT be inhibited
    assert inhibition.is_inhibited(100, "semantic", 1)
    assert not inhibition.is_inhibited(100, "episodic", 1)


def test_inhibition_different_projects(inhibition):
    """Test that inhibitions are project-specific."""
    # Add second project
    inhibition.db.create_project("project-2", "/test/path2")

    # Inhibit in project 1
    inhibition.inhibit(project_id=1, memory_id=100, memory_layer="semantic", strength=0.8)

    # Same memory in project 2 should NOT be inhibited
    assert inhibition.is_inhibited(100, "semantic", 1)
    assert not inhibition.is_inhibited(100, "semantic", 2)


def test_proactive_inhibition_scenario(inhibition):
    """Test proactive inhibition scenario: old memories suppressed by new."""
    # Learn "Paris is the capital of France"
    old_memory_id = 200

    # Later, learn conflicting fact in different context
    # This should proactively inhibit the old memory
    inhibition.inhibit(
        project_id=1,
        memory_id=old_memory_id,
        memory_layer="semantic",
        strength=0.6,
        inhibition_type=InhibitionType.PROACTIVE,
        reason="Old memory interferes with new learning context"
    )

    assert inhibition.is_inhibited(old_memory_id, "semantic", 1)

    # Get records and verify type
    records = inhibition.get_all_inhibitions(project_id=1)
    assert len(records) == 1
    assert records[0].inhibition_type == InhibitionType.PROACTIVE


def test_retroactive_inhibition_scenario(inhibition):
    """Test retroactive inhibition scenario: new learning suppresses old."""
    # Old memory that will be suppressed
    old_memory_id = 300

    # New learning happens, retroactively suppressing old memory
    inhibition.inhibit(
        project_id=1,
        memory_id=old_memory_id,
        memory_layer="semantic",
        strength=0.5,
        inhibition_type=InhibitionType.RETROACTIVE,
        reason="New learning makes old memory less relevant"
    )

    assert inhibition.is_inhibited(old_memory_id, "semantic", 1)

    # Get records and verify type
    records = inhibition.get_all_inhibitions(project_id=1)
    assert len(records) == 1
    assert records[0].inhibition_type == InhibitionType.RETROACTIVE


def test_selective_inhibition_scenario(inhibition):
    """Test selective inhibition scenario: user-directed suppression."""
    # User explicitly suppresses a memory
    unwanted_memory_id = 400

    inhibition.inhibit(
        project_id=1,
        memory_id=unwanted_memory_id,
        memory_layer="semantic",
        strength=0.9,
        inhibition_type=InhibitionType.SELECTIVE,
        reason="User marked this memory as irrelevant"
    )

    assert inhibition.is_inhibited(unwanted_memory_id, "semantic", 1)

    # Selective inhibitions should have high strength
    strength = inhibition.get_inhibition_strength(unwanted_memory_id, "semantic", 1)
    assert strength >= 0.85

    # Get records and verify type
    records = inhibition.get_all_inhibitions(project_id=1)
    assert len(records) == 1
    assert records[0].inhibition_type == InhibitionType.SELECTIVE


def test_decay_respects_explicit_expiration(inhibition):
    """Test that decay_inhibitions respects explicit expiration times."""
    # Add inhibition with future expiration
    inhibition.inhibit(
        project_id=1,
        memory_id=100,
        memory_layer="semantic",
        strength=0.8,
        duration_seconds=3600  # 1 hour from now
    )

    # Add inhibition with past expiration
    inhibition.inhibit(
        project_id=1,
        memory_id=101,
        memory_layer="semantic",
        strength=0.8,
        duration_seconds=-1  # Already expired
    )

    # Decay should remove only the expired one
    removed = inhibition.decay_inhibitions(project_id=1)
    assert removed == 1

    # Memory 100 should still be inhibited
    assert inhibition.is_inhibited(100, "semantic", 1)
    # Memory 101 should not be inhibited (was removed)
    assert not inhibition.is_inhibited(101, "semantic", 1)
