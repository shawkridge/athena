"""Test multi-project distributed memory architecture.

Tests:
- Cross-project entity references
- Shared knowledge bases
- Memory sync operations
- Project isolation boundaries
- Memory sharing graphs and cycles
"""

import pytest
from datetime import datetime

from athena.projects.distributed_memory import (
    DistributedMemoryManager,
    CrossProjectReference,
    SharedKnowledgeBase,
    MemorySyncRecord,
    ProjectMemoryBoundary,
    SharingLevel,
    MemoryLayerType,
)


@pytest.fixture
def manager_p1():
    """Create distributed memory manager for project 1."""
    return DistributedMemoryManager(project_id=1)


@pytest.fixture
def manager_p2():
    """Create distributed memory manager for project 2."""
    return DistributedMemoryManager(project_id=2)


@pytest.fixture
def manager_p3():
    """Create distributed memory manager for project 3."""
    return DistributedMemoryManager(project_id=3)


class TestCrossProjectReferences:
    """Test cross-project entity references."""

    def test_create_cross_project_reference(self, manager_p1):
        """Test creating a cross-project reference."""
        ref = manager_p1.create_cross_project_reference(
            target_project_id=2,
            entity_id=100,
            entity_name="SharedEntity",
            entity_type="Concept",
            memory_layer=MemoryLayerType.SEMANTIC,
            reference_type="import",
            sharing_level=SharingLevel.REFERENCE,
        )

        assert ref.from_project_id == 1
        assert ref.to_project_id == 2
        assert ref.entity_id == 100
        assert ref.entity_name == "SharedEntity"
        assert ref.memory_layer == MemoryLayerType.SEMANTIC
        assert ref.sharing_level == SharingLevel.REFERENCE
        assert ref.is_active

    def test_get_cross_project_references_unfiltered(self, manager_p1):
        """Test retrieving all cross-project references."""
        # Create multiple references
        ref1 = manager_p1.create_cross_project_reference(
            2, 100, "Entity1", "Concept", MemoryLayerType.SEMANTIC
        )
        ref2 = manager_p1.create_cross_project_reference(
            3, 200, "Entity2", "Component", MemoryLayerType.PROCEDURAL
        )

        refs = manager_p1.get_cross_project_references()

        assert len(refs) == 2
        assert ref1 in refs
        assert ref2 in refs

    def test_get_cross_project_references_by_target(self, manager_p1):
        """Test filtering references by target project."""
        manager_p1.create_cross_project_reference(
            2, 100, "Entity1", "Concept", MemoryLayerType.SEMANTIC
        )
        manager_p1.create_cross_project_reference(
            3, 200, "Entity2", "Concept", MemoryLayerType.SEMANTIC
        )

        refs = manager_p1.get_cross_project_references(target_project_id=2)

        assert len(refs) == 1
        assert refs[0].to_project_id == 2

    def test_get_cross_project_references_by_layer(self, manager_p1):
        """Test filtering references by memory layer."""
        manager_p1.create_cross_project_reference(
            2, 100, "Entity1", "Concept", MemoryLayerType.SEMANTIC
        )
        manager_p1.create_cross_project_reference(
            2, 200, "Entity2", "Component", MemoryLayerType.PROCEDURAL
        )

        refs = manager_p1.get_cross_project_references(memory_layer=MemoryLayerType.SEMANTIC)

        assert len(refs) == 1
        assert refs[0].memory_layer == MemoryLayerType.SEMANTIC

    def test_reference_counter_increments(self, manager_p1):
        """Test that reference IDs are unique."""
        ref1 = manager_p1.create_cross_project_reference(
            2, 100, "E1", "Concept", MemoryLayerType.SEMANTIC
        )
        ref2 = manager_p1.create_cross_project_reference(
            2, 101, "E2", "Concept", MemoryLayerType.SEMANTIC
        )

        assert ref1.reference_id != ref2.reference_id
        assert ref1.reference_id == 1
        assert ref2.reference_id == 2


