"""Answer Generator with Self-Reflection for Self-RAG

Generates answers to queries and performs self-reflection to assess quality,
identify hallucinations, and iteratively improve responses through critique
and regeneration cycles.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime


class CritiqueType(str, Enum):
    """Types of self-critique"""

    SUPPORTED = "supported"  # Answer is fully supported by documents
    PARTIALLY_SUPPORTED = "partially_supported"  # Some parts are supported
    NOT_SUPPORTED = "not_supported"  # Answer not supported by documents
    HALLUCINATION = "hallucination"  # Answer contains contradictions


@dataclass
class CritiqueResult:
    """Result of self-critique on generated answer"""

    answer: str
    critique_type: CritiqueType
    confidence: float  # 0.0-1.0
    issues_found: List[str] = field(default_factory=list)
    supported_segments: List[str] = field(default_factory=list)
    unsupported_segments: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def should_regenerate(self, threshold: float = 0.7) -> bool:
        """Check if answer should be regenerated

        Args:
            threshold: Confidence threshold below which regeneration is triggered

        Returns:
            True if answer quality is below threshold
        """
        return self.confidence < threshold

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "critique_type": self.critique_type.value,
            "confidence": self.confidence,
            "issues": self.issues_found,
            "suggestions": self.suggestions,
            "should_regenerate": self.should_regenerate(),
        }


@dataclass
class GeneratedAnswer:
    """Generated answer with metadata"""

    query: str
    answer: str
    supporting_documents: List[str] = field(default_factory=list)
    generation_method: str = "baseline"  # baseline, regenerated_once, regenerated_twice, etc
    critique_results: Optional[CritiqueResult] = None
    confidence: float = 0.5
    is_final: bool = False
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "query": self.query,
            "answer": self.answer,
            "documents": len(self.supporting_documents),
            "method": self.generation_method,
            "confidence": self.confidence,
            "is_final": self.is_final,
            "critique": self.critique_results.to_dict() if self.critique_results else None,
        }


class AnswerGenerator:
    """Generates answers with self-reflection and critique"""

    def __init__(self, max_regeneration_cycles: int = 3):
        """Initialize answer generator

        Args:
            max_regeneration_cycles: Maximum cycles of regeneration
        """
        self.max_regeneration_cycles = max_regeneration_cycles
        self.generation_history: List[GeneratedAnswer] = []

    def generate_answer(
        self,
        query: str,
        documents: List[str] = None,
        use_critique: bool = True,
    ) -> GeneratedAnswer:
        """Generate an answer to a query

        Args:
            query: The query/question
            documents: List of supporting documents (optional)
            use_critique: Whether to perform self-critique

        Returns:
            GeneratedAnswer with optional critique
        """
        # Generate baseline answer
        answer_text = self._generate_baseline_answer(query, documents)

        answer = GeneratedAnswer(
            query=query,
            answer=answer_text,
            supporting_documents=documents or [],
            generation_method="baseline",
            confidence=0.6,
        )

        # Perform critique if enabled
        if use_critique:
            critique = self.critique_answer(query, answer_text, documents or [])
            answer.critique_results = critique
            answer.confidence = critique.confidence

        self.generation_history.append(answer)
        return answer

    def generate_with_feedback_loop(
        self,
        query: str,
        documents: List[str] = None,
        quality_threshold: float = 0.8,
    ) -> GeneratedAnswer:
        """Generate answer with iterative feedback and regeneration

        Args:
            query: The query
            documents: Supporting documents
            quality_threshold: Minimum quality threshold

        Returns:
            Best generated answer after feedback loops
        """
        documents = documents or []
        regeneration_count = 0
        best_answer = None

        while regeneration_count <= self.max_regeneration_cycles:
            # Generate answer
            answer_text = self._generate_baseline_answer(query, documents)

            # Critique it
            critique = self.critique_answer(query, answer_text, documents)

            # Create answer object
            answer = GeneratedAnswer(
                query=query,
                answer=answer_text,
                supporting_documents=documents,
                generation_method=(
                    f"regenerated_{regeneration_count}" if regeneration_count > 0 else "baseline"
                ),
                critique_results=critique,
                confidence=critique.confidence,
            )

            best_answer = answer
            self.generation_history.append(answer)

            # Check if quality is acceptable
            if critique.confidence >= quality_threshold or not critique.should_regenerate(
                quality_threshold
            ):
                answer.is_final = True
                break

            regeneration_count += 1

        return best_answer or answer

    def critique_answer(
        self,
        query: str,
        answer: str,
        documents: List[str] = None,
    ) -> CritiqueResult:
        """Perform self-critique on a generated answer

        Args:
            query: The original query
            answer: The generated answer
            documents: Supporting documents for verification

        Returns:
            CritiqueResult with assessment
        """
        documents = documents or []
        issues = []
        supported_segments = []
        unsupported_segments = []

        # Parse answer into segments (sentences)
        segments = [s.strip() for s in answer.split(".") if s.strip()]

        # Factor 1: Check support by documents
        support_score = 0.0
        if documents:
            supported_count = 0
            for segment in segments:
                if self._is_segment_supported(segment, documents):
                    supported_segments.append(segment)
                    supported_count += 1
                else:
                    unsupported_segments.append(segment)

            support_ratio = supported_count / len(segments) if segments else 0.0
            support_score = min(1.0, support_ratio * 1.2)  # Slight boost for full support

            if support_ratio == 1.0:
                critique_type = CritiqueType.SUPPORTED
            elif support_ratio >= 0.7:
                critique_type = CritiqueType.PARTIALLY_SUPPORTED
                issues.append(f"{100 - int(support_ratio*100)}% of answer lacks document support")
            else:
                critique_type = CritiqueType.NOT_SUPPORTED
                issues.append("Answer is not supported by provided documents")
        else:
            critique_type = CritiqueType.PARTIALLY_SUPPORTED
            support_score = 0.5
            issues.append("No documents provided for verification")

        # Factor 2: Check for hallucinations
        hallucination_score = self._check_hallucinations(answer, documents)
        if hallucination_score < 0.5:
            critique_type = CritiqueType.HALLUCINATION
            issues.append("Answer contains potential hallucinations or contradictions")

        # Factor 3: Check coherence and length
        coherence_score = self._check_coherence(answer)
        if coherence_score < 0.5:
            issues.append("Answer lacks coherence or clarity")

        # Factor 4: Check completeness
        completeness_score = self._check_completeness(query, answer)
        if completeness_score < 0.5:
            issues.append("Answer does not fully address the query")

        # Compute overall confidence
        weights = {
            "support": 0.4,
            "hallucination": 0.3,
            "coherence": 0.2,
            "completeness": 0.1,
        }

        confidence = (
            support_score * weights["support"]
            + hallucination_score * weights["hallucination"]
            + coherence_score * weights["coherence"]
            + completeness_score * weights["completeness"]
        )

        # Generate suggestions
        suggestions = self._generate_suggestions(critique_type, issues)

        return CritiqueResult(
            answer=answer,
            critique_type=critique_type,
            confidence=confidence,
            issues_found=issues,
            supported_segments=supported_segments,
            unsupported_segments=unsupported_segments,
            suggestions=suggestions,
        )

    def _generate_baseline_answer(self, query: str, documents: List[str] = None) -> str:
        """Generate baseline answer from query and documents

        Args:
            query: The query
            documents: Supporting documents

        Returns:
            Generated answer text
        """
        documents = documents or []

        # Simple heuristic-based answer generation
        if not documents:
            return f"Based on available information, I cannot provide a specific answer to: {query}"

        # Extract key information from documents
        combined_text = " ".join(documents)[:500]

        # Create a simple answer template
        answer = f"Based on the provided information about {query.split()[0] if query else 'your query'}: {combined_text}"

        return answer

    def _is_segment_supported(self, segment: str, documents: List[str]) -> bool:
        """Check if a segment is supported by documents

        Args:
            segment: The text segment
            documents: List of documents

        Returns:
            True if segment is supported
        """
        # Simple keyword matching
        segment_words = set(segment.lower().split())
        min_overlap = max(1, len(segment_words) // 3)  # At least 1/3 of words

        for doc in documents:
            doc_words = set(doc.lower().split())
            overlap = len(segment_words & doc_words)
            if overlap >= min_overlap:
                return True

        return False

    def _check_hallucinations(self, answer: str, documents: List[str]) -> float:
        """Check for hallucinations in answer

        Args:
            answer: The generated answer
            documents: Supporting documents

        Returns:
            Score 0.0-1.0 (higher = fewer hallucinations)
        """
        if not documents:
            return 0.5  # Unknown without documents

        # Count segments that are grounded
        segments = [s.strip() for s in answer.split(".") if s.strip()]
        if not segments:
            return 0.5

        grounded_count = sum(1 for seg in segments if self._is_segment_supported(seg, documents))

        return min(1.0, grounded_count / len(segments))

    def _check_coherence(self, answer: str) -> float:
        """Check answer coherence

        Args:
            answer: The generated answer

        Returns:
            Score 0.0-1.0
        """
        # Simple coherence checks
        if not answer:
            return 0.0

        # Check for minimum length
        words = answer.split()
        if len(words) < 5:
            return 0.3

        # Check for sentence structure
        sentences = [s.strip() for s in answer.split(".") if s.strip()]
        if not sentences or len(sentences) == 1:
            return 0.6

        # Good coherence if multiple sentences
        return 0.8

    def _check_completeness(self, query: str, answer: str) -> float:
        """Check if answer completely addresses query

        Args:
            query: The original query
            answer: The generated answer

        Returns:
            Score 0.0-1.0
        """
        # Simple completeness check
        query_words = set(query.lower().split())
        answer_words = set(answer.lower().split())

        if not query_words:
            return 0.5

        # Check what % of query is addressed in answer
        coverage = len(query_words & answer_words) / len(query_words)

        return min(1.0, coverage * 1.2)  # Slight boost for good coverage

    def _generate_suggestions(self, critique_type: CritiqueType, issues: List[str]) -> List[str]:
        """Generate suggestions for improvement

        Args:
            critique_type: Type of critique
            issues: List of identified issues

        Returns:
            List of suggestions
        """
        suggestions = []

        if critique_type == CritiqueType.HALLUCINATION:
            suggestions.append("Verify all claims against source documents")
            suggestions.append("Remove unsupported statements")
            suggestions.append("Mark uncertain information as speculative")

        elif critique_type == CritiqueType.NOT_SUPPORTED:
            suggestions.append("Retrieve additional documents")
            suggestions.append("Reformulate query for better retrieval")
            suggestions.append("Request clarification from user")

        elif critique_type == CritiqueType.PARTIALLY_SUPPORTED:
            suggestions.append("Strengthen unsupported claims with evidence")
            suggestions.append("Retrieve targeted documents for missing topics")
            suggestions.append("Consider multi-hop retrieval for complex queries")

        else:  # SUPPORTED
            suggestions.append("Answer is well-supported, consider finalizing")

        return suggestions[:2]  # Return top 2 suggestions

    def get_history(self) -> List[Dict[str, Any]]:
        """Get generation history

        Returns:
            List of generated answers with metadata
        """
        return [answer.to_dict() for answer in self.generation_history]

    def get_statistics(self) -> Dict[str, Any]:
        """Get generation statistics

        Returns:
            Dictionary with statistics
        """
        if not self.generation_history:
            return {
                "total_answers": 0,
                "average_confidence": 0.0,
                "answers_needing_critique": 0,
                "critique_types": {},
            }

        total = len(self.generation_history)
        avg_confidence = sum(a.confidence for a in self.generation_history) / total

        critique_types = {}
        needing_critique = 0

        for answer in self.generation_history:
            if answer.critique_results:
                ctype = answer.critique_results.critique_type.value
                critique_types[ctype] = critique_types.get(ctype, 0) + 1

                if answer.critique_results.should_regenerate():
                    needing_critique += 1

        return {
            "total_answers": total,
            "average_confidence": avg_confidence,
            "answers_needing_critique": needing_critique,
            "critique_distribution": critique_types,
            "regeneration_cycles": sum(
                1 for a in self.generation_history if "regenerated" in a.generation_method
            ),
        }

    def clear_history(self) -> None:
        """Clear generation history"""
        self.generation_history.clear()
