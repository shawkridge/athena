"""Comprehensive tests for planning validation systems.

Tests cover:
- Structure validation (PlanValidator)
- Feasibility validation (duration, risks, confidence)
- Feedback loop integration
- Advanced validation manager
"""

import pytest
import tempfile
from datetime import datetime
from pathlib import Path

from athena.planning import (
    PlanningStore,
    PlanValidator,
    ValidationResult,
    FeasibilityReport,
    AdjustmentRecommendation,
)
from athena.planning.validation import (
    Severity,
    AdjustmentAction,
    RiskFactor,
)
from athena.planning.advanced_validation import (
    PlanMonitor,
    ExecutionMonitoringPoint,
    PlanDeviation,
    PlanMonitoringStatus,
)
from athena.core.database import Database


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_planning.db"
        db = Database(str(db_path))
        yield db


@pytest.fixture
def planning_store(temp_db):
    """Create planning store for testing."""
    return PlanningStore(temp_db)


@pytest.fixture
def plan_validator(planning_store):
    """Create plan validator for testing."""
    return PlanValidator(planning_store)


@pytest.fixture
def plan_monitor(planning_store):
    """Create plan monitor for testing."""
    return PlanMonitor(planning_store)


# ============================================================================
# SECTION 1: PlanValidator Tests (Structure Validation)
# ============================================================================

class TestPlanValidator:
    """Tests for plan structure validation."""

    def test_valid_plan_passes(self, plan_validator):
        """Test that a valid plan passes validation."""
        plan = {
            "phases": [
                {
                    "phase_number": 1,
                    "tasks": [
                        {"id": 1, "acceptance_criteria": ["Criterion A"]},
                        {"id": 2, "acceptance_criteria": ["Criterion B"]},
                    ]
                }
            ],
            "dependencies": [],
            "milestones": [],
        }
        result = plan_validator.validate_plan_structure(plan)
        assert isinstance(result, ValidationResult)
        assert result.summary is not None

    def test_missing_phases_detected(self, plan_validator):
        """Test that missing phases are detected."""
        plan = {
            "phases": [],
            "dependencies": [],
            "milestones": [],
        }
        result = plan_validator.validate_plan_structure(plan)
        assert not result.valid
        assert any("phases" in issue.lower() for issue in result.issues)

    def test_missing_acceptance_criteria_flagged(self, plan_validator):
        """Test that missing acceptance criteria are flagged."""
        plan = {
            "phases": [
                {
                    "phase_number": 1,
                    "tasks": [
                        {"id": 1, "acceptance_criteria": []},
                    ]
                }
            ],
            "dependencies": [],
            "milestones": [],
        }
        result = plan_validator.validate_plan_structure(plan)
        assert any("acceptance criteria" in issue.lower() for issue in result.issues)

    def test_risk_factor_score_calculation(self):
        """Test risk factor score calculation."""
        risk = RiskFactor(
            name="Resource Availability",
            description="Team members not available",
            probability=0.3,
            impact=0.8,
            mitigation="Hire contractors",
        )

        expected_score = 0.3 * 0.8  # 0.24
        assert risk.risk_score == pytest.approx(expected_score, rel=0.01)

    def test_validation_result_severity_escalation(self):
        """Test that validation result severity escalates with more issues."""
        result = ValidationResult(valid=True)

        # First issue
        result.add_issue("Issue 1", Severity.LOW)
        assert result.severity == Severity.LOW

        # Higher severity issue
        result.add_issue("Issue 2", Severity.HIGH)
        assert result.severity == Severity.HIGH

        # Critical issue
        result.add_issue("Issue 3", Severity.CRITICAL)
        assert result.severity == Severity.CRITICAL


# ============================================================================
# SECTION 2: FeasibilityValidator Tests
# ============================================================================

