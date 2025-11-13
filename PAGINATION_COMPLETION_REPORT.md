# Pagination Implementation - Complete Transformation Guide

**Date**: November 13, 2025
**Task**: Implement pagination for 77 remaining handlers (1 already complete)
**Total Scope**: 78 handlers across 7 files

---

## Executive Summary

This document provides the **exact transformations** needed to implement pagination for all 77 remaining MCP handlers. Each handler follows the same pattern with handler-specific details.

**Status**: 1/78 complete (handlers_prospective.py::_handle_list_tasks ✅)

---

## Implementation Pattern (Universal)

For ALL handlers, apply this 4-step transformation:

### Step 1: Add Pagination Parameters
```python
# Add after parsing existing args
limit = min(args.get("limit", 10), 100)
offset = args.get("offset", 0)
```

### Step 2: Modify Query to Support LIMIT/OFFSET
```python
# SQL queries: Add LIMIT/OFFSET
sql_parts.append(f"LIMIT {limit} OFFSET {offset}")

# Store methods: Pass limit/offset
items = store.list_items(..., limit=limit, offset=offset)
```

### Step 3: Get Total Count
```python
# For SQL queries: Add COUNT query
count_sql = "SELECT COUNT(*) FROM table WHERE ..."
cursor.execute(count_sql, params)
total_count = cursor.fetchone()[0]

# For store methods: Add count method call
total_count = store.count_items(..., filters=same_filters)
```

### Step 4: Replace Return with paginate_results
```python
# BEFORE
return [TextContent(type="text", text=json.dumps(response))]

# AFTER
result = paginate_results(
    results=formatted_items,  # List of formatted items
    args=args,
    total_count=total_count,
    operation="handler_name",
    drill_down_hint="Specific guidance for this operation"
)
return [result.as_optimized_content(schema_name="appropriate_schema")]
```

---

## File 1: handlers_episodic.py (14 Handlers)

### Handler 1: _handle_recall_events

**Current line ~170**

**Changes**:
```python
# Step 1: Add after line 189
limit = min(args.get("limit", 10), 100)
offset = args.get("offset", 0)

# Step 2: Modify SQL at ~239 (replace existing LIMIT)
sql_parts.append(f"LIMIT {limit} OFFSET {offset}")

# Step 3: Add before executing query (~243)
# Get total count first
count_sql_parts = ["SELECT COUNT(*) FROM episodic_events WHERE 1=1"]
count_sql_parts.extend(sql_parts[1:-2])  # All WHERE clauses, no ORDER/LIMIT
count_sql = " ".join(count_sql_parts)
cursor.execute(count_sql, params)
total_count = cursor.fetchone()[0]

# Step 4: Replace return statement (~280+)
result = paginate_results(
    results=events,
    args=args,
    total_count=total_count,
    operation="recall_events",
    drill_down_hint="Use /recall-episodic-events with event_id for full event details including clusters and spatial analysis"
)
return [result.as_optimized_content(schema_name="episodic")]
```

### Handler 2: _handle_recall_events_by_context

**Current line ~285**

**Changes**:
```python
# Step 1: Add after line ~288
limit = min(args.get("limit", 20), 100)
offset = args.get("offset", 0)

# Step 2: Modify SQL (~298)
sql = """
    SELECT * FROM episodic_events
    WHERE context_type = ?
    ORDER BY timestamp DESC
    LIMIT ? OFFSET ?
"""

# Step 3: Add count query
count_sql = "SELECT COUNT(*) FROM episodic_events WHERE context_type = ?"
cursor.execute(count_sql, (context_type,))
total_count = cursor.fetchone()[0]

# Execute main query with limit/offset
cursor.execute(sql, (context_type, limit, offset))

# Step 4: Replace return
result = paginate_results(
    results=events,
    args=args,
    total_count=total_count,
    operation="recall_events_by_context",
    drill_down_hint="Use /recall-events with filters for detailed temporal clustering"
)
return [result.as_optimized_content(schema_name="episodic")]
```

