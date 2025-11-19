"""Planning-aware RAG module for intelligent query routing and pattern recommendations."""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ..core.models import MemorySearchResult
from ..semantic.store import SemanticStore
from ..planning.models import (
    ExecutionOutcome,
    PlanningPattern,
    DecompositionStrategy,
    OrchestratorPattern,
    ValidationRule,
)
from ..planning.store import PlanningStore
from .llm_client import LLMClient

logger = logging.getLogger(__name__)

# Planning-related keywords for query classification
PLANNING_KEYWORDS = {
    "decompose",
    "break down",
    "split",
    "chunk",
    "hierarchical",
    "recursive",
    "planning",
    "strategy",
    "approach",
    "structure",
    "organize",
    "orchestrate",
    "coordinate",
    "validate",
    "verify",
    "check",
    "ensure",
    "pattern",
    "workflow",
    "process",
    "procedure",
    "timeline",
    "estimate",
    "duration",
    "complexity",
    "difficulty",
}


@dataclass
class PatternRecommendation:
    """Recommendation for a planning pattern."""

    pattern: PlanningPattern
    confidence: float  # 0.0-1.0
    rationale: str
    similar_past_tasks: int
    success_rate: float
    applicable_domains: List[str]
    applicable_task_types: List[str]


@dataclass
class FailureAnalysis:
    """Analysis of failures from past projects."""

    failure_type: str  # planning_failure, execution_failure, quality_issue
    root_causes: List[str]
    prevention_strategies: List[str]
    alternative_approaches: List[str]
    similar_past_failures: int
    success_rate_with_alternatives: float


@dataclass
class HybridSearchResult:
    """Result from hybrid planning-aware search."""

    semantic_results: List[MemorySearchResult]
    planning_results: List[PlanningPattern]
    orchestration_results: List[OrchestratorPattern]
    validation_results: List[ValidationRule]
    recommended_strategy: Optional[DecompositionStrategy]
    hybrid_score: float  # Blended relevance score


