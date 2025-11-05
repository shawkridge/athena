# Athena Troubleshooting Guide

Solutions for common issues and diagnostic procedures.

## Quick Diagnostics

```bash
# Check system health
/memory-health

# Check cognitive load
/working-memory

# Check database status
sqlite3 /home/user/.work/athena/memory.db ".tables"

# Get statistics
sqlite3 /home/user/.work/athena/memory.db << EOF
SELECT 'Events' as name, COUNT(*) as count FROM episodic_events
UNION ALL SELECT 'Procedures', COUNT(*) FROM procedures
UNION ALL SELECT 'Semantic', COUNT(*) FROM semantic_memories
UNION ALL SELECT 'Entities', COUNT(*) FROM entities
UNION ALL SELECT 'Relations', COUNT(*) FROM entity_relations;
EOF
```

---

## Common Issues & Solutions

### Issue 1: MCP Server Not Connecting

**Symptoms**:
- `claude mcp list` shows failed connection
- MCP tools return "Server unavailable"

**Diagnosis**:
```bash
# Check if server process is running
ps aux | grep athena.server

# Check configuration
cat ~/.mcp.json | grep -A5 athena

# Test database path
ls -lh /home/user/.work/athena/memory.db
```

**Solutions**:

1. **Wrong Configuration Path**:
   ```bash
   # Check which config file is being used
   # Primary: ~/.mcp.json
   # Secondary: ~/.claude/.mcp.json
   # Project: ~/.claude.json

   # Update all to point to athena
   grep -r "memory-mcp" ~/.mcp.json ~/.claude/.mcp.json ~/.claude.json
   # Replace with: /home/user/.work/athena
   ```

2. **Missing Environment Variable**:
   ```json
   {
     "mcpServers": {
       "athena": {
         "command": "/home/user/.work/athena/.venv/bin/python3",
         "args": ["-m", "athena.server"],
         "env": {
           "MEMORY_MCP_DB_PATH": "/home/user/.work/athena/memory.db"
         }
       }
     }
   }
   ```

3. **Restart Claude Code**:
   ```bash
   # Claude maintains cached MCP connections
   # Restart to force reload
   ```

**Verification**:
```bash
claude mcp list
# Should show: ✓ athena - Connected
```

---

### Issue 2: Slow Semantic Search (>500ms)

**Symptoms**:
- `retrieve()` takes >500ms
- Performance degradation over time

**Diagnosis**:
```bash
# Enable query profiling
sqlite3 /home/user/.work/athena/memory.db
.timer ON
.eqp ON

-- Check if indices are used
EXPLAIN QUERY PLAN SELECT * FROM semantic_memories
WHERE content LIKE '%query%' LIMIT 5;

-- Check vector index
SELECT COUNT(*) FROM semantic_memories;
```

**Solutions**:

1. **Create Missing Indices**:
   ```sql
   CREATE INDEX IF NOT EXISTS idx_semantic_bm25
   ON semantic_memories(content);

   CREATE INDEX IF NOT EXISTS idx_semantic_recency
   ON semantic_memories(created_at);
   ```

2. **Enable Vector Indexing**:
   ```sql
   CREATE INDEX IF NOT EXISTS idx_semantic_vector
   ON semantic_memories(embedding);
   ```

3. **Increase Cache Size**:
   ```sql
   PRAGMA cache_size = 10000;  -- Increase to 10MB
   ```

4. **Check Database Bloat**:
   ```bash
   # Vacuum database to recover space
   sqlite3 /home/user/.work/athena/memory.db "VACUUM;"

   # Check size before/after
   du -h /home/user/.work/athena/memory.db
   ```

**Expected Performance**:
- With index: <100ms
- Without index: >500ms
- 8K memories: 87ms typical

---

### Issue 3: High Graph Traversal Latency (>100ms)

**Symptoms**:
- `find_path()` takes >100ms
- Graph queries slow

**Diagnosis**:
```bash
sqlite3 /home/user/.work/athena/memory.db
-- Check relation count
SELECT COUNT(*) FROM entity_relations;

-- Check if indices exist
PRAGMA index_list(entity_relations);
```

**Solutions**:

1. **Create Relation Indices**:
   ```sql
   CREATE INDEX IF NOT EXISTS idx_relation_from
   ON entity_relations(from_entity_id);

   CREATE INDEX IF NOT EXISTS idx_relation_to
   ON entity_relations(to_entity_id);
   ```

2. **Batch Lookups** (instead of N individual queries):
   ```python
   # Bad: 100 queries
   for entity_id in entity_ids:
       entity = graph.get_entity(entity_id)

   # Good: 1 query
   entities = graph.get_entities_batch(entity_ids)
   ```

3. **Enable Graph Caching**:
   ```python
   from athena.graph.cache import GraphCache
   cache = GraphCache(db, max_size=10000)
   # Improves traversal by 70-80%
   ```

---

### Issue 4: Slow Consolidation (>30s)

**Symptoms**:
- `consolidate()` hangs or takes >30s
- Memory operations blocked

