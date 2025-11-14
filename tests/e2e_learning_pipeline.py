"""End-to-End Evaluation of Complete Learning Pipeline.

This script validates the entire learning system:
1. Event capture (episodic events)
2. Consolidation (pattern extraction)
3. Semantic memory persistence (memory_vectors table)
4. Procedure extraction (procedures table)
5. Search with relevance ranking
6. Full round-trip verification

Run with: python tests/e2e_learning_pipeline.py
"""

import sys
import os
from datetime import datetime, timedelta
import time
import uuid

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from athena.core.database import get_database, reset_database
from athena.episodic.store import EpisodicStore
from athena.memory.store import MemoryStore
from athena.procedural.store import ProceduralStore


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def print_result(test_name: str, passed: bool, details: str = ""):
    """Print test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"       {details}")


class E2EEvaluation:
    """End-to-end evaluation harness."""

    def __init__(self):
        self.db = None
        self.episodic_store = None
        self.memory_store = None
        self.procedural_store = None
        self.project = None
        self.results = []
        self.session_id = "session_001"  # Track the session we use for events

    def setup(self):
        """Initialize test environment."""
        print_section("SETUP: Initializing Test Environment")

        try:
            # Reset singleton for clean state
            reset_database()

            # Get database
            self.db = get_database(
                dbname="athena_test",
                host="localhost",
                port=5432,
                user="postgres",
                password="postgres"
            )

            print(f"✅ Database initialized")

            # Create project with unique name and path using UUID
            project_uuid = uuid.uuid4().hex[:8]
            project_name = f"e2e_eval_{project_uuid}"
            project_path = f"/e2e/test/project/{project_uuid}"
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                INSERT INTO projects (name, path)
                VALUES (%s, %s)
                RETURNING id, name, path
                """,
                (project_name, project_path)
            )

            try:
                result = cursor.fetchone()
            except Exception as e:
                print(f"DEBUG: fetchone() failed: {e}")
                result = None

            if result:
                from athena.core.models import Project
                # Result is now a dict due to dict_row factory
                if isinstance(result, dict):
                    self.project = Project(
                        id=result['id'],
                        name=result['name'],
                        path=result['path']
                    )
                else:
                    # Fallback for tuple access
                    self.project = Project(
                        id=result[0],
                        name=result[1],
                        path=result[2]
                    )
                print(f"✅ Project created: {self.project.name} (ID: {self.project.id})")
            else:
                raise Exception(f"Failed to create project")

            # Initialize stores
            self.episodic_store = EpisodicStore(self.db)
            self.memory_store = MemoryStore()
            self.procedural_store = ProceduralStore(self.db)

            print(f"✅ All stores initialized")
            return True

        except Exception as e:
            print(f"❌ Setup failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _consolidate_events_to_memories(self):
        """Run consolidation hook to convert events to memories (simulates background consolidation)."""
        try:
            # Set database environment variables to point to test database
            import os
            os.environ["ATHENA_POSTGRES_DB"] = "athena_test"
            os.environ["ATHENA_POSTGRES_HOST"] = "localhost"
            os.environ["ATHENA_POSTGRES_PORT"] = "5432"
            os.environ["ATHENA_POSTGRES_USER"] = "postgres"
            os.environ["ATHENA_POSTGRES_PASSWORD"] = "postgres"

            # Import the consolidation helper that hooks use
            import sys
            sys.path.insert(0, os.path.expanduser('~/.claude/hooks/lib'))

            from consolidation_helper import ConsolidationHelper

            # Create consolidation helper and run consolidation
            # This simulates what the session-end hook would do
            consolidation = ConsolidationHelper()
            result = consolidation.consolidate_session(
                project_id=self.project.id,
                session_id=self.session_id  # Consolidate the session we stored events in
            )

            # Result should include created memories and procedures
            print(f"  DEBUG: Consolidation result: {result}")
            if result and result.get("status") == "success":
                print(f"  Consolidation completed: {result.get('summary', '')}")
            elif result:
                print(f"  Consolidation status: {result.get('status')}, Error: {result.get('error')}")

        except Exception as e:
            import logging
            import traceback
            logging.warning(f"Failed to consolidate events: {e}")
            traceback.print_exc()

    def test_and_consolidate(self):
        """Test 1: Episodic event capture."""
        print_section("TEST 1: Event Capture (Episodic Memory)")

        try:
            # Create test events using valid EventTypes
            events = [
                {
                    "content": "Analyzed database schema for performance issues",
                    "event_type": "debugging",  # Changed from 'analysis' to valid EventType
                    "session_id": "session_001",
                    "context_cwd": "/project/src",
                },
                {
                    "content": "Fixed N+1 query by adding index on user_id",
                    "event_type": "file_change",  # Changed from 'code_change' to valid EventType
                    "session_id": "session_001",
                    "context_cwd": "/project/src",
                },
                {
                    "content": "Discovered memory leak in websocket handler",
                    "event_type": "error",  # Changed from 'discovery' to valid EventType
                    "session_id": "session_001",
                    "context_cwd": "/project/src",
                },
            ]

            event_ids = []
            for event in events:
                event_id = self.episodic_store.store_event(
                    project_id=self.project.id,
                    content=event["content"],
                    event_type=event["event_type"],
                    session_id=event["session_id"],
                    outcome="success",
                    context_cwd=event["context_cwd"]
                )
                event_ids.append(event_id)

            # Verify events were stored
            stored_events = self.episodic_store.list_events(
                project_id=self.project.id,
                limit=10
            )

            passed = len(stored_events) >= 3
            print_result(
                "Store 3 episodic events",
                passed,
                f"Stored {len(stored_events)} events (IDs: {event_ids})"
            )

            self.results.append(("Event Capture", passed))
            return passed

        except Exception as e:
            print_result("Store episodic events", False, str(e))
            self.results.append(("Event Capture", False))
            return False

    def test_semantic_memories(self):
        """Test 2: Semantic memory creation and storage."""
        print_section("TEST 2: Semantic Memory Persistence")

        try:
            # Use MemoryStore to list memories (public API, not SQL)
            memories = self.memory_store.list_memories(
                self.project.id,
                limit=10
            )

            passed = len(memories) > 0
            print_result(
                "Semantic memories created and stored",
                passed,
                f"Found {len(memories)} memories"
            )

            if memories:
                for i, mem in enumerate(memories[:3]):  # Show first 3
                    print(f"  Memory {i+1}: type={mem.memory_type}, tags={mem.tags}")
                    if mem.content:
                        print(f"             Content: {str(mem.content)[:60]}...")

            self.results.append(("Semantic Memory", passed))
            return passed

        except Exception as e:
            print_result("Semantic memories", False, str(e))
            import traceback
            traceback.print_exc()
            self.results.append(("Semantic Memory", False))
            return False

    def test_procedure_extraction(self):
        """Test 3: Procedure extraction and storage."""
        print_section("TEST 3: Procedure Extraction")

        try:
            # Use ProceduralStore to list procedures (public API, not SQL)
            procedures = self.procedural_store.list_procedures(
                limit=100
            )

            # Filter for procedures created by consolidation
            consolidation_procs = [p for p in procedures if p.created_by == "consolidation"]

            passed = len(consolidation_procs) > 0
            print_result(
                "Procedures extracted and stored",
                passed,
                f"Found {len(consolidation_procs)} procedures created by consolidation"
            )

            if consolidation_procs:
                for i, proc in enumerate(consolidation_procs[:3]):  # Show first 3
                    print(f"  Procedure {i+1}: name={proc.name}, category={proc.category}")
                    if proc.description:
                        print(f"               Description: {proc.description[:60]}...")

            self.results.append(("Procedure Extraction", passed))
            return passed

        except Exception as e:
            print_result("Procedure extraction", False, str(e))
            import traceback
            traceback.print_exc()
            self.results.append(("Procedure Extraction", False))
            return False

    def test_search_ranking(self):
        """Test 4: Search with relevance ranking."""
        print_section("TEST 4: Search Ranking (Relevance Scoring)")

        try:
            # Use MemoryStore.recall_with_reranking to search with relevance ranking
            # This tests the public search API, not raw SQL
            search_results = self.memory_store.recall_with_reranking(
                query="database query optimization",
                project_id=self.project.id,
                k=5
            )

            passed = len(search_results) > 0
            print_result(
                "Search with relevance ranking",
                passed,
                f"Found {len(search_results)} results"
            )

            if search_results:
                for i, result in enumerate(search_results[:3]):
                    # result should be a tuple of (memory, score) or a Memory object
                    if isinstance(result, tuple):
                        mem, score = result
                        print(f"  Result {i+1}: relevance={score:.2f}")
                        if mem.content:
                            print(f"           Content: {str(mem.content)[:60]}...")
                    else:
                        # If it's just a memory object
                        print(f"  Result {i+1}: type={result.memory_type}")
                        if result.content:
                            print(f"           Content: {str(result.content)[:60]}...")

            self.results.append(("Search Ranking", passed))
            return passed

        except Exception as e:
            print_result("Search ranking", False, str(e))
            import traceback
            traceback.print_exc()
            self.results.append(("Search Ranking", False))
            return False

    def test_end_to_end_flow(self):
        """Test 5: Complete end-to-end flow."""
        print_section("TEST 5: End-to-End Flow Verification")

        try:
            # Verify all components are working together using public APIs

            checks = []

            # Check 1: Events exist
            events = self.episodic_store.list_events(self.project.id, limit=1)
            checks.append(("Events captured", len(events) > 0))

            # Check 2: Memories created
            memories = self.memory_store.list_memories(self.project.id, limit=100)
            checks.append(("Memories persisted", len(memories) > 0))

            # Check 3: Procedures extracted
            procedures = self.procedural_store.list_procedures(limit=100)
            consolidation_procs = [p for p in procedures if p.created_by == "consolidation"]
            checks.append(("Procedures extracted", len(consolidation_procs) > 0))

            # Check 4: Search works
            search_results = self.memory_store.recall_with_reranking(
                query="test",
                project_id=self.project.id,
                k=10
            )
            checks.append(("Search enabled", len(search_results) > 0))

            # Print results
            all_passed = True
            for check_name, check_passed in checks:
                print_result(f"  {check_name}", check_passed)
                all_passed = all_passed and check_passed

            self.results.append(("End-to-End Flow", all_passed))
            return all_passed

        except Exception as e:
            print_result("End-to-end flow", False, str(e))
            self.results.append(("End-to-End Flow", False))
            return False

    def generate_report(self):
        """Generate evaluation report."""
        print_section("EVALUATION REPORT")

        passed_count = sum(1 for _, passed in self.results if passed)
        total_count = len(self.results)

        print(f"Total Tests: {total_count}")
        print(f"Passed: {passed_count}")
        print(f"Failed: {total_count - passed_count}")
        print(f"Success Rate: {(passed_count/total_count*100):.1f}%")

        print("\nDetailed Results:")
        for test_name, passed in self.results:
            status = "✅" if passed else "❌"
            print(f"  {status} {test_name}")

        print_section("CONCLUSION")

        if passed_count == total_count:
            print("✅ ALL TESTS PASSED")
            print("\nThe complete learning pipeline is FUNCTIONAL:")
            print("  ✅ Event capture works")
            print("  ✅ Semantic memories persist to database")
            print("  ✅ Procedures are extracted and stored")
            print("  ✅ Search with relevance ranking works")
            print("  ✅ End-to-end flow is integrated")
            print("\n🎉 Production-ready learning system verified!")
            return True
        else:
            print("⚠️ SOME TESTS FAILED")
            print("\nPlease review failures above and check:")
            print("  - PostgreSQL is running and accessible")
            print("  - All dependencies are installed")
            print("  - Database schema is properly initialized")
            return False

    def run(self):
        """Run complete evaluation."""
        print("\n" + "="*70)
        print("  ATHENA LEARNING SYSTEM - END-TO-END EVALUATION")
        print("="*70)

        if not self.setup():
            return False

        # Run all tests
        self.test_and_consolidate()  # Capture events
        self._consolidate_events_to_memories()  # Run consolidation once after event capture
        self.test_semantic_memories()
        self.test_procedure_extraction()
        self.test_search_ranking()
        self.test_end_to_end_flow()

        # Generate report
        return self.generate_report()


if __name__ == "__main__":
    evaluator = E2EEvaluation()
    success = evaluator.run()
    sys.exit(0 if success else 1)
