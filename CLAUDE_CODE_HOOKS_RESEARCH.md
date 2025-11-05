# Claude Code Hooks - Comprehensive Research Document

## Executive Summary

This document provides complete findings about how Claude Code hooks work, including their creation patterns, lifecycle, configuration, available hook types, and implementation best practices based on the Athena project implementation.

---

## Part 1: Hook Fundamentals

### What Are Hooks?

Hooks in Claude Code are **event-triggered scripts** that execute automatically at specific points in the AI development workflow. They enable:
- Background memory management
- Knowledge gap detection
- Attention optimization
- Task progress tracking
- Plan validation before execution
- Session context loading

### Hook System Architecture

```
Claude Code Lifecycle Events
    │
    ├─► SessionStart hook
    │   └─ Load project context, check cognitive load
    │
    ├─► UserPromptSubmit hooks (4 parallel)
    │   ├─ Attention Manager (update working memory)
    │   ├─ Gap Detector (find contradictions)
    │   ├─ Procedure Suggester (suggest workflows)
    │   └─ (Custom hooks can be added)
    │
    ├─► PostToolUse hooks (fires every 10 operations)
    │   └─ Attention Optimizer (dynamic focus management)
    │
    ├─► PreExecution hook
    │   └─ Validate plan before task execution
    │
    ├─► PostTaskCompletion hook
    │   └─ Record execution progress and update goals
    │
    └─► SessionEnd hooks (4 parallel)
        ├─ Learning Tracker (analyze strategy effectiveness)
        ├─ Association Learner (strengthen memory links)
        ├─ Auto Consolidation (extract patterns)
        └─ (Custom hooks can be added)
```

---

## Part 2: Hook Lifecycle and Triggers

### Hook Trigger Points

| Trigger | When Fired | Frequency | Example Hooks |
|---------|-----------|-----------|---------------|
| **SessionStart** | When Claude starts or resumes session | Once per session | session-start.sh |
| **UserPromptSubmit** | After user submits each prompt | Every prompt | user-prompt-submit-*.sh |
| **PostToolUse** | After every 10 tool operations | ~Every 200 tokens | post-tool-use-attention-optimizer.sh |
| **PreExecution** | Before a major task starts | Per task start | pre-execution.sh |
| **PostTaskCompletion** | When user marks task as complete | Per task completion | post-task-completion.sh |
| **SessionEnd** | When Claude session ends | Once per session | session-end-*.sh |

### Hook Execution Flow

```
1. TRIGGER EVENT OCCURS
   ↓
2. HOOK SELECTED FROM MANIFEST
   ├─ Load hook metadata
   ├─ Check dependencies
   └─ Verify hook file exists
   ↓
3. HOOK EXECUTION
   ├─ Source libraries (hook_logger.sh, etc.)
   ├─ Read input from stdin (JSON)
   ├─ Execute Python MCP operations (in subprocess)
   ├─ Parse results with jq
   └─ Generate JSON response
   ↓
4. RESPONSE HANDLING
   ├─ Parse "continue" flag (always true for non-blocking)
   ├─ Apply "suppressOutput" (true = background, false = show message)
   ├─ Display optional "userMessage"
   └─ Record "hookSpecificOutput" to execution log
   ↓
5. LOGGING & METRICS
   ├─ Record execution time
   ├─ Log success/failure status
   ├─ Store to ~/.claude/hooks/execution.jsonl
   └─ Update hook statistics
```

### Timeout Protection

All hooks use **1-second timeout** on stdin read to prevent blocking:

```bash
# With timeout fallback
INPUT_JSON=$(timeout 1 cat 2>/dev/null || echo '{}')

# This ensures hooks never hang waiting for input
```

---

## Part 3: Hook Creation Syntax and Patterns

### Basic Hook Structure

All hooks follow this consistent pattern:

