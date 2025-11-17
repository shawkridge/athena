# Athena Tasks & Projects

**Source**: COMPREHENSIVE_ANALYSIS.md - Critical gaps and high-impact projects
**Date**: November 17, 2025
**Status**: Analysis phase complete, ready for implementation

---

## Critical Gaps (Quick Wins)

### Gap 1: Episodic→Graph Extraction Incomplete
- **Problem**: Episodic events created independently; entities not auto-extracted
- **Impact**: No temporal causality chains; historical context fragmented
- **Fix**: Auto-extract entities/relations from episodic events → graph on store
- **Effort**: Medium (1-2 days)
- **Files**: `episodic/store.py`, `graph/store.py`, `manager.py`

### Gap 2: Prospective→Consolidation Feedback Loop Missing
- **Problem**: Task completion not analyzed for pattern learning
- **Impact**: System doesn't improve at planning/task execution
- **Fix**: Add task completion patterns to consolidation pipeline
- **Effort**: Medium (2-3 days)
- **Files**: `prospective/store.py`, `consolidation/system.py`

### Gap 3: Meta-Memory→Manager Reweighting Not Implemented
- **Problem**: Quality scores tracked but never used to adjust layer behavior
- **Impact**: Ineffective layers waste computational resources
- **Fix**: Reweight layer queries based on quality scores
- **Effort**: High (3-5 days)
- **Files**: `meta/store.py`, `manager.py`, `optimization/tier_selection.py`

### Gap 4: Tool Stubs (17 NotImplementedError)
- **Problem**: Tools API has stubs; agents told to "use manager instead"
- **Impact**: Tool discovery confusing; API inconsistent
- **Fix**: Implement actual tools or remove stubs; clarify architecture
- **Effort**: Low-Medium (2-3 days)
- **Files**: `tools/*`, documentation

---

## High-Impact Projects

### PROJECT 1: Complete Episodic→Graph Integration [HIGH IMPACT]

**Goal**: Auto-extract and link entities from episodic events to knowledge graph

**Scope**:
1. **Entity Recognition** from episodic event content
   - Extract: Projects, Tasks, Files, Functions, Concepts
   - Use: NER + code symbol extraction
   - Effort: 3-5 days

2. **Relationship Extraction** from context
   - Extract: contains, depends_on, implements, tests, etc.
   - Temporal linking: Event A caused Event B
   - Effort: 3-5 days

3. **Temporal Causality Chains**
   - Link episodic events via causality
   - Enable: "Why did this happen?" queries
   - Effort: 2-3 days

**Expected Outcomes**:
- Rich temporal knowledge graph (causality chains)
- Better context retrieval (understanding dependencies)
- Improved pattern learning (understanding causality)
- 20-30% improvement in RAG relevance

**Implementation Strategy**:
- Add entity_id FK to episodic_events
- Hook episodic store.save() to extract entities
- Call graph.add_relation() for causality
- Index temporal relationships

**Business Value**: ~$100K+ in improved RAG quality for enterprise deployments

---

### PROJECT 2: Task Learning & Execution Analytics [HIGH IMPACT]

**Goal**: Learn from task execution; improve future planning

**Scope**:
1. **Task Pattern Extraction**
   - Analyze completed tasks for patterns
   - Extract: "95% success when prep phase >2 hours"
   - Effort: 4-6 days

2. **Execution Metrics**
   - Track: actual vs estimated time, success rate, failure modes
   - Correlate: task properties → success
   - Effort: 3-5 days

3. **Planning Feedback Loop**
   - Use task patterns to improve goal decomposition
   - Adjust effort estimates based on history
   - Effort: 4-6 days

**Expected Outcomes**:
- Planning accuracy +40-60%
- Task success rate improvement +25-35%
- Better effort estimation (reduce surprises)

**Implementation Strategy**:
- Add task_patterns table (like procedures)
- Hook prospective store to consolidation on task completion
- Update planning goal_decomposition with task history
- Create MCP tool: get_task_history()

