# Phase 5: PostgreSQL + pgvector Schema Design

**Status**: Greenfield Design (No Migration Needed)
**Date**: November 8, 2025
**Architecture**: Unified Multi-Domain Database

---

## Overview

Unified PostgreSQL schema supporting all three integrated domains:
1. **Memory** (70+ operations across 8 layers)
2. **Planning** (Q*, tasks, goals, adaptive replanning)
3. **Code Analysis** (semantic code search, dependency analysis, metadata)

**Key Design Principles**:
- ✅ Single ACID source of truth
- ✅ Native hybrid search (vectors + full-text + relational)
- ✅ Project-scoped isolation (multi-project support)
- ✅ Efficient filtering by type, domain, recency
- ✅ Support for reconsolidation and memory versioning
- ✅ Code metadata and semantic relationships

---

## Core Tables

### 1. Projects (Multi-Project Isolation)

```sql
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    path TEXT UNIQUE NOT NULL,
    description TEXT,

    -- Metadata
    language VARCHAR(50),  -- 'python', 'typescript', 'go', etc.
    framework VARCHAR(100),  -- For code analysis context

    -- Lifecycle
    created_at TIMESTAMP DEFAULT NOW(),
    last_accessed TIMESTAMP DEFAULT NOW(),
    last_modified TIMESTAMP DEFAULT NOW(),

    -- Statistics
    memory_count INT DEFAULT 0,
    total_events INT DEFAULT 0,
    task_count INT DEFAULT 0,

    -- Settings
    embedding_dim INT DEFAULT 768,
    consolidation_interval INT DEFAULT 3600,  -- seconds

    -- Indices
    INDEX idx_projects_created (created_at DESC),
    INDEX idx_projects_accessed (last_accessed DESC)
);
```

