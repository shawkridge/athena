"""Intelligent query routing for optimal RAG strategy selection.

This module provides intelligent query type detection and routing to select
the optimal RAG strategy based on query characteristics.

Key Features:
1. **Query Type Detection**: Automatically classify queries
   - Factual: "What is X?"
   - Temporal: "When did X happen?"
   - Relational: "How is X related to Y?"
   - Exploratory: "Tell me about X"
   - Comparative: "Compare X and Y"
   - Procedural: "How do I do X?"
   - Reasoning: "Why does X happen?"

2. **Multi-Factor Query Analysis**: Analyze multiple aspects
   - Semantic complexity
   - Temporal indicators
   - Relationship indicators
   - Knowledge domain
   - Question structure

3. **Strategy Selection**: Route to optimal RAG strategy
   - Basic: Simple factual queries
   - HyDE: Ambiguous or complex queries
   - Reranking: High-precision requirements
   - Reflective: Multi-hop reasoning
   - Planning: Task/goal-oriented queries

4. **Confidence Scoring**: Assess confidence in routing decision
   - High: Clear query type, optimal strategy obvious
   - Medium: Mixed signals, need multiple strategies
   - Low: Ambiguous query, try multiple approaches

5. **Learning & Adaptation**: Track routing effectiveness
   - Cache successful routings
   - Learn from feedback
   - Improve over time
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set
from collections import Counter

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Detected query types."""

    FACTUAL = "factual"           # What/Where/Who questions
    TEMPORAL = "temporal"         # When/How long questions
    RELATIONAL = "relational"     # How/Why relationship questions
    EXPLORATORY = "exploratory"   # Tell me about/Explain
    COMPARATIVE = "comparative"   # Compare/Contrast
    PROCEDURAL = "procedural"     # How to/Instructions
    REASONING = "reasoning"       # Why/Causal questions
    UNKNOWN = "unknown"           # Unclear type


class RAGStrategy(Enum):
    """RAG strategies to apply."""

    BASIC = "basic"               # Simple vector search
    HYDE = "hyde"                 # Hypothetical documents
    RERANKING = "reranking"       # LLM-based reranking
    REFLECTIVE = "reflective"     # Iterative refinement
    PLANNING = "planning"         # Planning-aware RAG
    HYBRID = "hybrid"             # Combine multiple strategies
    AUTO = "auto"                 # Automatic selection


class ComplexityLevel(Enum):
    """Query complexity assessment."""

    SIMPLE = "simple"             # Single-hop, direct answer
    MODERATE = "moderate"         # Some context needed
    COMPLEX = "complex"           # Multi-hop, reasoning required
    VERY_COMPLEX = "very_complex" # Deep reasoning, synthesis


@dataclass
class QueryAnalysis:
    """Analysis of query characteristics."""

    query_type: QueryType
    primary_strategy: RAGStrategy
    secondary_strategies: List[RAGStrategy]
    complexity: ComplexityLevel
    confidence_score: float        # 0-1, higher = more confident
    reasoning: str                 # Explanation of routing decision
    indicators: Dict[str, float]   # Component scores
    requires_planning: bool = False
    requires_temporal: bool = False
    requires_reasoning: bool = False
    estimated_hops: int = 1        # Estimated reasoning hops


