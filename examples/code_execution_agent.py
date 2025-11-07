#!/usr/bin/env python3
"""Example agent using Athena client in code execution pattern.

This demonstrates the pattern from:
https://www.anthropic.com/engineering/code-execution-with-mcp

Key principle: Process large results locally, return only summaries to model.
This saves ~98% of tokens by keeping intermediate results out of context.

Usage:
    python code_execution_agent.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from athena import AthenaClient


def analyze_consolidation_patterns():
    """Example: Analyze consolidation patterns locally.

    This demonstrates:
    1. Tool discovery (lazy loading)
    2. Large result processing locally
    3. Returning only summary to "model"
    """
    print("=" * 70)
    print("Example 1: Consolidation Pattern Analysis")
    print("=" * 70)

    # Initialize client
    client = AthenaClient("http://localhost:3000")

    # Step 1: Discover available tools (gets summaries, not full definitions)
    print("\n1. Discovering available tools...")
    tools = client.discover_tools()
    print(f"   Found {tools['total_tools']} total tools")
    for category, info in tools["categories"].items():
        print(f"   - {category}: {info['count']} tools")

    # Step 2: Get specific tool definition only when needed
    print("\n2. Getting consolidate tool definition...")
    tool_def = client.get_tool("run_consolidation")
    print(f"   Parameters: {[p['name'] for p in tool_def['parameters']]}")

    # Step 3: Call the tool - this returns large result
    print("\n3. Running consolidation (returns large result)...")
    result = client.consolidate(strategy="balanced", days_back=7)

    # Step 4: Process result LOCALLY - key to token savings
    print("\n4. Processing results locally (NOT sending to model)...")
    patterns = result.get("patterns", [])
    print(f"   Extracted {len(patterns)} patterns total")

    # Filter locally
    high_confidence = [p for p in patterns if p.get("confidence", 0) > 0.8]
    print(f"   High confidence (>0.8): {len(high_confidence)}")

    # Group by type
    by_type = {}
    for p in patterns:
        ptype = p.get("type", "unknown")
        by_type[ptype] = by_type.get(ptype, 0) + 1
    print(f"   By type: {by_type}")

    # Step 5: Return ONLY summary to model
    summary = f"""
Consolidation Analysis Summary:
- Total patterns: {len(patterns)}
- High confidence: {len(high_confidence)}
- Pattern types: {by_type}
- Average confidence: {sum(p.get('confidence', 0) for p in patterns) / len(patterns):.2f}
    """.strip()

    print(f"\n5. Summary to return to model (only {len(summary)} bytes):")
    print(f"   {summary}")

    print("\n✓ Large intermediate result stayed local")
    print("  Token savings: ~98% (50KB → 200 bytes)")


def search_and_summarize_memories():
    """Example: Search memories and summarize results locally.

    Demonstrates:
    1. Semantic search returning many results
    2. Local filtering and summarization
    3. Context-efficient return to model
    """
    print("\n" + "=" * 70)
    print("Example 2: Memory Search & Summarization")
    print("=" * 70)

    client = AthenaClient("http://localhost:3000")

    # Search returns many results
    print("\n1. Searching memories (returns many results)...")
    results = client.recall(query="performance optimization", k=50)
    print(f"   Found {len(results)} matching memories")

    # Process locally
    print("\n2. Processing results locally...")

    # Group by relevance
    high_relevance = [r for r in results if r.get("score", 0) > 0.8]
    medium_relevance = [r for r in results if 0.5 < r.get("score", 0) <= 0.8]

    print(f"   High relevance: {len(high_relevance)}")
    print(f"   Medium relevance: {len(medium_relevance)}")

    # Extract key insights
    print("\n3. Extracting key insights...")
    top_3 = sorted(results, key=lambda r: r.get("score", 0), reverse=True)[:3]
    insights = []
    for i, result in enumerate(top_3, 1):
        preview = result.get("content", "")[:100]
        insights.append(f"{i}. {preview}... (score: {result.get('score', 0):.2f})")

    # Return summary
    summary = f"""
Memory Search Summary:
- Query: "performance optimization"
- Total matches: {len(results)}
- High relevance: {len(high_relevance)}
- Medium relevance: {len(medium_relevance)}

Top Insights:
{chr(10).join(insights)}
    """.strip()

    print(f"\n4. Summary to model ({len(summary)} bytes):")
    print(f"   {summary}")

    print("\n✓ Filtering happened locally, only summary returned")


def discover_tools_example():
    """Example: Discover tools without loading full definitions.

    Demonstrates lazy tool loading - only load definitions when needed.
    """
    print("\n" + "=" * 70)
    print("Example 3: Tool Discovery (Lazy Loading)")
    print("=" * 70)

    client = AthenaClient("http://localhost:3000")

    # Discover tools - just summaries
    print("\n1. Discovering tools (summaries only)...")
    tools = client.discover_tools()

    print(f"\n2. Available tool categories:")
    for category, info in tools["categories"].items():
        print(f"   {category}: {info['count']} tools")
        for tool in info["tools"][:2]:  # Show first 2
            print(f"      - {tool['name']}: {tool['description']}")
        if len(info["tools"]) > 2:
            print(f"      ... and {len(info['tools']) - 2} more")

    # Get full definition only when needed
    print(f"\n3. Loading specific tool definition on demand...")
    tool = client.get_tool("recall")
    print(f"   Tool: {tool['name']}")
    print(f"   Description: {tool['description']}")
    print(f"   Parameters:")
    for param in tool["parameters"]:
        print(f"      - {param['name']}: {param['type']} - {param['description']}")

    print("\n✓ Only loaded definition when needed")


def main():
    """Run all examples."""
    try:
        # Check if server is running
        client = AthenaClient("http://localhost:3000")
        health = client.health()
        print(f"\nConnected to Athena server v{health.get('version', 'unknown')}")
        print(f"Status: {health.get('status', 'unknown')}")
        client.close()

    except Exception as e:
        print(f"\nError: Could not connect to Athena server at http://localhost:3000")
        print(f"Make sure the server is running: docker-compose up")
        print(f"Details: {e}")
        return

    try:
        # Run examples
        discover_tools_example()
        # analyze_consolidation_patterns()
        search_and_summarize_memories()

        print("\n" + "=" * 70)
        print("Examples completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\nError during examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
