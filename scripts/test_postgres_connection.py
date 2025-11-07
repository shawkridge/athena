#!/usr/bin/env python3
"""Quick test script to verify PostgreSQL connection and setup."""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from athena.core.database_factory import get_database, DatabaseFactory


async def test_database_connection():
    """Test PostgreSQL database connection and basic operations."""

    print("=" * 70)
    print("PostgreSQL Database Connection Test")
    print("=" * 70)
    print()

    # Step 1: Check available backends
    print("[1] Checking available backends...")
    available = DatabaseFactory.get_available_backends()
    print(f"   Available backends: {available}")
    print()

    # Step 2: Get database instance
    print("[2] Creating database instance...")
    try:
        db = get_database()
        print(f"   Backend: {type(db).__name__}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    print()

    # Step 3: Initialize database
    print("[3] Initializing database (creating schema)...")
    try:
        await db.initialize()
        print("   ✓ Schema initialized")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    print()

    # Step 4: Create test project
    print("[4] Creating test project...")
    try:
        project = await db.create_project(
            name="test_connection_" + str(int(asyncio.get_event_loop().time())),
            path="/test/connection/path",
            language="python",
            description="Connection test project",
        )
        print(f"   ✓ Project created: {project.name} (ID: {project.id})")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    print()

    # Step 5: Store test memory
    print("[5] Storing test memory vector...")
    try:
        embedding = [0.1] * 768  # 768-dimensional test embedding
        memory_id = await db.store_memory(
            project_id=project.id,
            content="Test memory for connection verification",
            embedding=embedding,
            memory_type="fact",
            domain="memory",
            tags=["test", "connection"],
        )
        print(f"   ✓ Memory stored (ID: {memory_id})")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    print()

    # Step 6: Retrieve test memory
    print("[6] Retrieving test memory...")
    try:
        memory = await db.get_memory(memory_id)
        if memory:
            print(f"   ✓ Memory retrieved:")
            print(f"     - Content: {memory['content'][:50]}...")
            print(f"     - Type: {memory['memory_type']}")
            print(f"     - Quality: {memory['quality_score']:.2f}")
        else:
            print("   ❌ Memory not found")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    print()

    # Step 7: Test semantic search
    print("[7] Testing semantic search...")
    try:
        query_embedding = [0.1] * 768
        results = await db.semantic_search(
            project_id=project.id,
            embedding=query_embedding,
            limit=5,
            threshold=0.0,  # Get all for testing
        )
        print(f"   ✓ Search successful, found {len(results)} memories")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    print()

    # Step 8: Test hybrid search
    print("[8] Testing hybrid search...")
    try:
        results = await db.hybrid_search(
            project_id=project.id,
            embedding=query_embedding,
            query_text="connection verification",
            limit=5,
        )
        print(f"   ✓ Hybrid search successful, found {len(results)} memories")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    print()

    # Step 9: Test task creation
    print("[9] Testing task creation...")
    try:
        task_id = await db.create_task(
            project_id=project.id,
            title="Test task",
            description="Task for connection test",
            priority=5,
        )
        print(f"   ✓ Task created (ID: {task_id})")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    print()

    # Step 10: Cleanup
    print("[10] Closing database connection...")
    try:
        await db.close()
        print("   ✓ Connection closed")
    except Exception as e:
        print(f"   ⚠️  Warning closing connection: {e}")
    print()

    return True


def main():
    """Run the connection test."""
    try:
        success = asyncio.run(test_database_connection())
        print("=" * 70)
        if success:
            print("✅ All tests passed! PostgreSQL is working correctly.")
            print("=" * 70)
            return 0
        else:
            print("❌ Some tests failed.")
            print("=" * 70)
            return 1
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
