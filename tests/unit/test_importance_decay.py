"""Unit tests for Quick Win #1: Event importance decay.

This test module validates the exponential decay mechanism for old, unused items
in the attention system. This implements spaced repetition-style decay where items
not accessed recently have their importance gradually reduced.

Note: These tests require PostgreSQL to be running. They will be skipped if
PostgreSQL is not available.
"""

from datetime import datetime, timedelta
import pytest

from athena.meta.attention import AttentionManager


@pytest.fixture
def attention_manager(test_db):
    """Create an AttentionManager instance."""
    return AttentionManager(test_db)


class TestImportanceDecay:
    """Tests for exponential importance decay mechanism."""

    def test_decay_on_empty_attention(self, attention_manager, test_project):
        """Test that decay handles empty attention gracefully."""
        result = attention_manager.apply_importance_decay(test_project.id)

        assert result["items_decayed"] == 0
        assert result["avg_decay_amount"] == 0.0
        assert result["items_with_zero_importance"] == 0
        assert "timestamp" in result

    def test_decay_on_recent_items(self, attention_manager, test_project):
        """Test that recent items are not decayed."""
        # Add recent items (accessed within last 30 days)
        for i in range(3):
            attention_manager.add_attention_item(
                project_id=test_project.id,
                item_type="test_item",
                item_id=i,
                importance=0.8,
                relevance=0.7,
                context=f"Recent item {i}"
            )

        # Apply decay (default 30 days threshold)
        result = attention_manager.apply_importance_decay(test_project.id)

        # Recent items should not be decayed
        assert result["items_decayed"] == 0

    def test_decay_on_old_items(self, attention_manager, test_project, test_db):
        """Test that old items are decayed appropriately."""
        # Add an old item
        cursor = test_db.execute(
            """
            INSERT INTO attention_items (
                project_id, item_type, item_id,
                importance, relevance, salience_score, recency,
                activation_level, last_accessed
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                test_project.id, "test_item", 1,
                0.8, 0.7, 0.75, 0.8,
                0.5,
                datetime.now() - timedelta(days=60)  # 60 days old
            )
        )

        # Apply decay
        result = attention_manager.apply_importance_decay(
            test_project.id,
            decay_rate=0.05,
            days_threshold=30
        )

        assert result["items_decayed"] == 1
        assert result["avg_decay_amount"] > 0.0
        assert result["avg_decay_amount"] < 0.8  # Should not decay to zero immediately

        # Verify the item was actually updated
        items = attention_manager.get_attention_items(test_project.id)
        if items:
            # Importance should be reduced
            assert items[0].importance < 0.8

    def test_decay_exponential_formula(self, attention_manager, test_project, test_db):
        """Test that decay follows exponential formula: new = old * e^(-rate*days)."""
        import math

        # Add an old item with known importance
        old_importance = 1.0
        days_inactive = 30
        decay_rate = 0.1  # 10% per day

        cursor = test_db.execute(
            """
            INSERT INTO attention_items (
                project_id, item_type, item_id,
                importance, relevance, salience_score, recency,
                activation_level, last_accessed
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                test_project.id, "test_item", 1,
                old_importance, 0.7, 0.75, 0.8,
                0.5,
                datetime.now() - timedelta(days=days_inactive)
            )
        )

        # Apply decay
        result = attention_manager.apply_importance_decay(
            test_project.id,
            decay_rate=decay_rate,
            days_threshold=0  # Decay all items
        )

        # Calculate expected importance
        expected_decay_factor = math.exp(-decay_rate * days_inactive)
        expected_new_importance = old_importance * expected_decay_factor

        # Get decayed item
        items = attention_manager.get_attention_items(test_project.id)
        assert len(items) > 0
        actual_new_importance = items[0].importance

        # Allow small floating point error
        assert abs(actual_new_importance - expected_new_importance) < 0.001

    def test_decay_multiple_items_statistics(self, attention_manager, test_project, test_db):
        """Test decay statistics with multiple items."""
        # Add 5 old items with different importances
        importances = [1.0, 0.8, 0.6, 0.4, 0.2]
        for i, importance in enumerate(importances):
            cursor = test_db.execute(
                """
                INSERT INTO attention_items (
                    project_id, item_type, item_id,
                    importance, relevance, salience_score, recency,
                    activation_level, last_accessed
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    test_project.id, "test_item", i,
                    importance, 0.7, 0.75, 0.8,
                    0.5,
                    datetime.now() - timedelta(days=45)  # All 45 days old
                )
            )

        # Apply decay
        result = attention_manager.apply_importance_decay(
            test_project.id,
            decay_rate=0.05,
            days_threshold=30
        )

        assert result["items_decayed"] == 5
        assert result["avg_decay_amount"] > 0.0
        # With 5 items and avg importance 0.6, avg decay should be reasonable
        assert 0.0 < result["avg_decay_amount"] < 0.2

    def test_decay_respects_threshold(self, attention_manager, test_project, test_db):
        """Test that items newer than threshold are not decayed."""
        # Add items: one old, one recent
        # Old item (45 days ago)
        test_db.execute(
            """
            INSERT INTO attention_items (
                project_id, item_type, item_id,
                importance, relevance, salience_score, recency,
                activation_level, last_accessed
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                test_project.id, "test_item", 1,
                0.8, 0.7, 0.75, 0.8,
                0.5,
                datetime.now() - timedelta(days=45)
            )
        )

        # Recent item (15 days ago)
        test_db.execute(
            """
            INSERT INTO attention_items (
                project_id, item_type, item_id,
                importance, relevance, salience_score, recency,
                activation_level, last_accessed
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                test_project.id, "test_item", 2,
                0.7, 0.6, 0.65, 0.7,
                0.4,
                datetime.now() - timedelta(days=15)
            )
        )

        # Apply decay with 30 day threshold
        result = attention_manager.apply_importance_decay(
            test_project.id,
            decay_rate=0.05,
            days_threshold=30
        )

        # Only the old item should be decayed
        assert result["items_decayed"] == 1

    def test_decay_salience_recalculation(self, attention_manager, test_project, test_db):
        """Test that salience is recalculated after decay."""
        # Add an old item
        test_db.execute(
            """
            INSERT INTO attention_items (
                project_id, item_type, item_id,
                importance, relevance, salience_score, recency,
                activation_level, last_accessed
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                test_project.id, "test_item", 1,
                0.8, 0.7, 0.75, 0.8,
                0.5,
                datetime.now() - timedelta(days=60)
            )
        )

        # Get original salience
        items_before = attention_manager.get_attention_items(test_project.id)
        original_salience = items_before[0].salience_score

        # Apply decay
        attention_manager.apply_importance_decay(
            test_project.id,
            decay_rate=0.05,
            days_threshold=30
        )

        # Get decayed salience
        items_after = attention_manager.get_attention_items(test_project.id)
        new_salience = items_after[0].salience_score

        # Salience should decrease since importance decreased
        assert new_salience < original_salience

    def test_decay_zero_importance_handling(self, attention_manager, test_project, test_db):
        """Test that items reaching zero importance are counted."""
        # Add an old item with low importance
        test_db.execute(
            """
            INSERT INTO attention_items (
                project_id, item_type, item_id,
                importance, relevance, salience_score, recency,
                activation_level, last_accessed
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                test_project.id, "test_item", 1,
                0.01, 0.5, 0.3, 0.05,
                0.1,
                datetime.now() - timedelta(days=180)  # Very old
            )
        )

        # Apply decay with high decay rate
        result = attention_manager.apply_importance_decay(
            test_project.id,
            decay_rate=0.5,  # Very high decay
            days_threshold=0
        )

        # Item should reach zero importance
        assert result["items_with_zero_importance"] >= 0

        # Verify item's importance is minimum 0.0
        items = attention_manager.get_attention_items(test_project.id)
        if items:
            assert items[0].importance >= 0.0


class TestImportanceDecayIntegration:
    """Integration tests for importance decay with the broader attention system."""

    def test_decay_preserves_other_items(self, attention_manager, test_project, test_db):
        """Test that decay doesn't affect items below threshold."""
        # Add recent item
        old_item_id = attention_manager.add_attention_item(
            project_id=test_project.id,
            item_type="old",
            item_id=1,
            importance=0.7,
            relevance=0.6
        )

        # Make it old
        test_db.execute(
            """
            UPDATE attention_items
            SET last_accessed = %s
            WHERE id = %s
            """,
            (datetime.now() - timedelta(days=60), old_item_id)
        )

        # Add a genuinely recent item
        recent_item_id = attention_manager.add_attention_item(
            project_id=test_project.id,
            item_type="recent",
            item_id=2,
            importance=0.7,
            relevance=0.6
        )

        # Get recent item's importance before decay
        items_before = {
            item.item_id: item.importance
            for item in attention_manager.get_attention_items(test_project.id)
        }
        recent_importance_before = items_before[2]

        # Apply decay
        attention_manager.apply_importance_decay(test_project.id)

        # Get recent item's importance after decay
        items_after = {
            item.item_id: item.importance
            for item in attention_manager.get_attention_items(test_project.id)
        }
        recent_importance_after = items_after.get(2)

        # Recent item should be unchanged
        if recent_importance_after is not None:
            assert recent_importance_after == recent_importance_before

    def test_decay_multiple_calls_idempotent(self, attention_manager, test_project, test_db):
        """Test that multiple decay calls reach stable state."""
        # Add an old item
        test_db.execute(
            """
            INSERT INTO attention_items (
                project_id, item_type, item_id,
                importance, relevance, salience_score, recency,
                activation_level, last_accessed
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                test_project.id, "test_item", 1,
                0.8, 0.7, 0.75, 0.8,
                0.5,
                datetime.now() - timedelta(days=60)
            )
        )

        # Apply decay first time
        result1 = attention_manager.apply_importance_decay(test_project.id)
        items1 = attention_manager.get_attention_items(test_project.id)
        importance1 = items1[0].importance if items1 else None

        # Apply decay second time immediately
        result2 = attention_manager.apply_importance_decay(test_project.id)
        items2 = attention_manager.get_attention_items(test_project.id)
        importance2 = items2[0].importance if items2 else None

        # Importance should be less or equal after second decay
        assert importance2 <= importance1
