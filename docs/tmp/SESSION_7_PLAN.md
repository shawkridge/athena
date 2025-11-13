# Session 7 - Planning & Strategy Document

**Date**: November 13, 2025 (End of Session 6)
**Status**: Planning Phase
**Objective**: Complete remaining Quick Wins + Start HIGH-priority Operations

---

## 📊 Context Summary

### Session 6 Achievements ✅
- Completed 2/4 Quick Wins (14 hours invested)
- Identified 40 missing operations across 8 layers
- Improved estimated completeness: 78.1% → ~82-85%
- Added 2 new MCP operations
- Created comprehensive test suite

### Current System Status
```
Completeness: 78.1% baseline → estimated 82-85% after Session 6 → 85-88% after Quick Wins #3-4
Layers Audit: All 8 layers analyzed with detailed missing operations list
Operations: 28 → 30 (added decay + versioning)
Test Coverage: 65% → 66% (new decay tests)
```

### Strategic Context
✅ **Token Optimization Ceiling Reached** (91-92% alignment)
✅ **Pivot to Quality Focus Validated** (10x better ROI than micro-optimizations)
✅ **Roadmap to 100% Completeness** Identified (40+ missing operations)

---

## 🎯 Session 7 Objectives

### Primary Goal: Complete Remaining Quick Wins (24 hours)

**Quick Win #3: Event Merging for Duplicates** (12 hours)
- **Layer**: Episodic (Layer 1)
- **Impact**: Reduce storage bloat, improve consolidation quality
- **Implementation**: `src/athena/episodic/store.py`
- **Files Modified**: episodic/store.py, handlers_episodic.py, operation_router.py
- **MCP Operation**: `merge_duplicate_events`

**Quick Win #4: Embedding Drift Detection** (12 hours)
- **Layer**: Semantic (Layer 2)
- **Impact**: Ensure embedding freshness, track quality
- **Foundation**: Uses versioning from Quick Win #2
- **Implementation**: `src/athena/memory/search.py`
- **Files Modified**: memory/search.py, handlers_memory_core.py, operation_router.py
- **MCP Operation**: `detect_embedding_drift`

**Expected Outcome**:
- Completeness: 82-85% → 85-88%
- New MCP operations: 30 → 32
- New test cases: +20
- Code added: ~600-800 lines

---

## 🗺️ Detailed Implementation Plan

### Phase 1: Quick Win #3 - Event Merging (Days 1-2)

#### Step 1.1: Analysis & Design (2 hours)
- [ ] Review `src/athena/episodic/store.py` structure
- [ ] Define merge strategy:
  - Content similarity threshold (0.85+)
  - Temporal proximity (within 5 minutes)
  - Preserve event chain integrity
- [ ] Design data model for merge metadata
- [ ] Document merge decision criteria

#### Step 1.2: Core Implementation (6 hours)
- [ ] Implement `detect_duplicates(self, project_id: int, threshold: float = 0.85) -> list[DuplicateGroup]`
  - Content similarity using embeddings (cosine distance)
  - Temporal proximity filtering
  - Return groupings of duplicate events

- [ ] Implement `merge_events(self, event_ids: list[int], keep_id: int) -> MergeResult`
  - Merge metadata (keep all important fields)
  - Preserve event references in consolidation
  - Update references in graph/procedural layers
  - Log merge operation for audit trail

- [ ] Add merge statistics tracking
  - `merge_count`, `unique_fields_preserved`, `storage_savings_bytes`

#### Step 1.3: MCP Handler & Routing (2 hours)
- [ ] Add `_handle_merge_duplicate_events` in `handlers_episodic.py`
- [ ] Register operation in `operation_router.py`
- [ ] Add comprehensive docstring with examples

#### Step 1.4: Testing (4 hours)
- [ ] Unit tests: Detection logic, merge operations, edge cases
- [ ] Integration tests: Merge with consolidation, graph references
- [ ] Performance tests: Merge large event sets
- [ ] Test coverage: Aim for 90%+ of new code

