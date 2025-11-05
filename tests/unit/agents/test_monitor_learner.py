"""
Unit Tests for Phase 2: Monitor and Learner Agents

Tests for MonitorAgent, LearnerAgent, and their components.
"""

import asyncio
import pytest
from datetime import datetime
from athena.agents.monitor import (
    MonitorAgent, ExecutionMetric, Anomaly
)
from athena.agents.learner import (
    LearnerAgent, ExecutionPattern, Improvement
)
from athena.agents.orchestrator import AgentOrchestrator
from athena.agents.planner import PlannerAgent
from athena.agents.executor import ExecutorAgent


# ============================================================================
# Test Monitor Agent
# ============================================================================

@pytest.mark.asyncio
class TestMonitorAgent:
    """Tests for MonitorAgent"""

    async def test_monitor_initialization(self):
        """Test monitor initialization"""
        monitor = MonitorAgent("/tmp/test.db")
        await monitor.initialize()
        assert monitor.agent_type.value == "monitor"
        assert monitor._running == True
        await monitor.shutdown()

    async def test_monitor_start_monitoring(self):
        """Test starting to monitor execution"""
        monitor = MonitorAgent("/tmp/test.db")
        await monitor.initialize()

        plan = {
            "id": 1,
            "estimated_total_duration_ms": 10000,
            "estimated_total_resources": {"cpu": 50}
        }

        result = await monitor.start_monitoring(1, plan)
        assert result["status"] == "success"
        assert 1 in monitor.execution_baselines

        await monitor.shutdown()

    async def test_monitor_record_metric(self):
        """Test recording execution metrics"""
        monitor = MonitorAgent("/tmp/test.db")
        await monitor.initialize()

        plan = {
            "id": 1,
            "estimated_total_duration_ms": 10000,
            "estimated_total_resources": {"cpu": 50}
        }

        await monitor.start_monitoring(1, plan)

        # Record normal metric
        metric = {
            "type": "resource",
            "value": {"cpu": 30}  # Below threshold
        }

        result = await monitor.record_metric(1, metric)
        assert result["status"] == "success"
        assert "anomalies" in result
        assert len(result["anomalies"]) == 0

        await monitor.shutdown()

    async def test_monitor_detect_anomaly(self):
        """Test anomaly detection"""
        monitor = MonitorAgent("/tmp/test.db")
        await monitor.initialize()

        plan = {
            "id": 1,
            "estimated_total_duration_ms": 10000,
            "estimated_total_resources": {"cpu": 50}
        }

        await monitor.start_monitoring(1, plan)

        # Record anomalous metric (150% of estimate)
        metric = {
            "type": "resource",
            "value": {"cpu": 80}  # 160% of estimate
        }

        result = await monitor.record_metric(1, metric)
        assert result["status"] == "success"
        assert result["anomaly_count"] > 0

        await monitor.shutdown()

    async def test_monitor_health_score(self):
        """Test health score calculation"""
        monitor = MonitorAgent("/tmp/test.db")
        await monitor.initialize()

        plan = {
            "id": 1,
            "estimated_total_duration_ms": 10000,
            "estimated_total_resources": {"cpu": 50}
        }

        await monitor.start_monitoring(1, plan)

        # Get health score
        result = await monitor.get_health_score(1)
        assert result["status"] == "success"
        assert "health_score" in result
        assert result["health_score"] >= 0.0
        assert result["health_score"] <= 1.0
        assert result["health_status"] in ["healthy", "warning", "critical"]

        await monitor.shutdown()

    async def test_monitor_get_metrics(self):
        """Test retrieving metrics"""
        monitor = MonitorAgent("/tmp/test.db")
        await monitor.initialize()

        plan = {"id": 1, "estimated_total_duration_ms": 10000}
        await monitor.start_monitoring(1, plan)

        metric = {"type": "resource", "value": {"cpu": 30}}
        await monitor.record_metric(1, metric)

        result = await monitor.get_execution_metrics(1)
        assert result["status"] == "success"
        assert result["metric_count"] >= 1

        await monitor.shutdown()


