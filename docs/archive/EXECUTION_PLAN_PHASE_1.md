# Phase 1: Test Coverage Expansion (Weeks 1-2)

**Duration**: 2 weeks
**Goal**: Expand MCP tool tests from 50-70% to 95%+
**Success**: 350+ tests passing with 95%+ coverage

---

## Overview

### Current State
- Total tests: 240
- MCP tool coverage: 50-70%
- Integration tests: ~30-40
- Missing: Edge cases, error handling, concurrent scenarios

### Target State
- Total tests: 350+
- MCP tool coverage: 95%+
- Integration tests: 130+
- Complete: All error paths, boundary conditions, interactions

### Effort
- **Week 1**: 40-50 new MCP tool tests
- **Week 2**: 100+ integration tests
- **Total new tests**: 140-150
- **Estimated time**: 60-80 hours

---

## Week 1: MCP Tool Test Coverage (40-50 tests)

### Task 1.1: Memory Tools Tests (10-15 tests)

**File**: `tests/mcp/tools/test_memory_tools.py`
**Current**: ~26 tests
**Target**: 40+ tests
**Gap**: 14-15 new tests

**Tests to add**:
```python
# Error handling
- test_recall_with_invalid_query_format
- test_recall_with_null_query
- test_recall_with_empty_results
- test_remember_with_duplicate_memory
- test_remember_with_oversized_context
- test_forget_with_nonexistent_id
- test_forget_with_invalid_id_type

# Edge cases
- test_recall_with_special_characters
- test_recall_with_unicode_queries
- test_optimize_with_no_memory
- test_optimize_with_single_memory

# Concurrency
- test_recall_during_optimization
- test_concurrent_remember_operations
- test_remember_and_forget_race_condition
```

### Task 1.2: System Tools Tests (10-15 tests)

**File**: `tests/mcp/tools/test_system_tools.py`
**Current**: ~18 tests
**Target**: 30+ tests
**Gap**: 12-15 new tests

**Tests to add**:
```python
# Health check variations
- test_health_check_with_degraded_layer
- test_health_check_with_offline_component
- test_health_check_response_structure
- test_health_report_includes_all_metrics
- test_health_report_sorting

# Edge cases
- test_consolidation_status_with_no_events
- test_consolidation_status_with_corrupted_data
- test_metrics_with_extreme_values
- test_health_when_database_full
- test_health_under_memory_pressure

# Error scenarios
- test_health_check_timeout_handling
- test_health_report_with_missing_layers
```

### Task 1.3: Retrieval Tools Tests (10-15 tests)

**File**: `tests/mcp/tools/test_retrieval_integration_tools.py`
**Current**: ~21 tests
**Target**: 35+ tests
**Gap**: 14-15 new tests

**Tests to add**:
```python
# Strategy variations
- test_smart_retrieve_with_empty_query
- test_smart_retrieve_with_very_long_query
- test_smart_retrieve_strategy_fallback
- test_analyze_coverage_with_no_gaps
- test_analyze_coverage_with_full_gaps

# Integration scenarios
- test_retrieve_then_consolidate
- test_multiple_retrieve_calls_consistency
- test_retrieve_with_concurrent_consolidation
- test_coverage_analysis_after_new_memory

# Edge cases
- test_retrieve_timeout_handling
- test_coverage_analysis_with_corrupted_metadata
- test_smart_retrieve_cache_invalidation
```

### Task 1.4: Planning Tools Tests (10-15 tests)

**File**: `tests/mcp/tools/test_planning_tools.py`
**Current**: ~28 tests
**Target**: 40+ tests
**Gap**: 12-15 new tests

**Tests to add**:
```python
# Decomposition edge cases
- test_decompose_empty_task
- test_decompose_extremely_complex_task
- test_decompose_with_circular_dependencies
- test_decompose_invalid_strategy

# Validation scenarios
- test_validate_plan_missing_steps
- test_validate_plan_resource_constraints
- test_validate_plan_temporal_ordering

# Verification edge cases
- test_verify_with_contradictory_constraints
- test_verify_adaptive_replanning_trigger
- test_optimize_plan_efficiency

# Integration
- test_decompose_validate_verify_workflow
- test_plan_optimization_after_validation
```

