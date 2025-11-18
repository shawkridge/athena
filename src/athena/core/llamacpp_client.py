"""llama.cpp client for embeddings and LLM inference.

Provides unified interface to llama.cpp for both embedding generation
and text generation, optimized for CPU-only deployment.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional, Dict

try:
    from llama_cpp import Llama

    LLAMACPP_AVAILABLE = True
except ImportError:
    LLAMACPP_AVAILABLE = False

logger = logging.getLogger(__name__)


class LlamaCppEmbedding:
    """Embedding model using llama.cpp for CPU-optimized inference."""

    def __init__(
        self,
        model_path: str | Path,
        n_ctx: int = 512,
        n_threads: Optional[int] = None,
        embedding: bool = True,
    ):
        """Initialize embedding model.

        Args:
            model_path: Path to GGUF model file
            n_ctx: Context window size
            n_threads: Number of CPU threads (default: auto-detect)
            embedding: Enable embedding mode
        """
        if not LLAMACPP_AVAILABLE:
            raise ImportError(
                "llama-cpp-python not installed. " "Install with: pip install llama-cpp-python"
            )

        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        # Auto-detect threads if not specified
        if n_threads is None:
            n_threads = min(os.cpu_count() or 4, 8)  # Cap at 8 threads

        logger.info(f"Loading embedding model: {self.model_path.name}")
        logger.info(f"Context: {n_ctx}, Threads: {n_threads}")

        self.model = Llama(
            model_path=str(self.model_path),
            n_ctx=n_ctx,
            n_threads=n_threads,
            n_gpu_layers=0,  # CPU only
            embedding=embedding,
            verbose=False,
        )

        # Get embedding dimensions
        test_embed = self.model.embed("test")
        self.embedding_dim = len(test_embed)
        logger.info(f"Embedding dimensions: {self.embedding_dim}")

    def embed(self, text: str) -> List[float]:
        """Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        return self.model.embed(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        return [self.embed(text) for text in texts]


class LlamaCppLLM:
    """LLM using llama.cpp for CPU-optimized inference."""

    def __init__(
        self,
        model_path: str | Path,
        n_ctx: int = 8192,
        n_threads: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        max_tokens: int = 512,
    ):
        """Initialize LLM.

        Args:
            model_path: Path to GGUF model file
            n_ctx: Context window size
            n_threads: Number of CPU threads (default: auto-detect)
            temperature: Sampling temperature
            top_p: Nucleus sampling threshold
            top_k: Top-K sampling
            max_tokens: Maximum tokens to generate
        """
        if not LLAMACPP_AVAILABLE:
            raise ImportError(
                "llama-cpp-python not installed. " "Install with: pip install llama-cpp-python"
            )

        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        # Auto-detect threads if not specified
        if n_threads is None:
            n_threads = min(os.cpu_count() or 4, 8)

        logger.info(f"Loading LLM: {self.model_path.name}")
        logger.info(f"Context: {n_ctx}, Threads: {n_threads}")

        self.model = Llama(
            model_path=str(self.model_path),
            n_ctx=n_ctx,
            n_threads=n_threads,
            n_gpu_layers=0,  # CPU only
            verbose=False,
        )

        # Generation defaults
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.max_tokens = max_tokens

        logger.info(f"LLM loaded successfully: {self.model_path.name}")

    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop: Optional[List[str]] = None,
    ) -> str:
        """Generate text from prompt.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate (default: from init)
            temperature: Sampling temperature (default: from init)
            top_p: Nucleus sampling (default: from init)
            top_k: Top-K sampling (default: from init)
            stop: Stop sequences

        Returns:
            Generated text
        """
        response = self.model(
            prompt,
            max_tokens=max_tokens or self.max_tokens,
            temperature=temperature or self.temperature,
            top_p=top_p or self.top_p,
            top_k=top_k or self.top_k,
            stop=stop,
            echo=False,
        )

        return response["choices"][0]["text"]

    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Generate chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated response
        """
        response = self.model.create_chat_completion(
            messages=messages,
            max_tokens=max_tokens or self.max_tokens,
            temperature=temperature or self.temperature,
        )

        return response["choices"][0]["message"]["content"]


def get_embedding_model(model_path: Optional[str] = None, **kwargs) -> LlamaCppEmbedding:
    """Factory function to create embedding model.

    Args:
        model_path: Path to model file (default: from config)
        **kwargs: Additional arguments for LlamaCppEmbedding

    Returns:
        Embedding model instance
    """
    from . import config

    if model_path is None:
        model_path = config.LLAMACPP_EMBEDDING_MODEL_PATH

    return LlamaCppEmbedding(model_path, **kwargs)


def get_llm_model(model_path: Optional[str] = None, **kwargs) -> LlamaCppLLM:
    """Factory function to create LLM.

    Args:
        model_path: Path to model file (default: from config)
        **kwargs: Additional arguments for LlamaCppLLM

    Returns:
        LLM instance
    """
    from . import config

    if model_path is None:
        model_path = config.LLAMACPP_LLM_MODEL_PATH

    return LlamaCppLLM(model_path, **kwargs)
