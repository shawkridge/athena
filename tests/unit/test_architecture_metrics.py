"""Tests for architecture metrics analyzer."""

import pytest

from athena.symbols.symbol_models import Symbol, SymbolType, create_symbol
from athena.symbols.dependency_resolver import DependencyResolver, DependencyEdge
from athena.symbols.architecture_metrics import (
    ArchitectureAnalyzer,
    ArchitectureMetrics,
    CouplingType,
)


class TestArchitectureAnalyzerBasics:
    """Test basic architecture analyzer functionality."""

    def test_analyzer_initialization(self):
        """Test architecture analyzer can be created."""
        resolver = DependencyResolver()
        symbols = {}
        analyzer = ArchitectureAnalyzer(resolver, symbols)

        assert analyzer is not None
        assert len(analyzer.metrics) == 0

    def test_analyzer_with_single_module(self):
        """Test analyzer with single module."""
        resolver = DependencyResolver()
        symbol = create_symbol(
            file_path="main.py",
            symbol_type=SymbolType.FUNCTION,
            name="main",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="",
            language="python",
            visibility="public"
        )

        symbols = {"main.py": [symbol]}
        analyzer = ArchitectureAnalyzer(resolver, symbols)

        assert len(analyzer.metrics) == 1
        assert "main.py" in analyzer.metrics

    def test_metrics_creation(self):
        """Test creating architecture metrics."""
        metrics = ArchitectureMetrics(file_path="test.py")
        assert metrics.file_path == "test.py"
        assert metrics.afferent_coupling == 0
        assert metrics.efferent_coupling == 0
        assert metrics.instability == 0.0

    def test_get_module_metrics(self):
        """Test retrieving metrics for a module."""
        resolver = DependencyResolver()
        symbol = create_symbol(
            file_path="module.py",
            symbol_type=SymbolType.CLASS,
            name="MyClass",
            namespace="",
            signature="",
            line_start=1,
            line_end=10,
            code="",
            language="python",
            visibility="public"
        )

        symbols = {"module.py": [symbol]}
        analyzer = ArchitectureAnalyzer(resolver, symbols)

        metrics = analyzer.get_module_metrics("module.py")
        assert metrics is not None
        assert metrics.symbol_count == 1
        assert metrics.public_symbol_count == 1


class TestCouplingMetrics:
    """Test coupling metric calculations."""

    def test_afferent_coupling_calculation(self):
        """Test calculating afferent coupling."""
        resolver = DependencyResolver()

        sym_a = create_symbol(
            file_path="a.py",
            symbol_type=SymbolType.CLASS,
            name="ClassA",
            namespace="",
            signature="",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )
        sym_b = create_symbol(
            file_path="b.py",
            symbol_type=SymbolType.CLASS,
            name="ClassB",
            namespace="",
            signature="",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )

        resolver.add_symbols("a.py", [sym_a])
        resolver.add_symbols("b.py", [sym_b])

        symbols = {"a.py": [sym_a], "b.py": [sym_b]}
        analyzer = ArchitectureAnalyzer(resolver, symbols)

        # Check that afferent/efferent are calculated
        assert analyzer.metrics["a.py"].afferent_coupling >= 0
        assert analyzer.metrics["b.py"].efferent_coupling >= 0

    def test_efferent_coupling_calculation(self):
        """Test calculating efferent coupling."""
        resolver = DependencyResolver()

        sym_util = create_symbol(
            file_path="utils.py",
            symbol_type=SymbolType.FUNCTION,
            name="helper",
            namespace="",
            signature="()",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )
        sym_main = create_symbol(
            file_path="main.py",
            symbol_type=SymbolType.FUNCTION,
            name="main",
            namespace="",
            signature="()",
            line_start=10,
            line_end=10,
            code="",
            language="python",
            visibility="public"
        )

        resolver.add_symbols("utils.py", [sym_util])
        resolver.add_symbols("main.py", [sym_main])

        symbols = {"utils.py": [sym_util], "main.py": [sym_main]}
        analyzer = ArchitectureAnalyzer(resolver, symbols)

        # Check metrics exist
        assert "utils.py" in analyzer.metrics
        assert "main.py" in analyzer.metrics


