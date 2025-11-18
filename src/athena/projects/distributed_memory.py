"""Distributed memory architecture for multi-project memory sharing.

Enables cross-project entity linking, shared knowledge bases, and distributed
memory coordination while maintaining project isolation and data integrity.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict


class SharingLevel(str, Enum):
    """Levels of memory sharing between projects."""

    ISOLATED = "isolated"  # No sharing
    REFERENCE = "reference"  # Can reference but not modify
    SHARED = "shared"  # Can reference and use
    SYNCHRONIZED = "synchronized"  # Real-time sync


class MemoryLayerType(str, Enum):
    """Types of memory layers that can be shared."""

    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    PROSPECTIVE = "prospective"
    GRAPH = "graph"
    META = "meta"
    CONSOLIDATION = "consolidation"
    WORKING = "working"


@dataclass
class CrossProjectReference:
    """Reference to an entity in another project."""

    reference_id: int
    from_project_id: int
    to_project_id: int
    entity_id: int  # Entity ID in source project
    entity_name: str
    entity_type: str
    memory_layer: MemoryLayerType
    reference_type: str  # "import"|"link"|"extend"
    sharing_level: SharingLevel
    created_at: datetime = field(default_factory=datetime.now)
    last_synced: Optional[datetime] = None
    is_active: bool = True


@dataclass
class SharedKnowledgeBase:
    """A shared knowledge base between multiple projects."""

    id: int
    name: str
    description: str
    owner_project_id: int
    member_projects: List[int]  # Projects with access
    sharing_level: SharingLevel

    # Content summary
    entity_count: int = 0
    relation_count: int = 0

    # Sync tracking
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    last_sync: Optional[datetime] = None

    # Access control
    read_only_projects: Set[int] = field(default_factory=set)
    allow_extensions: bool = True
    allow_modifications: bool = True


@dataclass
class MemorySyncRecord:
    """Record of a memory sync operation between projects."""

    sync_id: int
    from_project_id: int
    to_project_id: int
    memory_layer: MemoryLayerType
    sync_type: str  # "pull"|"push"|"bidirectional"

    # Sync details
    entities_synced: int = 0
    relations_synced: int = 0
    conflicts_found: int = 0
    conflicts_resolved: int = 0

    # Status
    status: str = "pending"  # pending|in_progress|completed|failed
    error_message: Optional[str] = None

    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None


@dataclass
class ProjectMemoryBoundary:
    """Defines memory isolation boundaries for a project."""

    project_id: int

    # Isolation settings
    default_sharing_level: SharingLevel = SharingLevel.ISOLATED

    # Allowed memory layers for import/export
    importable_layers: Set[MemoryLayerType] = field(default_factory=lambda: set(MemoryLayerType))
    exportable_layers: Set[MemoryLayerType] = field(default_factory=lambda: set(MemoryLayerType))

    # Trusted projects (can import from without restrictions)
    trusted_projects: Set[int] = field(default_factory=set)

    # Allowed sync operations
    allow_bidirectional_sync: bool = True
    allow_pull_only: bool = True
    allow_push_only: bool = True

    # Data retention
    keep_local_copies: bool = True
    sync_on_demand_only: bool = False


class DistributedMemoryManager:
    """Manages distributed memory across multiple projects."""

    def __init__(self, project_id: int):
        """Initialize manager for a project.

        Args:
            project_id: Project ID for this manager
        """
        self.project_id = project_id

        # Cross-project references
        self.cross_project_refs: Dict[int, CrossProjectReference] = {}
        self.ref_counter = 0

        # Shared knowledge bases
        self.shared_kbs: Dict[int, SharedKnowledgeBase] = {}
        self.kb_counter = 0

        # Sync records
        self.sync_records: List[MemorySyncRecord] = []
        self.sync_counter = 0

        # Project boundaries
        self.project_boundaries: Dict[int, ProjectMemoryBoundary] = {}

        # Reference indices
        self.references_by_target: Dict[Tuple[int, int], List[int]] = defaultdict(list)
        self.references_by_layer: Dict[MemoryLayerType, List[int]] = defaultdict(list)

    def create_cross_project_reference(
        self,
        target_project_id: int,
        entity_id: int,
        entity_name: str,
        entity_type: str,
        memory_layer: MemoryLayerType,
        reference_type: str = "link",
        sharing_level: SharingLevel = SharingLevel.REFERENCE,
    ) -> CrossProjectReference:
        """Create a reference to an entity in another project.

        Args:
            target_project_id: Project containing the entity
            entity_id: Entity ID in target project
            entity_name: Entity name
            entity_type: Entity type
            memory_layer: Memory layer type
            reference_type: Type of reference (import|link|extend)
            sharing_level: Level of sharing allowed

        Returns:
            CrossProjectReference object
        """
        self.ref_counter += 1

        ref = CrossProjectReference(
            reference_id=self.ref_counter,
            from_project_id=self.project_id,
            to_project_id=target_project_id,
            entity_id=entity_id,
            entity_name=entity_name,
            entity_type=entity_type,
            memory_layer=memory_layer,
            reference_type=reference_type,
            sharing_level=sharing_level,
        )

        self.cross_project_refs[ref.reference_id] = ref

        # Index by target and layer
        self.references_by_target[(target_project_id, entity_id)].append(ref.reference_id)
        self.references_by_layer[memory_layer].append(ref.reference_id)

        return ref

    def get_cross_project_references(
        self,
        target_project_id: Optional[int] = None,
        memory_layer: Optional[MemoryLayerType] = None,
    ) -> List[CrossProjectReference]:
        """Get cross-project references filtered by criteria.

        Args:
            target_project_id: Optional project filter
            memory_layer: Optional layer filter

        Returns:
            List of matching references
        """
        refs = list(self.cross_project_refs.values())

        if target_project_id:
            refs = [r for r in refs if r.to_project_id == target_project_id]

        if memory_layer:
            refs = [r for r in refs if r.memory_layer == memory_layer]

        return [r for r in refs if r.is_active]

    def create_shared_knowledge_base(
        self,
        name: str,
        description: str,
        member_projects: List[int],
        sharing_level: SharingLevel = SharingLevel.SHARED,
    ) -> SharedKnowledgeBase:
        """Create a shared knowledge base for multiple projects.

        Args:
            name: Knowledge base name
            description: Knowledge base description
            member_projects: List of project IDs with access
            sharing_level: Level of sharing

        Returns:
            SharedKnowledgeBase object
        """
        self.kb_counter += 1

        kb = SharedKnowledgeBase(
            id=self.kb_counter,
            name=name,
            description=description,
            owner_project_id=self.project_id,
            member_projects=member_projects,
            sharing_level=sharing_level,
        )

        self.shared_kbs[kb.id] = kb
        return kb

    def add_project_to_knowledge_base(
        self, kb_id: int, project_id: int, read_only: bool = False
    ) -> bool:
        """Add a project to a shared knowledge base.

        Args:
            kb_id: Knowledge base ID
            project_id: Project to add
            read_only: Whether project has read-only access

        Returns:
            True if added, False if not found or duplicate
        """
        if kb_id not in self.shared_kbs:
            return False

        kb = self.shared_kbs[kb_id]

        if project_id in kb.member_projects:
            return False  # Already member

        kb.member_projects.append(project_id)

        if read_only:
            kb.read_only_projects.add(project_id)

        return True

    def can_import_from_project(
        self, source_project_id: int, memory_layer: MemoryLayerType
    ) -> bool:
        """Check if current project can import from another.

        Args:
            source_project_id: Source project ID
            memory_layer: Memory layer to import

        Returns:
            True if import is allowed
        """
        boundary = self.project_boundaries.get(
            source_project_id,
            ProjectMemoryBoundary(source_project_id),
        )

        # Check if source exports this layer
        if memory_layer not in boundary.exportable_layers:
            return False

        # Check if we're trusted
        if self.project_id in boundary.trusted_projects:
            return True

        # Check default sharing level
        return boundary.default_sharing_level in (
            SharingLevel.SHARED,
            SharingLevel.REFERENCE,
            SharingLevel.SYNCHRONIZED,
        )

    def can_export_to_project(self, target_project_id: int, memory_layer: MemoryLayerType) -> bool:
        """Check if current project can export to another.

        Args:
            target_project_id: Target project ID
            memory_layer: Memory layer to export

        Returns:
            True if export is allowed
        """
        boundary = self.project_boundaries.get(
            self.project_id,
            ProjectMemoryBoundary(self.project_id),
        )

        # Check if we export this layer
        if memory_layer not in boundary.exportable_layers:
            return False

        # Check target is trusted
        if target_project_id in boundary.trusted_projects:
            return True

        # Check default sharing level
        return boundary.default_sharing_level in (
            SharingLevel.SHARED,
            SharingLevel.REFERENCE,
            SharingLevel.SYNCHRONIZED,
        )

    def set_project_boundary(self, boundary: ProjectMemoryBoundary) -> None:
        """Set memory isolation boundary for a project.

        Args:
            boundary: ProjectMemoryBoundary to set
        """
        self.project_boundaries[boundary.project_id] = boundary

    def record_sync_operation(
        self,
        target_project_id: int,
        memory_layer: MemoryLayerType,
        sync_type: str,
    ) -> MemorySyncRecord:
        """Create a record of a sync operation.

        Args:
            target_project_id: Target project ID
            memory_layer: Memory layer being synced
            sync_type: Type of sync (pull|push|bidirectional)

        Returns:
            MemorySyncRecord
        """
        self.sync_counter += 1

        record = MemorySyncRecord(
            sync_id=self.sync_counter,
            from_project_id=self.project_id,
            to_project_id=target_project_id,
            memory_layer=memory_layer,
            sync_type=sync_type,
        )

        self.sync_records.append(record)
        return record

    def complete_sync_operation(
        self,
        sync_id: int,
        entities_synced: int = 0,
        relations_synced: int = 0,
        conflicts_found: int = 0,
        conflicts_resolved: int = 0,
        error_message: Optional[str] = None,
    ) -> bool:
        """Mark a sync operation as complete.

        Args:
            sync_id: Sync record ID
            entities_synced: Number of entities synced
            relations_synced: Number of relations synced
            conflicts_found: Number of conflicts found
            conflicts_resolved: Number of conflicts resolved
            error_message: Optional error message if failed

        Returns:
            True if updated, False if not found
        """
        sync_record = None
        for record in self.sync_records:
            if record.sync_id == sync_id:
                sync_record = record
                break

        if not sync_record:
            return False

        now = datetime.now()
        sync_record.completed_at = now
        sync_record.entities_synced = entities_synced
        sync_record.relations_synced = relations_synced
        sync_record.conflicts_found = conflicts_found
        sync_record.conflicts_resolved = conflicts_resolved
        sync_record.status = "failed" if error_message else "completed"
        sync_record.error_message = error_message

        if sync_record.started_at:
            sync_record.duration_ms = int((now - sync_record.started_at).total_seconds() * 1000)

        return True

    def get_sync_history(
        self,
        target_project_id: Optional[int] = None,
        memory_layer: Optional[MemoryLayerType] = None,
    ) -> List[MemorySyncRecord]:
        """Get sync operation history.

        Args:
            target_project_id: Optional filter by target project
            memory_layer: Optional filter by memory layer

        Returns:
            List of sync records
        """
        records = self.sync_records

        if target_project_id:
            records = [r for r in records if r.to_project_id == target_project_id]

        if memory_layer:
            records = [r for r in records if r.memory_layer == memory_layer]

        return records

    def compute_memory_sharing_graph(self) -> Dict[int, List[Tuple[int, SharingLevel]]]:
        """Compute a graph of memory sharing relationships.

        Returns:
            Dictionary mapping project_id to list of (target_project_id, sharing_level)
        """
        sharing_graph: Dict[int, List[Tuple[int, SharingLevel]]] = defaultdict(list)

        # Add all references
        for ref in self.cross_project_refs.values():
            if ref.is_active:
                sharing_graph[ref.from_project_id].append((ref.to_project_id, ref.sharing_level))

        # Add shared knowledge bases
        for kb in self.shared_kbs.values():
            for member in kb.member_projects:
                if member != kb.owner_project_id:
                    sharing_graph[kb.owner_project_id].append((member, kb.sharing_level))

        return sharing_graph

    def detect_sharing_cycles(self) -> List[List[int]]:
        """Detect cycles in memory sharing relationships.

        Returns:
            List of cycles (as lists of project IDs)
        """
        graph = self.compute_memory_sharing_graph()
        cycles = []

        # DFS to find cycles
        visited: Set[int] = set()
        rec_stack: Set[int] = set()
        path: List[int] = []

        def dfs(node: int) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor, _ in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])

            path.pop()
            rec_stack.remove(node)

        # Check all nodes
        for project_id in graph.keys():
            if project_id not in visited:
                dfs(project_id)

        return cycles

    def get_upstream_projects(self, distance: Optional[int] = None) -> Set[int]:
        """Get projects that this project imports from.

        Args:
            distance: Optional max distance (None = all)

        Returns:
            Set of upstream project IDs
        """
        upstream: Set[int] = set()
        to_visit = [(ref.to_project_id, 1) for ref in self.cross_project_refs.values()]

        while to_visit:
            proj_id, dist = to_visit.pop(0)

            if proj_id in upstream:
                continue

            if distance and dist > distance:
                continue

            upstream.add(proj_id)

        return upstream

    def get_downstream_projects(self, distance: Optional[int] = None) -> Set[int]:
        """Get projects that import from this project.

        Args:
            distance: Optional max distance (None = all)

        Returns:
            Set of downstream project IDs
        """
        downstream: Set[int] = set()

        # Find all projects that reference entities from this project
        # (would need to query database in real implementation)
        # For now, return empty set

        return downstream

    def estimate_memory_overlap(self, other_project_id: int) -> float:
        """Estimate memory overlap with another project.

        Args:
            other_project_id: Project to compare with

        Returns:
            Overlap score 0-1
        """
        # Count shared references
        my_refs = self.get_cross_project_references(target_project_id=other_project_id)
        other_refs = [
            r for r in self.get_cross_project_references() if r.to_project_id == self.project_id
        ]

        if not my_refs and not other_refs:
            return 0.0

        shared = len([r for r in my_refs if r.to_project_id == other_project_id])
        total = len(my_refs) + len(other_refs)

        return shared / total if total > 0 else 0.0
