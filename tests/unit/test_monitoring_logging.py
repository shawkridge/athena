"""Unit tests for monitoring and logging infrastructure."""

import pytest
import json
import tempfile
from pathlib import Path
import logging

from athena.monitoring.logging import (
    setup_logging,
    JSONFormatter,
    LogContext,
    get_logger,
    log_operation,
)
from athena.monitoring.metrics import (
    MetricsCollector,
    Counter,
    Gauge,
    Histogram,
    get_collector,
)
from athena.monitoring.health import (
    HealthChecker,
    HealthStatus,
    HealthReport,
)


class TestJSONFormatter:
    """Test JSON log formatting."""

    def test_formats_log_as_json(self):
        """Log records should be formatted as JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert data["logger"] == "test"
        assert "timestamp" in data

    def test_includes_context_in_json(self):
        """Context should be included in JSON output."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.context = {"project_id": 1, "user": "test"}

        output = formatter.format(record)
        data = json.loads(output)

        assert data["context"]["project_id"] == 1

    def test_includes_duration_in_json(self):
        """Duration should be included in JSON output."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.duration_ms = 123.45

        output = formatter.format(record)
        data = json.loads(output)

        assert data["duration_ms"] == 123.45


class TestLoggingSetup:
    """Test logging setup."""

    def test_setup_logging_creates_logger(self):
        """setup_logging should create a logger."""
        logger = setup_logging("test")
        assert logger is not None
        assert logger.name == "test"

    def test_setup_logging_with_file(self):
        """setup_logging should create file handler if log_file specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            logger = setup_logging("test", log_file=log_file)

            logger.info("Test message")

            assert log_file.exists()
            with open(log_file) as f:
                content = f.read()
                assert "Test message" in content

    def test_get_logger_returns_same_instance(self):
        """get_logger should return the same logger instance."""
        logger1 = get_logger("test")
        logger2 = get_logger("test")

        assert logger1 is logger2


class TestMetricsCollector:
    """Test metrics collection."""

    def test_record_query(self):
        """Collector should record query metrics."""
        collector = MetricsCollector()
        collector.record_query("semantic", 100.0, success=True)

        assert collector.metrics["query_count"] == 1
        assert 100.0 in collector.metrics["query_latency_ms"]

    def test_record_consolidation(self):
        """Collector should record consolidation metrics."""
        collector = MetricsCollector()
        collector.record_consolidation(500.0, 100, 5, success=True)

        assert collector.metrics["consolidation_count"] == 1
        assert collector.metrics["events_consolidated"] == 100
        assert collector.metrics["patterns_extracted"] == 5

    def test_record_cache(self):
        """Collector should record cache metrics."""
        collector = MetricsCollector()
        collector.record_cache_hit()
        collector.record_cache_miss()

        assert collector.metrics["cache_hits"] == 1
        assert collector.metrics["cache_misses"] == 1

    def test_record_error(self):
        """Collector should record error metrics."""
        collector = MetricsCollector()
        collector.record_error("ValueError")
        collector.record_error("ValueError")
        collector.record_error("KeyError")

        assert collector.metrics["errors_by_type"]["ValueError"] == 2
        assert collector.metrics["errors_by_type"]["KeyError"] == 1

    def test_get_stats(self):
        """Collector should provide statistics."""
        collector = MetricsCollector()
        collector.record_query("semantic", 100.0, success=True)
        collector.record_query("semantic", 200.0, success=True)

        stats = collector.get_stats()

        assert stats["query"]["count"] == 2
        assert "latency_ms" in stats["query"]
        assert stats["query"]["latency_ms"]["mean"] == 150.0

    def test_reset(self):
        """Collector should reset metrics."""
        collector = MetricsCollector()
        collector.record_query("semantic", 100.0)

        collector.reset()

        assert collector.metrics["query_count"] == 0


class TestMetricClasses:
    """Test Prometheus-like metric classes."""

    def test_counter(self):
        """Counter should increment values."""
        counter = Counter("test", "Test counter")
        counter.inc()
        counter.inc(5)

        assert counter.get() == 6

    def test_gauge(self):
        """Gauge should set and modify values."""
        gauge = Gauge("test", "Test gauge")
        gauge.set(100)
        assert gauge.get() == 100

        gauge.inc(10)
        assert gauge.get() == 110

        gauge.dec(20)
        assert gauge.get() == 90

    def test_histogram(self):
        """Histogram should track observations."""
        hist = Histogram("test", "Test histogram")
        hist.observe(10)
        hist.observe(20)
        hist.observe(30)

        stats = hist.get_stats()
        assert stats["count"] == 3
        assert stats["mean"] == 20


class TestHealthChecker:
    """Test health checking."""

    def test_health_report(self):
        """HealthReport should store check results."""
        report = HealthReport("test", HealthStatus.HEALTHY, "OK")

        assert report.name == "test"
        assert report.status == HealthStatus.HEALTHY
        assert report.message == "OK"

    def test_register_check(self):
        """Checker should register checks."""
        checker = HealthChecker()

        def check():
            return {"status": HealthStatus.HEALTHY, "message": "OK"}

        checker.register_check("test", check)
        assert "test" in checker.checks

    def test_perform_check(self):
        """Checker should perform checks."""
        checker = HealthChecker()

        def check():
            return {"status": HealthStatus.HEALTHY, "message": "OK"}

        checker.register_check("test", check)
        report = checker.perform_check("test")

        assert report.status == HealthStatus.HEALTHY
        assert report.message == "OK"

    def test_perform_all_checks(self):
        """Checker should perform all checks."""
        checker = HealthChecker()

        def check1():
            return {"status": HealthStatus.HEALTHY, "message": "OK"}

        def check2():
            return {"status": HealthStatus.HEALTHY, "message": "OK"}

        checker.register_check("check1", check1)
        checker.register_check("check2", check2)

        results = checker.perform_all_checks()

        assert len(results) == 2
        assert all(r.status == HealthStatus.HEALTHY for r in results.values())

    def test_overall_status_healthy(self):
        """Overall status should be healthy when all checks pass."""
        checker = HealthChecker()

        def check():
            return {"status": HealthStatus.HEALTHY, "message": "OK"}

        checker.register_check("test", check)
        status = checker.get_overall_status()

        assert status == HealthStatus.HEALTHY

    def test_overall_status_degraded(self):
        """Overall status should be degraded when any check is degraded."""
        checker = HealthChecker()

        def check1():
            return {"status": HealthStatus.HEALTHY, "message": "OK"}

        def check2():
            return {"status": HealthStatus.DEGRADED, "message": "Slow"}

        checker.register_check("check1", check1)
        checker.register_check("check2", check2)

        status = checker.get_overall_status()

        assert status == HealthStatus.DEGRADED

    def test_overall_status_unhealthy(self):
        """Overall status should be unhealthy when any check fails."""
        checker = HealthChecker()

        def check():
            return {"status": HealthStatus.UNHEALTHY, "message": "Failed"}

        checker.register_check("test", check)
        status = checker.get_overall_status()

        assert status == HealthStatus.UNHEALTHY

    def test_get_report(self):
        """Checker should provide comprehensive report."""
        checker = HealthChecker()

        def check():
            return {"status": HealthStatus.HEALTHY, "message": "OK"}

        checker.register_check("test", check)
        report = checker.get_report()

        assert "timestamp" in report
        assert "overall_status" in report
        assert "checks" in report
        assert report["checks"]["test"]["status"] == "healthy"
