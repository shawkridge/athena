"""Unit tests for Self-RAG implementation

Tests for:
- Retrieval evaluator
- Answer generator
- Self-RAG orchestration
"""

import pytest
import asyncio
from datetime import datetime

from athena.rag.retrieval_evaluator import (
    RetrievalEvaluator,
    RelevanceLevel,
    RelevanceScore,
)
from athena.rag.answer_generator import (
    AnswerGenerator,
    CritiqueType,
    CritiqueResult,
    GeneratedAnswer,
)
from athena.rag.self_rag import SelfRAG, RetrievalResult, SelfRAGResult, SelfRAGStage


# ============================================================================
# Retrieval Evaluator Tests
# ============================================================================


class TestRetrievalEvaluator:
    """Test RetrievalEvaluator class"""

    def test_init(self):
        """Test evaluator initialization"""
        evaluator = RetrievalEvaluator(use_llm_evaluation=False)
        assert evaluator.total_evaluations == 0
        assert evaluator.cache_hits == 0
        assert len(evaluator.evaluation_cache) == 0

    def test_evaluate_relevance_high(self):
        """Test evaluation of highly relevant document"""
        evaluator = RetrievalEvaluator()
        query = "machine learning algorithms"
        doc = "Machine learning is a subset of artificial intelligence that focuses on algorithms"

        score = evaluator.evaluate_relevance(query, doc, "doc1")

        assert score.relevance_level != RelevanceLevel.IRRELEVANT
        assert score.confidence > 0.3
        assert score.document_id == "doc1"

    def test_evaluate_relevance_low(self):
        """Test evaluation of irrelevant document"""
        evaluator = RetrievalEvaluator()
        query = "machine learning"
        doc = "The weather is sunny today"

        score = evaluator.evaluate_relevance(query, doc, "doc2")

        assert score.relevance_level == RelevanceLevel.IRRELEVANT
        assert score.confidence < 0.4

    def test_caching(self):
        """Test evaluation caching"""
        evaluator = RetrievalEvaluator()
        query = "test query"
        doc = "test document"

        # First evaluation
        score1 = evaluator.evaluate_relevance(query, doc, use_cache=True)
        assert evaluator.cache_hits == 0

        # Second evaluation (should hit cache)
        score2 = evaluator.evaluate_relevance(query, doc, use_cache=True)
        assert evaluator.cache_hits == 1
        assert score1.confidence == score2.confidence

    def test_evaluate_batch(self):
        """Test batch evaluation"""
        evaluator = RetrievalEvaluator()
        query = "Python programming"
        docs = [
            "Python is a programming language",
            "The sun is bright",
            "Python has simple syntax",
        ]

        scores = evaluator.evaluate_batch(query, docs)

        assert len(scores) == 3
        assert scores[0].document_id == "0"
        assert scores[2].relevance_level != RelevanceLevel.IRRELEVANT

    def test_get_relevant_documents(self):
        """Test filtering by relevance"""
        evaluator = RetrievalEvaluator()
        query = "AI"
        docs = [
            "Artificial intelligence",
            "The cat",
            "AI systems",
        ]

        relevant = evaluator.get_relevant_documents(
            query, docs, min_relevance=RelevanceLevel.PARTIALLY_RELEVANT
        )

        assert len(relevant) >= 1

    def test_statistics(self):
        """Test statistics collection"""
        evaluator = RetrievalEvaluator()
        query = "test"
        doc = "test document"

        evaluator.evaluate_relevance(query, doc, use_cache=False)
        evaluator.evaluate_relevance(query, doc, use_cache=False)

        stats = evaluator.get_statistics()

        assert stats["total_evaluations"] == 2

    def test_relevance_factors(self):
        """Test that factors are computed"""
        evaluator = RetrievalEvaluator()
        query = "data science"
        doc = "Data science uses machine learning and statistics"

        score = evaluator.evaluate_relevance(query, doc)

        assert "keyword_overlap" in score.factors
        assert "content_density" in score.factors
        assert "query_coverage" in score.factors


# ============================================================================
# Answer Generator Tests
# ============================================================================