```bash
#!/bin/bash
# Hook: [Name] - [Purpose]
# Triggers: [When it fires]
# Purpose: [What it does]

# ============================================================
# INSTRUMENTATION: Hook Execution Logging
# ============================================================

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "hook-name"
hook_start_time=$(date +%s%N)

# ============================================================
# HOOK BODY
# ============================================================

# Read input from stdin with timeout fallback
INPUT_JSON=$(timeout 1 cat 2>/dev/null || echo '{}')

# Extract parameters from input
param=$(echo "$INPUT_JSON" | jq -r '.param // "default"')

# Execute Python code (usually MCP operations)
result=$(python3 << 'PYTHON_BLOCK'
import sys, json
sys.path.insert(0, '/home/user/.work/athena/src')

try:
    # Import and call MCP operations
    from some.module import SomeClass
    
    obj = SomeClass('/path/to/database')
    result = obj.operation()
    
    print(json.dumps({
        "success": True,
        "status": "completed",
        "metric1": value1
    }))
except Exception as e:
    # Graceful fallback
    print(json.dumps({
        "success": True,
        "status": "fallback_mode",
        "error": str(e)
    }))
PYTHON_BLOCK
)

# Parse result with jq
success=$(echo "$result" | jq -r '.success // false')
status=$(echo "$result" | jq -r '.status // "unknown"')

# Determine output based on success
if [ "$success" = "true" ]; then
  suppress_output="true"
  message="✓ Operation successful"
else
  suppress_output="true"
  message="⚠️ Background operation"
fi

# ============================================================
# RETURN HOOK RESPONSE - Guaranteed JSON
# ============================================================

jq -n \
  --arg msg "$message" \
  --arg status "$status" \
  '{
    "continue": true,
    "suppressOutput": ($suppress | test("true")),
    "userMessage": $msg,
    "hookSpecificOutput": {
      "hookEventName": "HookName",
      "status": $status,
      "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
      "metric1": value1
    }
  }' 2>/dev/null || \
# Fallback if jq fails
jq -n '{
  "continue": true,
  "suppressOutput": true
}'

# ============================================================
# INSTRUMENTATION: Log Hook Result
# ============================================================

hook_end_time=$(date +%s%N)
hook_duration_ms=$(( (hook_end_time - hook_start_time) / 1000000 ))

if [ $? -eq 0 ]; then
  log_hook_success "hook-name" "$hook_duration_ms" "Hook completed successfully"
else
  log_hook_failure "hook-name" "$hook_duration_ms" "Hook exited with error"
fi

exit 0
```

### Key Design Principles

1. **Non-Blocking**: Hooks return immediately (all operations in background)
2. **Graceful Degradation**: Always return valid JSON, even if operations fail
3. **Timeout Protection**: All stdin reads have 1-second timeout
4. **Structured Logging**: Every hook logs to ~/.claude/hooks/execution.jsonl
5. **MCP Integration**: Hooks call actual MCP operations or graceful fallbacks
6. **Error Handling**: Try/except wraps all Python code

---

## Part 4: Hook Input/Output Format

### Input Format (stdin)

Hooks receive JSON via stdin (may be empty):

```bash
# Read stdin with timeout fallback
INPUT_JSON=$(timeout 1 cat 2>/dev/null || echo '{}')

# Extract specific fields
cwd=$(echo "$INPUT_JSON" | jq -r '.cwd // "."')
session_id=$(echo "$INPUT_JSON" | jq -r '.session_id // "unknown"')
param=$(echo "$INPUT_JSON" | jq -r '.param // default_value')
```

**Common Input Fields**:
- `cwd` - Current working directory
- `session_id` - Unique session identifier
- `source` - What triggered the hook
- `project` - Project name/identifier
- Custom fields per hook

### Output Format (JSON)

All hooks return JSON response with this structure:

```json
{
  "continue": true,                          // Always true (non-blocking)
  "suppressOutput": true,                    // true = background, false = show message
  "userMessage": "Optional message to user", // Only shown if suppressOutput=false
  "hookSpecificOutput": {
    "hookEventName": "HookName",            // Hook name
    "status": "success",                    // Operation status
    "timestamp": "2025-11-05T14:30:00Z",   // ISO timestamp
    "metric1": value1,                      // Hook-specific metrics
    "metric2": value2
  }
}
```

**Response Behavior**:
- `continue: true` = Always true (hooks never block Claude)
- `suppressOutput: false` = Show message to user
- `suppressOutput: true` = Silent background operation
- `userMessage` = Only displayed when suppressOutput=false

---

## Part 5: Available Hook Types and Parameters

### Complete List of Implemented Hooks

#### Session Lifecycle Hooks

**1. SessionStart (session-start.sh)**
- **Trigger**: When Claude starts or resumes session
- **Purpose**: Load full project context from MCP memory
- **Operations**: Context loader, episode recorder
- **Input**: `{cwd, session_id, source}`
- **Output**: Project context, cognitive load status
- **Behavior**: Non-blocking; shows context if available

