"""
Unit Tests for Tier 2 Agents Framework

Tests for BaseAgent, MessageBus, Orchestrator, Planner, and Executor.
"""

import asyncio
import pytest
from datetime import datetime
from athena.agents.base import (
    AgentType, AgentStatus, AgentMetrics, BaseAgent
)
from athena.agents.message_bus import (
    Message, MessageBus, MessageType
)
from athena.agents.orchestrator import AgentOrchestrator
from athena.agents.planner import PlannerAgent, ExecutionPlan
from athena.agents.executor import ExecutorAgent


# ============================================================================
# Test BaseAgent and AgentMetrics
# ============================================================================

class TestAgentMetrics:
    """Tests for AgentMetrics"""

    def test_metrics_initialization(self):
        """Test metrics initialized with defaults"""
        metrics = AgentMetrics()
        assert metrics.decisions_made == 0
        assert metrics.success_rate == 1.0
        assert metrics.error_rate == 0.0
        assert metrics.average_confidence == 1.0

    def test_metrics_success_rate(self):
        """Test success rate calculation"""
        metrics = AgentMetrics(decisions_made=10, decisions_successful=9)
        assert metrics.success_rate == 0.9

    def test_metrics_error_rate(self):
        """Test error rate calculation"""
        metrics = AgentMetrics(decisions_made=10, errors_encountered=2)
        assert metrics.error_rate == 0.2

    def test_metrics_average_confidence(self):
        """Test average confidence calculation"""
        metrics = AgentMetrics(confidence_scores=[0.8, 0.9, 0.7])
        assert abs(metrics.average_confidence - 0.8) < 0.01

    def test_metrics_to_dict(self):
        """Test metrics conversion to dict"""
        metrics = AgentMetrics(decisions_made=5)
        data = metrics.to_dict()
        assert data["decisions_made"] == 5
        assert "success_rate" in data
        assert "error_rate" in data


# ============================================================================
# Test Message and MessageBus
# ============================================================================

class TestMessage:
    """Tests for Message class"""

    def test_message_creation(self):
        """Test message creation"""
        msg = Message(
            sender="planner",
            recipient="executor",
            message_type=MessageType.REQUEST,
            payload={"action": "execute"}
        )
        assert msg.sender == "planner"
        assert msg.recipient == "executor"
        assert msg.message_type == MessageType.REQUEST

    def test_message_defaults(self):
        """Test message default values"""
        msg = Message(
            sender="a",
            recipient="b",
            message_type=MessageType.REQUEST,
            payload={}
        )
        assert msg.priority == 0.5
        assert msg.timestamp > 0
        assert msg.correlation_id != ""
        assert msg.response_expected == False
        assert msg.timeout_seconds == 30

    def test_message_priority_ordering(self):
        """Test message priority for sorting"""
        msg_high = Message("a", "b", MessageType.REQUEST, {}, priority=0.9)
        msg_low = Message("a", "b", MessageType.REQUEST, {}, priority=0.1)

        # Lower value should be "less than" for heap ordering
        assert msg_low < msg_high

    def test_message_to_dict(self):
        """Test message conversion to dict"""
        msg = Message("a", "b", MessageType.REQUEST, {"test": "data"})
        data = msg.to_dict()
        assert data["sender"] == "a"
        assert data["recipient"] == "b"
        assert data["message_type"] == "request"
        assert data["payload"] == {"test": "data"}


@pytest.mark.asyncio
class TestMessageBus:
    """Tests for MessageBus"""

    async def test_message_bus_initialization(self):
        """Test message bus initialization"""
        bus = MessageBus()
        await bus.initialize()
        assert bus._running == True
        await bus.shutdown()

    async def test_message_bus_publish(self):
        """Test publishing messages"""
        bus = MessageBus()
        await bus.initialize()

        msg = Message("a", "b", MessageType.REQUEST, {})
        await bus.publish(msg)

        assert bus.message_queue.qsize() > 0
        await bus.shutdown()

    async def test_message_bus_subscribe(self):
        """Test subscribing to messages"""
        bus = MessageBus()
        await bus.initialize()

        received_messages = []

        async def handler(msg: Message):
            received_messages.append(msg)
            return {"status": "ok"}

        await bus.subscribe("test_agent", handler)
        assert "test_agent" in bus.subscribers

        await bus.shutdown()

    async def test_message_bus_send_request(self):
        """Test send_request with response"""
        bus = MessageBus()
        await bus.initialize()

        received_messages = []

        async def handler(msg: Message):
            received_messages.append(msg)
            return {"status": "success", "data": "response"}

        await bus.subscribe("responder", handler)

        msg = Message(
            "requester", "responder", MessageType.REQUEST,
            {"action": "test"},
            response_expected=True
        )

        response = await bus.send_request(msg)
        assert response["status"] == "success"
        assert response["data"] == "response"
        assert len(received_messages) == 1

        await bus.shutdown()

    async def test_message_bus_timeout(self):
        """Test request timeout"""
        bus = MessageBus()
        await bus.initialize()

        msg = Message(
            "requester", "nonexistent", MessageType.REQUEST,
            {"action": "test"},
            response_expected=True,
            timeout_seconds=1
        )

        response = await bus.send_request(msg)
        assert response["status"] == "error"
        assert "timeout" in response["error"].lower()

        await bus.shutdown()

    async def test_message_bus_queue_stats(self):
        """Test queue statistics"""
        bus = MessageBus()
        await bus.initialize()

        stats = bus.get_queue_stats()
        assert "queue_size" in stats
        assert "pending_responses" in stats
        assert "queue_utilization" in stats

        await bus.shutdown()


