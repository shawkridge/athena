"""Pytest configuration and shared fixtures for MCP integration tests.

Provides:
- Database fixtures with proper isolation
- MCP server initialization
- Project management
- Mock embeddings and LLM responses
- Test data generators
"""

import pytest
import tempfile
import numpy as np
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

# Suppress warnings in tests
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Create mock EmbeddingModel BEFORE any imports that use it
class MockEmbeddingModel:
    def __init__(self, model=None, provider=None):
        self.model = model or "mock"
        self.provider = "mock"
        self.backend = None
        self.embedding_dim = 768
        self.available = True

    def embed(self, text: str):
        """Return deterministic embedding based on text."""
        seed = hash(text) % (2**32)
        np.random.seed(seed)
        return np.random.randn(768).tolist()

    def embed_batch(self, texts):
        """Batch embedding."""
        return [self.embed(text) for text in texts]


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        from src.athena.core.database import Database
        db = Database(str(db_path))
        yield db
        # Cleanup handled by tempfile context manager


@pytest.fixture(autouse=False)
def mcp_server(temp_db, monkeypatch):
    """Create MCP server instance with test database and mocked embeddings."""
    db_path = str(temp_db.db_path)

    # Patch the EmbeddingModel before importing anything that uses it
    from src.athena.core import embeddings
    from src.athena.memory import store as memory_store_module

    monkeypatch.setattr(embeddings, 'EmbeddingModel', MockEmbeddingModel)
    monkeypatch.setattr(memory_store_module, 'EmbeddingModel', MockEmbeddingModel)

    # Re-import to pick up the mocked class
    import importlib
    importlib.reload(memory_store_module)

    # Now import and create the server
    from src.athena.mcp.handlers import MemoryMCPServer

    server = MemoryMCPServer(db_path=db_path, enable_advanced_rag=False)

    yield server


@pytest.fixture
def project_id(temp_db):
    """Create a test project."""
    from src.athena.memory import MemoryStore
    from src.athena.projects import ProjectManager

    memory_store = MemoryStore(str(temp_db.db_path))
    pm = ProjectManager(memory_store)
    project = pm.get_or_create_project("test_project")
    return str(project.id)


# ============================================================================
# Mock Fixtures for External Services
# ============================================================================

@pytest.fixture
def mock_embeddings():
    """Mock embedding generator."""
    def generate_embedding(text: str, dim: int = 768) -> list:
        """Generate deterministic embedding for testing."""
        # Create deterministic embedding based on text hash
        seed = hash(text) % (2**32)
        np.random.seed(seed)
        return np.random.randn(dim).tolist()

    return generate_embedding


@pytest.fixture
def mock_llm_response():
    """Mock LLM responses for consolidation and RAG."""
    responses = {
        'consolidate': {
            'patterns': [
                {'pattern': 'Always validate input', 'confidence': 0.95},
                {'pattern': 'Use async/await', 'confidence': 0.87},
            ],
            'summary': 'Key patterns extracted from events'
        },
        'validate': {
            'is_valid': True,
            'confidence': 0.92,
            'reasoning': 'Pattern matches observed behavior'
        },
        'rag': {
            'response': 'Relevant information retrieved',
            'sources': [1, 2, 3],
            'confidence': 0.88
        }
    }

    async def mock_llm(prompt: str, **kwargs):
        # Simple routing based on prompt content
        if 'consolidate' in prompt.lower():
            return responses['consolidate']
        elif 'valid' in prompt.lower():
            return responses['validate']
        else:
            return responses['rag']

    return mock_llm


# ============================================================================
# Autouse Fixtures (Applied to All Tests)
# ============================================================================

@pytest.fixture(autouse=True)
def patch_embedding_backend(monkeypatch, mock_embeddings):
    """Automatically patch embedding backend for all tests."""
    from src.athena.core import embeddings

    # Create mock embedding model
    mock_model = Mock()
    mock_model.embed = Mock(side_effect=lambda text: mock_embeddings(text))
    mock_model.embed_batch = Mock(side_effect=lambda texts: [
        mock_embeddings(t) for t in texts
    ])

    # Patch the embedding model initialization
    monkeypatch.setattr(
        'src.athena.core.embeddings.EmbeddingModel',
        lambda *args, **kwargs: mock_model
    )

    # Also patch get_embedding_model function if it exists
    try:
        monkeypatch.setattr(
            'src.athena.core.embeddings.get_embedding_model',
            lambda *args, **kwargs: mock_model
        )
    except AttributeError:
        pass

    yield