#### Step 1.5: Documentation & Verification (2 hours)
- [ ] Update docstrings
- [ ] Add examples in handler docstring
- [ ] Verify backward compatibility
- [ ] Create mini test report

---

### Phase 2: Quick Win #4 - Embedding Drift Detection (Days 3-4)

#### Step 2.1: Design & Foundation (2 hours)
- [ ] Review embedding versioning from Quick Win #2
- [ ] Design drift detection algorithm:
  - Compare current model version vs event embedding version
  - Flag mismatches as "stale"
  - Estimate re-embedding cost
- [ ] Define drift report structure

#### Step 2.2: Core Implementation (6 hours)
- [ ] Implement `detect_embedding_drift(self, project_id: int) -> DriftReport`
  - Query all events with embedding metadata
  - Get current model version
  - Detect version mismatches
  - Count stale vectors
  - Estimate cost (tokens, time)

- [ ] Implement `refresh_embeddings(self, event_ids: Optional[list[int]] = None, batch_size: int = 100) -> RefreshResult`
  - Re-embed specified events (or all if None)
  - Update model version in metadata
  - Preserve temporal metadata
  - Return refresh statistics

- [ ] Add health metrics:
  - `drift_percentage`, `stale_vectors`, `estimated_cost_tokens`

#### Step 2.3: Integration with Health System (2 hours)
- [ ] Update `src/athena/memory/search.py` health checks
- [ ] Add drift detection to health report
- [ ] Create recommended actions for stale embeddings

#### Step 2.4: MCP Handler & Routing (2 hours)
- [ ] Add `_handle_detect_embedding_drift` in `handlers_memory_core.py`
- [ ] Add `_handle_refresh_embeddings` in `handlers_memory_core.py`
- [ ] Register operations in `operation_router.py`

#### Step 2.5: Testing (4 hours)
- [ ] Unit tests: Drift detection, version comparison
- [ ] Integration tests: Refresh with semantic search
- [ ] Cost estimation accuracy tests
- [ ] Test coverage: 90%+ of new code

#### Step 2.6: Documentation & Verification (2 hours)
- [ ] Update docstrings with examples
- [ ] Document drift detection algorithm
- [ ] Verify backward compatibility
- [ ] Create test report

---

## 🔄 Secondary Goal: Start HIGH-Priority Operations (Optional/Future)

If Quick Wins complete early, candidate operations by ROI:

### Priority 1: Task Dependencies (Layer 4, 14 hours)
- **Value**: Enables complex workflow management
- **Impact**: 70% → 75%
- **Implementation**: `src/athena/prospective/tasks.py`
- **Key Features**:
  - `add_dependency(task_id: int, depends_on: int)`
  - `get_blocked_tasks()` - tasks waiting on dependencies
  - `mark_dependency_complete(task_id: int, dependency_id: int)`

### Priority 2: Procedure Composition (Layer 3, 16 hours)
- **Value**: Enables workflow automation
- **Impact**: 75% → 80%
- **Implementation**: `src/athena/procedural/procedures.py`
- **Key Features**:
  - `compose_procedures(proc_ids: list[int]) -> ComposedProcedure`
  - `execute_composed(composed_id: int, params: dict) -> Result`
  - Handles parameter threading between procedures

### Priority 3: Goal Progress Tracking (Layer 4, 10 hours)
- **Value**: Enable goal-driven systems
- **Impact**: 70% → 73%
- **Implementation**: `src/athena/prospective/goals.py`
- **Key Features**:
  - `track_progress(goal_id: int, progress_value: float)`
  - `predict_completion(goal_id: int) -> Prediction`
  - `get_blocking_issues(goal_id: int) -> list[Issue]`

---

## 📋 Daily Schedule (Recommended)

