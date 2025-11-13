# MCP Operation Router - Quick Reference Guide

## 31 Meta-Tools at a Glance

### Core Memory Stack (70 operations)
| Tool | Ops | Purpose | Key Operations |
|------|-----|---------|-----------------|
| **memory_tools** | 28 | Core recall, storage, quality | recall, remember, forget, smart_retrieve |
| **episodic_tools** | 9 | Event recording & timeline | record_event, recall_events, get_timeline |
| **procedural_tools** | 8 | Workflow learning | create_procedure, find_procedures, apply_suggestion |
| **graph_tools** | 15 | Entity relationships | search_graph, create_entity, get_associations |
| **consolidation_tools** | 10 | Pattern extraction | run_consolidation, extract_patterns, measure_quality |

### Executive Function (45 operations)
| Tool | Ops | Purpose | Key Operations |
|------|-----|---------|-----------------|
| **task_management_tools** | 19 | Goal/task lifecycle | set_goal, activate_goal, complete_goal |
| **planning_tools** | 16 | Task decomposition | decompose_with_strategy, validate_plan, check_goal_conflicts |
| **phase6_planning_tools** | 10 | Advanced planning | validate_plan_comprehensive, simulate_plan_scenarios, trigger_adaptive_replanning |

### Monitoring & Analysis (20 operations)
| Tool | Ops | Purpose | Key Operations |
|------|-----|---------|-----------------|
| **monitoring_tools** | 8 | Health tracking | get_task_health, get_project_status, analyze_critical_path |
| **coordination_tools** | 10 | Multi-project sync | detect_bottlenecks, detect_resource_conflicts, analyze_uncertainty |
| **analysis_tools** | 2 | Code analysis | analyze_project_codebase, store_project_analysis |

### Advanced Retrieval (17 operations)
| Tool | Ops | Purpose | Key Operations |
|------|-----|---------|-----------------|
| **rag_tools** | 6 | Semantic search | retrieve_smart, reflective_retrieve, calibrate_uncertainty |
| **graphrag_tools** | 5 | Community detection | detect_graph_communities, find_bridge_entities |
| **zettelkasten_tools** | 6 | Memory versioning | create_memory_version, create_hierarchical_index |

### Learning & Optimization (23 operations)
| Tool | Ops | Purpose | Key Operations |
|------|-----|---------|-----------------|
| **ml_integration_tools** | 7 | ML strategies | recommend_strategy, predict_task_duration, compute_memory_saliency |
| **skills_tools** | 7 | Skill enhancement | analyze_health_trends, get_skill_recommendations |
| **agent_optimization_tools** | 5 | Agent tuning | optimize_planning_orchestrator, optimize_goal_orchestrator |
| **skill_optimization_tools** | 4 | Learning optimization | optimize_learning_tracker, optimize_gap_detector |

### Execution & Automation (23 operations)
| Tool | Ops | Purpose | Key Operations |
|------|-----|---------|-----------------|
| **automation_tools** | 5 | Event triggering | register_automation_rule, trigger_automation_event |
| **hook_coordination_tools** | 5 | Hook optimization | optimize_session_start, optimize_post_tool_use |
| **hooks_tools** | 5 | Hook management | register_hook, trigger_hook, detect_hook_cycles |
| **spatial_tools** | 8 | Code structure | build_spatial_hierarchy, analyze_symbols, code_navigation |

### Safety & Context (33 operations)
| Tool | Ops | Purpose | Key Operations |
|------|-----|---------|-----------------|
| **safety_tools** | 7 | Change validation | evaluate_change_safety, analyze_change_risk |
| **ide_context_tools** | 8 | IDE integration | get_ide_context, get_file_changes, get_git_status |
| **conversation_tools** | 8 | Session management | get_conversation_history, resume_conversation_session |
| **resilience_tools** | 6 | System health | check_system_health, configure_circuit_breaker |
| **performance_tools** | 4 | Query optimization | get_performance_metrics, optimize_queries |

### Financial & Coordination (23 operations)
| Tool | Ops | Purpose | Key Operations |
|------|-----|---------|-----------------|
| **financial_tools** | 6 | Cost tracking | calculate_task_cost, track_budget, estimate_roi |
| **security_tools** | 2 | Security | analyze_code_security, track_sensitive_data |
| **integration_tools** | 12 | Cross-layer | planning_assistance, analyze_project_coordination |
| **orchestration_tools** | 3 | Multi-agent | orchestrate_agent_tasks, recommend_planning_patterns |

---

## 20 Operation Clusters (User Workflows)

### Tier: CRITICAL (6 clusters)
```
1. Session Priming (500ms)
   → get_project_status → get_memory_quality_summary → get_active_goals

2. Memory Search & Recall (300ms)
   → recall → get_associations → temporal_kg_synthesis

3. Task Planning & Decomposition (800ms)
   → decompose_with_strategy → check_goal_conflicts → generate_alternative_plans

4. Goal & Task Management (400ms)
   → set_goal → activate_goal → record_execution_progress → complete_goal

5. Plan Validation & Risk (2000ms)
   → validate_plan_comprehensive → verify_plan_properties → simulate_plan_scenarios

6. Execution Monitoring (1000ms)
   → get_task_health → monitor_execution_deviation → trigger_adaptive_replanning
```

