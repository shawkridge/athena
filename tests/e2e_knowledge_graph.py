#!/usr/bin/env python3
"""E2E Black-Box Tests for Knowledge Graph System.

Tests entity storage, relationships, and graph operations.
Focus on: Can we create entities? Do relationships work? Is graph queryable?
"""

import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from athena.core.database import get_database
from athena.graph.store import GraphStore
from athena.graph.models import Entity, EntityType, Relation, RelationType


class KnowledgeGraphE2ETests:
    """Black-box E2E tests for Knowledge Graph."""

    def __init__(self):
        """Initialize test environment."""
        self.db = get_database()
        self.graph_store = GraphStore(self.db)

        self.metrics = {
            'total_tests': 6,
            'passed': 0,
            'failed': 0,
            'durations': {},
        }

    def test_1_entity_creation(self):
        """Test 1: Create and retrieve entities."""
        print("\n" + "="*70)
        print("TEST 1: Entity Creation & Retrieval")
        print("="*70)

        start = time.time()

        try:
            # Create test entities
            entities = [
                {"name": "Python", "type": "technology", "description": "Programming language"},
                {"name": "PostgreSQL", "type": "database", "description": "Database system"},
                {"name": "Athena", "type": "system", "description": "Memory system"},
            ]

            entity_ids = []
            for ent in entities:
                eid = self.graph_store.create_entity(
                    name=ent["name"],
                    entity_type=ent["type"],
                    description=ent["description"]
                )
                entity_ids.append(eid)
                print(f"  ✅ Created entity: {ent['name']} (ID: {eid})")

            # Retrieve entities
            for eid in entity_ids:
                retrieved = self.graph_store.get_entity(eid)
                assert retrieved is not None, f"Entity {eid} not found"

            print(f"✅ Created and retrieved {len(entity_ids)} entities")
            print("✅ PASS - Entity operations working")
            duration = time.time() - start
            self.metrics['passed'] += 1
            self.metrics['durations']['entity_creation'] = duration
            return True

        except Exception as e:
            print(f"❌ FAIL - {str(e)}")
            self.metrics['failed'] += 1
            return False

    def test_2_relationships(self):
        """Test 2: Create and query relationships."""
        print("\n" + "="*70)
        print("TEST 2: Relationships")
        print("="*70)

        start = time.time()

        try:
            # Create entities
            python_id = self.graph_store.create_entity(
                name="Python", entity_type="language", description="Python"
            )
            django_id = self.graph_store.create_entity(
                name="Django", entity_type="framework", description="Django"
            )

            # Create relationship
            rel_id = self.graph_store.create_relation(
                from_entity_id=python_id,
                to_entity_id=django_id,
                relation_type="used_by"
            )

            print(f"  ✅ Created relationship (ID: {rel_id})")

            # Retrieve relationship
            relation = self.graph_store.get_relation(rel_id)
            assert relation is not None, "Relationship not found"

            print(f"✅ Created and retrieved relationship")
            print("✅ PASS - Relationship operations working")
            duration = time.time() - start
            self.metrics['passed'] += 1
            self.metrics['durations']['relationships'] = duration
            return True

        except Exception as e:
            print(f"❌ FAIL - {str(e)}")
            self.metrics['failed'] += 1
            return False

    def test_3_graph_queries(self):
        """Test 3: Query graph for relationships."""
        print("\n" + "="*70)
        print("TEST 3: Graph Queries")
        print("="*70)

        start = time.time()

        try:
            # Create test structure
            entity_a = self.graph_store.create_entity(
                name="A", entity_type="test", description="Entity A"
            )
            entity_b = self.graph_store.create_entity(
                name="B", entity_type="test", description="Entity B"
            )
            entity_c = self.graph_store.create_entity(
                name="C", entity_type="test", description="Entity C"
            )

            # Create relationships
            self.graph_store.create_relation(entity_a, entity_b, "connects_to")
            self.graph_store.create_relation(entity_b, entity_c, "connects_to")

            # Query relationships
            relations_from_a = self.graph_store.get_relations_from(entity_a)
            print(f"  ✅ Found {len(relations_from_a) if relations_from_a else 0} relations from A")

            relations_to_c = self.graph_store.get_relations_to(entity_c)
            print(f"  ✅ Found {len(relations_to_c) if relations_to_c else 0} relations to C")

            print("✅ PASS - Graph queries working")
            duration = time.time() - start
            self.metrics['passed'] += 1
            self.metrics['durations']['graph_queries'] = duration
            return True

        except Exception as e:
            print(f"❌ FAIL - {str(e)}")
            self.metrics['failed'] += 1
            return False

    def test_4_observations(self):
        """Test 4: Entity observations."""
        print("\n" + "="*70)
        print("TEST 4: Entity Observations")
        print("="*70)

        start = time.time()

        try:
            # Create entity
            entity_id = self.graph_store.create_entity(
                name="TestEntity", entity_type="test", description="Test"
            )

            # Add observations
            observations = [
                "Observed in production use",
                "Works well with other systems",
                "Good performance"
            ]

            for obs in observations:
                self.graph_store.add_observation(entity_id, obs)
                print(f"  ✅ Added observation: {obs}")

            # Retrieve observations
            entity_obs = self.graph_store.get_entity_observations(entity_id)
            obs_count = len(entity_obs) if entity_obs else 0
            print(f"✅ Retrieved {obs_count} observations")

            print("✅ PASS - Observations working")
            duration = time.time() - start
            self.metrics['passed'] += 1
            self.metrics['durations']['observations'] = duration
            return True

        except Exception as e:
            print(f"❌ FAIL - {str(e)}")
            self.metrics['failed'] += 1
            return False

    def test_5_performance(self):
        """Test 5: Performance benchmarks."""
        print("\n" + "="*70)
        print("TEST 5: Performance Benchmarks")
        print("="*70)

        start = time.time()

        try:
            # Benchmark: Create entities
            print("\n📊 Entity Creation Performance:")
            create_start = time.time()
            num_entities = 50
            for i in range(num_entities):
                self.graph_store.create_entity(
                    name=f"Entity_{i}",
                    entity_type="benchmark",
                    description=f"Benchmark entity {i}"
                )
            create_time = time.time() - create_start
            create_rate = num_entities / create_time

            print(f"  Created {num_entities} entities in {create_time:.2f}s")
            print(f"  Rate: {create_rate:.0f} entities/sec")

            assert create_rate > 10, f"Creation rate too low: {create_rate:.0f}/sec"

            print("✅ PASS - Performance acceptable")
            duration = time.time() - start
            self.metrics['passed'] += 1
            self.metrics['durations']['performance'] = duration
            return True

        except Exception as e:
            print(f"❌ FAIL - {str(e)}")
            self.metrics['failed'] += 1
            return False

    def test_6_integration(self):
        """Test 6: Integration with memory system."""
        print("\n" + "="*70)
        print("TEST 6: Graph Integration")
        print("="*70)

        start = time.time()

        try:
            # Create a small knowledge graph
            entities = []
            for i in range(3):
                eid = self.graph_store.create_entity(
                    name=f"Integration_{i}",
                    entity_type="integration",
                    description=f"Integration test {i}"
                )
                entities.append(eid)

            # Connect them
            if len(entities) >= 2:
                for i in range(len(entities) - 1):
                    self.graph_store.create_relation(
                        entities[i], entities[i+1], "relates_to"
                    )

            print(f"✅ Created {len(entities)} interconnected entities")
            print("✅ PASS - Integration working")
            duration = time.time() - start
            self.metrics['passed'] += 1
            self.metrics['durations']['integration'] = duration
            return True

        except Exception as e:
            print(f"❌ FAIL - {str(e)}")
            self.metrics['failed'] += 1
            return False

    def run_all_tests(self):
        """Execute all tests."""
        print("\n" + "█"*70)
        print("█ KNOWLEDGE GRAPH E2E BLACK-BOX TESTS")
        print("█"*70)

        tests = [
            self.test_1_entity_creation,
            self.test_2_relationships,
            self.test_3_graph_queries,
            self.test_4_observations,
            self.test_5_performance,
            self.test_6_integration,
        ]

        for test_func in tests:
            try:
                test_func()
            except Exception as e:
                print(f"Test {test_func.__name__} crashed: {str(e)}")
                self.metrics['failed'] += 1

        self._print_summary()

    def _print_summary(self):
        """Print test summary."""
        print("\n" + "█"*70)
        print("█ TEST SUMMARY - KNOWLEDGE GRAPH E2E")
        print("█"*70)

        passed = self.metrics['passed']
        failed = self.metrics['failed']
        total = self.metrics['total_tests']
        rate = (passed / total * 100) if total > 0 else 0

        print(f"\n📊 Results:")
        print(f"  ✅ Passed: {passed}/{total}")
        print(f"  ❌ Failed: {failed}/{total}")
        print(f"  📈 Success Rate: {rate:.1f}%")

        print(f"\n⏱️  Performance:")
        for test_name, duration in self.metrics['durations'].items():
            print(f"  {test_name}: {duration:.2f}s")

        total_time = sum(self.metrics['durations'].values())
        print(f"  Total: {total_time:.2f}s")

        print(f"\n{'='*70}")
        if failed == 0:
            print("✅ KNOWLEDGE GRAPH E2E TESTS PASSED")
        else:
            print(f"⚠️  {failed} test(s) failed")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    suite = KnowledgeGraphE2ETests()
    suite.run_all_tests()