**Business Value**: Massive for agentic workflows; enables multi-day, multi-step task automation

---

### PROJECT 3: Adaptive Layer Weighting [HIGH IMPACT]

**Goal**: Automatically optimize which layers to query based on performance

**Scope**:
1. **Quality Metrics** (already tracked)
   - Use: MetaMemoryStore scores
   - Track: Precision, recall, latency per layer

2. **Dynamic Reweighting**
   - If semantic layer has 95%+ precision: query it first
   - If graph traversal slow: use alternative
   - Effort: 4-6 days

3. **Cost-Benefit Analysis**
   - Some layers expensive (LLM calls): only when needed
   - Parallel vs sequential routing: dynamic
   - Effort: 3-5 days

**Expected Outcomes**:
- 30-50% latency reduction (smart routing)
- Better recall (query right layers)
- Lower computational cost (skip slow layers)

**Implementation Strategy**:
- Extend tier_selection.py with ML-based routing
- Use past query results to train router
- Implement online learning (update daily)
- A/B test routing strategies

**Business Value**: ~50% cost reduction for large-scale deployments

---

### PROJECT 4: Advanced RAG Optimization [MEDIUM-HIGH IMPACT]

**Goal**: Implement emerging RAG techniques from 2024-2025 research

**Scope**:
1. **Temporal RAG** (Gap identified)
   - Enrich results with temporal evolution
   - Show causality chains
   - Effort: 3-5 days

2. **Cross-Modal RAG** (Emerging)
   - Support: Text, code, logs, diagrams
   - Effort: 5-7 days

3. **RAG Evaluation Framework**
   - Build: BLEU, ROUGE, custom semantic metrics
   - Benchmark: Different strategies
   - Effort: 4-6 days

**Expected Outcomes**:
- +15-25% answer quality
- Better multimodal search
- Measurable improvement tracking

**Implementation Strategy**:
- Extend temporal_enrichment module
- Add code embeddings (separate model)
- Create evaluation benchmark suite
- Document each RAG strategy

**Business Value**: Competitive advantage in enterprise search; measurable quality improvements

---

### PROJECT 5: Consolidation System Completion [MEDIUM IMPACT]

**Goal**: Complete missing consolidation features

**Scope**:
1. **Event Prioritization** (Research shows this matters)
   - Surprise: Novel events (unexpected)
   - Utility: Likely to be useful in future
   - Relevance: Matches current goals
   - Effort: 3-4 days

2. **Conflict Resolution** (Dual-process identified gap)
   - When System 1 & System 2 disagree
   - Need: Human feedback mechanism or LLM arbitration
   - Effort: 4-5 days

3. **Pattern Strengthening**
   - Repeated patterns → higher confidence
   - Implement: Spaced repetition (Ebbinghaus)
   - Effort: 2-3 days

**Expected Outcomes**:
- 20-30% improvement in learned patterns
- Better pattern stability (conflict resolution)
- Optimized memory refresh (spaced repetition)

**Implementation Strategy**:
- Extend dual_process_consolidator
- Add PriorityQueue for event selection
- Implement Ebbinghaus curve tracking
- Create conflict resolution handler

**Business Value**: More reliable learned patterns; reduced "hallucination" from bad generalizations

---

### PROJECT 6: Planning System Enhancement [MEDIUM IMPACT]

**Goal**: Add advanced planning capabilities from latest research

**Scope**:
1. **Scenario Simulation** (Exists but not integrated)
   - Generate alternative execution paths
   - Test robustness
   - Effort: 4-5 days

2. **Adaptive Replanning** (Emerging, not implemented)
   - Detect plan failures in real-time
   - Replan on-the-fly
   - Effort: 5-7 days

3. **Risk Quantification** (Partial)
   - Bayesian uncertainty in estimates
   - Monte Carlo simulation
   - Effort: 4-6 days

**Expected Outcomes**:
- 40-60% improvement in plan success rate
- Real-time adaptability
- Better risk-aware planning

