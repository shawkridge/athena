# Cross-Project Setup: Using Athena from Any Project

**Status**: Athena is fully operational and available to all projects on this machine.

---

## What's Now Available

When working on ANY project, you can use:

1. **Athena Tools** (7+ discoverable tools)
   - Memory tools (recall, remember, forget)
   - Planning tools (plan_task, validate_plan)
   - Consolidation tools (consolidate, get_patterns)
   - Graph tools (query, analyze)
   - Retrieval tools (hybrid search)

2. **Athena Skills** (29 reusable skills)
   - Research skills, planning skills, analysis skills, etc.
   - Automatically available in any Claude session

3. **Athena Memory** (Automatic)
   - Hooks record your actions during each session
   - Working memory (7±2 items) loaded at session start
   - Patterns extracted and consolidated at session end

4. **Athena Hooks** (Active)
   - SessionStart: Load relevant context automatically
   - PostToolUse: Record what you do
   - SessionEnd: Consolidate learnings
   - UserPromptSubmit: Ground your work in context
   - PreExecution: Validate environment

---

## Prerequisites

### 1. PostgreSQL Running (Required for Memory)

Athena stores everything in PostgreSQL. Memory will be recorded only if PostgreSQL is accessible.

**Check if PostgreSQL is running**:
```bash
psql -h localhost -U postgres -d athena -c "SELECT 1"
```

**If not running** (and you have PostgreSQL installed):
```bash
# macOS with Homebrew
brew services start postgresql

# Linux with systemd
sudo systemctl start postgresql

# Or manually
postgres -D /usr/local/var/postgres &
```

**If you don't have PostgreSQL**, Athena will still work for:
- Using skills
- Planning and analysis
- Cross-project access to tools

But it won't store memories across sessions.

### 2. Environment Variables (Optional but Recommended)

Add these to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.):

```bash
# PostgreSQL connection for Athena
export ATHENA_POSTGRES_HOST=localhost
export ATHENA_POSTGRES_PORT=5432
export ATHENA_POSTGRES_DB=athena
export ATHENA_POSTGRES_USER=postgres
export ATHENA_POSTGRES_PASSWORD=postgres

# MCP server (for Claude Code integration)
export ANTHROPIC_API_KEY=your-api-key  # If using Anthropic models
```

### 3. Python Path (Should Be Automatic)

Athena is installed in `/home/user/.work/athena/`. Python can find it automatically because:
- It's in your `sys.path` (configured in hooks)
- The package is importable: `from athena.manager import UnifiedMemoryManager`

---

## Using Athena from Your Project

### Option 1: Automatic (Recommended)

Athena hooks work automatically - you don't need to do anything:

1. Start a Claude Code session in your project
2. Hooks automatically run at session start/end
3. Working memory is loaded automatically
4. Your actions are recorded automatically

That's it! Everything works globally.

### Option 2: Explicit Tool Use

When you need specific capabilities:

```python
# In a Python script or task
import sys
sys.path.insert(0, '/home/user/.work/athena/src')

from athena.manager import UnifiedMemoryManager
import asyncio

async def use_athena():
    manager = UnifiedMemoryManager()
    await manager.initialize()

    # Search memories from previous sessions
    results = await manager.recall("topic I'm interested in", limit=5)

    # Store what you're doing
    memory_id = await manager.remember(
        "implemented feature X with approach Y",
        tags=["feature", "architecture"]
    )

    # Get patterns Athena learned
    patterns = await manager.get_patterns(limit=3)

    return results, memory_id, patterns

# Run it
result = asyncio.run(use_athena())
```

### Option 3: Use Skills

Skills are language-agnostic and available in Claude:

```
# In Claude, simply invoke a skill
/deep-research "question to research"
/advanced-planning "complex task to plan"
/code-analyzer "code to analyze"
```

Skills are automatically available - see `~/.claude/skills/` for all options.

---

## What Happens Automatically (With Hooks)

### SessionStart Hook

**When**: Every new Claude session starts

**What it does**:
1. Queries your recent work from PostgreSQL
2. Selects top 7±2 memories by importance
3. Formats them as a "Working Memory" section
4. Injects into your context automatically

**You see**: At the start of each session, a "## Working Memory" section with recent context

### PostToolUse Hook

**When**: After each tool execution (bash command, file operation, etc.)

**What it does**:
1. Records what tool ran and its output
2. Stores as episodic event in PostgreSQL
3. Tags with project ID and timestamp
4. Indexed for future retrieval

**You benefit**: Your actions are automatically remembered

### SessionEnd Hook

**When**: When Claude session ends