### 2. Memory Vectors (Unified Vector Storage)

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE memory_vectors (
    id BIGSERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Core content
    content TEXT NOT NULL,
    content_type VARCHAR(50),  -- 'episodic', 'semantic', 'code', 'task'

    -- Embedding
    embedding vector(768) NOT NULL,

    -- Full-text search index
    content_tsvector tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,

    -- Memory classification
    memory_type VARCHAR(50) NOT NULL,  -- 'fact', 'pattern', 'decision', 'context', 'code_snippet'
    domain VARCHAR(100),  -- 'memory', 'planning', 'code-analysis'
    tags TEXT[] DEFAULT '{}',

    -- Temporal & Access
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_accessed TIMESTAMP DEFAULT NOW(),
    last_retrieved TIMESTAMP,  -- For reconsolidation window
    access_count INT DEFAULT 0,

    -- Quality metrics
    usefulness_score FLOAT DEFAULT 0.0,  -- 0-1
    confidence FLOAT DEFAULT 1.0,
    quality_score FLOAT GENERATED ALWAYS AS (
        (0.5 * usefulness_score + 0.3 * confidence + 0.2 * LEAST(access_count::float / 100, 1.0))
    ) STORED,

    -- Consolidation state
    consolidation_state VARCHAR(50) DEFAULT 'unconsolidated',  -- unconsolidated, consolidating, consolidated, labile, reconsolidating, superseded
    consolidated_at TIMESTAMP,
    superseded_by BIGINT REFERENCES memory_vectors(id) ON DELETE SET NULL,
    version INT DEFAULT 1,

    -- Relationships for episodic events
    session_id VARCHAR(255),  -- For grouping related events
    event_type VARCHAR(50),  -- 'action', 'learning', 'error', 'decision'

    -- Code-specific metadata
    code_language VARCHAR(50),  -- for code domain
    code_hash VARCHAR(64),  -- for deduplication

    -- Indices for performance
    CONSTRAINT fk_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    INDEX idx_memory_project (project_id),
    INDEX idx_memory_type (memory_type),
    INDEX idx_memory_consolidation (consolidation_state),
    INDEX idx_memory_quality (quality_score DESC),
    INDEX idx_memory_accessed (last_accessed DESC),
    INDEX idx_memory_session (session_id),
    INDEX idx_memory_embedding ON memory_vectors USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100),
    FULLTEXT INDEX idx_memory_fts (content)
);
```

### 3. Memory Relationships

```sql
CREATE TABLE memory_relationships (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    from_memory_id BIGINT NOT NULL REFERENCES memory_vectors(id) ON DELETE CASCADE,
    to_memory_id BIGINT NOT NULL REFERENCES memory_vectors(id) ON DELETE CASCADE,

    -- Relationship type
    relationship_type VARCHAR(50) NOT NULL,  -- 'reinforces', 'contradicts', 'extends', 'depends_on', 'caused_by'
    strength FLOAT DEFAULT 1.0,  -- 0-1

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(from_memory_id, to_memory_id, relationship_type),
    INDEX idx_from_memory (from_memory_id),
    INDEX idx_to_memory (to_memory_id),
    INDEX idx_relationship_type (relationship_type)
);
```

### 4. Episodic Events (Temporal Grounding)

```sql
CREATE TABLE episodic_events (
    id BIGSERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    memory_vector_id BIGINT REFERENCES memory_vectors(id) ON DELETE SET NULL,

    -- Temporal
    session_id VARCHAR(255) NOT NULL,
    timestamp BIGINT NOT NULL,  -- Unix timestamp ms
    duration_ms INT,

    -- Event details
    event_type VARCHAR(50) NOT NULL,  -- 'action', 'learning', 'error', 'decision'
    content TEXT NOT NULL,
    outcome TEXT,

    -- Spatial-temporal context
    context_cwd TEXT,  -- Current working directory
    context_files TEXT[],  -- Files involved
    context_task VARCHAR(255),  -- Current task
    context_phase VARCHAR(50),  -- Development phase
    context_branch VARCHAR(255),  -- Git branch

    -- Code metrics
    files_changed INT DEFAULT 0,
    lines_added INT DEFAULT 0,
    lines_deleted INT DEFAULT 0,

    -- Learning signal
    learned TEXT,
    surprise_score FLOAT,  -- 0-1, how surprising was this?
    confidence FLOAT DEFAULT 1.0,

    -- Consolidation
    consolidation_status VARCHAR(50) DEFAULT 'unconsolidated',
    consolidated_at TIMESTAMP,

    INDEX idx_project (project_id),
    INDEX idx_session (session_id),
    INDEX idx_timestamp (timestamp DESC),
    INDEX idx_event_type (event_type),
    INDEX idx_consolidation (consolidation_status)
);
```

### 5. Tasks & Goals (Prospective Memory)

```sql
CREATE TABLE prospective_tasks (
    id BIGSERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    title VARCHAR(255) NOT NULL,
    description TEXT,

    -- Status lifecycle
    status VARCHAR(50) DEFAULT 'pending',  -- pending, in_progress, blocked, completed, cancelled
    priority INT DEFAULT 5,  -- 1-10

    -- Goals
    goal_id BIGINT REFERENCES prospective_goals(id) ON DELETE SET NULL,

    -- Decomposition
    parent_task_id BIGINT REFERENCES prospective_tasks(id) ON DELETE SET NULL,

    -- Effort & Time
    estimated_effort_hours FLOAT,
    actual_effort_hours FLOAT,
    due_date DATE,

    -- Association with knowledge
    related_memory_ids BIGINT[] DEFAULT '{}',  -- Vector of related memory IDs
    related_code_ids BIGINT[] DEFAULT '{}',    -- Vector of related code vectors

    -- Metrics
    completion_percentage INT DEFAULT 0,
    success_rate FLOAT,

    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    INDEX idx_project (project_id),
    INDEX idx_status (status),
    INDEX idx_priority (priority DESC),
    INDEX idx_goal (goal_id),
    INDEX idx_due_date (due_date)
);