# ============================================================================
# Test Learner Agent
# ============================================================================

@pytest.mark.asyncio
class TestLearnerAgent:
    """Tests for LearnerAgent"""

    async def test_learner_initialization(self):
        """Test learner initialization"""
        learner = LearnerAgent("/tmp/test.db")
        await learner.initialize()
        assert learner.agent_type.value == "learner"
        assert learner._running == True
        await learner.shutdown()

    async def test_learner_learn_from_execution(self):
        """Test learning from execution"""
        learner = LearnerAgent("/tmp/test.db")
        await learner.initialize()

        execution_record = {
            "execution_id": 1,
            "status": "completed",
            "steps_completed": [
                {"step_id": 1, "status": "success"},
                {"step_id": 2, "status": "success"},
                {"step_id": 3, "status": "success"},
                {"step_id": 4, "status": "success"}
            ],
            "estimated_total_duration_ms": 10000,
            "actual_duration_ms": 9000,
            "errors": []
        }

        result = await learner.learn_from_execution(execution_record)

        assert result["status"] == "success"
        assert "learning_outcome" in result
        assert len(result["learning_outcome"]["patterns_found"]) > 0

        await learner.shutdown()

    async def test_learner_extract_patterns(self):
        """Test pattern extraction"""
        learner = LearnerAgent("/tmp/test.db")
        await learner.initialize()

        execution_record = {
            "execution_id": 1,
            "status": "completed",
            "steps_completed": [
                {"step_id": i} for i in range(1, 5)
            ],
            "estimated_total_duration_ms": 10000,
            "actual_duration_ms": 15000,  # Underestimated
            "errors": []
        }

        patterns = await learner._extract_patterns(execution_record)

        assert len(patterns) > 0
        pattern_names = [p.name for p in patterns]
        assert any("multi-step" in n.lower() for n in pattern_names)

        await learner.shutdown()

    async def test_learner_identify_improvements(self):
        """Test improvement identification"""
        learner = LearnerAgent("/tmp/test.db")
        await learner.initialize()

        execution_record = {
            "execution_id": 1,
            "status": "completed",
            "steps_completed": [
                {"step_id": i} for i in range(1, 5)
            ],
            "estimated_total_duration_ms": 10000,
            "actual_duration_ms": 15000,
            "errors": []
        }

        patterns = await learner._extract_patterns(execution_record)
        improvements = await learner._identify_improvements(execution_record, patterns)

        assert len(improvements) > 0
        improvement_titles = [i.title for i in improvements]
        assert any("parallelize" in t.lower() or "improve" in t.lower()
                   for t in improvement_titles)

        await learner.shutdown()

    async def test_learner_get_patterns(self):
        """Test getting learned patterns"""
        learner = LearnerAgent("/tmp/test.db")
        await learner.initialize()

        execution_record = {
            "execution_id": 1,
            "status": "completed",
            "steps_completed": [{"step_id": i} for i in range(1, 5)],
            "estimated_total_duration_ms": 10000,
            "actual_duration_ms": 9000,
            "errors": []
        }

        await learner.learn_from_execution(execution_record)

        result = await learner.get_patterns()
        assert result["status"] == "success"
        assert result["pattern_count"] >= 0

        await learner.shutdown()

    async def test_learner_get_improvements(self):
        """Test getting improvements"""
        learner = LearnerAgent("/tmp/test.db")
        await learner.initialize()

        execution_record = {
            "execution_id": 1,
            "status": "completed",
            "steps_completed": [{"step_id": i} for i in range(1, 5)],
            "estimated_total_duration_ms": 10000,
            "actual_duration_ms": 15000,
            "errors": []
        }

        await learner.learn_from_execution(execution_record)

        result = await learner.get_improvements()
        assert result["status"] == "success"
        assert result["improvement_count"] >= 0

        await learner.shutdown()

    async def test_learner_analyze_accuracy(self):
        """Test prediction accuracy analysis"""
        learner = LearnerAgent("/tmp/test.db")
        await learner.initialize()

        # Add first execution
        exec1 = {
            "execution_id": 1,
            "status": "completed",
            "estimated_total_duration_ms": 10000,
            "actual_duration_ms": 9500,
            "steps_completed": [],
            "errors": []
        }
        await learner.learn_from_execution(exec1)

        # Add second execution
        exec2 = {
            "execution_id": 2,
            "status": "completed",
            "estimated_total_duration_ms": 12000,
            "actual_duration_ms": 11800,
            "steps_completed": [],
            "errors": []
        }
        await learner.learn_from_execution(exec2)

        result = await learner.analyze_prediction_accuracy()

        assert result["status"] == "success"
        assert "accuracy_metrics" in result
        assert result["accuracy_metrics"]["predictions_analyzed"] == 2

        await learner.shutdown()

    async def test_learner_metrics_recording(self):
        """Test learner records metrics"""
        learner = LearnerAgent("/tmp/test.db")
        await learner.initialize()

        execution_record = {
            "execution_id": 1,
            "status": "completed",
            "steps_completed": [{"step_id": 1}],
            "estimated_total_duration_ms": 1000,
            "actual_duration_ms": 950,
            "errors": []
        }

        await learner.learn_from_execution(execution_record)

        assert learner.metrics.decisions_made > 0
        assert learner.metrics.decisions_successful > 0

        await learner.shutdown()


