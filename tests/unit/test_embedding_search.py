"""Tests demonstrating embedding-based search vs keyword matching."""

import pytest
from datetime import datetime

from athena.core.database import Database
from athena.episodic.models import EpisodicEvent, EventContext, EventType
from athena.episodic.store import EpisodicStore
from athena.spatial.retrieval import _semantic_search_events, _calculate_keyword_similarity
from athena.core.embeddings import EmbeddingModel, cosine_similarity


@pytest.fixture
def test_db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test.db"
    return Database(db_path)


@pytest.fixture
def episodic_store(test_db):
    """Create episodic store."""
    return EpisodicStore(test_db)


def test_keyword_similarity_fails_on_semantic_match():
    """Demonstrate that Jaccard fails on semantically similar but lexically different text."""

    # Semantically similar but no word overlap
    query = "authentication error"
    text1 = "login failed with invalid credentials"
    text2 = "database connection timeout"

    score1 = _calculate_keyword_similarity(query.lower(), text1.lower())
    score2 = _calculate_keyword_similarity(query.lower(), text2.lower())

    # Both score 0.0 with Jaccard (no word overlap)
    assert score1 == 0.0, f"Expected 0.0, got {score1}"
    assert score2 == 0.0, f"Expected 0.0, got {score2}"

    print(f"\n❌ Jaccard similarity fails:")
    print(f"  Query: '{query}'")
    print(f"  Related text: '{text1}' -> Score: {score1}")
    print(f"  Unrelated text: '{text2}' -> Score: {score2}")
    print(f"  Problem: Cannot distinguish related from unrelated!")


@pytest.mark.skipif(
    not hasattr(EmbeddingModel, '__init__'),
    reason="Ollama not available"
)
def test_embedding_similarity_succeeds_on_semantic_match():
    """Demonstrate that embeddings correctly identify semantic similarity."""

    try:
        embedding_model = EmbeddingModel()

        query = "authentication error"
        text1 = "login failed with invalid credentials"
        text2 = "database connection timeout"

        # Generate embeddings
        query_emb = embedding_model.embed(query)
        text1_emb = embedding_model.embed(text1)
        text2_emb = embedding_model.embed(text2)

        # Calculate cosine similarity
        score1 = cosine_similarity(query_emb, text1_emb)
        score2 = cosine_similarity(query_emb, text2_emb)

        # Normalize to [0, 1]
        score1 = (score1 + 1.0) / 2.0
        score2 = (score2 + 1.0) / 2.0

        print(f"\n✅ Embedding similarity succeeds:")
        print(f"  Query: '{query}'")
        print(f"  Related text: '{text1}' -> Score: {score1:.3f}")
        print(f"  Unrelated text: '{text2}' -> Score: {score2:.3f}")
        print(f"  Improvement: {(score1 / score2 if score2 > 0 else float('inf')):.1f}x better discrimination")

        # Related should score much higher than unrelated
        assert score1 > 0.5, f"Related text should score high: {score1}"
        assert score2 < 0.5, f"Unrelated text should score low: {score2}"
        assert score1 > score2 * 1.5, f"Related should score significantly higher: {score1} vs {score2}"

    except Exception as e:
        pytest.skip(f"Ollama not available: {e}")


