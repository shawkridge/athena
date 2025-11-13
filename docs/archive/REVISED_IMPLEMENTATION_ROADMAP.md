# Revised Implementation Roadmap: MCP-Aligned Event Ingestion

**Date**: November 10, 2025
**Status**: Alignment verified with Anthropic's MCP paradigm
**Key Insight**: Implement MCP tools BEFORE concrete sources for better design

---

## Current Status

✅ **Foundation Complete (11 of 15 tasks)**:
- Query Expansion Module + Integration
- PostgreSQL Pooling Optimization
- EventHasher, BaseEventSource, EventSourceFactory, CursorManager
- EventProcessingPipeline, EventIngestionOrchestrator
- Comprehensive tests and documentation

⏳ **Remaining (4 tasks)** - Now in correct order:

1. **Add MCP Tools** (1 week) ← **MOVED UP** (was #4, now #1)
2. **FileSystemEventSource** (2 weeks)
3. **GitHubEventSource** (2 weeks)
4. **Additional Sources** (Ongoing)

---

## Why We're Reordering

### The MCP Paradigm Changes Everything

**Old Thinking** (Wrong):
1. Build sources first
2. Then expose via MCP tools
3. Problem: Tools designed to pass raw events → token explosion

**New Thinking** (Correct):
1. Design MCP tools around context efficiency
2. Then build sources that work with tools
3. Benefit: 98.7% token reduction from the start

### Key Insight from Anthropic's Blog

**Context is expensive**:
- 10,000 raw events → 150,000 tokens
- Agent must filter manually
- Result: Bloated context, slow agent reasoning

**Processing locally is cheap**:
- Sync operation processes 10,000 events
- Returns only: `{"inserted": 950, "skipped": 50, ...}`
- Result: 2,000 tokens, 98.7% reduction

---

## Revised Roadmap (8-10 weeks total)

### Phase 1: MCP Tools Design & Implementation (1 week)

**File**: `src/athena/mcp/handlers_episodic.py` (new)

**Tools to Implement**:
1. `list_event_sources()` - Discovery
2. `get_event_source_config(source_type)` - Schema
3. `create_event_source(source_type, source_id, config)` - Creation
4. `sync_event_source(source_id)` - Sync (context-efficient!)
5. `get_sync_status(source_id)` - Status
6. `reset_event_source(source_id)` - Reset

**Deliverables**:
- [ ] All 6 MCP tools implemented
- [ ] Security validation (no credentials in parameters)
- [ ] Token efficiency verified (98%+ reduction)
- [ ] Integration tests with mock sources
- [ ] Documentation with examples

**Effort**: 40 hours

**Success Criteria**:
- ✅ All tools follow MCP paradigm
- ✅ sync_event_source returns stats only (no raw events)
- ✅ Credentials read from environment, not parameters
- ✅ Progressive disclosure working (list → config → create → sync)

---

### Phase 2: FileSystemEventSource Implementation (2 weeks)

**File**: `src/athena/episodic/sources/filesystem.py` (new)

**Purpose**: Extract events from filesystem changes (git commits, file modifications)

**Features**:
- Watch file creation, modification, deletion
- Extract git commit details (author, message, changed files)
- Directory structure analysis
- Incremental sync with `last_scan_time` cursor

**Implementation**:
```python
@event_source(
    name="FileSystem",
    supports_incremental=True,
    cursor_schema=FileSystemCursor
)
class FileSystemEventSource(BaseEventSource):
    async def generate_events(self) -> AsyncGenerator[EpisodicEvent, None]:
        # Watch filesystem, yield events
        pass
```

**Deliverables**:
- [ ] FileSystemEventSource implementation (300 lines)
- [ ] FileSystemCursor schema (100 lines)
- [ ] Git integration (commit extraction)
- [ ] Incremental sync support
- [ ] Unit tests (50+ tests)
- [ ] Integration test with MCP tools
- [ ] Documentation and examples

**Effort**: 80 hours

**Testing**:
```python
# Test 1: Discover source
sources = list_event_sources()
assert 'filesystem' in sources

# Test 2: Get configuration
schema = get_event_source_config('filesystem')
assert 'root_dir' in schema['config_fields']

# Test 3: Create source
source = create_event_source('filesystem', 'athena-repo', {
    'root_dir': '/home/user/.work/athena'
})
assert source['status'] == 'connected'

# Test 4: Sync events
stats = sync_event_source('athena-repo')
assert stats['events_inserted'] > 0
assert 'cursor_saved' in stats
```

---

### Phase 3: GitHubEventSource Implementation (2 weeks)

**File**: `src/athena/episodic/sources/github.py` (new)

**Purpose**: Extract events from GitHub repositories

**Features**:
- Pull commits, PRs, issues, reviews
- GitHub Events API integration
- Incremental sync with `last_event_id` cursor
- Support for multiple repositories
- Rate limiting and retry logic

**Implementation**:
```python
@event_source(
    name="GitHub",
    supports_incremental=True,
    cursor_schema=GitHubCursor
)
class GitHubEventSource(BaseEventSource):
    async def generate_events(self) -> AsyncGenerator[EpisodicEvent, None]:
        # Fetch from GitHub, yield events
        pass
```

**Deliverables**:
- [ ] GitHubEventSource implementation (400 lines)
- [ ] GitHubCursor schema (100 lines)
- [ ] Multi-repository support
- [ ] Rate limiting handling
- [ ] Error recovery
- [ ] Unit tests (50+ tests)
- [ ] Integration test with MCP tools
- [ ] Documentation and examples

**Effort**: 80 hours

**Testing**:
```python
# Test: GitHub source workflow
source = create_event_source('github', 'github-athena', {
    'owner': 'anthropic',
    'repo': 'athena'
})

stats = sync_event_source('github-athena')
assert 'events_generated' in stats
assert 'throughput' in stats

status = get_sync_status('github-athena')
assert status['cursor']['last_event_id'] is not None
```

---

### Phase 4: Integration Testing & Validation (1 week)

**Purpose**: Verify end-to-end workflow with multiple sources

**Tests**:
- [ ] Multi-source concurrent ingestion
- [ ] Cursor recovery (simulate source failure)
- [ ] Token efficiency verification (measure actual reduction)
- [ ] Error handling and retry logic
- [ ] Performance benchmarks
- [ ] Security audit (credential handling)

**Deliverables**:
- [ ] Integration test suite (100+ tests)
- [ ] Performance report (throughput, latency)
- [ ] Token efficiency analysis (target: 98%+ reduction)
- [ ] Security validation
- [ ] Production readiness checklist

**Effort**: 40 hours

---

### Phase 5: Optional - Additional Sources (Ongoing)

**Future Connectors** (after core 4 phases):

1. **SlackEventSource** (2 weeks)
   - Monitor channels, threads, reactions
   - Slack Events API

2. **CICDEventSource** (2 weeks)
   - Build/deploy events
   - GitHub Actions, CI/CD logs

3. **JiraEventSource** (1 week)
   - Issues, transitions, comments
   - Jira REST API

4. **CalendarEventSource** (1 week)
   - Meetings, event scheduling
   - Google Calendar, Outlook

5. **APILogEventSource** (1 week)
   - HTTP request logging
   - Application instrumentation

---

## Timeline Summary

| Phase | Task | Duration | Start | End |
|-------|------|----------|-------|-----|
| 1 | MCP Tools | 1 week | Week 1 | Week 1 |
| 2 | FileSystemEventSource | 2 weeks | Week 2 | Week 3 |
| 3 | GitHubEventSource | 2 weeks | Week 4 | Week 5 |
| 4 | Integration Testing | 1 week | Week 6 | Week 6 |
| 5 | Additional Sources | Ongoing | Week 7+ | - |

**Total (Phases 1-4)**: 6 weeks
**Total (with Phase 5)**: 8-10 weeks

---

## Implementation Strategy

### Week 1: MCP Tools (40 hours)

**Monday-Tuesday** (16 hours):
- Design 6 MCP tool signatures
- Security review (no credentials in params)
- Create handlers_episodic.py template

**Wednesday-Thursday** (16 hours):
- Implement all 6 tools
- Create MCP server integration
- Write tool documentation

**Friday** (8 hours):
- Integration tests with mock sources
- Token efficiency verification
- Code review and polish

---

### Week 2-3: FileSystemEventSource (80 hours)

**Implementation** (60 hours):
- FileSystemEventSource class
- Git integration
- Incremental sync with cursors
- Error handling and retry

**Testing** (12 hours):
- Unit tests (50+)
- Integration with MCP tools
- Performance validation

**Documentation** (8 hours):
- Usage guide
- Configuration reference
- Examples and troubleshooting

---

### Week 4-5: GitHubEventSource (80 hours)

**Same pattern as FileSystemEventSource**:
- Implementation: 60 hours
- Testing: 12 hours
- Documentation: 8 hours

---

### Week 6: Integration Testing (40 hours)

**Comprehensive validation**:
- Multi-source ingestion
- Cursor recovery
- Token efficiency measurement
- Security audit
- Production readiness

---

## Success Criteria

### Phase 1: MCP Tools
- ✅ All 6 tools implemented and working
- ✅ No credentials in MCP parameters
- ✅ Token reduction verified (98%+)
- ✅ Progressive disclosure working (list → config → create → sync)

### Phase 2-3: Concrete Sources
- ✅ FileSystemEventSource fully functional
- ✅ GitHubEventSource fully functional
- ✅ Both integrated with MCP tools
- ✅ 50+ unit tests per source
- ✅ Incremental sync working
- ✅ Documentation complete

### Phase 4: Integration
- ✅ Multi-source concurrent ingestion
- ✅ Cursor recovery verified
- ✅ Performance benchmarks met
- ✅ Security validated
- ✅ Production readiness confirmed

---

## Key Design Principles (From MCP Blog)

1. **Progressive Disclosure**: Agents discover tools on-demand
2. **Context Efficiency**: Return stats only, not raw data
3. **Data Filtering at Source**: Batch operations reduce round-trips
4. **State Persistence**: Cursors enable resumable workflows
5. **Privacy-Preserving**: Credentials in environment, not MCP params

---

## MCP Paradigm in Action

### Agent Workflow (Efficient)

```
Agent: "Sync events from GitHub"
↓
Agent calls: list_event_sources()
Response: {"github": "Pull from GitHub...", ...}
↓
Agent calls: get_event_source_config("github")
Response: {config_fields, cursor_schema, ...}
↓
Agent calls: create_event_source("github", "athena-repo", {owner: "anthropic"})
Response: {status: "connected", source_id: "github-athena-repo"}
↓
Agent calls: sync_event_source("github-athena-repo")
Response: {inserted: 135, skipped: 5, errors: 0, duration_ms: 3500}
↓
Token usage: ~2,000 tokens (98.7% reduction vs raw events!)
```

---

## Documentation References

1. **MCP Alignment**: `/home/user/.work/athena/MCP_ALIGNMENT_ANALYSIS.md`
2. **Implementation Status**: `/home/user/.work/athena/IMPLEMENTATION_EXECUTION_SUMMARY.md`
3. **Original Analysis**: `/home/user/.work/athena/AIRWEAVE_INTEGRATION_ANALYSIS.md`
4. **MCP Blog** (Reference): https://www.anthropic.com/engineering/code-execution-with-mcp

---

## Conclusion

By implementing MCP tools FIRST (before concrete sources), we:
- ✅ Design for context efficiency from the start
- ✅ Ensure progressive disclosure works correctly
- ✅ Build sources that integrate seamlessly
- ✅ Achieve 98.7% token reduction
- ✅ Follow Anthropic's paradigm perfectly

This order is better than the original plan because the tool design informs the source implementation, rather than retrofitting tools onto sources.

**Ready to proceed with Phase 1: MCP Tools implementation!**
