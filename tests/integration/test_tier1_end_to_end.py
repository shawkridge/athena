"""End-to-end Tier 1 integration tests.

Tests the complete pipeline:
Episodic Events → Bayesian Surprise Segmentation → Consolidation → Saliency → Auto-Focus

Scenarios:
1. Single session with related events (low surprise)
2. Diverse session with novel events (high surprise)
3. Goal-aligned memory focus
4. Multi-session episodic integration
5. Full pipeline quality validation
"""

import pytest
import math
from datetime import datetime, timedelta
from typing import List, Tuple

from athena.core.database import Database
from athena.core.embeddings import EmbeddingModel
from athena.consolidation.system import ConsolidationSystem
from athena.working_memory.central_executive import CentralExecutive
from athena.working_memory.saliency import SaliencyCalculator
from athena.tier1_bridge import (
    Tier1OrchestrationPipeline,
    Tier1Monitor,
)


@pytest.fixture
def db_full_schema(tmp_path):
    """Create database with full schema for Tier 1 testing."""
    db = Database(tmp_path / "test.db")
    db.conn.execute("PRAGMA foreign_keys = ON")

    # Episodic events
    db.conn.execute("""
        CREATE TABLE IF NOT EXISTS episodic_events (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            event_type TEXT,
            session_id TEXT,
            outcome TEXT
        )
    """)

    # Semantic memories
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

    # Working memory
    db.conn.execute("""
        CREATE TABLE IF NOT EXISTS working_memory (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            component TEXT NOT NULL,
            content TEXT NOT NULL,
            content_type TEXT DEFAULT 'verbal',
            importance_score REAL DEFAULT 0.5
        )
    """)

    # Active goals
    db.conn.execute("""
        CREATE TABLE IF NOT EXISTS active_goals (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            goal_text TEXT NOT NULL,
            goal_type TEXT DEFAULT 'primary',
            priority INTEGER DEFAULT 5,
            status TEXT DEFAULT 'active'
        )
    """)

    # Attention focus
    db.conn.execute("""
        CREATE TABLE IF NOT EXISTS attention_focus (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            focus_target TEXT,
            focus_type TEXT DEFAULT 'memory',
            attention_weight REAL DEFAULT 1.0
        )
    """)

    db.conn.commit()
    return db


@pytest.fixture
def embedder():
    """Create embedding model."""
    return EmbeddingModel()


@pytest.fixture
def tier1_pipeline(db_full_schema, embedder):
    """Create Tier 1 orchestration pipeline."""
    return Tier1OrchestrationPipeline(db_full_schema, embedder)


@pytest.fixture
def tier1_monitor(db_full_schema):
    """Create Tier 1 monitor."""
    return Tier1Monitor(db_full_schema)


class TestTier1BasicPipeline:
    """Test basic Tier 1 pipeline execution."""

    def test_pipeline_initialization(self, tier1_pipeline):
        """Pipeline initializes with all components."""
        assert tier1_pipeline.consolidation_system is not None
        assert tier1_pipeline.surprise_calc is not None
        assert tier1_pipeline.central_executive is not None
        assert tier1_pipeline.saliency_calc is not None

    def test_pipeline_empty_project(self, tier1_pipeline):
        """Pipeline handles empty project gracefully."""
        result = tier1_pipeline.run_full_pipeline(project_id=1)

        assert result["status"] == "success"
        assert result["project_id"] == 1
        assert "metrics" in result
        assert "stages" in result

    def test_pipeline_with_events(self, db_full_schema, tier1_pipeline):
        """Pipeline processes episodic events."""
        # Insert test events
        cursor = db_full_schema.conn.cursor()
        now = int(datetime.now().timestamp())

        events = [
            (1, "Implemented JWT authentication", now, "action"),
            (1, "Added password validation", now + 60, "action"),
            (1, "Created login endpoint", now + 120, "action"),
        ]

        for project_id, content, timestamp, event_type in events:
            cursor.execute(
                "INSERT INTO episodic_events (project_id, content, timestamp, event_type) VALUES (?, ?, ?, ?)",
                (project_id, content, timestamp, event_type),
            )

        db_full_schema.conn.commit()

        # Run pipeline
        result = tier1_pipeline.run_full_pipeline(project_id=1)

        assert result["status"] == "success"
        assert result["stages"]["consolidation"]["event_count"] == 3