@pytest.fixture(autouse=True)
def patch_llm_backend(monkeypatch, mock_llm_response):
    """Automatically patch LLM backend for all tests."""
    # Create a mock LLM client
    mock_client = Mock()
    mock_client.chat = AsyncMock(return_value={"response": "Mock response"})
    mock_client.query = AsyncMock(return_value="Mock response")

    # Try to patch various potential LLM client locations
    try:
        from src.athena.rag import llm_client
        monkeypatch.setattr(llm_client, 'OllamaLLMClient', lambda *args, **kwargs: mock_client)
    except (ImportError, AttributeError):
        pass

    try:
        from src.athena.rag import llm_client
        monkeypatch.setattr(llm_client, 'AnthropicLLMClient', lambda *args, **kwargs: mock_client)
    except (ImportError, AttributeError):
        pass

    # Patch at the module level if it exists
    try:
        import src.athena.rag.llm_client as llm_module
        if hasattr(llm_module, 'OllamaLLMClient'):
            monkeypatch.setattr(llm_module, 'OllamaLLMClient', lambda *args, **kwargs: mock_client)
        if hasattr(llm_module, 'AnthropicLLMClient'):
            monkeypatch.setattr(llm_module, 'AnthropicLLMClient', lambda *args, **kwargs: mock_client)
    except (ImportError, AttributeError):
        pass


# ============================================================================
# Test Data Generators
# ============================================================================

@pytest.fixture
def sample_events():
    """Generate sample events for testing."""
    return [
        {
            'event_type': 'action',
            'description': 'User logged in',
            'context': {'ip': '192.168.1.1', 'browser': 'Chrome'}
        },
        {
            'event_type': 'error',
            'description': 'Database connection timeout',
            'context': {'duration_ms': 5000, 'retry': True}
        },
        {
            'event_type': 'action',
            'description': 'Generated report',
            'context': {'report_type': 'monthly', 'rows': 1500}
        },
    ]


@pytest.fixture
def sample_memories():
    """Generate sample memories for testing."""
    return [
        {'content': 'Python is a versatile programming language', 'memory_type': 'fact'},
        {'content': 'Always validate user input', 'memory_type': 'pattern'},
        {'content': 'Use async/await for I/O operations', 'memory_type': 'pattern'},
        {'content': 'Decided to use PostgreSQL for production', 'memory_type': 'decision'},
    ]


@pytest.fixture
def sample_entities():
    """Generate sample graph entities for testing."""
    return [
        {'name': 'Python', 'entity_type': 'technology', 'description': 'Programming language'},
        {'name': 'Django', 'entity_type': 'framework', 'description': 'Web framework'},
        {'name': 'API Design', 'entity_type': 'concept', 'description': 'REST API principles'},
        {'name': 'PostgreSQL', 'entity_type': 'database', 'description': 'Relational database'},
    ]


@pytest.fixture
def sample_relations():
    """Generate sample graph relations for testing."""
    return [
        {'source': 'Python', 'target': 'Django', 'relation_type': 'used_by'},
        {'source': 'Django', 'target': 'API Design', 'relation_type': 'implements'},
        {'source': 'PostgreSQL', 'target': 'Django', 'relation_type': 'works_with'},
    ]


@pytest.fixture
def sample_tasks():
    """Generate sample tasks for testing."""
    return [
        {
            'title': 'Implement feature X',
            'description': 'Add support for new feature',
            'priority': 'high',
            'status': 'pending'
        },
        {
            'title': 'Fix bug in consolidation',
            'description': 'Consolidation failing for large datasets',
            'priority': 'critical',
            'status': 'in_progress'
        },
        {
            'title': 'Write documentation',
            'description': 'Update API documentation',
            'priority': 'medium',
            'status': 'pending'
        },
    ]


# ============================================================================
# Helper Fixtures
# ============================================================================

@pytest.fixture
def async_context():
    """Helper for running async tests."""
    import asyncio

    class AsyncContext:
        @staticmethod
        def run(coro):
            """Run async coroutine."""
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(coro)

    return AsyncContext()


@pytest.fixture
def mock_time():
    """Mock time for testing."""
    start_time = 1000000.0
    current = start_time

    def advance(seconds: float) -> float:
        nonlocal current
        current += seconds
        return current

    with patch('time.time', return_value=start_time):
        yield type('Time', (), {'advance': advance})()
