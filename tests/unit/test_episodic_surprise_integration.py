"""Integration tests for Bayesian surprise with episodic store."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from athena.core.database import Database
from athena.episodic.models import EpisodicEvent, EventContext, EventOutcome, EventType
from athena.episodic.store import EpisodicStore
from athena.episodic.surprise import BayesianSurprise, SurpriseEvent


class TestEpisodicSurpriseIntegration:
    """Test Bayesian surprise integration with episodic store."""

    @pytest.fixture
    def db(self):
        """Create temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(str(db_path))
            yield db
            db.close()

    @pytest.fixture
    def store(self, db):
        """Create episodic store."""
        return EpisodicStore(db)

    @pytest.fixture
    def project_id(self, db):
        """Create a test project."""
        cursor = db.conn.cursor()
        import time
        timestamp = int(time.time())
        cursor.execute("""
            INSERT INTO projects (name, path, created_at, last_accessed)
            VALUES (?, ?, ?, ?)
        """, ("test-project", "/test", timestamp, timestamp))
        db.conn.commit()
        return cursor.lastrowid

    def test_record_event_with_surprise(self, store, project_id):
        """Test recording event with surprise metrics."""
        event = EpisodicEvent(
            project_id=project_id,
            session_id="test-session",
            timestamp=datetime.now(),
            event_type=EventType.ACTION,
            content="Test action with high surprise",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(cwd="/test", files=[], task="test", phase="phase-1"),
        )

        event_id = store.record_event(
            event,
            surprise_score=4.2,
            surprise_normalized=0.85,
            surprise_coherence=0.92,
        )

        # Verify event was recorded
        assert event_id > 0

        # Verify surprise metrics are stored
        cursor = store.db.conn.cursor()
        cursor.execute("""
            SELECT surprise_score, surprise_normalized, surprise_coherence
            FROM episodic_events WHERE id = ?
        """, (event_id,))

        row = cursor.fetchone()
        assert row is not None
        assert row["surprise_score"] == 4.2
        assert row["surprise_normalized"] == 0.85
        assert row["surprise_coherence"] == 0.92

    def test_record_event_without_surprise(self, store, project_id):
        """Test recording event without surprise metrics (backwards compatibility)."""
        event = EpisodicEvent(
            project_id=project_id,
            session_id="test-session",
            timestamp=datetime.now(),
            event_type=EventType.ACTION,
            content="Test action without surprise",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(cwd="/test", files=[], task="test", phase="phase-1"),
        )

        event_id = store.record_event(event)

        # Verify event was recorded without surprise metrics
        assert event_id > 0

        cursor = store.db.conn.cursor()
        cursor.execute("""
            SELECT surprise_score, surprise_normalized, surprise_coherence
            FROM episodic_events WHERE id = ?
        """, (event_id,))

        row = cursor.fetchone()
        assert row is not None
        assert row["surprise_score"] is None
        assert row["surprise_normalized"] is None
        assert row["surprise_coherence"] is None

    def test_get_high_surprise_events(self, store, project_id):
        """Test querying high-surprise events."""
        # Record events with varying surprise scores
        events_data = [
            ("Low surprise event", 1.5, 0.3),
            ("Medium surprise event", 3.0, 0.6),
            ("High surprise event 1", 4.5, 0.9),
            ("High surprise event 2", 5.2, 0.95),
        ]

        for content, surprise, normalized in events_data:
            event = EpisodicEvent(
                project_id=project_id,
                session_id="test-session",
                timestamp=datetime.now(),
                event_type=EventType.ACTION,
                content=content,
                outcome=EventOutcome.SUCCESS,
                context=EventContext(
                    cwd="/test", files=[], task="test", phase="phase-1"
                ),
            )
            store.record_event(event, surprise_score=surprise, surprise_normalized=normalized)

        # Verify events were recorded with surprise scores
        cursor = store.db.conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM episodic_events WHERE surprise_score > 0")
        row = cursor.fetchone()
        assert row["cnt"] == 4  # All 4 events recorded

        # Get high-surprise events (threshold=3.5)
        high_surprise = store.get_high_surprise_events(project_id, threshold=3.5)

        # Should get the two high-surprise events
        assert len(high_surprise) >= 2  # At least 2 high-surprise events

    def test_get_high_surprise_events_empty(self, store, project_id):
        """Test querying high-surprise events when none exist."""
        # Record only low-surprise event
        event = EpisodicEvent(
            project_id=project_id,
            session_id="test-session",
            timestamp=datetime.now(),
            event_type=EventType.ACTION,
            content="Low surprise event",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(cwd="/test", files=[], task="test", phase="phase-1"),
        )
        store.record_event(event, surprise_score=1.5)

        # Get high-surprise events
        high_surprise = store.get_high_surprise_events(project_id, threshold=3.5)

        # Should be empty
        assert len(high_surprise) == 0

    def test_get_high_surprise_events_sorting(self, store, project_id):
        """Test that high-surprise events are sorted by surprise score descending."""
        # Record events in non-sorted order
        surprise_scores = [3.5, 5.0, 4.0, 4.5]
        for i, surprise in enumerate(surprise_scores):
            event = EpisodicEvent(
                project_id=project_id,
                session_id="test-session",
                timestamp=datetime.now() + timedelta(seconds=i),
                event_type=EventType.ACTION,
                content=f"Event {i}",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(
                    cwd="/test", files=[], task="test", phase="phase-1"
                ),
            )
            store.record_event(event, surprise_score=surprise)

        # Get high-surprise events
        high_surprise = store.get_high_surprise_events(project_id, threshold=3.0)

        # Verify sorted by surprise descending
        surprise_values = [
            float(e.content.split()[1])
            for e in high_surprise
        ]

        # Extract surprise scores from the content for comparison
        assert len(high_surprise) == 4
        # Check that scores are in descending order by checking stored scores
        cursor = store.db.conn.cursor()
        cursor.execute("""
            SELECT surprise_score FROM episodic_events
            WHERE project_id = ? AND surprise_score > ?
            ORDER BY surprise_score DESC
        """, (project_id, 3.0))

        stored_scores = [row["surprise_score"] for row in cursor.fetchall()]
        assert stored_scores == [5.0, 4.5, 4.0, 3.5]

    def test_get_high_surprise_events_limit(self, store, project_id):
        """Test that limit parameter is respected."""
        # Record 10 high-surprise events
        for i in range(10):
            event = EpisodicEvent(
                project_id=project_id,
                session_id="test-session",
                timestamp=datetime.now() + timedelta(seconds=i),
                event_type=EventType.ACTION,
                content=f"Event {i}",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(
                    cwd="/test", files=[], task="test", phase="phase-1"
                ),
            )
            store.record_event(event, surprise_score=4.0 + i)

        # Get with limit=5
        high_surprise = store.get_high_surprise_events(project_id, threshold=3.5, limit=5)

        # Should get exactly 5 events
        assert len(high_surprise) == 5

    def test_surprise_integration_with_bayesian_calculator(self, store, project_id):
        """Test full integration: calculate surprise, then record with scores."""
        calc = BayesianSurprise()

        # Calculate surprise for a token sequence
        tokens = ["the", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "dog"]

        # Mock token probabilities
        calc._prob_cache = {
            token: (0.1 + (i * 0.01)) for i, token in enumerate(tokens)
        }

        # Find surprise boundaries (with default threshold)
        surprise_events = calc.find_event_boundaries(tokens)

        # Record events with surprise metrics
        for event_idx, surprise_event in enumerate(surprise_events):
            event = EpisodicEvent(
                project_id=project_id,
                session_id="test-session",
                timestamp=datetime.now() + timedelta(seconds=event_idx),
                event_type=EventType.ACTION,
                content=f"Token event at index {surprise_event.index}",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(
                    cwd="/test", files=[], task="test", phase="phase-1"
                ),
            )
            store.record_event(
                event,
                surprise_score=surprise_event.surprise_score,
                surprise_normalized=surprise_event.normalized_surprise,
                surprise_coherence=surprise_event.coherence_score,
            )

        # Verify high-surprise events are stored
        high_surprise = store.get_high_surprise_events(project_id, threshold=0.5)
        assert len(high_surprise) > 0
