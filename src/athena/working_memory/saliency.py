"""Automatic saliency detection for memory management.

Computes multi-factor saliency scores based on:
1. Frequency: How often accessed (30% weight)
2. Recency: How recently accessed (30% weight)
3. Task Relevance: Relevance to current goal (25% weight)
4. Surprise Value: How novel/unexpected (15% weight)

Research:
- Baddeley 2000: "The Episodic Buffer" - working memory saliency
- Kumar et al. 2023: "Bayesian Surprise Predicts Human Event Segmentation"
- StreamingLLM (ICLR 2024): Attention sinks maintain disproportionate weight
"""

import math
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from ..core.database import Database


class SaliencyCalculator:
    """Compute saliency scores for memories using multi-factor model.

    Saliency combines frequency, recency, task relevance, and surprise
    to determine which memories should be prioritized in working memory.
    """

    def __init__(self, db: Database):
        """Initialize saliency calculator.

        Args:
            db: Database instance for accessing memory metadata
        """
        self.db = db
        # Weights for each factor (sum = 1.0)
        self.weights = {
            "frequency": 0.30,
            "recency": 0.30,
            "relevance": 0.25,
            "surprise": 0.15,
        }
        # Time decay parameters
        self.recency_half_life = 7.0  # Days

    def compute_saliency(
        self,
        memory_id: int,
        layer: str,
        project_id: int,
        current_goal: Optional[str] = None,
        context_events: Optional[List[int]] = None,
    ) -> float:
        """Compute saliency score for a memory (0-1).

        Args:
            memory_id: Memory to score
            layer: Memory layer (semantic, episodic, procedural, etc.)
            project_id: Project context
            current_goal: Current task/goal (for relevance computation)
            context_events: Recent event IDs (for surprise computation)

        Returns:
            Saliency score (0-1, higher = more salient)
        """
        try:
            scores = {}

            # Factor 1: Frequency (access count)
            scores["frequency"] = self._compute_frequency_score(
                memory_id, layer, project_id
            )

            # Factor 2: Recency (time decay)
            scores["recency"] = self._compute_recency_score(
                memory_id, layer, project_id
            )

            # Factor 3: Task Relevance (goal alignment)
            scores["relevance"] = self._compute_relevance_score(
                memory_id, layer, project_id, current_goal
            )

            # Factor 4: Surprise Value (novelty bonus)
            scores["surprise"] = self._compute_surprise_score(
                memory_id, layer, project_id, context_events
            )

            # Weighted combination
            saliency = sum(
                scores[factor] * self.weights[factor]
                for factor in self.weights.keys()
            )

            # Clamp to [0, 1]
            return max(0.0, min(1.0, saliency))

        except (AttributeError, KeyError, ValueError, TypeError) as e:
            # Log error but return neutral score
            import logging
            logging.warning(f"Error computing saliency for memory {memory_id}: {e}")
            return 0.5  # Neutral/unknown

    def _compute_frequency_score(
        self,
        memory_id: int,
        layer: str,
        project_id: int,
    ) -> float:
        """Score based on access frequency.

        Frequency = (access_count / max_count) clamped to [0, 1]

        Args:
            memory_id: Memory to score
            layer: Memory layer
            project_id: Project context

        Returns:
            Frequency score (0-1)
        """
        try:
            cursor = self.db.get_cursor()

            # Try to get access count from semantic or episodic memory table
            tables = {
                "semantic": "memories",
                "episodic": "episodic_events",
                "procedural": "procedures",
            }

            if layer not in tables:
                return 0.5  # Unknown layer

            table = tables[layer]

            # Get memory access count
            if layer == "episodic":
                query = f"""
                    SELECT COUNT(*) as access_count
                    FROM {table}
                    WHERE id = ? AND project_id = ?
                """
            else:
                query = f"""
                    SELECT access_count
                    FROM {table}
                    WHERE id = ? AND project_id = ?
                """

            cursor.execute(query, (memory_id, project_id))
            result = cursor.fetchone()

            access_count = result[0] if result and result[0] else 0

            # Get max access count in layer (for normalization)
            max_query = f"SELECT MAX(access_count) FROM {table} WHERE project_id = ?"
            cursor.execute(max_query, (project_id,))
            max_result = cursor.fetchone()
            max_count = max_result[0] if max_result and max_result[0] else 1

            frequency_score = min(1.0, access_count / max(max_count, 1))
            return frequency_score

        except (AttributeError, TypeError, ValueError, ZeroDivisionError):
            return 0.5  # Default to neutral

    def _compute_recency_score(
        self,
        memory_id: int,
        layer: str,
        project_id: int,
    ) -> float:
        """Score based on recency with exponential decay.

        Recency = exp(-(age_days / half_life))
        Half-life = 7 days (score = 0.5 at 7 days)

        Args:
            memory_id: Memory to score
            layer: Memory layer
            project_id: Project context

        Returns:
            Recency score (0-1)
        """
        try:
            cursor = self.db.get_cursor()

            # Get last accessed/created timestamp
            if layer == "episodic":
                query = "SELECT timestamp FROM episodic_events WHERE id = ? AND project_id = ?"
            elif layer == "semantic":
                query = "SELECT created_at FROM memories WHERE id = ? AND project_id = ?"
            elif layer == "procedural":
                query = "SELECT created_at FROM procedures WHERE id = ? AND project_id = ?"
            else:
                return 0.5

            cursor.execute(query, (memory_id, project_id))
            result = cursor.fetchone()

            if not result or result[0] is None:
                return 0.5  # Unknown = moderate

            # Parse timestamp
            timestamp = result[0]
            if isinstance(timestamp, str):
                last_accessed = datetime.fromisoformat(timestamp)
            elif isinstance(timestamp, (int, float)):
                last_accessed = datetime.fromtimestamp(timestamp)
            else:
                return 0.5

            # Calculate age in days
            age_days = (datetime.now() - last_accessed).total_seconds() / 86400.0

            # Exponential decay: exp(-age / half_life)
            recency_score = math.exp(-age_days / self.recency_half_life)
            return max(0.0, min(1.0, recency_score))

        except (ValueError, TypeError, AttributeError, OverflowError):
            return 0.5

    def _compute_relevance_score(
        self,
        memory_id: int,
        layer: str,
        project_id: int,
        current_goal: Optional[str] = None,
    ) -> float:
        """Score based on relevance to current goal.

        If goal not provided, score based on usefulness.

        Args:
            memory_id: Memory to score
            layer: Memory layer
            project_id: Project context
            current_goal: Current task/goal

        Returns:
            Relevance score (0-1)
        """
        try:
            if current_goal is None:
                # Fallback: use usefulness score
                cursor = self.db.get_cursor()
                if layer == "semantic":
                    query = "SELECT usefulness_score FROM memories WHERE id = ? AND project_id = ?"
                else:
                    # Other layers don't have usefulness_score
                    return 0.5

                cursor.execute(query, (memory_id, project_id))
                result = cursor.fetchone()
                return result[0] if result and result[0] else 0.5

            # Goal-based relevance using embedding similarity
            cursor = self.db.get_cursor()

            # Get memory content
            if layer == "semantic":
                query = "SELECT content FROM memories WHERE id = ? AND project_id = ?"
            elif layer == "episodic":
                query = "SELECT content FROM episodic_events WHERE id = ? AND project_id = ?"
            elif layer == "procedural":
                query = "SELECT template FROM procedures WHERE id = ? AND project_id = ?"
            else:
                return 0.5

            cursor.execute(query, (memory_id, project_id))
            result = cursor.fetchone()

            if not result or not result[0]:
                return 0.0

            memory_content = result[0]

            # Compute semantic similarity using embeddings
            try:
                goal_embedding = self.db.embedding_model.embed(current_goal)
                memory_embedding = self.db.embedding_model.embed(memory_content)

                # Cosine similarity
                dot_product = np.dot(goal_embedding, memory_embedding)
                norm_goal = np.linalg.norm(goal_embedding)
                norm_memory = np.linalg.norm(memory_embedding)

                if norm_goal == 0 or norm_memory == 0:
                    return 0.5

                similarity = dot_product / (norm_goal * norm_memory)

                # Convert from [-1, 1] to [0, 1]
                relevance_score = (similarity + 1.0) / 2.0
                return max(0.0, min(1.0, relevance_score))

            except (AttributeError, ValueError, TypeError, ZeroDivisionError):
                # Fallback if embedding fails
                return 0.5

        except (AttributeError, TypeError, ValueError):
            return 0.5

    def _compute_surprise_score(
        self,
        memory_id: int,
        layer: str,
        project_id: int,
        context_events: Optional[List[int]] = None,
    ) -> float:
        """Score based on surprise value (novelty bonus).

        Novel or unexpected items get attention boost.
        Computed as: 1 - (avg_similarity_to_recent_events)

        Args:
            memory_id: Memory to score
            layer: Memory layer
            project_id: Project context
            context_events: Recent event IDs for context

        Returns:
            Surprise score (0-1)
        """
        try:
            if not context_events or len(context_events) == 0:
                return 0.0

            cursor = self.db.get_cursor()

            # Get memory content
            if layer == "semantic":
                query = "SELECT content FROM memories WHERE id = ? AND project_id = ?"
            elif layer == "episodic":
                query = "SELECT content FROM episodic_events WHERE id = ? AND project_id = ?"
            elif layer == "procedural":
                query = "SELECT template FROM procedures WHERE id = ? AND project_id = ?"
            else:
                return 0.0

            cursor.execute(query, (memory_id, project_id))
            result = cursor.fetchone()

            if not result or not result[0]:
                return 0.0

            memory_content = result[0]

            # Compute embedding similarity to recent events
            try:
                memory_embedding = self.db.embedding_model.embed(memory_content)

                # Get recent event embeddings (last 5)
                recent_similarities = []
                for event_id in context_events[-5:]:
                    cursor.execute(
                        "SELECT content FROM episodic_events WHERE id = ?",
                        (event_id,),
                    )
                    event_result = cursor.fetchone()

                    if event_result and event_result[0]:
                        event_embedding = self.db.embedding_model.embed(
                            event_result[0]
                        )

                        # Cosine similarity
                        dot_product = np.dot(memory_embedding, event_embedding)
                        norm_memory = np.linalg.norm(memory_embedding)
                        norm_event = np.linalg.norm(event_embedding)

                        if norm_memory > 0 and norm_event > 0:
                            similarity = dot_product / (norm_memory * norm_event)
                            recent_similarities.append(similarity)

                if not recent_similarities:
                    return 0.5

                # Average similarity
                avg_similarity = np.mean(recent_similarities)

                # Surprise = 1 - similarity (inverse relationship)
                # Convert from [-1, 1] to [0, 1] range
                surprise_score = 1.0 - (avg_similarity + 1.0) / 2.0
                return max(0.0, min(1.0, surprise_score))

            except (AttributeError, ValueError, TypeError, ZeroDivisionError):
                return 0.0

        except (AttributeError, TypeError, ValueError):
            return 0.0


def saliency_to_focus_type(saliency: float) -> str:
    """Convert saliency score to focus type.

    Args:
        saliency: Saliency score (0-1)

    Returns:
        Focus type: "primary", "secondary", or "background"
    """
    if saliency >= 0.7:
        return "primary"
    elif saliency >= 0.4:
        return "secondary"
    else:
        return "background"


def saliency_to_recommendation(saliency: float) -> str:
    """Provide recommendation based on saliency score.

    Args:
        saliency: Saliency score (0-1)

    Returns:
        Recommendation string
    """
    if saliency >= 0.8:
        return "KEEP_IN_FOCUS: High saliency, critical for current task"
    elif saliency >= 0.6:
        return "MONITOR: Moderate saliency, may be useful"
    elif saliency >= 0.4:
        return "BACKGROUND: Low saliency, not immediately relevant"
    else:
        return "INHIBIT: Very low saliency, consider suppressing"
