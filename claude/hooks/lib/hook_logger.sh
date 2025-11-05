#!/bin/bash
#
# Hook Logger Library - Structured logging for all hooks
# Provides reusable functions for hook execution tracking
#
# Usage:
#   source ~/.claude/hooks/lib/hook_logger.sh
#   log_hook_start "my-hook"
#   ... do work ...
#   log_hook_success "my-hook" "50" "Processed 42 events"
#

# Log file location
HOOK_LOG_FILE="${HOOK_LOG_FILE:-$HOME/.claude/hooks/execution.jsonl}"

# Create log directory if needed
mkdir -p "$(dirname "$HOOK_LOG_FILE")"

# Color codes for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================
# Log Hook Start
# ============================================================
# Usage: log_hook_start "hook-name"
log_hook_start() {
  local hook_name="$1"

  # Store start time in nanoseconds
  echo "$hook_name" > "/tmp/hook_${hook_name}_start.tmp"
  echo "$(date +%s%N)" >> "/tmp/hook_${hook_name}_start.tmp"

  if [ -n "$CLAUDE_DEBUG" ]; then
    echo -e "${YELLOW}→${NC} Starting hook: $hook_name" >&2
  fi
}

# ============================================================
# Log Hook Success
# ============================================================
# Usage: log_hook_success "hook-name" "duration-ms" "details"
log_hook_success() {
  local hook_name="$1"
  local duration_ms="${2:-0}"
  local details="${3:-OK}"
  local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  # Create JSON log entry (compact format for JSONL)
  local log_entry=$(jq -c -n \
    --arg name "$hook_name" \
    --arg status "success" \
    --arg ts "$timestamp" \
    --arg duration "$duration_ms" \
    --arg details "$details" \
    '{hook: $name, status: $status, timestamp: $ts, duration_ms: ($duration | tonumber), details: $details}')

  # Append to log file
  echo "$log_entry" >> "$HOOK_LOG_FILE"

  if [ -n "$CLAUDE_DEBUG" ]; then
    echo -e "${GREEN}✓${NC} $hook_name completed in ${duration_ms}ms" >&2
  fi
}

# ============================================================
# Log Hook Failure
# ============================================================
# Usage: log_hook_failure "hook-name" "duration-ms" "error-message"
log_hook_failure() {
  local hook_name="$1"
  local duration_ms="${2:-0}"
  local error_msg="${3:-Unknown error}"
  local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  # Create JSON log entry (compact format for JSONL)
  local log_entry=$(jq -c -n \
    --arg name "$hook_name" \
    --arg status "failure" \
    --arg ts "$timestamp" \
    --arg duration "$duration_ms" \
    --arg error "$error_msg" \
    '{hook: $name, status: $status, timestamp: $ts, duration_ms: ($duration | tonumber), error: $error}')

  # Append to log file
  echo "$log_entry" >> "$HOOK_LOG_FILE"

  if [ -n "$CLAUDE_DEBUG" ]; then
    echo -e "${RED}✗${NC} $hook_name failed: $error_msg" >&2
  fi
}

# ============================================================
# Log Hook Timeout
# ============================================================
# Usage: log_hook_timeout "hook-name" "timeout-ms"
log_hook_timeout() {
  local hook_name="$1"
  local timeout_ms="${2:-5000}"
  local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  # Create JSON log entry (compact format for JSONL)
  local log_entry=$(jq -c -n \
    --arg name "$hook_name" \
    --arg status "timeout" \
    --arg ts "$timestamp" \
    --arg timeout "$timeout_ms" \
    '{hook: $name, status: $status, timestamp: $ts, timeout_ms: ($timeout | tonumber)}')

  # Append to log file
  echo "$log_entry" >> "$HOOK_LOG_FILE"

  if [ -n "$CLAUDE_DEBUG" ]; then
    echo -e "${RED}⏱${NC} $hook_name timeout (${timeout_ms}ms)" >&2
  fi
}

# ============================================================
# Calculate Duration from Start
# ============================================================
# Usage: duration=$(hook_duration "hook-name")
hook_duration() {
  local hook_name="$1"
  local start_file="/tmp/hook_${hook_name}_start.tmp"

  if [ ! -f "$start_file" ]; then
    echo "0"
    return
  fi

  local start_ns=$(tail -1 "$start_file")
  local end_ns=$(date +%s%N)
  local duration_ms=$(( (end_ns - start_ns) / 1000000 ))

  # Clean up
  rm -f "$start_file"

  echo "$duration_ms"
}

# ============================================================
# Execute Hook with Logging
# ============================================================
# Usage: execute_hook_with_logging "hook-name" "/path/to/hook.sh" [timeout_ms]
execute_hook_with_logging() {
  local hook_name="$1"
  local hook_script="$2"
  local timeout_ms="${3:-5000}"

  log_hook_start "$hook_name"

  # Execute hook with timeout
  if timeout "$(( timeout_ms / 1000 ))s" bash "$hook_script" > /dev/null 2>&1; then
    local duration=$(hook_duration "$hook_name")
    log_hook_success "$hook_name" "$duration" "Hook executed successfully"
    return 0
  else
    local exit_code=$?

    if [ $exit_code -eq 124 ]; then
      # Timeout
      log_hook_timeout "$hook_name" "$timeout_ms"
      return 1
    else
      # Failure
      local duration=$(hook_duration "$hook_name")
      log_hook_failure "$hook_name" "$duration" "Exit code: $exit_code"
      return 1
    fi
  fi
}

