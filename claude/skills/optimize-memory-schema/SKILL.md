---
category: skill
name: optimize-memory-schema
description: Design and optimize database schemas for performance, scalability, and maintainability
allowed-tools: ["Bash", "Read", "Write", "Grep", "Glob", "Edit"]
confidence: 0.80
trigger: Database slow, schema redesign needed, "schema" mentioned, adding new table, performance regression
---

# Optimize Memory Schema Skill

Guides database schema design, optimization, and evolution for Memory MCP storage layers.

## When I Invoke This

You have:
- New table to add (need schema design)
- Query performance degraded
- Want to plan long-term schema evolution
- Need to add indexes strategically
- Schema migration needed without downtime

## What I Do

I guide schema optimization in these phases:

```
1. ANALYZE Phase: Understand current schema
   → Review existing tables and relationships
   → Identify access patterns (queries, filters)
   → Find performance bottlenecks
   → Calculate data growth rates

2. DESIGN Phase: Plan improvements
   → Normalize or denormalize strategically
   → Choose right column types
   → Plan indexes (before creating!)
   → Consider partitioning if data large

3. VALIDATE Phase: Check feasibility
   → Will schema support expected queries?
   → Migration path clear?
   → Backward compatible?
   → Performance acceptable?

4. IMPLEMENT Phase: Apply changes
   → Create indexes incrementally
   → Add columns with defaults
   → Migrate data carefully
   → Verify performance before/after

5. EVOLVE Phase: Plan for future
   → How will schema grow?
   → When will we need partitioning?
   → What migrations are planned?
   → How do we version schema changes?
```

## Database Design Principles

### Principle 1: Know Your Queries First

```python
# ❌ Bad: Design schema, then optimize for queries
# I want to store memories, let me add all possible fields...
CREATE TABLE memories (
    id INTEGER PRIMARY KEY,
    content TEXT,
    embedding BLOB,
    created_at INTEGER,
    updated_at INTEGER,
    access_count INTEGER,
    last_accessed INTEGER,
    user_id INTEGER,
    project_id INTEGER,
    metadata TEXT,
    tags TEXT,
    ...
);
# Then: Queries are slow! Add indexes everywhere.

# ✓ Good: Identify queries FIRST, design schema around them
# Query 1: Get memory by ID
#   SELECT * FROM memories WHERE id = ?
# Query 2: Find memories by project
#   SELECT * FROM memories WHERE project_id = ? ORDER BY created_at DESC
# Query 3: Search similar to embedding
#   SELECT * FROM memories WHERE embedding MATCH ? LIMIT 10

# Schema designed for these queries:
CREATE TABLE memories (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,  -- Needed for query 2 filter
    content TEXT NOT NULL,
    embedding BLOB,                -- Needed for query 3
    created_at INTEGER NOT NULL,  -- Needed for query 2 sort
    -- Only essential columns, nothing more
);

-- Indexes for identified queries:
CREATE INDEX idx_memories_project
  ON memories(project_id);           -- For query 2 filter
CREATE INDEX idx_memories_created
  ON memories(project_id, created_at); -- For query 2 sort
-- Query 3 needs vector index, handled separately

# Result: Fast queries, lean schema
```

**Key**: Identify queries first, then design schema to support them

---

### Principle 2: Right Column Types (Storage & Speed)

```python
# ❌ Bad: Store everything as TEXT (slow, large)
CREATE TABLE episodic_events (
    id TEXT PRIMARY KEY,      -- UUID as TEXT: 36 bytes per row
    timestamp TEXT,           -- "2025-01-15T10:30:00" as TEXT: 20 bytes
    event_type TEXT,          -- "action" as TEXT: variable length
    count TEXT,               -- "42" as TEXT: variable length
    flags TEXT,               -- "active,important" as TEXT: variable length
);
-- Result: Slow comparisons, large index, wasted space

# ✓ Good: Use right types (fast, small)
CREATE TABLE episodic_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 8 bytes, auto-indexed
    timestamp INTEGER NOT NULL,             -- 8 bytes, fast comparison
    event_type TEXT NOT NULL,               -- Only if actually variable length
    count INTEGER NOT NULL,                 -- 8 bytes, numeric operations
    is_important BOOLEAN,                   -- 1 byte (via INTEGER 0/1)
    is_active BOOLEAN,
);
-- Result: Fast comparisons, compact, efficient

# Type size comparison:
TEXT "42"              → 3 bytes (+ overhead)
INTEGER 42             → 8 bytes (fixed, indexed)
TEXT "2025-01-15..." → 20 bytes
INTEGER 1735300200   → 8 bytes (faster sort/filter)
TEXT "true"          → 5 bytes
BOOLEAN/INTEGER      → 1 byte (0 or 1)
```

**Key**: INTEGER for IDs/timestamps, BOOLEAN for flags, TEXT only if needed

