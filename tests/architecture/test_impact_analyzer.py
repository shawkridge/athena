"""Tests for architecture impact analysis."""

from pathlib import Path

import pytest

from athena.architecture.impact_analyzer import (
    Component,
    ComponentType,
    Dependency,
    DependencyGraph,
    EffortEstimate,
    ImpactAnalyzer,
    RiskLevel,
)


@pytest.fixture
def sample_graph():
    """Create a sample dependency graph for testing."""
    graph = DependencyGraph()

    # Create components
    adr1 = Component("ADR-1: Use PostgreSQL", ComponentType.MODULE, metadata={"adr_id": 1})
    adr2 = Component("ADR-2: Use async pattern", ComponentType.MODULE, metadata={"adr_id": 2})
    adr3 = Component("ADR-3: Use Redis cache", ComponentType.MODULE, metadata={"adr_id": 3})

    api_layer = Component("API Layer", ComponentType.LAYER)
    data_layer = Component("Data Layer", ComponentType.LAYER)
    cache_layer = Component("Cache Layer", ComponentType.LAYER)

    # Add components
    for comp in [adr1, adr2, adr3, api_layer, data_layer, cache_layer]:
        graph.add_component(comp)

    # Add dependencies
    # API depends on Data and Cache
    graph.add_dependency(
        Dependency(api_layer, data_layer, "uses", strength=1.0)
    )
    graph.add_dependency(
        Dependency(api_layer, cache_layer, "uses", strength=0.8)
    )

    # Data layer depends on ADR-1 (PostgreSQL)
    graph.add_dependency(
        Dependency(data_layer, adr1, "implements", strength=1.0)
    )

    # Data layer depends on ADR-2 (async)
    graph.add_dependency(
        Dependency(data_layer, adr2, "implements", strength=1.0)
    )

    # Cache layer depends on ADR-3 (Redis)
    graph.add_dependency(
        Dependency(cache_layer, adr3, "implements", strength=1.0)
    )

    return graph


def test_dependency_graph_basics(sample_graph):
    """Test basic dependency graph operations."""
    assert len(sample_graph.nodes) == 6
    assert len(sample_graph.edges) == 5


def test_get_dependencies_of(sample_graph):
    """Test getting dependencies of a component."""
    api_layer = next(c for c in sample_graph.nodes if c.name == "API Layer")
    deps = sample_graph.get_dependencies_of(api_layer)

    assert len(deps) == 2
    target_names = {dep.target.name for dep in deps}
    assert "Data Layer" in target_names
    assert "Cache Layer" in target_names


def test_get_dependents_of(sample_graph):
    """Test getting dependents of a component."""
    data_layer = next(c for c in sample_graph.nodes if c.name == "Data Layer")
    dependents = sample_graph.get_dependents_of(data_layer)

    assert len(dependents) == 1
    assert dependents[0].source.name == "API Layer"


def test_transitive_dependents(sample_graph):
    """Test getting transitive dependents."""
    # ADR-1 (PostgreSQL) is used by Data Layer, which is used by API Layer
    adr1 = next(c for c in sample_graph.nodes if c.metadata.get("adr_id") == 1)
    transitive = sample_graph.get_transitive_dependents(adr1)

    # Should include both Data Layer and API Layer
    assert len(transitive) >= 2
    names = {c.name for c in transitive}
    assert "Data Layer" in names
    assert "API Layer" in names


def test_blast_radius_calculation(sample_graph):
    """Test blast radius calculation."""
    # ADR-1 affects Data Layer and API Layer (2 out of 6 components)
    adr1 = next(c for c in sample_graph.nodes if c.metadata.get("adr_id") == 1)
    blast_radius = sample_graph.calculate_blast_radius(adr1)

    # Should be approximately 2/6 = 0.33
    assert 0.2 <= blast_radius <= 0.5


def test_circular_dependencies():
    """Test circular dependency detection."""
    graph = DependencyGraph()

    # Create circular dependency: A -> B -> C -> A
    comp_a = Component("Component A", ComponentType.MODULE)
    comp_b = Component("Component B", ComponentType.MODULE)
    comp_c = Component("Component C", ComponentType.MODULE)

    graph.add_dependency(Dependency(comp_a, comp_b, "imports"))
    graph.add_dependency(Dependency(comp_b, comp_c, "imports"))
    graph.add_dependency(Dependency(comp_c, comp_a, "imports"))

    cycles = graph.find_circular_dependencies()

    # Should detect the cycle
    assert len(cycles) > 0


def test_graph_serialization(sample_graph):
    """Test graph serialization to dict."""
    graph_dict = sample_graph.to_dict()

    assert "nodes" in graph_dict
    assert "edges" in graph_dict
    assert len(graph_dict["nodes"]) == 6
    assert len(graph_dict["edges"]) == 5

    # Check node structure
    node = graph_dict["nodes"][0]
    assert "id" in node
    assert "name" in node
    assert "type" in node


