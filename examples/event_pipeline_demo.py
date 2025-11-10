"""Demonstration of EventProcessingPipeline capabilities.

This example shows:
1. Basic batch processing
2. Deduplication (in-memory and database)
3. High throughput ingestion
4. LRU cache management
5. Statistics tracking
"""

import asyncio
import tempfile
import os
from datetime import datetime
from pathlib import Path

# Add src to path for development
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from athena.episodic.pipeline import EventProcessingPipeline
from athena.episodic.store import EpisodicStore
from athena.episodic.hashing import EventHasher
from athena.episodic.models import EpisodicEvent, EventType, EventContext, EventOutcome
from athena.core.embeddings import EmbeddingModel
from athena.core.database import Database


def create_sample_event(project_id: int, content: str, session_id: str = "demo") -> EpisodicEvent:
    """Create a sample episodic event."""
    return EpisodicEvent(
        project_id=project_id,
        session_id=session_id,
        timestamp=datetime.now(),
        event_type=EventType.ACTION,
        content=content,
        outcome=EventOutcome.SUCCESS,
        context=EventContext(
            cwd="/home/user/project", files=["main.py"], task="Development", phase="implementation"
        ),
    )


async def demo_basic_processing():
    """Demo 1: Basic batch processing."""
    print("\n" + "=" * 80)
    print("Demo 1: Basic Batch Processing")
    print("=" * 80)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name

    try:
        # Initialize pipeline
        db = Database(db_path)
        store = EpisodicStore(db)
        hasher = EventHasher()
        embedder = EmbeddingModel()
        pipeline = EventProcessingPipeline(store, embedder, hasher)

        # Create batch of events
        events = [
            create_sample_event(1, "Implemented user authentication"),
            create_sample_event(1, "Added OAuth 2.0 support"),
            create_sample_event(1, "Fixed login bug"),
            create_sample_event(1, "Updated tests"),
            create_sample_event(1, "Deployed to staging"),
        ]

        print(f"\nProcessing {len(events)} events...")
        stats = await pipeline.process_batch(events)

        print("\nResults:")
        print(f"  Total events: {stats['total']}")
        print(f"  Inserted: {stats['inserted']}")
        print(f"  Skipped (duplicate): {stats['skipped_duplicate']}")
        print(f"  Skipped (existing): {stats['skipped_existing']}")
        print(f"  Processing time: {stats['processing_time_ms']:.1f}ms")
        print(
            f"  Throughput: {stats['total'] / (stats['processing_time_ms'] / 1000):.0f} events/sec"
        )

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


async def demo_deduplication():
    """Demo 2: Deduplication capabilities."""
    print("\n" + "=" * 80)
    print("Demo 2: Deduplication")
    print("=" * 80)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name

    try:
        db = Database(db_path)
        store = EpisodicStore(db)
        hasher = EventHasher()
        embedder = EmbeddingModel()
        pipeline = EventProcessingPipeline(store, embedder, hasher)

        # Test 1: In-memory deduplication (within batch)
        print("\nTest 1: In-memory deduplication (within batch)")
        duplicate_event = create_sample_event(1, "Duplicate event test")
        batch_with_dupes = [duplicate_event] * 5  # 5 copies

        stats1 = await pipeline.process_batch(batch_with_dupes)
        print(f"  Inserted: {stats1['inserted']} (expected: 1)")
        print(f"  Skipped (duplicate): {stats1['skipped_duplicate']} (expected: 4)")

        # Test 2: Cache-based deduplication
        print("\nTest 2: Cache-based deduplication")
        same_batch = [duplicate_event] * 3
        stats2 = await pipeline.process_batch(same_batch)
        print(f"  Inserted: {stats2['inserted']} (expected: 0)")
        print(f"  Skipped (cache hit): {stats2['skipped_duplicate'] + stats2['skipped_existing']}")

        # Test 3: Database-based deduplication (after cache clear)
        print("\nTest 3: Database-based deduplication (after cache clear)")
        pipeline.clear_cache()
        stats3 = await pipeline.process_batch([duplicate_event])
        print(f"  Inserted: {stats3['inserted']} (expected: 0)")
        print(f"  Skipped (database lookup): {stats3['skipped_existing']}")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


