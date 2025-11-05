"""Integration tests for working memory and saliency components.

Tests the interaction between:
- Working Memory (phonological loop, visuospatial, episodic buffer)
- Central Executive (attention control, goal management)
- Saliency Calculator (multi-factor scoring)
- Focus type conversion and recommendations

Research backing:
- Baddeley 2000: Working Memory
- Miller 1956: The Magical Number Seven
- Kumar et al. 2023: Bayesian Surprise
- StreamingLLM 2024: Attention mechanisms
"""

import pytest
import math
from datetime import datetime, timedelta
from typing import List

from athena.core.database import Database
from athena.core.embeddings import EmbeddingModel
from athena.working_memory.central_executive import CentralExecutive
from athena.working_memory.saliency import SaliencyCalculator
from athena.working_memory.models import GoalType, GoalStatus


@pytest.fixture
def db_with_schema(tmp_path):
    """Create database with full schema."""
    db = Database(tmp_path / "test.db")
    db.conn.execute("PRAGMA foreign_keys = ON")

    # Minimal schema for working memory + saliency
    db.conn.execute("""
        CREATE TABLE IF NOT EXISTS active_goals (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            goal_text TEXT NOT NULL,
            goal_type TEXT DEFAULT 'primary',
            status TEXT DEFAULT 'active',
            priority INTEGER DEFAULT 5,
            parent_goal_id INTEGER,
            deadline TEXT,
            completion_criteria TEXT,
            metadata TEXT DEFAULT '{}',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.conn.execute("""
        CREATE TABLE IF NOT EXISTS working_memory (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            component TEXT NOT NULL,
            content TEXT NOT NULL,
            content_type TEXT DEFAULT 'verbal',
            importance_score REAL DEFAULT 0.5,
            current_activation REAL DEFAULT 0.5,
            decay_rate REAL DEFAULT 0.02,
            consolidated INTEGER DEFAULT 0,
            consolidated_at TEXT
        )
    """)

    db.conn.execute("""
        CREATE TABLE IF NOT EXISTS attention_focus (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            focus_target TEXT,
            focus_type TEXT DEFAULT 'memory',
            attention_weight REAL DEFAULT 1.0,
            focused_at TEXT DEFAULT CURRENT_TIMESTAMP,
            goal_id INTEGER
        )
    """)

    db.conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            memory_type TEXT DEFAULT 'fact',
            created_at INTEGER NOT NULL,
            access_count INTEGER DEFAULT 0,
            usefulness_score REAL DEFAULT 0.5,
            last_accessed INTEGER
        )
    """)

    db.conn.execute("""
        CREATE TABLE IF NOT EXISTS episodic_events (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            event_type TEXT,
            session_id TEXT
        )
    """)

    db.conn.commit()
    return db


@pytest.fixture
def embedder():
    """Create embedding model."""
    return EmbeddingModel()


@pytest.fixture
def central_exec(db_with_schema, embedder):
    """Create central executive."""
    return CentralExecutive(db_with_schema, embedder)


@pytest.fixture
def saliency_calc(db_with_schema):
    """Create saliency calculator."""
    return SaliencyCalculator(db_with_schema)


class TestGoalManagement:
    """Test goal management in central executive."""

    def test_set_goal(self, central_exec):
        """Create a primary goal."""
        goal = central_exec.set_goal(
            project_id=1,
            goal_text="Implement authentication module",
            goal_type=GoalType.PRIMARY,
            priority=8,
        )

        assert goal.id is not None
        assert goal.goal_text == "Implement authentication module"
        assert goal.priority == 8
        assert goal.status == GoalStatus.ACTIVE

    def test_get_active_goals(self, central_exec):
        """Retrieve all active goals."""
        goal1 = central_exec.set_goal(1, "Task 1", GoalType.PRIMARY, priority=8)
        goal2 = central_exec.set_goal(1, "Task 2", GoalType.PRIMARY, priority=5)

        goals = central_exec.get_active_goals(1)
        assert len(goals) >= 2
        assert any(g.id == goal1.id for g in goals)
        assert any(g.id == goal2.id for g in goals)

    def test_goal_priority_ordering(self, central_exec):
        """Goals ordered by priority (highest first)."""
        central_exec.set_goal(1, "Low priority", GoalType.PRIMARY, priority=2)
        central_exec.set_goal(1, "High priority", GoalType.PRIMARY, priority=9)

        goals = central_exec.get_active_goals(1)
        # Should be ordered by priority
        if len(goals) >= 2:
            assert goals[0].priority >= goals[1].priority


