"""
Benchmark: Lost in Middle Mitigation

Tests whether recency-weighted retrieval helps retrieve recent memories
that might be lost in the middle of a long context window.

Background:
- Liu et al. (2024): LLMs show U-shaped attention curve
- Early and recent content is attended to; middle content is ignored
- This test verifies recency weighting can mitigate this bias
"""

import pytest
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

from athena.rag.recency_weighting import (
    RecencyWeightingConfig,
    RecencyWeightedRetriever,
)
from athena.memory.search import MemorySearchResult
from athena.core.models import Memory


class TestLostInMiddleMitigation:
    """Benchmark for Lost in Middle attention bias mitigation."""

    @pytest.fixture
    def retriever_with_recency(self):
        """Create retriever with recency weighting (30% recency)."""
        config = RecencyWeightingConfig(recency_weight=0.3)
        return RecencyWeightedRetriever(config)

    @pytest.fixture
    def retriever_semantic_only(self):
        """Create retriever with pure semantic (0% recency)."""
        config = RecencyWeightingConfig(recency_weight=0.0)
        return RecencyWeightedRetriever(config)

    def _create_memory(self, content: str, age_days: float) -> Memory:
        """Create a mock memory with specified age."""
        created_at = datetime.now() - timedelta(days=age_days)
        return Memory(
            content=content,
            memory_type="fact",
            created_at=created_at,
            updated_at=created_at,
            tags=[],
            project_id=1,  # Default project
        )

    def _create_search_result(
        self, memory: Memory, score: float
    ) -> MemorySearchResult:
        """Create a search result for a memory."""
        return MemorySearchResult(
            memory=memory,
            score=score,
            similarity=score,  # Use score as similarity
            rank=0,  # Will be updated by retriever
            relevance="high",
            context="test",
        )

    def test_recency_score_calculation(self, retriever_with_recency):
        """Test that recency scores decay over time."""
        memory_today = self._create_memory("Recent fact", age_days=0)
        memory_week_ago = self._create_memory("Old fact", age_days=7)
        memory_month_ago = self._create_memory("Very old fact", age_days=30)

        score_today = retriever_with_recency.calculate_recency_score(memory_today)
        score_week = retriever_with_recency.calculate_recency_score(memory_week_ago)
        score_month = retriever_with_recency.calculate_recency_score(memory_month_ago)

        # Scores should decay over time
        assert score_today > score_week
        assert score_week > score_month
        assert 0.0 <= score_today <= 1.0
        assert 0.0 <= score_week <= 1.0
        assert 0.0 <= score_month <= 1.0

        print(f"\nRecency Score Decay:")
        print(f"  Today (0 days): {score_today:.3f}")
        print(f"  1 week ago: {score_week:.3f}")
        print(f"  1 month ago: {score_month:.3f}")

    def test_lost_in_middle_mitigation(
        self, retriever_with_recency, retriever_semantic_only
    ):
        """Test that recency weighting retrieves middle memories better.

        Scenario:
        - 100 memories over 10 days (early, middle, recent)
        - Middle memory is semantically low relevance but recent
        - Recency weighting should rank it higher than semantic-only
        """
        # Create memories spanning 10 days
        memories = []
        for i in range(100):
            age = 10 - (i / 10)  # Spread across 10 days
            memory = self._create_memory(f"Event {i}", age_days=age)
            memories.append(memory)

        # Simulate semantic search results
        # (in practice, this comes from vector database)
        results = []
        for i, mem in enumerate(memories):
            # Middle memories get lower semantic scores
            # (they're "less relevant" semantically)
            if 40 <= i <= 60:  # Middle
                semantic_score = 0.3  # Low semantic relevance
            elif i < 20 or i > 80:  # Early/recent
                semantic_score = 0.8  # High semantic relevance
            else:  # Transition
                semantic_score = 0.5

            results.append(self._create_search_result(mem, semantic_score))

        # Retrieve with and without recency weighting
        retrieved_semantic = retriever_semantic_only.retrieve_with_recency(
            "query", results, k=10
        )
        retrieved_recency = retriever_with_recency.retrieve_with_recency(
            "query", results, k=10
        )

        # Extract content to see what was retrieved
        semantic_contents = [r.memory.content for r in retrieved_semantic]
        recency_contents = [r.memory.content for r in retrieved_recency]

        print(f"\nLost in Middle Mitigation:")
        print(f"  Semantic-only retrieved: {semantic_contents[:5]}...")
        print(f"  With recency weighting: {recency_contents[:5]}...")

        # Count how many middle memories each approach retrieved
        semantic_middle = sum(
            1 for r in retrieved_semantic if 40 <= memories.index(r.memory) <= 60
        )
        recency_middle = sum(
            1 for r in retrieved_recency if 40 <= memories.index(r.memory) <= 60
        )

        print(f"  Semantic-only retrieved {semantic_middle} middle memories")
        print(f"  Recency weighting retrieved {recency_middle} middle memories")

        # Recency weighting should retrieve more middle memories
        # (Since middle memories are recent even if less semantically relevant)
        assert recency_middle >= semantic_middle

    def test_recency_weighting_impact(self, retriever_with_recency):
        """Test that recency weighting actually changes ranking.

        Given:
        - Memory A: Very recent, moderate semantic relevance (0.6)
        - Memory B: Old, very high semantic relevance (0.95)

        With pure semantic: B ranks higher
        With recency weighting: A should rank higher (or close)
        """
        memory_recent = self._create_memory(
            "Recent but less relevant fact", age_days=0.1
        )
        memory_old = self._create_memory(
            "Old but very relevant fact", age_days=30
        )

        result_recent = self._create_search_result(memory_recent, score=0.6)
        result_old = self._create_search_result(memory_old, score=0.95)

        # Score without recency weighting
        config_semantic = RecencyWeightingConfig(recency_weight=0.0)
        retriever_semantic = RecencyWeightedRetriever(config_semantic)

        score_recent_semantic = retriever_semantic.calculate_combined_score(
            memory_recent, 0.6
        )
        score_old_semantic = retriever_semantic.calculate_combined_score(
            memory_old, 0.95
        )

        # Score with recency weighting
        score_recent_recency = retriever_with_recency.calculate_combined_score(
            memory_recent, 0.6
        )
        score_old_recency = retriever_with_recency.calculate_combined_score(
            memory_old, 0.95
        )

        print(f"\nRecency Weighting Impact:")
        print(f"  Semantic-only:")
        print(f"    Recent (0.6): {score_recent_semantic:.3f}")
        print(f"    Old (0.95):   {score_old_semantic:.3f}")
        print(f"  With recency (0.3 weight):")
        print(f"    Recent (0.6): {score_recent_recency:.3f}")
        print(f"    Old (0.95):   {score_old_recency:.3f}")

        # Pure semantic ranks old higher
        assert score_old_semantic > score_recent_semantic

        # Recency weighting brings recent and old closer (or reverses ranking)
        gap_semantic = score_old_semantic - score_recent_semantic
        gap_recency = score_old_recency - score_recent_recency

        print(f"  Gap reduction: {gap_semantic:.3f} → {gap_recency:.3f}")
        assert gap_recency < gap_semantic

    def test_configurable_recency_weight(self):
        """Test that recency weight is configurable."""
        memory_recent = self._create_memory("Recent", age_days=0.1)
        memory_old = self._create_memory("Old", age_days=30)

        # Test different weights
        weights = [0.0, 0.1, 0.3, 0.5, 0.7, 1.0]

        results = []
        for weight in weights:
            config = RecencyWeightingConfig(recency_weight=weight)
            retriever = RecencyWeightedRetriever(config)

            score_recent = retriever.calculate_combined_score(memory_recent, 0.5)
            score_old = retriever.calculate_combined_score(memory_old, 0.5)

            results.append(
                {
                    "weight": weight,
                    "recent_score": score_recent,
                    "old_score": score_old,
                    "gap": score_old - score_recent,
                }
            )

        print(f"\nRecency Weight Configuration:")
        for r in results:
            print(
                f"  Weight {r['weight']:.1f}: Recent={r['recent_score']:.3f}, "
                f"Old={r['old_score']:.3f}, Gap={r['gap']:.3f}"
            )

        # As weight increases, recent should score higher relative to old
        # (gap should decrease)
        for i in range(len(results) - 1):
            assert results[i]["gap"] >= results[i + 1]["gap"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
