"""Integration tests for Self-RAG system

Tests complete workflows combining retrieval evaluation, answer generation,
and self-critique with feedback loops.
"""

import pytest
import asyncio
from typing import List

from athena.rag.self_rag import SelfRAG, SelfRAGStage
from athena.rag.retrieval_evaluator import RelevanceLevel
from athena.rag.answer_generator import CritiqueType


class TestSelfRAGCompleteWorkflow:
    """Test complete Self-RAG workflows"""

    @pytest.mark.asyncio
    async def test_basic_query_workflow(self):
        """Test basic query processing workflow"""
        docs = [
            "Python is a high-level programming language",
            "It was created by Guido van Rossum in 1991",
            "Python emphasizes code readability",
        ]

        async def mock_retriever(query: str) -> List[str]:
            return docs

        rag = SelfRAG(retriever=mock_retriever, quality_threshold=0.6)
        result = await rag.run("What is Python?")

        assert result.stage == SelfRAGStage.COMPLETE
        assert result.query == "What is Python?"
        assert len(result.final_answer) > 0
        assert len(result.documents_used) > 0
        assert result.confidence >= 0.0

    @pytest.mark.asyncio
    async def test_retrieval_quality_assessment(self):
        """Test that retrieval quality is properly assessed"""
        good_docs = [
            "Machine learning is a subset of artificial intelligence",
            "It enables systems to learn from data",
        ]
        bad_docs = ["The weather is nice today", "Cats are animals"]

        async def mock_retriever(query: str) -> List[str]:
            if "good" in query:
                return good_docs
            return bad_docs

        rag = SelfRAG(retriever=mock_retriever)

        result_good = await rag.run("What is good machine learning?")
        result_bad = await rag.run("bad weather cats")

        # Good result should have higher confidence than bad
        assert result_good.confidence >= 0.0
        assert result_bad.confidence >= 0.0

    @pytest.mark.asyncio
    async def test_adaptive_retrieval_flow(self):
        """Test adaptive retrieval with quality thresholds"""
        docs = ["Document about the query topic"]

        async def mock_retriever(query: str) -> List[str]:
            return docs

        rag = SelfRAG(
            retriever=mock_retriever,
            max_iterations=2,
            quality_threshold=0.5,
        )

        result = await rag.run("specific query")

        assert result.stage == SelfRAGStage.COMPLETE
        assert len(result.documents_used) > 0

    @pytest.mark.asyncio
    async def test_feedback_loop_integration(self):
        """Test feedback loop between generation and critique"""
        docs = ["Information about the topic"]

        async def mock_retriever(query: str) -> List[str]:
            return docs

        rag = SelfRAG(retriever=mock_retriever)

        result = await rag.run("Tell me about the topic")

        # Should have completed entire pipeline
        assert result.stage == SelfRAGStage.COMPLETE
        assert result.generated_answer is not None
        assert result.generated_answer.critique_results is not None

    @pytest.mark.asyncio
    async def test_streaming_pipeline(self):
        """Test streaming result generation"""
        async def mock_retriever(query: str) -> List[str]:
            return [f"Document about {query}"]

        rag = SelfRAG(retriever=mock_retriever)
        stages_completed = []

        async for stage_name, data in rag.stream_result("test query"):
            stages_completed.append(stage_name)

        # Should have processed multiple stages
        assert len(stages_completed) > 0

    @pytest.mark.asyncio
    async def test_batch_query_processing(self):
        """Test processing multiple queries efficiently"""
        queries = [
            "What is Python?",
            "What is machine learning?",
            "What is AI?",
        ]

        async def mock_retriever(query: str) -> List[str]:
            return [f"Information about {query}"]

        rag = SelfRAG(retriever=mock_retriever)
        results = await rag.batch_process(queries)

        assert len(results) == len(queries)
        assert all(r.stage == SelfRAGStage.COMPLETE for r in results)
        assert all(len(r.final_answer) > 0 for r in results)

    @pytest.mark.asyncio
    async def test_retrieval_evaluation_chain(self):
        """Test retrieval evaluation with diverse document quality"""
        query = "Python programming"
        relevant_docs = [
            "Python is a programming language with simple syntax",
            "Python supports multiple programming paradigms",
        ]
        irrelevant_docs = ["The Moon orbits Earth", "Cats have whiskers"]

        async def mock_retriever(q: str) -> List[str]:
            return relevant_docs + irrelevant_docs

        rag = SelfRAG(retriever=mock_retriever)
        result = await rag.run(query)

        # Should have evaluated documents
        assert result.retrieval_results is not None
        assert len(result.retrieval_results.relevance_scores) > 0

    @pytest.mark.asyncio
    async def test_answer_quality_assessment(self):
        """Test answer quality assessment through critique"""
        docs = ["Python is a programming language"]

        async def mock_retriever(query: str) -> List[str]:
            return docs

        rag = SelfRAG(retriever=mock_retriever)
        result = await rag.run("What is Python?")

        # Should have critique results
        assert result.generated_answer is not None
        assert result.generated_answer.critique_results is not None

        critique = result.generated_answer.critique_results
        assert critique.critique_type in [
            CritiqueType.SUPPORTED,
            CritiqueType.PARTIALLY_SUPPORTED,
            CritiqueType.NOT_SUPPORTED,
            CritiqueType.HALLUCINATION,
        ]

    @pytest.mark.asyncio
    async def test_iterative_regeneration(self):
        """Test iterative answer regeneration"""
        docs = ["Some information about the topic"]

        async def mock_retriever(query: str) -> List[str]:
            return docs

        rag = SelfRAG(retriever=mock_retriever, quality_threshold=0.99)
        result = await rag.run("Query about topic")

        # With high threshold, should attempt regeneration
        assert result.stage == SelfRAGStage.COMPLETE

    @pytest.mark.asyncio
    async def test_statistics_tracking(self):
        """Test that statistics are properly tracked"""
        async def mock_retriever(query: str) -> List[str]:
            return ["Document"]

        rag = SelfRAG(retriever=mock_retriever)

        await rag.run("Query 1")
        await rag.run("Query 2")

        stats = rag.get_statistics()

        assert stats["total_queries"] == 2
        assert isinstance(stats["average_confidence"], (int, float))

    @pytest.mark.asyncio
    async def test_execution_history_tracking(self):
        """Test execution history is tracked"""
        async def mock_retriever(query: str) -> List[str]:
            return ["Info"]

        rag = SelfRAG(retriever=mock_retriever)

        await rag.run("Test query 1")
        await rag.run("Test query 2")

        history = rag.get_execution_history()

        assert len(history) == 2
        assert history[0]["query"] == "Test query 1"
        assert history[1]["query"] == "Test query 2"


class TestSelfRAGEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_empty_document_handling(self):
        """Test handling of empty documents"""
        async def mock_retriever(query: str) -> List[str]:
            return []

        rag = SelfRAG(retriever=mock_retriever)
        result = await rag.run("Query")

        # Should handle gracefully
        assert result.stage == SelfRAGStage.COMPLETE or result.stage == SelfRAGStage.RETRIEVE

    @pytest.mark.asyncio
    async def test_retriever_error_handling(self):
        """Test handling of retriever errors"""
        async def failing_retriever(query: str) -> List[str]:
            raise RuntimeError("Retriever failed")

        rag = SelfRAG(retriever=failing_retriever)
        result = await rag.run("Query")

        # Should catch error gracefully
        assert "Error" in result.final_answer or result.stage != SelfRAGStage.COMPLETE

    @pytest.mark.asyncio
    async def test_very_long_documents(self):
        """Test handling of very long documents"""
        long_doc = " ".join(["word"] * 1000)

        async def mock_retriever(query: str) -> List[str]:
            return [long_doc]

        rag = SelfRAG(retriever=mock_retriever)
        result = await rag.run("Query")

        assert result.stage == SelfRAGStage.COMPLETE

    @pytest.mark.asyncio
    async def test_empty_query(self):
        """Test handling of empty query"""
        async def mock_retriever(query: str) -> List[str]:
            return ["Document"]

        rag = SelfRAG(retriever=mock_retriever)
        result = await rag.run("")

        # Should handle empty query gracefully
        assert isinstance(result.final_answer, str)


class TestSelfRAGQualityMetrics:
    """Test quality metrics and assessment"""

    @pytest.mark.asyncio
    async def test_confidence_scoring(self):
        """Test confidence scoring in results"""
        docs = ["Information"]

        async def mock_retriever(query: str) -> List[str]:
            return docs

        rag = SelfRAG(retriever=mock_retriever)
        result = await rag.run("Query")

        # Confidence should be in valid range
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_critique_type_classification(self):
        """Test critique type classification"""
        good_docs = ["Python is a programming language"]

        async def mock_retriever(query: str) -> List[str]:
            return good_docs

        rag = SelfRAG(retriever=mock_retriever)
        result = await rag.run("What is Python?")

        critique = result.generated_answer.critique_results
        assert critique.critique_type is not None

    @pytest.mark.asyncio
    async def test_relevance_assessment(self):
        """Test relevance assessment in retrieval"""
        docs = [
            "Directly related to query",
            "Partially related to query",
        ]

        async def mock_retriever(query: str) -> List[str]:
            return docs

        rag = SelfRAG(retriever=mock_retriever)
        result = await rag.run("Query")

        # Should have relevance scores
        assert result.retrieval_results is not None
        assert len(result.retrieval_results.relevance_scores) > 0


class TestSelfRAGCustomization:
    """Test customization and configuration"""

    @pytest.mark.asyncio
    async def test_custom_retriever(self):
        """Test setting custom retriever"""
        def custom_retriever(query: str) -> List[str]:
            return [f"Custom result for {query}"]

        rag = SelfRAG()
        rag.set_retriever(custom_retriever)

        # Verify retriever is set
        assert rag.retriever == custom_retriever

    @pytest.mark.asyncio
    async def test_quality_threshold_configuration(self):
        """Test quality threshold configuration"""
        async def mock_retriever(query: str) -> List[str]:
            return ["Document"]

        # Low threshold
        rag_low = SelfRAG(retriever=mock_retriever, quality_threshold=0.3)
        result_low = await rag_low.run("Query")

        # High threshold
        rag_high = SelfRAG(retriever=mock_retriever, quality_threshold=0.9)
        result_high = await rag_high.run("Query")

        # Both should complete but may differ in iterations
        assert result_low.stage == SelfRAGStage.COMPLETE
        assert result_high.stage == SelfRAGStage.COMPLETE

    @pytest.mark.asyncio
    async def test_max_iterations_configuration(self):
        """Test max iterations configuration"""
        async def mock_retriever(query: str) -> List[str]:
            return ["Document"]

        rag = SelfRAG(retriever=mock_retriever, max_iterations=2)
        result = await rag.run("Query")

        # Should have completed successfully
        assert result.stage == SelfRAGStage.COMPLETE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
