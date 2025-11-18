"""Embedding generation via llama.cpp."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """Wrapper for llama.cpp embedding model with version tracking."""

    def __init__(
        self,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        version: Optional[str] = None,
    ):
        """Initialize llama.cpp embedding model with optional version tracking.

        Args:
            model: Model name or URL for llama.cpp server
            provider: Always "llamacpp" (ignored, kept for compatibility)
            version: Optional explicit version string (default: detected from model metadata)
        """
        self.provider = "llamacpp"
        self.model = model
        self.backend = None
        self.version = version  # Explicitly set version if provided
        self.model_metadata = {}  # Store detected model info
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

            # Get embedding dimension and model info by testing with a small prompt
            with httpx.Client(timeout=30.0) as client:
                test_response = client.post(
                    f"{model_path}/embedding",
                    json={"content": "test"},
                )
                test_response.raise_for_status()
                test_data = test_response.json()
                self.embedding_dim = len(test_data.get("embedding", []))

                # Try to get model metadata
                try:
                    props_response = client.get(f"{model_path}/props")
                    if props_response.status_code == 200:
                        self.model_metadata = props_response.json()
                        logger.debug(f"Detected model metadata: {self.model_metadata}")
                except Exception as e:
                    logger.debug(f"Could not retrieve model metadata: {e}")

            # Detect version if not explicitly provided
            if not self.version:
                self.version = self._detect_version()

            self.backend = model_path  # Store URL for later use
            logger.info(
                f"Using llama.cpp embeddings: {self.embedding_dim}D, version={self.version} at {model_path}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to llama.cpp server at {model_path}: {e}")
            # Ensure model_path is a string (in case it got set to something else)
            url_str = str(model_path) if model_path else "http://localhost:8001"
            raise RuntimeError(
                f"Embedding backend unavailable. Ensure llama.cpp server is running at {url_str}\n"
                f"Start with: ./llama-server -m nomic-embed-text-v1.5.Q4_K_M.gguf --embedding --port 8001"
            )

    def _detect_version(self) -> str:
        """Detect embedding model version from metadata or defaults.

        Returns:
            Version string (e.g., 'nomic-embed-text-v1.5', 'unknown')
        """
        # Try to extract from metadata
        if self.model_metadata:
            # Check common version fields
            for key in ["model", "version", "name", "model_name"]:
                if key in self.model_metadata:
                    return str(self.model_metadata[key])

        # Try to extract from model path
        if self.model:
            model_str = str(self.model)
            # Extract model name from path (e.g., "nomic-embed-text-v1.5.Q4_K_M.gguf" -> "nomic-embed-text-v1.5")
            if "." in model_str:
                return model_str.split(".")[0]
            return model_str

        # Default fallback
        return "unknown"

    def get_version(self) -> str:
        """Get the embedding model version.

        Returns:
            Version string identifying the embedding model
        """
        return self.version or "unknown"

    def get_model_info(self) -> dict:
        """Get complete model information including version.

        Returns:
            Dictionary with:
            - version: Model version string
            - provider: 'llamacpp'
            - backend: Server URL
            - embedding_dim: Dimension of embeddings
            - metadata: Raw model metadata
        """
        return {
            "version": self.get_version(),
            "provider": self.provider,
            "backend": self.backend,
            "embedding_dim": getattr(self, "embedding_dim", None),
            "metadata": self.model_metadata,
        }

    def embed(self, text: str) -> list[float]:
        """Generate embedding for text via llama.cpp HTTP server.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        import httpx

        if not self.backend:
            logger.warning("Embedding backend not initialized, using fallback mock embedding")
            return self._mock_embedding(text)

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(f"{self.backend}/embedding", json={"content": text})
                response.raise_for_status()
                data = response.json()
                return data.get("embedding", [])
        except Exception as e:
            logger.warning(
                f"Failed to generate embedding via llama.cpp: {e}, using fallback mock embedding"
            )
            return self._mock_embedding(text)

    def _mock_embedding(self, text: str) -> list[float]:
        """Generate a deterministic mock embedding for fallback.

        Args:
            text: Text to embed

        Returns:
            Mock embedding vector (768 dimensions for mxbai-embed-large compatibility)
        """
        import hashlib
        import math

        # Use hash of text to generate deterministic but varied embeddings
        h = hashlib.md5(text.encode()).hexdigest()
        seed = int(h[:8], 16)

        # Generate 768-dimensional embedding (mxbai-embed-large dimension)
        embedding = []
        for i in range(768):
            # Pseudo-random number based on seed and index
            val = math.sin(seed + i * 12.9898) * 43758.5453
            val = val - int(val)  # Get fractional part
            embedding.append(val * 2.0 - 1.0)  # Scale to [-1, 1]

        # Normalize to unit length
        norm = sum(x**2 for x in embedding) ** 0.5
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding

    def embed_with_version(self, text: str) -> dict:
        """Generate embedding for text and return with version information.

        This is useful for storing embeddings with version tracking, enabling
        re-embedding detection when the model changes.

        Args:
            text: Text to embed

        Returns:
            Dictionary with:
            - embedding: The embedding vector
            - version: Model version used
            - provider: Embedding provider (llamacpp)
            - timestamp: When embedding was generated
        """
        from datetime import datetime

        embedding = self.embed(text)
        return {
            "embedding": embedding,
            "version": self.get_version(),
            "provider": self.provider,
            "timestamp": datetime.now().isoformat(),
        }

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        return [self.embed(text) for text in texts]

    def embed_batch_with_versions(self, texts: list[str]) -> list[dict]:
        """Generate embeddings for multiple texts with version tracking.

        Args:
            texts: List of texts to embed

        Returns:
            List of dictionaries with embedding and version info
        """
        return [self.embed_with_version(text) for text in texts]


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