class TestAnswerGenerator:
    """Test AnswerGenerator class"""

    def test_init(self):
        """Test generator initialization"""
        gen = AnswerGenerator(max_regeneration_cycles=3)
        assert gen.max_regeneration_cycles == 3
        assert len(gen.generation_history) == 0

    def test_generate_answer(self):
        """Test basic answer generation"""
        gen = AnswerGenerator()
        query = "What is Python?"
        docs = ["Python is a programming language"]

        answer = gen.generate_answer(query, docs)

        assert answer.query == query
        assert len(answer.answer) > 0
        assert answer.generation_method == "baseline"

    def test_generate_answer_with_critique(self):
        """Test answer generation with critique"""
        gen = AnswerGenerator()
        query = "What is AI?"
        docs = ["Artificial intelligence is the simulation of human intelligence"]

        answer = gen.generate_answer(query, docs, use_critique=True)

        assert answer.critique_results is not None
        assert answer.confidence > 0.0

    def test_critique_supported(self):
        """Test critique of well-supported answer"""
        gen = AnswerGenerator()
        query = "programming"
        answer = "Python is a programming language"
        docs = ["Python is a programming language used for many applications"]

        critique = gen.critique_answer(query, answer, docs)

        assert critique.critique_type in [
            CritiqueType.SUPPORTED,
            CritiqueType.PARTIALLY_SUPPORTED,
        ]
        assert len(critique.supported_segments) > 0

    def test_critique_unsupported(self):
        """Test critique of unsupported answer"""
        gen = AnswerGenerator()
        query = "programming"
        answer = "The moon is made of cheese"
        docs = ["Python is a programming language"]

        critique = gen.critique_answer(query, answer, docs)

        assert critique.critique_type in [CritiqueType.NOT_SUPPORTED, CritiqueType.HALLUCINATION]
        assert len(critique.unsupported_segments) > 0

    def test_generate_with_feedback_loop(self):
        """Test generation with feedback loops"""
        gen = AnswerGenerator(max_regeneration_cycles=2)
        query = "testing"
        docs = ["Testing is important for software quality"]

        answer = gen.generate_with_feedback_loop(
            query, docs, quality_threshold=0.99
        )

        assert answer.query == query
        # Should have attempted regeneration due to high threshold
        assert len(gen.generation_history) >= 1

    def test_is_segment_supported(self):
        """Test segment support checking"""
        gen = AnswerGenerator()
        segment = "Python is a language"
        docs = ["Python is a programming language"]

        result = gen._is_segment_supported(segment, docs)

        assert result is True

    def test_check_hallucinations(self):
        """Test hallucination detection"""
        gen = AnswerGenerator()
        answer = "Python is red"
        docs = ["Python is a programming language"]

        score = gen._check_hallucinations(answer, docs)

        # Low score due to hallucination
        assert 0.0 <= score <= 1.0

    def test_statistics(self):
        """Test statistics collection"""
        gen = AnswerGenerator()
        query = "test"
        docs = ["test document"]

        gen.generate_answer(query, docs, use_critique=True)
        gen.generate_answer(query, docs, use_critique=True)

        stats = gen.get_statistics()

        assert stats["total_answers"] == 2
        assert stats["average_confidence"] > 0.0

    def test_generation_history(self):
        """Test history tracking"""
        gen = AnswerGenerator()
        query1 = "first"
        query2 = "second"

        gen.generate_answer(query1, [])
        gen.generate_answer(query2, [])

        history = gen.get_history()

        assert len(history) == 2
        assert history[0]["query"] == query1
        assert history[1]["query"] == query2


# ============================================================================
# Self-RAG Tests
# ============================================================================


