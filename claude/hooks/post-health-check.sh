#!/bin/bash
#
# Hook: PostHealthCheck - Records health metrics trends
# Triggers: After health check completion (Phase 5 monitoring)
# Purpose: Store health data for trend analysis and early warnings
#
# Input (stdin): JSON with health data {task_id, health_score, status, variance, errors, blockers}
# Output (stdout): JSON with recording directives
# Exit code: 0 = success (non-blocking)


# ============================================================
# INSTRUMENTATION: Hook Execution Logging
# ============================================================
# Added by instrument_hooks.py on 2025-10-29T15:00:44.175652

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "post-health-check"
hook_start_time=$(date +%s%N)

# ============================================================
# HOOK BODY
# ============================================================

# Read hook input from stdin
input=$(timeout 1 cat 2>/dev/null || echo '{}')

# Extract fields
task_id=$(echo "$input" | jq -r '.task_id // ""')
health_score=$(echo "$input" | jq -r '.health_score // 0.5')
health_status=$(echo "$input" | jq -r '.health_status // "unknown"')
progress=$(echo "$input" | jq -r '.progress_percent // 0')
duration_variance=$(echo "$input" | jq -r '.duration_variance // 0')
errors=$(echo "$input" | jq -r '.errors // 0')
blockers=$(echo "$input" | jq -r '.blockers // 0')

# Create timestamp
timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Log hook execution if debugging enabled
if [ -n "$CLAUDE_DEBUG" ]; then
  echo "[HOOK] PostHealthCheck: task=$task_id score=$health_score status=$health_status ts=$timestamp" >&2
fi

# ============================================================
# STEP 1: Record Health Metrics as Episodic Event
# ============================================================

event_recorded="false"
event_id=""

python_cmd="python3"
if [ -f "/home/user/.work/athena/.venv/bin/python3" ]; then
  python_cmd="/home/user/.work/athena/.venv/bin/python3"
fi

# Record health check event
record_output=$("$python_cmd" "$(dirname "$0")/lib/record_episode.py" \
  --tool "HealthCheck" \
  --event-type "monitoring" \
  --metadata "{\"task_id\": $task_id, \"health_score\": $health_score, \"status\": \"$health_status\", \"progress\": $progress, \"errors\": $errors, \"blockers\": $blockers}" \
  --json 2>/dev/null)

if echo "$record_output" | jq empty 2>/dev/null; then
  event_recorded=$(echo "$record_output" | jq -r '.success // false')
  event_id=$(echo "$record_output" | jq -r '.event_id // ""')
  if [ -n "$CLAUDE_DEBUG" ]; then
    echo "[HOOK] Health metrics recorded: id=$event_id success=$event_recorded" >&2
  fi
fi

# ============================================================
# STEP 2: Store Health Data for Trend Analysis
# ============================================================

# Add health metrics to working memory for trend tracking
health_memory_status="pending"

python3 << 'PYTHON_HEALTH_BLOCK'
import json
import sys
import os
from pathlib import Path

try:
    # Try to update working memory with health data
    sys.path.insert(0, str(Path.home() / ".claude" / "hooks" / "lib"))

    # Parse environment
    task_id = os.environ.get("task_id", "")
    health_score = float(os.environ.get("health_score", "0.5"))
    health_status = os.environ.get("health_status", "unknown")

    if task_id:
        # Store in a simple health history file (alternative to memory system)
        history_file = Path.home() / ".memory-mcp" / "health_history.jsonl"
        history_file.parent.mkdir(parents=True, exist_ok=True)

        record = {
            "task_id": int(task_id),
            "health_score": health_score,
            "health_status": health_status,
            "timestamp": "%(timestamp)s"
        }

        with open(history_file, "a") as f:
            f.write(json.dumps(record) + "\n")

        print("Health metrics stored for trend analysis")
except Exception as e:
    print(f"Health storage: {e}")

PYTHON_HEALTH_BLOCK

health_memory_status="stored"

# ============================================================
# STEP 3: Check for Alert Conditions
# ============================================================

alert_triggered="false"
alert_type=""
alert_msg=""

# Convert health_score to number for comparison
health_score_num=$(echo "$health_score" | awk '{printf "%.2f", $1}')

# Check if health is degrading
if [ "$(echo "$health_score_num < 0.5" | bc -l)" -eq 1 ]; then
  alert_triggered="true"
  alert_type="critical"
  alert_msg="Task $task_id health CRITICAL: score=$health_score_num - immediate intervention needed"

  if [ -n "$CLAUDE_DEBUG" ]; then
    echo "[HOOK] ALERT: $alert_msg" >&2
  fi
elif [ "$(echo "$health_score_num < 0.65" | bc -l)" -eq 1 ]; then
  alert_triggered="true"
  alert_type="warning"
  alert_msg="Task $task_id health WARNING: score=$health_score_num - optimization recommended"

  if [ -n "$CLAUDE_DEBUG" ]; then
    echo "[HOOK] WARNING: $alert_msg" >&2
  fi
fi

# Check for high error count
if [ "$errors" -ge 3 ]; then
  alert_triggered="true"
  if [ -z "$alert_type" ]; then
    alert_type="high_errors"
  fi
  if [ -n "$CLAUDE_DEBUG" ]; then
    echo "[HOOK] Multiple errors detected: $errors" >&2
  fi
fi

# Check for high blocker count
if [ "$blockers" -ge 2 ]; then
  alert_triggered="true"
  if [ -z "$alert_type" ]; then
    alert_type="blocked"
  fi
  if [ -n "$CLAUDE_DEBUG" ]; then
    echo "[HOOK] Multiple blockers detected: $blockers" >&2
  fi
fi

# ============================================================
# STEP 4: Return Hook Response
# ============================================================

jq -n \
  --arg task "$task_id" \
  --arg score "$health_score" \
  --arg status "$health_status" \
  --arg event_id_str "$event_id" \
  --arg event_recorded "$event_recorded" \
  --arg alert "$alert_triggered" \
  --arg alert_type_str "$alert_type" \
  '{
    "continue": true,
    "suppressOutput": true,
    "hookSpecificOutput": {
      "hookEventName": "PostHealthCheck",
      "status": "silent",
      "task_id": $task,
      "health_score": '$health_score',
      "health_status": $status,
      "timestamp": "'$timestamp'",
      "episodic_event": {
        "recorded": ($event_recorded | test("true")),
        "event_id": $event_id_str
      },
      "health_storage": "'$health_memory_status'",
      "alert": {
        "triggered": ($alert | test("true")),
        "type": $alert_type_str
      }
    }
  }' 2>/dev/null || \
jq -n '{
  "continue": true,
  "suppressOutput": true
}'

exit 0


# ============================================================
# INSTRUMENTATION: Log Hook Result
# ============================================================

hook_end_time=$(date +%s%N)
hook_duration_ms=$(( (hook_end_time - hook_start_time) / 1000000 ))

if [ $? -eq 0 ]; then
  log_hook_success "post-health-check" "$hook_duration_ms" "Hook completed successfully"
else
  log_hook_failure "post-health-check" "$hook_duration_ms" "Hook exited with error"
fi

exit 0
