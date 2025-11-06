"""Tests for Athena HTTP client."""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import httpx

from athena.client.http_client import (
    AthenaHTTPClient,
    AthenaHTTPAsyncClient,
    AthenaHTTPClientError,
    AthenaHTTPClientConnectionError,
    AthenaHTTPClientTimeoutError,
    AthenaHTTPClientOperationError,
)


class TestAthenaHTTPClient:
    """Tests for synchronous HTTP client."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return AthenaHTTPClient(url="http://localhost:3000", retries=1)

    def test_client_initialization(self, client):
        """Test client initialization."""
        assert client.url == "http://localhost:3000"
        assert client.timeout == 30.0
        assert client.retries == 1

    def test_context_manager(self):
        """Test context manager functionality."""
        with AthenaHTTPClient() as client:
            assert client is not None
        # Should not raise

    def test_close(self, client):
        """Test client close."""
        client.close()
        # Should not raise

    @patch("athena.client.http_client.httpx.Client.post")
    def test_recall_success(self, mock_post, client):
        """Test successful recall operation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "data": [{"id": 1, "content": "test memory"}],
            "execution_time_ms": 45.2,
        }
        mock_post.return_value = mock_response

        result = client.recall(query="test", k=5)

        assert result == [{"id": 1, "content": "test memory"}]
        mock_post.assert_called_once()

    @patch("athena.client.http_client.httpx.Client.post")
    def test_remember_success(self, mock_post, client):
        """Test successful remember operation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "data": {"memory_id": 123},
            "execution_time_ms": 12.5,
        }
        mock_post.return_value = mock_response

        result = client.remember(content="test", memory_type="fact")

        assert result == {"memory_id": 123}
        mock_post.assert_called_once()

    @patch("athena.client.http_client.httpx.Client.post")
    def test_forget_success(self, mock_post, client):
        """Test successful forget operation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "data": {"deleted": True},
            "execution_time_ms": 8.3,
        }
        mock_post.return_value = mock_response

        result = client.forget(memory_id=123)

        assert result == {"deleted": True}

    @patch("athena.client.http_client.httpx.Client.post")
    def test_consolidate_success(self, mock_post, client):
        """Test successful consolidation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "data": {"patterns_extracted": 5, "compression_ratio": 0.75},
            "execution_time_ms": 2500.0,
        }
        mock_post.return_value = mock_response

        result = client.run_consolidation(strategy="balanced")

        assert result["patterns_extracted"] == 5
        assert result["compression_ratio"] == 0.75

    @patch("athena.client.http_client.httpx.Client.post")
    def test_operation_failure(self, mock_post, client):
        """Test operation failure response."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": False,
            "error": "Operation failed",
        }
        mock_post.return_value = mock_response

        with pytest.raises(AthenaHTTPClientOperationError):
            client.recall(query="test")

    @patch("athena.client.http_client.httpx.Client.post")
    def test_connection_error_with_retry(self, mock_post, client):
        """Test connection error with retry."""
        mock_post.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(AthenaHTTPClientConnectionError):
            client.recall(query="test")

    @patch("athena.client.http_client.httpx.Client.post")
    def test_timeout_error_with_retry(self, mock_post, client):
        """Test timeout error with retry."""
        mock_post.side_effect = httpx.TimeoutException("Request timed out")

        with pytest.raises(AthenaHTTPClientTimeoutError):
            client.recall(query="test")

    @patch("athena.client.http_client.httpx.Client.get")
    def test_health_check_success(self, mock_get, client):
        """Test health check."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "healthy",
            "version": "1.0.0",
            "uptime_seconds": 3600,
        }
        mock_get.return_value = mock_response

        result = client.health()

        assert result["status"] == "healthy"
        assert result["version"] == "1.0.0"

    @patch("athena.client.http_client.httpx.Client.get")
    def test_health_check_failure(self, mock_get, client):
        """Test health check failure."""
        mock_get.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(AthenaHTTPClientConnectionError):
            client.health()

    @patch("athena.client.http_client.httpx.Client.post")
    def test_create_task(self, mock_post, client):
        """Test task creation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "data": {"task_id": 1, "content": "test task"},
            "execution_time_ms": 15.2,
        }
        mock_post.return_value = mock_response

        result = client.create_task(content="test task", priority="high")

        assert result["task_id"] == 1

    @patch("athena.client.http_client.httpx.Client.post")
    def test_set_goal(self, mock_post, client):
        """Test goal setting."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "data": {"goal_id": 2, "content": "test goal"},
            "execution_time_ms": 12.5,
        }
        mock_post.return_value = mock_response

        result = client.set_goal(content="test goal", priority="high")

        assert result["goal_id"] == 2

    @patch("athena.client.http_client.httpx.Client.post")
    def test_search_graph(self, mock_post, client):
        """Test graph search."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "data": [{"name": "entity1", "type": "concept"}],
            "execution_time_ms": 25.3,
        }
        mock_post.return_value = mock_response

        result = client.search_graph(query="test", max_results=10)

        assert len(result) == 1
        assert result[0]["name"] == "entity1"

    @patch("athena.client.http_client.httpx.Client.post")
    def test_record_event(self, mock_post, client):
        """Test event recording."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "data": {"event_id": 42},
            "execution_time_ms": 8.2,
        }
        mock_post.return_value = mock_response

        result = client.record_event(
            content="test event",
            event_type="action",
            outcome="success"
        )

        assert result["event_id"] == 42

    @patch("athena.client.http_client.httpx.Client.post")
    def test_decompose_task(self, mock_post, client):
        """Test task decomposition."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "steps": [
                    {"step": 1, "description": "analyze"},
                    {"step": 2, "description": "design"},
                ]
            },
            "execution_time_ms": 150.0,
        }
        mock_post.return_value = mock_response

        result = client.decompose_with_strategy(
            task_description="complex task",
            strategy="hierarchical"
        )

        assert len(result["steps"]) == 2


