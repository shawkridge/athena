# Claude Configuration Alignment with Filesystem API Paradigm

## Goal

Update all hooks, commands, skills, and agents to use the filesystem API code execution paradigm instead of direct MCP tool calls.

## The Paradigm Shift

**Old**: Slash command → Direct MCP tool call → Full data in context (15K tokens)
**New**: Slash command → Discover filesystem → Read code → Execute locally → Summary (300 tokens)

## What Needs Changing

### 1. Hooks (`/home/user/.work/athena/claude/hooks/lib/`)

**Current behavior**: Direct Athena client calls returning full data
**New behavior**: Should encourage local processing and progressive disclosure

Files to update:
- `athena_direct_client.py` - Add filesystem discovery methods
- `athena_http_client.py` - Support code execution paradigm
- `context_injector.py` - Inject filesystem API instead of full data
- `memory_helper.py` - Use summary-first approach
- `event_recorder.py` - Record events as summaries

### 2. Commands (`/home/user/.work/athena/claude/commands/`)

**Current**: Execute operations directly via MCP tools
**New**: Discover → Read → Execute → Summarize

Key commands to update:
- **critical/memory-search.md** → Filesystem discovery + local execution
- **useful/retrieve-smart.md** → Progressive disclosure pattern
- **useful/analyze-code.md** → Analyze locally, return summaries
- **useful/system-health.md** → Health check via filesystem API
- **important/consolidate.md** → Consolidation via filesystem API

### 3. Skills (`/home/user/.work/athena/.claude/skills/`)

**Current**: Perform operations directly
**New**: Discover capabilities → Read code → Execute locally

Skills should demonstrate:
- Progressive filesystem discovery
- Code reading and understanding
- Local execution patterns
- Summary-based decision making

### 4. Agents (`/home/user/.work/athena/claude/agents/`)

**Current**: Call MCP tools directly
**New**: Write code that executes locally

Agents should:
- List available operations (`list_directory`)
- Read operation code (`read_file`)
- Execute locally (`execute`)
- Return summaries (never full data)

## Implementation Strategy

### Phase 1: Core Infrastructure (Hooks)

Update hook libraries to:
1. Add `filesystem_api_router` imports
2. Implement `discover_operations()` method
3. Add `read_operation_code()` method
4. Replace direct Athena calls with `router.route_*()` calls
5. Always return summaries, not full data

### Phase 2: High-Impact Commands

Update commands in this order (by impact):
1. **memory-search** (most-used, highest token cost)
2. **retrieve-smart** (advanced RAG)
3. **system-health** (diagnostics)
4. **consolidate** (batch operations)
5. **analyze-code** (complex queries)

### Phase 3: Skills Enhancement

Update skills to demonstrate:
1. Filesystem discovery patterns
2. Code reading and execution
3. Progressive disclosure
4. Summary-first decision making
5. Error handling and edge cases

### Phase 4: Agent Retraining

Update agents to:
1. Discover operations dynamically
2. Read code before execution
3. Execute in local sandbox
4. Use summaries for planning
5. Drill down only when necessary

## Key Principles

1. **Progressive Disclosure**: Never load all definitions upfront
2. **Summary-First**: Always return statistics, not full objects
3. **Local Processing**: Filter/aggregate in execution, not context
4. **Code-Based**: Let agents write code, not call tools
5. **Efficient**: 98%+ token reduction target

## Success Criteria

- ✅ All commands follow discover → read → execute → summarize pattern
- ✅ No full data returned (only summaries with IDs for drill-down)
- ✅ All operations accessible via filesystem API
- ✅ Hooks use router instead of direct Athena calls
- ✅ Tests pass (token usage <300 per operation)
- ✅ Documentation updated

## File Structure After Alignment

```
claude/
├── CLAUDE.md (UPDATED - paradigm documented)
├── hooks/
│   └── lib/
│       ├── filesystem_api_adapter.py (NEW)
│       ├── athena_direct_client.py (UPDATED)
│       ├── memory_helper.py (UPDATED)
│       └── context_injector.py (UPDATED)
├── commands/
│   ├── critical/
│   │   ├── memory-search.md (UPDATED)
│   │   └── session-start.md (UPDATED)
│   ├── useful/
│   │   ├── retrieve-smart.md (UPDATED)
│   │   ├── analyze-code.md (UPDATED)
│   │   └── system-health.md (UPDATED)
│   └── important/
│       └── consolidate.md (UPDATED)
├── skills/
│   └── (ALL updated to demonstrate filesystem API pattern)
└── agents/
    └── (ALL updated to use code execution paradigm)
```

## Timeline

- **Now**: Update critical hooks
- **Day 1**: Update high-impact commands
- **Day 2-3**: Update skills and agents
- **Day 4**: Testing and validation
- **Day 5**: Documentation and deployment

## Next Steps

1. Create `filesystem_api_adapter.py` in hooks/lib/
2. Update hook imports to use filesystem API router
3. Update memory-search command (highest impact)
4. Update retrieve-smart command (advanced RAG)
5. Update system-health command (diagnostics)
6. Validate all changes work correctly
7. Update documentation

---

**Status**: Ready to implement
**Priority**: High (core to the paradigm shift)
**Impact**: Transforms how Claude interacts with Athena from tool-calling to code execution