class TestInstabilityMetrics:
    """Test instability calculations."""

    def test_instability_calculation_zero_coupling(self):
        """Test instability with zero coupling."""
        resolver = DependencyResolver()
        symbol = create_symbol(
            file_path="isolated.py",
            symbol_type=SymbolType.CLASS,
            name="Isolated",
            namespace="",
            signature="",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )

        resolver.add_symbols("isolated.py", [symbol])
        symbols = {"isolated.py": [symbol]}
        analyzer = ArchitectureAnalyzer(resolver, symbols)

        metrics = analyzer.metrics["isolated.py"]
        # With no coupling, instability should be 0
        assert metrics.instability == 0.0

    def test_instability_range(self):
        """Test that instability is between 0 and 1."""
        resolver = DependencyResolver()
        symbols_list = []

        for i in range(3):
            symbol = create_symbol(
                file_path=f"module{i}.py",
                symbol_type=SymbolType.CLASS,
                name=f"Class{i}",
                namespace="",
                signature="",
                line_start=1,
                line_end=1,
                code="",
                language="python",
                visibility="public"
            )
            symbols_list.append((f"module{i}.py", [symbol]))
            resolver.add_symbols(f"module{i}.py", [symbol])

        symbols = {fp: syms for fp, syms in symbols_list}
        analyzer = ArchitectureAnalyzer(resolver, symbols)

        for metrics in analyzer.metrics.values():
            assert 0.0 <= metrics.instability <= 1.0


class TestAbstractnessMetrics:
    """Test abstractness calculations."""

    def test_abstractness_with_interfaces(self):
        """Test abstractness calculation with interfaces."""
        resolver = DependencyResolver()

        symbols = [
            create_symbol(
                file_path="types.py",
                symbol_type=SymbolType.INTERFACE,
                name="Reader",
                namespace="",
                signature="",
                line_start=1,
                line_end=1,
                code="",
                language="python",
                visibility="public"
            ),
            create_symbol(
                file_path="types.py",
                symbol_type=SymbolType.CLASS,
                name="FileReader",
                namespace="",
                signature="",
                line_start=5,
                line_end=10,
                code="",
                language="python",
                visibility="public"
            ),
        ]

        resolver.add_symbols("types.py", symbols)
        analyzer = ArchitectureAnalyzer(resolver, {"types.py": symbols})

        metrics = analyzer.metrics["types.py"]
        # 1 interface out of 2 symbols = 0.5 abstractness
        assert metrics.abstractness == 0.5

    def test_abstractness_range(self):
        """Test that abstractness is between 0 and 1."""
        resolver = DependencyResolver()

        symbols = [
            create_symbol(
                file_path="test.py",
                symbol_type=SymbolType.CLASS,
                name=f"Class{i}",
                namespace="",
                signature="",
                line_start=i + 1,
                line_end=i + 1,
                code="",
                language="python",
                visibility="public"
            )
            for i in range(5)
        ]

        resolver.add_symbols("test.py", symbols)
        analyzer = ArchitectureAnalyzer(resolver, {"test.py": symbols})

        metrics = analyzer.metrics["test.py"]
        assert 0.0 <= metrics.abstractness <= 1.0


class TestNormalizedDistance:
    """Test normalized distance from main sequence."""

    def test_distance_calculation(self):
        """Test normalized distance calculation."""
        resolver = DependencyResolver()

        symbol = create_symbol(
            file_path="module.py",
            symbol_type=SymbolType.CLASS,
            name="Module",
            namespace="",
            signature="",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )

        resolver.add_symbols("module.py", [symbol])
        analyzer = ArchitectureAnalyzer(resolver, {"module.py": [symbol]})

        metrics = analyzer.metrics["module.py"]
        # Distance should be |A + I - 1|
        expected = abs(metrics.abstractness + metrics.instability - 1.0)
        assert abs(metrics.normalized_distance - expected) < 0.01

    def test_distance_range(self):
        """Test that distance is within reasonable range."""
        resolver = DependencyResolver()

        symbols = [
            create_symbol(
                file_path=f"mod{i}.py",
                symbol_type=SymbolType.CLASS,
                name=f"Mod{i}",
                namespace="",
                signature="",
                line_start=1,
                line_end=1,
                code="",
                language="python",
                visibility="public"
            )
            for i in range(3)
        ]

        for sym in symbols:
            resolver.add_symbols(sym.file_path, [sym])

        symbols_dict = {sym.file_path: [sym] for sym in symbols}
        analyzer = ArchitectureAnalyzer(resolver, symbols_dict)

        for metrics in analyzer.metrics.values():
            assert 0.0 <= metrics.normalized_distance <= 2.0


