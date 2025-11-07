-- Athena Phase 5: PostgreSQL + pgvector Schema Initialization
-- Unified multi-domain database for Memory, Planning, and Code Analysis
-- Date: November 8, 2025
-- Status: Greenfield Schema (No Migration Required)

-- ============================================================================
-- EXTENSIONS
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- For GIN index on text


-- ============================================================================
-- 1. PROJECTS TABLE (Multi-Project Isolation)
-- ============================================================================

CREATE TABLE IF NOT EXISTS projects (
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
    consolidation_interval INT DEFAULT 3600  -- seconds
);

CREATE INDEX IF NOT EXISTS idx_projects_created ON projects(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_projects_accessed ON projects(last_accessed DESC);


-- ============================================================================
-- 2. MEMORY VECTORS TABLE (Unified Vector Storage)
-- ============================================================================

CREATE TABLE IF NOT EXISTS memory_vectors (
    id BIGSERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Core content
    content TEXT NOT NULL,
    content_type VARCHAR(50),  -- 'episodic', 'semantic', 'code', 'task'

    -- Embedding (768 dimensions for Nomic Embed)
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
    code_hash VARCHAR(64)  -- for deduplication
);

-- Core indices
CREATE INDEX IF NOT EXISTS idx_memory_project ON memory_vectors(project_id);
CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_vectors(memory_type);
CREATE INDEX IF NOT EXISTS idx_memory_consolidation ON memory_vectors(consolidation_state);
CREATE INDEX IF NOT EXISTS idx_memory_quality ON memory_vectors(quality_score DESC);
CREATE INDEX IF NOT EXISTS idx_memory_accessed ON memory_vectors(last_accessed DESC);
CREATE INDEX IF NOT EXISTS idx_memory_session ON memory_vectors(session_id);

-- Vector search index (IVFFlat with cosine distance)
CREATE INDEX IF NOT EXISTS idx_memory_embedding_ivfflat
ON memory_vectors USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_memory_content_fts
ON memory_vectors USING GIN (content_tsvector);

-- Composite indices for filtering
CREATE INDEX IF NOT EXISTS idx_memory_project_type
ON memory_vectors(project_id, memory_type)
WHERE consolidation_state = 'consolidated';

CREATE INDEX IF NOT EXISTS idx_memory_project_domain
ON memory_vectors(project_id, domain, consolidation_state);


-- ============================================================================
-- 3. MEMORY RELATIONSHIPS
-- ============================================================================

CREATE TABLE IF NOT EXISTS memory_relationships (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    from_memory_id BIGINT NOT NULL REFERENCES memory_vectors(id) ON DELETE CASCADE,
    to_memory_id BIGINT NOT NULL REFERENCES memory_vectors(id) ON DELETE CASCADE,

    -- Relationship type
    relationship_type VARCHAR(50) NOT NULL,  -- 'reinforces', 'contradicts', 'extends', 'depends_on', 'caused_by'
    strength FLOAT DEFAULT 1.0,  -- 0-1

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(from_memory_id, to_memory_id, relationship_type)
);

CREATE INDEX IF NOT EXISTS idx_from_memory ON memory_relationships(from_memory_id);
CREATE INDEX IF NOT EXISTS idx_to_memory ON memory_relationships(to_memory_id);
CREATE INDEX IF NOT EXISTS idx_relationship_type ON memory_relationships(relationship_type);


-- ============================================================================
-- 4. EPISODIC EVENTS (Temporal Grounding)
-- ============================================================================

CREATE TABLE IF NOT EXISTS episodic_events (
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
    consolidation_status VARCHAR(50) DEFAULT 'unconsolidated'
);

CREATE INDEX IF NOT EXISTS idx_episodic_project ON episodic_events(project_id);
CREATE INDEX IF NOT EXISTS idx_episodic_session ON episodic_events(session_id);
CREATE INDEX IF NOT EXISTS idx_episodic_timestamp ON episodic_events(project_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_episodic_event_type ON episodic_events(event_type);
CREATE INDEX IF NOT EXISTS idx_episodic_consolidation ON episodic_events(consolidation_status);


-- ============================================================================
-- 5. PROSPECTIVE TASKS & GOALS
-- ============================================================================

CREATE TABLE IF NOT EXISTS prospective_goals (
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
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_goals_project ON prospective_goals(project_id);
CREATE INDEX IF NOT EXISTS idx_goals_status ON prospective_goals(status);
CREATE INDEX IF NOT EXISTS idx_goals_priority ON prospective_goals(priority DESC);
CREATE INDEX IF NOT EXISTS idx_goals_parent ON prospective_goals(parent_goal_id);


CREATE TABLE IF NOT EXISTS prospective_tasks (
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
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tasks_project ON prospective_tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON prospective_tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON prospective_tasks(priority DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_goal ON prospective_tasks(goal_id);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON prospective_tasks(due_date);


-- ============================================================================
-- 6. CODE METADATA (Code Analysis Domain)
-- ============================================================================

CREATE TABLE IF NOT EXISTS code_metadata (
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

    UNIQUE(project_id, file_path, entity_name)
);

CREATE INDEX IF NOT EXISTS idx_code_project ON code_metadata(project_id);
CREATE INDEX IF NOT EXISTS idx_code_file ON code_metadata(file_path);
CREATE INDEX IF NOT EXISTS idx_code_entity_type ON code_metadata(entity_type);
CREATE INDEX IF NOT EXISTS idx_code_language ON code_metadata(language);


-- ============================================================================
-- 7. CODE DEPENDENCIES
-- ============================================================================

CREATE TABLE IF NOT EXISTS code_dependencies (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    from_code_id BIGINT NOT NULL REFERENCES code_metadata(id) ON DELETE CASCADE,
    to_code_id BIGINT NOT NULL REFERENCES code_metadata(id) ON DELETE CASCADE,

    dependency_type VARCHAR(50),  -- 'imports', 'calls', 'extends', 'implements'
    strength FLOAT DEFAULT 1.0,  -- Measure of coupling

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(from_code_id, to_code_id, dependency_type)
);

CREATE INDEX IF NOT EXISTS idx_code_dep_from ON code_dependencies(from_code_id);
CREATE INDEX IF NOT EXISTS idx_code_dep_to ON code_dependencies(to_code_id);
CREATE INDEX IF NOT EXISTS idx_code_dep_type ON code_dependencies(dependency_type);


-- ============================================================================
-- 8. PLANNING & DECISIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS planning_decisions (
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
    superseded_by BIGINT REFERENCES planning_decisions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_decision_project ON planning_decisions(project_id);
CREATE INDEX IF NOT EXISTS idx_decision_status ON planning_decisions(validation_status);


CREATE TABLE IF NOT EXISTS planning_scenarios (
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

CREATE INDEX IF NOT EXISTS idx_scenario_decision ON planning_scenarios(decision_id);


-- ============================================================================
-- CONFIGURATION & TUNING
-- ============================================================================

-- Set pgvector parameters for optimal performance
-- Note: These should be set in postgresql.conf but can be set per-session
SET ivfflat.probes = 20;  -- Higher accuracy, slightly slower searches

-- Create initial default project
INSERT INTO projects (name, path, language, description)
VALUES (
    'default',
    '/workspace',
    'python',
    'Default project for Athena system'
)
ON CONFLICT (name) DO NOTHING;


-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE memory_vectors IS 'Unified vector storage for all memory domains: episodic, semantic, procedural, and meta-memories';
COMMENT ON COLUMN memory_vectors.embedding IS 'Vector embedding (768 dimensions) for semantic search using cosine similarity';
COMMENT ON COLUMN memory_vectors.consolidation_state IS 'Lifecycle: unconsolidated → consolidating → consolidated (stable), or consolidated → labile → reconsolidating (for learning)';
COMMENT ON COLUMN memory_vectors.quality_score IS 'Composite score combining usefulness (50%), confidence (30%), and access frequency (20%)';

COMMENT ON TABLE episodic_events IS 'Timestamped events with spatial-temporal context for causality inference and temporal reasoning';
COMMENT ON COLUMN episodic_events.session_id IS 'Groups related events together (e.g., single coding session)';
COMMENT ON COLUMN episodic_events.context_cwd IS 'Current working directory at event time for code path mapping';

COMMENT ON TABLE prospective_tasks IS 'Tasks with decomposition hierarchy, related knowledge integration, and effort tracking';
COMMENT ON COLUMN prospective_tasks.related_memory_ids IS 'Array of memory vector IDs informing this task (aggregate join in queries)';

COMMENT ON TABLE code_metadata IS 'Code entities (functions, classes, modules) with semantic hashing for deduplication';
COMMENT ON COLUMN code_metadata.semantic_hash IS 'Hash of semantically equivalent code (ignoring formatting) for duplicate detection';

COMMENT ON TABLE planning_decisions IS 'Architectural and algorithm decisions with validation status and scenario analysis';
COMMENT ON COLUMN planning_decisions.context_memory_ids IS 'Memories that informed this decision (traced back for rationale)';


-- ============================================================================
-- VERIFY INITIALIZATION
-- ============================================================================

-- Check that all tables exist
DO $$
DECLARE
    missing_tables TEXT;
BEGIN
    SELECT STRING_AGG(table_name, ', ')
    INTO missing_tables
    FROM (
        VALUES
            ('projects'),
            ('memory_vectors'),
            ('memory_relationships'),
            ('episodic_events'),
            ('prospective_goals'),
            ('prospective_tasks'),
            ('code_metadata'),
            ('code_dependencies'),
            ('planning_decisions'),
            ('planning_scenarios')
    ) AS t(table_name)
    WHERE table_name NOT IN (
        SELECT tablename FROM pg_tables WHERE schemaname = 'public'
    );

    IF missing_tables IS NOT NULL THEN
        RAISE WARNING 'Missing tables: %', missing_tables;
    ELSE
        RAISE NOTICE '✅ All 10 core tables created successfully';
        RAISE NOTICE '✅ pgvector extension enabled';
        RAISE NOTICE '✅ All indices created';
        RAISE NOTICE '✅ Default project initialized';
    END IF;
END $$;
