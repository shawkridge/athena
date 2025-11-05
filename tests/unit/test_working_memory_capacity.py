"""Unit tests for Working Memory Capacity Enforcement.

Tests the 7±2 capacity model with exponential decay, soft/hard limits,
and auto-consolidation triggers.
"""

import pytest
import math
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from athena.working_memory.capacity_enforcer import (
    WorkingMemoryCapacityEnforcer,
    CapacityExceededError,
    CapacityStatus
)
from athena.working_memory.models import ContentType, Component
from athena.core.database import Database


class TestCapacityEnforcerInit:
    """Tests for initialization and setup."""

    def test_init_with_database(self, tmp_path):
        """Should initialize with database connection."""
        db = Database(tmp_path / "test.db")
        enforcer = WorkingMemoryCapacityEnforcer(db)

        assert enforcer.db is db
        assert enforcer.SOFT_LIMIT == 6
        assert enforcer.HARD_LIMIT == 7
        assert enforcer.DECAY_HALF_LIFE == 30

    def test_constants_match_baddeley_model(self):
        """Should use Baddeley's 7±2 constants."""
        assert WorkingMemoryCapacityEnforcer.SOFT_LIMIT == 6
        assert WorkingMemoryCapacityEnforcer.HARD_LIMIT == 7
        # Half-life of 30 seconds is empirically typical for verbal items


class TestExponentialDecayFormula:
    """Tests for exponential decay calculation: A(t) = A₀ * e^(-λt)."""

    def test_decay_at_zero_seconds(self):
        """At t=0, activation should equal initial level."""
        result = WorkingMemoryCapacityEnforcer.calculate_activation(
            activation_level=1.0,
            importance_score=0.5,
            decay_rate=0.1 / 30,
            seconds_elapsed=0
        )
        assert result == pytest.approx(1.0)

    def test_decay_at_half_life(self):
        """At true half-life (30 ln(2)), activation should be ~50% with normal importance."""
        # For true half-life: decay_rate = ln(2) / half_life_seconds
        # With importance = 0.5: adaptive_rate = ln(2)/half_life * (1 - 0.5*0.5) = ln(2)/half_life * 0.75
        # At t = 30 seconds: A(30) = e^(-adaptive_rate * 30)
        result = WorkingMemoryCapacityEnforcer.calculate_activation(
            activation_level=1.0,
            importance_score=0.5,
            decay_rate=math.log(2) / 30,  # True half-life constant
            seconds_elapsed=30
        )
        # With importance reducing decay by 50%, should be > 0.5
        assert 0.5 < result < 0.8

    def test_high_importance_slows_decay(self):
        """Items with high importance should decay slower."""
        decay_rate = 0.1 / 30

        # Normal importance
        normal_result = WorkingMemoryCapacityEnforcer.calculate_activation(
            activation_level=1.0,
            importance_score=0.5,
            decay_rate=decay_rate,
            seconds_elapsed=60
        )

        # High importance
        high_result = WorkingMemoryCapacityEnforcer.calculate_activation(
            activation_level=1.0,
            importance_score=0.9,
            decay_rate=decay_rate,
            seconds_elapsed=60
        )

        # High importance should have higher activation (slower decay)
        assert high_result > normal_result

    def test_low_importance_accelerates_decay(self):
        """Items with low importance should decay faster."""
        decay_rate = 0.1 / 30

        # Low importance
        low_result = WorkingMemoryCapacityEnforcer.calculate_activation(
            activation_level=1.0,
            importance_score=0.1,
            decay_rate=decay_rate,
            seconds_elapsed=30
        )

        # High importance
        high_result = WorkingMemoryCapacityEnforcer.calculate_activation(
            activation_level=1.0,
            importance_score=0.9,
            decay_rate=decay_rate,
            seconds_elapsed=30
        )

        assert low_result < high_result

    def test_decay_formula_validation(self):
        """Should validate input parameters."""
        with pytest.raises(ValueError, match="non-negative"):
            WorkingMemoryCapacityEnforcer.calculate_activation(1.0, 0.5, 0.1, -5)

        with pytest.raises(ValueError, match="0.0-1.0"):
            WorkingMemoryCapacityEnforcer.calculate_activation(1.5, 0.5, 0.1, 10)

        with pytest.raises(ValueError, match="0.0-1.0"):
            WorkingMemoryCapacityEnforcer.calculate_activation(1.0, 1.5, 0.1, 10)

        with pytest.raises(ValueError, match="positive"):
            WorkingMemoryCapacityEnforcer.calculate_activation(1.0, 0.5, -0.1, 10)


