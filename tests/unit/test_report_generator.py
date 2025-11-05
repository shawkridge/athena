"""Unit tests for Report Generator.

Tests report generation including:
- Report generation from multiple metrics
- Format conversion (JSON, text, HTML)
- Section generation
- Metrics aggregation
- Recommendation generation
- File save operations
"""

import pytest
import json
import tempfile
from pathlib import Path
from athena.symbols.report_generator import ReportGenerator, AnalysisReport
from athena.symbols.symbol_models import Symbol, SymbolType, SymbolMetrics


@pytest.fixture
def generator():
    """Create a fresh report generator."""
    return ReportGenerator(project_name="Test Project")


@pytest.fixture
def sample_metrics():
    """Create sample analysis metrics."""
    return {
        "overall_score": 75.0,
        "health_score": 0.8,
        "total_issues": 5,
        "critical_issues": 1,
        "violations": [
            {"severity": "error", "message": "Test error", "symbol": "test_func"},
            {"severity": "warning", "message": "Test warning", "symbol": "test_func2"},
        ],
        "security_stats": {"mean": 0.8},
        "documentation_stats": {"mean": 0.6},
        "testability_stats": {"mean": 0.7},
    }


@pytest.fixture
def symbols():
    """Create test symbols."""
    return {
        "func1": Symbol(
            name="func1",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=1,
            line_end=10,
            namespace="",
            full_qualified_name="test.func1",
            signature="def func1():",
            code="",
            docstring="",
            metrics=SymbolMetrics(),
        ),
        "func2": Symbol(
            name="func2",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=20,
            line_end=30,
            namespace="",
            full_qualified_name="test.func2",
            signature="def func2():",
            code="",
            docstring="",
            metrics=SymbolMetrics(),
        ),
    }


# ============================================================================
# Initialization Tests
# ============================================================================


def test_generator_initialization(generator):
    """Test generator initializes correctly."""
    assert generator.project_name == "Test Project"
    assert generator.report is None


# ============================================================================
# Report Generation Tests
# ============================================================================


def test_generate_basic_report(generator, symbols, sample_metrics):
    """Test basic report generation."""
    report = generator.generate_report(
        symbols=symbols,
        quality_metrics=sample_metrics,
        complexity_metrics={"average_complexity": 10, "complex_count": 2},
        dependency_metrics={"hotspots": []},
        violations=[],
    )

    assert report.symbols_analyzed == 2
    assert report.quality_score == 75.0
    assert report.health_score == 0.8
    assert report.status == "good"


def test_report_status_excellent(generator, symbols):
    """Test excellent status determination."""
    metrics = {"overall_score": 90.0, "health_score": 0.95}

    report = generator.generate_report(
        symbols=symbols,
        quality_metrics=metrics,
        complexity_metrics={},
        dependency_metrics={},
        violations=[],
    )

    assert report.status == "excellent"


def test_report_status_poor(generator, symbols):
    """Test poor status determination."""
    metrics = {"overall_score": 35.0, "health_score": 0.3}

    report = generator.generate_report(
        symbols=symbols,
        quality_metrics=metrics,
        complexity_metrics={},
        dependency_metrics={},
        violations=[],
    )

    assert report.status == "critical"


# ============================================================================
# Finding Generation Tests
# ============================================================================


def test_findings_with_issues(generator, symbols, sample_metrics):
    """Test finding generation with issues."""
    report = generator.generate_report(
        symbols=symbols,
        quality_metrics=sample_metrics,
        complexity_metrics={"complex_count": 3},
        dependency_metrics={},
        violations=sample_metrics.get("violations", []),
    )

    assert len(report.findings) > 0
    assert any("issues" in f.lower() for f in report.findings)


def test_findings_with_no_issues(generator, symbols):
    """Test finding generation with no issues."""
    metrics = {
        "overall_score": 95.0,
        "health_score": 0.95,
        "total_issues": 0,
        "critical_issues": 0,
    }

    report = generator.generate_report(
        symbols=symbols,
        quality_metrics=metrics,
        complexity_metrics={"complex_count": 0},
        dependency_metrics={},
        violations=[],
    )

    assert len(report.findings) > 0


# ============================================================================
# Recommendation Generation Tests
# ============================================================================


def test_recommendations_urgent(generator, symbols, sample_metrics):
    """Test urgent recommendations."""
    metrics = sample_metrics.copy()
    metrics["critical_issues"] = 5

    report = generator.generate_report(
        symbols=symbols,
        quality_metrics=metrics,
        complexity_metrics={},
        dependency_metrics={},
        violations=[],
    )

    assert any("URGENT" in r for r in report.recommendations)