---

### Principle 3: Strategic Indexes (Performance Without Bloat)

```python
# ❌ Bad: Index everything (slow writes, large DB)
CREATE TABLE semantic_memories (
    id INTEGER PRIMARY KEY,
    content TEXT,
    embedding BLOB,
    created_at INTEGER,
    project_id INTEGER,
    layer TEXT,
    usefulness REAL
);

-- Someone creates 7 indexes:
CREATE INDEX idx_content ON semantic_memories(content);
CREATE INDEX idx_embedding ON semantic_memories(embedding);
CREATE INDEX idx_created ON semantic_memories(created_at);
CREATE INDEX idx_project ON semantic_memories(project_id);
CREATE INDEX idx_layer ON semantic_memories(layer);
CREATE INDEX idx_usefulness ON semantic_memories(usefulness);
CREATE INDEX idx_project_layer ON semantic_memories(project_id, layer);

-- Result: Inserts slow (7 index updates), DB large, most indexes unused

# ✓ Good: Index only queries that need it
-- Query 1: Find by project
--   SELECT * FROM WHERE project_id = ?
-- Query 2: Find by layer within project
--   SELECT * FROM WHERE project_id = ? AND layer = ?
-- Query 3: Find high-value memories
--   SELECT * FROM WHERE usefulness > ? ORDER BY created_at

-- Only create indexes for these:
CREATE INDEX idx_semantic_project_layer
  ON semantic_memories(project_id, layer);        -- For query 2 filter
CREATE INDEX idx_semantic_usefulness
  ON semantic_memories(usefulness);               -- For query 3 filter
-- Query 1 could use project index, but project_layer serves both

-- Result: Inserts fast (2 index updates), DB small, all indexes used

# Index selection rules:
- Filter columns → needs index
- Sort columns → needs index
- Covering index: Include both filter AND sort columns
- Don't index: TEXT columns unless filtered, low-cardinality, updated often
```

**Key**: Index only for identified queries; prefer covering indexes

---

### Principle 4: Normalize for Correctness, Denormalize for Speed

```python
# ❌ Pure denormalization (data integrity issues)
CREATE TABLE episodic_events (
    id INTEGER PRIMARY KEY,
    content TEXT,
    semantic_memory_id INTEGER,     -- Denormalized
    semantic_content TEXT,          -- Denormalized copy (can go stale!)
    semantic_created_at INTEGER,    -- Denormalized copy
);
-- Problem: If semantic memory updates, this gets stale!

# ✓ Pure normalization (slower)
CREATE TABLE episodic_events (
    id INTEGER PRIMARY KEY,
    content TEXT,
    semantic_memory_id INTEGER,  -- Foreign key only
);

-- To get semantic content:
SELECT e.content, s.content
FROM episodic_events e
LEFT JOIN semantic_memories s ON e.semantic_memory_id = s.id
-- Result: Correct data, but requires JOIN (slower)

# ✓ Smart denormalization (fast + correct)
CREATE TABLE episodic_events (
    id INTEGER PRIMARY KEY,
    content TEXT,
    semantic_memory_id INTEGER,  -- Foreign key for integrity
    -- DON'T denormalize semantic_content (it can change)
);

CREATE TABLE semantic_memories (
    id INTEGER PRIMARY KEY,
    content TEXT,
    ...
);

-- If you need semantic content often:
-- Option 1: Accept the JOIN (correct, acceptable speed)
-- Option 2: Cache it in application layer
-- Option 3: Denormalize only immutable fields (created_at is OK)

CREATE TABLE episodic_events (
    id INTEGER PRIMARY KEY,
    content TEXT,
    semantic_memory_id INTEGER,
    semantic_created_at INTEGER,  -- ✓ Immutable, safe to denormalize
    semantic_memory_version INTEGER,  -- ✓ Reference version
);
-- Updates to semantic don't affect this table
```

**Key**: Normalize for correctness; denormalize only for immutable fields

---

### Principle 5: Growth Planning (Tomorrow's Schema)

```python
# Current data (2025):
# - 100k episodic events
# - 10k semantic memories
# - DB size: 50MB
# - Indexes: 20MB

# Projected growth (2 years):
# - 100M episodic events (1000x growth)
# - 1M semantic memories (100x growth)
# - Estimated DB size: 50GB

# ❌ Don't design for today only
CREATE TABLE episodic_events (
    id INTEGER PRIMARY KEY,
    content TEXT,
    timestamp INTEGER
);
-- Fine for 100k rows
-- Slow for 100M rows (full table scans)

# ✓ Design for future scale
CREATE TABLE episodic_events (
    id INTEGER PRIMARY KEY,
    content TEXT,
    timestamp INTEGER NOT NULL,
    session_id INTEGER NOT NULL,     -- For partitioning later
    project_id INTEGER NOT NULL
);

-- Index for common access patterns
CREATE INDEX idx_episodic_session_time
  ON episodic_events(session_id, timestamp);

-- Plan for partitioning by session_id when needed:
-- CREATE TABLE episodic_events_2025Q1
-- CREATE TABLE episodic_events_2025Q2
-- ...
-- Queries automatically partition on session_id

# Partitioning benefits:
- 100M rows spread across 100 tables = 1M rows per table (fast)
- Old tables archived (dropped or moved to cold storage)
- Queries only scan relevant partitions
```

