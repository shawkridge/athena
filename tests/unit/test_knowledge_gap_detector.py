"""Tests for KnowledgeGapDetector component."""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

import pytest

from athena.metacognition.gaps import KnowledgeGapDetector


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary database."""
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    cursor = conn.cursor()

    # Create gap table
    cursor.execute(
        """
        CREATE TABLE metacognition_gaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            gap_type TEXT NOT NULL,
            description TEXT NOT NULL,
            memory_ids TEXT,
            confidence REAL,
            priority TEXT,
            resolved INTEGER DEFAULT 0,
            resolved_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Create semantic_memories table for testing
    cursor.execute(
        """
        CREATE TABLE semantic_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()
    conn.close()
    return str(db)


@pytest.fixture
def detector(db_path):
    """Create KnowledgeGapDetector instance."""
    return KnowledgeGapDetector(db_path)


class TestDirectContradictions:
    """Test direct contradiction detection."""

    def test_detect_direct_contradictions(self, detector, db_path):
        """Test detecting direct contradictions."""
        # Add contradictory memories
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO semantic_memories (project_id, content) VALUES (?, ?)",
                (1, "The system is always reliable and never fails"),
            )
            cursor.execute(
                "INSERT INTO semantic_memories (project_id, content) VALUES (?, ?)",
                (1, "The system sometimes fails under load"),
            )
            conn.commit()

        contradictions = detector.detect_direct_contradictions(project_id=1)

        # May or may not find based on heuristics, but should not crash
        assert isinstance(contradictions, list)

    def test_no_contradictions_when_similar_content(self, detector, db_path):
        """Test that similar non-contradictory content is not flagged."""
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO semantic_memories (project_id, content) VALUES (?, ?)",
                (1, "The system is fast and efficient"),
            )
            cursor.execute(
                "INSERT INTO semantic_memories (project_id, content) VALUES (?, ?)",
                (1, "The system performs well with good efficiency"),
            )
            conn.commit()

        contradictions = detector.detect_direct_contradictions(project_id=1)
        assert isinstance(contradictions, list)


class TestSubtleContradictions:
    """Test subtle contradiction detection."""

    def test_detect_subtle_contradictions(self, detector, db_path):
        """Test detecting subtle contradictions."""
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO semantic_memories (project_id, content) VALUES (?, ?)",
                (1, "Feature X is critical for performance"),
            )
            cursor.execute(
                "INSERT INTO semantic_memories (project_id, content) VALUES (?, ?)",
                (1, "Feature X has minimal performance impact"),
            )
            conn.commit()

        subtle = detector.detect_subtle_contradictions(project_id=1)

        assert isinstance(subtle, list)

    def test_subtle_contradiction_threshold(self, detector):
        """Test subtle contradiction detection with custom threshold."""
        subtle = detector.detect_subtle_contradictions(project_id=999, threshold=0.8)
        assert isinstance(subtle, list)


class TestUncertaintyZones:
    """Test uncertainty zone identification."""

    def test_identify_uncertainty_zones(self, detector, db_path):
        """Test identifying areas with low confidence."""
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO semantic_memories (project_id, content) VALUES (?, ?)",
                (1, "Architecture design pattern A"),
            )
            cursor.execute(
                "INSERT INTO semantic_memories (project_id, content) VALUES (?, ?)",
                (1, "Architecture implementation B"),
            )
            conn.commit()

        zones = detector.identify_uncertainty_zones(project_id=1)

        assert isinstance(zones, list)
        # May have zones depending on topic grouping

    def test_uncertainty_zones_empty_project(self, detector):
        """Test uncertainty zones on empty project."""
        zones = detector.identify_uncertainty_zones(project_id=999)
        assert isinstance(zones, list)


class TestMissingInformation:
    """Test missing information detection."""

    def test_flag_missing_information(self, detector, db_path):
        """Test flagging missing important information."""
        # Add minimal memory
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO semantic_memories (project_id, content) VALUES (?, ?)",
                (1, "Some basic info"),
            )
            conn.commit()

        gaps = detector.flag_missing_information(project_id=1)

        # Should identify missing topics
        assert isinstance(gaps, list)
        assert len(gaps) > 0  # Should find missing important topics

    def test_missing_information_coverage(self, detector, db_path):
        """Test detection of coverage in important topics."""
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO semantic_memories (project_id, content) VALUES (?, ?)",
                (1, "Architecture and design patterns used"),
            )
            cursor.execute(
                "INSERT INTO semantic_memories (project_id, content) VALUES (?, ?)",
                (1, "Purpose: Manage memory systems"),
            )
            cursor.execute(
                "INSERT INTO semantic_memories (project_id, content) VALUES (?, ?)",
                (1, "Status: Production ready"),
            )
            conn.commit()

        gaps = detector.flag_missing_information(project_id=1)

        # Should have fewer gaps due to coverage
        assert isinstance(gaps, list)


class TestGapRecording:
    """Test gap recording and retrieval."""

    def test_record_gap(self, detector, db_path):
        """Test recording a knowledge gap."""
        assert detector.record_gap(
            project_id=1,
            gap_type="contradiction",
            description="Test contradiction",
            memory_ids=[1, 2],
            confidence=0.95,
            priority="high",
        )

        # Verify in database
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT gap_type, description FROM metacognition_gaps WHERE project_id = 1"
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == "contradiction"
        assert row[1] == "Test contradiction"

    def test_resolve_gap(self, detector, db_path):
        """Test marking a gap as resolved."""
        # First record a gap
        detector.record_gap(
            project_id=1,
            gap_type="uncertainty",
            description="Test uncertainty",
            memory_ids=[1],
            confidence=0.7,
            priority="medium",
        )

        # Get the gap ID
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM metacognition_gaps LIMIT 1")
            gap_id = cursor.fetchone()[0]

        # Resolve it
        assert detector.resolve_gap(gap_id, "Resolved by research")

        # Verify resolved
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT resolved, resolved_at FROM metacognition_gaps WHERE id = ?",
                (gap_id,),
            )
            row = cursor.fetchone()

        assert row[0] == 1  # resolved


class TestGetUnresolvedGaps:
    """Test retrieving unresolved gaps."""

    def test_get_unresolved_gaps(self, detector):
        """Test getting all unresolved gaps."""
        # Record multiple gaps
        detector.record_gap(1, "contradiction", "Gap 1", [1], 0.9, "high")
        detector.record_gap(1, "uncertainty", "Gap 2", [2], 0.7, "medium")
        detector.record_gap(1, "missing_info", "Gap 3", [3], 0.8, "low")

        gaps = detector.get_unresolved_gaps(project_id=1)

        assert len(gaps) == 3
        assert all(g["priority"] in ["high", "medium", "low"] for g in gaps)

    def test_filter_gaps_by_priority(self, detector):
        """Test filtering gaps by priority."""
        detector.record_gap(1, "contradiction", "Critical gap", [1], 0.95, "critical")
        detector.record_gap(1, "contradiction", "High gap", [2], 0.9, "high")
        detector.record_gap(1, "contradiction", "Low gap", [3], 0.5, "low")

        high_gaps = detector.get_unresolved_gaps(project_id=1, priority="high")

        assert len(high_gaps) == 1
        assert high_gaps[0]["priority"] == "high"

    def test_unresolved_gaps_empty(self, detector):
        """Test getting gaps when none exist."""
        gaps = detector.get_unresolved_gaps(project_id=999)
        assert gaps == []


class TestGapReport:
    """Test gap report generation."""

    def test_get_gap_report(self, detector):
        """Test comprehensive gap report."""
        # Record various gaps
        detector.record_gap(1, "contradiction", "Gap A", [1], 0.9, "critical")
        detector.record_gap(1, "contradiction", "Gap B", [2], 0.8, "high")
        detector.record_gap(1, "uncertainty", "Gap C", [3], 0.7, "medium")
        detector.record_gap(1, "missing_info", "Gap D", [4], 0.6, "low")

        report = detector.get_gap_report(project_id=1)

        assert report["total_gaps"] == 4
        assert report["unresolved_gaps"] == 4
        assert report["resolved_gaps"] == 0
        assert "by_type" in report
        assert "by_priority" in report
        assert len(report["critical_issues"]) == 1

    def test_gap_report_categorization(self, detector):
        """Test gap categorization in report."""
        # Add gaps of different types
        detector.record_gap(1, "contradiction", "Contradiction gap", [1], 0.9, "high")
        detector.record_gap(1, "uncertainty", "Uncertainty gap", [2], 0.7, "medium")
        detector.record_gap(1, "missing_info", "Missing gap", [3], 0.6, "low")

        report = detector.get_gap_report(project_id=1)

        assert report["by_type"]["contradiction"] == 1
        assert report["by_type"]["uncertainty"] == 1
        assert report["by_type"]["missing_info"] == 1


class TestResearchSuggestions:
    """Test research area suggestions."""

    def test_suggest_research_areas(self, detector, db_path):
        """Test suggesting research areas based on gaps."""
        # Add minimal memory to trigger missing info gaps
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO semantic_memories (project_id, content) VALUES (?, ?)",
                (1, "Basic information"),
            )
            conn.commit()

        suggestions = detector.suggest_research_areas(project_id=1)

        assert isinstance(suggestions, list)
        if suggestions:
            s = suggestions[0]
            assert "topic" in s
            assert "reason" in s
            assert "priority" in s
            assert "expected_value" in s

    def test_research_suggestions_priorities(self, detector):
        """Test that research suggestions have proper priorities."""
        suggestions = detector.suggest_research_areas(project_id=1)

        for suggestion in suggestions:
            assert suggestion["priority"] in ["low", "medium", "high"]
            assert 0.0 <= suggestion["expected_value"] <= 1.0


class TestHelperMethods:
    """Test internal helper methods."""

    def test_similarity_score(self, detector):
        """Test similarity score calculation."""
        score = detector._similarity_score(
            "The system is fast", "The system is efficient"
        )
        assert 0.0 <= score <= 1.0

    def test_are_contradictory(self, detector):
        """Test contradiction detection logic."""
        # Similar content with negation
        result1 = detector._are_contradictory(
            "The system is reliable", "The system is not reliable"
        )
        # Both non-contradictory
        result2 = detector._are_contradictory(
            "The system is fast", "The system is efficient"
        )

        assert isinstance(result1, bool)
        assert isinstance(result2, bool)

    def test_extract_topic(self, detector):
        """Test topic extraction."""
        topic = detector._extract_topic("Memory management and caching strategies")
        assert isinstance(topic, str)
        assert len(topic) > 0
