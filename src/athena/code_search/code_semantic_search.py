"""Semantic code search query engine with advanced parsing and optimization.

This module provides intelligent query parsing, expansion, and optimization for
semantic code search, enabling users to express complex search intents in natural language.
"""

import logging
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field as dataclass_field
from enum import Enum
from collections import OrderedDict

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of semantic search queries."""

    SIMPLE = "simple"  # Single keyword (e.g., "process_data")
    PHRASE = "phrase"  # Multi-word phrase (e.g., "data processing")
    INTENT = "intent"  # Intentional query (e.g., "find functions that validate input")
    FILTER = "filter"  # Filter-based (e.g., "classes in utils.py with high complexity")
    BOOLEAN = "boolean"  # Boolean operators (e.g., "authentication AND validation")
    PATTERN = "pattern"  # Pattern-based (e.g., "singleton pattern")
    COMPOSITE = "composite"  # Combination of above


class QueryStrategy(Enum):
    """Search strategies for different query types."""

    SEMANTIC = "semantic"  # Pure semantic similarity
    SYNTACTIC = "syntactic"  # Syntax/pattern matching
    GRAPH = "graph"  # Graph-based traversal
    TEMPORAL = "temporal"  # Recency-focused
    HYBRID = "hybrid"  # Combination of above


@dataclass
class QueryTerm:
    """Represents a single search term with metadata."""

    text: str
    weight: float = 1.0  # Importance weight (0-2)
    is_negation: bool = False  # True if preceded by NOT
    is_phrase: bool = False  # True if part of multi-word phrase
    target_field: Optional[str] = None  # Target field: name, type, file, etc.
    variants: List[str] = dataclass_field(default_factory=list)  # Synonym/related terms


@dataclass
class ParsedQuery:
    """Represents a parsed semantic search query."""

    original: str
    query_type: QueryType
    strategy: QueryStrategy
    primary_terms: List[QueryTerm]
    filters: Dict[str, Any] = dataclass_field(default_factory=dict)
    exclusions: List[str] = dataclass_field(default_factory=list)
    context: Dict[str, Any] = dataclass_field(default_factory=dict)
    confidence: float = 1.0


@dataclass
class SearchMetrics:
    """Metrics about a search execution."""

    query: str
    query_type: QueryType
    terms_used: int
    filters_applied: int
    cache_hit: bool
    execution_time_ms: float
    result_count: int
    top_score: float


class QueryParser:
    """Parses natural language queries into structured search forms."""

    # Common query patterns and intent markers
    INTENT_PATTERNS = {
        "find": ["search", "look for", "locate", "discover"],
        "filter": ["with", "having", "containing", "matching"],
        "combine": ["and", "or", "both", "either"],
        "exclude": ["not", "without", "excluding", "except"],
        "pattern": ["pattern", "implementing", "using", "following"],
    }

    def __init__(self):
        """Initialize parser."""
        self.term_cache = {}
        self.pattern_cache = {}

    def parse(self, query: str) -> ParsedQuery:
        """Parse natural language query into structured form."""
        query = query.strip()

        # Detect query type
        query_type = self._detect_query_type(query)

        # Extract terms and filters
        terms, filters, exclusions = self._extract_components(query)

        # Determine optimal strategy
        strategy = self._select_strategy(query_type, len(terms), bool(filters))

        # Build parsed query
        parsed = ParsedQuery(
            original=query,
            query_type=query_type,
            strategy=strategy,
            primary_terms=terms,
            filters=filters,
            exclusions=exclusions,
        )

        return parsed

    def _detect_query_type(self, query: str) -> QueryType:
        """Detect the type of query based on content."""
        query_lower = query.lower()

        # Check for boolean operators
        if any(op in query_lower for op in ["and", "or", "not"]):
            return QueryType.BOOLEAN

        # Check for intentional patterns
        if any(
            marker in query_lower for markers in self.INTENT_PATTERNS.values() for marker in markers
        ):
            return QueryType.INTENT

        # Check for filter patterns
        if any(keyword in query_lower for keyword in ["with", "having", "where", "in "]):
            return QueryType.FILTER

        # Check for design patterns
        if any(
            pattern in query_lower
            for pattern in [
                "pattern",
                "singleton",
                "factory",
                "observer",
                "decorator",
                "strategy",
                "adapter",
                "bridge",
                "composite",
                "facade",
            ]
        ):
            return QueryType.PATTERN

        # Check for phrase (multiple words with natural language flow)
        words = query.split()
        if len(words) > 2:
            return QueryType.PHRASE

        # Default to simple for single/double terms
        return QueryType.SIMPLE

    def _extract_components(self, query: str) -> Tuple[List[QueryTerm], Dict[str, Any], List[str]]:
        """Extract terms, filters, and exclusions from query."""
        terms = []
        filters = {}
        exclusions = []

        # Split on filter keywords
        parts = query.split(" with ")
        main_part = parts[0]
        filter_part = " with ".join(parts[1:]) if len(parts) > 1 else ""

        # Extract main terms
        words = main_part.split()
        skip_next = False
        for i, word in enumerate(words):
            if skip_next:
                skip_next = False
                continue

            word_lower = word.lower()

            # Handle NOT/negation
            if word_lower in ["not", "without"]:
                if i + 1 < len(words):
                    exclusions.append(words[i + 1])
                    skip_next = True
                continue

            # Skip connector words
            if word_lower in ["and", "or", "the", "a", "in"]:
                continue

            # Create term
            if word and word_lower not in ["find", "search", "look"]:
                term = QueryTerm(
                    text=word.lower(),
                    weight=1.0 if i == 0 else 0.8,  # First term weighted higher
                )
                terms.append(term)

        # Extract filters
        if filter_part:
            filters = self._parse_filters(filter_part)

        return terms, filters, exclusions

    def _parse_filters(self, filter_str: str) -> Dict[str, Any]:
        """Parse filter string into structured filters."""
        filters = {}

        # Simple pattern matching for common filters
        parts = filter_str.split(" and ")
        for part in parts:
            part = part.strip()

            # Type filter
            if part.startswith("type:"):
                filters["entity_type"] = part.replace("type:", "").strip()
            # File filter
            elif part.startswith("file:") or "in " in part:
                file_part = part.replace("in ", "").replace("file:", "").strip()
                filters["file_path"] = file_part
            # Complexity filter
            elif "complexity" in part:
                if "high" in part.lower():
                    filters["min_complexity"] = 4
                elif "low" in part.lower():
                    filters["max_complexity"] = 2
                else:
                    filters["min_complexity"] = 2
            # Pattern filter
            elif "pattern" in part:
                pattern = part.replace("pattern:", "").strip()
                filters["pattern"] = pattern

        return filters

    def _select_strategy(
        self, query_type: QueryType, term_count: int, has_filters: bool
    ) -> QueryStrategy:
        """Select optimal search strategy based on query characteristics."""
        if query_type == QueryType.PATTERN:
            return QueryStrategy.SYNTACTIC
        elif query_type == QueryType.FILTER and has_filters:
            return QueryStrategy.GRAPH
        elif query_type == QueryType.BOOLEAN:
            return QueryStrategy.HYBRID
        elif has_filters:
            return QueryStrategy.HYBRID
        else:
            return QueryStrategy.SEMANTIC


class QueryExpander:
    """Expands queries with related terms and variations."""

    # Common term relationships and synonyms
    SYNONYMS = {
        "process": ["handle", "execute", "run", "perform", "manage"],
        "validate": ["check", "verify", "test", "confirm"],
        "fetch": ["get", "retrieve", "pull", "download"],
        "send": ["transmit", "push", "upload", "notify"],
        "store": ["save", "persist", "write", "cache"],
        "create": ["make", "build", "generate", "initialize"],
        "delete": ["remove", "destroy", "clean", "purge"],
        "search": ["find", "locate", "discover", "query"],
    }

    # Related patterns for pattern queries
    PATTERN_RELATED = {
        "singleton": ["factory", "builder", "prototype"],
        "factory": ["builder", "prototype", "abstract_factory"],
        "observer": ["subscriber", "listener", "event_emitter"],
        "strategy": ["policy", "algorithm", "behavior"],
    }

    def __init__(self):
        """Initialize expander."""
        self.expansion_cache = {}

    def expand(self, query: ParsedQuery, max_variants: int = 3) -> ParsedQuery:
        """Expand query with related terms and variations."""
        expanded_terms = list(query.primary_terms)

        for term in query.primary_terms:
            variants = self._find_variants(term.text, query.query_type, max_variants)
            if variants:
                # Add variants to term
                term.variants.extend(variants)

                # Also add as separate lower-weight terms for some strategies
                if query.strategy in [QueryStrategy.HYBRID, QueryStrategy.SEMANTIC]:
                    for variant in variants:
                        expanded_terms.append(
                            QueryTerm(
                                text=variant,
                                weight=term.weight * 0.6,  # Variants have lower weight
                                variants=[],
                            )
                        )

        query.primary_terms = expanded_terms
        return query

    def _find_variants(self, term: str, query_type: QueryType, max_count: int) -> List[str]:
        """Find synonyms and related terms for a given term."""
        cache_key = f"{term}:{query_type.value}"
        if cache_key in self.expansion_cache:
            return self.expansion_cache[cache_key]

        variants = []

        # Get synonyms
        if term in self.SYNONYMS:
            variants.extend(self.SYNONYMS[term][:max_count])

        # For pattern queries, get pattern relationships
        if query_type == QueryType.PATTERN and term in self.PATTERN_RELATED:
            variants.extend(self.PATTERN_RELATED[term][:max_count])

        # Cache result
        self.expansion_cache[cache_key] = variants
        return variants


class QueryOptimizer:
    """Optimizes queries based on patterns and cache effectiveness."""

    def __init__(self, cache_size: int = 1000):
        """Initialize optimizer."""
        self.query_history: OrderedDict[str, SearchMetrics] = OrderedDict()
        self.max_history = cache_size
        self.optimization_rules = self._init_optimization_rules()

    def optimize(self, query: ParsedQuery) -> ParsedQuery:
        """Optimize query for better performance and relevance."""
        # Remove stop words that don't add value
        query.primary_terms = [
            t
            for t in query.primary_terms
            if t.text not in ["code", "function", "class", "file", "module"]
        ]

        # Reorder terms by estimated importance
        query.primary_terms.sort(key=lambda t: t.weight, reverse=True)

        # Apply optimization rules
        for rule in self.optimization_rules:
            rule(query)

        return query

    def _init_optimization_rules(self) -> List:
        """Initialize optimization rule functions."""
        rules = [
            self._collapse_similar_terms,
            self._adjust_term_weights,
            self._simplify_filters,
        ]
        return rules

    def _collapse_similar_terms(self, query: ParsedQuery) -> None:
        """Merge terms that are variants of each other."""
        unique_terms = {}
        for term in query.primary_terms:
            # Use base form as key
            key = term.text.lower()
            if key not in unique_terms:
                unique_terms[key] = term
            else:
                # Merge weights
                unique_terms[key].weight += term.weight * 0.5

        query.primary_terms = list(unique_terms.values())

    def _adjust_term_weights(self, query: ParsedQuery) -> None:
        """Adjust term weights based on heuristics."""
        if not query.primary_terms:
            return

        total_weight = sum(t.weight for t in query.primary_terms)
        for term in query.primary_terms:
            # Normalize weights
            term.weight = term.weight / total_weight if total_weight > 0 else 1.0
            # Boost specialized terms
            if any(c.isupper() for c in term.text):  # CamelCase terms
                term.weight *= 1.2

    def _simplify_filters(self, query: ParsedQuery) -> None:
        """Remove redundant filters."""
        # Remove complexity filter if we have specific pattern filters
        if "pattern" in query.filters:
            query.filters.pop("min_complexity", None)
            query.filters.pop("max_complexity", None)

    def record_query(self, query: str, metrics: SearchMetrics) -> None:
        """Record query execution for optimization."""
        self.query_history[query] = metrics

        # Maintain size limit
        if len(self.query_history) > self.max_history:
            self.query_history.popitem(last=False)

    def get_common_patterns(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get most frequently executed queries."""
        query_counts: Dict[str, int] = {}
        for query, metrics in self.query_history.items():
            # Group similar queries
            base_query = " ".join(query.split()[:2])  # First two terms
            query_counts[base_query] = query_counts.get(base_query, 0) + 1

        sorted_queries = sorted(query_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_queries[:limit]


class SearchCache:
    """LRU cache for search results."""

    def __init__(self, max_size: int = 500):
        """Initialize cache."""
        self.cache: OrderedDict[str, Any] = OrderedDict()
        self.max_size = max_size
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get cached result."""
        if key in self.cache:
            # Move to end (LRU)
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None

    def set(self, key: str, value: Any) -> None:
        """Cache result."""
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value

        # Evict oldest if over size
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

    def clear(self) -> None:
        """Clear cache."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0.0
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
        }