class TestSharedKnowledgeBases:
    """Test shared knowledge bases."""

    def test_create_shared_knowledge_base(self, manager_p1):
        """Test creating a shared knowledge base."""
        kb = manager_p1.create_shared_knowledge_base(
            name="SharedML",
            description="Machine learning knowledge base",
            member_projects=[1, 2, 3],
            sharing_level=SharingLevel.SHARED,
        )

        assert kb.name == "SharedML"
        assert kb.owner_project_id == 1
        assert 2 in kb.member_projects
        assert 3 in kb.member_projects
        assert kb.sharing_level == SharingLevel.SHARED

    def test_add_project_to_knowledge_base(self, manager_p1):
        """Test adding a project to a knowledge base."""
        kb = manager_p1.create_shared_knowledge_base(
            "SharedKB", "Test KB", [1, 2]
        )

        success = manager_p1.add_project_to_knowledge_base(kb.id, 3)
        assert success
        assert 3 in kb.member_projects

    def test_add_duplicate_project_to_kb(self, manager_p1):
        """Test that duplicate project additions fail."""
        kb = manager_p1.create_shared_knowledge_base(
            "SharedKB", "Test KB", [1, 2]
        )

        success = manager_p1.add_project_to_knowledge_base(kb.id, 2)
        assert not success

    def test_add_project_to_nonexistent_kb(self, manager_p1):
        """Test adding to non-existent knowledge base."""
        success = manager_p1.add_project_to_knowledge_base(999, 3)
        assert not success

    def test_read_only_access(self, manager_p1):
        """Test setting read-only access."""
        kb = manager_p1.create_shared_knowledge_base(
            "SharedKB", "Test KB", [1, 2]
        )

        manager_p1.add_project_to_knowledge_base(kb.id, 3, read_only=True)

        assert 3 in kb.read_only_projects


class TestMemorySyncOperations:
    """Test memory sync operations."""

    def test_record_sync_operation(self, manager_p1):
        """Test recording a sync operation."""
        sync = manager_p1.record_sync_operation(
            target_project_id=2,
            memory_layer=MemoryLayerType.SEMANTIC,
            sync_type="pull",
        )

        assert sync.from_project_id == 1
        assert sync.to_project_id == 2
        assert sync.memory_layer == MemoryLayerType.SEMANTIC
        assert sync.sync_type == "pull"
        assert sync.status == "pending"

    def test_complete_sync_operation(self, manager_p1):
        """Test completing a sync operation."""
        sync = manager_p1.record_sync_operation(
            2, MemoryLayerType.SEMANTIC, "pull"
        )

        success = manager_p1.complete_sync_operation(
            sync.sync_id,
            entities_synced=100,
            relations_synced=50,
            conflicts_resolved=2,
        )

        assert success
        assert sync.status == "completed"
        assert sync.entities_synced == 100
        assert sync.relations_synced == 50
        assert sync.completed_at is not None
        assert sync.duration_ms is not None

    def test_complete_failed_sync(self, manager_p1):
        """Test completing a failed sync."""
        sync = manager_p1.record_sync_operation(
            2, MemoryLayerType.SEMANTIC, "pull"
        )

        success = manager_p1.complete_sync_operation(
            sync.sync_id,
            error_message="Network timeout",
        )

        assert success
        assert sync.status == "failed"
        assert sync.error_message == "Network timeout"

    def test_get_sync_history(self, manager_p1):
        """Test retrieving sync history."""
        sync1 = manager_p1.record_sync_operation(
            2, MemoryLayerType.SEMANTIC, "pull"
        )
        sync2 = manager_p1.record_sync_operation(
            3, MemoryLayerType.PROCEDURAL, "push"
        )

        history = manager_p1.get_sync_history()

        assert len(history) == 2
        assert sync1 in history
        assert sync2 in history

    def test_get_sync_history_filtered_by_project(self, manager_p1):
        """Test filtering sync history by target project."""
        manager_p1.record_sync_operation(
            2, MemoryLayerType.SEMANTIC, "pull"
        )
        manager_p1.record_sync_operation(
            3, MemoryLayerType.PROCEDURAL, "push"
        )

        history = manager_p1.get_sync_history(target_project_id=2)

        assert len(history) == 1
        assert history[0].to_project_id == 2


