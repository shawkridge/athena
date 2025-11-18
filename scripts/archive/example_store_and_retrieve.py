"""
Example: Store and retrieve an episodic event using Athena.

This example demonstrates:
1. Initializing the episodic memory system
2. Storing an event with remember()
3. Retrieving the event with recall()
4. Accessing event details

Run with: python example_store_and_retrieve.py
"""

import asyncio
from datetime import datetime

from src.athena.core.database import Database
from src.athena.episodic.store import EpisodicStore
from src.athena.episodic.operations import EpisodicOperations


async def main():
    """Store and retrieve an event."""

    print("=" * 60)
    print("Athena Episodic Memory: Store & Retrieve Example")
    print("=" * 60)

    # Initialize database (creates connection pool)
    db = Database()
    await db.initialize()
    print("✓ Database initialized")

    # Initialize episodic store (creates tables on first use)
    episodic_store = EpisodicStore(db)
    print("✓ Episodic store initialized")

    # Create operations interface
    operations = EpisodicOperations(db, episodic_store)
    print("✓ Operations interface created\n")

    # ─────────────────────────────────────────────────────────────
    # STEP 1: Store an event
    # ─────────────────────────────────────────────────────────────

    print("STEP 1: Storing an event...")
    print("-" * 60)

    event_id = await operations.remember(
        content="User analyzed quarterly sales data and identified 15% growth trend",
        context={
            "analysis_type": "quarterly_review",
            "data_source": "sales_database",
            "duration_seconds": 45,
        },
        tags=["sales", "analysis", "q3_2024"],
        source="agent",
        importance=0.85,  # High importance
        session_id="session_abc123"
    )

    print(f"✓ Event stored successfully")
    print(f"  Event ID: {event_id}\n")

    # ─────────────────────────────────────────────────────────────
    # STEP 2: Retrieve the event by semantic search
    # ─────────────────────────────────────────────────────────────

    print("STEP 2: Retrieving by semantic search...")
    print("-" * 60)

    results = await operations.recall(
        query="quarterly sales analysis",
        limit=5,
        min_confidence=0.5
    )

    print(f"✓ Search completed")
    print(f"  Found {len(results)} result(s)\n")

    # ─────────────────────────────────────────────────────────────
    # STEP 3: Display the retrieved event
    # ─────────────────────────────────────────────────────────────

    print("STEP 3: Event details...")
    print("-" * 60)

    if results:
        event = results[0]  # First result
        print(f"Content:        {event.content}")
        print(f"ID:             {event.id}")
        print(f"Timestamp:      {event.timestamp}")
        print(f"Tags:           {', '.join(event.tags)}")
        print(f"Importance:     {event.importance}")
        print(f"Event Type:     {event.event_type}")
        print(f"Session ID:     {event.session_id}")

        if event.metadata:
            print(f"Metadata:")
            for key, value in event.metadata.items():
                print(f"  - {key}: {value}")

    print()

    # ─────────────────────────────────────────────────────────────
    # STEP 4: Retrieve by tags
    # ─────────────────────────────────────────────────────────────

    print("STEP 4: Retrieving by tags...")
    print("-" * 60)

    tag_results = await operations.get_by_tags(
        tags=["sales", "analysis"],
        limit=10
    )

    print(f"✓ Tag search completed")
    print(f"  Found {len(tag_results)} result(s) with tags ['sales', 'analysis']\n")

    # ─────────────────────────────────────────────────────────────
    # STEP 5: Retrieve recent events
    # ─────────────────────────────────────────────────────────────

    print("STEP 5: Retrieving recent events...")
    print("-" * 60)

    recent = await operations.recall_recent(limit=5)

    print(f"✓ Recent events retrieved")
    print(f"  Found {len(recent)} recent event(s)\n")

    # ─────────────────────────────────────────────────────────────
    # STEP 6: Get session statistics
    # ─────────────────────────────────────────────────────────────

    print("STEP 6: Session statistics...")
    print("-" * 60)

    stats = await operations.get_statistics(session_id="session_abc123")

    print(f"Total events in session:  {stats.get('total_events', 0)}")
    print(f"Average importance:       {stats.get('avg_importance', 0):.2f}")
    print(f"Time span (days):         {stats.get('time_span_days', 0)}")
    print()

    # ─────────────────────────────────────────────────────────────
    # Cleanup
    # ─────────────────────────────────────────────────────────────

    print("=" * 60)
    print("✓ Example completed successfully!")
    print("=" * 60)

    # Close database connections
    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