---

## Week 2: Integration Tests (100+ tests)

### Task 2.1: Memory Workflow Tests (20-25 tests)

**File**: `tests/mcp/tools/test_integration_memory_workflows.py` (NEW)

**Test Categories**:
```python
class TestRecallOptimizeFlow:
    """recall → optimize workflow"""
    async def test_recall_then_optimize
    async def test_optimize_removes_low_value_memories
    async def test_recall_consistency_after_optimize
    async def test_concurrent_recall_and_optimize
    async def test_recall_optimize_preserve_important_memories

class TestRememberForgetFlow:
    """remember → forget workflow"""
    async def test_remember_then_forget
    async def test_forget_after_multiple_remember
    async def test_consistency_after_remember_forget_cycle
    async def test_forget_doesnt_affect_semantically_similar

class TestConsolidateRecallFlow:
    """consolidate → recall workflow"""
    async def test_consolidate_improves_recall_quality
    async def test_recall_after_consolidation
    async def test_consolidation_preserves_critical_memories
    async def test_concurrent_consolidate_and_recall

class TestMemoryStateConsistency:
    """State consistency across operations"""
    async def test_memory_count_consistency
    async def test_memory_uniqueness_after_operations
    async def test_storage_consistency_after_batch_ops
    async def test_recovery_after_partial_failure
```

### Task 2.2: Planning Workflow Tests (20-25 tests)

**File**: `tests/mcp/tools/test_integration_planning_workflows.py` (NEW)

**Test Categories**:
```python
class TestDecomposeValidateVerifyFlow:
    """decompose → validate → verify workflow"""
    async def test_full_planning_pipeline
    async def test_decomposed_plan_passes_validation
    async def test_verified_plan_meets_quality_gates
    async def test_plan_modifications_maintain_validity
    async def test_complex_task_planning_reliability

class TestAdaptiveReplanningFlow:
    """Plan adaptation under changing conditions"""
    async def test_replanning_on_assumption_violation
    async def test_plan_quality_after_replanning
    async def test_incremental_plan_repair
    async def test_multiple_replanning_cycles
    async def test_replanning_preserves_completed_steps

class TestScenarioSimulation:
    """Scenario-based plan validation"""
    async def test_plan_survives_adverse_scenarios
    async def test_scenario_coverage_completeness
    async def test_plan_resilience_scoring
    async def test_scenario_failure_recovery

class TestPlanQuality:
    """Overall plan quality metrics"""
    async def test_decomposition_quality_metrics
    async def test_plan_efficiency_optimization
    async def test_constraint_satisfaction_validation
```

### Task 2.3: Tool Interaction Tests (20-25 tests)

**File**: `tests/mcp/tools/test_integration_cross_tool.py` (NEW)

**Test Categories**:
```python
class TestAgentOptimizationIntegration:
    """Agent tools interaction with other systems"""
    async def test_tune_agent_then_analyze_performance
    async def test_performance_improvement_from_tuning
    async def test_multiple_agents_independent_tuning
    async def test_tuning_effects_on_consolidation
    async def test_agent_tuning_with_concurrent_tasks

class TestSkillOptimizationIntegration:
    """Skill tools integration"""
    async def test_enhance_skill_then_measure
    async def test_measurement_reflects_enhancement
    async def test_skill_improvement_accumulation
    async def test_skill_effectiveness_with_consolidation

class TestHookCoordinationIntegration:
    """Hook tools interaction"""
    async def test_register_manage_coordinate_flow
    async def test_hooks_execute_on_events
    async def test_concurrent_hook_execution
    async def test_hook_priority_ordering
    async def test_hook_failure_isolation

class TestSystemWideIntegration:
    """Cross-system integration"""
    async def test_consolidation_improves_recall
    async def test_agent_tuning_improves_reliability
    async def test_skill_enhancement_increases_coverage
    async def test_hooks_enable_automation
    async def test_full_system_workflow_end_to_end
```

