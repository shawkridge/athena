"""Shared pytest fixtures for Phase 1 (Memory API Exposure) tests.

This module provides reusable fixtures for all Phase 1 tests including:
- Temporary databases
- Memory API instances
- Sample data generators
- Mock stores and managers
"""

import tempfile
from pathlib import Path
from datetime import datetime

import pytest

from athena.core.database import Database
from athena.core.models import MemoryType
from athena.episodic.models import EpisodicEvent, EventType, EventOutcome, EventContext
from athena.episodic.store import EpisodicStore
from athena.memory.store import MemoryStore
from athena.procedural.models import Procedure, ProcedureCategory
from athena.procedural.store import ProceduralStore
from athena.prospective.models import ProspectiveTask, TaskStatus, TaskPriority, TaskPhase
from athena.prospective.store import ProspectiveStore
from athena.graph.models import Entity, Relation, EntityType, RelationType
from athena.graph.store import GraphStore
from athena.meta.store import MetaMemoryStore
from athena.consolidation.system import ConsolidationSystem
from athena.manager import UnifiedMemoryManager
from athena.projects.manager import ProjectManager
from athena.mcp.memory_api import MemoryAPI
from athena.sandbox.config import SandboxConfig, SandboxMode, ExecutionLanguage


# ==== DATABASE FIXTURES ====

@pytest.fixture
def temp_db():
    """Create a temporary in-memory database for testing.

    Returns:
        Database: Temporary test database that's cleaned up after test
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(str(db_path))
        yield db
        db.conn.close()


@pytest.fixture
def temp_db_path():
    """Create a temporary database path (without creating the database).

    Returns:
        Path: Temporary database path
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.db"


# ==== MEMORY LAYER FIXTURES ====

@pytest.fixture
def episodic_store(temp_db):
    """Create an EpisodicStore with temporary database.

    Args:
        temp_db: Temporary test database

    Returns:
        EpisodicStore: Episodic memory store instance
    """
    return EpisodicStore(temp_db)


@pytest.fixture
def semantic_store(temp_db):
    """Create a MemoryStore (semantic) with temporary database.

    Args:
        temp_db: Temporary test database

    Returns:
        MemoryStore: Semantic memory store instance
    """
    return MemoryStore(temp_db)


@pytest.fixture
def procedural_store(temp_db):
    """Create a ProceduralStore with temporary database.

    Args:
        temp_db: Temporary test database

    Returns:
        ProceduralStore: Procedural memory store instance
    """
    return ProceduralStore(temp_db)


@pytest.fixture
def prospective_store(temp_db):
    """Create a ProspectiveStore with temporary database.

    Args:
        temp_db: Temporary test database

    Returns:
        ProspectiveStore: Prospective memory store instance
    """
    return ProspectiveStore(temp_db)


@pytest.fixture
def graph_store(temp_db):
    """Create a GraphStore with temporary database.

    Args:
        temp_db: Temporary test database

    Returns:
        GraphStore: Knowledge graph store instance
    """
    return GraphStore(temp_db)


@pytest.fixture
def meta_store(temp_db):
    """Create a MetaMemoryStore with temporary database.

    Args:
        temp_db: Temporary test database

    Returns:
        MetaMemoryStore: Meta-memory store instance
    """
    return MetaMemoryStore(temp_db)


@pytest.fixture
def consolidation_system(temp_db, episodic_store):
    """Create a ConsolidationSystem with temporary database.

    Args:
        temp_db: Temporary test database
        episodic_store: Episodic store for consolidation

    Returns:
        ConsolidationSystem: Consolidation system instance
    """
    return ConsolidationSystem(episodic_store, temp_db)


# ==== MANAGER FIXTURES ====

@pytest.fixture
def project_manager(temp_db):
    """Create a ProjectManager with temporary database.

    Args:
        temp_db: Temporary test database

    Returns:
        ProjectManager: Project manager instance
    """
    return ProjectManager(temp_db)


@pytest.fixture
def unified_manager(
    temp_db,
    semantic_store,
    episodic_store,
    procedural_store,
    prospective_store,
    graph_store,
    meta_store,
    consolidation_system,
    project_manager,
):
    """Create a UnifiedMemoryManager with all layers.

    Args:
        temp_db: Temporary test database
        semantic_store: Semantic memory layer
        episodic_store: Episodic memory layer
        procedural_store: Procedural memory layer
        prospective_store: Prospective memory layer
        graph_store: Knowledge graph layer
        meta_store: Meta-memory layer
        consolidation_system: Consolidation system
        project_manager: Project manager

    Returns:
        UnifiedMemoryManager: Unified manager instance
    """
    return UnifiedMemoryManager(
        semantic=semantic_store,
        episodic=episodic_store,
        procedural=procedural_store,
        prospective=prospective_store,
        graph=graph_store,
        meta=meta_store,
        consolidation=consolidation_system,
        project_manager=project_manager,
    )