class TestAthenaHTTPAsyncClient:
    """Tests for asynchronous HTTP client."""

    @pytest.mark.asyncio
    async def test_async_client_initialization(self):
        """Test async client initialization."""
        client = AthenaHTTPAsyncClient(url="http://localhost:3000", retries=1)
        assert client.url == "http://localhost:3000"
        assert client.timeout == 30.0
        assert client.retries == 1
        await client.close()

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager."""
        async with AthenaHTTPAsyncClient() as client:
            assert client is not None

    @pytest.mark.asyncio
    async def test_async_recall(self):
        """Test async recall operation."""
        client = AthenaHTTPAsyncClient(url="http://localhost:3000", retries=1)

        # Create a proper mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "data": [{"id": 1, "content": "test memory"}],
            "execution_time_ms": 45.2,
        }
        mock_response.raise_for_status = Mock()

        # Mock the _client
        client._client = AsyncMock()
        client._client.post = AsyncMock(return_value=mock_response)

        result = await client.recall(query="test", k=5)

        assert result == [{"id": 1, "content": "test memory"}]
        await client.close()

    @pytest.mark.asyncio
    async def test_async_remember(self):
        """Test async remember operation."""
        client = AthenaHTTPAsyncClient(url="http://localhost:3000", retries=1)

        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "data": {"memory_id": 123},
            "execution_time_ms": 12.5,
        }
        mock_response.raise_for_status = Mock()

        client._client = AsyncMock()
        client._client.post = AsyncMock(return_value=mock_response)

        result = await client.remember(content="test", memory_type="fact")

        assert result == {"memory_id": 123}
        await client.close()


class TestClientErrorHandling:
    """Tests for error handling."""

    def test_client_error_hierarchy(self):
        """Test error class hierarchy."""
        assert issubclass(AthenaHTTPClientConnectionError, AthenaHTTPClientError)
        assert issubclass(AthenaHTTPClientTimeoutError, AthenaHTTPClientError)
        assert issubclass(AthenaHTTPClientOperationError, AthenaHTTPClientError)

    def test_error_messages(self):
        """Test error messages are descriptive."""
        error = AthenaHTTPClientConnectionError("test error")
        assert str(error) == "test error"

        error = AthenaHTTPClientTimeoutError("timeout")
        assert "timeout" in str(error).lower()


class TestClientIntegration:
    """Integration tests (require running HTTP service)."""

    @pytest.mark.integration
    def test_real_health_check(self):
        """Test real health check (requires running service)."""
        try:
            client = AthenaHTTPClient(url="http://localhost:3000", timeout=2.0, retries=1)
            health = client.health()
            assert "status" in health
            client.close()
        except AthenaHTTPClientConnectionError:
            pytest.skip("Athena HTTP service not running")

    @pytest.mark.integration
    def test_real_info_check(self):
        """Test real info check (requires running service)."""
        try:
            client = AthenaHTTPClient(url="http://localhost:3000", timeout=2.0, retries=1)
            info = client.info()
            assert "name" in info
            assert "version" in info
            client.close()
        except AthenaHTTPClientConnectionError:
            pytest.skip("Athena HTTP service not running")