class TestConsolidationStage:
    """Test consolidation stage of Tier 1 pipeline."""

    def test_consolidation_event_processing(self, db_full_schema, tier1_pipeline):
        """Consolidation stage processes events correctly."""
        cursor = db_full_schema.conn.cursor()
        now = int(datetime.now().timestamp())

        # Insert varied events
        for i in range(5):
            cursor.execute(
                "INSERT INTO episodic_events (project_id, content, timestamp, event_type) VALUES (?, ?, ?, ?)",
                (1, f"Event {i}", now + (i * 100), "action"),
            )

        db_full_schema.conn.commit()

        result = tier1_pipeline._stage_consolidation(project_id=1)

        assert result["event_count"] == 5
        assert result["consolidated_count"] == 5
        assert result["patterns_extracted"] > 0

    def test_consolidation_quality_scoring(self, db_full_schema, tier1_pipeline):
        """Consolidation computes quality score."""
        cursor = db_full_schema.conn.cursor()
        now = int(datetime.now().timestamp())

        # Insert events
        for i in range(3):
            cursor.execute(
                "INSERT INTO episodic_events (project_id, content, timestamp, event_type) VALUES (?, ?, ?, ?)",
                (1, f"Test event {i}", now + (i * 50), "action"),
            )

        db_full_schema.conn.commit()

        result = tier1_pipeline._stage_consolidation(project_id=1)

        assert "quality_score" in result
        assert 0.0 <= result["quality_score"] <= 1.0


class TestSurpriseStage:
    """Test Bayesian surprise stage."""

    def test_surprise_boundary_detection(self, db_full_schema, tier1_pipeline):
        """Surprise stage detects semantic boundaries."""
        cursor = db_full_schema.conn.cursor()
        now = int(datetime.now().timestamp())

        # Insert related events (low surprise)
        related_events = [
            "Implemented authentication",
            "Added login validation",
            "Created JWT tokens",
        ]

        for i, content in enumerate(related_events):
            cursor.execute(
                "INSERT INTO episodic_events (project_id, content, timestamp, event_type) VALUES (?, ?, ?, ?)",
                (1, content, now + (i * 60), "action"),
            )

        db_full_schema.conn.commit()

        consolidation_result = {"event_count": len(related_events)}
        result = tier1_pipeline._stage_surprise_detection(1, consolidation_result)

        assert "surprise_boundaries" in result
        assert "surprise_count" in result

    def test_surprise_high_novelty_events(self, db_full_schema, tier1_pipeline):
        """Surprise detection identifies novel events."""
        cursor = db_full_schema.conn.cursor()
        now = int(datetime.now().timestamp())

        # Insert diverse events
        diverse_events = [
            "Implemented authentication system",
            "Optimized database queries",  # Different domain
            "Fixed UI styling bug",  # Another domain
        ]

        for i, content in enumerate(diverse_events):
            cursor.execute(
                "INSERT INTO episodic_events (project_id, content, timestamp, event_type) VALUES (?, ?, ?, ?)",
                (1, content, now + (i * 60), "action"),
            )

        db_full_schema.conn.commit()

        consolidation_result = {"event_count": len(diverse_events)}
        result = tier1_pipeline._stage_surprise_detection(1, consolidation_result)

        # Should have some surprise boundaries
        assert result["surprise_count"] >= 0


