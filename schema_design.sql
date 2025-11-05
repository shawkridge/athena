-- ==============================================================================
-- UNIFIED 8-LAYER MEMORY SYSTEM SCHEMA
-- For solo senior software engineer with multiple long-running projects
-- SQLite + sqlite-vec (optimal for local-first, portable, single-user)
-- ==============================================================================

-- ==============================================================================
-- LAYER 0 & 1: Working Memory / Session Memory
-- (Handled by Claude Code context window, not stored)
-- ==============================================================================

-- ==============================================================================
-- EXISTING TABLES (Layer 3: Semantic Memory)
-- ==============================================================================

-- Already exists: projects table
-- Already exists: memories table (content, type, tags, scores)
-- Already exists: memory_vectors (sqlite-vec for embeddings)
-- Already exists: memory_relations (basic relations between memories)
-- Already exists: optimization_stats

-- ==============================================================================
-- LAYER 2: EPISODIC MEMORY (Temporal Events)
-- "What happened when" - time-stamped experiences
-- ==============================================================================

-- Core events table
CREATE TABLE IF NOT EXISTS episodic_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    session_id TEXT NOT NULL,           -- Links related events in same session
    timestamp INTEGER NOT NULL,         -- Unix timestamp
    event_type TEXT NOT NULL,           -- conversation|action|decision|error|success|file_change
    content TEXT NOT NULL,              -- What happened
    outcome TEXT,                       -- success|failure|partial

    -- Context snapshot at time of event
    context_cwd TEXT,                   -- Working directory
    context_files TEXT,                 -- JSON array of active files
    context_task TEXT,                  -- Active task if any
    context_phase TEXT,                 -- Active phase if any

    -- Metadata
    duration_ms INTEGER,                -- How long action took
    files_changed INTEGER DEFAULT 0,    -- Number of files modified
    lines_added INTEGER DEFAULT 0,
    lines_deleted INTEGER DEFAULT 0,

    -- Learning
    learned TEXT,                       -- What we learned from this event
    confidence REAL DEFAULT 1.0,        -- How confident we are in this memory

    -- Foreign keys
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Event outcomes and metrics
CREATE TABLE IF NOT EXISTS event_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    metric_name TEXT NOT NULL,          -- tests_passed|coverage|performance|etc
    metric_value TEXT NOT NULL,         -- JSON value
    FOREIGN KEY (event_id) REFERENCES episodic_events(id) ON DELETE CASCADE
);

-- Event relations (cause → effect chains)
CREATE TABLE IF NOT EXISTS event_relations (
    from_event_id INTEGER NOT NULL,
    to_event_id INTEGER NOT NULL,
    relation_type TEXT NOT NULL,        -- caused_by|led_to|related_to
    strength REAL DEFAULT 1.0,
    PRIMARY KEY (from_event_id, to_event_id),
    FOREIGN KEY (from_event_id) REFERENCES episodic_events(id) ON DELETE CASCADE,
    FOREIGN KEY (to_event_id) REFERENCES episodic_events(id) ON DELETE CASCADE
);

-- Vector embeddings for semantic search of events
CREATE VIRTUAL TABLE IF NOT EXISTS event_vectors USING vec0(
    embedding FLOAT[768]
);

-- Indices for fast temporal queries
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON episodic_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_project ON episodic_events(project_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_session ON episodic_events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON episodic_events(event_type);

-- ==============================================================================
-- LAYER 4: PROCEDURAL MEMORY (Skills & Templates)
-- "How to do X" - executable patterns and workflows
-- ==============================================================================

-- Procedure templates
CREATE TABLE IF NOT EXISTS procedures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,             -- git|refactoring|debugging|testing|deployment|architecture
    description TEXT,

    -- When to use this procedure
    trigger_pattern TEXT,               -- Regex or condition for when to suggest
    applicable_contexts TEXT,           -- JSON array of contexts (e.g., ["react", "typescript"])

    -- The procedure itself
    template TEXT NOT NULL,             -- Template with {{variables}}
    steps TEXT,                         -- JSON array of step objects
    examples TEXT,                      -- JSON array of example usages

    -- Learning metrics
    success_rate REAL DEFAULT 0.0,      -- 0.0 to 1.0
    usage_count INTEGER DEFAULT 0,
    avg_completion_time_ms INTEGER,

    -- Metadata
    created_at INTEGER NOT NULL,
    last_used INTEGER,
    created_by TEXT DEFAULT 'user'      -- user|learned|imported
);