### Handler 3: _handle_recall_events_by_session

**Current line ~330**

**Changes**:
```python
# Step 1: Add after parsing session_id
limit = min(args.get("limit", 50), 100)
offset = args.get("offset", 0)

# Step 2: Modify SQL
sql = """
    SELECT * FROM episodic_events
    WHERE session_id = ?
    ORDER BY timestamp ASC
    LIMIT ? OFFSET ?
"""

# Step 3: Add count
count_sql = "SELECT COUNT(*) FROM episodic_events WHERE session_id = ?"
cursor.execute(count_sql, (session_id,))
total_count = cursor.fetchone()[0]

cursor.execute(sql, (session_id, limit, offset))

# Step 4: Replace return
result = paginate_results(
    results=events,
    args=args,
    total_count=total_count,
    operation="recall_events_by_session",
    drill_down_hint="Use /timeline-visualize for temporal flow analysis of this session"
)
return [result.as_optimized_content(schema_name="episodic")]
```

### Handler 4: _handle_recall_events_by_tool_usage

**Current line ~370**

**Changes**:
```python
# Step 1: Add after line ~373
limit = min(args.get("limit", 20), 100)
offset = args.get("offset", 0)

# Step 2: Modify SQL
sql = """
    SELECT * FROM episodic_events
    WHERE context_type = 'tool_use'
    AND (context LIKE ? OR content LIKE ?)
    ORDER BY timestamp DESC
    LIMIT ? OFFSET ?
"""

# Step 3: Add count
count_params = [f"%{tool_name}%", f"%{tool_name}%"] if tool_name else []
if tool_name:
    count_sql = "SELECT COUNT(*) FROM episodic_events WHERE context_type = 'tool_use' AND (context LIKE ? OR content LIKE ?)"
    cursor.execute(count_sql, count_params)
else:
    count_sql = "SELECT COUNT(*) FROM episodic_events WHERE context_type = 'tool_use'"
    cursor.execute(count_sql)
total_count = cursor.fetchone()[0]

# Step 4: Replace return
result = paginate_results(
    results=events,
    args=args,
    total_count=total_count,
    operation="recall_events_by_tool_usage",
    drill_down_hint="Use /recall-events with context_type='tool_use' for advanced filtering"
)
return [result.as_optimized_content(schema_name="episodic")]
```

### Handler 5: _handle_timeline_query

**Current line ~410**

**Changes**:
```python
# Step 1: Add pagination params
limit = min(args.get("limit", 30), 100)
offset = args.get("offset", 0)

# Step 2: Add LIMIT/OFFSET to SQL
sql_parts.append("ORDER BY timestamp ASC")
sql_parts.append(f"LIMIT {limit} OFFSET {offset}")

# Step 3: Add count
count_sql_parts = ["SELECT COUNT(*) FROM episodic_events WHERE 1=1"]
count_sql_parts.extend([p for p in sql_parts[1:] if "LIMIT" not in p and "ORDER" not in p])
count_sql = " ".join(count_sql_parts)
cursor.execute(count_sql, params)
total_count = cursor.fetchone()[0]

# Step 4: Replace return
result = paginate_results(
    results=events,
    args=args,
    total_count=total_count,
    operation="timeline_query",
    drill_down_hint="Use /timeline-visualize for graphical timeline representation"
)
return [result.as_optimized_content(schema_name="episodic")]
```

### Handlers 6-14: Similar Transformations

**Remaining episodic handlers**:
- _handle_trace_consolidation → paginate consolidation trace steps
- _handle_recall_episodic_events → paginate event list
- _handle_temporal_chain_events → paginate chain links
- _handle_timeline_retrieve → paginate timeline segments
- _handle_timeline_visualize → paginate visualization data points
- _handle_consolidate_episodic_session → return summary (no pagination needed)
- _handle_surprise_detect → paginate surprising events
- _handle_temporal_consolidate → return consolidation summary (no pagination needed)