def test_component_equality():
    """Test component equality and hashing."""
    comp1 = Component("Test", ComponentType.MODULE)
    comp2 = Component("Test", ComponentType.MODULE)
    comp3 = Component("Test", ComponentType.LAYER)

    # Same name and type should be equal
    assert comp1 == comp2
    assert hash(comp1) == hash(comp2)

    # Different type should not be equal
    assert comp1 != comp3


def test_impact_report_serialization():
    """Test impact report serialization."""
    from athena.architecture.impact_analyzer import ImpactReport

    comp = Component("Test Component", ComponentType.MODULE)

    report = ImpactReport(
        change_description="Test change",
        risk_level=RiskLevel.MEDIUM,
        estimated_effort=EffortEstimate.HIGH,
        affected_components=[comp],
        blast_radius_score=0.25,
        recommendations=["Test recommendation"],
    )

    # Convert to dict
    report_dict = report.to_dict()

    assert report_dict["risk_level"] == "medium"
    assert report_dict["estimated_effort"] == "high"
    assert report_dict["blast_radius_score"] == 0.25
    assert len(report_dict["affected_components"]) == 1
    assert len(report_dict["recommendations"]) == 1


def test_constraint_impact_report():
    """Test constraint impact report."""
    from athena.architecture.impact_analyzer import ConstraintImpactReport

    report = ConstraintImpactReport(
        constraint_description="API response time < 200ms",
        current_violations=5,
        affected_files=["api/users.py", "api/products.py"],
        estimated_fix_effort=EffortEstimate.MEDIUM,
        breaking_changes=True,
    )

    assert report.current_violations == 5
    assert len(report.affected_files) == 2

    # Convert to dict
    report_dict = report.to_dict()
    assert report_dict["current_violations"] == 5
    assert report_dict["breaking_changes"] is True


@pytest.mark.skip(reason="Requires database connection")
def test_impact_analyzer_adr_change():
    """Test ADR change impact analysis (integration test)."""
    from athena.core.database import get_database

    db = get_database()
    analyzer = ImpactAnalyzer(db, Path.cwd())

    # This would require actual database with ADRs
    # Skip in unit tests, but shows how to use
    impact = analyzer.analyze_adr_change(
        adr_id=1,
        proposed_change="Switch from PostgreSQL to MySQL",
    )

    assert impact.change_description == "Switch from PostgreSQL to MySQL"
    assert isinstance(impact.risk_level, RiskLevel)
    assert isinstance(impact.estimated_effort, EffortEstimate)


@pytest.mark.skip(reason="Requires database connection")
def test_build_dependency_graph():
    """Test building dependency graph from database (integration test)."""
    from athena.core.database import get_database

    db = get_database()
    analyzer = ImpactAnalyzer(db, Path.cwd())

    # This requires actual database
    graph = analyzer.build_dependency_graph(project_id=1)

    assert isinstance(graph, DependencyGraph)
    assert len(graph.nodes) > 0


def test_risk_level_ordering():
    """Test that risk levels can be compared."""
    assert RiskLevel.LOW.value == "low"
    assert RiskLevel.MEDIUM.value == "medium"
    assert RiskLevel.HIGH.value == "high"
    assert RiskLevel.CRITICAL.value == "critical"


def test_effort_estimate_ordering():
    """Test effort estimate values."""
    assert EffortEstimate.TRIVIAL.value == "trivial"
    assert EffortEstimate.LOW.value == "low"
    assert EffortEstimate.MEDIUM.value == "medium"
    assert EffortEstimate.HIGH.value == "high"
    assert EffortEstimate.VERY_HIGH.value == "very_high"


def test_empty_graph():
    """Test operations on empty graph."""
    graph = DependencyGraph()

    assert len(graph.nodes) == 0
    assert len(graph.edges) == 0

    comp = Component("Test", ComponentType.MODULE)
    deps = graph.get_dependencies_of(comp)
    assert len(deps) == 0

    blast_radius = graph.calculate_blast_radius(comp)
    assert blast_radius == 0.0


def test_graph_with_isolated_nodes():
    """Test graph with nodes that have no dependencies."""
    graph = DependencyGraph()

    comp1 = Component("Isolated 1", ComponentType.MODULE)
    comp2 = Component("Isolated 2", ComponentType.MODULE)

    graph.add_component(comp1)
    graph.add_component(comp2)

    assert len(graph.nodes) == 2
    assert len(graph.edges) == 0

    # Blast radius of isolated component should be 0
    blast_radius = graph.calculate_blast_radius(comp1)
    assert blast_radius == 0.0