async def demo_high_throughput():
    """Demo 3: High throughput processing."""
    print("\n" + "=" * 80)
    print("Demo 3: High Throughput Processing")
    print("=" * 80)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name

    try:
        db = Database(db_path)
        store = EpisodicStore(db)
        hasher = EventHasher()
        embedder = EmbeddingModel()
        pipeline = EventProcessingPipeline(store, embedder, hasher)

        # Process batches of increasing size
        batch_sizes = [100, 500, 1000, 5000]

        for size in batch_sizes:
            print(f"\nProcessing {size} events...")
            events = [
                create_sample_event(1, f"Event {i}", session_id=f"sess_{i // 100}")
                for i in range(size)
            ]

            stats = await pipeline.process_batch(events)
            throughput = stats["total"] / (stats["processing_time_ms"] / 1000)

            print(f"  Time: {stats['processing_time_ms']:.1f}ms")
            print(f"  Throughput: {throughput:.0f} events/sec")
            print(f"  Inserted: {stats['inserted']}")

        # Show global statistics
        print("\nGlobal Statistics:")
        global_stats = pipeline.get_statistics()
        print(f"  Total processed: {global_stats['total_processed']}")
        print(f"  Total inserted: {global_stats['total_inserted']}")
        print(f"  Cache size: {global_stats['cache_size']}")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


async def demo_lru_cache():
    """Demo 4: LRU cache management."""
    print("\n" + "=" * 80)
    print("Demo 4: LRU Cache Management")
    print("=" * 80)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name

    try:
        db = Database(db_path)
        store = EpisodicStore(db)
        hasher = EventHasher()
        embedder = EmbeddingModel()

        # Create pipeline with small cache (10 items) for demo
        pipeline = EventProcessingPipeline(store, embedder, hasher, lru_cache_size=10)

        print("\nCreated pipeline with LRU cache size: 10")

        # Insert 15 events (will exceed cache limit)
        events = [create_sample_event(1, f"Cache test event {i}") for i in range(15)]

        stats = await pipeline.process_batch(events)
        print(f"\nInserted {stats['inserted']} events")

        global_stats = pipeline.get_statistics()
        print(f"Cache size: {global_stats['cache_size']} (limited to 10)")

        # Re-insert first 5 events (should be evicted from cache)
        print("\nRe-inserting first 5 events (likely evicted from cache)...")
        stats2 = await pipeline.process_batch(events[:5])
        print(f"  Skipped (database lookup): {stats2['skipped_existing']}")

        # Re-insert last 5 events (should be in cache)
        print("\nRe-inserting last 5 events (should be in cache)...")
        stats3 = await pipeline.process_batch(events[-5:])
        print(
            f"  Skipped (cache or database): {stats3['skipped_duplicate'] + stats3['skipped_existing']}"
        )

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


async def demo_code_aware_events():
    """Demo 5: Code-aware event processing."""
    print("\n" + "=" * 80)
    print("Demo 5: Code-Aware Event Processing")
    print("=" * 80)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name

    try:
        db = Database(db_path)
        store = EpisodicStore(db)
        hasher = EventHasher()
        embedder = EmbeddingModel()
        pipeline = EventProcessingPipeline(store, embedder, hasher)

        # Create code-aware events
        from athena.episodic.models import CodeEventType

        events = [
            EpisodicEvent(
                project_id=1,
                session_id="code_session",
                timestamp=datetime.now(),
                event_type=EventType.ACTION,
                code_event_type=CodeEventType.CODE_EDIT,
                content="Refactored authentication module",
                file_path="src/auth.py",
                symbol_name="authenticate_user",
                symbol_type="function",
                language="python",
                diff="@@ -10,3 +10,5 @@ def authenticate_user(...):\n     return validate(credentials)",
                git_commit="abc123",
                git_author="developer@example.com",
                context=EventContext(cwd="/project"),
            ),
            EpisodicEvent(
                project_id=1,
                session_id="code_session",
                timestamp=datetime.now(),
                event_type=EventType.ACTION,
                code_event_type=CodeEventType.TEST_RUN,
                content="Ran authentication tests",
                file_path="tests/test_auth.py",
                test_name="test_oauth_flow",
                test_passed=True,
                language="python",
                context=EventContext(cwd="/project"),
            ),
        ]

        print(f"\nProcessing {len(events)} code-aware events...")
        stats = await pipeline.process_batch(events)

        print("\nResults:")
        print(f"  Inserted: {stats['inserted']}")
        print(f"  Events include:")
        print(f"    - Code edits with diffs")
        print(f"    - Test runs with results")
        print(f"    - File and symbol tracking")
        print(f"    - Git commit metadata")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


async def main():
    """Run all demonstrations."""
    print("\n" + "=" * 80)
    print("EventProcessingPipeline Demonstrations")
    print("=" * 80)

    # Suppress embedding warnings for cleaner output
    import logging

    logging.getLogger().setLevel(logging.ERROR)

    await demo_basic_processing()
    await demo_deduplication()
    await demo_high_throughput()
    await demo_lru_cache()
    await demo_code_aware_events()

    print("\n" + "=" * 80)
    print("All demonstrations complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