def test_recommendations_complexity(generator, symbols):
    """Test complexity recommendations."""
    metrics = {
        "overall_score": 70.0,
        "health_score": 0.7,
        "critical_issues": 0,
    }

    report = generator.generate_report(
        symbols=symbols,
        quality_metrics=metrics,
        complexity_metrics={"complex_count": 5},
        dependency_metrics={},
        violations=[],
    )

    assert any("complex" in r.lower() for r in report.recommendations)


# ============================================================================
# Metrics Collection Tests
# ============================================================================


def test_metrics_collection(generator, symbols, sample_metrics):
    """Test metrics collection."""
    complexity = {"average_complexity": 12, "complex_count": 2}
    dependency = {"hotspots": ["func1"]}

    report = generator.generate_report(
        symbols=symbols,
        quality_metrics=sample_metrics,
        complexity_metrics=complexity,
        dependency_metrics=dependency,
        violations=[],
    )

    assert "summary" in report.metrics
    assert report.metrics["summary"]["quality_score"] == 75.0


# ============================================================================
# High Risk Items Tests
# ============================================================================


def test_identify_high_risk_items(generator, symbols):
    """Test high-risk item identification."""
    violations = [
        {"severity": "critical", "symbol": "func1", "message": "Critical issue"},
        {"severity": "error", "symbol": "func2", "message": "Error issue"},
        {"severity": "warning", "symbol": "func1", "message": "Warning"},
    ]

    report = generator.generate_report(
        symbols=symbols,
        quality_metrics={"overall_score": 50.0, "health_score": 0.5},
        complexity_metrics={},
        dependency_metrics={},
        violations=violations,
    )

    assert len(report.high_risk_items) > 0


# ============================================================================
# Improvement Opportunities Tests
# ============================================================================


def test_improvement_opportunities(generator, symbols):
    """Test improvement opportunity identification."""
    metrics = {
        "overall_score": 70.0,
        "health_score": 0.7,
        "security_stats": {"mean": 0.5},
        "documentation_stats": {"mean": 0.4},
    }

    report = generator.generate_report(
        symbols=symbols,
        quality_metrics=metrics,
        complexity_metrics={"average_complexity": 20},
        dependency_metrics={},
        violations=[],
    )

    assert len(report.improvement_opportunities) > 0


# ============================================================================
# JSON Export Tests
# ============================================================================


def test_to_json(generator, symbols, sample_metrics):
    """Test JSON export."""
    report = generator.generate_report(
        symbols=symbols,
        quality_metrics=sample_metrics,
        complexity_metrics={},
        dependency_metrics={},
        violations=[],
    )

    json_str = generator.to_json()

    assert json_str is not None
    data = json.loads(json_str)
    assert data["title"] == "Test Project - Code Analysis Report"
    assert data["quality_score"] == 75.0


def test_json_valid_format(generator, symbols):
    """Test that JSON is valid."""
    metrics = {"overall_score": 80.0, "health_score": 0.8}

    generator.generate_report(
        symbols=symbols,
        quality_metrics=metrics,
        complexity_metrics={},
        dependency_metrics={},
        violations=[],
    )

    json_str = generator.to_json()

    # Should not raise exception
    parsed = json.loads(json_str)
    assert isinstance(parsed, dict)


# ============================================================================
# Text Export Tests
# ============================================================================


def test_to_text(generator, symbols, sample_metrics):
    """Test text export."""
    report = generator.generate_report(
        symbols=symbols,
        quality_metrics=sample_metrics,
        complexity_metrics={},
        dependency_metrics={},
        violations=[],
    )

    text = generator.to_text()

    assert "Test Project" in text
    assert "Quality Score" in text
    assert "EXECUTIVE SUMMARY" in text


def test_text_includes_sections(generator, symbols):
    """Test that text includes all sections."""
    metrics = {"overall_score": 75.0, "health_score": 0.8}

    generator.generate_report(
        symbols=symbols,
        quality_metrics=metrics,
        complexity_metrics={},
        dependency_metrics={},
        violations=[],
    )

    text = generator.to_text()

    assert "KEY FINDINGS" in text
    assert "RECOMMENDATIONS" in text
    assert "HIGH-RISK ITEMS" in text


# ============================================================================
# HTML Export Tests
# ============================================================================


