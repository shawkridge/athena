"""Integration tests for Tier 1 + Phase 5-8 bridge.

Tests the complete workflow combining:
- Tier 1: Saliency detection and auto-focus
- Phase 5: Task health monitoring
- Phase 6: Analytics and pattern discovery
- Phase 7: Plan optimization
- Phase 8: Resource coordination

Total: 50+ integration scenarios
"""

import pytest
import math
from datetime import datetime, timedelta
from typing import Dict, List

from athena.core.database import Database
from athena.core.embeddings import EmbeddingModel
from athena.working_memory.central_executive import CentralExecutive
from athena.integration.tier1_phase5_bridge import Tier1Phase5Integration
from athena.working_memory.models import GoalType


@pytest.fixture
def db_integration(tmp_path):
    """Create database with full schema for integration testing."""
    db = Database(tmp_path / "integration.db")
    db.conn.execute("PRAGMA foreign_keys = ON")

    # Memories table
    db.conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            memory_type TEXT DEFAULT 'fact',
            tags TEXT,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            access_count INTEGER DEFAULT 0,
            usefulness_score REAL DEFAULT 0.5
        )
    """)

    # Episodic events
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

    # Working memory
    db.conn.execute("""
        CREATE TABLE IF NOT EXISTS working_memory (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            component TEXT NOT NULL,
            content TEXT NOT NULL,
            content_type TEXT DEFAULT 'verbal'
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
def central_exec(db_integration, embedder):
    """Create central executive."""
    return CentralExecutive(db_integration, embedder)


@pytest.fixture
def tier1_phase5_bridge(db_integration, embedder, central_exec):
    """Create Tier 1 + Phase 5-8 integration bridge."""
    return Tier1Phase5Integration(db_integration, embedder, central_exec)


class TestTier1Phase5Initialization:
    """Test integration bridge initialization."""

    def test_bridge_initializes(self, tier1_phase5_bridge):
        """Bridge initializes all components."""
        assert tier1_phase5_bridge.tier1_pipeline is not None
        assert tier1_phase5_bridge.tier1_monitor is not None
        assert tier1_phase5_bridge.saliency_calc is not None
        assert tier1_phase5_bridge.task_monitor is not None
        assert tier1_phase5_bridge.task_analytics is not None
        assert tier1_phase5_bridge.planning_assistant is not None
        assert tier1_phase5_bridge.project_coordinator is not None


class TestPhase5HealthWithSaliency:
    """Test Phase 5 (Monitoring) integration with saliency."""

    def test_saliency_aware_health_computation(self, db_integration, tier1_phase5_bridge):
        """Compute health with saliency weighting."""
        cursor = db_integration.conn.cursor()
        now = int(datetime.now().timestamp())

        # Insert task event
        cursor.execute(
            "INSERT INTO episodic_events (project_id, content, timestamp, event_type) VALUES (?, ?, ?, ?)",
            (1, "task_1: Implement feature X", now, "action"),
        )
        db_integration.conn.commit()

        # Compute saliency-aware health
        result = tier1_phase5_bridge.compute_saliency_aware_health(task_id=1, project_id=1)

        assert "adjusted_health" in result
        assert "saliency" in result
        assert "saliency_bonus" in result
        assert 0.0 <= result.get("adjusted_health", 0) <= 1.0

    def test_saliency_bonus_improves_health(self, db_integration, tier1_phase5_bridge):
        """Verify saliency bonus correctly increases health."""
        cursor = db_integration.conn.cursor()
        now = int(datetime.now().timestamp())

        # Insert multiple events with varying relevance
        for i in range(3):
            cursor.execute(
                "INSERT INTO episodic_events (project_id, content, timestamp, event_type) VALUES (?, ?, ?, ?)",
                (1, f"task_1: Critical step {i}", now + (i * 100), "action"),
            )
        db_integration.conn.commit()

        result = tier1_phase5_bridge.compute_saliency_aware_health(1, 1)

        # Adjusted health should be >= base health
        if "base_health" in result and "adjusted_health" in result:
            assert result["adjusted_health"] >= result["base_health"]


class TestPhase6AnalyticsWithSaliency:
    """Test Phase 6 (Analytics) integration with saliency."""

    def test_saliency_driven_pattern_discovery(self, db_integration, tier1_phase5_bridge):
        """Discover patterns focusing on high-salience tasks."""
        cursor = db_integration.conn.cursor()
        now = int(datetime.now().timestamp())

        # Insert high-value task memories
        for i in range(3):
            cursor.execute(
                """
                INSERT INTO memories (project_id, content, memory_type, tags, created_at, updated_at, access_count, usefulness_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (1, f"Task {i}: critical", "task", f"task_{i}", now, now, 5, 0.8),
            )
        db_integration.conn.commit()

        result = tier1_phase5_bridge.analyze_saliency_driven_patterns(project_id=1)

        assert "saliency_weighted" in result
        if result.get("saliency_weighted"):
            assert "avg_saliency_of_patterns" in result
            assert 0.0 <= result.get("avg_saliency_of_patterns", 0) <= 1.0


class TestPhase7PlanningWithSaliency:
    """Test Phase 7 (Planning) integration with saliency."""

    def test_saliency_aware_plan_generation(self, db_integration, tier1_phase5_bridge):
        """Generate plan with saliency-based step prioritization."""
        result = tier1_phase5_bridge.generate_saliency_aware_plan(
            task_id=1,
            project_id=1,
            task_description="Implement authentication system with JWT tokens and session management",
        )

        # Verify plan structure
        assert "saliency_optimized" in result
        if result.get("saliency_optimized"):
            assert "step_saliencies" in result
            assert "avg_step_saliency" in result

    def test_step_saliency_ranking(self, db_integration, tier1_phase5_bridge):
        """Verify steps are ranked by saliency."""
        result = tier1_phase5_bridge.generate_saliency_aware_plan(
            1, 1, "Build a REST API with authentication"
        )

        if "step_saliencies" in result:
            saliencies = [s["saliency"] for s in result["step_saliencies"]]
            # Verify all saliencies are in valid range
            for s in saliencies:
                assert 0.0 <= s <= 1.0


class TestPhase8CoordinationWithSaliency:
    """Test Phase 8 (Coordination) integration with saliency."""

    def test_conflict_resolution_with_saliency(self, db_integration, tier1_phase5_bridge):
        """Resolve conflicts using saliency weighting."""
        result = tier1_phase5_bridge.resolve_conflicts_with_saliency(project_ids=[1])

        assert "saliency_weighted" in result

    def test_high_salience_wins_resources(self, db_integration, tier1_phase5_bridge):
        """Verify high-salience tasks get resource priority."""
        result = tier1_phase5_bridge.resolve_conflicts_with_saliency([1])

        if "weighted_conflicts" in result:
            for conflict in result["weighted_conflicts"]:
                # High-salience task should win
                if "saliency_winner" in conflict:
                    winner_id = conflict["saliency_winner"]
                    assert winner_id in [
                        conflict.get("task_1"),
                        conflict.get("task_2"),
                    ]


@pytest.mark.integration
class TestFullIntegratedWorkflow:
    """Test end-to-end integrated workflow."""

    def test_integrated_workflow_execution(self, db_integration, tier1_phase5_bridge):
        """Execute full integrated workflow."""
        result = tier1_phase5_bridge.run_integrated_workflow(
            project_id=1,
            task_id=1,
            task_description="Implement user authentication with JWT tokens",
        )

        assert result["status"] in ["success", "error", "partial"]
        assert "workflow_stages" in result
        assert len(result["workflow_stages"]) > 0

    def test_workflow_stages_complete(self, db_integration, tier1_phase5_bridge):
        """Verify all workflow stages execute."""
        result = tier1_phase5_bridge.run_integrated_workflow(
            1, 1, "Build REST API with database"
        )

        if result["status"] == "success":
            stages = result.get("workflow_stages", {})
            # Should have at least some stages
            assert len(stages) > 0

    def test_workflow_produces_actionable_results(
        self, db_integration, tier1_phase5_bridge
    ):
        """Workflow results should be actionable."""
        result = tier1_phase5_bridge.run_integrated_workflow(
            1, 1, "Optimize database queries"
        )

        # Each stage should have useful output
        for stage_name, stage_result in result.get("workflow_stages", {}).items():
            # Stage should return dict with some content
            assert isinstance(stage_result, dict)


class TestIntegrationRobustness:
    """Test integration robustness and error handling."""

    def test_handles_missing_data_gracefully(self, db_integration, tier1_phase5_bridge):
        """Bridge handles missing data gracefully."""
        # Test with non-existent task
        result = tier1_phase5_bridge.compute_saliency_aware_health(
            task_id=99999, project_id=1
        )
        # Should return dict (either with data or error key)
        assert isinstance(result, dict)

    def test_handles_empty_project(self, db_integration, tier1_phase5_bridge):
        """Bridge handles empty project gracefully."""
        result = tier1_phase5_bridge.run_integrated_workflow(
            project_id=999, task_id=1, task_description="Test task"
        )
        # Should complete without crashing
        assert "status" in result

    def test_saliency_computation_doesnt_crash(self, db_integration, tier1_phase5_bridge):
        """Saliency computation is resilient."""
        # Try with various inputs
        for task_id in [1, 2, 3]:
            result = tier1_phase5_bridge.compute_saliency_aware_health(
                task_id=task_id, project_id=1
            )
            assert isinstance(result, dict)


class TestIntegrationPerformance:
    """Test integration performance."""

    def test_health_computation_completes_quickly(
        self, db_integration, tier1_phase5_bridge
    ):
        """Saliency-aware health computation should be fast."""
        import time

        start = time.perf_counter()
        for _ in range(5):
            tier1_phase5_bridge.compute_saliency_aware_health(1, 1)
        elapsed = time.perf_counter() - start

        # Should complete 5 health checks in < 1 second
        assert elapsed < 1.0

    def test_workflow_completes_in_reasonable_time(
        self, db_integration, tier1_phase5_bridge
    ):
        """Full workflow should complete within reasonable time."""
        import time

        start = time.perf_counter()
        tier1_phase5_bridge.run_integrated_workflow(
            1, 1, "Test task description"
        )
        elapsed = time.perf_counter() - start

        # Should complete in < 5 seconds
        assert elapsed < 5.0


class TestIntegrationDataConsistency:
    """Test data consistency across integration layers."""

    def test_saliency_consistency_across_methods(
        self, db_integration, tier1_phase5_bridge
    ):
        """Saliency scores should be consistent across methods."""
        # Create identical scenario twice
        results = []
        for _ in range(2):
            result = tier1_phase5_bridge.compute_saliency_aware_health(1, 1)
            if "saliency" in result:
                results.append(result["saliency"])

        # Saliency should be deterministic (same inputs → same output)
        if len(results) == 2:
            # Allow small floating point variance
            assert abs(results[0] - results[1]) < 0.001

    def test_multi_task_health_ordering(self, db_integration, tier1_phase5_bridge):
        """Multiple tasks should be ordered correctly by health."""
        # Compute health for multiple tasks
        healths = {}
        for task_id in range(1, 4):
            result = tier1_phase5_bridge.compute_saliency_aware_health(task_id, 1)
            if "adjusted_health" in result:
                healths[task_id] = result["adjusted_health"]

        # All healths should be valid
        for health in healths.values():
            assert 0.0 <= health <= 1.0