**Implementation Strategy**:
- Extend scenario_simulator module
- Add real-time plan monitoring
- Implement Bayesian uncertainty tracking
- Create feedback loop from actual execution

**Business Value**: Multi-day complex task automation; enables agentic reasoning

---

## Additional Projects

### PROJECT 7: Database Schema Optimization [MEDIUM IMPACT]

**Missing Foreign Keys**:
- Add entity_id FK to episodic_events
- Add learned_pattern_id FK to prospective_tasks
- Add cascading deletes to procedural_skills

**Missing Indexes** (Performance risk):
- Temporal queries: `idx_episodic_temporal` on (project_id, timestamp DESC)
- Consolidation queries: `idx_episodic_consolidation` on (consolidation_status, confidence)
- Graph traversal: `idx_entity_relations_from` on (from_entity_id, relation_type)
- Task filtering: `idx_prospective_active` on (status, priority, due_at)

**Temporal Inconsistency**:
- Some tables use `created_at` (ISO string), others `timestamp` (Unix)
- Standardize temporal convention across all layers

**Effort**: 3-5 days
**Impact**: Performance improvement, referential integrity

### PROJECT 8: Code Quality Improvements [MEDIUM IMPACT]

**Async/Sync Mixing** (20+ instances):
- Stores are sync-only but manager is async
- Remove SyncCursor wrapper; make stores fully async
- Effort: 4-6 days

**Broad Exception Handling** (30+ instances):
- Replace silent failures with proper logging
- Add specific exception types
- Effort: 3-5 days

**Duplicate Code** (Observed in 10+ stores):
- Centralize `_ensure_schema()` in DatabasePostgres
- Effort: 2-3 days

---

## Priority Ranking

### Immediate (Week 1)
1. Gap 4: Tool Stubs (2-3 days) - Unblocks API clarity
2. Gap 1: Episodic→Graph (1-2 days) - Quick win
3. DATABASE: Schema optimization (3-5 days) - Foundation for other projects

### High Priority (Week 2-3)
1. PROJECT 1: Episodic→Graph Integration (8-13 days)
2. PROJECT 2: Task Learning & Execution (11-17 days)
3. PROJECT 3: Adaptive Layer Weighting (7-11 days)

### Medium Priority (Month 2)
1. PROJECT 4: Advanced RAG Optimization (12-18 days)
2. PROJECT 5: Consolidation System (9-12 days)
3. PROJECT 6: Planning System Enhancement (13-18 days)

### Ongoing
- PROJECT 8: Code Quality (4-8 days spread across work)

---

## Effort Summary

| Project | Effort | Impact | Business Value |
|---------|--------|--------|-----------------|
| Gap 4: Tool Stubs | 2-3d | HIGH | Unblocks development |
| Gap 1: Episodic→Graph | 1-2d | HIGH | Foundation |
| DATABASE: Schema | 3-5d | HIGH | Performance |
| PROJECT 1: Episodic→Graph Full | 8-13d | HIGH | $100K+ RAG quality |
| PROJECT 2: Task Learning | 11-17d | HIGH | $500K+ (agentic) |
| PROJECT 3: Adaptive Weighting | 7-11d | HIGH | $200K+ (cost savings) |
| PROJECT 4: RAG Optimization | 12-18d | MEDIUM-HIGH | Competitive edge |
| PROJECT 5: Consolidation | 9-12d | MEDIUM | Pattern reliability |
| PROJECT 6: Planning | 13-18d | MEDIUM | Complex automation |
| CODE: Quality | 4-8d | MEDIUM | Maintainability |

**Total Estimated Effort**: 70-110 days (~3-5 months at full-time)

---

## Current System Status (Baseline)

- **Episodic Events**: 8,128 stored
- **Learned Procedures**: 101 extracted
- **MCP Operations**: 467+ available
- **Test Coverage**: 94/94 tests passing
- **Production Readiness**: 95%

All gaps are fixable with focused engineering; no architectural redesign needed.