class TestProjectMemoryBoundaries:
    """Test project memory isolation boundaries."""

    def test_set_project_boundary(self, manager_p1):
        """Test setting memory boundary for a project."""
        boundary = ProjectMemoryBoundary(
            project_id=2,
            default_sharing_level=SharingLevel.REFERENCE,
            importable_layers={MemoryLayerType.SEMANTIC, MemoryLayerType.PROCEDURAL},
            exportable_layers={MemoryLayerType.SEMANTIC},
            trusted_projects={1},
        )

        manager_p1.set_project_boundary(boundary)

        assert 2 in manager_p1.project_boundaries
        assert manager_p1.project_boundaries[2].default_sharing_level == SharingLevel.REFERENCE

    def test_can_import_from_project(self, manager_p1):
        """Test checking import permissions."""
        boundary = ProjectMemoryBoundary(
            project_id=2,
            default_sharing_level=SharingLevel.ISOLATED,
            exportable_layers={MemoryLayerType.SEMANTIC},
            trusted_projects={1},
        )

        manager_p1.set_project_boundary(boundary)

        # Can import semantic (in exportable layers and project 1 is trusted)
        assert manager_p1.can_import_from_project(
            2, MemoryLayerType.SEMANTIC
        )

        # Cannot import procedural (not in exportable layers)
        assert not manager_p1.can_import_from_project(
            2, MemoryLayerType.PROCEDURAL
        )

    def test_can_export_to_project(self, manager_p1):
        """Test checking export permissions."""
        boundary = ProjectMemoryBoundary(
            project_id=1,
            default_sharing_level=SharingLevel.SHARED,
            exportable_layers={MemoryLayerType.SEMANTIC, MemoryLayerType.GRAPH},
            trusted_projects={2},
        )

        manager_p1.set_project_boundary(boundary)

        # Can export semantic to project 2
        assert manager_p1.can_export_to_project(
            2, MemoryLayerType.SEMANTIC
        )

        # Cannot export procedural (not in exportable layers)
        assert not manager_p1.can_export_to_project(
            2, MemoryLayerType.PROCEDURAL
        )


class TestSharingGraphs:
    """Test memory sharing relationship graphs."""

    def test_compute_memory_sharing_graph(self, manager_p1):
        """Test computing sharing graph."""
        manager_p1.create_cross_project_reference(
            2, 100, "E1", "Concept", MemoryLayerType.SEMANTIC,
            sharing_level=SharingLevel.REFERENCE
        )
        manager_p1.create_cross_project_reference(
            3, 200, "E2", "Component", MemoryLayerType.PROCEDURAL,
            sharing_level=SharingLevel.SHARED
        )

        graph = manager_p1.compute_memory_sharing_graph()

        assert 1 in graph
        assert len(graph[1]) == 2
        assert (2, SharingLevel.REFERENCE) in graph[1]
        assert (3, SharingLevel.SHARED) in graph[1]

    def test_detect_no_cycles(self, manager_p1, manager_p2, manager_p3):
        """Test cycle detection with no cycles."""
        manager_p1.create_cross_project_reference(
            2, 100, "E1", "Concept", MemoryLayerType.SEMANTIC
        )
        manager_p2.create_cross_project_reference(
            3, 200, "E2", "Concept", MemoryLayerType.SEMANTIC
        )

        cycles_p1 = manager_p1.detect_sharing_cycles()
        cycles_p2 = manager_p2.detect_sharing_cycles()
        cycles_p3 = manager_p3.detect_sharing_cycles()

        assert len(cycles_p1) == 0
        assert len(cycles_p2) == 0
        assert len(cycles_p3) == 0

    def test_get_upstream_projects(self, manager_p1):
        """Test getting upstream projects."""
        manager_p1.create_cross_project_reference(
            2, 100, "E1", "Concept", MemoryLayerType.SEMANTIC
        )
        manager_p1.create_cross_project_reference(
            3, 200, "E2", "Concept", MemoryLayerType.SEMANTIC
        )

        upstream = manager_p1.get_upstream_projects()

        assert 2 in upstream
        assert 3 in upstream
        assert 1 not in upstream


class TestMemoryOverlapEstimation:
    """Test memory overlap estimation."""

    def test_estimate_memory_overlap_no_overlap(self, manager_p1, manager_p2):
        """Test overlap estimation with no shared entities."""
        overlap = manager_p1.estimate_memory_overlap(2)
        assert overlap == 0.0

    def test_estimate_memory_overlap_with_references(self, manager_p1):
        """Test overlap estimation with references."""
        manager_p1.create_cross_project_reference(
            2, 100, "E1", "Concept", MemoryLayerType.SEMANTIC
        )
        manager_p1.create_cross_project_reference(
            2, 101, "E2", "Concept", MemoryLayerType.SEMANTIC
        )

        overlap = manager_p1.estimate_memory_overlap(2)

        assert 0 <= overlap <= 1
        assert overlap > 0


