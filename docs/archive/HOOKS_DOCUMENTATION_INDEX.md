# Claude Code Hooks - Documentation Index

## Documents Created

This research produced **3 comprehensive documents** about Claude Code hooks:

### 1. CLAUDE_CODE_HOOKS_RESEARCH.md (30 KB)
**Full comprehensive reference** with 14 sections covering every aspect of hooks.

**Contents**:
- Part 1: Hook Fundamentals (system architecture)
- Part 2: Hook Lifecycle and Triggers (execution flow)
- Part 3: Hook Creation Syntax and Patterns (template + principles)
- Part 4: Hook Input/Output Format (JSON contracts)
- Part 5: Available Hook Types and Parameters (all 11 hooks documented)
- Part 6: Hook Configuration Methods (setup and directory structure)
- Part 7: Error Handling in Hooks (graceful fallbacks)
- Part 8: Hook Execution Examples (real code from Athena)
- Part 9: Hook Library and Utilities (logger, orchestrator, wrapper)
- Part 10: Best Practices (do's and don'ts)
- Part 11: Hook Performance Targets (latency goals)
- Part 12: Monitoring and Debugging Hooks (observability)
- Part 13: Real-World Examples from Athena Project (3 detailed examples)
- Part 14: Integration with Claude Code System (how it all fits together)

**Use this for**: Deep understanding, implementation reference, advanced topics

### 2. CLAUDE_CODE_HOOKS_SUMMARY.md (Quick Reference)
**Condensed cheat sheet** for quick lookup and copy-paste templates.

**Contents**:
- Overview and quick facts
- Hook triggers table
- File locations tree
- Basic hook template (copy-paste ready)
- Input/output JSON format
- All 11 hooks listed with descriptions
- Key design principles
- Error handling pattern
- Monitoring commands
- Performance targets
- Common code patterns
- Best/worst practices

**Use this for**: Quick reference, copy templates, cheat sheet during development

### 3. HOOKS_DOCUMENTATION_INDEX.md (This File)
**Navigation guide** to all hook documentation and files.

---

## Quick Navigation

### I want to...

**...understand how hooks work**
→ Read CLAUDE_CODE_HOOKS_RESEARCH.md (Part 1-3)

**...create a new hook**
→ Read CLAUDE_CODE_HOOKS_SUMMARY.md "Creating a New Hook" + "Basic Hook Template"
→ Reference CLAUDE_CODE_HOOKS_RESEARCH.md Part 3 for patterns

**...debug a failing hook**
→ Read CLAUDE_CODE_HOOKS_RESEARCH.md Part 7 (Error Handling)
→ Use commands in CLAUDE_CODE_HOOKS_SUMMARY.md "Monitoring Hooks"
→ Enable `export CLAUDE_DEBUG=1`

**...understand hook execution order**
→ Read CLAUDE_CODE_HOOKS_RESEARCH.md Part 2 (Lifecycle)

**...see all hook types**
→ Read CLAUDE_CODE_HOOKS_RESEARCH.md Part 5 (Available Hooks)
→ Or CLAUDE_CODE_HOOKS_SUMMARY.md "All 11 Hooks"

**...monitor hook performance**
→ Read CLAUDE_CODE_HOOKS_RESEARCH.md Part 11-12 (Performance + Monitoring)

**...see code examples**
→ Read CLAUDE_CODE_HOOKS_RESEARCH.md Part 8 (Hook Execution Examples)
→ Or Part 13 (Real-World Examples from Athena)

**...follow best practices**
→ Read CLAUDE_CODE_HOOKS_RESEARCH.md Part 10 (Best Practices)
→ Or CLAUDE_CODE_HOOKS_SUMMARY.md "Best/Worst Practices"

**...understand hook configuration**
→ Read CLAUDE_CODE_HOOKS_RESEARCH.md Part 6 (Configuration Methods)

---

## Key Concepts Summary

### What Are Hooks?
Event-triggered bash scripts that run automatically at specific Claude Code lifecycle points. They enable background operations like memory management, gap detection, and plan validation.

### Design Philosophy
- **Non-blocking** - Always return immediately
- **Gracefully degraded** - Always return valid JSON, even on failure
- **Well-logged** - Every execution recorded with metrics
- **Timeout protected** - 1-second stdin timeout prevents hanging
- **Composable** - Can be chained with dependencies

### Hook Lifecycle
1. Trigger event occurs (SessionStart, UserPromptSubmit, etc.)
2. Hook selected from manifest
3. Hook script executes
4. Python MCP operation called (with fallback)
5. Result parsed with jq
6. JSON response returned (always valid)
7. Output recorded to execution.jsonl
8. Always exit code 0 (non-blocking)