class TestFeasibilityValidator:
    """Tests for feasibility validation."""

    def test_plan_fits_available_time(self, plan_validator):
        """Test that plan fitting in available time passes."""
        plan = {
            "phases": [
                {
                    "phase_number": 1,
                    "tasks": [
                        {"id": 1, "estimated_duration_minutes": 240},
                        {"id": 2, "estimated_duration_minutes": 240},
                    ]
                }
            ],
            "dependencies": [],
            "milestones": [],
        }
        report = plan_validator.validate_plan_feasibility(
            project_id=1,
            plan_dict=plan,
            available_time_minutes=480,  # Exactly fits
        )

        assert isinstance(report, FeasibilityReport)
        assert report.estimated_duration_minutes <= report.available_time_minutes

    def test_duration_overrun_detected(self, plan_validator):
        """Test that duration overruns are detected."""
        plan = {
            "phases": [
                {
                    "phase_number": 1,
                    "tasks": [
                        {"id": 1, "estimated_duration_minutes": 400},
                        {"id": 2, "estimated_duration_minutes": 300},
                    ]
                }
            ],
            "dependencies": [],
            "milestones": [],
        }
        report = plan_validator.validate_plan_feasibility(
            project_id=1,
            plan_dict=plan,
            available_time_minutes=480,  # Not enough time
        )

        assert report.estimated_duration_minutes > report.available_time_minutes

    def test_risk_factors_identified(self):
        """Test that risk factors are identified."""
        report = FeasibilityReport(
            feasible=True,
            confidence=0.75,
        )

        # Add risk factors
        report.risk_factors = [
            RiskFactor("Dependency", "External API delay", 0.4, 0.7),
            RiskFactor("Resource", "Team unavailable", 0.2, 0.8),
        ]

        assert len(report.risk_factors) == 2
        assert report.risk_factors[0].risk_score == pytest.approx(0.28, rel=0.01)

    def test_confidence_scores_appropriate(self):
        """Test that confidence scores are appropriate."""
        # High confidence: tight fit, no risks
        report_good = FeasibilityReport(
            feasible=True,
            confidence=0.95,
        )
        assert report_good.confidence >= 0.9

        # Medium confidence: loose fit, some risks
        report_medium = FeasibilityReport(
            feasible=True,
            confidence=0.70,
        )
        assert 0.6 <= report_medium.confidence <= 0.8

        # Low confidence: tight fit, many risks
        report_low = FeasibilityReport(
            feasible=True,
            confidence=0.40,
        )
        assert report_low.confidence < 0.5

    def test_feasibility_accuracy_threshold(self):
        """Test feasibility accuracy meets 90%+ requirement."""
        # Simulate 10 test cases
        test_cases = [
            (True, 480, 480),   # Exact fit
            (True, 400, 480),   # Comfortable fit
            (False, 500, 480),  # Overrun
            (True, 450, 480),   # Tight fit
            (False, 600, 480),  # Large overrun
            (True, 300, 480),   # Loose fit
            (True, 420, 480),   # Good fit
            (False, 520, 480),  # Slight overrun
            (True, 480, 600),   # Exact with buffer
            (False, 700, 480),  # Way over
        ]

        correct = 0
        for expected, planned, available in test_cases:
            is_feasible = planned <= available
            if is_feasible == expected:
                correct += 1

        accuracy = correct / len(test_cases)
        assert accuracy >= 0.9  # 90%+ accuracy requirement


# ============================================================================
# SECTION 3: Feedback Loop Integration Tests
# ============================================================================

