"""Embedding generation via Ollama."""

import ollama
from typing import Optional


class EmbeddingModel:
    """Wrapper for Ollama embedding model."""

    def __init__(self, model: str = "nomic-embed-text"):
        """Initialize embedding model.

        Args:
            model: Ollama model name
        """
        self.model = model
        self._verify_model()

    def _verify_model(self):
        """Verify model is available in Ollama."""
        try:
            # Test embedding generation
            ollama.embeddings(model=self.model, prompt="test")
        except Exception as e:
            raise RuntimeError(
                f"Model '{self.model}' not available. "
                f"Install with: ollama pull {self.model}\n"
                f"Error: {e}"
            )

    def embed(self, text: str) -> list[float]:
        """Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            768-dimensional embedding vector
        """
        response = ollama.embeddings(model=self.model, prompt=text)
        return response["embedding"]

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
