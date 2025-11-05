"""
Comprehensive tests for Phase 4 Integration Orchestrator.

Tests workflow management, error handling, circuit breaker, and orchestration.
"""

import pytest
from datetime import datetime

from athena.agents.orchestrator_models import (
    TaskWorkflow,
    WorkflowStep,
    WorkflowPhase,
    AgentHealthStatus,
    SystemMetrics,
    ErrorRecord,
    OrchestratorConfig,
)
from athena.agents.workflow_manager import WorkflowManager
from athena.agents.error_handler import ErrorHandler, CircuitBreaker


# ============================================================================
# Test Models
# ============================================================================


class TestWorkflowStep:
    """Test WorkflowStep model."""

    def test_workflow_step_creation(self):
        """Test creating a workflow step."""
        step = WorkflowStep(
            step_id="step-1",
            agent_type="planner",
            action="create_plan",
        )
        assert step.step_id == "step-1"
        assert step.agent_type == "planner"
        assert step.status == WorkflowPhase.PENDING

    def test_workflow_step_to_dict(self):
        """Test converting step to dict."""
        step = WorkflowStep(
            step_id="step-1",
            agent_type="executor",
            action="execute",
            execution_time_ms=100.5,
        )
        d = step.to_dict()
        assert d["step_id"] == "step-1"
        assert d["execution_time_ms"] == 100.5


class TestTaskWorkflow:
    """Test TaskWorkflow model."""

    def test_workflow_creation(self):
        """Test creating a task workflow."""
        workflow = TaskWorkflow(
            workflow_id="wf-1",
            task_id=1,
            task_type="compute",
            priority=7,
        )
        assert workflow.task_id == 1
        assert workflow.priority == 7
        assert workflow.overall_status == "pending"

    def test_workflow_to_dict(self):
        """Test converting workflow to dict."""
        workflow = TaskWorkflow(
            workflow_id="wf-2",
            task_id=2,
            task_type="io",
            completion_percentage=50.0,
        )
        d = workflow.to_dict()
        assert d["task_id"] == 2
        assert d["completion_percentage"] == 50.0


class TestSystemMetrics:
    """Test SystemMetrics model."""

    def test_metrics_creation(self):
        """Test creating system metrics."""
        metrics = SystemMetrics(
            total_tasks=10,
            completed_tasks=7,
            active_agents=5,
        )
        assert metrics.total_tasks == 10
        assert metrics.completed_tasks == 7
        assert metrics.active_agents == 5


# ============================================================================
# Test Workflow Manager
# ============================================================================


