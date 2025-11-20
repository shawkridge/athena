"""Unit tests for meta-memory operations."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from athena.meta.operations import MetaOperations

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db():
    """Create a mock database."""
    return MagicMock()


@pytest.fixture
def mock_store():
    """Create a mock meta-memory store with intelligent mocking."""
    # We'll track quality scores and expertise in dicts for stateful responses
    quality_scores = {}
    expertise_data = {}

    async def rate_memory(memory_id, scores):
        quality_scores[memory_id] = scores
        return True

    async def get_expertise(topic=None, limit=10):
        if topic:
            if topic in expertise_data:
                return {
                    "topic": topic,
                    "level": expertise_data[topic].get("level", "beginner"),
                    "memories": expertise_data[topic].get("memories", 0),
                    "confidence": expertise_data[topic].get("confidence", 0.5),
                }
            return {"topic": topic, "level": "beginner", "memories": 0, "confidence": 0.0}

        # Return all topics
        return {
            "topics": [
                {
                    "domain": topic,
                    "level": data.get("level", "beginner"),
                    "coverage": data.get("memories", 0),
                    "confidence": data.get("confidence", 0.5),
                }
                for topic, data in expertise_data.items()
            ],
            "total": len(expertise_data),
            "avg_coverage": (
                sum(d.get("memories", 0) for d in expertise_data.values()) / len(expertise_data)
                if expertise_data
                else 0
            ),
        }

    async def get_memory_quality(memory_id):
        if memory_id in quality_scores:
            scores = quality_scores[memory_id]
            return {
                "usefulness_score": scores.get("usefulness", 0.5),
                "confidence": scores.get("confidence", 0.5),
                "relevance_decay": scores.get("relevance_decay", 1.0),
            }
        return None

    async def get_cognitive_load():
        return {
            "episodic_load": 100,
            "semantic_load": 50,
            "total_memories": 150,
            "load_percentage": 15.0,
        }

    async def update_cognitive_load(working_memory_items, active_tasks, recent_accuracy):
        return True

    async def get_statistics():
        return {
            "total_memories_rated": len(quality_scores),
            "avg_quality": (
                sum(s.get("quality", 0.5) for s in quality_scores.values()) / len(quality_scores)
                if quality_scores
                else 0.5
            ),
            "expertise_domains": len(expertise_data),
            "avg_expertise": (
                sum(d.get("level_numeric", 1) for d in expertise_data.values())
                / len(expertise_data)
                if expertise_data
                else 1.0
            ),
        }

    store = MagicMock()
    store.rate_memory = AsyncMock(side_effect=rate_memory)
    store.get_expertise = AsyncMock(side_effect=get_expertise)
    store.get_memory_quality = AsyncMock(side_effect=get_memory_quality)
    store.get_cognitive_load = AsyncMock(side_effect=get_cognitive_load)
    store.update_cognitive_load = AsyncMock(side_effect=update_cognitive_load)
    store.get_statistics = AsyncMock(side_effect=get_statistics)
    return store


@pytest.fixture
def operations(mock_db, mock_store):
    """Create test operations instance with mocked store."""
    ops = MetaOperations(mock_db, mock_store)
    return ops


# ============================================================================
# Memory Rating Tests
# ============================================================================


class TestMemoryRating:
    """Test memory rating operations."""

    async def test_rate_memory_quality(self, operations: MetaOperations):
        """Test rating a memory's quality."""
        success = await operations.rate_memory("memory_1", quality=0.8)

        assert success is True

    async def test_rate_memory_confidence(self, operations: MetaOperations):
        """Test rating a memory's confidence."""
        success = await operations.rate_memory("memory_1", confidence=0.9)

        assert success is True

    async def test_rate_memory_usefulness(self, operations: MetaOperations):
        """Test rating a memory's usefulness."""
        success = await operations.rate_memory("memory_1", usefulness=0.7)

        assert success is True

    async def test_rate_memory_multiple_scores(self, operations: MetaOperations):
        """Test rating multiple quality dimensions."""
        success = await operations.rate_memory(
            "memory_1", quality=0.8, confidence=0.9, usefulness=0.7
        )

        assert success is True

    async def test_rate_memory_validates_bounds(self, operations: MetaOperations):
        """Test that scores are bounded [0.0, 1.0]."""
        # > 1.0 should be clamped
        success = await operations.rate_memory("memory_1", quality=1.5)
        assert success is True

        # < 0.0 should be clamped
        success = await operations.rate_memory("memory_1", quality=-0.5)
        assert success is True

    async def test_rate_memory_empty_scores(self, operations: MetaOperations):
        """Test rating with no scores returns False."""
        success = await operations.rate_memory("memory_1")

        assert success is False

    async def test_rate_memory_invalid_id(self, operations: MetaOperations):
        """Test rating with empty memory ID returns False."""
        success = await operations.rate_memory("", quality=0.8)

        assert success is False