class QueryTypeDetector:
    """Detects query type from text."""

    # Query patterns for each type
    FACTUAL_PATTERNS = [
        r'\bwhat\s+is\b',
        r'\bwhere\s+is\b',
        r'\bwho\s+is\b',
        r'\bdefine\b',
        r'\bwhat\s+does\b',
        r'\bhow\s+much\b',
        r'\bhow\s+many\b',
    ]

    TEMPORAL_PATTERNS = [
        r'\bwhen\b',
        r'\bhow\s+long\b',
        r'\btimeline\b',
        r'\bhistory\s+of\b',
        r'\byear\b',
        r'\bdate\b',
        r'\brecent\b',
        r'\bpast\b',
        r'\bfuture\b',
    ]

    RELATIONAL_PATTERNS = [
        r'\bhow\s+is.*related\b',
        r'\bconnect\b',
        r'\brelationship\b',
        r'\bimpact\b',
        r'\binfluence\b',
        r'\bcause\b',
        r'\beffect\b',
    ]

    EXPLORATORY_PATTERNS = [
        r'\btell\s+me\s+about\b',
        r'\bexplain\b',
        r'\bdescribe\b',
        r'\bsummarize\b',
        r'\boverview\b',
        r'\bbackground\b',
        r'\bcontext\b',
    ]

    COMPARATIVE_PATTERNS = [
        r'\bcompare\b',
        r'\bcontrast\b',
        r'\bdifference\s+between\b',
        r'\bsimilarities\b',
        r'\bvs\.|versus\b',
        r'\bbetter\s+than\b',
        r'\bworse\s+than\b',
    ]

    PROCEDURAL_PATTERNS = [
        r'\bhow\s+to\b',
        r'\bsteps?\s+to\b',
        r'\binstructions?\b',
        r'\bprocess\b',
        r'\bmethod\b',
        r'\bprocedure\b',
    ]

    REASONING_PATTERNS = [
        r'\bwhy\b',
        r'\breason\b',
        r'\bcause\b',
        r'\bexplain\s+why\b',
        r'\binterpret\b',
        r'\banalyze\b',
    ]

    def __init__(self):
        """Initialize detector."""
        self._compile_patterns()
        self._cache: Dict[str, QueryType] = {}

    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficiency."""
        self.patterns = {
            QueryType.FACTUAL: [re.compile(p, re.IGNORECASE) for p in self.FACTUAL_PATTERNS],
            QueryType.TEMPORAL: [re.compile(p, re.IGNORECASE) for p in self.TEMPORAL_PATTERNS],
            QueryType.RELATIONAL: [re.compile(p, re.IGNORECASE) for p in self.RELATIONAL_PATTERNS],
            QueryType.EXPLORATORY: [re.compile(p, re.IGNORECASE) for p in self.EXPLORATORY_PATTERNS],
            QueryType.COMPARATIVE: [re.compile(p, re.IGNORECASE) for p in self.COMPARATIVE_PATTERNS],
            QueryType.PROCEDURAL: [re.compile(p, re.IGNORECASE) for p in self.PROCEDURAL_PATTERNS],
            QueryType.REASONING: [re.compile(p, re.IGNORECASE) for p in self.REASONING_PATTERNS],
        }

    def detect(self, query: str) -> QueryType:
        """Detect query type.

        Args:
            query: Query text

        Returns:
            Detected QueryType
        """
        if not query:
            return QueryType.UNKNOWN

        # Check cache
        if query in self._cache:
            return self._cache[query]

        # Find matching patterns
        matches = {}
        for query_type, patterns in self.patterns.items():
            match_count = sum(1 for p in patterns if p.search(query))
            if match_count > 0:
                matches[query_type] = match_count

        # Determine type based on matches
        if not matches:
            query_type = QueryType.UNKNOWN
        else:
            # Return most common match type
            query_type = max(matches, key=matches.get)

        # Cache result
        self._cache[query] = query_type
        return query_type

    def clear_cache(self) -> None:
        """Clear detection cache."""
        self._cache.clear()


class ComplexityAnalyzer:
    """Analyzes query complexity."""

    def __init__(self):
        """Initialize analyzer."""
        self._cache: Dict[str, ComplexityLevel] = {}

    def analyze(self, query: str) -> ComplexityLevel:
        """Analyze query complexity.

        Args:
            query: Query text

        Returns:
            ComplexityLevel
        """
        if not query:
            return ComplexityLevel.SIMPLE

        # Check cache
        if query in self._cache:
            return self._cache[query]

        # Calculate complexity factors
        length = len(query.split())
        conjunctions = len(re.findall(r'\band\b|\bor\b|\bbut\b', query, re.IGNORECASE))
        subordinations = len(re.findall(r'\bif\b|\bbecause\b|\bwhile\b|\balthough\b', query, re.IGNORECASE))
        multi_questions = query.count('?')

        # Score components
        length_score = min(1.0, length / 20)  # Longer queries tend to be complex
        conjunction_score = min(1.0, conjunctions / 3)
        subordination_score = min(1.0, subordinations / 2)
        question_score = min(1.0, multi_questions / 2)

        # Weighted combination
        complexity_score = (
            0.3 * length_score +
            0.2 * conjunction_score +
            0.25 * subordination_score +
            0.25 * question_score
        )

        # Classify
        if complexity_score < 0.3:
            level = ComplexityLevel.SIMPLE
        elif complexity_score < 0.6:
            level = ComplexityLevel.MODERATE
        elif complexity_score < 0.8:
            level = ComplexityLevel.COMPLEX
        else:
            level = ComplexityLevel.VERY_COMPLEX

        # Cache result
        self._cache[query] = level
        return level

    def clear_cache(self) -> None:
        """Clear analysis cache."""
        self._cache.clear()


class StrategySelector:
    """Selects optimal RAG strategy based on query analysis."""

    def __init__(self):
        """Initialize selector."""
        # Strategy mappings for each query type
        self.type_to_strategies = {
            QueryType.FACTUAL: [
                RAGStrategy.BASIC,
                RAGStrategy.RERANKING,
                RAGStrategy.HYDE,
            ],
            QueryType.TEMPORAL: [
                RAGStrategy.PLANNING,
                RAGStrategy.RERANKING,
                RAGStrategy.HYBRID,
            ],
            QueryType.RELATIONAL: [
                RAGStrategy.REFLECTIVE,
                RAGStrategy.PLANNING,
                RAGStrategy.RERANKING,
            ],
            QueryType.EXPLORATORY: [
                RAGStrategy.HYDE,
                RAGStrategy.REFLECTIVE,
                RAGStrategy.RERANKING,
            ],
            QueryType.COMPARATIVE: [
                RAGStrategy.RERANKING,
                RAGStrategy.HYBRID,
                RAGStrategy.PLANNING,
            ],
            QueryType.PROCEDURAL: [
                RAGStrategy.PLANNING,
                RAGStrategy.RERANKING,
                RAGStrategy.BASIC,
            ],
            QueryType.REASONING: [
                RAGStrategy.REFLECTIVE,
                RAGStrategy.PLANNING,
                RAGStrategy.HYBRID,
            ],
            QueryType.UNKNOWN: [
                RAGStrategy.AUTO,
                RAGStrategy.HYBRID,
                RAGStrategy.RERANKING,
            ],
        }

        # Strategy adjustments for complexity
        self.complexity_adjustments = {
            ComplexityLevel.SIMPLE: [RAGStrategy.BASIC, RAGStrategy.RERANKING],
            ComplexityLevel.MODERATE: [RAGStrategy.RERANKING, RAGStrategy.HYDE],
            ComplexityLevel.COMPLEX: [RAGStrategy.REFLECTIVE, RAGStrategy.PLANNING],
            ComplexityLevel.VERY_COMPLEX: [RAGStrategy.REFLECTIVE, RAGStrategy.HYBRID],
        }

    def select(
        self,
        query_type: QueryType,
        complexity: ComplexityLevel,
        confidence_score: float
    ) -> Tuple[RAGStrategy, List[RAGStrategy]]:
        """Select primary and secondary strategies.

        Args:
            query_type: Detected query type
            complexity: Analyzed complexity level
            confidence_score: Confidence in type detection (0-1)

        Returns:
            Tuple of (primary_strategy, secondary_strategies)
        """
        # Get base strategies for query type
        base_strategies = self.type_to_strategies.get(query_type, [RAGStrategy.AUTO])

        # Adjust based on complexity
        complexity_strategies = self.complexity_adjustments.get(complexity, [])

        # Combine and prioritize
        if confidence_score < 0.5:
            # Low confidence: be more exploratory
            strategies = [RAGStrategy.AUTO, RAGStrategy.HYBRID] + base_strategies
        elif complexity == ComplexityLevel.VERY_COMPLEX:
            # High complexity: use advanced strategies
            strategies = complexity_strategies + base_strategies
        else:
            # Normal case: use type-based strategies
            strategies = base_strategies

        # Remove duplicates while preserving order
        seen = set()
        unique_strategies = []
        for s in strategies:
            if s not in seen:
                unique_strategies.append(s)
                seen.add(s)

        if not unique_strategies:
            unique_strategies = [RAGStrategy.AUTO]

        primary = unique_strategies[0]
        secondary = unique_strategies[1:]

        return primary, secondary


class QueryRouter:
    """Routes queries to optimal RAG strategy."""

    def __init__(self):
        """Initialize router."""
        self.type_detector = QueryTypeDetector()
        self.complexity_analyzer = ComplexityAnalyzer()
        self.strategy_selector = StrategySelector()
        self._routing_cache: Dict[str, QueryAnalysis] = {}

    def route(self, query: str, use_cache: bool = True) -> QueryAnalysis:
        """Route query to optimal strategy.

        Args:
            query: Query text
            use_cache: Whether to use cached routing

        Returns:
            QueryAnalysis with routing decision
        """
        if not query:
            return self._create_default_analysis(QueryType.UNKNOWN)

        # Check cache
        if use_cache and query in self._routing_cache:
            return self._routing_cache[query]

        # Detect query type
        query_type = self.type_detector.detect(query)

        # Analyze complexity
        complexity = self.complexity_analyzer.analyze(query)

        # Calculate confidence score
        confidence = self._calculate_confidence(query, query_type, complexity)

        # Detect special requirements
        requires_planning = self._detect_planning_requirement(query)
        requires_temporal = self._detect_temporal_requirement(query)
        requires_reasoning = self._detect_reasoning_requirement(query)
        estimated_hops = self._estimate_reasoning_hops(query)

        # Select strategy
        primary_strategy, secondary_strategies = self.strategy_selector.select(
            query_type, complexity, confidence
        )

        # Calculate component indicators
        indicators = {
            "query_type_score": self._score_query_type(query_type),
            "complexity_score": self._score_complexity(complexity),
            "planning_indicator": 1.0 if requires_planning else 0.0,
            "temporal_indicator": 1.0 if requires_temporal else 0.0,
            "reasoning_indicator": 1.0 if requires_reasoning else 0.0,
        }

        # Create analysis
        analysis = QueryAnalysis(
            query_type=query_type,
            primary_strategy=primary_strategy,
            secondary_strategies=secondary_strategies,
            complexity=complexity,
            confidence_score=confidence,
            reasoning=self._generate_reasoning(query_type, complexity, confidence),
            indicators=indicators,
            requires_planning=requires_planning,
            requires_temporal=requires_temporal,
            requires_reasoning=requires_reasoning,
            estimated_hops=estimated_hops,
        )

        # Cache result
        if use_cache:
            self._routing_cache[query] = analysis

        return analysis

    def _calculate_confidence(
        self, query: str, query_type: QueryType, complexity: ComplexityLevel
    ) -> float:
        """Calculate confidence in routing decision."""
        base_confidence = 0.7

        # Increase confidence for clear query types
        if query_type != QueryType.UNKNOWN:
            base_confidence += 0.15
        else:
            base_confidence -= 0.2

        # Adjust for complexity clarity
        if complexity in (ComplexityLevel.SIMPLE, ComplexityLevel.VERY_COMPLEX):
            base_confidence += 0.1
        else:
            base_confidence -= 0.05

        # Adjust for query length clarity
        words = query.split()
        if 5 <= len(words) <= 30:
            base_confidence += 0.05
        elif len(words) < 3 or len(words) > 50:
            base_confidence -= 0.15

        return max(0.0, min(1.0, base_confidence))

    def _detect_planning_requirement(self, query: str) -> bool:
        """Detect if query requires planning-aware retrieval."""
        planning_keywords = [
            'goal', 'task', 'objective', 'plan', 'strategy', 'steps',
            'process', 'workflow', 'sequence', 'order', 'procedure'
        ]
        query_lower = query.lower()
        return any(kw in query_lower for kw in planning_keywords)

    def _detect_temporal_requirement(self, query: str) -> bool:
        """Detect if query has temporal aspects."""
        temporal_keywords = [
            'when', 'time', 'date', 'year', 'month', 'week', 'day',
            'before', 'after', 'during', 'since', 'until', 'recent',
            'history', 'timeline', 'evolution', 'progress'
        ]
        query_lower = query.lower()
        return any(kw in query_lower for kw in temporal_keywords)

    def _detect_reasoning_requirement(self, query: str) -> bool:
        """Detect if query requires multi-hop reasoning."""
        reasoning_keywords = [
            'why', 'because', 'reason', 'explain', 'cause', 'effect',
            'impact', 'consequence', 'result', 'implication', 'analyze'
        ]
        query_lower = query.lower()
        return any(kw in query_lower for kw in reasoning_keywords)

    def _estimate_reasoning_hops(self, query: str) -> int:
        """Estimate number of reasoning hops needed."""
        # Count compound structures
        conjunctions = len(re.findall(r'\band\b|\bor\b|\bbut\b', query, re.IGNORECASE))
        subordinations = len(re.findall(r'\bif\b|\bbecause\b|\bwhile\b', query, re.IGNORECASE))

        base_hops = 1
        hops = base_hops + conjunctions + subordinations

        return min(hops, 5)  # Cap at 5 hops

    def _score_query_type(self, query_type: QueryType) -> float:
        """Score clarity of query type."""
        if query_type == QueryType.UNKNOWN:
            return 0.3
        else:
            return 0.8  # Most specific types have good clarity

    def _score_complexity(self, complexity: ComplexityLevel) -> float:
        """Score complexity level."""
        scores = {
            ComplexityLevel.SIMPLE: 0.2,
            ComplexityLevel.MODERATE: 0.5,
            ComplexityLevel.COMPLEX: 0.75,
            ComplexityLevel.VERY_COMPLEX: 0.95,
        }
        return scores.get(complexity, 0.5)

    def _generate_reasoning(
        self, query_type: QueryType, complexity: ComplexityLevel, confidence: float
    ) -> str:
        """Generate human-readable reasoning for routing decision."""
        parts = []

        # Query type reasoning
        if query_type != QueryType.UNKNOWN:
            parts.append(f"Query is {query_type.value}")
        else:
            parts.append("Query type is ambiguous")

        # Complexity reasoning
        if complexity == ComplexityLevel.SIMPLE:
            parts.append("and relatively straightforward")
        elif complexity == ComplexityLevel.COMPLEX:
            parts.append("and moderately complex")
        elif complexity == ComplexityLevel.VERY_COMPLEX:
            parts.append("and highly complex")

        # Confidence reasoning
        if confidence > 0.8:
            parts.append("with high confidence")
        elif confidence > 0.5:
            parts.append("with moderate confidence")
        else:
            parts.append("with low confidence")

        return " ".join(parts)

    def _create_default_analysis(self, query_type: QueryType) -> QueryAnalysis:
        """Create default analysis."""
        return QueryAnalysis(
            query_type=query_type,
            primary_strategy=RAGStrategy.AUTO,
            secondary_strategies=[RAGStrategy.RERANKING],
            complexity=ComplexityLevel.SIMPLE,
            confidence_score=0.3,
            reasoning="Unable to analyze query",
            indicators={},
            requires_planning=False,
            requires_temporal=False,
            requires_reasoning=False,
            estimated_hops=1,
        )

    def clear_cache(self) -> None:
        """Clear routing cache."""
        self._routing_cache.clear()
        self.type_detector.clear_cache()
        self.complexity_analyzer.clear_cache()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "routing_cache": len(self._routing_cache),
            "type_detection_cache": len(self.type_detector._cache),
            "complexity_cache": len(self.complexity_analyzer._cache),
        }