### Task 2.4: Error & Edge Case Tests (25-30 tests)

**File**: `tests/mcp/tools/test_integration_edge_cases.py` (NEW)

**Test Categories**:
```python
class TestConcurrencyScenarios:
    """Concurrent operation handling"""
    async def test_10_concurrent_recall_operations
    async def test_concurrent_remember_and_forget
    async def test_concurrent_consolidation_and_recall
    async def test_race_condition_prevention
    async def test_deadlock_detection_and_prevention

class TestResourceConstraints:
    """Operation under resource limits"""
    async def test_operations_with_limited_memory
    async def test_operations_with_slow_database
    async def test_large_batch_operations
    async def test_recovery_from_out_of_memory
    async def test_recovery_from_storage_full

class TestBoundaryConditions:
    """Boundary and edge values"""
    async def test_empty_inputs_handling
    async def test_maximum_size_inputs
    async def test_null_optional_parameters
    async def test_special_characters_in_inputs
    async def test_unicode_handling

class TestFailureRecovery:
    """Graceful failure handling"""
    async def test_partial_operation_failure
    async def test_tool_timeout_handling
    async def test_invalid_data_detection
    async def test_rollback_on_failure
    async def test_consistency_after_failure
```

---

## Execution Strategy

### Week 1 Schedule

**Day 1-2**: Task 1.1 (Memory Tools)
- Identify uncovered code paths
- Write 14-15 new tests
- Run and verify

**Day 3**: Task 1.2 (System Tools)
- Identify uncovered code paths
- Write 12-15 new tests
- Run and verify

**Day 4**: Task 1.3 (Retrieval Tools)
- Identify uncovered code paths
- Write 14-15 new tests
- Run and verify

**Day 5-6**: Task 1.4 (Planning Tools)
- Identify uncovered code paths
- Write 12-15 new tests
- Run and verify

**Day 7**: Review & Commit
- Run full test suite
- Generate coverage report
- Commit with message: "test: Expand MCP tool coverage to 95% - Phase 1 Week 1"

### Week 2 Schedule

**Day 1-2**: Task 2.1 (Memory Workflows)
- Design 20-25 integration tests
- Implement and verify
- Validate interactions

**Day 3**: Task 2.2 (Planning Workflows)
- Design 20-25 integration tests
- Implement and verify
- Validate planning pipeline

**Day 4**: Task 2.3 (Cross-Tool Integration)
- Design 20-25 interaction tests
- Implement and verify
- Validate system-wide flow

**Day 5-6**: Task 2.4 (Edge Cases)
- Design 25-30 edge case tests
- Implement failure scenarios
- Validate recovery

**Day 7**: Final Review & Commit
- Run full 350+ test suite
- Generate final coverage report
- Commit: "test: Complete integration tests - Phase 1 Week 2"
- Create summary metrics

---

## Success Criteria

### Week 1 Completion
- [ ] MCP tool tests: 50-70% → 85%+ coverage
- [ ] New tests: 40-50 added
- [ ] 100% pass rate on all new tests
- [ ] All committed to main branch

### Week 2 Completion
- [ ] MCP tool tests: 85% → 95%+ coverage
- [ ] Integration tests: 30 → 130+
- [ ] Total tests: 240 → 350+
- [ ] 100% pass rate on all 350+ tests
- [ ] Coverage report showing 95%+ on tools

### Verification
```bash
# Run full test suite
pytest tests/mcp/tools/ -v

# Generate coverage report
pytest tests/mcp/tools/ --cov=src/athena/mcp/tools --cov-report=html

# Verify all passing
pytest tests/mcp/tools/ -q
```

---

## Notes

- Start with highest-impact tools (those used most frequently)
- Use parametrized tests for multiple scenarios
- Add docstrings explaining what each test validates
- Group related tests in classes
- Use fixtures for common setup
- Mock external dependencies (LLM calls, database)
- Verify both success and failure paths

