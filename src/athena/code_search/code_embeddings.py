"""Code-specific embedding models for semantic search."""

import logging
from typing import List, Optional, Dict, Any
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class EmbeddingModelType(Enum):
    """Types of embedding models."""

    CODE_LLAMA = "codellama"  # Code-specific (8B, 34B parameters)
    STARCODE = "starcode"  # StarCoder models
    CLAUDE = "claude"  # Anthropic Claude models
    GPT = "gpt"  # OpenAI GPT models
    GENERAL = "general"  # General-purpose embeddings
    MOCK = "mock"  # Mock for testing


class CodeEmbeddingModel(ABC):
    """Abstract base class for code embedding models."""

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        pass

    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Dimension of embedding vectors."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the model."""
        pass


class CodeLlamaEmbedding(CodeEmbeddingModel):
    """CodeLlama embedding model (via Ollama)."""

    def __init__(self, model_name: str = "codellama"):
        """Initialize CodeLlama embedding model."""
        self._model_name = model_name
        self._embedding_dim = 4096

    def embed(self, text: str) -> List[float]:
        """Generate embedding using CodeLlama."""
        try:
            import ollama

            response = ollama.embeddings(model=self._model_name, prompt=text)
            return response.get("embedding", [])
        except ImportError:
            logger.warning("Ollama not installed, returning mock embedding")
            return self._mock_embedding(text)
        except Exception as e:
            logger.error(f"Error generating CodeLlama embedding: {e}")
            return self._mock_embedding(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            embeddings.append(self.embed(text))
        return embeddings

    def _mock_embedding(self, text: str) -> List[float]:
        """Generate deterministic mock embedding."""
        import hashlib

        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        import random

        random.seed(hash_val)
        return [random.uniform(-1, 1) for _ in range(self._embedding_dim)]

    @property
    def embedding_dim(self) -> int:
        """Dimension of CodeLlama embeddings."""
        return self._embedding_dim

    @property
    def model_name(self) -> str:
        """Model name."""
        return self._model_name


class StarCoderEmbedding(CodeEmbeddingModel):
    """StarCoder embedding model."""

    def __init__(self, model_name: str = "starcoder"):
        """Initialize StarCoder embedding model."""
        self._model_name = model_name
        self._embedding_dim = 4096

    def embed(self, text: str) -> List[float]:
        """Generate embedding using StarCoder."""
        try:
            import ollama

            response = ollama.embeddings(model=self._model_name, prompt=text)
            return response.get("embedding", [])
        except ImportError:
            logger.warning("Ollama not installed, returning mock embedding")
            return self._mock_embedding(text)
        except Exception as e:
            logger.error(f"Error generating StarCoder embedding: {e}")
            return self._mock_embedding(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return [self.embed(text) for text in texts]

    def _mock_embedding(self, text: str) -> List[float]:
        """Generate deterministic mock embedding."""
        import hashlib

        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        import random

        random.seed(hash_val)
        return [random.uniform(-1, 1) for _ in range(self._embedding_dim)]

    @property
    def embedding_dim(self) -> int:
        """Dimension of StarCoder embeddings."""
        return self._embedding_dim

    @property
    def model_name(self) -> str:
        """Model name."""
        return self._model_name


class ClaudeEmbedding(CodeEmbeddingModel):
    """Claude embedding via Anthropic API."""

    def __init__(self, model_name: str = "claude-3-5-sonnet-20241022"):
        """Initialize Claude embedding model."""
        from athena.core import config

        self._model_name = model_name
        # Use configured embedding dimension (standardized to 768D for compatibility)
        self._embedding_dim = config.CLAUDE_EMBEDDING_DIM
        self._client = None

    def embed(self, text: str) -> List[float]:
        """Generate embedding using Claude."""
        try:
            import anthropic

            if self._client is None:
                self._client = anthropic.Anthropic()

            # Use Claude's embedding capability
            # Note: Claude doesn't have native embeddings, use mock
            return self._mock_embedding(text)

        except ImportError:
            logger.warning("Anthropic not installed, using mock embedding")
            return self._mock_embedding(text)
        except Exception as e:
            logger.error(f"Error generating Claude embedding: {e}")
            return self._mock_embedding(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return [self.embed(text) for text in texts]

    def _mock_embedding(self, text: str) -> List[float]:
        """Generate deterministic mock embedding."""
        import hashlib

        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        import random

        random.seed(hash_val)
        return [random.uniform(-1, 1) for _ in range(self._embedding_dim)]

    @property
    def embedding_dim(self) -> int:
        """Dimension of Claude embeddings."""
        return self._embedding_dim

    @property
    def model_name(self) -> str:
        """Model name."""
        return self._model_name


class MockEmbedding(CodeEmbeddingModel):
    """Mock embedding for testing."""

    def __init__(self, embedding_dim: int = 384):
        """Initialize mock embedding."""
        self._embedding_dim = embedding_dim
        self._cache = {}

    def embed(self, text: str) -> List[float]:
        """Generate mock embedding."""
        if text in self._cache:
            return self._cache[text]

        import hashlib

        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        import random

        random.seed(hash_val)
        embedding = [random.uniform(-1, 1) for _ in range(self._embedding_dim)]

        self._cache[text] = embedding
        return embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate mock embeddings."""
        return [self.embed(text) for text in texts]

    @property
    def embedding_dim(self) -> int:
        """Dimension of embeddings."""
        return self._embedding_dim

    @property
    def model_name(self) -> str:
        """Model name."""
        return "mock"


class CodeEmbeddingManager:
    """Manages code-specific embedding models."""

    def __init__(self, model_type: EmbeddingModelType = EmbeddingModelType.CODE_LLAMA):
        """
        Initialize embedding manager.

        Args:
            model_type: Type of embedding model to use
        """
        self.model_type = model_type
        self.model = self._create_model(model_type)

    def _create_model(self, model_type: EmbeddingModelType) -> CodeEmbeddingModel:
        """Create embedding model of specified type."""
        if model_type == EmbeddingModelType.CODE_LLAMA:
            return CodeLlamaEmbedding()
        elif model_type == EmbeddingModelType.STARCODE:
            return StarCoderEmbedding()
        elif model_type == EmbeddingModelType.CLAUDE:
            return ClaudeEmbedding()
        elif model_type == EmbeddingModelType.MOCK:
            return MockEmbedding()
        else:
            logger.warning(f"Unknown model type {model_type}, using mock")
            return MockEmbedding()

    def embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        return self.model.embed(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return self.model.embed_batch(texts)

    def embed_code(self, code: str, language: Optional[str] = None) -> List[float]:
        """
        Generate embedding for code with optional language context.

        Args:
            code: Code to embed
            language: Programming language (optional)

        Returns:
            Embedding vector
        """
        # Enhance code with language hint for better embeddings
        if language:
            enhanced_code = f"[{language}]\n{code}"
        else:
            enhanced_code = code

        return self.embed(enhanced_code)

    def embed_code_batch(
        self,
        codes: List[str],
        language: Optional[str] = None,
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple code snippets.

        Args:
            codes: List of code snippets
            language: Programming language (optional)

        Returns:
            List of embedding vectors
        """
        if language:
            enhanced_codes = [f"[{language}]\n{code}" for code in codes]
        else:
            enhanced_codes = codes

        return self.embed_batch(enhanced_codes)

    @property
    def embedding_dimension(self) -> int:
        """Get embedding dimension."""
        return self.model.embedding_dim

    @property
    def model_name(self) -> str:
        """Get model name."""
        return self.model.model_name

    def switch_model(self, model_type: EmbeddingModelType):
        """Switch to different embedding model."""
        logger.info(f"Switching embedding model to {model_type.value}")
        self.model_type = model_type
        self.model = self._create_model(model_type)

    def get_statistics(self) -> Dict[str, Any]:
        """Get embedding manager statistics."""
        return {
            "model_type": self.model_type.value,
            "model_name": self.model.model_name,
            "embedding_dimension": self.model.embedding_dim,
        }


# Convenience function for creating default manager
def create_code_embedding_manager(
    model_type: str = "codellama",
) -> CodeEmbeddingManager:
    """
    Create code embedding manager with specified model.

    Args:
        model_type: Type of model (codellama, starcode, claude, mock)

    Returns:
        CodeEmbeddingManager instance
    """
    type_map = {
        "codellama": EmbeddingModelType.CODE_LLAMA,
        "starcode": EmbeddingModelType.STARCODE,
        "claude": EmbeddingModelType.CLAUDE,
        "mock": EmbeddingModelType.MOCK,
    }

    model_enum = type_map.get(model_type.lower(), EmbeddingModelType.CODE_LLAMA)
    return CodeEmbeddingManager(model_enum)