-- Procedure variables/parameters
CREATE TABLE IF NOT EXISTS procedure_params (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    procedure_id INTEGER NOT NULL,
    param_name TEXT NOT NULL,
    param_type TEXT NOT NULL,           -- string|number|boolean|file|directory
    required BOOLEAN DEFAULT 1,
    default_value TEXT,
    description TEXT,
    FOREIGN KEY (procedure_id) REFERENCES procedures(id) ON DELETE CASCADE
);

-- Procedure execution history
CREATE TABLE IF NOT EXISTS procedure_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    procedure_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    outcome TEXT NOT NULL,              -- success|failure|partial
    duration_ms INTEGER,
    variables TEXT,                     -- JSON of variable values used
    learned TEXT,                       -- What we learned from this execution
    FOREIGN KEY (procedure_id) REFERENCES procedures(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_procedures_category ON procedures(category);
CREATE INDEX IF NOT EXISTS idx_procedures_usage ON procedures(usage_count DESC);
CREATE INDEX IF NOT EXISTS idx_executions_procedure ON procedure_executions(procedure_id);

-- ==============================================================================
-- LAYER 5: PROSPECTIVE MEMORY (Future Tasks & Intentions)
-- "Remember to X" - tasks with intelligent triggers
-- ==============================================================================

-- Tasks with trigger conditions
CREATE TABLE IF NOT EXISTS prospective_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,                 -- NULL for cross-project tasks
    content TEXT NOT NULL,
    active_form TEXT NOT NULL,          -- Present continuous form for display

    -- Timing
    created_at INTEGER NOT NULL,
    due_at INTEGER,                     -- Optional deadline
    completed_at INTEGER,

    -- Status
    status TEXT NOT NULL DEFAULT 'pending',  -- pending|active|completed|cancelled|blocked
    priority TEXT DEFAULT 'medium',     -- low|medium|high|critical

    -- Assignment
    assignee TEXT DEFAULT 'user',       -- user|claude|sub-agent:name

    -- Metadata
    notes TEXT,                         -- Additional context
    blocked_reason TEXT,                -- Why task is blocked

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Task trigger conditions
CREATE TABLE IF NOT EXISTS task_triggers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    trigger_type TEXT NOT NULL,         -- time|event|context|dependency|file
    trigger_condition TEXT NOT NULL,    -- JSON condition
    fired BOOLEAN DEFAULT 0,            -- Has this trigger fired?
    fired_at INTEGER,                   -- When it fired
    FOREIGN KEY (task_id) REFERENCES prospective_tasks(id) ON DELETE CASCADE
);