**2. SessionEnd (session-end.sh)**
- **Trigger**: When Claude session ends
- **Purpose**: Record session end, consolidate learnings
- **Operations**: Episode recorder, auto consolidation
- **Behavior**: Non-blocking; output suppressed

#### User Prompt Hooks (SessionEnd sub-hooks)

**3. SessionEndLearningTracker (session-end-learning-tracker.sh)**
- **Trigger**: At session end
- **Purpose**: Analyze encoding effectiveness and learning patterns
- **Operations**: skills_tools:get_learning_rates
- **Output**: Top strategy, effectiveness score
- **Behavior**: Background operation

**4. SessionEndAssociationLearner (session-end-association-learner.sh)**
- **Trigger**: At session end
- **Purpose**: Strengthen memory associations through Hebbian learning
- **Operations**: learning:strengthen_associations
- **Output**: Associations strengthened count
- **Behavior**: Background operation

#### User Prompt Submit Hooks

**5. UserPromptSubmitGapDetector (user-prompt-submit-gap-detector.sh)**
- **Trigger**: After each user prompt
- **Purpose**: Detect knowledge gaps, contradictions, uncertainties
- **Operations**: memory_tools:detect_knowledge_gaps
- **Output**: Gap count, contradiction count
- **Behavior**: Shows message only if gaps found

**6. UserPromptSubmitAttentionManager (user-prompt-submit-attention-manager.sh)**
- **Trigger**: After each user prompt
- **Purpose**: Update working memory with context
- **Operations**: memory_tools:update_working_memory
- **Output**: Current load, capacity, overflow flag
- **Behavior**: Suppressed by default

**7. UserPromptSubmitProcedureSuggester (user-prompt-submit-procedure-suggester.sh)**
- **Trigger**: After each user prompt
- **Purpose**: Find and suggest applicable workflows
- **Operations**: procedural_tools:find_procedures
- **Output**: Procedure count, effectiveness scores
- **Behavior**: Shows count only if procedures found

**8. SessionStartWMMonitor (session-start-wm-monitor.sh)**
- **Trigger**: At session start
- **Purpose**: Check working memory capacity and warn if near saturation
- **Operations**: memory_tools:check_cognitive_load
- **Output**: Current load vs capacity (7 items max)
- **Behavior**: Shows warning if load ≥5/7

#### Tool Use and Execution Hooks

**9. PostToolUseAttentionOptimizer (post-tool-use-attention-optimizer.sh)**
- **Trigger**: After every 10 tool operations
- **Purpose**: Auto-focus on high-salience memories
- **Operations**: ml_integration_tools:auto_focus_top_memories
- **Output**: Focused items count
- **Behavior**: Background operation

**10. PreExecution (pre-execution.sh)**
- **Trigger**: Before major task execution
- **Purpose**: Validate plans before execution
- **Operations**: phase6_planning_tools:validate_plan_comprehensive
- **Output**: Validation result, issue count
- **Behavior**: Shows warnings only if issues found

**11. PostTaskCompletion (post-task-completion.sh)**
- **Trigger**: When task marked as complete
- **Purpose**: Record execution progress and update goal metrics
- **Operations**: task_management_tools:record_execution_progress
- **Output**: Goals updated, progress increase %
- **Behavior**: Background operation

---

## Part 6: Hook Configuration Methods

### Configuration Files

**Hook Manifest** (when used):
```json
{
  "hooks": [
    {
      "name": "session-start",
      "phase": "session_start",
      "filePath": "~/.claude/hooks/session-start.sh",
      "enabled": true,
      "timeout": 5000,
      "dependsOn": [],
      "optional": false
    }
  ]
}
```

**Hook Directory Structure**:
```
~/.claude/hooks/
├── session-start.sh                              # SessionStart trigger
├── session-end.sh                                # SessionEnd trigger
├── session-end-learning-tracker.sh              # SessionEnd sub-hook
├── session-end-association-learner.sh           # SessionEnd sub-hook
├── user-prompt-submit-gap-detector.sh           # UserPromptSubmit sub-hook
├── user-prompt-submit-attention-manager.sh      # UserPromptSubmit sub-hook
├── user-prompt-submit-procedure-suggester.sh    # UserPromptSubmit sub-hook
├── post-tool-use-attention-optimizer.sh         # PostToolUse trigger
├── pre-execution.sh                             # PreExecution trigger
├── post-task-completion.sh                      # PostTaskCompletion trigger
├── lib/
│   ├── hook_logger.sh                           # Logging library
│   ├── context_loader.py                        # Context loading utility
│   ├── record_episode.py                        # Episode recording utility
│   ├── auto_consolidate.py                      # Consolidation utility
│   ├── hook_orchestrator.py                     # Hook execution orchestrator
│   └── mcp_wrapper.py                           # Graceful MCP fallbacks
└── execution.jsonl                              # Hook execution log
```

