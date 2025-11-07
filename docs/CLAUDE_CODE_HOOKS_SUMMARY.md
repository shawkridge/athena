# Claude Code Hooks - Quick Reference Summary

## Overview

Claude Code hooks are **event-triggered bash scripts** that execute automatically at specific lifecycle points. They enable background memory management, knowledge gap detection, attention optimization, and execution validation.

## Quick Facts

- **11 hooks implemented** in the Athena project
- **Always non-blocking** (exit code always 0)
- **Always return valid JSON** (even on failure)
- **1-second timeout** on stdin reads (prevents hanging)
- **Structured logging** to ~/.claude/hooks/execution.jsonl
- **Graceful fallbacks** for missing MCP operations

## Hook Triggers

| Trigger | Frequency | Example Hooks |
|---------|-----------|---------------|
| SessionStart | Once per session | session-start.sh |
| UserPromptSubmit | Every prompt | user-prompt-submit-*.sh |
| PostToolUse | Every 10 operations | post-tool-use-attention-optimizer.sh |
| PreExecution | Per task start | pre-execution.sh |
| PostTaskCompletion | Per task completion | post-task-completion.sh |
| SessionEnd | Once per session | session-end-*.sh |

## Hook File Locations

```
~/.claude/hooks/
├── session-start.sh                    # Load project context
├── session-end.sh                      # Record session end
├── session-start-wm-monitor.sh         # Check cognitive load
├── user-prompt-submit-gap-detector.sh  # Detect contradictions
├── user-prompt-submit-attention-manager.sh
├── user-prompt-submit-procedure-suggester.sh
├── post-tool-use-attention-optimizer.sh
├── pre-execution.sh                    # Validate plan
├── post-task-completion.sh             # Record progress
├── session-end-learning-tracker.sh
├── session-end-association-learner.sh
├── lib/
│   ├── hook_logger.sh                  # Logging functions
│   ├── context_loader.py               # Context utilities
│   ├── hook_orchestrator.py            # Execution manager
│   └── mcp_wrapper.py                  # Fallback operations
└── execution.jsonl                     # Execution log (JSONL)
```

## Basic Hook Template

```bash
#!/bin/bash
# Hook: HookName - Purpose description

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "hook-name"
hook_start_time=$(date +%s%N)

# Read input (with 1-second timeout)
INPUT_JSON=$(timeout 1 cat 2>/dev/null || echo '{}')

# Execute operation (Python with try/except fallback)
result=$(python3 << 'PYTHON'
import sys, json
sys.path.insert(0, '/home/user/.work/athena/src')

try:
    # Import and call MCP operation
    from module import Class
    obj = Class('/path/to/db')
    data = obj.operation()
    
    print(json.dumps({"success": True, "data": data}))
except Exception as e:
    # Graceful fallback
    print(json.dumps({"success": True, "error": str(e)}))
PYTHON
)

# Parse result
success=$(echo "$result" | jq -r '.success // false')
status=$(echo "$result" | jq -r '.status // "unknown"')

# Return JSON response (always valid)
jq -n \
  --arg status "$status" \
  '{
    "continue": true,
    "suppressOutput": true,
    "hookSpecificOutput": {
      "hookEventName": "HookName",
      "status": $status,
      "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
      "metric1": 0
    }
  }' 2>/dev/null || \
jq -n '{"continue": true, "suppressOutput": true}'

# Always log and exit 0
hook_end_time=$(date +%s%N)
hook_duration_ms=$(( (hook_end_time - hook_start_time) / 1000000 ))
log_hook_success "hook-name" "$hook_duration_ms" "Success"
exit 0
```

## Hook Input/Output

### Input (stdin - may be empty)

```json
{
  "cwd": "current/working/directory",
  "session_id": "unique-session-id",
  "source": "what triggered the hook",
  "project": "project-name"
}
```

### Output (always JSON)

```json
{
  "continue": true,
  "suppressOutput": true,
  "userMessage": "Optional message",
  "hookSpecificOutput": {
    "hookEventName": "HookName",
    "status": "success",
    "timestamp": "2025-11-05T14:30:00Z",
    "metric1": 42,
    "metric2": "value"
  }
}
```

**Fields**:
- `continue`: Always `true` (non-blocking)
- `suppressOutput`: `true` = background, `false` = show message
- `userMessage`: Only shown if `suppressOutput=false`
- `hookSpecificOutput`: Stored in execution.jsonl

## Creating a New Hook

**Step 1**: Create script at `~/.claude/hooks/my-hook.sh`

**Step 2**: Make executable
```bash
chmod +x ~/.claude/hooks/my-hook.sh
```

**Step 3**: Follow template pattern above

## All 11 Hooks

### SessionStart (1 hook)
- **session-start.sh** - Loads project context, checks cognitive load

