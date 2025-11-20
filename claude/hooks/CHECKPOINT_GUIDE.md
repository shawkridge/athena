# Pre-Clear Context Checkpoint

## Overview

When you run `/clear`, the context window resets but your work doesn't disappear. The **Pre-Clear Context Checkpoint** feature ensures you have warm, resumable context when your next session starts.

## How It Works

### Three-Step Flow

1. **SessionEnd Hook** (when current session ends):
   - Creates a `session_checkpoint` episodic event
   - Captures: active TodoWrite items, recent important findings
   - Stores with high `importance_score = 0.95`

2. **Context Clear** (`/clear` command):
   - Clears the Claude Code context window
   - But the checkpoint is safely stored in PostgreSQL

3. **SessionStart Hook** (when you resume):
   - Runs `get_active_memories()` to load top 7±2 items
   - Checkpoint is ranked HIGH due to importance score
   - Appears naturally in "## Working Memory (Resuming)" section
   - You're back up to speed immediately

### Architecture

```
SessionEnd (Phase 0)
  ↓
  Create session_checkpoint event
  Set importance_score = 0.95
  Store in PostgreSQL episodic_events

         [/clear command]

SessionStart
  ↓
  Call get_active_memories(limit=7)
  ↓
  ACT-R ranking (based on importance_score)
  ↓
  Checkpoint ranks #1-3 (0.95 > normal items)
  ↓
  Inject as part of Working Memory
```

## What Gets Captured

The checkpoint captures:

1. **Active Tasks** (from TodoWrite):
   - In-progress items
   - Pending items (up to 3 total)

2. **Recent Important Findings**:
   - Events with `importance_score > 0.6`
   - From last 30 minutes
   - Limited to 2 items

This keeps the checkpoint under 400 tokens—compact but informative.

## Usage

### Automatic (Recommended)

Just use normally. The checkpoint happens automatically:
- Every time a session ends (whether you clear or not)
- SessionStart automatically injects it if it exists

### Manual Testing

To test the checkpoint flow:

```bash
# Simulate session end to create checkpoint
/home/user/.claude/hooks/session-end.sh 2>&1 | grep "Checkpoint created"

# Check that checkpoint was stored
psql -h localhost -U postgres -d athena -c "SELECT id, event_type, importance_score FROM episodic_events WHERE event_type='session_checkpoint' ORDER BY timestamp DESC LIMIT 1"

# Then run /clear in Claude Code
/clear

# On next session, SessionStart will inject the checkpoint automatically
```

## Why This Approach

**Simple**: Uses existing episodic memory + ACT-R ranking (no new infrastructure)

**Reliable**: Importance scoring ensures checkpoint is always picked up

**Non-invasive**: SessionStart doesn't need special logic—checkpoint ranks naturally

**Flexible**: Captures what matters (active work + recent findings)

## Limitations

- Checkpoint created only at SessionEnd (not on `/clear` directly—documented issue #6428)
- If you never end the session before clearing (e.g., crash), no checkpoint exists
- Checkpoint is lost if PostgreSQL is unavailable

## Future Enhancements

- Add PreClear hook support if Claude Code adds this event
- Store checkpoints in multiple formats (JSON file backup)
- Let users customize what gets captured
