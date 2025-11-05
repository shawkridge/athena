"""Architecture Metrics Analyzer for calculating coupling and cohesion.

Provides:
- Afferent coupling (incoming dependencies)
- Efferent coupling (outgoing dependencies)
- Instability metrics
- Coupling/cohesion analysis
- Module dependency metrics
"""

from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from .symbol_models import Symbol, SymbolType
from .dependency_resolver import DependencyResolver, DependencyEdge


class CouplingType(str, Enum):
    """Types of coupling between modules."""
    AFFERENT = "afferent"  # Incoming dependencies (fan-in)
    EFFERENT = "efferent"  # Outgoing dependencies (fan-out)
    STRUCTURAL = "structural"  # Structural coupling (shared symbols)


@dataclass
class ArchitectureMetrics:
    """Architecture metrics for a module/file."""
    file_path: str
    afferent_coupling: int = 0  # How many modules depend on this
    efferent_coupling: int = 0  # How many modules this depends on
    instability: float = 0.0  # (efferent) / (afferent + efferent)
    abstractness: float = 0.0  # Ratio of abstract symbols (interfaces, traits)
    symbol_count: int = 0
    public_symbol_count: int = 0
    private_symbol_count: int = 0
    interface_count: int = 0
    concrete_count: int = 0
    normalized_distance: float = 0.0  # Distance from main sequence


@dataclass
class CouplingViolation:
    """A detected coupling issue."""
    from_file: str
    to_file: str
    coupling_type: CouplingType
    severity: str  # low, medium, high, critical
    edge_count: int
    recommendation: str


