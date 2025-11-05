"""Tests for procedural memory extraction."""

from datetime import datetime, timedelta

import pytest

from athena.core.database import Database
from athena.episodic.models import EpisodicEvent, EventContext, EventType
from athena.episodic.store import EpisodicStore
from athena.procedural.extraction import (
    extract_procedures_from_patterns,
    suggest_procedure_for_context,
)
from athena.procedural.models import Procedure, ProcedureCategory
from athena.procedural.store import ProceduralStore


@pytest.fixture
def db():
    """Create in-memory database."""
    return Database(":memory:")


@pytest.fixture
def episodic_store(db):
    """Create episodic store."""
    return EpisodicStore(db)


@pytest.fixture
def procedural_store(db):
    """Create procedural store."""
    return ProceduralStore(db)


@pytest.fixture
def project_id():
    """Return test project ID."""
    return 1


def test_extract_tdd_procedure(db, project_id, episodic_store, procedural_store):
    """Test extracting TDD procedure from repeated pattern."""
    session_id = "test_session"
    base_time = datetime.now()

    # Create 3 instances of TDD cycle pattern
    for i in range(3):
        offset_hours = i * 2
        events = [
            EpisodicEvent(
                project_id=project_id,
                session_id=f"{session_id}_{i}",
                event_type=EventType.FILE_CHANGE,
                content="Write failing test for authentication",
                outcome="success",
                timestamp=base_time - timedelta(hours=offset_hours, minutes=10),
                context=EventContext(cwd="/project/tests"),
            ),
            EpisodicEvent(
                project_id=project_id,
                session_id=f"{session_id}_{i}",
                event_type=EventType.FILE_CHANGE,
                content="Implement authentication code",
                outcome="success",
                timestamp=base_time - timedelta(hours=offset_hours, minutes=5),
                context=EventContext(cwd="/project/src"),
            ),
            EpisodicEvent(
                project_id=project_id,
                session_id=f"{session_id}_{i}",
                event_type=EventType.ACTION,
                content="Run tests",
                outcome="success",
                timestamp=base_time - timedelta(hours=offset_hours),
                context=EventContext(cwd="/project"),
            ),
        ]

        # Record events
        for event in events:
            event_id = episodic_store.record_event(event)
            event.id = event_id

    # Extract procedures
    procedures = extract_procedures_from_patterns(
        project_id=project_id,
        episodic_store=episodic_store,
        procedural_store=procedural_store,
        min_occurrences=3,
        lookback_days=1,
    )

    # Verify extraction
    assert len(procedures) >= 1

    # Check procedure properties
    procedure = procedures[0]
    assert procedure.id is not None
    assert procedure.category == ProcedureCategory.TESTING
    assert procedure.success_rate > 0
    assert procedure.usage_count == 3
    assert len(procedure.steps) >= 3
    assert procedure.created_by == "learned"


def test_extract_git_workflow_procedure(db, project_id, episodic_store, procedural_store):
    """Test extracting git commit workflow."""
    session_id = "git_session"
    base_time = datetime.now()

    # Create 4 instances of git workflow
    for i in range(4):
        offset_hours = i * 3
        events = [
            EpisodicEvent(
                project_id=project_id,
                session_id=f"{session_id}_{i}",
                event_type=EventType.ACTION,
                content="git status",
                outcome="success",
                timestamp=base_time - timedelta(hours=offset_hours, minutes=15),
                context=EventContext(cwd="/project"),
            ),
            EpisodicEvent(
                project_id=project_id,
                session_id=f"{session_id}_{i}",
                event_type=EventType.ACTION,
                content="git add files",
                outcome="success",
                timestamp=base_time - timedelta(hours=offset_hours, minutes=10),
                context=EventContext(cwd="/project"),
            ),
            EpisodicEvent(
                project_id=project_id,
                session_id=f"{session_id}_{i}",
                event_type=EventType.ACTION,
                content="git commit with message",
                outcome="success",
                timestamp=base_time - timedelta(hours=offset_hours, minutes=5),
                context=EventContext(cwd="/project"),
            ),
        ]

        # Record events
        for event in events:
            event_id = episodic_store.record_event(event)
            event.id = event_id

    # Extract procedures
    procedures = extract_procedures_from_patterns(
        project_id=project_id,
        episodic_store=episodic_store,
        procedural_store=procedural_store,
        min_occurrences=3,
        lookback_days=1,
    )

    # Verify
    assert len(procedures) >= 1
    procedure = procedures[0]
    assert procedure.category == ProcedureCategory.GIT
    assert "git" in procedure.name
    assert len(procedure.examples) > 0


