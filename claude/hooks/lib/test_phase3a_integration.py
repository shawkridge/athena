"""Comprehensive integration tests for Phase 3a: Dependencies + Metadata.

Tests the full workflow:
1. Create tasks with estimates
2. Create dependencies (task A blocks task B)
3. Mark task A complete (unblocks task B)
4. Verify metadata accuracy calculation
5. Get next task suggestion (respects dependencies)
"""

import sys
from datetime import datetime

from task_dependency_manager import TaskDependencyManager
from metadata_manager import MetadataManager
from task_updater import TaskUpdater
from checkpoint_task_linker import CheckpointTaskLinker


class Phase3aIntegrationTest:
    """Run full Phase 3a integration tests."""

    def __init__(self):
        """Initialize test fixtures."""
        self.dep_mgr = TaskDependencyManager()
        self.metadata_mgr = MetadataManager()
        self.task_updater = TaskUpdater()
        self.checkpoint_linker = CheckpointTaskLinker()
        self.test_project_id = 1
        self.test_tasks = []

    def setup_test_tasks(self):
        """Create test tasks for the test suite.

        We need to use real task IDs from the database.
        """
        # For testing, we'll assume tasks 1, 2, 3 exist in project 1
        # If they don't, the tests will gracefully degrade
        self.test_task_ids = [1, 2, 3]
        print("✓ Using existing task IDs for integration testing")

    def test_1_create_dependencies(self):
        """Test 1: Create dependency chain (1 → 2 → 3)."""
        print("\n🧪 TEST 1: Create Dependency Chain")
        print("═" * 50)

        # Task 1 blocks Task 2
        result = self.dep_mgr.create_dependency(
            project_id=self.test_project_id,
            from_task_id=self.test_task_ids[0],
            to_task_id=self.test_task_ids[1],
        )
        if result.get("success"):
            print(f"  ✓ {result['message']}")
        else:
            print(f"  ⚠ {result.get('error')}")
            return False

        # Task 2 blocks Task 3
        result = self.dep_mgr.create_dependency(
            project_id=self.test_project_id,
            from_task_id=self.test_task_ids[1],
            to_task_id=self.test_task_ids[2],
        )
        if result.get("success"):
            print(f"  ✓ {result['message']}")
        else:
            print(f"  ⚠ {result.get('error')}")
            return False

        return True

    def test_2_verify_blocking(self):
        """Test 2: Verify tasks are blocked correctly."""
        print("\n🧪 TEST 2: Verify Blocking")
        print("═" * 50)

        # Task 2 should be blocked by Task 1
        is_blocked, blocking_list = self.dep_mgr.is_task_blocked(
            self.test_project_id, self.test_task_ids[1]
        )
        print(f"  Task {self.test_task_ids[1]} blocked: {is_blocked}")
        if is_blocked:
            print(f"    ✓ Blocked by: {blocking_list}")
        else:
            print(f"    ⚠ Expected to be blocked")
            return False

        # Task 3 should be blocked by Task 2 (transitively by Task 1)
        is_blocked, blocking_list = self.dep_mgr.is_task_blocked(
            self.test_project_id, self.test_task_ids[2]
        )
        print(f"  Task {self.test_task_ids[2]} blocked: {is_blocked}")
        if is_blocked:
            print(f"    ✓ Blocked by: {blocking_list}")
        else:
            print(f"    ⚠ Expected to be blocked")
            return False

        return True

    def test_3_set_metadata(self):
        """Test 3: Set metadata (effort estimates, complexity, tags)."""
        print("\n🧪 TEST 3: Set Metadata")
        print("═" * 50)

        for task_id in self.test_task_ids:
            result = self.metadata_mgr.set_metadata(
                project_id=self.test_project_id,
                task_id=task_id,
                effort_estimate=120,  # 2 hours estimate
                complexity_score=7,
                priority_score=8,
                tags=["feature", "urgent"],
            )
            if result.get("success"):
                print(f"  ✓ Task {task_id}: estimate={result['effort_estimate']}m, "
                      f"complexity={result['complexity_score']}/10, "
                      f"tags={result['tags']}")
            else:
                print(f"  ⚠ Task {task_id}: {result.get('error')}")

        return True

    def test_4_complete_and_unblock(self):
        """Test 4: Complete Task 1, verify Task 2 unblocks."""
        print("\n🧪 TEST 4: Complete Task + Unblock Downstream")
        print("═" * 50)

        # Complete task using updated mark_task_complete with dependency support
        result = self.task_updater.mark_task_complete(
            project_id=self.test_project_id,
            task_id=self.test_task_ids[0],
            with_dependencies=True,
        )

        if result.get("success"):
            print(f"  ✓ Task {self.test_task_ids[0]} marked complete")
            newly_unblocked = result.get("newly_unblocked", [])
            if newly_unblocked:
                print(f"    ✓ Newly unblocked: {newly_unblocked}")
            else:
                print(f"    ℹ No tasks unblocked")
        else:
            print(f"  ⚠ Failed: {result.get('error')}")
            return False

        # Verify Task 2 is now unblocked
        is_blocked, _ = self.dep_mgr.is_task_blocked(
            self.test_project_id, self.test_task_ids[1]
        )
        if not is_blocked:
            print(f"  ✓ Task {self.test_task_ids[1]} is now unblocked")
            return True
        else:
            print(f"  ⚠ Task {self.test_task_ids[1]} still blocked")
            return False

    def test_5_record_effort_and_accuracy(self):
        """Test 5: Record actual effort and calculate accuracy."""
        print("\n🧪 TEST 5: Record Effort + Calculate Accuracy")
        print("═" * 50)

        # Record actual effort for Task 1 (estimate was 120, actual 150)
        result = self.metadata_mgr.record_actual_effort(
            project_id=self.test_project_id,
            task_id=self.test_task_ids[0],
            actual_minutes=150,
        )

        if result.get("success"):
            print(f"  ✓ Effort recorded for Task {self.test_task_ids[0]}")
            print(f"    Estimate: {result['effort_estimate']}m")
            print(f"    Actual: {result['effort_actual']}m")
            if "accuracy_percent" in result:
                print(f"    Accuracy: {result['accuracy_percent']}%")
                print(f"    Variance: {result['variance_minutes']}m")
        else:
            print(f"  ⚠ {result.get('error')}")
            return False

        # Verify accuracy calculation
        accuracy = self.metadata_mgr.calculate_accuracy(
            self.test_project_id, self.test_task_ids[0]
        )
        if accuracy:
            print(f"  ✓ Accuracy calculated: {accuracy['accuracy_percent']}%")
            print(f"    Underestimated: {accuracy['underestimated']}")
            return True
        else:
            print(f"  ⚠ Could not calculate accuracy")
            return False

    def test_6_get_unblocked_tasks(self):
        """Test 6: Get list of unblocked (ready to work) tasks."""
        print("\n🧪 TEST 6: Get Unblocked Tasks")
        print("═" * 50)

        unblocked = self.dep_mgr.get_unblocked_tasks(
            self.test_project_id,
            statuses=["pending", "in_progress"],
            limit=10,
        )

        if unblocked:
            print(f"  ✓ Found {len(unblocked)} unblocked task(s)")
            for task in unblocked:
                print(f"    - Task {task['id']}: {task['content']} "
                      f"(status: {task['status']}, priority: {task['priority']})")
            return True
        else:
            print(f"  ℹ No unblocked tasks found")
            return False

    def test_7_suggest_next_task_respects_dependencies(self):
        """Test 7: Next task suggestion respects dependencies."""
        print("\n🧪 TEST 7: Next Task Suggestion (Dependency-Aware)")
        print("═" * 50)

        # Suggest next task after completing Task 1
        suggested = self.checkpoint_linker.suggest_next_task(
            project_id=self.test_project_id,
            completed_task_id=self.test_task_ids[0],
        )

        if suggested:
            print(f"  ✓ Suggested task: {suggested.get('id')}")
            print(f"    Content: {suggested.get('content')}")
            print(f"    Status: {suggested.get('status')}")
            print(f"    Priority: {suggested.get('priority')}")
            return True
        else:
            print(f"  ℹ No task suggestion available")
            return False

    def test_8_project_analytics(self):
        """Test 8: Get project analytics (aggregate effort/accuracy)."""
        print("\n🧪 TEST 8: Project Analytics")
        print("═" * 50)

        analytics = self.metadata_mgr.get_project_analytics(self.test_project_id)

        if "error" not in analytics:
            print(f"  ✓ Project {self.test_project_id} analytics:")
            print(f"    Total tasks: {analytics.get('total_tasks')}")
            print(f"    Estimated: {analytics.get('estimated_tasks')}")
            print(f"    Tracked: {analytics.get('tracked_tasks')}")
            print(f"    Avg estimate: {analytics.get('avg_estimate_minutes')}m")
            print(f"    Avg actual: {analytics.get('avg_actual_minutes')}m")
            print(f"    Avg complexity: {analytics.get('avg_complexity')}/10")
            if "overall_accuracy_percent" in analytics:
                print(f"    Overall accuracy: {analytics['overall_accuracy_percent']}%")
            return True
        else:
            print(f"  ⚠ {analytics.get('error')}")
            return False

    def test_9_task_with_full_context(self):
        """Test 9: Get task with full context (dependencies + metadata)."""
        print("\n🧪 TEST 9: Task With Full Context")
        print("═" * 50)

        task = self.dep_mgr.get_task_with_dependencies(
            self.test_project_id, self.test_task_ids[1]
        )

        if task:
            print(f"  ✓ Task {task['id']}: {task['content']}")
            print(f"    Status: {task['status']}")
            print(f"    Is blocked: {task['is_blocked']}")
            if task['blocking_tasks']:
                print(f"    Blocked by: {[t['id'] for t in task['blocking_tasks']]}")
            if task['blocked_tasks']:
                print(f"    Blocks: {task['blocked_tasks']}")

            # Also get metadata
            metadata = self.metadata_mgr.get_task_metadata(
                self.test_project_id, self.test_task_ids[1]
            )
            if metadata:
                print(f"    Effort: {metadata['effort_estimate']}m estimate")
                print(f"    Complexity: {metadata['complexity_score']}/10")
                print(f"    Tags: {metadata['tags']}")
            return True
        else:
            print(f"  ⚠ Task not found")
            return False

    def run_all_tests(self):
        """Run all integration tests."""
        print("\n" + "=" * 70)
        print("  PHASE 3A: DEPENDENCIES + METADATA - INTEGRATION TEST SUITE")
        print("=" * 70)

        self.setup_test_tasks()

        tests = [
            ("Create Dependency Chain", self.test_1_create_dependencies),
            ("Verify Blocking", self.test_2_verify_blocking),
            ("Set Metadata", self.test_3_set_metadata),
            ("Complete + Unblock", self.test_4_complete_and_unblock),
            ("Record Effort & Accuracy", self.test_5_record_effort_and_accuracy),
            ("Get Unblocked Tasks", self.test_6_get_unblocked_tasks),
            ("Suggest Next Task", self.test_7_suggest_next_task_respects_dependencies),
            ("Project Analytics", self.test_8_project_analytics),
            ("Full Task Context", self.test_9_task_with_full_context),
        ]

        passed = 0
        failed = 0

        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"\n  ✗ Exception in test: {e}", file=sys.stderr)
                failed += 1

        # Summary
        print("\n" + "=" * 70)
        print(f"  RESULTS: {passed} passed, {failed} failed")
        print("=" * 70 + "\n")

        return failed == 0


if __name__ == "__main__":
    tester = Phase3aIntegrationTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