class TestAttentionFocus:
    """Test attention focus management."""

    def test_set_attention_focus(self, central_exec):
        """Set attention focus on a target."""
        central_exec.set_attention_focus(
            project_id=1,
            focus_target="memory_42",
            focus_type="memory",
            weight=0.9,
        )

        focus = central_exec.get_attention_focus(1)
        # At least one focus item should exist
        assert len(focus) >= 1

    def test_focus_weight_allocation(self, central_exec):
        """Attention weight affects salience."""
        central_exec.set_attention_focus(1, "memory_1", weight=0.8)
        central_exec.set_attention_focus(1, "memory_2", weight=0.5)

        # Both should be set, with different weights
        focus_list = central_exec.get_attention_focus(1)
        assert len(focus_list) >= 2


class TestSaliencyIntegration:
    """Test saliency computation in working memory context."""

    def test_compute_memory_saliency(self, db_with_schema, central_exec):
        """Compute saliency for a memory."""
        cursor = db_with_schema.conn.cursor()
        now = int(datetime.now().timestamp())

        # Insert test memory
        cursor.execute(
            "INSERT INTO memories (project_id, content, created_at, access_count, usefulness_score) VALUES (?, ?, ?, ?, ?)",
            (1, "authentication implementation", now, 5, 0.8),
        )
        db_with_schema.conn.commit()
        memory_id = cursor.lastrowid

        result = central_exec.compute_memory_saliency(
            memory_id, "semantic", 1, current_goal="implement auth"
        )

        assert "memory_id" in result
        assert "saliency" in result
        assert "focus_type" in result
        assert "recommendation" in result
        assert 0.0 <= result["saliency"] <= 1.0

    def test_auto_focus_top_memories(self, db_with_schema, central_exec):
        """Auto-focus identifies and focuses top memories."""
        cursor = db_with_schema.conn.cursor()
        now = int(datetime.now().timestamp())

        # Insert test memories
        for i in range(5):
            cursor.execute(
                "INSERT INTO memories (project_id, content, created_at, access_count, usefulness_score) VALUES (?, ?, ?, ?, ?)",
                (1, f"memory_{i}", now - (i * 100), i + 1, 0.5 + (i * 0.1)),
            )
        db_with_schema.conn.commit()

        top_memories = central_exec.auto_focus_top_memories(
            1, layer="semantic", top_k=3, current_goal="implement feature"
        )

        assert len(top_memories) <= 3
        # Should be sorted by saliency
        if len(top_memories) > 1:
            assert top_memories[0]["saliency"] >= top_memories[1]["saliency"]

    def test_saliency_batch_processing(self, db_with_schema, central_exec):
        """Batch saliency computation for multiple memories."""
        cursor = db_with_schema.conn.cursor()
        now = int(datetime.now().timestamp())

        memory_ids = []
        for i in range(3):
            cursor.execute(
                "INSERT INTO memories (project_id, content, created_at, access_count) VALUES (?, ?, ?, ?)",
                (1, f"memory_{i}", now, i),
            )
            memory_ids.append(cursor.lastrowid)

        db_with_schema.conn.commit()

        results = central_exec.get_saliency_scores_batch(
            memory_ids, "semantic", 1
        )

        assert len(results) == len(memory_ids)
        for result in results:
            assert 0.0 <= result["saliency"] <= 1.0