### Tier: IMPORTANT (6 clusters)
```
7. Pattern Consolidation (3000ms)
   → run_consolidation → extract_consolidation_patterns → measure_consolidation_quality

8. Knowledge Graph Navigation (400ms)
   → search_graph → get_associations → find_memory_path

9. Cognitive Load Management (200ms)
   → get_working_memory → check_cognitive_load → consolidate_working_memory

10. Memory Quality & Gaps (600ms)
    → get_memory_quality_summary → detect_knowledge_gaps → analyze_coverage

11. Procedural Learning (500ms)
    → find_procedures → apply_suggestion → record_execution

12. Strategy Selection & Optimization (700ms)
    → recommend_strategy → analyze_strategy_effectiveness
```

### Tier: USEFUL (6 clusters)
```
13. Advanced Retrieval & Ranking (800ms)
14. Automation & Triggering (300ms)
15. Code & Context Analysis (1500ms)
16. Safety & Risk Management (600ms)
17. Cost & Resource Planning (500ms)
18. System Health Monitoring (800ms)
```

### Tier: NICE-TO-HAVE (2 clusters)
```
19. Agent & Skill Optimization (1000ms)
20. Community & Connection Discovery (1200ms)
```

---

## 6 User Workflow Patterns

| Workflow | Duration | Clusters | Key Operations |
|----------|----------|----------|-----------------|
| **Daily Morning** | 2-3 min | Session Priming | get_project_status, get_memory_quality_summary, get_goal_priority_ranking |
| **Complex Feature** | 30-60 min | Planning + Validation + Consolidation | smart_retrieve, decompose_with_strategy, validate_plan_comprehensive, run_consolidation |
| **Bug Fix** | 15-45 min | Search + Analysis + Procedure | recall, analyze_project_codebase, decompose_with_strategy, create_procedure |
| **Weekly Consolidation** | 5-10 min | Consolidation | run_consolidation, extract_patterns, measure_quality, analyze_project_patterns |
| **Project Review** | 10-15 min | Monitoring + Analysis | get_project_status, analyze_critical_path, detect_bottlenecks, optimize_plan_suggestions |
| **Crisis Management** | 5-30 min | Search + Planning + Monitoring | recall, get_ide_context, generate_lightweight_plan, verify_task |

---

## Priority Summary

| Tier | Count | % | Impact if Missing | Usage/Session |
|------|-------|---|-------------------|----------------|
| **CRITICAL** | 85 | 33.5% | Workflow broken | 3-5 times |
| **IMPORTANT** | 80 | 31.5% | 30-50% degradation | 1-3 times |
| **USEFUL** | 60 | 23.6% | 10-20% loss | 0-2 times |
| **NICE-TO-HAVE** | 29 | 11.4% | Minimal | 0-1 times |

---

## Quick Command Reference

### Session Start
```
get_project_status              # Load project context
get_memory_quality_summary      # Check memory health
get_working_memory              # Check cognitive load
get_active_goals                # List active goals
```

### During Work
```
recall                          # Search memory
decompose_with_strategy         # Break down task
validate_plan_comprehensive     # Validate plan
monitor_execution_deviation     # Track progress
```

### Session End
```
run_consolidation               # Extract patterns
analyze_strategy_effectiveness  # Review strategies
get_memory_quality_summary      # Final health check
```

### Weekly Review
```
run_consolidation               # Deep consolidation
extract_consolidation_patterns  # Get new patterns
measure_consolidation_quality   # Check quality metrics
analyze_project_patterns        # Cross-project analysis
```

---

## Integration Points

```
Core Memory ←→ Task Management ←→ Monitoring
    ↓              ↓                  ↓
Learning       Execution         Analysis
    ↓              ↓                  ↓
Strategies   Automation         Insights
```

---

## Performance Tips

- **Fastest** (<100ms): get_working_memory, check_cognitive_load, get_active_goals
- **Slowest** (>2000ms): run_consolidation, analyze_project_codebase, validate_plan_comprehensive
- **Run async**: consolidation (3s), code analysis (2.5s), validation (2s)
- **Cache**: frequently accessed: memory_quality, task_health, project_status

---

## MVP Focus (CRITICAL Only)

```
Core Memory
├─ recall, remember, forget
├─ record_event, get_timeline
├─ search_graph, create_entity
└─ run_consolidation

Task Management
├─ set_goal, activate_goal, complete_goal
├─ decompose_with_strategy
└─ validate_plan_comprehensive

Monitoring
├─ get_task_health
├─ get_project_status
└─ monitor_execution_deviation
```

**Estimated effort**: 2-3 weeks for 85 critical operations

---

## Full Reference

See `MCP_ARCHITECTURE_ANALYSIS.json` for complete operation definitions, timing, and integration details.

---

**Last Updated**: 2025-11-06  
**Status**: Complete Analysis