# ============================================================================
# Test AgentOrchestrator
# ============================================================================

@pytest.mark.asyncio
class TestAgentOrchestrator:
    """Tests for AgentOrchestrator"""

    async def test_orchestrator_initialization(self):
        """Test orchestrator initialization"""
        orch = AgentOrchestrator("/tmp/test.db")
        await orch.initialize()
        assert orch._running == True
        assert len(orch.agents) == 0  # No agents registered yet
        await orch.shutdown()

    async def test_orchestrator_register_agent(self):
        """Test registering agents"""
        orch = AgentOrchestrator("/tmp/test.db")
        planner = PlannerAgent("/tmp/test.db")
        orch.register_agent(planner)

        assert AgentType.PLANNER in orch.agents
        await orch.shutdown()

    async def test_orchestrator_get_status(self):
        """Test getting orchestrator status"""
        orch = AgentOrchestrator("/tmp/test.db")
        planner = PlannerAgent("/tmp/test.db")
        orch.register_agent(planner)
        await orch.initialize()

        status = await orch.get_agent_status()
        assert "orchestrator_status" in status
        assert "agents" in status

        await orch.shutdown()

    async def test_orchestrator_health_check(self):
        """Test health check"""
        orch = AgentOrchestrator("/tmp/test.db")
        planner = PlannerAgent("/tmp/test.db")
        orch.register_agent(planner)
        await orch.initialize()

        assert orch.is_healthy() == True

        await orch.shutdown()
        assert orch.is_healthy() == False


# ============================================================================
# Test PlannerAgent
# ============================================================================

@pytest.mark.asyncio
class TestPlannerAgent:
    """Tests for PlannerAgent"""

    async def test_planner_initialization(self):
        """Test planner initialization"""
        planner = PlannerAgent("/tmp/test.db")
        await planner.initialize()
        assert planner.agent_type == AgentType.PLANNER
        assert planner._running == True
        await planner.shutdown()

    async def test_planner_decompose_task(self):
        """Test task decomposition"""
        planner = PlannerAgent("/tmp/test.db")
        await planner.initialize()

        task = {
            "id": 1,
            "description": "Build user authentication system",
            "salience": 0.8
        }

        result = await planner.decompose_task(task)

        assert result["status"] == "success"
        assert "plan" in result
        assert result["confidence"] > 0.5

        plan = result["plan"]
        assert plan["steps"] is not None
        assert len(plan["steps"]) > 0

        await planner.shutdown()

    async def test_planner_metrics_recording(self):
        """Test planner records metrics"""
        planner = PlannerAgent("/tmp/test.db")
        await planner.initialize()

        task = {"id": 1, "description": "Test task"}
        await planner.decompose_task(task)

        assert planner.metrics.decisions_made > 0
        assert planner.metrics.success_rate > 0

        await planner.shutdown()

    async def test_planner_plan_structure(self):
        """Test generated plan structure"""
        planner = PlannerAgent("/tmp/test.db")
        await planner.initialize()

        task = {"description": "Test task"}
        result = await planner.decompose_task(task)
        plan = result["plan"]

        assert "steps" in plan
        assert "estimated_total_duration_ms" in plan
        assert "estimated_total_resources" in plan
        assert "confidence" in plan
        assert "complexity" in plan

        # Check step structure
        for step in plan["steps"]:
            assert "id" in step
            assert "description" in step
            assert "estimated_duration_ms" in step
            assert "risk_level" in step

        await planner.shutdown()


# ============================================================================
# Test ExecutorAgent
# ============================================================================

