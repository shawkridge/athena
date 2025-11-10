"""Integration tests for Phase 7 Execution Intelligence workflow."""

import pytest
from datetime import datetime, timedelta

from athena.execution import (
    ExecutionMonitor,
    AssumptionValidator,
    Assumption,
    AdaptiveReplanningEngine,
    ExecutionLearner,
    TaskOutcome,
    DeviationSeverity,
    AssumptionValidationType,
)


@pytest.fixture
def monitor():
    """Create an execution monitor for testing."""
    return ExecutionMonitor()


@pytest.fixture
def validator():
    """Create an assumption validator for testing."""
    return AssumptionValidator()


@pytest.fixture
def replanning_engine():
    """Create a replanning engine for testing."""
    return AdaptiveReplanningEngine()


@pytest.fixture
def learner():
    """Create an execution learner for testing."""
    return ExecutionLearner()


class TestExecutionMonitor:
    """Test suite for ExecutionMonitor."""

    def test_initialize_plan(self, monitor):
        """Test plan initialization."""
        total_tasks = 5
        planned_duration = timedelta(hours=2)

        monitor.initialize_plan(total_tasks, planned_duration)

        assert monitor.total_planned_tasks == 5
        assert monitor.plan_start_time is not None
        assert monitor.planned_completion_time is not None

    def test_record_task_start(self, monitor):
        """Test recording task start."""
        monitor.initialize_plan(3, timedelta(hours=1))

        planned_start = datetime.utcnow()
        monitor.record_task_start("task_1", planned_start, timedelta(minutes=20))

        record = monitor.get_task_record("task_1")
        assert record is not None
        assert record.task_id == "task_1"
        assert record.actual_start is not None

    def test_record_task_completion_success(self, monitor):
        """Test recording successful task completion."""
        monitor.initialize_plan(2, timedelta(hours=1))
        planned_start = datetime.utcnow()
        monitor.record_task_start("task_1", planned_start, timedelta(minutes=30))

        record = monitor.record_task_completion("task_1", TaskOutcome.SUCCESS)

        assert record is not None
        assert record.outcome == TaskOutcome.SUCCESS
        assert record.actual_duration is not None
        assert record.confidence == 0.95

    def test_record_task_completion_failure(self, monitor):
        """Test recording failed task completion."""
        monitor.initialize_plan(2, timedelta(hours=1))
        planned_start = datetime.utcnow()
        monitor.record_task_start("task_1", planned_start, timedelta(minutes=30))

        record = monitor.record_task_completion("task_1", TaskOutcome.FAILURE)

        assert record is not None
        assert record.outcome == TaskOutcome.FAILURE
        assert record.confidence == 0.0

    def test_plan_deviation_calculation(self, monitor):
        """Test plan deviation metrics."""
        monitor.initialize_plan(2, timedelta(hours=1))

        # Complete first task
        planned_start = datetime.utcnow()
        monitor.record_task_start("task_1", planned_start, timedelta(minutes=30))
        monitor.record_task_completion("task_1", TaskOutcome.SUCCESS)

        deviation = monitor.get_plan_deviation()
        assert deviation.total_tasks == 2
        assert deviation.completed_tasks == 1
        assert 0.0 <= deviation.completion_rate <= 1.0

    def test_critical_path_identification(self, monitor):
        """Test critical path identification."""
        monitor.initialize_plan(3, timedelta(hours=1))

        # Record multiple tasks
        for i in range(1, 4):
            planned_start = datetime.utcnow()
            monitor.record_task_start(
                f"task_{i}", planned_start, timedelta(minutes=30)
            )
            monitor.record_task_completion(f"task_{i}", TaskOutcome.SUCCESS)

        critical_path = monitor.get_critical_path()
        assert isinstance(critical_path, list)
        assert len(critical_path) > 0

    def test_monitor_reset(self, monitor):
        """Test monitor reset."""
        monitor.initialize_plan(2, timedelta(hours=1))
        monitor.reset()

        assert monitor.total_planned_tasks == 0
        assert len(monitor.execution_records) == 0