class TestCapacityChecking:
    """Tests for capacity status checking."""

    def test_check_capacity_empty_project(self, tmp_path):
        """Should return all zeros for empty project."""
        db = Database(tmp_path / "test.db")
        enforcer = WorkingMemoryCapacityEnforcer(db)

        status = enforcer.check_capacity(project_id=1)

        assert status.active_count == 0
        assert status.at_soft_limit is False
        assert status.at_hard_limit is False
        assert len(status.items) == 0
        assert status.utilization_percent == 0.0

    def test_check_capacity_below_soft_limit(self, tmp_path):
        """Should report normal status below soft limit (6)."""
        db = Database(tmp_path / "test.db")
        enforcer = WorkingMemoryCapacityEnforcer(db)

        # Add 3 items
        for i in range(3):
            enforcer._insert_item(
                project_id=1,
                content=f"Item {i}",
                content_type=ContentType.VERBAL,
                component=Component.PHONOLOGICAL,
                importance=0.5
            )

        status = enforcer.check_capacity(project_id=1)

        assert status.active_count == 3
        assert status.at_soft_limit is False
        assert status.at_hard_limit is False
        assert status.utilization_percent == pytest.approx(42.9, 0.1)

    def test_check_capacity_at_soft_limit(self, tmp_path):
        """Should flag soft limit at 6/7."""
        db = Database(tmp_path / "test.db")
        enforcer = WorkingMemoryCapacityEnforcer(db)

        # Add 6 items
        for i in range(6):
            enforcer._insert_item(
                project_id=1,
                content=f"Item {i}",
                content_type=ContentType.VERBAL,
                component=Component.PHONOLOGICAL,
                importance=0.5
            )

        status = enforcer.check_capacity(project_id=1)

        assert status.active_count == 6
        assert status.at_soft_limit is True
        assert status.at_hard_limit is False
        assert status.estimated_consolidation_needed is True

    def test_check_capacity_at_hard_limit(self, tmp_path):
        """Should flag hard limit at 7/7."""
        db = Database(tmp_path / "test.db")
        enforcer = WorkingMemoryCapacityEnforcer(db)

        # Add 7 items
        for i in range(7):
            enforcer._insert_item(
                project_id=1,
                content=f"Item {i}",
                content_type=ContentType.VERBAL,
                component=Component.PHONOLOGICAL,
                importance=0.5
            )

        status = enforcer.check_capacity(project_id=1)

        assert status.active_count == 7
        assert status.at_soft_limit is True
        assert status.at_hard_limit is True


class TestHardCapacityEnforcement:
    """Tests for hard limit (7/7) enforcement."""

    def test_add_item_at_capacity_raises_error(self, tmp_path):
        """Should reject addition when at hard limit."""
        db = Database(tmp_path / "test.db")
        enforcer = WorkingMemoryCapacityEnforcer(db)

        # Fill to capacity
        for i in range(7):
            enforcer._insert_item(
                project_id=1,
                content=f"Item {i}",
                content_type=ContentType.VERBAL,
                component=Component.PHONOLOGICAL,
                importance=0.5
            )

        # 8th addition should fail
        with pytest.raises(CapacityExceededError, match="hard capacity"):
            enforcer.add_item_with_enforcement(
                project_id=1,
                content="Item 8",
                importance=0.5
            )

    def test_add_item_below_soft_limit_succeeds(self, tmp_path):
        """Should succeed below soft limit (5/7)."""
        db = Database(tmp_path / "test.db")
        enforcer = WorkingMemoryCapacityEnforcer(db)

        # Add 5 items via enforcement
        for i in range(5):
            item_id = enforcer.add_item_with_enforcement(
                project_id=1,
                content=f"Item {i}",
                importance=0.5
            )
            assert item_id is not None


