"""Pytest configuration and shared fixtures for Phase 1 unit tests.

Provides:
- Mock embedding model to avoid external dependencies
- Automatic patching of EmbeddingModel before any imports
- Consistent test environment across all unit tests
"""

import pytest
import numpy as np
import sys
from pathlib import Path


# ============================================================================
# Mock Embedding Model
# ============================================================================

class MockEmbeddingModel:
    """Mock embedding model for testing without external embedding server."""

    def __init__(self, model=None, provider=None):
        """Initialize mock embedding model.

        Args:
            model: Model name (ignored for mock)
            provider: Provider type (ignored for mock)
        """
        self.model = model or "mock"
        self.provider = "mock"
        self.backend = None
        self.embedding_dim = 768
        self.available = True

    def embed(self, text: str) -> list[float]:
        """Generate deterministic embedding based on text hash.

        Args:
            text: Text to embed

        Returns:
            768-dimensional embedding vector
        """
        # Use text hash as seed for reproducible but varied embeddings
        seed = hash(text) % (2**32)
        np.random.seed(seed)
        return np.random.randn(768).tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        return [self.embed(text) for text in texts]


# ============================================================================
# Pytest Hooks for Early Patching
# ============================================================================

def pytest_configure(config):
    """Configure pytest before test collection.

    Patch EmbeddingModel before any imports that use it.
    Also configure test environment to use SQLite only.
    """
    import os

    # Ensure tests use SQLite, not PostgreSQL
    # Remove PostgreSQL environment variables
    for key in list(os.environ.keys()):
        if 'POSTGRES' in key or 'DATABASE_URL' in key.upper():
            del os.environ[key]

    import athena.core.embeddings
    import athena.memory.store

    # Replace EmbeddingModel with mock
    athena.core.embeddings.EmbeddingModel = MockEmbeddingModel
    athena.memory.store.EmbeddingModel = MockEmbeddingModel

    # Also patch in the actual module dictionary for safety
    sys.modules["athena.core.embeddings"].EmbeddingModel = MockEmbeddingModel
    sys.modules["athena.memory.store"].EmbeddingModel = MockEmbeddingModel


# ============================================================================
# Shared Fixtures
# ============================================================================

@pytest.fixture
def mock_embedding_instance():
    """Provide a mock embedding model instance for tests that need it."""
    return MockEmbeddingModel()
