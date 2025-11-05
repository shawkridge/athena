"""Tests for SessionContinuity layer - save/restore session state."""

import time
from datetime import datetime
from uuid import uuid4

import pytest

from athena.ai_coordination.session_continuity import (
    ActionCycleSnapshot,
    CodeContextSnapshot,
    ExecutionTraceSnapshot,
    ProjectContextSnapshot,
    ResumptionRecommendation,
    SessionMetadata,
    SessionSnapshot,
    SessionStatus,
)
from athena.ai_coordination.session_continuity_mcp_tools import (
    SessionContinuityMCPTools,
)
from athena.ai_coordination.session_continuity_store import SessionContinuityStore
from athena.core.database import Database


class TestSessionContinuityModels:
    """Test SessionContinuity data models."""

    def test_create_project_context_snapshot(self):
        """Test creating a project context snapshot."""
        snapshot = ProjectContextSnapshot(
            project_id="proj-123",
            project_name="Test Project",
            current_phase="feature_development",
            completed_goals=5,
            in_progress_goals=2,
            blocked_goals=1,
            progress_percentage=62.5,
        )

        assert snapshot.project_id == "proj-123"
        assert snapshot.project_name == "Test Project"
        assert snapshot.current_phase == "feature_development"
        assert snapshot.completed_goals == 5
        assert snapshot.progress_percentage == 62.5

    def test_create_action_cycle_snapshot(self):
        """Test creating an action cycle snapshot."""
        snapshot = ActionCycleSnapshot(
            cycle_id=42,
            goal_id="goal-999",
            status="executing",
            attempt_count=3,
            max_attempts=5,
            current_step="Running tests",
            goal_description="Implement feature X",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert snapshot.cycle_id == 42
        assert snapshot.status == "executing"
        assert snapshot.attempt_count == 3
        assert snapshot.max_attempts == 5

    def test_create_code_context_snapshot(self):
        """Test creating a code context snapshot."""
        snapshot = CodeContextSnapshot(
            context_id=1,
            task_id="task-123",
            relevant_files=["src/main.py", "src/utils.py"],
            file_count=2,
            dependency_count=3,
            recent_changes=["Updated main.py", "Fixed utils.py"],
            known_issues=["Import cycle in module X"],
        )

        assert snapshot.context_id == 1
        assert len(snapshot.relevant_files) == 2
        assert snapshot.file_count == 2
        assert len(snapshot.recent_changes) == 2

    def test_create_execution_trace_snapshot(self):
        """Test creating an execution trace snapshot."""
        snapshot = ExecutionTraceSnapshot(
            execution_id="exec-999",
            timestamp=datetime.now(),
            phase="executing",
            outcome="success",
            duration_seconds=45,
        )

        assert snapshot.execution_id == "exec-999"
        assert snapshot.outcome == "success"
        assert snapshot.duration_seconds == 45
        assert snapshot.phase == "executing"

    def test_create_resumption_recommendation(self):
        """Test creating a resumption recommendation."""
        rec = ResumptionRecommendation(
            recommended_next_action="Continue executing cycle #5",
            reason="Last attempt was partial success",
            blockers=["Missing dependency"],
            context_summary="In the middle of implementation",
            estimated_remaining_time_minutes=30,
        )

        assert rec.recommended_next_action == "Continue executing cycle #5"
        assert len(rec.blockers) == 1
        assert rec.estimated_remaining_time_minutes == 30

    def test_create_session_snapshot(self):
        """Test creating a complete session snapshot."""
        project = ProjectContextSnapshot(
            project_id="proj-123",
            project_name="Test Project",
            current_phase="feature_development",
            completed_goals=5,
            in_progress_goals=2,
            blocked_goals=0,
        )

        rec = ResumptionRecommendation(
            recommended_next_action="Continue with Phase 5",
            reason="On schedule",
            context_summary="Ready to implement Phase 5",
        )

        snapshot = SessionSnapshot(
            snapshot_id=str(uuid4()),
            session_id="sess-123",
            project_snapshot=project,
            resumption_recommendation=rec,
            goals_at_snapshot=["Goal 1", "Goal 2"],
            time_in_session_seconds=7200,
        )

        assert snapshot.snapshot_id is not None
        assert snapshot.session_id == "sess-123"
        assert snapshot.status == SessionStatus.PAUSED
        assert snapshot.time_in_session_seconds == 7200


class TestSessionContinuityStore:
    """Test SessionContinuityStore operations."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create test database."""
        return Database(tmp_path / "test.db")

    @pytest.fixture
    def store(self, db):
        """Create store instance."""
        return SessionContinuityStore(db)

    @pytest.fixture
    def sample_project(self):
        """Create sample project snapshot."""
        return ProjectContextSnapshot(
            project_id="proj-123",
            project_name="Memory MCP",
            current_phase="feature_development",
            completed_goals=10,
            in_progress_goals=3,
            blocked_goals=1,
            progress_percentage=77.0,
        )

    @pytest.fixture
    def sample_recommendation(self):
        """Create sample resumption recommendation."""
        return ResumptionRecommendation(
            recommended_next_action="Resume Phase 5 implementation",
            reason="Session paused at checkpoint",
            blockers=[],
            context_summary="Completed models and store, ready for tests",
            estimated_remaining_time_minutes=120,
        )

    def test_save_basic_session(self, store, sample_project, sample_recommendation):
        """Test saving a basic session snapshot."""
        snapshot = store.save_session(
            session_id="sess-001",
            project_snapshot=sample_project,
            resumption_recommendation=sample_recommendation,
            goals_at_snapshot=["Phase 5", "Phase 6"],
            time_in_session_seconds=14400,
        )

        assert snapshot.snapshot_id is not None
        assert snapshot.session_id == "sess-001"
        assert snapshot.status == SessionStatus.PAUSED

    def test_load_saved_session(self, store, sample_project, sample_recommendation):
        """Test loading a saved session snapshot."""
        saved = store.save_session(
            session_id="sess-001",
            project_snapshot=sample_project,
            resumption_recommendation=sample_recommendation,
        )

        loaded = store.load_session(saved.snapshot_id)
        assert loaded is not None
        assert loaded.snapshot_id == saved.snapshot_id
        assert loaded.session_id == "sess-001"
        assert loaded.project_snapshot.project_name == "Memory MCP"

    def test_load_nonexistent_session(self, store):
        """Test loading a non-existent session returns None."""
        result = store.load_session("fake-snapshot-id")
        assert result is None

    def test_save_session_with_cycle(self, store, sample_project, sample_recommendation):
        """Test saving session with active action cycle."""
        cycle = ActionCycleSnapshot(
            cycle_id=42,
            goal_id="goal-123",
            status="executing",
            attempt_count=2,
            max_attempts=5,
            current_step="Running tests",
            goal_description="Implement SessionContinuity",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        snapshot = store.save_session(
            session_id="sess-002",
            project_snapshot=sample_project,
            active_cycle_snapshot=cycle,
            resumption_recommendation=sample_recommendation,
        )

        loaded = store.load_session(snapshot.snapshot_id)
        assert loaded.active_cycle_snapshot is not None
        assert loaded.active_cycle_snapshot.cycle_id == 42
        assert loaded.active_cycle_snapshot.status == "executing"

    def test_save_session_with_code_context(self, store, sample_project, sample_recommendation):
        """Test saving session with code context."""
        code = CodeContextSnapshot(
            context_id=1,
            task_id="task-123",
            relevant_files=["src/session_continuity.py", "src/session_continuity_store.py"],
            file_count=2,
            dependency_count=5,
        )

        snapshot = store.save_session(
            session_id="sess-003",
            project_snapshot=sample_project,
            code_context_snapshot=code,
            resumption_recommendation=sample_recommendation,
        )

        loaded = store.load_session(snapshot.snapshot_id)
        assert loaded.code_context_snapshot is not None
        assert loaded.code_context_snapshot.file_count == 2
        assert "src/session_continuity.py" in loaded.code_context_snapshot.relevant_files

    def test_save_session_with_execution_history(
        self, store, sample_project, sample_recommendation
    ):
        """Test saving session with recent execution traces."""
        executions = [
            ExecutionTraceSnapshot(
                execution_id="exec-1",
                timestamp=datetime.now(),
                phase="executing",
                outcome="success",
                duration_seconds=60,
            ),
            ExecutionTraceSnapshot(
                execution_id="exec-2",
                timestamp=datetime.now(),
                phase="learning",
                outcome="partial",
                duration_seconds=90,
            ),
        ]

        snapshot = store.save_session(
            session_id="sess-004",
            project_snapshot=sample_project,
            recent_executions=executions,
            resumption_recommendation=sample_recommendation,
        )

        loaded = store.load_session(snapshot.snapshot_id)
        assert len(loaded.recent_executions) == 2
        assert loaded.recent_executions[0].execution_id == "exec-1"

    def test_get_resumption_hints(self, store, sample_project, sample_recommendation):
        """Test getting resumption hints for a session."""
        snapshot = store.save_session(
            session_id="sess-005",
            project_snapshot=sample_project,
            resumption_recommendation=sample_recommendation,
        )

        hints = store.get_resumption_hints(snapshot.snapshot_id)
        assert hints is not None
        assert hints.recommended_next_action == "Resume Phase 5 implementation"
        assert hints.estimated_remaining_time_minutes == 120

    def test_list_sessions(self, store, sample_project, sample_recommendation):
        """Test listing all sessions."""
        # Save multiple sessions
        for i in range(3):
            store.save_session(
                session_id=f"sess-{i}",
                project_snapshot=sample_project,
                resumption_recommendation=sample_recommendation,
            )

        sessions = store.list_sessions(limit=10)
        assert len(sessions) == 3
        assert all(s.project_id == "proj-123" for s in sessions)

    def test_list_sessions_by_project(self, store, sample_recommendation):
        """Test filtering sessions by project."""
        proj1 = ProjectContextSnapshot(
            project_id="proj-1",
            project_name="Project 1",
            current_phase="planning",
        )
        proj2 = ProjectContextSnapshot(
            project_id="proj-2",
            project_name="Project 2",
            current_phase="testing",
        )

        store.save_session("sess-1", proj1, resumption_recommendation=sample_recommendation)
        store.save_session("sess-2", proj2, resumption_recommendation=sample_recommendation)

        sessions = store.list_sessions(project_id="proj-1")
        assert len(sessions) == 1
        assert sessions[0].project_id == "proj-1"

    def test_get_latest_session(self, store, sample_project, sample_recommendation):
        """Test getting the most recent session for a session_id."""
        session_id = "sess-repeat"

        snap1 = store.save_session(
            session_id=session_id,
            project_snapshot=sample_project,
            resumption_recommendation=sample_recommendation,
        )
        time.sleep(1.1)  # Sleep > 1 second to ensure different integer timestamp
        snap2 = store.save_session(
            session_id=session_id,
            project_snapshot=sample_project,
            resumption_recommendation=sample_recommendation,
        )

        latest = store.get_latest_session(session_id)
        assert latest.snapshot_id == snap2.snapshot_id

    def test_mark_session_resumed(self, store, sample_project, sample_recommendation):
        """Test marking a session as resumed."""
        snapshot = store.save_session(
            session_id="sess-006",
            project_snapshot=sample_project,
            resumption_recommendation=sample_recommendation,
        )

        success = store.mark_session_resumed(snapshot.snapshot_id)
        assert success

        loaded = store.load_session(snapshot.snapshot_id)
        assert loaded.status == SessionStatus.RESUMED

    def test_delete_session(self, store, sample_project, sample_recommendation):
        """Test deleting a session snapshot."""
        snapshot = store.save_session(
            session_id="sess-007",
            project_snapshot=sample_project,
            resumption_recommendation=sample_recommendation,
        )

        success = store.delete_session(snapshot.snapshot_id)
        assert success

        loaded = store.load_session(snapshot.snapshot_id)
        assert loaded is None

    def test_session_snapshot_with_metadata(self, store, sample_project, sample_recommendation):
        """Test that session metadata is created alongside snapshot."""
        snapshot = store.save_session(
            session_id="sess-008",
            project_snapshot=sample_project,
            resumption_recommendation=sample_recommendation,
            goals_at_snapshot=["Goal A", "Goal B", "Goal C"],
        )

        sessions = store.list_sessions(project_id="proj-123")
        metadata = [s for s in sessions if s.snapshot_id == snapshot.snapshot_id]
        assert len(metadata) == 1
        assert metadata[0].active_goal_count == 3


class TestSessionContinuityMCPTools:
    """Test SessionContinuity MCP tools."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create test database."""
        return Database(tmp_path / "test.db")

    @pytest.fixture
    def tools(self, db):
        """Create MCP tools instance."""
        return SessionContinuityMCPTools(db)

    def test_get_tools_returns_list(self, tools):
        """Test that get_tools returns a list of Tool definitions."""
        tools_list = tools.get_tools()
        assert isinstance(tools_list, list)
        assert len(tools_list) > 0
        assert all(hasattr(t, "name") for t in tools_list)

    def test_save_session_tool(self, tools):
        """Test save_session MCP tool."""
        result = tools.handle_tool_call(
            "save_session",
            {
                "session_id": "sess-test",
                "project_id": "proj-123",
                "project_name": "Test Project",
                "current_phase": "feature_development",
                "completed_goals": 5,
                "in_progress_goals": 2,
                "blocked_goals": 0,
                "progress_percentage": 77.0,
                "resumption_advice": "Continue with Phase 5",
                "time_in_session_seconds": 14400,
                "primary_objective": "Complete SessionContinuity layer",
            },
        )

        assert result["status"] == "success"
        assert "snapshot_id" in result

    def test_load_session_tool(self, tools):
        """Test load_session MCP tool."""
        # First save
        save_result = tools.handle_tool_call(
            "save_session",
            {
                "session_id": "sess-test",
                "project_id": "proj-123",
                "project_name": "Test Project",
                "current_phase": "feature_development",
                "completed_goals": 5,
                "in_progress_goals": 2,
                "blocked_goals": 0,
                "progress_percentage": 77.0,
                "resumption_advice": "Continue with Phase 5",
            },
        )

        # Then load
        load_result = tools.handle_tool_call(
            "load_session",
            {"snapshot_id": save_result["snapshot_id"]},
        )

        assert load_result["status"] == "success"
        assert load_result["project"] == "Test Project"
        assert load_result["phase"] == "feature_development"

    def test_get_resumption_hints_tool(self, tools):
        """Test get_resumption_hints MCP tool."""
        # First save
        save_result = tools.handle_tool_call(
            "save_session",
            {
                "session_id": "sess-test",
                "project_id": "proj-123",
                "project_name": "Test Project",
                "current_phase": "feature_development",
                "completed_goals": 5,
                "in_progress_goals": 2,
                "blocked_goals": 0,
                "progress_percentage": 77.0,
                "resumption_advice": "Continue with Phase 5",
            },
        )

        # Get hints
        hints_result = tools.handle_tool_call(
            "get_resumption_hints",
            {"snapshot_id": save_result["snapshot_id"]},
        )

        assert hints_result["status"] == "success"
        assert "next_action" in hints_result
        assert "context" in hints_result

    def test_list_sessions_tool(self, tools):
        """Test list_sessions MCP tool."""
        # Save a session
        tools.handle_tool_call(
            "save_session",
            {
                "session_id": "sess-test",
                "project_id": "proj-123",
                "project_name": "Test Project",
                "current_phase": "feature_development",
                "completed_goals": 5,
                "in_progress_goals": 2,
                "blocked_goals": 0,
                "progress_percentage": 77.0,
                "resumption_advice": "Continue",
            },
        )

        # List sessions
        result = tools.handle_tool_call("list_sessions", {"limit": 10})

        assert result["status"] == "success"
        assert result["count"] > 0

    def test_mark_session_resumed_tool(self, tools):
        """Test mark_session_resumed MCP tool."""
        # First save
        save_result = tools.handle_tool_call(
            "save_session",
            {
                "session_id": "sess-test",
                "project_id": "proj-123",
                "project_name": "Test Project",
                "current_phase": "feature_development",
                "completed_goals": 5,
                "in_progress_goals": 2,
                "blocked_goals": 0,
                "progress_percentage": 77.0,
                "resumption_advice": "Continue",
            },
        )

        # Mark as resumed
        result = tools.handle_tool_call(
            "mark_session_resumed",
            {"snapshot_id": save_result["snapshot_id"]},
        )

        assert result["status"] == "success"
