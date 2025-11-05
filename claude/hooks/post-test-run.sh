#!/bin/bash
# Post-Test-Run Hook - Detect test results and update task status
#
# Triggered after: pytest, test runs, validation
# Actions:
#   1. Parse test results
#   2. Map test files to tasks
#   3. Update task status (pending → verified if passing)
#   4. Record test outcomes to episodic memory
#   5. Calculate phase progress
#
# Usage: Called automatically by test runner or manually
# Example: post-test-run.sh test_results.json


# ============================================================
# INSTRUMENTATION: Hook Execution Logging
# ============================================================
# Added by instrument_hooks.py on 2025-10-29T15:00:44.178410

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "post-test-run"
hook_start_time=$(date +%s%N)

# ============================================================
# HOOK BODY
# ============================================================

set -euo pipefail

# Logging
log() { echo "[TEST-HOOK] $(date '+%Y-%m-%d %H:%M:%S') $*" >&2; }
die() { log "ERROR: $*"; exit 1; }

# Get input (test results file or read from stdin)
TEST_RESULTS_FILE="${1:--}"

if [ "$TEST_RESULTS_FILE" = "-" ]; then
  TEST_RESULTS=$(cat)
else
  [ -f "$TEST_RESULTS_FILE" ] || die "Test results file not found: $TEST_RESULTS_FILE"
  TEST_RESULTS=$(cat "$TEST_RESULTS_FILE")
fi

log "Processing test results..."

# Parse pytest output for passing/failing tests
PASSING_TESTS=()
FAILING_TESTS=()
TEST_SUMMARY=""

# Try to parse JSON format (if pytest --json-report used)
if echo "$TEST_RESULTS" | grep -q '"passed"'; then
  PASSED=$(echo "$TEST_RESULTS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('summary', {}).get('passed', 0))")
  FAILED=$(echo "$TEST_RESULTS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('summary', {}).get('failed', 0))")
  TEST_SUMMARY="$PASSED passed, $FAILED failed"
else
  # Fallback: parse text output
  PASSED=$(echo "$TEST_RESULTS" | grep -oP '(\d+) passed' | head -1 | grep -oP '\d+' || echo "0")
  FAILED=$(echo "$TEST_RESULTS" | grep -oP '(\d+) failed' | head -1 | grep -oP '\d+' || echo "0")
  TEST_SUMMARY="$PASSED passed, $FAILED failed"
fi

log "Test summary: $TEST_SUMMARY"

# Check if all tests passed
if [ "$FAILED" -eq 0 ] 2>/dev/null; then
  TESTS_PASSED=true
  log "✓ All tests passed"
else
  TESTS_PASSED=false
  log "✗ Some tests failed"
fi

# Find test files from results
log "Mapping test files to tasks..."

# Get list of test files from pytest output
TEST_FILES=$(echo "$TEST_RESULTS" | grep -oP '(tests?/\S+\.py)' | sort -u || echo "")

if [ -z "$TEST_FILES" ]; then
  # Alternative: use git to find recently changed test files
  TEST_FILES=$(git diff --name-only --cached 2>/dev/null | grep "^tests" || echo "")
fi

if [ -z "$TEST_FILES" ]; then
  log "WARNING: No test files found in results"
else
  log "Found test files:"
  echo "$TEST_FILES" | while read -r test_file; do
    echo "  - $test_file"
  done
fi

# Update task status for each test file
log "Updating task statuses..."

python3 << 'PYTHON_BLOCK'
import sys
import os
import json
from pathlib import Path

# Add hooks lib to path
sys.path.insert(0, str(Path.home() / ".claude" / "hooks" / "lib"))

try:
    from task_manager import TaskManager
except ImportError:
    print("ERROR: Cannot import TaskManager", file=sys.stderr)
    sys.exit(1)

tm = TaskManager()

# Get test files from environment
test_results_str = os.environ.get("TEST_RESULTS", "")
tests_passed = os.environ.get("TESTS_PASSED", "false").lower() == "true"
test_summary = os.environ.get("TEST_SUMMARY", "")

# Parse test files (from git)
test_files = []
try:
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", "--cached"],
        capture_output=True,
        text=True
    )
    test_files = [f for f in result.stdout.split('\n') if f.startswith('tests') and f.endswith('.py')]
except:
    pass

if not test_files:
    print("No test files found", file=sys.stderr)
    sys.exit(0)

# Find tasks for these test files
tasks_updated = set()
for test_file in test_files:
    tasks = tm.find_tasks_by_test_file(test_file)

    for task in tasks:
        if task in tasks_updated:
            continue

        if tests_passed:
            # Mark task as verified
            new_status = "verified"
            notes = f"Tests passing ({test_summary})"
        else:
            # Mark task as blocked
            new_status = "blocked"
            notes = f"Tests failing ({test_summary})"

        tm.update_task_status(task, new_status, notes)
        tm.record_task_event(task, "test_run", test_summary, "success" if tests_passed else "failure")

        tasks_updated.add(task)

print(f"Updated {len(tasks_updated)} tasks")

PYTHON_BLOCK

log "✓ Task status updates complete"

# Record event to episodic memory
log "Recording test event to episodic memory..."

python3 ~/.claude/hooks/lib/record_episode.py \
  --event-type test_run \
  --content "Test run completed: $TEST_SUMMARY" \
  --outcome success \
  --context-phase "phase-1-gap-closing" 2>/dev/null || true

log "✓ Test hook complete"

# Return status
if [ "$TESTS_PASSED" = "true" ]; then
  exit 0
else
  exit 1
fi


# ============================================================
# INSTRUMENTATION: Log Hook Result
# ============================================================

hook_end_time=$(date +%s%N)
hook_duration_ms=$(( (hook_end_time - hook_start_time) / 1000000 ))

if [ $? -eq 0 ]; then
  log_hook_success "post-test-run" "$hook_duration_ms" "Hook completed successfully"
else
  log_hook_failure "post-test-run" "$hook_duration_ms" "Hook exited with error"
fi

exit 0