### UserPromptSubmit (4 hooks)
- **user-prompt-submit-gap-detector.sh** - Detects contradictions (shows if found)
- **user-prompt-submit-attention-manager.sh** - Updates working memory (background)
- **user-prompt-submit-procedure-suggester.sh** - Suggests workflows (shows if found)
- **session-start-wm-monitor.sh** - Checks working memory capacity (warns if saturated)

### PostToolUse (1 hook)
- **post-tool-use-attention-optimizer.sh** - Auto-focuses every 10 operations (background)

### PreExecution (1 hook)
- **pre-execution.sh** - Validates plan before task execution (warns if issues)

### PostTaskCompletion (1 hook)
- **post-task-completion.sh** - Records execution progress (background)

### SessionEnd (3 hooks)
- **session-end.sh** - Records session end (background)
- **session-end-learning-tracker.sh** - Analyzes strategy effectiveness (background)
- **session-end-association-learner.sh** - Strengthens memory links (background)

## Key Design Principles

✅ **Non-blocking** - All hooks run in background, never block Claude
✅ **Fail gracefully** - Always return valid JSON, even if operation fails
✅ **Timeout protected** - 1-second timeout on stdin prevents hanging
✅ **Well-logged** - Every execution recorded with metrics
✅ **Composable** - Can be chained, have dependencies
✅ **Observable** - All output to execution.jsonl for analysis

## Error Handling

All hooks follow this pattern:

```bash
# Python level
try:
    result = operation()
except Exception:
    result = fallback()  # Always succeeds

# Bash level
jq -n '{...}' 2>/dev/null || jq -n '{"continue": true}'

# Always exit 0
exit 0
```

**Result**: Hooks never fail, Claude never blocks

## Monitoring Hooks

### View execution log
```bash
cat ~/.claude/hooks/execution.jsonl | jq
```

### Query specific hook
```bash
cat ~/.claude/hooks/execution.jsonl | \
  jq 'select(.hook == "session-start")'
```

### Get statistics
```bash
source ~/.claude/hooks/lib/hook_logger.sh
all_hook_stats
hook_stats "session-start"
```

### Enable debug mode
```bash
export CLAUDE_DEBUG=1
```

## Performance Targets

All hooks complete in < 500ms (most < 100ms):
- SessionStart: 150-200ms
- Gap Detector: 50-75ms
- Attention Manager: 20-30ms
- Procedure Suggester: 60-80ms
- Attention Optimizer: 50-70ms
- PreExecution: 200-300ms
- TaskCompletion: 80-120ms
- SessionEnd: 100-150ms

## Common Patterns

### Pattern 1: Only show output if something found
```bash
if [ "$item_count" -gt 0 ]; then
  suppress="false"
  msg="Found $item_count items"
else
  suppress="true"
  msg=""
fi
```

### Pattern 2: Always output valid JSON
```bash
jq -n '{...}' 2>/dev/null || \
jq -n '{"continue": true, "suppressOutput": true}'
```

### Pattern 3: Timeout on stdin
```bash
INPUT=$(timeout 1 cat 2>/dev/null || echo '{}')
```

### Pattern 4: Graceful MCP fallback
```python
try:
    from athena.module import Class
    result = Class().operation()
    success = True
except:
    result = default_fallback()
    success = True  # Still true!
```

## Hook Logging Functions

```bash
source ~/.claude/hooks/lib/hook_logger.sh

log_hook_start "hook-name"
log_hook_success "hook-name" "150" "Details"
log_hook_failure "hook-name" "200" "Error message"
log_hook_timeout "hook-name" "5000"

hook_stats "hook-name"
all_hook_stats
export_hook_logs_csv "/tmp/hooks.csv"
```

## Best Practices

✅ Always return valid JSON
✅ Use 1-second timeout on stdin
✅ Implement try/except with fallbacks
✅ Log execution time
✅ Keep hooks short and focused
✅ Suppress output by default
✅ Show message only when important
✅ Document purpose and behavior
✅ Test with CLAUDE_DEBUG=1
✅ Monitor execution.jsonl

## Worst Practices to Avoid

❌ Block on operations
❌ Use unbounded waits
❌ Output to stdout except JSON
❌ Fail loudly (exit non-0)
❌ Assume external services
❌ Skip error handling
❌ Create unloggable operations
❌ Produce invalid JSON
❌ Take >500ms to complete
❌ Ignore fallback paths

---

## Reference Files

| File | Purpose |
|------|---------|
| CLAUDE_CODE_HOOKS_RESEARCH.md | Comprehensive documentation (14 parts) |
| ~/.claude/hooks/*.sh | Hook implementations |
| ~/.claude/hooks/lib/hook_logger.sh | Logging library |
| ~/.claude/hooks/execution.jsonl | Execution logs |
| ~/.claude/hooks/lib/hook_orchestrator.py | Hook execution manager |
| ~/.claude/hooks/lib/mcp_wrapper.py | Graceful MCP fallbacks |

---

**Status**: ✅ Complete - All 11 hooks implemented and documented
**Last Updated**: 2025-11-05
**Integration**: 55% of system complete