CREATE TABLE prospective_goals (
    id BIGSERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Priority & lifecycle
    priority INT DEFAULT 5,  -- 1-10
    status VARCHAR(50) DEFAULT 'active',  -- active, completed, archived, superseded

    -- Progress
    completion_percentage INT DEFAULT 0,
    estimated_completion_date DATE,

    -- Relationships
    parent_goal_id BIGINT REFERENCES prospective_goals(id) ON DELETE SET NULL,
    related_memory_ids BIGINT[] DEFAULT '{}',

    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,

    INDEX idx_project (project_id),
    INDEX idx_status (status),
    INDEX idx_priority (priority DESC),
    INDEX idx_parent (parent_goal_id)
);
```

### 6. Code Metadata (Code Analysis Domain)

```sql
CREATE TABLE code_metadata (
    id BIGSERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    memory_vector_id BIGINT NOT NULL REFERENCES memory_vectors(id) ON DELETE CASCADE,

    -- Code location
    file_path TEXT NOT NULL,
    language VARCHAR(50),

    -- Code entity
    entity_type VARCHAR(50),  -- 'function', 'class', 'module', 'constant'
    entity_name VARCHAR(255),

    -- Structure
    start_line INT,
    end_line INT,
    signature TEXT,  -- Function/class signature
    docstring TEXT,

    -- Semantic properties
    semantic_hash VARCHAR(64),  -- Hash of semantic content (ignoring formatting)
    dependencies TEXT[],  -- What this code depends on
    dependents TEXT[],  -- What depends on this code

    -- Complexity metrics
    cyclomatic_complexity INT,
    lines_of_code INT,

    created_at TIMESTAMP DEFAULT NOW(),
    last_analyzed_at TIMESTAMP,

    UNIQUE(project_id, file_path, entity_name),
    INDEX idx_project (project_id),
    INDEX idx_file (file_path),
    INDEX idx_entity_type (entity_type),
    INDEX idx_language (language)
);
```

### 7. Code Dependencies

```sql
CREATE TABLE code_dependencies (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    from_code_id BIGINT NOT NULL REFERENCES code_metadata(id) ON DELETE CASCADE,
    to_code_id BIGINT NOT NULL REFERENCES code_metadata(id) ON DELETE CASCADE,

    dependency_type VARCHAR(50),  -- 'imports', 'calls', 'extends', 'implements'
    strength FLOAT DEFAULT 1.0,  -- Measure of coupling

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(from_code_id, to_code_id, dependency_type),
    INDEX idx_from (from_code_id),
    INDEX idx_to (to_code_id),
    INDEX idx_type (dependency_type)
);
```

### 8. Planning & Decisions (Planning Domain)

```sql
CREATE TABLE planning_decisions (
    id BIGSERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    decision_type VARCHAR(50),  -- 'architectural', 'algorithm', 'refactoring', 'integration'
    title VARCHAR(255) NOT NULL,
    rationale TEXT,

    -- Decision context
    context_memory_ids BIGINT[] DEFAULT '{}',  -- Memories informing decision
    alternatives TEXT[],

    -- Validation
    validation_status VARCHAR(50) DEFAULT 'pending',  -- pending, validated, superseded
    validation_confidence FLOAT,

    created_at TIMESTAMP DEFAULT NOW(),
    validated_at TIMESTAMP,
    superseded_by BIGINT REFERENCES planning_decisions(id) ON DELETE SET NULL,

    INDEX idx_project (project_id),
    INDEX idx_status (validation_status)
);

