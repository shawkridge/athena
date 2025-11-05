"""Phase 7.2 Spatial-Temporal Grounding unit tests.

Tests for:
- SpatialGrounder: Code-to-spatial linking
- TemporalChainer: Event sequencing and causality
- GraphLinker: Entity relationships
- Phase72MCPTools: MCP tool integration
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

from athena.core.database import Database
from athena.ai_coordination.integration.spatial_grounding import SpatialGrounder
from athena.ai_coordination.integration.temporal_chaining import TemporalChainer
from athena.ai_coordination.integration.graph_linking import (
    GraphLinker,
    EntityType,
    RelationType,
)
from athena.ai_coordination.integration.phase7_2_mcp_tools import Phase72MCPTools


class TestSpatialGrounder:
    """Tests for SpatialGrounder spatial linking."""

    def test_spatial_grounding_initialization(self, tmp_path):
        """Test SpatialGrounder initializes and creates schema."""
        db = Database(tmp_path / "test.db")
        grounder = SpatialGrounder(db)

        # Check tables exist
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('integration_links', 'graph_entity_refs')
        """)
        tables = [row[0] for row in cursor.fetchall()]
        assert "integration_links" in tables
        assert "graph_entity_refs" in tables

    def test_link_code_context_to_spatial(self, tmp_path):
        """Test linking code context to spatial hierarchy."""
        db = Database(tmp_path / "test.db")
        grounder = SpatialGrounder(db)

        # Create mock code context
        class MockCodeContext:
            context_id = "ctx_1"
            relevant_files = ["src/auth/login.py", "src/auth/token.py"]
            file_count = 2
            dependency_types = []

        code_context = MockCodeContext()
        link_count = grounder.link_code_context_to_spatial(code_context, 1, "task_1")

        assert link_count == 2

    def test_get_files_for_task(self, tmp_path):
        """Test retrieving files involved in a task."""
        db = Database(tmp_path / "test.db")
        grounder = SpatialGrounder(db)

        # Create mock code context
        class MockCodeContext:
            context_id = "ctx_1"
            relevant_files = ["src/auth/login.py", "src/auth/token.py"]
            file_count = 2
            dependency_types = []

        code_context = MockCodeContext()
        grounder.link_code_context_to_spatial(code_context, 1, "task_123")

        files = grounder.get_files_for_task("task_123")
        assert len(files) == 2
        assert "src/auth/login.py" in files

    def test_record_file_access(self, tmp_path):
        """Test recording file access during execution."""
        db = Database(tmp_path / "test.db")
        grounder = SpatialGrounder(db)

        link_id = grounder.record_file_access(
            "src/core/main.py",
            "write",
            "exec_1",
            1
        )

        assert link_id is not None

    def test_get_execution_locations(self, tmp_path):
        """Test retrieving all code locations accessed during execution."""
        db = Database(tmp_path / "test.db")
        grounder = SpatialGrounder(db)

        grounder.record_file_access("src/core/main.py", "read", "exec_1", 1)
        grounder.record_file_access("src/auth/login.py", "write", "exec_1", 1)

        locations = grounder.get_execution_locations("exec_1")
        assert len(locations) == 2
        files = [loc.get("file_path") for loc in locations]
        assert "src/core/main.py" in files

    def test_get_spatial_context(self, tmp_path):
        """Test retrieving spatial context for an episodic event."""
        db = Database(tmp_path / "test.db")
        grounder = SpatialGrounder(db)

        # Add some spatial links
        grounder.record_file_access("src/auth/login.py", "read", "exec_1", 1)
        grounder.record_file_access("src/auth/token.py", "write", "exec_1", 1)

        context = grounder.get_spatial_context(1)
        assert "files" in context
        assert len(context["files"]) >= 2