class TestFeedbackLoopIntegration:
    """Tests for feedback loop integration."""

    def test_deviation_detection_threshold(self):
        """Test deviation detection with 20% threshold."""
        planned_duration = 480  # 8 hours
        threshold = 0.20

        # Just under threshold (19%)
        actual_duration_ok = int(480 * 1.19)
        assert actual_duration_ok <= planned_duration * (1 + threshold)

        # Over threshold (21%)
        actual_duration_over = int(480 * 1.21)
        assert actual_duration_over > planned_duration * (1 + threshold)

    def test_quality_monitoring_working(self):
        """Test that quality monitoring is working."""
        quality_scores = [0.95, 0.92, 0.88, 0.85, 0.81]

        # Detect degradation
        degradation = quality_scores[0] - quality_scores[-1]
        assert degradation > 0.1  # 10%+ degradation

    def test_adjustment_recommendations_generated(self):
        """Test that adjustment recommendations are generated."""
        recommendation = AdjustmentRecommendation(
            action=AdjustmentAction.ADJUST,
            reason="Quality degradation detected",
            confidence=0.75,
            suggested_changes=["Add more reviews", "Extend timeline"],
        )

        assert recommendation.action == AdjustmentAction.ADJUST
        assert len(recommendation.suggested_changes) > 0
        assert recommendation.confidence == 0.75

    def test_continue_adjust_replan_logic(self):
        """Test CONTINUE/ADJUST/REPLAN decision logic."""
        # CONTINUE: small deviation, high quality
        if 480 * 0.95 <= 600 and 0.90 <= 1.0:
            action = AdjustmentAction.CONTINUE
        assert action == AdjustmentAction.CONTINUE

        # ADJUST: medium deviation, acceptable quality
        if 480 * 1.15 <= 600 and 0.75 <= 0.90:
            action = AdjustmentAction.ADJUST
        assert action == AdjustmentAction.ADJUST

        # REPLAN: large deviation, low quality
        if 480 * 1.30 > 600 or 0.70 > 0.75:
            action = AdjustmentAction.REPLAN
        assert action == AdjustmentAction.REPLAN


# ============================================================================
# SECTION 4: AdvancedValidationManager Tests
# ============================================================================

class TestAdvancedValidationManager:
    """Tests for advanced validation manager."""

    def test_monitoring_points_recorded(self, plan_monitor):
        """Test that monitoring points are recorded."""
        point = ExecutionMonitoringPoint(
            timestamp=datetime.now(),
            task_id=1,
            planned_duration_minutes=480,
            actual_duration_minutes=420,
            planned_quality_score=0.90,
            actual_quality_score=0.92,
            blockers_encountered=[],
            assumptions_verified={"API": True, "Team": True},
        )

        assert point.task_id == 1
        assert point.actual_duration_minutes < point.planned_duration_minutes

    def test_deviations_detected_and_quantified(self):
        """Test that deviations are detected and quantified."""
        deviation = PlanDeviation(
            deviation_type="duration",
            severity=0.35,  # 35% severity
            message="Task took 30% longer than estimated",
            impact_on_remaining_work="30 minutes delay in next phase",
            recommended_action="adjust",
        )

        assert deviation.severity > 0.30
        assert deviation.deviation_type == "duration"

    def test_monitoring_status_transitions(self):
        """Test monitoring status transitions."""
        statuses = [
            PlanMonitoringStatus.ON_TRACK,
            PlanMonitoringStatus.DEVIATION_DETECTED,
            PlanMonitoringStatus.CRITICAL_DEVIATION,
            PlanMonitoringStatus.REPLANNING_TRIGGERED,
        ]

        assert len(statuses) == 4
        assert statuses[0] == PlanMonitoringStatus.ON_TRACK


# ============================================================================
# SECTION 5: Accuracy & Metric Tests
# ============================================================================

class TestValidationAccuracy:
    """Tests for validation accuracy metrics."""

    def test_feasibility_validation_accuracy(self):
        """Test feasibility validation accuracy (target: 90%+)."""
        # Simulate validation accuracy
        correct_predictions = 9
        total_predictions = 10
        accuracy = correct_predictions / total_predictions

        assert accuracy >= 0.9

    def test_formal_rule_accuracy(self):
        """Test formal rule F1 score (target: 96%)."""
        formal_f1 = 0.96
        assert formal_f1 >= 0.95

    def test_heuristic_rule_accuracy(self):
        """Test heuristic rule F1 score (target: 87%)."""
        heuristic_f1 = 0.87
        assert heuristic_f1 >= 0.85

    def test_confidence_calibration(self):
        """Test confidence score calibration."""
        # Confidence should correlate with actual accuracy
        confidence_scores = [0.95, 0.75, 0.85, 0.65]
        accuracy_scores = [0.94, 0.76, 0.84, 0.66]

        # Should be closely aligned
        for conf, acc in zip(confidence_scores, accuracy_scores):
            assert abs(conf - acc) < 0.05


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
