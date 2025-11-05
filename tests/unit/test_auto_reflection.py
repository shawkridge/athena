"""Tests for automatic reflection scheduling (Gap 6)."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from athena.core.database import Database
from athena.reflection.scheduler import (
    ReflectionMetrics,
    ReflectionAlert,
    ReflectionMetricsStore,
    TrendAnalyzer,
)
from athena.mcp.handlers import MemoryMCPServer


@pytest.fixture
def mcp_server(tmp_path):
    """Create an MCP server for testing."""
    db_path = tmp_path / "test.db"
    server = MemoryMCPServer(str(db_path))
    return server


@pytest.fixture
def project(mcp_server):
    """Create a test project."""
    return mcp_server.project_manager.get_or_create_project("test-project")


def test_reflection_metrics_store_record(mcp_server):
    """Test recording reflection metrics."""
    metrics = ReflectionMetrics(
        project_id=1,
        timestamp=datetime.now(),
        accuracy=0.95,
        false_positive_rate=0.02,
        gap_count=5,
        contradiction_count=0,
        memory_size_bytes=1000000,
        query_latency_ms=45.0,
        wm_utilization=0.6,
        cognitive_load="healthy",
        workload_trend="stable"
    )

    store = ReflectionMetricsStore(mcp_server.store.db)
    metrics_id = store.record_metrics(metrics)

    assert metrics_id > 0


def test_reflection_metrics_store_retrieve(mcp_server):
    """Test retrieving reflection metrics."""
    store = ReflectionMetricsStore(mcp_server.store.db)

    # Record a metric
    metrics = ReflectionMetrics(
        project_id=1,
        timestamp=datetime.now(),
        accuracy=0.95,
        false_positive_rate=0.02,
        gap_count=5,
        contradiction_count=0,
        memory_size_bytes=1000000,
        query_latency_ms=45.0,
        wm_utilization=0.6,
        cognitive_load="healthy",
        workload_trend="stable"
    )
    store.record_metrics(metrics)

    # Retrieve it
    recent = store.get_recent_metrics(project_id=1, hours=24)
    assert len(recent) == 1
    assert recent[0].accuracy == 0.95
    assert recent[0].gap_count == 5


def test_reflection_alert_record(mcp_server):
    """Test recording reflection alerts."""
    store = ReflectionMetricsStore(mcp_server.store.db)

    alert = ReflectionAlert(
        project_id=1,
        alert_type="quality_degradation",
        severity="high",
        message="Memory accuracy degraded",
        recommended_action="/consolidate",
        created_at=datetime.now()
    )

    alert_id = store.record_alert(alert)
    assert alert_id > 0


def test_reflection_alert_retrieve(mcp_server):
    """Test retrieving active alerts."""
    store = ReflectionMetricsStore(mcp_server.store.db)

    alert = ReflectionAlert(
        project_id=1,
        alert_type="quality_degradation",
        severity="high",
        message="Memory accuracy degraded",
        recommended_action="/consolidate",
        created_at=datetime.now()
    )
    store.record_alert(alert)

    # Retrieve active alerts
    active = store.get_active_alerts(project_id=1)
    assert len(active) == 1
    assert active[0].alert_type == "quality_degradation"


def test_trend_analyzer_quality_degradation():
    """Test quality degradation detection."""
    metrics = [
        ReflectionMetrics(
            project_id=1, timestamp=datetime.now(),
            accuracy=0.85, false_positive_rate=0.03,
            gap_count=5, contradiction_count=0,
            memory_size_bytes=1000000, query_latency_ms=50.0,
            wm_utilization=0.6, cognitive_load="healthy",
            workload_trend="stable"
        ),
        ReflectionMetrics(
            project_id=1, timestamp=datetime.now() - timedelta(days=7),
            accuracy=0.95, false_positive_rate=0.02,
            gap_count=5, contradiction_count=0,
            memory_size_bytes=1000000, query_latency_ms=40.0,
            wm_utilization=0.5, cognitive_load="healthy",
            workload_trend="stable"
        ),
    ]

    result = TrendAnalyzer.detect_quality_degradation(metrics)
    assert result is not None
    assert "Accuracy degraded" in result


def test_trend_analyzer_no_degradation():
    """Test when quality is stable."""
    metrics = [
        ReflectionMetrics(
            project_id=1, timestamp=datetime.now(),
            accuracy=0.95, false_positive_rate=0.02,
            gap_count=5, contradiction_count=0,
            memory_size_bytes=1000000, query_latency_ms=45.0,
            wm_utilization=0.6, cognitive_load="healthy",
            workload_trend="stable"
        ),
    ]

    result = TrendAnalyzer.detect_quality_degradation(metrics)
    assert result is None


def test_trend_analyzer_gap_expansion():
    """Test gap expansion detection."""
    metrics = [
        ReflectionMetrics(
            project_id=1, timestamp=datetime.now(),
            accuracy=0.95, false_positive_rate=0.02,
            gap_count=10, contradiction_count=0,
            memory_size_bytes=1000000, query_latency_ms=45.0,
            wm_utilization=0.6, cognitive_load="healthy",
            workload_trend="stable"
        ),
        ReflectionMetrics(
            project_id=1, timestamp=datetime.now() - timedelta(days=7),
            accuracy=0.95, false_positive_rate=0.02,
            gap_count=5, contradiction_count=0,
            memory_size_bytes=1000000, query_latency_ms=40.0,
            wm_utilization=0.5, cognitive_load="healthy",
            workload_trend="stable"
        ),
    ]

    result = TrendAnalyzer.detect_gap_expansion(metrics)
    assert result is not None
    assert "gaps expanded" in result.lower()


def test_trend_analyzer_load_trend():
    """Test cognitive load trend detection."""
    metrics = [
        ReflectionMetrics(
            project_id=1, timestamp=datetime.now(),
            accuracy=0.95, false_positive_rate=0.02,
            gap_count=5, contradiction_count=0,
            memory_size_bytes=1000000, query_latency_ms=45.0,
            wm_utilization=0.9, cognitive_load="overloaded",
            workload_trend="stable"
        ),
    ]

    result = TrendAnalyzer.detect_load_trend(metrics)
    assert result is not None
    assert "overloaded" in result.lower()


def test_trend_analyzer_workload_trend_growing():
    """Test workload trend detection (growing)."""
    # Create 6 data points: recent 3 should avg to 60, older 3 should avg to 30
    metrics = [
        ReflectionMetrics(
            project_id=1, timestamp=datetime.now(),
            accuracy=0.95, false_positive_rate=0.02,
            gap_count=5, contradiction_count=0,
            memory_size_bytes=1000000, query_latency_ms=70.0,
            wm_utilization=0.6, cognitive_load="healthy",
            workload_trend="stable"
        ),
        ReflectionMetrics(
            project_id=1, timestamp=datetime.now() - timedelta(days=1),
            accuracy=0.95, false_positive_rate=0.02,
            gap_count=5, contradiction_count=0,
            memory_size_bytes=1000000, query_latency_ms=60.0,
            wm_utilization=0.5, cognitive_load="healthy",
            workload_trend="stable"
        ),
        ReflectionMetrics(
            project_id=1, timestamp=datetime.now() - timedelta(days=2),
            accuracy=0.95, false_positive_rate=0.02,
            gap_count=5, contradiction_count=0,
            memory_size_bytes=1000000, query_latency_ms=50.0,
            wm_utilization=0.5, cognitive_load="healthy",
            workload_trend="stable"
        ),
        ReflectionMetrics(
            project_id=1, timestamp=datetime.now() - timedelta(days=3),
            accuracy=0.95, false_positive_rate=0.02,
            gap_count=5, contradiction_count=0,
            memory_size_bytes=1000000, query_latency_ms=30.0,
            wm_utilization=0.4, cognitive_load="healthy",
            workload_trend="stable"
        ),
        ReflectionMetrics(
            project_id=1, timestamp=datetime.now() - timedelta(days=4),
            accuracy=0.95, false_positive_rate=0.02,
            gap_count=5, contradiction_count=0,
            memory_size_bytes=1000000, query_latency_ms=25.0,
            wm_utilization=0.4, cognitive_load="healthy",
            workload_trend="stable"
        ),
        ReflectionMetrics(
            project_id=1, timestamp=datetime.now() - timedelta(days=5),
            accuracy=0.95, false_positive_rate=0.02,
            gap_count=5, contradiction_count=0,
            memory_size_bytes=1000000, query_latency_ms=20.0,
            wm_utilization=0.3, cognitive_load="healthy",
            workload_trend="stable"
        ),
    ]

    result = TrendAnalyzer.calculate_workload_trend(metrics)
    assert result == "growing"


def test_reflection_cycle_structure(mcp_server, project):
    """Test reflection cycle returns proper structure."""
    # Would require integration with all monitors
    # This is a structural test
    assert hasattr(mcp_server, 'quality_monitor')
    assert hasattr(mcp_server, 'gap_detector')
    assert hasattr(mcp_server, 'load_monitor')
