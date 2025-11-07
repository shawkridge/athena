# Athena Gap Implementation - Context Restart Prompt

**Use this prompt to restart work after clearing context**

---

## 🎯 SESSION OBJECTIVE

Continue executing the Athena Gap Implementation Plan. We are on **Task 1.2: Git-Aware Context** (Week 1, Day 4-6).

## 📋 CURRENT STATUS

**Project**: Athena Memory System (95% → 98% complete)
**Phase**: Quick Wins Execution (Week 1-2)
**Progress**: 1/10 tasks complete

### Completed Tasks
- ✅ **Task 1.1: GraphRAG Integration** (455-line implementation + 25 tests)

### Active Task
- ⏳ **Task 1.2: Git-Aware Context** (IN PROGRESS - 3 days)

### Pending Tasks (Week 1-2)
- **Task 1.3**: Community Summarization (3 days)
- **Task 1.4**: Gisting (Prompt Caching) (1 week)
- **Task 1.5**: Path Finding Algorithms (1 week)

## 📂 KEY FILES & DOCUMENTS

**Implementation Plans**:
- `/home/user/.work/athena/GAP_IMPLEMENTATION_PLAN.md` - Full 16-week roadmap
- `/home/user/.work/athena/athena-reference-projects.md` - Research synthesis (1059 lines)
- `/home/user/.work/athena/EXECUTION_SUMMARY.md` - Progress & metrics

**Code Files Created**:
- `/home/user/.work/athena/src/athena/rag/graphrag.py` - GraphRAG implementation
- `/home/user/.work/athena/tests/unit/test_graphrag.py` - GraphRAG tests

## 🔧 NEXT IMMEDIATE ACTIONS

### Task 1.2: Git-Aware Context (TODAY - 3 days)

**Files to Create**:
```
src/athena/code/git_context.py          # Git context manager
tests/unit/test_git_context.py          # Unit tests
```

**Implementation Steps**:
1. Create `GitContext` class with methods:
   - `get_changed_files(since: str = "HEAD~1")` - List files changed since commit
   - `get_changed_diff(filepath: str)` - Get diff for specific file
   - `get_file_status(filepath: str)` - Track changes (added/modified/deleted)

2. Integrate with code analyzer:
   - Modify `src/athena/code/enhanced_parser.py` or code analyzer
   - Prioritize changed files in context assembly
   - Use git diff for differential context

3. Write comprehensive tests:
   - Test file change detection
   - Test diff retrieval
   - Test integration with code analyzer

4. Update context assembly:
   - Modified `src/athena/memory/store.py` context building
   - Ensure changed files appear first in context

**Success Criteria**:
- ✅ Correctly identifies changed files (accuracy)
- ✅ Git integration reliability (no errors)
- ✅ Changed files prioritized in context
- ✅ All tests passing

**Estimated Time**: 3 days

### Task 1.3: Community Summarization (AFTER 1.2)

**What to do**:
1. Add `summary` field to community entities in graph
2. Create summarization function
3. Batch summarize all Leiden communities
4. Cache summaries for reuse
5. Update community retrieval to return summaries

**Files to Modify**:
- `src/athena/graph/store.py` - Add summary handling

### Task 1.4: Gisting (Week 2)

**Implementation**:
- Create `src/athena/efficiency/gisting.py`
- Pre-compute document summaries
- Integrate with Anthropic prompt caching
- Cache summaries for high-hit-rate reuse

---

## 📊 GAP ANALYSIS SUMMARY

**37 Total Gaps Identified** across 5 categories

### Top 10 Critical Gaps (Ranked by Score)

1. **CRAG** (Corrective RAG) - Score: 95 - 3 weeks effort
2. **ReAct Loop** - Score: 92 - 4 weeks effort
3. **Automated Graph Construction (NER)** - Score: 90 - 4 weeks effort
4. **Call Graph Analysis** - Score: 88 - 2 weeks effort
5. **LLMLingua Compression** - Score: 85 - 3 weeks effort
6. **GraphRAG Integration** - Score: 83 - 1 week effort ✅ DONE
7. **Self-RAG** - Score: 82 - 3 weeks effort
8. **Git-Aware Context** - Score: 80 - 3 days effort (CURRENT)
9. **Token Budgeting** - Score: 78 - 2 weeks effort
10. **Chain-of-Verification** - Score: 75 - 2 weeks effort

