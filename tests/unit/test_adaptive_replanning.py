"""Tests for adaptive replanning with failure recovery and plan refinement."""

import pytest
from datetime import timedelta, datetime
from athena.execution.adaptive_replanning import (
    AdaptiveReplanningOrchestrator,
    ExecutionMetrics,
    PlanFailure,
    FailureType,
    RecoveryLevel,
    RecoveryAction,
)


class TestFailureDetection:
    """Test failure detection from execution metrics."""

    def test_detect_timing_overrun(self):
        """Test detection of timing overrun failure."""
        orchestrator = AdaptiveReplanningOrchestrator()

        failure = orchestrator.detect_failure(
            step_id=1,
            expected_duration=timedelta(minutes=10),
            actual_duration=timedelta(minutes=20),  # 2x overrun
            errors_count=0,
        )

        assert failure is not None
        assert failure.failure_type == FailureType.TIMING_OVERRUN
        # Severity = (2.0 - 1.5) / 1.0 = 0.5, so >= 0.5
        assert failure.severity >= 0.5
        assert "took" in failure.message.lower()

    def test_no_failure_on_minor_overrun(self):
        """Test that minor overruns don't trigger failure."""
        orchestrator = AdaptiveReplanningOrchestrator()

        failure = orchestrator.detect_failure(
            step_id=1,
            expected_duration=timedelta(minutes=10),
            actual_duration=timedelta(minutes=13),  # 1.3x (minor)
            errors_count=0,
        )

        # Minor overrun (< 1.5x) should not trigger failure
        assert failure is None

    def test_detect_quality_degradation(self):
        """Test detection of quality degradation (too many errors)."""
        orchestrator = AdaptiveReplanningOrchestrator()

        failure = orchestrator.detect_failure(
            step_id=2,
            expected_duration=timedelta(minutes=10),
            actual_duration=timedelta(minutes=10),
            errors_count=5,  # >= 3 triggers
        )

        assert failure is not None
        assert failure.failure_type == FailureType.QUALITY_DEGRADATION
        assert "5 errors" in failure.message

    def test_detect_assumption_violation(self):
        """Test detection of assumption violations."""
        orchestrator = AdaptiveReplanningOrchestrator()

        failure = orchestrator.detect_failure(
            step_id=3,
            expected_duration=timedelta(minutes=10),
            actual_duration=timedelta(minutes=10),
            errors_count=0,
            assumptions_violated=["database available", "network stable"],
        )

        assert failure is not None
        assert failure.failure_type == FailureType.ASSUMPTION_VIOLATED
        assert "2 assumptions violated" in failure.message

    def test_severity_scales_with_error_count(self):
        """Test that severity increases with error count."""
        orchestrator = AdaptiveReplanningOrchestrator()

        failure_3_errors = orchestrator.detect_failure(
            step_id=1,
            expected_duration=timedelta(minutes=10),
            actual_duration=timedelta(minutes=10),
            errors_count=3,
        )

        failure_7_errors = orchestrator.detect_failure(
            step_id=2,
            expected_duration=timedelta(minutes=10),
            actual_duration=timedelta(minutes=10),
            errors_count=7,
        )

        # More errors should have higher severity
        assert failure_7_errors.severity > failure_3_errors.severity

    def test_multiple_failures_tracked(self):
        """Test that multiple failures are tracked."""
        orchestrator = AdaptiveReplanningOrchestrator()

        for i in range(3):
            orchestrator.detect_failure(
                step_id=i,
                expected_duration=timedelta(minutes=10),
                actual_duration=timedelta(minutes=20),
                errors_count=0,
            )

        assert len(orchestrator.failures) == 3


