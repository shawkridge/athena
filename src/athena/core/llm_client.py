"""Unified client for local LLM services (embedding + reasoning + compression)."""

import asyncio
import json
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

import httpx
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result from embedding operation."""
    embedding: List[float]
    dimension: int
    latency_ms: float


@dataclass
class ReasoningResult:
    """Result from reasoning operation."""
    text: str
    tokens: int
    latency_ms: float


@dataclass
class CompressionResult:
    """Result from compression operation."""
    compressed_prompt: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    latency_ms: float


class LocalLLMClient:
    """
    Unified client for local embedding, reasoning, and prompt compression.

    Connects to llama.cpp HTTP servers for embedding and reasoning,
    with integrated LLMLingua-2 for prompt compression.

    Architecture:
    - Embedding Server (llama.cpp): nomic-embed-text-v1.5 (768D)
    - Reasoning Server (llama.cpp): Qwen2.5-7B-Instruct
    - Compression: LLMLingua-2 (optional, requires install)
    """

    def __init__(
        self,
        embedding_url: str = "http://localhost:8001",
        reasoning_url: str = "http://localhost:8002",
        enable_compression: bool = True,
        timeout_seconds: float = 60.0,
    ):
        """
        Initialize LocalLLMClient.

        Args:
            embedding_url: URL of llama.cpp embedding server
            reasoning_url: URL of llama.cpp reasoning server
            enable_compression: Enable LLMLingua-2 compression (optional)
            timeout_seconds: HTTP request timeout
        """
        self.embedding_url = embedding_url
        self.reasoning_url = reasoning_url
        self.timeout = httpx.Timeout(timeout_seconds)
        self.enable_compression = enable_compression

        # LLMLingua-2 compressor (optional)
        self.compressor = None
        if enable_compression:
            try:
                from llmlingua import PromptCompressor

                self.compressor = PromptCompressor(
                    model_name="microsoft/llmlingua-2-xlm-roberta-large-meetingbank"
                )
                logger.info("LLMLingua-2 compression enabled")
            except ImportError:
                logger.warning(
                    "LLMLingua-2 not installed. Install with: pip install llmlingua"
                )
                self.enable_compression = False

    async def check_health(self) -> Dict[str, bool]:
        """
        Check health of all LLM services.

        Returns:
            Dictionary with service health status
        """
        health = {
            "embedding": False,
            "reasoning": False,
            "compression": self.compressor is not None,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Check embedding server
            try:
                response = await client.get(f"{self.embedding_url}/health")
                health["embedding"] = response.status_code == 200
            except Exception as e:
                logger.warning(f"Embedding server health check failed: {e}")

            # Check reasoning server
            try:
                response = await client.get(f"{self.reasoning_url}/health")
                health["reasoning"] = response.status_code == 200
            except Exception as e:
                logger.warning(f"Reasoning server health check failed: {e}")

        return health

    async def embed(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for text using nomic-embed-text-v1.5.

        Args:
            text: Text to embed

        Returns:
            EmbeddingResult with 768-dimensional vector

        Raises:
            RuntimeError: If embedding server is unavailable
        """
        import time

        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.embedding_url}/embedding",
                    json={"content": text},
                )
                response.raise_for_status()
                data = response.json()

                embedding = data.get("embedding", [])
                dimension = len(embedding)
                latency_ms = (time.time() - start_time) * 1000

                logger.debug(f"Embedding generated: {dimension}D in {latency_ms:.1f}ms")

                return EmbeddingResult(
                    embedding=embedding,
                    dimension=dimension,
                    latency_ms=latency_ms,
                )
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise RuntimeError(f"Embedding generation failed: {e}")

    async def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            batch_size: Process in batches to avoid memory issues

        Returns:
            List of EmbeddingResult objects
        """
        results = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            tasks = [self.embed(text) for text in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)

        return results

    async def reason(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> ReasoningResult:
        """
        Run local reasoning with Qwen2.5-7B-Instruct.

        Args:
            prompt: Main prompt/question
            system: System prompt (optional)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-2.0)
            top_p: Nucleus sampling parameter

        Returns:
            ReasoningResult with generated text

        Raises:
            RuntimeError: If reasoning server is unavailable
        """
        import time

        start_time = time.time()

        try:
            # Format prompt with system if provided
            full_prompt = prompt
            if system:
                full_prompt = f"{system}\n\n{prompt}"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.reasoning_url}/completion",
                    json={
                        "prompt": full_prompt,
                        "n_predict": max_tokens,
                        "temperature": temperature,
                        "top_p": top_p,
                        "stop": ["\n\nUser:", "Human:"],
                    },
                )
                response.raise_for_status()
                data = response.json()

                generated_text = data.get("content", "")
                tokens = data.get("tokens_predicted", 0)
                latency_ms = (time.time() - start_time) * 1000

                logger.debug(
                    f"Reasoning generated {tokens} tokens in {latency_ms:.1f}ms"
                )

                return ReasoningResult(
                    text=generated_text,
                    tokens=tokens,
                    latency_ms=latency_ms,
                )
        except Exception as e:
            logger.error(f"Reasoning failed: {e}")
            raise RuntimeError(f"Reasoning generation failed: {e}")

    async def compress_prompt(
        self,
        context: str,
        instruction: str,
        compression_ratio: float = 0.5,
    ) -> CompressionResult:
        """
        Compress prompt using LLMLingua-2 before sending to Claude.

        Reduces prompt length while preserving semantic information.
        Useful for cost optimization on Claude API.

        Args:
            context: Long-form context/memory to compress
            instruction: Task instruction to preserve
            compression_ratio: Target compression ratio (0.0-1.0)

        Returns:
            CompressionResult with compressed prompt

        Raises:
            RuntimeError: If compression not enabled
        """
        import time

        start_time = time.time()

        if not self.enable_compression or not self.compressor:
            # Return original if compression not available
            return CompressionResult(
                compressed_prompt=context,
                original_tokens=len(context.split()),
                compressed_tokens=len(context.split()),
                compression_ratio=1.0,
                latency_ms=0,
            )

        try:
            result = self.compressor.compress_prompt(
                prompt=context,
                instruction=instruction,
                rate=compression_ratio,
                target_token=-1,  # Auto-calculate from rate
            )

            original_tokens = len(context.split())
            compressed_tokens = len(result["compressed_prompt"].split())
            actual_ratio = compressed_tokens / original_tokens if original_tokens > 0 else 1.0
            latency_ms = (time.time() - start_time) * 1000

            logger.debug(
                f"Prompt compressed: {original_tokens} → {compressed_tokens} tokens "
                f"({actual_ratio:.1%}) in {latency_ms:.1f}ms"
            )

            return CompressionResult(
                compressed_prompt=result["compressed_prompt"],
                original_tokens=original_tokens,
                compressed_tokens=compressed_tokens,
                compression_ratio=actual_ratio,
                latency_ms=latency_ms,
            )
        except Exception as e:
            logger.error(f"Prompt compression failed: {e}")
            # Return original on failure
            return CompressionResult(
                compressed_prompt=context,
                original_tokens=len(context.split()),
                compressed_tokens=len(context.split()),
                compression_ratio=1.0,
                latency_ms=(time.time() - start_time) * 1000,
            )

    async def consolidate_with_reasoning(
        self,
        events_text: str,
        task_description: str = "Extract semantic patterns from these episodic events",
    ) -> ReasoningResult:
        """
        Use local reasoning for consolidation task.

        Optimized system prompt for pattern extraction.

        Args:
            events_text: Formatted episodic events
            task_description: Task description

        Returns:
            ReasoningResult with extracted patterns
        """
        system_prompt = (
            "You are a consolidation engine for memory systems. "
            "Your role is to extract semantic patterns, relationships, and insights "
            "from episodic events. Be precise and concise. Output structured data."
        )

        prompt = f"""{task_description}:

{events_text}

Provide output in JSON format:
{{
  "patterns": [
    {{"name": "...", "confidence": 0.0-1.0, "evidence_count": N, "description": "..."}}
  ],
  "relationships": [
    {{"source": "...", "target": "...", "type": "...", "strength": 0.0-1.0}}
  ],
  "insights": ["..."]
}}"""

        return await self.reason(
            prompt=prompt,
            system=system_prompt,
            max_tokens=2048,
            temperature=0.5,
            top_p=0.9,
        )


def get_llm_client(
    embedding_url: Optional[str] = None,
    reasoning_url: Optional[str] = None,
    enable_compression: bool = True,
) -> LocalLLMClient:
    """
    Factory function to get or create LocalLLMClient.

    Uses environment variables if URLs not provided:
    - LLAMACPP_EMBEDDINGS_URL (default: http://localhost:8001)
    - LLAMACPP_REASONING_URL (default: http://localhost:8002)

    Args:
        embedding_url: Override embedding server URL
        reasoning_url: Override reasoning server URL
        enable_compression: Enable prompt compression

    Returns:
        LocalLLMClient instance
    """
    from . import config

    if embedding_url is None:
        embedding_url = config.LLAMACPP_EMBEDDINGS_URL
    if reasoning_url is None:
        reasoning_url = config.LLAMACPP_REASONING_URL

    return LocalLLMClient(
        embedding_url=embedding_url,
        reasoning_url=reasoning_url,
        enable_compression=enable_compression,
    )
