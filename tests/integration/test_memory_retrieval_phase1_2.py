"""
Integration tests for Memory Retrieval System - Phase 1 & 2.

Tests auto context injection, conversation history, attention-based ranking,
graph traversal, temporal queries, and spatial context integration.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

from athena.core.database import Database
from athena.rag.context_injector import ContextInjector, ContextMemory
from athena.rag.manager import RAGManager
from athena.rag.graph_traversal import GraphTraversal
from athena.rag.temporal_queries import TemporalQueries
from athena.rag.spatial_context import SpatialContextIntegration


@pytest.fixture
def db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    return db


@pytest.fixture
def rag_manager(db):
    """Create RAG manager."""
    return RAGManager(db)


@pytest.fixture
def context_injector(db, rag_manager):
    """Create context injector."""
    return ContextInjector(
        db=db,
        rag_manager=rag_manager,
        token_budget=1000,
        min_usefulness=0.4,
        max_memories=5,
    )


class TestPhase1AutoContextInjection:
    """Test Phase 1: Auto context injection."""

    @pytest.mark.asyncio
    async def test_inject_context_success(self, context_injector):
        """Test successful context injection."""
        result = await context_injector.inject_context(
            user_prompt="How do I debug authentication issues?"
        )

        # Should return a ContextInjection with proper structure
        assert result is not None
        assert isinstance(result.total_tokens, int)
        assert isinstance(result.injection_confidence, float)
        assert isinstance(result.memories, list)

    @pytest.mark.asyncio
    async def test_inject_context_with_conversation_history(self, context_injector):
        """Test context injection with conversation history."""
        conversation = [
            {"role": "user", "content": "I'm debugging authentication"},
            {"role": "assistant", "content": "Here are the key JWT concepts..."},
            {"role": "user", "content": "What about it?"},
        ]

        result = await context_injector.inject_context(
            user_prompt="What about it?",
            conversation_history=conversation,
        )

        assert result is not None
        # Should augment query with previous context
        assert result.formatted_context is not None

    @pytest.mark.asyncio
    async def test_inject_context_respects_token_budget(self, context_injector):
        """Test that injection respects token budget."""
        context_injector.token_budget = 100  # Very small budget

        result = await context_injector.inject_context(
            user_prompt="Debug authentication"
        )

        # Should not exceed token budget
        assert result.total_tokens <= 100 + 10  # Small margin

    @pytest.mark.asyncio
    async def test_should_inject_context_frequency_control(self, context_injector):
        """Test frequency control for context injection."""
        prompt = "Test query"

        # First prompt should inject
        should_inject = await context_injector.should_inject_context(
            user_prompt=prompt,
            recent_injections=0,
        )
        assert should_inject is True

        # After injections, should skip some
        should_inject = await context_injector.should_inject_context(
            user_prompt=prompt,
            recent_injections=1,
        )
        # May skip depending on frequency control logic
        assert isinstance(should_inject, bool)

    def test_format_injection_for_claude(self, context_injector):
        """Test formatting injection for Claude."""
        from athena.rag.context_injector import ContextInjection

        memories = [
            ContextMemory(
                content="JWT authentication pattern",
                source_layer="semantic",
                usefulness=0.8,
                relevance=0.9,
                recency=0.7,
            )
        ]

        injection = ContextInjection(
            memories=memories,
            total_tokens=50,
            formatted_context="📚 Background Context...",
            injection_confidence=0.85,
        )

        formatted = context_injector.format_injection_for_claude(injection)

        assert "Background Context" in formatted
        assert "85%" in formatted

    def test_augment_query_with_history(self, context_injector):
        """Test query augmentation with conversation history."""
        conversation = [
            {"role": "assistant", "content": "JWT tokens are..."},
            {"role": "user", "content": "How is it used?"},
        ]

        augmented = context_injector._augment_query_with_history(
            "How is it used?",
            conversation,
        )

        # Should include previous context for pronoun resolution
        assert len(augmented) >= len("How is it used?")


class TestPhase1ConversationHistoryIntegration:
    """Test Phase 1: Conversation history integration."""

    def test_augment_with_pronouns(self, context_injector):
        """Test pronoun resolution with conversation history."""
        conversation = [
            {"role": "assistant", "content": "Authentication uses JWT tokens"},
            {"role": "user", "content": "Tell me about that"},
        ]

        augmented = context_injector._augment_query_with_history(
            "Tell me about that",
            conversation,
        )

        # Should detect pronoun "that" and augment with previous context
        assert "JWT" in augmented or "authentication" in augmented.lower()

    def test_augment_without_pronouns(self, context_injector):
        """Test that augmentation doesn't change explicit queries."""
        augmented = context_injector._augment_query_with_history(
            "How does JWT authentication work?",
            None,
        )

        # Should return original if no pronouns
        assert augmented == "How does JWT authentication work?"

    def test_augment_empty_history(self, context_injector):
        """Test augmentation with empty history."""
        augmented = context_injector._augment_query_with_history(
            "What is that?",
            [],
        )

        # Should return original if no history
        assert augmented == "What is that?"