**Note**: _handle_record_event returns single event, no pagination needed.

---

## File 2: handlers_prospective.py (7 Remaining Handlers)

### Handler 1: _handle_list_tasks ✅ COMPLETE

### Handler 2: _handle_create_task

**Status**: Returns single task, **no pagination needed**.

### Handler 3: _handle_update_task_status

**Status**: Returns single task update result, **no pagination needed**.

### Handler 4: _handle_verify_task

**Status**: Returns verification result, **no pagination needed** unless verification includes related tasks list.

### Handler 5: _handle_create_task_with_milestones

**Status**: Returns created task with milestones list.

**Changes**: If milestones list is large:
```python
# Paginate milestones within response
milestone_limit = min(args.get("milestone_limit", 10), 50)
milestone_offset = args.get("milestone_offset", 0)

paginated_milestones = milestones[milestone_offset:milestone_offset + milestone_limit]

result = paginate_results(
    results=paginated_milestones,
    args={"limit": milestone_limit, "offset": milestone_offset},
    total_count=len(milestones),
    operation="create_task_with_milestones",
    drill_down_hint="Use /get-task-details for complete milestone history"
)
```

### Handler 6: _handle_get_active_goals

**Current line ~580**

**Changes**:
```python
# Step 1: Add pagination
limit = min(args.get("limit", 10), 100)
offset = args.get("offset", 0)

# Step 2: Modify store call
active_goals = self.prospective_store.list_goals(
    project.id,
    status="active",
    limit=limit,
    offset=offset
)

# Step 3: Get count
total_count = self.prospective_store.count_goals(
    project.id,
    status="active"
)

# Step 4: Replace return
formatted_goals = [...]  # Format goals
result = paginate_results(
    results=formatted_goals,
    args=args,
    total_count=total_count,
    operation="get_active_goals",
    drill_down_hint="Use /get-goal-details with goal_id for complete goal hierarchy and progress"
)
return [result.as_optimized_content(schema_name="prospective")]
```

### Handlers 7-8: _handle_calculate_task_cost, _handle_predict_task_duration

**Status**: Both return single estimates, **no pagination needed**.

---

## File 3: handlers_procedural.py (7 Handlers)

### Handler 1: _handle_find_procedures

**Current line ~150**

**Changes**:
```python
# Step 1: Add pagination
limit = min(args.get("limit", 10), 100)
offset = args.get("offset", 0)

# Step 2: Modify store call
procedures = self.procedural_store.find_procedures(
    query=query,
    tags=tags,
    limit=limit,
    offset=offset
)

# Step 3: Get count
total_count = self.procedural_store.count_procedures(
    query=query,
    tags=tags
)

# Step 4: Replace return
result = paginate_results(
    results=procedures,
    args=args,
    total_count=total_count,
    operation="find_procedures",
    drill_down_hint="Use /get-procedure with procedure_id for full implementation code and effectiveness metrics"
)
return [result.as_optimized_content(schema_name="procedural")]
```

### Handler 2: _handle_get_procedure_effectiveness

**Status**: Returns single procedure metrics, **no pagination needed**.

### Handler 3: _handle_suggest_procedure_improvements

**Status**: Returns improvement suggestions (could be paginated if list is large).

**Changes**:
```python
# If suggestions list is large, paginate
limit = min(args.get("limit", 5), 20)
offset = args.get("offset", 0)

paginated_suggestions = suggestions[offset:offset + limit]

result = paginate_results(
    results=paginated_suggestions,
    args=args,
    total_count=len(suggestions),
    operation="suggest_procedure_improvements",
    drill_down_hint="Use /get-procedure-effectiveness for detailed metrics before applying suggestions"
)
return [result.as_optimized_content(schema_name="procedural")]
```

### Handler 4: _handle_list_procedure_versions

**Current line ~340**