# ==== MEMORY API FIXTURES ====

@pytest.fixture
def memory_api(temp_db_path):
    """Create a MemoryAPI instance with temporary database.

    Args:
        temp_db_path: Path to temporary database

    Returns:
        MemoryAPI: Memory API instance
    """
    return MemoryAPI.create(db_path=str(temp_db_path))


@pytest.fixture
def memory_api_direct(unified_manager, project_manager, temp_db):
    """Create a MemoryAPI instance directly (for more control in tests).

    Args:
        unified_manager: Unified memory manager
        project_manager: Project manager
        temp_db: Temporary test database

    Returns:
        MemoryAPI: Memory API instance
    """
    return MemoryAPI(unified_manager, project_manager, temp_db)


# ==== SANDBOX CONFIG FIXTURES ====

@pytest.fixture
def sandbox_config_srt():
    """Create a SandboxConfig with SRT mode.

    Returns:
        SandboxConfig: Sandbox configuration in SRT mode
    """
    return SandboxConfig(
        mode=SandboxMode.SRT,
        enabled=True,
        allowed_languages=[ExecutionLanguage.PYTHON],
    )


@pytest.fixture
def sandbox_config_restricted():
    """Create a SandboxConfig with restricted mode.

    Returns:
        SandboxConfig: Sandbox configuration in restricted mode
    """
    return SandboxConfig(
        mode=SandboxMode.RESTRICTED,
        enabled=True,
        allowed_languages=[ExecutionLanguage.PYTHON, ExecutionLanguage.JAVASCRIPT],
    )


@pytest.fixture
def sandbox_config_mock():
    """Create a SandboxConfig with mock mode.

    Returns:
        SandboxConfig: Sandbox configuration in mock mode
    """
    return SandboxConfig(
        mode=SandboxMode.MOCK,
        enabled=True,
        allowed_languages=[
            ExecutionLanguage.PYTHON,
            ExecutionLanguage.JAVASCRIPT,
            ExecutionLanguage.BASH,
        ],
    )


# ==== SAMPLE DATA FIXTURES ====

@pytest.fixture
def sample_memory_content():
    """Provide sample memory content for testing.

    Returns:
        dict: Dictionary with various memory content samples
    """
    return {
        "semantic": "This is an important fact about the system architecture",
        "event": "Ran test suite and fixed 3 bugs",
        "procedure": "How to deploy to production safely",
        "task": "Implement user authentication system",
    }


@pytest.fixture
def sample_episodic_event(project_manager):
    """Create a sample episodic event for testing.

    Args:
        project_manager: Project manager to get project

    Returns:
        EpisodicEvent: Sample episodic event
    """
    project = project_manager.get_or_create_project()

    return EpisodicEvent(
        project_id=project.id,
        session_id="test_session_001",
        event_type=EventType.ACTION,
        content="Tested the memory API integration",
        timestamp=datetime.now(),
        outcome=EventOutcome.SUCCESS,
        context=EventContext(
            working_directory="/home/user/.work/athena",
            files=["src/athena/mcp/memory_api.py", "tests/unit/test_memory_api.py"],
            metadata={"test_count": 42, "failures": 0},
        ),
    )


@pytest.fixture
def sample_procedure(project_manager):
    """Create a sample procedure for testing.

    Args:
        project_manager: Project manager to get project

    Returns:
        Procedure: Sample procedure
    """
    project = project_manager.get_or_create_project()

    return Procedure(
        project_id=project.id,
        name="test_procedure",
        description="A test procedure for unit testing",
        category=ProcedureCategory.SYSTEM,
        steps=["Step 1: Initialize", "Step 2: Execute", "Step 3: Verify"],
        prerequisites=["Python 3.10+", "SQLite3"],
    )


@pytest.fixture
def sample_task(project_manager):
    """Create a sample prospective task for testing.

    Args:
        project_manager: Project manager to get project

    Returns:
        ProspectiveTask: Sample task
    """
    project = project_manager.get_or_create_project()

    return ProspectiveTask(
        project_id=project.id,
        title="Test Memory API Integration",
        description="Write comprehensive tests for Phase 1 API",
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.HIGH,
        phase=TaskPhase.ACTIVE,
        due_date=None,
    )


@pytest.fixture
def sample_entity(project_manager):
    """Create a sample knowledge graph entity for testing.

    Args:
        project_manager: Project manager to get project

    Returns:
        Entity: Sample entity
    """
    project = project_manager.get_or_create_project()

    return Entity(
        project_id=project.id,
        name="MemoryAPI",
        entity_type=EntityType.CONCEPT,
        description="Direct Python API for memory operations",
        properties={"version": "1.0", "paradigm": "code-execution"},
    )