class TestHighCouplingDetection:
    """Test detection of high coupling modules."""

    def test_detect_high_coupling(self):
        """Test detecting high efferent coupling."""
        resolver = DependencyResolver()
        symbols_dict = {}

        # Create a module with many dependencies
        for i in range(7):
            symbol = create_symbol(
                file_path=f"dep{i}.py",
                symbol_type=SymbolType.CLASS,
                name=f"Dep{i}",
                namespace="",
                signature="",
                line_start=1,
                line_end=1,
                code="",
                language="python",
                visibility="public"
            )
            resolver.add_symbols(f"dep{i}.py", [symbol])
            symbols_dict[f"dep{i}.py"] = [symbol]

        analyzer = ArchitectureAnalyzer(resolver, symbols_dict)

        # Should detect modules with high coupling
        high_coupling = analyzer.detect_high_coupling_modules(threshold=3)
        assert isinstance(high_coupling, list)

    def test_high_coupling_returns_sorted(self):
        """Test that high coupling results are sorted."""
        resolver = DependencyResolver()
        symbols_dict = {}

        for i in range(3):
            symbol = create_symbol(
                file_path=f"mod{i}.py",
                symbol_type=SymbolType.CLASS,
                name=f"Mod{i}",
                namespace="",
                signature="",
                line_start=1,
                line_end=1,
                code="",
                language="python",
                visibility="public"
            )
            resolver.add_symbols(f"mod{i}.py", [symbol])
            symbols_dict[f"mod{i}.py"] = [symbol]

        analyzer = ArchitectureAnalyzer(resolver, symbols_dict)
        high_coupling = analyzer.detect_high_coupling_modules(threshold=0)

        # Check sorting
        for i in range(1, len(high_coupling)):
            assert high_coupling[i - 1][1] >= high_coupling[i][1]


class TestHighInstabilityDetection:
    """Test detection of high instability modules."""

    def test_detect_high_instability(self):
        """Test detecting high instability."""
        resolver = DependencyResolver()

        symbol = create_symbol(
            file_path="unstable.py",
            symbol_type=SymbolType.CLASS,
            name="Unstable",
            namespace="",
            signature="",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )

        resolver.add_symbols("unstable.py", [symbol])
        analyzer = ArchitectureAnalyzer(resolver, {"unstable.py": [symbol]})

        high_instability = analyzer.detect_high_instability_modules(threshold=0.5)
        assert isinstance(high_instability, list)

    def test_instability_detection_sorted(self):
        """Test that instability results are sorted."""
        resolver = DependencyResolver()
        symbols_dict = {}

        for i in range(3):
            symbol = create_symbol(
                file_path=f"mod{i}.py",
                symbol_type=SymbolType.CLASS,
                name=f"Mod{i}",
                namespace="",
                signature="",
                line_start=1,
                line_end=1,
                code="",
                language="python",
                visibility="public"
            )
            resolver.add_symbols(f"mod{i}.py", [symbol])
            symbols_dict[f"mod{i}.py"] = [symbol]

        analyzer = ArchitectureAnalyzer(resolver, symbols_dict)
        high_instability = analyzer.detect_high_instability_modules(threshold=0.0)

        # Check sorting
        for i in range(1, len(high_instability)):
            assert high_instability[i - 1][1] >= high_instability[i][1]


class TestGodModuleDetection:
    """Test detection of god modules."""

    def test_detect_god_module(self):
        """Test detecting god modules."""
        resolver = DependencyResolver()

        # Create module with many symbols
        symbols = [
            create_symbol(
                file_path="god.py",
                symbol_type=SymbolType.CLASS,
                name=f"Class{i}",
                namespace="",
                signature="",
                line_start=i * 10 + 1,
                line_end=i * 10 + 9,
                code="",
                language="python",
                visibility="public"
            )
            for i in range(25)
        ]

        resolver.add_symbols("god.py", symbols)
        analyzer = ArchitectureAnalyzer(resolver, {"god.py": symbols})

        god_modules = analyzer.detect_god_modules(symbol_threshold=20)
        assert len(god_modules) > 0
        assert god_modules[0][0] == "god.py"

    def test_god_module_sorted(self):
        """Test that god modules are sorted by size."""
        resolver = DependencyResolver()
        symbols_dict = {}

        for j in range(3):
            symbols = [
                create_symbol(
                    file_path=f"mod{j}.py",
                    symbol_type=SymbolType.CLASS,
                    name=f"Mod{j}_Class{i}",
                    namespace="",
                    signature="",
                    line_start=i + 1,
                    line_end=i + 1,
                    code="",
                    language="python",
                    visibility="public"
                )
                for i in range(10 + j * 5)  # Varying sizes
            ]
            resolver.add_symbols(f"mod{j}.py", symbols)
            symbols_dict[f"mod{j}.py"] = symbols

        analyzer = ArchitectureAnalyzer(resolver, symbols_dict)
        god_modules = analyzer.detect_god_modules(symbol_threshold=5)

        # Check sorting
        for i in range(1, len(god_modules)):
            assert god_modules[i - 1][1] >= god_modules[i][1]


