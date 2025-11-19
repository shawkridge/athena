"""Advanced Conflict Resolution with Learning

Implements intelligent conflict resolution that learns from past resolutions
to make better decisions about todo ↔ plan conflicts.

Uses preference history and pattern analysis to automatically resolve conflicts
without user intervention when confidence is high.

Strategies:
1. Direct resolution (high confidence)
2. Historical learning (past patterns)
3. Semantic similarity (content analysis)
4. User intervention (low confidence)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..core.database import Database
from .todowrite_sync import (
    detect_sync_conflict,
    resolve_sync_conflict,
)
from .database_sync import get_store

logger = logging.getLogger(__name__)


class ConflictResolutionStrategy:
    """Base class for conflict resolution strategies."""

    def __init__(self, name: str, confidence_threshold: float = 0.7):
        self.name = name
        self.confidence_threshold = confidence_threshold

    async def resolve(
        self,
        todo: Dict[str, Any],
        plan: Dict[str, Any],
    ) -> Tuple[bool, float, str]:
        """Resolve a conflict.

        Args:
            todo: TodoWrite todo
            plan: Athena plan

        Returns:
            (success, confidence, resolution_preference)
        """
        raise NotImplementedError


class DirectResolutionStrategy(ConflictResolutionStrategy):
    """Resolve based on conflict type."""

    async def resolve(
        self,
        todo: Dict[str, Any],
        plan: Dict[str, Any],
    ) -> Tuple[bool, float, str]:
        """Determine resolution based on conflict characteristics."""
        has_conflict, reason = detect_sync_conflict(todo, plan)

        if not has_conflict:
            return True, 1.0, "no_conflict"

        # Status mismatch → use plan as source of truth
        if "Status mismatch" in reason:
            return True, 0.8, "plan"

        # Content mismatch → use todo as source of truth
        if "Content mismatch" in reason:
            return True, 0.6, "todo"

        # Default: prefer plan
        return True, 0.5, "plan"


class HistoricalLearningStrategy(ConflictResolutionStrategy):
    """Resolve based on past conflict resolutions."""

    def __init__(self, db: Database, name: str = "historical_learning"):
        super().__init__(name)
        self.db = db
        self._history: Dict[str, int] = {}  # todo_id → resolution count

    async def resolve(
        self,
        todo: Dict[str, Any],
        plan: Dict[str, Any],
    ) -> Tuple[bool, float, str]:
        """Determine resolution based on history."""
        todo_id = todo.get("id", "unknown")

        # Load historical preferences
        await self._load_history(plan.get("project_id", 1))

        # Check if we've seen similar conflicts
        if todo_id in self._history:
            # If we've resolved this before, use same strategy
            if self._history[todo_id] > 5:  # High confidence threshold
                return True, 0.85, "plan"
            elif self._history[todo_id] > 2:
                return True, 0.7, "plan"

        return True, 0.4, "plan"

    async def _load_history(self, project_id: int) -> None:
        """Load resolution history from database."""
        try:
            store = get_store()
            plans = await store.list_plans_by_sync_status("synced", project_id, 1000)

            # Count resolutions by todo_id
            for plan in plans:
                todo_id = plan.get("todo_id", "")
                if todo_id:
                    self._history[todo_id] = self._history.get(todo_id, 0) + 1

        except Exception as e:
            logger.warning(f"Failed to load resolution history: {e}")


class SemanticSimilarityStrategy(ConflictResolutionStrategy):
    """Resolve based on semantic similarity of content."""

    async def resolve(
        self,
        todo: Dict[str, Any],
        plan: Dict[str, Any],
    ) -> Tuple[bool, float, str]:
        """Determine resolution based on content similarity."""
        todo_content = todo.get("content", "").lower().strip()
        plan_goal = plan.get("goal", "").lower().strip()

        if not todo_content or not plan_goal:
            return True, 0.5, "plan"

        # Simple similarity: word overlap
        todo_words = set(todo_content.split())
        plan_words = set(plan_goal.split())

        if todo_words and plan_words:
            overlap = len(todo_words & plan_words) / max(len(todo_words), len(plan_words))
            confidence = 0.5 + (overlap * 0.5)  # 0.5-1.0 confidence

            # High overlap → content is similar → prefer plan
            if overlap > 0.7:
                return True, confidence, "plan"
            # Low overlap → content diverged → prefer todo
            else:
                return True, confidence, "todo"

        return True, 0.5, "plan"


class AdaptiveConflictResolver:
    """Main conflict resolver using multiple strategies."""

    def __init__(self, db: Database, min_confidence: float = 0.7):
        self.db = db
        self.min_confidence = min_confidence
        self.strategies = [
            DirectResolutionStrategy("direct"),
            SemanticSimilarityStrategy("semantic"),
            HistoricalLearningStrategy(db, "historical"),
        ]

    async def resolve_with_learning(
        self,
        todo: Dict[str, Any],
        plan: Dict[str, Any],
    ) -> Tuple[bool, Optional[str], float]:
        """Resolve conflict using multiple strategies with learning.

        Args:
            todo: TodoWrite todo
            plan: Athena plan

        Returns:
            (success, resolution_preference, average_confidence)
        """
        try:
            # Check for conflict first
            has_conflict, reason = detect_sync_conflict(todo, plan)
            if not has_conflict:
                return True, None, 1.0

            # Run all strategies and get votes
            strategy_results = []
            for strategy in self.strategies:
                success, confidence, preference = await strategy.resolve(todo, plan)
                if success and confidence >= 0.5:  # Only count reasonable results
                    strategy_results.append((preference, confidence))

            if not strategy_results:
                logger.warning("No strategy could resolve conflict")
                return False, None, 0.0

            # Weighted voting
            total_weight = sum(conf for _, conf in strategy_results)
            preference_scores = {}

            for preference, confidence in strategy_results:
                weight = confidence / total_weight
                preference_scores[preference] = preference_scores.get(preference, 0.0) + weight

            # Winner takes all
            best_preference = max(preference_scores, key=preference_scores.get)
            confidence = preference_scores[best_preference]

            # Log resolution
            logger.info(
                f"Resolved conflict: preference={best_preference}, confidence={confidence:.2f}"
            )

            # Record if high confidence
            if confidence >= self.min_confidence:
                await self._record_resolution(
                    todo.get("id", ""),
                    plan.get("plan_id", ""),
                    best_preference,
                    confidence,
                    reason,
                )

            return True, best_preference, confidence

        except Exception as e:
            logger.error(f"Failed to resolve conflict with learning: {e}")
            return False, None, 0.0

    async def _record_resolution(
        self,
        todo_id: str,
        plan_id: str,
        preference: str,
        confidence: float,
        reason: str,
    ) -> None:
        """Record resolution for learning."""
        try:
            store = get_store()
            await store.update_sync_status(
                plan_id,
                "synced",
                None,  # No conflict
            )
            logger.info(
                f"Recorded resolution: todo={todo_id}, plan={plan_id}, "
                f"preference={preference}, confidence={confidence:.2f}"
            )
        except Exception as e:
            logger.warning(f"Failed to record resolution: {e}")

    async def auto_resolve_with_threshold(
        self,
        todo: Dict[str, Any],
        plan: Dict[str, Any],
        confidence_threshold: float = 0.8,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Automatically resolve if confidence meets threshold.

        Args:
            todo: TodoWrite todo
            plan: Athena plan
            confidence_threshold: Minimum confidence for auto-resolution

        Returns:
            (success, resolved_plan or None if needs manual resolution)
        """
        success, preference, confidence = await self.resolve_with_learning(todo, plan)

        if not success or preference is None:
            return False, None

        if confidence < confidence_threshold:
            # Not confident enough for automatic resolution
            logger.warning(
                f"Confidence {confidence:.2f} below threshold {confidence_threshold}. "
                f"Requires manual resolution."
            )
            return False, None

        # Confidence is high enough → auto-resolve
        resolved = await resolve_sync_conflict(todo, plan, prefer=preference)
        return True, resolved["plan"]


class ConflictResolutionStore:
    """Database storage for conflict resolution history."""

    def __init__(self, db: Database):
        self.db = db
        self._ensure_schema()