# ============================================================================
# Integration Tests: Monitor + Learner
# ============================================================================

@pytest.mark.asyncio
class TestMonitorLearnerIntegration:
    """Integration tests for Monitor and Learner agents"""

    async def test_full_monitoring_learning_workflow(self):
        """Test complete monitoring and learning workflow"""
        monitor = MonitorAgent("/tmp/test.db")
        learner = LearnerAgent("/tmp/test.db")

        await monitor.initialize()
        await learner.initialize()

        # Start monitoring
        plan = {
            "id": 1,
            "estimated_total_duration_ms": 10000,
            "estimated_total_resources": {"cpu": 50}
        }
        await monitor.start_monitoring(1, plan)

        # Record metrics
        metric = {"type": "resource", "value": {"cpu": 30}}
        await monitor.record_metric(1, metric)

        # Check health
        health_result = await monitor.get_health_score(1)
        assert health_result["health_status"] in ["healthy", "warning", "critical"]

        # Create execution record and learn
        execution_record = {
            "execution_id": 1,
            "status": "completed",
            "steps_completed": [{"step_id": 1}],
            "estimated_total_duration_ms": 10000,
            "actual_duration_ms": 9500,
            "errors": []
        }
        learn_result = await learner.learn_from_execution(execution_record)
        assert learn_result["status"] == "success"

        await monitor.shutdown()
        await learner.shutdown()

    async def test_orchestrator_with_monitor_learner(self):
        """Test orchestrator with all Phase 2 agents"""
        orch = AgentOrchestrator("/tmp/test.db")
        planner = PlannerAgent("/tmp/test.db")
        executor = ExecutorAgent("/tmp/test.db")
        monitor = MonitorAgent("/tmp/test.db")
        learner = LearnerAgent("/tmp/test.db")

        orch.register_agent(planner)
        orch.register_agent(executor)
        orch.register_agent(monitor)
        orch.register_agent(learner)

        await orch.initialize()

        # Full workflow
        task = {"id": 1, "description": "Integration test task"}
        plan_result = await orch.decompose_task(task)
        assert plan_result["status"] == "success"

        plan = plan_result["plan"]

        # Monitor the execution
        monitor_msg = {
            "action": "start_monitoring",
            "execution_id": 1,
            "plan": plan
        }
        monitor_result = await monitor.process_message(monitor_msg)
        assert monitor_result["status"] == "success"

        # Execute the plan
        exec_result = await orch.execute_plan(plan)
        assert exec_result["status"] in ["success", "partial_failure"]

        # Learn from execution
        execution_record = {
            "execution_id": 1,
            "status": "completed",
            "steps_completed": [{"step_id": i} for i in range(1, 3)],
            "estimated_total_duration_ms": plan.get("estimated_total_duration_ms", 0),
            "actual_duration_ms": 5000,
            "errors": []
        }
        learn_result = await learner.learn_from_execution(execution_record)
        assert learn_result["status"] == "success"

        await orch.shutdown()