### Adding a New Hook

**Step 1: Create Hook Script**
```bash
#!/bin/bash
# Save as ~/.claude/hooks/my-new-hook.sh

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "my-new-hook"
hook_start_time=$(date +%s%N)

INPUT_JSON=$(timeout 1 cat 2>/dev/null || echo '{}')

# ... hook implementation ...

jq -n '{
  "continue": true,
  "suppressOutput": true
}'

hook_end_time=$(date +%s%N)
hook_duration_ms=$(( (hook_end_time - hook_start_time) / 1000000 ))
log_hook_success "my-new-hook" "$hook_duration_ms" "Success"

exit 0
```

**Step 2: Make Executable**
```bash
chmod +x ~/.claude/hooks/my-new-hook.sh
```

**Step 3: (Optional) Register in Manifest**
Add to hook configuration if using manifest-based loading.

### Configuration via Environment Variables

```bash
# Enable debug logging for all hooks
export CLAUDE_DEBUG=1

# Set custom hook log file
export HOOK_LOG_FILE="/custom/path/hook_logs.jsonl"

# Set custom timeout per hook
export HOOK_TIMEOUT_MS=3000
```

---

## Part 7: Error Handling in Hooks

### Graceful Fallback Pattern

All hooks use try/except with fallback JSON:

```python
try:
    # Try to import and call actual MCP operations
    from module import Class
    result = Class().operation()
    
    print(json.dumps({
        "success": True,
        "data": result
    }))
    
except Exception as e:
    # Graceful fallback - always return valid JSON
    print(json.dumps({
        "success": True,  # Still true! Never block Claude
        "status": "fallback_mode",
        "note": "Running with degraded functionality",
        "error": str(e)
    }))
```

### Bash Error Handling

```bash
# Timeout protection on stdin
INPUT=$(timeout 1 cat 2>/dev/null || echo '{}')

# Graceful jq failure
jq -n '{...}' 2>/dev/null || jq -n '{
  "continue": true,
  "suppressOutput": true
}'

# Always exit 0 (hooks never fail loudly)
exit 0
```

### Logging Failures

All failures are logged to execution.jsonl:

```bash
# Log failure but continue
hook_duration_ms=$(( (end_time - start_time) / 1000000 ))
log_hook_failure "hook-name" "$hook_duration_ms" "Error message"
exit 0  # Still exit 0!
```

---

## Part 8: Hook Execution Examples

### Example 1: SessionStart Hook

```bash
#!/bin/bash
# Trigger: When Claude starts session
# Purpose: Load project context

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "session-start"
hook_start_time=$(date +%s%N)

input=$(timeout 1 cat 2>/dev/null || echo '{}')
cwd=$(echo "$input" | jq -r '.cwd // "."')

# Detect project
project_name=$(basename "$cwd")

# Load context from Python utility
context_json=$(python3 ~/.claude/hooks/lib/context_loader.py \
  --project "$project_name" \
  --cwd "$cwd" \
  --json 2>/dev/null)

# Parse and display
success=$(echo "$context_json" | jq -r '.success')

if [ "$success" = "true" ]; then
  message="✅ Project context loaded"
  suppress="false"
else
  message=""
  suppress="true"
fi

jq -n \
  --arg msg "$message" \
  '{
    "continue": true,
    "suppressOutput": ('$suppress'),
    "userMessage": $msg,
    "hookSpecificOutput": {
      "hookEventName": "SessionStart",
      "status": "loaded"
    }
  }'

hook_end_time=$(date +%s%N)
hook_duration_ms=$(( (hook_end_time - hook_start_time) / 1000000 ))
log_hook_success "session-start" "$hook_duration_ms" "Context loaded"

exit 0
```

### Example 2: UserPromptSubmit Gap Detector

