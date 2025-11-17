"""Local LLM Client - Qwen3-4B-Instruct reasoning on llamacpp.

Uses local llamacpp server on port 8002 for fast, cost-free reasoning about:
- Agent outcome analysis
- Strategy improvements
- Pattern analysis
- No API costs, ~50ms latency
"""

import logging
import httpx
import json
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Configuration
LLM_BASE_URL = "http://localhost:8002"
LLM_TIMEOUT = 30.0  # seconds
LLM_MAX_TOKENS = 500


class LocalLLMClient:
    """Client for Qwen3-4B-Instruct local reasoning via llamacpp."""

    def __init__(self, base_url: str = LLM_BASE_URL, timeout: float = LLM_TIMEOUT):
        """Initialize LLM client.

        Args:
            base_url: URL of local LLM server (default: localhost:8002)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        self._health_checked = False

        logger.info(f"LLMClient: Initialized at {self.base_url}")

    async def health_check(self) -> bool:
        """Check if LLM server is healthy.

        Returns:
            True if server is healthy
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            self._health_checked = response.status_code == 200
            if self._health_checked:
                logger.info("LLMClient: Local LLM server is healthy")
            return self._health_checked
        except Exception as e:
            logger.warning(f"LLMClient: Health check failed: {e}")
            return False

    async def reason_about_outcome(
        self,
        agent_id: str,
        action: str,
        result: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Ask LLM to reason about why an action succeeded/failed.

        Args:
            agent_id: ID of agent that performed action
            action: Action that was taken
            result: Result of the action
            context: Additional context

        Returns:
            Reasoning from LLM or None if failed
        """
        if not await self.health_check():
            logger.warning("LLMClient: LLM server not healthy, skipping reasoning")
            return None

        try:
            prompt = self._build_outcome_reasoning_prompt(
                agent_id=agent_id,
                action=action,
                result=result,
                context=context,
            )

            response = await self._call_llm(prompt)

            logger.debug(f"LLMClient: Got reasoning for {agent_id}/{action}")
            return response

        except Exception as e:
            logger.error(f"LLMClient: Error getting reasoning: {e}")
            return None

    async def suggest_improvement(
        self,
        agent_id: str,
        strategy: str,
        outcomes: list,
        limit: int = 10,
    ) -> Optional[str]:
        """Ask LLM to suggest strategy improvements.

        Args:
            agent_id: ID of agent
            strategy: Current strategy description
            outcomes: Recent outcomes (success rates, etc.)
            limit: Limit recent outcomes to consider

        Returns:
            Suggestion from LLM or None if failed
        """
        if not await self.health_check():
            logger.warning("LLMClient: LLM server not healthy, skipping improvement")
            return None

        try:
            prompt = self._build_improvement_prompt(
                agent_id=agent_id,
                strategy=strategy,
                outcomes=outcomes[:limit],
            )

            response = await self._call_llm(prompt)

            logger.debug(f"LLMClient: Got improvement suggestion for {agent_id}")
            return response

        except Exception as e:
            logger.error(f"LLMClient: Error getting improvement: {e}")
            return None

    async def analyze_pattern(
        self,
        pattern_description: str,
        examples: list,
    ) -> Optional[str]:
        """Ask LLM to analyze a pattern.

        Args:
            pattern_description: Description of pattern
            examples: Examples of the pattern

        Returns:
            Analysis from LLM or None if failed
        """
        if not await self.health_check():
            return None

        try:
            prompt = self._build_pattern_analysis_prompt(
                pattern_description=pattern_description,
                examples=examples[:5],
            )

            response = await self._call_llm(prompt)
            return response

        except Exception as e:
            logger.error(f"LLMClient: Error analyzing pattern: {e}")
            return None

    async def _call_llm(self, prompt: str) -> Optional[str]:
        """Call local LLM with prompt.

        Args:
            prompt: Prompt to send

        Returns:
            Response text or None if failed
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/v1/completions",
                json={
                    "prompt": prompt,
                    "max_tokens": LLM_MAX_TOKENS,
                    "temperature": 0.7,
                    "top_p": 0.9,
                },
            )

            if response.status_code == 200:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0].get("text", "").strip()

            logger.warning(f"LLMClient: Unexpected response: {response.status_code}")
            return None

        except Exception as e:
            logger.error(f"LLMClient: Error calling LLM: {e}")
            return None

    def _build_outcome_reasoning_prompt(
        self,
        agent_id: str,
        action: str,
        result: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build prompt for outcome reasoning.

        Args:
            agent_id: Agent ID
            action: Action taken
            result: Action result
            context: Additional context

        Returns:
            Prompt string
        """
        context_str = ""
        if context:
            context_str = f"\nContext: {json.dumps(context, default=str)}"

        return f"""Agent Learning: Outcome Analysis
Agent: {agent_id}
Action: {action}
Result: {result}{context_str}

Question: Why was this action successful or unsuccessful?
What factors contributed to this outcome?

Answer (be concise, 2-3 sentences):"""

    def _build_improvement_prompt(
        self,
        agent_id: str,
        strategy: str,
        outcomes: list,
    ) -> str:
        """Build prompt for improvement suggestion.

        Args:
            agent_id: Agent ID
            strategy: Current strategy
            outcomes: Recent outcomes

        Returns:
            Prompt string
        """
        outcomes_str = json.dumps(outcomes, default=str)

        return f"""Agent Learning: Strategy Improvement
Agent: {agent_id}
Current Strategy: {strategy}
Recent Outcomes: {outcomes_str}

Question: Based on these outcomes, what specific improvements
should this agent make to its strategy?

Answer (be concrete and actionable, 2-3 sentences):"""

    def _build_pattern_analysis_prompt(
        self,
        pattern_description: str,
        examples: list,
    ) -> str:
        """Build prompt for pattern analysis.

        Args:
            pattern_description: Pattern description
            examples: Examples of pattern

        Returns:
            Prompt string
        """
        examples_str = json.dumps(examples, default=str)

        return f"""Pattern Analysis
Pattern: {pattern_description}
Examples: {examples_str}

Question: What is the underlying cause of this pattern?
How can we prevent or optimize for it?

Answer (be practical, 2-3 sentences):"""

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()


# Global LLM client instance
_llm_client: Optional[LocalLLMClient] = None


async def initialize_llm_client(base_url: str = LLM_BASE_URL) -> LocalLLMClient:
    """Initialize global LLM client.

    Args:
        base_url: URL of local LLM server

    Returns:
        Initialized LLM client
    """
    global _llm_client
    _llm_client = LocalLLMClient(base_url=base_url)
    await _llm_client.health_check()
    logger.info("LLMClient: Initialized")
    return _llm_client


async def get_llm_client() -> LocalLLMClient:
    """Get global LLM client instance.

    Returns:
        LLM client (creates if needed)
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = LocalLLMClient()
    return _llm_client