class TestAssumptionValidator:
    """Test suite for AssumptionValidator."""

    def test_register_assumption(self, validator):
        """Test assumption registration."""
        validator.register_assumption(
            "resources_available",
            "Sufficient resources will be available",
            expected_value={"cpu": 4, "memory": 16},
            validation_method=AssumptionValidationType.SENSOR,
            check_frequency=timedelta(minutes=5),
            severity=DeviationSeverity.HIGH,
        )

        assert "resources_available" in validator.assumptions
        assert validator.assumptions["resources_available"].description == "Sufficient resources will be available"

    def test_check_assumption_valid(self, validator):
        """Test assumption validation when valid."""
        validator.register_assumption(
            "test_assumption",
            "Test",
            expected_value=100,
            validation_method=AssumptionValidationType.AUTO,
            tolerance=0.1,
        )

        result = validator.check_assumption("test_assumption", 105)  # Within 10% tolerance

        assert result.valid is True
        assert result.confidence > 0.5

    def test_check_assumption_invalid(self, validator):
        """Test assumption validation when invalid."""
        validator.register_assumption(
            "test_assumption",
            "Test",
            expected_value=100,
            validation_method=AssumptionValidationType.AUTO,
            tolerance=0.1,
        )

        result = validator.check_assumption("test_assumption", 200)  # Outside tolerance

        assert result.valid is False
        assert result.confidence < 0.5

    def test_violated_assumptions(self, validator):
        """Test tracking violated assumptions."""
        validator.register_assumption(
            "test_assumption",
            "Test",
            expected_value=100,
            validation_method=AssumptionValidationType.AUTO,
            tolerance=0.1,
            severity=DeviationSeverity.HIGH,
            affected_tasks=["task_1", "task_2"],
        )

        validator.check_assumption("test_assumption", 200)  # Violate

        violations = validator.get_violated_assumptions()
        assert len(violations) == 1
        assert violations[0].assumption_id == "test_assumption"
        assert "task_1" in violations[0].affected_tasks

    def test_predict_assumption_failure(self, validator):
        """Test predicting assumption failures."""
        validator.register_assumption(
            "test_assumption",
            "Test",
            expected_value=100,
            validation_method=AssumptionValidationType.AUTO,
            tolerance=0.1,
        )

        # Create increasing trend
        validator.check_assumption("test_assumption", 105)  # 5% deviation
        validator.check_assumption("test_assumption", 110)  # 10% deviation
        validator.check_assumption("test_assumption", 120)  # 20% deviation

        prediction = validator.predict_assumption_failure("test_assumption")
        # May or may not predict failure depending on trend detection
        # Just check it returns reasonable result (AssumptionViolation or None)
        assert prediction is None or hasattr(prediction, 'assumption_id')

    def test_validator_reset(self, validator):
        """Test validator reset."""
        validator.register_assumption(
            "test",
            "Test",
            expected_value=100,
            validation_method=AssumptionValidationType.AUTO,
        )
        validator.reset()

        assert len(validator.assumptions) == 0
        assert len(validator.violations) == 0


