"""
Refactored Consolidation Router using Store APIs.

This version replaces direct SQL calls with store API calls for better
abstraction, maintainability, and consistency with the rest of the codebase.

Features:
- Uses MemoryStore, EpisodicStore, ProceduralStore, ProspectiveStore
- Async/sync dual interface with run_async bridge
- Same ML routing logic as v1 but cleaner implementation
- Better error handling and logging
"""

import logging
import json
from typing import Dict, Optional, Tuple

import numpy as np

from ..core.database import Database
from ..core.async_utils import run_async
from ..memory.store import MemoryStore
from ..episodic.store import EpisodicStore
from ..procedural.store import ProceduralStore
from ..prospective.store import ProspectiveStore
from .models import WorkingMemoryItem, TargetLayer

logger = logging.getLogger(__name__)


class ConsolidationRouterV2:
    """ML-based router using Store APIs for consolidation.

    This is a cleaner implementation that uses the store layer abstraction
    instead of direct SQL, making it more maintainable and consistent with
    the codebase architecture.

    Usage:
        router = ConsolidationRouterV2(
            db=db,
            memory_store=memory_store,
            episodic_store=episodic_store,
            procedural_store=procedural_store,
            prospective_store=prospective_store,
        )

        # Route a working memory item
        target_layer, confidence = router.route(wm_item, project_id)

        # Consolidate to target layer
        result = router.consolidate_item(wm_item, project_id)
    """

    def __init__(
        self,
        db: Database,
        memory_store: MemoryStore,
        episodic_store: EpisodicStore,
        procedural_store: ProceduralStore,
        prospective_store: ProspectiveStore,
    ):
        """Initialize consolidation router with stores.

        Args:
            db: Database instance
            memory_store: Semantic memory store
            episodic_store: Episodic memory store
            procedural_store: Procedural memory store
            prospective_store: Prospective memory store
        """
        self.db = db
        self.memory_store = memory_store
        self.episodic_store = episodic_store
        self.procedural_store = procedural_store
        self.prospective_store = prospective_store

        # ML model state
        self.model = None
        self.is_trained = False

        # Feature names for ML
        self.feature_names = [
            "content_length",
            "is_verbal",
            "is_spatial",
            "activation_level",
            "importance_score",
            "time_in_wm_seconds",
            "has_temporal_markers",
            "has_action_verbs",
            "has_future_markers",
            "has_question_words",
            "has_file_references",
        ]

    # ========================================================================
    # Routing Decision (Async)
    # ========================================================================

    async def route_async(
        self,
        wm_item: WorkingMemoryItem,
        project_id: int,
        use_ml: bool = True,
    ) -> Tuple[TargetLayer, float]:
        """Route working memory item to appropriate layer (async).

        Args:
            wm_item: Item to route
            project_id: Project ID
            use_ml: Use ML model if trained, else use heuristics

        Returns:
            Tuple of (target_layer, confidence)
        """
        # Extract features
        features = self._extract_features(wm_item)

        # Route using ML or heuristics
        if use_ml and self.is_trained and self.model is not None:
            target_layer, confidence = self._ml_predict(features)
        else:
            target_layer = self._heuristic_route(wm_item)
            confidence = 0.6

        # Log routing decision
        await self._log_route_decision_async(
            wm_item.id,
            target_layer,
            confidence,
            features,
        )

        logger.debug(
            f"Routed item {wm_item.id} to {target_layer.value} " f"(confidence: {confidence:.2f})"
        )

        return target_layer, confidence

    async def consolidate_item_async(
        self,
        wm_item: WorkingMemoryItem,
        project_id: int,
        target_layer: Optional[TargetLayer] = None,
    ) -> Dict:
        """Consolidate item to long-term memory (async).

        Args:
            wm_item: Item to consolidate
            project_id: Project ID
            target_layer: Optional override for target layer

        Returns:
            Dict with consolidation result
        """
        # Determine target if not specified
        if target_layer is None:
            target_layer, confidence = await self.route_async(wm_item, project_id)
        else:
            confidence = 1.0  # User override = full confidence

        # Consolidate to target layer using store APIs
        ltm_id = await self._consolidate_to_layer_async(wm_item, target_layer, project_id)

        logger.info(
            f"Consolidated item {wm_item.id} to {target_layer.value} " f"(LTM ID: {ltm_id})"
        )

        return {
            "wm_item_id": wm_item.id,
            "target_layer": target_layer.value,
            "ltm_id": ltm_id,
            "confidence": confidence,
        }

    async def _consolidate_to_layer_async(
        self,
        wm_item: WorkingMemoryItem,
        target_layer: TargetLayer,
        project_id: int,
    ) -> Optional[int]:
        """Execute consolidation to target layer using store API (async).

        Args:
            wm_item: Item to consolidate
            target_layer: Target layer
            project_id: Project ID

        Returns:
            ID in target layer or None if failed
        """
        metadata = {
            "source": "working_memory",
            "wm_id": wm_item.id,
            "importance": wm_item.importance_score,
        }

        try:
            if target_layer == TargetLayer.SEMANTIC:
                # Use MemoryStore to create semantic memory
                from ..core.models import Memory, MemoryType

                memory = Memory(
                    project_id=project_id,
                    content=wm_item.content,
                    memory_type=MemoryType.FACT,
                    tags=["consolidated"],
                    metadata=metadata,
                )

                result = await self.memory_store.remember(memory)
                return result.id if result else None

            elif target_layer == TargetLayer.EPISODIC:
                # Use EpisodicStore to create episodic event
                from ..episodic.models import EpisodicEvent, EventType, EventOutcome

                event = EpisodicEvent(
                    project_id=project_id,
                    session_id="consolidation",
                    event_type=EventType.ACTION,
                    content=wm_item.content,
                    outcome=EventOutcome.SUCCESS,
                    context={"source": "working_memory"},
                )

                result = await self.episodic_store.store_async(event)
                return result.id if result else None

            elif target_layer == TargetLayer.PROCEDURAL:
                # Use ProceduralStore to create procedure
                from ..procedural.models import Procedure, ProcedureCategory

                procedure = Procedure(
                    project_id=project_id,
                    name=f"Procedure from WM #{wm_item.id}",
                    category=ProcedureCategory.WORKFLOW,
                    content=wm_item.content,
                    metadata=metadata,
                )

                result = await self.procedural_store.create(procedure)
                return result.id if result else None

            elif target_layer == TargetLayer.PROSPECTIVE:
                # Use ProspectiveStore to create task
                task = {
                    "project_id": project_id,
                    "content": wm_item.content,
                    "active_form": f"Follow up: {wm_item.content[:50]}",
                    "priority": "medium",
                    "metadata": metadata,
                }

                # Note: ProspectiveStore might not have direct create method
                # In that case, use memory_store as fallback
                logger.warning(
                    f"Prospective consolidation not yet implemented, "
                    f"falling back to semantic for item {wm_item.id}"
                )

                from ..core.models import Memory, MemoryType

                memory = Memory(
                    project_id=project_id,
                    content=wm_item.content,
                    memory_type=MemoryType.TASK,
                    tags=["prospective", "consolidated"],
                    metadata=metadata,
                )

                result = await self.memory_store.remember(memory)
                return result.id if result else None

            else:
                logger.error(f"Unknown target layer: {target_layer}")
                return None

        except Exception as e:
            logger.error(f"Failed to consolidate item {wm_item.id} to {target_layer.value}: {e}")
            return None

    # ========================================================================
    # Routing Logic
    # ========================================================================

    def _extract_features(self, wm_item: WorkingMemoryItem | int) -> np.ndarray:
        """Extract features for ML classification.

        Args:
            wm_item: WorkingMemoryItem or item ID

        Returns:
            Feature vector as numpy array
        """
        if isinstance(wm_item, int):
            logger.warning(f"Cannot extract features from item ID {wm_item}")
            return np.zeros(len(self.feature_names))

        features = np.zeros(len(self.feature_names))

        content = wm_item.content if wm_item.content else ""
        features[0] = len(content)  # content_length
        features[1] = float(wm_item.component.value == "phonological")  # is_verbal
        features[2] = float(wm_item.component.value == "visuospatial")  # is_spatial
        features[3] = wm_item.activation_level  # activation_level
        features[4] = wm_item.importance_score  # importance_score
        features[5] = (
            (datetime.now() - wm_item.last_accessed).total_seconds()
            if hasattr(wm_item, "last_accessed")
            else 0
        )  # time_in_wm_seconds
        features[6] = float(self._has_temporal_markers(content))  # has_temporal_markers
        features[7] = float(self._has_action_verbs(content))  # has_action_verbs
        features[8] = float(self._has_future_markers(content))  # has_future_markers
        features[9] = float(self._has_question_words(content))  # has_question_words
        features[10] = float(self._has_file_references(content))  # has_file_references

        return features

    def _ml_predict(self, features: np.ndarray) -> Tuple[TargetLayer, float]:
        """Predict target layer using ML model.

        Args:
            features: Feature vector

        Returns:
            Tuple of (target_layer, confidence)
        """
        if not self.is_trained or self.model is None:
            return TargetLayer.SEMANTIC, 0.5

        try:
            prediction = self.model.predict([features])[0]
            confidence = float(max(self.model.predict_proba([features])[0]))
            return TargetLayer(prediction), confidence
        except Exception as e:
            logger.error(f"ML prediction failed: {e}, falling back to heuristics")
            return TargetLayer.SEMANTIC, 0.5

    def _heuristic_route(self, wm_item: WorkingMemoryItem | str) -> TargetLayer:
        """Route using heuristics (when ML not available).

        Args:
            wm_item: WorkingMemoryItem or content string

        Returns:
            Target layer
        """
        content = wm_item.content if isinstance(wm_item, WorkingMemoryItem) else str(wm_item)

        # Check for prospective (future-oriented)
        if self._has_future_markers(content) or self._has_question_words(content):
            return TargetLayer.PROSPECTIVE

        # Check for procedural (action/how-to)
        if self._has_action_verbs(content) or self._has_procedural_patterns(content):
            return TargetLayer.PROCEDURAL

        # Check for temporal (event-based)
        if self._has_temporal_markers(content):
            return TargetLayer.EPISODIC

        # Default to semantic
        return TargetLayer.SEMANTIC

    # ========================================================================
    # Feature Detection
    # ========================================================================

    def _has_temporal_markers(self, content: str) -> bool:
        """Check for temporal indicators."""

        temporal_words = [
            "yesterday",
            "today",
            "tomorrow",
            "week",
            "month",
            "year",
            "morning",
            "afternoon",
            "evening",
            "night",
            "when",
            "then",
            "after",
            "before",
            "during",
        ]
        return any(word in content.lower() for word in temporal_words)

    def _has_action_verbs(self, content: str) -> bool:
        """Check for action verbs."""
        action_verbs = [
            "do",
            "make",
            "build",
            "create",
            "write",
            "code",
            "implement",
            "execute",
            "run",
            "test",
            "deploy",
            "fix",
            "solve",
            "complete",
        ]
        return any(verb in content.lower() for verb in action_verbs)

    def _has_future_markers(self, content: str) -> bool:
        """Check for future-oriented language."""
        future_markers = [
            "will",
            "should",
            "must",
            "need",
            "want",
            "plan",
            "schedule",
            "remind",
            "task",
            "todo",
            "goal",
        ]
        return any(marker in content.lower() for marker in future_markers)

    def _has_question_words(self, content: str) -> bool:
        """Check for question words."""
        question_words = ["what", "how", "why", "when", "where", "which", "who"]
        return any(word in content.lower() for word in question_words)

    def _has_file_references(self, content: str) -> bool:
        """Check for file path references."""
        return "/" in content or "\\" in content or ".py" in content

    def _has_procedural_patterns(self, content: str) -> bool:
        """Check for procedural patterns."""
        patterns = ["step", "process", "workflow", "procedure", "algorithm", "pattern"]
        return any(pattern in content.lower() for pattern in patterns)

    # ========================================================================
    # Logging & Statistics (Async)
    # ========================================================================

    async def _log_route_decision_async(
        self,
        wm_id: Optional[int],
        target_layer: TargetLayer,
        confidence: float,
        features: np.ndarray,
    ) -> None:
        """Log routing decision for training/analysis (async).

        Args:
            wm_id: Working memory item ID
            target_layer: Target layer decision
            confidence: Confidence score
            features: Feature vector
        """
        try:
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                INSERT INTO consolidation_routes
                (target_layer, confidence, features)
                VALUES (?, ?, ?)
            """,
                (
                    target_layer.value,
                    confidence,
                    json.dumps(features.tolist()),
                ),
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log routing decision: {e}")

    async def get_routing_statistics_async(self, project_id: int) -> Dict:
        """Get routing statistics (async).

        Args:
            project_id: Project ID

        Returns:
            Dict with routing statistics
        """
        try:
            cursor = self.db.get_cursor()

            # Total routes
            cursor.execute("SELECT COUNT(*) as count FROM consolidation_routes")
            total = cursor.fetchone()["count"] if cursor.fetchone() else 0

            # Routes by layer
            cursor.execute(
                """
                SELECT target_layer, COUNT(*) as count
                FROM consolidation_routes
                GROUP BY target_layer
            """
            )
            by_layer = cursor.fetchall()

            return {
                "total_routes": total,
                "by_layer": (
                    {row["target_layer"]: row["count"] for row in by_layer} if by_layer else {}
                ),
                "is_trained": self.is_trained,
            }
        except Exception as e:
            logger.error(f"Failed to get routing statistics: {e}")
            return {"total_routes": 0, "by_layer": {}, "is_trained": False}

    # ========================================================================
    # Sync Wrappers
    # ========================================================================

    def route(
        self,
        wm_item: WorkingMemoryItem,
        project_id: int,
        use_ml: bool = True,
    ) -> Tuple[TargetLayer, float]:
        """Route working memory item to appropriate layer (sync).

        Args:
            wm_item: Item to route
            project_id: Project ID
            use_ml: Use ML model if trained

        Returns:
            Tuple of (target_layer, confidence)
        """
        return run_async(self.route_async(wm_item, project_id, use_ml))

    def consolidate_item(
        self,
        wm_item: WorkingMemoryItem,
        project_id: int,
        target_layer: Optional[TargetLayer] = None,
    ) -> Dict:
        """Consolidate item to long-term memory (sync).

        Args:
            wm_item: Item to consolidate
            project_id: Project ID
            target_layer: Optional override

        Returns:
            Consolidation result dict
        """
        return run_async(self.consolidate_item_async(wm_item, project_id, target_layer))

    def get_routing_statistics(self, project_id: int) -> Dict:
        """Get routing statistics (sync).

        Args:
            project_id: Project ID

        Returns:
            Dict with statistics
        """
        return run_async(self.get_routing_statistics_async(project_id))


from datetime import datetime