class TestMultiProjectWorkflow:
    """Test realistic multi-project workflows."""

    def test_simple_knowledge_sharing(self, manager_p1, manager_p2):
        """Test simple knowledge sharing between two projects."""
        # P1 creates a shared knowledge base
        kb = manager_p1.create_shared_knowledge_base(
            name="DataScience",
            description="Shared data science knowledge",
            member_projects=[1, 2],
            sharing_level=SharingLevel.SHARED,
        )

        # P1 imports from P2
        ref = manager_p1.create_cross_project_reference(
            target_project_id=2,
            entity_id=50,
            entity_name="MLModel",
            entity_type="Component",
            memory_layer=MemoryLayerType.PROCEDURAL,
            sharing_level=SharingLevel.REFERENCE,
        )

        # Check state
        assert kb.id in [kb.id for kb in manager_p1.shared_kbs.values()]
        assert len(manager_p1.get_cross_project_references()) == 1

    def test_multi_project_collaboration(self, manager_p1, manager_p2, manager_p3):
        """Test three-project collaboration."""
        # Create shared KB
        kb = manager_p1.create_shared_knowledge_base(
            "TeamKB",
            "Shared team knowledge",
            [1, 2, 3],
            SharingLevel.SHARED,
        )

        # P1 exports to P2
        manager_p1.create_cross_project_reference(
            2, 100, "Resource1", "Concept", MemoryLayerType.SEMANTIC
        )

        # P2 exports to P3
        manager_p2.create_cross_project_reference(
            3, 200, "Resource2", "Concept", MemoryLayerType.SEMANTIC
        )

        # Verify network
        graph_p1 = manager_p1.compute_memory_sharing_graph()
        graph_p2 = manager_p2.compute_memory_sharing_graph()

        # Check that graphs have the expected structure
        assert 1 in graph_p1
        assert any(proj_id == 2 for proj_id, _ in graph_p1[1])

        assert 2 in graph_p2
        assert any(proj_id == 3 for proj_id, _ in graph_p2[2])

    def test_access_control_enforcement(self, manager_p1):
        """Test access control enforcement."""
        # Set restrictive boundary for project 2
        # Project 1 is trusted, so it can import semantic
        boundary = ProjectMemoryBoundary(
            project_id=2,
            default_sharing_level=SharingLevel.ISOLATED,
            importable_layers={MemoryLayerType.SEMANTIC},
            exportable_layers={MemoryLayerType.SEMANTIC},  # Export semantic only
            trusted_projects={1},  # Project 1 is trusted
        )

        manager_p1.set_project_boundary(boundary)

        # Can import semantic (project 1 is trusted)
        assert manager_p1.can_import_from_project(
            2, MemoryLayerType.SEMANTIC
        )

        # Cannot import other layers
        assert not manager_p1.can_import_from_project(
            2, MemoryLayerType.PROCEDURAL
        )

        # Cannot export to project 3 (not trusted in our boundary)
        boundary_p1 = ProjectMemoryBoundary(
            project_id=1,
            exportable_layers={MemoryLayerType.SEMANTIC},
            trusted_projects=set(),  # No projects trusted
        )
        manager_p1.set_project_boundary(boundary_p1)

        assert not manager_p1.can_export_to_project(
            2, MemoryLayerType.SEMANTIC
        )


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_manager(self, manager_p1):
        """Test manager with no references."""
        refs = manager_p1.get_cross_project_references()
        assert len(refs) == 0

        graph = manager_p1.compute_memory_sharing_graph()
        assert 1 not in graph

        cycles = manager_p1.detect_sharing_cycles()
        assert len(cycles) == 0

    def test_self_reference(self, manager_p1):
        """Test that projects can reference themselves."""
        ref = manager_p1.create_cross_project_reference(
            target_project_id=1,  # Same project
            entity_id=100,
            entity_name="SelfEntity",
            entity_type="Concept",
            memory_layer=MemoryLayerType.SEMANTIC,
        )

        assert ref.to_project_id == 1

    def test_large_number_of_references(self, manager_p1):
        """Test manager with many references."""
        for i in range(100):
            manager_p1.create_cross_project_reference(
                target_project_id=2,
                entity_id=i,
                entity_name=f"Entity{i}",
                entity_type="Concept",
                memory_layer=MemoryLayerType.SEMANTIC,
            )

        refs = manager_p1.get_cross_project_references()
        assert len(refs) == 100

        # Verify IDs are unique
        ids = [r.reference_id for r in refs]
        assert len(ids) == len(set(ids))

    def test_all_memory_layers(self, manager_p1):
        """Test that all memory layer types are supported."""
        for layer in MemoryLayerType:
            ref = manager_p1.create_cross_project_reference(
                target_project_id=2,
                entity_id=100,
                entity_name=f"Entity_{layer}",
                entity_type="Concept",
                memory_layer=layer,
            )

            assert ref.memory_layer == layer

    def test_all_sharing_levels(self, manager_p1):
        """Test that all sharing levels are supported."""
        for sharing_level in SharingLevel:
            ref = manager_p1.create_cross_project_reference(
                target_project_id=2,
                entity_id=100,
                entity_name=f"Entity_{sharing_level}",
                entity_type="Concept",
                memory_layer=MemoryLayerType.SEMANTIC,
                sharing_level=sharing_level,
            )

            assert ref.sharing_level == sharing_level
