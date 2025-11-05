"""Tests for project learning and consolidation."""

import pytest
from datetime import datetime

from athena.consolidation.project_learning import (
    ProjectLearningEngine,
    ProjectInsight,
    ProjectTemplate,
    ProjectDifficulty,
)


class TestProjectInsight:
    """Tests for ProjectInsight dataclass."""

    def test_create_project_insight(self):
        """Test creating a project insight."""
        insight = ProjectInsight(
            title="Effective Strategy",
            description="Hierarchical decomposition worked well",
            extracted_at=datetime.now(),
            project_id=1,
            confidence=0.95,
        )

        assert insight.title == "Effective Strategy"
        assert insight.confidence == 0.95
        assert insight.project_id == 1

    def test_insight_with_low_confidence(self):
        """Test insight with low confidence."""
        insight = ProjectInsight(
            title="Uncertain Finding",
            description="Only 1 task to base conclusion on",
            extracted_at=datetime.now(),
            project_id=1,
            confidence=0.3,
        )

        assert insight.confidence == 0.3


class TestProjectTemplate:
    """Tests for ProjectTemplate dataclass."""

    def test_create_project_template(self):
        """Test creating a project template."""
        template = ProjectTemplate(
            template_name="Standard 3-Phase Refactor",
            description="Template for refactoring projects",
            typical_phases=["Planning", "Implementation", "Testing"],
            typical_tasks_per_phase={
                "Planning": ["Requirements analysis", "Design review"],
                "Implementation": ["Code refactoring", "Unit testing"],
                "Testing": ["Integration testing", "Performance testing"],
            },
            estimated_duration_days=10.0,
            recommended_strategy_id=5,
            applicable_project_types=["refactoring", "modernization"],
            created_from_project_ids=[1, 2, 3],
        )

        assert template.template_name == "Standard 3-Phase Refactor"
        assert len(template.typical_phases) == 3
        assert template.estimated_duration_days == 10.0

    def test_template_usage_tracking(self):
        """Test template usage tracking."""
        template = ProjectTemplate(
            template_name="Template",
            description="Description",
            typical_phases=[],
            typical_tasks_per_phase={},
            estimated_duration_days=5.0,
            applicable_project_types=["type1"],
            created_from_project_ids=[1],
            recommended_strategy_id=None,
            usage_count=5,
            success_rate=0.8,
        )

        assert template.usage_count == 5
        assert template.success_rate == 0.8


