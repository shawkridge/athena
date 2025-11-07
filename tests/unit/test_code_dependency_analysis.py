"""Tests for code dependency analysis."""

import pytest

from src.athena.code_search.code_dependency_analysis import (
    DependencyType,
    Dependency,
    DependencyMetrics,
    DependencyGraph,
    DependencyAnalyzer,
)


class TestDependency:
    """Tests for Dependency."""

    def test_dependency_creation(self):
        """Test creating dependency."""
        dep = Dependency(
            source="process_data",
            target="validate_input",
            source_file="utils.py",
            target_file="validators.py",
            dependency_type=DependencyType.FUNCTION_CALL,
            line_number=10,
        )

        assert dep.source == "process_data"
        assert dep.target == "validate_input"
        assert dep.dependency_type == DependencyType.FUNCTION_CALL

    def test_dependency_to_dict(self):
        """Test dependency serialization."""
        dep = Dependency(
            source="ClassA",
            target="ClassB",
            source_file="models.py",
            target_file="base.py",
            dependency_type=DependencyType.CLASS_INHERITANCE,
            is_external=False,
            strength=0.9,
        )

        dep_dict = dep.to_dict()
        assert dep_dict["source"] == "ClassA"
        assert dep_dict["dependency_type"] == "inheritance"
        assert dep_dict["strength"] == 0.9


class TestDependencyMetrics:
    """Tests for DependencyMetrics."""

    def test_metrics_creation(self):
        """Test creating metrics."""
        metrics = DependencyMetrics(
            entity_name="my_function",
            file_path="utils.py",
            incoming_dependencies=3,
            outgoing_dependencies=2,
        )

        assert metrics.entity_name == "my_function"
        assert metrics.incoming_dependencies == 3
        assert metrics.outgoing_dependencies == 2


class TestDependencyGraph:
    """Tests for DependencyGraph."""

    @pytest.fixture
    def graph(self):
        """Create dependency graph."""
        return DependencyGraph()

    @pytest.fixture
    def sample_dependencies(self):
        """Create sample dependencies."""
        return [
            Dependency(
                source="func_a",
                target="func_b",
                source_file="module1.py",
                target_file="module1.py",
                dependency_type=DependencyType.FUNCTION_CALL,
            ),
            Dependency(
                source="func_b",
                target="func_c",
                source_file="module1.py",
                target_file="module2.py",
                dependency_type=DependencyType.FUNCTION_CALL,
            ),
            Dependency(
                source="ClassA",
                target="ClassB",
                source_file="models.py",
                target_file="base.py",
                dependency_type=DependencyType.CLASS_INHERITANCE,
            ),
        ]

    def test_add_dependency(self, graph, sample_dependencies):
        """Test adding dependencies."""
        graph.add_dependency(sample_dependencies[0])

        assert len(graph.dependencies) == 1
        assert "func_b" in graph.graph["func_a"]

    def test_get_direct_dependencies(self, graph, sample_dependencies):
        """Test getting direct dependencies."""
        for dep in sample_dependencies:
            graph.add_dependency(dep)

        deps = graph.get_direct_dependencies("func_a")
        assert "func_b" in deps

    def test_get_dependents(self, graph, sample_dependencies):
        """Test getting dependents."""
        for dep in sample_dependencies:
            graph.add_dependency(dep)

        dependents = graph.get_dependents("func_b")
        assert "func_a" in dependents

    def test_find_import_chain(self, graph, sample_dependencies):
        """Test finding import chains."""
        for dep in sample_dependencies:
            graph.add_dependency(dep)

        chain = graph.find_import_chain("func_a", "func_c")
        assert chain is not None
        assert chain[0] == "func_a"
        assert chain[-1] == "func_c"

    def test_find_import_chain_no_path(self, graph, sample_dependencies):
        """Test import chain when no path exists."""
        for dep in sample_dependencies:
            graph.add_dependency(dep)

        chain = graph.find_import_chain("func_c", "func_a")
        assert chain is None

    def test_find_circular_dependencies_no_cycles(self, graph, sample_dependencies):
        """Test circular dependency detection with no cycles."""
        for dep in sample_dependencies:
            graph.add_dependency(dep)

        cycles = graph.find_circular_dependencies()
        assert isinstance(cycles, list)

    def test_find_circular_dependencies_with_cycle(self, graph):
        """Test circular dependency detection."""
        # Create cycle: a -> b -> c -> a
        graph.add_dependency(
            Dependency(
                source="a",
                target="b",
                source_file="test.py",
                target_file="test.py",
                dependency_type=DependencyType.FUNCTION_CALL,
            )
        )
        graph.add_dependency(
            Dependency(
                source="b",
                target="c",
                source_file="test.py",
                target_file="test.py",
                dependency_type=DependencyType.FUNCTION_CALL,
            )
        )
        graph.add_dependency(
            Dependency(
                source="c",
                target="a",
                source_file="test.py",
                target_file="test.py",
                dependency_type=DependencyType.FUNCTION_CALL,
            )
        )

        cycles = graph.find_circular_dependencies()
        assert len(cycles) >= 1

    def test_get_dependency_metrics(self, graph, sample_dependencies):
        """Test dependency metrics calculation."""
        for dep in sample_dependencies:
            graph.add_dependency(dep)

        metrics = graph.get_dependency_metrics("func_a")
        assert metrics.entity_name == "func_a"
        assert metrics.outgoing_dependencies >= 1
        assert 0.0 <= metrics.instability <= 1.0

    def test_get_file_dependencies(self, graph, sample_dependencies):
        """Test file-level dependency analysis."""
        for dep in sample_dependencies:
            graph.add_dependency(dep)

        file_deps = graph.get_file_dependencies("module1.py")
        assert file_deps["file_path"] == "module1.py"
        assert "outgoing_file_dependencies" in file_deps

    def test_find_problematic_dependencies(self, graph, sample_dependencies):
        """Test finding problematic dependencies."""
        for dep in sample_dependencies:
            graph.add_dependency(dep)

        problematic = graph.find_problematic_dependencies(instability_threshold=0.5)
        assert isinstance(problematic, list)


