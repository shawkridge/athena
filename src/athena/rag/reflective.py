"""Self-reflective RAG with iterative refinement and critique."""

import logging
from typing import Optional

from ..core.models import MemorySearchResult
from ..memory.search import SemanticSearch
from .llm_client import LLMClient

logger = logging.getLogger(__name__)


class ReflectiveRAG:
    """Self-reflective iterative retrieval with LLM critique.

    Implements a critique-and-refine loop:
    1. Retrieve initial documents
    2. LLM critiques: "Do these answer the query?"
    3. If insufficient, refine query and retrieve more
    4. Repeat until confident or max iterations
    """

    def __init__(self, search: SemanticSearch, llm_client: LLMClient):
        """Initialize reflective RAG.

        Args:
            search: Semantic search instance for retrieval
            llm_client: LLM client for critique and refinement
        """
        self.search = search
        self.llm = llm_client

    def retrieve(
        self,
        query: str,
        project_id: int,
        k: int = 5,
        max_iterations: int = 3,
        confidence_threshold: float = 0.8,
        candidate_multiplier: int = 2,
    ) -> list[MemorySearchResult]:
        """Iterative retrieval with self-critique.

        Args:
            query: User query
            project_id: Project ID
            k: Number of final results to return
            max_iterations: Maximum refinement iterations
            confidence_threshold: Stop when confidence exceeds this (0-1)
            candidate_multiplier: Get k*multiplier candidates per iteration

        Returns:
            Best search results after iterative refinement

        Examples:
            >>> reflective = ReflectiveRAG(search, llm_client)
            >>> results = reflective.retrieve(
            ...     "What's the JWT token expiry?",
            ...     project_id=1,
            ...     max_iterations=3
            ... )
            >>> # Returns results after critique loop
        """
        all_results = []
        current_query = query
        iteration_info = []

        logger.info(
            f"Starting reflective retrieval: query='{query}', "
            f"max_iterations={max_iterations}, threshold={confidence_threshold}"
        )

        for iteration in range(max_iterations):
            logger.debug(f"Iteration {iteration + 1}/{max_iterations}")
            logger.debug(f"Current query: '{current_query}'")

            # Retrieve with current query
            results = self.search.recall(
                current_query,
                project_id,
                k=k * candidate_multiplier,
                min_similarity=0.2,  # Lower threshold for broader search
            )

            logger.info(f"Retrieved {len(results)} candidates")
            all_results.extend(results)

            # Critique results
            try:
                critique = self._critique_results(query, results)

                iteration_info.append(
                    {
                        "iteration": iteration + 1,
                        "query": current_query,
                        "results_count": len(results),
                        "confidence": critique["confidence"],
                        "should_stop": critique["should_stop"],
                        "missing_info": critique.get("missing_info"),
                    }
                )

                logger.info(
                    f"Critique: confidence={critique['confidence']:.2f}, "
                    f"should_stop={critique['should_stop']}"
                )

                # Check stopping conditions
                if critique["should_stop"] or critique["confidence"] >= confidence_threshold:
                    logger.info(
                        f"Stopping after {iteration + 1} iterations "
                        f"(confidence: {critique['confidence']:.2f})"
                    )
                    break

                # Refine query for next iteration (if not last iteration)
                if iteration < max_iterations - 1:
                    if critique.get("missing_info"):
                        current_query = self._refine_query(query, critique)
                        logger.info(f"Refined query: '{current_query}'")
                    else:
                        logger.info("No missing info specified, keeping original query")
                        break

            except Exception as e:
                logger.error(f"Critique failed on iteration {iteration + 1}: {e}")
                # Continue with what we have
                break

        # Deduplicate and return top-k
        unique_results = self._deduplicate(all_results)
        final_results = unique_results[:k]

        # Add iteration metadata to results
        for result in final_results:
            if result.metadata is None:
                result.metadata = {}
            result.metadata["reflective_iterations"] = len(iteration_info)
            result.metadata["iteration_info"] = iteration_info

        logger.info(
            f"Reflective retrieval complete: {len(final_results)} results "
            f"after {len(iteration_info)} iterations"
        )

        return final_results

    def _critique_results(self, original_query: str, results: list[MemorySearchResult]) -> dict:
        """LLM critiques retrieval results.

        Args:
            original_query: Original user query
            results: Retrieved documents to critique

        Returns:
            Dict with keys:
                - should_stop: bool - whether to stop iterating
                - confidence: float - confidence that query is answered (0-1)
                - missing_info: str - what information is still needed
        """
        if not results:
            return {
                "should_stop": False,
                "confidence": 0.0,
                "missing_info": "No documents retrieved, need different search approach",
            }

        # Format documents for prompt (limit to top 5 for conciseness)
        docs_text = "\n\n".join(
            [
                f"Document {i+1} (similarity: {r.similarity:.2f}):\n{r.memory.content[:300]}..."
                for i, r in enumerate(results[:5])
            ]
        )

        prompt = f"""Evaluate whether these retrieved documents answer the user's query.

Query: {original_query}

Retrieved documents:
{docs_text}

Evaluate:
1. Do these documents answer the query? (yes/no)
2. How confident are you that the query is answered? (0.0 = not at all, 1.0 = completely)
3. What key information is still missing? (or "none" if query is answered)

Respond in this exact format:
ANSWERS: yes/no
CONFIDENCE: 0.X
MISSING: brief description or "none"

Be concise and direct."""

        try:
            response = self.llm.generate(
                prompt, max_tokens=150, temperature=0.3  # Low temp for consistent evaluation
            )

            # Parse response
            critique = self._parse_critique_response(response)
            return critique

        except Exception as e:
            logger.error(f"Failed to parse critique: {e}")
            # Conservative fallback: assume we need more info
            return {"should_stop": False, "confidence": 0.5, "missing_info": None}

    def _parse_critique_response(self, response: str) -> dict:
        """Parse LLM critique response.

        Args:
            response: Raw LLM response

        Returns:
            Parsed critique dict
        """
        response_lower = response.lower()

        # Parse ANSWERS
        answers_line = ""
        for line in response.split("\n"):
            if "answers:" in line.lower():
                answers_line = line
                break

        answers_query = "yes" in answers_line.lower() if answers_line else False

        # Parse CONFIDENCE
        confidence = 0.5  # Default
        for line in response.split("\n"):
            if "confidence:" in line.lower():
                try:
                    # Extract number after "confidence:"
                    conf_str = line.split(":", 1)[1].strip()
                    confidence = float(conf_str)
                    confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
                except (ValueError, IndexError):
                    pass
                break

        # Parse MISSING
        missing_info = None
        for line in response.split("\n"):
            if "missing:" in line.lower():
                missing_str = line.split(":", 1)[1].strip()
                if missing_str and missing_str.lower() not in ["none", "nothing"]:
                    missing_info = missing_str
                break

        # Determine should_stop
        should_stop = answers_query and confidence > 0.7

        return {
            "should_stop": should_stop,
            "confidence": confidence,
            "missing_info": missing_info,
        }

    def _refine_query(self, original_query: str, critique: dict) -> str:
        """Refine query based on critique feedback.

        Args:
            original_query: Original query
            critique: Critique dict with missing_info

        Returns:
            Refined query string
        """
        missing_info = critique.get("missing_info")
        if not missing_info:
            return original_query

        prompt = f"""The user's original query was not fully answered. Refine the query to specifically ask for the missing information.

Original query: {original_query}

Missing information: {missing_info}

Generate a refined query that specifically asks for the missing information while preserving the original intent.

Refined query:"""

        try:
            refined = self.llm.generate(
                prompt, max_tokens=100, temperature=0.5  # Moderate temp for creativity
            )
            return refined.strip()
        except Exception as e:
            logger.error(f"Query refinement failed: {e}")
            return original_query

    def _deduplicate(self, results: list[MemorySearchResult]) -> list[MemorySearchResult]:
        """Remove duplicate memories from results.

        Args:
            results: List of search results (may contain duplicates)

        Returns:
            Deduplicated results, sorted by similarity, with updated ranks
        """
        if not results:
            return []

        # Track seen memory IDs
        seen = set()
        unique = []

        for result in results:
            if result.memory.id not in seen:
                seen.add(result.memory.id)
                unique.append(result)

        # Sort by similarity (descending)
        unique.sort(key=lambda x: x.similarity, reverse=True)

        # Update ranks
        for rank, result in enumerate(unique, 1):
            result.rank = rank

        return unique