class ArchitectureAnalyzer:
    """Analyzes architecture metrics for code modules."""

    def __init__(self, resolver: DependencyResolver, symbols_by_file: Dict[str, List[Symbol]]):
        """Initialize the architecture analyzer.

        Args:
            resolver: DependencyResolver with populated dependency graph
            symbols_by_file: Dictionary mapping file paths to symbol lists
        """
        self.resolver = resolver
        self.symbols_by_file = symbols_by_file
        self.metrics: Dict[str, ArchitectureMetrics] = {}
        self._compute_metrics()

    def _compute_metrics(self) -> None:
        """Compute architecture metrics for all files."""
        for file_path, symbols in self.symbols_by_file.items():
            metrics = ArchitectureMetrics(file_path=file_path)
            metrics.symbol_count = len(symbols)
            metrics.public_symbol_count = len([s for s in symbols if s.visibility == "public"])
            metrics.private_symbol_count = len([s for s in symbols if s.visibility == "private"])
            metrics.interface_count = len([s for s in symbols if s.symbol_type == SymbolType.INTERFACE])
            metrics.concrete_count = len([s for s in symbols if s.symbol_type == SymbolType.CLASS])

            # Compute coupling
            metrics.afferent_coupling = self._compute_afferent_coupling(file_path)
            metrics.efferent_coupling = self._compute_efferent_coupling(file_path)

            # Compute instability
            total_coupling = metrics.afferent_coupling + metrics.efferent_coupling
            if total_coupling > 0:
                metrics.instability = metrics.efferent_coupling / total_coupling
            else:
                metrics.instability = 0.0

            # Compute abstractness
            if metrics.symbol_count > 0:
                metrics.abstractness = metrics.interface_count / metrics.symbol_count
            else:
                metrics.abstractness = 0.0

            # Compute normalized distance from main sequence
            metrics.normalized_distance = self._compute_normalized_distance(metrics)

            self.metrics[file_path] = metrics

    def _compute_afferent_coupling(self, file_path: str) -> int:
        """Compute afferent coupling (incoming dependencies)."""
        count = 0
        for from_file, symbols in self.symbols_by_file.items():
            if from_file == file_path:
                continue

            for symbol in symbols:
                qname = symbol.full_qualified_name or f"{from_file}:{symbol.name}"
                # Check if this symbol depends on anything in target file
                edges = self.resolver.dependencies.get(qname, [])
                for edge in edges:
                    if edge.to_symbol and edge.to_symbol.file_path == file_path:
                        count += 1
                        break

        return count

    def _compute_efferent_coupling(self, file_path: str) -> int:
        """Compute efferent coupling (outgoing dependencies)."""
        count = 0
        symbols = self.symbols_by_file.get(file_path, [])
        dependencies_set: Set[str] = set()

        for symbol in symbols:
            qname = symbol.full_qualified_name or f"{file_path}:{symbol.name}"
            edges = self.resolver.dependencies.get(qname, [])
            for edge in edges:
                if edge.to_symbol and edge.to_symbol.file_path != file_path:
                    dep_file = edge.to_symbol.file_path
                    dependencies_set.add(dep_file)

        return len(dependencies_set)

    def _compute_normalized_distance(self, metrics: ArchitectureMetrics) -> float:
        """Compute normalized distance from main sequence.
        
        Formula: |A + I - 1| where A = abstractness, I = instability
        Lower is better (0 is on main sequence)
        """
        distance = abs(metrics.abstractness + metrics.instability - 1.0)
        return distance

    def detect_high_coupling_modules(self, threshold: int = 5) -> List[Tuple[str, int]]:
        """Detect modules with high efferent coupling.

        Args:
            threshold: Maximum acceptable efferent coupling

        Returns:
            List of (file_path, coupling_count) tuples
        """
        high_coupling = []
        for file_path, metrics in self.metrics.items():
            if metrics.efferent_coupling > threshold:
                high_coupling.append((file_path, metrics.efferent_coupling))

        return sorted(high_coupling, key=lambda x: x[1], reverse=True)

    def detect_high_instability_modules(self, threshold: float = 0.8) -> List[Tuple[str, float]]:
        """Detect modules with high instability.

        Args:
            threshold: Maximum acceptable instability (0.0 - 1.0)

        Returns:
            List of (file_path, instability) tuples
        """
        high_instability = []
        for file_path, metrics in self.metrics.items():
            if metrics.instability > threshold:
                high_instability.append((file_path, metrics.instability))

        return sorted(high_instability, key=lambda x: x[1], reverse=True)

    def detect_distance_violations(self, tolerance: float = 0.1) -> List[Tuple[str, float]]:
        """Detect modules far from main sequence.

        Args:
            tolerance: Maximum distance from main sequence

        Returns:
            List of (file_path, distance) tuples
        """
        violations = []
        for file_path, metrics in self.metrics.items():
            if metrics.normalized_distance > tolerance:
                violations.append((file_path, metrics.normalized_distance))

        return sorted(violations, key=lambda x: x[1], reverse=True)

    def detect_god_modules(self, symbol_threshold: int = 20) -> List[Tuple[str, int]]:
        """Detect 'god modules' (too many responsibilities).

        Args:
            symbol_threshold: Maximum acceptable symbols per module

        Returns:
            List of (file_path, symbol_count) tuples
        """
        god_modules = []
        for file_path, metrics in self.metrics.items():
            if metrics.symbol_count > symbol_threshold:
                god_modules.append((file_path, metrics.symbol_count))

        return sorted(god_modules, key=lambda x: x[1], reverse=True)

    def get_coupling_statistics(self) -> Dict:
        """Get coupling statistics across all modules.

        Returns:
            Dictionary with coupling metrics
        """
        if not self.metrics:
            return {
                "total_modules": 0,
                "avg_afferent": 0.0,
                "avg_efferent": 0.0,
                "avg_instability": 0.0,
                "avg_abstractness": 0.0,
                "max_efferent": 0,
                "max_afferent": 0,
            }

        total_afferent = sum(m.afferent_coupling for m in self.metrics.values())
        total_efferent = sum(m.efferent_coupling for m in self.metrics.values())
        total_instability = sum(m.instability for m in self.metrics.values())
        total_abstractness = sum(m.abstractness for m in self.metrics.values())

        count = len(self.metrics)

        return {
            "total_modules": count,
            "avg_afferent": total_afferent / count if count > 0 else 0.0,
            "avg_efferent": total_efferent / count if count > 0 else 0.0,
            "avg_instability": total_instability / count if count > 0 else 0.0,
            "avg_abstractness": total_abstractness / count if count > 0 else 0.0,
            "max_efferent": max((m.efferent_coupling for m in self.metrics.values()), default=0),
            "max_afferent": max((m.afferent_coupling for m in self.metrics.values()), default=0),
        }

    def get_architecture_report(self) -> str:
        """Generate a human-readable architecture report.

        Returns:
            Formatted report string
        """
        stats = self.get_coupling_statistics()
        report = "═" * 70 + "\n"
        report += "                    ARCHITECTURE METRICS REPORT\n"
        report += "═" * 70 + "\n\n"

        report += f"Total Modules:            {stats['total_modules']}\n"
        report += f"Avg Afferent Coupling:    {stats['avg_afferent']:.2f}\n"
        report += f"Avg Efferent Coupling:    {stats['avg_efferent']:.2f}\n"
        report += f"Avg Instability:          {stats['avg_instability']:.2f}\n"
        report += f"Avg Abstractness:         {stats['avg_abstractness']:.2f}\n"
        report += f"Max Efferent Coupling:    {stats['max_efferent']}\n"
        report += f"Max Afferent Coupling:    {stats['max_afferent']}\n\n"

        # High coupling modules
        high_coupling = self.detect_high_coupling_modules(threshold=3)
        if high_coupling:
            report += "─" * 70 + "\n"
            report += "High Efferent Coupling Modules:\n"
            report += "─" * 70 + "\n"
            for file_path, coupling in high_coupling[:5]:
                report += f"{file_path:40} coupling: {coupling}\n"

        # High instability
        high_instability = self.detect_high_instability_modules(threshold=0.7)
        if high_instability:
            report += "\n" + "─" * 70 + "\n"
            report += "High Instability Modules:\n"
            report += "─" * 70 + "\n"
            for file_path, instability in high_instability[:5]:
                report += f"{file_path:40} instability: {instability:.2f}\n"

        # God modules
        god_modules = self.detect_god_modules(symbol_threshold=15)
        if god_modules:
            report += "\n" + "─" * 70 + "\n"
            report += "God Modules (Too Many Symbols):\n"
            report += "─" * 70 + "\n"
            for file_path, symbol_count in god_modules[:5]:
                report += f"{file_path:40} symbols: {symbol_count}\n"

        return report

    def get_module_metrics(self, file_path: str) -> ArchitectureMetrics:
        """Get metrics for a specific module.

        Args:
            file_path: Path to the module

        Returns:
            ArchitectureMetrics for the module
        """
        return self.metrics.get(file_path)

    def suggest_refactoring(self, file_path: str) -> List[str]:
        """Suggest refactoring for a module.

        Args:
            file_path: Path to the module

        Returns:
            List of refactoring suggestions
        """
        suggestions = []
        metrics = self.metrics.get(file_path)

        if not metrics:
            return suggestions

        # High efferent coupling
        if metrics.efferent_coupling > 5:
            suggestions.append(
                f"High efferent coupling ({metrics.efferent_coupling}). "
                "Consider breaking into smaller modules or extracting dependencies."
            )

        # High instability
        if metrics.instability > 0.8:
            suggestions.append(
                f"High instability ({metrics.instability:.2f}). "
                "This module is unstable. Consider making it more abstract or reducing dependencies."
            )

        # Low abstractness but high instability
        if metrics.abstractness < 0.2 and metrics.instability > 0.6:
            suggestions.append(
                "Low abstractness with high instability. "
                "Consider extracting interfaces for better decoupling."
            )

        # Too many symbols
        if metrics.symbol_count > 20:
            suggestions.append(
                f"Too many symbols ({metrics.symbol_count}). "
                "Consider breaking this module into smaller, more focused modules."
            )

        # Distance from main sequence
        if metrics.normalized_distance > 0.15:
            suggestions.append(
                f"Far from main sequence (distance: {metrics.normalized_distance:.2f}). "
                "Consider adjusting abstractness or instability."
            )

        return suggestions