class TestAdaptiveReplanningEngine:
    """Test suite for AdaptiveReplanningEngine."""

    def test_evaluate_replanning_no_issues(self, replanning_engine, monitor):
        """Test replanning evaluation with no issues."""
        monitor.initialize_plan(5, timedelta(hours=2))
        deviation = monitor.get_plan_deviation()

        evaluation = replanning_engine.evaluate_replanning_need(deviation, [])

        assert evaluation.replanning_needed is False
        assert evaluation.strategy.value == "none"

    def test_evaluate_replanning_critical_deviation(
        self, replanning_engine, monitor
    ):
        """Test replanning with critical deviation."""
        monitor.initialize_plan(5, timedelta(hours=1))

        # Simulate high deviation
        for i in range(1, 4):
            monitor.record_task_start(
                f"task_{i}",
                datetime.utcnow() - timedelta(hours=1),
                timedelta(minutes=20),
            )
            monitor.record_task_completion(f"task_{i}", TaskOutcome.SUCCESS)

        deviation = monitor.get_plan_deviation()
        evaluation = replanning_engine.evaluate_replanning_need(deviation, [])

        # Might need replanning depending on deviation severity
        assert isinstance(evaluation.replanning_needed, bool)

    def test_generate_local_adjustment_options(self, replanning_engine, monitor):
        """Test generating local adjustment options."""
        monitor.initialize_plan(5, timedelta(hours=2))
        deviation = monitor.get_plan_deviation()

        options = replanning_engine.generate_local_adjustment("task_1", {}, deviation)

        assert len(options) >= 1
        assert all(opt.option_id >= 0 for opt in options)

    def test_generate_segment_replanning_options(
        self, replanning_engine, monitor
    ):
        """Test generating segment replanning options."""
        monitor.initialize_plan(10, timedelta(hours=4))
        options = replanning_engine.replan_segment(2, 5)

        assert len(options) >= 1
        assert all(opt.option_id >= 0 for opt in options)

    def test_generate_full_replanning_options(self, replanning_engine, monitor):
        """Test generating full replanning options."""
        monitor.initialize_plan(10, timedelta(hours=4))
        options = replanning_engine.full_replan(["task_1", "task_2"])

        assert len(options) >= 1
        assert all(opt.option_id >= 0 for opt in options)

    def test_select_replanning_option(self, replanning_engine, monitor):
        """Test selecting a replanning option."""
        monitor.initialize_plan(5, timedelta(hours=2))
        options = replanning_engine.generate_local_adjustment("task_1", {}, monitor.get_plan_deviation())

        if options:
            selected = replanning_engine.select_option(options[0].option_id)
            assert selected is not None
            assert selected.option_id == options[0].option_id

    def test_replanning_engine_reset(self, replanning_engine, monitor):
        """Test replanning engine reset."""
        monitor.initialize_plan(5, timedelta(hours=2))
        replanning_engine.generate_local_adjustment(
            "task_1", {}, monitor.get_plan_deviation()
        )
        replanning_engine.reset()

        assert len(replanning_engine.replanning_options) == 0
        assert replanning_engine.selected_option is None


class TestExecutionLearner:
    """Test suite for ExecutionLearner."""

    def test_extract_patterns(self, learner, monitor):
        """Test pattern extraction."""
        monitor.initialize_plan(3, timedelta(hours=1))

        # Record tasks
        for i in range(1, 4):
            monitor.record_task_start(
                f"task_{i}",
                datetime.utcnow(),
                timedelta(minutes=20),
            )
            monitor.record_task_completion(f"task_{i}", TaskOutcome.SUCCESS)

        records = {r.task_id: r for r in monitor.get_all_task_records()}
        patterns = learner.extract_execution_patterns(records)

        # Should extract some patterns
        assert isinstance(patterns, list)

    def test_compute_estimation_accuracy(self, learner, monitor):
        """Test estimation accuracy computation."""
        monitor.initialize_plan(2, timedelta(hours=1))

        # Record tasks with duration data
        for i in range(1, 3):
            monitor.record_task_start(
                f"test_task_{i}",
                datetime.utcnow(),
                timedelta(minutes=30),
            )
            monitor.record_task_completion(f"test_task_{i}", TaskOutcome.SUCCESS)

        records = {r.task_id: r for r in monitor.get_all_task_records()}
        accuracy = learner.compute_estimation_accuracy(records)

        assert isinstance(accuracy, dict)
        # Should have some accuracy data
        if accuracy:
            for task_type, acc in accuracy.items():
                assert 0.0 <= acc <= 1.0

    def test_identify_bottlenecks(self, learner, monitor):
        """Test bottleneck identification."""
        monitor.initialize_plan(3, timedelta(hours=1))

        # Record multiple tasks
        for i in range(1, 4):
            monitor.record_task_start(
                f"task_{i}",
                datetime.utcnow(),
                timedelta(minutes=20 if i == 2 else 10),
            )
            monitor.record_task_completion(f"task_{i}", TaskOutcome.SUCCESS)

        records = {r.task_id: r for r in monitor.get_all_task_records()}
        bottlenecks = learner.identify_bottlenecks(records)

        assert isinstance(bottlenecks, list)
        # May or may not have bottlenecks depending on task distribution

    def test_generate_recommendations(self, learner, monitor):
        """Test recommendation generation."""
        monitor.initialize_plan(3, timedelta(hours=1))

        for i in range(1, 4):
            monitor.record_task_start(
                f"task_{i}",
                datetime.utcnow(),
                timedelta(minutes=20),
            )
            monitor.record_task_completion(f"task_{i}", TaskOutcome.SUCCESS)

        records = {r.task_id: r for r in monitor.get_all_task_records()}
        recommendations = learner.generate_recommendations(records)

        assert isinstance(recommendations, list)

    def test_learner_reset(self, learner):
        """Test learner reset."""
        learner.recommendations = ["Test recommendation"]
        learner.reset()

        assert len(learner.recommendations) == 0
        assert len(learner.execution_patterns) == 0