class ReflectiveRAGConfig:
    """Configuration for self-reflective RAG."""

    # Enable/disable reflective RAG
    enabled: bool = True

    # Iteration control
    max_iterations: int = 3  # Maximum refinement iterations
    confidence_threshold: float = 0.8  # Stop when confidence exceeds this

    # Retrieval parameters
    candidate_multiplier: int = 2  # Get k*multiplier candidates per iteration
    min_similarity: float = 0.2  # Lower threshold for broader search

    # LLM parameters
    critique_max_tokens: int = 150
    critique_temperature: float = 0.3  # Low for consistent evaluation
    refine_max_tokens: int = 100
    refine_temperature: float = 0.5  # Moderate for creative refinement

    def __init__(self, **kwargs):
        """Initialize config with overrides.

        Args:
            **kwargs: Config options to override

        Examples:
            >>> config = ReflectiveRAGConfig(max_iterations=5)
            >>> config = ReflectiveRAGConfig(confidence_threshold=0.9)
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                logger.warning(f"Unknown reflective RAG config option: {key}")


def get_iteration_metrics(results: list[MemorySearchResult]) -> Optional[dict]:
    """Extract iteration metrics from reflective RAG results.

    Args:
        results: Results from reflective retrieve()

    Returns:
        Dict with metrics, or None if not reflective results

    Examples:
        >>> metrics = get_iteration_metrics(results)
        >>> if metrics:
        ...     print(f"Iterations: {metrics['total_iterations']}")
        ...     print(f"Final confidence: {metrics['final_confidence']:.2f}")
    """
    if not results or not results[0].metadata:
        return None

    metadata = results[0].metadata
    if "reflective_iterations" not in metadata:
        return None

    iteration_info = metadata.get("iteration_info", [])
    if not iteration_info:
        return None

    return {
        "total_iterations": len(iteration_info),
        "queries_used": [info["query"] for info in iteration_info],
        "confidences": [info["confidence"] for info in iteration_info],
        "final_confidence": iteration_info[-1]["confidence"] if iteration_info else 0.0,
        "stopped_early": len(iteration_info) < metadata.get("max_iterations", 3),
    }