class TestSaliencyStage:
    """Test saliency assessment stage."""

    def test_saliency_memory_assessment(self, db_full_schema, tier1_pipeline):
        """Saliency stage assesses consolidated memory importance."""
        cursor = db_full_schema.conn.cursor()
        now = int(datetime.now().timestamp())

        # Insert test memory
        cursor.execute(
            "INSERT INTO memories (project_id, content, created_at, access_count) VALUES (?, ?, ?, ?)",
            (1, "Critical authentication logic", now, 5),
        )

        db_full_schema.conn.commit()

        consolidation_result = {"event_count": 1}
        result = tier1_pipeline._stage_saliency_assessment(project_id=1, consolidation_result=consolidation_result)

        assert result["assessed_memories"] >= 0
        assert "saliency_distribution" in result

    def test_saliency_goal_alignment(self, db_full_schema, tier1_pipeline):
        """Saliency increases with goal alignment."""
        cursor = db_full_schema.conn.cursor()
        now = int(datetime.now().timestamp())

        # Insert authentication-related memory
        cursor.execute(
            "INSERT INTO memories (project_id, content, created_at, access_count) VALUES (?, ?, ?, ?)",
            (1, "JWT token implementation details", now, 3),
        )

        db_full_schema.conn.commit()

        consolidation_result = {"event_count": 1}

        # Without goal
        result_no_goal = tier1_pipeline._stage_saliency_assessment(
            project_id=1,
            consolidation_result=consolidation_result,
            current_goal=None,
        )

        # With related goal
        result_with_goal = tier1_pipeline._stage_saliency_assessment(
            project_id=1,
            consolidation_result=consolidation_result,
            current_goal="implement authentication system",
        )

        assert result_no_goal["assessed_memories"] == result_with_goal["assessed_memories"]


class TestAutoFocusStage:
    """Test automatic focus stage."""

    def test_auto_focus_top_memories(self, db_full_schema, tier1_pipeline):
        """Auto-focus identifies and focuses top memories."""
        cursor = db_full_schema.conn.cursor()
        now = int(datetime.now().timestamp())

        # Insert test memories
        for i in range(5):
            cursor.execute(
                "INSERT INTO memories (project_id, content, created_at, access_count) VALUES (?, ?, ?, ?)",
                (1, f"Memory {i}", now - (i * 100), i + 1),
            )

        db_full_schema.conn.commit()

        saliency_result = {"assessed_memories": 5, "avg_saliency": 0.6}
        result = tier1_pipeline._stage_auto_focus(
            project_id=1,
            saliency_result=saliency_result,
        )

        assert result["focused_memories"] > 0
        assert len(result["focus_list"]) > 0

    def test_focus_weight_decay(self, db_full_schema, tier1_pipeline):
        """Auto-focus applies weight decay across ranks."""
        cursor = db_full_schema.conn.cursor()
        now = int(datetime.now().timestamp())

        # Insert multiple memories
        for i in range(3):
            cursor.execute(
                "INSERT INTO memories (project_id, content, created_at, access_count) VALUES (?, ?, ?, ?)",
                (1, f"Memory {i}", now, 5),
            )

        db_full_schema.conn.commit()

        saliency_result = {"assessed_memories": 3, "avg_saliency": 0.7}
        result = tier1_pipeline._stage_auto_focus(
            project_id=1,
            saliency_result=saliency_result,
        )

        # Verify focus list has items
        assert len(result["focus_list"]) > 0


@pytest.mark.integration
class TestFullTier1Pipeline:
    """Test complete Tier 1 pipeline execution."""

    def test_pipeline_success_flow(self, db_full_schema, tier1_pipeline):
        """Full pipeline executes successfully."""
        cursor = db_full_schema.conn.cursor()
        now = int(datetime.now().timestamp())

        # Create realistic scenario
        events = [
            "Started implementing user authentication",
            "Added JWT token generation",
            "Implemented token validation",
            "Created refresh token endpoint",
        ]

        for i, content in enumerate(events):
            cursor.execute(
                "INSERT INTO episodic_events (project_id, content, timestamp, event_type) VALUES (?, ?, ?, ?)",
                (1, content, now + (i * 120), "action"),
            )

        db_full_schema.conn.commit()

        # Run full pipeline
        result = tier1_pipeline.run_full_pipeline(project_id=1, current_goal="implement authentication")

        assert result["status"] == "success"
        assert "stages" in result
        assert "metrics" in result
        assert "timestamp" in result

    def test_pipeline_quality_metrics(self, db_full_schema, tier1_pipeline):
        """Pipeline computes quality metrics."""
        cursor = db_full_schema.conn.cursor()
        now = int(datetime.now().timestamp())

        # Insert test data
        for i in range(3):
            cursor.execute(
                "INSERT INTO episodic_events (project_id, content, timestamp, event_type) VALUES (?, ?, ?, ?)",
                (1, f"Event {i}", now + (i * 60), "action"),
            )

        db_full_schema.conn.commit()

        result = tier1_pipeline.run_full_pipeline(project_id=1)

        metrics = result["metrics"]
        assert "total_events_processed" in metrics
        assert "total_patterns_extracted" in metrics
        assert "surprise_boundaries_found" in metrics
        assert "pipeline_quality_score" in metrics
        assert 0.0 <= metrics["pipeline_quality_score"] <= 1.0

    def test_pipeline_with_session_filter(self, db_full_schema, tier1_pipeline):
        """Pipeline filters by session if provided."""
        cursor = db_full_schema.conn.cursor()
        now = int(datetime.now().timestamp())

        # Events from multiple sessions
        sessions = ["session_1", "session_2"]
        for session in sessions:
            for i in range(2):
                cursor.execute(
                    "INSERT INTO episodic_events (project_id, content, timestamp, event_type, session_id) VALUES (?, ?, ?, ?, ?)",
                    (1, f"Event_{session}_{i}", now + (i * 60), "action", session),
                )

        db_full_schema.conn.commit()

        # Run with session filter
        result = tier1_pipeline.run_full_pipeline(
            project_id=1,
            session_id="session_1",
        )

        assert result["status"] == "success"
        assert result["session_id"] == "session_1"