class TestArchitectureStatistics:
    """Test architecture statistics."""

    def test_coupling_statistics_empty(self):
        """Test statistics on empty project."""
        resolver = DependencyResolver()
        analyzer = ArchitectureAnalyzer(resolver, {})

        stats = analyzer.get_coupling_statistics()
        assert stats["total_modules"] == 0

    def test_coupling_statistics_with_modules(self):
        """Test statistics with modules."""
        resolver = DependencyResolver()
        symbols_dict = {}

        for i in range(3):
            symbol = create_symbol(
                file_path=f"mod{i}.py",
                symbol_type=SymbolType.CLASS,
                name=f"Mod{i}",
                namespace="",
                signature="",
                line_start=1,
                line_end=1,
                code="",
                language="python",
                visibility="public"
            )
            resolver.add_symbols(f"mod{i}.py", [symbol])
            symbols_dict[f"mod{i}.py"] = [symbol]

        analyzer = ArchitectureAnalyzer(resolver, symbols_dict)
        stats = analyzer.get_coupling_statistics()

        assert stats["total_modules"] == 3
        assert "avg_afferent" in stats
        assert "avg_efferent" in stats
        assert "avg_instability" in stats


class TestDistanceViolations:
    """Test distance from main sequence violations."""

    def test_detect_distance_violations(self):
        """Test detecting modules far from main sequence."""
        resolver = DependencyResolver()

        symbol = create_symbol(
            file_path="far.py",
            symbol_type=SymbolType.CLASS,
            name="Far",
            namespace="",
            signature="",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )

        resolver.add_symbols("far.py", [symbol])
        analyzer = ArchitectureAnalyzer(resolver, {"far.py": [symbol]})

        violations = analyzer.detect_distance_violations(tolerance=0.05)
        assert isinstance(violations, list)


class TestArchitectureReporting:
    """Test architecture reporting."""

    def test_architecture_report_generation(self):
        """Test generating architecture report."""
        resolver = DependencyResolver()

        symbol = create_symbol(
            file_path="module.py",
            symbol_type=SymbolType.CLASS,
            name="Module",
            namespace="",
            signature="",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )

        resolver.add_symbols("module.py", [symbol])
        analyzer = ArchitectureAnalyzer(resolver, {"module.py": [symbol]})

        report = analyzer.get_architecture_report()
        assert "ARCHITECTURE METRICS REPORT" in report
        assert "Total Modules" in report

    def test_report_includes_statistics(self):
        """Test that report includes statistics."""
        resolver = DependencyResolver()

        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.CLASS,
            name="Test",
            namespace="",
            signature="",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )

        resolver.add_symbols("test.py", [symbol])
        analyzer = ArchitectureAnalyzer(resolver, {"test.py": [symbol]})

        report = analyzer.get_architecture_report()
        assert "Total Modules:            1" in report
        assert "Avg Afferent Coupling" in report


class TestRefactoringsuggestions:
    """Test refactoring suggestions."""

    def test_suggest_refactoring_empty(self):
        """Test suggestions for non-existent module."""
        resolver = DependencyResolver()
        analyzer = ArchitectureAnalyzer(resolver, {})

        suggestions = analyzer.suggest_refactoring("nonexistent.py")
        assert suggestions == []

    def test_suggest_refactoring_high_coupling(self):
        """Test suggestions for high coupling."""
        resolver = DependencyResolver()

        symbols = [
            create_symbol(
                file_path="coupled.py",
                symbol_type=SymbolType.CLASS,
                name=f"Class{i}",
                namespace="",
                signature="",
                line_start=i + 1,
                line_end=i + 1,
                code="",
                language="python",
                visibility="public"
            )
            for i in range(3)
        ]

        resolver.add_symbols("coupled.py", symbols)
        analyzer = ArchitectureAnalyzer(resolver, {"coupled.py": symbols})

        suggestions = analyzer.suggest_refactoring("coupled.py")
        assert isinstance(suggestions, list)

    def test_suggest_refactoring_too_many_symbols(self):
        """Test suggestions for god modules."""
        resolver = DependencyResolver()

        symbols = [
            create_symbol(
                file_path="god.py",
                symbol_type=SymbolType.CLASS,
                name=f"Class{i}",
                namespace="",
                signature="",
                line_start=i + 1,
                line_end=i + 1,
                code="",
                language="python",
                visibility="public"
            )
            for i in range(25)
        ]

        resolver.add_symbols("god.py", symbols)
        analyzer = ArchitectureAnalyzer(resolver, {"god.py": symbols})

        suggestions = analyzer.suggest_refactoring("god.py")
        assert len(suggestions) > 0
        assert any("symbols" in s.lower() for s in suggestions)
