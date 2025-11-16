# Athena Execution Plan: Critical Path to Production Excellence

**Timeline**: 2 weeks (Weeks 1-2 = Immediate Actions)
**Target**: Production-hardened system ready for enterprise deployment
**Team**: 2-3 engineers
**Effort**: ~200-240 engineering hours

---

## PHASE 1: IMMEDIATE FIXES (Days 1-3)

### Task 1.1: Implement 17 Tool Stubs [P0 - BLOCKING]
**Status**: Ready to start
**Effort**: 2-3 days
**Impact**: HIGH (unblocks tool API)
**Owner**: Backend Engineer

**Scope**:
1. Remove NotImplementedError from tools/*
2. Route to UnifiedMemoryManager methods
3. Add comprehensive error handling
4. Write tests for each tool

**Files**:
- `/src/athena/tools/memory/recall.py`
- `/src/athena/tools/memory/remember.py`
- `/src/athena/tools/memory/forget.py`
- `/src/athena/tools/consolidation/*.py` (4 files)
- `/src/athena/tools/planning/*.py` (10 files)

**Deliverables**:
- All 17 tools functional
- Test coverage >90%
- Documentation updated

---

### Task 1.2: Add Missing FK Relationships [P0 - DATA INTEGRITY]
**Status**: Ready to start
**Effort**: 1 day
**Impact**: HIGH (prevents orphaned data)
**Owner**: Database Engineer

**Scope**:
```sql
-- 1. Link episodic events to entities
ALTER TABLE episodic_events ADD COLUMN entity_id INT REFERENCES entities(id);
CREATE INDEX idx_episodic_entity ON episodic_events(entity_id);

-- 2. Link prospective tasks to patterns
ALTER TABLE prospective_tasks ADD COLUMN learned_pattern_id INT REFERENCES extracted_patterns(id);
CREATE INDEX idx_prospective_pattern ON prospective_tasks(learned_pattern_id);

-- 3. Add cascading deletes
ALTER TABLE procedural_skills DROP CONSTRAINT IF EXISTS learned_from_fk;
ALTER TABLE procedural_skills
  ADD CONSTRAINT learned_from_fk
  FOREIGN KEY (learned_from_event_id)
  REFERENCES episodic_events(id) ON DELETE CASCADE;
```

**Deliverables**:
- All FKs created
- Indexes added
- Cascading deletes verified
- Migration script tested

---

### Task 1.3: Add Composite Indexes [P1 - PERFORMANCE]
**Status**: Ready to start
**Effort**: 1 day
**Impact**: MEDIUM (30-40% latency reduction)
**Owner**: Database Engineer

**Scope**:
```sql
-- Hot path indexes
CREATE INDEX idx_episodic_temporal
  ON episodic_events(project_id, timestamp DESC);

CREATE INDEX idx_episodic_consolidation
  ON episodic_events(consolidation_status, confidence);

CREATE INDEX idx_entity_relations_from
  ON entity_relations(from_entity_id, relation_type);

CREATE INDEX idx_prospective_active
  ON prospective_tasks(status, priority, due_at);

CREATE INDEX idx_graph_centrality
  ON entities(project_id, updated_at DESC);
```

**Deliverables**:
- All indexes created
- Query plan analysis documented
- Performance benchmarks before/after

---

## PHASE 2: CRITICAL INTEGRATION (Days 4-6)

### Task 2.1: Episodic→Graph Extraction [P1 - HIGH VALUE]
**Status**: Design ready
**Effort**: 3-5 days
**Impact**: HIGH (20-30% RAG improvement)
**Owner**: Backend Engineer

**Design**:
```python
# In episodic/store.py
class EpisodicStore:
    async def store_event(self, event: EpisodicEvent) -> int:
        event_id = await self._insert_event(event)

        # NEW: Extract entities and relationships
        await self._extract_and_link_entities(event)

        # NEW: Build temporal causality
        await self._link_causality(event_id)

        return event_id

    async def _extract_and_link_entities(self, event: EpisodicEvent):
        """Extract entities from event content → graph."""
        entities = self._extract_entities(event.content)
        for entity in entities:
            entity_id = await self.graph.add_entity(entity)
            # Link event to entity
            await self.db.execute(
                "UPDATE episodic_events SET entity_id = ? WHERE id = ?",
                (entity_id, event.id)
            )

    async def _link_causality(self, event_id: int):
        """Link this event to causal predecessors."""
        # Find previous events that might have caused this one
        prev_events = await self._find_related_events(event_id)
        for prev_id in prev_events:
            await self.graph.add_relation(
                from_entity_id=prev_id,
                to_entity_id=event_id,
                relation_type="CAUSED_BY"
            )
```

**Deliverables**:
- Entity extraction working
- Causality chains built
- Graph populated from episodic events
- Tests with sample events

---

### Task 2.2: Tool Stub Documentation [P1 - DEV EXPERIENCE]
**Status**: Writing
**Effort**: 1 day
**Impact**: MEDIUM (clarity for developers)
**Owner**: Documentation Engineer

**Scope**:
1. Document tool discovery pattern
2. Update API reference with all 17 tools
3. Add examples for each tool
4. Clarify routing: Tools → Manager → Layers

**Deliverables**:
- Updated API_REFERENCE.md (all 467+ operations)
- Tool usage guide
- Routing architecture diagram

---

### Task 2.3: Consolidation Prioritization [P1 - LEARNING QUALITY]
**Status**: Ready to start
**Effort**: 2-3 days
**Impact**: MEDIUM (20-30% pattern quality)
**Owner**: Backend Engineer

**Design**:
```python
# In consolidation/dual_process.py
class EventPrioritizer:
    def score_event(self, event: EpisodicEvent) -> float:
        """
        Priority = Surprise + Utility + Relevance

        Surprise: How unexpected was this outcome?
        Utility: How likely to be useful in future?
        Relevance: How related to current goals?
        """
        surprise = self._bayesian_surprise(event)  # 0-1
        utility = self._future_utility(event)       # 0-1
        relevance = self._goal_relevance(event)     # 0-1

        # Weighted sum (tunable)
        return 0.4 * surprise + 0.4 * utility + 0.2 * relevance

    async def prioritize_events(self, events: list[EpisodicEvent]) -> list[EpisodicEvent]:
        """Sort events by consolidation priority."""
        scored = [(event, self.score_event(event)) for event in events]
        return [event for event, score in sorted(scored, key=lambda x: -x[1])]
```

**Deliverables**:
- Priority scoring implemented
- Integration with consolidation pipeline
- Tests and benchmarks

---

## PHASE 3: VALIDATION & HARDENING (Days 7-10)

### Task 3.1: Error Handling Framework [P1 - RELIABILITY]
**Status**: Design ready
**Effort**: 2-3 days
**Impact**: MEDIUM (better debugging)
**Owner**: Backend Engineer

**Scope**:
1. Replace 30+ broad `except Exception` with specific types
2. Add context to error messages
3. Implement logging strategy
4. Create error reference guide

**Deliverables**:
- Specific exception types defined
- All handlers updated
- Error logging tests
- Reference guide

---

### Task 3.2: Performance Testing [P1 - VERIFICATION]
**Status**: Test suite ready
**Effort**: 2-3 days
**Impact**: MEDIUM (validate improvements)
**Owner**: QA Engineer

**Scope**:
1. Benchmark queries before/after indexes
2. Measure Episodic→Graph overhead
3. Test consolidation with 8,128+ events
4. Load test with concurrent requests

**Deliverables**:
- Performance benchmark report
- Latency improvement metrics
- Throughput measurements
- Scalability projections

---

### Task 3.3: Schema Migration Testing [P0 - SAFETY]
**Status**: Scripts ready
**Effort**: 1-2 days
**Impact**: HIGH (production safety)
**Owner**: Database Engineer

**Scope**:
1. Test FK additions on staging DB
2. Verify index creation (no downtime)
3. Validate cascading deletes
4. Create rollback procedures

**Deliverables**:
- Tested migration scripts
- Rollback procedures
- Production deployment checklist

---

## PHASE 4: RELEASE PREPARATION (Days 11-14)

### Task 4.1: Documentation Updates [P1 - CLARITY]
**Status**: Ready
**Effort**: 1-2 days
**Owner**: Documentation Engineer

**Scope**:
1. Update CLAUDE.md with changes
2. Update API reference
3. Add migration guide
4. Document new features

**Deliverables**:
- Updated documentation
- Migration guide for users
- Deployment guide

---

### Task 4.2: Testing & QA [P0 - QUALITY]
**Status**: Ready
**Effort**: 2-3 days
**Owner**: QA Engineer

**Scope**:
1. Run full test suite (expected: all passing)
2. Integration tests for new features
3. Regression testing on all layers
4. Load testing

**Deliverables**:
- Test report (94/94+ passing)
- No regressions identified
- Performance validation

---

### Task 4.3: Release & Deployment [P0 - DELIVERY]
**Status**: Ready
**Effort**: 1 day
**Owner**: DevOps + Team Lead

**Scope**:
1. Create release PR
2. Deploy to staging
3. Run smoke tests
4. Deploy to production
5. Monitor for 24 hours

**Deliverables**:
- Release PR merged
- Production deployment successful
- Monitoring alerts in place

---

## TASK DEPENDENCIES & CRITICAL PATH

```
Week 1:
├─ Day 1-2: Implement tool stubs [2.1.1]
├─ Day 1-2: Add FK relationships [parallel]
├─ Day 2-3: Add indexes [parallel]
├─ Day 3-4: Episodic→Graph extraction [starts after indexes]
└─ Day 4: Tool documentation [parallel]

Week 2:
├─ Day 5-6: Consolidation prioritization
├─ Day 6-7: Error handling framework
├─ Day 7-8: Performance testing
├─ Day 8-9: Schema migration testing
├─ Day 9-10: Documentation updates
├─ Day 10-11: Full QA & testing
└─ Day 11-14: Release prep & deployment
```

**Critical Path** (longest chain):
1. Tool stubs + FK + Indexes (3 days)
2. Episodic→Graph (3 days)
3. Testing (3 days)
4. Release (1 day)
**Total**: ~10 days critical path

---

## RESOURCE ALLOCATION

**Team Composition** (3 engineers, 2 weeks):
- **Backend Engineer 1** (160 hours)
  - Tool stub implementation
  - Episodic→Graph extraction
  - Error handling framework

- **Backend Engineer 2** (160 hours)
  - Database migrations
  - Index optimization
  - Consolidation prioritization

- **QA/Documentation** (80 hours)
  - Testing & benchmarks
  - Documentation
  - Release preparation

**Estimated Total**: 400 engineering hours (~2 weeks, 3 people)

---

## SUCCESS CRITERIA

### Week 1 Deliverables:
- [ ] All 17 tool stubs implemented & tested
- [ ] Foreign key relationships added & verified
- [ ] Composite indexes created & benchmarked
- [ ] Episodic→Graph extraction working
- [ ] Tool documentation updated

### Week 2 Deliverables:
- [ ] Error handling framework deployed
- [ ] Performance tests passed (30-40% improvement)
- [ ] Schema migrations tested & safe
- [ ] All 94+ tests passing
- [ ] Production deployment complete

### Quality Gates:
- ✅ Test coverage >95%
- ✅ No regressions identified
- ✅ Performance benchmarks show improvement
- ✅ Error rate <0.1%
- ✅ All documentation updated

---

## RISK MITIGATION

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| FK constraints block existing data | Medium | Run data audit before adding FKs; use ALTER ADD with validation |
| Indexes slow writes temporarily | Low | Create indexes concurrently; off-peak timing |
| Episodic→Graph extraction slow | Medium | Implement batching; async processing |
| Tool stubs have missing methods | Medium | Comprehensive testing; integration tests |
| Schema migration fails in prod | Low | Thorough staging tests; rollback procedure |

---

## NEXT STEPS (Post Week 2)

Once this plan is complete:

**Weeks 3-4** (Medium-term):
- Task Learning & Execution Analytics [Project 2]
- PostgreSQL Optimization [Project 7]

**Weeks 5-8** (Medium-term):
- Adaptive Layer Weighting [Project 3]
- Advanced RAG Optimization [Project 4]

**Weeks 9-12** (Long-term):
- Planning System Enhancement [Project 6]
- MaaS Product Development [Innovation]

---

## APPROVAL & SIGN-OFF

**Status**: Ready for execution
**Created**: November 16, 2025
**Next Review**: Daily standups (Mon-Fri)
**Completion Target**: November 30, 2025