class TestDependencyAnalyzer:
    """Tests for DependencyAnalyzer."""

    @pytest.fixture
    def setup(self):
        """Setup analyzer with sample graph."""
        graph = DependencyGraph()

        # Create complex dependency structure
        dependencies = [
            Dependency(
                source="ServiceA",
                target="ServiceB",
                source_file="service_a.py",
                target_file="service_b.py",
                dependency_type=DependencyType.FUNCTION_CALL,
            ),
            Dependency(
                source="ServiceB",
                target="ServiceA",
                source_file="service_b.py",
                target_file="service_a.py",
                dependency_type=DependencyType.FUNCTION_CALL,
            ),
            Dependency(
                source="ServiceC",
                target="ServiceA",
                source_file="service_c.py",
                target_file="service_a.py",
                dependency_type=DependencyType.FUNCTION_CALL,
            ),
            Dependency(
                source="ServiceD",
                target="ServiceA",
                source_file="service_d.py",
                target_file="service_a.py",
                dependency_type=DependencyType.FUNCTION_CALL,
            ),
        ]

        for dep in dependencies:
            graph.add_dependency(dep)

        analyzer = DependencyAnalyzer(graph)
        return analyzer, graph

    def test_detect_high_coupling_pairs(self, setup):
        """Test high coupling detection."""
        analyzer, _ = setup

        coupling_pairs = analyzer.detect_high_coupling_pairs(threshold=1)
        assert isinstance(coupling_pairs, list)

    def test_find_stable_entities(self, setup):
        """Test finding stable entities."""
        analyzer, _ = setup

        stable = analyzer.find_stable_entities()
        assert isinstance(stable, list)

    def test_find_bottleneck_entities(self, setup):
        """Test finding bottleneck entities."""
        analyzer, _ = setup

        bottlenecks = analyzer.find_bottleneck_entities()
        assert isinstance(bottlenecks, list)
        # ServiceA should be a bottleneck (many dependents)
        if bottlenecks:
            assert any("A" in b for b in bottlenecks)

    def test_calculate_average_path_length(self, setup):
        """Test average path length calculation."""
        analyzer, _ = setup

        avg_length = analyzer.calculate_average_path_length()
        assert isinstance(avg_length, float)
        assert avg_length >= 0.0

    def test_generate_dependency_report(self, setup):
        """Test report generation."""
        analyzer, _ = setup

        report = analyzer.generate_dependency_report()
        assert "DEPENDENCY ANALYSIS REPORT" in report
        assert "Total Dependencies" in report


class TestDependencyIntegration:
    """Integration tests for dependency analysis."""

    def test_full_dependency_workflow(self):
        """Test complete dependency analysis workflow."""
        # Create graph
        graph = DependencyGraph()

        # Add realistic dependency structure
        modules = [
            ("UserService", "auth.py", "Database", "db.py", DependencyType.FUNCTION_CALL),
            ("UserService", "auth.py", "Logger", "logger.py", DependencyType.FUNCTION_CALL),
            ("AuthController", "controller.py", "UserService", "auth.py", DependencyType.FUNCTION_CALL),
            ("Database", "db.py", "Connection", "connection.py", DependencyType.CLASS_INHERITANCE),
            ("APIClient", "api.py", "AuthController", "controller.py", DependencyType.FUNCTION_CALL),
        ]

        for source, src_file, target, tgt_file, dep_type in modules:
            graph.add_dependency(
                Dependency(
                    source=source,
                    target=target,
                    source_file=src_file,
                    target_file=tgt_file,
                    dependency_type=dep_type,
                )
            )

        # Analyze
        analyzer = DependencyAnalyzer(graph)

        # Test various analyses
        cycles = graph.find_circular_dependencies()
        assert isinstance(cycles, list)

        metrics = graph.get_dependency_metrics("UserService")
        assert metrics.entity_name == "UserService"
        assert metrics.outgoing_dependencies >= 2

        file_deps = graph.get_file_dependencies("auth.py")
        assert file_deps["file_path"] == "auth.py"

        stable = analyzer.find_stable_entities()
        assert isinstance(stable, list)

        bottlenecks = analyzer.find_bottleneck_entities()
        assert isinstance(bottlenecks, list)

        # Generate report
        report = analyzer.generate_dependency_report()
        assert len(report) > 0
        assert "Total Dependencies" in report

        # Verify all dependencies are tracked
        assert len(graph.dependencies) == len(modules)
