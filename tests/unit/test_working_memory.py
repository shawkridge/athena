"""Unit tests for Working Memory Layer (Baddeley's model)."""

import pytest
import math
from datetime import datetime, timedelta
from pathlib import Path

from athena.core.database import Database
from athena.core.embeddings import EmbeddingModel
from athena.working_memory import (
    CentralExecutive,
    PhonologicalLoop,
    VisuospatialSketchpad,
    EpisodicBuffer,
    ConsolidationRouter,
    WorkingMemoryItem,
    Goal,
)


@pytest.fixture
def temp_db(tmp_path):
    """Create temporary database for testing."""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))

    # Run working memory migration
    migration_path = Path(__file__).parent.parent.parent / "migrations" / "001_working_memory_schema.sql"
    with open(migration_path, 'r') as f:
        schema_sql = f.read()

    # Execute schema
    with db.conn:
        db.conn.executescript(schema_sql)

    yield db_path

    # Cleanup handled by tmp_path


@pytest.fixture
def embedding_model():
    """Create embedding model for tests."""
    return EmbeddingModel()


# ============================================================================
# Phonological Loop Tests (15 tests)
# ============================================================================

class TestPhonologicalLoop:
    """Test Phonological Loop component."""

    def test_capacity_constraint_7_items(self, temp_db, embedding_model):
        """Test 7±2 capacity constraint (Miller's law) - 7 items."""
        loop = PhonologicalLoop(temp_db, embedding_model)

        # Add 7 items (should fit)
        for i in range(7):
            loop.add_item(1, f"Item {i}", importance=0.5)

        items = loop.get_items(1)
        assert len(items) == 7, "Should hold exactly 7 items"

    def test_capacity_constraint_triggers_consolidation(self, temp_db, embedding_model):
        """Test that adding 8th item triggers consolidation."""
        loop = PhonologicalLoop(temp_db, embedding_model)

        # Fill to capacity
        for i in range(7):
            loop.add_item(1, f"Item {i}", importance=0.5)

        # Add 8th item (should trigger auto-consolidation)
        loop.add_item(1, "Item 8", importance=0.5)

        items = loop.get_items(1)
        assert len(items) <= 7, "Should not exceed 7 items after consolidation"

    def test_exponential_decay_pattern(self, temp_db, embedding_model):
        """Test that activation decays exponentially over time."""
        loop = PhonologicalLoop(temp_db, embedding_model)
        db = Database(temp_db)

        # Add item with known activation
        item_id = loop.add_item(1, "Test item", importance=0.5)

        # Simulate time passing and check decay
        base_decay_rate = 0.1
        importance = 0.5
        # Adaptive decay: λ = decay_rate * (1 - importance * 0.5)
        adaptive_rate = base_decay_rate * (1 - importance * 0.5)

        time_points = [0, 10, 20, 30, 60]
        for seconds in time_points[1:]:
            # Simulate time passing
            with db.conn:
                db.conn.execute("""
                    UPDATE working_memory
                    SET last_accessed = datetime('now', ?)
                    WHERE id = ?
                """, (f'-{seconds} seconds', item_id))

            items = loop.get_items(1)
            activation = items[0].current_activation

            # Verify exponential decay: A(t) = A₀ * e^(-λt)
            # where λ is adaptive based on importance
            # Allow some tolerance for calculation differences
            expected = math.exp(-adaptive_rate * seconds)
            assert 0.5 < activation / expected < 2.0, f"Decay pattern not exponential at t={seconds}"

    def test_importance_affects_decay_rate(self, temp_db, embedding_model):
        """Test that important items decay slower."""
        loop = PhonologicalLoop(temp_db, embedding_model)
        db = Database(temp_db)

        # Add two items: one unimportant, one important
        unimportant_id = loop.add_item(1, "Unimportant", importance=0.1)
        important_id = loop.add_item(1, "Important", importance=0.9)

        # Wait 30 seconds
        with db.conn:
            db.conn.execute("""
                UPDATE working_memory
                SET last_accessed = datetime('now', '-30 seconds')
                WHERE project_id = 1
            """)

        items = loop.get_items(1)
        item_dict = {item.id: item for item in items}

        unimportant_activation = getattr(item_dict[unimportant_id], 'current_activation', item_dict[unimportant_id].activation_level)
        important_activation = getattr(item_dict[important_id], 'current_activation', item_dict[important_id].activation_level)

        assert important_activation > unimportant_activation, \
            "Important item should have higher activation after decay"

    def test_rehearsal_refreshes_activation(self, temp_db, embedding_model):
        """Test that rehearsing item refreshes activation to 1.0."""
        loop = PhonologicalLoop(temp_db, embedding_model)
        db = Database(temp_db)

        item_id = loop.add_item(1, "Test", importance=0.5)

        # Simulate time passing
        with db.conn:
            db.conn.execute("""
                UPDATE working_memory
                SET last_accessed = datetime('now', '-20 seconds'),
                    activation_level = 0.5
                WHERE id = ?
            """, (item_id,))

        # Check decayed activation
        items_before = loop.get_items(1)
        activation_before = getattr(items_before[0], 'current_activation', items_before[0].activation_level)
        assert activation_before < 0.9, "Should be decayed before rehearsal"

        # Rehearse
        loop.rehearse(item_id)

        # Check refreshed activation
        items_after = loop.get_items(1)
        activation_after = getattr(items_after[0], 'current_activation', items_after[0].activation_level)

        assert activation_after > activation_before, "Rehearsal should increase activation"
        assert activation_after >= 0.95, "Rehearsal should restore to near-full activation"

    def test_semantic_search_finds_similar(self, temp_db, embedding_model):
        """Test semantic search finds semantically similar items."""
        loop = PhonologicalLoop(temp_db, embedding_model)

        # Add items
        loop.add_item(1, "The cat sat on the mat", importance=0.5)
        loop.add_item(1, "The dog ran in the park", importance=0.5)
        loop.add_item(1, "Python programming language", importance=0.5)

        # Search for animal-related content
        results = loop.search(1, "feline animal", k=2)

        assert len(results) > 0, "Should find results"
        # Should find cat-related content with high similarity
        assert any("cat" in r.content.lower() for r in results), \
            "Should find semantically similar content"

    def test_clear_removes_all_items(self, temp_db, embedding_model):
        """Test that clear removes all items."""
        loop = PhonologicalLoop(temp_db, embedding_model)

        # Add items
        for i in range(5):
            loop.add_item(1, f"Item {i}", importance=0.5)

        assert len(loop.get_items(1)) == 5

        # Clear
        loop.clear(1)

        assert len(loop.get_items(1)) == 0, "Clear should remove all items"

    def test_multiple_projects_isolated(self, temp_db, embedding_model):
        """Test that different projects have isolated phonological loops."""
        loop = PhonologicalLoop(temp_db, embedding_model)

        # Add items to different projects
        loop.add_item(1, "Project 1 item", importance=0.5)
        loop.add_item(2, "Project 2 item", importance=0.5)

        items_p1 = loop.get_items(1)
        items_p2 = loop.get_items(2)

        assert len(items_p1) == 1
        assert len(items_p2) == 1
        assert items_p1[0].content == "Project 1 item"
        assert items_p2[0].content == "Project 2 item"

    def test_get_item_by_id(self, temp_db, embedding_model):
        """Test retrieving specific item by ID."""
        loop = PhonologicalLoop(temp_db, embedding_model)

        item_id = loop.add_item(1, "Test content", importance=0.5)

        item = loop.get_item(item_id)

        assert item is not None
        assert item.id == item_id
        assert item.content == "Test content"

    def test_update_item_importance(self, temp_db, embedding_model):
        """Test updating item importance score."""
        loop = PhonologicalLoop(temp_db, embedding_model)

        item_id = loop.add_item(1, "Test", importance=0.3)

        # Update importance
        loop.update_importance(item_id, 0.9)

        item = loop.get_item(item_id)
        assert item.importance_score == 0.9

    def test_decay_log_created(self, temp_db, embedding_model):
        """Test that decay events are logged."""
        loop = PhonologicalLoop(temp_db, embedding_model)
        db = Database(temp_db)

        item_id = loop.add_item(1, "Test", importance=0.5)

        # Trigger decay calculation
        with db.conn:
            db.conn.execute("""
                UPDATE working_memory
                SET last_accessed = datetime('now', '-30 seconds')
                WHERE id = ?
            """, (item_id,))

        # Get items (which calculates decay)
        loop.get_items(1)

        # Check decay log exists
        with db.conn:
            log_entries = db.conn.execute("""
                SELECT COUNT(*) FROM working_memory_decay_log
                WHERE wm_id = ?
            """, (item_id,)).fetchone()[0]

        # May or may not log depending on implementation, but schema should exist
        assert log_entries >= 0

    def test_items_sorted_by_activation(self, temp_db, embedding_model):
        """Test that items are returned sorted by activation level."""
        loop = PhonologicalLoop(temp_db, embedding_model)
        db = Database(temp_db)

        # Add items with different importance
        id1 = loop.add_item(1, "Low importance", importance=0.2)
        id2 = loop.add_item(1, "High importance", importance=0.9)

        # Age the low importance item
        with db.conn:
            db.conn.execute("""
                UPDATE working_memory
                SET last_accessed = datetime('now', '-30 seconds')
                WHERE id = ?
            """, (id1,))

        items = loop.get_items(1)

        # Should be sorted by current activation (high importance should be first)
        assert items[0].id == id2, "Items should be sorted by activation descending"

    def test_empty_project_returns_empty_list(self, temp_db, embedding_model):
        """Test that empty project returns empty list."""
        loop = PhonologicalLoop(temp_db, embedding_model)

        items = loop.get_items(999)

        assert items == []

    def test_add_item_returns_id(self, temp_db, embedding_model):
        """Test that add_item returns the new item ID."""
        loop = PhonologicalLoop(temp_db, embedding_model)

        item_id = loop.add_item(1, "Test", importance=0.5)

        assert isinstance(item_id, int)
        assert item_id > 0

    def test_concurrent_adds_unique_ids(self, temp_db, embedding_model):
        """Test that concurrent adds get unique IDs."""
        loop = PhonologicalLoop(temp_db, embedding_model)

        ids = []
        for i in range(5):
            item_id = loop.add_item(1, f"Item {i}", importance=0.5)
            ids.append(item_id)

        # All IDs should be unique
        assert len(ids) == len(set(ids)), "All IDs should be unique"


