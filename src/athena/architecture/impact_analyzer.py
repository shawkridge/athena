"""Architecture Impact Analysis - "What-if" simulation for architectural changes.

This module provides impact analysis capabilities to answer questions like:
- "If I change ADR-X, what components are affected?"
- "What's the blast radius of this architectural change?"
- "Which ADRs depend on this pattern?"
- "If I add this constraint, which existing code violates it?"

Inspired by AI-driven dependency visualization tools that reduce analysis time by 70%.

Usage:
    from athena.architecture.impact_analyzer import ImpactAnalyzer

    analyzer = ImpactAnalyzer(db, project_root)

    # Analyze ADR change
    impact = analyzer.analyze_adr_change(
        adr_id=12,
        proposed_change="Switch from JWT to session-based auth"
    )

    print(f"Risk level: {impact.risk_level}")
    print(f"Affected components: {impact.affected_components}")
    print(f"Estimated effort: {impact.estimated_effort}")
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ..core.database import Database


class RiskLevel(str, Enum):
    """Risk level for architectural changes."""

    LOW = "low"  # Minimal impact, easy to reverse
    MEDIUM = "medium"  # Moderate impact, some effort to reverse
    HIGH = "high"  # Significant impact, difficult to reverse
    CRITICAL = "critical"  # Major impact, very difficult/impossible to reverse


class EffortEstimate(str, Enum):
    """Effort estimate for implementing changes."""

    TRIVIAL = "trivial"  # < 1 hour
    LOW = "low"  # 1-4 hours
    MEDIUM = "medium"  # 1-2 days
    HIGH = "high"  # 3-5 days
    VERY_HIGH = "very_high"  # 1+ weeks


class ComponentType(str, Enum):
    """Types of architectural components."""

    LAYER = "layer"  # Architectural layer (e.g., "API Layer")
    MODULE = "module"  # Python module/package
    CLASS = "class"  # Class definition
    FUNCTION = "function"  # Function/method
    EXTERNAL_API = "external_api"  # External API dependency
    DATABASE = "database"  # Database schema/table


@dataclass
class Component:
    """Represents an architectural component."""

    name: str
    type: ComponentType
    path: Optional[str] = None  # File path or module path
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.type.value}:{self.name}"

    def __hash__(self) -> int:
        return hash((self.name, self.type))


@dataclass
class Dependency:
    """Represents a dependency between components."""

    source: Component
    target: Component
    dependency_type: str  # "imports", "calls", "references", "implements"
    strength: float = 1.0  # 0.0-1.0, how strong the coupling
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImpactReport:
    """Report of impact analysis for an architectural change."""

    change_description: str
    risk_level: RiskLevel
    estimated_effort: EffortEstimate

    # What's affected
    affected_components: List[Component] = field(default_factory=list)
    affected_adrs: List[int] = field(default_factory=list)  # ADR IDs
    affected_patterns: List[str] = field(default_factory=list)  # Pattern names
    constraint_conflicts: List[int] = field(default_factory=list)  # Constraint IDs

    # Analysis
    blast_radius_score: float = 0.0  # 0.0-1.0, how much of system affected
    reversibility_score: float = 1.0  # 0.0-1.0, how easy to reverse (1.0 = very easy)
    breaking_changes: bool = False

    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Metadata
    analysis_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "change_description": self.change_description,
            "risk_level": self.risk_level.value,
            "estimated_effort": self.estimated_effort.value,
            "affected_components": [
                {"name": c.name, "type": c.type.value, "path": c.path}
                for c in self.affected_components
            ],
            "affected_adrs": self.affected_adrs,
            "affected_patterns": self.affected_patterns,
            "constraint_conflicts": self.constraint_conflicts,
            "blast_radius_score": self.blast_radius_score,
            "reversibility_score": self.reversibility_score,
            "breaking_changes": self.breaking_changes,
            "recommendations": self.recommendations,
            "warnings": self.warnings,
            "analysis_timestamp": self.analysis_timestamp,
            "metadata": self.metadata,
        }


@dataclass
class ConstraintImpactReport:
    """Report of impact when adding/changing constraints."""

    constraint_description: str
    current_violations: int  # How many existing violations
    affected_files: List[str] = field(default_factory=list)
    affected_components: List[Component] = field(default_factory=list)
    estimated_fix_effort: EffortEstimate = EffortEstimate.MEDIUM
    breaking_changes: bool = False
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "constraint_description": self.constraint_description,
            "current_violations": self.current_violations,
            "affected_files": self.affected_files,
            "affected_components": [
                {"name": c.name, "type": c.type.value}
                for c in self.affected_components
            ],
            "estimated_fix_effort": self.estimated_fix_effort.value,
            "breaking_changes": self.breaking_changes,
            "recommendations": self.recommendations,
        }


class DependencyGraph:
    """Graph of architectural dependencies."""

    def __init__(self):
        self.nodes: Set[Component] = set()
        self.edges: List[Dependency] = []

    def add_component(self, component: Component) -> None:
        """Add a component to the graph."""
        self.nodes.add(component)

    def add_dependency(self, dependency: Dependency) -> None:
        """Add a dependency edge."""
        self.nodes.add(dependency.source)
        self.nodes.add(dependency.target)
        self.edges.append(dependency)

    def get_dependencies_of(self, component: Component) -> List[Dependency]:
        """Get all dependencies where component is the source."""
        return [dep for dep in self.edges if dep.source == component]

    def get_dependents_of(self, component: Component) -> List[Dependency]:
        """Get all dependencies where component is the target."""
        return [dep for dep in self.edges if dep.target == component]

    def get_transitive_dependents(
        self, component: Component, max_depth: int = 10
    ) -> Set[Component]:
        """Get all components that transitively depend on this component."""
        dependents = set()
        to_visit = {component}
        visited = set()
        depth = 0

        while to_visit and depth < max_depth:
            current = to_visit.pop()
            if current in visited:
                continue

            visited.add(current)
            direct_dependents = [
                dep.source for dep in self.get_dependents_of(current)
            ]

            for dependent in direct_dependents:
                if dependent != component:  # Avoid including starting component
                    dependents.add(dependent)
                    to_visit.add(dependent)

            depth += 1

        return dependents

    def calculate_blast_radius(self, component: Component) -> float:
        """Calculate blast radius: % of system affected by change to component.

        Returns:
            Float between 0.0-1.0
        """
        if not self.nodes:
            return 0.0

        affected = self.get_transitive_dependents(component)
        return len(affected) / len(self.nodes)

    def find_circular_dependencies(self) -> List[List[Component]]:
        """Find circular dependency chains."""
        cycles = []

        def dfs(node: Component, path: List[Component], visited: Set[Component]):
            if node in path:
                # Found cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:]
                if cycle not in cycles:
                    cycles.append(cycle)
                return

            if node in visited:
                return

            visited.add(node)
            path.append(node)

            for dep in self.get_dependencies_of(node):
                dfs(dep.target, path.copy(), visited)

        visited_global = set()
        for node in self.nodes:
            if node not in visited_global:
                dfs(node, [], visited_global)

        return cycles

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for visualization."""
        return {
            "nodes": [
                {
                    "id": str(node),
                    "name": node.name,
                    "type": node.type.value,
                    "path": node.path,
                }
                for node in self.nodes
            ],
            "edges": [
                {
                    "source": str(edge.source),
                    "target": str(edge.target),
                    "type": edge.dependency_type,
                    "strength": edge.strength,
                }
                for edge in self.edges
            ],
        }


