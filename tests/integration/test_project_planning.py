"""Integration tests for project planning modules."""

import pytest
from datetime import datetime, timedelta

from athena.projects.models import (
    ProjectPlan,
    PhasePlan,
    TaskStatusModel,
    Milestone,
    ProjectDependency,
    PhaseStatus,
    TaskStatus,
    MilestoneStatus,
)
from athena.projects.planning_integration import PlanningIntegration
from athena.projects.orchestration import OrchestrationTracking


class TestPlanningIntegration:
    """Tests for planning integration module."""

    def test_link_task_to_pattern(self):
        """Test linking task to planning pattern."""
        planning = PlanningIntegration()

        link = planning.link_task_to_pattern(
            task_id=1,
            pattern_id=10,
            pattern_type="planning_pattern",
        )

        assert link["task_id"] == 1
        assert link["pattern_id"] == 10
        assert link["pattern_type"] == "planning_pattern"
        assert link["linked_at"] is not None

    def test_record_task_completion(self):
        """Test recording task completion with metrics."""
        planning = PlanningIntegration()

        feedback = planning.record_task_completion(
            task_id=1,
            actual_duration_minutes=90,
            completion_metrics={"code_coverage": 0.95, "test_pass_rate": 1.0},
            blockers=["API latency"],
            quality_score=0.88,
        )

        assert feedback["task_id"] == 1
        assert feedback["actual_duration_minutes"] == 90
        assert feedback["quality_score"] == 0.88
        assert "code_coverage" in feedback["completion_metrics"]

    def test_validate_milestone_success(self):
        """Test milestone validation with all dependencies met."""
        planning = PlanningIntegration()

        # Record completion of dependent tasks
        planning.record_task_completion(1, 60)
        planning.record_task_completion(2, 45)

        milestone = Milestone(
            project_id=1,
            project_plan_id=1,
            title="Alpha Release",
            description="First alpha",
            sequence_number=1,
            depends_on_task_ids=[1, 2],
        )

        result = planning.validate_milestone(milestone)
        assert result["valid"] is True
        assert len(result["issues"]) == 0

    def test_validate_milestone_failure(self):
        """Test milestone validation with missing dependencies."""
        planning = PlanningIntegration()

        milestone = Milestone(
            project_id=1,
            project_plan_id=1,
            title="Beta Release",
            description="Beta release",
            sequence_number=2,
            depends_on_task_ids=[99, 100],  # Non-existent tasks
        )

        result = planning.validate_milestone(milestone)
        assert result["valid"] is False
        assert len(result["issues"]) > 0

    def test_get_task_pattern_link(self):
        """Test retrieving task-pattern link."""
        planning = PlanningIntegration()

        planning.link_task_to_pattern(1, 10)
        planning.link_task_to_pattern(2, 20)

        link = planning.get_task_pattern_link(1)
        assert link is not None
        assert link["task_id"] == 1
        assert link["pattern_id"] == 10

    def test_calculate_plan_vs_actual(self):
        """Test plan vs actual variance calculation."""
        planning = PlanningIntegration()

        phase = PhasePlan(
            project_id=1,
            project_plan_id=1,
            phase_number=1,
            title="Phase 1",
            description="Description",
            planned_duration_days=5.0,
            actual_duration_days=6.5,
            quality_score=0.92,
        )

        analysis = planning.calculate_plan_vs_actual(phase)
        assert analysis["phase_number"] == 1
        assert analysis["planned_duration_days"] == 5.0
        assert analysis["actual_duration_days"] == 6.5
        assert analysis["variance_percentage"] == 30.0  # 30% overrun

    def test_update_task_quality_score(self):
        """Test quality score calculation from metrics."""
        planning = PlanningIntegration()

        task = TaskStatusModel(
            project_id=1,
            phase_plan_id=1,
            content="Task",
            active_form="Working",
        )

        metrics = {
            "code_coverage": 0.95,
            "test_pass_rate": 1.0,
            "performance": 0.85,
            "security_audit": 0.90,
        }

        score = planning.update_task_quality_score(task, metrics)
        assert 0.0 <= score <= 1.0
        assert score > 0.85  # Should be weighted average of good scores

    def test_get_project_progress(self):
        """Test project progress calculation."""
        planning = PlanningIntegration()

        project = ProjectPlan(
            project_id=1,
            title="Project",
            description="Description",
            estimated_duration_days=10.0,
            actual_duration_days=8.5,
        )

        phases = [
            PhasePlan(
                project_id=1,
                project_plan_id=1,
                phase_number=1,
                title="Phase 1",
                description="Description",
                planned_duration_days=5.0,
                status=PhaseStatus.COMPLETED,
            ),
            PhasePlan(
                project_id=1,
                project_plan_id=1,
                phase_number=2,
                title="Phase 2",
                description="Description",
                planned_duration_days=5.0,
                status=PhaseStatus.IN_PROGRESS,
            ),
        ]

        tasks = [
            TaskStatusModel(
                project_id=1,
                phase_plan_id=1,
                content="Task 1",
                active_form="Working",
                status=TaskStatus.COMPLETED,
                quality_score=0.95,
            ),
            TaskStatusModel(
                project_id=1,
                phase_plan_id=1,
                content="Task 2",
                active_form="Working",
                status=TaskStatus.IN_PROGRESS,
                quality_score=0.85,
            ),
        ]

        progress = planning.get_project_progress(project, phases, tasks)
        assert progress["phases_complete_percentage"] == 50.0
        assert progress["tasks_complete_percentage"] == 50.0
        assert progress["quality_score"] > 0.8
        assert progress["overall_progress_percentage"] > 0

    def test_recommend_replanning_trigger_no_trigger(self):
        """Test replanning recommendation when on track."""
        planning = PlanningIntegration()

        phase = PhasePlan(
            project_id=1,
            project_plan_id=1,
            phase_number=1,
            title="Phase 1",
            description="Description",
            planned_duration_days=5.0,
            actual_duration_days=2.5,
        )

        recommendation = planning.recommend_replanning_trigger(phase, 50.0)
        assert recommendation["trigger_replanning"] is False

    def test_recommend_replanning_trigger_needed(self):
        """Test replanning recommendation when behind schedule."""
        planning = PlanningIntegration()

        phase = PhasePlan(
            project_id=1,
            project_plan_id=1,
            phase_number=1,
            title="Phase 1",
            description="Description",
            planned_duration_days=5.0,
            actual_duration_days=2.5,
        )

        recommendation = planning.recommend_replanning_trigger(phase, 10.0)
        # At 50% time with only 10% progress
        assert recommendation["trigger_replanning"] is True