**Changes**:
```python
# Step 1: Add pagination
limit = min(args.get("limit", 10), 100)
offset = args.get("offset", 0)

# Step 2: Query with pagination
versions = self.procedural_store.list_versions(
    procedure_id=procedure_id,
    limit=limit,
    offset=offset
)

# Step 3: Get count
total_count = self.procedural_store.count_versions(procedure_id)

# Step 4: Replace return
result = paginate_results(
    results=versions,
    args=args,
    total_count=total_count,
    operation="list_procedure_versions",
    drill_down_hint="Use /get-procedure-version with version_id for complete version diff and metadata"
)
return [result.as_optimized_content(schema_name="procedural")]
```

### Handlers 5-7: Similar patterns

**Remaining handlers**:
- _handle_create_procedure → single creation, no pagination
- _handle_record_execution → single execution record, no pagination
- _handle_record_execution_feedback → single feedback, no pagination

---

## File 4: handlers_metacognition.py (10 Handlers)

### Handler 1: _handle_smart_retrieve

**Current line ~180**

**Changes**:
```python
# Step 1: Add pagination
limit = min(args.get("limit", 10), 100)
offset = args.get("offset", 0)

# Step 2: Retrieve with pagination
results = self.rag_manager.retrieve(
    query=query,
    strategy=strategy,
    limit=limit,
    offset=offset
)

# Step 3: Get total
total_count = self.rag_manager.count_results(query, strategy)

# Step 4: Replace return
result = paginate_results(
    results=results,
    args=args,
    total_count=total_count,
    operation="smart_retrieve",
    drill_down_hint="Use /recall-memory with memory_id for complete memory context and relationships"
)
return [result.as_optimized_content(schema_name="semantic")]
```

### Handler 2: _handle_get_working_memory

**Current line ~240**

**Changes**:
```python
# Step 1: Add pagination
limit = min(args.get("limit", 7), 20)  # 7±2 cognitive load limit
offset = args.get("offset", 0)

# Step 2: Get working memory items
items = self.episodic_buffer.get_items(project.id)
total_count = len(items)

# Apply pagination in-memory
paginated_items = items[offset:offset + limit]

# Step 3 & 4: Format and return
formatted_items = [...]  # Format items
result = paginate_results(
    results=formatted_items,
    args=args,
    total_count=total_count,
    operation="get_working_memory",
    drill_down_hint="Current 7±2 items in focus. Use /consolidate-working-memory to free capacity."
)
return [result.as_optimized_content(schema_name="working_memory")]
```

### Handler 3: _handle_get_expertise

**Current line ~310**

**Changes**:
```python
# Step 1: Add pagination
limit = min(args.get("limit", 10), 100)
offset = args.get("offset", 0)

# Step 2: Get expertise data
expertise_map = self.meta_memory_store.get_expertise(
    project_id=project.id,
    limit=limit + offset  # Get enough for offset
)

# Convert to list and paginate
expertise_list = list(expertise_map.items())
total_count = len(expertise_list)
paginated = expertise_list[offset:offset + limit]

# Step 3 & 4: Format and return
formatted = [{"domain": d, "metrics": m} for d, m in paginated]
result = paginate_results(
    results=formatted,
    args=args,
    total_count=total_count,
    operation="get_expertise",
    drill_down_hint="Use /detect-knowledge-gaps to identify domains needing development"
)
return [result.as_optimized_content(schema_name="metacognition")]
```

### Handlers 4-10: Similar patterns

**Remaining handlers**:
- _handle_analyze_coverage → paginate coverage gaps
- _handle_update_working_memory → single update, no pagination
- _handle_get_associations → paginate association list
- _handle_get_learning_rates → paginate domain learning rates
- _handle_detect_knowledge_gaps → paginate gap list
- _handle_check_cognitive_load → single load metric, no pagination

---

## File 5: handlers_graph.py (6 Handlers)

### Handler 1: _handle_search_graph

**Current line ~180**

