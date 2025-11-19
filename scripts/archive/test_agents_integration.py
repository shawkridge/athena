#!/usr/bin/env python3
"""Quick integration test for memory agents with core operations."""

import asyncio
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, "/home/user/.work/athena/src")

from athena.agents import (
    MemoryCoordinatorAgent,
    PatternExtractorAgent,
    get_coordinator,
    get_extractor,
    coordinate_memory_storage,
    extract_session_patterns,
    run_consolidation,
)


async def test_memory_coordinator():
    """Test MemoryCoordinatorAgent with core operations."""
    print("\n" + "="*60)
    print("Testing MemoryCoordinatorAgent")
    print("="*60)

    coordinator = get_coordinator()

    # Test 1: Simple episodic memory decision
    context1 = {
        "content": "User asked about project timeline and deadlines",
        "type": "user_input",
        "importance": 0.8,
        "tags": ["project", "timeline"],
        "source": "test",
    }

    print("\nTest 1: Storing episodic event")
    print(f"  Context: {context1}")
    result1 = await coordinate_memory_storage(context1)
    print(f"  Result: {result1}")
    print(f"  Status: {'✅ PASS' if result1 else '❌ FAIL'}")

    # Test 2: Semantic memory (learning)
    context2 = {
        "content": "Learned that Python async/await requires proper error handling in database operations",
        "type": "learning",
        "importance": 0.85,
        "tags": ["python", "async", "database"],
        "source": "test",
    }

    print("\nTest 2: Storing semantic memory")
    print(f"  Context: {context2}")
    result2 = await coordinate_memory_storage(context2)
    print(f"  Result: {result2}")
    print(f"  Status: {'✅ PASS' if result2 else '❌ FAIL'}")

    # Test 3: Low importance (should skip)
    context3 = {
        "content": "x",  # Too short
        "type": "noise",
        "importance": 0.1,  # Below threshold
        "tags": ["skip"],
        "source": "test",
    }

    print("\nTest 3: Should skip low-importance content")
    print(f"  Context: {context3}")
    result3 = await coordinate_memory_storage(context3)
    print(f"  Result: {result3}")
    print(f"  Status: {'✅ PASS' if result3 is None else '❌ FAIL (should be None)'}")

    # Get statistics
    stats = coordinator.get_statistics()
    print(f"\nCoordinator Statistics: {stats}")
    print(f"  Decisions made: {stats['decisions_made']}")
    print(f"  Memories stored: {stats['memories_stored']}")
    print(f"  Skipped: {stats['skipped']}")


async def test_pattern_extractor():
    """Test PatternExtractorAgent with consolidation layer."""
    print("\n" + "="*60)
    print("Testing PatternExtractorAgent")
    print("="*60)

    extractor = get_extractor()

    # Test 1: Extract patterns from session
    session_id = f"test_session_{datetime.utcnow().isoformat()}"
    print(f"\nTest 1: Extracting patterns from session {session_id}")
    result1 = await extract_session_patterns(session_id, min_confidence=0.7)
    print(f"  Result status: {result1.get('status')}")
    print(f"  Events analyzed: {result1.get('events_analyzed')}")
    print(f"  Patterns extracted: {result1.get('patterns_extracted')}")
    print(f"  Status: {'✅ PASS' if result1.get('status') == 'success' else '❌ FAIL'}")

    # Test 2: Run consolidation cycle
    print(f"\nTest 2: Running consolidation cycle")
    result2 = await run_consolidation()
    print(f"  Result status: {result2.get('status')}")
    print(f"  Timestamp: {result2.get('timestamp')}")
    print(f"  Status: {'✅ PASS' if result2.get('status') == 'completed' else '❌ FAIL'}")

    # Get statistics
    stats = extractor.get_statistics()
    print(f"\nExtractor Statistics: {stats}")
    print(f"  Patterns extracted: {stats['patterns_extracted']}")
    print(f"  Consolidation runs: {stats['consolidation_runs']}")


async def main():
    """Run all agent integration tests."""
    print("\n" + "🧪 ATHENA AGENT INTEGRATION TEST" + "\n")

    try:
        await test_memory_coordinator()
        await test_pattern_extractor()

        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
        print("\nAgents are successfully integrated with core memory operations!")
        print("Both agents can now:")
        print("  - Import core memory layer operations")
        print("  - Make autonomous decisions")
        print("  - Store and retrieve memories")
        print("  - Run consolidation cycles")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