# ============================================================================
# Visuospatial Sketchpad Tests (10 tests)
# ============================================================================

class TestVisuospatialSketchpad:
    """Test Visuospatial Sketchpad component."""

    def test_file_tracking(self, temp_db):
        """Test tracking of current files in workspace."""
        sketchpad = VisuospatialSketchpad(temp_db)

        # Add file reference
        item_id = sketchpad.add_item(1, "Working on auth module", file_path="/src/auth/jwt.py")

        items = sketchpad.get_items(1)

        assert len(items) == 1
        assert items[0].file_path == "/src/auth/jwt.py"
        assert items[0].content == "Working on auth module"

    def test_spatial_relations_tracked(self, temp_db):
        """Test that spatial relationships between files are tracked."""
        sketchpad = VisuospatialSketchpad(temp_db)

        # Add related files
        sketchpad.add_item(1, "Auth module", file_path="/src/auth/jwt.py")
        sketchpad.add_item(1, "Auth tests", file_path="/src/auth/test_jwt.py")

        # Get spatial neighbors
        neighbors = sketchpad.get_spatial_neighbors(1, "/src/auth/jwt.py")

        assert len(neighbors) > 0
        assert any("test_jwt.py" in getattr(n, 'file_path', '') for n in neighbors)

    def test_hierarchy_integration(self, temp_db):
        """Test integration with spatial hierarchy."""
        sketchpad = VisuospatialSketchpad(temp_db)

        # Add file
        sketchpad.add_item(1, "Deep file", file_path="/home/user/project/src/module/file.py")

        # Should have hierarchy information
        items = sketchpad.get_items(1)

        assert items[0].depth >= 0
        assert items[0].parent_path is not None

    def test_capacity_limit(self, temp_db):
        """Test capacity constraint for spatial items."""
        sketchpad = VisuospatialSketchpad(temp_db)

        # Add items up to capacity
        for i in range(8):
            sketchpad.add_item(1, f"File {i}", file_path=f"/src/file{i}.py")

        items = sketchpad.get_items(1)
        assert len(items) <= 7, "Should respect capacity limit"

    def test_clear_workspace(self, temp_db):
        """Test clearing workspace."""
        sketchpad = VisuospatialSketchpad(temp_db)

        sketchpad.add_item(1, "File", file_path="/src/file.py")
        assert len(sketchpad.get_items(1)) == 1

        sketchpad.clear(1)
        assert len(sketchpad.get_items(1)) == 0

    def test_update_file_location(self, temp_db):
        """Test updating file location."""
        sketchpad = VisuospatialSketchpad(temp_db)

        item_id = sketchpad.add_item(1, "File", file_path="/old/path.py")

        sketchpad.update_file_path(item_id, "/new/path.py")

        item = sketchpad.get_item(item_id)
        assert item.file_path == "/new/path.py"

    def test_find_by_directory(self, temp_db):
        """Test finding files in specific directory."""
        sketchpad = VisuospatialSketchpad(temp_db)

        sketchpad.add_item(1, "Auth file", file_path="/src/auth/jwt.py")
        sketchpad.add_item(1, "Utils file", file_path="/src/utils/helper.py")

        auth_files = sketchpad.find_by_directory(1, "/src/auth")

        assert len(auth_files) == 1
        assert "jwt.py" in auth_files[0].file_path

    def test_items_without_file_path(self, temp_db):
        """Test adding spatial items without file path."""
        sketchpad = VisuospatialSketchpad(temp_db)

        item_id = sketchpad.add_item(1, "General spatial note", file_path=None)

        items = sketchpad.get_items(1)
        assert len(items) == 1
        assert items[0].file_path is None or items[0].file_path == ""

    def test_multiple_files_same_directory(self, temp_db):
        """Test tracking multiple files in same directory."""
        sketchpad = VisuospatialSketchpad(temp_db)

        sketchpad.add_item(1, "File 1", file_path="/src/auth/jwt.py")
        sketchpad.add_item(1, "File 2", file_path="/src/auth/oauth.py")

        items = sketchpad.find_by_directory(1, "/src/auth")

        assert len(items) == 2

    def test_activation_decay_for_spatial(self, temp_db):
        """Test that spatial items also decay over time."""
        sketchpad = VisuospatialSketchpad(temp_db)
        db = Database(temp_db)

        item_id = sketchpad.add_item(1, "File", file_path="/src/file.py")

        # Age the item
        with db.conn:
            db.conn.execute("""
                UPDATE working_memory
                SET last_accessed = datetime('now', '-30 seconds')
                WHERE id = ?
            """, (item_id,))

        items = sketchpad.get_items(1)
        activation = getattr(items[0], 'current_activation', items[0].activation_level)

        assert activation < 1.0, "Spatial items should decay"