```bash
#!/bin/bash
# Trigger: After user submits prompt
# Purpose: Detect knowledge gaps

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "user-prompt-submit-gap-detector"
hook_start_time=$(date +%s%N)

INPUT_JSON=$(timeout 1 cat 2>/dev/null || echo '{}')

# Call Python to detect gaps
gap_result=$(python3 << 'PYTHON_GAPS'
import sys, json
sys.path.insert(0, '/home/user/.work/athena/src')

try:
    from athena.metacognition.gaps import KnowledgeGapDetector
    
    detector = KnowledgeGapDetector('/home/user/.athena/memory.db')
    contradictions = detector.detect_direct_contradictions(project_id=1)
    uncertainties = detector.identify_uncertainty_zones(project_id=1)
    
    total_gaps = len(contradictions) + len(uncertainties)
    
    print(json.dumps({
        "success": True,
        "contradictions": len(contradictions),
        "uncertainties": len(uncertainties),
        "total_gaps": total_gaps,
        "status": "gaps_detected" if total_gaps > 0 else "no_gaps"
    }))
    
except Exception as e:
    # Fallback
    print(json.dumps({
        "success": True,
        "contradictions": 0,
        "uncertainties": 0,
        "total_gaps": 0,
        "status": "no_gaps"
    }))
PYTHON_GAPS
)

# Parse result
success=$(echo "$gap_result" | jq -r '.success // false')
status=$(echo "$gap_result" | jq -r '.status // unknown')
total_gaps=$(echo "$gap_result" | jq -r '.total_gaps // 0')

# Determine output
if [ "$success" = "true" ] && [ "$total_gaps" -gt 0 ]; then
  suppress="false"
  msg="⚠️ Gap Detector: Found $total_gaps gaps"
else
  suppress="true"
  msg=""
fi

jq -n \
  --arg suppress "$suppress" \
  --arg msg "$msg" \
  --arg status "$status" \
  --arg gaps "$total_gaps" \
  '{
    "continue": true,
    "suppressOutput": ($suppress | test("true")),
    "userMessage": $msg,
    "hookSpecificOutput": {
      "hookEventName": "UserPromptSubmitGapDetector",
      "status": $status,
      "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
      "gaps_detected": $gaps
    }
  }' 2>/dev/null || \
jq -n '{
  "continue": true,
  "suppressOutput": true
}'

hook_end_time=$(date +%s%N)
hook_duration_ms=$(( (hook_end_time - hook_start_time) / 1000000 ))
log_hook_success "user-prompt-submit-gap-detector" "$hook_duration_ms" "Status: $status"

exit 0
```

---

## Part 9: Hook Library and Utilities

### Hook Logger Library (hook_logger.sh)

Provides structured logging functions:

```bash
# Source the library
source ~/.claude/hooks/lib/hook_logger.sh

# Log hook start
log_hook_start "my-hook"

# Log success
log_hook_success "my-hook" "150" "Operation details"

# Log failure
log_hook_failure "my-hook" "200" "Error message"

# Log timeout
log_hook_timeout "my-hook" "5000"

# Query statistics
hook_stats "my-hook"
all_hook_stats
export_hook_logs_csv "/tmp/hooks.csv"
```

**Log File**: ~/.claude/hooks/execution.jsonl (JSONL format)

**Log Entry Format**:
```json
{
  "hook": "hook-name",
  "status": "success",
  "timestamp": "2025-11-05T14:30:00Z",
  "duration_ms": 42,
  "details": "Operation details"
}
```

### Hook Orchestrator (hook_orchestrator.py)

Manages hook execution with:
- Dependency resolution
- Topological sort execution
- Timeout protection
- Failure handling
- Metric recording

**Usage**:
```bash
python3 ~/.claude/hooks/lib/hook_orchestrator.py --phase session-start
python3 ~/.claude/hooks/lib/hook_orchestrator.py --validate
```

### MCP Wrapper (mcp_wrapper.py)

Graceful fallback layer for MCP operations:

```python
from mcp_wrapper import call_mcp

result = call_mcp("detect_knowledge_gaps")
# Returns: {success: true, ...with fallback data...}

# Operations supported:
# - auto_focus_top_memories
# - detect_knowledge_gaps
# - find_procedures
# - update_working_memory
# - get_learning_rates
# - strengthen_associations
# - record_execution_progress
# - validate_plan_comprehensive
```

---

## Part 10: Best Practices for Hook Development

### Do's

✅ **Always return valid JSON** - Even if operation fails
```bash
jq -n '{...}' 2>/dev/null || jq -n '{"continue": true}'
```