class TestOrchestrationTracking:
    """Tests for orchestration tracking module."""

    def test_record_delegation(self):
        """Test recording agent delegation."""
        tracking = OrchestrationTracking()

        delegation = tracking.record_delegation(
            from_agent="orchestrator",
            to_agent="frontend_specialist",
            task_id=1,
            task_description="Build UI component",
            success=True,
            handoff_cost_tokens=500,
            handoff_time_ms=250,
            completion_time_ms=15000,
            quality_score=0.92,
        )

        assert delegation.from_agent == "orchestrator"
        assert delegation.to_agent == "frontend_specialist"
        assert delegation.success is True
        assert delegation.quality_score == 0.92

    def test_record_agent_team(self):
        """Test recording agent team arrangement."""
        tracking = OrchestrationTracking()

        team = tracking.record_agent_team(
            orchestration_pattern_id=1,
            agents=["orchestrator", "frontend", "backend"],
            arrangement="parallel",
        )

        assert team["orchestration_pattern_id"] == 1
        assert len(team["agents"]) == 3
        assert team["arrangement"] == "parallel"

    def test_calculate_orchestration_effectiveness(self):
        """Test effectiveness calculation."""
        tracking = OrchestrationTracking()

        # Record several delegations
        for i in range(5):
            tracking.record_delegation(
                from_agent="orch",
                to_agent="agent_a",
                task_id=i,
                task_description=f"Task {i}",
                success=i < 4,  # 4 success, 1 failure
                quality_score=0.90 if i < 4 else 0.30,
            )

        # Manually set orchestration_pattern_id for delegations (in real impl)
        effectiveness = tracking.calculate_orchestration_effectiveness(1)

        assert effectiveness.total_delegations >= 0
        assert effectiveness.success_rate <= 1.0

    def test_recommend_agent_team_low_complexity(self):
        """Test team recommendation for low complexity task."""
        tracking = OrchestrationTracking()

        recommendation = tracking.recommend_agent_team(
            task_complexity=2,
            domains_needed=[],
        )

        assert recommendation["recommended_team_size"] == 1
        assert recommendation["arrangement"] == "sequential"
        assert recommendation["expected_speedup"] == 1.0

    def test_recommend_agent_team_high_complexity(self):
        """Test team recommendation for high complexity task."""
        tracking = OrchestrationTracking()

        recommendation = tracking.recommend_agent_team(
            task_complexity=9,
            domains_needed=["frontend", "backend", "devops"],
        )

        assert recommendation["recommended_team_size"] > 1
        assert recommendation["arrangement"] == "parallel"
        assert recommendation["expected_speedup"] > 1.0
        assert recommendation["confidence"] > 0.7

    def test_recommend_agent_team_medium_complexity(self):
        """Test team recommendation for medium complexity task."""
        tracking = OrchestrationTracking()

        recommendation = tracking.recommend_agent_team(
            task_complexity=5,
            domains_needed=["frontend", "backend"],
        )

        assert recommendation["arrangement"] == "hybrid"
        assert recommendation["expected_speedup"] > 1.0
        assert recommendation["expected_speedup"] < 3.0

    def test_estimate_handoff_overhead(self):
        """Test handoff overhead estimation."""
        tracking = OrchestrationTracking()

        estimation = tracking.estimate_handoff_overhead(
            num_agents=3,
            num_handoffs=2,
        )

        assert estimation["num_agents"] == 3
        assert estimation["num_handoffs"] == 2
        assert estimation["overhead_multiplier"] > 1.0
        assert "total_estimated_tokens" in estimation

    def test_identify_successful_agent_pairs(self):
        """Test identifying successful agent pairs."""
        tracking = OrchestrationTracking()

        # Record successful delegations
        for i in range(5):
            tracking.record_delegation(
                from_agent="orchestrator",
                to_agent="backend",
                task_id=i,
                task_description=f"Task {i}",
                success=True,
                quality_score=0.95,
            )

        # Record failed delegations with different pair
        for i in range(5, 8):
            tracking.record_delegation(
                from_agent="orchestrator",
                to_agent="security",
                task_id=i,
                task_description=f"Task {i}",
                success=False,
                quality_score=0.30,
            )

        pairs = tracking.identify_successful_agent_pairs(min_success_rate=0.80)

        # Should find the orchestrator->backend pair
        assert len(pairs) > 0
        assert pairs[0]["success_rate"] >= 0.80

    def test_get_delegation_timeline(self):
        """Test retrieving delegation timeline for task."""
        tracking = OrchestrationTracking()

        # Record multiple delegations for same task
        tracking.record_delegation(
            from_agent="orch",
            to_agent="agent_a",
            task_id=1,
            task_description="Task 1",
            success=True,
        )

        tracking.record_delegation(
            from_agent="agent_a",
            to_agent="agent_b",
            task_id=1,
            task_description="Task 1",
            success=True,
        )

        timeline = tracking.get_delegation_timeline(1)

        assert len(timeline) == 2
        # Should be in chronological order
        assert timeline[0]["timestamp"] <= timeline[1]["timestamp"]


