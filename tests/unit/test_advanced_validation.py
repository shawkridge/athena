"""Unit tests for advanced validation & feedback loops."""

import pytest
from datetime import datetime
from unittest.mock import Mock

from athena.planning.advanced_validation import (
    PlanMonitor,
    AdaptiveReplanning,
    FormalVerificationEngine,
    HumanValidationGate,
    AdvancedValidationManager,
    PlanMonitoringStatus,
    ReplanTriggerType,
    ExecutionMonitoringPoint,
    PlanDeviation,
)
from athena.planning.store import PlanningStore


class TestPlanMonitor:
    """Tests for PlanMonitor."""

    @pytest.fixture
    def mock_planning_store(self):
        """Create mock planning store."""
        return Mock(spec=PlanningStore)

    @pytest.fixture
    def monitor(self, mock_planning_store):
        """Create plan monitor."""
        return PlanMonitor(mock_planning_store)

    def test_record_monitoring_point(self, monitor):
        """Test recording a monitoring point."""
        point = monitor.record_monitoring_point(
            task_id=1,
            planned_duration=30,
            actual_duration=45,
            quality_score=0.85,
            blockers=["API timeout"],
        )

        assert isinstance(point, ExecutionMonitoringPoint)
        assert point.task_id == 1
        assert point.planned_duration_minutes == 30
        assert point.actual_duration_minutes == 45
        assert point.actual_quality_score == 0.85
        assert "API timeout" in point.blockers_encountered

    def test_detect_duration_deviation(self, monitor):
        """Test detecting duration deviation."""
        deviations = monitor.detect_deviations(
            task_id=1,
            planned_duration=30,
            actual_duration=60,  # 100% overrun
            quality_score=0.9,
        )

        assert len(deviations) > 0
        assert deviations[0].deviation_type == "duration"
        assert deviations[0].severity >= 0.5

    def test_detect_quality_deviation(self, monitor):
        """Test detecting quality deviation."""
        deviations = monitor.detect_deviations(
            task_id=1,
            planned_duration=30,
            actual_duration=35,
            quality_score=0.4,  # Below 0.5 threshold
        )

        assert any(d.deviation_type == "quality" for d in deviations)

    def test_detect_blocker_deviation(self, monitor):
        """Test detecting blocker deviation."""
        deviations = monitor.detect_deviations(
            task_id=1,
            planned_duration=30,
            actual_duration=35,
            blockers=["Database down", "API error", "Network issue"],
        )

        assert any(d.deviation_type == "blockers" for d in deviations)

    def test_monitoring_status_on_track(self, monitor):
        """Test monitoring status when on track."""
        # No deviations recorded
        status = monitor.get_monitoring_status(1)
        assert status == PlanMonitoringStatus.ON_TRACK

    def test_monitoring_status_with_deviations(self, monitor):
        """Test monitoring status with deviations."""
        # Detect large deviation
        monitor.detect_deviations(
            task_id=1,
            planned_duration=30,
            actual_duration=120,  # 400% overrun
            quality_score=0.5,
        )

        status = monitor.get_monitoring_status(1)
        assert status == PlanMonitoringStatus.CRITICAL_DEVIATION

    def test_multiple_monitoring_points(self, monitor):
        """Test recording multiple monitoring points."""
        monitor.record_monitoring_point(1, 30, 35)
        monitor.record_monitoring_point(1, 30, 40)
        monitor.record_monitoring_point(1, 30, 45)

        assert len(monitor.monitoring_points[1]) == 3


class TestAdaptiveReplanning:
    """Tests for AdaptiveReplanning."""

    @pytest.fixture
    def mock_planning_store(self):
        """Create mock planning store."""
        return Mock(spec=PlanningStore)

    @pytest.fixture
    def replanning(self, mock_planning_store):
        """Create adaptive replanning engine."""
        return AdaptiveReplanning(mock_planning_store)

    def test_trigger_replanning(self, replanning):
        """Test triggering adaptive replanning."""
        revised_plan = replanning.trigger_replanning(
            task_id=1,
            trigger_type=ReplanTriggerType.DURATION_EXCEEDED,
            trigger_reason="Task took 2x longer than planned",
            remaining_work_description="3 more tasks to complete",
        )

        assert revised_plan is not None
        assert revised_plan.original_plan_id == 1
        assert revised_plan.revision_number == 1
        assert revised_plan.trigger == ReplanTriggerType.DURATION_EXCEEDED

    def test_multiple_revisions(self, replanning):
        """Test tracking multiple replanning revisions."""
        revised_plan_1 = replanning.trigger_replanning(
            1, ReplanTriggerType.DURATION_EXCEEDED, "First replan", ""
        )
        revised_plan_2 = replanning.trigger_replanning(
            1, ReplanTriggerType.QUALITY_DEGRADATION, "Second replan", ""
        )

        assert revised_plan_1.revision_number == 1
        assert revised_plan_2.revision_number == 2

    def test_calculate_remaining_work(self, replanning):
        """Test calculating remaining work."""
        remaining_minutes, description = replanning.calculate_remaining_work(
            completed_tasks=5,
            total_planned_tasks=10,
            average_duration_actual=45,
            average_duration_planned=30,
        )

        assert remaining_minutes > 0
        assert "5 tasks remaining" in description
        assert "150" in description  # 1.5x ratio (150.0%)


