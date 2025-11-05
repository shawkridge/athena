"""Phase 7.3 Consolidation Triggers unit tests.

Tests for:
- ConsolidationTrigger: Session-based consolidation triggering
- LearningPathway: Learning progression tracking
- ProcedureAutoCreator: Procedure creation from patterns
- Phase73MCPTools: MCP tool integration
"""

import pytest
from datetime import datetime

from athena.core.database import Database
from athena.ai_coordination.integration.consolidation_trigger import (
    ConsolidationTrigger,
    ConsolidationTriggerType,
    ConsolidationStatus,
)
from athena.ai_coordination.integration.learning_pathway import LearningPathway
from athena.ai_coordination.integration.procedure_auto_creator import ProcedureAutoCreator
from athena.ai_coordination.integration.phase7_3_mcp_tools import Phase73MCPTools


class TestConsolidationTrigger:
    """Tests for ConsolidationTrigger consolidation management."""

    def test_consolidation_trigger_initialization(self, tmp_path):
        """Test ConsolidationTrigger initializes and creates schema."""
        db = Database(tmp_path / "test.db")
        trigger = ConsolidationTrigger(db)

        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('consolidation_triggers', 'pattern_sources', 'consolidation_metrics')
        """)
        tables = [row[0] for row in cursor.fetchall()]
        assert "consolidation_triggers" in tables
        assert "pattern_sources" in tables

    def test_should_consolidate_not_enough_events(self, tmp_path):
        """Test consolidation check with insufficient events."""
        db = Database(tmp_path / "test.db")
        trigger = ConsolidationTrigger(db)

        result = trigger.should_consolidate("session_1")
        assert result["should_consolidate"] is False
        assert result["event_count"] == 0

    def test_should_consolidate_enough_events(self, tmp_path):
        """Test consolidation check with sufficient events."""
        db = Database(tmp_path / "test.db")
        from athena.episodic.store import EpisodicStore
        from athena.episodic.models import EpisodicEvent, EventType, EventOutcome

        episodic_store = EpisodicStore(db)
        trigger = ConsolidationTrigger(db)

        # Create enough events
        for i in range(15):
            event = EpisodicEvent(
                project_id=1,
                session_id="session_1",
                event_type=EventType.ACTION,
                content=f"Event {i}",
                outcome=EventOutcome.SUCCESS,
            )
            episodic_store.record_event(event)

        result = trigger.should_consolidate("session_1")
        assert result["should_consolidate"] is True
        assert result["event_count"] >= 15

    def test_trigger_consolidation(self, tmp_path):
        """Test triggering consolidation."""
        db = Database(tmp_path / "test.db")
        trigger = ConsolidationTrigger(db)

        trigger_id = trigger.trigger_consolidation(
            "session_1",
            ConsolidationTriggerType.SESSION_END,
            {"goal_id": "goal_1"}
        )

        assert trigger_id is not None
        assert trigger_id > 0

    def test_mark_consolidation_started(self, tmp_path):
        """Test marking consolidation as started."""
        db = Database(tmp_path / "test.db")
        trigger = ConsolidationTrigger(db)

        trigger_id = trigger.trigger_consolidation(
            "session_1",
            ConsolidationTriggerType.SESSION_END
        )

        success = trigger.mark_consolidation_started(trigger_id)
        assert success is True

    def test_mark_consolidation_completed(self, tmp_path):
        """Test marking consolidation as completed."""
        db = Database(tmp_path / "test.db")
        trigger = ConsolidationTrigger(db)

        trigger_id = trigger.trigger_consolidation(
            "session_1",
            ConsolidationTriggerType.SESSION_END
        )

        success = trigger.mark_consolidation_completed(
            trigger_id,
            ConsolidationStatus.SUCCESS,
            consolidated_events=10,
            patterns_extracted=3,
            procedures_created=1
        )

        assert success is True

    def test_get_consolidation_status(self, tmp_path):
        """Test retrieving consolidation status."""
        db = Database(tmp_path / "test.db")
        trigger = ConsolidationTrigger(db)

        trigger_id = trigger.trigger_consolidation(
            "session_1",
            ConsolidationTriggerType.SESSION_END
        )

        trigger.mark_consolidation_started(trigger_id)
        trigger.mark_consolidation_completed(
            trigger_id,
            ConsolidationStatus.SUCCESS,
            consolidated_events=10,
            patterns_extracted=3
        )

        status = trigger.get_consolidation_status(trigger_id)
        assert status is not None
        assert status["status"] == ConsolidationStatus.SUCCESS.value
        assert status["consolidated_events"] == 10

    def test_link_pattern_to_source_events(self, tmp_path):
        """Test linking patterns to source events."""
        db = Database(tmp_path / "test.db")
        trigger = ConsolidationTrigger(db)

        # Create episodic events first
        from athena.episodic.store import EpisodicStore
        from athena.episodic.models import EpisodicEvent, EventType, EventOutcome

        episodic_store = EpisodicStore(db)
        event_ids = []
        for i in range(3):
            event = EpisodicEvent(
                project_id=1,
                session_id="session_1",
                event_type=EventType.ACTION,
                content=f"Event {i}",
                outcome=EventOutcome.SUCCESS,
            )
            event_id = episodic_store.record_event(event)
            event_ids.append(event_id)

        link_count = trigger.link_pattern_to_source_events(1, event_ids, 0.9)
        assert link_count == 3

    def test_get_consolidation_metrics(self, tmp_path):
        """Test retrieving consolidation metrics."""
        db = Database(tmp_path / "test.db")
        trigger = ConsolidationTrigger(db)

        # Create multiple consolidations
        for i in range(3):
            trigger_id = trigger.trigger_consolidation(
                "session_1",
                ConsolidationTriggerType.SESSION_END
            )
            trigger.mark_consolidation_completed(
                trigger_id,
                ConsolidationStatus.SUCCESS,
                consolidated_events=10,
                patterns_extracted=2,
                procedures_created=1
            )

        metrics = trigger.get_consolidation_metrics("session_1")
        assert metrics["consolidation_count"] >= 3
        assert metrics["total_procedures_created"] >= 3


class TestLearningPathway:
    """Tests for LearningPathway learning progression."""

    def test_learning_pathway_initialization(self, tmp_path):
        """Test LearningPathway initializes and creates schema."""
        db = Database(tmp_path / "test.db")
        pathway = LearningPathway(db)

        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('learning_pathways', 'pathway_metrics')
        """)
        tables = [row[0] for row in cursor.fetchall()]
        assert "learning_pathways" in tables

    def test_create_execution_pathway(self, tmp_path):
        """Test creating execution learning pathway."""
        db = Database(tmp_path / "test.db")
        pathway = LearningPathway(db)

        pathway_id = pathway.create_execution_pathway(
            "session_1",
            "exec_1",
            episodic_event_id=1,
            confidence=0.8
        )

        assert pathway_id is not None
        assert pathway_id > 0

    def test_create_thinking_pathway(self, tmp_path):
        """Test creating thinking learning pathway."""
        db = Database(tmp_path / "test.db")
        pathway = LearningPathway(db)

        pathway_id = pathway.create_thinking_pathway(
            "session_1",
            "think_1",
            confidence=0.9
        )

        assert pathway_id is not None

    def test_create_action_cycle_pathway(self, tmp_path):
        """Test creating action cycle learning pathway."""
        db = Database(tmp_path / "test.db")
        pathway = LearningPathway(db)

        pathway_id = pathway.create_action_cycle_pathway(
            "session_1",
            "cycle_1",
            confidence=0.7
        )

        assert pathway_id is not None

    def test_link_to_semantic(self, tmp_path):
        """Test linking pathway to semantic pattern."""
        db = Database(tmp_path / "test.db")
        pathway = LearningPathway(db)

        pathway_id = pathway.create_execution_pathway(
            "session_1",
            "exec_1",
            episodic_event_id=1
        )

        success = pathway.link_to_semantic(pathway_id, 100)
        assert success is True

    def test_get_pathway(self, tmp_path):
        """Test retrieving pathway details."""
        db = Database(tmp_path / "test.db")
        pathway = LearningPathway(db)

        pathway_id = pathway.create_execution_pathway(
            "session_1",
            "exec_1",
            episodic_event_id=1,
            confidence=0.85
        )

        retrieved = pathway.get_pathway(pathway_id)
        assert retrieved is not None
        assert retrieved["pathway_type"] == "execution"
        assert retrieved["confidence"] == 0.85

    def test_get_session_pathways(self, tmp_path):
        """Test retrieving pathways for a session."""
        db = Database(tmp_path / "test.db")
        pathway = LearningPathway(db)

        # Create multiple pathways
        for i in range(3):
            pathway.create_execution_pathway(
                "session_1",
                f"exec_{i}",
                episodic_event_id=i+1
            )

        pathways = pathway.get_session_pathways("session_1")
        assert len(pathways) >= 3

    def test_record_pathway_metric(self, tmp_path):
        """Test recording pathway effectiveness metric."""
        db = Database(tmp_path / "test.db")
        pathway = LearningPathway(db)

        pathway_id = pathway.create_execution_pathway(
            "session_1",
            "exec_1",
            episodic_event_id=1
        )

        metric_id = pathway.record_pathway_metric(
            pathway_id,
            "reuse_count",
            5.0
        )

        assert metric_id is not None

    def test_get_learning_effectiveness(self, tmp_path):
        """Test calculating learning effectiveness."""
        db = Database(tmp_path / "test.db")
        pathway = LearningPathway(db)

        # Create pathways
        pathway.create_execution_pathway("session_1", "exec_1", 1)
        pathway.create_thinking_pathway("session_1", "think_1")

        effectiveness = pathway.get_learning_effectiveness("session_1")
        assert effectiveness["total_pathways"] >= 2
        assert "pathway_types" in effectiveness