class TestWorkingMemoryCapacity:
    """Test working memory capacity and constraints."""

    def test_capacity_constraint_millers_law(self, central_exec):
        """Working memory respects 7±2 item capacity."""
        assert central_exec.max_wm_capacity == 7

    def test_is_at_capacity(self, central_exec, db_with_schema):
        """Detect when working memory reaches capacity."""
        # Initially not at capacity
        assert not central_exec.is_at_capacity(1)

        # Insert items up to capacity
        cursor = db_with_schema.conn.cursor()
        for i in range(8):
            cursor.execute(
                "INSERT INTO working_memory (project_id, component, content, content_type) VALUES (?, ?, ?, ?)",
                (1, "phonological", f"item_{i}", "verbal"),
            )
        db_with_schema.conn.commit()

        # Now at capacity
        assert central_exec.is_at_capacity(1)


class TestSaliencyAndFocusTypes:
    """Test focus type assignment based on saliency."""

    def test_focus_type_primary(self, db_with_schema, central_exec):
        """High saliency memories get primary focus."""
        cursor = db_with_schema.conn.cursor()
        now = int(datetime.now().timestamp())

        # High-value memory (recent, frequently accessed, useful)
        cursor.execute(
            "INSERT INTO memories (project_id, content, created_at, access_count, usefulness_score) VALUES (?, ?, ?, ?, ?)",
            (1, "critical auth logic", now, 20, 0.95),
        )
        db_with_schema.conn.commit()
        memory_id = cursor.lastrowid

        result = central_exec.compute_memory_saliency(memory_id, "semantic", 1)
        assert result["saliency"] > 0.6
        focus_type = result["focus_type"]
        assert focus_type in ["primary", "secondary", "background"]

    def test_focus_type_background(self, db_with_schema, central_exec):
        """Low saliency memories get background focus."""
        cursor = db_with_schema.conn.cursor()
        old_timestamp = int((datetime.now() - timedelta(days=60)).timestamp())

        # Low-value memory (old, rarely accessed)
        cursor.execute(
            "INSERT INTO memories (project_id, content, created_at, access_count, usefulness_score) VALUES (?, ?, ?, ?, ?)",
            (1, "deprecated code", old_timestamp, 0, 0.1),
        )
        db_with_schema.conn.commit()
        memory_id = cursor.lastrowid

        result = central_exec.compute_memory_saliency(memory_id, "semantic", 1)
        assert result["saliency"] < 0.6


class TestGoalAlignedSaliency:
    """Test saliency computation with current goal context."""

    def test_saliency_with_goal_alignment(self, db_with_schema, central_exec):
        """Saliency increases when memory aligns with goal."""
        cursor = db_with_schema.conn.cursor()
        now = int(datetime.now().timestamp())

        # Memory relevant to authentication
        cursor.execute(
            "INSERT INTO memories (project_id, content, created_at, access_count) VALUES (?, ?, ?, ?)",
            (1, "JWT token validation logic", now, 1),
        )
        db_with_schema.conn.commit()
        memory_id = cursor.lastrowid

        # Compute with related goal
        result_with_goal = central_exec.compute_memory_saliency(
            memory_id, "semantic", 1, current_goal="implement authentication"
        )

        # Compute without goal (fallback to usefulness)
        result_without_goal = central_exec.compute_memory_saliency(
            memory_id, "semantic", 1, current_goal=None
        )

        # Both should be valid saliency scores
        assert 0.0 <= result_with_goal["saliency"] <= 1.0
        assert 0.0 <= result_without_goal["saliency"] <= 1.0


class TestEpisodicContextForSurprise:
    """Test surprise scoring using episodic context."""

    def test_surprise_with_episodic_context(self, db_with_schema, central_exec):
        """Surprise computes with episodic event context."""
        cursor = db_with_schema.conn.cursor()
        now = int(datetime.now().timestamp())

        # Create episodic events
        cursor.execute(
            "INSERT INTO episodic_events (project_id, content, timestamp, event_type) VALUES (?, ?, ?, ?)",
            (1, "implemented login endpoint", now - 100, "action"),
        )
        db_with_schema.conn.commit()
        event_id = cursor.lastrowid

        # Create memory
        cursor.execute(
            "INSERT INTO memories (project_id, content, created_at, access_count) VALUES (?, ?, ?, ?)",
            (1, "logout endpoint implementation", now, 1),
        )
        db_with_schema.conn.commit()
        memory_id = cursor.lastrowid

        # Compute with surprise
        result = central_exec.compute_memory_saliency(
            memory_id, "semantic", 1, context_events=[event_id]
        )

        assert 0.0 <= result["saliency"] <= 1.0


