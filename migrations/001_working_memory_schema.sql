-- Migration: Working Memory Layer Schema
-- Version: 2
-- Date: 2025-10-16
-- Description: Add Working Memory (Layer 0-1) with Baddeley's model

-- ============================================================================
-- Working Memory Tables
-- ============================================================================

-- Core working memory store (7±2 items max - Miller's law)
CREATE TABLE IF NOT EXISTS working_memory (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_type TEXT NOT NULL CHECK (content_type IN ('verbal', 'spatial', 'episodic', 'goal')),
    component TEXT NOT NULL CHECK (component IN ('phonological', 'visuospatial', 'episodic_buffer', 'central_executive')),
    activation_level REAL DEFAULT 1.0 CHECK (activation_level >= 0.0 AND activation_level <= 1.0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    decay_rate REAL DEFAULT 0.1 CHECK (decay_rate > 0.0),
    importance_score REAL DEFAULT 0.5 CHECK (importance_score >= 0.0 AND importance_score <= 1.0),
    embedding BLOB,
    metadata TEXT,  -- JSON
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Active goals managed by Central Executive
CREATE TABLE IF NOT EXISTS active_goals (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    goal_text TEXT NOT NULL,
    goal_type TEXT NOT NULL CHECK (goal_type IN ('primary', 'subgoal', 'maintenance')),
    parent_goal_id INTEGER,
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'completed', 'failed', 'in_progress', 'blocked')),
    progress REAL DEFAULT 0.0 CHECK (progress >= 0.0 AND progress <= 1.0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deadline TIMESTAMP,
    completion_criteria TEXT,
    metadata TEXT,  -- JSON
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_goal_id) REFERENCES active_goals(id) ON DELETE SET NULL
);

-- Attention focus tracking
CREATE TABLE IF NOT EXISTS attention_focus (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    goal_id INTEGER,
    focus_target TEXT,
    focus_type TEXT CHECK (focus_type IN ('file', 'concept', 'task', 'problem', 'memory')),
    attention_weight REAL DEFAULT 1.0 CHECK (attention_weight >= 0.0),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    focused_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_seconds INTEGER DEFAULT 0,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (goal_id) REFERENCES active_goals(id) ON DELETE CASCADE
);

-- Decay history for psychological validation
CREATE TABLE IF NOT EXISTS working_memory_decay_log (
    id SERIAL PRIMARY KEY,
    wm_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activation_level REAL CHECK (activation_level >= 0.0 AND activation_level <= 1.0),
    access_count INTEGER DEFAULT 0,
    FOREIGN KEY (wm_id) REFERENCES working_memory(id) ON DELETE CASCADE
);

-- Consolidation routing decisions (for ML training)
CREATE TABLE IF NOT EXISTS consolidation_routes (
    id SERIAL PRIMARY KEY,
    wm_id INTEGER NOT NULL,
    target_layer TEXT NOT NULL CHECK (target_layer IN ('semantic', 'episodic', 'procedural', 'prospective')),
    confidence REAL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    was_correct BOOLEAN,
    routed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    features TEXT,  -- JSON array of feature values
    FOREIGN KEY (wm_id) REFERENCES working_memory(id) ON DELETE CASCADE
);

-- ============================================================================
-- Indexes for Working Memory
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_wm_project ON working_memory(project_id);
CREATE INDEX IF NOT EXISTS idx_wm_activation ON working_memory(activation_level DESC);
CREATE INDEX IF NOT EXISTS idx_wm_component ON working_memory(component);
CREATE INDEX IF NOT EXISTS idx_wm_accessed ON working_memory(last_accessed DESC);
CREATE INDEX IF NOT EXISTS idx_wm_project_component ON working_memory(project_id, component);

CREATE INDEX IF NOT EXISTS idx_goals_project ON active_goals(project_id);
CREATE INDEX IF NOT EXISTS idx_goals_status ON active_goals(status);
CREATE INDEX IF NOT EXISTS idx_goals_parent ON active_goals(parent_goal_id);
CREATE INDEX IF NOT EXISTS idx_goals_priority ON active_goals(priority DESC);
CREATE INDEX IF NOT EXISTS idx_goals_project_status ON active_goals(project_id, status);

CREATE INDEX IF NOT EXISTS idx_attention_project ON attention_focus(project_id);
CREATE INDEX IF NOT EXISTS idx_attention_started ON attention_focus(started_at DESC);

CREATE INDEX IF NOT EXISTS idx_decay_wm ON working_memory_decay_log(wm_id);
CREATE INDEX IF NOT EXISTS idx_decay_timestamp ON working_memory_decay_log(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_routes_wm ON consolidation_routes(wm_id);
CREATE INDEX IF NOT EXISTS idx_routes_layer ON consolidation_routes(target_layer);
CREATE INDEX IF NOT EXISTS idx_routes_correct ON consolidation_routes(was_correct);

-- ============================================================================
-- Triggers for automatic timestamp updates
-- ============================================================================

CREATE TRIGGER IF NOT EXISTS update_goal_timestamp
AFTER UPDATE ON active_goals
FOR EACH ROW
BEGIN
    UPDATE active_goals SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS log_wm_access
AFTER UPDATE OF last_accessed ON working_memory
FOR EACH ROW
BEGIN
    INSERT INTO working_memory_decay_log (wm_id, activation_level, access_count)
    VALUES (NEW.id, NEW.activation_level,
            (SELECT COUNT(*) FROM working_memory_decay_log WHERE wm_id = NEW.id) + 1);
END;

-- ============================================================================
-- Views for convenient access
-- ============================================================================

-- Current working memory state (with decay applied)
CREATE VIEW IF NOT EXISTS v_working_memory_current AS
SELECT
    wm.id,
    wm.project_id,
    wm.content,
    wm.content_type,
    wm.component,
    wm.activation_level,
    wm.last_accessed,
    wm.importance_score,
    -- Calculate current activation with decay
    wm.activation_level * EXP(
        -wm.decay_rate * (1 - wm.importance_score * 0.5) *
        (JULIANDAY('now') - JULIANDAY(wm.last_accessed)) * 86400
    ) as current_activation,
    -- Time since last access in seconds
    (JULIANDAY('now') - JULIANDAY(wm.last_accessed)) * 86400 as seconds_since_access
FROM working_memory wm;

-- Active goals hierarchy
CREATE VIEW IF NOT EXISTS v_goals_hierarchy AS
WITH RECURSIVE goal_tree AS (
    -- Base case: top-level goals
    SELECT
        id, project_id, goal_text, goal_type, parent_goal_id,
        priority, status, progress, created_at, deadline,
        0 as depth,
        goal_text as path
    FROM active_goals
    WHERE parent_goal_id IS NULL

    UNION ALL

    -- Recursive case: subgoals
    SELECT
        g.id, g.project_id, g.goal_text, g.goal_type, g.parent_goal_id,
        g.priority, g.status, g.progress, g.created_at, g.deadline,
        gt.depth + 1,
        gt.path || ' > ' || g.goal_text
    FROM active_goals g
    INNER JOIN goal_tree gt ON g.parent_goal_id = gt.id
)
SELECT * FROM goal_tree
ORDER BY depth, priority DESC;

-- Working memory capacity status
CREATE VIEW IF NOT EXISTS v_wm_capacity AS
SELECT
    project_id,
    COUNT(*) as item_count,
    7 as max_capacity,
    CASE
        WHEN COUNT(*) >= 7 THEN 'full'
        WHEN COUNT(*) >= 5 THEN 'near_full'
        ELSE 'available'
    END as status,
    AVG(current_activation) as avg_activation
FROM v_working_memory_current
GROUP BY project_id;

-- ============================================================================
-- Validation Queries
-- ============================================================================

-- Check Miller's law compliance (7±2 items)
-- SELECT * FROM v_wm_capacity WHERE item_count > 9;  -- Should be empty

-- Check decay is working
-- SELECT id, content, activation_level, current_activation,
--        seconds_since_access / 60.0 as minutes_since_access
-- FROM v_working_memory_current
-- WHERE current_activation < activation_level
-- ORDER BY seconds_since_access DESC;

-- Check goal hierarchy integrity
-- SELECT * FROM v_goals_hierarchy;
