"""Embedding generation via Ollama or llama.cpp."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """Wrapper for embedding models (Ollama or llama.cpp)."""

    def __init__(
        self,
        model: Optional[str] = None,
        provider: Optional[str] = None
    ):
        """Initialize embedding model.

        Args:
            model: Model name (for Ollama) or path (for llama.cpp)
            provider: "ollama" or "llamacpp" (default: from config)
        """
        from . import config

        # Determine provider
        if provider is None:
            provider = config.EMBEDDING_PROVIDER

        self.provider = provider
        self.model = model
        self.backend = None

        if provider == "llamacpp":
            self._init_llamacpp(model)
        elif provider == "ollama":
            self._init_ollama(model)
        else:
            raise ValueError(f"Unknown embedding provider: {provider}")

    def _init_llamacpp(self, model_path: Optional[str]):
        """Initialize llama.cpp backend."""
        from . import config
        from .llamacpp_client import get_embedding_model

        try:
            self.backend = get_embedding_model(model_path)
            self.embedding_dim = self.backend.embedding_dim
            logger.info(f"Using llama.cpp embeddings: {self.embedding_dim}D")
        except Exception as e:
            logger.error(f"Failed to initialize llama.cpp: {e}")
            logger.warning("Falling back to Ollama")
            self._init_ollama(config.OLLAMA_EMBEDDING_MODEL)

    def _init_ollama(self, model: Optional[str]):
        """Initialize Ollama backend."""
        from . import config
        import ollama

        if model is None:
            model = config.OLLAMA_EMBEDDING_MODEL

        self.model = model
        self.provider = "ollama"

        try:
            # Test embedding generation
            response = ollama.embeddings(model=self.model, prompt="test")
            self.embedding_dim = len(response["embedding"])
            self.backend = ollama
            logger.info(f"Using Ollama embeddings: {self.embedding_dim}D")
        except Exception as e:
            import sys
            print(
                f"WARNING: Embedding model '{self.model}' not available. "
                f"Install with: ollama pull {self.model}\n"
                f"Error: {e}",
                file=sys.stderr
            )
            self.available = False

    def embed(self, text: str) -> list[float]:
        """Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        if self.provider == "llamacpp" and self.backend:
            return self.backend.embed(text)
        elif self.provider == "ollama" and self.backend:
            response = self.backend.embeddings(model=self.model, prompt=text)
            return response["embedding"]
        else:
            raise RuntimeError("No embedding backend available")

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if self.provider == "llamacpp" and self.backend:
            return self.backend.embed_batch(texts)
        else:
            return [self.embed(text) for text in texts]


def cosine_similarity(vec1, vec2) -> float:
    """Calculate cosine similarity between two vectors.

    Accepts both list[float] and np.ndarray inputs.

    Args:
        vec1: First vector (list or numpy array)
        vec2: Second vector (list or numpy array)

    Returns:
        Similarity score between -1 and 1
    """
    import numpy as np

    # Convert to numpy arrays if needed
    v1 = np.array(vec1) if not isinstance(vec1, np.ndarray) else vec1
    v2 = np.array(vec2) if not isinstance(vec2, np.ndarray) else vec2

    dot_product = np.dot(v1, v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return float(dot_product / (norm1 * norm2))
