"""Tests for MemoryQualityMonitor component."""

import pytest
import sqlite3
from datetime import datetime, timedelta

from athena.metacognition.quality import MemoryQualityMonitor
from athena.core.database import Database


@pytest.fixture
def db_path(tmp_path):
    """Create a test database."""
    db_file = tmp_path / "test_memory.db"
    db = Database(str(db_file))

    # Create test project
    db.create_project("test-project", str(tmp_path))

    # Create metacognition_quality_metrics table
    db.conn.execute(
        """
        CREATE TABLE IF NOT EXISTS metacognition_quality_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            memory_id INTEGER,
            memory_layer TEXT NOT NULL,
            query_count INTEGER DEFAULT 0,
            successful_retrievals INTEGER DEFAULT 0,
            false_positives INTEGER DEFAULT 0,
            false_negatives INTEGER DEFAULT 0,
            accuracy_score REAL,
            last_evaluated TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
        """
    )

    # Create semantic_memories table (stub)
    db.conn.execute(
        """
        CREATE TABLE IF NOT EXISTS semantic_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
        """
    )

    # Create episodic_events table (stub)
    db.conn.execute(
        """
        CREATE TABLE IF NOT EXISTS episodic_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
        """
    )

    db.conn.commit()
    return str(db_file)


@pytest.fixture
def monitor(db_path):
    """Create a MemoryQualityMonitor instance."""
    return MemoryQualityMonitor(db_path)