### Day 1: Quick Win #3 Part A (6 hours)
- 1-2h: Analysis & design
- 2-3h: Core detection implementation
- 3-4h: Start core merge implementation
- 4-5h: Continue merge implementation
- 5-6h: Begin testing

### Day 2: Quick Win #3 Part B (6 hours)
- 1-2h: Complete merge implementation
- 2-3h: Finish testing (unit tests)
- 3-4h: Integration tests
- 4-5h: MCP handler + routing
- 5-6h: Documentation & verification

### Day 3: Quick Win #4 Part A (6 hours)
- 1-2h: Design & requirements
- 2-3h: Drift detection implementation
- 3-4h: Cost estimation implementation
- 4-5h: Health system integration
- 5-6h: Begin testing

### Day 4: Quick Win #4 Part B (6 hours)
- 1-2h: Complete core implementation
- 2-3h: Finish testing
- 3-4h: MCP handlers
- 4-5h: Integration verification
- 5-6h: Documentation & final checks

### Buffer (2-3 hours)
- Async test failures
- Edge case fixes
- Additional validation

---

## 🧪 Testing Strategy

### Unit Tests (Per Quick Win)
```python
# Quick Win #3: Event Merging
- test_detect_duplicates_by_content
- test_detect_duplicates_by_temporal_proximity
- test_merge_events_preserves_chain
- test_merge_preserves_graph_references
- test_merge_with_consolidation_data
- test_merge_statistics_accuracy

# Quick Win #4: Embedding Drift
- test_detect_drift_empty_dataset
- test_detect_drift_with_version_mismatch
- test_drift_report_calculation
- test_refresh_embeddings_updates_version
- test_refresh_preserves_temporal_metadata
- test_cost_estimation_accuracy
```

### Integration Tests
- Event merging + consolidation interaction
- Drift detection + search quality impact
- Drift refresh + layer updates

### Performance Tests
- Merge 1,000+ events (target: <5 seconds)
- Detect drift in large dataset (target: <10 seconds)
- Refresh 500+ embeddings (target: <30 seconds)

---

## 📊 Success Criteria

### Functional Criteria
- [ ] Quick Win #3: Event merging fully functional
  - [ ] Duplicate detection working
  - [ ] Merge preserves data integrity
  - [ ] No data loss
  - [ ] Graph references updated

- [ ] Quick Win #4: Embedding drift detection working
  - [ ] Drift detection accurate
  - [ ] Cost estimation within 10% accuracy
  - [ ] Refresh operation successful
  - [ ] Health metrics updated

### Code Quality Criteria
- [ ] All new code passes syntax validation
- [ ] Test coverage: 90%+ of new code
- [ ] No breaking changes
- [ ] Backward compatible

### Documentation Criteria
- [ ] Comprehensive docstrings
- [ ] Examples in handler docs
- [ ] Design document for each Quick Win
- [ ] Test report generated

### Performance Criteria
- [ ] Event merging: <5 seconds for 1,000 events
- [ ] Drift detection: <10 seconds for 10,000 events
- [ ] No performance regression in existing operations

---

## 🎓 Learning Goals

### Technical Learning
- [ ] Understand embedding versioning patterns
- [ ] Learn duplicate detection algorithms
- [ ] Explore event chain integrity preservation
- [ ] Study drift detection best practices

### System Understanding
- [ ] How layers interact during merge
- [ ] Propagation of changes across layers
- [ ] Graph reference management
- [ ] Health metric integration

---

## 📝 Deliverables

### Code Deliverables
1. **Event Merging Implementation**
   - `src/athena/episodic/store.py` (additions)
   - `src/athena/mcp/handlers_episodic.py` (handler)
   - `src/athena/mcp/operation_router.py` (routing)
   - `tests/unit/test_event_merging.py` (tests)

2. **Embedding Drift Detection Implementation**
   - `src/athena/memory/search.py` (additions)
   - `src/athena/mcp/handlers_memory_core.py` (handlers)
   - `src/athena/mcp/operation_router.py` (routing update)
   - `tests/unit/test_embedding_drift.py` (tests)