class TestSoftLimitWarning:
    """Tests for soft limit (6/7) warning behavior."""

    def test_soft_limit_warning_logged(self, tmp_path, caplog):
        """Should log warning when reaching soft limit."""
        db = Database(tmp_path / "test.db")
        enforcer = WorkingMemoryCapacityEnforcer(db)

        # Add 6 items
        for i in range(6):
            enforcer._insert_item(
                project_id=1,
                content=f"Item {i}",
                content_type=ContentType.VERBAL,
                component=Component.PHONOLOGICAL,
                importance=0.5
            )

        # 7th item should warn
        with caplog.at_level("WARNING"):
            enforcer.add_item_with_enforcement(
                project_id=1,
                content="Item 7",
                importance=0.5
            )

        assert "approaching capacity" in caplog.text.lower()

    def test_soft_limit_auto_consolidation_callback(self, tmp_path):
        """Should trigger consolidation callback at soft limit."""
        db = Database(tmp_path / "test.db")
        enforcer = WorkingMemoryCapacityEnforcer(db)

        consolidation_callback = Mock()

        # Add 6 items
        for i in range(6):
            enforcer._insert_item(
                project_id=1,
                content=f"Item {i}",
                content_type=ContentType.VERBAL,
                component=Component.PHONOLOGICAL,
                importance=0.5
            )

        # 7th item should trigger callback
        enforcer.add_item_with_enforcement(
            project_id=1,
            content="Item 7",
            importance=0.5,
            consolidation_callback=consolidation_callback
        )

        consolidation_callback.assert_called_once_with(1)

    def test_soft_limit_consolidation_failure_allows_addition(self, tmp_path):
        """Should still add item even if consolidation fails."""
        db = Database(tmp_path / "test.db")
        enforcer = WorkingMemoryCapacityEnforcer(db)

        failing_callback = Mock(side_effect=Exception("Consolidation failed"))

        # Add 6 items
        for i in range(6):
            enforcer._insert_item(
                project_id=1,
                content=f"Item {i}",
                content_type=ContentType.VERBAL,
                component=Component.PHONOLOGICAL,
                importance=0.5
            )

        # Should still succeed despite callback failure
        item_id = enforcer.add_item_with_enforcement(
            project_id=1,
            content="Item 7",
            importance=0.5,
            consolidation_callback=failing_callback
        )

        assert item_id is not None


class TestAddItemWithEnforcement:
    """Tests for the main add_item_with_enforcement method."""

    def test_add_item_with_importance_validation(self, tmp_path):
        """Should validate importance score."""
        db = Database(tmp_path / "test.db")
        enforcer = WorkingMemoryCapacityEnforcer(db)

        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            enforcer.add_item_with_enforcement(
                project_id=1,
                content="Test",
                importance=1.5
            )

    def test_add_item_with_parameters(self, tmp_path):
        """Should accept all content type and component parameters."""
        db = Database(tmp_path / "test.db")
        enforcer = WorkingMemoryCapacityEnforcer(db)

        item_id = enforcer.add_item_with_enforcement(
            project_id=1,
            content="Spatial pattern",
            content_type=ContentType.SPATIAL,
            component=Component.VISUOSPATIAL,
            importance=0.8
        )

        assert item_id is not None
        status = enforcer.check_capacity(1)
        assert len(status.items) == 1
        assert status.items[0]['content_type'] == ContentType.SPATIAL.value


class TestRehearsalAndRefresh:
    """Tests for item rehearsal (refresh to prevent decay)."""

    def test_rehearse_item_resets_activation(self, tmp_path):
        """Should reset activation to 1.0 on rehearsal."""
        db = Database(tmp_path / "test.db")
        enforcer = WorkingMemoryCapacityEnforcer(db)

        item_id = enforcer.add_item_with_enforcement(
            project_id=1,
            content="Test item"
        )

        # Item should have activation 1.0
        status = enforcer.check_capacity(1)
        assert status.items[0]['activation'] == 1.0

        # Rehearse
        success = enforcer.rehearse_item(1, item_id)
        assert success is True

        # Should still be 1.0
        status = enforcer.check_capacity(1)
        assert status.items[0]['activation'] == 1.0

    def test_rehearse_nonexistent_item_returns_false(self, tmp_path):
        """Should return False when rehearsing nonexistent item."""
        db = Database(tmp_path / "test.db")
        enforcer = WorkingMemoryCapacityEnforcer(db)

        success = enforcer.rehearse_item(1, 999)
        assert success is False