class TestPhase1AttentionBasedRanking:
    """Test Phase 1: Attention-based ranking."""

    def test_rank_memories_composite_score(self, context_injector):
        """Test memory ranking with composite score."""
        memories = [
            ContextMemory(
                content="High usefulness memory",
                source_layer="semantic",
                usefulness=0.9,
                relevance=0.8,
                recency=0.7,
            ),
            ContextMemory(
                content="Low usefulness memory",
                source_layer="semantic",
                usefulness=0.2,
                relevance=0.9,
                recency=0.9,
            ),
            ContextMemory(
                content="Medium usefulness memory",
                source_layer="semantic",
                usefulness=0.6,
                relevance=0.6,
                recency=0.6,
            ),
        ]

        ranked = context_injector._rank_memories(memories)

        # Should rank by composite score (0.35*useful + 0.35*relevant + 0.15*recency + 0.15*attention)
        assert len(ranked) >= 2  # At least keep medium and high
        # High usefulness should rank higher
        assert ranked[0].usefulness >= 0.6

    def test_rank_respects_min_usefulness(self, context_injector):
        """Test that ranking respects min usefulness threshold."""
        context_injector.min_usefulness = 0.5

        memories = [
            ContextMemory(
                content="High quality",
                source_layer="semantic",
                usefulness=0.9,
                relevance=0.8,
                recency=0.7,
            ),
            ContextMemory(
                content="Low quality",
                source_layer="semantic",
                usefulness=0.3,
                relevance=0.9,
                recency=0.9,
            ),
        ]

        ranked = context_injector._rank_memories(memories)

        # Should filter out low usefulness
        assert len(ranked) == 1
        assert ranked[0].usefulness == 0.9

    def test_get_attention_scores_graceful_degradation(self, context_injector):
        """Test attention scores with graceful degradation."""
        scores = context_injector._get_attention_scores()

        # Should return dict even if tables don't exist
        assert isinstance(scores, dict)
        assert "primary_focus" in scores or len(scores) == 0


class TestPhase2GraphTraversal:
    """Test Phase 2: Graph traversal."""

    def test_graph_traversal_initialization(self, db):
        """Test graph traversal initialization."""
        traversal = GraphTraversal(db, max_depth=2, max_results=10)

        assert traversal.db is not None
        assert traversal.max_depth == 2
        assert traversal.max_results == 10

    @pytest.mark.asyncio
    async def test_find_related_context_no_entity(self, db):
        """Test finding context for non-existent entity."""
        traversal = GraphTraversal(db)

        result = await traversal.find_related_context("NonExistentEntity")

        # Should return empty result gracefully
        assert result.root_entity is None
        assert len(result.related_entities) == 0

    @pytest.mark.asyncio
    async def test_find_similar_entities(self, db):
        """Test finding similar entities."""
        traversal = GraphTraversal(db)

        similar = await traversal.find_similar_entities(
            entity_type="Component",
            limit=5,
        )

        # Should return list (may be empty if no entities)
        assert isinstance(similar, list)

    def test_calculate_richness_score(self, db):
        """Test richness score calculation."""
        from athena.rag.graph_traversal import GraphEntity

        traversal = GraphTraversal(db)

        root = GraphEntity(entity_id=1, name="Test", entity_type="Component")
        related = [
            GraphEntity(entity_id=i, name=f"Related{i}", entity_type="Component")
            for i in range(2, 6)
        ]
        relations = []

        richness = traversal._calculate_richness(root, related, relations)

        assert 0.0 <= richness <= 1.0
        assert richness > 0.4  # Should have decent richness with 4 related entities


class TestPhase2TemporalQueries:
    """Test Phase 2: Temporal queries."""

    def test_temporal_queries_initialization(self, db):
        """Test temporal queries initialization."""
        temporal = TemporalQueries(db)

        assert temporal.db is not None

    @pytest.mark.asyncio
    async def test_find_causal_sequence_not_found(self, db):
        """Test finding causal sequence for non-existent event."""
        temporal = TemporalQueries(db)

        sequence = await temporal.find_causal_sequence("NonExistentEvent")

        assert sequence is None

    @pytest.mark.asyncio
    async def test_find_temporal_pattern(self, db):
        """Test finding temporal patterns."""
        temporal = TemporalQueries(db)

        pattern = await temporal.find_temporal_pattern(
            pattern_description="Debug event",
            time_window=timedelta(days=7),
        )

        # Should return pattern dict
        assert isinstance(pattern, dict)
        assert "pattern" in pattern
        assert "occurrences" in pattern

    def test_calculate_causal_strength(self, db):
        """Test causal strength calculation."""
        from athena.rag.temporal_queries import TemporalEvent

        temporal = TemporalQueries(db)

        now = datetime.utcnow()
        events = [
            TemporalEvent(
                event_id=1,
                content="Event 1",
                event_type="action",
                timestamp=now,
                session_id="test",
                outcome="success",
            ),
            TemporalEvent(
                event_id=2,
                content="Event 2",
                event_type="action",
                timestamp=now + timedelta(minutes=2),
                session_id="test",
                outcome="success",
            ),
        ]

        strength = temporal._calculate_causal_strength(events)

        assert 0.0 <= strength <= 1.0
        assert strength > 0.7  # Close in time with success = high strength


