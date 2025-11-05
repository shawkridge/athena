"""Tests for memory reconsolidation API.

Based on neuroscience research (Nader & Hardt 2009): memories become labile
when retrieved and can be modified during a reconsolidation window.
"""

import pytest
from datetime import datetime, timedelta
import time

from athena.core.models import Memory, MemoryType, ConsolidationState
from athena.memory.store import MemoryStore


@pytest.fixture
def memory_store(tmp_path):
    """Create test memory store."""
    db_path = tmp_path / "test.db"
    store = MemoryStore(db_path)

    # Run migration to add reconsolidation fields
    from migrations.runner import run_all_migrations
    run_all_migrations(str(db_path))

    # Create test project
    project = store.create_project("test_project", "/test/path")

    return store, project


def test_update_memory_creates_new_version(memory_store):
    """Test that update_memory creates a new version."""
    store, project = memory_store

    # Create original memory
    original_id = store.remember(
        content="User authentication uses MD5 hashing",
        memory_type=MemoryType.FACT,
        project_id=project.id,
        tags=["authentication", "security"]
    )

    # Update memory with corrected information
    new_id = store.update_memory(
        memory_id=original_id,
        new_content="User authentication uses bcrypt hashing",
        update_reason="Corrected hashing algorithm - MD5 is insecure"
    )

    assert new_id != original_id, "Should create new memory ID"
    assert new_id > original_id, "New ID should be sequential"


def test_original_memory_marked_superseded(memory_store):
    """Test that original memory is marked as superseded."""
    store, project = memory_store

    original_id = store.remember(
        content="API rate limit is 100 requests per minute",
        memory_type=MemoryType.FACT,
        project_id=project.id
    )

    new_id = store.update_memory(
        memory_id=original_id,
        new_content="API rate limit is 1000 requests per minute",
        update_reason="Rate limit increased"
    )

    # Check original memory state
    cursor = store.db.conn.cursor()
    cursor.execute("""
        SELECT consolidation_state, superseded_by
        FROM memories WHERE id = ?
    """, (original_id,))

    original = cursor.fetchone()

    assert original['consolidation_state'] == 'superseded'
    assert original['superseded_by'] == new_id


def test_version_tracking(memory_store):
    """Test version numbering across updates."""
    store, project = memory_store

    # Create original (version 1)
    v1_id = store.remember(
        content="Version 1",
        memory_type=MemoryType.FACT,
        project_id=project.id
    )

    # Update to version 2
    v2_id = store.update_memory(
        memory_id=v1_id,
        new_content="Version 2",
        update_reason="First update"
    )

    # Update to version 3
    v3_id = store.update_memory(
        memory_id=v2_id,
        new_content="Version 3",
        update_reason="Second update"
    )

    # Check versions
    cursor = store.db.conn.cursor()

    cursor.execute("SELECT version FROM memories WHERE id = ?", (v1_id,))
    assert cursor.fetchone()['version'] == 1

    cursor.execute("SELECT version FROM memories WHERE id = ?", (v2_id,))
    assert cursor.fetchone()['version'] == 2

    cursor.execute("SELECT version FROM memories WHERE id = ?", (v3_id,))
    assert cursor.fetchone()['version'] == 3


def test_get_memory_history(memory_store):
    """Test retrieving full memory history."""
    store, project = memory_store

    # Create memory with multiple updates
    v1_id = store.remember(
        content="Initial version",
        memory_type=MemoryType.FACT,
        project_id=project.id
    )

    v2_id = store.update_memory(
        memory_id=v1_id,
        new_content="Second version",
        update_reason="Refinement"
    )

    v3_id = store.update_memory(
        memory_id=v2_id,
        new_content="Third version",
        update_reason="Further refinement"
    )

    # Get history from latest version
    history = store.get_memory_history(v3_id)

    assert len(history) == 3, "Should have 3 versions"

    # Should be ordered oldest first
    assert history[0]['id'] == v1_id
    assert history[1]['id'] == v2_id
    assert history[2]['id'] == v3_id

    # Check content
    assert "Initial" in history[0]['content']
    assert "Second" in history[1]['content']
    assert "Third" in history[2]['content']

    # Check update reasons
    assert history[1]['update_reason'] == "Refinement"
    assert history[2]['update_reason'] == "Further refinement"


