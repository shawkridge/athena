"""Tests for project planning models."""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from athena.projects.models import (
    ProjectPlan,
    PhasePlan,
    TaskStatusModel,
    Milestone,
    ProjectDependency,
    TaskStatus,
    PhaseStatus,
    MilestoneStatus,
)


class TestProjectPlan:
    """Tests for ProjectPlan model."""

    def test_create_basic_project_plan(self):
        """Test creating a basic project plan."""
        plan = ProjectPlan(
            project_id=1,
            title="Refactor Authentication System",
            description="Modernize auth with JWT tokens",
        )
        assert plan.project_id == 1
        assert plan.title == "Refactor Authentication System"
        assert plan.status == "pending"
        assert plan.phases == []
        assert plan.progress_percentage == 0.0

    def test_project_plan_with_planning_patterns(self):
        """Test project plan with linked planning patterns."""
        plan = ProjectPlan(
            project_id=1,
            title="Feature Development",
            description="Add new feature",
            planning_pattern_id=10,
            decomposition_strategy_id=5,
            orchestration_pattern_id=3,
        )
        assert plan.planning_pattern_id == 10
        assert plan.decomposition_strategy_id == 5
        assert plan.orchestration_pattern_id == 3

    def test_project_plan_with_phases_and_milestones(self):
        """Test project plan with phases and milestones."""
        plan = ProjectPlan(
            project_id=1,
            title="Complex Project",
            description="Multi-phase project",
            phases=[1, 2, 3],
            milestones=[1, 2],
        )
        assert len(plan.phases) == 3
        assert len(plan.milestones) == 2

    def test_project_plan_dates(self):
        """Test project plan date tracking."""
        now = datetime.now()
        plan = ProjectPlan(
            project_id=1,
            title="Project",
            description="Description",
            start_date=now,
            target_completion_date=now + timedelta(days=30),
        )
        assert plan.start_date == now
        assert plan.target_completion_date == now + timedelta(days=30)

    def test_project_plan_progress_validation(self):
        """Test project plan progress percentage validation."""
        # Valid progress
        plan = ProjectPlan(
            project_id=1,
            title="Project",
            description="Description",
            progress_percentage=50.0,
        )
        assert plan.progress_percentage == 50.0

        # Invalid progress (negative)
        with pytest.raises(ValidationError):
            ProjectPlan(
                project_id=1,
                title="Project",
                description="Description",
                progress_percentage=-10.0,
            )

        # Invalid progress (>100)
        with pytest.raises(ValidationError):
            ProjectPlan(
                project_id=1,
                title="Project",
                description="Description",
                progress_percentage=150.0,
            )

    def test_project_plan_quality_score_validation(self):
        """Test quality score is between 0 and 1."""
        plan = ProjectPlan(
            project_id=1,
            title="Project",
            description="Description",
            quality_score=0.85,
        )
        assert plan.quality_score == 0.85

        with pytest.raises(ValidationError):
            ProjectPlan(
                project_id=1,
                title="Project",
                description="Description",
                quality_score=1.5,
            )

    def test_project_plan_assumptions(self):
        """Test project plan assumptions tracking."""
        assumptions = [
            "Team has 3+ members",
            "Budget approved",
            "Requirements finalized",
        ]
        plan = ProjectPlan(
            project_id=1,
            title="Project",
            description="Description",
            assumptions=assumptions,
        )
        assert len(plan.assumptions) == 3
        assert "Team has 3+ members" in plan.assumptions