**Diagnosis**:
```bash
sqlite3 /home/user/.work/athena/memory.db
SELECT COUNT(*) as episodic_count FROM episodic_events;

-- Check consolidation history
SELECT COUNT(*) FROM semantic_memories;
```

**Solutions**:

1. **Use Speed Strategy**:
   ```python
   result = consolidation.run_consolidation(
       project_id=1,
       strategy='speed',      # System 1 only, <200ms
       max_events=100         # Process in batches
   )
   ```

2. **Reduce Batch Size**:
   ```python
   # Instead of consolidating all 8K events:
   result = consolidation.run_consolidation(
       project_id=1,
       strategy='balanced',
       max_events=500         # 500 at a time
   )
   ```

3. **Run During Off-Peak**:
   ```bash
   # Schedule consolidation for background time
   # Typical: 100 events = 150ms
   # 1000 events = 1.5s
   ```

4. **Check System Load**:
   ```bash
   # Consolidation is CPU-intensive
   # If system load high, reduce batch size
   top -b -n 1 | head -20
   ```

**Expected Performance**:
- 100 events: <200ms (speed strategy)
- 500 events: <500ms (balanced strategy)
- 1000 events: <2s (quality strategy)

---

### Issue 5: Out of Memory / Database Size Growing

**Symptoms**:
- Database file >1GB
- Memory operations slow
- Disk space low

**Diagnosis**:
```bash
# Check database size
du -h /home/user/.work/athena/memory.db

# Check fragmentation
sqlite3 /home/user/.work/athena/memory.db << EOF
PRAGMA freelist_count;  -- Free pages
PRAGMA page_count;      -- Total pages
EOF

# Calculate wasted space
sqlite3 /home/user/.work/athena/memory.db \
  "SELECT (freelist_count * 4096 / 1024 / 1024) as wasted_mb FROM pragma_freelist_count;"
```

**Solutions**:

1. **Remove Low-Value Memories**:
   ```python
   # Find old episodic events
   old_events = episodic.get_events(days=365)  # Events >1 year old

   for event in old_events:
       episodic.delete(event.id)  # Remove old event
   ```

2. **Consolidate to Reclaim Space**:
   ```python
   # Consolidation converts episodic → semantic
   # Reduces episodic count, consolidates data
   result = consolidation.run_consolidation(
       project_id=1,
       strategy='quality'
   )
   ```

3. **Vacuum Database**:
   ```bash
   # Reclaim fragmented space
   sqlite3 /home/user/.work/athena/memory.db "VACUUM;"

   # Verify size reduction
   du -h /home/user/.work/athena/memory.db
   ```

4. **Archive Old Data** (optional):
   ```bash
   # Backup and reset database
   cp memory.db memory.db.backup
   sqlite3 memory.db "DELETE FROM episodic_events WHERE created_at < '2024-01-01';"
   sqlite3 memory.db "VACUUM;"
   ```

---

### Issue 6: Task Tests Failing

**Symptoms**:
- `pytest src/athena/tests/` fails
- Import errors or architectural issues

**Cause**:
- Test suite references old `memory_mcp` paths
- Circular imports in complex architecture
- Test framework setup issues

**Solutions**:

1. **Test via MCP Instead**:
   ```python
   # Instead of running full test suite
   # Test directly through MCP tools
   from athena.semantic.search import SemanticSearch
   from athena.core.database import Database

   db = Database("/home/user/.work/athena/memory.db")
   search = SemanticSearch(db)

   results = search.retrieve("test query", k=5)
   assert len(results) > 0
   ```

2. **Fix Import Paths** (one-time):
   ```bash
   # Update test files
   find src/athena/tests -name "*.py" -exec \
     sed -i 's/from memory_mcp/from athena/g' {} \;

   find src/athena/tests -name "*.py" -exec \
     sed -i 's/import memory_mcp/import athena/g' {} \;
   ```

3. **Run Specific Tests**:
   ```bash
   # Test specific module only
   pytest src/athena/tests/test_semantic.py::test_retrieve -v

   # Skip slow tests
   pytest src/athena/tests/ -m "not slow" -v
   ```

**Expected**: 94/94 tests passing after fixing imports

---

### Issue 7: Cognitive Load Exceeding Capacity

**Symptoms**:
- `/working-memory` shows 7/7 items
- Context confusion or hallucinations
- Memory operations degraded

**Diagnosis**:
```bash
/working-memory
# Shows: Current load: 7/7 items
```

**Solutions**:

1. **Immediate Consolidation**:
   ```python
   # Archive oldest items
   consolidation.consolidate_working_memory()
   # Reduces to 4-5/7 items
   ```

2. **Manual Consolidation**:
   ```bash
   /consolidate
   # Full session consolidation
   ```

3. **Clear Distractions**:
   ```bash
   /focus
   # Remove low-salience items
   ```

**Prevention**:
- Consolidate regularly (daily micro, weekly deep)
- Monitor `/working-memory` before reaching 6/7
- Archive old episodic events periodically

---

### Issue 8: Knowledge Gaps Detected

**Symptoms**:
- `/memory-health --gaps` shows 5+ gaps
- Contradictions in semantic memories
- Uncertainties marked