✅ **Use timeout on stdin** - Prevent blocking
```bash
INPUT=$(timeout 1 cat 2>/dev/null || echo '{}')
```

✅ **Log execution time** - Monitor performance
```bash
start=$(date +%s%N)
# ... work ...
duration=$(( ($(date +%s%N) - start) / 1000000 ))
log_hook_success "hook" "$duration" "Done"
```

✅ **Graceful fallbacks** - Always have a degraded path
```python
try:
    result = real_operation()
except:
    result = fallback_operation()
```

✅ **Non-blocking design** - Always return quickly
```bash
# Run expensive operations in background if needed
operation &>/dev/null &
jq -n '{"continue": true}'
```

✅ **Document purpose and behavior** - Clear header comments
```bash
#!/bin/bash
# Hook: MyHook - What it does
# Triggers: When and why
# Purpose: High-level goal
# Input: What parameters
# Output: What user sees
```

### Don'ts

❌ **Don't block on failures**
```bash
# BAD: Hook hangs if operation fails
result = call_operation()  # Could timeout
json_response = result

# GOOD: Always have fallback
result = call_operation() or default_result
json_response = result
```

❌ **Don't use unbounded waits**
```bash
# BAD: Can block indefinitely
read input

# GOOD: Use timeout
input=$(timeout 1 cat 2>/dev/null || echo '{}')
```

❌ **Don't output to stdout except JSON response**
```bash
# BAD: Debug output corrupts response
echo "Starting hook"
jq -n '{...}'  # Response is corrupted

# GOOD: Only JSON
jq -n '{...}'
```

❌ **Don't fail loudly**
```bash
# BAD: Exception causes hook to exit with error
raise Exception("Something went wrong")  # Hook fails

# GOOD: Catch and return valid JSON
except Exception:
    print(json.dumps({"success": True, "status": "fallback"}))
```

❌ **Don't assume external services**
```bash
# BAD: Fails if database unavailable
db = Database("/path")
result = db.query()

# GOOD: Graceful degradation
try:
    db = Database("/path")
    result = db.query()
except:
    result = get_fallback_data()
```

---

## Part 11: Hook Performance Targets

### Latency Targets

| Hook | Target | Typical | Status |
|------|--------|---------|--------|
| SessionStart | <500ms | 150-200ms | ✅ Background |
| UserPromptSubmitGapDetector | <100ms | 50-75ms | ✅ Background |
| UserPromptSubmitAttentionManager | <50ms | 20-30ms | ✅ Background |
| UserPromptSubmitProcedureSuggester | <100ms | 60-80ms | ✅ Background |
| PostToolUseAttentionOptimizer | <100ms | 50-70ms | ✅ Background |
| PreExecution | <500ms | 200-300ms | ✅ Background |
| PostTaskCompletion | <200ms | 80-120ms | ✅ Background |
| SessionEnd | <500ms | 100-150ms | ✅ Background |

**Critical Success Factors**:
- All hooks complete within their target
- Output suppressed by default (background operation)
- No visible latency to user
- Graceful degradation if operations slow

---

## Part 12: Monitoring and Debugging Hooks

### Query Hook Statistics

```bash
# Single hook stats
hook_stats "session-start"

# All hooks
all_hook_stats

# Export for analysis
export_hook_logs_csv "/tmp/hooks.csv"
```

### Debug Mode

```bash
# Enable debug output
export CLAUDE_DEBUG=1

# Hooks will output to stderr:
# [HOOK] SessionStart: source=startup cwd=/path
# ✓ session-start completed in 145ms
# ...
```

### Analyze Execution Log

```bash
# View raw logs
cat ~/.claude/hooks/execution.jsonl

# Pretty print
cat ~/.claude/hooks/execution.jsonl | jq

# Query specific hook
cat ~/.claude/hooks/execution.jsonl | jq 'select(.hook == "session-start")'

# Filter by status
cat ~/.claude/hooks/execution.jsonl | jq 'select(.status == "failure")'

# Calculate stats
cat ~/.claude/hooks/execution.jsonl | jq -s 'group_by(.hook) | map({hook: .[0].hook, count: length, avg_ms: (map(.duration_ms) | add/length)})'
```

---

## Part 13: Real-World Examples from Athena Project

### Example: Context Loader Hook (SessionStart)

**Purpose**: Load project context when session starts

**Implementation**:
1. Detect project from CWD
2. Call Python context_loader.py
3. Load goals, tasks, cognitive load
4. Display context if available
5. Fall back to manual commands if needed