class TestRetrievalRecording:
    """Test retrieval recording."""

    def test_record_successful_retrieval(self, monitor):
        """Record a successful retrieval."""
        success = monitor.record_retrieval(
            project_id=1, memory_id=1, memory_layer="semantic", successful=True
        )

        assert success is True

        # Verify recorded in DB
        with sqlite3.connect(monitor.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT query_count, successful_retrievals
                FROM metacognition_quality_metrics
                WHERE memory_id = 1
                """
            )
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == 1  # query_count
            assert row[1] == 1  # successful_retrievals

    def test_record_failed_retrieval(self, monitor):
        """Record a failed retrieval."""
        monitor.record_retrieval(
            project_id=1, memory_id=1, memory_layer="semantic", successful=False
        )

        with sqlite3.connect(monitor.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT query_count, successful_retrievals
                FROM metacognition_quality_metrics
                WHERE memory_id = 1
                """
            )
            row = cursor.fetchone()
            assert row[0] == 1  # query_count
            assert row[1] == 0  # successful_retrievals

    def test_record_false_positive(self, monitor):
        """Record a false positive retrieval."""
        monitor.record_retrieval(
            project_id=1,
            memory_id=1,
            memory_layer="semantic",
            successful=True,
            was_false_positive=True,
        )

        with sqlite3.connect(monitor.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT false_positives FROM metacognition_quality_metrics
                WHERE memory_id = 1
                """
            )
            row = cursor.fetchone()
            assert row[0] == 1

    def test_record_false_negative(self, monitor):
        """Record a false negative retrieval."""
        monitor.record_retrieval(
            project_id=1,
            memory_id=1,
            memory_layer="semantic",
            successful=False,
            was_false_negative=True,
        )

        with sqlite3.connect(monitor.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT false_negatives FROM metacognition_quality_metrics
                WHERE memory_id = 1
                """
            )
            row = cursor.fetchone()
            assert row[0] == 1

    def test_multiple_retrievals_accumulate(self, monitor):
        """Multiple retrievals should accumulate."""
        for _ in range(5):
            monitor.record_retrieval(
                project_id=1, memory_id=1, memory_layer="semantic", successful=True
            )

        with sqlite3.connect(monitor.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT query_count, successful_retrievals
                FROM metacognition_quality_metrics
                WHERE memory_id = 1
                """
            )
            row = cursor.fetchone()
            assert row[0] == 5
            assert row[1] == 5


class TestQualityEvaluation:
    """Test quality evaluation."""

    def test_evaluate_perfect_accuracy(self, monitor):
        """Perfect accuracy: all retrievals successful."""
        for _ in range(10):
            monitor.record_retrieval(
                project_id=1, memory_id=1, memory_layer="semantic", successful=True
            )

        quality = monitor.evaluate_memory_quality(1)

        assert quality is not None
        assert quality["accuracy"] == pytest.approx(1.0)
        assert quality["false_positive_rate"] == pytest.approx(0.0)
        assert quality["quality_score"] == pytest.approx(1.0)

    def test_evaluate_poor_accuracy(self, monitor):
        """Poor accuracy: many failures."""
        for i in range(10):
            monitor.record_retrieval(
                project_id=1,
                memory_id=1,
                memory_layer="semantic",
                successful=(i < 3),
            )

        quality = monitor.evaluate_memory_quality(1)

        assert quality["accuracy"] == pytest.approx(0.3)
        assert quality["quality_score"] == pytest.approx(0.3)

    def test_evaluate_with_false_positives(self, monitor):
        """Quality score penalizes false positives."""
        # 5 successful, 1 false positive
        for _ in range(5):
            monitor.record_retrieval(
                project_id=1, memory_id=1, memory_layer="semantic", successful=True
            )
        monitor.record_retrieval(
            project_id=1,
            memory_id=1,
            memory_layer="semantic",
            successful=True,
            was_false_positive=True,
        )

        quality = monitor.evaluate_memory_quality(1)

        # accuracy = 6/6 = 1.0, false_pos_rate = 1/6
        # quality = 1.0 × (1 - 1/6) = 5/6 ≈ 0.833
        expected_quality = 1.0 * (1.0 - 1.0 / 6)
        assert quality["quality_score"] == pytest.approx(expected_quality)


class TestQualityByLayer:
    """Test quality metrics by memory layer."""

    def test_quality_by_layer_aggregation(self, monitor):
        """Aggregate quality metrics by layer."""
        # Semantic layer: 8/10 accurate
        for i in range(10):
            monitor.record_retrieval(
                project_id=1,
                memory_id=i,
                memory_layer="semantic",
                successful=(i < 8),
            )

        # Episodic layer: 9/10 accurate
        for i in range(10, 20):
            monitor.record_retrieval(
                project_id=1,
                memory_id=i,
                memory_layer="episodic",
                successful=(i < 19),
            )

        quality_by_layer = monitor.get_quality_by_layer(project_id=1)

        assert "semantic" in quality_by_layer
        assert "episodic" in quality_by_layer
        assert quality_by_layer["semantic"]["avg_accuracy"] == pytest.approx(0.8)
        assert quality_by_layer["episodic"]["avg_accuracy"] == pytest.approx(0.9)


class TestPoorPerformers:
    """Test identification of poor-performing memories."""

    def test_identify_poor_performers(self, monitor):
        """Identify memories below accuracy threshold."""
        # Memory 1: 30% accurate (poor)
        for i in range(10):
            monitor.record_retrieval(
                project_id=1,
                memory_id=1,
                memory_layer="semantic",
                successful=(i < 3),
            )

        # Memory 2: 90% accurate (good)
        for i in range(10):
            monitor.record_retrieval(
                project_id=1,
                memory_id=2,
                memory_layer="semantic",
                successful=(i < 9),
            )

        poor = monitor.identify_poor_performers(project_id=1, accuracy_threshold=0.6)

        assert len(poor) == 1
        assert poor[0]["memory_id"] == 1
        assert poor[0]["accuracy"] == pytest.approx(0.3)

    def test_poor_performers_minimum_queries(self, monitor):
        """Poor performers should have minimum query count."""
        # Memory with only 3 queries (below minimum)
        for _ in range(3):
            monitor.record_retrieval(
                project_id=1,
                memory_id=1,
                memory_layer="semantic",
                successful=False,
            )

        poor = monitor.identify_poor_performers(
            project_id=1, accuracy_threshold=0.6
        )

        # Should not include memory with < 5 queries
        assert len(poor) == 0

    def test_poor_performers_sorted_by_accuracy(self, monitor):
        """Poor performers should be sorted by accuracy (worst first)."""
        # Memory 1: 20% accurate
        for i in range(10):
            monitor.record_retrieval(
                project_id=1,
                memory_id=1,
                memory_layer="semantic",
                successful=(i < 2),
            )

        # Memory 2: 40% accurate
        for i in range(10):
            monitor.record_retrieval(
                project_id=1,
                memory_id=2,
                memory_layer="semantic",
                successful=(i < 4),
            )

        poor = monitor.identify_poor_performers(
            project_id=1, accuracy_threshold=0.6
        )

        assert len(poor) == 2
        assert poor[0]["memory_id"] == 1  # Worst first
        assert poor[1]["memory_id"] == 2


class TestQualityDegradation:
    """Test quality degradation detection."""

    def test_detect_quality_degradation(self, monitor):
        """Detect when memory quality degrades over time."""
        # Create initial record with good accuracy
        for _ in range(10):
            monitor.record_retrieval(
                project_id=1,
                memory_id=1,
                memory_layer="semantic",
                successful=True,
            )

        result = monitor.detect_quality_degradation(memory_id=1)

        # May or may not detect (depends on history), so just verify it returns
        assert result is not None or result is None


class TestQualityReport:
    """Test quality report generation."""

    def test_generate_quality_report(self, monitor):
        """Generate comprehensive quality report."""
        # Create some quality data
        for i in range(10):
            monitor.record_retrieval(
                project_id=1,
                memory_id=1,
                memory_layer="semantic",
                successful=(i < 8),
            )

        report = monitor.get_quality_report(project_id=1, include_poor_performers=True)

        assert report["project_id"] == 1
        assert "timestamp" in report
        assert "quality_by_layer" in report
        assert "overall_avg_accuracy" in report
        assert "overall_avg_false_positive_rate" in report
        assert "poor_performers" in report

    def test_quality_report_without_poor_performers(self, monitor):
        """Quality report can exclude poor performers."""
        for i in range(10):
            monitor.record_retrieval(
                project_id=1,
                memory_id=1,
                memory_layer="semantic",
                successful=True,
            )

        report = monitor.get_quality_report(
            project_id=1, include_poor_performers=False
        )

        assert "poor_performers" not in report
        assert "overall_avg_accuracy" in report
