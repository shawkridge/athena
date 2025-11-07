"""Observation Memory for ReAct Loop

Implements persistent storage and retrieval of observations from ReAct reasoning loops.
Observations are indexed by action type, result type, and content similarity for
efficient retrieval during future reasoning.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4


class ObservationIndexType(str, Enum):
    """Types of indices for observations"""
    BY_ACTION_TYPE = "by_action_type"
    BY_RESULT_TYPE = "by_result_type"
    BY_RELEVANCE = "by_relevance"
    BY_TEMPORAL = "by_temporal"
    BY_CONTENT = "by_content"


@dataclass
class IndexedObservation:
    """An observation with indexing metadata"""
    id: str = field(default_factory=lambda: str(uuid4()))
    content: str = ""
    action_type: str = ""
    result_type: str = ""
    relevance_score: float = 0.5
    timestamp: datetime = field(default_factory=datetime.now)
    action_context: Dict[str, Any] = field(default_factory=dict)
    surprise_flags: List[str] = field(default_factory=list)
    success: bool = True
    lesson_learned: str = ""
    embeddings: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "content": self.content,
            "action_type": self.action_type,
            "result_type": self.result_type,
            "relevance": self.relevance_score,
            "timestamp": self.timestamp.isoformat(),
            "action_context": self.action_context,
            "surprises": self.surprise_flags,
            "success": self.success,
            "lesson": self.lesson_learned,
            "metadata": self.metadata,
        }


class ObservationMemory:
    """Manages storage and retrieval of observations from ReAct loops"""

    def __init__(self, max_observations: int = 10000):
        """Initialize observation memory

        Args:
            max_observations: Maximum number of observations to store
        """
        self.observations: List[IndexedObservation] = []
        self.max_size = max_observations

        # Indices for efficient retrieval
        self.by_action_type: Dict[str, List[str]] = {}
        self.by_result_type: Dict[str, List[str]] = {}
        self.by_temporal: Dict[str, List[str]] = {}
        self.by_success: Dict[bool, List[str]] = {True: [], False: []}

    def add_observation(
        self,
        content: str,
        action_type: str,
        result_type: str,
        success: bool = True,
        relevance_score: float = 0.5,
        action_context: Optional[Dict[str, Any]] = None,
        surprise_flags: Optional[List[str]] = None,
        lesson_learned: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> IndexedObservation:
        """Add an observation to memory

        Args:
            content: The observation content
            action_type: Type of action (e.g., "query", "retrieve")
            result_type: Type of result (e.g., "success", "partial", "failure")
            success: Whether the action succeeded
            relevance_score: How relevant this observation is (0.0-1.0)
            action_context: Context information about the action
            surprise_flags: Any surprising aspects of this observation
            lesson_learned: Key lesson or insight from this observation
            metadata: Additional metadata

        Returns:
            The created IndexedObservation
        """
        obs = IndexedObservation(
            content=content,
            action_type=action_type,
            result_type=result_type,
            relevance_score=relevance_score,
            action_context=action_context or {},
            surprise_flags=surprise_flags or [],
            success=success,
            lesson_learned=lesson_learned,
            metadata=metadata or {},
        )

        self.observations.append(obs)

        # Update indices
        obs_id = obs.id
        self._index_by_action_type(obs_id, action_type)
        self._index_by_result_type(obs_id, result_type)
        self._index_by_temporal(obs_id, obs.timestamp)
        self._index_by_success(obs_id, success)

        # Maintain size limit
        if len(self.observations) > self.max_size:
            # Remove oldest observations
            removed_count = len(self.observations) - self.max_size
            for removed_obs in self.observations[:removed_count]:
                self._remove_from_indices(removed_obs.id)
            self.observations = self.observations[removed_count:]

        return obs

    def _index_by_action_type(self, obs_id: str, action_type: str) -> None:
        """Add observation to action type index"""
        if action_type not in self.by_action_type:
            self.by_action_type[action_type] = []
        self.by_action_type[action_type].append(obs_id)

    def _index_by_result_type(self, obs_id: str, result_type: str) -> None:
        """Add observation to result type index"""
        if result_type not in self.by_result_type:
            self.by_result_type[result_type] = []
        self.by_result_type[result_type].append(obs_id)

    def _index_by_temporal(self, obs_id: str, timestamp: datetime) -> None:
        """Add observation to temporal index"""
        date_key = timestamp.strftime("%Y-%m-%d")
        if date_key not in self.by_temporal:
            self.by_temporal[date_key] = []
        self.by_temporal[date_key].append(obs_id)

    def _index_by_success(self, obs_id: str, success: bool) -> None:
        """Add observation to success index"""
        self.by_success[success].append(obs_id)

    def _remove_from_indices(self, obs_id: str) -> None:
        """Remove observation from all indices"""
        for obs_list in self.by_action_type.values():
            if obs_id in obs_list:
                obs_list.remove(obs_id)
        for obs_list in self.by_result_type.values():
            if obs_id in obs_list:
                obs_list.remove(obs_id)
        for obs_list in self.by_temporal.values():
            if obs_id in obs_list:
                obs_list.remove(obs_id)
        for obs_list in self.by_success.values():
            if obs_id in obs_list:
                obs_list.remove(obs_id)

    def get_observation(self, obs_id: str) -> Optional[IndexedObservation]:
        """Get observation by ID

        Args:
            obs_id: The observation ID

        Returns:
            The observation or None if not found
        """
        for obs in self.observations:
            if obs.id == obs_id:
                return obs
        return None

    def get_by_action_type(self, action_type: str) -> List[IndexedObservation]:
        """Get all observations for a specific action type

        Args:
            action_type: The action type to search for

        Returns:
            List of matching observations
        """
        obs_ids = self.by_action_type.get(action_type, [])
        return [obs for obs in self.observations if obs.id in obs_ids]

    def get_by_result_type(self, result_type: str) -> List[IndexedObservation]:
        """Get all observations for a specific result type

        Args:
            result_type: The result type to search for

        Returns:
            List of matching observations
        """
        obs_ids = self.by_result_type.get(result_type, [])
        return [obs for obs in self.observations if obs.id in obs_ids]

    def get_successful_observations(self) -> List[IndexedObservation]:
        """Get all successful observations

        Returns:
            List of successful observations
        """
        obs_ids = self.by_success[True]
        return [obs for obs in self.observations if obs.id in obs_ids]

    def get_failed_observations(self) -> List[IndexedObservation]:
        """Get all failed observations

        Returns:
            List of failed observations
        """
        obs_ids = self.by_success[False]
        return [obs for obs in self.observations if obs.id in obs_ids]

    def get_by_date_range(
        self, start_date: str, end_date: str
    ) -> List[IndexedObservation]:
        """Get observations within a date range

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            List of observations in date range
        """
        result = []
        for date_key, obs_ids in self.by_temporal.items():
            if start_date <= date_key <= end_date:
                result.extend([obs for obs in self.observations if obs.id in obs_ids])
        return result

    def get_high_relevance_observations(
        self, threshold: float = 0.7
    ) -> List[IndexedObservation]:
        """Get observations above a relevance threshold

        Args:
            threshold: Minimum relevance score (0.0-1.0)

        Returns:
            List of observations with relevance >= threshold
        """
        return [obs for obs in self.observations if obs.relevance_score >= threshold]

    def get_surprising_observations(self) -> List[IndexedObservation]:
        """Get observations flagged as surprising

        Returns:
            List of observations with surprise flags
        """
        return [obs for obs in self.observations if obs.surprise_flags]

    def get_similar_observations(
        self, query_content: str, action_type: Optional[str] = None, limit: int = 5
    ) -> List[Tuple[IndexedObservation, float]]:
        """Get observations similar to a query (basic substring/keyword matching)

        Args:
            query_content: Content to match against
            action_type: Optional action type filter
            limit: Maximum number of results

        Returns:
            List of (observation, similarity_score) tuples sorted by similarity
        """
        query_words = set(query_content.lower().split())
        candidates = []

        obs_list = (
            self.get_by_action_type(action_type)
            if action_type
            else self.observations
        )

        for obs in obs_list:
            obs_words = set(obs.content.lower().split())
            if not obs_words or not query_words:
                continue

            # Jaccard similarity
            intersection = len(query_words & obs_words)
            union = len(query_words | obs_words)
            similarity = intersection / union if union > 0 else 0.0

            if similarity > 0.0:
                candidates.append((obs, similarity))

        # Sort by similarity and return top results
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about observations in memory

        Returns:
            Dictionary containing observation statistics
        """
        total_obs = len(self.observations)
        successful = len(self.by_success[True])
        failed = len(self.by_success[False])

        return {
            "total_observations": total_obs,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total_obs if total_obs > 0 else 0.0,
            "unique_action_types": len(self.by_action_type),
            "unique_result_types": len(self.by_result_type),
            "observations_with_surprises": sum(
                1 for obs in self.observations if obs.surprise_flags
            ),
            "average_relevance": (
                sum(obs.relevance_score for obs in self.observations) / total_obs
                if total_obs > 0
                else 0.0
            ),
            "action_type_distribution": {
                action_type: len(obs_ids)
                for action_type, obs_ids in self.by_action_type.items()
            },
        }

    def get_lessons_learned(self) -> List[Tuple[str, str]]:
        """Get all lessons learned from observations

        Returns:
            List of (action_type, lesson) tuples
        """
        lessons = []
        for obs in self.observations:
            if obs.lesson_learned:
                lessons.append((obs.action_type, obs.lesson_learned))
        return lessons

    def get_common_issues(self, action_type: Optional[str] = None) -> List[str]:
        """Get common failure patterns

        Args:
            action_type: Optional action type filter

        Returns:
            List of common issues found in failed observations
        """
        failed = (
            self.get_by_action_type(action_type)
            if action_type
            else self.get_failed_observations()
        )

        # Collect common issue patterns
        issues = []
        for obs in failed:
            if obs.lesson_learned:
                issues.append(obs.lesson_learned)

        # Count occurrences
        issue_counts: Dict[str, int] = {}
        for issue in issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

        # Sort by frequency
        sorted_issues = sorted(
            issue_counts.items(), key=lambda x: x[1], reverse=True
        )
        return [issue for issue, _ in sorted_issues]

    def export_to_dict(self) -> Dict[str, Any]:
        """Export all observations to dictionary

        Returns:
            Dictionary representation of all observations and indices
        """
        return {
            "observations": [obs.to_dict() for obs in self.observations],
            "indices": {
                "by_action_type": {
                    k: len(v) for k, v in self.by_action_type.items()
                },
                "by_result_type": {k: len(v) for k, v in self.by_result_type.items()},
                "by_success": {
                    "successful": len(self.by_success[True]),
                    "failed": len(self.by_success[False]),
                },
            },
            "statistics": self.get_statistics(),
        }

    def clear_memory(self) -> None:
        """Clear all observations and indices"""
        self.observations.clear()
        self.by_action_type.clear()
        self.by_result_type.clear()
        self.by_temporal.clear()
        self.by_success = {True: [], False: []}
