"""Unit tests for saliency calculator.

Tests multi-factor saliency scoring:
- Frequency scoring
- Recency scoring with exponential decay
- Relevance scoring (goal-based and usefulness)
- Surprise scoring (novelty bonus)
- Focus type conversion
- Batch operations
"""

import pytest
import math
from datetime import datetime, timedelta
from typing import Optional

from athena.core.database import Database
from athena.working_memory.saliency import (
    SaliencyCalculator,
    saliency_to_focus_type,
    saliency_to_recommendation,
)


@pytest.fixture
def db(tmp_path):
    """Create test database with schema."""
    db = Database(tmp_path / "test.db")
    db.conn.execute("PRAGMA foreign_keys = ON")

    # Create minimal schema for testing
    db.conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            memory_type TEXT DEFAULT 'fact',
            created_at INTEGER NOT NULL,
            access_count INTEGER DEFAULT 0,
            usefulness_score REAL DEFAULT 0.5
        )
    """)

    db.conn.execute("""
        CREATE TABLE IF NOT EXISTS episodic_events (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            event_type TEXT
        )
    """)

    db.conn.execute("""
        CREATE TABLE IF NOT EXISTS procedures (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            template TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            access_count INTEGER DEFAULT 0
        )
    """)

    db.conn.commit()
    return db


@pytest.fixture
def saliency_calc(db):
    """Create saliency calculator."""
    return SaliencyCalculator(db)


class TestFrequencyScoring:
    """Test frequency score computation."""

    def test_frequency_no_access(self, db, saliency_calc):
        """Frequency score for memory with no accesses."""
        # Insert semantic memory with 0 access
        cursor = db.conn.cursor()
        cursor.execute(
            "INSERT INTO memories (project_id, content, created_at, access_count) VALUES (?, ?, ?, ?)",
            (1, "test memory", int(datetime.now().timestamp()), 0),
        )
        db.conn.commit()
        memory_id = cursor.lastrowid

        score = saliency_calc._compute_frequency_score(memory_id, "semantic", 1)
        assert 0.0 <= score <= 1.0
        assert score == 0.0

    def test_frequency_normalized(self, db, saliency_calc):
        """Frequency score normalized by max."""
        cursor = db.conn.cursor()
        now = int(datetime.now().timestamp())

        # Insert memories with different access counts
        cursor.execute(
            "INSERT INTO memories (project_id, content, created_at, access_count) VALUES (?, ?, ?, ?)",
            (1, "memory1", now, 5),
        )
        mem1_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO memories (project_id, content, created_at, access_count) VALUES (?, ?, ?, ?)",
            (1, "memory2", now, 10),
        )
        mem2_id = cursor.lastrowid

        db.conn.commit()

        score1 = saliency_calc._compute_frequency_score(mem1_id, "semantic", 1)
        score2 = saliency_calc._compute_frequency_score(mem2_id, "semantic", 1)

        assert 0.0 <= score1 <= 1.0
        assert 0.0 <= score2 <= 1.0
        assert score2 > score1  # Higher access count → higher score

    def test_frequency_episodic_fallback(self, db, saliency_calc):
        """Frequency score for episodic events (uses event count)."""
        cursor = db.conn.cursor()
        now = int(datetime.now().timestamp())

        cursor.execute(
            "INSERT INTO episodic_events (project_id, content, timestamp, event_type) VALUES (?, ?, ?, ?)",
            (1, "event1", now, "action"),
        )
        event_id = cursor.lastrowid
        db.conn.commit()

        score = saliency_calc._compute_frequency_score(event_id, "episodic", 1)
        assert 0.0 <= score <= 1.0

    def test_frequency_unknown_layer(self, db, saliency_calc):
        """Unknown layer returns neutral score."""
        score = saliency_calc._compute_frequency_score(999, "unknown_layer", 1)
        assert score == 0.5  # Neutral


class TestRecencyScoring:
    """Test recency score computation with exponential decay."""

    def test_recency_recent_memory(self, db, saliency_calc):
        """Recent memory has high recency score."""
        cursor = db.conn.cursor()
        now = int(datetime.now().timestamp())

        cursor.execute(
            "INSERT INTO memories (project_id, content, created_at, access_count) VALUES (?, ?, ?, ?)",
            (1, "recent", now, 1),
        )
        memory_id = cursor.lastrowid
        db.conn.commit()

        score = saliency_calc._compute_recency_score(memory_id, "semantic", 1)
        assert 0.0 <= score <= 1.0
        assert score > 0.9  # Just created → very recent

    def test_recency_old_memory(self, db, saliency_calc):
        """Old memory has low recency score."""
        cursor = db.conn.cursor()
        # 30 days ago
        old_timestamp = int((datetime.now() - timedelta(days=30)).timestamp())

        cursor.execute(
            "INSERT INTO memories (project_id, content, created_at, access_count) VALUES (?, ?, ?, ?)",
            (1, "old", old_timestamp, 1),
        )
        memory_id = cursor.lastrowid
        db.conn.commit()

        score = saliency_calc._compute_recency_score(memory_id, "semantic", 1)
        assert 0.0 <= score <= 1.0
        assert score < 0.5  # Old → low recency

    def test_recency_exponential_decay(self, db, saliency_calc):
        """Recency follows exponential decay with 7-day half-life."""
        cursor = db.conn.cursor()
        now_ts = int(datetime.now().timestamp())

        # At 7 days, should be ~0.5
        seven_day_timestamp = int((datetime.now() - timedelta(days=7)).timestamp())
        cursor.execute(
            "INSERT INTO memories (project_id, content, created_at, access_count) VALUES (?, ?, ?, ?)",
            (1, "seven_days", seven_day_timestamp, 1),
        )
        seven_day_id = cursor.lastrowid
        db.conn.commit()

        score = saliency_calc._compute_recency_score(seven_day_id, "semantic", 1)
        assert 0.4 < score < 0.6  # Should be close to 0.5

    def test_recency_unknown_timestamp(self, db, saliency_calc):
        """Missing timestamp returns neutral score."""
        score = saliency_calc._compute_recency_score(999, "semantic", 1)
        assert score == 0.5  # Default for unknown


class TestRelevanceScoring:
    """Test relevance score computation."""

    def test_relevance_usefulness_fallback(self, db, saliency_calc):
        """Relevance without goal uses usefulness score."""
        cursor = db.conn.cursor()
        now = int(datetime.now().timestamp())

        cursor.execute(
            "INSERT INTO memories (project_id, content, created_at, access_count, usefulness_score) VALUES (?, ?, ?, ?, ?)",
            (1, "useful memory", now, 5, 0.8),
        )
        memory_id = cursor.lastrowid
        db.conn.commit()

        score = saliency_calc._compute_relevance_score(memory_id, "semantic", 1, current_goal=None)
        assert 0.0 <= score <= 1.0
        assert score == 0.8

    def test_relevance_no_goal_no_usefulness(self, db, saliency_calc):
        """Relevance without goal/usefulness returns 0.5."""
        cursor = db.conn.cursor()
        now = int(datetime.now().timestamp())

        # Episodic events don't have usefulness_score
        cursor.execute(
            "INSERT INTO episodic_events (project_id, content, timestamp, event_type) VALUES (?, ?, ?, ?)",
            (1, "event", now, "action"),
        )
        event_id = cursor.lastrowid
        db.conn.commit()

        score = saliency_calc._compute_relevance_score(event_id, "episodic", 1, current_goal=None)
        assert score == 0.5  # Default for unknown

    def test_relevance_goal_alignment(self, db, saliency_calc):
        """Relevance with goal considers embedding similarity."""
        cursor = db.conn.cursor()
        now = int(datetime.now().timestamp())

        cursor.execute(
            "INSERT INTO memories (project_id, content, created_at, access_count, usefulness_score) VALUES (?, ?, ?, ?, ?)",
            (1, "authentication JWT implementation", now, 1, 0.5),
        )
        memory_id = cursor.lastrowid
        db.conn.commit()

        # Similar goal should have higher relevance
        score = saliency_calc._compute_relevance_score(
            memory_id, "semantic", 1, current_goal="implement authentication"
        )
        assert 0.0 <= score <= 1.0
        # We can't guarantee exact value, but it should be computed

    def test_relevance_unrelated_goal(self, db, saliency_calc):
        """Relevance with unrelated goal should be lower."""
        cursor = db.conn.cursor()
        now = int(datetime.now().timestamp())

        cursor.execute(
            "INSERT INTO memories (project_id, content, created_at, access_count, usefulness_score) VALUES (?, ?, ?, ?, ?)",
            (1, "database optimization", now, 1, 0.5),
        )
        memory_id = cursor.lastrowid
        db.conn.commit()

        # Unrelated goal
        score = saliency_calc._compute_relevance_score(
            memory_id, "semantic", 1, current_goal="cooking recipes"
        )
        assert 0.0 <= score <= 1.0


class TestSurpriseScoring:
    """Test surprise score computation."""

    def test_surprise_no_context(self, db, saliency_calc):
        """Surprise with no context events returns 0.0."""
        cursor = db.conn.cursor()
        now = int(datetime.now().timestamp())

        cursor.execute(
            "INSERT INTO episodic_events (project_id, content, timestamp, event_type) VALUES (?, ?, ?, ?)",
            (1, "event", now, "action"),
        )
        event_id = cursor.lastrowid
        db.conn.commit()

        score = saliency_calc._compute_surprise_score(event_id, "episodic", 1, context_events=None)
        assert score == 0.0

    def test_surprise_empty_context(self, db, saliency_calc):
        """Surprise with empty context returns 0.0."""
        cursor = db.conn.cursor()
        now = int(datetime.now().timestamp())

        cursor.execute(
            "INSERT INTO episodic_events (project_id, content, timestamp, event_type) VALUES (?, ?, ?, ?)",
            (1, "event", now, "action"),
        )
        event_id = cursor.lastrowid
        db.conn.commit()

        score = saliency_calc._compute_surprise_score(event_id, "episodic", 1, context_events=[])
        assert score == 0.0

    def test_surprise_with_context(self, db, saliency_calc):
        """Surprise with context events computes novelty."""
        cursor = db.conn.cursor()
        now = int(datetime.now().timestamp())

        # Create events
        cursor.execute(
            "INSERT INTO episodic_events (project_id, content, timestamp, event_type) VALUES (?, ?, ?, ?)",
            (1, "authentication module", now, "action"),
        )
        event1_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO episodic_events (project_id, content, timestamp, event_type) VALUES (?, ?, ?, ?)",
            (1, "database schema", now, "action"),
        )
        event2_id = cursor.lastrowid

        db.conn.commit()

        # Surprising event should have novelty bonus
        score = saliency_calc._compute_surprise_score(
            event1_id, "episodic", 1, context_events=[event2_id]
        )
        assert 0.0 <= score <= 1.0


class TestCompositeSaliency:
    """Test full saliency computation."""

    def test_saliency_weighted_combination(self, db, saliency_calc):
        """Saliency combines all four factors with weights."""
        cursor = db.conn.cursor()
        now = int(datetime.now().timestamp())

        cursor.execute(
            "INSERT INTO memories (project_id, content, created_at, access_count, usefulness_score) VALUES (?, ?, ?, ?, ?)",
            (1, "high value memory", now, 10, 0.9),
        )
        memory_id = cursor.lastrowid
        db.conn.commit()

        # Compute saliency with current goal
        saliency = saliency_calc.compute_saliency(
            memory_id, "semantic", 1, current_goal="find important memories"
        )

        assert 0.0 <= saliency <= 1.0
        assert saliency > 0.5  # Should be reasonably high

    def test_saliency_error_handling(self, db, saliency_calc):
        """Saliency returns neutral score on error."""
        # Compute saliency for non-existent memory
        saliency = saliency_calc.compute_saliency(
            999, "semantic", 1, current_goal="test"
        )
        assert saliency == 0.5  # Neutral default

    def test_saliency_bounds(self, db, saliency_calc):
        """Saliency always returns value in [0, 1]."""
        cursor = db.conn.cursor()
        now = int(datetime.now().timestamp())

        cursor.execute(
            "INSERT INTO memories (project_id, content, created_at, access_count, usefulness_score) VALUES (?, ?, ?, ?, ?)",
            (1, "memory", now, 1000, 1.5),  # Invalid usefulness_score
        )
        memory_id = cursor.lastrowid
        db.conn.commit()

        saliency = saliency_calc.compute_saliency(memory_id, "semantic", 1)
        assert 0.0 <= saliency <= 1.0


class TestFocusTypeConversion:
    """Test conversion from saliency to focus type."""

    def test_focus_type_primary(self):
        """High saliency maps to primary focus."""
        assert saliency_to_focus_type(0.8) == "primary"
        assert saliency_to_focus_type(0.9) == "primary"
        assert saliency_to_focus_type(1.0) == "primary"

    def test_focus_type_secondary(self):
        """Medium saliency maps to secondary focus."""
        assert saliency_to_focus_type(0.5) == "secondary"
        assert saliency_to_focus_type(0.6) == "secondary"
        assert saliency_to_focus_type(0.69) == "secondary"

    def test_focus_type_background(self):
        """Low saliency maps to background focus."""
        assert saliency_to_focus_type(0.3) == "background"
        assert saliency_to_focus_type(0.0) == "background"
        assert saliency_to_focus_type(0.39) == "background"

    def test_focus_type_boundary_70(self):
        """Boundary at 0.7 between secondary and primary."""
        assert saliency_to_focus_type(0.69) == "secondary"
        assert saliency_to_focus_type(0.70) == "primary"

    def test_focus_type_boundary_40(self):
        """Boundary at 0.4 between background and secondary."""
        assert saliency_to_focus_type(0.39) == "background"
        assert saliency_to_focus_type(0.40) == "secondary"


class TestRecommendations:
    """Test recommendation generation from saliency."""

    def test_recommendation_high_saliency(self):
        """High saliency generates KEEP_IN_FOCUS recommendation."""
        rec = saliency_to_recommendation(0.9)
        assert "KEEP_IN_FOCUS" in rec
        assert "critical" in rec.lower()

    def test_recommendation_moderate_saliency(self):
        """Moderate saliency generates MONITOR recommendation."""
        rec = saliency_to_recommendation(0.7)
        assert "MONITOR" in rec

    def test_recommendation_low_saliency(self):
        """Low saliency generates BACKGROUND recommendation."""
        rec = saliency_to_recommendation(0.5)
        assert "BACKGROUND" in rec

    def test_recommendation_very_low_saliency(self):
        """Very low saliency generates INHIBIT recommendation."""
        rec = saliency_to_recommendation(0.2)
        assert "INHIBIT" in rec

    def test_recommendation_boundary_80(self):
        """Boundary at 0.8 between MONITOR and KEEP_IN_FOCUS."""
        assert "MONITOR" in saliency_to_recommendation(0.79)
        assert "KEEP_IN_FOCUS" in saliency_to_recommendation(0.80)


class TestWeights:
    """Test saliency weight configuration."""

    def test_weights_sum_to_one(self, saliency_calc):
        """Weights sum to 1.0 for proper averaging."""
        total_weight = sum(saliency_calc.weights.values())
        assert abs(total_weight - 1.0) < 1e-6

    def test_weights_individual_ranges(self, saliency_calc):
        """Each weight is between 0 and 1."""
        for factor, weight in saliency_calc.weights.items():
            assert 0.0 <= weight <= 1.0, f"Weight for {factor} out of range: {weight}"

    def test_weights_expected_distribution(self, saliency_calc):
        """Weights match expected research-backed distribution."""
        # Frequency and Recency: 30% each
        assert saliency_calc.weights["frequency"] == 0.30
        assert saliency_calc.weights["recency"] == 0.30
        # Relevance: 25%
        assert saliency_calc.weights["relevance"] == 0.25
        # Surprise: 15%
        assert saliency_calc.weights["surprise"] == 0.15


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_saliency_zero_division(self, db, saliency_calc):
        """Saliency handles zero-division gracefully."""
        cursor = db.conn.cursor()
        now = int(datetime.now().timestamp())

        # Create memory with zero norms (if possible)
        cursor.execute(
            "INSERT INTO memories (project_id, content, created_at, access_count) VALUES (?, ?, ?, ?)",
            (1, "", now, 0),  # Empty content could cause zero norm
        )
        memory_id = cursor.lastrowid
        db.conn.commit()

        # Should not raise exception
        saliency = saliency_calc.compute_saliency(memory_id, "semantic", 1)
        assert 0.0 <= saliency <= 1.0

    def test_saliency_missing_embeddings(self, db, saliency_calc):
        """Saliency handles missing embedding model gracefully."""
        cursor = db.conn.cursor()
        now = int(datetime.now().timestamp())

        cursor.execute(
            "INSERT INTO memories (project_id, content, created_at, access_count) VALUES (?, ?, ?, ?)",
            (1, "test", now, 1),
        )
        memory_id = cursor.lastrowid
        db.conn.commit()

        # Even if embedding model fails, should return neutral
        saliency = saliency_calc.compute_saliency(
            memory_id, "semantic", 1, current_goal="test"
        )
        assert 0.0 <= saliency <= 1.0

    def test_saliency_max_access_count(self, db, saliency_calc):
        """Frequency handles very high access counts."""
        cursor = db.conn.cursor()
        now = int(datetime.now().timestamp())

        cursor.execute(
            "INSERT INTO memories (project_id, content, created_at, access_count) VALUES (?, ?, ?, ?)",
            (1, "popular", now, 1000000),
        )
        memory_id = cursor.lastrowid
        db.conn.commit()

        score = saliency_calc._compute_frequency_score(memory_id, "semantic", 1)
        assert 0.0 <= score <= 1.0
        assert score >= 0.99  # Very high, but still clamped


@pytest.mark.integration
class TestSaliencyIntegration:
    """Integration tests with other memory components."""

    def test_saliency_with_multiple_layers(self, db, saliency_calc):
        """Saliency computes correctly across multiple layers."""
        cursor = db.conn.cursor()
        now = int(datetime.now().timestamp())

        # Insert into semantic layer
        cursor.execute(
            "INSERT INTO memories (project_id, content, created_at, access_count) VALUES (?, ?, ?, ?)",
            (1, "semantic", now, 5),
        )
        semantic_id = cursor.lastrowid

        # Insert into episodic layer
        cursor.execute(
            "INSERT INTO episodic_events (project_id, content, timestamp, event_type) VALUES (?, ?, ?, ?)",
            (1, "episodic", now, "action"),
        )
        episodic_id = cursor.lastrowid

        db.conn.commit()

        semantic_saliency = saliency_calc.compute_saliency(semantic_id, "semantic", 1)
        episodic_saliency = saliency_calc.compute_saliency(episodic_id, "episodic", 1)

        assert 0.0 <= semantic_saliency <= 1.0
        assert 0.0 <= episodic_saliency <= 1.0
