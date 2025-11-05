#!/bin/bash
#
# Hook: PeriodicMonitor - Triggers periodic health monitoring
# Triggers: Session start and periodically during work
# Purpose: Ensure continuous health monitoring of active tasks
#
# This hook initiates background monitoring via AutomationOrchestrator
# Monitoring runs every 30 minutes to detect health degradation early
#


# ============================================================
# INSTRUMENTATION: Hook Execution Logging
# ============================================================
# Added by instrument_hooks.py on 2025-10-29T15:00:44.172813

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "periodic-monitor"
hook_start_time=$(date +%s%N)

# ============================================================
# HOOK BODY
# ============================================================

# Create timestamp
timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Log hook execution if debugging enabled
if [ -n "$CLAUDE_DEBUG" ]; then
  echo "[HOOK] PeriodicMonitor: Starting background monitoring at $timestamp" >&2
fi

# Detect project ID from working directory if not set
project_id="${PROJECT_ID:-1}"
if [ -z "$PROJECT_ID" ]; then
  # Try to auto-detect project from pwd
  pwd_path="$(pwd)"

  if [[ "$pwd_path" == *"memory-mcp"* ]]; then
    project_id=1
  elif [[ "$pwd_path" == *"web-app"* ]]; then
    project_id=2
  elif [[ "$pwd_path" == *"mobile-app"* ]]; then
    project_id=3
  fi
fi

# ============================================================
# Start Background Monitoring via Python
# ============================================================

monitor_status="pending"
monitor_result="{}"

python_cmd="python3"
if [ -f "/home/user/.work/athena/.venv/bin/python3" ]; then
  python_cmd="/home/user/.work/athena/.venv/bin/python3"
fi

# Start background monitoring in a detached process
start_monitoring_py=$(cat <<'PYTHON_MONITOR_BLOCK'
#!/usr/bin/env python3
"""Start periodic health monitoring via AutomationOrchestrator."""

import asyncio
import json
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[PeriodicMonitor] %(message)s"
)
logger = logging.getLogger(__name__)

async def start_monitoring(project_id: int):
    """Start background health monitoring."""
    try:
        # Import orchestrator
        sys.path.insert(0, str(Path("/home/user/.work/athena/src")))

        from memory_mcp.core.database import Database
        from memory_mcp.automation.orchestrator import AutomationOrchestrator

        # Initialize database and orchestrator
        db_path = Path.home() / ".memory-mcp" / "memory.db"
        db = Database(str(db_path))

        orchestrator = AutomationOrchestrator(db)

        # Start background monitoring
        await orchestrator.start_background_monitoring(project_id)

        logger.info(f"Background monitoring started for project {project_id}")

        # Return success status
        return {
            "status": "started",
            "project_id": project_id,
            "interval_minutes": 30
        }

    except Exception as e:
        logger.error(f"Failed to start monitoring: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

async def main():
    """Main entry point."""
    try:
        project_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
        result = await start_monitoring(project_id)
        print(json.dumps(result))
        sys.exit(0 if result.get("status") == "started" else 1)
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
PYTHON_MONITOR_BLOCK
)

# Run monitoring startup in background
monitor_output=$("$python_cmd" -c "$start_monitoring_py" "$project_id" 2>&1)

if echo "$monitor_output" | jq empty 2>/dev/null; then
  monitor_status=$(echo "$monitor_output" | jq -r '.status // "pending"')
  monitor_result="$monitor_output"

  if [ "$monitor_status" = "started" ]; then
    if [ -n "$CLAUDE_DEBUG" ]; then
      echo "[HOOK] Background monitoring started successfully for project $project_id" >&2
    fi
  else
    if [ -n "$CLAUDE_DEBUG" ]; then
      echo "[HOOK] Monitor status: $monitor_status" >&2
    fi
  fi
fi

# ============================================================
# Return Hook Response
# ============================================================

jq -n \
  --arg status "$monitor_status" \
  --arg project "$project_id" \
  --arg ts "$timestamp" \
  --argjson result "$monitor_result" \
  '{
    "continue": true,
    "suppressOutput": true,
    "hookSpecificOutput": {
      "hookEventName": "PeriodicMonitor",
      "status": $status,
      "project_id": ($project | tonumber),
      "timestamp": $ts,
      "monitoring_result": $result
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
  log_hook_success "periodic-monitor" "$hook_duration_ms" "Hook completed successfully"
else
  log_hook_failure "periodic-monitor" "$hook_duration_ms" "Hook exited with error"
fi

exit 0