### Documentation Deliverables
1. Session 7 completion report
2. Quick Win #3 design document
3. Quick Win #4 design document
4. Test report with coverage metrics
5. Updated LAYER_COMPLETENESS_ANALYSIS.md

---

## 🚀 Post-Session 7 Roadmap

### Estimated Completeness Progress
```
Session 6: 78.1% → ~82-85%
Session 7: ~82-85% → ~85-88% (Quick Wins #3-4)
Session 8: ~85-88% → ~88-92% (HIGH-priority ops #1-3)
Session 9+: ~88-92% → 95%+ (Remaining operations)
```

### Next Major Milestones
1. **Session 8**: HIGH-priority operations (task dependencies, procedure composition, goal tracking)
2. **Session 9**: MEDIUM-priority operations (error handling, edge cases)
3. **Session 10**: Test coverage improvement (80%+ overall)
4. **Session 11**: Phase 7 features (advanced planning, GraphRAG optimizations)
5. **Session 12**: Production hardening & optimization

---

## 💡 Key Insights for Session 7

### What to Remember
1. **Quick Wins are High-ROI**: 24 hours → 3-4% completeness gain (10x better than micro-optimizations)
2. **Backward Compatibility is Critical**: No breaking changes allowed
3. **Documentation is Part of the Feature**: Every Quick Win needs design + tests + docs
4. **Early Testing Saves Time**: Test as you build, not after

### Potential Challenges & Solutions
| Challenge | Solution |
|-----------|----------|
| Event merge with consolidation conflicts | Design merge before consolidation |
| Embedding version tracking reliability | Implement robust version detection |
| Drift detection performance on large datasets | Use indexed queries, batch processing |
| Cost estimation accuracy | Validate against actual embedding costs |

### Time Estimates (Contingency)
- **Optimistic**: 20-22 hours (Quick Wins #3-4)
- **Realistic**: 24-26 hours (with testing, docs)
- **Pessimistic**: 28-30 hours (with troubleshooting)

---

## 📌 Session 7 Entry Point

### Before Starting Session 7
1. Read this plan
2. Review Session 6 completion report
3. Check git status (ensure clean working directory)
4. Run syntax validation on any modified code

### Command to Resume
```bash
cd /home/user/.work/athena
git log -1 --oneline  # Verify last commit is Session 6
cat docs/tmp/SESSION_7_PLAN.md  # This file
pytest tests/unit/ -v -m "not benchmark"  # Verify baseline
```

### First Task in Session 7
Start with **Quick Win #3: Event Merging**
1. Review `src/athena/episodic/store.py` structure
2. Design merge strategy (duplicate detection + merge logic)
3. Implement core functions
4. Add tests

---

## ✅ Verification Checklist

Before committing Session 7 work:
- [ ] All syntax valid (py_compile)
- [ ] All tests passing (unit + integration)
- [ ] Backward compatibility verified
- [ ] No breaking changes
- [ ] Documentation complete
- [ ] Code review checklist passed
- [ ] Performance targets met
- [ ] Examples added to docstrings

---

## 📞 Summary

### Session 7 Mission
✅ **Complete Remaining Quick Wins #3-4** (24 hours)
✅ **Improve completeness: 82-85% → 85-88%**
✅ **Add 2 new MCP operations**
✅ **Maintain 100% backward compatibility**

### Expected Outcome
```
Completeness: ~85-88%
New Operations: +2 (merge, drift detection)
Test Coverage: 66% → 68%
Code Quality: Maintained/improved
Production Readiness: ✅ Maintained
```

---

**Generated**: November 13, 2025
**Time to Prepare**: ~30 minutes
**Time to Execute**: ~24-26 hours
**Expected ROI**: +3-4% completeness (10x ROI vs. micro-optimizations)

🚀 Ready to start Session 7!