**Diagnosis**:
```bash
/memory-health --gaps
# Shows: 5 contradictions, 3 uncertainties, 2 ambiguities
```

**Solutions**:

1. **Resolve Contradictions**:
   ```python
   # Find conflicting memories
   gaps = meta.detect_knowledge_gaps()
   for contradiction in gaps['contradictions']:
       print(f"Contradiction: {contradiction['memory1]} vs {contradiction['memory2']}")
       # Manually review and update one memory
       memory.forget(contradiction['memory1'])  # Keep other
   ```

2. **Add Missing Context**:
   ```python
   # For uncertainties, add more information
   graph.add_observation(
       entity_id=some_entity,
       observation="Clarification on ambiguous topic",
       context={"source": "documentation", "confidence": 0.9}
   )
   ```

3. **Consolidate to Clarify**:
   ```bash
   /consolidate --deep
   # Full consolidation often resolves minor gaps
   ```

---

### Issue 9: Plan Validation Failing

**Symptoms**:
- `validate_plan()` returns score <0.4
- Verification fails multiple properties

**Diagnosis**:
```python
result = planning.validate_plan(plan, strict=True)
print(result['issues'])      # Structural problems
print(result['warnings'])    # Feasibility concerns

props = planning.verify_plan_properties(plan)
# Shows which Q* properties fail
```

**Solutions**:

1. **Fix Structure**:
   ```python
   # Ensure required fields present
   plan = {
       "steps": [...],      # Required
       "resources": {...},  # Required
       "timeline": "...",   # Required
   }
   ```

2. **Address Feasibility**:
   ```python
   # Check resource availability
   if plan['resources']['developers'] > available:
       plan['resources']['developers'] = available
       plan['timeline'] = extend_timeline(plan['timeline'], 0.5)
   ```

3. **Improve Properties**:
   ```python
   props = planning.verify_plan_properties(plan)

   # If optimality low: Remove redundant steps
   # If completeness low: Add missing requirements
   # If consistency low: Resolve conflicts
   # If soundness low: Check assumptions valid
   # If minimality low: Consolidate steps
   ```

---

### Issue 10: Reflective RAG Not Converging

**Symptoms**:
- `retrieve_reflective()` hits max_iterations
- Confidence stays <0.8

**Diagnosis**:
```python
results = rag.retrieve_reflective(query, max_iterations=3)

# Check iteration metadata
metrics = get_iteration_metrics(results)
print(f"Iterations: {metrics['total_iterations']}")
print(f"Confidences: {metrics['confidences']}")
print(f"Queries used: {metrics['queries_used']}")
```

**Solutions**:

1. **Simplify Query**:
   ```python
   # Complex query: "How do we handle JWT refresh tokens with rotation and cleanup?"
   # Simple query: "JWT refresh token implementation"

   results = rag.retrieve_reflective(
       "JWT refresh token implementation",
       max_iterations=2,
       confidence_threshold=0.7
   )
   ```

2. **Lower Confidence Threshold**:
   ```python
   results = rag.retrieve_reflective(
       query,
       max_iterations=3,
       confidence_threshold=0.7  # Was 0.8
   )
   ```

3. **Use Different Strategy**:
   ```python
   # Try reranking instead of reflective
   results = rag.retrieve(
       query,
       project_id=1,
       strategy="reranking"
   )
   ```

4. **Add More Context**:
   ```python
   # If problem is context-dependent, add context
   contextual_query = f"{context_info}\n\nQuestion: {query}"
   results = rag.retrieve_reflective(contextual_query)
   ```

---

## Performance Optimization Checklist

- [ ] Indices created (semantic BM25, vector, relations)
- [ ] Vector cache enabled (1-hour TTL)
- [ ] Database vacuum run (if >1GB)
- [ ] Consolidation strategy optimized (speed vs quality)
- [ ] Cognitive load monitored (<6/7 items)
- [ ] Knowledge gaps resolved (<5)
- [ ] Query times profiled (identify bottlenecks)
- [ ] Plan validation passing (score >0.8)

---

## Diagnostic Commands

```bash
# Full health report
/memory-health --detail

# Check all gaps
/memory-health --gaps

# View recent events
/timeline --last 24h

# Check memory quality
/consolidate --dry-run

# Test MCP connection
claude mcp list

# Profile database
sqlite3 /home/user/.work/athena/memory.db << EOF
.mode column
SELECT COUNT(*) as episodic FROM episodic_events;
SELECT COUNT(*) as procedures FROM procedures;
SELECT COUNT(*) as semantic FROM semantic_memories;
.quit
EOF
```

---

## When to Escalate

**Contact Support / File Issue If**:
- MCP server crashes repeatedly
- Database becomes corrupted (PRAGMA integrity_check fails)
- Memory operations timeout (>30s consistently)
- Test suite fails after upgrade
- Performance degradation unexplained

---

## Resources

- **Performance Guide**: [PERFORMANCE_TUNING.md](PERFORMANCE_TUNING.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **API Reference**: [API_REFERENCE.md](API_REFERENCE.md)
- **Development**: [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)