**Changes**:
```python
# Step 1: Add pagination
limit = min(args.get("limit", 10), 100)
offset = args.get("offset", 0)

# Step 2: Search with pagination
results = self.graph_store.search(
    query=query,
    entity_type=entity_type,
    limit=limit,
    offset=offset
)

# Step 3: Get count
total_count = self.graph_store.count_search_results(query, entity_type)

# Step 4: Replace return
result = paginate_results(
    results=results,
    args=args,
    total_count=total_count,
    operation="search_graph",
    drill_down_hint="Use /search-graph-with-depth for traversal with relationship context"
)
return [result.as_optimized_content(schema_name="graph")]
```

### Handler 2: _handle_search_graph_with_depth

**Current line ~240**

**Changes**:
```python
# Step 1: Add pagination
limit = min(args.get("limit", 20), 100)
offset = args.get("offset", 0)
depth = args.get("depth", 2)

# Step 2: BFS/DFS with pagination
# Note: Graph traversal pagination is complex - paginate results, not traversal
all_results = self.graph_store.traverse(
    start_entity=start_entity,
    depth=depth
)

total_count = len(all_results)
paginated_results = all_results[offset:offset + limit]

# Step 4: Replace return
result = paginate_results(
    results=paginated_results,
    args=args,
    total_count=total_count,
    operation="search_graph_with_depth",
    drill_down_hint="Use /get-entity with entity_id for complete neighborhood and relations"
)
return [result.as_optimized_content(schema_name="graph")]
```

### Handler 3: _handle_get_graph_metrics

**Current line ~310**

**Changes**:
```python
# If metrics list is large, paginate
metrics_list = [...]  # List of metric objects

limit = min(args.get("limit", 10), 100)
offset = args.get("offset", 0)

total_count = len(metrics_list)
paginated = metrics_list[offset:offset + limit]

result = paginate_results(
    results=paginated,
    args=args,
    total_count=total_count,
    operation="get_graph_metrics",
    drill_down_hint="Use /analyze-graph-metrics for detailed analysis and recommendations"
)
return [result.as_optimized_content(schema_name="graph")]
```

### Handlers 4-6: _handle_create_entity, _handle_create_relation, _handle_add_observation

**Status**: All return single created items, **no pagination needed**.

---

## File 6: handlers_consolidation.py (2 Handlers)

### Handler 1: _handle_consolidate_working_memory

**Current line ~179**

**Changes**:
```python
# If consolidating multiple items, paginate results list
if item_id is None:
    # ... existing logic to get all_items ...

    # Paginate before consolidation
    limit = min(args.get("limit", 3), 10)
    offset = args.get("offset", 0)

    total_count = len(all_items)
    items_to_consolidate = all_items[offset:offset + limit]

    results = []
    for item in items_to_consolidate:
        result = self.consolidation_router.route_item(project.id, item.id, use_ml=auto_route)
        results.append(result)

    formatted = [...]  # Format results
    result = paginate_results(
        results=formatted,
        args=args,
        total_count=total_count,
        operation="consolidate_working_memory",
        drill_down_hint="Use /get-working-memory to see remaining unconsolidated items"
    )
    return [result.as_optimized_content(schema_name="consolidation")]
```

### Handler 2: _handle_cluster_consolidation_events

**Current line ~268**

**Changes**:
```python
# Step 1: Add pagination
limit = min(args.get("limit", 10), 100)
offset = args.get("offset", 0)

# Step 2: Cluster events
clusters = self.llm_consolidation_clusterer.cluster_events(events, limit=limit+offset)

# Paginate clusters
total_count = len(clusters)
paginated_clusters = clusters[offset:offset + limit]

# Step 4: Replace return
result = paginate_results(
    results=paginated_clusters,
    args=args,
    total_count=total_count,
    operation="cluster_consolidation_events",
    drill_down_hint="Use /run-consolidation to apply these patterns to semantic memory"
)
return [result.as_optimized_content(schema_name="consolidation")]
```

---

## File 7: handlers_planning.py (31 Handlers)

**Note**: This file is massive (5,982 lines). Most planning handlers return analysis results or single plans.

### Handlers Needing Pagination

