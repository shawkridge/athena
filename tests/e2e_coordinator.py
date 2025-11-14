#!/usr/bin/env python3
"""Master E2E Test Coordinator for Athena System.

Runs all E2E test suites in sequence and generates consolidated report.
Follows black-box testing methodology.
"""

import subprocess
import sys
import time
import json
from pathlib import Path
from datetime import datetime


class E2ETestCoordinator:
    """Coordinates and runs all E2E test suites."""

    def __init__(self):
        """Initialize coordinator."""
        self.test_dir = Path(__file__).parent
        self.project_root = self.test_dir.parent

        self.test_suites = [
            {
                'name': 'Memory System',
                'file': 'e2e_memory_system.py',
                'priority': 1,
                'status': 'pending',
            },
            {
                'name': 'Working Memory',
                'file': 'e2e_working_memory.py',
                'priority': 1,
                'status': 'pending',
            },
            {
                'name': 'Planning & Verification',
                'file': 'e2e_planning.py',
                'priority': 2,
                'status': 'pending',
            },
            {
                'name': 'RAG System',
                'file': 'e2e_rag.py',
                'priority': 2,
                'status': 'pending',
            },
            {
                'name': 'Knowledge Graph',
                'file': 'e2e_knowledge_graph.py',
                'priority': 1,
                'status': 'pending',
            },
            {
                'name': 'Learning System',
                'file': 'e2e_learning.py',
                'priority': 3,
                'status': 'pending',
            },
            {
                'name': 'Automation/Triggers',
                'file': 'e2e_automation.py',
                'priority': 3,
                'status': 'pending',
            },
            {
                'name': 'Code Analysis',
                'file': 'e2e_code_analysis.py',
                'priority': 3,
                'status': 'pending',
            },
        ]

        self.results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'suites': [],
            'duration': 0,
        }

    def run_test_suite(self, suite):
        """Run a single E2E test suite."""
        print(f"\n{'='*70}")
        print(f"Running: {suite['name']} (Priority {suite['priority']})")
        print(f"{'='*70}")

        test_file = self.test_dir / suite['file']

        if not test_file.exists():
            print(f"⚠️  Test file not found: {test_file}")
            suite['status'] = 'skipped'
            suite['result'] = 'File not found'
            self.results['skipped'] += 1
            return False

        try:
            start = time.time()
            result = subprocess.run(
                [sys.executable, str(test_file)],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per suite
            )
            duration = time.time() - start

            suite['duration'] = duration
            suite['returncode'] = result.returncode

            # Parse output for test results
            output = result.stdout + result.stderr

            # Look for success/failure indicators
            if 'ALL TESTS PASSED' in output or result.returncode == 0:
                suite['status'] = 'passed'
                suite['result'] = 'All tests passed'
                self.results['passed'] += 1
            elif 'FAIL' in output or result.returncode != 0:
                suite['status'] = 'failed'
                suite['result'] = 'Some tests failed'
                self.results['failed'] += 1
            else:
                suite['status'] = 'skipped'
                suite['result'] = 'Tests skipped'
                self.results['skipped'] += 1

            # Print last 30 lines of output
            lines = output.split('\n')
            print('\n'.join(lines[-30:]))

            print(f"\n✓ {suite['name']}: {suite['result']} ({duration:.2f}s)")

        except subprocess.TimeoutExpired:
            print(f"❌ {suite['name']}: TIMEOUT (>5 minutes)")
            suite['status'] = 'failed'
            suite['result'] = 'Timeout'
            self.results['failed'] += 1
        except Exception as e:
            print(f"❌ {suite['name']}: ERROR - {str(e)}")
            suite['status'] = 'failed'
            suite['result'] = f'Error: {str(e)}'
            self.results['failed'] += 1

        self.results['suites'].append(suite)
        self.results['total'] += 1

    def run_all_tests(self, priority_level=None):
        """Run all E2E tests, optionally filtered by priority."""
        print("\n" + "█"*70)
        print("█ ATHENA SYSTEM-WIDE E2E TEST COORDINATOR")
        print("█"*70)
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Filter by priority if specified
        suites_to_run = self.test_suites
        if priority_level:
            suites_to_run = [s for s in self.test_suites if s['priority'] <= priority_level]
            print(f"\nRunning Priority {priority_level} tests only ({len(suites_to_run)} suites)")
        else:
            print(f"\nRunning all {len(suites_to_run)} test suites")

        start_time = time.time()

        for suite in suites_to_run:
            self.run_test_suite(suite)

        self.results['duration'] = time.time() - start_time
        self._print_summary()

    def _print_summary(self):
        """Print comprehensive test summary."""
        print("\n" + "█"*70)
        print("█ E2E TEST SUMMARY")
        print("█"*70)

        passed = self.results['passed']
        failed = self.results['failed']
        skipped = self.results['skipped']
        total = self.results['total']
        duration = self.results['duration']

        if total > 0:
            pass_rate = (passed / total) * 100
        else:
            pass_rate = 0

        print(f"\n📊 Overall Results:")
        print(f"  ✅ Passed:  {passed}/{total}")
        print(f"  ❌ Failed:  {failed}/{total}")
        print(f"  ⏭️  Skipped: {skipped}/{total}")
        print(f"  📈 Pass Rate: {pass_rate:.1f}%")

        print(f"\n⏱️  Timing:")
        print(f"  Total Duration: {duration:.2f}s ({duration/60:.1f}m)")

        print(f"\n📋 Test Suite Details:")
        for suite in self.results['suites']:
            status_icon = {
                'passed': '✅',
                'failed': '❌',
                'skipped': '⏭️',
            }.get(suite['status'], '❓')

            duration_str = f"({suite.get('duration', 0):.2f}s)" if 'duration' in suite else ""
            print(f"  {status_icon} {suite['name']:<30} {suite.get('result', 'Unknown'):<30} {duration_str}")

        print(f"\n{'='*70}")
        if failed == 0 and passed > 0:
            print("✅ ALL TESTS PASSED - SYSTEM READY FOR NEXT PHASE")
        elif failed == 0 and skipped > 0:
            print(f"⚠️  {skipped} test(s) skipped - Create test files to enable")
        else:
            print(f"❌ {failed} test suite(s) failed - Review logs above")
        print(f"{'='*70}\n")

    def generate_json_report(self, output_file=None):
        """Generate JSON report of test results."""
        if output_file is None:
            output_file = self.test_dir.parent / f"e2e_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total': self.results['total'],
                'passed': self.results['passed'],
                'failed': self.results['failed'],
                'skipped': self.results['skipped'],
                'pass_rate': (self.results['passed'] / self.results['total'] * 100) if self.results['total'] > 0 else 0,
                'duration': self.results['duration'],
            },
            'suites': self.results['suites'],
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n📄 Report saved: {output_file}")
        return output_file


def main():
    """Run the E2E test coordinator."""
    coordinator = E2ETestCoordinator()

    # Check for command line arguments
    priority = None
    if len(sys.argv) > 1:
        try:
            priority = int(sys.argv[1])
            print(f"Running Priority {priority} tests")
        except ValueError:
            print(f"Invalid priority level: {sys.argv[1]}")
            print("Usage: python e2e_coordinator.py [priority_level]")
            sys.exit(1)

    # Run tests
    coordinator.run_all_tests(priority_level=priority)

    # Generate JSON report
    coordinator.generate_json_report()

    # Return exit code based on results
    if coordinator.results['failed'] > 0:
        sys.exit(1)
    elif coordinator.results['total'] == 0:
        sys.exit(2)  # No tests ran
    else:
        sys.exit(0)  # All passed


if __name__ == "__main__":
    main()
