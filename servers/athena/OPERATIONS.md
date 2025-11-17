# Athena Operations Registry

Complete mapping of TypeScript stubs to Python implementations. This is the **source of truth** for agent discovery and operation coverage.

## Discovery Pattern

Agents discover operations by:
1. Listing `./servers/athena/` directory
2. Reading TypeScript stub files (type signatures only)
3. Checking `@implementation` comments to find Python module
4. Importing directly from Python: `from athena.[layer].operations import [function]`

## Layer 1: Episodic Memory - Event Storage & Retrieval

| Operation | TypeScript Stub | Python Implementation | Status |
|-----------|---|---|---|
| Store event | `remember()` | `athena.episodic.operations:remember` | ✅ Stub exists |
| Retrieve events | `recall()` | `athena.episodic.operations:recall` | ✅ Stub exists |
| Retrieve recent | `recall_recent()` | `athena.episodic.operations:recall_recent` | ⚠️ No stub |
| Get by session | `get_by_session()` | `athena.episodic.operations:get_by_session` | ⚠️ No stub |
| Get by tags | `get_by_tags()` | `athena.episodic.operations:get_by_tags` | ⚠️ No stub |
| Get by time range | `get_by_time_range()` | `athena.episodic.operations:get_by_time_range` | ⚠️ No stub |
| Get statistics | `episodic_get_statistics()` | `athena.episodic.operations:get_statistics` | ⚠️ No stub |

**Module**: `src/athena/episodic/operations.py` (1,200+ lines)

---

## Layer 2: Semantic Memory - Facts & Knowledge

| Operation | TypeScript Stub | Python Implementation | Status |
|-----------|---|---|---|
| Store fact | `store()` | `athena.memory.operations:store` | ⚠️ No stub |
| Search facts | `search()` | `athena.memory.operations:search` | ⚠️ No stub |

**Module**: `src/athena/memory/operations.py`

---

## Layer 3: Procedural Memory - Reusable Workflows

| Operation | TypeScript Stub | Python Implementation | Status |
|-----------|---|---|---|
| Extract procedure | `extract_procedure()` | `athena.procedural.operations:extract_procedure` | ⚠️ No stub |
| List procedures | `list_procedures()` | `athena.procedural.operations:list_procedures` | ⚠️ No stub |
| Get procedure | `get_procedure()` | `athena.procedural.operations:get_procedure` | ⚠️ No stub |
| Search procedures | `search_procedures()` | `athena.procedural.operations:search_procedures` | ⚠️ No stub |
| Get by tags | `get_procedures_by_tags()` | `athena.procedural.operations:get_procedures_by_tags` | ⚠️ No stub |
| Update success | `update_procedure_success()` | `athena.procedural.operations:update_procedure_success` | ⚠️ No stub |
| Get statistics | `procedural_get_statistics()` | `athena.procedural.operations:get_statistics` | ⚠️ No stub |

**Module**: `src/athena/procedural/operations.py`

---

## Layer 4: Prospective Memory - Tasks & Goals

| Operation | TypeScript Stub | Python Implementation | Status |
|-----------|---|---|---|
| Create task | `create_task()` | `athena.prospective.operations:create_task` | ⚠️ No stub |
| List tasks | `list_tasks()` | `athena.prospective.operations:list_tasks` | ⚠️ No stub |
| Get task | `get_task()` | `athena.prospective.operations:get_task` | ⚠️ No stub |
| Update task status | `update_task_status()` | `athena.prospective.operations:update_task_status` | ⚠️ No stub |
| Get active tasks | `get_active_tasks()` | `athena.prospective.operations:get_active_tasks` | ⚠️ No stub |
| Get overdue tasks | `get_overdue_tasks()` | `athena.prospective.operations:get_overdue_tasks` | ⚠️ No stub |
| Get statistics | `prospective_get_statistics()` | `athena.prospective.operations:get_statistics` | ⚠️ No stub |

**Module**: `src/athena/prospective/operations.py`

---

## Layer 5: Knowledge Graph - Entities & Relations

| Operation | TypeScript Stub | Python Implementation | Status |
|-----------|---|---|---|
| Add entity | `add_entity()` | `athena.graph.operations:add_entity` | ⚠️ No stub |
| Add relationship | `add_relationship()` | `athena.graph.operations:add_relationship` | ⚠️ No stub |
| Find entity | `find_entity()` | `athena.graph.operations:find_entity` | ⚠️ No stub |
| Search entities | `search_entities()` | `athena.graph.operations:search_entities` | ⚠️ No stub |
| Find related | `find_related()` | `athena.graph.operations:find_related` | ⚠️ No stub |
| Get communities | `get_communities()` | `athena.graph.operations:get_communities` | ⚠️ No stub |
| Update importance | `update_entity_importance()` | `athena.graph.operations:update_entity_importance` | ⚠️ No stub |
| Get statistics | `graph_get_statistics()` | `athena.graph.operations:get_statistics` | ⚠️ No stub |

**Module**: `src/athena/graph/operations.py`

---

## Layer 6: Meta-Memory - Quality & Expertise

