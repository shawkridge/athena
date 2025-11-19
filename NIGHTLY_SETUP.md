# Athena Nightly Dream Consolidation Setup

## Overview

Procedural memory extraction (and other heavy consolidation tasks) have been moved from session-end (which runs on every Claude Code session) to a nightly scheduled job that runs when Claude Code is idle.

**Location:** `/home/user/.work/athena/scripts/run_athena_dreams.sh`

## Installation

### Option 1: Install via crontab (Recommended)

Run this once to schedule nightly dreams at 2 AM:

```bash
# Add to your crontab
(crontab -l 2>/dev/null || true; echo "0 2 * * * /home/user/.work/athena/scripts/run_athena_dreams.sh 2>&1") | crontab -
```

Verify installation:
```bash
crontab -l | grep athena
```

Expected output:
```
0 2 * * * /home/user/.work/athena/scripts/run_athena_dreams.sh 2>&1
```

### Option 2: Manual execution

Run consolidation manually anytime:

```bash
/home/user/.work/athena/scripts/run_athena_dreams.sh
```

Or with custom strategy:
```bash
DREAM_STRATEGY=deep /home/user/.work/athena/scripts/run_athena_dreams.sh
```

## What Happens Nightly

1. **Phase 1: Consolidation**
   - Analyzes all episodic events
   - Extracts temporal and frequency patterns
   - Creates semantic memories

2. **Phase 2: Procedure Extraction**
   - Builds procedures from high-confidence patterns
   - Learns reusable workflows
   - Updates L3 (procedural memory)

3. **Phase 3: Dream Generation**
   - Uses local LLMs to generate procedure variants
   - Explores parameter space
   - Creates "dream" procedure candidates

4. **Phase 4: Evaluation**
   - Spawns Claude for dream evaluation
   - Assesses viability of generated procedures
   - Tiered ranking (Tier 1 = ready to use, Tier 3 = archive)

## Environment Variables

Customize nightly execution:

```bash
# Dream generation strategy: light, balanced (default), deep
DREAM_STRATEGY=deep

# Where to log output
ATHENA_LOG_FILE=/var/log/athena-dreams.log

# Athena home directory (auto-detected)
ATHENA_HOME=/home/user/.work/athena

# Python binary to use
PYTHON_BIN=python3
```

Example with custom settings:
```bash
DREAM_STRATEGY=deep ATHENA_LOG_FILE=/tmp/dreams.log /home/user/.work/athena/scripts/run_athena_dreams.sh
```

## Logs

Check nightly dream execution:

```bash
# View log file
tail -f /var/log/athena-dreams.log

# Or manually run and see output
/home/user/.work/athena/scripts/run_athena_dreams.sh
```

## Architecture Changes

### Before (Session-End Only)
```
Session End Hook (runs every session)
  ├─ Consolidate episodic → semantic
  ├─ Extract patterns
  ├─ Extract procedures (blocking!)
  └─ Return to Claude (~500ms)
```

**Problem:** Procedure extraction is heavy (LLM validation, pattern analysis), blocking Claude Code session-end.

### After (Session-End + Nightly)
```
Session End Hook (runs every session)
  ├─ Fast consolidation (System 1 only, ~100ms)
  ├─ Create semantic memories
  └─ Record patterns (deferred)

Nightly Dream Script (2 AM or on-demand)
  ├─ Full consolidation (System 1 + System 2)
  ├─ Extract procedures
  ├─ Generate dreams (LLM)
  └─ Queue for evaluation
```

**Benefits:**
- Session-end stays fast (<200ms)
- Procedures learned during idle time
- Claude can evaluate dreams when ready
- No blocking operations during interactive sessions

## Monitoring

Check L3 (Procedural Memory) growth in statusline:

```
● Athena 31MB │ epi:11839 sem:197 proc:1 prosp:8 graph:15 meta:0* cons:0 plan:0
                                      ↑
                              Procedures learned
```

After first nightly run, you should see `proc` count increase.

## Troubleshooting

### "Claude CLI not found"
```bash
pip install --upgrade claude-cli
```

### "Consolidation script not found"
Verify path exists:
```bash
ls -la /home/user/.work/athena/scripts/run_consolidation_with_dreams.py
```

### "PostgreSQL connection failed"
Verify database is running:
```bash
psql -h localhost -U postgres -d athena -c "SELECT 1"
```

### "No dreams generated"
Check logs:
```bash
tail -50 /var/log/athena-dreams.log
```

May need more events in episodic memory before procedures can be extracted.

## Next Steps

1. Install cron job (see Option 1 above)
2. Monitor logs for successful runs
3. Check statusline for L3 (proc) growth
4. Evaluate dreams when prompted by Claude
5. Tier successful procedures for future use

---

**Status:** Ready for production use ✓