**Key**: Design schema to support planned growth

---

## Memory MCP Schema Best Practices

### Pattern 1: Table Design for Memory Layers

```python
# Pattern for episodic layer
CREATE TABLE episodic_events (
    -- Unique identifier
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Session tracking (for partitioning)
    session_id INTEGER NOT NULL,

    -- Time-based ordering (essential for consolidation)
    timestamp INTEGER NOT NULL,

    -- Content and type
    content TEXT NOT NULL,
    event_type TEXT NOT NULL,

    -- Consolidation state
    is_consolidated BOOLEAN DEFAULT 0,

    -- Indexing
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

-- Indexes for identified queries:
CREATE INDEX idx_episodic_session_time
  ON episodic_events(session_id, timestamp);        -- For time-range queries
CREATE INDEX idx_episodic_consolidated
  ON episodic_events(is_consolidated, timestamp);   -- For consolidation queries

-- Pattern for semantic layer
CREATE TABLE semantic_memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding BLOB,                 -- Vector data
    created_at INTEGER NOT NULL,    -- Immutable reference
    is_archived BOOLEAN DEFAULT 0,  -- For pruning
);

-- Indexes
CREATE INDEX idx_semantic_project
  ON semantic_memories(project_id);
CREATE INDEX idx_semantic_archived
  ON semantic_memories(is_archived);
```

---

### Pattern 2: Foreign Key Relationships

```python
# ✓ Good: Explicit relationships
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE episodic_events (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id)
);

-- Benefits:
-- 1. Referential integrity (can't delete project with events)
-- 2. Database enforces consistency
-- 3. Query optimization (DB knows relationships)

# Enable foreign keys:
PRAGMA foreign_keys = ON;
```

---

### Pattern 3: Schema Migration

```python
# ❌ Bad: Direct ALTER (can fail mid-migration)
ALTER TABLE episodic_events ADD COLUMN is_important BOOLEAN;
-- If this fails midway, schema is corrupted

# ✓ Good: Safe migration strategy
-- Step 1: Add column with default
ALTER TABLE episodic_events
ADD COLUMN is_important BOOLEAN DEFAULT 0;

-- Step 2: Update existing rows in batches
UPDATE episodic_events
SET is_important = 1
WHERE ... (batch conditions)
LIMIT 1000;

-- Step 3: Verify
SELECT COUNT(*) FROM episodic_events WHERE is_important IS NULL;
-- Should be 0

-- Step 4: Remove default if not needed going forward
-- (SQLite doesn't support dropping defaults, so we're done)

# For adding indexed columns:
-- Step 1: Add column
-- Step 2: Update data
-- Step 3: Create index (don't create before data!)
CREATE INDEX idx_episodic_important
  ON episodic_events(is_important);
```

---

### Pattern 4: Viewing Schema Health

```bash
# Analyze current schema
sqlite3 ~/.memory-mcp/memory.db

# View all tables
.schema

# View specific table
.schema episodic_events

# Check indexes
.indices episodic_events

# Get table statistics
PRAGMA table_info(episodic_events);

# Check foreign keys
PRAGMA foreign_key_list(episodic_events);

# Query performance analysis
EXPLAIN QUERY PLAN SELECT * FROM episodic_events WHERE session_id = ? AND timestamp > ?;
-- Look for "SEARCH" (good, uses index) vs "SCAN" (bad, full table scan)
```

---

## Step-by-Step Schema Optimization

### Step 1: Document Current Access Patterns

```python
# For each layer, document:
# 1. What queries do we run?
# 2. How often?
# 3. What filters?
# 4. What sorting?

# Example for episodic:
# Query 1: Get all events from session (daily, frequent)
#   SELECT * FROM episodic_events
#   WHERE session_id = ?
#   ORDER BY timestamp DESC
# Query 2: Find unconsolidated events (consolidation process)
#   SELECT * FROM episodic_events
#   WHERE is_consolidated = 0
#   ORDER BY timestamp
# Query 3: Find events by type (analysis)
#   SELECT * FROM episodic_events
#   WHERE event_type = ?
```

### Step 2: Analyze Slow Queries

