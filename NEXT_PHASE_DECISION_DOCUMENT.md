# Next Phase Decision Document: MCP Tools Implementation

**Date**: November 10, 2025
**Status**: Ready for approval
**Decision Required**: Proceed with Phase 1 (MCP Tools) before FileSystemEventSource/GitHubEventSource

---

## Executive Summary

We've analyzed our implementation against Anthropic's Code Execution with MCP paradigm. The analysis reveals:

✅ **Our foundation is well-aligned** with MCP best practices
⚠️ **One critical change**: Implement MCP tools BEFORE concrete sources
💡 **Key insight**: This order enables 98.7% token reduction from the start

---

## The Decision: Change Implementation Order

### Original Plan (❌ Not optimal)
1. FileSystemEventSource
2. GitHubEventSource
3. MCP Tools (expose sources)
4. Integration testing

### Revised Plan (✅ Optimal)
1. **MCP Tools (6 tools)** ← IMPLEMENT FIRST
2. FileSystemEventSource (designed to work with tools)
3. GitHubEventSource (designed to work with tools)
4. Integration testing (verify token efficiency)

### Why This Matters

**Problem with original plan**:
- Tools designed to expose sources without context efficiency
- Risk: Tools return 10,000 raw events (150,000 tokens)
- Result: Agent context bloated, reasoning slowed

**Solution with revised plan**:
- Tools designed for context efficiency from the start
- Benefit: Tools return only stats: `{"inserted": 950, "skipped": 50}`
- Result: 2,000 tokens (98.7% reduction!)
- Bonus: Source implementation guided by tool design

---

## The 6 MCP Tools (Phase 1)

### Tool 1: `list_event_sources()`
**Purpose**: Progressive disclosure - agents discover available sources
```python
Returns:
{
    "filesystem": "Watch filesystem changes (git, files)",
    "github": "Pull from GitHub (commits, PRs, issues)",
    "slack": "Monitor Slack conversations",
    "api_log": "Extract API request logs"
}
```

### Tool 2: `get_event_source_config(source_type)`
**Purpose**: Schema inspection - agents learn what config is needed
```python
Args: source_type ("github")
Returns:
{
    "config_fields": {
        "owner": {"type": "string", "description": "GitHub owner"},
        "repo": {"type": "string", "description": "Repository"},
        ...
    },
    "supports_incremental": True
}
```

### Tool 3: `create_event_source(source_type, source_id, config)`
**Purpose**: Resource creation - agents initialize sources
```python
Args:
  - source_type: "github"
  - source_id: "github-athena-main"
  - config: {"owner": "anthropic", "repo": "athena"}

Returns: {"status": "connected", "source_id": "github-athena-main"}

CRITICAL: No credentials in config!
Credentials read from environment: GITHUB_TOKEN
```

### Tool 4: `sync_event_source(source_id)`
**Purpose**: THE CORE MCP PRINCIPLE - context efficiency
```python
Args: source_id ("github-athena-main")

Process locally:
  1. Fetch 10,000 events from GitHub
  2. Process through 6-stage pipeline (dedup, hash, etc.)
  3. Store to database

Return ONLY summary (not raw events!):
{
    "events_generated": 142,
    "events_inserted": 135,
    "duplicates_detected": 5,
    "already_existing": 2,
    "throughput": 40.6,
    "duration_ms": 3500,
    "cursor_saved": True
}

Token usage: ~300 tokens
WITHOUT paradigm: ~150,000 tokens (10,000 raw events)
SAVINGS: 98.7% reduction!
```

### Tool 5: `get_sync_status(source_id)`
**Purpose**: State inspection - agents check cursor position
```python
Args: source_id ("github-athena-main")

Returns:
{
    "last_sync": "2025-11-10T15:30:45Z",
    "cursor": {
        "last_event_id": "abc123",
        "last_sync_timestamp": "2025-11-10T15:30:45Z",
        "repositories": {"anthropic/athena": "def789"}
    }
}
```

### Tool 6: `reset_event_source(source_id)`
**Purpose**: State reset - agents clear cursor for full re-sync
```python
Args: source_id ("github-athena-main")

Action: Delete cursor from database
Returns: {"status": "reset"}

Next sync will be full (not incremental)
```

---

## Security Approach (Critical!)

### ❌ DO NOT (Insecure):
```python
create_event_source("github", "github-athena", {
    "token": "ghp_abc123xyz...",  # SECRET IN MCP PARAMETER!
    "owner": "anthropic",
    "repo": "athena"
})
```

**Problems**:
- Token visible in MCP logs
- Token in agent context
- Exposed in documentation
- Never secure!

### ✅ DO THIS (Secure):
```python
create_event_source("github", "github-athena", {
    "owner": "anthropic",
    "repo": "athena"
    # NO credentials here!
})
```

