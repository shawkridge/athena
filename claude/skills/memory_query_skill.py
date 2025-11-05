"""
Memory Query Skill - Auto-triggered semantic memory search

Auto-triggers on questions like:
- "what do I know about X?"
- "do I remember X?"
- "show me what we know about X"
- "query memory for X"

Uses advanced RAG:
- HyDE (Hypothetical Document Embeddings)
- Query transformation
- LLM reranking
- Reflective retrieval
"""

import asyncio
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class MemoryResult:
    """Single memory query result"""
    content: str
    source_layer: str  # semantic, episodic, procedural, graph
    relevance: float
    confidence: float
    metadata: Dict[str, Any]


class MemoryQuerySkill:
    """Auto-triggered memory query skill"""

    def __init__(self):
        self.trigger_patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for memory queries"""
        return {
            "what_do_know": re.compile(
                r'what\s+do\s+(?:i|we|you)\s+know\s+about\s+(.+?)\??$',
                re.IGNORECASE | re.MULTILINE
            ),
            "do_remember": re.compile(
                r'do\s+(?:i|we|you)\s+remember\s+(.+?)\??$',
                re.IGNORECASE | re.MULTILINE
            ),
            "show_what_know": re.compile(
                r'show\s+(?:me\s+)?(?:what\s+)?(?:i|we|you)\s+know\s+about\s+(.+)',
                re.IGNORECASE
            ),
            "query_memory": re.compile(
                r'(?:query|search)\s+(?:memory\s+)?(?:for\s+)?(.+)',
                re.IGNORECASE
            ),
            "memory_query_slash": re.compile(
                r'/memory-query\s+(.+)',
                re.IGNORECASE
            ),
        }

    def detect_memory_query_intent(self, user_input: str) -> Optional[Dict[str, Any]]:
        """Detect if user is querying memory

        Returns: Dict with query topic and pattern, or None
        """
        for pattern_name, pattern in self.trigger_patterns.items():
            match = pattern.search(user_input)
            if match:
                query = match.group(1).strip()
                return {
                    "query": query,
                    "pattern": pattern_name,
                    "confidence": 0.9,
                }

        return None

    def should_trigger(self, user_input: str) -> bool:
        """Check if skill should auto-trigger"""
        if not user_input or len(user_input) < 10:
            return False

        intent = self.detect_memory_query_intent(user_input)
        return intent is not None

    async def execute_raag_search(
        self,
        query: str,
        strategy: str = "auto",
        include_hyde: bool = True,
        include_reranking: bool = True,
    ) -> List[MemoryResult]:
        """Execute RAG search with multiple strategies

        Args:
            query: Search query
            strategy: "hyde" | "transform" | "reflective" | "auto" (default)
            include_hyde: Enable HyDE expansion
            include_reranking: Enable LLM reranking

        Returns:
            Ranked memory results
        """
        results = []

        # 1. SEMANTIC SEARCH (always do this)
        semantic_results = await self._semantic_search(query)
        results.extend(semantic_results)

        # 2. HYDE EXPANSION (for short/ambiguous queries)
        if include_hyde and len(query.split()) < 5:
            hyde_results = await self._hyde_expansion_search(query)
            results.extend(hyde_results)

        # 3. QUERY TRANSFORMATION (for complex queries with references)
        if "it" in query.lower() or "that" in query.lower():
            transform_results = await self._query_transformation_search(query)
            results.extend(transform_results)

        # 4. REFLECTIVE RETRIEVAL (for nuanced understanding)
        if include_reranking:
            reflective_results = await self._reflective_retrieval(query)
            results.extend(reflective_results)

        # 5. DEDUPLICATE & RERANK
        dedup_results = self._deduplicate_results(results)
        ranked_results = await self._rerank_with_llm(dedup_results) if include_reranking else dedup_results

        # 6. SORT BY RELEVANCE
        ranked_results.sort(key=lambda x: x.relevance, reverse=True)

        return ranked_results[:10]  # Return top 10

    async def _semantic_search(self, query: str) -> List[MemoryResult]:
        """Semantic search across all memory layers"""
        # In real implementation, would query memory system
        # For now, return mock results
        return [
            MemoryResult(
                content="Example finding from semantic memory",
                source_layer="semantic",
                relevance=0.95,
                confidence=0.9,
                metadata={"memory_id": 1, "tags": ["example"]}
            )
        ]

    async def _hyde_expansion_search(self, query: str) -> List[MemoryResult]:
        """HyDE: Search for hypothetical documents similar to query"""
        # Expands short queries by generating hypothetical documents
        return []

    async def _query_transformation_search(self, query: str) -> List[MemoryResult]:
        """Transform query to handle references (it, that, etc.)"""
        return []

    async def _reflective_retrieval(self, query: str) -> List[MemoryResult]:
        """Reflective retrieval: iteratively refine search based on results"""
        return []

    def _deduplicate_results(self, results: List[MemoryResult]) -> List[MemoryResult]:
        """Remove duplicate results"""
        seen = set()
        dedup = []

        for result in sorted(results, key=lambda x: x.relevance, reverse=True):
            if result.content not in seen:
                dedup.append(result)
                seen.add(result.content)

        return dedup

    async def _rerank_with_llm(self, results: List[MemoryResult]) -> List[MemoryResult]:
        """Rerank results using LLM for better relevance"""
        # In real implementation, would use Claude to rerank
        return results

    async def handle_user_input(self, user_input: str) -> Optional[Dict[str, Any]]:
        """Main entry point for memory query

        Args:
            user_input: User's input

        Returns:
            Query results or None
        """
        # Detect intent
        intent = self.detect_memory_query_intent(user_input)
        if not intent:
            return None

        # Execute search
        results = await self.execute_raag_search(intent["query"])

        # Format results
        return {
            "query": intent["query"],
            "results_count": len(results),
            "results": [
                {
                    "content": r.content,
                    "source_layer": r.source_layer,
                    "relevance": r.relevance,
                    "confidence": r.confidence,
                    "metadata": r.metadata,
                }
                for r in results
            ],
            "raag_strategy": "auto",
        }


# ============================================================================
# Global Skill Instance
# ============================================================================

_memory_query_skill_instance: Optional[MemoryQuerySkill] = None


def get_memory_query_skill() -> MemoryQuerySkill:
    """Get or create global skill instance"""
    global _memory_query_skill_instance
    if _memory_query_skill_instance is None:
        _memory_query_skill_instance = MemoryQuerySkill()
    return _memory_query_skill_instance


# ============================================================================
# Hook for Auto-Triggering
# ============================================================================

async def auto_trigger_memory_query(user_input: str) -> Optional[Dict[str, Any]]:
    """
    Called by UserPromptSubmit hook when user input detected.

    Returns: Query results if triggered, None otherwise
    """
    skill = get_memory_query_skill()

    if not skill.should_trigger(user_input):
        return None

    result = await skill.handle_user_input(user_input)
    return result


# ============================================================================
# Example Usage
# ============================================================================

async def example_usage():
    """Example of skill usage"""
    skill = MemoryQuerySkill()

    # Example 1: Direct query
    user_input_1 = "what do I know about memory consolidation?"
    result_1 = await skill.handle_user_input(user_input_1)
    print("Example 1: Direct query")
    print(f"Query: {result_1.get('query')}")
    print(f"Results: {result_1.get('results_count')}")

    # Example 2: Do I remember?
    user_input_2 = "do I remember the research on transformers?"
    result_2 = await skill.handle_user_input(user_input_2)
    print("\nExample 2: Do I remember?")
    print(f"Query: {result_2.get('query')}")

    # Example 3: Show me
    user_input_3 = "show me what we know about Claude Code"
    result_3 = await skill.handle_user_input(user_input_3)
    print("\nExample 3: Show me")
    print(f"Query: {result_3.get('query')}")

    # Example 4: No memory query detected
    user_input_4 = "What time is it?"
    result_4 = await skill.handle_user_input(user_input_4)
    print(f"\nExample 4: No memory query detected")
    print(f"Result: {result_4}")


if __name__ == "__main__":
    asyncio.run(example_usage())