class SemanticSearchEngine:
    """Main semantic code search engine."""

    def __init__(self, rag_pipeline=None):
        """Initialize search engine."""
        self.rag_pipeline = rag_pipeline
        self.parser = QueryParser()
        self.expander = QueryExpander()
        self.optimizer = QueryOptimizer()
        self.cache = SearchCache()
        self.search_history: List[SearchMetrics] = []

    def search(self, query_text: str, top_k: int = 10) -> List[Any]:
        """Execute semantic search on query."""
        import time

        start_time = time.time()

        # Check cache first
        cache_key = f"{query_text}:{top_k}"
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Parse query
        parsed = self.parser.parse(query_text)

        # Expand query
        parsed = self.expander.expand(parsed)

        # Optimize
        parsed = self.optimizer.optimize(parsed)

        # Execute search (delegate to RAG pipeline if available)
        results = self._execute_search(parsed, top_k)

        # Cache results
        self.cache.set(cache_key, results)

        # Record metrics
        execution_time = (time.time() - start_time) * 1000  # Convert to ms
        metrics = SearchMetrics(
            query=query_text,
            query_type=parsed.query_type,
            terms_used=len(parsed.primary_terms),
            filters_applied=len(parsed.filters),
            cache_hit=False,
            execution_time_ms=execution_time,
            result_count=len(results),
            top_score=(
                results[0].combined_score
                if results and hasattr(results[0], "combined_score")
                else 0.0
            ),
        )
        self.search_history.append(metrics)
        self.optimizer.record_query(query_text, metrics)

        return results

    def _execute_search(self, parsed: ParsedQuery, top_k: int) -> List[Any]:
        """Execute search using parsed query."""
        if not self.rag_pipeline:
            return []

        # Build search query for RAG pipeline
        search_text = " ".join(t.text for t in parsed.primary_terms[:5])

        # Execute appropriate search based on strategy
        if parsed.strategy == QueryStrategy.SEMANTIC:
            from .code_rag_integration import SearchQuery, SearchStrategy

            query = SearchQuery(
                query_text=search_text,
                strategy=SearchStrategy.SEMANTIC,
                top_k=top_k,
                filters=parsed.filters,
            )
            return self.rag_pipeline.execute_query(search_text)

        elif parsed.strategy == QueryStrategy.SYNTACTIC:
            return self.rag_pipeline.search_by_pattern(search_text, top_k=top_k)

        elif parsed.strategy == QueryStrategy.HYBRID:
            from .code_rag_integration import SearchQuery

            query = SearchQuery(
                query_text=search_text,
                strategy="hybrid",
                top_k=top_k,
                filters=parsed.filters,
            )
            return self.rag_pipeline.execute_advanced_query(search_text, **parsed.filters)

        else:
            # Fallback to basic search
            return self.rag_pipeline.execute_query(search_text)

    def get_analytics(self) -> Dict[str, Any]:
        """Get search analytics."""
        if not self.search_history:
            return {
                "total_searches": 0,
                "average_execution_time_ms": 0.0,
                "query_types": {},
                "cache_stats": self.cache.get_stats(),
            }

        query_types = {}
        total_time = 0.0
        for metric in self.search_history:
            query_types[metric.query_type.value] = query_types.get(metric.query_type.value, 0) + 1
            total_time += metric.execution_time_ms

        return {
            "total_searches": len(self.search_history),
            "average_execution_time_ms": total_time / len(self.search_history),
            "query_types": query_types,
            "cache_stats": self.cache.get_stats(),
            "common_patterns": self.optimizer.get_common_patterns(5),
        }

    def clear_cache(self) -> None:
        """Clear search cache."""
        self.cache.clear()

    def generate_search_report(self) -> str:
        """Generate comprehensive search analytics report."""
        analytics = self.get_analytics()

        report = "SEMANTIC SEARCH REPORT\n"
        report += "=" * 60 + "\n\n"

        report += f"Total Searches: {analytics['total_searches']}\n"
        report += f"Average Execution Time: {analytics['average_execution_time_ms']:.2f}ms\n\n"

        # Query types
        if analytics["query_types"]:
            report += "Query Types Used:\n"
            for qtype, count in analytics["query_types"].items():
                report += f"  {qtype}: {count}\n"
            report += "\n"

        # Cache stats
        cache_stats = analytics["cache_stats"]
        report += "Cache Performance:\n"
        report += f"  Hit Rate: {cache_stats['hit_rate']:.1%}\n"
        report += f"  Size: {cache_stats['size']}/{cache_stats['max_size']}\n\n"

        # Common patterns
        if analytics["common_patterns"]:
            report += "Most Common Query Patterns:\n"
            for pattern, count in analytics["common_patterns"][:5]:
                report += f"  '{pattern}': {count} searches\n"

        return report