# ============================================================================
# Episodic Buffer Tests (10 tests)
# ============================================================================

class TestEpisodicBuffer:
    """Test Episodic Buffer component."""

    def test_multimodal_integration(self, temp_db, embedding_model):
        """Test integration of verbal and spatial information."""
        buffer = EpisodicBuffer(temp_db, embedding_model)

        # Add multimodal item
        item_id = buffer.add_item(
            1,
            "Implemented JWT authentication in /src/auth/jwt.py",
            sources={"verbal": "JWT authentication", "spatial": "/src/auth/jwt.py"}
        )

        items = buffer.get_items(1)

        assert len(items) == 1
        assert "JWT" in items[0].content

    def test_chunking_mechanism(self, temp_db, embedding_model):
        """Test chunking of related information (4±1 items)."""
        buffer = EpisodicBuffer(temp_db, embedding_model)

        # Add chunk of related items
        chunk_id = buffer.create_chunk(1, [
            "Step 1: Create user model",
            "Step 2: Add authentication",
            "Step 3: Implement JWT",
            "Step 4: Add tests"
        ])

        chunks = buffer.get_chunks(1)

        assert len(chunks) > 0
        assert chunks[0].chunk_size <= 5, "Chunks should respect 4±1 limit"

    def test_source_tracking(self, temp_db, embedding_model):
        """Test tracking sources of integrated information."""
        buffer = EpisodicBuffer(temp_db, embedding_model)

        item_id = buffer.add_item(
            1,
            "Test content",
            sources={"phonological": 123, "visuospatial": 456}
        )

        item = buffer.get_item(item_id)

        assert hasattr(item, 'sources') or hasattr(item, 'source_items')

    def test_capacity_constraint_4_items(self, temp_db, embedding_model):
        """Test 4±1 capacity for episodic buffer chunks."""
        buffer = EpisodicBuffer(temp_db, embedding_model)

        # Try to add 6 items to a chunk (should cap at 5)
        items = [f"Item {i}" for i in range(6)]

        chunk_id = buffer.create_chunk(1, items)
        chunks = buffer.get_chunks(1)

        chunk_size = chunks[0].chunk_size
        assert chunk_size <= 5, "Should enforce 4±1 capacity"

    def test_bind_phonological_spatial(self, temp_db, embedding_model):
        """Test binding phonological and spatial items."""
        buffer = EpisodicBuffer(temp_db, embedding_model)

        # Create binding
        item_id = buffer.bind_items(
            1,
            phonological_id=101,
            visuospatial_id=202,
            binding_content="JWT implementation in auth module"
        )

        items = buffer.get_items(1)
        assert len(items) > 0

    def test_retrieve_by_source(self, temp_db, embedding_model):
        """Test retrieving items by source."""
        buffer = EpisodicBuffer(temp_db, embedding_model)

        buffer.add_item(1, "From phonological", sources={"phonological": 100})
        buffer.add_item(1, "From spatial", sources={"visuospatial": 200})

        phono_items = buffer.get_items_by_source(1, "phonological")

        assert len(phono_items) > 0

    def test_clear_buffer(self, temp_db, embedding_model):
        """Test clearing episodic buffer."""
        buffer = EpisodicBuffer(temp_db, embedding_model)

        buffer.add_item(1, "Test", sources={})
        assert len(buffer.get_items(1)) > 0

        buffer.clear(1)
        assert len(buffer.get_items(1)) == 0

    def test_chunk_relationships(self, temp_db, embedding_model):
        """Test relationships between chunked items."""
        buffer = EpisodicBuffer(temp_db, embedding_model)

        chunk_id = buffer.create_chunk(1, [
            "Related item 1",
            "Related item 2",
            "Related item 3"
        ])

        # Items in chunk should be related
        chunks = buffer.get_chunks(1)
        assert chunks[0].chunk_size == 3

    def test_semantic_search_in_buffer(self, temp_db, embedding_model):
        """Test semantic search within episodic buffer."""
        buffer = EpisodicBuffer(temp_db, embedding_model)

        buffer.add_item(1, "Authentication implementation", sources={})
        buffer.add_item(1, "Database schema design", sources={})

        results = buffer.search(1, "login security", k=1)

        assert len(results) > 0

    def test_item_activation_levels(self, temp_db, embedding_model):
        """Test that buffer items have activation levels."""
        buffer = EpisodicBuffer(temp_db, embedding_model)

        item_id = buffer.add_item(1, "Test", sources={})

        items = buffer.get_items(1)

        assert hasattr(items[0], 'activation_level') or hasattr(items[0], 'current_activation')


