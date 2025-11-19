-- Migration: m001_initial_8layers.sql
-- Description: Initial 8-layer memory system schema for Athena
-- Created: 2025-11-19
-- Status: Production

-- =============================================================================
-- LAYER 0: CORE INFRASTRUCTURE
-- =============================================================================

-- Projects (multi-project isolation)
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    path TEXT UNIQUE NOT NULL,
    description TEXT,
    language VARCHAR(50),
    framework VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    last_accessed TIMESTAMP DEFAULT NOW(),
    last_modified TIMESTAMP DEFAULT NOW(),
    memory_count INT DEFAULT 0,
    total_events INT DEFAULT 0,
    task_count INT DEFAULT 0,
    embedding_dim INT DEFAULT 768,
    consolidation_interval INT DEFAULT 3600
);

-- =============================================================================
-- LAYER 1: EPISODIC MEMORY (Events with spatial-temporal grounding)
-- =============================================================================

-- Core episodic events table
CREATE TABLE IF NOT EXISTS episodic_events (
    id BIGSERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    memory_vector_id BIGINT REFERENCES semantic_memories(id) ON DELETE SET NULL,
    entity_id INT REFERENCES entities(id) ON DELETE SET NULL,
    session_id VARCHAR(255) NOT NULL,
    timestamp BIGINT NOT NULL,
    duration_ms INT,
    event_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    outcome TEXT,
    context_cwd TEXT,
    context_files TEXT[],
    context_task VARCHAR(255),
    context_phase VARCHAR(50),
    context_branch VARCHAR(255),
    files_changed INT DEFAULT 0,
    lines_added INT DEFAULT 0,
    lines_deleted INT DEFAULT 0,
    learned TEXT,
    surprise_score FLOAT,
    surprise_normalized FLOAT,
    surprise_coherence FLOAT,
    confidence FLOAT DEFAULT 1.0,
    -- Evidence tracking (what kind of knowledge is this?)
    evidence_type VARCHAR(50) DEFAULT 'observed',
    source_id VARCHAR(500),
    evidence_quality FLOAT DEFAULT 1.0,
    -- Lifecycle system for consolidation tracking
    lifecycle_status VARCHAR(50) DEFAULT 'active',
    consolidation_score FLOAT DEFAULT 0.0,
    last_activation TIMESTAMP DEFAULT NOW(),
    activation_count INT DEFAULT 0,
    embedding vector(768)
);

-- Event source cursor tracking
CREATE TABLE IF NOT EXISTS event_source_cursors (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source_type VARCHAR(100) NOT NULL,
    source_name VARCHAR(255) NOT NULL,
    cursor_value TEXT NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, source_type, source_name)
);

-- Working memory (short-term focus)
CREATE TABLE IF NOT EXISTS working_memory (
    id BIGSERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    session_id VARCHAR(255) NOT NULL,
    memory_id BIGINT NOT NULL REFERENCES episodic_events(id) ON DELETE CASCADE,
    priority_score FLOAT DEFAULT 0.5,
    activation_level FLOAT DEFAULT 1.0,
    last_activated TIMESTAMP DEFAULT NOW(),
    activation_count INT DEFAULT 1,
    time_window_start TIMESTAMP,
    time_window_end TIMESTAMP
);

