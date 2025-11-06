#!/usr/bin/env python3
"""Test Qdrant integration with MemoryStore."""

import sys
import os
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from athena.memory.store import MemoryStore
from athena.core.models import MemoryType

def test_qdrant_integration():
    """Test Qdrant integration end-to-end."""

    print("=" * 60)
    print("Testing Qdrant Integration")
    print("=" * 60)

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    print(f"\n1. Initializing MemoryStore with Qdrant...")
    print(f"   Database: {db_path}")
    print(f"   Qdrant URL: {os.environ.get('QDRANT_URL', 'http://localhost:6333')}")

    try:
        store = MemoryStore(db_path, use_qdrant=True)

        # Check if Qdrant is enabled
        if store.qdrant:
            print("   ✅ Qdrant adapter initialized")

            # Test health
            if store.qdrant.health_check():
                print("   ✅ Qdrant health check passed")
            else:
                print("   ❌ Qdrant health check failed")
                return False
        else:
            print("   ⚠️  Qdrant not available, using SQLite fallback")

        # Create project
        print("\n2. Creating test project...")
        project = store.create_project("test_project", "/tmp/test")
        print(f"   ✅ Project created: ID={project.id}")

        # Store some memories
        print("\n3. Storing test memories...")
        memory_ids = []
        test_memories = [
            ("Python is a high-level programming language", "fact"),
            ("Docker containers provide isolation", "fact"),
            ("Vector databases enable semantic search", "fact"),
        ]

        for content, mem_type in test_memories:
            mem_id = store.remember(
                content=content,
                memory_type=MemoryType(mem_type),
                project_id=project.id,
                tags=["test"]
            )
            memory_ids.append(mem_id)
            print(f"   ✅ Stored memory {mem_id}: {content[:50]}...")

        # Verify in Qdrant
        if store.qdrant:
            count = store.qdrant.count()
            print(f"\n   Qdrant collection size: {count} memories")

        # Test semantic search
        print("\n4. Testing semantic search...")
        query = "programming languages"
        results = store.recall(query, project_id=project.id, k=3)

        print(f"   Query: '{query}'")
        print(f"   Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"   {i}. {result.memory.content[:60]}... (score: {result.similarity:.3f})")

        if len(results) > 0:
            print("   ✅ Semantic search working")
        else:
            print("   ❌ No results returned")
            return False

        # Test deletion
        print("\n5. Testing memory deletion...")
        deleted = store.forget(memory_ids[0])
        if deleted:
            print(f"   ✅ Deleted memory {memory_ids[0]}")

        if store.qdrant:
            count_after = store.qdrant.count()
            print(f"   Qdrant collection size after delete: {count_after}")

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"\n🧹 Cleaned up test database")

if __name__ == "__main__":
    success = test_qdrant_integration()
    sys.exit(0 if success else 1)
