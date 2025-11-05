"""Tests for temporal priming."""

import time
from datetime import datetime, timedelta

import pytest

from athena.associations.priming import TemporalPriming
from athena.core.database import Database


@pytest.fixture
def db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))

    # Create test project
    db.create_project("test-project", str(tmp_path))

    # Create priming_state table
    db.conn.execute(
        """
        CREATE TABLE IF NOT EXISTS priming_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            memory_id INTEGER NOT NULL,
            memory_layer TEXT NOT NULL,
            priming_strength REAL DEFAULT 1.0,
            primed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
        """
    )
    db.conn.commit()

    return db


@pytest.fixture
def priming(db):
    """Create temporal priming manager."""
    return TemporalPriming(db)


def test_prime_memory(priming):
    """Test priming a memory."""
    priming_id = priming.prime(
        memory_id=100,
        layer="semantic",
        project_id=1,
        duration_seconds=300,
    )

    assert priming_id > 0

    # Verify priming created
    boost = priming.get_priming_boost(100, "semantic", 1)
    assert boost > 1.0  # Should be boosted


def test_short_term_priming_boost(priming):
    """Test short-term priming (0-5 min) gives 2x boost."""
    priming.prime(100, "semantic", 1, duration_seconds=300)

    boost = priming.get_priming_boost(100, "semantic", 1)
    assert boost == 2.0  # Short-term boost


def test_medium_term_priming_boost(priming, db):
    """Test medium-term priming (5-30 min) gives 1.5x boost."""
    from datetime import timezone
    # Prime with timestamp 10 minutes ago, expires in future
    primed_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=60)

    # Normalize timestamps to SQLite format
    primed_at_str = primed_at.isoformat().replace('T', ' ').split('+')[0]
    expires_at_str = expires_at.isoformat().replace('T', ' ').split('+')[0]

    with db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO priming_state (
                project_id, memory_id, memory_layer,
                priming_strength, primed_at, expires_at
            )
            VALUES (?, ?, ?, 1.0, ?, ?)
            """,
            (1, 100, "semantic", primed_at_str, expires_at_str),
        )
        conn.commit()

    boost = priming.get_priming_boost(100, "semantic", 1)
    assert boost == 1.5  # Medium-term boost


def test_long_term_priming_boost(priming, db):
    """Test long-term priming (30-60 min) gives 1.2x boost."""
    from datetime import timezone
    # Prime with timestamp 45 minutes ago, expires in future
    primed_at = datetime.now(timezone.utc) - timedelta(minutes=45)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=60)

    # Normalize timestamps to SQLite format
    primed_at_str = primed_at.isoformat().replace('T', ' ').split('+')[0]
    expires_at_str = expires_at.isoformat().replace('T', ' ').split('+')[0]

    with db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO priming_state (
                project_id, memory_id, memory_layer,
                priming_strength, primed_at, expires_at
            )
            VALUES (?, ?, ?, 1.0, ?, ?)
            """,
            (1, 100, "semantic", primed_at_str, expires_at_str),
        )
        conn.commit()

    boost = priming.get_priming_boost(100, "semantic", 1)
    assert boost == 1.2  # Long-term boost


def test_no_priming_boost(priming):
    """Test unprimed memory has no boost."""
    boost = priming.get_priming_boost(999, "semantic", 1)
    assert boost == 1.0  # No boost


def test_refresh_priming(priming):
    """Test that re-priming refreshes duration."""
    # Prime initially
    priming_id1 = priming.prime(100, "semantic", 1, duration_seconds=60)

    # Re-prime (should refresh, not create new)
    priming_id2 = priming.prime(100, "semantic", 1, duration_seconds=300)

    assert priming_id1 == priming_id2

    # Verify still has strong boost (refreshed)
    boost = priming.get_priming_boost(100, "semantic", 1)
    assert boost == 2.0


def test_get_primed_memories(priming):
    """Test getting all primed memories."""
    # Prime multiple memories
    priming.prime(100, "semantic", 1, duration_seconds=300)
    priming.prime(200, "semantic", 1, duration_seconds=300)
    priming.prime(300, "episodic", 1, duration_seconds=300)

    primed = priming.get_primed_memories(1, min_boost=1.2)

    assert len(primed) == 3
    assert all(p.priming_strength >= 1.2 for p in primed)


def test_get_primed_memories_filtered_by_boost(priming, db):
    """Test filtering primed memories by minimum boost."""
    from datetime import timezone
    # Create priming with different ages
    # Recent: 2x boost
    priming.prime(100, "semantic", 1, duration_seconds=300)

    # Old (45 min ago): 1.2x boost
    primed_at = datetime.now(timezone.utc) - timedelta(minutes=45)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=60)

    # Normalize timestamps to SQLite format
    primed_at_str = primed_at.isoformat().replace('T', ' ').split('+')[0]
    expires_at_str = expires_at.isoformat().replace('T', ' ').split('+')[0]

    with db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO priming_state (
                project_id, memory_id, memory_layer,
                priming_strength, primed_at, expires_at
            )
            VALUES (?, ?, ?, 1.0, ?, ?)
            """,
            (1, 200, "semantic", primed_at_str, expires_at_str),
        )
        conn.commit()

    # Get with min_boost=1.5 (should only include recent)
    primed = priming.get_primed_memories(1, min_boost=1.5)
    assert len(primed) == 1
    assert primed[0].memory_id == 100


def test_decay_priming(priming):
    """Test decaying priming strength."""
    priming.prime(100, "semantic", 1, duration_seconds=300)

    # Decay
    decayed = priming.decay_priming(1, decay_rate=0.2)
    assert decayed >= 0


def test_expire_old_priming(priming, db):
    """Test expiring old priming records."""
    from datetime import timezone
    # Create expired priming (both primed and expires in the past)
    expired_at = datetime.now(timezone.utc) - timedelta(minutes=10)

    # Normalize timestamp to SQLite format
    expired_at_str = expired_at.isoformat().replace('T', ' ').split('+')[0]

    with db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO priming_state (
                project_id, memory_id, memory_layer,
                priming_strength, primed_at, expires_at
            )
            VALUES (?, ?, ?, 1.0, ?, ?)
            """,
            (1, 100, "semantic", expired_at_str, expired_at_str),
        )
        conn.commit()

    # Expire old records
    expired = priming.expire_old_priming(1)
    assert expired == 1

    # Verify removed
    boost = priming.get_priming_boost(100, "semantic", 1)
    assert boost == 1.0


def test_clear_priming(priming):
    """Test clearing all priming state."""
    # Create priming
    priming.prime(100, "semantic", 1)
    priming.prime(200, "semantic", 1)

    # Clear all
    cleared = priming.clear_priming(1)
    assert cleared == 2

    # Verify all cleared
    count = priming.get_priming_count(1)
    assert count == 0


def test_get_priming_count(priming):
    """Test counting active priming records."""
    # Initially zero
    assert priming.get_priming_count(1) == 0

    # Add priming
    priming.prime(100, "semantic", 1)
    priming.prime(200, "semantic", 1)

    assert priming.get_priming_count(1) == 2
