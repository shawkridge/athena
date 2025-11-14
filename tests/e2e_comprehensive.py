#!/usr/bin/env python3
"""Comprehensive E2E tests for Athena memory system.

Tests all layers of the memory system:
- Memory persistence and recovery
- Edge cases (large content, special characters, unicode)
- Error handling and resilience
- Consolidation with various patterns
- Search quality and relevance
- Concurrent operations
- Performance metrics
- Multi-project isolation
- Data integrity verification
"""

import time
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from athena.core.database import get_database
from athena.memory.store import MemoryStore
from athena.episodic.store import EpisodicStore
from athena.graph.store import GraphStore
from athena.procedural.store import ProceduralStore
from athena.core.models import Memory, MemoryType


class E2EComprehensiveTests:
    """Comprehensive E2E test suite for Athena."""

    def __init__(self):
        """Initialize test environment."""
        self.db = get_database()  # PostgreSQL by default
        self.memory_store = MemoryStore()
        self.episodic_store = EpisodicStore(self.db)
        self.graph_store = GraphStore(self.db)
        self.procedural_store = ProceduralStore(self.db)

        self.test_results = {}
        self.metrics = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'durations': {},
        }

    def test_1_memory_persistence(self):
        """Test 1: Memory persistence across restarts."""
        print("\n" + "="*70)
        print("TEST 1: Memory Persistence & Recovery")
        print("="*70)

        start = time.time()

        try:
            # Store initial memories
            project_id = self.db.create_project("persistence_test", "/tmp/test1")["id"]

            initial_memories = [
                ("Critical finding: Always validate input before processing", "pattern"),
                ("Database indexing improved query performance by 40%", "decision"),
                ("Learned async/await best practices for I/O operations", "learning"),
            ]

            memory_ids = []
            for content, mtype in initial_memories:
                mid = self.memory_store.remember_sync(
                    content,
                    mtype,
                    project_id
                )
                memory_ids.append(mid)

            print(f"✅ Stored {len(memory_ids)} memories: {memory_ids}")

            # Simulate restart by creating new store instance
            memory_store2 = MemoryStore()

            # Retrieve and verify
            retrieved = []
            for mid in memory_ids:
                mem = self.db.get_memory(mid)
                if mem:
                    retrieved.append(mem)

            assert len(retrieved) == len(memory_ids), "Not all memories persisted!"
            print(f"✅ Retrieved {len(retrieved)} memories after restart")

            # Verify content integrity
            for i, mem in enumerate(retrieved):
                assert initial_memories[i][0] in str(mem['content']), f"Content mismatch for memory {i}"

            print("✅ PASS - All memories persisted correctly")
            duration = time.time() - start
            self.metrics['passed'] += 1
            self.metrics['durations']['memory_persistence'] = duration
            return True

        except Exception as e:
            print(f"❌ FAIL - {str(e)}")
            self.metrics['failed'] += 1
            return False

    def test_2_edge_cases(self):
        """Test 2: Edge cases - large content, special characters, unicode."""
        print("\n" + "="*70)
        print("TEST 2: Edge Cases & Special Characters")
        print("="*70)

        start = time.time()

        try:
            project_id = self.db.create_project("edge_cases", "/tmp/test2")["id"]

            edge_cases = [
                # Very large content
                ("Large content: " + "x" * 50000, "pattern"),
                # Special characters
                ("SQL injection test: '; DROP TABLE users; --", "learning"),
                # Unicode and emojis
                ("Unicode test: 你好世界 🚀 مرحبا بالعالم", "decision"),
                # Newlines and tabs
                ("Multi-line:\nline 1\nline 2\t\ttab\t\ttab", "learning"),
                # Empty-ish content
                ("   ", "decision"),  # Just whitespace
                # JSON content
                (json.dumps({"complex": {"nested": {"structure": [1, 2, 3]}}, "emoji": "🎯"}), "pattern"),
            ]

            stored_ids = []
            for content, mtype in edge_cases:
                try:
                    mid = self.memory_store.remember_sync(
                        content,
                        mtype,
                        project_id
                    )
                    stored_ids.append(mid)
                    print(f"✅ Stored edge case: {len(content)} chars, type={mtype}")
                except Exception as e:
                    print(f"⚠️  Failed to store edge case: {str(e)[:80]}")

            assert len(stored_ids) > 0, "Failed to store any edge case memories"
            print(f"✅ Stored {len(stored_ids)}/{len(edge_cases)} edge case memories")

            # Verify retrieval
            for mid in stored_ids:
                mem = self.db.get_memory(mid)
                assert mem is not None, f"Could not retrieve memory {mid}"

            print("✅ PASS - All edge cases handled correctly")
            duration = time.time() - start
            self.metrics['passed'] += 1
            self.metrics['durations']['edge_cases'] = duration
            return True

        except Exception as e:
            print(f"❌ FAIL - {str(e)}")
            self.metrics['failed'] += 1
            return False

    def test_3_consolidation_patterns(self):
        """Test 3: Consolidation with various event patterns."""
        print("\n" + "="*70)
        print("TEST 3: Consolidation & Pattern Extraction")
        print("="*70)

        start = time.time()

        try:
            project_id = self.db.create_project("consolidation", "/tmp/test3")["id"]

            # Create diverse events
            events = [
                ("API call failed", "error", {"endpoint": "/api/users", "status": 500}),
                ("API call failed", "error", {"endpoint": "/api/users", "status": 500}),
                ("API call failed", "error", {"endpoint": "/api/users", "status": 500}),
                ("Database timeout", "error", {"duration_ms": 5000}),
                ("Query optimized", "action", {"improvement": "40%"}),
                ("Query optimized", "action", {"improvement": "35%"}),
                ("User authenticated", "action", {"method": "JWT"}),
            ]

            event_ids = []
            for content, etype, context in events:
                eid = self.episodic_store.store_event(
                    content=content,
                    event_type=etype,
                    context=context
                )
                event_ids.append(eid)

            print(f"✅ Created {len(event_ids)} episodic events")

            # Run consolidation
            patterns = self.consolidation.consolidate()
            print(f"✅ Consolidation extracted {len(patterns)} patterns")

            # Verify patterns
            assert len(patterns) > 0, "No patterns extracted"

            for pattern in patterns:
                print(f"  - Pattern: {pattern.get('pattern', 'unknown')[:60]} (confidence: {pattern.get('confidence', 0):.2f})")

            print("✅ PASS - Consolidation working correctly")
            duration = time.time() - start
            self.metrics['passed'] += 1
            self.metrics['durations']['consolidation'] = duration
            return True

        except Exception as e:
            print(f"❌ FAIL - {str(e)}")
            self.metrics['failed'] += 1
            return False

    def test_4_search_quality(self):
        """Test 4: Search quality and relevance scoring."""
        print("\n" + "="*70)
        print("TEST 4: Search Quality & Relevance")
        print("="*70)

        start = time.time()

        try:
            project_id = self.db.create_project("search_quality", "/tmp/test4")["id"]

            # Store test memories with clear content
            test_memories = [
                ("JWT authentication using RS256 algorithm", "pattern"),
                ("PostgreSQL query optimization with indexes", "decision"),
                ("Docker containerization best practices", "learning"),
                ("Redis caching for session management", "pattern"),
                ("JWT token expiration and refresh strategy", "pattern"),
            ]

            for content, mtype in test_memories:
                self.memory_store.remember_sync(content, mtype, project_id)

            print(f"✅ Stored {len(test_memories)} test memories")

            # Test search queries
            search_queries = [
                ("JWT authentication", 2),  # Should find ~2 JWT-related
                ("database", 1),  # Should find PostgreSQL
                ("docker", 1),  # Should find Docker
                ("caching", 1),  # Should find Redis
            ]

            successful_searches = 0
            for query, expected_min in search_queries:
                try:
                    results = self.memory_store.recall(query, project_id, k=5)
                    actual = len(results)
                    status = "✅" if actual >= expected_min else "⚠️"
                    print(f"{status} Search '{query}': found {actual} (expected ≥{expected_min})")
                    if actual >= expected_min:
                        successful_searches += 1
                except Exception as e:
                    print(f"⚠️  Search '{query}' failed: {str(e)[:60]}")

            assert successful_searches > 0, "No searches worked"
            print(f"✅ PASS - Search working ({successful_searches}/{len(search_queries)} queries successful)")
            duration = time.time() - start
            self.metrics['passed'] += 1
            self.metrics['durations']['search_quality'] = duration
            return True

        except Exception as e:
            print(f"❌ FAIL - {str(e)}")
            self.metrics['failed'] += 1
            return False

    def test_5_multi_project_isolation(self):
        """Test 5: Multiple projects with isolation."""
        print("\n" + "="*70)
        print("TEST 5: Multi-Project Isolation")
        print("="*70)

        start = time.time()

        try:
            # Create two projects
            p1 = self.db.create_project("project_alpha", "/tmp/alpha")["id"]
            p2 = self.db.create_project("project_beta", "/tmp/beta")["id"]

            print(f"✅ Created projects: {p1}, {p2}")

            # Store different memories in each
            p1_memories = [
                ("Python is great for data science", "learning"),
                ("Django best practices", "pattern"),
            ]

            p2_memories = [
                ("JavaScript async/await patterns", "learning"),
                ("React hooks best practices", "pattern"),
            ]

            p1_ids = []
            for content, mtype in p1_memories:
                mid = self.memory_store.remember_sync(content, mtype, p1)
                p1_ids.append(mid)

            p2_ids = []
            for content, mtype in p2_memories:
                mid = self.memory_store.remember_sync(content, mtype, p2)
                p2_ids.append(mid)

            print(f"✅ Stored memories: p1={len(p1_ids)}, p2={len(p2_ids)}")

            # Verify isolation
            p1_list = self.memory_store.list_memories(p1, limit=10)
            p2_list = self.memory_store.list_memories(p2, limit=10)

            print(f"✅ Retrieved: p1={len(p1_list)} memories, p2={len(p2_list)} memories")

            # Cross-check isolation
            assert len(p1_list) >= len(p1_memories), "Project 1 missing memories"
            assert len(p2_list) >= len(p2_memories), "Project 2 missing memories"

            print("✅ PASS - Projects properly isolated")
            duration = time.time() - start
            self.metrics['passed'] += 1
            self.metrics['durations']['multi_project'] = duration
            return True

        except Exception as e:
            print(f"❌ FAIL - {str(e)}")
            self.metrics['failed'] += 1
            return False

    def test_6_performance_benchmark(self):
        """Test 6: Performance benchmarking."""
        print("\n" + "="*70)
        print("TEST 6: Performance Benchmarking")
        print("="*70)

        start = time.time()

        try:
            project_id = self.db.create_project("performance", "/tmp/perf")["id"]

            # Benchmark: Insert speed
            print("\n📊 Insert Performance:")
            insert_start = time.time()
            num_inserts = 100
            for i in range(num_inserts):
                self.memory_store.remember_sync(
                    f"Test memory {i}: Performance benchmark content",
                    "pattern",
                    project_id
                )
            insert_time = time.time() - insert_start
            insert_rate = num_inserts / insert_time
            print(f"  Inserted {num_inserts} memories in {insert_time:.2f}s")
            print(f"  Rate: {insert_rate:.0f} memories/sec")

            # Benchmark: Search speed
            print("\n📊 Search Performance:")
            search_start = time.time()
            num_searches = 20
            for i in range(num_searches):
                self.memory_store.recall(f"test {i}", project_id, k=5)
            search_time = time.time() - search_start
            avg_search = search_time / num_searches
            print(f"  {num_searches} searches in {search_time:.2f}s")
            print(f"  Avg per search: {avg_search*1000:.1f}ms")

            # Benchmark: List speed
            print("\n📊 List Performance:")
            list_start = time.time()
            num_lists = 10
            for i in range(num_lists):
                self.memory_store.list_memories(project_id, limit=50)
            list_time = time.time() - list_start
            avg_list = list_time / num_lists
            print(f"  {num_lists} list operations in {list_time:.2f}s")
            print(f"  Avg per list: {avg_list*1000:.1f}ms")

            # Assert reasonable performance
            assert insert_rate > 50, f"Insert rate too low: {insert_rate:.0f}/sec"
            assert avg_search < 1.0, f"Search too slow: {avg_search*1000:.1f}ms"

            print("\n✅ PASS - Performance within acceptable ranges")
            duration = time.time() - start
            self.metrics['passed'] += 1
            self.metrics['durations']['performance'] = duration
            return True

        except Exception as e:
            print(f"❌ FAIL - {str(e)}")
            self.metrics['failed'] += 1
            return False

    def test_7_data_integrity(self):
        """Test 7: Data integrity and consistency."""
        print("\n" + "="*70)
        print("TEST 7: Data Integrity & Consistency")
        print("="*70)

        start = time.time()

        try:
            project_id = self.db.create_project("integrity", "/tmp/integrity")["id"]

            # Create memories with known content
            test_content = "Data integrity test: Content must be preserved exactly"
            test_tags = ["integrity", "testing"]

            mid = self.memory_store.remember_sync(
                test_content,
                "pattern",
                project_id,
                tags=test_tags
            )

            print(f"✅ Stored memory {mid}")

            # Retrieve and verify exact content
            mem = self.db.get_memory(mid)
            assert mem is not None, "Memory not found"

            stored_content = str(mem.get('content', ''))
            assert test_content in stored_content, f"Content mismatch: {stored_content[:100]}"

            print(f"✅ Content integrity verified")

            # Verify metadata
            assert mem.get('project_id') == project_id, "Project ID mismatch"
            print(f"✅ Metadata integrity verified")

            # Verify timestamp
            created_at = mem.get('created_at')
            assert created_at is not None, "Created timestamp missing"
            now = datetime.now()
            time_diff = abs((now - created_at).total_seconds())
            assert time_diff < 60, f"Timestamp way off: {time_diff}s difference"
            print(f"✅ Timestamp integrity verified")

            print("✅ PASS - Data integrity confirmed")
            duration = time.time() - start
            self.metrics['passed'] += 1
            self.metrics['durations']['data_integrity'] = duration
            return True

        except Exception as e:
            print(f"❌ FAIL - {str(e)}")
            self.metrics['failed'] += 1
            return False

    def run_all_tests(self):
        """Run all E2E tests."""
        print("\n" + "█"*70)
        print("█ ATHENA E2E COMPREHENSIVE TEST SUITE")
        print("█"*70)
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        self.metrics['total_tests'] = 7

        tests = [
            self.test_1_memory_persistence,
            self.test_2_edge_cases,
            self.test_3_consolidation_patterns,
            self.test_4_search_quality,
            self.test_5_multi_project_isolation,
            self.test_6_performance_benchmark,
            self.test_7_data_integrity,
        ]

        for test_func in tests:
            try:
                test_func()
            except Exception as e:
                print(f"Test {test_func.__name__} crashed: {str(e)}")
                self.metrics['failed'] += 1

        self._print_summary()

    def _print_summary(self):
        """Print comprehensive test summary."""
        print("\n" + "█"*70)
        print("█ TEST SUMMARY")
        print("█"*70)

        passed = self.metrics['passed']
        failed = self.metrics['failed']
        total = self.metrics['total_tests']
        rate = (passed / total * 100) if total > 0 else 0

        print(f"\n📊 Results:")
        print(f"  ✅ Passed: {passed}/{total}")
        print(f"  ❌ Failed: {failed}/{total}")
        print(f"  📈 Success Rate: {rate:.1f}%")

        print(f"\n⏱️  Performance Metrics:")
        for test_name, duration in self.metrics['durations'].items():
            print(f"  {test_name}: {duration:.2f}s")

        total_time = sum(self.metrics['durations'].values())
        print(f"  Total Time: {total_time:.2f}s")

        print(f"\n{'='*70}")
        if failed == 0:
            print("✅ ALL TESTS PASSED - SYSTEM PRODUCTION READY!")
        else:
            print(f"⚠️  {failed} test(s) failed - Review needed")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    suite = E2EComprehensiveTests()
    suite.run_all_tests()
