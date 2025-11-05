"""Dependency Analyzer for code dependency mapping and analysis.

Provides:
- Code dependency mapping
- Coupling analysis
- Circular dependency detection
- Impact analysis for changes
- Dependency graphs and metrics
"""

from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .symbol_models import Symbol


class DependencyType(str, Enum):
    """Types of code dependencies."""
    CALLS = "calls"  # Function/method calls
    IMPORTS = "imports"  # Module imports
    INHERITS = "inherits"  # Class inheritance
    IMPLEMENTS = "implements"  # Interface implementation
    USES = "uses"  # General usage
    DEPENDS_ON = "depends_on"  # Generic dependency


class CouplingLevel(str, Enum):
    """Coupling strength between symbols."""
    LOOSE = "loose"  # 1-2 dependencies
    MODERATE = "moderate"  # 3-5 dependencies
    TIGHT = "tight"  # 6-10 dependencies
    VERY_TIGHT = "very_tight"  # >10 dependencies


@dataclass
class Dependency:
    """Single code dependency."""
    from_symbol: Symbol
    to_symbol: Symbol
    dependency_type: DependencyType
    strength: float  # 0-1, how critical this dependency is
    is_circular: bool = False
    path_length: int = 1


@dataclass
class DependencyMetrics:
    """Metrics for a symbol's dependencies."""
    symbol: Symbol
    incoming_count: int  # Number of symbols depending on this
    outgoing_count: int  # Number of symbols this depends on
    coupling_level: CouplingLevel
    is_hotspot: bool  # Frequently depended on
    is_isolated: bool  # No dependencies
    circular_dependencies: List[Dependency] = field(default_factory=list)
    impact_score: float = 0.0  # 0-1, impact if this changes