**List/Search Operations** (11 handlers):
- _handle_list_rules → paginate rules list
- _handle_get_suggestions → paginate suggestion list
- _handle_score_semantic_memories → paginate scored memories
- _handle_generate_alternative_plans → paginate plan alternatives
- _handle_suggest_cost_optimizations → paginate optimization suggestions
- _handle_detect_budget_anomalies → paginate anomaly list
- _handle_list_external_sources → paginate source list
- _handle_track_sensitive_data → paginate sensitive data instances
- _handle_detect_bottlenecks → paginate bottleneck list
- _handle_batch_create_entities → return batch result summary (paginate if creating many)
- _handle_synchronize_layers → return sync status (paginate if many layers)

**Analysis Operations** (20 handlers):
Most return analysis summaries or single results. Apply pagination only if analysis includes large datasets:
- _handle_decompose_hierarchically → paginate decomposition levels if deep
- _handle_validate_plan → single validation result
- _handle_verify_plan → single verification result
- _handle_analyze_estimation_accuracy → single accuracy report
- _handle_optimize_plan → single optimized plan
- _handle_analyze_critical_path → paginate path segments if long
- _handle_detect_resource_conflicts → paginate conflict list
- ... (remaining analysis handlers follow similar pattern)

### Example: _handle_list_rules

**Current line ~1740**

**Changes**:
```python
# Step 1: Add pagination
limit = min(args.get("limit", 10), 100)
offset = args.get("offset", 0)

# Step 2: Get rules with pagination
rules = self.rule_validator.list_rules(
    category=category,
    limit=limit,
    offset=offset
)

# Step 3: Get count
total_count = self.rule_validator.count_rules(category=category)

# Step 4: Replace return
formatted_rules = [...]  # Format rules
result = paginate_results(
    results=formatted_rules,
    args=args,
    total_count=total_count,
    operation="list_rules",
    drill_down_hint="Use /validate-task-against-rules to check task compliance with specific rule"
)
return [result.as_optimized_content(schema_name="planning")]
```

---

## Implementation Checklist

### Pre-Implementation
- [x] Review structured_result.py pagination utilities
- [x] Understand paginate_results() API
- [x] Identify all 78 handlers needing pagination
- [ ] Prioritize handlers by usage frequency (TIER 1-4)

### Per-Handler Implementation
For each handler:
- [ ] Read current implementation
- [ ] Identify data source (SQL, store method, in-memory)
- [ ] Add pagination parameters (limit, offset)
- [ ] Modify query/fetch to support pagination
- [ ] Add total count query/calculation
- [ ] Format results as list of dicts
- [ ] Replace return with paginate_results() call
- [ ] Choose appropriate drill_down_hint
- [ ] Choose appropriate schema_name

### Post-Implementation
- [ ] Run syntax validation: `python -m py_compile <file>`
- [ ] Run unit tests: `pytest tests/unit/ -v`
- [ ] Spot-check 5-10 handlers manually
- [ ] Update API documentation

---

## Common Patterns & Solutions

### Pattern 1: SQL Query with Filters

**Problem**: Need to add LIMIT/OFFSET and COUNT query.

**Solution**:
```python
# Build WHERE clauses once
sql_parts = ["SELECT * FROM table WHERE 1=1"]
params = []
# ... add filters ...

# COUNT query (reuse WHERE clauses)
count_sql_parts = ["SELECT COUNT(*) FROM table WHERE 1=1"]
count_sql_parts.extend(sql_parts[1:])  # Skip SELECT *, include WHERE
count_sql = " ".join(count_sql_parts)
cursor.execute(count_sql, params)
total_count = cursor.fetchone()[0]

# Main query (add ORDER + LIMIT)
sql_parts.append("ORDER BY timestamp DESC")
sql_parts.append(f"LIMIT {limit} OFFSET {offset}")
sql = " ".join(sql_parts)
cursor.execute(sql, params)
rows = cursor.fetchall()
```

### Pattern 2: Store Method Without limit/offset Support

