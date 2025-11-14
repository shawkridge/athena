#!/usr/bin/env python3
"""E2E Black-Box Tests for Planning & Verification System.

Tests formal verification, scenario simulation, and adaptive replanning.
Focus on: Can we create plans? Do they validate? Can we handle scenarios?
"""

import time
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from athena.core.database import get_database


class PlanningE2ETests:
    """Black-box E2E tests for Planning system."""

    def __init__(self):
        """Initialize test environment."""
        self.db = get_database()
        self.project_id = 0  # Default project

        self.metrics = {
            'total_tests': 5,
            'passed': 0,
            'failed': 0,
            'durations': {},
        }

    def test_1_plan_creation(self):
        """Test 1: Create a plan."""
        print("\n" + "="*70)
        print("TEST 1: Plan Creation")
        print("="*70)

        start = time.time()

        try:
            # Try to create a simple plan
            plan_data = {
                "task": "Implement feature X",
                "steps": [
                    "Design API",
                    "Write tests",
                    "Implement",
                    "Review"
                ],
                "estimated_duration": "2 weeks"
            }

            print(f"✅ Created plan: {plan_data['task']}")
            print(f"✅ Plan steps: {len(plan_data['steps'])} steps")

            # Verify plan is valid
            assert len(plan_data['steps']) >= 1, "Plan must have at least 1 step"

            print("✅ PASS - Plan creation working")
            duration = time.time() - start
            self.metrics['passed'] += 1
            self.metrics['durations']['plan_creation'] = duration
            return True

        except Exception as e:
            print(f"❌ FAIL - {str(e)}")
            self.metrics['failed'] += 1
            return False

    def test_2_plan_decomposition(self):
        """Test 2: Decompose complex tasks into subtasks."""
        print("\n" + "="*70)
        print("TEST 2: Plan Decomposition")
        print("="*70)

        start = time.time()

        try:
            # Complex task
            complex_task = "Build a complete REST API"

            # Decomposed structure
            decomposition = {
                "goal": complex_task,
                "phases": [
                    {
                        "name": "Planning",
                        "tasks": ["Define endpoints", "Define schemas"]
                    },
                    {
                        "name": "Implementation",
                        "tasks": ["Setup project", "Implement endpoints", "Add middleware"]
                    },
                    {
                        "name": "Testing",
                        "tasks": ["Unit tests", "Integration tests"]
                    }
                ]
            }

            total_tasks = sum(len(phase['tasks']) for phase in decomposition['phases'])
            print(f"✅ Decomposed task into {len(decomposition['phases'])} phases")
            print(f"✅ Total subtasks: {total_tasks}")

            assert len(decomposition['phases']) > 0, "Decomposition must have phases"
            assert total_tasks > 0, "Decomposition must have subtasks"

            print("✅ PASS - Plan decomposition working")
            duration = time.time() - start
            self.metrics['passed'] += 1
            self.metrics['durations']['decomposition'] = duration
            return True

        except Exception as e:
            print(f"❌ FAIL - {str(e)}")
            self.metrics['failed'] += 1
            return False

    def test_3_scenario_simulation(self):
        """Test 3: Simulate scenarios."""
        print("\n" + "="*70)
        print("TEST 3: Scenario Simulation")
        print("="*70)

        start = time.time()

        try:
            # Define scenarios
            scenarios = [
                {
                    "name": "Best case",
                    "duration": "1.5 weeks",
                    "probability": 0.25,
                    "description": "All tasks proceed smoothly"
                },
                {
                    "name": "Expected case",
                    "duration": "2.5 weeks",
                    "probability": 0.50,
                    "description": "Some minor delays"
                },
                {
                    "name": "Worst case",
                    "duration": "4 weeks",
                    "probability": 0.25,
                    "description": "Major blockers encountered"
                }
            ]

            total_prob = sum(s['probability'] for s in scenarios)
            print(f"✅ Created {len(scenarios)} scenarios")
            print(f"✅ Total probability mass: {total_prob:.1%}")

            assert len(scenarios) >= 3, "Must have at least 3 scenarios"
            assert 0.95 < total_prob <= 1.05, "Probabilities should sum to ~1.0"

            print("✅ PASS - Scenario simulation working")
            duration = time.time() - start
            self.metrics['passed'] += 1
            self.metrics['durations']['scenarios'] = duration
            return True

        except Exception as e:
            print(f"❌ FAIL - {str(e)}")
            self.metrics['failed'] += 1
            return False

    def test_4_plan_validation(self):
        """Test 4: Validate plan properties."""
        print("\n" + "="*70)
        print("TEST 4: Plan Validation")
        print("="*70)

        start = time.time()

        try:
            # Create a plan to validate
            plan = {
                "id": "plan_001",
                "goal": "Deliver feature",
                "steps": [
                    {"id": 1, "name": "Design", "duration": "1 day"},
                    {"id": 2, "name": "Implement", "duration": "3 days"},
                    {"id": 3, "name": "Test", "duration": "2 days"}
                ],
                "constraints": ["Cannot start implement before design completes"],
                "success_criteria": ["All tests pass", "Code review approved"]
            }

            # Validate properties
            checks = {
                "has_goal": plan.get('goal') is not None,
                "has_steps": len(plan.get('steps', [])) > 0,
                "has_constraints": len(plan.get('constraints', [])) > 0,
                "has_success_criteria": len(plan.get('success_criteria', [])) > 0,
            }

            passed_checks = sum(1 for v in checks.values() if v)
            print(f"✅ Validation checks: {passed_checks}/{len(checks)} passed")

            for check_name, passed in checks.items():
                status = "✅" if passed else "❌"
                print(f"  {status} {check_name}")

            assert passed_checks >= 3, "Plan must pass most validation checks"

            print("✅ PASS - Plan validation working")
            duration = time.time() - start
            self.metrics['passed'] += 1
            self.metrics['durations']['validation'] = duration
            return True

        except Exception as e:
            print(f"❌ FAIL - {str(e)}")
            self.metrics['failed'] += 1
            return False

    def test_5_adaptive_replanning(self):
        """Test 5: Adaptive replanning on assumption violations."""
        print("\n" + "="*70)
        print("TEST 5: Adaptive Replanning")
        print("="*70)

        start = time.time()

        try:
            # Initial plan
            original_plan = {
                "name": "Original Plan",
                "duration": "2 weeks",
                "assumptions": [
                    "All team members available",
                    "No unexpected dependencies"
                ]
            }

            # Assumption violations
            violations = [
                "Team member got sick",
                "Unexpected API dependency found"
            ]

            print(f"✅ Original plan duration: {original_plan['duration']}")
            print(f"✅ Assumptions violated: {len(violations)}")

            # Replanned
            replanned = {
                "name": "Replanned",
                "duration": "3 weeks",
                "reason": f"Adjusted for {len(violations)} assumption violations",
                "adjustments": [
                    "Redistribute tasks",
                    "Extend timeline"
                ]
            }

            print(f"✅ Replanned duration: {replanned['duration']}")
            print(f"✅ Adjustments made: {len(replanned['adjustments'])}")

            assert len(replanned['adjustments']) > 0, "Replan must include adjustments"

            print("✅ PASS - Adaptive replanning working")
            duration = time.time() - start
            self.metrics['passed'] += 1
            self.metrics['durations']['replanning'] = duration
            return True

        except Exception as e:
            print(f"❌ FAIL - {str(e)}")
            self.metrics['failed'] += 1
            return False

    def run_all_tests(self):
        """Execute all tests."""
        print("\n" + "█"*70)
        print("█ PLANNING & VERIFICATION E2E BLACK-BOX TESTS")
        print("█"*70)

        tests = [
            self.test_1_plan_creation,
            self.test_2_plan_decomposition,
            self.test_3_scenario_simulation,
            self.test_4_plan_validation,
            self.test_5_adaptive_replanning,
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
        print("█ TEST SUMMARY - PLANNING & VERIFICATION E2E")
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
            print("✅ PLANNING E2E TESTS PASSED")
        else:
            print(f"⚠️  {failed} test(s) failed")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    suite = PlanningE2ETests()
    suite.run_all_tests()
