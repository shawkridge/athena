"""Query expansion for generating alternative query phrasings.

This module implements query expansion to generate multiple semantically similar
versions of a query, improving recall by capturing different ways users might
express the same information need.

Based on Airweave's query expansion pattern with Athena-specific adaptations.
"""

import logging
from functools import lru_cache
from typing import Optional

from pydantic import BaseModel, Field

from .llm_client import LLMClient

logger = logging.getLogger(__name__)


class QueryExpansions(BaseModel):
    """Container for expanded query alternatives."""

    original: str = Field(..., description="Original query")
    alternatives: list[str] = Field(
        default_factory=list, description="Alternative query phrasings"
    )
    total_variants: int = Field(0, description="Total number of variants (including original)")

    def all_queries(self) -> list[str]:
        """Get all queries including original.

        Returns:
            List of all queries (original + alternatives)
        """
        return [self.original] + self.alternatives

    def __len__(self) -> int:
        """Return total number of query variants."""
        return self.total_variants


class QueryExpansionConfig:
    """Configuration for query expansion."""

    # Enable/disable query expansion
    enabled: bool = True

    # Number of alternative phrasings to generate
    num_variants: int = 4

    # LLM parameters
    max_tokens: int = 200
    temperature: float = 0.7  # Higher temperature for diversity

    # Caching
    enable_cache: bool = True
    cache_size: int = 1000  # Number of queries to cache

    # Error handling
    fallback_on_error: bool = True  # Return original query if expansion fails

    def __init__(self, **kwargs):
        """Initialize config with overrides.

        Args:
            **kwargs: Config options to override

        Examples:
            >>> config = QueryExpansionConfig(num_variants=6)
            >>> config = QueryExpansionConfig(enabled=False)
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                logger.warning(f"Unknown query expansion config option: {key}")


class QueryExpander:
    """Generate alternative query phrasings for improved recall.

    The query expander uses an LLM to generate semantically similar but differently
    worded versions of a query. This improves recall by:
    1. Capturing synonyms and related terms
    2. Addressing vocabulary mismatch between query and documents
    3. Exploring different query formulations

    Examples:
        >>> from athena.rag.llm_client import create_llm_client
        >>> llm = create_llm_client("claude")
        >>> expander = QueryExpander(llm)
        >>> expanded = expander.expand("How do we handle authentication?")
        >>> print(expanded.alternatives)
        ['What authentication methods are used?',
         'How is user auth implemented?',
         'Authentication approach in the codebase?']
    """

    def __init__(self, llm_client: LLMClient, config: Optional[QueryExpansionConfig] = None):
        """Initialize query expander.

        Args:
            llm_client: LLM client for generating alternatives
            config: Configuration options (uses defaults if None)
        """
        self.llm = llm_client
        self.config = config or QueryExpansionConfig()
        logger.info(
            f"Initialized QueryExpander (variants={self.config.num_variants}, "
            f"cache={self.config.enable_cache})"
        )

    def expand(
        self, query: str, include_original: bool = True
    ) -> QueryExpansions:
        """Expand query into alternative phrasings.

        Args:
            query: Original query string
            include_original: Whether to include original query in results

        Returns:
            QueryExpansions object with original and alternatives

        Examples:
            >>> expanded = expander.expand("How to optimize database queries?")
            >>> for q in expanded.all_queries():
            ...     print(f"- {q}")
        """
        if not self.config.enabled:
            # Expansion disabled, return original only
            return QueryExpansions(
                original=query,
                alternatives=[],
                total_variants=1
            )

        try:
            # Generate alternatives (with caching if enabled)
            if self.config.enable_cache:
                alternatives = self._cached_generate_alternatives(query)
            else:
                alternatives = self._generate_alternatives(query)

            # Validate and deduplicate
            validated = self._validate_alternatives(query, alternatives)

            total = len(validated) + (1 if include_original else 0)

            logger.info(
                f"Expanded query into {len(validated)} alternatives "
                f"(total variants: {total})"
            )

            return QueryExpansions(
                original=query,
                alternatives=validated,
                total_variants=total
            )

        except Exception as e:
            logger.error(f"Query expansion failed: {e}")

            if self.config.fallback_on_error:
                # Graceful degradation: return original query
                logger.info("Falling back to original query")
                return QueryExpansions(
                    original=query,
                    alternatives=[],
                    total_variants=1
                )
            else:
                raise

    def _generate_alternatives(self, query: str) -> list[str]:
        """Generate alternative query phrasings using LLM.

        Args:
            query: Original query

        Returns:
            List of alternative phrasings (may contain duplicates/empty strings)
        """
        prompt = self._build_expansion_prompt(query)

        try:
            response = self.llm.generate(
                prompt=prompt,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )

            # Parse response into alternatives
            alternatives = self._parse_alternatives(response)

            logger.debug(
                f"Generated {len(alternatives)} raw alternatives for: '{query}'"
            )

            return alternatives

        except Exception as e:
            logger.error(f"Failed to generate alternatives: {e}")
            raise

    def _cached_generate_alternatives(self, query: str) -> list[str]:
        """Generate alternatives with caching.

        Uses functools.lru_cache to avoid regenerating expansions for
        frequently used queries.

        Args:
            query: Original query

        Returns:
            List of alternative phrasings
        """
        # Create a cached version of _generate_alternatives
        # Note: We can't use @lru_cache decorator directly on instance methods
        # with self reference, so we use a closure approach

        cache_key = query.strip().lower()

        # Check if we have a cache
        if not hasattr(self, "_expansion_cache"):
            self._expansion_cache = {}

        if cache_key in self._expansion_cache:
            logger.debug(f"Cache hit for query: '{query}'")
            return self._expansion_cache[cache_key]

        # Cache miss - generate and store
        alternatives = self._generate_alternatives(query)

        # Manage cache size
        if len(self._expansion_cache) >= self.config.cache_size:
            # Simple FIFO eviction (remove oldest)
            oldest_key = next(iter(self._expansion_cache))
            del self._expansion_cache[oldest_key]
            logger.debug(f"Evicted cache entry for: '{oldest_key}'")

        self._expansion_cache[cache_key] = alternatives
        logger.debug(f"Cached alternatives for: '{query}'")

        return alternatives

    def _build_expansion_prompt(self, query: str) -> str:
        """Build prompt for query expansion.

        Args:
            query: Original query

        Returns:
            Formatted prompt for LLM
        """
        num_variants = self.config.num_variants

        prompt = f"""Generate {num_variants} alternative ways to phrase this search query for a codebase.