class TestWorkflowManager:
    """Test WorkflowManager."""

    def test_create_workflow(self):
        """Test creating a workflow."""
        manager = WorkflowManager()
        workflow = manager.create_workflow(task_id=1, task_type="compute")
        assert workflow.task_id == 1
        assert workflow.workflow_id in manager.workflows

    def test_add_step(self):
        """Test adding a step to workflow."""
        manager = WorkflowManager()
        workflow = manager.create_workflow(task_id=1, task_type="test")
        step = manager.add_step(workflow.workflow_id, "planner", "create_plan")
        assert step.agent_type == "planner"
        assert len(workflow.steps) == 1

    def test_step_dependencies(self):
        """Test step dependency tracking."""
        manager = WorkflowManager()
        workflow = manager.create_workflow(task_id=1, task_type="test")
        step1 = manager.add_step(workflow.workflow_id, "planner", "create_plan")
        step2 = manager.add_step(
            workflow.workflow_id,
            "executor",
            "execute",
            dependencies=[step1.step_id],
        )
        assert step1.step_id in step2.dependencies

    def test_get_next_executable_step(self):
        """Test getting next executable step."""
        manager = WorkflowManager()
        workflow = manager.create_workflow(task_id=1, task_type="test")
        step1 = manager.add_step(workflow.workflow_id, "planner", "plan")
        step2 = manager.add_step(
            workflow.workflow_id, "executor", "execute", dependencies=[step1.step_id]
        )

        # First step should be executable
        next_step = manager.get_next_executable_step(workflow.workflow_id)
        assert next_step.step_id == step1.step_id

        # Mark first step complete
        manager.mark_step_completed(step1.step_id, {})

        # Second step should now be executable
        next_step = manager.get_next_executable_step(workflow.workflow_id)
        assert next_step.step_id == step2.step_id

    def test_mark_step_completed(self):
        """Test marking a step as completed."""
        manager = WorkflowManager()
        workflow = manager.create_workflow(task_id=1, task_type="test")
        step = manager.add_step(workflow.workflow_id, "planner", "plan")

        manager.mark_step_completed(step.step_id, {"result": "success"})
        assert step.status == WorkflowPhase.COMPLETE
        assert step.step_id in manager.completed_steps

    def test_mark_step_failed_with_retry(self):
        """Test marking a step as failed with retry."""
        manager = WorkflowManager()
        workflow = manager.create_workflow(task_id=1, task_type="test")
        step = manager.add_step(workflow.workflow_id, "executor", "execute")

        # First failure - should retry
        manager.mark_step_failed(step.step_id, "Timeout")
        assert step.retry_count == 1
        assert step.status == WorkflowPhase.PENDING

        # Fail max retries times
        for _ in range(step.max_retries):
            manager.mark_step_failed(step.step_id, "Timeout")

        # Should give up after max retries
        assert step.status == WorkflowPhase.FAILED

    def test_workflow_progress_tracking(self):
        """Test tracking overall workflow progress."""
        manager = WorkflowManager()
        workflow = manager.create_workflow(task_id=1, task_type="test")
        step1 = manager.add_step(workflow.workflow_id, "planner", "plan")
        step2 = manager.add_step(workflow.workflow_id, "executor", "execute")

        # Initially 0% complete
        assert workflow.completion_percentage == 0.0

        # Mark first step complete
        manager.mark_step_completed(step1.step_id, {})
        manager.update_workflow_progress(workflow.workflow_id)
        assert workflow.completion_percentage == 50.0

        # Mark second step complete
        manager.mark_step_completed(step2.step_id, {})
        manager.update_workflow_progress(workflow.workflow_id)
        assert workflow.completion_percentage == 100.0
        assert workflow.overall_status == "success"

    def test_deadlock_detection(self):
        """Test deadlock detection."""
        manager = WorkflowManager()
        workflow = manager.create_workflow(task_id=1, task_type="test")
        step1 = manager.add_step(workflow.workflow_id, "planner", "plan")
        step2 = manager.add_step(
            workflow.workflow_id, "executor", "execute", dependencies=[step1.step_id]
        )

        # Manually set step1 to FAILED (simulate exhausted retries)
        step1.status = WorkflowPhase.FAILED
        step1.max_retries = 0
        manager.failed_steps.add(step1.step_id)

        # Now step1 is in FAILED state
        manager.update_workflow_progress(workflow.workflow_id)

        # Should detect deadlock (step2 depends on failed step1)
        is_deadlock = manager.detect_deadlock(workflow.workflow_id)
        # Deadlock is detected when a dependency is failed
        assert is_deadlock

    def test_critical_path(self):
        """Test critical path detection."""
        manager = WorkflowManager()
        workflow = manager.create_workflow(task_id=1, task_type="test")
        step1 = manager.add_step(workflow.workflow_id, "planner", "plan")
        step1.execution_time_ms = 100.0
        step2 = manager.add_step(
            workflow.workflow_id,
            "executor",
            "execute",
            dependencies=[step1.step_id],
        )
        step2.execution_time_ms = 200.0

        path = manager.get_critical_path(workflow.workflow_id)
        assert len(path) > 0


# ============================================================================
# Test Error Handler
# ============================================================================


