# handlers.py Analysis Document

**Date**: 2025-11-13
**Status**: Complete
**Total Methods Analyzed**: 313

---

## Summary

The handlers.py file contains **313 handler methods** that can be categorized into **11 domains**. A refined categorization achieves ~100% coverage without uncategorized methods by treating all unclassified items as "system" operations.

---

## Categorization Results

| Category | Methods | Est. Lines | % of Total |
|----------|---------|-----------|-----------|
| **memory_core** | 6 | 280 | 1.9% |
| **episodic** | 18 | 640 | 4.1% |
| **procedural** | 25 | 850 | 6.1% |
| **prospective** | 25 | 850 | 6.1% |
| **graph** | 11 | 430 | 3.1% |
| **working_memory** | 12 | 460 | 3.5% |
| **metacognition** | 11 | 430 | 3.1% |
| **planning** | 33 | 1,090 | 10.5% |
| **consolidation** | 8 | 340 | 2.4% |
| **research** | 2 | 160 | 1.2% |
| **system** | 162 | 4,960 | 47.4% |
| **handlers.py (core)** | - | 600 | 4.6% |
| **Total** | 313 | 10,490 | 100% |

---

## Detailed Breakdown

### 1. handlers_memory_core.py (6 methods, ~280 lines)

Core memory operations (remember, recall, forget, list, search):

```
• forget
• list_memories
• optimize (core memory optimization)
• recall
• recall_events
• remember
• search_projects
```

**Primary Imports Needed**:
- UnifiedMemoryManager
- MemoryType
- StructuredResult

---

### 2. handlers_episodic.py (18 methods, ~640 lines)

Event recording, retrieval, and temporal operations:

```
• batch_record_events
• cluster_consolidation_events
• consolidation_analyze_performance
• consolidation_analyze_project
• consolidation_analyze_strategy
• consolidation_analyze_validation
• consolidation_cluster_events
• consolidation_discover_orchestration
• consolidation_extract_patterns
• consolidation_measure_advanced
• consolidation_measure_quality
• consolidation_quality_metrics
• consolidation_run_consolidation
• get_timeline
• record_event
• recall_events_by_session
• schedule_consolidation
```

**Primary Imports Needed**:
- EpisodicStore
- EpisodicEvent, EventType, EventContext
- ConsolidationSystem

---

### 3. handlers_procedural.py (25 methods, ~850 lines)

Workflow management, procedures, and execution tracking:

```
• compare_procedure_versions
• create_memory_version
• create_procedure
• execute_automation_workflow
• execute_procedure
• find_procedures
• generate_procedure_code
• generate_workflow_from_task
• get_execution_context
• get_pattern_effectiveness
• get_procedure_effectiveness
• get_workflow_status
• learn_from_outcomes
• list_procedure_versions
• monitor_execution
• record_execution
• rollback_procedure
• suggest_procedure_improvements
• suggest_refactorings
• suggest_bug_fixes
• suggest_cost_optimizations
• synthesize_knowledge
• train_estimation_model
• trigger_automation_event
```

**Primary Imports Needed**:
- ProceduralStore
- Procedure, ProcedureCategory
- ExecutionMonitoring

---

### 4. handlers_prospective.py (25 methods, ~850 lines)

Task management, goals, milestones, and planning:

```
• activate_goal
• analyze_task_analytics_detailed
• calculate_task_cost
• check_goal_conflicts
• complete_goal
• create_task
• create_task_from_template
• create_task_with_milestones
• create_task_with_planning
• estimate_task_resources_detailed
• generate_task_plan
• get_active_goals
• get_goal_priority_ranking
• get_task_health
• list_tasks
• start_task
• suggest_planning_strategy
• update_milestone_progress
• update_task_status
• verify_task
• what_changed_since
• when_was_introduced
• who_introduced_regression
```

**Primary Imports Needed**:
- ProspectiveStore
- ProspectiveTask, TaskStatus, TaskPriority
- TaskMonitor

---

### 5. handlers_graph.py (11 methods, ~430 lines)

Knowledge graph operations:

```
• add_observation
• analyze_community_connectivity
• analyze_coverage
• analyze_graph_metrics
• create_entity
• create_relation
• detect_graph_communities
• expand_knowledge_relations
• get_community_details
• search_graph
• search_graph_with_depth
```

**Primary Imports Needed**:
- GraphStore
- Entity, Relation, EntityType, RelationType
- GraphAnalyzer

---

### 6. handlers_working_memory.py (12 methods, ~460 lines)

Working memory operations and goal management:

```
• auto_focus_top_memories
• clear_working_memory
• consolidate_working_memory
• find_memory_path
• get_associations
• get_working_memory
• get_active_goals
• set_attention_focus
• set_goal
• strengthen_association
• update_working_memory
```