class TestFormalVerificationEngine:
    """Tests for FormalVerificationEngine."""

    @pytest.fixture
    def mock_planning_store(self):
        """Create mock planning store."""
        return Mock(spec=PlanningStore)

    @pytest.fixture
    def verification(self, mock_planning_store):
        """Create formal verification engine."""
        return FormalVerificationEngine(mock_planning_store)

    def test_verify_plan_properties(self, verification):
        """Test formal plan verification."""
        result = verification.verify_plan_properties(
            plan_id=1,
            properties_to_verify=[
                "no_circular_dependencies",
                "all_tasks_have_acceptance_criteria",
            ],
        )

        assert result.plan_id == 1
        assert len(result.properties_verified) > 0
        assert 0.0 <= result.verification_confidence <= 1.0

    def test_all_properties_pass(self, verification):
        """Test when all properties pass verification."""
        result = verification.verify_plan_properties(plan_id=1)

        assert result.all_properties_passed is True
        assert result.verification_confidence >= 0.90
        assert len(result.counterexamples) == 0


class TestHumanValidationGate:
    """Tests for HumanValidationGate."""

    @pytest.fixture
    def mock_planning_store(self):
        """Create mock planning store."""
        return Mock(spec=PlanningStore)

    @pytest.fixture
    def gates(self, mock_planning_store):
        """Create human validation gate system."""
        return HumanValidationGate(mock_planning_store)

    def test_create_validation_gate(self, gates):
        """Test creating a validation gate."""
        gate = gates.create_validation_gate(
            gate_name="Phase 1 Transition",
            gate_type="phase_transition",
            plan_id=1,
            description="Review planning decisions before implementation",
            context={"phase_number": 1},
        )

        assert gate["gate_id"] == 0
        assert gate["gate_name"] == "Phase 1 Transition"
        assert gate["human_review_provided"] is False

    def test_record_human_review_approval(self, gates):
        """Test recording human approval."""
        gate = gates.create_validation_gate(
            "Test Gate", "phase_transition", 1, "Test", {}
        )

        success = gates.record_human_review(
            gate_id=0,
            decision="approved",
            feedback="Plan looks good, proceed with implementation",
        )

        assert success is True
        assert gate["human_review_provided"] is True
        assert gate["human_decision"] == "approved"

    def test_record_human_rejection(self, gates):
        """Test recording human rejection."""
        gates.create_validation_gate(
            "Test Gate", "phase_transition", 1, "Test", {}
        )

        success = gates.record_human_review(
            gate_id=0,
            decision="rejected",
            feedback="Duration estimates seem too optimistic",
        )

        assert success is True
        gate = gates.get_gate_status(0)
        assert gate["human_decision"] == "rejected"

    def test_get_pending_gates(self, gates):
        """Test retrieving pending gates."""
        gates.create_validation_gate(
            "Gate 1", "phase_transition", 1, "Test", {}
        )
        gates.create_validation_gate(
            "Gate 2", "phase_transition", 1, "Test", {}
        )
        gates.record_human_review(0, "approved")

        pending = gates.get_pending_gates()
        assert len(pending) == 1
        assert pending[0]["gate_name"] == "Gate 2"

    def test_get_gate_status(self, gates):
        """Test getting gate status."""
        gates.create_validation_gate(
            "Test Gate", "phase_transition", 1, "Test", {}
        )

        status = gates.get_gate_status(0)
        assert status is not None
        assert status["gate_name"] == "Test Gate"

    def test_get_nonexistent_gate(self, gates):
        """Test getting nonexistent gate."""
        status = gates.get_gate_status(999)
        assert status is None


