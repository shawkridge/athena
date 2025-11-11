"""Embedding generation via llama.cpp."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """Wrapper for llama.cpp embedding model."""

    def __init__(
        self,
        model: Optional[str] = None,
        provider: Optional[str] = None
    ):
        """Initialize llama.cpp embedding model.

        Args:
            model: Model name or URL for llama.cpp server
            provider: Always "llamacpp" (ignored, kept for compatibility)
        """
        self.provider = "llamacpp"
        self.model = model
        self.backend = None
        self._init_llamacpp(model)

    def _init_llamacpp(self, model_path: Optional[str]):
        """Initialize llama.cpp backend via HTTP server.

        Connects to running llama.cpp server for embedding generation.
        Server should be running:
          ./llama-server -m nomic-embed-text-v1.5.Q4_K_M.gguf --embedding --port 8001
        """
        import httpx
        from . import config

        # Use environment variable or default
        if model_path is None:
            model_path = config.LLAMACPP_EMBEDDINGS_URL

        self.model = model_path

        try:
            # Test connection to llama.cpp server
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{model_path}/health")
                response.raise_for_status()
                logger.info(f"Connected to llama.cpp embedding server at {model_path}")

            # Get embedding dimension by testing with a small prompt
            with httpx.Client(timeout=30.0) as client:
                test_response = client.post(
                    f"{model_path}/embedding",
                    json={"content": "test"},
                )
                test_response.raise_for_status()
                test_data = test_response.json()
                self.embedding_dim = len(test_data.get("embedding", []))

            self.backend = model_path  # Store URL for later use
            logger.info(
                f"Using llama.cpp embeddings (nomic-embed-text-v1.5): {self.embedding_dim}D at {model_path}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to llama.cpp server at {model_path}: {e}")
            # Ensure model_path is a string (in case it got set to something else)
            url_str = str(model_path) if model_path else "http://localhost:8001"
            raise RuntimeError(
                f"Embedding backend unavailable. Ensure llama.cpp server is running at {url_str}\n"
                f"Start with: ./llama-server -m nomic-embed-text-v1.5.Q4_K_M.gguf --embedding --port 8001"
            )

    def embed(self, text: str) -> list[float]:
        """Generate embedding for text via llama.cpp HTTP server.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        import httpx

        if not self.backend:
            raise RuntimeError("Embedding backend not initialized")

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.backend}/embedding",
                    json={"content": text}
                )
                response.raise_for_status()
                data = response.json()
                return data.get("embedding", [])
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise RuntimeError(f"Embedding generation failed: {e}")

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
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
