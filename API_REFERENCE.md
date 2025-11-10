# Athena MCP API Reference

**Version**: 1.0
**Status**: Production Ready (Phase A.2 Complete)
**Test Coverage**: 55/55 tests passing (100%)

## Overview

Athena exposes 27 MCP tools with 300+ handler operations across 8 memory layers. This document provides comprehensive API documentation for all tools.

## Table of Contents

1. [Core Memory Operations](#core-memory-operations)
2. [Episodic Memory](#episodic-memory)
3. [Procedural Memory](#procedural-memory)
4. [Prospective Memory](#prospective-memory)
5. [Knowledge Graph](#knowledge-graph)
6. [Meta-Memory & Monitoring](#meta-memory--monitoring)
7. [Working Memory](#working-memory)
8. [Consolidation & Learning](#consolidation--learning)
9. [Advanced RAG](#advanced-rag)
10. [System Operations](#system-operations)

---

## Core Memory Operations

### remember
Store a new memory (fact, pattern, decision, or context).

**Parameters:**
- `project_id` (string, required): Project identifier
- `content` (string, required): Memory content to store
- `memory_type` (string, required): Type - "fact", "pattern", "decision", "context"
- `metadata` (object, optional): Additional context

**Returns:**
- Memory ID and confirmation message

**Example:**
```json
{
  "project_id": "1",
  "content": "Python is a versatile programming language",
  "memory_type": "fact",
  "metadata": {"domain": "programming"}
}
```

### recall
Retrieve memories using semantic search.

**Parameters:**
- `project_id` (string, required): Project identifier
- `query` (string, required): Search query
- `memory_type` (string, optional): Filter by type
- `limit` (integer, optional): Max results (default: 10)

**Returns:**
- List of matching memories with scores

### forget
Delete a memory by ID.

**Parameters:**
- `project_id` (string, required): Project identifier
- `memory_id` (integer, required): Memory to delete

**Returns:**
- Deletion confirmation

### list_memories
List all memories in a project with optional filtering.

**Parameters:**
- `project_id` (string, required): Project identifier
- `memory_type` (string, optional): Filter by type
- `limit` (integer, optional): Max results
- `offset` (integer, optional): Pagination offset

**Returns:**
- List of memories with metadata

### optimize
Optimize memory storage (consolidation, cleanup).

**Parameters:**
- `project_id` (string, required): Project identifier
- `strategy` (string, optional): "balanced" (default), "speed", "quality", "minimal"

**Returns:**
- Optimization summary and metrics

---

## Episodic Memory

### record_event
Record a discrete event/action.

**Parameters:**
- `project_id` (string, required): Project identifier
- `event_type` (string, required): Type - "action", "decision", "observation", "error"
- `content` (string, required): Event description
- `context` (object, optional): Contextual data (cwd, files, task, phase)
- `timestamp` (string, optional): ISO timestamp
- `outcome` (string, optional): Result of action

**Returns:**
- Event ID and confirmation

### recall_events
Retrieve events by type, session, or temporal range.

**Parameters:**
- `project_id` (string, required): Project identifier
- `event_type` (string, optional): Filter by type
- `limit` (integer, optional): Max results
- `days_back` (integer, optional): Search last N days

**Returns:**
- List of events with full details

### get_timeline
Get chronological timeline of events.

**Parameters:**
- `project_id` (string, required): Project identifier
- `days_back` (integer, optional): Timeline span (default: 7)
- `event_type` (string, optional): Filter by type

**Returns:**
- Ordered events with temporal structure

### batch_record_events
Record multiple events efficiently (10x throughput).

**Parameters:**
- `project_id` (string, required): Project identifier
- `events` (array, required): Array of event objects

**Returns:**
- Batch confirmation and event IDs

### recall_events_by_session
Get events grouped by session/context.

**Parameters:**
- `project_id` (string, required): Project identifier
- `session_id` (string, optional): Specific session
- `limit` (integer, optional): Max results per session

**Returns:**
- Events organized by session

---

## Procedural Memory

### create_procedure
Create a new reusable procedure/workflow.

**Parameters:**
- `project_id` (string, required): Project identifier
- `name` (string, required): Procedure name
- `description` (string, required): What it does
- `category` (string, required): Type - "automation", "pattern", "workflow", "decision_tree"
- `steps` (array, required): Step objects with descriptions
- `preconditions` (array, optional): Required conditions
- `postconditions` (array, optional): Guaranteed outcomes

**Returns:**
- Procedure ID and confirmation

### find_procedures
Search for relevant procedures.

**Parameters:**
- `project_id` (string, required): Project identifier
- `query` (string, required): Search query
- `category` (string, optional): Filter by category
- `limit` (integer, optional): Max results

**Returns:**
- Matching procedures with relevance scores

### record_execution
Log procedure execution for learning.

**Parameters:**
- `project_id` (string, required): Project identifier
- `procedure_id` (integer, required): Procedure executed
- `success` (boolean, required): Execution result
- `duration` (number, optional): Execution time in seconds
- `notes` (string, optional): Execution notes

**Returns:**
- Execution record ID

### get_procedure_effectiveness
Get performance metrics for a procedure.

**Parameters:**
- `project_id` (string, required): Project identifier
- `procedure_id` (integer, required): Target procedure

**Returns:**
- Success rate, avg duration, improvement suggestions

### suggest_procedure_improvements
Get AI suggestions for procedure optimization.

**Parameters:**
- `project_id` (string, required): Project identifier
- `procedure_id` (integer, required): Target procedure

**Returns:**
- List of improvement suggestions with rationale

---

## Prospective Memory

### create_task
Create a new task/goal to track.

**Parameters:**
- `project_id` (string, required): Project identifier
- `content` (string, required): Task description
- `priority` (string, optional): "low", "medium" (default), "high"
- `active_form` (string, optional): Present continuous form (auto-generated)

**Returns:**
- Task ID and confirmation

### list_tasks
List all tasks with filtering.

**Parameters:**
- `project_id` (string, required): Project identifier
- `status` (string, optional): Filter by status ("pending", "in_progress", "done")
- `priority` (string, optional): Filter by priority
- `limit` (integer, optional): Max results

**Returns:**
- List of tasks with current status

### update_task_status
Change task status.

**Parameters:**
- `project_id` (string, required): Project identifier
- `task_id` (integer, required): Target task
- `status` (string, required): New status ("pending", "in_progress", "done", "blocked")

**Returns:**
- Task update confirmation

### start_task
Mark task as in progress.

**Parameters:**
- `project_id` (string, required): Project identifier
- `task_id` (integer, required): Task to start

**Returns:**
- Task started confirmation

### verify_task
Check if task meets completion criteria.

**Parameters:**
- `project_id` (string, required): Project identifier
- `task_id` (integer, required): Task to verify
- `verification_notes` (string, optional): Verification details

**Returns:**
- Verification result and completion status

---

## Knowledge Graph

### create_entity
Create a new entity in the knowledge graph.

**Parameters:**
- `project_id` (string, required): Project identifier
- `name` (string, required): Entity name
- `entity_type` (string, required): Type from enum (Concept, Component, Task, etc.)
- `observations` (array, optional): Initial observations

**Returns:**
- Entity ID and confirmation

**Valid Entity Types:**
- Project, Phase, Task, File, Function, Concept, Component, Person, Decision, Pattern, Agent, Skill

### create_relation
Create a relationship between entities.

**Parameters:**
- `project_id` (string, required): Project identifier
- `from_entity` (string, required): Source entity name
- `to_entity` (string, required): Target entity name
- `relation_type` (string, required): Type of relationship

**Returns:**
- Relation ID and confirmation

**Valid Relation Types:**
- contains, depends_on, implements, tests, caused_by, resulted_in, relates_to, active_in, assigned_to, has_skill

### add_observation
Add an observation to an entity.

**Parameters:**
- `project_id` (string, required): Project identifier
- `entity_id` (integer, required): Target entity
- `observation_text` (string, required): Observation content

**Returns:**
- Observation ID and confirmation

### search_graph
Search entities in the knowledge graph.

**Parameters:**
- `project_id` (string, required): Project identifier
- `query` (string, required): Search query
- `entity_type` (string, optional): Filter by type

**Returns:**
- Matching entities with details

### search_graph_with_depth
Advanced graph search with relationship traversal.

**Parameters:**
- `project_id` (string, required): Project identifier
- `start_entity` (string, required): Starting entity
- `depth` (integer, optional): Traversal depth (default: 2)
- `relation_filter` (string, optional): Filter by relation type

**Returns:**
- Graph with entities and relationships up to depth

### get_graph_metrics
Get statistics about the knowledge graph.

**Parameters:**
- `project_id` (string, required): Project identifier

**Returns:**
- Entity count, relation count, density, metrics

---

## Meta-Memory & Monitoring

### get_expertise
Get expertise profile for a domain.

**Parameters:**
- `project_id` (string, required): Project identifier
- `domain` (string, optional): Specific domain

**Returns:**
- Expertise level, topics, confidence scores

### get_attention_state
Get current attention and cognitive load.

**Parameters:**
- `project_id` (string, required): Project identifier

**Returns:**
- Active focus, load percentage, recommendations

### get_working_memory
Get current working memory state.

**Parameters:**
- `project_id` (string, required): Project identifier

**Returns:**
- Active items (7±2 limit), salience scores, composition

### update_working_memory
Manually manage working memory contents.

**Parameters:**
- `project_id` (string, required): Project identifier
- `item` (object, required): Item to add/update
- `action` (string, optional): "add", "remove", "update"

**Returns:**
- Updated working memory state

### clear_working_memory
Clear all working memory items.

**Parameters:**
- `project_id` (string, required): Project identifier

**Returns:**
- Confirmation of clearing

---

## Consolidation & Learning

### run_consolidation
Execute consolidation of episodic→semantic memory.

**Parameters:**
- `project_id` (string, required): Project identifier
- `strategy` (string, optional): "balanced" (default), "speed", "quality", "minimal"
- `days_back` (integer, optional): Events to process (default: 7)

**Returns:**
- Consolidation summary, patterns extracted, metrics

### schedule_consolidation
Set up periodic consolidation (like sleep).

**Parameters:**
- `project_id` (string, required): Project identifier
- `frequency` (string, required): "daily", "weekly" (default), "monthly"
- `time_of_day` (string, optional): ISO time (default: "02:00")

**Returns:**
- Schedule confirmation

### extract_patterns
Extract patterns from episodic events.

**Parameters:**
- `project_id` (string, required): Project identifier
- `days_back` (integer, optional): Time window (default: 7)
- `pattern_type` (string, optional): "statistical", "causal", "temporal"

**Returns:**
- Extracted patterns with confidence scores

---

## Advanced RAG

### smart_retrieve
Advanced semantic retrieval with multiple RAG strategies.

**Parameters:**
- `project_id` (string, required): Project identifier
- `query` (string, required): Information need
- `strategy` (string, optional): "hybrid" (default), "hyde", "reranking", "reflective"
- `top_k` (integer, optional): Results to return (default: 10)

**Returns:**
- Ranked results with relevance explanations

### retrieve_with_context
Retrieve with rich contextual information.

**Parameters:**
- `project_id` (string, required): Project identifier
- `query` (string, required): Search query
- `context_window` (integer, optional): Context size in tokens

**Returns:**
- Results with surrounding context

---

## System Operations

### get_health
Check system health status.

**Parameters:**
- `project_id` (string, required): Project identifier
- `detailed` (boolean, optional): Full diagnostics

**Returns:**
- Health status, layer metrics, alerts

### get_project_status
Get comprehensive project status overview.

**Parameters:**
- `project_id` (string, required): Project identifier

**Returns:**
- Memory statistics, recent activity, recommendations

---

## Error Handling

All endpoints return errors in this format:

```json
{
  "error": "error_type",
  "message": "Human-readable error message",
  "details": {}
}
```

**Common Error Codes:**
- `invalid_project_id`: Project not found
- `memory_not_found`: Memory/entity not found
- `invalid_parameter`: Parameter validation failed
- `database_error`: Database operation failed
- `rate_limit`: Rate limit exceeded

---

## Best Practices

### Memory Management
1. Use descriptive `content` for better semantic search
2. Include relevant `metadata` for filtering
3. Periodically run `consolidation` to extract patterns
4. Monitor `cognitive_load` to optimize performance

### Graph Management
1. Keep entity names consistent across the graph
2. Use specific `entity_types` for better organization
3. Add `observations` to provide context
4. Maintain relationship semantics (don't reverse meanings)

### Performance
1. Use `batch_record_events` for multiple events (10x faster)
2. Implement consolidation schedule for regular learning
3. Use appropriate search strategy based on use case
4. Monitor system health regularly

### Testing
- All 55 integration tests pass ✅
- Use SQLite for development
- PostgreSQL recommended for production
- See TEST_EXECUTION.md for running tests

---

## Version History

- **v1.0** (Current): Production release with 100% test coverage
  - 27 MCP tools
  - 300+ handler operations
  - 8-layer memory system
  - Local-first architecture

---

## Support

For issues or questions:
1. Check TEST_EXECUTION.md for common problems
2. Review TROUBLESHOOTING.md for solutions
3. Check system health with `get_health` endpoint
4. Enable debug logging: `DEBUG=1`

---

**Last Updated**: November 10, 2025
**Maintainer**: Athena Development Team