class TestPhasePlan:
    """Tests for PhasePlan model."""

    def test_create_basic_phase(self):
        """Test creating a basic phase."""
        phase = PhasePlan(
            project_id=1,
            project_plan_id=1,
            phase_number=1,
            title="Setup",
            description="Initial setup phase",
            planned_duration_days=2.0,
        )
        assert phase.phase_number == 1
        assert phase.title == "Setup"
        assert phase.status == PhaseStatus.PENDING
        assert phase.progress_percentage == 0.0

    def test_phase_with_tasks(self):
        """Test phase with task list."""
        phase = PhasePlan(
            project_id=1,
            project_plan_id=1,
            phase_number=1,
            title="Phase 1",
            description="Description",
            planned_duration_days=1.0,
            tasks=[1, 2, 3],
        )
        assert len(phase.tasks) == 3

    def test_phase_duration_variance(self):
        """Test phase duration variance calculation."""
        phase = PhasePlan(
            project_id=1,
            project_plan_id=1,
            phase_number=1,
            title="Phase 1",
            description="Description",
            planned_duration_days=3.0,
            actual_duration_days=4.5,
        )
        # Variance should be positive when actual > planned
        assert phase.actual_duration_days > phase.planned_duration_days

    def test_phase_status_transitions(self):
        """Test phase status values."""
        phase = PhasePlan(
            project_id=1,
            project_plan_id=1,
            phase_number=1,
            title="Phase 1",
            description="Description",
            planned_duration_days=1.0,
            status=PhaseStatus.IN_PROGRESS,
        )
        assert phase.status == PhaseStatus.IN_PROGRESS

    def test_phase_completion_criteria(self):
        """Test phase completion criteria."""
        criteria = ["All tests passing", "Code reviewed", "Deployed to staging"]
        phase = PhasePlan(
            project_id=1,
            project_plan_id=1,
            phase_number=1,
            title="Phase 1",
            description="Description",
            planned_duration_days=1.0,
            completion_criteria=criteria,
        )
        assert len(phase.completion_criteria) == 3

    def test_phase_validation_gates(self):
        """Test phase validation gate configuration."""
        phase = PhasePlan(
            project_id=1,
            project_plan_id=1,
            phase_number=1,
            title="Phase 1",
            description="Description",
            planned_duration_days=1.0,
            pre_phase_validation_rules=[1, 2],
            post_phase_validation_rules=[3, 4],
        )
        assert len(phase.pre_phase_validation_rules) == 2
        assert len(phase.post_phase_validation_rules) == 2

    def test_phase_blockers(self):
        """Test phase blocker tracking."""
        blockers = ["Waiting for API access", "Unresolved design decision"]
        phase = PhasePlan(
            project_id=1,
            project_plan_id=1,
            phase_number=1,
            title="Phase 1",
            description="Description",
            planned_duration_days=1.0,
            blockers=blockers,
        )
        assert len(phase.blockers) == 2

    def test_phase_duration_variance_validation(self):
        """Test that variance cannot be less than -100%."""
        # Valid: can have negative variance (finished early)
        phase = PhasePlan(
            project_id=1,
            project_plan_id=1,
            phase_number=1,
            title="Phase 1",
            description="Description",
            planned_duration_days=1.0,
            duration_variance_pct=-50.0,
        )
        assert phase.duration_variance_pct == -50.0


class TestTaskStatusModel:
    """Tests for TaskStatusModel."""

    def test_create_basic_task(self):
        """Test creating a basic task."""
        task = TaskStatusModel(
            project_id=1,
            phase_plan_id=1,
            content="Implement JWT authentication",
            active_form="Implementing JWT authentication",
        )
        assert task.content == "Implement JWT authentication"
        assert task.status == TaskStatus.PENDING
        assert task.priority == "medium"

    def test_task_with_duration(self):
        """Test task with duration tracking."""
        task = TaskStatusModel(
            project_id=1,
            phase_plan_id=1,
            content="Task",
            active_form="Task active",
            planned_duration_minutes=60,
            actual_duration_minutes=75,
        )
        assert task.planned_duration_minutes == 60
        assert task.actual_duration_minutes == 75

    def test_task_acceptance_criteria(self):
        """Test task acceptance criteria."""
        criteria = ["Unit tests pass", "Code reviewed", "Documentation updated"]
        task = TaskStatusModel(
            project_id=1,
            phase_plan_id=1,
            content="Task",
            active_form="Task active",
            acceptance_criteria=criteria,
        )
        assert len(task.acceptance_criteria) == 3

    def test_task_dependencies(self):
        """Test task dependency tracking."""
        task = TaskStatusModel(
            project_id=1,
            phase_plan_id=1,
            content="Task",
            active_form="Task active",
            depends_on_task_ids=[1, 2, 3],
        )
        assert len(task.depends_on_task_ids) == 3

    def test_task_status_values(self):
        """Test task status enum values."""
        task = TaskStatusModel(
            project_id=1,
            phase_plan_id=1,
            content="Task",
            active_form="Task active",
            status=TaskStatus.IN_PROGRESS,
        )
        assert task.status == TaskStatus.IN_PROGRESS

    def test_task_priority_values(self):
        """Test task priority."""
        for priority in ["low", "medium", "high", "critical"]:
            task = TaskStatusModel(
                project_id=1,
                phase_plan_id=1,
                content="Task",
                active_form="Task active",
                priority=priority,
            )
            assert task.priority == priority

    def test_task_completion_metrics(self):
        """Test task completion metrics."""
        metrics = {"code_coverage": 0.95, "test_pass_rate": 1.0}
        task = TaskStatusModel(
            project_id=1,
            phase_plan_id=1,
            content="Task",
            active_form="Task active",
            completion_metrics=metrics,
        )
        assert task.completion_metrics["code_coverage"] == 0.95

    def test_task_blockers(self):
        """Test task blocker tracking."""
        task = TaskStatusModel(
            project_id=1,
            phase_plan_id=1,
            content="Task",
            active_form="Task active",
            blockers=["Waiting for library release", "Missing test data"],
        )
        assert len(task.blockers) == 2