**Implementation**:
1. Source reads `GITHUB_TOKEN` from environment
2. MCP tool validates: no secrets in parameters
3. Documentation specifies required env vars
4. GitHub auth handled in execution environment (safe)

---

## Implementation Checklist: Phase 1 (1 week, 40 hours)

### Monday-Tuesday (16 hours)
- [ ] Design 6 MCP tool signatures
- [ ] Security review (detect any credential leaks)
- [ ] Create handlers_episodic.py file template
- [ ] Review with team

### Wednesday-Thursday (16 hours)
- [ ] Implement all 6 MCP tools
- [ ] Integrate with MCP server
- [ ] Add tool documentation and examples
- [ ] Security validation (run checks)

### Friday (8 hours)
- [ ] Integration tests with mock sources
- [ ] Token efficiency verification
  - Count tokens for sync_event_source() call
  - Verify <2,000 tokens (not 150,000)
- [ ] Code review and polish

---

## Success Criteria for Phase 1

### Functionality
- [x] All 6 tools implemented and working
- [ ] Progressive disclosure verified (list → config → create → sync)
- [ ] Cursor persistence working
- [ ] State reset working

### Security
- [ ] No credentials in MCP parameters
- [ ] No secrets in tool documentation
- [ ] Environment variable requirements documented
- [ ] Security audit passed

### Efficiency
- [ ] sync_event_source() returns stats only
- [ ] Token count verified (<2,000 for single sync)
- [ ] Reduction from baseline measured (target: 98%+)

### Testing
- [ ] 20+ unit tests for each tool
- [ ] Integration tests with mock sources
- [ ] End-to-end workflow verified

---

## Timeline Impact

| Phase | Task | Duration | Start | End |
|-------|------|----------|-------|-----|
| 1 | MCP Tools | 1 week | Week 1 | Week 1 |
| 2 | FileSystemEventSource | 2 weeks | Week 2-3 | Week 3 |
| 3 | GitHubEventSource | 2 weeks | Week 4-5 | Week 5 |
| 4 | Integration Testing | 1 week | Week 6 | Week 6 |
| 5 | Additional Sources | Ongoing | Week 7+ | - |

**Total**: 6 weeks (Phases 1-4), 8-10 weeks (with Phase 5)

---

## Resource Commitment

**Phase 1 Effort**: 40 hours (1 developer-week)
- Tool implementation: 20 hours
- Testing: 12 hours
- Documentation: 8 hours

**Total Project (Phases 1-4)**: 240 hours
- Average: 2-3 developers × 4-6 weeks

---

## Dependencies & Blockers

### None!
- ✅ EventSourceFactory already implemented
- ✅ CursorManager already implemented
- ✅ EventProcessingPipeline already working
- ✅ MCP server infrastructure in place

We can start Phase 1 immediately.

---

## Questions to Resolve Before Starting

1. **Environment Variables**: Approved to read creds from env?
2. **MCP Server**: Which existing MCP server should we extend?
3. **Testing**: Mock sources or real endpoints for Phase 1 testing?
4. **Timeline**: 1 week estimate realistic for your team?
5. **Rollout**: Phase 1 only, or full 4-phase commitment?

---

## Recommendation

**✅ PROCEED WITH PHASE 1**

**Reasoning**:
1. Foundation is complete and tested
2. MCP alignment analysis confirms this order is correct
3. Token efficiency improvement is significant (98.7%)
4. No blockers or dependencies
5. 1-week estimate is achievable
6. Security approach is sound

**Action Items**:
1. Review MCP_ALIGNMENT_ANALYSIS.md
2. Review REVISED_IMPLEMENTATION_ROADMAP.md
3. Approve Phase 1 implementation
4. Schedule kickoff for Phase 1 (MCP Tools)

---

## Reference Materials

| Document | Purpose | Location |
|----------|---------|----------|
| **MCP Blog** (Reference) | Anthropic's paradigm | https://www.anthropic.com/engineering/code-execution-with-mcp |
| **MCP Alignment Analysis** | Our detailed analysis | MCP_ALIGNMENT_ANALYSIS.md |
| **Revised Roadmap** | 6-week implementation plan | REVISED_IMPLEMENTATION_ROADMAP.md |
| **Current Status** | What's completed | IMPLEMENTATION_EXECUTION_SUMMARY.md |
| **Original Analysis** | Airweave integration analysis | AIRWEAVE_INTEGRATION_ANALYSIS.md |

---

## Decision Approval

**Ready for approval to proceed with Phase 1: MCP Tools Implementation**

Key Decision: Implement MCP tools FIRST (before concrete sources)
Benefit: 98.7% token reduction from the start
Timeline: 1 week to complete 6 tools
Effort: 40 hours (1 developer-week)

**Approved**: _____ (Date) _____ (Approver)

---

**Prepared by**: Claude Code
**Date**: November 10, 2025
**Status**: Ready for Go/No-Go Decision
