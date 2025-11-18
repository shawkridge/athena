"""Advanced RAG (Retrieval-Augmented Generation) strategies for code search.

Implements:
- Self-RAG: Self-retrieval-augmented generation with relevance evaluation
- CRAG: Corrective RAG with adaptive retrieval and correction
- Adaptive RAG: Combines both strategies based on query characteristics
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum

from .models import SearchResult

logger = logging.getLogger(__name__)


class RelevanceLevel(Enum):
    """Relevance levels for retrieved documents."""

    HIGHLY_RELEVANT = "highly_relevant"
    RELEVANT = "relevant"
    PARTIALLY_RELEVANT = "partially_relevant"
    NOT_RELEVANT = "not_relevant"


class ConfidenceLevel(Enum):
    """Confidence levels for self-evaluation."""

    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


@dataclass
class RetrievedDocument:
    """A retrieved code unit with metadata."""

    result: SearchResult
    relevance: RelevanceLevel
    confidence: float  # 0.0 to 1.0


@dataclass
class RetrievalDecision:
    """Decision about whether to retrieve documents."""

    should_retrieve: bool
    confidence: float
    reason: str


class SelfRAG:
    """Self-Retrieval-Augmented Generation for code search.

    The system decides:
    1. Whether to retrieve documents
    2. Which retrieved documents are relevant
    3. Whether the answer can be formed from retrieved documents
    """

    def __init__(self, search_engine):
        """Initialize Self-RAG.

        Args:
            search_engine: TreeSitterCodeSearch instance
        """
        self.search_engine = search_engine

    def should_retrieve(self, query: str) -> RetrievalDecision:
        """Decide whether to retrieve documents for this query.

        Heuristics:
        - Specific queries (longer, more detailed) likely need retrieval
        - Vague queries might be answerable from knowledge
        - Technical terms indicate need for code context

        Args:
            query: Search query

        Returns:
            RetrievalDecision with confidence and reasoning
        """
        # Analyze query characteristics
        words = query.split()
        is_specific = len(words) >= 2  # Lowered from > 2
        has_technical_terms = any(
            term in query.lower()
            for term in ["function", "class", "method", "interface", "implement", "extend"]
        )
        is_long = len(query) > 15  # Lowered from > 20

        # Check for code-like terms (function names, patterns)
        has_code_pattern = any(char in query for char in ["(", ")", "_", "-", "/"]) or any(
            term in query.lower()
            for term in ["authenticate", "validate", "process", "handle", "find", "get", "set"]
        )

        confidence = 0.5  # Base confidence for any non-empty query
        reason = ""

        if has_code_pattern:
            confidence = 0.85
            reason = f"Code-like pattern detected (confidence: {confidence:.2f})"
        elif is_specific or has_technical_terms or is_long:
            confidence = 0.75 if is_specific else 0.65
            if has_technical_terms:
                confidence = min(confidence + 0.1, 1.0)
            reason = f"Specific query needing code context (confidence: {confidence:.2f})"
        else:
            confidence = 0.55
            reason = f"General query - attempting retrieval (confidence: {confidence:.2f})"

        return RetrievalDecision(True, confidence, reason)

    def evaluate_relevance(self, query: str, result: SearchResult) -> Tuple[RelevanceLevel, float]:
        """Evaluate relevance of a retrieved document.

        Combines multiple signals:
        - Search relevance score from the engine
        - Query-result overlap
        - Code unit type matching

        Args:
            query: Original search query
            result: SearchResult from search engine

        Returns:
            Tuple of (RelevanceLevel, confidence)
        """
        relevance_score = result.relevance
        query_terms = set(query.lower().split())
        unit_name = result.unit.name.lower()
        unit_doc = (result.unit.docstring or "").lower()

        # Calculate term overlap
        term_overlap = len(query_terms & set(unit_name.split("_")))
        term_overlap_ratio = term_overlap / len(query_terms) if query_terms else 0

        # Determine relevance level based on score and term overlap
        if relevance_score > 0.5 and term_overlap_ratio > 0.3:
            relevance = RelevanceLevel.HIGHLY_RELEVANT
            confidence = min(relevance_score + 0.1, 1.0)
        elif relevance_score > 0.3 and term_overlap_ratio > 0.1:
            relevance = RelevanceLevel.RELEVANT
            confidence = relevance_score
        elif relevance_score > 0.1 or term_overlap_ratio > 0.0:
            relevance = RelevanceLevel.PARTIALLY_RELEVANT
            confidence = max(relevance_score, term_overlap_ratio)
        else:
            relevance = RelevanceLevel.NOT_RELEVANT
            confidence = relevance_score

        return relevance, confidence

    def retrieve_and_evaluate(self, query: str, limit: int = 10) -> List[RetrievedDocument]:
        """Retrieve documents and evaluate their relevance.

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of RetrievedDocument with relevance scores
        """
        # Decide whether to retrieve
        decision = self.should_retrieve(query)
        logger.debug(f"Retrieval decision: {decision.should_retrieve} - {decision.reason}")

        # Retrieve documents (use lower threshold, we'll filter with relevance evaluation)
        results = self.search_engine.search(query, top_k=limit * 2, min_score=0.0)

        # Evaluate relevance of each
        retrieved = []
        for result in results:
            relevance, confidence = self.evaluate_relevance(query, result)

            # Only keep relevant documents
            if relevance != RelevanceLevel.NOT_RELEVANT:
                retrieved.append(
                    RetrievedDocument(result=result, relevance=relevance, confidence=confidence)
                )

        # Sort by relevance
        retrieved.sort(key=lambda x: (x.relevance.value, x.confidence), reverse=True)

        return retrieved[:limit]


class CorrectiveRAG:
    """Corrective RAG for code search.

    Retrieves documents and evaluates them. If retrieval is insufficient,
    tries alternative queries or different search strategies.
    """

    def __init__(self, search_engine, self_rag: Optional[SelfRAG] = None):
        """Initialize Corrective RAG.

        Args:
            search_engine: TreeSitterCodeSearch instance
            self_rag: Optional SelfRAG instance for relevance evaluation
        """
        self.search_engine = search_engine
        self.self_rag = self_rag or SelfRAG(search_engine)

    def _generate_alternative_queries(self, query: str) -> List[str]:
        """Generate alternative queries when initial retrieval fails.

        Strategies:
        - Keyword extraction and re-weighting
        - Synonym expansion
        - Type-specific queries
        - Related concept queries

        Args:
            query: Original query

        Returns:
            List of alternative queries
        """
        alternatives = []
        terms = query.split()

        # Strategy 1: Focus on main terms (remove modifiers)
        main_terms = [t for t in terms if len(t) > 3]
        if main_terms and len(main_terms) < len(terms):
            alternatives.append(" ".join(main_terms))

        # Strategy 2: Add code-specific keywords
        for keyword in ["function", "class", "method", "handler"]:
            if keyword not in query.lower():
                alternatives.append(f"{query} {keyword}")

        # Strategy 3: Type-specific searches
        for unit_type in ["function", "class"]:
            if unit_type not in query.lower():
                alternatives.append(f"{query} {unit_type}")

        # Strategy 4: Dependency-focused
        for term in ["dependency", "dependency analysis", "call"]:
            if term not in query.lower():
                alternatives.append(f"{query} {term}")

        return alternatives[:3]  # Limit to top 3

    def retrieve_with_correction(
        self, query: str, limit: int = 10, max_iterations: int = 3
    ) -> List[RetrievedDocument]:
        """Retrieve documents with correction if needed.

        Process:
        1. Initial retrieval and evaluation
        2. If insufficient relevant docs, generate alternative queries
        3. Retry with alternative queries
        4. Combine and deduplicate results

        Args:
            query: Search query
            limit: Maximum results to return
            max_iterations: Maximum retrieval attempts

        Returns:
            List of RetrievedDocument
        """
        all_retrieved = []
        seen_units = set()

        current_query = query
        for iteration in range(max_iterations):
            # Retrieve and evaluate (use lower threshold, we'll filter with relevance evaluation)
            results = self.search_engine.search(current_query, top_k=limit * 2, min_score=0.0)

            # Evaluate relevance
            for result in results:
                if result.unit.id in seen_units:
                    continue

                relevance, confidence = self.self_rag.evaluate_relevance(current_query, result)

                if relevance != RelevanceLevel.NOT_RELEVANT:
                    all_retrieved.append(
                        RetrievedDocument(result=result, relevance=relevance, confidence=confidence)
                    )
                    seen_units.add(result.unit.id)

            # Check if we have enough relevant results
            highly_relevant = sum(
                1 for r in all_retrieved if r.relevance == RelevanceLevel.HIGHLY_RELEVANT
            )

            if highly_relevant >= (limit // 2):
                logger.debug(f"Retrieved sufficient results in iteration {iteration + 1}")
                break

            # Generate alternative query for next iteration
            if iteration < max_iterations - 1:
                alternatives = self._generate_alternative_queries(current_query)
                if alternatives:
                    current_query = alternatives[iteration % len(alternatives)]
                    logger.debug(f"Trying alternative query: {current_query}")

        # Sort by relevance and confidence
        all_retrieved.sort(key=lambda x: (x.relevance.value, x.confidence), reverse=True)

        return all_retrieved[:limit]


class AdaptiveRAG:
    """Adaptive RAG that combines Self-RAG and Corrective RAG.

    Chooses strategy based on:
    - Query characteristics
    - Initial retrieval quality
    - Result composition
    """

    def __init__(self, search_engine):
        """Initialize Adaptive RAG.

        Args:
            search_engine: TreeSitterCodeSearch instance
        """
        self.search_engine = search_engine
        self.self_rag = SelfRAG(search_engine)
        self.corrective_rag = CorrectiveRAG(search_engine, self.self_rag)

    def _analyze_query_complexity(self, query: str) -> Tuple[str, float]:
        """Analyze query complexity to determine strategy.

        Args:
            query: Search query

        Returns:
            Tuple of (complexity level, confidence)
        """
        words = query.split()
        has_specifics = any(
            term in query.lower()
            for term in ["function", "class", "interface", "method", "handler"]
        )
        has_logic = any(
            term in query.lower()
            for term in ["authenticate", "validate", "process", "handle", "convert"]
        )

        if len(words) > 3 and (has_specifics or has_logic):
            return "high", 0.8
        elif len(words) > 2:
            return "medium", 0.6
        else:
            return "low", 0.4

    def retrieve(
        self, query: str, limit: int = 10, prefer_strategy: Optional[str] = None
    ) -> List[RetrievedDocument]:
        """Adaptively retrieve documents.

        Args:
            query: Search query
            limit: Maximum results to return
            prefer_strategy: "self" for Self-RAG, "corrective" for Corrective RAG, None for auto

        Returns:
            List of RetrievedDocument
        """
        # Analyze query
        complexity, confidence = self._analyze_query_complexity(query)

        # Choose strategy
        if prefer_strategy == "self":
            strategy = "self"
        elif prefer_strategy == "corrective":
            strategy = "corrective"
        else:
            # Auto selection based on complexity
            strategy = "corrective" if complexity in ("high", "medium") else "self"

        logger.debug(
            f"Query complexity: {complexity}, confidence: {confidence:.2f}, "
            f"using {strategy}-RAG"
        )

        # Execute retrieval
        if strategy == "self":
            return self.self_rag.retrieve_and_evaluate(query, limit)
        else:
            return self.corrective_rag.retrieve_with_correction(query, limit)

    def get_strategy_recommendation(self, query: str) -> dict:
        """Get recommendation for which strategy to use.

        Args:
            query: Search query

        Returns:
            Dictionary with strategy recommendation and reasoning
        """
        decision = self.self_rag.should_retrieve(query)
        complexity, conf = self._analyze_query_complexity(query)

        recommendation = {
            "recommended_strategy": "corrective" if complexity in ("high", "medium") else "self",
            "should_retrieve": decision.should_retrieve,
            "query_complexity": complexity,
            "confidence": max(decision.confidence, conf),
            "reasoning": decision.reason,
        }

        return recommendation