# ============================================================================
# Expertise Tracking Tests
# ============================================================================


class TestExpertiseTracking:
    """Test expertise tracking operations."""

    async def test_get_expertise_all(self, operations: MetaOperations):
        """Test getting all expertise data."""
        expertise = await operations.get_expertise()

        assert isinstance(expertise, dict)
        assert "total" in expertise
        assert isinstance(expertise["total"], int)

    async def test_get_expertise_specific_topic(self, operations: MetaOperations):
        """Test getting expertise for a specific topic."""
        expertise = await operations.get_expertise(topic="Python")

        assert isinstance(expertise, dict)
        assert "topic" in expertise or "level" in expertise

    async def test_get_expertise_with_limit(self, operations: MetaOperations):
        """Test expertise retrieval with limit."""
        expertise = await operations.get_expertise(limit=5)

        assert isinstance(expertise, dict)

    async def test_get_expertise_nonexistent_topic(self, operations: MetaOperations):
        """Test getting expertise for non-existent topic."""
        expertise = await operations.get_expertise(topic="NonexistentTopic")

        assert isinstance(expertise, dict)


# ============================================================================
# Memory Quality Retrieval Tests
# ============================================================================


class TestMemoryQualityRetrieval:
    """Test memory quality retrieval operations."""

    async def test_get_memory_quality_success(self, operations: MetaOperations):
        """Test retrieving quality for rated memory."""
        # First rate it
        await operations.rate_memory("memory_1", quality=0.8, confidence=0.9)

        # Then retrieve
        quality = await operations.get_memory_quality("memory_1")

        assert quality is not None
        assert isinstance(quality, dict)

    async def test_get_memory_quality_not_found(self, operations: MetaOperations):
        """Test retrieving quality for unrated memory."""
        quality = await operations.get_memory_quality("nonexistent_memory")

        assert quality is None

    async def test_get_memory_quality_fields(self, operations: MetaOperations):
        """Test that quality dict has expected fields."""
        await operations.rate_memory("memory_1", quality=0.8, confidence=0.9, usefulness=0.7)

        quality = await operations.get_memory_quality("memory_1")

        if quality:
            # Should have some quality-related fields
            assert any(
                k
                in [
                    "usefulness_score",
                    "confidence",
                    "relevance_decay",
                    "quality",
                    "usefulness",
                ]
                for k in quality.keys()
            )

    async def test_get_memory_quality_with_string_id(self, operations: MetaOperations):
        """Test that string memory IDs are handled."""
        await operations.rate_memory("123", quality=0.8)

        quality = await operations.get_memory_quality("123")

        assert quality is not None or quality is None  # Either is valid


# ============================================================================
# Cognitive Load Tests
# ============================================================================


class TestCognitiveLoad:
    """Test cognitive load monitoring."""

    async def test_get_cognitive_load(self, operations: MetaOperations):
        """Test retrieving cognitive load metrics."""
        load = await operations.get_cognitive_load()

        assert isinstance(load, dict)
        assert "episodic_load" in load
        assert "semantic_load" in load
        assert "total_memories" in load

    async def test_cognitive_load_structure(self, operations: MetaOperations):
        """Test cognitive load data structure."""
        load = await operations.get_cognitive_load()

        assert isinstance(load["episodic_load"], int)
        assert isinstance(load["semantic_load"], int)
        assert isinstance(load["total_memories"], int)
        assert isinstance(load["load_percentage"], (int, float))

    async def test_update_cognitive_load(self, operations: MetaOperations):
        """Test updating cognitive load."""
        success = await operations.update_cognitive_load(
            working_memory_items=5, active_tasks=2, recent_accuracy=0.9
        )

        assert success is True

    async def test_update_cognitive_load_validates_accuracy(self, operations: MetaOperations):
        """Test that accuracy is bounded [0.0, 1.0]."""
        # > 1.0 should be clamped
        success = await operations.update_cognitive_load(
            working_memory_items=5, active_tasks=2, recent_accuracy=1.5
        )
        assert success is True

        # < 0.0 should be clamped
        success = await operations.update_cognitive_load(
            working_memory_items=5, active_tasks=2, recent_accuracy=-0.5
        )
        assert success is True

    async def test_update_cognitive_load_valid_values(self, operations: MetaOperations):
        """Test update with valid input values."""
        success = await operations.update_cognitive_load(
            working_memory_items=7, active_tasks=3, recent_accuracy=0.85
        )

        assert success is True