-- Consolidation triggers
CREATE TABLE IF NOT EXISTS consolidation_triggers (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    trigger_type VARCHAR(100) NOT NULL,
    trigger_condition TEXT,
    target_layer VARCHAR(50),
    enabled BOOLEAN DEFAULT TRUE,
    last_fired TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =============================================================================
-- LAYER 2: SEMANTIC MEMORY (Vector + hybrid search)
-- =============================================================================

-- Memory vectors table (unified semantic memory)
CREATE TABLE IF NOT EXISTS semantic_memories (
    id BIGSERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    content_type VARCHAR(50),
    embedding vector(768) NOT NULL,
    content_tsvector tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    memory_type VARCHAR(50) NOT NULL,
    domain VARCHAR(100),
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_accessed TIMESTAMP DEFAULT NOW(),
    last_retrieved TIMESTAMP,
    access_count INT DEFAULT 0,
    usefulness_score FLOAT DEFAULT 0.0,
    confidence FLOAT DEFAULT 1.0,
    quality_score FLOAT GENERATED ALWAYS AS (
        (0.5 * usefulness_score + 0.3 * confidence + 0.2 * LEAST(access_count::float / 100, 1.0))
    ) STORED,
    consolidation_state VARCHAR(50) DEFAULT 'unconsolidated',
    consolidated_at TIMESTAMP,
    superseded_by BIGINT REFERENCES semantic_memories(id) ON DELETE SET NULL,
    version INT DEFAULT 1,
    session_id VARCHAR(255),
    event_type VARCHAR(50),
    code_language VARCHAR(50),
    code_hash VARCHAR(64)
);

-- Memory relationships (semantic links)
CREATE TABLE IF NOT EXISTS memory_relationships (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    from_memory_id BIGINT NOT NULL REFERENCES semantic_memories(id) ON DELETE CASCADE,
    to_memory_id BIGINT NOT NULL REFERENCES semantic_memories(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,
    strength FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(from_memory_id, to_memory_id, relationship_type)
);

-- =============================================================================
-- LAYER 3: PROCEDURAL MEMORY (Learned workflows)
-- =============================================================================

-- Procedures (learned workflows)
CREATE TABLE IF NOT EXISTS procedures (
    id BIGSERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    learned_from_event_id BIGINT REFERENCES episodic_events(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    description TEXT,
    steps TEXT,
    inputs TEXT[],
    outputs TEXT[],
    success_rate FLOAT DEFAULT 0.0,
    execution_count INT DEFAULT 0,
    last_executed TIMESTAMP,
    created_by VARCHAR(50) DEFAULT 'manual',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, name)
);

-- =============================================================================
-- LAYER 4: PROSPECTIVE MEMORY (Goals and tasks)
-- =============================================================================

-- Prospective goals
CREATE TABLE IF NOT EXISTS prospective_goals (
    id BIGSERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    priority INT DEFAULT 5,
    status VARCHAR(50) DEFAULT 'active',
    completion_percentage INT DEFAULT 0,
    estimated_completion_date DATE,
    parent_goal_id BIGINT REFERENCES prospective_goals(id) ON DELETE SET NULL,
    related_memory_ids BIGINT[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Prospective tasks
CREATE TABLE IF NOT EXISTS prospective_tasks (
    id BIGSERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    priority INT DEFAULT 5,
    goal_id BIGINT REFERENCES prospective_goals(id) ON DELETE SET NULL,
    parent_task_id BIGINT REFERENCES prospective_tasks(id) ON DELETE SET NULL,
    learned_pattern_id INT REFERENCES extracted_patterns(id) ON DELETE SET NULL,
    estimated_effort_hours FLOAT,
    actual_effort_hours FLOAT,
    due_date DATE,
    related_memory_ids BIGINT[] DEFAULT '{}',
    related_code_ids BIGINT[] DEFAULT '{}',
    completion_percentage INT DEFAULT 0,
    success_rate FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- =============================================================================
-- LAYER 5: KNOWLEDGE GRAPH (Entity relationships)
-- =============================================================================

-- Entities (concepts in knowledge graph)
CREATE TABLE IF NOT EXISTS entities (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    entity_type VARCHAR(100) NOT NULL,
    entity_name TEXT NOT NULL,
    description TEXT,
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, entity_type, entity_name)
);

-- =============================================================================
-- LAYER 6: META-MEMORY (Quality & cognitive metrics)
-- =============================================================================

-- Agent domain expertise
CREATE TABLE IF NOT EXISTS agent_domain_expertise (
    id BIGSERIAL PRIMARY KEY,
    agent_name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) NOT NULL,
    total_findings INT DEFAULT 0,
    avg_credibility FLOAT DEFAULT 0.0,
    successful_tasks INT DEFAULT 0,
    confidence FLOAT DEFAULT 0.5,
    last_updated TIMESTAMP DEFAULT NOW(),
    UNIQUE(agent_name, domain)
);

-- Source domain credibility
CREATE TABLE IF NOT EXISTS source_domain_credibility (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(255) NOT NULL,
    domain VARCHAR(255) NOT NULL,
    avg_credibility FLOAT NOT NULL,
    finding_count INT NOT NULL,
    cross_validation_rate FLOAT,
    temporal_trend FLOAT,
    confidence FLOAT DEFAULT 0.5,
    last_updated TIMESTAMP DEFAULT NOW(),
    UNIQUE(source, domain)
);

-- Quality thresholds
CREATE TABLE IF NOT EXISTS quality_thresholds (
    id BIGSERIAL PRIMARY KEY,
    domain VARCHAR(255) NOT NULL UNIQUE,
    threshold_optimal FLOAT DEFAULT 0.75,
    threshold_strict FLOAT DEFAULT 0.85,
    threshold_lenient FLOAT DEFAULT 0.60,
    findings_tested INT DEFAULT 0,
    retention_rate_optimal FLOAT,
    last_updated TIMESTAMP DEFAULT NOW()
);

-- =============================================================================
-- LAYER 7: CONSOLIDATION (Pattern extraction & learning)
-- =============================================================================

-- Consolidation runs
CREATE TABLE IF NOT EXISTS consolidation_runs (
    id SERIAL PRIMARY KEY,
    project_id INTEGER,
    started_at INTEGER NOT NULL,
    completed_at INTEGER,
    status TEXT DEFAULT 'running',
    memories_scored INTEGER DEFAULT 0,
    memories_pruned INTEGER DEFAULT 0,
    patterns_extracted INTEGER DEFAULT 0,
    conflicts_resolved INTEGER DEFAULT 0,
    avg_quality_before REAL,
    avg_quality_after REAL,
    compression_ratio REAL,
    retrieval_recall REAL,
    pattern_consistency REAL,
    avg_information_density REAL,
    overall_quality_score REAL
);

-- Extracted patterns
CREATE TABLE IF NOT EXISTS extracted_patterns (
    id SERIAL PRIMARY KEY,
    consolidation_run_id INTEGER NOT NULL,
    pattern_type TEXT NOT NULL,
    pattern_content TEXT NOT NULL,
    confidence REAL DEFAULT 0.0,
    occurrences INTEGER DEFAULT 1,
    source_events TEXT,
    created_procedure BOOLEAN DEFAULT FALSE,
    created_semantic_memory BOOLEAN DEFAULT FALSE,
    updated_entity BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (consolidation_run_id) REFERENCES consolidation_runs(id) ON DELETE CASCADE
);

-- Memory conflicts
CREATE TABLE IF NOT EXISTS memory_conflicts (
    id SERIAL PRIMARY KEY,
    discovered_at INTEGER NOT NULL,
    resolved_at INTEGER,
    status TEXT DEFAULT 'pending',
    item1_layer TEXT NOT NULL,
    item1_id INTEGER NOT NULL,
    item2_layer TEXT NOT NULL,
    item2_id INTEGER NOT NULL,
    conflict_type TEXT NOT NULL,
    description TEXT,
    resolution_strategy TEXT,
    resolution_notes TEXT
);

-- Research patterns (Phase 3.3)
CREATE TABLE IF NOT EXISTS research_patterns (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES research_tasks(id) ON DELETE CASCADE,
    pattern_type VARCHAR(100) NOT NULL,
    pattern_content TEXT NOT NULL,
    confidence FLOAT NOT NULL,
    metrics JSONB DEFAULT '{}',
    source_findings BIGINT[] DEFAULT '{}',
    finding_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =============================================================================
-- LAYER 8: SUPPORTING INFRASTRUCTURE (Planning, Code analysis, Research)
-- =============================================================================

-- Code metadata
CREATE TABLE IF NOT EXISTS code_metadata (
    id BIGSERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    memory_vector_id BIGINT NOT NULL REFERENCES semantic_memories(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    language VARCHAR(50),
    entity_type VARCHAR(50),
    entity_name VARCHAR(255),
    start_line INT,
    end_line INT,
    signature TEXT,
    docstring TEXT,
    semantic_hash VARCHAR(64),
    dependencies TEXT[],
    dependents TEXT[],
    cyclomatic_complexity INT,
    lines_of_code INT,
    created_at TIMESTAMP DEFAULT NOW(),
    last_analyzed_at TIMESTAMP,
    UNIQUE(project_id, file_path, entity_name)
);

-- Code dependencies
CREATE TABLE IF NOT EXISTS code_dependencies (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    from_code_id BIGINT NOT NULL REFERENCES code_metadata(id) ON DELETE CASCADE,
    to_code_id BIGINT NOT NULL REFERENCES code_metadata(id) ON DELETE CASCADE,
    dependency_type VARCHAR(50),
    strength FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(from_code_id, to_code_id, dependency_type)
);

-- Planning decisions
CREATE TABLE IF NOT EXISTS planning_decisions (
    id BIGSERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    decision_type VARCHAR(50),
    title VARCHAR(255) NOT NULL,
    rationale TEXT,
    context_memory_ids BIGINT[] DEFAULT '{}',
    alternatives TEXT[],
    validation_status VARCHAR(50) DEFAULT 'pending',
    validation_confidence FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    validated_at TIMESTAMP,
    superseded_by BIGINT REFERENCES planning_decisions(id) ON DELETE SET NULL
);

-- Planning scenarios
CREATE TABLE IF NOT EXISTS planning_scenarios (
    id BIGSERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    decision_id BIGINT REFERENCES planning_decisions(id) ON DELETE CASCADE,
    scenario_type VARCHAR(50),
    scenario_name VARCHAR(255),
    description TEXT,
    assumptions TEXT[],
    expected_outcomes TEXT[],
    impact_assessment TEXT,
    risk_level VARCHAR(50),
    probability FLOAT,
    testing_status VARCHAR(50) DEFAULT 'not_tested',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Research tasks
CREATE TABLE IF NOT EXISTS research_tasks (
    id BIGSERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    research_goal VARCHAR(255) NOT NULL,
    research_domain VARCHAR(255) NOT NULL,
    research_query TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    priority INT DEFAULT 5,
    start_time TIMESTAMP DEFAULT NOW(),
    end_time TIMESTAMP,
    findings_found INT DEFAULT 0,
    patterns_extracted INT DEFAULT 0,
    total_findings INT DEFAULT 0,
    avg_credibility FLOAT DEFAULT 0.0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Search strategies
CREATE TABLE IF NOT EXISTS search_strategies (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) NOT NULL,
    description TEXT,
    recommended_sources TEXT[],
    excluded_sources TEXT[],
    expected_quality FLOAT DEFAULT 0.8,
    expected_findings_per_query INT DEFAULT 50,
    success_count INT DEFAULT 0,
    failure_count INT DEFAULT 0,
    created_from_patterns BIGINT[],
    procedure_id BIGINT REFERENCES procedures(id) ON DELETE SET NULL,
    confidence FLOAT DEFAULT 0.5,
    last_updated TIMESTAMP DEFAULT NOW(),
    UNIQUE(domain, name)
);

-- Research graph entities
CREATE TABLE IF NOT EXISTS research_graph_entities (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES research_tasks(id) ON DELETE CASCADE,
    entity_name TEXT NOT NULL,
    entity_type VARCHAR(100),
    mentioned_in_findings BIGINT[],
    frequency INT DEFAULT 1,
    confidence FLOAT DEFAULT 0.8,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Research graph relations
CREATE TABLE IF NOT EXISTS research_graph_relations (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES research_tasks(id) ON DELETE CASCADE,
    source_entity TEXT NOT NULL,
    relation_type VARCHAR(100) NOT NULL,
    target_entity TEXT NOT NULL,
    strength FLOAT DEFAULT 0.8,
    source_findings BIGINT[],
    confidence FLOAT DEFAULT 0.8,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Research consolidation runs
CREATE TABLE IF NOT EXISTS research_consolidation_runs (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL UNIQUE REFERENCES research_tasks(id) ON DELETE CASCADE,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'running',
    patterns_extracted INT DEFAULT 0,
    procedures_created INT DEFAULT 0,
    entities_created INT DEFAULT 0,
    relations_created INT DEFAULT 0,
    expertise_updates INT DEFAULT 0,
    strategy_improvements INT DEFAULT 0,
    error_message TEXT
);

-- =============================================================================
-- INDICES FOR PERFORMANCE OPTIMIZATION
-- =============================================================================

-- pgvector extension (optional)
CREATE EXTENSION IF NOT EXISTS vector;

-- Projects indices
CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);
CREATE INDEX IF NOT EXISTS idx_projects_path ON projects(path);

-- Episodic events indices
CREATE INDEX IF NOT EXISTS idx_episodic_project ON episodic_events(project_id);
CREATE INDEX IF NOT EXISTS idx_episodic_session ON episodic_events(session_id);
CREATE INDEX IF NOT EXISTS idx_episodic_timestamp ON episodic_events(project_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_episodic_event_type ON episodic_events(event_type);
CREATE INDEX IF NOT EXISTS idx_episodic_lifecycle ON episodic_events(lifecycle_status);
CREATE INDEX IF NOT EXISTS idx_episodic_temporal ON episodic_events(project_id, timestamp DESC);

-- Semantic memory indices
CREATE INDEX IF NOT EXISTS idx_memory_project ON semantic_memories(project_id);
CREATE INDEX IF NOT EXISTS idx_memory_type ON semantic_memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_memory_consolidation ON semantic_memories(consolidation_state);
CREATE INDEX IF NOT EXISTS idx_memory_quality ON semantic_memories(quality_score DESC);
CREATE INDEX IF NOT EXISTS idx_memory_accessed ON semantic_memories(last_accessed DESC);
CREATE INDEX IF NOT EXISTS idx_memory_session ON semantic_memories(session_id);
CREATE INDEX IF NOT EXISTS idx_memory_project_type ON semantic_memories(project_id, memory_type)
    WHERE consolidation_state = 'consolidated';
CREATE INDEX IF NOT EXISTS idx_memory_project_domain ON semantic_memories(project_id, domain, consolidation_state);

-- Vector search indices (if pgvector available)
CREATE INDEX IF NOT EXISTS idx_memory_embedding_ivfflat ON semantic_memories USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
CREATE INDEX IF NOT EXISTS episodic_events_embedding_ivfflat ON episodic_events USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_memory_content_fts ON semantic_memories USING GIN (content_tsvector);

-- Task and goal indices
CREATE INDEX IF NOT EXISTS idx_tasks_project ON prospective_tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON prospective_tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON prospective_tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_goals_project ON prospective_goals(project_id);
CREATE INDEX IF NOT EXISTS idx_goals_status ON prospective_goals(status);
CREATE INDEX IF NOT EXISTS idx_prospective_active ON prospective_tasks(status, priority, due_date);

-- Code indices
CREATE INDEX IF NOT EXISTS idx_code_project ON code_metadata(project_id);
CREATE INDEX IF NOT EXISTS idx_code_file ON code_metadata(file_path);
CREATE INDEX IF NOT EXISTS idx_code_entity_type ON code_metadata(entity_type);
CREATE INDEX IF NOT EXISTS idx_code_dep_from ON code_dependencies(from_code_id);
CREATE INDEX IF NOT EXISTS idx_code_dep_to ON code_dependencies(to_code_id);

-- Planning indices
CREATE INDEX IF NOT EXISTS idx_decision_project ON planning_decisions(project_id);
CREATE INDEX IF NOT EXISTS idx_decision_status ON planning_decisions(validation_status);

-- Entity indices
CREATE INDEX IF NOT EXISTS idx_entities_project ON entities(project_id);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_project_type ON entities(project_id, entity_type);

-- Research indices
CREATE INDEX IF NOT EXISTS idx_research_tasks_project ON research_tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_research_tasks_status ON research_tasks(status);
CREATE INDEX IF NOT EXISTS idx_research_tasks_domain ON research_tasks(research_domain);
CREATE INDEX IF NOT EXISTS idx_research_patterns_task ON research_patterns(task_id);
CREATE INDEX IF NOT EXISTS idx_research_patterns_type ON research_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_agent_expertise ON agent_domain_expertise(agent_name, domain);
CREATE INDEX IF NOT EXISTS idx_source_credibility ON source_domain_credibility(source, domain);
CREATE INDEX IF NOT EXISTS idx_quality_thresholds ON quality_thresholds(domain);
CREATE INDEX IF NOT EXISTS idx_search_strategies ON search_strategies(domain);
CREATE INDEX IF NOT EXISTS idx_research_entities ON research_graph_entities(task_id, entity_type);
CREATE INDEX IF NOT EXISTS idx_research_relations ON research_graph_relations(task_id);
CREATE INDEX IF NOT EXISTS idx_consolidation_runs ON research_consolidation_runs(task_id, status);
