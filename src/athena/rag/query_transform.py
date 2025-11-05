"""Query transformation for conversation-aware retrieval."""

import logging
import re
from typing import Optional

from .llm_client import LLMClient

logger = logging.getLogger(__name__)


class QueryTransformer:
    """Transform queries to be self-contained using conversation context."""

    def __init__(self, llm_client: LLMClient):
        """Initialize query transformer.

        Args:
            llm_client: LLM client for query rewriting
        """
        self.llm = llm_client

    def transform(
        self,
        query: str,
        conversation_history: Optional[list[dict]] = None,
        max_history_turns: int = 3,
    ) -> str:
        """Transform query to be self-contained.

        Args:
            query: User query (possibly with pronouns/implicit references)
            conversation_history: Recent messages
                Format: [{"role": "user"|"assistant", "content": str}, ...]
            max_history_turns: Maximum conversation turns to consider

        Returns:
            Transformed self-contained query

        Examples:
            >>> transformer = QueryTransformer(llm_client)
            >>> history = [
            ...     {"role": "user", "content": "How do we handle authentication?"},
            ...     {"role": "assistant", "content": "We use JWT tokens..."},
            ... ]
            >>> query = "What's the expiry for those?"
            >>> transformed = transformer.transform(query, history)
            >>> # Returns: "What's the JWT token expiry for authentication?"
        """
        # Quick check: does query need transformation?
        if not conversation_history or len(conversation_history) == 0:
            logger.debug("No conversation history, returning query as-is")
            return query

        if not self._needs_transformation(query):
            logger.debug("Query doesn't need transformation")
            return query

        # Limit history to recent turns
        recent_history = conversation_history[-max_history_turns * 2 :] if conversation_history else []

        try:
            # Build prompt with context
            context_str = self._format_history(recent_history)

            prompt = f"""Rewrite this query to be self-contained, resolving any pronouns or implicit references using the conversation history.

Conversation history:
{context_str}

Current query: {query}

Rewrite the query so it can be understood without the conversation context. Replace pronouns (it, that, those, etc.) with their actual referents. Make implicit references explicit.

Rewritten query (self-contained):"""

            transformed = self.llm.generate(
                prompt=prompt, max_tokens=100, temperature=0.3  # Low temp for consistency
            )

            result = transformed.strip()
            logger.info(f"Transformed query: '{query}' → '{result}'")
            return result

        except Exception as e:
            logger.error(f"Query transformation failed: {e}")
            # Fallback to original query on error
            return query

    def _needs_transformation(self, query: str) -> bool:
        """Check if query contains pronouns or implicit references.

        Args:
            query: User query

        Returns:
            True if transformation likely needed
        """
        query_lower = query.lower()

        # Pronouns that reference previous context
        pronouns = [
            r"\bit\b",
            r"\bthat\b",
            r"\bthis\b",
            r"\bthey\b",
            r"\bthem\b",
            r"\bthose\b",
            r"\bthese\b",
            r"\bhe\b",
            r"\bshe\b",
            r"\bhis\b",
            r"\bher\b",
            r"\bits\b",
            r"\btheir\b",
        ]

        # Implicit references
        implicit_refs = [
            r"the function",
            r"the class",
            r"the file",
            r"the method",
            r"the variable",
            r"the code",
            r"previous",
            r"earlier",
            r"mentioned",
            r"above",
            r"same",
        ]

        # Check for pronouns
        for pattern in pronouns:
            if re.search(pattern, query_lower):
                return True

        # Check for implicit references
        for pattern in implicit_refs:
            if pattern in query_lower:
                return True

        return False

    def _format_history(self, history: list[dict]) -> str:
        """Format conversation history for prompt.

        Args:
            history: List of conversation messages

        Returns:
            Formatted history string
        """
        if not history:
            return "(no history)"

        lines = []
        for msg in history:
            role = msg.get("role", "unknown").capitalize()
            content = msg.get("content", "")

            # Truncate very long messages
            if len(content) > 300:
                content = content[:300] + "..."

            lines.append(f"{role}: {content}")

        return "\n".join(lines)


class QueryTransformConfig:
    """Configuration for query transformation."""

    # Enable/disable transformation
    enabled: bool = True

    # Conversation context
    max_history_turns: int = 3  # Number of turns to consider (user + assistant = 1 turn)

    # Query analysis
    check_pronouns: bool = True  # Check for pronouns before transforming
    check_implicit_refs: bool = True  # Check for implicit references

    # LLM parameters
    max_tokens: int = 100  # Max tokens for rewritten query
    temperature: float = 0.3  # Low temperature for consistency

    # Fallback behavior
    fallback_on_error: bool = True  # Return original query if transformation fails

    def __init__(self, **kwargs):
        """Initialize config with overrides.

        Args:
            **kwargs: Config options to override

        Examples:
            >>> config = QueryTransformConfig(max_history_turns=5)
            >>> config = QueryTransformConfig(temperature=0.1)
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                logger.warning(f"Unknown query transform config option: {key}")


def batch_transform(
    transformer: QueryTransformer,
    queries: list[str],
    conversation_histories: list[list[dict]],
) -> list[str]:
    """Transform multiple queries in batch.

    Args:
        transformer: QueryTransformer instance
        queries: List of queries to transform
        conversation_histories: List of conversation histories (one per query)

    Returns:
        List of transformed queries

    Note:
        Currently processes sequentially. Could be parallelized for better performance.
    """
    if len(queries) != len(conversation_histories):
        raise ValueError(
            f"Number of queries ({len(queries)}) must match "
            f"number of histories ({len(conversation_histories)})"
        )

    transformed = []
    for i, (query, history) in enumerate(zip(queries, conversation_histories)):
        logger.debug(f"Transforming query {i+1}/{len(queries)}")
        result = transformer.transform(query, history)
        transformed.append(result)

    return transformed
