"""LLM client abstraction for RAG operations."""

import logging
import os
import re
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """Abstract LLM client for RAG operations."""

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        """Generate text from prompt.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)

        Returns:
            Generated text
        """
        pass

    @abstractmethod
    def score_relevance(self, query: str, document: str) -> float:
        """Score document relevance to query.

        Args:
            query: Search query
            document: Document content

        Returns:
            Relevance score (0.0-1.0)
        """
        pass


class MockLLMClient(LLMClient):
    """Mock LLM client for testing that doesn't require external services."""

    def __init__(self):
        """Initialize mock client."""
        logger.info("Initialized MockLLMClient (testing/no external service)")

    def generate(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        """Generate mock response.

        Args:
            prompt: Input prompt (ignored for mock)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Mock generated text
        """
        # Return a simple mock response for query expansion
        return "alternative query phrasing"

    def score_relevance(self, query: str, document: str) -> float:
        """Mock relevance scoring.

        Args:
            query: Search query
            document: Document content

        Returns:
            Fixed mock relevance score
        """
        # Always return high relevance for mock
        return 0.85


class ClaudeLLMClient(LLMClient):
    """Claude API client for RAG operations."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4"):
        """Initialize Claude client.

        Args:
            api_key: Anthropic API key (or use ANTHROPIC_API_KEY env var)
            model: Claude model to use
        """
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "anthropic package required for Claude client. "
                "Install with: pip install anthropic"
            )

        self.client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self.model = model
        logger.info(f"Initialized Claude client with model: {model}")

    def generate(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        """Generate using Claude API.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except Exception as e:
            logger.error(f"Claude generation failed: {e}")
            raise

    def score_relevance(self, query: str, document: str) -> float:
        """Score relevance using Claude.

        Args:
            query: Search query
            document: Document content

        Returns:
            Relevance score (0.0-1.0)
        """
        prompt = f"""Rate the relevance of this document to the query on a scale of 0.0 to 1.0.

Query: {query}

Document: {document}

Consider:
- Direct answer to query: High relevance (0.8-1.0)
- Related context: Medium relevance (0.5-0.7)
- Tangentially related: Low relevance (0.2-0.4)
- Unrelated: 0.0-0.1

Respond with ONLY a number between 0.0 and 1.0, nothing else."""

        try:
            response = self.generate(prompt, max_tokens=10, temperature=0.0)
            score = float(response.strip())
            # Clamp to valid range
            return max(0.0, min(1.0, score))
        except ValueError:
            logger.warning(f"Failed to parse relevance score from: {response}")
            # Fallback: medium relevance
            return 0.5
        except Exception as e:
            logger.error(f"Relevance scoring failed: {e}")
            return 0.5


class LocalLLMClientSync(LLMClient):
    """Synchronous wrapper around the async LocalLLMClient for local reasoning.

    Uses the LocalLLMClient from athena.core for reasoning via localhost:8002
    (Qwen2.5-7B-Instruct) with fallback to embedding-based text generation.

    No external API dependencies - uses local llamacpp services.
    """

    def __init__(self, reasoning_url: Optional[str] = None, embedding_url: Optional[str] = None):
        """Initialize LocalLLMClientSync.

        Args:
            reasoning_url: URL of llama.cpp reasoning server (default: localhost:8002)
            embedding_url: URL of llama.cpp embedding server (default: localhost:8001)
        """
        try:
            from athena.core.llm_client import LocalLLMClient
            from athena.core import config
        except ImportError as e:
            raise ImportError(f"Failed to import LocalLLMClient from core: {e}")

        reasoning_url = reasoning_url or config.LLAMACPP_REASONING_URL
        embedding_url = embedding_url or config.LLAMACPP_EMBEDDINGS_URL

        self.local_client = LocalLLMClient(
            reasoning_url=reasoning_url,
            embedding_url=embedding_url,
            enable_compression=False,  # Disable compression for simplicity
        )
        logger.info(f"Initialized LocalLLMClientSync with reasoning at {reasoning_url}")

    def generate(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        """Generate text using local reasoning service.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)

        Returns:
            Generated text
        """
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        try:
            # Check if there's an active event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context
                in_async_context = True
            except RuntimeError:
                # No running loop
                in_async_context = False

            if in_async_context:
                # We're in an async context, run the async function in a thread pool
                # to avoid nested event loop issues
                def run_in_thread():
                    return asyncio.run(
                        self.local_client.reason(
                            prompt=prompt,
                            max_tokens=max_tokens,
                            temperature=temperature,
                        )
                    )

                with ThreadPoolExecutor(max_workers=1) as executor:
                    result = executor.submit(run_in_thread).result(timeout=30)
                    return result.text
            else:
                # No active event loop, use asyncio.run() normally
                result = asyncio.run(
                    self.local_client.reason(
                        prompt=prompt,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                )
                return result.text
        except Exception as e:
            logger.error(f"Local reasoning generation failed: {e}")
            raise

    def score_relevance(self, query: str, document: str) -> float:
        """Score relevance using local reasoning.

        Args:
            query: Search query
            document: Document content

        Returns:
            Relevance score (0.0-1.0)
        """
        prompt = f"""Rate the relevance of this document to the query on a scale of 0.0 to 1.0.

Query: {query}

Document: {document}

Consider:
- Direct answer to query: High relevance (0.8-1.0)
- Related context: Medium relevance (0.5-0.7)
- Tangentially related: Low relevance (0.2-0.4)
- Unrelated: 0.0-0.1

Respond with ONLY a number between 0.0 and 1.0, nothing else."""

        try:
            response = self.generate(prompt, max_tokens=10, temperature=0.0)
            score = float(response.strip())
            # Clamp to valid range
            return max(0.0, min(1.0, score))
        except (ValueError, RuntimeError) as e:
            logger.warning(f"Relevance scoring failed: {e}. Returning 0.0")
            return 0.0


class OllamaLLMClient(LLMClient):
    """Ollama local LLM client (free, local alternative)."""

    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize Ollama client.

        Args:
            model: Ollama model name (defaults to config.OLLAMA_LLM_MODEL)
            base_url: Ollama server URL (defaults to config.OLLAMA_BASE_URL)
        """
        from athena.core.config import OLLAMA_LLM_MODEL, OLLAMA_BASE_URL

        model = model or OLLAMA_LLM_MODEL
        base_url = base_url or OLLAMA_BASE_URL
        try:
            import ollama
        except ImportError:
            raise ImportError(
                "ollama package required for Ollama client. " "Install with: pip install ollama"
            )

        self.client = ollama.Client(host=base_url) if base_url else ollama
        self.model = model
        logger.info(f"Initialized Ollama client with model: {model}")

        # Verify model exists
        try:
            self.client.show(model)
        except Exception:
            logger.warning(f"Model {model} not found. Pull it with: ollama pull {model}")

    def generate(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        """Generate using Ollama.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={"num_predict": max_tokens, "temperature": temperature},
            )
            return response["response"]
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise

    def score_relevance(self, query: str, document: str) -> float:
        """Score relevance using Ollama.

        Args:
            query: Search query
            document: Document content

        Returns:
            Relevance score (0.0-1.0)
        """
        prompt = f"""Rate the relevance of this document to the query on a scale of 0.0 to 1.0.

Query: {query}

Document: {document}

Consider:
- Direct answer to query: High relevance (0.8-1.0)
- Related context: Medium relevance (0.5-0.7)
- Tangentially related: Low relevance (0.2-0.4)
- Unrelated: 0.0-0.1

Respond with ONLY a number between 0.0 and 1.0."""

        try:
            response = self.generate(prompt, max_tokens=10, temperature=0.0)

            # Extract first number from response (Ollama may add extra text)
            match = re.search(r"0?\.\d+|1\.0|0|1", response)
            if match:
                score = float(match.group())
                return max(0.0, min(1.0, score))

            logger.warning(f"No score found in response: {response}")
            return 0.5
        except ValueError:
            logger.warning(f"Failed to parse relevance score from: {response}")
            return 0.5
        except Exception as e:
            logger.error(f"Relevance scoring failed: {e}")
            return 0.5


def create_llm_client(
    provider: str = "auto",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs,
) -> LLMClient:
    """Factory function to create LLM clients.

    Prioritizes local services (llamacpp) over cloud APIs for independence and cost.

    Args:
        provider: "auto" (default), "local", "claude", or "ollama"
                 "auto" tries local first, then Claude as fallback
        model: Model name (optional, uses defaults)
        api_key: API key for Claude (optional, uses env var)
        **kwargs: Additional provider-specific arguments

    Returns:
        Configured LLM client

    Raises:
        ValueError: If provider is unknown or no client available

    Examples:
        >>> # Auto-detect: tries local first, falls back to Claude
        >>> client = create_llm_client()

        >>> # Force local (localhost:8002)
        >>> client = create_llm_client("local")

        >>> # Force Claude with API key
        >>> client = create_llm_client("claude", api_key="sk-ant-...")
    """
    provider = provider.lower()

    # Auto mode: try local first, then Claude, then mock as fallback
    if provider == "auto":
        try:
            logger.info("Trying local llamacpp reasoning service (localhost:8002)...")
            return LocalLLMClientSync(**kwargs)
        except Exception as e:
            logger.warning(f"Local service unavailable: {e}. Falling back to Claude...")
            if os.getenv("ANTHROPIC_API_KEY"):
                model = model or "claude-sonnet-4"
                try:
                    return ClaudeLLMClient(api_key=api_key, model=model, **kwargs)
                except Exception as e2:
                    logger.warning(f"Claude client failed: {e2}. Using mock for testing...")
                    return MockLLMClient()
            else:
                logger.warning("No API key or local service. Using mock for testing...")
                return MockLLMClient()

    elif provider == "local":
        return LocalLLMClientSync(**kwargs)

    elif provider == "claude":
        model = model or "claude-sonnet-4"
        return ClaudeLLMClient(api_key=api_key, model=model, **kwargs)

    elif provider == "mock":
        logger.info("Using MockLLMClient for testing")
        return MockLLMClient()

    elif provider == "ollama":
        # Keep for backward compatibility but warn users
        logger.warning("Ollama provider is deprecated. Use 'local' for llamacpp instead.")
        return OllamaLLMClient(model=model, **kwargs)

    else:
        raise ValueError(
            f"Unknown provider: {provider}. "
            f"Supported: 'auto' (default), 'local', 'claude', 'mock', 'ollama'"
        )
