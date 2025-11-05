"""Unit tests for project context layer."""

import tempfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest

from athena.ai_coordination.project_context import (
    Decision,
    ErrorPattern,
    ProjectContext,
    ProjectPhase,
)
from athena.ai_coordination.project_context_store import ProjectContextStore
from athena.core.database import Database


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(str(db_path))
        yield db
        db.conn.close()


@pytest.fixture
def store(temp_db):
    """Create a ProjectContextStore with temporary database."""
    return ProjectContextStore(temp_db)


@pytest.fixture
def project_id():
    """Generate a unique project ID."""
    return str(uuid4())


class TestProjectContextStore:
    """Tests for ProjectContextStore."""

    def test_get_or_create_new_project(self, store, project_id):
        """Test creating a new project context."""
        context = store.get_or_create(
            project_id=project_id,
            name="Test Project",
            description="A test project"
        )

        assert context.project_id == project_id
        assert context.name == "Test Project"
        assert context.description == "A test project"
        assert context.current_phase == ProjectPhase.PLANNING.value
        assert context.completed_goal_count == 0
        assert context.in_progress_goal_count == 0
        assert context.blocked_goal_count == 0

    def test_get_or_create_existing_project(self, store, project_id):
        """Test retrieving existing project context."""
        # Create first time
        context1 = store.get_or_create(
            project_id=project_id,
            name="Test Project",
            description="A test project"
        )

        # Get same project
        context2 = store.get_or_create(
            project_id=project_id,
            name="Different Name",  # Should be ignored
            description="Different description"  # Should be ignored
        )

        assert context2.id == context1.id
        assert context2.name == "Test Project"  # Original name preserved
        assert context2.description == "A test project"  # Original description preserved

    def test_get_context(self, store, project_id):
        """Test retrieving project context."""
        created = store.get_or_create(
            project_id=project_id,
            name="Test Project",
        )

        retrieved = store.get_context(project_id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.project_id == project_id

    def test_get_context_not_found(self, store):
        """Test getting non-existent project."""
        retrieved = store.get_context("nonexistent-project-id")
        assert retrieved is None

    def test_update_phase(self, store, project_id):
        """Test updating project phase."""
        store.get_or_create(project_id=project_id, name="Test")

        store.update_phase(project_id, ProjectPhase.FEATURE_DEVELOPMENT)

        context = store.get_context(project_id)
        assert context.current_phase == ProjectPhase.FEATURE_DEVELOPMENT.value

    def test_update_goal(self, store, project_id):
        """Test updating current goal."""
        store.get_or_create(project_id=project_id, name="Test")

        goal_id = str(uuid4())
        store.update_goal(project_id, goal_id)

        context = store.get_context(project_id)
        assert context.current_goal_id == goal_id

    def test_update_goal_to_none(self, store, project_id):
        """Test clearing current goal."""
        store.get_or_create(project_id=project_id, name="Test")
        store.update_goal(project_id, str(uuid4()))

        store.update_goal(project_id, None)

        context = store.get_context(project_id)
        assert context.current_goal_id is None

    def test_update_progress(self, store, project_id):
        """Test updating goal progress counts."""
        store.get_or_create(project_id=project_id, name="Test")

        store.update_progress(
            project_id,
            completed=5,
            in_progress=3,
            blocked=1
        )

        context = store.get_context(project_id)
        assert context.completed_goal_count == 5
        assert context.in_progress_goal_count == 3
        assert context.blocked_goal_count == 1

    def test_update_progress_partial(self, store, project_id):
        """Test updating progress with partial counts."""
        store.get_or_create(project_id=project_id, name="Test")
        store.update_progress(project_id, completed=5, in_progress=3, blocked=1)

        # Update only completed
        store.update_progress(project_id, completed=6)

        context = store.get_context(project_id)
        assert context.completed_goal_count == 6
        assert context.in_progress_goal_count == 3  # Unchanged
        assert context.blocked_goal_count == 1  # Unchanged

    def test_update_architecture(self, store, project_id):
        """Test updating architecture."""
        store.get_or_create(project_id=project_id, name="Test")

        architecture = {
            "modules": ["auth", "api", "db"],
            "entry_points": ["main.py"],
            "dependencies": ["requests", "pydantic"],
        }
        store.update_architecture(project_id, architecture)

        context = store.get_context(project_id)
        assert context.architecture == architecture

    def test_add_decision(self, store, project_id):
        """Test adding a decision."""
        store.get_or_create(project_id=project_id, name="Test")

        decision = Decision(
            project_id=project_id,
            decision="Use async/await for database operations",
            reasoning="Improves performance and prevents blocking",
            alternatives_considered=["threading", "multiprocessing"],
            impact="positive"
        )

        decision_id = store.add_decision(decision)

        assert decision_id is not None
        assert isinstance(decision_id, int)

    def test_get_decisions(self, store, project_id):
        """Test retrieving decisions."""
        import time

        store.get_or_create(project_id=project_id, name="Test")

        # Add multiple decisions with small delays to ensure ordering
        for i in range(3):
            decision = Decision(
                project_id=project_id,
                decision=f"Decision {i}",
                reasoning="Test reasoning",
                impact="positive"
            )
            store.add_decision(decision)
            time.sleep(0.01)  # Small delay to ensure timestamp ordering

        decisions = store.get_decisions(project_id)

        assert len(decisions) == 3
        # Decisions should be ordered most recent first
        assert decisions[0].decision == "Decision 2"  # Most recent first
        assert decisions[-1].decision == "Decision 0"  # Oldest last

    def test_get_decisions_limit(self, store, project_id):
        """Test limiting decision retrieval."""
        store.get_or_create(project_id=project_id, name="Test")

        # Add 10 decisions
        for i in range(10):
            decision = Decision(
                project_id=project_id,
                decision=f"Decision {i}",
                reasoning="Test reasoning",
                impact="positive"
            )
            store.add_decision(decision)

        decisions = store.get_decisions(project_id, limit=5)

        assert len(decisions) == 5

    def test_track_error_new(self, store, project_id):
        """Test tracking a new error pattern."""
        store.get_or_create(project_id=project_id, name="Test")

        error = ErrorPattern(
            project_id=project_id,
            error_type="type_mismatch",
            frequency=1,
            mitigation="Check function signatures",
            resolved=False
        )

        store.track_error(error)

        errors = store.get_error_patterns(project_id)
        assert len(errors) == 1
        assert errors[0].error_type == "type_mismatch"
        assert errors[0].frequency == 1

    def test_track_error_increments_frequency(self, store, project_id):
        """Test that tracking same error increments frequency."""
        store.get_or_create(project_id=project_id, name="Test")

        error1 = ErrorPattern(
            project_id=project_id,
            error_type="type_mismatch",
            frequency=1,
            mitigation="Check function signatures"
        )
        store.track_error(error1)

        error2 = ErrorPattern(
            project_id=project_id,
            error_type="type_mismatch",
            frequency=1,
            mitigation="Updated mitigation"
        )
        store.track_error(error2)

        errors = store.get_error_patterns(project_id)
        assert len(errors) == 1
        assert errors[0].frequency == 2
        assert errors[0].mitigation == "Updated mitigation"

    def test_get_error_patterns_unresolved_only(self, store, project_id):
        """Test filtering to unresolved errors only."""
        store.get_or_create(project_id=project_id, name="Test")

        error1 = ErrorPattern(
            project_id=project_id,
            error_type="type_mismatch",
            resolved=False
        )
        store.track_error(error1)

        error2 = ErrorPattern(
            project_id=project_id,
            error_type="async_deadlock",
            resolved=True
        )
        store.track_error(error2)

        unresolved = store.get_error_patterns(project_id, unresolved_only=True)
        assert len(unresolved) == 1
        assert unresolved[0].error_type == "type_mismatch"

    def test_get_error_patterns_all(self, store, project_id):
        """Test getting all errors (resolved and unresolved)."""
        store.get_or_create(project_id=project_id, name="Test")

        error1 = ErrorPattern(
            project_id=project_id,
            error_type="type_mismatch",
            resolved=False
        )
        store.track_error(error1)

        error2 = ErrorPattern(
            project_id=project_id,
            error_type="async_deadlock",
            resolved=True
        )
        store.track_error(error2)

        all_errors = store.get_error_patterns(project_id, unresolved_only=False)
        assert len(all_errors) == 2

    def test_mark_error_resolved(self, store, project_id):
        """Test marking an error as resolved."""
        store.get_or_create(project_id=project_id, name="Test")

        error = ErrorPattern(
            project_id=project_id,
            error_type="type_mismatch",
            resolved=False
        )
        store.track_error(error)

        errors = store.get_error_patterns(project_id, unresolved_only=False)
        error_id = errors[0].id

        store.mark_error_resolved(error_id)

        updated_error = store.get_error_patterns(project_id, unresolved_only=False)[0]
        assert updated_error.resolved is True

    def test_multiple_projects_isolated(self, store):
        """Test that projects don't interfere with each other."""
        project_id_1 = str(uuid4())
        project_id_2 = str(uuid4())

        store.get_or_create(project_id=project_id_1, name="Project 1")
        store.get_or_create(project_id=project_id_2, name="Project 2")

        decision1 = Decision(
            project_id=project_id_1,
            decision="Decision for Project 1",
            reasoning="Test",
            impact="positive"
        )
        store.add_decision(decision1)

        decisions_1 = store.get_decisions(project_id_1)
        decisions_2 = store.get_decisions(project_id_2)

        assert len(decisions_1) == 1
        assert len(decisions_2) == 0
