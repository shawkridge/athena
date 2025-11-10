#!/usr/bin/env python3
"""Example: Using PostgreSQL Connection Pool Optimizations

This example demonstrates the new features from Airweave integration:
1. Dynamic pool sizing
2. Pool monitoring
3. Health checks
4. Configuration best practices
"""

import asyncio
import os
from athena.core.database_postgres import PostgresDatabase


async def example_1_basic_configuration():
    """Example 1: Basic configuration with defaults."""
    print("\n" + "="*80)
    print("Example 1: Basic Configuration")
    print("="*80)

    # Create database with default settings
    db = PostgresDatabase(
        host="localhost",
        port=5432,
        dbname="athena",
        user="athena",
        password="athena_dev",
    )

    print(f"Pool configured:")
    print(f"  - min_size: {db.min_size}")
    print(f"  - max_size: {db.max_size}")
    print(f"  - pool_timeout: {db.pool_timeout}s")
    print(f"  - max_idle: {db.max_idle}s")
    print(f"  - max_lifetime: {db.max_lifetime}s")


async def example_2_dynamic_scaling():
    """Example 2: Dynamic pool scaling based on worker count."""
    print("\n" + "="*80)
    print("Example 2: Dynamic Pool Scaling")
    print("="*80)

    # Get worker count from environment (or default to 10)
    worker_count = int(os.environ.get('WORKER_COUNT', 10))

    # Create database with dynamic pool sizing
    db = PostgresDatabase(
        host="localhost",
        port=5432,
        dbname="athena",
        user="athena",
        password="athena_dev",
        worker_count=worker_count,  # Enable auto-scaling
    )

    print(f"Dynamic pool for {worker_count} workers:")
    print(f"  - min_size: {db.min_size} (auto-calculated)")
    print(f"  - max_size: {db.max_size} (auto-calculated)")

    # Show scaling for different worker counts
    print("\nScaling examples:")
    for workers in [10, 50, 100, 200]:
        test_db = PostgresDatabase(host="localhost", worker_count=workers)
        print(f"  - {workers:3d} workers → min={test_db.min_size}, max={test_db.max_size}")


async def example_3_pool_monitoring():
    """Example 3: Pool monitoring and statistics."""
    print("\n" + "="*80)
    print("Example 3: Pool Monitoring")
    print("="*80)

    db = PostgresDatabase(
        host="localhost",
        port=5432,
        dbname="athena",
        user="athena",
        password="athena_dev",
    )

    # Initialize pool
    await db.initialize()

    # Get pool statistics
    pool_stats = await db.get_pool_stats()
    print(f"\nPool statistics:")
    print(f"  - status: {pool_stats['status']}")
    print(f"  - total_connections: {pool_stats['total_connections']}")
    print(f"  - available_connections: {pool_stats['available_connections']}")
    print(f"  - pool_utilization: {pool_stats['pool_utilization']*100:.1f}%")

    # Get connection statistics
    conn_stats = await db.get_connection_stats()
    print(f"\nConnection statistics:")
    print(f"  - total_connections: {conn_stats['total_connections']}")
    print(f"  - active_queries: {conn_stats['active_queries']}")
    print(f"  - idle_connections: {conn_stats['idle_connections']}")

    await db.close()


async def example_4_health_check():
    """Example 4: Comprehensive health check."""
    print("\n" + "="*80)
    print("Example 4: Health Check")
    print("="*80)

    db = PostgresDatabase(
        host="localhost",
        port=5432,
        dbname="athena",
        user="athena",
        password="athena_dev",
    )

    await db.initialize()

    # Perform health check
    health = await db.health_check()
    print(f"\nHealth check results:")
    print(f"  - overall_status: {health['status']}")
    print(f"  - pool_status: {health['pool']['status']}")
    print(f"  - database_connected: {health['database']['connected']}")
    print(f"  - query_latency: {health['database']['query_latency_ms']:.2f}ms")

    if 'warnings' in health:
        print(f"\nWarnings:")
        for warning in health['warnings']:
            print(f"  - {warning}")

    await db.close()


async def example_5_production_monitoring():
    """Example 5: Production monitoring pattern."""
    print("\n" + "="*80)
    print("Example 5: Production Monitoring Pattern")
    print("="*80)

    db = PostgresDatabase(
        host="localhost",
        port=5432,
        dbname="athena",
        user="athena",
        password="athena_dev",
        worker_count=int(os.environ.get('WORKER_COUNT', 10)),
    )

    await db.initialize()

    async def monitor_health():
        """Background task to monitor pool health."""
        while True:
            health = await db.health_check()

            # Check for issues
            if health['status'] != 'healthy':
                print(f"⚠ ALERT: Database unhealthy - {health}")

            # Check pool utilization
            pool_util = health['pool'].get('pool_utilization', 0)
            if pool_util > 0.8:
                print(f"⚠ WARNING: High pool utilization ({pool_util*100:.0f}%)")

            # Check query latency
            latency = health['database'].get('query_latency_ms', 0)
            if latency > 100:
                print(f"⚠ WARNING: High query latency ({latency:.0f}ms)")

            # Wait before next check
            await asyncio.sleep(60)

    print("\nStarting health monitoring (60s interval)...")
    print("Press Ctrl+C to stop\n")

    # Run monitoring for 3 minutes as demo
    try:
        await asyncio.wait_for(monitor_health(), timeout=180)
    except asyncio.TimeoutError:
        print("\nMonitoring demo completed (3 minutes)")

    await db.close()


async def example_6_index_monitoring():
    """Example 6: Index usage monitoring."""
    print("\n" + "="*80)
    print("Example 6: Index Usage Monitoring")
    print("="*80)

    db = PostgresDatabase(
        host="localhost",
        port=5432,
        dbname="athena",
        user="athena",
        password="athena_dev",
    )

    await db.initialize()

    # Get index statistics
    index_stats = await db.get_index_stats()

    print(f"\nFound {len(index_stats)} indices")
    print("\nTop 5 most-used indices:")
    for stat in index_stats[:5]:
        print(f"\n  {stat['index']} on {stat['table']}")
        print(f"    - scans: {stat['scans']:,}")
        print(f"    - efficiency: {stat['efficiency']*100:.1f}%")

    await db.close()


async def main():
    """Run all examples."""
    print("\n" + "="*80)
    print("PostgreSQL Connection Pool Optimization Examples")
    print("Based on Airweave Integration Patterns")
    print("="*80)

    # Example 1: Basic configuration
    await example_1_basic_configuration()

    # Example 2: Dynamic scaling
    await example_2_dynamic_scaling()

    # Note: Examples 3-6 require PostgreSQL to be running
    try:
        await example_3_pool_monitoring()
        await example_4_health_check()
        await example_6_index_monitoring()
        # await example_5_production_monitoring()  # Uncomment to run monitoring demo
    except Exception as e:
        print(f"\n⚠ Skipping runtime examples (PostgreSQL not available): {e}")
        print("\nTo run full examples:")
        print("  1. Start PostgreSQL: docker-compose up -d postgres")
        print("  2. Wait for initialization: sleep 10")
        print("  3. Re-run this script")

    print("\n" + "="*80)
    print("Examples completed!")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