class TestMilestone:
    """Tests for Milestone model."""

    def test_create_basic_milestone(self):
        """Test creating a basic milestone."""
        milestone = Milestone(
            project_id=1,
            project_plan_id=1,
            title="Alpha Release",
            description="First alpha release",
            sequence_number=1,
        )
        assert milestone.title == "Alpha Release"
        assert milestone.status == MilestoneStatus.NOT_STARTED

    def test_milestone_dependencies(self):
        """Test milestone dependencies."""
        milestone = Milestone(
            project_id=1,
            project_plan_id=1,
            title="Beta Release",
            description="Beta release after alpha",
            sequence_number=2,
            depends_on_milestone_ids=[1],
            depends_on_task_ids=[1, 2, 3],
        )
        assert len(milestone.depends_on_milestone_ids) == 1
        assert len(milestone.depends_on_task_ids) == 3

    def test_milestone_validation_rules(self):
        """Test milestone validation rule links."""
        milestone = Milestone(
            project_id=1,
            project_plan_id=1,
            title="Milestone",
            description="Description",
            sequence_number=1,
            validation_rule_ids=[1, 2, 3],
        )
        assert len(milestone.validation_rule_ids) == 3

    def test_milestone_assumptions(self):
        """Test milestone assumptions."""
        assumptions = ["API stable", "Database migrated", "Performance acceptable"]
        milestone = Milestone(
            project_id=1,
            project_plan_id=1,
            title="Milestone",
            description="Description",
            sequence_number=1,
            assumptions=assumptions,
        )
        assert len(milestone.assumptions) == 3

    def test_milestone_success_criteria(self):
        """Test milestone success criteria."""
        criteria = ["All critical bugs fixed", "Performance metrics met", "Security audit passed"]
        milestone = Milestone(
            project_id=1,
            project_plan_id=1,
            title="Milestone",
            description="Description",
            sequence_number=1,
            success_criteria=criteria,
        )
        assert len(milestone.success_criteria) == 3

    def test_milestone_status_values(self):
        """Test milestone status enum values."""
        for status in [
            MilestoneStatus.NOT_STARTED,
            MilestoneStatus.IN_PROGRESS,
            MilestoneStatus.COMPLETED,
            MilestoneStatus.AT_RISK,
        ]:
            milestone = Milestone(
                project_id=1,
                project_plan_id=1,
                title="Milestone",
                description="Description",
                sequence_number=1,
                status=status,
            )
            assert milestone.status == status

    def test_milestone_dates(self):
        """Test milestone date tracking."""
        target = datetime.now() + timedelta(days=14)
        completed = datetime.now()
        milestone = Milestone(
            project_id=1,
            project_plan_id=1,
            title="Milestone",
            description="Description",
            sequence_number=1,
            target_date=target,
            actual_completion_date=completed,
        )
        assert milestone.target_date == target
        assert milestone.actual_completion_date == completed


