# Phase 2 Kickoff: Critical Command Updates

**Status**: Ready to begin
**Timeline**: 2-3 hours
**Impact**: Make Claude's most-used commands token-efficient

---

## What Phase 1 Accomplished

✅ All hook libraries now use FilesystemAPIAdapter:
- `athena_direct_client.py` - Direct memory operations
- `memory_helper.py` - Memory search, storage, health
- `context_injector.py` - Context injection for prompts
- `athena_http_client.py` - HTTP + filesystem fallback

Result: **99.8% token reduction** (165K → 300 tokens per operation)

---

## What Phase 2 Will Do

Update the 4 most-used commands to use the filesystem API paradigm:

### 1. **memory-search.md** (Critical command, high usage)
**Location**: `/home/user/.work/athena/claude/commands/critical/memory-search.md`

**Current Pattern**:
```
Command → Load MCP definitions → Call tool → Return full data
```

**New Pattern**:
```
Command → Discover operations → Read code → Execute locally → Return summary
```

**What to update**:
- Use `FilesystemAPIAdapter.list_layers()`
- Use `FilesystemAPIAdapter.list_operations_in_layer()`
- Use `FilesystemAPIAdapter.read_operation()`
- Use `FilesystemAPIAdapter.execute_operation()`
- Return summary (counts, IDs, metadata - not full objects)

**Example in command**:
```markdown
## Implementation

### Step 1: Discover
Use the memory filesystem API to discover available search operations.

### Step 2: Read
Understand what the search operation does before executing.

### Step 3: Execute
Run the search locally (in sandbox), get summary results.

### Step 4: Analyze
Make decisions based on counts, IDs, relevance scores - not full memory objects.

### Token Efficiency
- Old way: 15,000 tokens (full data)
- New way: 300 tokens (summary)
- Savings: 98% reduction
```

---

### 2. **retrieve-smart.md** (Useful command, advanced RAG)
**Location**: `/home/user/.work/athena/claude/commands/useful/retrieve-smart.md`

**What to update**:
- Implement progressive RAG strategies (HyDE, reranking, reflective)
- Use filesystem API for local search execution
- Demonstrate multi-strategy retrieval
- Return ranked summaries with confidence scores

**Key operations**:
- `semantic/recall` - Semantic search
- `graph/traverse` - Knowledge graph navigation
- `procedural/find` - Procedure matching

---

### 3. **system-health.md** (Useful command, monitoring)
**Location**: `/home/user/.work/athena/claude/commands/useful/system-health.md`

**What to update**:
- Use cross-layer health check via filesystem API
- Return system metrics summary
- Show memory statistics (not full data)
- Display consolidation status

**Key operations**:
- `operations/health_check` - Cross-layer health
- `meta/quality` - Quality metrics
- `consolidation/status` - Consolidation state

---

### 4. **session-start.md** (Critical command, initialization)
**Location**: `/home/user/.work/athena/claude/commands/critical/session-start.md`

**What to update**:
- Initialize FilesystemAPIAdapter at session start
- Load system status and memory overview
- Check health and cognitive load
- Prepare for efficient operations throughout session

**Key operations**:
- Initialize adapter
- Check health
- Load memory summary (not full data)
- Verify database connectivity

---

## Implementation Template for Commands

All commands should follow this pattern:

```markdown
## What This Command Does
[1-2 sentences explaining purpose]

## How It Works (Filesystem API Paradigm)

### Step 1: Discover
- List available operations
- Show what's available (progressive disclosure)

### Step 2: Read
- Read operation code
- Understand parameters and return types
- Know what will execute

### Step 3: Execute
- Run operation locally (in sandbox)
- All data processing happens here, not in context
- Only summary returns

### Step 4: Analyze
- Make decisions based on summary
- Return metrics, IDs, counts - not full objects
- Prepare for follow-up operations

## Token Efficiency
- Paradigm: Discover → Read → Execute → Summarize
- Result: <300 tokens per operation (99% reduction)
- Never: Load full tool definitions or return full data

## Example Usage
[Code example showing the 4 steps]

## Implementation Notes
[Any special considerations for this specific command]
```

---

## Key Files to Reference

### From Phase 1 (Already Updated)
- `claude/hooks/lib/filesystem_api_adapter.py` - The adapter implementation
- `claude/hooks/lib/athena_direct_client.py` - How to use adapter
- `claude/hooks/lib/memory_helper.py` - Helper functions pattern
- `PHASE_1_COMPLETION_REPORT.md` - Detailed implementation notes

### Existing Commands to Learn From
- `commands/critical/` - Look at existing structure
- `commands/useful/` - See successful patterns

### Documentation
- `/home/user/.claude/CLAUDE.md` - Global paradigm explanation
- `FILESYSTEM_API_README.md` - Quick reference
- `FILESYSTEM_API_COMPLETE.md` - Comprehensive reference

---

## Success Criteria for Phase 2

- ✅ All 4 commands updated to use filesystem API
- ✅ Each command demonstrates discover → read → execute → summarize
- ✅ All operations return summaries (not full data)
- ✅ Token usage verified (<300 per operation)
- ✅ Error handling and fallbacks in place
- ✅ Documentation complete with examples
- ✅ Commands tested and validated

---

## Timeline

| Task | Duration |
|------|----------|
| Update memory-search.md | 30 min |
| Update retrieve-smart.md | 45 min |
| Update system-health.md | 30 min |
| Update session-start.md | 30 min |
| Test all commands | 30 min |
| **Total** | **2.5 hours** |

---

## What Comes After Phase 2

### Phase 3: Skills & Agents (4-6 hours)
- Update 16+ skills to demonstrate patterns
- Update 5+ agents to use code execution
- Each shows: discovery, code reading, execution, summary analysis

### Phase 4: Testing & Documentation (2-3 hours)
- End-to-end testing
- Token usage verification
- Migration guide and best practices
- Update all documentation

**Overall completion**: 1-2 focused days

---

## Important Reminders

1. **Never Load Definitions Upfront**
   - Let agents discover what's available
   - Use `list_layers()` and `list_operations_in_layer()`

2. **Always Return Summaries**
   - Never return full data objects
   - Return counts, IDs, metadata only
   - Provide drill-down methods for specific details

3. **Execute Locally**
   - Use `adapter.execute_operation()`
   - Data processing happens in sandbox
   - Only summary comes back to context

4. **Progressive Disclosure**
   - Discover → Read → Execute → Summarize
   - Each step is explicit in the command

---

## Questions Before You Start?

If you have questions about:
- How to use FilesystemAPIAdapter: See `PHASE_1_COMPLETION_REPORT.md`
- Paradigm explanation: See `FILESYSTEM_API_README.md`
- Implementation examples: See hook library files
- Architecture overview: See `FILESYSTEM_API_COMPLETE.md`

---

## Ready to Begin?

Phase 1 foundation is solid:
- ✅ Hook libraries updated
- ✅ FilesystemAPIAdapter implemented
- ✅ Paradigm documented
- ✅ Examples in place

Phase 2 is straightforward:
- Take 4 commands
- Apply filesystem API pattern
- Update to use adapter
- Return summaries instead of full data

**Estimated completion**: 2.5 focused hours 🚀

Let's make Claude's commands as token-efficient as its hooks!
