"""Tests for agent coordination framework (Gap 7)."""

import asyncio
from pathlib import Path

import pytest

from athena.orchestration.coordinator import (
    AgentTask,
    TaskStatus,
    AgentOrchestrator,
    DAGBuilder,
    WorkflowBuilder,
    ExecutionPlan,
)


@pytest.fixture
def mock_agents():
    """Create mock agent functions."""
    async def researcher(**kwargs):
        await asyncio.sleep(0.01)  # Simulate work
        return {"findings": f"Research on {kwargs.get('query', 'topic')}"}

    async def analyzer(**kwargs):
        await asyncio.sleep(0.01)
        return {"analysis": "Synthesized results"}

    async def consolidator(**kwargs):
        await asyncio.sleep(0.01)
        return {"consolidated": True}

    return {
        "arxiv_researcher": researcher,
        "github_researcher": researcher,
        "blogs_researcher": researcher,
        "analyzer": analyzer,
        "consolidator": consolidator,
    }


def test_agent_task_creation():
    """Test creating an agent task."""
    task = AgentTask(
        id="task_1",
        agent_name="researcher",
        task_type="research",
        input_data={"query": "transformers"}
    )

    assert task.id == "task_1"
    assert task.agent_name == "researcher"
    assert task.status == TaskStatus.PENDING
    assert task.result is None


def test_agent_task_with_dependencies():
    """Test task with dependencies."""
    task = AgentTask(
        id="task_2",
        agent_name="analyzer",
        task_type="analysis",
        input_data={},
        dependencies=["task_1"]
    )

    assert len(task.dependencies) == 1
    assert task.dependencies[0] == "task_1"


def test_orchestrator_creation(mock_agents):
    """Test creating an orchestrator."""
    orchestrator = AgentOrchestrator(mock_agents)

    assert len(orchestrator.agents) == 5
    assert "arxiv_researcher" in orchestrator.agents


def test_execution_plan_creation(mock_agents):
    """Test creating an execution plan."""
    orchestrator = AgentOrchestrator(mock_agents)
    plan = orchestrator.create_plan("plan_1", project_id=1)

    assert plan.plan_id == "plan_1"
    assert plan.project_id == 1
    assert plan.status == TaskStatus.PENDING


def test_add_task_to_plan(mock_agents):
    """Test adding tasks to a plan."""
    orchestrator = AgentOrchestrator(mock_agents)
    plan = orchestrator.create_plan("plan_1", project_id=1)

    task = AgentTask(
        id="task_1",
        agent_name="arxiv_researcher",
        task_type="research",
        input_data={"query": "transformers"}
    )

    orchestrator.add_task("plan_1", task)

    assert "task_1" in plan.tasks
    assert plan.tasks["task_1"].agent_name == "arxiv_researcher"


@pytest.mark.asyncio
async def test_simple_execution(mock_agents):
    """Test executing a simple single task."""
    orchestrator = AgentOrchestrator(mock_agents)
    plan = orchestrator.create_plan("plan_1", project_id=1)

    task = AgentTask(
        id="task_1",
        agent_name="arxiv_researcher",
        task_type="research",
        input_data={"query": "transformers"}
    )

    orchestrator.add_task("plan_1", task)
    result = await orchestrator.execute_plan("plan_1")

    assert result.status == TaskStatus.COMPLETED
    assert "task_1" in result.results
    assert "findings" in result.results["task_1"]


@pytest.mark.asyncio
async def test_parallel_execution(mock_agents):
    """Test executing tasks in parallel."""
    orchestrator = AgentOrchestrator(mock_agents)
    plan = orchestrator.create_plan("plan_2", project_id=1)

    # Add 3 parallel research tasks
    for i in range(3):
        task = AgentTask(
            id=f"research_{i}",
            agent_name="arxiv_researcher",
            task_type="research",
            input_data={"query": "topic"}
        )
        orchestrator.add_task("plan_2", task)

    result = await orchestrator.execute_plan("plan_2")

    assert result.status == TaskStatus.COMPLETED
    assert len(result.results) == 3


