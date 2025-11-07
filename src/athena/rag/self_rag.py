"""Self-RAG (Self-Reflective Retrieval Augmented Generation)

Main orchestration system that combines retrieval evaluation and answer
generation with self-critique for improved quality. Implements the complete
Self-RAG pipeline with adaptive retrieval and iterative improvement.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
import asyncio

from .retrieval_evaluator import RetrievalEvaluator, RelevanceLevel, RelevanceScore
from .answer_generator import AnswerGenerator, GeneratedAnswer, CritiqueType


class SelfRAGStage(str, Enum):
    """Stages in Self-RAG pipeline"""
    RETRIEVE = "retrieve"
    EVALUATE_RETRIEVAL = "evaluate_retrieval"
    GENERATE = "generate"
    CRITIQUE = "critique"
    REGENERATE = "regenerate"
    COMPLETE = "complete"


@dataclass
class RetrievalResult:
    """Result of retrieval phase"""
    query: str
    documents: List[str]
    relevance_scores: List[RelevanceScore] = field(default_factory=list)
    relevant_document_count: int = 0
    relevance_score_avg: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "query": self.query,
            "total_documents": len(self.documents),
            "relevant_documents": self.relevant_document_count,
            "average_relevance": self.relevance_score_avg,
        }


@dataclass
class SelfRAGResult:
    """Complete result of Self-RAG pipeline"""
    query: str
    final_answer: str
    confidence: float
    stage: SelfRAGStage
    retrieval_results: Optional[RetrievalResult] = None
    generated_answer: Optional[GeneratedAnswer] = None
    iterations_completed: int = 0
    documents_used: List[str] = field(default_factory=list)
    total_generation_cycles: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "query": self.query,
            "answer": self.final_answer,
            "confidence": self.confidence,
            "stage": self.stage.value,
            "iterations": self.iterations_completed,
            "documents_used": len(self.documents_used),
            "generation_cycles": self.total_generation_cycles,
        }


class SelfRAG:
    """Self-RAG pipeline orchestrator"""

    def __init__(
        self,
        retriever: Optional[Callable] = None,
        use_llm_evaluation: bool = False,
        max_iterations: int = 3,
        quality_threshold: float = 0.8,
    ):
        """Initialize Self-RAG

        Args:
            retriever: Optional function to retrieve documents (query -> List[str])
            use_llm_evaluation: Whether to use LLM for retrieval evaluation
            max_iterations: Maximum iterations for retrieval
            quality_threshold: Confidence threshold for answer quality
        """
        self.retriever = retriever or self._default_retriever
        self.evaluator = RetrievalEvaluator(use_llm_evaluation=use_llm_evaluation)
        self.generator = AnswerGenerator(max_regeneration_cycles=3)
        self.max_iterations = max_iterations
        self.quality_threshold = quality_threshold
        self.execution_history: List[SelfRAGResult] = []

    async def run(self, query: str, initial_documents: List[str] = None) -> SelfRAGResult:
        """Run complete Self-RAG pipeline

        Args:
            query: The query/question
            initial_documents: Optional initial documents for evaluation

        Returns:
            SelfRAGResult with final answer and metadata
        """
        try:
            # Stage 1: Retrieve initial documents
            if initial_documents is None:
                documents = await self._retrieve_documents(query)
            else:
                documents = initial_documents

            # Stage 2: Evaluate retrieval quality
            retrieval_result = await self._evaluate_retrieval(query, documents)

            # Stage 3: Generate and critique answer
            final_answer, generated_answer, iterations = await self._generate_and_critique(
                query, retrieval_result.documents
            )

            # Build result
            result = SelfRAGResult(
                query=query,
                final_answer=final_answer,
                confidence=generated_answer.confidence if generated_answer else 0.5,
                stage=SelfRAGStage.COMPLETE,
                retrieval_results=retrieval_result,
                generated_answer=generated_answer,
                iterations_completed=iterations,
                documents_used=retrieval_result.documents,
                total_generation_cycles=iterations,
            )

            self.execution_history.append(result)
            return result

        except Exception as e:
            return SelfRAGResult(
                query=query,
                final_answer=f"Error during Self-RAG pipeline: {str(e)}",
                confidence=0.0,
                stage=SelfRAGStage.RETRIEVE,
            )

    async def _retrieve_documents(self, query: str) -> List[str]:
        """Retrieve documents for query

        Args:
            query: The query

        Returns:
            List of retrieved documents
        """
        # Use provided retriever or default
        return await self.retriever(query) if asyncio.iscoroutinefunction(
            self.retriever
        ) else self.retriever(query)

    async def _evaluate_retrieval(
        self, query: str, documents: List[str]
    ) -> RetrievalResult:
        """Evaluate quality of retrieved documents

        Args:
            query: The query
            documents: Retrieved documents

        Returns:
            RetrievalResult with evaluation
        """
        # Evaluate each document
        relevance_scores = self.evaluator.evaluate_batch(query, documents)

        # Count relevant documents
        relevant_count = sum(
            1
            for score in relevance_scores
            if score.relevance_level
            in [RelevanceLevel.RELEVANT, RelevanceLevel.HIGHLY_RELEVANT]
        )

        # Compute average relevance
        avg_relevance = (
            sum(score.confidence for score in relevance_scores) / len(relevance_scores)
            if relevance_scores
            else 0.0
        )

        return RetrievalResult(
            query=query,
            documents=documents,
            relevance_scores=relevance_scores,
            relevant_document_count=relevant_count,
            relevance_score_avg=avg_relevance,
        )

    async def _generate_and_critique(
        self, query: str, documents: List[str]
    ) -> tuple:
        """Generate answer and perform iterative critique

        Args:
            query: The query
            documents: Supporting documents

        Returns:
            Tuple of (final_answer, generated_answer, iterations)
        """
        # Generate answer with feedback loop
        generated_answer = self.generator.generate_with_feedback_loop(
            query, documents, self.quality_threshold
        )

        iterations = 0
        for history_item in self.generator.generation_history:
            if "regenerated" in history_item.generation_method:
                iterations += 1

        return generated_answer.answer, generated_answer, iterations + 1

    async def adaptive_retrieval(
        self, query: str, max_retrievals: int = 3
    ) -> RetrievalResult:
        """Adaptive retrieval that continues until quality threshold

        Args:
            query: The query
            max_retrievals: Maximum retrieval attempts

        Returns:
            Best RetrievalResult achieved
        """
        best_result = None
        retrieval_count = 0

        while retrieval_count < max_retrievals:
            # Retrieve documents
            documents = await self._retrieve_documents(query)

            # Evaluate
            result = await self._evaluate_retrieval(query, documents)
            best_result = result

            # Check if quality is acceptable
            if (
                result.relevant_document_count > 0
                and result.relevance_score_avg >= self.quality_threshold
            ):
                break

            retrieval_count += 1
            # Note: In practice, you'd modify query or retrieval params here

        return best_result

    async def stream_result(
        self, query: str, initial_documents: List[str] = None
    ) -> Any:
        """Stream result generation for real-time feedback

        Args:
            query: The query
            initial_documents: Optional initial documents

        Returns:
            Async generator yielding pipeline stages
        """
        # Stage 1: Retrieve
        if initial_documents is None:
            documents = await self._retrieve_documents(query)
        else:
            documents = initial_documents
        yield ("retrieve", documents)

        # Stage 2: Evaluate retrieval
        retrieval_result = await self._evaluate_retrieval(query, documents)
        yield ("evaluate_retrieval", retrieval_result)

        # Stage 3: Generate
        generated_answer = self.generator.generate_answer(query, documents)
        yield ("generate", generated_answer)

        # Stage 4: Critique
        critique_result = self.generator.critique_answer(query, generated_answer.answer, documents)
        yield ("critique", critique_result)

        # Stage 5: Regenerate if needed
        if critique_result.should_regenerate(self.quality_threshold):
            regenerated = self.generator.generate_answer(query, documents, use_critique=True)
            yield ("regenerate", regenerated)

    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics

        Returns:
            Dictionary with statistics
        """
        if not self.execution_history:
            return {
                "total_queries": 0,
                "average_confidence": 0.0,
                "total_documents_retrieved": 0,
                "average_documents_used": 0.0,
                "total_iterations": 0,
            }

        total = len(self.execution_history)
        avg_confidence = sum(r.confidence for r in self.execution_history) / total
        total_docs = sum(len(r.documents_used) for r in self.execution_history)
        avg_docs = total_docs / total if total > 0 else 0

        total_iterations = sum(r.iterations_completed for r in self.execution_history)

        return {
            "total_queries": total,
            "average_confidence": avg_confidence,
            "total_documents_retrieved": total_docs,
            "average_documents_used": avg_docs,
            "total_iterations": total_iterations,
            "evaluator_stats": self.evaluator.get_statistics(),
            "generator_stats": self.generator.get_statistics(),
        }

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get execution history

        Returns:
            List of execution results
        """
        return [result.to_dict() for result in self.execution_history]

    def clear_history(self) -> None:
        """Clear execution history"""
        self.execution_history.clear()
        self.evaluator.clear_cache()
        self.generator.clear_history()

    async def _default_retriever(self, query: str) -> List[str]:
        """Default retriever (returns empty list)

        Args:
            query: The query

        Returns:
            Empty list (to be overridden)
        """
        return []

    def set_retriever(self, retriever: Callable) -> None:
        """Set custom retriever function

        Args:
            retriever: Function that takes query and returns List[str]
        """
        self.retriever = retriever

    async def batch_process(self, queries: List[str]) -> List[SelfRAGResult]:
        """Process multiple queries

        Args:
            queries: List of queries

        Returns:
            List of results
        """
        results = [await self.run(query) for query in queries]
        return results
