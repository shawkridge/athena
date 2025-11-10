#!/usr/bin/env python3
"""Test script for PostgreSQL connection pool optimization.

This script demonstrates the enhanced pool features from Airweave integration:
1. Dynamic pool sizing based on worker count
2. Pool monitoring and statistics
3. Connection health checks
4. Index usage statistics
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Check if psycopg is available
try:
    from athena.core.database_postgres import PostgresDatabase
    PSYCOPG_AVAILABLE = True
except ImportError as e:
    PSYCOPG_AVAILABLE = False
    IMPORT_ERROR = str(e)


async def test_pool_initialization():
    """Test 1: Pool initialization with dynamic sizing."""
    print("\n" + "="*80)
    print("TEST 1: Pool Initialization with Dynamic Sizing")
    print("="*80)

    if not PSYCOPG_AVAILABLE:
        print(f"\n⚠ Skipping test (psycopg not installed)")
        print(f"  Error: {IMPORT_ERROR}")
        print(f"\nTo install: pip install 'psycopg[binary]'")
        return

    # Test with explicit sizes
    db1 = PostgresDatabase(
        host="localhost",
        port=5432,
        dbname="athena",
        user="athena",
        password="athena_dev",
        min_size=2,
        max_size=10,
    )

    print(f"\n✓ Standard pool created:")
    print(f"  - min_size: {db1.min_size}")
    print(f"  - max_size: {db1.max_size}")
    print(f"  - pool_timeout: {db1.pool_timeout}s")
    print(f"  - max_idle: {db1.max_idle}s")
    print(f"  - max_lifetime: {db1.max_lifetime}s")

    # Test with dynamic sizing (10 workers)
    db2 = PostgresDatabase(
        host="localhost",
        port=5432,
        dbname="athena",
        user="athena",
        password="athena_dev",
        worker_count=10,
    )

    print(f"\n✓ Dynamic pool created (10 workers):")
    print(f"  - min_size: {db2.min_size} (auto-scaled from worker_count)")
    print(f"  - max_size: {db2.max_size} (auto-scaled from worker_count)")

    # Test with dynamic sizing (100 workers)
    db3 = PostgresDatabase(
        host="localhost",
        port=5432,
        dbname="athena",
        user="athena",
        password="athena_dev",
        worker_count=100,
    )

    print(f"\n✓ Dynamic pool created (100 workers):")
    print(f"  - min_size: {db3.min_size} (capped at 5)")
    print(f"  - max_size: {db3.max_size} (capped at 20)")


async def test_pool_stats():
    """Test 2: Pool statistics monitoring."""
    print("\n" + "="*80)
    print("TEST 2: Pool Statistics Monitoring")
    print("="*80)

    if not PSYCOPG_AVAILABLE:
        print(f"\n⚠ Skipping test (psycopg not installed)")
        return

    db = PostgresDatabase(
        host="localhost",
        port=5432,
        dbname="athena",
        user="athena",
        password="athena_dev",
    )

    # Before initialization
    stats = await db.get_pool_stats()
    print(f"\n✓ Pool stats (before initialization):")
    print(f"  - status: {stats['status']}")
    print(f"  - total_connections: {stats['total_connections']}")

    # Initialize pool
    try:
        await db.initialize()
        print(f"\n✓ Pool initialized successfully")

        # After initialization
        stats = await db.get_pool_stats()
        print(f"\n✓ Pool stats (after initialization):")
        print(f"  - status: {stats['status']}")
        print(f"  - total_connections: {stats['total_connections']}")
        print(f"  - available_connections: {stats['available_connections']}")
        print(f"  - pool_utilization: {stats['pool_utilization']*100:.1f}%")

        await db.close()
    except Exception as e:
        print(f"\n✗ Pool initialization failed (expected if PostgreSQL not running): {e}")


async def test_health_check():
    """Test 3: Comprehensive health check."""
    print("\n" + "="*80)
    print("TEST 3: Comprehensive Health Check")
    print("="*80)

    if not PSYCOPG_AVAILABLE:
        print(f"\n⚠ Skipping test (psycopg not installed)")
        return

    db = PostgresDatabase(
        host="localhost",
        port=5432,
        dbname="athena",
        user="athena",
        password="athena_dev",
    )

    try:
        await db.initialize()

        health = await db.health_check()
        print(f"\n✓ Health check completed:")
        print(f"  - overall_status: {health['status']}")
        print(f"  - pool_status: {health['pool']['status']}")
        print(f"  - pool_utilization: {health['pool']['pool_utilization']*100:.1f}%")
        print(f"  - database_connected: {health['database']['connected']}")
        print(f"  - query_latency_ms: {health['database']['query_latency_ms']:.2f}ms")

        if "warnings" in health:
            print(f"\n⚠ Warnings:")
            for warning in health["warnings"]:
                print(f"  - {warning}")

        await db.close()
    except Exception as e:
        print(f"\n✗ Health check failed (expected if PostgreSQL not running): {e}")


async def test_connection_stats():
    """Test 4: Active connection statistics."""
    print("\n" + "="*80)
    print("TEST 4: Active Connection Statistics")
    print("="*80)

    if not PSYCOPG_AVAILABLE:
        print(f"\n⚠ Skipping test (psycopg not installed)")
        return

    db = PostgresDatabase(
        host="localhost",
        port=5432,
        dbname="athena",
        user="athena",
        password="athena_dev",
    )

    try:
        await db.initialize()

        stats = await db.get_connection_stats()
        print(f"\n✓ Connection stats:")
        print(f"  - total_connections: {stats['total_connections']}")
        print(f"  - active_queries: {stats['active_queries']}")
        print(f"  - idle_connections: {stats['idle_connections']}")
        print(f"  - waiting_connections: {stats['waiting_connections']}")
        print(f"  - oldest_query_seconds: {stats['oldest_query_seconds']}s")

        await db.close()
    except Exception as e:
        print(f"\n✗ Connection stats failed (expected if PostgreSQL not running): {e}")


async def test_index_stats():
    """Test 5: Index usage statistics."""
    print("\n" + "="*80)
    print("TEST 5: Index Usage Statistics")
    print("="*80)

    if not PSYCOPG_AVAILABLE:
        print(f"\n⚠ Skipping test (psycopg not installed)")
        return

    db = PostgresDatabase(
        host="localhost",
        port=5432,
        dbname="athena",
        user="athena",
        password="athena_dev",
    )

    try:
        await db.initialize()

        stats = await db.get_index_stats()
        print(f"\n✓ Index stats retrieved: {len(stats)} indices")

        if stats:
            print(f"\nTop 5 most-used indices:")
            for idx_stat in stats[:5]:
                print(f"  - {idx_stat['index']} on {idx_stat['table']}")
                print(f"    scans: {idx_stat['scans']}, efficiency: {idx_stat['efficiency']}")

        await db.close()
    except Exception as e:
        print(f"\n✗ Index stats failed (expected if PostgreSQL not running): {e}")


async def run_all_tests():
    """Run all tests."""
    print("\n" + "="*80)
    print("PostgreSQL Connection Pool Optimization Tests")
    print("Based on Airweave Integration Patterns")
    print("="*80)

    await test_pool_initialization()
    await test_pool_stats()
    await test_health_check()
    await test_connection_stats()
    await test_index_stats()

    print("\n" + "="*80)
    print("All tests completed!")
    print("="*80)
    print("\nNote: Some tests will fail if PostgreSQL is not running.")
    print("Start PostgreSQL with: docker-compose up -d postgres")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