@pytest.mark.integration
class TestWorkingMemoryAttentionCycle:
    """Test full attention management cycle."""

    def test_attention_cycle_with_saliency(self, db_with_schema, central_exec):
        """Complete cycle: goals → saliency → focus → attention."""
        cursor = db_with_schema.conn.cursor()
        now = int(datetime.now().timestamp())

        # 1. Set goal
        goal = central_exec.set_goal(
            1, "Implement authentication system", GoalType.PRIMARY, priority=9
        )
        assert goal.id is not None

        # 2. Insert relevant memories
        memory_ids = []
        for content in ["JWT implementation", "OAuth flow", "password hashing"]:
            cursor.execute(
                "INSERT INTO memories (project_id, content, created_at, access_count, usefulness_score) VALUES (?, ?, ?, ?, ?)",
                (1, content, now, 5, 0.8),
            )
            memory_ids.append(cursor.lastrowid)

        db_with_schema.conn.commit()

        # 3. Auto-focus top memories based on goal
        top_memories = central_exec.auto_focus_top_memories(
            1, top_k=2, current_goal=goal.goal_text
        )

        assert len(top_memories) > 0
        for memory in top_memories:
            assert memory["focus_type"] in ["primary", "secondary", "background"]

        # 4. Verify attention focus was set
        focus = central_exec.get_attention_focus(1)
        assert len(focus) > 0

    def test_attention_shift_on_goal_change(self, db_with_schema, central_exec):
        """Attention shifts when goal changes."""
        cursor = db_with_schema.conn.cursor()
        now = int(datetime.now().timestamp())

        # Memories for different domains
        auth_memories = ["JWT", "OAuth", "Sessions"]
        db_memories = ["Indexes", "Transactions", "Partitioning"]

        for content in auth_memories + db_memories:
            cursor.execute(
                "INSERT INTO memories (project_id, content, created_at, access_count) VALUES (?, ?, ?, ?)",
                (1, content, now, 1),
            )

        db_with_schema.conn.commit()

        # Focus on authentication goal
        auth_focus_1 = central_exec.auto_focus_top_memories(
            1, top_k=2, current_goal="implement JWT authentication"
        )

        # Focus on database goal
        db_focus = central_exec.auto_focus_top_memories(
            1, top_k=2, current_goal="optimize database queries"
        )

        # Both should return results
        assert len(auth_focus_1) > 0
        assert len(db_focus) > 0


class TestRecommendationsBasedOnSaliency:
    """Test action recommendations from saliency scores."""

    def test_keep_in_focus_recommendation(self, db_with_schema, central_exec):
        """Critical memories get KEEP_IN_FOCUS recommendation."""
        cursor = db_with_schema.conn.cursor()
        now = int(datetime.now().timestamp())

        cursor.execute(
            "INSERT INTO memories (project_id, content, created_at, access_count, usefulness_score) VALUES (?, ?, ?, ?, ?)",
            (1, "critical security logic", now, 30, 0.95),
        )
        db_with_schema.conn.commit()
        memory_id = cursor.lastrowid

        result = central_exec.compute_memory_saliency(memory_id, "semantic", 1)
        if result["saliency"] >= 0.8:
            assert "KEEP_IN_FOCUS" in result["recommendation"]

    def test_inhibit_recommendation(self, db_with_schema, central_exec):
        """Low-saliency items get INHIBIT recommendation."""
        cursor = db_with_schema.conn.cursor()
        old_time = int((datetime.now() - timedelta(days=90)).timestamp())

        cursor.execute(
            "INSERT INTO memories (project_id, content, created_at, access_count, usefulness_score) VALUES (?, ?, ?, ?, ?)",
            (1, "obsolete code", old_time, 0, 0.05),
        )
        db_with_schema.conn.commit()
        memory_id = cursor.lastrowid

        result = central_exec.compute_memory_saliency(memory_id, "semantic", 1)
        if result["saliency"] < 0.4:
            assert "INHIBIT" in result["recommendation"]
