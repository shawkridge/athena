"""
Example: Dual-Process Reasoning Integration with Memory-MCP

Demonstrates System 1 (fast) and System 2 (extended thinking) integration
with Memory-MCP for optimal performance and cost efficiency.

Run with: python examples/dual_process_reasoning.py
"""

import asyncio
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class DualProcessConfig:
    """Configuration for dual-process reasoning."""
    system_1_latency_budget_ms: float = 200  # Must respond <200ms
    system_1_max_tokens: int = 200  # Brief responses
    system_2_thinking_budget: int = 3000  # Medium thinking depth
    system_2_max_tokens: int = 1000  # Detailed responses
    adaptive_threshold: float = 0.75  # Escalate if confidence <75%


class DualProcessReasoner:
    """Manages System 1 and System 2 reasoning with Memory-MCP."""

    def __init__(self, config: Optional[DualProcessConfig] = None):
        """Initialize with configuration."""
        self.config = config or DualProcessConfig()
        self.stats = {
            "system_1_queries": 0,
            "system_2_queries": 0,
            "escalations": 0,
            "total_latency_ms": 0,
        }

    def _analyze_query_complexity(self, query: str) -> float:
        """Analyze query to estimate required reasoning depth.

        Returns: Complexity score 0-10
          0-3: Factual/retrieval (System 1)
          3-7: Analysis (Hybrid)
          7-10: Complex reasoning (System 2)
        """
        # Complexity signals and their weights
        signals = {
            "why": 2.0,
            "how": 2.5,
            "explain": 3.0,
            "debug": 4.0,
            "root cause": 5.0,
            "architecture": 6.0,
            "strategy": 7.0,
            "design": 6.5,
            "tradeoff": 6.0,
            "impact": 4.0,
        }

        complexity = 3.0  # Baseline

        for signal, weight in signals.items():
            if signal in query.lower():
                complexity = max(complexity, weight)

        # Adjust for query length (longer = more complex)
        if len(query) > 200:
            complexity += 1.0
        if len(query) > 500:
            complexity += 1.0

        return min(10.0, complexity)

    def _extract_confidence(self, response: str) -> float:
        """Extract confidence from response text.

        Returns: Confidence 0.0-1.0
        """
        uncertain_signals = ["uncertain", "might", "could", "not sure", "unclear", "probably"]
        confident_signals = ["definitely", "clearly", "proven", "confirmed", "certain"]

        uncertain_count = sum(1 for signal in uncertain_signals if signal in response.lower())
        confident_count = sum(1 for signal in confident_signals if signal in response.lower())

        total = uncertain_count + confident_count
        if total == 0:
            return 0.5  # Neutral if no signals

        return (confident_count - uncertain_count) / total

    async def system_1_reasoning(
        self, query: str, context: str
    ) -> Dict[str, Any]:
        """Fast reasoning for factual questions.

        Characteristics:
        - Response time: <200ms
        - No extended thinking
        - Top-k retrieval only (k=3)
        - Direct answers
        """
        print(f"📚 System 1: Fast retrieval")
        start = time.time()

        # Simulate fast retrieval + generation
        await asyncio.sleep(0.05)  # Mock retrieval

        response = f"Based on context: {context[:100]}... Answer: Quick factual response"

        latency_ms = (time.time() - start) * 1000
        print(f"   ✓ Completed in {latency_ms:.0f}ms")

        self.stats["system_1_queries"] += 1
        self.stats["total_latency_ms"] += latency_ms

        return {
            "system": "System 1",
            "response": response,
            "latency_ms": latency_ms,
            "thinking": None,  # No thinking
            "confidence": 0.8,
            "tokens_used": 150,
        }

    async def system_2_reasoning(
        self, query: str, context: str
    ) -> Dict[str, Any]:
        """Deep reasoning with extended thinking.

        Characteristics:
        - Response time: 5-30s
        - Extended thinking enabled
        - Full context retrieval
        - Step-by-step reasoning
        """
        print(f"🧠 System 2: Extended thinking (budget={self.config.system_2_thinking_budget})")
        start = time.time()

        # Simulate extended thinking
        thinking_time = self.config.system_2_thinking_budget / 1000  # Convert to seconds
        await asyncio.sleep(min(thinking_time / 3, 2.0))  # Mock thinking

        thinking = """<thinking>
Let me analyze this step-by-step:
1. First, I'll examine the context provided
2. Identify the key patterns and relationships
3. Consider alternative explanations
4. Evaluate evidence for each possibility
5. Reach reasoned conclusion
</thinking>"""

        response = f"After careful analysis of {context[:50]}... Detailed reasoning provides this answer"

        latency_ms = (time.time() - start) * 1000
        print(f"   ✓ Completed in {latency_ms:.0f}ms (with thinking)")

        self.stats["system_2_queries"] += 1
        self.stats["total_latency_ms"] += latency_ms

        return {
            "system": "System 2",
            "response": response,
            "latency_ms": latency_ms,
            "thinking": thinking,
            "confidence": 0.95,
            "tokens_used": 800,
        }

    async def hybrid_reasoning(
        self, query: str, context: str
    ) -> Dict[str, Any]:
        """Adaptive routing: System 1 first, escalate if needed.

        Decision flow:
        1. Analyze query complexity
        2. Use System 1 if simple
        3. Check confidence
        4. Escalate to System 2 if needed
        """
        complexity = self._analyze_query_complexity(query)
        print(f"📊 Hybrid: Complexity score {complexity:.1f}/10")

        if complexity < 4.0:
            # Simple query - use System 1 only
            print("   → Routing to System 1 (simple query)")
            return await self.system_1_reasoning(query, context)

        # Medium complexity - try System 1, may escalate
        print("   → Trying System 1 first (medium query)")
        result_1 = await self.system_1_reasoning(query, context)
        confidence = self._extract_confidence(result_1["response"])

        if confidence >= self.config.adaptive_threshold:
            print(f"   ✓ Confidence {confidence:.0%} - satisfied with System 1")
            return result_1
        else:
            print(
                f"   ⚠ Confidence {confidence:.0%} low - escalating to System 2"
            )
            self.stats["escalations"] += 1
            return await self.system_2_reasoning(query, context)

    async def run_examples(self):
        """Run example scenarios."""
        print("=" * 60)
        print("Dual-Process Reasoning Examples with Memory-MCP")
        print("=" * 60)

        # Example 1: Simple factual query
        print("\n📝 Example 1: Factual Question")
        print("-" * 60)
        print("Query: 'When did user A log in yesterday?'")
        result = await self.system_1_reasoning(
            "When did user A log in yesterday?",
            "User login events: A at 09:30, B at 14:15, A at 17:45"
        )
        print(f"Result: {result['response']}")
        print(f"Latency: {result['latency_ms']:.0f}ms | Confidence: {result['confidence']:.0%}\n")

        # Example 2: Complex analysis query
        print("📝 Example 2: Root Cause Analysis")
        print("-" * 60)
        print("Query: 'Why did the database connection pool exhaust at 3pm?'")
        result = await self.system_2_reasoning(
            "Why did the database connection pool exhaust at 3pm?",
            "At 3pm, connection count jumped from 20 to max (100). " +
            "Queries per second spiked 10x. New batch job started."
        )
        print(f"Thinking: {result['thinking'][:100]}...")
        print(f"Result: {result['response']}")
        print(f"Latency: {result['latency_ms']:.0f}ms | Confidence: {result['confidence']:.0%}\n")

        # Example 3: Hybrid routing
        print("📝 Example 3: Adaptive Routing")
        print("-" * 60)
        print("Query: 'Is this a critical bug?'")
        result = await self.hybrid_reasoning(
            "Is this a critical bug or expected behavior?",
            "Error occurs in 0.1% of requests. No data loss. Affects admin panel."
        )
        print(f"System used: {result['system']}")
        print(f"Result: {result['response']}")
        print(f"Latency: {result['latency_ms']:.0f}ms | Confidence: {result['confidence']:.0%}\n")

        # Stats summary
        print("=" * 60)
        print("Summary Statistics")
        print("=" * 60)
        total_queries = self.stats["system_1_queries"] + self.stats["system_2_queries"]
        print(f"Total queries: {total_queries}")
        print(f"  System 1: {self.stats['system_1_queries']}")
        print(f"  System 2: {self.stats['system_2_queries']}")
        print(f"  Escalations: {self.stats['escalations']}")
        if total_queries > 0:
            avg_latency = self.stats["total_latency_ms"] / total_queries
            print(f"Average latency: {avg_latency:.0f}ms")

        # Cost estimate
        print("\nEstimated Cost:")
        s1_tokens = self.stats["system_1_queries"] * 150
        s2_tokens = self.stats["system_2_queries"] * 800
        s1_thinking = self.stats["system_2_queries"] * self.config.system_2_thinking_budget

        print(f"  System 1 tokens: {s1_tokens}")
        print(f"  System 2 tokens: {s2_tokens} + {s1_thinking} thinking tokens")
        print(f"  Estimated: ${(s1_tokens * 0.0001 + s2_tokens * 0.0003 + s1_thinking * 0.00001):.3f}")


async def main():
    """Run the examples."""
    reasoner = DualProcessReasoner()
    await reasoner.run_examples()


if __name__ == "__main__":
    asyncio.run(main())