class TestRecoveryPlanning:
    """Test recovery planning from failures."""

    def test_critical_failure_triggers_full_replan(self):
        """Test that critical failures trigger full replanning."""
        orchestrator = AdaptiveReplanningOrchestrator()

        failure = PlanFailure(
            failure_type=FailureType.TIMING_OVERRUN,
            step_id=1,
            timestamp=datetime.now(),
            severity=0.9,  # Critical
            message="Critical overrun",
        )

        action = orchestrator.plan_recovery(
            failure=failure,
            current_plan={"id": "test_plan", "steps": [1, 2, 3]},
            remaining_steps=[2, 3],
        )

        assert action.recovery_level == RecoveryLevel.FULL_REPLAN
        assert action.risk_level == "high"
        assert action.success_probability < 0.8

    def test_medium_failure_triggers_segment_replan(self):
        """Test that medium failures trigger segment replanning."""
        orchestrator = AdaptiveReplanningOrchestrator()

        failure = PlanFailure(
            failure_type=FailureType.TIMING_OVERRUN,
            step_id=1,
            timestamp=datetime.now(),
            severity=0.6,  # Medium
            message="Moderate overrun",
        )

        action = orchestrator.plan_recovery(
            failure=failure,
            current_plan={"id": "test_plan", "steps": [1, 2, 3]},
            remaining_steps=[2, 3],
        )

        assert action.recovery_level == RecoveryLevel.SEGMENT_REPLAN
        assert action.risk_level == "medium"

    def test_low_failure_triggers_local_adjust(self):
        """Test that low failures trigger local adjustment."""
        orchestrator = AdaptiveReplanningOrchestrator()

        failure = PlanFailure(
            failure_type=FailureType.TIMING_OVERRUN,
            step_id=1,
            timestamp=datetime.now(),
            severity=0.35,  # Medium-low (triggers LOCAL_ADJUST at >= 0.3)
            message="Minor overrun",
        )

        action = orchestrator.plan_recovery(
            failure=failure,
            current_plan={"id": "test_plan", "steps": [1, 2, 3]},
            remaining_steps=[2, 3],
        )

        assert action.recovery_level == RecoveryLevel.LOCAL_ADJUST
        assert action.risk_level == "low"
        assert action.success_probability > 0.8

    def test_recovery_action_has_estimated_time(self):
        """Test that recovery actions have time estimates."""
        orchestrator = AdaptiveReplanningOrchestrator()

        failure = PlanFailure(
            failure_type=FailureType.TIMING_OVERRUN,
            step_id=1,
            timestamp=datetime.now(),
            severity=0.5,
            message="Overrun",
        )

        action = orchestrator.plan_recovery(
            failure=failure,
            current_plan={"id": "test_plan"},
            remaining_steps=[2, 3],
        )

        # Recovery time should be > 0 for segment replan
        assert action.estimated_time_recovery > timedelta(0)

    def test_recovery_affects_remaining_steps(self):
        """Test that recovery action tracks affected steps."""
        orchestrator = AdaptiveReplanningOrchestrator()

        failure = PlanFailure(
            failure_type=FailureType.TIMING_OVERRUN,
            step_id=1,
            timestamp=datetime.now(),
            severity=0.5,
            message="Overrun",
        )

        remaining = [2, 3, 4, 5]
        action = orchestrator.plan_recovery(
            failure=failure,
            current_plan={"id": "test_plan"},
            remaining_steps=remaining,
        )

        assert action.steps_affected == remaining


class TestPlanRefinement:
    """Test plan refinement based on execution feedback."""

    def test_refine_plan_adjusts_duration(self):
        """Test that plan refinement adjusts step durations."""
        orchestrator = AdaptiveReplanningOrchestrator()

        metrics = [
            ExecutionMetrics(
                step_id=1,
                expected_duration=timedelta(minutes=10),
                actual_duration=timedelta(minutes=15),  # 1.5x overrun
                errors_count=0,
                resource_constraints_hit=False,
            ),
        ]

        refined = orchestrator.refine_plan(
            original_plan={"id": "plan1", "steps": [1, 2, 3]},
            execution_metrics=metrics,
        )

        # Should have at least one change for duration adjustment
        duration_changes = [c for c in refined.changes if c["adjustment"] == "duration_increase"]
        assert len(duration_changes) > 0

    def test_refine_plan_adds_error_handling(self):
        """Test that plan refinement adds error handling for low quality steps."""
        orchestrator = AdaptiveReplanningOrchestrator()

        metrics = [
            ExecutionMetrics(
                step_id=2,
                expected_duration=timedelta(minutes=10),
                actual_duration=timedelta(minutes=10),
                errors_count=5,  # Low quality
                resource_constraints_hit=False,
                quality_score=0.5,  # Low
            ),
        ]

        refined = orchestrator.refine_plan(
            original_plan={"id": "plan1"},
            execution_metrics=metrics,
        )

        error_changes = [c for c in refined.changes if c["adjustment"] == "add_error_handling"]
        assert len(error_changes) > 0

    def test_refine_plan_adds_preconditions(self):
        """Test that plan refinement adds preconditions for violated assumptions."""
        orchestrator = AdaptiveReplanningOrchestrator()

        metrics = [
            ExecutionMetrics(
                step_id=3,
                expected_duration=timedelta(minutes=10),
                actual_duration=timedelta(minutes=10),
                errors_count=0,
                resource_constraints_hit=False,
                assumptions_violated=["database_available", "network_stable"],
            ),
        ]

        refined = orchestrator.refine_plan(
            original_plan={"id": "plan1"},
            execution_metrics=metrics,
        )

        precond_changes = [c for c in refined.changes if c["adjustment"] == "add_preconditions"]
        assert len(precond_changes) > 0

    def test_refine_plan_calculates_confidence(self):
        """Test that refinement confidence based on observation count."""
        orchestrator = AdaptiveReplanningOrchestrator()

        # With few observations
        refined_few = orchestrator.refine_plan(
            original_plan={"id": "plan1"},
            execution_metrics=[
                ExecutionMetrics(
                    step_id=i,
                    expected_duration=timedelta(minutes=10),
                    actual_duration=timedelta(minutes=10),
                    errors_count=0,
                    resource_constraints_hit=False,
                )
                for i in range(1)
            ],
        )

        # With many observations
        refined_many = orchestrator.refine_plan(
            original_plan={"id": "plan1"},
            execution_metrics=[
                ExecutionMetrics(
                    step_id=i,
                    expected_duration=timedelta(minutes=10),
                    actual_duration=timedelta(minutes=10),
                    errors_count=0,
                    resource_constraints_hit=False,
                )
                for i in range(20)
            ],
        )

        # More observations should have higher confidence
        assert refined_many.confidence > refined_few.confidence

    def test_refine_plan_estimates_time_saved(self):
        """Test that refinement estimates time saved."""
        orchestrator = AdaptiveReplanningOrchestrator()

        metrics = [
            ExecutionMetrics(
                step_id=1,
                expected_duration=timedelta(minutes=30),
                actual_duration=timedelta(minutes=20),  # Faster than expected
                errors_count=0,
                resource_constraints_hit=False,
            ),
        ]

        refined = orchestrator.refine_plan(
            original_plan={"id": "plan1"},
            execution_metrics=metrics,
        )

        # Should show time savings
        assert refined.estimated_time_saved == timedelta(minutes=10)