class TestAdvancedValidationManager:
    """Tests for AdvancedValidationManager."""

    @pytest.fixture
    def mock_planning_store(self):
        """Create mock planning store."""
        return Mock(spec=PlanningStore)

    @pytest.fixture
    def manager(self, mock_planning_store):
        """Create advanced validation manager."""
        return AdvancedValidationManager(mock_planning_store)

    def test_manager_initialization(self, manager):
        """Test manager initializes all subsystems."""
        assert manager.monitor is not None
        assert manager.replanning is not None
        assert manager.verification is not None
        assert manager.human_gates is not None

    def test_start_plan_monitoring(self, manager):
        """Test starting plan monitoring."""
        manager.start_plan_monitoring(1)
        # Should complete without error

    def test_record_execution_checkpoint_on_track(self, manager):
        """Test recording checkpoint when on track."""
        status = manager.record_execution_checkpoint(
            plan_id=1,
            task_id=1,
            planned_duration=30,
            actual_duration=32,
            quality_score=0.95,
        )

        assert status == PlanMonitoringStatus.ON_TRACK

    def test_record_execution_checkpoint_deviation(self, manager):
        """Test recording checkpoint with deviation."""
        status = manager.record_execution_checkpoint(
            plan_id=1,
            task_id=1,
            planned_duration=30,
            actual_duration=90,  # Large overrun
            quality_score=0.5,
            blockers=["Database issue", "API error"],
        )

        assert status in [
            PlanMonitoringStatus.CRITICAL_DEVIATION,
            PlanMonitoringStatus.DEVIATION_DETECTED,
        ]

    def test_verify_plan_before_execution(self, manager):
        """Test formal verification before execution."""
        result = manager.verify_plan_before_execution(1)

        assert result.plan_id == 1
        assert isinstance(result.all_properties_passed, bool)
        assert result.verification_confidence > 0.0

    def test_create_phase_transition_gate(self, manager):
        """Test creating phase transition gate."""
        gate = manager.create_phase_transition_gate(
            plan_id=1,
            phase_number=1,
            phase_name="Planning",
        )

        assert gate["gate_type"] == "phase_transition"
        assert "Phase 1" in gate["gate_name"]

    def test_full_monitoring_workflow(self, manager):
        """Test complete monitoring workflow."""
        # Start monitoring
        manager.start_plan_monitoring(1)

        # Verify plan
        verification = manager.verify_plan_before_execution(1)
        assert verification.all_properties_passed is True

        # Create phase gate
        gate = manager.create_phase_transition_gate(1, 1, "Planning")
        assert gate is not None

        # Record checkpoint
        status = manager.record_execution_checkpoint(1, 1, 30, 35, 0.90)
        assert status == PlanMonitoringStatus.ON_TRACK


# Integration tests
class TestAdvancedValidationIntegration:
    """Integration tests for advanced validation system."""

    def test_complete_validation_flow(self):
        """Test complete validation flow from planning to execution."""
        mock_store = Mock(spec=PlanningStore)
        manager = AdvancedValidationManager(mock_store)

        # 1. Verify plan
        verification = manager.verify_plan_before_execution(1)
        assert verification.all_properties_passed is True

        # 2. Create pre-execution gate
        gate_1 = manager.create_phase_transition_gate(1, 1, "Planning")
        assert not gate_1["human_review_provided"]

        # 3. Record human approval
        manager.human_gates.record_human_review(0, "approved")
        assert gate_1["human_review_provided"]

        # 4. Start monitoring
        manager.start_plan_monitoring(1)

        # 5. Record successful checkpoint
        status_1 = manager.record_execution_checkpoint(1, 1, 30, 31, 0.95)
        assert status_1 == PlanMonitoringStatus.ON_TRACK

        # 6. Record checkpoint with deviation
        status_2 = manager.record_execution_checkpoint(1, 2, 30, 80, 0.4)
        assert status_2 in [
            PlanMonitoringStatus.CRITICAL_DEVIATION,
            PlanMonitoringStatus.DEVIATION_DETECTED,
        ]

    def test_replanning_triggered_by_deviation(self):
        """Test that replanning is triggered by critical deviations."""
        mock_store = Mock(spec=PlanningStore)
        manager = AdvancedValidationManager(mock_store)

        # Record critical deviation
        status = manager.record_execution_checkpoint(
            plan_id=1,
            task_id=1,
            planned_duration=30,
            actual_duration=120,
            quality_score=0.3,
            blockers=["Major issue"],
        )

        # Should detect critical deviation
        assert status == PlanMonitoringStatus.CRITICAL_DEVIATION

    def test_human_gate_approval_workflow(self):
        """Test human approval workflow through gates."""
        mock_store = Mock(spec=PlanningStore)
        manager = AdvancedValidationManager(mock_store)

        # Create multiple gates
        gate_1 = manager.create_phase_transition_gate(1, 1, "Planning")
        gate_2 = manager.create_phase_transition_gate(1, 2, "Implementation")

        # Check pending gates
        pending = manager.human_gates.get_pending_gates()
        assert len(pending) == 2

        # Approve first gate
        manager.human_gates.record_human_review(0, "approved")

        # Check pending gates again
        pending = manager.human_gates.get_pending_gates()
        assert len(pending) == 1
        assert pending[0]["gate_name"] == "Phase 2: Implementation Transition"