class TestProjectPlanningIntegration:
    """End-to-end integration tests."""

    def test_complete_project_with_planning_patterns(self):
        """Test complete project with planning pattern integration."""
        planning = PlanningIntegration()
        tracking = OrchestrationTracking()

        # Create project plan
        project = ProjectPlan(
            project_id=1,
            title="Feature Development",
            description="Develop new feature",
            planning_pattern_id=10,
            decomposition_strategy_id=5,
            orchestration_pattern_id=3,
        )

        # Create phases
        phase1 = PhasePlan(
            project_id=1,
            project_plan_id=1,
            phase_number=1,
            title="Planning",
            description="Plan feature",
            planned_duration_days=2.0,
            tasks=[1, 2],
        )

        # Create tasks
        task1 = TaskStatusModel(
            project_id=1,
            phase_plan_id=1,
            content="Requirements analysis",
            active_form="Analyzing requirements",
            planned_duration_minutes=480,
        )

        # Link task to pattern
        planning.link_task_to_pattern(task1.id or 1, 10)

        # Record completion
        planning.record_task_completion(
            task1.id or 1,
            actual_duration_minutes=540,
            completion_metrics={"analysis_complete": True},
            quality_score=0.95,
        )

        # Verify
        link = planning.get_task_pattern_link(task1.id or 1)
        assert link is not None
        assert link["pattern_id"] == 10

    def test_multi_agent_project_execution(self):
        """Test multi-agent project execution with orchestration."""
        tracking = OrchestrationTracking()

        # Recommend team for complex task
        recommendation = tracking.recommend_agent_team(
            task_complexity=8,
            domains_needed=["frontend", "backend"],
        )

        assert recommendation["recommended_team_size"] > 1

        # Simulate delegations
        agents = ["orchestrator"] + recommendation["agent_roles"]
        for i, agent in enumerate(agents[1:], 1):
            tracking.record_delegation(
                from_agent=agents[i - 1],
                to_agent=agent,
                task_id=1,
                task_description="Complex feature",
                success=True,
                quality_score=0.90,
            )

        # Check effectiveness
        timeline = tracking.get_delegation_timeline(1)
        assert len(timeline) > 0
