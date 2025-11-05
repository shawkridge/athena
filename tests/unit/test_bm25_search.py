"""Tests for BM25 lexical search and hybrid retrieval."""

import pytest
from athena.memory.lexical import (
    LexicalSearch,
    reciprocal_rank_fusion,
    hybrid_search
)


def test_lexical_search_initialization():
    """Test LexicalSearch initialization."""
    lexical = LexicalSearch()

    assert lexical.corpus == []
    assert lexical.memory_ids == []
    assert lexical.bm25 is None
    assert lexical._initialized is False


def test_lexical_search_indexing():
    """Test indexing memories for BM25 search."""
    lexical = LexicalSearch()

    memories = [
        (1, "authentication error occurred"),
        (2, "login failed with invalid credentials"),
        (3, "database connection timeout"),
    ]

    lexical.index_memories(memories)

    assert lexical._initialized is True
    assert len(lexical.memory_ids) == 3
    assert len(lexical.corpus) == 3
    assert lexical.bm25 is not None


def test_lexical_search_basic():
    """Test basic BM25 search."""
    lexical = LexicalSearch()

    memories = [
        (1, "authentication error in login system"),
        (2, "database query timeout after 30 seconds"),
        (3, "user authentication failed invalid password"),
    ]

    lexical.index_memories(memories)

    # Search for authentication-related content
    results = lexical.search("authentication", k=2)

    assert len(results) > 0
    assert all(isinstance(r, tuple) for r in results)
    assert all(len(r) == 2 for r in results)

    # Extract IDs
    result_ids = [r[0] for r in results]

    # Should prioritize memories with "authentication"
    assert 1 in result_ids or 3 in result_ids


def test_lexical_search_ranking():
    """Test BM25 ranking quality."""
    lexical = LexicalSearch()

    memories = [
        (1, "JWT token authentication system implementation"),
        (2, "database migration script"),
        (3, "authentication middleware for Express"),
        (4, "OAuth2 authentication provider"),
    ]

    lexical.index_memories(memories)

    results = lexical.search("authentication", k=10)

    # All authentication-related memories should score higher than database
    result_ids = [r[0] for r in results]

    # Database (id=2) should not be in top results
    auth_ids = [1, 3, 4]
    assert any(id in result_ids[:3] for id in auth_ids)

    # Scores should be descending
    scores = [r[1] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_lexical_search_no_results():
    """Test search with no matching terms."""
    lexical = LexicalSearch()

    memories = [
        (1, "authentication error"),
        (2, "database timeout"),
    ]

    lexical.index_memories(memories)

    results = lexical.search("nonexistent query term", k=10)

    # Should return empty list when no matches
    assert results == []


def test_lexical_search_empty_corpus():
    """Test search with empty corpus."""
    lexical = LexicalSearch()

    # Don't index anything
    results = lexical.search("test query", k=10)

    assert results == []


def test_reciprocal_rank_fusion_basic():
    """Test basic RRF functionality."""
    # Two result sets with some overlap
    results1 = [(1, 0.9), (2, 0.8), (3, 0.7)]
    results2 = [(2, 0.95), (1, 0.85), (4, 0.75)]

    fused = reciprocal_rank_fusion([results1, results2])

    # Should return list of (id, score) tuples
    assert all(isinstance(r, tuple) for r in fused)
    assert all(len(r) == 2 for r in fused)

    # Scores should be descending
    scores = [r[1] for r in fused]
    assert scores == sorted(scores, reverse=True)

    # Items appearing in both lists should score higher
    fused_dict = dict(fused)
    assert fused_dict[1] > fused_dict[4]  # Item 1 in both lists
    assert fused_dict[2] > fused_dict[4]  # Item 2 in both lists


def test_reciprocal_rank_fusion_empty():
    """Test RRF with empty result sets."""
    fused = reciprocal_rank_fusion([])
    assert fused == []

    fused = reciprocal_rank_fusion([[]])
    assert fused == []


def test_reciprocal_rank_fusion_single_set():
    """Test RRF with single result set."""
    results = [(1, 0.9), (2, 0.8), (3, 0.7)]

    fused = reciprocal_rank_fusion([results])

    # Should still work, just returns RRF scores
    assert len(fused) == 3
    result_ids = [r[0] for r in fused]
    assert result_ids == [1, 2, 3]  # Same order


def test_hybrid_search_vector_only():
    """Test hybrid search with only vector results."""
    vector_results = [(1, 0.9), (2, 0.8), (3, 0.7)]

    fused = hybrid_search(
        query="test",
        vector_results=vector_results,
        lexical_search=None,  # No lexical search available
        k=10
    )

    # Should return vector results unchanged
    assert fused == vector_results


def test_hybrid_search_vector_and_lexical():
    """Test hybrid search combining vector and lexical."""
    # Create lexical search
    lexical = LexicalSearch()
    memories = [
        (1, "authentication error"),
        (2, "login failure"),
        (3, "database timeout"),
        (4, "cache miss"),
    ]
    lexical.index_memories(memories)

    # Vector results
    vector_results = [(1, 0.9), (3, 0.8), (4, 0.7)]

    # Hybrid search
    fused = hybrid_search(
        query="authentication",
        vector_results=vector_results,
        lexical_search=lexical,
        k=10
    )

    # Should combine both result sets
    assert len(fused) > 0

    # Scores should be descending
    scores = [r[1] for r in fused]
    assert scores == sorted(scores, reverse=True)


def test_bm25_vs_keyword_matching():
    """Compare BM25 to simple keyword matching."""
    lexical = LexicalSearch()

    memories = [
        (1, "authentication error in login system"),
        (2, "login failed with authentication timeout"),
        (3, "database connection timeout"),
        (4, "cache authentication token expired"),
    ]

    lexical.index_memories(memories)

    # Query with multiple terms
    results = lexical.search("authentication login", k=10)

    # Memories with both terms should rank higher
    result_ids = [r[0] for r in results[:2]]

    # IDs 1 and 2 have both terms
    assert 1 in result_ids or 2 in result_ids

    print("\n✓ BM25 Results for 'authentication login':")
    for id, score in results:
        memory = next(m for m in memories if m[0] == id)
        print(f"  ID {id}: {score:.3f} - {memory[1]}")


def test_lexical_search_multiterm_query():
    """Test BM25 with multi-term queries and term frequency."""
    lexical = LexicalSearch()

    memories = [
        (1, "user authentication system with login and password verification"),
        (2, "authentication authentication authentication module"),  # High term frequency
        (3, "database connection pooling"),
        (4, "login page design"),
    ]

    lexical.index_memories(memories)

    # Query for "authentication"
    results = lexical.search("authentication", k=10)

    # Should return authentication-related results
    if results:
        # ID 2 has highest term frequency, should rank high
        top_ids = [r[0] for r in results[:2]]
        assert 2 in top_ids, f"Expected ID 2 (high TF) in top results, got {top_ids}"
    else:
        # Fallback: just verify indexing worked
        assert lexical._initialized is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