class ImpactAnalyzer:
    """Analyzes impact of architectural changes."""

    def __init__(self, db: Database, project_root: Path):
        self.db = db
        self.project_root = project_root
        self._graph: Optional[DependencyGraph] = None

    def build_dependency_graph(self, project_id: int) -> DependencyGraph:
        """Build dependency graph from database.

        Includes:
        - ADR dependencies (ADR A references ADR B)
        - Pattern usage (Component uses Pattern)
        - Constraint coverage (Constraint applies to Component)
        """
        graph = DependencyGraph()

        # Add ADR nodes and dependencies
        cursor = self.db.conn.cursor()

        # Get all ADRs
        cursor.execute(
            """
            SELECT id, title, status
            FROM architecture_decisions
            WHERE project_id = %s
            """,
            (project_id,),
        )
        adrs = cursor.fetchall()

        for adr_id, title, status in adrs:
            component = Component(
                name=f"ADR-{adr_id}: {title}",
                type=ComponentType.MODULE,
                path=None,
                metadata={"adr_id": adr_id, "status": status},
            )
            graph.add_component(component)

        # Add pattern nodes
        cursor.execute(
            """
            SELECT DISTINCT dp.id, dp.name, dp.type
            FROM design_patterns dp
            JOIN pattern_usage pu ON dp.id = pu.pattern_id
            WHERE pu.project_id = %s
            """,
            (project_id,),
        )
        patterns = cursor.fetchall()

        for pattern_id, name, pattern_type in patterns:
            component = Component(
                name=f"Pattern: {name}",
                type=ComponentType.MODULE,
                metadata={"pattern_id": pattern_id, "pattern_type": pattern_type},
            )
            graph.add_component(component)

        # Add constraint nodes
        cursor.execute(
            """
            SELECT id, type, description, is_hard_constraint
            FROM architectural_constraints
            WHERE project_id = %s
            """,
            (project_id,),
        )
        constraints = cursor.fetchall()

        for constraint_id, ctype, description, is_hard in constraints:
            component = Component(
                name=f"Constraint: {description[:50]}",
                type=ComponentType.MODULE,
                metadata={
                    "constraint_id": constraint_id,
                    "constraint_type": ctype,
                    "is_hard": is_hard,
                },
            )
            graph.add_component(component)

        # TODO: Add dependencies between nodes
        # This would require parsing ADR content for references,
        # tracking which components use which patterns, etc.

        self._graph = graph
        return graph

    def analyze_adr_change(
        self,
        adr_id: int,
        proposed_change: str,
        project_id: Optional[int] = None,
    ) -> ImpactReport:
        """Analyze impact of changing an ADR.

        Args:
            adr_id: ID of ADR to change
            proposed_change: Description of proposed change
            project_id: Optional project ID (will query from ADR if not provided)

        Returns:
            ImpactReport with analysis results
        """
        cursor = self.db.conn.cursor()

        # Get ADR details
        cursor.execute(
            """
            SELECT project_id, title, decision, status
            FROM architecture_decisions
            WHERE id = %s
            """,
            (adr_id,),
        )
        row = cursor.fetchone()

        if not row:
            return ImpactReport(
                change_description=proposed_change,
                risk_level=RiskLevel.LOW,
                estimated_effort=EffortEstimate.TRIVIAL,
                warnings=[f"ADR {adr_id} not found"],
            )

        proj_id, title, decision, status = row
        if project_id is None:
            project_id = proj_id

        # Build dependency graph if not cached
        if self._graph is None:
            self.build_dependency_graph(project_id)

        # Find ADR component in graph
        adr_component = None
        for node in self._graph.nodes:
            if node.metadata.get("adr_id") == adr_id:
                adr_component = node
                break

        if adr_component is None:
            adr_component = Component(
                name=f"ADR-{adr_id}: {title}",
                type=ComponentType.MODULE,
                metadata={"adr_id": adr_id},
            )

        # Calculate impact
        blast_radius = self._graph.calculate_blast_radius(adr_component) if self._graph else 0.0
        affected_components = list(self._graph.get_transitive_dependents(adr_component)) if self._graph else []

        # Find related ADRs (simplified - would need reference parsing)
        cursor.execute(
            """
            SELECT id, title
            FROM architecture_decisions
            WHERE project_id = %s
              AND id != %s
              AND status = 'accepted'
            ORDER BY created_at DESC
            LIMIT 5
            """,
            (project_id, adr_id),
        )
        related_adrs = [row[0] for row in cursor.fetchall()]

        # Determine risk level based on blast radius and status
        if blast_radius > 0.5 or status == "accepted":
            risk_level = RiskLevel.HIGH
        elif blast_radius > 0.2:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        # Estimate effort
        num_affected = len(affected_components)
        if num_affected > 10:
            effort = EffortEstimate.VERY_HIGH
        elif num_affected > 5:
            effort = EffortEstimate.HIGH
        elif num_affected > 2:
            effort = EffortEstimate.MEDIUM
        else:
            effort = EffortEstimate.LOW

        # Generate recommendations
        recommendations = []
        warnings = []

        if status == "accepted":
            warnings.append(
                f"ADR-{adr_id} is currently accepted - changing it affects active architecture"
            )
            recommendations.append(
                f"Consider creating new ADR to supersede ADR-{adr_id} instead of modifying"
            )

        if blast_radius > 0.3:
            warnings.append(
                f"High blast radius ({blast_radius:.1%}) - many components affected"
            )
            recommendations.append("Plan migration strategy with incremental rollout")

        if related_adrs:
            recommendations.append(
                f"Review related ADRs: {', '.join(f'ADR-{id}' for id in related_adrs[:3])}"
            )

        return ImpactReport(
            change_description=proposed_change,
            risk_level=risk_level,
            estimated_effort=effort,
            affected_components=affected_components,
            affected_adrs=related_adrs,
            affected_patterns=[],
            constraint_conflicts=[],
            blast_radius_score=blast_radius,
            reversibility_score=1.0 - blast_radius,  # Harder to reverse if more affected
            breaking_changes=status == "accepted",
            recommendations=recommendations,
            warnings=warnings,
            metadata={
                "adr_id": adr_id,
                "adr_title": title,
                "current_status": status,
            },
        )

    def analyze_constraint_addition(
        self,
        constraint_description: str,
        constraint_type: str,
        validation_criteria: str,
        project_id: int,
    ) -> ConstraintImpactReport:
        """Analyze impact of adding a new constraint.

        This would check which existing code violates the proposed constraint.

        Args:
            constraint_description: What the constraint is
            constraint_type: performance/security/scalability/etc
            validation_criteria: How to validate it
            project_id: Project ID

        Returns:
            ConstraintImpactReport
        """
        # This is a simplified version - real implementation would
        # run fitness functions or static analysis to detect violations

        # For now, return estimated impact
        return ConstraintImpactReport(
            constraint_description=constraint_description,
            current_violations=0,  # Would need actual analysis
            affected_files=[],
            affected_components=[],
            estimated_fix_effort=EffortEstimate.MEDIUM,
            breaking_changes=False,
            recommendations=[
                "Run architecture fitness checks to detect current violations",
                f"Add fitness function to validate {constraint_type} constraint",
                "Communicate constraint to team before enforcement",
            ],
        )

    def get_dependency_graph(self, project_id: int) -> DependencyGraph:
        """Get or build dependency graph for project."""
        if self._graph is None:
            return self.build_dependency_graph(project_id)
        return self._graph

    def analyze_pattern_change(
        self,
        pattern_name: str,
        change_type: str,  # "adopt", "modify", "deprecate"
        project_id: int,
    ) -> ImpactReport:
        """Analyze impact of changing a design pattern."""
        cursor = self.db.conn.cursor()

        # Find pattern usage
        cursor.execute(
            """
            SELECT dp.id, dp.name, COUNT(pu.id) as usage_count
            FROM design_patterns dp
            LEFT JOIN pattern_usage pu ON dp.id = pu.pattern_id
            WHERE dp.name = %s AND (pu.project_id = %s OR pu.project_id IS NULL)
            GROUP BY dp.id, dp.name
            """,
            (pattern_name, project_id),
        )
        row = cursor.fetchone()

        if not row:
            return ImpactReport(
                change_description=f"{change_type} pattern: {pattern_name}",
                risk_level=RiskLevel.LOW,
                estimated_effort=EffortEstimate.LOW,
                recommendations=[f"Pattern '{pattern_name}' not found in usage history"],
            )

        pattern_id, name, usage_count = row

        # Determine impact based on usage
        if usage_count > 10:
            risk_level = RiskLevel.HIGH
            effort = EffortEstimate.VERY_HIGH
        elif usage_count > 5:
            risk_level = RiskLevel.MEDIUM
            effort = EffortEstimate.HIGH
        elif usage_count > 0:
            risk_level = RiskLevel.LOW
            effort = EffortEstimate.MEDIUM
        else:
            risk_level = RiskLevel.LOW
            effort = EffortEstimate.LOW

        recommendations = []
        if change_type == "deprecate" and usage_count > 0:
            recommendations.append(
                f"Pattern is used {usage_count} times - plan migration strategy"
            )
            recommendations.append("Suggest alternative pattern to migrate to")
            recommendations.append("Create deprecation timeline with team")

        return ImpactReport(
            change_description=f"{change_type} pattern: {pattern_name}",
            risk_level=risk_level,
            estimated_effort=effort,
            affected_patterns=[pattern_name],
            recommendations=recommendations,
            metadata={"pattern_id": pattern_id, "usage_count": usage_count},
        )