-- Task dependencies
CREATE TABLE IF NOT EXISTS task_dependencies (
    task_id INTEGER NOT NULL,
    depends_on_task_id INTEGER NOT NULL,
    dependency_type TEXT DEFAULT 'blocks',  -- blocks|related|enables
    PRIMARY KEY (task_id, depends_on_task_id),
    FOREIGN KEY (task_id) REFERENCES prospective_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (depends_on_task_id) REFERENCES prospective_tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tasks_project ON prospective_tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON prospective_tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON prospective_tasks(priority);
CREATE INDEX IF NOT EXISTS idx_triggers_task ON task_triggers(task_id);

-- ==============================================================================
-- LAYER 6: KNOWLEDGE GRAPH (Associative Network)
-- Entities, relations, and observations for structured knowledge
-- ==============================================================================

-- Entities (nodes in the graph)
CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,          -- Project|Phase|Task|File|Function|Concept|Person|Decision|Pattern
    project_id INTEGER,                 -- Optional project scope

    -- Metadata
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    metadata TEXT,                      -- JSON for flexible attributes

    -- Make name unique within type and project
    UNIQUE(name, entity_type, project_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Relations (edges in the graph)
CREATE TABLE IF NOT EXISTS entity_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_entity_id INTEGER NOT NULL,
    to_entity_id INTEGER NOT NULL,
    relation_type TEXT NOT NULL,        -- contains|depends_on|implements|tests|caused_by|relates_to|active_in

    -- Relation strength and confidence
    strength REAL DEFAULT 1.0,
    confidence REAL DEFAULT 1.0,

    -- Temporal aspects
    created_at INTEGER NOT NULL,
    valid_from INTEGER,                 -- Optional temporal validity
    valid_until INTEGER,

    -- Metadata
    metadata TEXT,                      -- JSON for flexible attributes

    FOREIGN KEY (from_entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (to_entity_id) REFERENCES entities(id) ON DELETE CASCADE
);

-- Observations (facts about entities)
CREATE TABLE IF NOT EXISTS entity_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL,
    content TEXT NOT NULL,              -- The observation itself
    observation_type TEXT,              -- status|property|note|metric

    -- Confidence and provenance
    confidence REAL DEFAULT 1.0,
    source TEXT DEFAULT 'user',         -- user|inferred|learned|imported

    -- Temporal
    timestamp INTEGER NOT NULL,
    superseded_by INTEGER,              -- Points to newer observation that replaces this

    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (superseded_by) REFERENCES entity_observations(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_project ON entities(project_id);
CREATE INDEX IF NOT EXISTS idx_relations_from ON entity_relations(from_entity_id);
CREATE INDEX IF NOT EXISTS idx_relations_to ON entity_relations(to_entity_id);
CREATE INDEX IF NOT EXISTS idx_relations_type ON entity_relations(relation_type);
CREATE INDEX IF NOT EXISTS idx_observations_entity ON entity_observations(entity_id);

-- ==============================================================================
-- LAYER 7: META-MEMORY (Self-Awareness)
-- Knowledge about what we know - coverage, confidence, gaps
-- ==============================================================================

-- Domain coverage tracking
CREATE TABLE IF NOT EXISTS memory_coverage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL UNIQUE,        -- react|authentication|testing|graphql|etc
    category TEXT NOT NULL,             -- technology|pattern|project-area|skill

    -- Coverage metrics
    memory_count INTEGER DEFAULT 0,     -- How many memories in this domain
    episodic_count INTEGER DEFAULT 0,   -- Events related to this
    procedural_count INTEGER DEFAULT 0, -- Procedures for this
    entity_count INTEGER DEFAULT 0,     -- Entities in this domain

    -- Quality metrics
    avg_confidence REAL DEFAULT 0.0,
    avg_usefulness REAL DEFAULT 0.0,
    last_updated INTEGER,

    -- Gap analysis
    gaps TEXT,                          -- JSON array of identified knowledge gaps
    strength_areas TEXT,                -- JSON array of strong areas

    -- Metadata
    first_encounter INTEGER,            -- When we first learned about this
    expertise_level TEXT DEFAULT 'beginner'  -- beginner|intermediate|advanced|expert
);

-- Memory quality tracking (extends existing optimization)
CREATE TABLE IF NOT EXISTS memory_quality_tracking (
    memory_id INTEGER PRIMARY KEY,
    memory_layer TEXT NOT NULL,         -- semantic|episodic|procedural|prospective|graph

    -- Usage metrics
    access_count INTEGER DEFAULT 0,
    last_accessed INTEGER,
    useful_count INTEGER DEFAULT 0,     -- Times marked as useful

    -- Quality scores
    usefulness_score REAL DEFAULT 0.0,  -- 0-1, how useful this memory is
    confidence REAL DEFAULT 1.0,        -- 0-1, how confident we are
    relevance_decay REAL DEFAULT 1.0,   -- 0-1, time-based decay

    -- Provenance
    source TEXT DEFAULT 'user',         -- user|inferred|learned|imported
    verified BOOLEAN DEFAULT 0,         -- Has this been verified?

    -- Composite quality score (computed)
    quality_score REAL GENERATED ALWAYS AS (
        (usefulness_score * 0.4 + confidence * 0.3 + relevance_decay * 0.3)
    ) STORED
);

-- Cross-project knowledge transfer tracking
CREATE TABLE IF NOT EXISTS knowledge_transfer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_project_id INTEGER NOT NULL,
    to_project_id INTEGER NOT NULL,
    knowledge_item_id INTEGER NOT NULL,     -- ID in respective layer table
    knowledge_layer TEXT NOT NULL,
    transferred_at INTEGER NOT NULL,
    applicability_score REAL DEFAULT 0.0,   -- How well it transferred
    FOREIGN KEY (from_project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (to_project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_coverage_domain ON memory_coverage(domain);
CREATE INDEX IF NOT EXISTS idx_quality_layer ON memory_quality_tracking(memory_layer);
CREATE INDEX IF NOT EXISTS idx_quality_score ON memory_quality_tracking(quality_score DESC);

-- ==============================================================================
-- LAYER 8: CONSOLIDATION SYSTEM
-- Background optimization and learning
-- ==============================================================================

-- Consolidation runs
CREATE TABLE IF NOT EXISTS consolidation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,                 -- NULL for global consolidation
    started_at INTEGER NOT NULL,
    completed_at INTEGER,
    status TEXT DEFAULT 'running',      -- running|completed|failed

    -- What was done
    memories_scored INTEGER DEFAULT 0,
    memories_pruned INTEGER DEFAULT 0,
    patterns_extracted INTEGER DEFAULT 0,
    conflicts_resolved INTEGER DEFAULT 0,

    -- Quality improvements
    avg_quality_before REAL,
    avg_quality_after REAL,

    -- Metadata
    consolidation_type TEXT DEFAULT 'scheduled',  -- scheduled|manual|triggered
    notes TEXT,

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Pattern extraction results
CREATE TABLE IF NOT EXISTS extracted_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    consolidation_run_id INTEGER NOT NULL,
    pattern_type TEXT NOT NULL,         -- workflow|anti-pattern|best-practice|relationship
    pattern_content TEXT NOT NULL,
    confidence REAL DEFAULT 0.0,
    occurrences INTEGER DEFAULT 1,      -- How many times we've seen this

    -- Source events that led to this pattern
    source_events TEXT,                 -- JSON array of event IDs

    -- Actions taken
    created_procedure BOOLEAN DEFAULT 0,
    created_semantic_memory BOOLEAN DEFAULT 0,
    updated_entity BOOLEAN DEFAULT 0,

    FOREIGN KEY (consolidation_run_id) REFERENCES consolidation_runs(id) ON DELETE CASCADE
);

-- Conflict tracking and resolution
CREATE TABLE IF NOT EXISTS memory_conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discovered_at INTEGER NOT NULL,
    resolved_at INTEGER,
    status TEXT DEFAULT 'pending',      -- pending|resolved|ignored

    -- Conflicting items
    item1_layer TEXT NOT NULL,
    item1_id INTEGER NOT NULL,
    item2_layer TEXT NOT NULL,
    item2_id INTEGER NOT NULL,

    -- Conflict details
    conflict_type TEXT NOT NULL,        -- contradiction|duplication|inconsistency
    description TEXT,

    -- Resolution
    resolution_strategy TEXT,           -- timestamp_precedence|merge|user_input|keep_both
    resolution_notes TEXT,

    -- Metadata
    severity TEXT DEFAULT 'medium'      -- low|medium|high|critical
);

CREATE INDEX IF NOT EXISTS idx_consolidation_project ON consolidation_runs(project_id);
CREATE INDEX IF NOT EXISTS idx_consolidation_time ON consolidation_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_conflicts_status ON memory_conflicts(status);

-- ==============================================================================
-- VIEWS FOR CONVENIENT QUERIES
-- ==============================================================================

-- Unified memory view across all layers
CREATE VIEW IF NOT EXISTS unified_memory_view AS
SELECT
    'semantic' as layer,
    id,
    project_id,
    content,
    memory_type as type,
    created_at,
    NULL as timestamp,
    usefulness_score as quality_score
FROM memories

UNION ALL

SELECT
    'episodic' as layer,
    id,
    project_id,
    content,
    event_type as type,
    timestamp as created_at,
    timestamp,
    confidence as quality_score
FROM episodic_events

UNION ALL

SELECT
    'procedural' as layer,
    id,
    NULL as project_id,
    name as content,
    category as type,
    created_at,
    last_used as timestamp,
    success_rate as quality_score
FROM procedures;

-- Project health dashboard
CREATE VIEW IF NOT EXISTS project_health AS
SELECT
    p.id,
    p.name,
    p.path,
    p.memory_count as semantic_memories,
    COUNT(DISTINCT e.id) as episodic_events,
    COUNT(DISTINCT t.id) as active_tasks,
    COUNT(DISTINCT ent.id) as entities,
    MAX(e.timestamp) as last_activity,
    AVG(m.usefulness_score) as avg_memory_quality
FROM projects p
LEFT JOIN memories m ON p.id = m.project_id
LEFT JOIN episodic_events e ON p.id = e.project_id
LEFT JOIN prospective_tasks t ON p.id = t.project_id AND t.status IN ('pending', 'active')
LEFT JOIN entities ent ON p.id = ent.project_id
GROUP BY p.id;

-- ==============================================================================
-- INITIALIZATION AND MIGRATION
-- ==============================================================================

-- Version tracking for schema migrations
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at INTEGER NOT NULL,
    description TEXT
);

-- Record this schema version
INSERT OR IGNORE INTO schema_version (version, applied_at, description)
VALUES (1, strftime('%s', 'now'), 'Initial 8-layer unified memory system');