class TestTemporalChainer:
    """Tests for TemporalChainer temporal chain building."""

    def test_temporal_chaining_initialization(self, tmp_path):
        """Test TemporalChainer initializes and creates schema."""
        db = Database(tmp_path / "test.db")
        chainer = TemporalChainer(db)

        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('temporal_chains', 'execution_sequences')
        """)
        tables = [row[0] for row in cursor.fetchall()]
        assert "temporal_chains" in tables
        assert "execution_sequences" in tables

    def test_link_temporal_events_immediately_after(self, tmp_path):
        """Test linking events with 'immediately_after' relationship."""
        db = Database(tmp_path / "test.db")
        chainer = TemporalChainer(db)

        now = int(datetime.now().timestamp() * 1000)
        later = now + 2 * 60 * 1000  # 2 minutes later

        chain_id = chainer.link_temporal_events(
            1, 2,  # event IDs
            now, later,  # timestamps
            session_continuity=True
        )

        assert chain_id is not None
        assert chain_id > 0

    def test_link_temporal_events_shortly_after(self, tmp_path):
        """Test linking events with 'shortly_after' relationship."""
        db = Database(tmp_path / "test.db")
        chainer = TemporalChainer(db)

        now = int(datetime.now().timestamp() * 1000)
        later = now + 30 * 60 * 1000  # 30 minutes later

        chain_id = chainer.link_temporal_events(1, 2, now, later)
        assert chain_id is not None

    def test_link_temporal_events_causal_strength(self, tmp_path):
        """Test that causal strength is calculated correctly."""
        db = Database(tmp_path / "test.db")
        chainer = TemporalChainer(db)

        now = int(datetime.now().timestamp() * 1000)
        later = now + 2 * 60 * 1000

        # Link with both session continuity and file overlap
        chainer.link_temporal_events(
            1, 2, now, later,
            session_continuity=True,
            file_overlap=True
        )

        cursor = db.conn.cursor()
        cursor.execute("SELECT causal_strength FROM temporal_chains LIMIT 1")
        strength = cursor.fetchone()[0]
        assert strength > 0.8  # Should be high with both continuity and overlap

    def test_build_session_sequence(self, tmp_path):
        """Test building execution sequence for a session."""
        db = Database(tmp_path / "test.db")

        # Create episodic events for sequence
        from athena.episodic.store import EpisodicStore
        from athena.episodic.models import EpisodicEvent, EventType, EventOutcome

        episodic_store = EpisodicStore(db)
        chainer = TemporalChainer(db)

        # Create mock events
        for i in range(3):
            event = EpisodicEvent(
                project_id=1,
                session_id="session_1",
                event_type=EventType.ACTION,
                content=f"Action {i}",
                outcome=EventOutcome.SUCCESS,
            )
            episodic_store.record_event(event)

        # Build sequence
        count = chainer.build_session_sequence("session_1", "goal_1", "task_1")
        assert count >= 3

    def test_get_temporal_chain(self, tmp_path):
        """Test retrieving temporal chain for an event."""
        db = Database(tmp_path / "test.db")
        chainer = TemporalChainer(db)

        now = int(datetime.now().timestamp() * 1000)
        chainer.link_temporal_events(1, 2, now, now + 2 * 60 * 1000)

        chain = chainer.get_temporal_chain(2)
        assert "predecessors" in chain
        assert "successors" in chain
        assert len(chain["predecessors"]) > 0

    def test_detect_event_patterns(self, tmp_path):
        """Test detecting repeating patterns in event sequence."""
        db = Database(tmp_path / "test.db")
        from athena.episodic.store import EpisodicStore
        from athena.episodic.models import EpisodicEvent, EventType, EventOutcome

        episodic_store = EpisodicStore(db)
        chainer = TemporalChainer(db)

        # Create repeating pattern: A, B, C, A, B, C
        for letter in ["A", "B", "C", "A", "B", "C"]:
            event = EpisodicEvent(
                project_id=1,
                session_id="session_pattern",
                event_type=EventType.ACTION,
                content=f"Event {letter}",
                outcome=EventOutcome.SUCCESS,
            )
            episodic_store.record_event(event)

        chainer.build_session_sequence("session_pattern", goal_id="goal_1", task_id="task_1")

        # Pattern detection should run without error
        # (may or may not find patterns depending on sequence layout)
        patterns = chainer.detect_event_patterns("session_pattern", pattern_length=2)
        assert isinstance(patterns, list)

    def test_calculate_sequence_metrics(self, tmp_path):
        """Test calculating metrics for a session."""
        db = Database(tmp_path / "test.db")
        from athena.episodic.store import EpisodicStore
        from athena.episodic.models import EpisodicEvent, EventType, EventOutcome

        episodic_store = EpisodicStore(db)
        chainer = TemporalChainer(db)

        # Create events
        for i in range(5):
            event = EpisodicEvent(
                project_id=1,
                session_id="session_metrics",
                event_type=EventType.ACTION,
                content=f"Event {i}",
                outcome=EventOutcome.SUCCESS,
            )
            episodic_store.record_event(event)

        chainer.build_session_sequence("session_metrics", goal_id="goal_1", task_id="task_1")
        metrics = chainer.calculate_sequence_metrics("session_metrics")

        assert "event_count" in metrics
        assert "outcomes" in metrics
        assert metrics["event_count"] >= 5


class TestGraphLinker:
    """Tests for GraphLinker entity relationships."""

    def test_graph_linker_initialization(self, tmp_path):
        """Test GraphLinker initializes and creates schema."""
        db = Database(tmp_path / "test.db")
        linker = GraphLinker(db)

        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('graph_entity_nodes', 'graph_entity_relationships')
        """)
        tables = [row[0] for row in cursor.fetchall()]
        assert "graph_entity_nodes" in tables
        assert "graph_entity_relationships" in tables

    def test_create_entity(self, tmp_path):
        """Test creating entity nodes."""
        db = Database(tmp_path / "test.db")
        linker = GraphLinker(db)

        entity_id = linker.create_entity(
            "auth_module",
            EntityType.MODULE,
            "coordination",
            source_id=1
        )

        assert entity_id is not None
        assert entity_id > 0

    def test_create_entity_idempotent(self, tmp_path):
        """Test that creating same entity returns same ID."""
        db = Database(tmp_path / "test.db")
        linker = GraphLinker(db)

        id1 = linker.create_entity("auth", EntityType.MODULE, "coordination")
        id2 = linker.create_entity("auth", EntityType.MODULE, "coordination")

        assert id1 == id2

    def test_link_entities(self, tmp_path):
        """Test creating relationships between entities."""
        db = Database(tmp_path / "test.db")
        linker = GraphLinker(db)

        file_id = linker.create_entity("login.py", EntityType.FILE, "coordination")
        func_id = linker.create_entity("validate_user", EntityType.FUNCTION, "coordination")

        rel_id = linker.link_entities(
            file_id, func_id,
            RelationType.IMPLEMENTS,
            strength=0.9
        )

        assert rel_id is not None
        assert rel_id > 0

    def test_get_entity(self, tmp_path):
        """Test retrieving entity details."""
        db = Database(tmp_path / "test.db")
        linker = GraphLinker(db)

        linker.create_entity(
            "auth_module",
            EntityType.MODULE,
            "coordination",
            description="Authentication module"
        )

        entity = linker.get_entity("auth_module", EntityType.MODULE)
        assert entity is not None
        assert entity["name"] == "auth_module"
        assert entity["type"] == "module"

    def test_get_relationships(self, tmp_path):
        """Test retrieving relationships for an entity."""
        db = Database(tmp_path / "test.db")
        linker = GraphLinker(db)

        file_id = linker.create_entity("login.py", EntityType.FILE, "coordination")
        func_id = linker.create_entity("auth_check", EntityType.FUNCTION, "coordination")

        linker.link_entities(file_id, func_id, RelationType.IMPLEMENTS)

        rels = linker.get_relationships(file_id)
        assert len(rels) > 0
        assert any(r["relation_type"] == "implements" for r in rels)

    def test_traverse_graph(self, tmp_path):
        """Test graph traversal."""
        db = Database(tmp_path / "test.db")
        linker = GraphLinker(db)

        # Create a small graph: A -> B -> C
        a = linker.create_entity("entity_a", EntityType.MODULE, "coordination")
        b = linker.create_entity("entity_b", EntityType.MODULE, "coordination")
        c = linker.create_entity("entity_c", EntityType.MODULE, "coordination")

        linker.link_entities(a, b, RelationType.DEPENDS_ON)
        linker.link_entities(b, c, RelationType.DEPENDS_ON)

        graph = linker.traverse_graph(a, max_depth=2)
        assert len(graph["nodes"]) >= 2
        assert len(graph["edges"]) >= 1

    def test_find_paths(self, tmp_path):
        """Test finding paths between entities."""
        db = Database(tmp_path / "test.db")
        linker = GraphLinker(db)

        # Create a graph with multiple paths
        a = linker.create_entity("start", EntityType.MODULE, "coordination")
        b = linker.create_entity("middle", EntityType.MODULE, "coordination")
        c = linker.create_entity("end", EntityType.MODULE, "coordination")

        linker.link_entities(a, b, RelationType.USES)
        linker.link_entities(b, c, RelationType.USES)
        linker.link_entities(a, c, RelationType.USES)

        paths = linker.find_paths(a, c, max_depth=3)
        assert len(paths) > 0

    def test_get_entity_stats(self, tmp_path):
        """Test retrieving entity statistics."""
        db = Database(tmp_path / "test.db")
        linker = GraphLinker(db)

        hub = linker.create_entity("hub", EntityType.MODULE, "coordination")
        dep1 = linker.create_entity("dep1", EntityType.MODULE, "coordination")
        dep2 = linker.create_entity("dep2", EntityType.MODULE, "coordination")

        linker.link_entities(hub, dep1, RelationType.USES)
        linker.link_entities(hub, dep2, RelationType.USES)
        linker.link_entities(dep1, hub, RelationType.IMPLEMENTS)

        stats = linker.get_entity_stats(hub)
        assert stats["total_outgoing"] >= 2
        assert stats["total_incoming"] >= 1


