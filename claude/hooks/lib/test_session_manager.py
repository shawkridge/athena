#!/usr/bin/env python3
"""Quick unit tests for session context manager."""

import sys
import os
from datetime import datetime, timedelta

# Add hooks lib to path
sys.path.insert(0, os.path.dirname(__file__))

from session_context_manager import (
    TokenEstimator,
    AdaptiveFormatter,
    PrioritizationAlgorithm,
    SessionMemoryCache,
    SessionContextManager,
)


def test_token_estimator():
    """Test token estimation."""
    print("Testing TokenEstimator...")

    # ~4 chars per token
    assert TokenEstimator.estimate_tokens("hello world") == 2  # 11 chars // 4 = 2
    assert TokenEstimator.estimate_tokens("a" * 100) == 25  # 100 // 4 = 25

    truncated = TokenEstimator.truncate_to_budget("hello world test", max_tokens=2)
    assert len(truncated) <= 10  # 2 * 4 + "..."
    print("  ✓ Token estimation working")


def test_adaptive_formatter():
    """Test adaptive formatting based on relevance."""
    print("Testing AdaptiveFormatter...")

    # High relevance: full context
    high, high_tokens = AdaptiveFormatter.format_memory(
        memory_id="mem1",
        title="High Relevance Memory",
        content="This is a detailed memory about high relevance topics.",
        relevance_score=0.95,
        memory_type="implementation",
    )
    assert "[implementation]" in high
    assert "High Relevance Memory" in high
    print(f"  ✓ High relevance: {high_tokens} tokens")

    # Medium relevance: summary only
    med, med_tokens = AdaptiveFormatter.format_memory(
        memory_id="mem2",
        title="Medium Relevance Memory",
        content="This is a medium relevance memory with more content.",
        relevance_score=0.75,
        memory_type="procedure",
    )
    assert med_tokens <= high_tokens  # Summary should be smaller
    print(f"  ✓ Medium relevance: {med_tokens} tokens")

    # Low relevance: reference only
    low, low_tokens = AdaptiveFormatter.format_memory(
        memory_id="mem3",
        title="Low Relevance Memory",
        content="Low relevance content",
        relevance_score=0.5,
        memory_type="learning",
    )
    assert low_tokens <= med_tokens
    print(f"  ✓ Low relevance: {low_tokens} tokens")


def test_recency_decay():
    """Test recency decay calculation."""
    print("Testing PrioritizationAlgorithm recency decay...")

    now = datetime.utcnow()

    # 1 hour ago: max score
    recent = (now - timedelta(minutes=30)).isoformat()
    score = PrioritizationAlgorithm.calculate_recency_score(recent)
    assert score == 1.0
    print(f"  ✓ 30 min ago: {score}")

    # 1 week ago: 70%
    old = (now - timedelta(days=3)).isoformat()
    score = PrioritizationAlgorithm.calculate_recency_score(old)
    assert score == 0.7
    print(f"  ✓ 3 days ago: {score}")

    # 2 months ago: 30%
    very_old = (now - timedelta(days=60)).isoformat()
    score = PrioritizationAlgorithm.calculate_recency_score(very_old)
    assert score == 0.3
    print(f"  ✓ 60 days ago: {score}")


def test_composite_scoring():
    """Test composite score calculation."""
    print("Testing PrioritizationAlgorithm composite scoring...")

    # High relevance, recent, important, frequently accessed, successful
    score = PrioritizationAlgorithm.calculate_composite_score(
        semantic_similarity=0.9,
        timestamp_iso=datetime.utcnow().isoformat(),
        importance=0.9,
        access_frequency=10,
        success_indicator=True,
    )
    assert score > 0.85
    print(f"  ✓ High-quality memory: {score:.2f}")

    # Low relevance, old, not important
    score = PrioritizationAlgorithm.calculate_composite_score(
        semantic_similarity=0.3,
        timestamp_iso=(datetime.utcnow() - timedelta(days=90)).isoformat(),
        importance=0.2,
        access_frequency=1,
        success_indicator=False,
    )
    assert score < 0.5
    print(f"  ✓ Low-quality memory: {score:.2f}")


def test_session_cache_deduplication():
    """Test session memory cache deduplication."""
    print("Testing SessionMemoryCache deduplication...")

    cache = SessionMemoryCache("test_session_123")

    # First injection: should be allowed
    assert cache.should_inject("mem1") == True
    cache.mark_injected("mem1", 0.9, "content")

    # Immediate re-injection: should be skipped (deduplication)
    assert cache.should_inject("mem1") == False
    print("  ✓ Deduplication working (recent skipped)")

    # Different memory: should be allowed
    assert cache.should_inject("mem2") == True
    print("  ✓ New memory injection allowed")


def test_session_manager():
    """Test full session manager."""
    print("Testing SessionContextManager...")

    mgr = SessionContextManager("test_session_456")

    memories = [
        {
            "id": "mem1",
            "title": "Very Relevant Task",
            "content": "We were implementing JWT authentication.",
            "type": "implementation",
            "timestamp": datetime.utcnow().isoformat(),
            "relevance": 0.95,
            "composite_score": 0.95,
            "importance": 0.9,
            "access_count": 5,
            "success_indicator": True,
        },
        {
            "id": "mem2",
            "title": "Somewhat Relevant",
            "content": "We discussed database design.",
            "type": "learning",
            "timestamp": (datetime.utcnow() - timedelta(days=7)).isoformat(),
            "relevance": 0.6,
            "composite_score": 0.6,
            "importance": 0.5,
            "access_count": 2,
            "success_indicator": False,
        },
    ]

    # Format with token budget
    formatted, injected_ids, tokens = mgr.format_context_adaptive(
        memories=memories,
        max_tokens=300
    )

    assert len(injected_ids) > 0
    assert tokens > 0
    assert tokens <= 300
    print(f"  ✓ Formatted {len(injected_ids)} memories ({tokens} tokens)")

    stats = mgr.get_session_stats()
    assert stats['cache_stats']['unique_memories'] == len(injected_ids)
    print(f"  ✓ Session stats: {stats['cache_stats']}")


if __name__ == "__main__":
    print("\n=== Phase 3: Session Context Manager Tests ===\n")

    try:
        test_token_estimator()
        test_adaptive_formatter()
        test_recency_decay()
        test_composite_scoring()
        test_session_cache_deduplication()
        test_session_manager()

        print("\n✅ All Phase 3 tests passed!\n")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