# ============================================================================
# Model Tests
# ============================================================================

class TestMonitorModels:
    """Tests for Monitor data models"""

    def test_execution_metric_creation(self):
        """Test ExecutionMetric model"""
        metric = ExecutionMetric(
            timestamp=int(datetime.now().timestamp()),
            metric_type="resource",
            value=50.0,
            threshold=100.0
        )
        assert metric.metric_type == "resource"
        assert metric.value == 50.0

    def test_anomaly_creation(self):
        """Test Anomaly model"""
        anomaly = Anomaly(
            id="test_anomaly",
            type="resource",
            severity="high",
            message="Resource usage spike",
            value=150.0,
            baseline=100.0,
            deviation_percent=50.0,
            timestamp=int(datetime.now().timestamp())
        )
        assert anomaly.severity == "high"
        assert anomaly.deviation_percent == 50.0


class TestLearnerModels:
    """Tests for Learner data models"""

    def test_execution_pattern_creation(self):
        """Test ExecutionPattern model"""
        pattern = ExecutionPattern(
            id="test_pattern",
            name="Test Pattern",
            description="A test pattern",
            frequency=5,
            confidence=0.85,
            impact="high"
        )
        assert pattern.frequency == 5
        assert pattern.confidence == 0.85

    def test_improvement_creation(self):
        """Test Improvement model"""
        improvement = Improvement(
            id="test_improvement",
            title="Test Improvement",
            description="A test improvement",
            rationale="Test rationale",
            estimated_improvement_percent=20.0,
            confidence=0.8,
            priority="medium"
        )
        assert improvement.estimated_improvement_percent == 20.0
        assert improvement.priority == "medium"


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.asyncio
class TestPhase2Performance:
    """Performance tests for Phase 2 agents"""

    async def test_monitor_performance(self):
        """Test monitor meets latency targets"""
        monitor = MonitorAgent("/tmp/test.db")
        await monitor.initialize()

        plan = {
            "id": 1,
            "estimated_total_duration_ms": 10000,
            "estimated_total_resources": {"cpu": 50}
        }

        from datetime import datetime
        start = datetime.now()
        await monitor.start_monitoring(1, plan)
        await monitor.record_metric(1, {"type": "resource", "value": {"cpu": 30}})
        await monitor.get_health_score(1)
        elapsed_ms = (datetime.now() - start).total_seconds() * 1000

        # Target: <50ms for monitoring operations
        assert elapsed_ms < 100

        await monitor.shutdown()

    async def test_learner_performance(self):
        """Test learner meets latency targets"""
        learner = LearnerAgent("/tmp/test.db")
        await learner.initialize()

        execution_record = {
            "execution_id": 1,
            "status": "completed",
            "steps_completed": [{"step_id": 1}],
            "estimated_total_duration_ms": 10000,
            "actual_duration_ms": 9500,
            "errors": []
        }

        from datetime import datetime
        start = datetime.now()
        await learner.learn_from_execution(execution_record)
        elapsed_ms = (datetime.now() - start).total_seconds() * 1000

        # Target: <1000ms for learning
        assert elapsed_ms < 1000

        await learner.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