class TestProcedureAutoCreator:
    """Tests for ProcedureAutoCreator procedure generation."""

    def test_procedure_creator_initialization(self, tmp_path):
        """Test ProcedureAutoCreator initializes and creates schema."""
        db = Database(tmp_path / "test.db")
        creator = ProcedureAutoCreator(db)

        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('procedure_creations', 'procedure_usage')
        """)
        tables = [row[0] for row in cursor.fetchall()]
        assert "procedure_creations" in tables

    def test_create_procedure_from_pattern(self, tmp_path):
        """Test creating procedure from pattern."""
        db = Database(tmp_path / "test.db")
        creator = ProcedureAutoCreator(db)

        procedure_id = creator.create_procedure_from_pattern(
            pattern_id=1,
            pattern_name="Fix Authentication Bug",
            pattern_description="How to fix auth bugs",
            success_rate=0.85,
            lessons=["Check token validation", "Verify scope permissions"]
        )

        assert procedure_id is not None

    def test_create_procedure_low_confidence(self, tmp_path):
        """Test that low-confidence patterns are skipped."""
        db = Database(tmp_path / "test.db")
        creator = ProcedureAutoCreator(db)

        # Low success rate should be skipped
        procedure_id = creator.create_procedure_from_pattern(
            pattern_id=1,
            pattern_name="Risky Pattern",
            pattern_description="Not reliable",
            success_rate=0.4,  # Below threshold
            lessons=[]
        )

        assert procedure_id is None

    def test_record_procedure_usage(self, tmp_path):
        """Test recording procedure usage."""
        db = Database(tmp_path / "test.db")
        creator = ProcedureAutoCreator(db)

        procedure_id = creator.create_procedure_from_pattern(
            pattern_id=1,
            pattern_name="Test Procedure",
            pattern_description="Test",
            success_rate=0.8,
            lessons=["Lesson 1"]
        )

        usage_id = creator.record_procedure_usage(
            procedure_id,
            "session_1",
            "goal_1",
            "success",
            effectiveness=0.9
        )

        assert usage_id is not None

    def test_get_procedure(self, tmp_path):
        """Test retrieving procedure details."""
        db = Database(tmp_path / "test.db")
        creator = ProcedureAutoCreator(db)

        procedure_id = creator.create_procedure_from_pattern(
            pattern_id=1,
            pattern_name="Debug Procedure",
            pattern_description="Debug steps",
            success_rate=0.75,
            lessons=["Check logs", "Verify variables"]
        )

        procedure = creator.get_procedure(procedure_id)
        assert procedure is not None
        assert procedure["name"] == "Debug Procedure"

    def test_get_procedures_by_category(self, tmp_path):
        """Test retrieving procedures by category."""
        db = Database(tmp_path / "test.db")
        creator = ProcedureAutoCreator(db)

        # Create procedures that will be categorized
        creator.create_procedure_from_pattern(
            1, "Debug Error", "Debug", 0.8, []
        )
        creator.create_procedure_from_pattern(
            2, "Git Commit Workflow", "Git", 0.85, []
        )

        debug_procs = creator.get_procedures_by_category("debugging")
        assert isinstance(debug_procs, list)

    def test_get_creation_metrics(self, tmp_path):
        """Test retrieving creation metrics."""
        db = Database(tmp_path / "test.db")
        creator = ProcedureAutoCreator(db)

        # Create some procedures
        for i in range(3):
            creator.create_procedure_from_pattern(
                i, f"Procedure {i}", "Test", 0.8 + i*0.05, []
            )

        metrics = creator.get_creation_metrics()
        assert metrics["total_procedures_created"] >= 3


class TestPhase73MCPTools:
    """Tests for Phase 7.3 MCP tool integration."""

    def test_mcp_tools_initialization(self, tmp_path):
        """Test Phase73MCPTools initializes with components."""
        db = Database(tmp_path / "test.db")
        trigger = ConsolidationTrigger(db)
        pathway = LearningPathway(db)
        creator = ProcedureAutoCreator(db)

        tools = Phase73MCPTools(trigger, pathway, creator)
        assert tools.trigger is not None
        assert tools.pathway is not None
        assert tools.creator is not None

    def test_trigger_consolidation_tool(self, tmp_path):
        """Test trigger_consolidation_for_session MCP tool."""
        db = Database(tmp_path / "test.db")
        trigger = ConsolidationTrigger(db)
        pathway = LearningPathway(db)
        creator = ProcedureAutoCreator(db)

        tools = Phase73MCPTools(trigger, pathway, creator)

        # Add some events
        from athena.episodic.store import EpisodicStore
        from athena.episodic.models import EpisodicEvent, EventType, EventOutcome

        episodic_store = EpisodicStore(db)
        for i in range(15):
            event = EpisodicEvent(
                project_id=1,
                session_id="test_session",
                event_type=EventType.ACTION,
                content=f"Event {i}",
                outcome=EventOutcome.SUCCESS,
            )
            episodic_store.record_event(event)

        result = tools.trigger_consolidation_for_session("test_session")
        assert result["status"] in ["triggered", "skipped"]

    def test_get_consolidation_results_tool(self, tmp_path):
        """Test get_consolidation_results MCP tool."""
        db = Database(tmp_path / "test.db")
        trigger = ConsolidationTrigger(db)
        pathway = LearningPathway(db)
        creator = ProcedureAutoCreator(db)

        tools = Phase73MCPTools(trigger, pathway, creator)

        result = tools.get_consolidation_results("session_1")
        assert result["status"] == "success"

    def test_create_procedure_tool(self, tmp_path):
        """Test create_procedure_from_pattern MCP tool."""
        db = Database(tmp_path / "test.db")
        trigger = ConsolidationTrigger(db)
        pathway = LearningPathway(db)
        creator = ProcedureAutoCreator(db)

        tools = Phase73MCPTools(trigger, pathway, creator)

        result = tools.create_procedure_from_pattern(
            pattern_id=1,
            pattern_name="Test Pattern",
            pattern_description="Test description",
            success_rate=0.8,
            lessons=["Lesson 1", "Lesson 2"]
        )

        assert result["status"] == "success"

    def test_get_learning_pathways_tool(self, tmp_path):
        """Test get_learning_pathways MCP tool."""
        db = Database(tmp_path / "test.db")
        trigger = ConsolidationTrigger(db)
        pathway = LearningPathway(db)
        creator = ProcedureAutoCreator(db)

        tools = Phase73MCPTools(trigger, pathway, creator)

        # Create a pathway
        pathway.create_execution_pathway("session_1", "exec_1", 1)

        result = tools.get_learning_pathways("session_1")
        assert result["status"] == "success"
        assert "effectiveness" in result

    def test_record_procedure_usage_tool(self, tmp_path):
        """Test record_procedure_usage MCP tool."""
        db = Database(tmp_path / "test.db")
        trigger = ConsolidationTrigger(db)
        pathway = LearningPathway(db)
        creator = ProcedureAutoCreator(db)

        tools = Phase73MCPTools(trigger, pathway, creator)

        # Create a procedure first
        proc_id = creator.create_procedure_from_pattern(
            1, "Test", "Test", 0.8, []
        )

        result = tools.record_procedure_usage(
            proc_id,
            "session_1",
            "goal_1",
            "success",
            effectiveness=0.9
        )

        assert result["status"] == "success"