class DependencyAnalyzer:
    """Analyzes code dependencies and coupling."""

    def __init__(self):
        """Initialize analyzer."""
        self.dependencies: List[Dependency] = []
        self.metrics: Dict[str, DependencyMetrics] = {}
        self.circular_chains: List[List[Symbol]] = []

    def add_dependency(self, from_symbol: Symbol, to_symbol: Symbol,
                       dependency_type: DependencyType = DependencyType.USES,
                       strength: float = 0.5) -> None:
        """Add a dependency relationship.

        Args:
            from_symbol: Symbol that depends on another
            to_symbol: Symbol being depended on
            dependency_type: Type of dependency
            strength: How critical (0-1)
        """
        dep = Dependency(
            from_symbol=from_symbol,
            to_symbol=to_symbol,
            dependency_type=dependency_type,
            strength=strength
        )
        self.dependencies.append(dep)

    def analyze(self) -> Dict[str, DependencyMetrics]:
        """Analyze all dependencies.

        Returns:
            Dict of symbol name -> DependencyMetrics
        """
        self.metrics = {}
        all_symbols = set()

        # Collect all symbols
        for dep in self.dependencies:
            all_symbols.add(dep.from_symbol.full_qualified_name)
            all_symbols.add(dep.to_symbol.full_qualified_name)

        # Create metrics for each symbol
        for symbol_name in all_symbols:
            symbol = self._find_symbol(symbol_name)
            if symbol:
                metrics = self._calculate_metrics(symbol)
                self.metrics[symbol_name] = metrics

        # Detect circular dependencies
        self._detect_circular_dependencies()

        return self.metrics

    def _calculate_metrics(self, symbol: Symbol) -> DependencyMetrics:
        """Calculate dependency metrics for a symbol."""
        incoming = self._get_incoming_dependencies(symbol)
        outgoing = self._get_outgoing_dependencies(symbol)

        incoming_count = len(incoming)
        outgoing_count = len(outgoing)

        # Coupling level
        total_deps = incoming_count + outgoing_count
        if total_deps == 0:
            coupling_level = CouplingLevel.LOOSE
        elif total_deps <= 2:
            coupling_level = CouplingLevel.LOOSE
        elif total_deps <= 5:
            coupling_level = CouplingLevel.MODERATE
        elif total_deps <= 10:
            coupling_level = CouplingLevel.TIGHT
        else:
            coupling_level = CouplingLevel.VERY_TIGHT

        # Impact score (0-1)
        impact_score = min(1.0, (incoming_count * 0.7 + outgoing_count * 0.3) / 10.0)

        # Check if hotspot or isolated
        is_hotspot = incoming_count > 5
        is_isolated = incoming_count == 0 and outgoing_count == 0

        return DependencyMetrics(
            symbol=symbol,
            incoming_count=incoming_count,
            outgoing_count=outgoing_count,
            coupling_level=coupling_level,
            is_hotspot=is_hotspot,
            is_isolated=is_isolated,
            impact_score=impact_score,
        )

    def _get_incoming_dependencies(self, symbol: Symbol) -> List[Dependency]:
        """Get dependencies pointing to this symbol."""
        return [d for d in self.dependencies if d.to_symbol.full_qualified_name == symbol.full_qualified_name]

    def _get_outgoing_dependencies(self, symbol: Symbol) -> List[Dependency]:
        """Get dependencies from this symbol."""
        return [d for d in self.dependencies if d.from_symbol.full_qualified_name == symbol.full_qualified_name]

    def _find_symbol(self, full_name: str) -> Optional[Symbol]:
        """Find symbol by full qualified name."""
        for dep in self.dependencies:
            if dep.from_symbol.full_qualified_name == full_name:
                return dep.from_symbol
            if dep.to_symbol.full_qualified_name == full_name:
                return dep.to_symbol
        return None

    def _detect_circular_dependencies(self) -> None:
        """Detect circular dependency chains."""
        self.circular_chains = []
        visited: Set[str] = set()

        for dep in self.dependencies:
            if self._has_circular_path(dep.to_symbol, dep.from_symbol, visited=set()):
                dep.is_circular = True
                # Mark in metrics
                if dep.to_symbol.full_qualified_name in self.metrics:
                    self.metrics[dep.to_symbol.full_qualified_name].circular_dependencies.append(dep)
                if dep.from_symbol.full_qualified_name in self.metrics:
                    self.metrics[dep.from_symbol.full_qualified_name].circular_dependencies.append(dep)

    def _has_circular_path(self, current: Symbol, target: Symbol, visited: Set[str]) -> bool:
        """Check if there's a circular path from current to target."""
        if current.full_qualified_name in visited:
            return False

        visited.add(current.full_qualified_name)

        for dep in self._get_outgoing_dependencies(current):
            if dep.to_symbol.full_qualified_name == target.full_qualified_name:
                return True
            if self._has_circular_path(dep.to_symbol, target, visited):
                return True

        return False

    def get_hotspot_symbols(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get most frequently depended-on symbols.

        Args:
            limit: Number of hotspots to return

        Returns:
            List of (symbol_name, incoming_count) tuples
        """
        hotspots = sorted(
            [(name, m.incoming_count) for name, m in self.metrics.items()],
            key=lambda x: x[1],
            reverse=True
        )
        return hotspots[:limit]

    def get_isolated_symbols(self) -> List[str]:
        """Get symbols with no dependencies."""
        return [name for name, m in self.metrics.items() if m.is_isolated]

    def get_circular_chains(self) -> List[List[str]]:
        """Get all circular dependency chains."""
        chains = []
        for name, metrics in self.metrics.items():
            if metrics.circular_dependencies:
                chain = [name]
                for dep in metrics.circular_dependencies:
                    chain.append(dep.to_symbol.full_qualified_name)
                chains.append(chain)
        return chains

    def calculate_change_impact(self, symbol: Symbol) -> Dict:
        """Calculate impact of changing a symbol.

        Args:
            symbol: Symbol to analyze

        Returns:
            Impact analysis
        """
        if symbol.full_qualified_name not in self.metrics:
            return {"impact_scope": "unknown"}

        metrics = self.metrics[symbol.full_qualified_name]
        downstream = self._get_downstream_symbols(symbol)
        upstream = self._get_upstream_symbols(symbol)

        return {
            "symbol": symbol.name,
            "impact_scope": "high" if metrics.is_hotspot else "moderate" if metrics.incoming_count > 2 else "low",
            "affected_symbols": len(downstream),
            "dependent_symbols": len(upstream),
            "total_impact": len(downstream) + len(upstream),
            "is_critical": metrics.is_hotspot,
            "has_circular_deps": len(metrics.circular_dependencies) > 0,
        }

    def _get_downstream_symbols(self, symbol: Symbol, depth: int = 3) -> Set[str]:
        """Get all symbols that depend on this symbol."""
        downstream: Set[str] = set()
        if depth == 0:
            return downstream

        incoming = self._get_incoming_dependencies(symbol)
        for dep in incoming:
            downstream.add(dep.from_symbol.full_qualified_name)
            downstream.update(self._get_downstream_symbols(dep.from_symbol, depth - 1))

        return downstream

    def _get_upstream_symbols(self, symbol: Symbol, depth: int = 3) -> Set[str]:
        """Get all symbols this symbol depends on."""
        upstream: Set[str] = set()
        if depth == 0:
            return upstream

        outgoing = self._get_outgoing_dependencies(symbol)
        for dep in outgoing:
            upstream.add(dep.to_symbol.full_qualified_name)
            upstream.update(self._get_upstream_symbols(dep.to_symbol, depth - 1))

        return upstream

    def get_dependency_report(self) -> Dict:
        """Generate comprehensive dependency report."""
        if not self.metrics:
            return {"status": "no_dependencies"}

        hotspots = self.get_hotspot_symbols(5)
        isolated = self.get_isolated_symbols()
        circular = self.get_circular_chains()

        tight_coupling = sum(1 for m in self.metrics.values() if m.coupling_level == CouplingLevel.VERY_TIGHT)
        moderate_coupling = sum(1 for m in self.metrics.values() if m.coupling_level == CouplingLevel.MODERATE)

        return {
            "status": "analyzed",
            "total_symbols": len(self.metrics),
            "total_dependencies": len(self.dependencies),
            "hotspot_symbols": hotspots,
            "isolated_symbols": len(isolated),
            "tight_coupling_count": tight_coupling,
            "moderate_coupling_count": moderate_coupling,
            "circular_dependencies": len(circular),
            "circular_chains": circular,
            "average_incoming_deps": sum(m.incoming_count for m in self.metrics.values()) / max(1, len(self.metrics)),
            "average_outgoing_deps": sum(m.outgoing_count for m in self.metrics.values()) / max(1, len(self.metrics)),
        }
