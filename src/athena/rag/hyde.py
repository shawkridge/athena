"""HyDE (Hypothetical Document Embeddings) for improved retrieval."""

import logging

from ..core.models import MemorySearchResult
from ..memory.search import SemanticSearch
from .llm_client import LLMClient

logger = logging.getLogger(__name__)


class HyDERetriever:
    """Hypothetical Document Embeddings for bridging query-document gaps."""

    def __init__(self, search: SemanticSearch, llm_client: LLMClient):
        """Initialize HyDE retriever.

        Args:
            search: Semantic search instance
            llm_client: LLM client for generating hypothetical answers
        """
        self.search = search
        self.llm = llm_client

    def retrieve(
        self,
        query: str,
        project_id: int,
        k: int = 5,
        use_hyde: bool = True,
        fallback_on_error: bool = True,
    ) -> list[MemorySearchResult]:
        """Retrieve memories using HyDE if enabled.

        Args:
            query: User query
            project_id: Project ID
            k: Number of results
            use_hyde: Enable HyDE (False for fallback)
            fallback_on_error: Fallback to basic search on HyDE failure

        Returns:
            Search results

        Examples:
            >>> hyde = HyDERetriever(search, llm_client)
            >>> results = hyde.retrieve("How do we handle auth?", project_id=1)
            >>> for result in results:
            ...     print(f"{result.memory.content} (score: {result.similarity:.2f})")
        """
        if not use_hyde:
            # Direct passthrough to basic search
            return self.search.recall(query, project_id, k)

        try:
            # Generate hypothetical answer
            hypothetical = self._generate_hypothetical_answer(query)
            logger.info(f"HyDE generated hypothetical ({len(hypothetical)} chars)")
            logger.debug(f"Hypothetical: {hypothetical[:200]}...")

            # Search using answer embedding (get more candidates for diversity)
            results = self.search.recall(hypothetical, project_id, k=k * 2, min_similarity=0.2)

            # Return top-k
            return results[:k]

        except Exception as e:
            logger.warning(f"HyDE failed: {e}")

            if fallback_on_error:
                # Graceful degradation to basic search
                logger.info("Falling back to basic search")
                return self.search.recall(query, project_id, k)
            else:
                raise

    def _generate_hypothetical_answer(
        self, query: str, max_tokens: int = 200, temperature: float = 0.7
    ) -> str:
        """Generate hypothetical answer using LLM.

        Args:
            query: User query
            max_tokens: Maximum answer length
            temperature: Sampling temperature (higher = more creative)

        Returns:
            Hypothetical answer text

        Note:
            Uses moderate temperature (0.7) to generate plausible but creative
            hypothetical answers that might match actual stored memories.
        """
        prompt = f"""You are answering a question about a software project's codebase.

Question: {query}

Provide a direct, factual answer as if you had access to the project's documentation.
Be specific and technical. Do not say "I don't know" - make reasonable assumptions based on common software engineering practices.

Answer (2-3 sentences):"""

        try:
            response = self.llm.generate(
                prompt=prompt, max_tokens=max_tokens, temperature=temperature
            )
            return response.strip()
        except Exception as e:
            logger.error(f"Failed to generate hypothetical answer: {e}")
            raise


class HyDEConfig:
    """Configuration for HyDE retrieval."""

    # Enable/disable HyDE
    enabled: bool = True

    # Hypothetical answer generation
    max_tokens: int = 200
    temperature: float = 0.7

    # Retrieval parameters
    candidate_multiplier: int = 2  # Get k*2 candidates, return top k
    min_similarity: float = 0.2  # Lower threshold for initial retrieval

    # Error handling
    fallback_on_error: bool = True  # Fall back to basic search on error

    def __init__(self, **kwargs):
        """Initialize config with overrides."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                logger.warning(f"Unknown HyDE config option: {key}")
