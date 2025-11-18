"""Cross-file dependency analysis for code.

This module analyzes dependencies between code units across different files,
detects import chains, circular dependencies, and provides metrics on
code coupling and cohesion.
"""

import logging
from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class DependencyType(Enum):
    """Types of dependencies between code units."""

    IMPORT = "import"  # Direct import
    FUNCTION_CALL = "function_call"  # Function/method call
    CLASS_INHERITANCE = "inheritance"  # Class inheritance
    INTERFACE_IMPL = "interface_impl"  # Interface implementation
    TYPE_REFERENCE = "type_reference"  # Type/class reference
    COMPOSITION = "composition"  # Object composition


@dataclass
class Dependency:
    """Represents a dependency between two code units."""

    source: str
    target: str
    source_file: str
    target_file: str
    dependency_type: DependencyType
    line_number: int = 0
    is_external: bool = False  # External library
    strength: float = 1.0  # 0-1, directness of dependency
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "target": self.target,
            "source_file": self.source_file,
            "target_file": self.target_file,
            "dependency_type": self.dependency_type.value,
            "line_number": self.line_number,
            "is_external": self.is_external,
            "strength": self.strength,
            "metadata": self.metadata,
        }


@dataclass
class DependencyMetrics:
    """Metrics for dependency analysis."""

    entity_name: str
    file_path: str
    incoming_dependencies: int = 0  # Number of entities depending on this
    outgoing_dependencies: int = 0  # Number of entities this depends on
    external_dependencies: int = 0  # Number of external library dependencies
    dependency_depth: int = 0  # Maximum chain length
    fan_in: float = 0.0  # Incoming dependency count (normalized)
    fan_out: float = 0.0  # Outgoing dependency count (normalized)
    instability: float = 0.0  # fan_out / (fan_in + fan_out)
    coupling: float = 0.0  # Overall coupling score


class DependencyGraph:
    """Graph representation of code dependencies."""

    def __init__(self):
        """Initialize dependency graph."""
        self.dependencies: List[Dependency] = []
        self.graph: Dict[str, List[str]] = defaultdict(list)  # source -> targets
        self.reverse_graph: Dict[str, List[str]] = defaultdict(list)  # target -> sources
        self.by_file: Dict[str, List[Dependency]] = defaultdict(list)
        self.external_deps: Set[str] = set()

    def add_dependency(self, dep: Dependency) -> None:
        """Add a dependency to the graph."""
        self.dependencies.append(dep)
        self.graph[dep.source].append(dep.target)
        self.reverse_graph[dep.target].append(dep.source)

        if dep.is_external:
            self.external_deps.add(dep.target)

        # Index by file
        self.by_file[dep.source_file].append(dep)

    def get_direct_dependencies(self, entity: str) -> List[str]:
        """Get direct dependencies of an entity."""
        return self.graph.get(entity, [])

    def get_dependents(self, entity: str) -> List[str]:
        """Get entities that depend on this entity."""
        return self.reverse_graph.get(entity, [])

    def find_import_chain(self, source: str, target: str) -> Optional[List[str]]:
        """Find path from source to target."""
        visited = set()
        queue = deque([(source, [source])])

        while queue:
            current, path = queue.popleft()
            if current == target:
                return path

            if current in visited:
                continue
            visited.add(current)

            for neighbor in self.get_direct_dependencies(current):
                if neighbor not in visited:
                    queue.append((neighbor, path + [neighbor]))

        return None

    def find_circular_dependencies(self) -> List[List[str]]:
        """Find all circular dependency chains."""
        cycles = []
        visited = set()

        def dfs(node: str, path: List[str]) -> bool:
            if node in path:
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return True

            if node in visited:
                return False

            visited.add(node)
            path.append(node)

            for neighbor in self.get_direct_dependencies(node):
                if dfs(neighbor, path.copy()):
                    return True

            return False

        for node in self.graph.keys():
            if node not in visited:
                dfs(node, [])

        return cycles

    def get_dependency_metrics(self, entity: str) -> DependencyMetrics:
        """Calculate dependency metrics for an entity."""
        # Find entity file
        entity_file = None
        for dep in self.dependencies:
            if dep.source == entity:
                entity_file = dep.source_file
                break
            elif dep.target == entity:
                entity_file = dep.target_file
                break

        metrics = DependencyMetrics(
            entity_name=entity,
            file_path=entity_file or "unknown",
        )

        # Count incoming/outgoing
        metrics.incoming_dependencies = len(self.get_dependents(entity))
        metrics.outgoing_dependencies = len(self.get_direct_dependencies(entity))

        # Count external
        for target in self.get_direct_dependencies(entity):
            if target in self.external_deps:
                metrics.external_dependencies += 1

        # Calculate fan-in/out (normalized 0-1)
        all_entities = len(
            set(d.source for d in self.dependencies) | set(d.target for d in self.dependencies)
        )
        if all_entities > 0:
            metrics.fan_in = min(metrics.incoming_dependencies / all_entities, 1.0)
            metrics.fan_out = min(metrics.outgoing_dependencies / all_entities, 1.0)

        # Instability: how likely to change
        denominator = metrics.fan_in + metrics.fan_out
        if denominator > 0:
            metrics.instability = metrics.fan_out / denominator
        else:
            metrics.instability = 0.5

        # Coupling: overall metric
        metrics.coupling = (metrics.fan_in + metrics.fan_out) / 2

        return metrics

    def get_file_dependencies(self, file_path: str) -> Dict[str, Any]:
        """Analyze dependencies for a file."""
        file_deps = self.by_file.get(file_path, [])

        # Count unique files this file depends on
        depends_on_files = set()
        is_depended_on_files = set()

        for dep in self.dependencies:
            if dep.source_file == file_path and dep.target_file != file_path:
                depends_on_files.add(dep.target_file)
            elif dep.target_file == file_path and dep.source_file != file_path:
                is_depended_on_files.add(dep.source_file)

        return {
            "file_path": file_path,
            "outgoing_file_dependencies": len(depends_on_files),
            "incoming_file_dependencies": len(is_depended_on_files),
            "depends_on_files": list(depends_on_files),
            "depended_on_by_files": list(is_depended_on_files),
            "total_dependencies": len(file_deps),
        }

    def find_problematic_dependencies(
        self, instability_threshold: float = 0.7
    ) -> List[Tuple[str, DependencyMetrics]]:
        """Find entities with high instability."""
        problematic = []
        all_entities = set(d.source for d in self.dependencies) | set(
            d.target for d in self.dependencies
        )

        for entity in all_entities:
            metrics = self.get_dependency_metrics(entity)
            if metrics.instability >= instability_threshold:
                problematic.append((entity, metrics))

        return sorted(problematic, key=lambda x: x[1].instability, reverse=True)