def test_mark_memory_labile(memory_store):
    """Test marking memory as labile after retrieval."""
    store, project = memory_store

    memory_id = store.remember(
        content="Test memory",
        memory_type=MemoryType.FACT,
        project_id=project.id
    )

    # Mark as labile
    store.mark_memory_labile(memory_id)

    # Check state
    cursor = store.db.conn.cursor()
    cursor.execute("""
        SELECT consolidation_state, last_retrieved
        FROM memories WHERE id = ?
    """, (memory_id,))

    row = cursor.fetchone()

    assert row['consolidation_state'] == 'labile'
    assert row['last_retrieved'] is not None


def test_reconsolidation_window_active(memory_store):
    """Test reconsolidation window is active immediately after marking labile."""
    store, project = memory_store

    memory_id = store.remember(
        content="Test memory",
        memory_type=MemoryType.FACT,
        project_id=project.id
    )

    store.mark_memory_labile(memory_id, window_minutes=5)

    # Should be in window immediately
    assert store.is_in_reconsolidation_window(memory_id, window_minutes=5)


def test_reconsolidation_window_expires(memory_store):
    """Test reconsolidation window expires after time limit."""
    store, project = memory_store

    memory_id = store.remember(
        content="Test memory",
        memory_type=MemoryType.FACT,
        project_id=project.id
    )

    # Mark labile with very short window
    store.mark_memory_labile(memory_id, window_minutes=0.01)  # ~0.6 seconds

    # Wait for window to expire
    time.sleep(1)

    # Should not be in window anymore
    assert not store.is_in_reconsolidation_window(memory_id, window_minutes=0.01)


def test_update_preserves_metadata(memory_store):
    """Test that update preserves tags and memory type."""
    store, project = memory_store

    original_tags = ["important", "security", "authentication"]

    original_id = store.remember(
        content="Original content",
        memory_type=MemoryType.DECISION,
        project_id=project.id,
        tags=original_tags
    )

    new_id = store.update_memory(
        memory_id=original_id,
        new_content="Updated content",
        update_reason="Refinement"
    )

    # Check new memory has same metadata
    cursor = store.db.conn.cursor()
    cursor.execute("""
        SELECT memory_type, tags FROM memories WHERE id = ?
    """, (new_id,))

    new_mem = cursor.fetchone()

    assert new_mem['memory_type'] == 'decision'
    import json
    assert set(json.loads(new_mem['tags'])) == set(original_tags)


def test_update_records_confidence(memory_store):
    """Test that update records confidence score."""
    store, project = memory_store

    memory_id = store.remember(
        content="Original",
        memory_type=MemoryType.FACT,
        project_id=project.id
    )

    new_id = store.update_memory(
        memory_id=memory_id,
        new_content="Updated",
        update_reason="Correction",
        confidence=0.95
    )

    # Check confidence was recorded
    cursor = store.db.conn.cursor()
    cursor.execute("""
        SELECT confidence FROM memory_updates WHERE updated_id = ?
    """, (new_id,))

    update_record = cursor.fetchone()
    assert update_record['confidence'] == 0.95


def test_get_history_from_any_version(memory_store):
    """Test that history can be retrieved from any version in chain."""
    store, project = memory_store

    v1 = store.remember("V1", MemoryType.FACT, project.id)
    v2 = store.update_memory(v1, "V2", "Update 1")
    v3 = store.update_memory(v2, "V3", "Update 2")

    # Get history from middle version - should get v1, v2, v3 (full chain)
    history_from_v2 = store.get_memory_history(v2)

    # Should get v1 and v2 (v3 is a future version from v2's perspective)
    assert len(history_from_v2) == 2
    assert history_from_v2[0]['id'] == v1
    assert history_from_v2[1]['id'] == v2

    # Get history from latest version - should get all three
    history_from_v3 = store.get_memory_history(v3)
    assert len(history_from_v3) == 3
    assert history_from_v3[0]['id'] == v1
    assert history_from_v3[1]['id'] == v2
    assert history_from_v3[2]['id'] == v3


def test_consolidation_states_enum(memory_store):
    """Test ConsolidationState enum values."""
    assert ConsolidationState.UNCONSOLIDATED.value == "unconsolidated"
    assert ConsolidationState.CONSOLIDATING.value == "consolidating"
    assert ConsolidationState.CONSOLIDATED.value == "consolidated"
    assert ConsolidationState.LABILE.value == "labile"
    assert ConsolidationState.RECONSOLIDATING.value == "reconsolidating"
    assert ConsolidationState.SUPERSEDED.value == "superseded"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