**Primary Imports Needed**:
- CentralExecutive, PhonologicalLoop, VisuospatialSketchpad, EpisodicBuffer
- AssociationNetwork

---

### 7. handlers_metacognition.py (11 methods, ~430 lines)

Quality metrics, learning, gaps, and reflection:

```
• check_cognitive_load
• detect_knowledge_gaps
• evaluate_memory_quality
• get_expertise
• get_learning_rates
• get_memory_quality_summary
• get_self_reflection
• get_metacognition_insights
• learn_from_outcomes
• assess_memory_expertise
```

**Primary Imports Needed**:
- MetaMemoryStore
- MemoryQualityMonitor
- KnowledgeGapDetector
- SelfReflectionSystem
- CognitiveLoadMonitor

---

### 8. handlers_planning.py (33 methods, ~1,090 lines)

Planning, verification, validation, and strategy:

```
• decompose_hierarchically
• decompose_with_strategy
• estimate_confidence_interval
• generate_alternative_plans
• generate_alternative_plans_impl
• generate_confidence_scores
• planning_analyze_failure
• planning_assistance
• planning_create_validation_gate
• planning_extract_patterns
• planning_generate_lightweight
• planning_monitor_deviation
• planning_recommend_patterns
• planning_refine_plan
• planning_simulate_scenarios
• planning_trigger_replanning
• planning_validate_comprehensive
• planning_validate_llm
• planning_validation_benchmark
• planning_verify_properties
• rag_route_planning_query
• recommend_orchestration
• recommend_strategy
• suggest_planning_strategy
• trigger_replanning
• validate_plan
• validate_plan_with_reasoning
• verify_plan
• improve_estimations
• analyze_estimation_accuracy
• analyze_estimation_accuracy_adv
• analyze_uncertainty
• check_safety_policy
```

**Primary Imports Needed**:
- PlanningStore, PlanValidator, ValidationResult
- FormalVerificationEngine
- AdaptiveReplanning
- PlanMonitor

---

### 9. handlers_consolidation.py (8 methods, ~340 lines)

Consolidation and advanced retrieval:

```
• rag_calibrate_uncertainty
• rag_enrich_temporal_context
• rag_reflective_retrieve
• rag_retrieve_smart
• smart_retrieve
• spatial_distance
• spatial_indexing
• spatial_query
```

**Primary Imports Needed**:
- ConsolidationSystem
- RAGManager
- SpatialStore

---

### 10. handlers_research.py (2 methods, ~160 lines)

Research operations:

```
• research_findings
• store_research_findings
```

**Primary Imports Needed**:
- ResearchStore
- ResearchFinding
- ResearchMemoryIntegrator

---

### 11. handlers_system.py (162 methods, ~4,960 lines)

System monitoring, analytics, code analysis, project management, automation, and all other operations:

```
Categories within System:
- Project & Code Analysis (15 methods)
  • add_code_entities
  • add_project_dependency
  • analyze_code_file
  • analyze_code_security
  • analyze_project_codebase
  • analyze_project_coordination
  • analyze_repository
  • analyze_symbols
  • code_navigation
  • find_code_dependencies
  • find_symbol_dependencies
  • find_symbol_dependents
  • get_code_statistics
  • index_code_repository
  • search_code_*

- Health & Monitoring (15 methods)
  • check_system_health
  • get_health_report
  • get_layer_health
  • get_project_dashboard
  • analyze_health_trends
  • get_performance_metrics
  • detect_bottlenecks
  • get_resilience_status
  • synchronize_layers

- Analytics & Metrics (20 methods)
  • aggregate_analytics_summary
  • analyze_change_risk
  • analyze_author_risk
  • analyze_critical_path
  • get_commits_by_author
  • get_commits_by_file
  • find_high_risk_commits
  • get_analysis_metrics
  • get_regression_statistics
  • record_regression

- Distributed & Executive (15 methods)
  • recommend_orchestration
  • get_executive_function_tools
  • (executive function integration)

- Automation & Rules (25 methods)
  • register_automation_rule
  • list_automation_rules
  • update_automation_config
  • delete_rule
  • create_rule
  • trigger_hook
  • register_hook
  • list_hooks
  • detect_hook_cycles
  • override_rule

- Code Insights & Patterns (30 methods)
  • extract_bug_fix_patterns
  • extract_code_patterns
  • extract_refactoring_patterns
  • get_pattern_library
  • get_pattern_statistics
  • discover_patterns
  • discover_patterns_advanced
  • detect_code_smells
  • detect_bottlenecks_advanced
  • (pattern discovery and analysis)

- Budget & Resource (15 methods)
  • calculate_roi
  • estimate_roi
  • track_budget
  • get_resource_allocation
  • forecast_resource_needs
  • estimate_resources
  • detect_budget_anomalies
  • suggest_cost_optimizations

- IDE & Context (20 methods)
  • get_ide_context
  • track_ide_activity
  • get_cursor_position
  • get_open_files
  • get_recent_files
  • get_git_status
  • get_file_changes
  • get_file_history
  • get_file_recommendations
  • record_code_analysis
  • record_git_commit

- External Integration (10 methods)
  • lookup_external_knowledge
  • map_external_data
  • import_context_from_source
  • sync_with_external_system
  • list_external_sources
  • export_conversation_data
  • export_insights_to_system
  • recover_conversation_context
  • track_sensitive_data

- Conversation & History (10 methods)
  • add_message_to_conversation
  • get_conversation_history
  • list_active_conversations
  • start_new_conversation
  • export_conversation_data

- Other System Operations (15+ methods)
  • manage_cache
  • apply_suggestion
  • dismiss_suggestion
  • get_suggestions
  • get_skill_recommendations
  • get_saliency_recommendation
  • batch_operations
  • execute_code
  • test_fallback_chain
  • get_sandbox_config
  • configure_rate_limiting
  • configure_retry_policy
  • configure_circuit_breaker
  • create_code_snapshot
  • create_context_snapshot
  • get_audit_trail
  • request_approval
  • evaluate_change_safety
  • validate_code
  • inhibit_memory
  • temporal_kg_synthesis
  • temporal_search_enrich
  • graph_find_related_context
  • get_causal_context
  • get_spatial_context
  • symbol_analysis
  • create_hierarchical_index
  • build_spatial_hierarchy
  • explore_concept_network
  • find_bridge_entities
  • query_communities_by_level
  • compute_memory_attributes
  • compute_memory_saliency
  • get_memory_attributes
  • get_memory_evolution_history
  • get_saliency_batch
  • assign_memory_to_index
  • score_semantic_memories
  • bayesian_surprise_benchmark
```

**Primary Imports Needed**:
- ProjectManager
- LayerHealthMonitor
- GraphAnalyzer
- ExecutiveAgentBridge
- All integration modules

---

### 12. handlers.py (Core, ~600 lines)

Server class, tool registration, routing:

```
• MemoryMCPServer (class definition)
  - __init__
  - setup_tools
  - setup_consolidation_tools
  - setup_episodic_tools
  - setup_procedural_tools
  - setup_prospective_tools
  - setup_graph_tools
  - setup_working_memory_tools
  - setup_meta_tools
  - setup_planning_tools
  - setup_system_tools

• Tool listing & calling
  - list_tools
  - call_tool

• Main entry point
  - run_mcp_server
```

---

## Dependency Analysis

### High-Level Dependencies

**Core Imports** (used by all handlers):
```python
from mcp.server import Server
from mcp.types import Tool, TextContent
from .structured_result import StructuredResult, ResultStatus, PaginationMetadata
from ..core.models import MemoryType
from ..manager import UnifiedMemoryManager
```

**Per-Handler-Group Imports** (documented above in each section)

### Cross-Domain Dependencies

**planning** → **prospective** (task planning)
**consolidation** → **episodic** (event clustering)
**metacognition** → **all** (quality measurement)
**system** → **all** (analytics, health checking)

### No Circular Dependencies Expected

Since handlers are leaf operations (they don't import other handlers), the refactored structure should have zero circular dependencies.

---

## Extraction Strategy

### Priority Order

1. **handlers_memory_core.py** - Smallest, no dependencies on others
2. **handlers_episodic.py** - Few dependencies
3. **handlers_graph.py** - Few dependencies
4. **handlers_working_memory.py** - Few dependencies
5. **handlers_metacognition.py** - Few dependencies
6. **handlers_consolidation.py** - Few dependencies
7. **handlers_procedural.py** - Depends on episodic
8. **handlers_prospective.py** - Depends on episodic
9. **handlers_research.py** - Few dependencies
10. **handlers_planning.py** - Depends on prospective
11. **handlers_system.py** - Last (catch-all, depends on others)

---

## Success Metrics

After refactoring:

| Metric | Current | Target |
|--------|---------|--------|
| handlers.py size | 12,363 lines | ~600 lines |
| Total lines (11 files) | 12,363 lines | ~10,490 lines |
| Methods per file | 313 | 28.5 avg |
| Largest file | 12,363 lines | 4,960 lines |
| Code navigation | Poor | Excellent |
| Maintenance | Hard | Easy |

---

## Next Steps

1. ✅ **Task 1 Complete**: Analysis done
2. → **Task 2**: Create handler file templates
3. → **Task 3-13**: Extract methods into specialized files
4. → **Task 14-17**: Integration, validation, documentation

---

**End of Analysis Document**