```bash
# Identify slow queries with query plan
sqlite3 ~/.memory-mcp/memory.db
EXPLAIN QUERY PLAN SELECT * FROM episodic_events WHERE session_id = ? AND timestamp > ?;

# Output:
# 0|0|0|SCAN TABLE episodic_events (~...) ← BAD: Full table scan!

# Add index to fix:
CREATE INDEX idx_episodic_session_time ON episodic_events(session_id, timestamp);

# Re-check plan:
# 0|0|0|SEARCH TABLE episodic_events USING INDEX idx_episodic_session_time ← GOOD!
```

### Step 3: Design Indexes for Identified Queries

```python
# Rule: Index columns that appear in WHERE or ORDER BY

# Query: SELECT * WHERE project_id = ? AND layer = ? ORDER BY created_at
# Indexes needed:
# - On (project_id, layer) for WHERE
# - On created_at for ORDER BY
# - Best: Covering index on (project_id, layer, created_at)

CREATE INDEX idx_semantic_query
  ON semantic_memories(project_id, layer, created_at);
```

### Step 4: Plan for Growth

```python
# Current: 100k rows, 50MB
# Expected: 100M rows in 2 years
# Plan:
# - Partition by session_id when >10M rows
# - Archive old events after 1 year
# - Denormalize immutable fields only
```

### Step 5: Implement Incrementally

```bash
# 1. Backup first
cp ~/.memory-mcp/memory.db ~/.memory-mcp/memory.db.backup

# 2. Test changes in test database
sqlite3 /tmp/test.db < schema_changes.sql

# 3. Verify performance improvement
pytest tests/performance/ -v

# 4. Apply to production
sqlite3 ~/.memory-mcp/memory.db < schema_changes.sql

# 5. Verify again
pytest tests/performance/ -v
```

## Schema Checklist

- [ ] All tables have PRIMARY KEY (usually id)
- [ ] All foreign keys defined (referential integrity)
- [ ] Appropriate indexes for identified queries
- [ ] No TEXT where INTEGER would work
- [ ] No unused columns (slim schema)
- [ ] No redundant indexes
- [ ] Growth plan documented (future scaling)
- [ ] Partitioning strategy identified (if >100M rows)
- [ ] Migration path clear (how to evolve)
- [ ] Performance validated (query plans checked)
- [ ] Backup strategy clear
- [ ] Monitoring in place (size, query latency)

## Common Schema Mistakes

### Mistake 1: Over-Normalization

```python
# ❌ Too many joins
CREATE TABLE users (id, name)
CREATE TABLE projects (id, user_id, name)
CREATE TABLE sessions (id, project_id)
CREATE TABLE episodic_events (id, session_id, content)

-- Query: GET events for user
SELECT e.* FROM episodic_events e
JOIN sessions s ON e.session_id = s.id
JOIN projects p ON s.project_id = p.id
JOIN users u ON p.user_id = u.id
WHERE u.id = ?
-- 4 JOINs = slow!

# ✓ Denormalize user_id where it's frequently accessed
CREATE TABLE episodic_events (
    id INTEGER PRIMARY KEY,
    session_id INTEGER,
    user_id INTEGER,  -- Denormalized for fast access
    content TEXT
);

-- Query is now fast:
SELECT * FROM episodic_events WHERE user_id = ?
```

### Mistake 2: Unbounded Text Columns

```python
# ❌ No limit on text
CREATE TABLE memory_content (
    id INTEGER,
    content TEXT  -- Could be 10MB! Slows down all queries.
);

# ✓ Limit or separate
CREATE TABLE memory_content (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,      -- Summary, < 500 chars
    content_id INTEGER        -- Foreign key
);

CREATE TABLE memory_content_data (
    id INTEGER PRIMARY KEY,
    content TEXT              -- Full content in separate table
);
-- Main table stays fast (small rows)
-- Full content fetched only when needed
```

### Mistake 3: Missing Indexes on Foreign Keys

```python
# ❌ No index on foreign key
CREATE TABLE episodic_events (
    id INTEGER PRIMARY KEY,
    session_id INTEGER,  -- Foreign key, but no index
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

-- Query slow: SELECT * FROM episodic_events WHERE session_id = ?
-- Full table scan because session_id has no index

# ✓ Index foreign keys
CREATE INDEX idx_episodic_session ON episodic_events(session_id);
-- Now query is fast
```

## Related Skills

- **add-mcp-tool** - MCP tool to expose schema optimization operations
- **implement-memory-layer** - Layer store classes match schema
- **profile-performance** - Profile queries against schema
- **debug-integration-issue** - Schema issues cause integration problems

## Success Criteria

✓ Schema supports identified queries efficiently
✓ All queries use indexes (SEARCH, not SCAN)
✓ Growth plan documented
✓ No wasted columns or indexes
✓ Referential integrity enforced
✓ Migration path clear
✓ Performance meets targets (<100ms queries)
✓ Scalable to 10x expected growth
✓ Schema documented (access patterns, future plans)
✓ Backup and recovery strategy clear