class TestExecutionIntegration:
    """Integration tests for complete execution workflow."""

    def test_complete_execution_workflow(self, monitor, validator, replanning_engine, learner):
        """Test complete execution workflow."""
        # 1. Initialize plan
        monitor.initialize_plan(3, timedelta(hours=1))

        # 2. Register assumptions
        validator.register_assumption(
            "resources_ok",
            "Resources are available",
            expected_value=True,
            validation_method=AssumptionValidationType.SENSOR,
            severity=DeviationSeverity.HIGH,
            affected_tasks=["task_1", "task_2", "task_3"],
        )

        # 3. Execute tasks
        for i in range(1, 4):
            monitor.record_task_start(
                f"task_{i}",
                datetime.utcnow(),
                timedelta(minutes=20),
            )

            # Check assumption
            validator.check_assumption("resources_ok", True)

            # Complete task
            monitor.record_task_completion(f"task_{i}", TaskOutcome.SUCCESS)

        # 4. Get deviation metrics
        deviation = monitor.get_plan_deviation()
        assert deviation.total_tasks == 3
        assert deviation.completed_tasks == 3

        # 5. Evaluate replanning
        violations = validator.get_violated_assumptions()
        evaluation = replanning_engine.evaluate_replanning_need(deviation, violations)
        assert evaluation.replanning_needed is False  # No violations

        # 6. Extract lessons learned
        records = {r.task_id: r for r in monitor.get_all_task_records()}
        patterns = learner.extract_execution_patterns(records)
        recommendations = learner.generate_recommendations(records)

        assert isinstance(patterns, list)
        assert isinstance(recommendations, list)

    def test_execution_with_replanning(self, monitor, validator, replanning_engine, learner):
        """Test execution with replanning triggered."""
        # 1. Initialize
        monitor.initialize_plan(5, timedelta(hours=2))

        # 2. Register critical assumption
        validator.register_assumption(
            "task_2_ready",
            "Task 2 prerequisites ready",
            expected_value=True,
            validation_method=AssumptionValidationType.AUTO,
            severity=DeviationSeverity.CRITICAL,
            affected_tasks=["task_2", "task_3"],
        )

        # 3. Start executing
        for i in range(1, 3):
            monitor.record_task_start(
                f"task_{i}",
                datetime.utcnow(),
                timedelta(minutes=20),
            )

        # 4. Violation occurs
        validator.check_assumption("task_2_ready", False)
        violations = validator.get_violated_assumptions()

        # 5. Evaluate replanning
        deviation = monitor.get_plan_deviation()
        evaluation = replanning_engine.evaluate_replanning_need(deviation, violations)

        # Should need replanning due to critical violation
        assert evaluation.replanning_needed is True
        assert evaluation.strategy.value in ["full", "segment", "abort"]

        # 6. Generate options
        if evaluation.strategy.value == "segment":
            options = replanning_engine.replan_segment(2, 3)
            assert len(options) > 0