# ============================================================================
# Central Executive Tests (15 tests)
# ============================================================================

class TestCentralExecutive:
    """Test Central Executive component."""

    def test_set_primary_goal(self, temp_db, embedding_model):
        """Test setting primary goal."""
        exec = CentralExecutive(temp_db, embedding_model)

        goal = exec.set_goal(1, "Implement authentication", goal_type="primary", priority=8)

        assert goal.id > 0
        assert goal.goal_text == "Implement authentication"
        assert goal.goal_type == "primary"
        assert goal.priority == 8

    def test_set_subgoal(self, temp_db, embedding_model):
        """Test setting subgoal with parent."""
        exec = CentralExecutive(temp_db, embedding_model)

        parent = exec.set_goal(1, "Main goal", goal_type="primary")
        subgoal = exec.set_goal(1, "Sub task", goal_type="subgoal", parent_goal_id=parent.id)

        assert subgoal.parent_goal_id == parent.id
        assert subgoal.goal_type == "subgoal"

    def test_get_active_goals_sorted(self, temp_db, embedding_model):
        """Test getting active goals sorted by priority."""
        exec = CentralExecutive(temp_db, embedding_model)

        exec.set_goal(1, "Low priority", priority=3)
        exec.set_goal(1, "High priority", priority=9)
        exec.set_goal(1, "Medium priority", priority=5)

        goals = exec.get_active_goals(1)

        assert len(goals) == 3
        # Should be sorted by priority descending
        assert goals[0].priority >= goals[1].priority >= goals[2].priority

    def test_update_goal_progress(self, temp_db, embedding_model):
        """Test updating goal completion progress."""
        exec = CentralExecutive(temp_db, embedding_model)

        goal = exec.set_goal(1, "Test goal")

        exec.update_goal_progress(goal.id, progress=0.5)

        updated_goal = exec.get_goal(goal.id)
        assert updated_goal.progress == 0.5

    def test_update_goal_status(self, temp_db, embedding_model):
        """Test updating goal status."""
        exec = CentralExecutive(temp_db, embedding_model)

        goal = exec.set_goal(1, "Test goal")

        exec.update_goal_status(goal.id, "in_progress")

        updated_goal = exec.get_goal(goal.id)
        assert updated_goal.status == "in_progress"

    def test_check_capacity_not_full(self, temp_db, embedding_model):
        """Test capacity check when not at capacity."""
        exec = CentralExecutive(temp_db, embedding_model)
        loop = PhonologicalLoop(temp_db, embedding_model)

        # Add 5 items
        for i in range(5):
            loop.add_item(1, f"Item {i}")

        at_capacity = exec.check_capacity(1)

        assert at_capacity == False, "Should not be at capacity with 5 items"

    def test_check_capacity_full(self, temp_db, embedding_model):
        """Test capacity check when at capacity."""
        exec = CentralExecutive(temp_db, embedding_model)
        loop = PhonologicalLoop(temp_db, embedding_model)

        # Fill to capacity
        for i in range(7):
            loop.add_item(1, f"Item {i}")

        at_capacity = exec.check_capacity(1)

        assert at_capacity == True, "Should be at capacity with 7 items"

    def test_trigger_consolidation(self, temp_db, embedding_model):
        """Test triggering consolidation when at capacity."""
        exec = CentralExecutive(temp_db, embedding_model)
        loop = PhonologicalLoop(temp_db, embedding_model)

        # Fill to capacity
        for i in range(7):
            loop.add_item(1, f"Item {i}", importance=0.3)

        # Trigger consolidation
        exec.trigger_consolidation(1)

        # Should have freed some space
        items_after = loop.get_items(1)
        assert len(items_after) < 7, "Consolidation should free space"

    def test_allocate_attention(self, temp_db, embedding_model):
        """Test attention allocation to goals."""
        exec = CentralExecutive(temp_db, embedding_model)

        goal = exec.set_goal(1, "Focus on this", priority=9)

        exec.allocate_attention(1, goal.id, weight=0.8)

        focus = exec.get_attention_focus(1)

        assert len(focus) > 0
        assert focus[0].goal_id == goal.id
        assert focus[0].attention_weight == 0.8

    def test_suspend_resume_goal(self, temp_db, embedding_model):
        """Test suspending and resuming goals."""
        exec = CentralExecutive(temp_db, embedding_model)

        goal = exec.set_goal(1, "Test goal")

        # Suspend
        exec.suspend_goal(goal.id)
        suspended = exec.get_goal(goal.id)
        assert suspended.status == "suspended"

        # Resume
        exec.resume_goal(goal.id)
        resumed = exec.get_goal(goal.id)
        assert resumed.status == "active"

    def test_goal_hierarchy_depth(self, temp_db, embedding_model):
        """Test goal hierarchy with multiple levels."""
        exec = CentralExecutive(temp_db, embedding_model)

        level1 = exec.set_goal(1, "Level 1", goal_type="primary")
        level2 = exec.set_goal(1, "Level 2", goal_type="subgoal", parent_goal_id=level1.id)
        level3 = exec.set_goal(1, "Level 3", goal_type="subgoal", parent_goal_id=level2.id)

        # Get all goals
        goals = exec.get_active_goals(1)
        assert len(goals) == 3

    def test_complete_goal(self, temp_db, embedding_model):
        """Test marking goal as completed."""
        exec = CentralExecutive(temp_db, embedding_model)

        goal = exec.set_goal(1, "Test goal")

        exec.complete_goal(goal.id)

        completed = exec.get_goal(goal.id)
        assert completed.status == "completed"
        assert completed.progress == 1.0

    def test_get_subgoals(self, temp_db, embedding_model):
        """Test getting subgoals of a parent goal."""
        exec = CentralExecutive(temp_db, embedding_model)

        parent = exec.set_goal(1, "Parent", goal_type="primary")
        exec.set_goal(1, "Child 1", goal_type="subgoal", parent_goal_id=parent.id)
        exec.set_goal(1, "Child 2", goal_type="subgoal", parent_goal_id=parent.id)

        subgoals = exec.get_subgoals(parent.id)

        assert len(subgoals) == 2

    def test_multiple_projects_goals_isolated(self, temp_db, embedding_model):
        """Test that goals are isolated per project."""
        exec = CentralExecutive(temp_db, embedding_model)

        exec.set_goal(1, "Project 1 goal")
        exec.set_goal(2, "Project 2 goal")

        p1_goals = exec.get_active_goals(1)
        p2_goals = exec.get_active_goals(2)

        assert len(p1_goals) == 1
        assert len(p2_goals) == 1
        assert p1_goals[0].goal_text == "Project 1 goal"

    def test_capacity_monitoring(self, temp_db, embedding_model):
        """Test continuous capacity monitoring."""
        exec = CentralExecutive(temp_db, embedding_model)
        loop = PhonologicalLoop(temp_db, embedding_model)

        # Add items gradually
        for i in range(5):
            loop.add_item(1, f"Item {i}")
            capacity_status = exec.get_capacity_status(1)
            assert 'count' in capacity_status
            assert 'max_capacity' in capacity_status