### All 11 Hooks at a Glance

**SessionStart** (1)
- session-start.sh - Load context

**UserPromptSubmit** (4)
- user-prompt-submit-gap-detector.sh - Find gaps
- user-prompt-submit-attention-manager.sh - Update WM
- user-prompt-submit-procedure-suggester.sh - Suggest workflows
- session-start-wm-monitor.sh - Check capacity

**PostToolUse** (1)
- post-tool-use-attention-optimizer.sh - Focus every 10 ops

**PreExecution** (1)
- pre-execution.sh - Validate plan

**PostTaskCompletion** (1)
- post-task-completion.sh - Record progress

**SessionEnd** (3)
- session-end.sh - Record end
- session-end-learning-tracker.sh - Analyze strategies
- session-end-association-learner.sh - Strengthen links

### Hook Input/Output Contract

**Input** (JSON via stdin):
```json
{
  "cwd": "current/working/directory",
  "session_id": "unique-id",
  "source": "trigger-type",
  "project": "project-name"
}
```

**Output** (Always valid JSON):
```json
{
  "continue": true,
  "suppressOutput": true,
  "userMessage": "Optional",
  "hookSpecificOutput": {
    "hookEventName": "HookName",
    "status": "success",
    "timestamp": "ISO-8601",
    "metrics": {}
  }
}
```

### Error Handling Pattern

All hooks follow this pattern:
```bash
# Python level: try/except with fallback
# Bash level: jq with fallback
# Exit: Always 0 (non-blocking)
```

Result: Hooks never fail Claude execution

---

## Implementation Reference

### Hook Template (Copy-Paste Ready)

See CLAUDE_CODE_HOOKS_SUMMARY.md "Basic Hook Template" for full code.

Key sections:
1. Logging setup
2. Input reading (with timeout)
3. Python operation (try/except)
4. Result parsing (jq)
5. JSON response (with fallback)
6. Logging completion

### Common Patterns

**Pattern 1: Show output only if results found**
```bash
if [ "$count" -gt 0 ]; then
  suppress="false"
  msg="Found $count items"
else
  suppress="true"
fi
```

**Pattern 2: Always return valid JSON**
```bash
jq -n '{...}' 2>/dev/null || \
jq -n '{"continue": true, "suppressOutput": true}'
```

**Pattern 3: Timeout on stdin**
```bash
INPUT=$(timeout 1 cat 2>/dev/null || echo '{}')
```

**Pattern 4: Graceful MCP fallback**
```python
try:
    result = mcp_operation()
except:
    result = fallback_data()
```

### Performance Targets

All hooks should complete in <500ms (most <100ms):
- SessionStart: <500ms
- UserPromptSubmit hooks: <100ms each
- PostToolUse hooks: <100ms
- PreExecution: <500ms
- PostTaskCompletion: <200ms
- SessionEnd hooks: <500ms

---

## File Locations

### Hook Scripts
```
~/.claude/hooks/
├── session-start.sh
├── session-end.sh
├── user-prompt-submit-gap-detector.sh
├── user-prompt-submit-attention-manager.sh
├── user-prompt-submit-procedure-suggester.sh
├── session-start-wm-monitor.sh
├── post-tool-use-attention-optimizer.sh
├── pre-execution.sh
├── post-task-completion.sh
├── session-end-learning-tracker.sh
└── session-end-association-learner.sh
```

### Hook Libraries
```
~/.claude/hooks/lib/
├── hook_logger.sh           # Logging functions
├── context_loader.py        # Context utilities
├── record_episode.py        # Episode recording
├── auto_consolidate.py      # Consolidation utility
├── hook_orchestrator.py     # Execution manager
└── mcp_wrapper.py           # MCP fallbacks
```

### Logging
```
~/.claude/hooks/execution.jsonl  # JSONL execution log
```

### Documentation
```
/home/user/.work/athena/
├── CLAUDE_CODE_HOOKS_RESEARCH.md     # Comprehensive (14 parts)
├── CLAUDE_CODE_HOOKS_SUMMARY.md      # Quick reference
└── HOOKS_DOCUMENTATION_INDEX.md      # Navigation (this file)
```

---

## Monitoring and Debugging

### View Execution Logs
```bash
cat ~/.claude/hooks/execution.jsonl | jq
```

### Get Hook Statistics
```bash
source ~/.claude/hooks/lib/hook_logger.sh
all_hook_stats
hook_stats "hook-name"
```

### Enable Debug Mode
```bash
export CLAUDE_DEBUG=1
# Hooks will output debug info to stderr
```