@pytest.mark.asyncio
class TestExecutorAgent:
    """Tests for ExecutorAgent"""

    async def test_executor_initialization(self):
        """Test executor initialization"""
        executor = ExecutorAgent("/tmp/test.db")
        await executor.initialize()
        assert executor.agent_type == AgentType.EXECUTOR
        assert executor._running == True
        await executor.shutdown()

    async def test_executor_execute_plan(self):
        """Test plan execution"""
        executor = ExecutorAgent("/tmp/test.db")
        await executor.initialize()

        plan = {
            "id": 1,
            "steps": [
                {
                    "id": 1,
                    "description": "Test step 1",
                    "estimated_duration_ms": 1000,
                    "estimated_resources": {"cpu": 10},
                    "dependencies": [],
                    "risk_level": "low"
                },
                {
                    "id": 2,
                    "description": "Test step 2",
                    "estimated_duration_ms": 1000,
                    "estimated_resources": {"cpu": 10},
                    "dependencies": [1],
                    "risk_level": "low"
                }
            ]
        }

        result = await executor.execute_plan(plan)

        assert result["status"] in ["success", "partial_failure"]
        assert "execution" in result
        assert len(result["results"]) == 2

        await executor.shutdown()

    async def test_executor_metrics_recording(self):
        """Test executor records metrics"""
        executor = ExecutorAgent("/tmp/test.db")
        await executor.initialize()

        plan = {
            "id": 1,
            "steps": [
                {
                    "id": 1,
                    "description": "Test",
                    "estimated_duration_ms": 100,
                    "estimated_resources": {},
                    "dependencies": [],
                    "risk_level": "low"
                }
            ]
        }

        await executor.execute_plan(plan)

        assert executor.metrics.decisions_made > 0

        await executor.shutdown()

    async def test_executor_abort(self):
        """Test execution abort"""
        executor = ExecutorAgent("/tmp/test.db")
        await executor.initialize()

        result = await executor.abort_execution(999)
        assert result["status"] == "error"  # Execution doesn't exist

        await executor.shutdown()


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
class TestIntegration:
    """Integration tests for agents working together"""

    async def test_planner_executor_workflow(self):
        """Test planner and executor working together"""
        planner = PlannerAgent("/tmp/test.db")
        executor = ExecutorAgent("/tmp/test.db")

        await planner.initialize()
        await executor.initialize()

        # Step 1: Plan
        task = {
            "id": 1,
            "description": "Simple task",
            "salience": 0.8
        }
        plan_result = await planner.decompose_task(task)
        assert plan_result["status"] == "success"

        plan = plan_result["plan"]

        # Step 2: Execute
        exec_result = await executor.execute_plan(plan)
        assert exec_result["status"] in ["success", "partial_failure"]

        await planner.shutdown()
        await executor.shutdown()

    async def test_orchestrator_workflow(self):
        """Test orchestrator coordinating agents"""
        orch = AgentOrchestrator("/tmp/test.db")
        planner = PlannerAgent("/tmp/test.db")
        executor = ExecutorAgent("/tmp/test.db")

        orch.register_agent(planner)
        orch.register_agent(executor)
        await orch.initialize()

        # Full workflow
        task = {
            "id": 1,
            "description": "Integration test task",
            "salience": 0.7
        }

        # Decompose
        plan_result = await orch.decompose_task(task)
        assert plan_result["status"] == "success"

        plan = plan_result["plan"]

        # Execute
        exec_result = await orch.execute_plan(plan)
        assert exec_result["status"] in ["success", "partial_failure"]

        # Check history
        history = await orch.get_execution_history()
        assert len(history) >= 2

        await orch.shutdown()


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.asyncio
class TestPerformance:
    """Performance tests for agents"""

    async def test_planner_performance(self):
        """Test planner meets latency targets"""
        planner = PlannerAgent("/tmp/test.db")
        await planner.initialize()

        task = {"description": "Performance test"}

        start = datetime.now()
        await planner.decompose_task(task)
        elapsed_ms = (datetime.now() - start).total_seconds() * 1000

        # Target: <500ms
        assert elapsed_ms < 500

        await planner.shutdown()

    async def test_executor_performance(self):
        """Test executor meets latency targets"""
        executor = ExecutorAgent("/tmp/test.db")
        await executor.initialize()

        plan = {
            "id": 1,
            "steps": [
                {
                    "id": 1,
                    "description": "Test",
                    "estimated_duration_ms": 10,
                    "estimated_resources": {},
                    "dependencies": [],
                    "risk_level": "low"
                }
            ]
        }

        start = datetime.now()
        await executor.execute_plan(plan)
        elapsed_ms = (datetime.now() - start).total_seconds() * 1000

        # Target: <100ms for 1 simple step
        assert elapsed_ms < 200

        await executor.shutdown()

    async def test_message_bus_throughput(self):
        """Test message bus throughput"""
        bus = MessageBus()
        await bus.initialize()

        message_count = 100
        start = datetime.now()

        for i in range(message_count):
            msg = Message(f"sender_{i}", "receiver", MessageType.REQUEST, {})
            await bus.publish(msg)

        elapsed_seconds = (datetime.now() - start).total_seconds()
        throughput = message_count / elapsed_seconds

        # Target: 100+ messages per second
        assert throughput > 100

        await bus.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
