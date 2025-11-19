-- Migration m002: Additional tables from removed schema methods
--
-- This migration creates tables that were previously defined in scattered _ensure_schema()
-- and _init_schema() methods across the codebase. These methods have been removed as part
-- of the schema cleanup initiative, consolidating all schema definitions into migrations.
--
-- Tables created:
-- 1. procedure_versions - Track procedure versions for comparison and rollback
-- 2. task_dependencies - Task blocking relationships and dependency chains
-- 3. estimate_accuracy - Track estimate accuracy per task type
-- 4. attention_items - Attention budget and working memory management
-- 5. workflow_patterns - Workflow pattern storage and analysis
-- 6. session_contexts - Session context management
-- 7. todowrite_plans - TodoWrite-synced plan storage
-- 8. learning_outcomes - Agent decision outcomes and success rates
-- 9. consolidation_runs - Consolidation run history and metrics
-- 10. symbol_store - Symbol storage for code indexing
-- 11. memory_versions - Memory versioning for Zettelkasten evolution
-- 12. memory_attributes - Memory attributes for evolution tracking
-- 13. hierarchical_index - Hierarchical indexing for memories
-- 14. code_elements - Code element indexing
-- 15. conflict_resolutions - Conflict resolution tracking
-- 16. central_executive_state - Central executive working memory state

-- ============================================================================
-- PROCEDURAL LAYER TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS procedure_versions (
    id INTEGER PRIMARY KEY,
    procedure_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    extracted_from TEXT,
    effectiveness_score REAL DEFAULT 0.0,
    tags TEXT,
    active BOOLEAN DEFAULT FALSE,
    rollback_to INTEGER,
    procedure_snapshot TEXT,
    FOREIGN KEY (procedure_id) REFERENCES procedures(id),
    UNIQUE(procedure_id, version)
);

-- ============================================================================
-- PROSPECTIVE LAYER TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS task_dependencies (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    from_task_id INTEGER NOT NULL,
    to_task_id INTEGER NOT NULL,
    dependency_type VARCHAR(50) DEFAULT 'blocks',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (from_task_id) REFERENCES prospective_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (to_task_id) REFERENCES prospective_tasks(id) ON DELETE CASCADE,
    UNIQUE(from_task_id, to_task_id)
);

CREATE TABLE IF NOT EXISTS estimate_accuracy (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    task_type VARCHAR(50),
    accuracy_percent FLOAT DEFAULT 0.0,
    bias_factor FLOAT DEFAULT 1.0,
    variance FLOAT DEFAULT 0.0,
    sample_count INTEGER DEFAULT 0,
    avg_estimate INTEGER DEFAULT 0,
    avg_actual INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, task_type)
);

CREATE TABLE IF NOT EXISTS accuracy_trends (
    id SERIAL PRIMARY KEY,
    accuracy_id INTEGER NOT NULL,
    trend_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accuracy_value FLOAT,
    sample_size INTEGER,
    FOREIGN KEY (accuracy_id) REFERENCES estimate_accuracy(id) ON DELETE CASCADE
);

-- ============================================================================
-- META-MEMORY LAYER TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS attention_items (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    item_type VARCHAR(50) NOT NULL,
    item_id INTEGER NOT NULL,
    salience_score REAL DEFAULT 0.5,
    importance REAL DEFAULT 0.5,
    relevance REAL DEFAULT 0.5,
    recency REAL DEFAULT 0.5,
    last_accessed TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    activation_level REAL DEFAULT 0.0,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    context TEXT DEFAULT '',
    UNIQUE(project_id, item_type, item_id)
);