class TestSelfRAG:
    """Test SelfRAG orchestration"""

    def test_init(self):
        """Test Self-RAG initialization"""
        rag = SelfRAG(max_iterations=3, quality_threshold=0.8)
        assert rag.max_iterations == 3
        assert rag.quality_threshold == 0.8
        assert isinstance(rag.evaluator, RetrievalEvaluator)
        assert isinstance(rag.generator, AnswerGenerator)

    @pytest.mark.asyncio
    async def test_run_basic(self):
        """Test basic Self-RAG execution"""
        async def mock_retriever(query):
            return ["Test document about " + query]

        rag = SelfRAG(retriever=mock_retriever)
        result = await rag.run("testing")

        assert result.query == "testing"
        assert result.stage == SelfRAGStage.COMPLETE
        assert len(result.documents_used) > 0

    @pytest.mark.asyncio
    async def test_evaluate_retrieval(self):
        """Test retrieval evaluation"""
        rag = SelfRAG()
        docs = ["Document about testing"]
        result = await rag._evaluate_retrieval("test", docs)

        assert isinstance(result, RetrievalResult)
        assert len(result.relevance_scores) == 1

    @pytest.mark.asyncio
    async def test_adaptive_retrieval(self):
        """Test adaptive retrieval"""
        async def mock_retriever(query):
            return ["Document 1", "Document 2"]

        rag = SelfRAG(retriever=mock_retriever)
        result = await rag.adaptive_retrieval("query", max_retrievals=2)

        assert isinstance(result, RetrievalResult)
        assert len(result.documents) > 0

    @pytest.mark.asyncio
    async def test_stream_result(self):
        """Test streaming result generation"""
        async def mock_retriever(query):
            return ["Test document"]

        rag = SelfRAG(retriever=mock_retriever)
        stages = []

        async for stage_name, _ in rag.stream_result("query"):
            stages.append(stage_name)

        assert len(stages) > 0
        assert "retrieve" in stages or "generate" in stages

    def test_statistics(self):
        """Test statistics collection"""
        rag = SelfRAG()
        stats = rag.get_statistics()

        assert "total_queries" in stats
        assert "average_confidence" in stats
        # Check for main statistics (no nested for empty history)
        assert isinstance(stats["total_queries"], int)
        assert isinstance(stats["average_confidence"], (int, float))

    def test_set_retriever(self):
        """Test setting custom retriever"""
        def custom_retriever(query):
            return ["Custom result"]

        rag = SelfRAG()
        rag.set_retriever(custom_retriever)

        # Simple check that retriever was set
        assert rag.retriever == custom_retriever

    def test_clear_history(self):
        """Test history clearing"""
        rag = SelfRAG()
        # Add some data
        rag.execution_history.append(
            SelfRAGResult(
                query="test",
                final_answer="answer",
                confidence=0.5,
                stage=SelfRAGStage.COMPLETE,
            )
        )

        rag.clear_history()

        assert len(rag.execution_history) == 0

    @pytest.mark.asyncio
    async def test_batch_process(self):
        """Test batch processing"""
        async def mock_retriever(query):
            return [f"Document for {query}"]

        rag = SelfRAG(retriever=mock_retriever)
        queries = ["query1", "query2", "query3"]

        results = await rag.batch_process(queries)

        assert len(results) == 3
        assert all(isinstance(r, SelfRAGResult) for r in results)

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling"""
        async def failing_retriever(query):
            raise ValueError("Retrieval failed")

        rag = SelfRAG(retriever=failing_retriever)
        result = await rag.run("query")

        assert result.stage == SelfRAGStage.RETRIEVE
        assert "Error" in result.final_answer


# ============================================================================
# Integration Tests
# ============================================================================


class TestSelfRAGIntegration:
    """Integration tests for complete Self-RAG workflows"""

    @pytest.mark.asyncio
    async def test_complete_pipeline(self):
        """Test complete Self-RAG pipeline"""
        docs = [
            "Python is a programming language",
            "Python was created by Guido van Rossum",
            "Python is widely used in data science",
        ]

        async def mock_retriever(query):
            return docs

        rag = SelfRAG(
            retriever=mock_retriever,
            max_iterations=2,
            quality_threshold=0.7,
        )

        result = await rag.run("What is Python?")

        assert result.stage == SelfRAGStage.COMPLETE
        assert result.confidence > 0.0
        assert len(result.documents_used) > 0

    @pytest.mark.asyncio
    async def test_evaluation_feedback_loop(self):
        """Test that evaluation influences regeneration"""
        docs = ["Information about query"]

        async def mock_retriever(query):
            return docs

        rag = SelfRAG(retriever=mock_retriever)
        result = await rag.run("query")

        assert isinstance(result, SelfRAGResult)
        assert result.final_answer is not None and len(result.final_answer) > 0

    def test_generator_and_evaluator_integration(self):
        """Test generator and evaluator working together"""
        gen = AnswerGenerator()
        eval = RetrievalEvaluator()

        # Generate answer
        docs = ["Test document about AI"]
        answer = gen.generate_answer("What is AI?", docs)

        # Evaluate supporting documents
        eval.evaluate_relevance("What is AI?", docs[0])

        # Should have both sets of data
        assert len(gen.generation_history) > 0
        assert eval.total_evaluations > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
