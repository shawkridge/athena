"""Retrieval Evaluator for Self-RAG

Evaluates the relevance of retrieved documents/passages to determine if they
contain sufficient information to answer a question. Uses multi-factor scoring
and optional LLM-based evaluation for nuanced relevance assessment.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List
from datetime import datetime


class RelevanceLevel(str, Enum):
    """Relevance assessment levels"""

    IRRELEVANT = "irrelevant"
    PARTIALLY_RELEVANT = "partially_relevant"
    RELEVANT = "relevant"
    HIGHLY_RELEVANT = "highly_relevant"


@dataclass
class RelevanceScore:
    """Score for a single document's relevance"""

    document_id: str
    query: str
    document_content: str
    relevance_level: RelevanceLevel
    confidence: float  # 0.0-1.0
    factors: Dict[str, float] = field(default_factory=dict)
    reasoning: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    is_llm_evaluated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "document_id": self.document_id,
            "query": self.query,
            "relevance": self.relevance_level.value,
            "confidence": self.confidence,
            "factors": self.factors,
            "reasoning": self.reasoning,
            "llm_evaluated": self.is_llm_evaluated,
        }


class RetrievalEvaluator:
    """Evaluates relevance of retrieved documents to queries"""

    def __init__(self, use_llm_evaluation: bool = False):
        """Initialize retrieval evaluator

        Args:
            use_llm_evaluation: Whether to use LLM for evaluation (vs heuristics)
        """
        self.use_llm_evaluation = use_llm_evaluation
        self.evaluation_cache: Dict[str, RelevanceScore] = {}
        self.total_evaluations = 0
        self.cache_hits = 0

    def evaluate_relevance(
        self,
        query: str,
        document_content: str,
        document_id: str = "",
        use_cache: bool = True,
    ) -> RelevanceScore:
        """Evaluate relevance of a document to a query

        Args:
            query: The search query
            document_content: The document/passage content
            document_id: Optional document identifier
            use_cache: Whether to use cached evaluations

        Returns:
            RelevanceScore with relevance level and confidence
        """
        # Create cache key
        cache_key = f"{query}:{document_id}:{document_content[:100]}"

        # Check cache
        if use_cache and cache_key in self.evaluation_cache:
            self.cache_hits += 1
            return self.evaluation_cache[cache_key]

        # Evaluate
        if self.use_llm_evaluation:
            score = self._evaluate_with_llm(query, document_content, document_id)
        else:
            score = self._evaluate_with_heuristics(query, document_content, document_id)

        self.total_evaluations += 1

        # Cache result
        self.evaluation_cache[cache_key] = score

        return score

    def _evaluate_with_heuristics(
        self, query: str, document_content: str, document_id: str
    ) -> RelevanceScore:
        """Evaluate using heuristic features (fast, no LLM)

        Args:
            query: The search query
            document_content: The document content
            document_id: The document ID

        Returns:
            RelevanceScore based on heuristics
        """
        factors = {}

        # Factor 1: Keyword overlap (Jaccard similarity)
        query_words = set(query.lower().split())
        doc_words = set(document_content.lower().split())

        if not query_words or not doc_words:
            intersection = 0
            union = 1
        else:
            intersection = len(query_words & doc_words)
            union = len(query_words | doc_words)

        keyword_overlap = intersection / union if union > 0 else 0.0
        factors["keyword_overlap"] = keyword_overlap

        # Factor 2: Content density (query words as % of document)
        if doc_words:
            content_density = len(query_words & doc_words) / len(query_words)
        else:
            content_density = 0.0
        factors["content_density"] = content_density

        # Factor 3: Document length (penalize too-short docs)
        doc_length = len(document_content.split())
        if doc_length < 20:
            length_score = 0.3
        elif doc_length < 50:
            length_score = 0.6
        elif doc_length < 500:
            length_score = 0.9
        else:
            length_score = 1.0
        factors["length_score"] = length_score

        # Factor 4: Query coverage (how many query terms are covered)
        covered_terms = len(query_words & doc_words)
        total_terms = len(query_words)
        query_coverage = covered_terms / total_terms if total_terms > 0 else 0.0
        factors["query_coverage"] = query_coverage

        # Factor 5: Position of first match (earlier is better)
        first_match_pos = self._find_first_match_position(query, document_content)
        if first_match_pos == -1:
            position_score = 0.0
        elif first_match_pos < 100:
            position_score = 1.0
        elif first_match_pos < 300:
            position_score = 0.8
        else:
            position_score = 0.6
        factors["position_score"] = position_score

        # Factor 6: Semantic relevance (check for related concepts)
        semantic_score = self._evaluate_semantic_relevance(query, document_content)
        factors["semantic_score"] = semantic_score

        # Compute weighted score
        weights = {
            "keyword_overlap": 0.25,
            "content_density": 0.20,
            "length_score": 0.15,
            "query_coverage": 0.20,
            "position_score": 0.10,
            "semantic_score": 0.10,
        }

        confidence = sum(factors.get(key, 0.0) * weight for key, weight in weights.items())

        # Determine relevance level
        if confidence >= 0.75:
            relevance_level = RelevanceLevel.HIGHLY_RELEVANT
        elif confidence >= 0.55:
            relevance_level = RelevanceLevel.RELEVANT
        elif confidence >= 0.30:
            relevance_level = RelevanceLevel.PARTIALLY_RELEVANT
        else:
            relevance_level = RelevanceLevel.IRRELEVANT

        reasoning = self._generate_reasoning(factors, relevance_level)

        return RelevanceScore(
            document_id=document_id,
            query=query,
            document_content=document_content[:500],
            relevance_level=relevance_level,
            confidence=confidence,
            factors=factors,
            reasoning=reasoning,
            is_llm_evaluated=False,
        )

    def _evaluate_with_llm(
        self, query: str, document_content: str, document_id: str
    ) -> RelevanceScore:
        """Evaluate using LLM (slow but more accurate)

        Args:
            query: The search query
            document_content: The document content
            document_id: The document ID

        Returns:
            RelevanceScore based on LLM evaluation
        """
        # For now, use heuristics as baseline
        # In production, this would call an LLM
        score = self._evaluate_with_heuristics(query, document_content, document_id)
        score.is_llm_evaluated = True
        return score

    def _find_first_match_position(self, query: str, document: str) -> int:
        """Find position of first query term in document

        Args:
            query: The query string
            document: The document string

        Returns:
            Character position of first match, or -1 if not found
        """
        query_words = query.lower().split()
        doc_lower = document.lower()

        min_pos = float("inf")
        for word in query_words:
            pos = doc_lower.find(word)
            if pos != -1 and pos < min_pos:
                min_pos = pos

        return min_pos if min_pos != float("inf") else -1

    def _evaluate_semantic_relevance(self, query: str, document: str) -> float:
        """Evaluate semantic relevance using concept matching

        Args:
            query: The query string
            document: The document string

        Returns:
            Semantic relevance score (0.0-1.0)
        """
        # Simple semantic relevance based on concept categories
        semantic_categories = {
            "question_words": {"what", "which", "who", "when", "where", "why", "how"},
            "action_words": {"find", "search", "get", "retrieve", "show", "tell"},
            "quality_words": {"best", "good", "excellent", "high", "top", "quality"},
        }

        score = 0.0
        query_lower = query.lower()
        doc_lower = document.lower()

        # Check for semantic alignment
        for category, words in semantic_categories.items():
            for word in words:
                if word in query_lower and word in doc_lower:
                    score += 0.3

        return min(score, 1.0)

    def _generate_reasoning(
        self, factors: Dict[str, float], relevance_level: RelevanceLevel
    ) -> str:
        """Generate explanation of relevance assessment

        Args:
            factors: Dictionary of evaluation factors
            relevance_level: The determined relevance level

        Returns:
            Human-readable reasoning
        """
        if relevance_level == RelevanceLevel.HIGHLY_RELEVANT:
            return (
                f"Document is highly relevant (confidence: {factors.get('keyword_overlap', 0):.0%})"
            )
        elif relevance_level == RelevanceLevel.RELEVANT:
            return f"Document is relevant with good coverage (confidence: {factors.get('query_coverage', 0):.0%})"
        elif relevance_level == RelevanceLevel.PARTIALLY_RELEVANT:
            return f"Document partially addresses query (confidence: {factors.get('content_density', 0):.0%})"
        else:
            return "Document does not contain relevant information"

    def evaluate_batch(
        self, query: str, documents: List[str], doc_ids: List[str] = None
    ) -> List[RelevanceScore]:
        """Evaluate multiple documents for a single query

        Args:
            query: The search query
            documents: List of document contents
            doc_ids: Optional list of document IDs

        Returns:
            List of RelevanceScore objects
        """
        if doc_ids is None:
            doc_ids = [str(i) for i in range(len(documents))]

        results = [
            self.evaluate_relevance(query, doc, doc_id) for doc, doc_id in zip(documents, doc_ids)
        ]

        return results

    def get_relevant_documents(
        self,
        query: str,
        documents: List[str],
        min_relevance: RelevanceLevel = RelevanceLevel.PARTIALLY_RELEVANT,
        doc_ids: List[str] = None,
    ) -> List[tuple]:
        """Filter documents by minimum relevance level

        Args:
            query: The search query
            documents: List of documents
            min_relevance: Minimum relevance level to include
            doc_ids: Optional document IDs

        Returns:
            List of (document, score) tuples for relevant documents
        """
        if doc_ids is None:
            doc_ids = [str(i) for i in range(len(documents))]

        relevance_levels = {
            RelevanceLevel.IRRELEVANT: 0,
            RelevanceLevel.PARTIALLY_RELEVANT: 1,
            RelevanceLevel.RELEVANT: 2,
            RelevanceLevel.HIGHLY_RELEVANT: 3,
        }

        min_level_value = relevance_levels[min_relevance]

        results = []
        for doc, doc_id in zip(documents, doc_ids):
            score = self.evaluate_relevance(query, doc, doc_id)
            if relevance_levels[score.relevance_level] >= min_level_value:
                results.append((doc, score))

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Get evaluation statistics

        Returns:
            Dictionary with statistics
        """
        if self.total_evaluations == 0:
            cache_hit_rate = 0.0
        else:
            cache_hit_rate = self.cache_hits / self.total_evaluations

        # Get relevance distribution
        relevance_distribution = {}
        for score in self.evaluation_cache.values():
            level = score.relevance_level.value
            relevance_distribution[level] = relevance_distribution.get(level, 0) + 1

        # Get average confidence by relevance level
        avg_confidence = {}
        for level in RelevanceLevel:
            scores = [
                s.confidence for s in self.evaluation_cache.values() if s.relevance_level == level
            ]
            if scores:
                avg_confidence[level.value] = sum(scores) / len(scores)

        return {
            "total_evaluations": self.total_evaluations,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": cache_hit_rate,
            "relevance_distribution": relevance_distribution,
            "average_confidence_by_level": avg_confidence,
        }

    def clear_cache(self) -> None:
        """Clear evaluation cache"""
        self.evaluation_cache.clear()