class DependencyAnalyzer:
    """Analyzes code dependencies and provides insights."""

    def __init__(self, graph: DependencyGraph):
        """Initialize analyzer."""
        self.graph = graph

    def detect_high_coupling_pairs(self, threshold: int = 3) -> List[Tuple[str, str, int]]:
        """Find pairs of entities with high mutual dependency."""
        mutual_deps = defaultdict(int)

        for entity in self.graph.graph.keys():
            deps = self.graph.get_direct_dependencies(entity)
            dependents = self.graph.get_dependents(entity)

            for dep in deps:
                if entity in self.graph.get_direct_dependencies(dep):
                    # Mutual dependency
                    pair = tuple(sorted([entity, dep]))
                    mutual_deps[pair] += 1

        high_coupling = [
            (pair[0], pair[1], count) for pair, count in mutual_deps.items() if count >= threshold
        ]

        return sorted(high_coupling, key=lambda x: x[2], reverse=True)

    def find_stable_entities(self) -> List[str]:
        """Find stable entities (low instability)."""
        stable = []
        all_entities = set(self.graph.graph.keys()) | set(self.graph.reverse_graph.keys())

        for entity in all_entities:
            metrics = self.graph.get_dependency_metrics(entity)
            if metrics.instability < 0.3:
                stable.append(entity)

        return stable

    def find_bottleneck_entities(self) -> List[str]:
        """Find entities that are heavily depended on (potential bottlenecks)."""
        bottlenecks = []
        all_entities = set(self.graph.graph.keys()) | set(self.graph.reverse_graph.keys())

        max_incoming = max((len(self.graph.get_dependents(e)) for e in all_entities), default=0)

        if max_incoming > 0:
            threshold = max_incoming * 0.7
            for entity in all_entities:
                incoming = len(self.graph.get_dependents(entity))
                if incoming >= threshold:
                    bottlenecks.append(entity)

        return bottlenecks

    def calculate_average_path_length(self) -> float:
        """Calculate average dependency chain length."""
        if not self.graph.dependencies:
            return 0.0

        total_depth = 0
        all_entities = set(self.graph.graph.keys()) | set(self.graph.reverse_graph.keys())

        for entity in all_entities:
            metrics = self.graph.get_dependency_metrics(entity)
            total_depth += metrics.dependency_depth

        return total_depth / len(all_entities) if all_entities else 0.0

    def generate_dependency_report(self) -> str:
        """Generate comprehensive dependency analysis report."""
        report = "DEPENDENCY ANALYSIS REPORT\n"
        report += "=" * 60 + "\n\n"

        # Overview
        report += f"Total Dependencies: {len(self.graph.dependencies)}\n"
        report += f"External Dependencies: {len(self.graph.external_deps)}\n\n"

        # Circular dependencies
        cycles = self.graph.find_circular_dependencies()
        if cycles:
            report += f"Circular Dependencies Found: {len(cycles)}\n"
            for cycle in cycles[:5]:  # Show first 5
                report += f"  {' -> '.join(cycle)}\n"
        else:
            report += "No circular dependencies detected.\n\n"

        # High coupling pairs
        coupling_pairs = self.detect_high_coupling_pairs()
        if coupling_pairs:
            report += f"\nHigh Coupling Pairs: {len(coupling_pairs)}\n"
            for ent1, ent2, count in coupling_pairs[:5]:
                report += f"  {ent1} <-> {ent2} (mutual deps: {count})\n"

        # Stable vs Unstable
        stable = self.find_stable_entities()
        all_entities = len(set(self.graph.graph.keys()) | set(self.graph.reverse_graph.keys()))
        report += f"\nStability: {len(stable)}/{all_entities} entities are stable\n"

        # Bottlenecks
        bottlenecks = self.find_bottleneck_entities()
        if bottlenecks:
            report += f"\nBottleneck Entities: {len(bottlenecks)}\n"
            for entity in bottlenecks[:5]:
                metrics = self.graph.get_dependency_metrics(entity)
                report += f"  {entity} (depended on by {metrics.incoming_dependencies})\n"

        return report
