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
    def generate(
        self, prompt: str, max_tokens: int = 500, temperature: float = 0.7
    ) -> str:
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

    def generate(
        self, prompt: str, max_tokens: int = 500, temperature: float = 0.7
    ) -> str:
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


class OllamaLLMClient(LLMClient):
    """Ollama local LLM client (free, local alternative)."""

    def __init__(self, model: str = "llama3.1:8b", base_url: Optional[str] = None):
        """Initialize Ollama client.

        Args:
            model: Ollama model name
            base_url: Ollama server URL (default: http://localhost:11434)
        """
        try:
            import ollama
        except ImportError:
            raise ImportError(
                "ollama package required for Ollama client. "
                "Install with: pip install ollama"
            )

        self.client = ollama.Client(host=base_url) if base_url else ollama
        self.model = model
        logger.info(f"Initialized Ollama client with model: {model}")

        # Verify model exists
        try:
            self.client.show(model)
        except Exception as e:
            logger.warning(
                f"Model {model} not found. Pull it with: ollama pull {model}"
            )

    def generate(
        self, prompt: str, max_tokens: int = 500, temperature: float = 0.7
    ) -> str:
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
    provider: str = "claude",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs,
) -> LLMClient:
    """Factory function to create LLM clients.

    Args:
        provider: "claude" or "ollama"
        model: Model name (optional, uses defaults)
        api_key: API key for Claude (optional, uses env var)
        **kwargs: Additional provider-specific arguments

    Returns:
        Configured LLM client

    Raises:
        ValueError: If provider is unknown

    Examples:
        >>> # Claude with API key
        >>> client = create_llm_client("claude", api_key="sk-ant-...")

        >>> # Ollama with custom model
        >>> client = create_llm_client("ollama", model="mistral")

        >>> # Auto-detect from environment
        >>> client = create_llm_client()  # Uses ANTHROPIC_API_KEY if available
    """
    provider = provider.lower()

    if provider == "claude":
        model = model or "claude-sonnet-4"
        return ClaudeLLMClient(api_key=api_key, model=model, **kwargs)

    elif provider == "ollama":
        model = model or "llama3.1:8b"
        return OllamaLLMClient(model=model, **kwargs)

    else:
        raise ValueError(
            f"Unknown provider: {provider}. " f"Supported: 'claude', 'ollama'"
        )
