"""
Tests for performance monitoring API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone


@pytest.fixture
def performance_client():
    """Fixture for API test client."""
    from athena_dashboard.backend.app import app
    return TestClient(app)


class TestPerformanceMetrics:
    """Tests for /api/performance/metrics endpoint."""

    def test_get_performance_metrics_default(self, performance_client):
        """Test getting performance metrics with default parameters."""
        response = performance_client.get('/api/performance/metrics')
        assert response.status_code == 200

        data = response.json()
        assert 'current' in data
        assert 'trends' in data
        assert 'health' in data
        assert 'alerts' in data
        assert 'topQueries' in data

    def test_get_performance_metrics_current_metrics(self, performance_client):
        """Test current metrics structure."""
        response = performance_client.get('/api/performance/metrics')
        assert response.status_code == 200

        current = response.json()['current']
        assert 'cpuUsage' in current
        assert 'memoryUsage' in current
        assert 'memoryAvailable' in current
        assert 'queryLatency' in current
        assert 'apiResponseTime' in current
        assert 'activeConnections' in current
        assert 'diskUsage' in current

        # Verify metrics are in reasonable ranges
        assert 0 <= current['cpuUsage'] <= 100
        assert 0 <= current['memoryUsage'] <= 100
        assert 0 <= current['diskUsage'] <= 100
        assert current['queryLatency'] > 0
        assert current['apiResponseTime'] > 0

    def test_get_performance_metrics_health(self, performance_client):
        """Test health status structure."""
        response = performance_client.get('/api/performance/metrics')
        assert response.status_code == 200

        health = response.json()['health']
        assert 'status' in health
        assert 'score' in health
        assert 'components' in health

        assert health['status'] in ['healthy', 'warning', 'critical']
        assert 0 <= health['score'] <= 1

        components = health['components']
        assert 'cpu' in components
        assert 'memory' in components
        assert 'database' in components
        assert 'api' in components

    def test_get_performance_metrics_time_range_1h(self, performance_client):
        """Test performance metrics with 1 hour range."""
        response = performance_client.get('/api/performance/metrics?range=1h')
        assert response.status_code == 200

        trends = response.json()['trends']
        assert len(trends) <= 1  # At most 1 data point for 1h range

    def test_get_performance_metrics_time_range_6h(self, performance_client):
        """Test performance metrics with 6 hour range."""
        response = performance_client.get('/api/performance/metrics?range=6h')
        assert response.status_code == 200

        trends = response.json()['trends']
        assert len(trends) <= 6

    def test_get_performance_metrics_time_range_24h(self, performance_client):
        """Test performance metrics with 24 hour range."""
        response = performance_client.get('/api/performance/metrics?range=24h')
        assert response.status_code == 200

        trends = response.json()['trends']
        assert len(trends) <= 24

    def test_get_performance_metrics_invalid_range(self, performance_client):
        """Test performance metrics with invalid range."""
        response = performance_client.get('/api/performance/metrics?range=invalid')
        # Should default to 6h
        assert response.status_code == 200

    def test_get_performance_metrics_trends(self, performance_client):
        """Test trends data structure."""
        response = performance_client.get('/api/performance/metrics')
        assert response.status_code == 200

        trends = response.json()['trends']
        assert len(trends) > 0

        for trend in trends:
            assert 'timestamp' in trend
            assert 'cpuUsage' in trend
            assert 'memoryUsage' in trend
            assert 'queryLatency' in trend
            assert 'apiResponseTime' in trend

    def test_get_performance_metrics_top_queries(self, performance_client):
        """Test top slow queries structure."""
        response = performance_client.get('/api/performance/metrics')
        assert response.status_code == 200

        queries = response.json()['topQueries']

        for query in queries:
            assert 'name' in query
            assert 'avgLatency' in query
            assert 'count' in query


class TestCPUHistory:
    """Tests for /api/performance/cpu-history endpoint."""

    def test_get_cpu_history_default(self, performance_client):
        """Test getting CPU history with default parameters."""
        response = performance_client.get('/api/performance/cpu-history')
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_cpu_history_1h(self, performance_client):
        """Test CPU history for 1 hour."""
        response = performance_client.get('/api/performance/cpu-history?range=1h')
        assert response.status_code == 200

        data = response.json()
        assert len(data) <= 1

    def test_get_cpu_history_data_structure(self, performance_client):
        """Test CPU history data structure."""
        response = performance_client.get('/api/performance/cpu-history')
        assert response.status_code == 200

        data = response.json()
        for point in data:
            assert 'timestamp' in point
            assert 'usage' in point
            assert 0 <= point['usage'] <= 100


class TestMemoryHistory:
    """Tests for /api/performance/memory-history endpoint."""

    def test_get_memory_history_default(self, performance_client):
        """Test getting memory history with default parameters."""
        response = performance_client.get('/api/performance/memory-history')
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_memory_history_24h(self, performance_client):
        """Test memory history for 24 hours."""
        response = performance_client.get('/api/performance/memory-history?range=24h')
        assert response.status_code == 200

        data = response.json()
        assert len(data) <= 24

    def test_get_memory_history_data_structure(self, performance_client):
        """Test memory history data structure."""
        response = performance_client.get('/api/performance/memory-history')
        assert response.status_code == 200

        data = response.json()
        for point in data:
            assert 'timestamp' in point
            assert 'usage' in point
            assert 0 <= point['usage'] <= 100


class TestLatencyHistory:
    """Tests for /api/performance/latency-history endpoint."""

    def test_get_latency_history_default(self, performance_client):
        """Test getting latency history with default parameters."""
        response = performance_client.get('/api/performance/latency-history')
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_latency_history_6h(self, performance_client):
        """Test latency history for 6 hours."""
        response = performance_client.get('/api/performance/latency-history?range=6h')
        assert response.status_code == 200

        data = response.json()
        assert len(data) <= 6

    def test_get_latency_history_data_structure(self, performance_client):
        """Test latency history data structure."""
        response = performance_client.get('/api/performance/latency-history')
        assert response.status_code == 200

        data = response.json()
        for point in data:
            assert 'timestamp' in point
            assert 'latency' in point
            assert point['latency'] > 0


class TestSlowQueries:
    """Tests for /api/performance/slow-queries endpoint."""

    def test_get_slow_queries_default(self, performance_client):
        """Test getting slow queries with default parameters."""
        response = performance_client.get('/api/performance/slow-queries')
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    def test_get_slow_queries_limit(self, performance_client):
        """Test slow queries with custom limit."""
        response = performance_client.get('/api/performance/slow-queries?limit=5')
        assert response.status_code == 200

        data = response.json()
        assert len(data) <= 5

    def test_get_slow_queries_data_structure(self, performance_client):
        """Test slow queries data structure."""
        response = performance_client.get('/api/performance/slow-queries')
        assert response.status_code == 200

        data = response.json()
        for query in data:
            assert 'name' in query
            assert 'avgLatency' in query
            assert 'count' in query


class TestPerformanceIntegration:
    """Integration tests for performance monitoring."""

    def test_performance_metrics_consistency(self, performance_client):
        """Test consistency across performance metric endpoints."""
        # Get main metrics
        main_response = performance_client.get('/api/performance/metrics')
        main_data = main_response.json()

        # Get individual history endpoints
        cpu_response = performance_client.get('/api/performance/cpu-history?range=6h')
        memory_response = performance_client.get('/api/performance/memory-history?range=6h')
        latency_response = performance_client.get('/api/performance/latency-history?range=6h')

        assert main_response.status_code == 200
        assert cpu_response.status_code == 200
        assert memory_response.status_code == 200
        assert latency_response.status_code == 200

        # Verify trend data matches main metrics structure
        main_trends = main_data['trends']
        if main_trends:
            assert 'cpuUsage' in main_trends[0]
            assert 'memoryUsage' in main_trends[0]
            assert 'queryLatency' in main_trends[0]

    def test_performance_health_calculation(self, performance_client):
        """Test health score calculation is reasonable."""
        response = performance_client.get('/api/performance/metrics')
        assert response.status_code == 200

        health = response.json()['health']

        # Health score should be between 0 and 1
        assert 0 <= health['score'] <= 1

        # Status should match score
        if health['score'] > 0.7:
            assert health['status'] == 'healthy'
        elif health['score'] > 0.5:
            assert health['status'] == 'warning'
        else:
            assert health['status'] == 'critical'

    def test_performance_alerts_structure(self, performance_client):
        """Test alerts have proper structure."""
        response = performance_client.get('/api/performance/metrics')
        assert response.status_code == 200

        alerts = response.json()['alerts']

        for alert in alerts:
            assert 'id' in alert
            assert 'level' in alert
            assert 'message' in alert
            assert 'timestamp' in alert
            assert alert['level'] in ['info', 'warning', 'critical']