class TestPhase72MCPTools:
    """Tests for Phase 7.2 MCP tool integration."""

    def test_mcp_tools_initialization(self, tmp_path):
        """Test Phase72MCPTools initializes with components."""
        db = Database(tmp_path / "test.db")
        spatial = SpatialGrounder(db)
        temporal = TemporalChainer(db)
        graph = GraphLinker(db)

        tools = Phase72MCPTools(spatial, temporal, graph)
        assert tools.spatial is not None
        assert tools.temporal is not None
        assert tools.graph is not None

    def test_link_code_to_spatial_tool(self, tmp_path):
        """Test link_code_to_spatial MCP tool."""
        db = Database(tmp_path / "test.db")
        spatial = SpatialGrounder(db)
        temporal = TemporalChainer(db)
        graph = GraphLinker(db)

        tools = Phase72MCPTools(spatial, temporal, graph)

        result = tools.link_code_to_spatial(
            "task_1",
            ["src/auth/login.py", "src/auth/token.py"],
            1
        )

        assert result["status"] == "success"
        assert result["file_count"] == 2

    def test_get_temporal_context_tool(self, tmp_path):
        """Test get_temporal_context MCP tool."""
        db = Database(tmp_path / "test.db")
        spatial = SpatialGrounder(db)
        temporal = TemporalChainer(db)
        graph = GraphLinker(db)

        tools = Phase72MCPTools(spatial, temporal, graph)

        result = tools.get_temporal_context(1, include_causality=True)
        assert result["status"] == "success"
        assert "chain" in result

    def test_traverse_relationships_tool(self, tmp_path):
        """Test traverse_relationships MCP tool."""
        db = Database(tmp_path / "test.db")
        spatial = SpatialGrounder(db)
        temporal = TemporalChainer(db)
        graph = GraphLinker(db)

        tools = Phase72MCPTools(spatial, temporal, graph)

        # Create an entity first
        graph.create_entity("test_module", EntityType.MODULE, "coordination")

        result = tools.traverse_relationships(
            "test_module",
            "module",
            max_depth=2
        )

        assert result["status"] == "success"
        assert "entity" in result

    def test_get_task_scope_tool(self, tmp_path):
        """Test get_task_scope MCP tool."""
        db = Database(tmp_path / "test.db")
        spatial = SpatialGrounder(db)
        temporal = TemporalChainer(db)
        graph = GraphLinker(db)

        tools = Phase72MCPTools(spatial, temporal, graph)

        # Link some files first
        class MockCodeContext:
            context_id = "ctx_1"
            relevant_files = ["src/main.py"]
            file_count = 1
            dependency_types = []

        spatial.link_code_context_to_spatial(MockCodeContext(), 1, "task_scope")

        result = tools.get_task_scope("task_scope")
        assert result["status"] == "success"

    def test_build_session_sequence_tool(self, tmp_path):
        """Test build_session_sequence MCP tool."""
        db = Database(tmp_path / "test.db")
        spatial = SpatialGrounder(db)
        temporal = TemporalChainer(db)
        graph = GraphLinker(db)

        tools = Phase72MCPTools(spatial, temporal, graph)

        # Create some episodic events first
        from athena.episodic.store import EpisodicStore
        from athena.episodic.models import EpisodicEvent, EventType, EventOutcome

        episodic_store = EpisodicStore(db)
        for i in range(3):
            event = EpisodicEvent(
                project_id=1,
                session_id="test_session",
                event_type=EventType.ACTION,
                content=f"Action {i}",
                outcome=EventOutcome.SUCCESS,
            )
            episodic_store.record_event(event)

        result = tools.build_session_sequence("test_session", "goal_1", "task_1")
        assert result["status"] == "success"