class TestPhase2SpatialContext:
    """Test Phase 2: Spatial context."""

    def test_spatial_context_initialization(self, db):
        """Test spatial context initialization."""
        spatial = SpatialContextIntegration(db, cwd="/home/user/project")

        assert spatial.db is not None
        assert spatial.cwd == Path("/home/user/project")

    def test_analyze_spatial_context(self, db):
        """Test spatial context analysis."""
        spatial = SpatialContextIntegration(db)

        context = spatial.analyze_spatial_context("src/auth/jwt.py")

        assert context.file_path == "src/auth/jwt.py"
        assert context.depth == 3
        assert context.component == "auth"

    def test_analyze_spatial_context_empty(self, db):
        """Test spatial context analysis with empty path."""
        spatial = SpatialContextIntegration(db)

        context = spatial.analyze_spatial_context(None)

        assert context.file_path == ""
        assert context.depth == 0

    def test_calculate_spatial_proximity_same_component(self, db):
        """Test proximity calculation for same component."""
        spatial = SpatialContextIntegration(db)

        from athena.rag.spatial_context import SpatialContext

        context_a = SpatialContext(
            file_path="src/auth/jwt.py",
            directory="src/auth",
            depth=3,
            component="auth",
        )
        context_b = SpatialContext(
            file_path="src/auth/session.py",
            directory="src/auth",
            depth=3,
            component="auth",
        )

        proximity = spatial.calculate_spatial_proximity(context_a, context_b)

        assert proximity == 1.0  # Same component

    def test_calculate_spatial_proximity_different_component(self, db):
        """Test proximity calculation for different components."""
        spatial = SpatialContextIntegration(db)

        from athena.rag.spatial_context import SpatialContext

        context_a = SpatialContext(
            file_path="src/auth/jwt.py",
            directory="src/auth",
            depth=3,
            component="auth",
        )
        context_b = SpatialContext(
            file_path="src/api/routes.py",
            directory="src/api",
            depth=3,
            component="api",
        )

        proximity = spatial.calculate_spatial_proximity(context_a, context_b)

        assert proximity == 0.5  # Different components, same root

    def test_find_memories_in_spatial_context(self, db):
        """Test finding memories in spatial context."""
        spatial = SpatialContextIntegration(db)

        from athena.rag.spatial_context import SpatialContext

        context = SpatialContext(
            file_path="src/auth/jwt.py",
            directory="src/auth",
            depth=3,
            component="auth",
        )

        memories = spatial.find_memories_in_spatial_context(context)

        # Should return list (may be empty if no memories)
        assert isinstance(memories, list)

    def test_weight_memory_by_proximity(self, db):
        """Test memory weighting by proximity."""
        spatial = SpatialContextIntegration(db)

        from athena.rag.spatial_context import SpatialContext

        memories = [
            {
                "id": 1,
                "content": "Auth memory",
                "usefulness": 0.6,
                "file_path": "src/auth/jwt.py",
            }
        ]

        current_context = SpatialContext(
            file_path="src/auth/session.py",
            directory="src/auth",
            depth=3,
            component="auth",
        )

        weighted = spatial.weight_memory_by_proximity(memories, current_context)

        # Same component should get boost
        assert weighted[0]["usefulness"] >= 0.6
        assert weighted[0]["spatial_boost"] > 0

    def test_build_spatial_context_hierarchy(self, db):
        """Test building spatial hierarchy."""
        spatial = SpatialContextIntegration(db)

        hierarchy = spatial.build_spatial_context_hierarchy("/home/project")

        assert hierarchy is not None
        assert "root" in hierarchy
        assert "components" in hierarchy
        assert "total_files" in hierarchy


class TestEndToEndMemoryRetrieval:
    """End-to-end tests for complete memory retrieval."""

    @pytest.mark.asyncio
    async def test_complete_memory_injection_pipeline(self, context_injector):
        """Test complete context injection pipeline."""
        # Simulate user prompt
        user_prompt = "How do I debug authentication?"
        conversation_history = [
            {
                "role": "user",
                "content": "I'm having issues with JWT tokens"
            },
            {
                "role": "assistant",
                "content": "JWT tokens require proper validation..."
            },
        ]

        # Inject context
        result = await context_injector.inject_context(
            user_prompt=user_prompt,
            conversation_history=conversation_history,
        )

        # Verify result structure
        assert result is not None
        assert hasattr(result, "memories")
        assert hasattr(result, "formatted_context")
        assert hasattr(result, "injection_confidence")

    def test_phase1_2_integration_markers(self):
        """Verify Phase 1 & 2 are properly integrated."""
        # Phase 1: Auto context injection
        assert ContextInjector is not None

        # Phase 2: Enhanced retrieval
        assert GraphTraversal is not None
        assert TemporalQueries is not None
        assert SpatialContextIntegration is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
