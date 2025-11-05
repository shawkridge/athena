#!/bin/bash
#
# MCP Wrapper - Bash interface to persistent MCP connection pool
#
# This library provides bash functions that use the Python MCP connection pool,
# avoiding Python startup overhead (50-100ms per invocation).
#
# Usage:
#   source ~/.claude/hooks/lib/mcp_wrapper.sh
#   mcp_smart_retrieve "query" 5 "HyDE"
#   mcp_record_episode "Event happened" "action" "session-123"
#

# Path to MCP pool module
MCP_POOL_MODULE="$HOME/.claude/hooks/lib/mcp_pool.py"

# ============================================================
# Smart Retrieve - Query memories with optional RAG strategy
# ============================================================
# Usage: mcp_smart_retrieve "query" [k] [strategy]
# Example: mcp_smart_retrieve "authentication bug" 5 "HyDE"
mcp_smart_retrieve() {
  local query="$1"
  local k="${2:-5}"
  local strategy="${3:-}"

  python3 << PYTHON_RETRIEVE
import json
import sys
sys.path.insert(0, "$HOME/.claude/hooks/lib")

from mcp_pool import smart_retrieve

try:
    results = smart_retrieve("$query", k=$k, strategy_hint="$strategy" if "$strategy" else None)
    print(json.dumps({"success": True, "results": results, "count": len(results)}))
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
PYTHON_RETRIEVE
}

# ============================================================
# Record Episode - Log an event to episodic memory
# ============================================================
# Usage: mcp_record_episode "content" "type" [session_id] [location]
# Example: mcp_record_episode "User asked about auth" "action" "session-123"
mcp_record_episode() {
  local content="$1"
  local event_type="$2"
  local session_id="${3:-}"
  local location="${4:-.}"

  python3 << PYTHON_RECORD
import json
import sys
sys.path.insert(0, "$HOME/.claude/hooks/lib")

from mcp_pool import record_episode

try:
    result = record_episode("$content", "$event_type", "$session_id", "$location")
    print(json.dumps(result))
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
PYTHON_RECORD
}

# ============================================================
# Get Working Memory Status - Check cognitive load
# ============================================================
# Usage: mcp_get_wm_status
mcp_get_wm_status() {
  python3 << PYTHON_WM
import json
import sys
sys.path.insert(0, "$HOME/.claude/hooks/lib")

from mcp_pool import get_working_memory_status

try:
    result = get_working_memory_status()
    print(json.dumps(result))
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
PYTHON_WM
}

# ============================================================
# Test MCP Connection - Verify pool is working
# ============================================================
# Usage: mcp_test_connection && echo "OK" || echo "Failed"
mcp_test_connection() {
  python3 << PYTHON_TEST
import sys
sys.path.insert(0, "$HOME/.claude/hooks/lib")

from mcp_pool import test_connection

try:
    if test_connection():
        print("OK")
        sys.exit(0)
    else:
        print("FAIL")
        sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
PYTHON_TEST
}

# ============================================================
# Parse JSON result from MCP call
# ============================================================
# Usage: result=$(mcp_smart_retrieve "query")
#        count=$(echo "$result" | jq -r '.count')
parse_mcp_result() {
  jq . 2>/dev/null || echo "{\"error\": \"Invalid JSON\"}"
}

export -f mcp_smart_retrieve mcp_record_episode mcp_get_wm_status mcp_test_connection parse_mcp_result
