"""High-level service for planning recommendations using RAG.

Recommends planning strategies based on:
- Historical planning patterns and success rates
- Task characteristics (type, complexity, domain)
- Similar tasks from the past
- Pattern effectiveness scores
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PatternRecommendation:
    """Recommendation for a planning pattern."""

    pattern_name: str
    pattern_type: str
    success_rate: float  # 0.0 - 1.0
    execution_count: int
    confidence: str  # "low", "medium", "high"
    rationale: str
    decomposition_strategy: Optional[Dict[str, Any]] = None
    alternative_patterns: Optional[List[str]] = None


class PlanningRecommendationService:
    """Service for intelligent planning recommendations.

    Leverages RAG (Retrieval-Augmented Generation) to recommend
    planning strategies based on historical patterns and success metrics.

    Features:
    - Retrieves relevant patterns for task characteristics
    - Ranks patterns by effectiveness
    - Calculates confidence scores
    - Generates human-readable explanations
    - Provides alternative strategies
    """

    def __init__(self, planning_store: Any, planning_rag: Any = None):
        """Initialize planning recommendation service.

        Args:
            planning_store: Planning store for accessing patterns and strategies
            planning_rag: Optional RAG manager for advanced pattern retrieval
        """
        self.planning_store = planning_store
        self.planning_rag = planning_rag
        self.db = planning_store.db if hasattr(planning_store, 'db') else None

    async def recommend_for_task(
        self,
        project_id: int,
        task_description: str,
        task_type: str,
        complexity: int,
        domain: str = "general",
        min_success_rate: float = 0.60,
    ) -> List[PatternRecommendation]:
        """Get recommended planning patterns for a task.

        Args:
            project_id: Project ID for context
            task_description: Description of the task to plan
            task_type: Type of task (feature, bugfix, refactor, etc.)
            complexity: Complexity level (1-10)
            domain: Domain (web, mobile, infra, etc.)
            min_success_rate: Minimum success rate to recommend (0.0-1.0)

        Returns:
            List of pattern recommendations sorted by effectiveness
        """
        try:
            # Get relevant patterns from store or RAG
            relevant_patterns = await self._get_relevant_patterns(
                project_id=project_id,
                task_description=task_description,
                task_type=task_type,
                complexity=complexity,
                domain=domain,
                min_success_rate=min_success_rate,
            )

            if not relevant_patterns:
                logger.warning(
                    f"No patterns found for task type={task_type}, "
                    f"complexity={complexity}, domain={domain}"
                )
                return []

            # Rank patterns by effectiveness
            ranked_patterns = self._rank_by_effectiveness(relevant_patterns)

            # Generate recommendations
            recommendations = []
            for pattern in ranked_patterns[:3]:  # Top 3 patterns
                rec = await self._create_recommendation(pattern, task_description)
                if rec:
                    recommendations.append(rec)

            logger.info(
                f"Generated {len(recommendations)} planning recommendations "
                f"for task type={task_type}, complexity={complexity}"
            )
            return recommendations

        except Exception as e:
            logger.error(f"Error generating planning recommendations: {e}", exc_info=True)
            return []

    async def _get_relevant_patterns(
        self,
        project_id: int,
        task_description: str,
        task_type: str,
        complexity: int,
        domain: str,
        min_success_rate: float,
    ) -> List[Dict[str, Any]]:
        """Get patterns relevant to this task.

        Uses RAG if available, otherwise falls back to database query.

        Args:
            project_id: Project ID
            task_description: Task description
            task_type: Type of task
            complexity: Task complexity (1-10)
            domain: Task domain
            min_success_rate: Minimum success rate threshold

        Returns:
            List of relevant patterns
        """
        try:
            # Try RAG if available
            if self.planning_rag and hasattr(self.planning_rag, "recommend_patterns"):
                patterns = await self.planning_rag.recommend_patterns(
                    query=task_description,
                    project_id=project_id,
                    filters={
                        "applicable_domains": [domain],
                        "applicable_task_types": [task_type],
                        "complexity_range": [max(1, complexity - 2), min(10, complexity + 2)],
                    },
                    min_success_rate=min_success_rate,
                )
                if patterns:
                    return patterns
        except Exception as e:
            logger.warning(f"RAG pattern retrieval failed, falling back to database: {e}")

        # Fallback to database query
        if self.planning_store and hasattr(self.planning_store, "get_patterns_for_task"):
            try:
                patterns = self.planning_store.get_patterns_for_task(
                    task_type=task_type,
                    domain=domain,
                    min_success_rate=min_success_rate,
                )
                return patterns if patterns else []
            except Exception as e:
                logger.error(f"Database pattern retrieval failed: {e}")

        return []

    def _rank_by_effectiveness(
        self, patterns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rank patterns by success rate and execution count.

        Higher success rates and more executions = higher rank.

        Args:
            patterns: List of patterns to rank

        Returns:
            Sorted list of patterns
        """
        def rank_key(pattern):
            success_rate = pattern.get("success_rate", 0.0)
            execution_count = pattern.get("execution_count", 0)
            recency_score = pattern.get("recency_score", 0.5)

            # Weighted scoring: success rate is primary, count is secondary, recency is tertiary
            return (
                success_rate * 100,  # Success rate weight: 100
                execution_count,     # Execution count weight: 1
                recency_score,       # Recency weight: 0-1
            )

        return sorted(patterns, key=rank_key, reverse=True)

    async def _create_recommendation(
        self, pattern: Dict[str, Any], task_description: str
    ) -> Optional[PatternRecommendation]:
        """Create a recommendation from a pattern.

        Args:
            pattern: Pattern data from database/RAG
            task_description: Description of the task

        Returns:
            PatternRecommendation or None if invalid
        """
        try:
            pattern_name = pattern.get("name", pattern.get("pattern_type", "unknown"))
            pattern_type = pattern.get("pattern_type", "decomposition")
            success_rate = pattern.get("success_rate", 0.5)
            execution_count = pattern.get("execution_count", 0)

            confidence = self._calculate_confidence(pattern)
            rationale = self._generate_rationale(pattern, task_description)

            # Get decomposition strategy if available
            strategy = None
            if self.planning_store and hasattr(self.planning_store, "get_strategy_for_pattern"):
                try:
                    strategy = self.planning_store.get_strategy_for_pattern(pattern_type)
                except Exception as e:
                    logger.debug(f"Could not retrieve strategy for pattern {pattern_type}: {e}")

            return PatternRecommendation(
                pattern_name=pattern_name,
                pattern_type=pattern_type,
                success_rate=success_rate,
                execution_count=execution_count,
                confidence=confidence,
                rationale=rationale,
                decomposition_strategy=strategy,
                alternative_patterns=pattern.get("alternatives", []),
            )

        except Exception as e:
            logger.error(f"Error creating recommendation: {e}")
            return None

    def _calculate_confidence(self, pattern: Dict[str, Any]) -> str:
        """Calculate confidence based on pattern usage and recency.

        - Low: Less than 5 uses or haven't been used recently
        - Medium: 5-20 uses, reasonable recent activity
        - High: 20+ uses, frequently used and recent

        Args:
            pattern: Pattern data

        Returns:
            "low", "medium", or "high"
        """
        execution_count = pattern.get("execution_count", 0)
        recency_score = pattern.get("recency_score", 0.5)

        if execution_count < 5 or recency_score < 0.3:
            return "low"
        elif execution_count < 20 or recency_score < 0.7:
            return "medium"
        else:
            return "high"

    def _generate_rationale(self, pattern: Dict[str, Any], task_description: str) -> str:
        """Generate human-readable explanation for the recommendation.

        Args:
            pattern: Pattern data
            task_description: Task description (for context)

        Returns:
            Explanation string
        """
        pattern_name = pattern.get("name", pattern.get("pattern_type", "Strategy"))
        success_rate = pattern.get("success_rate", 0.0)
        execution_count = pattern.get("execution_count", 0)
        applicable_types = pattern.get("applicable_task_types", [])

        rationale = f"{pattern_name}: {int(success_rate * 100)}% success rate"

        if execution_count > 0:
            rationale += f" ({execution_count} uses)"

        if applicable_types:
            rationale += f". Works well for {', '.join(applicable_types)}"

        rationale += "."

        return rationale

    async def get_strategy_details(
        self, pattern_type: str, task_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get detailed strategy information for a pattern.

        Args:
            pattern_type: Type of pattern/strategy
            task_id: Optional task ID for context

        Returns:
            Strategy details dict
        """
        try:
            if self.planning_store and hasattr(self.planning_store, "get_strategy_for_pattern"):
                strategy = self.planning_store.get_strategy_for_pattern(pattern_type)
                if strategy:
                    return strategy

            # Return default strategy structure
            return {
                "pattern_type": pattern_type,
                "decomposition_type": "hierarchical",
                "chunk_size_minutes": 120,
                "max_depth": 3,
                "success_rate": 0.0,
                "steps": [],
            }

        except Exception as e:
            logger.error(f"Error getting strategy details: {e}")
            return {}