class TestCircuitBreaker:
    """Test CircuitBreaker."""

    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""
        cb = CircuitBreaker(failure_threshold=3)
        assert cb.state == "closed"
        assert cb.can_attempt()

    def test_circuit_breaker_failure_threshold(self):
        """Test circuit breaker failure threshold."""
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        assert cb.state == "closed"
        cb.record_failure()
        assert cb.state == "open"
        assert not cb.can_attempt()

    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout."""
        import time

        cb = CircuitBreaker(failure_threshold=1, timeout_seconds=1)
        cb.record_failure()
        assert cb.state == "open"

        # Too soon to recover
        assert not cb.can_attempt()

        # Wait for timeout
        time.sleep(1.1)
        assert cb.can_attempt()
        assert cb.state == "half_open"

    def test_circuit_breaker_success_reset(self):
        """Test circuit breaker resets on success."""
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()
        assert cb.state == "open"
        cb.record_success()
        assert cb.state == "closed"


class TestErrorHandler:
    """Test ErrorHandler."""

    def test_record_error(self):
        """Test recording an error."""
        handler = ErrorHandler()
        error = handler.record_error(
            workflow_id="wf-1",
            step_id="step-1",
            agent_type="executor",
            error_type="timeout",
            error_message="Operation timeout",
        )
        assert error.error_id in handler.error_records
        assert error.is_recoverable

    def test_error_classification(self):
        """Test error classification for recoverability."""
        handler = ErrorHandler()

        # Recoverable error
        error1 = handler.record_error(
            "wf-1", "step-1", "executor", "timeout", "msg", severity="high"
        )
        assert error1.is_recoverable

        # Non-recoverable error
        error2 = handler.record_error(
            "wf-2", "step-2", "planner", "error", "msg", severity="critical"
        )
        assert not error2.is_recoverable

    def test_recovery_attempt(self):
        """Test attempting error recovery."""
        handler = ErrorHandler()
        error = handler.record_error(
            "wf-1", "step-1", "executor", "timeout", "msg"
        )
        result = handler.attempt_recovery(error.error_id)
        assert result["success"]
        assert "action" in result

    def test_error_statistics(self):
        """Test error statistics collection."""
        handler = ErrorHandler()
        handler.record_error("wf-1", "step-1", "executor", "timeout", "msg")
        handler.record_error("wf-2", "step-2", "planner", "resource_exhausted", "msg")

        stats = handler.get_error_statistics()
        assert stats["total_errors"] == 2
        assert "timeout" in stats["by_type"]
        assert "resource_exhausted" in stats["by_type"]

    def test_circuit_breaker_integration(self):
        """Test circuit breaker integration."""
        handler = ErrorHandler()
        handler.record_error("wf-1", "step-1", "executor", "timeout", "msg")
        handler.record_error("wf-2", "step-2", "executor", "timeout", "msg")

        cb_status = handler.get_circuit_breaker_status("executor")
        assert cb_status["failure_count"] > 0


# ============================================================================
# Integration Tests
# ============================================================================


class TestWorkflowIntegration:
    """Integration tests for workflow management."""

    def test_complete_workflow_execution(self):
        """Test executing a complete workflow."""
        manager = WorkflowManager()
        workflow = manager.create_workflow(task_id=1, task_type="compute")

        # Create workflow steps
        plan_step = manager.add_step(workflow.workflow_id, "planner", "plan")
        predict_step = manager.add_step(
            workflow.workflow_id,
            "predictor",
            "predict",
            dependencies=[plan_step.step_id],
        )
        exec_step = manager.add_step(
            workflow.workflow_id,
            "executor",
            "execute",
            dependencies=[predict_step.step_id],
        )

        # Simulate execution
        manager.mark_step_started(plan_step.step_id)
        manager.mark_step_completed(plan_step.step_id, {"plan": "done"}, 100.0)
        manager.update_workflow_progress(workflow.workflow_id)

        manager.mark_step_started(predict_step.step_id)
        manager.mark_step_completed(predict_step.step_id, {"prediction": "ok"}, 50.0)
        manager.update_workflow_progress(workflow.workflow_id)

        manager.mark_step_started(exec_step.step_id)
        manager.mark_step_completed(exec_step.step_id, {"result": "success"}, 150.0)
        manager.update_workflow_progress(workflow.workflow_id)

        # Verify completion
        assert workflow.overall_status == "success"
        assert workflow.completion_percentage == 100.0

    def test_workflow_with_error_recovery(self):
        """Test workflow with error and recovery."""
        manager = WorkflowManager()
        handler = ErrorHandler()
        workflow = manager.create_workflow(task_id=1, task_type="test")

        step = manager.add_step(workflow.workflow_id, "executor", "execute")

        # Simulate error
        manager.mark_step_failed(step.step_id, "Timeout")

        # Record error
        error = handler.record_error(
            workflow.workflow_id,
            step.step_id,
            "executor",
            "timeout",
            "Operation timeout",
        )

        # Recover
        result = handler.attempt_recovery(error.error_id)
        assert result["success"]

        # Retry step
        manager.mark_step_started(step.step_id)
        manager.mark_step_completed(step.step_id, {"result": "success"})

        assert step.status == WorkflowPhase.COMPLETE


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Performance tests for orchestrator."""

    @pytest.mark.benchmark
    def test_workflow_creation_performance(self, benchmark):
        """Benchmark workflow creation."""
        manager = WorkflowManager()

        def create_workflows():
            for i in range(10):
                manager.create_workflow(task_id=i, task_type="test")

        benchmark(create_workflows)

    @pytest.mark.benchmark
    def test_step_completion_performance(self, benchmark):
        """Benchmark step completion."""
        manager = WorkflowManager()
        workflow = manager.create_workflow(task_id=1, task_type="test")
        steps = [
            manager.add_step(workflow.workflow_id, "agent", f"action_{i}")
            for i in range(5)
        ]

        def mark_steps_complete():
            for step in steps:
                manager.mark_step_completed(step.step_id, {}, 10.0)

        benchmark(mark_steps_complete)

    @pytest.mark.benchmark
    def test_error_handling_performance(self, benchmark):
        """Benchmark error handling."""
        handler = ErrorHandler()

        def record_errors():
            for i in range(10):
                handler.record_error(
                    f"wf-{i}",
                    f"step-{i}",
                    "agent",
                    "timeout",
                    "msg",
                )

        benchmark(record_errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