class TestProjectDifficulty:
    """Tests for ProjectDifficulty dataclass."""

    def test_create_difficulty_estimate(self):
        """Test creating a difficulty estimate."""
        difficulty = ProjectDifficulty(
            difficulty_level=7,
            reasoning=["High scope", "Multiple dependencies", "New technology"],
            estimated_duration_days=15.0,
            recommended_team_size=3,
            applicable_patterns_id=[1, 2],
            confidence=0.85,
        )

        assert difficulty.difficulty_level == 7
        assert difficulty.estimated_duration_days == 15.0
        assert difficulty.confidence == 0.85

    def test_difficulty_ranges(self):
        """Test difficulty level ranges."""
        for level in range(1, 11):
            difficulty = ProjectDifficulty(
                difficulty_level=level,
                reasoning=[],
                estimated_duration_days=5.0 * level,
                recommended_team_size=1 + (level // 3),
                applicable_patterns_id=[],
                confidence=0.8,
            )
            assert 1 <= difficulty.difficulty_level <= 10


class TestProjectLearningEngine:
    """Tests for ProjectLearningEngine."""

    def test_initialize_engine(self):
        """Test initializing the learning engine."""
        engine = ProjectLearningEngine()
        assert engine is not None
        assert len(engine._project_insights) == 0
        assert len(engine._templates) == 0

    def test_extract_project_insights_empty(self):
        """Test extracting insights from empty project."""
        engine = ProjectLearningEngine()

        insights = engine.extract_project_insights(
            project_id=1,
            project_data={},
            execution_feedback=[],
        )

        assert len(insights) == 0

    def test_extract_project_insights_with_feedback(self):
        """Test extracting insights from project with execution feedback."""
        engine = ProjectLearningEngine()

        execution_feedback = [
            {"decomposition_strategy": "hierarchical", "success": True, "quality_score": 0.95},
            {"decomposition_strategy": "hierarchical", "success": True, "quality_score": 0.90},
            {"decomposition_strategy": "flat", "success": False, "quality_score": 0.60},
        ]

        project_data = {
            "phases": [
                {"name": "Phase 1", "duration_variance_pct": 10.0},
                {"name": "Phase 2", "duration_variance_pct": -5.0},
            ],
        }

        insights = engine.extract_project_insights(
            project_id=1,
            project_data=project_data,
            execution_feedback=execution_feedback,
        )

        assert len(insights) > 0
        # Should extract insights about decomposition strategy, phase variance, and quality
        assert any("Decomposition" in i.title for i in insights)

    def test_extract_quality_insights(self):
        """Test extracting quality insights."""
        engine = ProjectLearningEngine()

        execution_feedback = [
            {"quality_score": 0.95},
            {"quality_score": 0.92},
            {"quality_score": 0.88},
            {"quality_score": 0.90},
            {"quality_score": 0.94},
        ]

        insights = engine.extract_project_insights(
            project_id=1,
            project_data={},
            execution_feedback=execution_feedback,
        )

        quality_insights = [i for i in insights if "Quality" in i.title]
        assert len(quality_insights) > 0
        assert quality_insights[0].confidence > 0.8

    def test_generate_project_template(self):
        """Test generating a project template."""
        engine = ProjectLearningEngine()

        project_data_list = [
            {
                "name": "Project 1",
                "type": "refactoring",
                "actual_duration_days": 10.0,
                "phases": [
                    {"name": "Planning", "tasks": ["Requirements", "Design"]},
                    {"name": "Implementation", "tasks": ["Coding", "Testing"]},
                    {"name": "Deployment", "tasks": ["Deploy", "Verify"]},
                ],
            },
            {
                "name": "Project 2",
                "type": "refactoring",
                "actual_duration_days": 12.0,
                "phases": [
                    {"name": "Planning", "tasks": ["Requirements"]},
                    {"name": "Implementation", "tasks": ["Coding"]},
                    {"name": "Deployment", "tasks": ["Deploy"]},
                ],
            },
        ]

        template = engine.generate_project_template(
            template_name="Refactoring Template",
            similar_project_ids=[1, 2],
            project_data_list=project_data_list,
        )

        assert template.template_name == "Refactoring Template"
        assert len(template.typical_phases) > 0
        assert template.estimated_duration_days > 0
        assert "refactoring" in template.applicable_project_types

    def test_estimate_project_difficulty_low(self):
        """Test estimating difficulty for a simple project."""
        engine = ProjectLearningEngine()

        difficulty = engine.estimate_project_difficulty(
            project_description="Add simple feature",
            complexity_indicators={
                "scope": 1,
                "dependencies": 0,
                "risk_level": "low",
                "domains": ["frontend"],
            },
            similar_project_ids=[1],
        )

        assert difficulty.difficulty_level <= 3
        assert difficulty.recommended_team_size == 1

    def test_estimate_project_difficulty_high(self):
        """Test estimating difficulty for a complex project."""
        engine = ProjectLearningEngine()

        difficulty = engine.estimate_project_difficulty(
            project_description="Complete system redesign",
            complexity_indicators={
                "scope": 15,
                "dependencies": 10,
                "risk_level": "high",
                "domains": ["frontend", "backend", "database", "devops"],
            },
            similar_project_ids=[1, 2, 3],
        )

        assert difficulty.difficulty_level >= 7
        assert difficulty.recommended_team_size >= 3
        assert difficulty.confidence > 0.5

    def test_estimate_project_difficulty_medium(self):
        """Test estimating difficulty for a medium project."""
        engine = ProjectLearningEngine()

        difficulty = engine.estimate_project_difficulty(
            project_description="Feature enhancement",
            complexity_indicators={
                "scope": 5,
                "dependencies": 2,
                "risk_level": "medium",
                "domains": ["frontend", "backend"],
            },
            similar_project_ids=[1, 2],
        )

        assert 4 <= difficulty.difficulty_level <= 7
        assert difficulty.estimated_duration_days > 0

    def test_get_lessons_learned(self):
        """Test retrieving lessons learned from a project."""
        engine = ProjectLearningEngine()

        # Add some insights
        engine._project_insights.append(ProjectInsight(
            title="High-confidence lesson",
            description="This pattern worked well",
            extracted_at=datetime.now(),
            project_id=1,
            confidence=0.95,
        ))

        engine._project_insights.append(ProjectInsight(
            title="Low-confidence lesson",
            description="This might work",
            extracted_at=datetime.now(),
            project_id=1,
            confidence=0.3,
        ))

        lessons = engine.get_lessons_learned(1)

        # Should only include high-confidence lessons
        assert len(lessons) >= 1
        assert "High-confidence lesson" in lessons[0]

    def test_recommend_template_for_project(self):
        """Test recommending a template for a new project."""
        engine = ProjectLearningEngine()

        # Add a template
        template = ProjectTemplate(
            template_name="Refactoring Template",
            description="For refactoring projects",
            typical_phases=["Plan", "Implement", "Test"],
            typical_tasks_per_phase={},
            estimated_duration_days=10.0,
            applicable_project_types=["refactoring"],
            created_from_project_ids=[1, 2],
            recommended_strategy_id=None,
            success_rate=0.9,
        )

        engine._templates["refactoring_template"] = template

        # Recommend for refactoring project
        recommendation = engine.recommend_template_for_project(
            project_description="Refactor authentication system",
            project_type="refactoring",
        )

        assert recommendation is not None
        assert recommendation.template_name == "Refactoring Template"

    def test_recommend_no_matching_template(self):
        """Test recommendation when no template matches."""
        engine = ProjectLearningEngine()

        recommendation = engine.recommend_template_for_project(
            project_description="Custom project",
            project_type="experimental",
        )

        assert recommendation is None

    def test_update_orchestration_patterns(self):
        """Test updating orchestration pattern metrics."""
        engine = ProjectLearningEngine()

        execution_data = {
            "success_count": 8,
            "total_executions": 10,
            "avg_execution_time_ms": 5000,
            "speedup_factor": 2.5,
        }

        metrics = engine.update_orchestration_patterns(1, execution_data)

        assert metrics["orchestration_pattern_id"] == 1
        assert metrics["success_rate"] == 0.8
        assert metrics["speedup_factor"] == 2.5

    def test_extract_common_phases(self):
        """Test extracting common phases across projects."""
        engine = ProjectLearningEngine()

        phase_lists = [
            ["Planning", "Development", "Testing", "Deployment"],
            ["Planning", "Development", "Testing"],
            ["Planning", "Development", "Testing", "Documentation"],
        ]

        common_phases = engine._extract_common_phases(phase_lists)

        # Should include phases present in all lists
        assert "Planning" in common_phases
        assert "Development" in common_phases
        assert "Testing" in common_phases

    def test_extract_typical_tasks(self):
        """Test extracting typical tasks per phase."""
        engine = ProjectLearningEngine()

        project_data_list = [
            {
                "phases": [
                    {"name": "Planning", "tasks": ["Requirements", "Design", "Review"]},
                    {"name": "Development", "tasks": ["Code", "Test", "Review"]},
                ]
            },
            {
                "phases": [
                    {"name": "Planning", "tasks": ["Requirements", "Design"]},
                    {"name": "Development", "tasks": ["Code", "Test", "Debug"]},
                ]
            },
        ]

        typical_tasks = engine._extract_typical_tasks(project_data_list)

        assert "Planning" in typical_tasks
        assert "Development" in typical_tasks
        # Should include common tasks
        assert "Requirements" in typical_tasks["Planning"]
        assert "Code" in typical_tasks["Development"]


class TestProjectLearningIntegration:
    """End-to-end tests for project learning."""

    def test_complete_learning_workflow(self):
        """Test complete workflow: extract insights, generate template, estimate difficulty."""
        engine = ProjectLearningEngine()

        # 1. Extract insights from completed projects
        project_data = {
            "phases": [
                {"name": "Phase 1", "duration_variance_pct": 5.0},
                {"name": "Phase 2", "duration_variance_pct": -10.0},
            ],
        }

        execution_feedback = [
            {"decomposition_strategy": "hierarchical", "success": True, "quality_score": 0.95},
            {"decomposition_strategy": "hierarchical", "success": True, "quality_score": 0.92},
        ]

        insights = engine.extract_project_insights(1, project_data, execution_feedback)
        assert len(insights) > 0

        # 2. Generate template from similar projects
        project_data_list = [
            {
                "type": "feature",
                "actual_duration_days": 8.0,
                "phases": [
                    {"name": "Planning", "tasks": ["Spec", "Design"]},
                    {"name": "Development", "tasks": ["Code", "Test"]},
                ],
            },
        ]

        template = engine.generate_project_template(
            "Feature Template",
            [1],
            project_data_list,
        )
        assert template is not None

        # 3. Estimate difficulty for new project
        difficulty = engine.estimate_project_difficulty(
            "New feature",
            {"scope": 5, "dependencies": 2, "risk_level": "medium", "domains": ["backend"]},
            [1],
        )
        assert difficulty is not None
        assert difficulty.difficulty_level > 0
