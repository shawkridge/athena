#!/usr/bin/env python3
"""Demo script showing query expansion in semantic search.

This script demonstrates how query expansion improves recall by generating
alternative query phrasings and merging results.
"""

import logging
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from athena.core.database import Database
from athena.core.embeddings import EmbeddingModel
from athena.memory.search import SemanticSearch
from athena.core.models import Memory, MemoryType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demo_query_expansion_enabled():
    """Demo with query expansion enabled."""
    logger.info("=" * 80)
    logger.info("DEMO 1: Query Expansion ENABLED")
    logger.info("=" * 80)

    # Set up temporary database
    db = Database(":memory:")
    embedder = EmbeddingModel()

    # Create search engine with expansion enabled
    os.environ["RAG_QUERY_EXPANSION_ENABLED"] = "true"
    os.environ["RAG_QUERY_EXPANSION_VARIANTS"] = "3"

    search = SemanticSearch(db, embedder)

    # Create test project
    project = db.create_project("demo_project", "/tmp/demo")

    # Add some test memories
    test_memories = [
        Memory(
            id=None,
            project_id=project.id,
            content="User authentication is handled by JWT tokens",
            memory_type=MemoryType.FACT,
            embedding=embedder.embed("JWT authentication"),
        ),
        Memory(
            id=None,
            project_id=project.id,
            content="Login system uses OAuth2 for third-party providers",
            memory_type=MemoryType.FACT,
            embedding=embedder.embed("OAuth2 login"),
        ),
        Memory(
            id=None,
            project_id=project.id,
            content="Password hashing uses bcrypt with salt",
            memory_type=MemoryType.FACT,
            embedding=embedder.embed("password security"),
        ),
    ]

    for memory in test_memories:
        db.store_memory(memory)

    # Search with query expansion
    logger.info("\nSearching: 'How do we handle authentication?'")
    logger.info("-" * 80)

    results = search.recall(
        query="How do we handle authentication?",
        project_id=project.id,
        k=3,
    )

    logger.info(f"\nFound {len(results)} results:")
    for result in results:
        logger.info(f"  [{result.rank}] Similarity: {result.similarity:.3f}")
        logger.info(f"      Content: {result.memory.content}")
        logger.info("")

    logger.info("=" * 80)


def demo_query_expansion_disabled():
    """Demo with query expansion disabled."""
    logger.info("\n" + "=" * 80)
    logger.info("DEMO 2: Query Expansion DISABLED")
    logger.info("=" * 80)

    # Set up temporary database
    db = Database(":memory:")
    embedder = EmbeddingModel()

    # Create search engine with expansion disabled
    os.environ["RAG_QUERY_EXPANSION_ENABLED"] = "false"

    search = SemanticSearch(db, embedder)

    # Create test project
    project = db.create_project("demo_project", "/tmp/demo")

    # Add same test memories
    test_memories = [
        Memory(
            id=None,
            project_id=project.id,
            content="User authentication is handled by JWT tokens",
            memory_type=MemoryType.FACT,
            embedding=embedder.embed("JWT authentication"),
        ),
        Memory(
            id=None,
            project_id=project.id,
            content="Login system uses OAuth2 for third-party providers",
            memory_type=MemoryType.FACT,
            embedding=embedder.embed("OAuth2 login"),
        ),
        Memory(
            id=None,
            project_id=project.id,
            content="Password hashing uses bcrypt with salt",
            memory_type=MemoryType.FACT,
            embedding=embedder.embed("password security"),
        ),
    ]

    for memory in test_memories:
        db.store_memory(memory)

    # Search without query expansion
    logger.info("\nSearching: 'How do we handle authentication?'")
    logger.info("-" * 80)

    results = search.recall(
        query="How do we handle authentication?",
        project_id=project.id,
        k=3,
    )

    logger.info(f"\nFound {len(results)} results:")
    for result in results:
        logger.info(f"  [{result.rank}] Similarity: {result.similarity:.3f}")
        logger.info(f"      Content: {result.memory.content}")
        logger.info("")

    logger.info("=" * 80)


def demo_performance_comparison():
    """Compare performance with and without expansion."""
    logger.info("\n" + "=" * 80)
    logger.info("DEMO 3: Performance Comparison")
    logger.info("=" * 80)

    import time

    # Set up database with more memories
    db = Database(":memory:")
    embedder = EmbeddingModel()
    project = db.create_project("perf_test", "/tmp/perf")

    # Add 100 test memories
    logger.info("\nCreating 100 test memories...")
    for i in range(100):
        memory = Memory(
            id=None,
            project_id=project.id,
            content=f"Test memory {i} with various content about software engineering",
            memory_type=MemoryType.FACT,
            embedding=embedder.embed(f"test content {i}"),
        )
        db.store_memory(memory)

    # Test with expansion disabled
    os.environ["RAG_QUERY_EXPANSION_ENABLED"] = "false"
    search_disabled = SemanticSearch(db, embedder)

    start = time.time()
    results_disabled = search_disabled.recall(
        query="software engineering best practices",
        project_id=project.id,
        k=10,
    )
    time_disabled = time.time() - start

    logger.info(f"\nWithout expansion:")
    logger.info(f"  Results: {len(results_disabled)}")
    logger.info(f"  Time: {time_disabled:.3f}s")

    # Test with expansion enabled
    os.environ["RAG_QUERY_EXPANSION_ENABLED"] = "true"
    os.environ["RAG_QUERY_EXPANSION_VARIANTS"] = "4"
    search_enabled = SemanticSearch(db, embedder)

    start = time.time()
    results_enabled = search_enabled.recall(
        query="software engineering best practices",
        project_id=project.id,
        k=10,
    )
    time_enabled = time.time() - start

    logger.info(f"\nWith expansion (4 variants):")
    logger.info(f"  Results: {len(results_enabled)}")
    logger.info(f"  Time: {time_enabled:.3f}s")
    logger.info(f"  Overhead: {time_enabled - time_disabled:.3f}s ({((time_enabled/time_disabled - 1) * 100):.1f}%)")

    logger.info("=" * 80)


if __name__ == "__main__":
    logger.info("\nQuery Expansion Integration Demo")
    logger.info("=" * 80)
    logger.info("This demo shows how query expansion improves recall by generating")
    logger.info("alternative query phrasings and merging results.")
    logger.info("")

    # Note: These demos require LLM client (Claude or Ollama)
    # If not available, query expansion will gracefully fall back to single query

    try:
        demo_query_expansion_enabled()
    except Exception as e:
        logger.warning(f"Demo 1 failed (LLM might not be available): {e}")

    try:
        demo_query_expansion_disabled()
    except Exception as e:
        logger.warning(f"Demo 2 failed: {e}")

    try:
        demo_performance_comparison()
    except Exception as e:
        logger.warning(f"Demo 3 failed: {e}")

    logger.info("\nDemo complete!")