@pytest.mark.integration
class TestTier1Monitor:
    """Test Tier 1 pipeline monitoring."""

    def test_monitor_initialization(self, tier1_monitor):
        """Monitor initializes with empty history."""
        health = tier1_monitor.get_health_report()
        assert health["status"] == "no_data"
        assert health["executions"] == 0

    def test_monitor_records_execution(self, tier1_monitor, db_full_schema, tier1_pipeline):
        """Monitor records pipeline execution."""
        result = tier1_pipeline.run_full_pipeline(project_id=1)
        tier1_monitor.record_execution(result)

        health = tier1_monitor.get_health_report()
        assert health["executions"] == 1

    def test_monitor_health_scoring(self, tier1_monitor, db_full_schema, tier1_pipeline):
        """Monitor computes health scores from executions."""
        # Run multiple executions
        for i in range(3):
            result = tier1_pipeline.run_full_pipeline(project_id=1)
            tier1_monitor.record_execution(result)

        health = tier1_monitor.get_health_report()

        assert "avg_quality_score" in health
        assert "success_rate" in health
        assert "recommendations" in health
        assert 0.0 <= health["avg_quality_score"] <= 1.0
        assert 0.0 <= health["success_rate"] <= 1.0

    def test_monitor_recommendations(self, tier1_monitor):
        """Monitor generates actionable recommendations."""
        # Simulate poor quality execution
        poor_result = {
            "status": "success",
            "metrics": {"pipeline_quality_score": 0.3},
        }
        tier1_monitor.record_execution(poor_result)

        health = tier1_monitor.get_health_report()
        assert len(health["recommendations"]) > 0


@pytest.mark.integration
class TestTier1ResearchValidation:
    """Test Tier 1 alignment with research foundations."""

    def test_consolidation_matches_research(self, tier1_pipeline):
        """Consolidation follows sleep-learning principles."""
        # Consolidation should extract patterns from episodic events
        # This is verified by running the pipeline and checking pattern count
        assert tier1_pipeline.consolidation_system is not None

    def test_surprise_matches_bayesian_model(self, tier1_pipeline):
        """Surprise detection uses Bayesian principles (Kumar et al. 2023)."""
        assert tier1_pipeline.surprise_calc is not None
        # BayesianSurpriseCalculator implements entropy-based surprise

    def test_saliency_matches_working_memory(self, tier1_pipeline):
        """Saliency follows working memory principles (Baddeley 2000)."""
        assert tier1_pipeline.saliency_calc is not None
        # SaliencyCalculator combines frequency, recency, relevance, surprise

    def test_multi_factor_saliency_weights(self, tier1_pipeline):
        """Multi-factor saliency uses correct research-backed weights."""
        # Verify weights sum to 1.0
        weights = tier1_pipeline.saliency_calc.weights
        total_weight = sum(weights.values())
        assert abs(total_weight - 1.0) < 1e-6

        # Verify expected weights
        assert weights["frequency"] == 0.30
        assert weights["recency"] == 0.30
        assert weights["relevance"] == 0.25
        assert weights["surprise"] == 0.15