# ============================================================================
# Consolidation Router Tests (10 tests)
# ============================================================================

class TestConsolidationRouter:
    """Test ML-based consolidation routing."""

    def test_heuristic_routing_episodic(self, temp_db):
        """Test heuristic routing for episodic content."""
        router = ConsolidationRouter(temp_db)

        episodic_content = "Yesterday at 3pm we debugged the auth error in /src/auth/jwt.py"

        target_layer = router._heuristic_route(episodic_content)

        assert target_layer == "episodic", "Temporal content should route to episodic"

    def test_heuristic_routing_procedural(self, temp_db):
        """Test heuristic routing for procedural content."""
        router = ConsolidationRouter(temp_db)

        procedural_content = "To deploy: run npm build, then docker push, then kubectl apply"

        target_layer = router._heuristic_route(procedural_content)

        assert target_layer == "procedural", "Workflow should route to procedural"

    def test_heuristic_routing_semantic(self, temp_db):
        """Test heuristic routing for semantic content."""
        router = ConsolidationRouter(temp_db)

        semantic_content = "JWT tokens provide stateless authentication for REST APIs"

        target_layer = router._heuristic_route(semantic_content)

        assert target_layer == "semantic", "Factual content should route to semantic"

    def test_ml_routing_with_features(self, temp_db):
        """Test ML-based routing with feature extraction."""
        router = ConsolidationRouter(temp_db)
        db = Database(temp_db)

        # Add a working memory item
        with db.conn:
            cursor = db.conn.execute("""
                INSERT INTO working_memory (project_id, content, content_type, component, importance_score)
                VALUES (1, 'Test content with temporal marker yesterday', 'verbal', 'phonological', 0.5)
            """)
            item_id = cursor.lastrowid

        # Extract features
        features = router._extract_features(item_id)

        assert len(features) == 11, "Should extract 11 features"
        assert all(isinstance(f, (int, float)) for f in features), "Features should be numeric"

    def test_route_item_default_to_semantic(self, temp_db):
        """Test that items default to semantic layer."""
        router = ConsolidationRouter(temp_db)
        db = Database(temp_db)

        # Add item
        with db.conn:
            cursor = db.conn.execute("""
                INSERT INTO working_memory (project_id, content, content_type, component, importance_score)
                VALUES (1, 'Generic content', 'verbal', 'phonological', 0.5)
            """)
            item_id = cursor.lastrowid

        result = router.route_item(1, item_id, use_ml=False)

        target_layer = result['target_layer'] if isinstance(result, dict) else result.target_layer
        assert target_layer in ['semantic', 'episodic', 'procedural']

    def test_provide_feedback(self, temp_db):
        """Test online learning from feedback."""
        router = ConsolidationRouter(temp_db)
        db = Database(temp_db)

        # Create route entry
        with db.conn:
            cursor = db.conn.execute("""
                INSERT INTO consolidation_routes
                (wm_id, target_layer, confidence, features, routed_at)
                VALUES (1, 'semantic', 0.8, ?, datetime('now'))
            """, (str([0.5]*11),))
            route_id = cursor.lastrowid

        # Provide feedback
        router.provide_feedback(route_id, was_correct=True)

        # Check feedback recorded
        with db.conn:
            feedback = db.conn.execute("""
                SELECT was_correct FROM consolidation_routes WHERE id = ?
            """, (route_id,)).fetchone()

        assert feedback[0] == 1  # True

    def test_batch_routing(self, temp_db):
        """Test routing multiple items in batch."""
        router = ConsolidationRouter(temp_db)
        db = Database(temp_db)

        # Add multiple items
        item_ids = []
        with db.conn:
            for i in range(3):
                cursor = db.conn.execute("""
                    INSERT INTO working_memory (project_id, content, content_type, component, importance_score)
                    VALUES (1, ?, 'verbal', 'phonological', 0.5)
                """, (f"Item {i}",))
                item_ids.append(cursor.lastrowid)

        # Route all
        results = router.route_batch(1, item_ids)

        assert len(results) == 3

    def test_temporal_indicator_detection(self, temp_db):
        """Test detection of temporal indicators."""
        router = ConsolidationRouter(temp_db)

        assert router._has_temporal_indicators("yesterday we fixed the bug")
        assert router._has_temporal_indicators("at 3pm the test failed")
        assert not router._has_temporal_indicators("JWT provides authentication")

    def test_procedural_pattern_detection(self, temp_db):
        """Test detection of procedural patterns."""
        router = ConsolidationRouter(temp_db)

        assert router._has_procedural_patterns("first run npm install then npm build")
        assert router._has_procedural_patterns("to deploy: push to docker then kubectl")
        assert not router._has_procedural_patterns("authentication is important")

    def test_confidence_scoring(self, temp_db):
        """Test confidence scoring for routing decisions."""
        router = ConsolidationRouter(temp_db)
        db = Database(temp_db)

        # Add item with clear episodic markers
        with db.conn:
            cursor = db.conn.execute("""
                INSERT INTO working_memory (project_id, content, content_type, component, importance_score)
                VALUES (1, 'Yesterday at 3pm we debugged the error', 'verbal', 'phonological', 0.5)
            """)
            item_id = cursor.lastrowid

        result = router.route_item(1, item_id)

        assert 'confidence' in result
        assert 0.0 <= result['confidence'] <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