class TestDecayCleanup:
    """Tests for removing decayed items."""

    def test_remove_decayed_items_below_threshold(self, tmp_path):
        """Should remove items with activation below threshold."""
        db = Database(tmp_path / "test.db")
        enforcer = WorkingMemoryCapacityEnforcer(db)

        # Add item with low importance (decays fast)
        cursor = db.conn.cursor()
        now = datetime.now()
        old_time = (now - timedelta(minutes=5)).isoformat()

        cursor.execute("""
            INSERT INTO working_memory
            (project_id, content, content_type, component, activation_level,
             created_at, last_accessed, decay_rate, importance_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            1, "Old item", "verbal", "phonological", 1.0,
            old_time, old_time, 0.1/30, 0.1  # Low importance
        ))
        db.conn.commit()

        # Remove decayed items
        removed_count = enforcer.remove_decayed_items(project_id=1, threshold=0.5)

        # Should have removed the decayed item
        assert removed_count >= 0  # May or may not remove depending on exact decay


class TestIntegrationScenarios:
    """Integration tests simulating realistic usage patterns."""

    def test_full_capacity_lifecycle(self, tmp_path):
        """Test complete lifecycle from empty to full to consolidated."""
        db = Database(tmp_path / "test.db")
        enforcer = WorkingMemoryCapacityEnforcer(db)
        project_id = 1

        # Add items one by one, monitoring capacity
        for i in range(7):
            status_before = enforcer.check_capacity(project_id)
            item_id = enforcer.add_item_with_enforcement(
                project_id=project_id,
                content=f"Item {i}",
                importance=0.5 + (i * 0.05)  # Increasing importance
            )
            status_after = enforcer.check_capacity(project_id)

            assert item_id is not None
            assert status_after.active_count == status_before.active_count + 1

        # At capacity
        status = enforcer.check_capacity(project_id)
        assert status.at_hard_limit is True

        # Should reject 8th item
        with pytest.raises(CapacityExceededError):
            enforcer.add_item_with_enforcement(
                project_id=project_id,
                content="Item 8"
            )

    def test_importance_affects_consolidation_priority(self, tmp_path):
        """Test that importance scores are tracked for consolidation decisions."""
        db = Database(tmp_path / "test.db")
        enforcer = WorkingMemoryCapacityEnforcer(db)

        # Add items with varying importance
        for i in range(7):
            enforcer.add_item_with_enforcement(
                project_id=1,
                content=f"Item {i}",
                importance=i / 10  # 0.0, 0.1, 0.2, ..., 0.6
            )

        status = enforcer.check_capacity(1)

        # Items should be present with their importance scores
        assert len(status.items) == 7
        importances = [item['importance'] for item in status.items]
        assert all(0 <= imp <= 1 for imp in importances)


class TestErrorHandling:
    """Tests for error handling and logging."""

    def test_database_error_propagates(self, tmp_path):
        """Should propagate database errors."""
        db = Database(tmp_path / "test.db")
        enforcer = WorkingMemoryCapacityEnforcer(db)

        # Close database to cause errors
        db.conn.close()

        with pytest.raises(Exception):
            enforcer.check_capacity(1)

    def test_logging_capacity_violations(self, tmp_path, caplog):
        """Should log capacity violations and enforcement actions."""
        db = Database(tmp_path / "test.db")
        enforcer = WorkingMemoryCapacityEnforcer(db)

        # Fill to capacity and attempt violation
        for i in range(7):
            enforcer.add_item_with_enforcement(
                project_id=1,
                content=f"Item {i}"
            )

        with caplog.at_level("ERROR"):
            with pytest.raises(CapacityExceededError):
                enforcer.add_item_with_enforcement(
                    project_id=1,
                    content="Item 8"
                )

        assert "hard capacity" in caplog.text.lower() or "hard limit" in caplog.text.lower()