@pytest.mark.asyncio
async def test_dependent_execution(mock_agents):
    """Test executing tasks with dependencies."""
    orchestrator = AgentOrchestrator(mock_agents)
    plan = orchestrator.create_plan("plan_3", project_id=1)

    # Add research task
    research = AgentTask(
        id="research_1",
        agent_name="arxiv_researcher",
        task_type="research",
        input_data={"query": "transformers"}
    )
    orchestrator.add_task("plan_3", research)

    # Add analysis task depending on research
    analysis = AgentTask(
        id="analysis_1",
        agent_name="analyzer",
        task_type="analysis",
        input_data={},
        dependencies=["research_1"]
    )
    orchestrator.add_task("plan_3", analysis)

    result = await orchestrator.execute_plan("plan_3")

    assert result.status == TaskStatus.COMPLETED
    assert result.tasks["research_1"].status == TaskStatus.COMPLETED
    assert result.tasks["analysis_1"].status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_circular_dependency_detection(mock_agents):
    """Test that circular dependencies are detected."""
    orchestrator = AgentOrchestrator(mock_agents)
    plan = orchestrator.create_plan("plan_4", project_id=1)

    # Create circular dependency: A->B->C->A
    task_a = AgentTask(
        id="task_a",
        agent_name="analyzer",
        task_type="analysis",
        input_data={},
        dependencies=["task_c"]
    )
    task_b = AgentTask(
        id="task_b",
        agent_name="analyzer",
        task_type="analysis",
        input_data={},
        dependencies=["task_a"]
    )
    task_c = AgentTask(
        id="task_c",
        agent_name="analyzer",
        task_type="analysis",
        input_data={},
        dependencies=["task_b"]
    )

    orchestrator.add_task("plan_4", task_a)
    orchestrator.add_task("plan_4", task_b)
    orchestrator.add_task("plan_4", task_c)

    result = await orchestrator.execute_plan("plan_4")

    # Should fail due to circular dependency
    assert result.status == TaskStatus.FAILED


def test_dag_builder_research_tasks():
    """Test DAGBuilder for research tasks."""
    builder = DAGBuilder("workflow_1", project_id=1)

    agents = ["arxiv", "github", "blogs"]
    task_ids = builder.add_research_tasks("transformers", agents)

    assert len(task_ids) == 3
    assert all(isinstance(tid, str) for tid in task_ids)


def test_dag_builder_with_analysis():
    """Test DAGBuilder with analysis phase."""
    builder = DAGBuilder("workflow_2", project_id=1)

    research_tasks = builder.add_research_tasks("topic", ["agent1", "agent2"])
    analysis_task = builder.add_analysis_task(research_tasks)

    plan = builder.build()

    assert len(plan.tasks) == 3
    assert plan.tasks[analysis_task].dependencies == research_tasks


def test_dag_builder_with_consolidation():
    """Test DAGBuilder with consolidation phase."""
    builder = DAGBuilder("workflow_3", project_id=1)

    research_tasks = builder.add_research_tasks("topic", ["agent1"])
    analysis_task = builder.add_analysis_task(research_tasks)
    consolidation_task = builder.add_consolidation_task([analysis_task])

    plan = builder.build()

    assert len(plan.tasks) == 3
    assert plan.tasks[consolidation_task].dependencies == [analysis_task]


def test_workflow_builder_research_workflow():
    """Test WorkflowBuilder for standard research workflow."""
    plan = WorkflowBuilder.create_research_workflow(
        query="transformers",
        agents=["arxiv", "github"],
        with_analysis=True,
        with_consolidation=True
    )

    assert isinstance(plan, ExecutionPlan)
    assert len(plan.tasks) > 0
    # Should have research, analysis, and consolidation tasks
    assert any("research" in task_id for task_id in plan.tasks.keys())


def test_workflow_builder_minimal():
    """Test WorkflowBuilder with minimal options."""
    plan = WorkflowBuilder.create_research_workflow(
        query="topic",
        agents=["agent1"],
        with_analysis=False,
        with_consolidation=False
    )

    assert isinstance(plan, ExecutionPlan)
    # Should only have research task
    assert len(plan.tasks) == 1


@pytest.mark.asyncio
async def test_execution_result_capture(mock_agents):
    """Test that execution results are properly captured."""
    orchestrator = AgentOrchestrator(mock_agents)
    plan = orchestrator.create_plan("plan_5", project_id=1)

    task = AgentTask(
        id="task_1",
        agent_name="arxiv_researcher",
        task_type="research",
        input_data={"query": "specific_topic"}
    )

    orchestrator.add_task("plan_5", task)
    result = await orchestrator.execute_plan("plan_5")

    # Check that result contains expected data
    assert result.results["task_1"]["findings"] is not None