CREATE TABLE planning_scenarios (
    id BIGSERIAL PRIMARY KEY,
    decision_id BIGINT NOT NULL REFERENCES planning_decisions(id) ON DELETE CASCADE,

    scenario_name VARCHAR(255),
    description TEXT,

    -- Scenario properties
    impact_assessment TEXT,
    risk_level VARCHAR(50),  -- low, medium, high
    probability FLOAT,

    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Query Patterns

### Hybrid Search (Semantic + Full-Text + Relational)

```sql
-- Find relevant memories for a query, combining vector similarity + keyword match
SELECT
    m.*,

    -- Scoring
    1 - (m.embedding <=> $1::vector) as semantic_similarity,
    ts_rank(m.content_tsvector, plainto_tsquery($2)) as keyword_rank,
    (0.7 * (1 - (m.embedding <=> $1::vector)) + 0.3 * COALESCE(ts_rank(m.content_tsvector, plainto_tsquery($2)), 0)) as hybrid_score

FROM memory_vectors m
WHERE
    m.project_id = $3
    AND m.consolidation_state = 'consolidated'
    AND (
        1 - (m.embedding <=> $1::vector) > 0.3  -- Semantic threshold
        OR ts_rank(m.content_tsvector, plainto_tsquery($2)) > 0  -- Has keywords
    )
    AND (memory_types IS NULL OR m.memory_type = ANY(memory_types))

ORDER BY hybrid_score DESC
LIMIT $4;
```

### Temporal Query (With Episodic Grounding)

```sql
-- Find events in time range with learned insights
SELECT
    e.*,
    m.content as learned_content,
    m.consolidation_state
FROM episodic_events e
LEFT JOIN memory_vectors m ON e.memory_vector_id = m.id
WHERE
    e.project_id = $1
    AND e.timestamp BETWEEN $2 AND $3
    AND e.event_type = ANY($4::text[])
ORDER BY e.timestamp DESC;
```

### Reconsolidation Window (For Learning)

```sql
-- Find memories ready for reconsolidation (labile window)
SELECT
    m.*,
    EXTRACT(EPOCH FROM (NOW() - m.last_retrieved)) as seconds_since_retrieval
FROM memory_vectors m
WHERE
    m.project_id = $1
    AND m.consolidation_state = 'labile'
    AND m.last_retrieved IS NOT NULL
    AND EXTRACT(EPOCH FROM (NOW() - m.last_retrieved)) < 3600  -- Within 1 hour
ORDER BY m.last_retrieved DESC;
```

### Task Planning with Knowledge Integration

```sql
-- Find tasks and related knowledge for planning
SELECT
    t.*,
    array_agg(DISTINCT m.content) as related_knowledge,
    COUNT(DISTINCT m.id) as knowledge_count
FROM prospective_tasks t
LEFT JOIN memory_vectors m ON m.id = ANY(t.related_memory_ids)
WHERE
    t.project_id = $1
    AND t.status != 'completed'
ORDER BY t.priority DESC, t.due_date ASC;
```

### Code Impact Analysis

```sql
-- Find all code affected by a change to one function
WITH RECURSIVE code_impact AS (
    -- Start with the changed function
    SELECT to_code_id as code_id, 1 as depth
    FROM code_dependencies
    WHERE from_code_id = $1

    UNION ALL

    -- Find dependents of dependents
    SELECT cd.to_code_id, ci.depth + 1
    FROM code_dependencies cd
    INNER JOIN code_impact ci ON cd.from_code_id = ci.code_id
    WHERE ci.depth < 5  -- Limit depth
)
SELECT DISTINCT cm.*, ci.depth
FROM code_impact ci
JOIN code_metadata cm ON cm.id = ci.code_id
ORDER BY ci.depth;
```

---

## Indices Strategy

### Vector Search
```sql
CREATE INDEX idx_memory_embedding_ivfflat
ON memory_vectors USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);  -- Adjust based on data size
```

### Full-Text Search
```sql
CREATE INDEX idx_memory_content_fts
ON memory_vectors USING GIN (content_tsvector);
```

### Filtering Optimization
```sql
CREATE INDEX idx_memory_project_type
ON memory_vectors(project_id, memory_type)
WHERE consolidation_state = 'consolidated';

CREATE INDEX idx_memory_project_domain
ON memory_vectors(project_id, domain, consolidation_state);
```

### Temporal Queries
```sql
CREATE INDEX idx_episodic_project_timestamp
ON episodic_events(project_id, timestamp DESC);
```

---

## Performance Characteristics

### Expected Latencies (Multi-Domain)

| Query Type | Data Size | Latency | Notes |
|-----------|-----------|---------|-------|
| Semantic search (vector only) | 100K vectors | 5-20ms | HNSW index |
| Keyword search (FTS) | 100K memories | 10-50ms | GIN index |
| Hybrid search (combined) | 100K memories | 20-60ms | Both indices |
| Filtering by project | 100K memories | <5ms | Composite index |
| Temporal range query | 100K events | 10-30ms | Timestamp index |
| Code dependency traverse | 10K functions | 20-100ms | Recursive query depth |
| Task planning with knowledge | 1K tasks | 50-150ms | Aggregate join |

---

## Partitioning Strategy (Future Optimization)

For systems with 1M+ vectors, consider partitioning by project:

```sql
CREATE TABLE memory_vectors_partition (
    LIKE memory_vectors
) PARTITION BY LIST (project_id);

-- Create partitions as needed
CREATE TABLE memory_vectors_proj_1 PARTITION OF memory_vectors_partition
    FOR VALUES IN (1);
```

---

## Configuration

### PostgreSQL Settings (postgresql.conf)

```ini
# Memory & Performance
shared_buffers = 256MB  # 25% of system RAM
effective_cache_size = 1GB  # 50-75% of system RAM
work_mem = 16MB
maintenance_work_mem = 64MB

# Vector Search (pgvector)
ivfflat.probes = 20  # Default is 1, higher = more accurate but slower

# Full-Text Search
max_wal_size = 4GB
checkpoint_completion_target = 0.9

# Connections
max_connections = 100
```

### pgvector Settings

```python
# Python/application config
VECTOR_SIMILARITY_THRESHOLD = 0.3  # Cosine similarity
VECTOR_INDEX_LISTS = 100  # IVFFlat lists (adjust based on vector count)
VECTOR_INDEX_PROBES = 20  # Query time accuracy vs speed tradeoff
```

---

## Benefits Over Alternatives

| Aspect | SQLite+sqlite-vec | Qdrant | PostgreSQL+pgvector |
|--------|------------------|--------|---------------------|
| **Vector search latency** | 100-150ms | 5-20ms | 5-20ms |
| **Full-text search** | ❌ App-level | ❌ Not native | ✅ Native FTS |
| **Relational queries** | ✅ But slow | ❌ No schema | ✅ Full SQL |
| **ACID transactions** | ✅ But limited | ❌ No | ✅ Yes |
| **Multi-project isolation** | Via code | Via filters | ✅ Native |
| **Hybrid search** | App-level fusion | Not native | ✅ SQL native |
| **Scalability** | <100K vectors | 100M+ | 1M+ vectors |
| **Infrastructure** | Zero | Docker | Docker |
| **Data consistency** | Good | Good | ✅ Excellent |

---

## Next Steps

1. Create docker-compose with PostgreSQL + pgvector
2. Implement Python database layer for PostgreSQL
3. Migrate semantic search to native pgvector hybrid queries
4. Update all 70+ operations to use pgvector schema
5. Performance tuning and benchmarking