**Problem**: Store method doesn't have limit/offset parameters yet.

**Solution Option A** (Quick Fix - In-Memory Pagination):
```python
all_items = store.list_items(project_id)
total_count = len(all_items)
paginated = all_items[offset:offset + limit]

result = paginate_results(
    results=paginated,
    args=args,
    total_count=total_count,
    ...
)
```

**Solution Option B** (Proper Fix - Update Store):
```python
# In store.py - add limit/offset to method signature
def list_items(self, project_id, limit=100, offset=0):
    sql = "SELECT * FROM items WHERE project_id = ? LIMIT ? OFFSET ?"
    return cursor.execute(sql, (project_id, limit, offset)).fetchall()

def count_items(self, project_id):
    sql = "SELECT COUNT(*) FROM items WHERE project_id = ?"
    return cursor.execute(sql, (project_id,)).fetchone()[0]
```

### Pattern 3: Analysis Results (Non-List)

**Problem**: Handler returns analysis summary, not a list.

**Solution**: **No pagination needed**. Only paginate if analysis includes a large list of items.

### Pattern 4: Graph Traversal

**Problem**: BFS/DFS traversal with depth - can't paginate mid-traversal.

**Solution**: Complete traversal, then paginate results:
```python
all_results = traverse_graph(start, depth)  # Full traversal
total_count = len(all_results)
paginated = all_results[offset:offset + limit]

result = paginate_results(results=paginated, ...)
```

---

## Testing Strategy

### 1. Syntax Validation
```bash
for file in src/athena/mcp/handlers_*.py; do
    python -m py_compile "$file" && echo "✓ $file" || echo "✗ $file"
done
```

### 2. Unit Tests
```bash
# Test pagination utilities
pytest tests/unit/test_structured_result.py -v

# Test specific handler
pytest tests/integration/test_mcp_handlers.py::test_recall_events_pagination -v
```

### 3. Manual Spot-Checks
```python
# Test with MCP client
result = client.call_tool("recall_events", {
    "query": "test",
    "limit": 5,
    "offset": 0
})
assert "pagination" in result
assert result["pagination"]["returned"] <= 5
assert result["pagination"]["total"] >= result["pagination"]["returned"]
```

---

## Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Handlers with pagination | 78/78 | 1/78 |
| Files with imports | 7/7 | 7/7 ✅ |
| Syntax errors | 0 | 0 ✅ |
| Unit tests passing | 100% | Pending |
| Average response size | <5KB | TBD |
| Token efficiency | 98%+ | TBD |

---

## Timeline Estimate

| Phase | Handlers | Time |
|-------|----------|------|
| TIER 1 (Critical) | 9 | 1.5 hours |
| TIER 2 (High) | 18 | 2.4 hours |
| TIER 3 (Medium) | 25 | 2.5 hours |
| TIER 4 (Low) | 25 | 2.1 hours |
| Testing | - | 1.5 hours |
| **TOTAL** | **77** | **10 hours** |

---

## Notes & Considerations

1. **Store Method Updates**: Some store methods need limit/offset parameters added. Use in-memory pagination as temporary workaround.

2. **Drill-Down Hints**: Each handler should have a specific, helpful hint. Avoid generic "use drill-down" messages.

3. **Error Handling**: All handlers should wrap pagination in try/except and return StructuredResult.error() on failure.

4. **Schema Names**: Use appropriate schema name for as_optimized_content():
   - "episodic" for event handlers
   - "semantic" for memory/retrieval handlers
   - "procedural" for workflow handlers
   - "prospective" for task/goal handlers
   - "graph" for knowledge graph handlers
   - "metacognition" for meta-memory handlers
   - "consolidation" for consolidation handlers
   - "planning" for planning handlers

5. **Count Queries**: Always use COUNT(*) for efficiency, not len(list).

6. **Offset Validation**: `offset = max(args.get("offset", 0), 0)` prevents negative offsets.

---

**Next Action**: Begin TIER 1 implementation (9 critical handlers).