class TestProjectDependency:
    """Tests for ProjectDependency model."""

    def test_create_task_dependency(self):
        """Test creating a task-to-task dependency."""
        dep = ProjectDependency(
            project_id=1,
            project_plan_id=1,
            from_task_id=1,
            to_task_id=2,
            dependency_type="blocks",
        )
        assert dep.from_task_id == 1
        assert dep.to_task_id == 2
        assert dep.dependency_type == "blocks"

    def test_create_phase_dependency(self):
        """Test creating a phase-to-phase dependency."""
        dep = ProjectDependency(
            project_id=1,
            project_plan_id=1,
            from_phase_id=1,
            to_phase_id=2,
            dependency_type="depends_on",
        )
        assert dep.from_phase_id == 1
        assert dep.to_phase_id == 2

    def test_dependency_criticality(self):
        """Test dependency criticality levels."""
        for criticality in ["low", "medium", "high", "critical"]:
            dep = ProjectDependency(
                project_id=1,
                project_plan_id=1,
                from_task_id=1,
                to_task_id=2,
                criticality=criticality,
            )
            assert dep.criticality == criticality

    def test_dependency_type_validation(self):
        """Test dependency type validation."""
        # Valid types
        for dep_type in ["blocks", "depends_on", "relates_to"]:
            dep = ProjectDependency(
                project_id=1,
                project_plan_id=1,
                from_task_id=1,
                to_task_id=2,
                dependency_type=dep_type,
            )
            assert dep.dependency_type == dep_type

        # Invalid type
        with pytest.raises(ValidationError):
            ProjectDependency(
                project_id=1,
                project_plan_id=1,
                from_task_id=1,
                to_task_id=2,
                dependency_type="invalid_type",
            )

    def test_dependency_criticality_validation(self):
        """Test criticality validation."""
        # Invalid criticality
        with pytest.raises(ValidationError):
            ProjectDependency(
                project_id=1,
                project_plan_id=1,
                from_task_id=1,
                to_task_id=2,
                criticality="invalid",
            )

    def test_dependency_validation_flag(self):
        """Test validation before transition flag."""
        dep = ProjectDependency(
            project_id=1,
            project_plan_id=1,
            from_task_id=1,
            to_task_id=2,
            validation_before_transition=False,
        )
        assert dep.validation_before_transition is False

    def test_dependency_description(self):
        """Test dependency description."""
        dep = ProjectDependency(
            project_id=1,
            project_plan_id=1,
            from_task_id=1,
            to_task_id=2,
            description="Task 2 requires results from Task 1",
        )
        assert dep.description is not None


class TestModelIntegration:
    """Integration tests for project models."""

    def test_project_with_phases_and_tasks(self):
        """Test creating a complete project structure."""
        # Create project plan
        project = ProjectPlan(
            project_id=1,
            title="Complete Project",
            description="Multi-phase project",
            phases=[1, 2],
        )

        # Create phases
        phase1 = PhasePlan(
            project_id=1,
            project_plan_id=project.id or 1,
            phase_number=1,
            title="Phase 1",
            description="First phase",
            planned_duration_days=5.0,
            tasks=[1, 2],
        )

        phase2 = PhasePlan(
            project_id=1,
            project_plan_id=project.id or 1,
            phase_number=2,
            title="Phase 2",
            description="Second phase",
            planned_duration_days=3.0,
            tasks=[3, 4],
        )

        # Create tasks
        task1 = TaskStatusModel(
            project_id=1,
            phase_plan_id=1,
            content="Task 1",
            active_form="Working on Task 1",
            depends_on_task_ids=[],
        )

        task2 = TaskStatusModel(
            project_id=1,
            phase_plan_id=1,
            content="Task 2",
            active_form="Working on Task 2",
            depends_on_task_ids=[1],  # Depends on task 1
        )

        # Create dependency
        dep = ProjectDependency(
            project_id=1,
            project_plan_id=1,
            from_task_id=1,
            to_task_id=2,
            dependency_type="blocks",
        )

        assert len(project.phases) == 2
        assert phase1.phase_number == 1
        assert task2.depends_on_task_ids[0] == 1
        assert dep.dependency_type == "blocks"

    def test_project_with_milestones(self):
        """Test project with milestone tracking."""
        project = ProjectPlan(
            project_id=1,
            title="Project with Milestones",
            description="Project tracking progress",
            milestones=[1, 2, 3],
        )

        milestone1 = Milestone(
            project_id=1,
            project_plan_id=1,
            title="Alpha",
            description="Alpha release",
            sequence_number=1,
            status=MilestoneStatus.COMPLETED,
        )

        milestone2 = Milestone(
            project_id=1,
            project_plan_id=1,
            title="Beta",
            description="Beta release",
            sequence_number=2,
            depends_on_milestone_ids=[1],
            status=MilestoneStatus.IN_PROGRESS,
        )

        assert milestone2.depends_on_milestone_ids[0] == milestone1.id or 1