CREATE TABLE IF NOT EXISTS working_memory_state (
    id SERIAL PRIMARY KEY,
    project_id INTEGER UNIQUE NOT NULL,
    capacity INTEGER DEFAULT 7,
    capacity_variance INTEGER DEFAULT 2,
    current_load INTEGER DEFAULT 0,
    cognitive_load REAL DEFAULT 0.0,
    active_items TEXT DEFAULT '[]',
    total_slots_used INTEGER DEFAULT 0,
    overflow_threshold REAL DEFAULT 0.85,
    overflow_items TEXT DEFAULT '[]',
    last_consolidated TIMESTAMP,
    consolidation_interval_hours INTEGER DEFAULT 8,
    item_decay_rate REAL DEFAULT 0.1,
    refresh_threshold REAL DEFAULT 0.3,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attention_budgets (
    id SERIAL PRIMARY KEY,
    project_id INTEGER UNIQUE NOT NULL,
    current_focus VARCHAR(50) NOT NULL,
    focus_allocation TEXT DEFAULT '{}',
    current_focus_level REAL DEFAULT 0.0,
    context_switches INTEGER DEFAULT 0,
    context_switch_cost REAL DEFAULT 0.0,
    mental_energy REAL DEFAULT 1.0,
    fatigue_level REAL DEFAULT 0.0,
    optimal_session_length_minutes INTEGER DEFAULT 90,
    distraction_sources TEXT DEFAULT '[]',
    distraction_level REAL DEFAULT 0.0,
    session_start TIMESTAMP,
    session_end TIMESTAMP,
    total_focused_time_minutes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- CONSOLIDATION & WORKFLOW TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS consolidation_runs (
    run_id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'pending',
    events_processed INTEGER DEFAULT 0,
    events_consolidated INTEGER DEFAULT 0,
    patterns_extracted INTEGER DEFAULT 0,
    patterns_validated INTEGER DEFAULT 0,
    quality_before FLOAT,
    quality_after FLOAT,
    quality_improvement FLOAT,
    duration_seconds FLOAT,
    events_per_second FLOAT,
    errors INTEGER,
    error_messages TEXT,
    config TEXT,
    notes TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS workflow_patterns (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    pattern_name VARCHAR(255) NOT NULL,
    pattern_type VARCHAR(50) NOT NULL,
    frequency INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, pattern_name)
);

CREATE TABLE IF NOT EXISTS task_type_workflows (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    task_type VARCHAR(100) NOT NULL,
    recommended_pattern_id INTEGER,
    workflow_steps TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (recommended_pattern_id) REFERENCES workflow_patterns(id)
);

-- ============================================================================
-- SESSION & INTEGRATION TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS session_contexts (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    context_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, session_id)
);

CREATE TABLE IF NOT EXISTS todowrite_plans (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    todo_id VARCHAR(255),
    plan_id INTEGER,
    plan_status VARCHAR(50) DEFAULT 'pending',
    sync_state VARCHAR(50) DEFAULT 'synced',
    last_sync_time TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS conflict_resolutions (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    conflict_type VARCHAR(100),
    resolution_strategy VARCHAR(100),
    resolved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    outcome TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- ============================================================================
-- LEARNING & DECISION TRACKING TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS learning_outcomes (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(255) NOT NULL,
    decision TEXT NOT NULL,
    outcome TEXT NOT NULL,
    success_rate FLOAT NOT NULL CHECK (success_rate >= 0.0 AND success_rate <= 1.0),
    execution_time_ms FLOAT NOT NULL,
    context JSONB DEFAULT '{}',
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_outcome CHECK (outcome IN ('success', 'failure', 'partial', 'error'))
);

-- ============================================================================
-- CODE INDEXING TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS symbols (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    symbol_name TEXT NOT NULL,
    symbol_type VARCHAR(50),
    file_path TEXT,
    line_number INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, symbol_name, file_path)
);

CREATE TABLE IF NOT EXISTS code_elements (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    element_type VARCHAR(50) NOT NULL,
    element_name TEXT NOT NULL,
    file_path TEXT,
    start_line INTEGER,
    end_line INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS code_relationships (
    id INTEGER PRIMARY KEY,
    element_id INTEGER NOT NULL,
    related_element_id INTEGER NOT NULL,
    relationship_type VARCHAR(50),
    FOREIGN KEY (element_id) REFERENCES code_elements(id),
    FOREIGN KEY (related_element_id) REFERENCES code_elements(id)
);

-- ============================================================================
-- MEMORY VERSIONING TABLES (Zettelkasten)
-- ============================================================================

CREATE TABLE IF NOT EXISTS memory_versions (
    id INTEGER PRIMARY KEY,
    memory_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    UNIQUE(memory_id, version),
    FOREIGN KEY(memory_id) REFERENCES semantic_memories(id)
);

CREATE TABLE IF NOT EXISTS memory_attributes (
    id INTEGER PRIMARY KEY,
    memory_id INTEGER NOT NULL UNIQUE,
    importance_score REAL NOT NULL DEFAULT 0.5,
    context_tags TEXT NOT NULL DEFAULT '[]',
    related_count INTEGER NOT NULL DEFAULT 0,
    evolution_stage TEXT NOT NULL DEFAULT 'nascent',
    last_evolved_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    FOREIGN KEY(memory_id) REFERENCES semantic_memories(id)
);

CREATE TABLE IF NOT EXISTS hierarchical_index (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    index_id TEXT NOT NULL UNIQUE,
    parent_id TEXT,
    label TEXT NOT NULL,
    depth INTEGER NOT NULL,
    memory_ids TEXT NOT NULL DEFAULT '[]',
    created_at INTEGER NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id)
);

-- ============================================================================
-- CENTRAL EXECUTIVE STATE TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS central_executive_state (
    id SERIAL PRIMARY KEY,
    project_id INTEGER UNIQUE NOT NULL,
    focused_item_type VARCHAR(50),
    focused_item_id INTEGER,
    task_queue TEXT DEFAULT '[]',
    active_goals TEXT DEFAULT '[]',
    cognitive_state VARCHAR(50) DEFAULT 'ready',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- ============================================================================
-- INDICES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_procedure_versions_procedure_id ON procedure_versions(procedure_id);
CREATE INDEX IF NOT EXISTS idx_task_dependencies_project ON task_dependencies(project_id);
CREATE INDEX IF NOT EXISTS idx_attention_items_project ON attention_items(project_id);
CREATE INDEX IF NOT EXISTS idx_attention_items_salience ON attention_items(salience_score DESC);
CREATE INDEX IF NOT EXISTS idx_consolidation_runs_project ON consolidation_runs(project_id);
CREATE INDEX IF NOT EXISTS idx_workflow_patterns_project ON workflow_patterns(project_id);
CREATE INDEX IF NOT EXISTS idx_session_contexts_project ON session_contexts(project_id);
CREATE INDEX IF NOT EXISTS idx_learning_outcomes_agent ON learning_outcomes(agent_name);
CREATE INDEX IF NOT EXISTS idx_symbols_project ON symbols(project_id);
CREATE INDEX IF NOT EXISTS idx_code_elements_project ON code_elements(project_id);
CREATE INDEX IF NOT EXISTS idx_memory_versions_id ON memory_versions(memory_id);
CREATE INDEX IF NOT EXISTS idx_memory_attributes_stage ON memory_attributes(evolution_stage);
CREATE INDEX IF NOT EXISTS idx_hierarchical_parent ON hierarchical_index(parent_id);