### Analyze Performance
```bash
cat ~/.claude/hooks/execution.jsonl | \
  jq -s 'group_by(.hook) | \
    map({
      hook: .[0].hook,
      count: length,
      avg_ms: (map(.duration_ms) | add/length),
      max_ms: (map(.duration_ms) | max)
    })'
```

---

## Best Practices Checklist

When creating hooks, ensure:

✅ **Structure**
- [ ] Uses logging library (hook_logger.sh)
- [ ] Has descriptive header comments
- [ ] Follows consistent pattern

✅ **Input/Output**
- [ ] Reads stdin with 1-second timeout
- [ ] Always returns valid JSON
- [ ] Has fallback for jq failures

✅ **Error Handling**
- [ ] Python code has try/except
- [ ] Falls back to sensible defaults
- [ ] Always exits with code 0

✅ **Performance**
- [ ] Completes in <500ms
- [ ] Timeout protected
- [ ] Suppresses output by default

✅ **Logging**
- [ ] Logs start time
- [ ] Logs success/failure with details
- [ ] Records execution duration
- [ ] Includes metrics in output

✅ **Observability**
- [ ] hookSpecificOutput includes metrics
- [ ] Status messages are clear
- [ ] Timestamps in ISO-8601 format

---

## Common Tasks

### Create a New Hook
1. Create file: `~/.claude/hooks/my-hook.sh`
2. Use template from CLAUDE_CODE_HOOKS_SUMMARY.md
3. Implement operation (Python or bash)
4. Add try/except fallback
5. Return valid JSON response
6. Make executable: `chmod +x`
7. Test with `export CLAUDE_DEBUG=1`

### Debug a Failing Hook
1. Enable debug: `export CLAUDE_DEBUG=1`
2. Check execution.jsonl: `cat ~/.claude/hooks/execution.jsonl | jq 'select(.hook == "hook-name")'`
3. Review error message in log
4. Test hook directly: `echo '{}' | bash ~/.claude/hooks/hook-name.sh`
5. Check Python fallback is working

### Monitor Hook Performance
1. View all stats: `source ~/.claude/hooks/lib/hook_logger.sh && all_hook_stats`
2. Check specific hook: `hook_stats "hook-name"`
3. Export for analysis: `export_hook_logs_csv /tmp/hooks.csv`

### Add New Trigger
1. Create hook script for new trigger
2. Document in hook header
3. Add to manifest (if using)
4. Test with `export CLAUDE_DEBUG=1`

---

## Research Methodology

This research was conducted by:

1. **Code Analysis** - Examined all 11 hook implementations
2. **Documentation Review** - Analyzed hook lifecycle documentation
3. **Architecture Study** - Reviewed hook orchestrator and logger
4. **Pattern Recognition** - Identified consistent patterns across hooks
5. **Best Practices Extraction** - Documented observed best practices
6. **Real-World Examples** - Provided examples from Athena project

**Sources**:
- ~/.claude/hooks/ (11 hook implementations)
- ~/.claude/hooks/lib/ (Hook libraries and utilities)
- /home/user/.work/athena/ (Architecture and implementation docs)
- /home/user/.work/athena/PHASE_1_1_HOOKS_COMPLETE.md (Hook specifications)
- /home/user/.work/athena/HOOK_FIXES_DOCUMENTATION.md (Error handling)

---

## Document Versions

| Document | Lines | Status | Last Updated |
|----------|-------|--------|--------------|
| CLAUDE_CODE_HOOKS_RESEARCH.md | 1000+ | Complete | 2025-11-05 |
| CLAUDE_CODE_HOOKS_SUMMARY.md | 400+ | Complete | 2025-11-05 |
| HOOKS_DOCUMENTATION_INDEX.md | 300+ | Complete | 2025-11-05 |

---

## Quick Links

- **Comprehensive Reference**: CLAUDE_CODE_HOOKS_RESEARCH.md
- **Quick Cheat Sheet**: CLAUDE_CODE_HOOKS_SUMMARY.md
- **Hook Template**: CLAUDE_CODE_HOOKS_SUMMARY.md → "Basic Hook Template"
- **All Hook Types**: CLAUDE_CODE_HOOKS_RESEARCH.md Part 5
- **Error Handling**: CLAUDE_CODE_HOOKS_RESEARCH.md Part 7
- **Best Practices**: CLAUDE_CODE_HOOKS_RESEARCH.md Part 10
- **Monitoring**: CLAUDE_CODE_HOOKS_RESEARCH.md Part 12
- **Real Examples**: CLAUDE_CODE_HOOKS_RESEARCH.md Part 13

---

**Complete Research Package**: 3 Documents, 1700+ Lines of Documentation
**Status**: ✅ Complete and Ready for Use
**Date**: 2025-11-05