**See `GAP_IMPLEMENTATION_PLAN.md` for full details on all 37 gaps**

---

## 🎓 REFERENCE MATERIALS

### Key Research Papers to Study

**For Git-Aware Context**:
- Claude Context MCP (Zilliztech) - AST-based context assembly
- DeepContext MCP - Hierarchical codebase navigation

**For Upcoming Tasks**:
- CRAG: "Corrective Retrieval Augmented Generation" (Yan et al., 2024)
- Self-RAG: "Self-RAG: Learning to Retrieve, Generate, and Critique" (Asai et al., 2023)
- LLMLingua: "Compressing Prompts" (Jiang et al., 2023)
- ReAct: "ReAct: Synergizing Reasoning and Acting" (Yao et al., 2023)

See `athena-reference-projects.md` for 20+ research papers with links and relevance.

---

## 📈 PROJECT METRICS

### Current Status
- **Architecture Completeness**: 98% (after GraphRAG)
- **Test Coverage**: 94/94 core tests passing
- **Dual Database Status**: FULLY OPERATIONAL
  - SQLite + Qdrant: Working
  - Multi-project isolation: Working
  - Memory migration: Working
  - Cross-project sharing: Working

### Impact Targets (After 10 Tasks)
- **Cost Reduction**: 60-70% (API costs via compression)
- **RAG Accuracy**: +40% (CRAG + Self-RAG)
- **Code Understanding**: +90% (call graphs + NER)
- **Context Efficiency**: 5-10x improvement (token budgeting)

### Timeline
- **Current**: Week 1 (Day 4-6)
- **Target Completion**: Q1 2026 (16 weeks total)
- **Tasks Completed**: 1/10 (10%)

---

## 🔄 WORKFLOW REMINDERS

1. **Use TodoWrite** to track tasks as you work
2. **Run tests frequently** after each implementation
3. **Commit code** when tasks are complete with conventional commits
4. **Update this context document** after major milestones
5. **Mark tasks as in_progress** when starting them
6. **Mark tasks as completed** immediately upon finishing

## 🚀 QUICK START COMMANDS

```bash
# View current implementation plan
cat /home/user/.work/athena/GAP_IMPLEMENTATION_PLAN.md

# View gap analysis summary
cat /home/user/.work/athena/athena-reference-projects.md

# View execution progress
cat /home/user/.work/athena/EXECUTION_SUMMARY.md

# Run tests for current task
pytest tests/unit/test_git_context.py -v

# Check which tests are currently failing
pytest tests/ -v --tb=short | grep -E "FAILED|ERROR"
```

---

## 💡 KEY PRINCIPLES

1. **GraphRAG is a foundation** - Global/local/hybrid search patterns can be reused
2. **Tests first** - Write comprehensive tests before full implementation
3. **Graceful degradation** - Each feature should work in isolation
4. **Performance matters** - Target latencies: <500ms queries, <100ms metadata
5. **Document as you go** - Docstrings, type hints, architecture notes

---

## ✅ SIGN-OFF CHECKLIST BEFORE CLEARING CONTEXT

Before clearing context, ensure:
- [ ] Current task status documented in EXECUTION_SUMMARY.md
- [ ] Any blockers/issues recorded
- [ ] Test results captured (pass/fail counts)
- [ ] Next task clearly identified
- [ ] Code committed (if applicable)
- [ ] This CONTEXT_RESTART_PROMPT.md is up-to-date

---

## 📞 QUICK REFERENCE

**Current Task**: Git-Aware Context (Task 1.2)
**Files to Create**: `src/athena/code/git_context.py`, `tests/unit/test_git_context.py`
**Estimated Duration**: 3 days
**Success Metric**: Changed files correctly identified and prioritized
**Next Task**: Community Summarization (Task 1.3)
**Week**: Week 1 (Day 4-6 of 14)

---

**Document Generated**: November 6, 2025
**Last Updated**: November 6, 2025
**Status**: Ready for context restart