class TestStatistics:
    """Test statistics collection and reporting."""

    def test_get_recovery_stats_empty(self):
        """Test statistics with no failures."""
        orchestrator = AdaptiveReplanningOrchestrator()

        stats = orchestrator.get_recovery_stats()

        assert stats["total_failures"] == 0
        assert stats["recoveries_attempted"] == 0

    def test_get_recovery_stats_with_failures(self):
        """Test statistics collection with multiple failures."""
        orchestrator = AdaptiveReplanningOrchestrator()

        # Create multiple failures
        for i in range(5):
            orchestrator.detect_failure(
                step_id=i,
                expected_duration=timedelta(minutes=10),
                actual_duration=timedelta(minutes=20),
                errors_count=0,
            )

        # Plan recovery for each
        for failure in orchestrator.failures:
            orchestrator.plan_recovery(
                failure=failure,
                current_plan={"id": "test_plan"},
                remaining_steps=[],
            )

        stats = orchestrator.get_recovery_stats()

        assert stats["total_failures"] == 5
        assert stats["recoveries_attempted"] == 5
        assert "failure_types" in stats
        assert "recovery_levels" in stats

    def test_average_severity_calculation(self):
        """Test average severity is calculated correctly."""
        orchestrator = AdaptiveReplanningOrchestrator()

        # Create failures with different severities
        severities = [0.2, 0.5, 0.8]
        for i, sev in enumerate(severities):
            failure = PlanFailure(
                failure_type=FailureType.TIMING_OVERRUN,
                step_id=i,
                timestamp=datetime.now(),
                severity=sev,
                message="Test",
            )
            orchestrator.failures.append(failure)

        stats = orchestrator.get_recovery_stats()

        expected_avg = sum(severities) / len(severities)
        assert abs(stats["average_failure_severity"] - expected_avg) < 0.01

    def test_recovery_success_probability_tracking(self):
        """Test tracking of recovery success probabilities."""
        orchestrator = AdaptiveReplanningOrchestrator()

        # Create recovery actions with different success probabilities
        probs = [0.6, 0.8, 0.95]
        for i, prob in enumerate(probs):
            action = RecoveryAction(
                action_id=f"recovery_{i}",
                recovery_level=RecoveryLevel.FULL_REPLAN,
                description="Test recovery",
                steps_affected=[],
                estimated_time_recovery=timedelta(hours=1),
                risk_level="high",
                success_probability=prob,
            )
            orchestrator.recovery_actions.append(action)

        stats = orchestrator.get_recovery_stats()

        expected_avg = sum(probs) / len(probs)
        assert abs(stats.get("average_recovery_success_probability", 0) - expected_avg) < 0.01


class TestExecutionMetricsTracking:
    """Test tracking of execution metrics."""

    def test_execution_metrics_recorded(self):
        """Test that execution metrics are recorded even without failure."""
        orchestrator = AdaptiveReplanningOrchestrator()

        orchestrator.detect_failure(
            step_id=1,
            expected_duration=timedelta(minutes=10),
            actual_duration=timedelta(minutes=11),
            errors_count=1,
        )

        assert len(orchestrator.execution_history) == 1
        assert orchestrator.execution_history[0].step_id == 1
        assert orchestrator.execution_history[0].errors_count == 1

    def test_quality_score_from_errors(self):
        """Test that quality score is calculated from errors."""
        orchestrator = AdaptiveReplanningOrchestrator()

        orchestrator.detect_failure(
            step_id=1,
            expected_duration=timedelta(minutes=10),
            actual_duration=timedelta(minutes=10),
            errors_count=5,
        )

        metric = orchestrator.execution_history[0]
        # Quality = max(0, 1 - (5/10)) = 0.5
        assert metric.quality_score == 0.5

    def test_multiple_metrics_cumulative(self):
        """Test that multiple metrics are tracked cumulatively."""
        orchestrator = AdaptiveReplanningOrchestrator()

        for i in range(3):
            orchestrator.detect_failure(
                step_id=i,
                expected_duration=timedelta(minutes=10),
                actual_duration=timedelta(minutes=10),
                errors_count=i,
            )

        assert len(orchestrator.execution_history) == 3