**What it does**:
1. Consolidates all episodic events from the session
2. Extracts patterns using dual-process:
   - Fast: Statistical clustering (~100ms)
   - Slow: LLM validation if uncertain
3. Stores patterns in procedural_skills table
4. Updates semantic memories

**You benefit**: Learnings persist across sessions

### UserPromptSubmit Hook

**When**: When you submit input to Claude

**What it does**:
1. Records your input with timestamp
2. Grounds it in project context
3. Stores for future analysis
4. Helps Athena understand your workflow

**You benefit**: Better context injection in future sessions

---

## Debugging: If Things Aren't Working

### Memory Not Recording?

1. **Check PostgreSQL**:
   ```bash
   psql -h localhost -U postgres -d athena -c "SELECT COUNT(*) FROM episodic_events;"
   ```
   If this fails, PostgreSQL isn't accessible.

2. **Check environment variables**:
   ```bash
   echo "ATHENA_POSTGRES_HOST=${ATHENA_POSTGRES_HOST:-not set}"
   echo "ATHENA_POSTGRES_DB=${ATHENA_POSTGRES_DB:-not set}"
   ```

3. **Check hook execution**:
   - Hooks are in `~/.claude/hooks/*.sh`
   - Hooks are configured in `~/.claude/settings.json`
   - View hook output: Run session with `DEBUG=1`

4. **Check database tables**:
   ```bash
   psql -h localhost -U postgres -d athena -c "\dt"
   ```
   Should see: episodic_events, semantic_memories, procedural_skills, etc.

### Tools Not Discoverable?

1. **Verify tools were generated**:
   ```bash
   ls ~/.work/athena/src/athena/tools/memory/
   ```
   Should show: recall.py, remember.py, forget.py, etc.

2. **Verify INDEX.md**:
   ```bash
   cat ~/.work/athena/src/athena/tools/INDEX.md
   ```
   Should show all tool categories and descriptions.

3. **Test tool import**:
   ```bash
   python3 -c "from athena.tools.memory.recall import recall; print('✅ recall tool works')"
   ```

### Skills Not Available?

1. **Verify skills directory**:
   ```bash
   ls ~/.claude/skills/
   ```
   Should show 29+ skill directories.

2. **Verify skill documentation**:
   ```bash
   cat ~/.claude/skills/advanced-planning/SKILL.md
   ```
   Should show when to use and how to invoke.

---

## Next Steps

### For Your Current Project

1. **Use working memory**: Refer to the "Working Memory" section at session start - it has your recent context
2. **Recall relevant knowledge**: Use `recall()` tool to search previous work
3. **Store insights**: Use `remember()` to save important learnings with tags
4. **Leverage skills**: Invoke appropriate skills like `/advanced-planning` or `/deep-research`

### To Improve Athena

See `ARCHITECTURE.md` for:
- How to add new memory layers
- How to add new hooks
- How to extend the system
- Debugging and optimization tips

### To Understand Athena Better

Documentation hierarchy:
1. **Global guidance**: `~/.claude/CLAUDE.md` - Using Athena from any project
2. **Internal architecture**: `ARCHITECTURE.md` - How Athena works (in this directory)
3. **Development guide**: `CLAUDE.md` (in this directory) - Developing Athena itself
4. **Tool documentation**: `~/.work/athena/src/athena/tools/INDEX.md` - Available tools
5. **Skill documentation**: `~/.claude/skills/*/SKILL.md` - Individual skill guides

---

## Summary: What Changed

| Before | Now |
|--------|-----|
| ❌ Tools framework existed but unused | ✅ 7+ tools generated and discoverable |
| ❌ No guidance on using Athena | ✅ Clear documentation in ~/.claude/CLAUDE.md |
| ❌ Hooks configured but not visible | ✅ 5 hooks active, 29 skills available |
| ❌ No architecture docs for improvement | ✅ Comprehensive ARCHITECTURE.md created |
| ❌ Memory system hidden | ✅ Cross-project memory now accessible |

**Result**: Athena is now fully operational as a persistent memory system for Claude Code instances on this machine.

---

## Example: Using Athena from a New Project

```bash
# Create or navigate to your project
cd ~/my-project

# Start Claude Code
claude-code .

# In Claude Code:
# 1. Working memory loads automatically at session start
# 2. You see previous context from other projects
# 3. You can explicitly search with:

# Claude> /explore to find relevant memories
# Claude> recall("topic") - search memories
# Claude> /advanced-planning to plan complex tasks
# Claude> /deep-research for research help

# 4. Your work is recorded automatically
# 5. Session-end consolidation extracts patterns

# Next time you work:
# Claude will remember what you did before
```

---

**Status**: ✅ Athena is live and working across all projects.