def test_to_html(generator, symbols, sample_metrics):
    """Test HTML export."""
    report = generator.generate_report(
        symbols=symbols,
        quality_metrics=sample_metrics,
        complexity_metrics={},
        dependency_metrics={},
        violations=[],
    )

    html = generator.to_html()

    assert "<!DOCTYPE html>" in html
    assert "<title>" in html
    assert "Test Project" in html


def test_html_includes_status_styling(generator, symbols):
    """Test HTML includes status styling."""
    metrics = {"overall_score": 90.0, "health_score": 0.9}

    generator.generate_report(
        symbols=symbols,
        quality_metrics=metrics,
        complexity_metrics={},
        dependency_metrics={},
        violations=[],
    )

    html = generator.to_html()

    assert "status" in html
    assert "excellent" in html


# ============================================================================
# File Save Tests
# ============================================================================


def test_save_json_report():
    """Test saving JSON report to file."""
    generator = ReportGenerator("Test")
    symbols = {"func1": Symbol(
        name="func1",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=10,
        namespace="",
        full_qualified_name="test.func1",
        signature="def func1():",
        code="",
        docstring="",
        metrics=SymbolMetrics(),
    )}

    generator.generate_report(
        symbols=symbols,
        quality_metrics={"overall_score": 80.0, "health_score": 0.8},
        complexity_metrics={},
        dependency_metrics={},
        violations=[],
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "report.json"
        result = generator.save_report(str(filepath), format="json")

        assert result is True
        assert filepath.exists()
        with open(filepath) as f:
            data = json.load(f)
            assert data["quality_score"] == 80.0


def test_save_text_report():
    """Test saving text report to file."""
    generator = ReportGenerator("Test")
    symbols = {"func1": Symbol(
        name="func1",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=10,
        namespace="",
        full_qualified_name="test.func1",
        signature="def func1():",
        code="",
        docstring="",
        metrics=SymbolMetrics(),
    )}

    generator.generate_report(
        symbols=symbols,
        quality_metrics={"overall_score": 80.0, "health_score": 0.8},
        complexity_metrics={},
        dependency_metrics={},
        violations=[],
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "report.txt"
        result = generator.save_report(str(filepath), format="text")

        assert result is True
        assert filepath.exists()


def test_save_html_report():
    """Test saving HTML report to file."""
    generator = ReportGenerator("Test")
    symbols = {"func1": Symbol(
        name="func1",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=10,
        namespace="",
        full_qualified_name="test.func1",
        signature="def func1():",
        code="",
        docstring="",
        metrics=SymbolMetrics(),
    )}

    generator.generate_report(
        symbols=symbols,
        quality_metrics={"overall_score": 80.0, "health_score": 0.8},
        complexity_metrics={},
        dependency_metrics={},
        violations=[],
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "report.html"
        result = generator.save_report(str(filepath), format="html")

        assert result is True
        assert filepath.exists()


def test_save_invalid_format():
    """Test saving with invalid format."""
    generator = ReportGenerator("Test")
    symbols = {"func1": Symbol(
        name="func1",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=10,
        namespace="",
        full_qualified_name="test.func1",
        signature="def func1():",
        code="",
        docstring="",
        metrics=SymbolMetrics(),
    )}

    generator.generate_report(
        symbols=symbols,
        quality_metrics={"overall_score": 80.0, "health_score": 0.8},
        complexity_metrics={},
        dependency_metrics={},
        violations=[],
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "report.xyz"
        result = generator.save_report(str(filepath), format="xyz")

        assert result is False


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_report_workflow(symbols, sample_metrics):
    """Test complete report generation workflow."""
    generator = ReportGenerator("Integration Test")

    # Generate report
    report = generator.generate_report(
        symbols=symbols,
        quality_metrics=sample_metrics,
        complexity_metrics={"average_complexity": 12, "complex_count": 2},
        dependency_metrics={"hotspots": []},
        violations=sample_metrics.get("violations", []),
    )

    # Verify report created
    assert report is not None
    assert report.symbols_analyzed == 2

    # Test all export formats
    json_str = generator.to_json()
    text_str = generator.to_text()
    html_str = generator.to_html()

    assert len(json_str) > 0
    assert len(text_str) > 0
    assert len(html_str) > 0

    # Test file save
    with tempfile.TemporaryDirectory() as tmpdir:
        json_ok = generator.save_report(Path(tmpdir) / "test.json", format="json")
        text_ok = generator.save_report(Path(tmpdir) / "test.txt", format="text")
        html_ok = generator.save_report(Path(tmpdir) / "test.html", format="html")

        assert all([json_ok, text_ok, html_ok])
