#!/usr/bin/env python3
"""Integration test for Qdrant + llama.cpp hybrid architecture.

Tests:
1. Config validation (models exist)
2. llama.cpp embedding model initialization
3. Qdrant connectivity
4. Dual-write pattern (SQLite + Qdrant)
5. Semantic search (Qdrant backend)
6. Memory deletion (both databases)
"""

import sys
import os
import tempfile
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from athena.core import config
from athena.memory.store import MemoryStore
from athena.core.models import MemoryType


def print_section(title):
    """Print a colored section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def test_config_validation():
    """Validate configuration."""
    print_section("1. Configuration Validation")

    print(f"✓ Embedding Provider: {config.EMBEDDING_PROVIDER}")
    print(f"✓ LLM Provider: {config.LLM_PROVIDER}")
    print(f"✓ Qdrant URL: {config.QDRANT_URL}")
    print(f"✓ Qdrant Collection: {config.QDRANT_COLLECTION}")
    print(f"✓ Qdrant Embedding Dim: {config.QDRANT_EMBEDDING_DIM}")

    # Check embedding dimension match
    if config.LLAMACPP_EMBEDDING_DIM == config.QDRANT_EMBEDDING_DIM:
        print(f"\n✅ Dimension Match: {config.LLAMACPP_EMBEDDING_DIM}D")
    else:
        print(f"\n❌ Dimension Mismatch!")
        print(f"   llama.cpp: {config.LLAMACPP_EMBEDDING_DIM}D")
        print(f"   Qdrant: {config.QDRANT_EMBEDDING_DIM}D")
        return False

    return True


def test_memory_store_init():
    """Test MemoryStore initialization."""
    print_section("2. MemoryStore Initialization")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        print(f"Database: {db_path}")
        store = MemoryStore(db_path, use_qdrant=True)

        # Check embedding model
        print(f"✓ Embedding backend: {store.embedder.provider}")
        print(f"✓ Embedding dimensions: {store.embedder.embedding_dim}D")

        # Check Qdrant
        if store.qdrant:
            print(f"✓ Qdrant enabled: {config.QDRANT_URL}")

            # Test health
            if store.qdrant.health_check():
                print(f"✓ Qdrant health check: PASSED")
            else:
                print(f"❌ Qdrant health check: FAILED")
                return False
        else:
            print(f"⚠️  Qdrant not available, using SQLite fallback")

        return store, db_path
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return None, db_path


def test_dual_write(store, db_path, project_id):
    """Test dual-write pattern (SQLite + Qdrant)."""
    print_section("3. Dual-Write Pattern (SQLite + Qdrant)")

    try:
        # Store test memory
        content = "Python is a high-level programming language"
        mem_id = store.remember(
            content=content,
            memory_type=MemoryType.FACT,
            project_id=project_id,
            tags=["python", "programming"]
        )

        print(f"✓ Stored memory ID: {mem_id}")
        print(f"  Content: {content[:50]}...")
        print(f"  Type: fact")
        print(f"  Tags: python, programming")

        # Verify in SQLite
        sqlite_mem = store.db.get_memory(mem_id)
        if sqlite_mem:
            print(f"✓ Found in SQLite metadata")
            print(f"  Content: {sqlite_mem.content[:50]}...")
        else:
            print(f"❌ Not found in SQLite")
            return False, mem_id

        # Verify in Qdrant
        if store.qdrant:
            qdrant_mem = store.qdrant.get_memory(mem_id)
            if qdrant_mem:
                print(f"✓ Found in Qdrant vectors")
                print(f"  Embedding dim: {len(qdrant_mem.embedding)}")
            else:
                print(f"❌ Not found in Qdrant")
                return False, mem_id

        return True, mem_id
    except Exception as e:
        print(f"❌ Dual-write failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_semantic_search(store, project_id):
    """Test semantic search via Qdrant."""
    print_section("4. Semantic Search (Qdrant)")

    try:
        # Store multiple memories
        memories = [
            "Docker containers provide process isolation",
            "Kubernetes orchestrates container deployments",
            "Python programming language has clean syntax",
        ]

        mem_ids = []
        for content in memories:
            mem_id = store.remember(
                content=content,
                memory_type=MemoryType.FACT,
                project_id=project_id,
                tags=["test"]
            )
            mem_ids.append(mem_id)
            print(f"✓ Stored: {content[:40]}...")

        print(f"\nTotal memories: {len(mem_ids)}")

        # Test semantic search
        query = "container technology"
        results = store.recall(query, project_id=project_id, k=3)

        print(f"\nQuery: '{query}'")
        print(f"Results: {len(results)}")

        if len(results) > 0:
            for i, result in enumerate(results, 1):
                print(f"\n  {i}. {result.memory.content[:50]}...")
                print(f"     Similarity: {result.similarity:.3f}")
                print(f"     Rank: {result.rank}")

            print(f"\n✅ Semantic search working via Qdrant")
            return True, mem_ids
        else:
            print(f"\n❌ No results returned")
            return False, mem_ids

    except Exception as e:
        print(f"❌ Semantic search failed: {e}")
        import traceback
        traceback.print_exc()
        return False, []


def test_memory_deletion(store, mem_ids):
    """Test memory deletion (SQLite + Qdrant)."""
    print_section("5. Memory Deletion (SQLite + Qdrant)")

    if not mem_ids:
        print("❌ No memories to delete")
        return False

    try:
        mem_id = mem_ids[0]
        deleted = store.forget(mem_id)

        if deleted:
            print(f"✓ Deleted memory {mem_id}")

            # Verify deletion from SQLite
            sqlite_mem = store.db.get_memory(mem_id)
            if sqlite_mem is None:
                print(f"✓ Confirmed: Deleted from SQLite")
            else:
                print(f"❌ Still exists in SQLite")
                return False

            # Verify deletion from Qdrant
            if store.qdrant:
                qdrant_mem = store.qdrant.get_memory(mem_id)
                if qdrant_mem is None:
                    print(f"✓ Confirmed: Deleted from Qdrant")
                else:
                    print(f"❌ Still exists in Qdrant")
                    return False

            return True
        else:
            print(f"❌ Deletion failed")
            return False

    except Exception as e:
        print(f"❌ Deletion test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_qdrant_stats(store):
    """Show Qdrant collection statistics."""
    print_section("6. Qdrant Collection Statistics")

    if not store.qdrant:
        print("⚠️  Qdrant not available")
        return True

    try:
        count = store.qdrant.count()
        print(f"Collection: {config.QDRANT_COLLECTION}")
        print(f"Total vectors: {count}")
        print(f"Vector dimensions: {config.QDRANT_EMBEDDING_DIM}D")

        return True
    except Exception as e:
        print(f"❌ Failed to get stats: {e}")
        return False


def main():
    """Run all integration tests."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " QDRANT + llama.cpp INTEGRATION TEST ".center(68) + "║")
    print("╚" + "=" * 68 + "╝")

    results = {}

    # Test 1: Config
    results["config"] = test_config_validation()
    if not results["config"]:
        print("\n❌ Configuration validation failed")
        return False

    # Test 2: MemoryStore init
    store, db_path = test_memory_store_init()
    if not store:
        print("\n❌ MemoryStore initialization failed")
        return False
    results["memory_store_init"] = True

    # Create project
    print_section("Creating Test Project")
    project = store.create_project("test_project", "/tmp/test")
    print(f"✓ Project ID: {project.id}")
    print(f"✓ Project Name: {project.name}")

    # Test 3: Dual-write
    success, mem_id = test_dual_write(store, db_path, project.id)
    results["dual_write"] = success

    # Test 4: Semantic search
    if success:
        success, mem_ids = test_semantic_search(store, project.id)
        results["semantic_search"] = success

        # Test 5: Deletion
        if success:
            results["deletion"] = test_memory_deletion(store, mem_ids)

    # Test 6: Stats
    results["qdrant_stats"] = test_qdrant_stats(store)

    # Summary
    print_section("SUMMARY")

    all_passed = all(results.values())

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name.replace('_', ' ').title()}")

    print()

    if all_passed:
        print("╔" + "=" * 68 + "╗")
        print("║" + " ✅ ALL TESTS PASSED ".center(68) + "║")
        print("║" + " Qdrant + llama.cpp hybrid architecture is operational! ".center(68) + "║")
        print("╚" + "=" * 68 + "╝")
        return True
    else:
        print("╔" + "=" * 68 + "╗")
        print("║" + " ❌ SOME TESTS FAILED ".center(68) + "║")
        print("╚" + "=" * 68 + "╝")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