Original query: {query}

Requirements:
1. Maintain the same information need and intent
2. Use different wording, synonyms, and sentence structures
3. Keep queries concise (1-2 sentences each)
4. Make each alternative meaningfully different
5. Focus on technical software engineering terms

Examples:
Query: "How do we handle authentication?"
Alternatives:
1. What authentication methods are used?
2. How is user auth implemented?
3. Authentication approach in the codebase?
4. User verification and login system?

Now generate {num_variants} alternatives for the query above.
List them as numbered items (1., 2., etc.):"""

        return prompt

    def _parse_alternatives(self, response: str) -> list[str]:
        """Parse LLM response into list of alternatives.

        Args:
            response: LLM response text

        Returns:
            List of alternative queries (may contain empty strings)
        """
        alternatives = []

        # Split by newlines and look for numbered items
        lines = response.strip().split("\n")

        for line in lines:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Remove numbering (1., 2), etc.) and quotes
            line = line.lstrip("0123456789.-) \t")
            line = line.strip('"\'')

            # Skip if still empty or too short
            if len(line) < 3:
                continue

            alternatives.append(line)

        return alternatives

    def _validate_alternatives(
        self, original: str, alternatives: list[str]
    ) -> list[str]:
        """Validate and deduplicate alternative queries.

        Removes:
        - Empty strings
        - Exact duplicates (case-insensitive)
        - Matches to original query (case-insensitive)

        Args:
            original: Original query
            alternatives: List of alternative queries

        Returns:
            Validated list of unique alternatives
        """
        original_lower = original.strip().lower()
        seen = set()
        validated = []

        for alt in alternatives:
            alt_stripped = alt.strip()

            # Skip empty strings
            if not alt_stripped:
                continue

            alt_lower = alt_stripped.lower()

            # Skip if matches original
            if alt_lower == original_lower:
                logger.debug(f"Skipping alternative that matches original: '{alt_stripped}'")
                continue

            # Skip duplicates
            if alt_lower in seen:
                logger.debug(f"Skipping duplicate alternative: '{alt_stripped}'")
                continue

            seen.add(alt_lower)
            validated.append(alt_stripped)

        logger.debug(
            f"Validated {len(validated)}/{len(alternatives)} alternatives "
            f"(removed {len(alternatives) - len(validated)} duplicates/empties)"
        )

        return validated

    def clear_cache(self):
        """Clear the expansion cache.

        Useful for testing or when you want to force regeneration.
        """
        if hasattr(self, "_expansion_cache"):
            cache_size = len(self._expansion_cache)
            self._expansion_cache.clear()
            logger.info(f"Cleared expansion cache ({cache_size} entries)")


def batch_expand(
    expander: QueryExpander,
    queries: list[str],
    include_original: bool = True,
) -> list[QueryExpansions]:
    """Expand multiple queries in batch.

    Args:
        expander: QueryExpander instance
        queries: List of queries to expand
        include_original: Include original query in results

    Returns:
        List of QueryExpansions objects

    Note:
        Currently processes sequentially. Could be parallelized for better performance
        with concurrent LLM requests.
    """
    expanded = []

    for i, query in enumerate(queries):
        logger.debug(f"Expanding query {i+1}/{len(queries)}: '{query}'")
        result = expander.expand(query, include_original=include_original)
        expanded.append(result)

    logger.info(
        f"Batch expanded {len(queries)} queries into "
        f"{sum(len(e) for e in expanded)} total variants"
    )

    return expanded