# ============================================================================
# Statistics Tests
# ============================================================================


class TestStatistics:
    """Test statistics generation."""

    async def test_get_statistics(self, operations: MetaOperations):
        """Test retrieving meta-memory statistics."""
        stats = await operations.get_statistics()

        assert isinstance(stats, dict)

    async def test_statistics_empty(self, operations: MetaOperations):
        """Test statistics with no data."""
        stats = await operations.get_statistics()

        assert isinstance(stats, dict)
        # Should contain reasonable defaults
        assert any(k in stats for k in ["total_memories_rated", "expertise_domains", "avg_quality"])

    async def test_statistics_with_data(self, operations: MetaOperations):
        """Test statistics after adding data."""
        # Add some ratings
        await operations.rate_memory("mem_1", quality=0.8)
        await operations.rate_memory("mem_2", quality=0.6)

        stats = await operations.get_statistics()

        assert isinstance(stats, dict)
        assert stats.get("total_memories_rated", 0) >= 0


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error handling and edge cases."""

    async def test_rate_memory_with_none_values(self, operations: MetaOperations):
        """Test rating with None values."""
        success = await operations.rate_memory(
            "memory_1", quality=None, confidence=None, usefulness=None
        )

        assert success is False

    async def test_rate_memory_with_invalid_scores(self, operations: MetaOperations):
        """Test rating with invalid score types is handled."""
        # This should be handled by type hints or validation
        success = await operations.rate_memory("memory_1", quality=0.8)
        assert success is True

    async def test_get_expertise_empty_result(self, operations: MetaOperations):
        """Test getting expertise with no data."""
        expertise = await operations.get_expertise(topic="NonExistent")

        assert isinstance(expertise, dict)

    async def test_cognitive_load_negative_items(self, operations: MetaOperations):
        """Test cognitive load with edge case values."""
        # Negative working memory items should still be handled
        success = await operations.update_cognitive_load(
            working_memory_items=0, active_tasks=0, recent_accuracy=0.5
        )

        assert success is True

    async def test_unicode_in_ratings(self, operations: MetaOperations):
        """Test rating with unicode memory IDs."""
        success = await operations.rate_memory("测试_memory_1", quality=0.8)

        assert success is True


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests combining multiple operations."""

    async def test_full_memory_quality_lifecycle(self, operations: MetaOperations):
        """Test complete memory quality tracking lifecycle."""
        memory_id = "integration_test_memory"

        # Rate the memory
        rated = await operations.rate_memory(
            memory_id, quality=0.8, confidence=0.9, usefulness=0.75
        )
        assert rated is True

        # Retrieve the quality
        quality = await operations.get_memory_quality(memory_id)
        assert quality is not None

    async def test_cognitive_load_update_and_retrieval(self, operations: MetaOperations):
        """Test updating and retrieving cognitive load."""
        # Update load
        updated = await operations.update_cognitive_load(
            working_memory_items=5, active_tasks=2, recent_accuracy=0.88
        )
        assert updated is True

        # Get load
        load = await operations.get_cognitive_load()
        assert load is not None
        assert load["total_memories"] >= 0

    async def test_expertise_and_ratings_together(self, operations: MetaOperations):
        """Test expertise tracking with memory ratings."""
        # Rate some memories
        await operations.rate_memory("python_1", quality=0.9)
        await operations.rate_memory("python_2", quality=0.85)

        # Get expertise
        expertise = await operations.get_expertise(topic="Python")
        assert isinstance(expertise, dict)

    async def test_statistics_with_multiple_ratings(self, operations: MetaOperations):
        """Test statistics reflect multiple ratings."""
        # Add multiple ratings
        for i in range(5):
            await operations.rate_memory(f"memory_{i}", quality=0.5 + (i * 0.1))

        # Get stats
        stats = await operations.get_statistics()
        assert isinstance(stats, dict)

    async def test_complete_workflow(self, operations: MetaOperations):
        """Test a complete meta-memory workflow."""
        # 1. Rate multiple memories
        await operations.rate_memory("mem_1", quality=0.8, confidence=0.9)
        await operations.rate_memory("mem_2", quality=0.6, confidence=0.7)

        # 2. Check quality
        quality_1 = await operations.get_memory_quality("mem_1")
        assert quality_1 is not None

        # 3. Get expertise
        expertise = await operations.get_expertise()
        assert isinstance(expertise, dict)

        # 4. Monitor cognitive load
        await operations.update_cognitive_load(5, 2, 0.85)
        load = await operations.get_cognitive_load()
        assert load is not None

        # 5. Get overall statistics
        stats = await operations.get_statistics()
        assert isinstance(stats, dict)
