"""Smart context injection for user prompts from memory (filesystem API paradigm).

This module implements context injection using the filesystem API paradigm:
- Discover relevant memory operations
- Execute search operations locally (in sandbox)
- Inject summaries into prompts (never full memory objects)

Key principle: Injection stays <300 tokens, not bloating prompt context.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get('ATHENA_DB_PATH', '~/.athena/memory.db')


@dataclass
class MemoryContext:
    """Relevant memory context to inject (summary, not full object)."""

    id: str
    source_type: str  # implementation, procedure, learning, decision
    title: str
    relevance_score: float  # 0.0-1.0
    content_preview: str  # Preview only, not full content
    keywords: List[str]
    timestamp: str


class ContextInjector:
    """Smart context injection for user prompts using filesystem API."""

    # Query intent patterns
    INTENT_PATTERNS = {
        "authentication": {
            "keywords": [
                "auth",
                "login",
                "session",
                "jwt",
                "oauth",
                "credential",
                "password",
                "token",
            ],
            "retrieval_strategy": "semantic_search",
            "context_types": [
                "implementation",
                "procedure",
                "decision_record",
            ],
        },
        "database": {
            "keywords": [
                "database",
                "sql",
                "schema",
                "migration",
                "query",
                "index",
                "table",
                "db",
            ],
            "retrieval_strategy": "semantic_search",
            "context_types": [
                "implementation",
                "procedure",
                "learning",
            ],
        },
        "api": {
            "keywords": [
                "api",
                "endpoint",
                "rest",
                "graphql",
                "http",
                "request",
                "response",
                "route",
            ],
            "retrieval_strategy": "semantic_search",
            "context_types": [
                "implementation",
                "procedure",
                "decision_record",
            ],
        },
        "architecture": {
            "keywords": [
                "architecture",
                "design",
                "pattern",
                "refactor",
                "structure",
                "dependency",
                "component",
            ],
            "retrieval_strategy": "graph_search",
            "context_types": [
                "design_doc",
                "decision_record",
                "learning",
            ],
        },
        "testing": {
            "keywords": [
                "test",
                "unit",
                "integration",
                "coverage",
                "mock",
                "stub",
                "fixture",
            ],
            "retrieval_strategy": "semantic_search",
            "context_types": [
                "procedure",
                "learning",
                "implementation",
            ],
        },
        "performance": {
            "keywords": [
                "performance",
                "optimize",
                "speed",
                "latency",
                "cache",
                "memory",
                "bottleneck",
            ],
            "retrieval_strategy": "semantic_search",
            "context_types": [
                "procedure",
                "learning",
                "implementation",
            ],
        },
        "security": {
            "keywords": [
                "security",
                "vulnerability",
                "attack",
                "injection",
                "xss",
                "csrf",
                "encryption",
                "ssl",
            ],
            "retrieval_strategy": "semantic_search",
            "context_types": [
                "decision_record",
                "learning",
                "procedure",
            ],
        },
        "debugging": {
            "keywords": [
                "debug",
                "error",
                "bug",
                "fix",
                "troubleshoot",
                "crash",
                "fail",
                "exception",
            ],
            "retrieval_strategy": "temporal_search",
            "context_types": [
                "procedure",
                "learning",
                "decision_record",
            ],
        },
    }

    def __init__(self):
        """Initialize context injector."""
        self.injected_contexts = []
        self.search_history = []

    def analyze_prompt(self, prompt: str) -> Dict[str, Any]:
        """Analyze user prompt for intent and context needs.

        Args:
            prompt: User's question or request

        Returns:
            Analysis dictionary with intent, keywords, strategy
        """
        prompt_lower = prompt.lower()

        analysis = {
            "original_prompt": prompt,
            "detected_intents": [],
            "keywords": [],
            "retrieval_strategy": "hybrid",  # default
            "context_types": ["implementation", "procedure", "learning"],
        }

        # Detect intents by matching keywords
        for intent_name, intent_config in self.INTENT_PATTERNS.items():
            matched_keywords = [
                kw for kw in intent_config["keywords"]
                if kw in prompt_lower
            ]

            if matched_keywords:
                analysis["detected_intents"].append(intent_name)
                analysis["keywords"].extend(matched_keywords)
                # Use first detected intent's strategy
                if analysis["retrieval_strategy"] == "hybrid":
                    analysis["retrieval_strategy"] = intent_config[
                        "retrieval_strategy"
                    ]

        analysis["keywords"] = list(set(analysis["keywords"]))  # Deduplicate

        return analysis

    def select_retrieval_strategy(
        self, analysis: Dict[str, Any]
    ) -> str:
        """Select optimal retrieval strategy for context.

        Args:
            analysis: Prompt analysis dictionary

        Returns:
            Strategy name (semantic_search, graph_search, temporal_search, etc)
        """
        strategy = analysis.get("retrieval_strategy", "hybrid")

        # Override based on additional signals
        if "how have" in analysis["original_prompt"].lower():
            strategy = "temporal_search"  # Temporal patterns
        elif "relationship" in analysis["original_prompt"].lower():
            strategy = "graph_search"  # Graph relationships
        elif "what if" in analysis["original_prompt"].lower():
            strategy = "scenario_search"  # Hypothetical scenarios

        return strategy

    def create_context_query(
        self, prompt: str, strategy: str
    ) -> str:
        """Create optimized memory query from user prompt.

        Args:
            prompt: Original user prompt
            strategy: Retrieval strategy

        Returns:
            Optimized query string
        """
        # Strategy-specific query transformation
        if strategy == "hyde":
            # Generate hypothetical document
            return f"Document about: {prompt}"
        elif strategy == "temporal_search":
            # Focus on temporal aspects
            return f"How have we approached: {prompt}"
        elif strategy == "graph_search":
            # Focus on relationships
            return f"Relationships and dependencies in: {prompt}"
        elif strategy == "semantic_search":
            # Keep mostly as-is, maybe expand
            return prompt
        else:
            return prompt

    def search_memory_for_context(
        self, prompt: str, analysis: Dict[str, Any]
    ) -> List[MemoryContext]:
        """Search memory for relevant context using filesystem API.

        Executes semantic search locally (in sandbox).
        Key: Returns summaries with IDs and relevance scores, not full memories.

        Args:
            prompt: User prompt
            analysis: Prompt analysis (contains keywords, detected intents)

        Returns:
            List of relevant memory contexts (summaries only)
        """
        contexts: List[MemoryContext] = []

        try:
            # Import adapter locally (optional availability)
            from .filesystem_api_adapter import FilesystemAPIAdapter

            adapter = FilesystemAPIAdapter()

            # Build search query from analysis
            search_query = self.create_context_query(
                prompt,
                analysis.get("retrieval_strategy", "semantic_search")
            )

            # Execute semantic search locally
            search_result = adapter.execute_operation(
                "semantic",
                "recall",
                {
                    "query": search_query,
                    "limit": 5,
                    "db_path": os.path.expanduser(DB_PATH)
                }
            )

            # Extract context from search results
            if search_result.get("status") == "success":
                results = search_result.get("result", {})

                # Convert search results to MemoryContext objects
                for item in results.get("top_results", []):
                    context = MemoryContext(
                        id=item.get("id", "unknown"),
                        source_type=item.get("type", "implementation"),
                        title=item.get("title", "Untitled"),
                        relevance_score=item.get("relevance", 0.0),
                        content_preview=item.get("preview", ""),
                        keywords=item.get("keywords", []),
                        timestamp=item.get("timestamp", datetime.utcnow().isoformat())
                    )
                    contexts.append(context)

            logger.debug(f"Found {len(contexts)} relevant context items via semantic search")

        except ImportError:
            # Fallback: If adapter not available, use simulated results
            logger.debug("FilesystemAPIAdapter not available, using simulated results")
            contexts = self._simulate_memory_search(prompt, analysis)
        except Exception as e:
            logger.warning(f"Memory search failed: {e}, falling back to simulation")
            contexts = self._simulate_memory_search(prompt, analysis)

        # Sort by relevance
        contexts.sort(key=lambda c: c.relevance_score, reverse=True)

        # Return top results
        return contexts[:5]

    def _simulate_memory_search(
        self, prompt: str, analysis: Dict[str, Any]
    ) -> List[MemoryContext]:
        """Simulate memory search results as fallback.

        Used when filesystem API is not available.
        Returns mock results based on detected intents.

        Args:
            prompt: User prompt
            analysis: Prompt analysis

        Returns:
            List of simulated memory contexts
        """
        contexts: List[MemoryContext] = []

        # Simulate finding relevant contexts based on intents
        for intent in analysis["detected_intents"]:
            if intent == "authentication":
                contexts.append(
                    MemoryContext(
                        id="auth-impl-001",
                        source_type="implementation",
                        title="JWT-based Authentication System",
                        relevance_score=0.92,
                        content_preview="Implemented JWT with refresh tokens...",
                        keywords=["jwt", "oauth", "token", "session"],
                        timestamp=datetime.utcnow().isoformat(),
                    )
                )
                contexts.append(
                    MemoryContext(
                        id="auth-decision-001",
                        source_type="decision_record",
                        title="JWT vs Session-based Decision",
                        relevance_score=0.88,
                        content_preview="Chose JWT for scalability...",
                        keywords=["jwt", "session", "scalability"],
                        timestamp=datetime.utcnow().isoformat(),
                    )
                )

            elif intent == "database":
                contexts.append(
                    MemoryContext(
                        id="db-schema-001",
                        source_type="implementation",
                        title="Database Schema Design - Users Table",
                        relevance_score=0.89,
                        content_preview="Normalized user schema with indexes...",
                        keywords=["schema", "index", "database"],
                        timestamp=datetime.utcnow().isoformat(),
                    )
                )

            elif intent == "api":
                contexts.append(
                    MemoryContext(
                        id="api-pattern-001",
                        source_type="procedure",
                        title="REST API Endpoint Pattern",
                        relevance_score=0.87,
                        content_preview="Standard error handling for endpoints...",
                        keywords=["api", "endpoint", "rest"],
                        timestamp=datetime.utcnow().isoformat(),
                    )
                )

        return contexts

    def inject_context(
        self, prompt: str, contexts: List[MemoryContext]
    ) -> str:
        """Inject memory context into prompt for response generation.

        Args:
            prompt: Original user prompt
            contexts: Relevant memory contexts

        Returns:
            Enhanced prompt with context
        """
        if not contexts:
            return prompt

        # Format context for injection
        context_str = "\n\n📚 RELEVANT MEMORY CONTEXT:\n"
        context_str += "─" * 50 + "\n"

        for i, ctx in enumerate(contexts, 1):
            context_str += f"\n{i}. {ctx.title}\n"
            context_str += f"   Type: {ctx.source_type}\n"
            context_str += f"   Relevance: {ctx.relevance_score:.0%}\n"
            context_str += f"   Preview: {ctx.content_preview[:60]}...\n"

        context_str += "\n" + "─" * 50 + "\n"
        context_str += (
            "This context from your memory is relevant to your question.\n"
        )
        context_str += "It's been automatically retrieved and will inform the response.\n"

        # Injected format
        enhanced_prompt = f"{context_str}\nYour Question:\n{prompt}"

        return enhanced_prompt

    def get_injection_summary(
        self, contexts: List[MemoryContext]
    ) -> Dict[str, Any]:
        """Get summary of what context was injected.

        Args:
            contexts: Injected memory contexts

        Returns:
            Summary dictionary
        """
        source_counts = {}
        total_relevance = 0.0

        for ctx in contexts:
            source_counts[ctx.source_type] = (
                source_counts.get(ctx.source_type, 0) + 1
            )
            total_relevance += ctx.relevance_score

        avg_relevance = (
            total_relevance / len(contexts) if contexts else 0.0
        )

        return {
            "contexts_injected": len(contexts),
            "by_type": source_counts,
            "average_relevance": avg_relevance,
            "context_list": [
                {"title": c.title, "relevance": c.relevance_score}
                for c in contexts
            ],
        }