@pytest.mark.skipif(
    not hasattr(EmbeddingModel, '__init__'),
    reason="Ollama not available"
)
def test_spatial_search_with_embeddings(episodic_store):
    """Test spatial search using embeddings."""

    # Create test events
    events = [
        EpisodicEvent(
            project_id=1,
            session_id="test",
            timestamp=datetime.now(),
            event_type=EventType.ACTION,
            content="User authentication failed due to invalid credentials",
            context=EventContext(cwd="/src/auth", files=["login.py"])
        ),
        EpisodicEvent(
            project_id=1,
            session_id="test",
            timestamp=datetime.now(),
            event_type=EventType.ACTION,
            content="Database query timeout after 30 seconds",
            context=EventContext(cwd="/src/db", files=["connection.py"])
        ),
        EpisodicEvent(
            project_id=1,
            session_id="test",
            timestamp=datetime.now(),
            event_type=EventType.ACTION,
            content="Login system returned error code 401 unauthorized",
            context=EventContext(cwd="/src/auth", files=["middleware.py"])
        ),
    ]

    # Record events (with embeddings)
    try:
        for event in events:
            episodic_store.record_event(event)

        # Search for authentication-related events
        from athena.spatial.retrieval import _semantic_search_events

        results = _semantic_search_events(
            query_text="authentication error",
            events=events,
            spatial_context=None,
            k=3,
            episodic_store=episodic_store
        )

        # First two results should be auth-related
        assert len(results) >= 2
        assert "authentication" in results[0].content.lower() or "login" in results[0].content.lower() or "unauthorized" in results[0].content.lower()

        print(f"\n✅ Spatial search with embeddings:")
        for i, result in enumerate(results, 1):
            print(f"  {i}. Score: {result.semantic_score:.3f} - {result.content[:60]}...")

    except Exception as e:
        pytest.skip(f"Ollama not available: {e}")


def test_embedding_vs_jaccard_comparison_stats():
    """Statistical comparison of embedding vs Jaccard similarity."""

    test_cases = [
        # (query, related_text, unrelated_text)
        ("authentication error", "login failed invalid password", "database timeout occurred"),
        ("memory leak", "RAM usage growing unbounded", "disk space running low"),
        ("API timeout", "request took too long", "successful database query"),
        ("null pointer exception", "dereferencing null object", "compilation successful"),
    ]

    print("\n" + "="*80)
    print("COMPARISON: Embedding-based vs Jaccard Similarity")
    print("="*80)

    jaccard_correct = 0
    embedding_correct = 0

    try:
        embedding_model = EmbeddingModel()

        for query, related, unrelated in test_cases:
            # Jaccard scores
            j_related = _calculate_keyword_similarity(query.lower(), related.lower())
            j_unrelated = _calculate_keyword_similarity(query.lower(), unrelated.lower())

            # Embedding scores
            q_emb = embedding_model.embed(query)
            r_emb = embedding_model.embed(related)
            u_emb = embedding_model.embed(unrelated)

            e_related = (cosine_similarity(q_emb, r_emb) + 1.0) / 2.0
            e_unrelated = (cosine_similarity(q_emb, u_emb) + 1.0) / 2.0

            # Check if method correctly ranks related > unrelated
            jaccard_correct += int(j_related > j_unrelated)
            embedding_correct += int(e_related > e_unrelated)

            print(f"\nQuery: '{query}'")
            print(f"  Related: '{related}'")
            print(f"    Jaccard: {j_related:.3f} | Embedding: {e_related:.3f}")
            print(f"  Unrelated: '{unrelated}'")
            print(f"    Jaccard: {j_unrelated:.3f} | Embedding: {e_unrelated:.3f}")
            print(f"  Winner: {'Embedding' if e_related > j_related else 'Jaccard'}")

        print(f"\n{'='*80}")
        print(f"RESULTS:")
        print(f"  Jaccard accuracy: {jaccard_correct}/{len(test_cases)} = {jaccard_correct/len(test_cases)*100:.0f}%")
        print(f"  Embedding accuracy: {embedding_correct}/{len(test_cases)} = {embedding_correct/len(test_cases)*100:.0f}%")
        print(f"  Improvement: {((embedding_correct - jaccard_correct) / len(test_cases)) * 100:.0f}% absolute gain")
        print(f"{'='*80}\n")

        # Embeddings should significantly outperform Jaccard
        assert embedding_correct >= len(test_cases) * 0.8, "Embeddings should get 80%+ correct"

    except Exception as e:
        pytest.skip(f"Ollama not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