def test_suggest_procedure_for_context(db, procedural_store):
    """Test procedure suggestion based on context."""
    # Create test procedures
    procedures = [
        Procedure(
            name="tdd_workflow",
            category=ProcedureCategory.TESTING,
            description="Test-driven development workflow",
            template="1. Write test\n2. Implement\n3. Run tests",
            applicable_contexts=["testing", "tdd", "pytest"],
            success_rate=0.9,
            usage_count=10,
        ),
        Procedure(
            name="debug_workflow",
            category=ProcedureCategory.DEBUGGING,
            description="Debugging workflow",
            template="1. Reproduce error\n2. Add logging\n3. Fix",
            applicable_contexts=["debugging", "errors"],
            success_rate=0.7,
            usage_count=5,
        ),
        Procedure(
            name="git_commit",
            category=ProcedureCategory.GIT,
            description="Git commit workflow",
            template="1. Status\n2. Add\n3. Commit",
            applicable_contexts=["git", "version-control"],
            success_rate=0.95,
            usage_count=20,
        ),
    ]

    for proc in procedures:
        procedural_store.create_procedure(proc)

    # Test suggestion for testing context
    suggestions = suggest_procedure_for_context(
        context="test workflow",
        applicable_contexts=["testing", "pytest"],
        procedural_store=procedural_store,
        top_k=3,
    )

    assert len(suggestions) >= 1
    assert suggestions[0].name == "tdd_workflow"

    # Test suggestion for git context
    suggestions = suggest_procedure_for_context(
        context="git workflow",
        applicable_contexts=["git"],
        procedural_store=procedural_store,
        top_k=3,
    )

    assert len(suggestions) >= 1
    assert suggestions[0].name == "git_commit"


def test_no_procedures_for_insufficient_patterns(db, project_id, episodic_store, procedural_store):
    """Test that procedures aren't extracted with insufficient occurrences."""
    session_id = "single_session"
    base_time = datetime.now()

    # Create only 1 instance (below min_occurrences=3)
    events = [
        EpisodicEvent(
            project_id=project_id,
            session_id=session_id,
            event_type=EventType.FILE_CHANGE,
            content="Make change",
            outcome="success",
            timestamp=base_time - timedelta(minutes=10),
            context=EventContext(cwd="/project"),
        ),
        EpisodicEvent(
            project_id=project_id,
            session_id=session_id,
            event_type=EventType.ACTION,
            content="Run build",
            outcome="success",
            timestamp=base_time - timedelta(minutes=5),
            context=EventContext(cwd="/project"),
        ),
    ]

    for event in events:
        event_id = episodic_store.record_event(event)
        event.id = event_id

    # Try to extract procedures
    procedures = extract_procedures_from_patterns(
        project_id=project_id,
        episodic_store=episodic_store,
        procedural_store=procedural_store,
        min_occurrences=3,
        lookback_days=1,
    )

    # Should extract nothing
    assert len(procedures) == 0


def test_procedure_deduplication(db, procedural_store):
    """Test that duplicate procedures aren't created."""
    # Create a test procedure
    proc1 = Procedure(
        name="test_workflow",
        category=ProcedureCategory.TESTING,
        description="Test workflow",
        template="1. Step 1\n2. Step 2",
        applicable_contexts=["testing"],
        success_rate=0.9,
        usage_count=5,
    )

    proc_id1 = procedural_store.create_procedure(proc1)
    assert proc_id1 is not None

    # Try to create the same procedure again - should fail due to unique name constraint
    proc2 = Procedure(
        name="test_workflow",  # Same name
        category=ProcedureCategory.DEBUGGING,
        description="Different description",
        template="Different template",
        applicable_contexts=["debugging"],
        success_rate=0.5,
        usage_count=1,
    )

    # SQLite will raise IntegrityError for duplicate name
    import sqlite3
    try:
        procedural_store.create_procedure(proc2)
        assert False, "Should have raised IntegrityError for duplicate name"
    except sqlite3.IntegrityError:
        pass  # Expected

    # Verify only one procedure exists
    procedures = procedural_store.list_procedures()
    assert len(procedures) == 1
    assert procedures[0].name == "test_workflow"
    assert procedures[0].description == "Test workflow"  # Original, not duplicate