| Operation | TypeScript Stub | Python Implementation | Status |
|-----------|---|---|---|
| Rate memory | `rate_memory()` | `athena.meta.operations:rate_memory` | ⚠️ No stub |
| Get expertise | `get_expertise()` | `athena.meta.operations:get_expertise` | ⚠️ No stub |
| Get memory quality | `get_memory_quality()` | `athena.meta.operations:get_memory_quality` | ⚠️ No stub |
| Get cognitive load | `get_cognitive_load()` | `athena.meta.operations:get_cognitive_load` | ⚠️ No stub |
| Update cognitive load | `update_cognitive_load()` | `athena.meta.operations:update_cognitive_load` | ⚠️ No stub |
| Get statistics | `meta_get_statistics()` | `athena.meta.operations:get_statistics` | ⚠️ No stub |

**Module**: `src/athena/meta/operations.py`

---

## Layer 7: Consolidation - Pattern Extraction

| Operation | TypeScript Stub | Python Implementation | Status |
|-----------|---|---|---|
| Consolidate | `consolidate()` | `athena.consolidation.operations:consolidate` | ⚠️ No stub |
| Extract patterns | `extract_patterns()` | `athena.consolidation.operations:extract_patterns` | ⚠️ No stub |
| Extract procedures | `extract_procedures()` | `athena.consolidation.operations:extract_procedures` | ⚠️ No stub |
| Get history | `get_consolidation_history()` | `athena.consolidation.operations:get_consolidation_history` | ⚠️ No stub |
| Get metrics | `get_consolidation_metrics()` | `athena.consolidation.operations:get_consolidation_metrics` | ⚠️ No stub |
| Get statistics | `consolidation_get_statistics()` | `athena.consolidation.operations:get_statistics` | ⚠️ No stub |

**Module**: `src/athena/consolidation/operations.py`

---

## Layer 8: Planning - Task Decomposition & Strategy

| Operation | TypeScript Stub | Python Implementation | Status |
|-----------|---|---|---|
| Create plan | `create_plan()` | `athena.planning.operations:create_plan` | ⚠️ No stub |
| Validate plan | `validate_plan()` | `athena.planning.operations:validate_plan` | ⚠️ No stub |
| Get plan | `get_plan()` | `athena.planning.operations:get_plan` | ⚠️ No stub |
| List plans | `list_plans()` | `athena.planning.operations:list_plans` | ⚠️ No stub |
| Estimate effort | `estimate_effort()` | `athena.planning.operations:estimate_effort` | ✅ Partial (effort_prediction.ts) |
| Update status | `update_plan_status()` | `athena.planning.operations:update_plan_status` | ⚠️ No stub |
| Get statistics | `planning_get_statistics()` | `athena.planning.operations:get_statistics` | ⚠️ No stub |

**Module**: `src/athena/planning/operations.py`

---

## Server-Specific Tools (Not Layer Operations)

These are specialized tools that combine multiple operations:

| Operation | TypeScript Stub | Purpose | Status |
|-----------|---|---|---|
| Planning recommendations | `planning_recommendations.ts` | Get strategy recommendations | ✅ Exists |
| Deviation monitoring | `deviation_monitor.ts` | Detect task deviations | ✅ Exists |
| Execution feedback | `execution_feedback.ts` | Record completion feedback | ✅ Exists |
| Trigger management | `trigger_management.ts` | Manage task triggers | ✅ Exists |
| Effort prediction | `effort_prediction.ts` | Predict task effort | ✅ Exists |

---

## Coverage Summary

**Total Operations**: 56 public functions across 8 layers

**With TypeScript Stubs**: 5 (operations or specialized tools)
- remember() ✅
- recall() ✅
- estimate_effort() ✅ (via effort_prediction.ts)
- (5 specialized server tools) ✅

**Missing Stubs**: 51 operations need type signatures
- Episodic: 6 missing
- Memory: 2 missing
- Procedural: 7 missing
- Prospective: 7 missing
- Graph: 8 missing
- Meta: 6 missing
- Consolidation: 6 missing
- Planning: 6 missing

---

## Next Steps

### Phase 1: Fix Existing Stubs
1. Convert all 5 existing stubs to **type signatures only** (no mock implementations)
2. Add `@implementation` comments linking to Python modules
3. Add `@example` sections showing how to use them

### Phase 2: Create Missing Stubs
1. Generate TypeScript stub files for all 51 missing operations
2. Organize by layer (one file per layer or one per operation - TBD)
3. Add full documentation

### Phase 3: Update Index
Update `index.ts` to export all 56 operations with discovery metadata

---

## Usage Example

Once complete, agent discovery will work like this:

```typescript
// 1. Agent lists available operations
ls ./servers/athena/

// 2. Agent reads a stub file to understand signature
cat ./servers/athena/episodic.ts

// 3. Agent imports and calls directly
import { remember, recall } from 'athena.episodic.operations';

const event_id = await remember("User asked about timeline", tags=["meeting"]);
const results = await recall("timeline", limit=5);

// Paradigm: 99% token efficient, 0% protocol overhead
```

---

**Last Updated**: 2025-11-17
**Status**: Phase 1 in progress