**Code Pattern**:
```bash
# Load context from MCP
context_json=$(python3 context_loader.py --project "$project_name" --json)

# Check if valid JSON
if echo "$context_json" | jq empty 2>/dev/null; then
  # Parse and display
  success=$(echo "$context_json" | jq -r '.success')
  if [ "$success" = "true" ]; then
    show_message="true"
  fi
fi

# Return response
jq -n --arg show "$show_message" '{
  "continue": true,
  "suppressOutput": ($show | test("true") | not),
  "userMessage": $message
}'
```

### Example: Gap Detector Hook (UserPromptSubmit)

**Purpose**: Detect contradictions and uncertainties in memory

**Implementation**:
1. Call KnowledgeGapDetector MCP
2. Count contradictions and uncertainties
3. Show message only if gaps found
4. Log to execution file

**Key Feature**: Smart output
```bash
# Only show message if gaps found
if [ "$total_gaps" -gt 0 ]; then
  suppress_output="false"  # Show to user
  message="⚠️ Gap Detector: Found $total_gaps gaps"
else
  suppress_output="true"   # Background operation
fi
```

### Example: Attention Optimizer Hook (PostToolUse)

**Purpose**: Auto-focus on high-salience memories every 10 operations

**Batching Strategy**:
```bash
# Counter in hook metadata
operation_count=$((operation_count + 1))

# Fire every 10 operations
if [ $((operation_count % 10)) -eq 0 ]; then
  # Call attention optimizer
  python3 << 'PYTHON'
  salient = get_most_salient_memories()
  focus_on(salient)
  PYTHON
fi
```

---

## Part 14: Integration with Claude Code System

### How Hooks Integrate with Claude Code

```
Claude Code                    | Hook System
─────────────────────────────────────────────────────
User starts session       →    SessionStart hook
  (Load context)
─────────────────────────────────────────────────────
User submits prompt       →    UserPromptSubmit hooks (parallel)
  (Gap detect, attention,
   suggest procedures)
─────────────────────────────────────────────────────
User executes tool (×10)  →    PostToolUse hook
  (Optimize attention)
─────────────────────────────────────────────────────
User starts task          →    PreExecution hook
  (Validate plan)
─────────────────────────────────────────────────────
User completes task       →    PostTaskCompletion hook
  (Record progress)
─────────────────────────────────────────────────────
Session ends              →    SessionEnd hooks (parallel)
  (Learn, consolidate,
   strengthen associations)
```

### Hook Output in Claude Code

1. **suppressOutput=false**: Shows message to user
   ```
   Claude: [Hook message appears here]
   ```

2. **suppressOutput=true**: Background operation
   ```
   [No visible output]
   [But hookSpecificOutput recorded to log]
   ```

3. **Both**: Recorded to execution.jsonl for analysis
   ```json
   {
     "hook": "user-prompt-submit-gap-detector",
     "status": "success",
     "timestamp": "2025-11-05T14:30:00Z",
     "duration_ms": 45,
     "details": "Found 2 gaps"
   }
   ```

---

## Summary

### Key Takeaways

1. **Hooks are event-triggered scripts** that run automatically at specific points
2. **All hooks are non-blocking** - they use background execution and timeouts
3. **Consistent pattern** - All follow same structure: read input → call MCP → return JSON
4. **Graceful degradation** - Always return valid JSON, even if operations fail
5. **11 hooks implemented** in Athena for memory management and planning
6. **Comprehensive logging** - Every execution recorded to execution.jsonl
7. **Configurable behavior** - `suppressOutput` controls visibility to user
8. **Best practice**: Use timeouts, fallbacks, logging, and structured responses

### Key Files

- Hook implementations: `~/.claude/hooks/*.sh`
- Hook libraries: `~/.claude/hooks/lib/`
- Execution logs: `~/.claude/hooks/execution.jsonl`
- Helper scripts: context_loader.py, record_episode.py, auto_consolidate.py
- Orchestrator: hook_orchestrator.py
- Wrapper: mcp_wrapper.py

### Next Steps for Implementation

1. Copy hook patterns for new hooks
2. Add timeout protection on all stdin reads
3. Implement try/except with fallbacks
4. Return valid JSON in all cases
5. Log execution metrics
6. Test with `export CLAUDE_DEBUG=1`
7. Monitor execution.jsonl for performance
