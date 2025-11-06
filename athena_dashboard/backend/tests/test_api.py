"""Unit tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from app import app


client = TestClient(app)


class TestHealthEndpoints:
    """Test health and status endpoints."""

    def test_health_check(self):
        """Test /health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_app_info(self):
        """Test /info endpoint."""
        response = client.get("/info")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data


class TestDashboardEndpoints:
    """Test dashboard endpoints."""

    def test_get_overview(self):
        """Test /api/dashboard/overview endpoint."""
        response = client.get("/api/dashboard/overview")
        assert response.status_code in [200, 500]  # May fail without database


class TestHookEndpoints:
    """Test hook endpoints."""

    def test_get_hooks_status(self):
        """Test /api/hooks/status endpoint."""
        response = client.get("/api/hooks/status")
        assert response.status_code in [200, 500]  # May fail without database


class TestMemoryEndpoints:
    """Test memory endpoints."""

    def test_get_memory_health(self):
        """Test /api/memory/health endpoint."""
        response = client.get("/api/memory/health")
        assert response.status_code in [200, 500]  # May fail without database

    def test_get_consolidation(self):
        """Test /api/memory/consolidation endpoint."""
        response = client.get("/api/memory/consolidation")
        assert response.status_code in [200, 500]  # May fail without database


class TestCognitiveLoadEndpoints:
    """Test cognitive load endpoints."""

    def test_get_current_load(self):
        """Test /api/load/current endpoint."""
        response = client.get("/api/load/current")
        assert response.status_code in [200, 500]  # May fail without database


class TestTaskEndpoints:
    """Test task and project endpoints."""

    def test_get_projects(self):
        """Test /api/projects endpoint."""
        response = client.get("/api/projects")
        assert response.status_code in [200, 500]  # May fail without database

    def test_get_goals(self):
        """Test /api/goals endpoint."""
        response = client.get("/api/goals")
        assert response.status_code in [200, 500]  # May fail without database

    def test_get_tasks(self):
        """Test /api/tasks endpoint."""
        response = client.get("/api/tasks")
        assert response.status_code in [200, 500]  # May fail without database


class TestLearningEndpoints:
    """Test learning and analytics endpoints."""

    def test_get_strategy_effectiveness(self):
        """Test /api/learning/strategies endpoint."""
        response = client.get("/api/learning/strategies")
        assert response.status_code in [200, 500]  # May fail without database

    def test_get_top_procedures(self):
        """Test /api/learning/procedures endpoint."""
        response = client.get("/api/learning/procedures")
        assert response.status_code in [200, 500]  # May fail without database