class PlanningQueryClassifier:
    """Classifies whether a query is planning-related."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """Initialize query classifier.

        Args:
            llm_client: Optional LLM client for semantic classification
        """
        self.llm = llm_client

    def classify(self, query: str) -> Tuple[bool, float]:
        """Classify if query is planning-related.

        Args:
            query: User query

        Returns:
            Tuple of (is_planning_query, confidence)
        """
        # Keyword-based heuristic
        query_lower = query.lower()
        keyword_matches = sum(1 for kw in PLANNING_KEYWORDS if kw in query_lower)
        # Calculate confidence: 1 match = 0.5, 2 matches = 0.75, 3+ matches = 1.0
        if keyword_matches == 0:
            keyword_confidence = 0.0
        elif keyword_matches == 1:
            keyword_confidence = 0.5
        elif keyword_matches == 2:
            keyword_confidence = 0.75
        else:
            keyword_confidence = 1.0

        # If keyword confidence is high, return early
        if keyword_confidence >= 0.7:
            return True, keyword_confidence

        # Use LLM if available for semantic classification
        if self.llm:
            try:
                # Ask LLM to classify
                response = self.llm.generate(
                    f"Is this a planning/task decomposition query? Respond with 'yes' or 'no':\n\n{query}",
                    temperature=0.1,
                )
                is_planning = "yes" in response.lower()
                llm_confidence = 0.8 if is_planning else 0.5
                return is_planning, llm_confidence
            except Exception as e:
                logger.warning(f"LLM classification failed: {e}. Using keyword heuristic.")

        # Default: use keyword heuristic
        return keyword_confidence >= 0.3, keyword_confidence


class PatternRecommender:
    """Recommends planning patterns with confidence scoring."""

    def __init__(self, planning_store: PlanningStore, llm_client: Optional[LLMClient] = None):
        """Initialize pattern recommender.

        Args:
            planning_store: Planning store for pattern queries
            llm_client: Optional LLM client for semantic matching
        """
        self.store = planning_store
        self.llm = llm_client

    def recommend_patterns(
        self,
        task_description: str,
        task_type: Optional[str] = None,
        complexity: Optional[int] = None,
        domain: Optional[str] = None,
        project_id: int = 1,
        k: int = 3,
    ) -> List[PatternRecommendation]:
        """Recommend planning patterns for a task.

        Args:
            task_description: Description of the task
            task_type: Optional task type (e.g., 'refactoring', 'feature')
            complexity: Optional complexity level (1-10)
            domain: Optional domain (e.g., 'backend', 'frontend')
            project_id: Project ID for filtering
            k: Number of recommendations to return

        Returns:
            Ordered list of pattern recommendations (highest confidence first)
        """
        recommendations = []

        # Find patterns by task type if provided
        if task_type:
            patterns = self.store.find_patterns_by_task_type(project_id, task_type)
            for pattern in patterns[:k]:
                rec = self._score_pattern(pattern, task_description, complexity, domain)
                recommendations.append(rec)

        # Find patterns by domain if provided
        if domain and len(recommendations) < k:
            domain_patterns = self.store.find_patterns_by_domain(project_id, domain)
            for pattern in domain_patterns[:k]:
                # Skip if already recommended
                if not any(r.pattern.id == pattern.id for r in recommendations):
                    rec = self._score_pattern(pattern, task_description, complexity, domain)
                    recommendations.append(rec)

        # Sort by confidence (highest first)
        recommendations.sort(key=lambda r: r.confidence, reverse=True)

        return recommendations[:k]

    def _score_pattern(
        self,
        pattern: PlanningPattern,
        task_description: str,
        complexity: Optional[int] = None,
        domain: Optional[str] = None,
    ) -> PatternRecommendation:
        """Score a pattern's relevance to a task.

        Args:
            pattern: Pattern to score
            task_description: Task description for semantic matching
            complexity: Task complexity level
            domain: Task domain

        Returns:
            Pattern recommendation with confidence score
        """
        # Base score from success rate
        base_score = pattern.success_rate

        # Complexity matching
        complexity_score = 1.0
        if complexity is not None:
            pattern_min, pattern_max = pattern.complexity_range
            if pattern_min <= complexity <= pattern_max:
                complexity_score = 1.0
            else:
                # Penalty for out-of-range complexity
                distance = min(
                    abs(complexity - pattern_min),
                    abs(complexity - pattern_max),
                )
                complexity_score = max(0.5, 1.0 - (distance * 0.1))

        # Domain matching
        domain_score = 1.0
        if domain and pattern.applicable_domains:
            if domain in pattern.applicable_domains:
                domain_score = 1.0
            else:
                domain_score = 0.6

        # Semantic matching using LLM if available
        semantic_score = 0.8
        if self.llm:
            try:
                response = self.llm.generate(
                    f"How relevant is this pattern to the task? Respond with a number 0-10.\n\n"
                    f"Pattern: {pattern.description}\n\n"
                    f"Task: {task_description}",
                    temperature=0.1,
                )
                # Extract number from response
                try:
                    score = float("".join(filter(str.isdigit, response.split()[0])))
                    semantic_score = min(score / 10.0, 1.0)
                except (ValueError, IndexError):
                    semantic_score = 0.8
            except Exception as e:
                logger.warning(f"Semantic scoring failed: {e}")

        # Combine scores
        confidence = (
            base_score * 0.4 + complexity_score * 0.2 + domain_score * 0.2 + semantic_score * 0.2
        )

        # Count similar past tasks (execution_count as proxy)
        similar_tasks = pattern.execution_count

        return PatternRecommendation(
            pattern=pattern,
            confidence=confidence,
            rationale=f"Pattern '{pattern.name}' applies to {domain or 'general'} domain "
            f"with {pattern.success_rate:.0%} success rate. "
            f"Used in {similar_tasks} past tasks.",
            similar_past_tasks=similar_tasks,
            success_rate=pattern.success_rate,
            applicable_domains=pattern.applicable_domains,
            applicable_task_types=pattern.applicable_task_types,
        )


class HybridPlanningSearch:
    """Hybrid search combining semantic search and planning logic."""

    def __init__(
        self,
        memory_store: SemanticStore,
        planning_store: PlanningStore,
        llm_client: Optional[LLMClient] = None,
    ):
        """Initialize hybrid search.

        Args:
            memory_store: Memory store for semantic search
            planning_store: Planning store for pattern queries
            llm_client: Optional LLM client for advanced matching
        """
        self.memory_store = memory_store
        self.planning_store = planning_store
        self.llm = llm_client
        self.pattern_recommender = PatternRecommender(planning_store, llm_client)

    def search(
        self,
        query: str,
        project_id: int = 1,
        k: int = 5,
        semantic_weight: float = 0.5,
        planning_weight: float = 0.5,
    ) -> HybridSearchResult:
        """Perform hybrid search combining semantic and planning logic.

        Args:
            query: User query
            project_id: Project ID
            k: Number of results per category
            semantic_weight: Weight for semantic results (0.0-1.0)
            planning_weight: Weight for planning results (0.0-1.0)

        Returns:
            Hybrid search result with blended results
        """
        # Semantic search
        semantic_results = self.memory_store.search(query, project_id=project_id, k=k)

        # Extract task context from query for planning search
        task_type = self._extract_task_type(query)
        complexity = self._extract_complexity(query)
        domain = self._extract_domain(query)

        # Planning pattern search
        planning_patterns = []
        if task_type:
            patterns = self.planning_store.find_patterns_by_task_type(project_id, task_type)
            planning_patterns = patterns[:k]

        # Orchestration search
        orchestration_patterns = []
        if "orchestrate" in query.lower() or "coordinate" in query.lower():
            # Find orchestration patterns (using planning store)
            orchestration_patterns = self.planning_store.find_orchestration_patterns(
                project_id, num_agents=None
            )[:k]

        # Validation rules search
        validation_rules = []
        if "validate" in query.lower() or "verify" in query.lower():
            validation_rules = self.planning_store.find_validation_rules_by_risk(
                project_id, "high"
            )[:k]

        # Recommend decomposition strategy
        recommended_strategy = None
        if task_type:
            strategies = self.planning_store.find_strategies_by_type(project_id, task_type)
            if strategies:
                recommended_strategy = strategies[0]  # Highest success rate

        # Calculate hybrid score
        hybrid_score = (
            (sum(r.similarity for r in semantic_results) / len(semantic_results))
            if semantic_results
            else 0.0
        ) * semantic_weight + (
            (sum(p.success_rate for p in planning_patterns) / len(planning_patterns))
            if planning_patterns
            else 0.0
        ) * planning_weight

        return HybridSearchResult(
            semantic_results=semantic_results,
            planning_results=planning_patterns,
            orchestration_results=orchestration_patterns,
            validation_results=validation_rules,
            recommended_strategy=recommended_strategy,
            hybrid_score=hybrid_score,
        )

    def _extract_task_type(self, query: str) -> Optional[str]:
        """Extract task type from query (heuristic).

        Args:
            query: User query

        Returns:
            Inferred task type or None
        """
        task_keywords = {
            "refactoring": ["refactor", "reorganize", "restructure"],
            "feature": ["add", "implement", "new", "create"],
            "bug-fix": ["fix", "bug", "issue", "problem"],
            "testing": ["test", "coverage", "validate"],
        }

        query_lower = query.lower()
        for task_type, keywords in task_keywords.items():
            if any(kw in query_lower for kw in keywords):
                return task_type

        return None

    def _extract_complexity(self, query: str) -> Optional[int]:
        """Extract complexity level from query (heuristic).

        Args:
            query: User query

        Returns:
            Estimated complexity (1-10) or None
        """
        if "simple" in query.lower() or "easy" in query.lower():
            return 3
        elif "complex" in query.lower() or "complicated" in query.lower():
            return 7
        elif "trivial" in query.lower():
            return 1
        elif "challenging" in query.lower() or "difficult" in query.lower():
            return 8

        return None

    def _extract_domain(self, query: str) -> Optional[str]:
        """Extract domain from query (heuristic).

        Args:
            query: User query

        Returns:
            Inferred domain or None
        """
        domain_keywords = {
            "backend": ["backend", "api", "server", "database", "db"],
            "frontend": ["frontend", "ui", "ux", "react", "vue", "angular"],
            "devops": ["deploy", "infrastructure", "ci/cd", "kubernetes"],
            "database": ["database", "db", "sql", "query"],
        }

        query_lower = query.lower()
        for domain, keywords in domain_keywords.items():
            if any(kw in query_lower for kw in keywords):
                return domain

        return None


class FailureAnalyzer:
    """Analyzes failures from past projects and recommends prevention strategies."""

    def __init__(self, planning_store: PlanningStore, llm_client: Optional[LLMClient] = None):
        """Initialize failure analyzer.

        Args:
            planning_store: Planning store for feedback queries
            llm_client: Optional LLM client for analysis
        """
        self.store = planning_store
        self.llm = llm_client

    def analyze_failure_type(
        self,
        failure_type: str,  # planning_failure, execution_failure, quality_issue
        context: Optional[str] = None,
        project_id: int = 1,
    ) -> Optional[FailureAnalysis]:
        """Analyze failures of a specific type.

        Args:
            failure_type: Type of failure to analyze
            context: Optional context about the failure
            project_id: Project ID

        Returns:
            Failure analysis with prevention strategies or None if no data
        """
        # Map failure type to execution outcomes
        failure_outcome_map = {
            "planning_failure": ExecutionOutcome.FAILURE,
            "execution_failure": ExecutionOutcome.FAILURE,
            "quality_issue": ExecutionOutcome.PARTIAL,
            "blocked": ExecutionOutcome.BLOCKED,
        }

        outcome = failure_outcome_map.get(failure_type)
        if not outcome:
            return None

        # Get all feedback records
        cursor = self.store.db.conn.cursor()
        cursor.execute(
            "SELECT * FROM execution_feedback WHERE project_id = ? AND execution_outcome = ?",
            (project_id, outcome.value),
        )
        rows = cursor.fetchall()

        if not rows:
            return None

        # Extract failure data
        blockers = []
        assumptions_violated = []
        for row in rows:
            # Parse blockers
            if row[11]:  # blockers_encountered column
                blockers.extend(str(row[11]).split(";"))
            # Parse assumption violations
            if row[13]:  # assumption_violations column
                assumptions_violated.extend(str(row[13]).split(";"))

        # Analyze with LLM if available
        prevention_strategies = []
        alternative_approaches = []
        if self.llm and blockers:
            try:
                # Ask LLM for prevention strategies
                response = self.llm.generate(
                    f"Given these blockers: {', '.join(blockers[:3])}\n\n"
                    f"What are 3 prevention strategies?",
                    temperature=0.7,
                )
                prevention_strategies = [s.strip() for s in response.split("\n") if s.strip()][:3]
            except Exception as e:
                logger.warning(f"LLM prevention strategy generation failed: {e}")

        # Calculate success rate with alternatives
        success_count = sum(1 for row in rows if row[5] == ExecutionOutcome.SUCCESS.value)
        success_rate_with_alternatives = success_count / len(rows) if rows else 0.0

        return FailureAnalysis(
            failure_type=failure_type,
            root_causes=[b.strip() for b in blockers if b.strip()][:3],
            prevention_strategies=prevention_strategies,
            alternative_approaches=alternative_approaches,
            similar_past_failures=len(rows),
            success_rate_with_alternatives=success_rate_with_alternatives,
        )


class PlanningRAGRouter:
    """Unified planning-aware RAG routing system."""

    def __init__(
        self,
        memory_store: SemanticStore,
        planning_store: PlanningStore,
        llm_client: Optional[LLMClient] = None,
    ):
        """Initialize planning RAG router.

        Args:
            memory_store: Memory store for semantic search
            planning_store: Planning store for pattern queries
            llm_client: Optional LLM client for advanced features
        """
        self.memory_store = memory_store
        self.planning_store = planning_store
        self.llm = llm_client

        self.classifier = PlanningQueryClassifier(llm_client)
        self.pattern_recommender = PatternRecommender(planning_store, llm_client)
        self.hybrid_search = HybridPlanningSearch(memory_store, planning_store, llm_client)
        self.failure_analyzer = FailureAnalyzer(planning_store, llm_client)

    def route_query(
        self,
        query: str,
        project_id: int = 1,
        task_type: Optional[str] = None,
        complexity: Optional[int] = None,
        domain: Optional[str] = None,
    ) -> Dict:
        """Route query through planning-aware RAG system.

        Args:
            query: User query
            project_id: Project ID
            task_type: Optional task type hint
            complexity: Optional complexity hint
            domain: Optional domain hint

        Returns:
            Dict with planning recommendations and search results
        """
        # Classify query
        is_planning_query, classification_confidence = self.classifier.classify(query)

        result = {
            "query": query,
            "is_planning_query": is_planning_query,
            "classification_confidence": classification_confidence,
            "pattern_recommendations": [],
            "hybrid_search_results": None,
            "failure_analysis": None,
        }

        if is_planning_query:
            # Recommend patterns
            patterns = self.pattern_recommender.recommend_patterns(
                query,
                task_type=task_type,
                complexity=complexity,
                domain=domain,
                project_id=project_id,
            )
            result["pattern_recommendations"] = patterns

            # Hybrid search
            hybrid_results = self.hybrid_search.search(query, project_id=project_id)
            result["hybrid_search_results"] = hybrid_results

            # Failure analysis if mentioned
            if "fail" in query.lower() or "error" in query.lower():
                failure_analysis = self.failure_analyzer.analyze_failure_type(
                    "execution_failure", query, project_id
                )
                result["failure_analysis"] = failure_analysis

        return result