# ============================================================
# Query Hook Statistics
# ============================================================
# Usage: hook_stats "hook-name"
hook_stats() {
  local hook_name="$1"

  if [ ! -f "$HOOK_LOG_FILE" ]; then
    echo "No execution logs found"
    return
  fi

  python3 << PYTHON_STATS
import json
from pathlib import Path
from statistics import mean, stdev
from datetime import datetime, timedelta

log_file = Path("$HOOK_LOG_FILE")

# Load logs for this hook
hook_entries = []
with open(log_file) as f:
    for line in f:
        entry = json.loads(line)
        if entry.get("hook") == "$hook_name":
            hook_entries.append(entry)

if not hook_entries:
    print(f"No entries found for hook: $hook_name")
    exit(0)

# Calculate stats
durations = [e.get("duration_ms", 0) for e in hook_entries if e.get("status") == "success"]
success_count = len([e for e in hook_entries if e.get("status") == "success"])
failure_count = len([e for e in hook_entries if e.get("status") == "failure"])
timeout_count = len([e for e in hook_entries if e.get("status") == "timeout"])

print(f"Hook: $hook_name")
print(f"Executions: {len(hook_entries)} (success: {success_count}, failure: {failure_count}, timeout: {timeout_count})")

if durations:
    print(f"Latency: avg={mean(durations):.0f}ms, min={min(durations):.0f}ms, max={max(durations):.0f}ms")
    if len(durations) > 1:
        print(f"Stddev: {stdev(durations):.0f}ms")

PYTHON_STATS
}

# ============================================================
# All Hook Statistics
# ============================================================
# Usage: all_hook_stats
all_hook_stats() {
  if [ ! -f "$HOOK_LOG_FILE" ]; then
    echo "No execution logs found"
    return
  fi

  python3 << PYTHON_ALL_STATS
import json
from pathlib import Path
from collections import defaultdict
from statistics import mean, stdev

log_file = Path("$HOOK_LOG_FILE")

# Load and group logs
hooks = defaultdict(list)
with open(log_file) as f:
    for line in f:
        entry = json.loads(line)
        hooks[entry.get("hook", "unknown")].append(entry)

# Display stats
print("=" * 70)
print("HOOK EXECUTION STATISTICS")
print("=" * 70)

for hook_name in sorted(hooks.keys()):
    entries = hooks[hook_name]
    durations = [e.get("duration_ms", 0) for e in entries if e.get("status") == "success"]

    success_count = len([e for e in entries if e.get("status") == "success"])
    failure_count = len([e for e in entries if e.get("status") == "failure"])
    timeout_count = len([e for e in entries if e.get("status") == "timeout"])

    print(f"\n{hook_name}")
    print(f"  Executions: {len(entries)} (✓ {success_count}, ✗ {failure_count}, ⏱ {timeout_count})")

    if durations:
        avg_duration = mean(durations)
        min_duration = min(durations)
        max_duration = max(durations)
        print(f"  Latency: avg={avg_duration:.0f}ms, min={min_duration:.0f}ms, max={max_duration:.0f}ms")

        if len(durations) > 1:
            std_duration = stdev(durations)
            print(f"  Stddev: {std_duration:.0f}ms")

        # Show if slow (>200ms)
        if avg_duration > 200:
            print(f"  ⚠️  SLOW (avg > 200ms)")

print("\n" + "=" * 70)

PYTHON_ALL_STATS
}

# ============================================================
# Export to CSV for analysis
# ============================================================
# Usage: export_hook_logs_csv "/tmp/hook_logs.csv"
export_hook_logs_csv() {
  local output_file="${1:-/tmp/hook_logs.csv}"

  if [ ! -f "$HOOK_LOG_FILE" ]; then
    echo "No execution logs found"
    return
  fi

  python3 << PYTHON_EXPORT
import json
import csv
from pathlib import Path

log_file = Path("$HOOK_LOG_FILE")
output = Path("$output_file")

# Read and convert to CSV
with open(log_file) as f_in, open(output, 'w', newline='') as f_out:
    rows = [json.loads(line) for line in f_in]

    if not rows:
        print("No data to export")
        exit(1)

    # Get all keys
    keys = set()
    for row in rows:
        keys.update(row.keys())

    writer = csv.DictWriter(f_out, fieldnames=sorted(keys))
    writer.writeheader()
    writer.writerows(rows)

print(f"Exported {len(rows)} entries to {output}")

PYTHON_EXPORT
}

export "HOOK_LOG_FILE" "log_hook_start" "log_hook_success" "log_hook_failure" "log_hook_timeout" "hook_duration" "execute_hook_with_logging" "hook_stats" "all_hook_stats" "export_hook_logs_csv"
