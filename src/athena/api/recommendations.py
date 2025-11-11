"""Recommendations engine for marketplace procedures."""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from .marketplace import MarketplaceProcedure
from .marketplace_store import MarketplaceStore
from .semantic_search import SemanticProcedureSearch


class RecommendationEngine:
    """Engine for recommending marketplace procedures to users/agents."""

    def __init__(self, marketplace_store: MarketplaceStore, semantic_search: SemanticProcedureSearch):
        """Initialize recommendations engine.

        Args:
            marketplace_store: MarketplaceStore instance
            semantic_search: SemanticProcedureSearch instance
        """
        self.store = marketplace_store
        self.search = semantic_search
        self.user_history: Dict[str, List[str]] = {}
        self.user_preferences: Dict[str, Dict[str, Any]] = {}

    def recommend_for_use_case(
        self,
        use_case_description: str,
        limit: int = 5,
        require_stable: bool = False,
    ) -> List[MarketplaceProcedure]:
        """Recommend procedures for a specific use case.

        Args:
            use_case_description: Natural language description of use case
            limit: Maximum number of recommendations
            require_stable: Only recommend stable/production quality

        Returns:
            List of recommended procedures
        """
        # Get semantically relevant procedures
        candidates = self.search.search_by_use_case(use_case_description, limit=limit * 2)

        # Filter by quality if required
        if require_stable:
            candidates = [
                p for p in candidates
                if p.metadata.quality_level.value in ("stable", "production")
            ]

        # Score and sort
        scored = [(p, self._score_procedure(p)) for p in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)

        return [p for p, _ in scored[:limit]]

    def recommend_for_user(
        self,
        user_id: str,
        limit: int = 5,
    ) -> List[MarketplaceProcedure]:
        """Recommend procedures based on user history and preferences.

        Args:
            user_id: User/agent ID
            limit: Maximum number of recommendations

        Returns:
            List of personalized recommendations
        """
        # Get user history
        history = self.user_history.get(user_id, [])
        preferences = self.user_preferences.get(user_id, {})

        if not history:
            # New user: recommend trending stable procedures
            return self.search.get_quality_recommendations("stable", limit)

        # Find related procedures based on history
        recommendations = set()

        for proc_id in history:
            related = self.search.search_related_procedures(proc_id, limit=3)
            recommendations.update([p.metadata.procedure_id for p, _ in related])

        # Remove already-used procedures
        recommendations.difference_update(history)

        # Fetch and score recommendations
        procedures = []
        for proc_id in recommendations:
            procedure = self.store.get_procedure(proc_id)
            if procedure:
                score = self._personalize_score(procedure, user_id, preferences)
                procedures.append((procedure, score))

        # Sort by personalized score
        procedures.sort(key=lambda x: x[1], reverse=True)

        return [p for p, _ in procedures[:limit]]

    def recommend_by_tags(
        self,
        tags: List[str],
        limit: int = 5,
        boost_recent: bool = True,
    ) -> List[MarketplaceProcedure]:
        """Recommend procedures matching specific tags.

        Args:
            tags: List of tags/keywords
            limit: Maximum number of recommendations
            boost_recent: Boost recently updated procedures

        Returns:
            List of recommended procedures
        """
        candidates = self.search.search_by_tags_semantic(tags, limit=limit * 2)

        if boost_recent:
            # Sort by update date
            candidates.sort(
                key=lambda p: p.metadata.updated_at or datetime.now(),
                reverse=True,
            )

        return candidates[:limit]

    def recommend_high_quality(
        self,
        limit: int = 10,
        min_rating: float = 4.0,
    ) -> List[MarketplaceProcedure]:
        """Recommend highly-rated, stable procedures.

        Args:
            limit: Maximum number of recommendations
            min_rating: Minimum average rating

        Returns:
            List of high-quality procedures
        """
        cursor = self.store.db.conn.cursor()
        cursor.execute(
            """
            SELECT p.procedure_id, AVG(r.rating) as avg_rating, p.success_rate
            FROM marketplace_procedures p
            LEFT JOIN marketplace_reviews r ON p.procedure_id = r.procedure_id
            WHERE p.quality_level IN ('stable', 'production')
            GROUP BY p.procedure_id
            HAVING avg_rating >= ? OR avg_rating IS NULL
            ORDER BY COALESCE(avg_rating, 5.0) DESC, p.success_rate DESC
            LIMIT ?
            """,
            (min_rating, limit),
        )

        procedures = []
        for row in cursor.fetchall():
            procedure = self.store.get_procedure(row[0])
            if procedure:
                procedures.append(procedure)

        return procedures

    def recommend_similar_to(
        self,
        procedure_id: str,
        limit: int = 5,
    ) -> List[MarketplaceProcedure]:
        """Recommend procedures similar to a reference procedure.

        Args:
            procedure_id: Reference procedure ID
            limit: Maximum number of recommendations

        Returns:
            List of similar procedures
        """
        related = self.search.search_related_procedures(procedure_id, limit=limit)
        return [p for p, _ in related]

    def get_trending_recommendations(
        self,
        days: int = 30,
        limit: int = 10,
    ) -> List[MarketplaceProcedure]:
        """Get recommendations based on trending procedures.

        Args:
            days: Time window for trending (default 30 days)
            limit: Maximum number of recommendations

        Returns:
            List of trending procedures
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        cursor = self.store.db.conn.cursor()
        cursor.execute(
            """
            SELECT procedure_id, COUNT(*) as install_count
            FROM marketplace_installations
            WHERE installed_at >= ?
            GROUP BY procedure_id
            ORDER BY install_count DESC
            LIMIT ?
            """,
            (cutoff_date.isoformat(), limit),
        )

        procedures = []
        for row in cursor.fetchall():
            procedure = self.store.get_procedure(row[0])
            if procedure:
                procedures.append(procedure)

        return procedures

    def record_user_interaction(
        self,
        user_id: str,
        procedure_id: str,
        interaction_type: str,  # "view", "execute", "install", "rate"
    ):
        """Record user interaction for personalization.

        Args:
            user_id: User/agent ID
            procedure_id: Procedure ID
            interaction_type: Type of interaction
        """
        if user_id not in self.user_history:
            self.user_history[user_id] = []
            self.user_preferences[user_id] = {}

        # Add to history (avoid duplicates)
        if procedure_id not in self.user_history[user_id]:
            self.user_history[user_id].append(procedure_id)

        # Update preferences
        if "interaction_types" not in self.user_preferences[user_id]:
            self.user_preferences[user_id]["interaction_types"] = {}

        prefs = self.user_preferences[user_id]["interaction_types"]
        prefs[interaction_type] = prefs.get(interaction_type, 0) + 1

    def get_next_steps(
        self,
        current_procedure_id: str,
        user_id: Optional[str] = None,
        limit: int = 3,
    ) -> List[MarketplaceProcedure]:
        """Get recommended next procedures after using one.

        Args:
            current_procedure_id: Current procedure ID
            user_id: Optional user ID for personalization
            limit: Maximum number of recommendations

        Returns:
            List of next recommended procedures
        """
        current = self.store.get_procedure(current_procedure_id)
        if not current:
            return []

        # Start with related procedures
        recommendations = self.recommend_similar_to(current_procedure_id, limit=limit * 2)

        # If user history exists, boost matching preferences
        if user_id and user_id in self.user_history:
            recommendations = sorted(
                recommendations,
                key=lambda p: self._personalize_score(p, user_id, self.user_preferences[user_id]),
                reverse=True,
            )

        return recommendations[:limit]

    def _score_procedure(self, procedure: MarketplaceProcedure) -> float:
        """Score a procedure based on quality metrics.

        Args:
            procedure: Procedure to score

        Returns:
            Score (0.0-10.0)
        """
        metadata = procedure.metadata

        # Quality level weight
        quality_weights = {
            "experimental": 2.0,
            "beta": 5.0,
            "stable": 8.0,
            "production": 10.0,
        }
        quality_score = quality_weights.get(metadata.quality_level.value, 5.0)

        # Success rate weight
        success_score = metadata.success_rate * 2.0

        # Installation popularity
        installation_count = self.store.get_installation_count(metadata.procedure_id)
        popularity_score = min(installation_count / 100.0, 2.0)

        # Rating score
        rating = self.store.get_average_rating(metadata.procedure_id) or 0.0
        rating_score = (rating / 5.0) * 2.0

        # Combine scores
        total = (quality_score * 0.4 + success_score * 0.2 + popularity_score * 0.2 + rating_score * 0.2)

        return total

    def _personalize_score(
        self,
        procedure: MarketplaceProcedure,
        user_id: str,
        preferences: Dict[str, Any],
    ) -> float:
        """Score a procedure with user personalization.

        Args:
            procedure: Procedure to score
            user_id: User ID
            preferences: User preferences

        Returns:
            Personalized score (0.0-10.0)
        """
        base_score = self._score_procedure(procedure)

        # Check for user category/tag preferences
        if "preferred_categories" in preferences:
            if procedure.metadata.use_case.value in preferences["preferred_categories"]:
                base_score += 2.0

        if "preferred_tags" in preferences:
            matching_tags = set(procedure.metadata.tags) & set(preferences["preferred_tags"])
            base_score += min(len(matching_tags) * 0.5, 2.0)

        # Check for disliked categories
        if "disliked_categories" in preferences:
            if procedure.metadata.use_case.value in preferences["disliked_categories"]:
                base_score -= 3.0

        return max(base_score, 0.0)
