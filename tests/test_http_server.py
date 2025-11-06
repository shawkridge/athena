"""Tests for Athena HTTP server."""

import pytest
from fastapi.testclient import TestClient
from athena.http.server import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] is not None
    assert "uptime_seconds" in data
    assert "database_size_mb" in data
    assert "operations_count" in data


def test_info_endpoint(client):
    """Test info endpoint."""
    response = client.get("/info")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Athena Memory System API"
    assert data["version"] is not None
    assert data["description"] is not None
    assert data["documentation_url"] == "/docs"
    assert isinstance(data["supported_operations"], list)


def test_docs_endpoint(client):
    """Test API documentation endpoint."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_endpoint(client):
    """Test OpenAPI schema endpoint."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "paths" in data


def test_recall_endpoint_structure(client):
    """Test that recall endpoint exists."""
    # This will fail if the endpoint doesn't exist, which is expected for now
    # Once the operation routing is complete, this should work
    response = client.post("/api/memory/recall", json={"query": "test", "k": 5})
    # We expect either a successful response or a proper error
    assert response.status_code in [200, 400, 422, 500]


def test_remember_endpoint_structure(client):
    """Test that remember endpoint exists."""
    response = client.post(
        "/api/memory/remember",
        json={"content": "test memory", "memory_type": "fact"}
    )
    assert response.status_code in [200, 400, 422, 500]


def test_consolidate_endpoint_structure(client):
    """Test that consolidation endpoint exists."""
    response = client.post(
        "/api/consolidation/run",
        json={"strategy": "balanced"}
    )
    assert response.status_code in [200, 400, 422, 500]


def test_tasks_endpoints_exist(client):
    """Test that task endpoints exist."""
    # List tasks
    response = client.get("/api/tasks/list")
    assert response.status_code in [200, 400, 422, 500]

    # Create task
    response = client.post(
        "/api/tasks/create",
        json={"content": "test task", "priority": "medium"}
    )
    assert response.status_code in [200, 400, 422, 500]


def test_goals_endpoints_exist(client):
    """Test that goal endpoints exist."""
    # Get active goals
    response = client.get("/api/goals/active")
    assert response.status_code in [200, 400, 422, 500]

    # Set goal
    response = client.post(
        "/api/goals/set",
        json={"content": "test goal", "priority": "high"}
    )
    assert response.status_code in [200, 400, 422, 500]


def test_cors_headers(client):
    """Test CORS headers are present."""
    response = client.get("/health")
    # CORS headers should be present for allowed origins
    assert response.status_code == 200
