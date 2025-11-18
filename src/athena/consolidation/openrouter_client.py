"""
OpenRouter API client for dream generation models.

Provides unified interface to multiple OpenRouter models with fallback handling,
rate limiting, and error recovery.
"""

import asyncio
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import httpx
import logging

logger = logging.getLogger(__name__)


class OpenRouterModel(str, Enum):
    """Available OpenRouter models for dream generation."""

    # Reasoning & dependency analysis
    DEEPSEEK_V3_1 = "deepseek/deepseek-chat-v3.1:free"

    # Code synthesis
    QWEN_2_5_CODER_32B = "qwen/qwen-2.5-coder-32b-instruct:free"

    # Fallback options
    DEEPSEEK_R1 = "deepseek/deepseek-r1:free"
    MISTRAL_SMALL_3_2 = "mistralai/mistral-small-3.2-24b-instruct:free"


@dataclass
class OpenRouterConfig:
    """Configuration for OpenRouter API client."""

    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"
    timeout_seconds: int = 120
    max_retries: int = 3
    retry_delay_seconds: float = 2.0

    @classmethod
    def from_env(cls) -> "OpenRouterConfig":
        """Load configuration from environment variables."""
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY environment variable not set. "
                "Please provide your OpenRouter API key."
            )
        return cls(api_key=api_key)


class RateLimitError(Exception):
    """Raised when OpenRouter rate limit is hit."""

    pass


class ModelUnavailableError(Exception):
    """Raised when a model is unavailable."""

    pass


class OpenRouterClient:
    """
    Client for OpenRouter API with support for multiple models and fallbacks.

    Usage:
        client = OpenRouterClient.from_env()
        response = await client.generate(
            model=OpenRouterModel.DEEPSEEK_V3_1,
            prompt="Generate 5 procedure variants...",
            max_tokens=2000
        )
    """

    def __init__(self, config: OpenRouterConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.timeout_seconds,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "HTTP-Referer": "https://athena-memory.local",
                "X-Title": "Athena Dream System",
            },
        )

    @classmethod
    def from_env(cls) -> "OpenRouterClient":
        """Create client from environment variables."""
        config = OpenRouterConfig.from_env()
        return cls(config)

    async def generate(
        self,
        model: OpenRouterModel,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> Dict[str, Any]:
        """
        Generate text using OpenRouter model.

        Args:
            model: Model to use
            prompt: User prompt
            system: System prompt (optional)
            max_tokens: Max tokens in response
            temperature: Sampling temperature (0.0-2.0)
            top_p: Nucleus sampling parameter

        Returns:
            Response dict with 'content' and metadata

        Raises:
            RateLimitError: If rate limited
            ModelUnavailableError: If model unavailable
            Exception: For other API errors after retries
        """
        messages = []

        if system:
            messages.append({"role": "system", "content": system})

        messages.append({"role": "user", "content": prompt})

        return await self._call_with_retries(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        )

    async def _call_with_retries(
        self,
        model: OpenRouterModel,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> Dict[str, Any]:
        """Make API call with automatic retry logic."""
        last_error = None

        for attempt in range(self.config.max_retries):
            try:
                response = await self._call_openrouter(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                )
                return response

            except RateLimitError as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    wait_time = self.config.retry_delay_seconds * (2**attempt)
                    logger.warning(
                        f"Rate limited on attempt {attempt + 1}. "
                        f"Waiting {wait_time}s before retry..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise

            except ModelUnavailableError as e:
                last_error = e
                logger.error(f"Model {model} unavailable: {e}")
                raise

            except Exception as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    logger.warning(f"Error on attempt {attempt + 1}: {e}. Retrying...")
                    await asyncio.sleep(self.config.retry_delay_seconds)
                else:
                    raise

        raise last_error or Exception("Unknown error in API call")

    async def _call_openrouter(
        self,
        model: OpenRouterModel,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> Dict[str, Any]:
        """Make single API call to OpenRouter."""
        payload = {
            "model": model.value,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }

        try:
            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()

            data = response.json()

            # Check for rate limiting
            if response.status_code == 429:
                raise RateLimitError("OpenRouter rate limit exceeded")

            # Check for model unavailable
            if "error" in data and "unavailable" in str(data.get("error", "")).lower():
                raise ModelUnavailableError(f"Model {model} unavailable")

            # Extract content from response
            if "choices" not in data or not data["choices"]:
                raise ValueError(f"Invalid response format: {data}")

            choice = data["choices"][0]
            if "message" not in choice:
                raise ValueError(f"No message in choice: {choice}")

            content = choice["message"].get("content", "")

            return {
                "content": content,
                "model": model.value,
                "usage": data.get("usage", {}),
                "stop_reason": choice.get("finish_reason"),
                "raw_response": data,
            }

        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling {model}: {e}")
            raise

    async def generate_batch(
        self, model: OpenRouterModel, prompts: List[str], system: Optional[str] = None, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Generate responses for multiple prompts in parallel.

        Args:
            model: Model to use
            prompts: List of prompts
            system: System prompt for all
            **kwargs: Additional args for generate()

        Returns:
            List of responses in same order as prompts
        """
        tasks = [
            self.generate(model=model, prompt=prompt, system=system, **kwargs) for prompt in prompts
        ]

        return await asyncio.gather(*tasks)

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Model-specific configuration for dream generation
DREAM_MODELS_CONFIG = {
    "constraint_relaxation": {
        "primary": OpenRouterModel.DEEPSEEK_V3_1,
        "fallback": OpenRouterModel.MISTRAL_SMALL_3_2,
        "temperature": 0.8,
        "top_p": 0.9,
        "max_tokens": 2000,
    },
    "cross_project_synthesis": {
        "primary": OpenRouterModel.QWEN_2_5_CODER_32B,
        "fallback": OpenRouterModel.DEEPSEEK_V3_1,
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 3000,
    },
    "semantic_matching": {
        "primary": OpenRouterModel.DEEPSEEK_V3_1,
        "fallback": OpenRouterModel.MISTRAL_SMALL_3_2,
        "temperature": 0.5,
        "top_p": 0.9,
        "max_tokens": 1000,
    },
}
