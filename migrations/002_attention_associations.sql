-- Migration: Attention System & Associative Networks
-- Version: 4
-- Date: 2025-10-17
-- Description: Add Phase 2 - Attention mechanisms, spreading activation, Hebbian learning

-- ============================================================================
-- ATTENTION SYSTEM TABLES
-- ============================================================================

-- Salience tracking (novelty, surprise, contradiction)
CREATE TABLE IF NOT EXISTS attention_salience (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    memory_id INTEGER NOT NULL,
    memory_layer TEXT NOT NULL CHECK (memory_layer IN ('working', 'semantic', 'episodic', 'procedural', 'prospective', 'graph')),
    salience_score REAL DEFAULT 0.0 CHECK (salience_score >= 0.0 AND salience_score <= 1.0),
    novelty_score REAL DEFAULT 0.0 CHECK (novelty_score >= 0.0 AND novelty_score <= 1.0),
    surprise_score REAL DEFAULT 0.0 CHECK (surprise_score >= 0.0 AND surprise_score <= 1.0),
    contradiction_score REAL DEFAULT 0.0 CHECK (contradiction_score >= 0.0 AND contradiction_score <= 1.0),
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reason TEXT,
    conflicting_memory_id INTEGER,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Attention state (what's currently focused)
CREATE TABLE IF NOT EXISTS attention_state (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    focus_memory_id INTEGER NOT NULL,
    focus_layer TEXT NOT NULL,
    attention_weight REAL DEFAULT 1.0 CHECK (attention_weight >= 0.0 AND attention_weight <= 1.0),
    focus_type TEXT DEFAULT 'primary' CHECK (focus_type IN ('primary', 'secondary', 'background')),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    transition_type TEXT CHECK (transition_type IN ('voluntary', 'automatic', 'interruption', 'return')),
    previous_focus_id INTEGER,  -- For context preservation
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (previous_focus_id) REFERENCES attention_state(id) ON DELETE SET NULL
);

-- Inhibited memories (suppressed from retrieval)
CREATE TABLE IF NOT EXISTS attention_inhibition (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    memory_id INTEGER NOT NULL,
    memory_layer TEXT NOT NULL,
    inhibition_strength REAL DEFAULT 0.5 CHECK (inhibition_strength >= 0.0 AND inhibition_strength <= 1.0),
    inhibition_type TEXT CHECK (inhibition_type IN ('proactive', 'retroactive', 'selective')),
    reason TEXT,
    inhibited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- ============================================================================
-- SPREADING ACTIVATION NETWORK TABLES
-- ============================================================================

-- Associative links between memories
CREATE TABLE IF NOT EXISTS association_links (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    from_memory_id INTEGER NOT NULL,
    to_memory_id INTEGER NOT NULL,
    from_layer TEXT NOT NULL,
    to_layer TEXT NOT NULL,
    link_strength REAL DEFAULT 0.5 CHECK (link_strength >= 0.0 AND link_strength <= 1.0),
    co_occurrence_count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_strengthened TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    link_type TEXT DEFAULT 'semantic' CHECK (link_type IN ('semantic', 'temporal', 'causal', 'similarity')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, from_memory_id, to_memory_id, from_layer, to_layer)
);

-- Current activation levels (transient state)
CREATE TABLE IF NOT EXISTS activation_state (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    memory_id INTEGER NOT NULL,
    memory_layer TEXT NOT NULL,
    activation_level REAL DEFAULT 0.0 CHECK (activation_level >= 0.0 AND activation_level <= 1.0),
    source_activation_id INTEGER,  -- What triggered this activation
    hop_distance INTEGER DEFAULT 0,  -- How many hops from source
    activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, memory_id, memory_layer)
);

-- Temporal priming state
CREATE TABLE IF NOT EXISTS priming_state (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    memory_id INTEGER NOT NULL,
    memory_layer TEXT NOT NULL,
    priming_strength REAL DEFAULT 1.0 CHECK (priming_strength >= 0.0),
    primed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, memory_id, memory_layer)
);

-- ============================================================================
-- HEBBIAN LEARNING TABLES
-- ============================================================================

-- Access history for Hebbian learning
CREATE TABLE IF NOT EXISTS memory_access_log (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    memory_id INTEGER NOT NULL,
    memory_layer TEXT NOT NULL,
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_type TEXT CHECK (access_type IN ('read', 'update', 'consolidate', 'search')),
    context_goal_id INTEGER,  -- What goal was active during access
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Learning statistics
CREATE TABLE IF NOT EXISTS hebbian_stats (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    link_id INTEGER NOT NULL,
    strengthening_events INTEGER DEFAULT 0,
    last_strengthened TIMESTAMP,
    total_strength_delta REAL DEFAULT 0.0,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (link_id) REFERENCES association_links(id) ON DELETE CASCADE,
    UNIQUE(project_id, link_id)
);

-- ============================================================================
-- INDEXES FOR ATTENTION SYSTEM
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_salience_project ON attention_salience(project_id);
CREATE INDEX IF NOT EXISTS idx_salience_score ON attention_salience(salience_score DESC);
CREATE INDEX IF NOT EXISTS idx_salience_layer ON attention_salience(memory_layer);
CREATE INDEX IF NOT EXISTS idx_salience_memory ON attention_salience(memory_id, memory_layer);
CREATE INDEX IF NOT EXISTS idx_salience_detected ON attention_salience(detected_at DESC);

CREATE INDEX IF NOT EXISTS idx_attention_project ON attention_state(project_id);
CREATE INDEX IF NOT EXISTS idx_attention_active ON attention_state(project_id, ended_at) WHERE ended_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_attention_weight ON attention_state(attention_weight DESC);
CREATE INDEX IF NOT EXISTS idx_attention_memory ON attention_state(focus_memory_id, focus_layer);
CREATE INDEX IF NOT EXISTS idx_attention_started ON attention_state(started_at DESC);

CREATE INDEX IF NOT EXISTS idx_inhibition_project ON attention_inhibition(project_id);
CREATE INDEX IF NOT EXISTS idx_inhibition_memory ON attention_inhibition(memory_id, memory_layer);
CREATE INDEX IF NOT EXISTS idx_inhibition_expires ON attention_inhibition(expires_at);
CREATE INDEX IF NOT EXISTS idx_inhibition_strength ON attention_inhibition(inhibition_strength DESC);

-- ============================================================================
-- INDEXES FOR SPREADING ACTIVATION
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_assoc_from ON association_links(from_memory_id, from_layer);
CREATE INDEX IF NOT EXISTS idx_assoc_to ON association_links(to_memory_id, to_layer);
CREATE INDEX IF NOT EXISTS idx_assoc_strength ON association_links(link_strength DESC);
CREATE INDEX IF NOT EXISTS idx_assoc_project ON association_links(project_id);
CREATE INDEX IF NOT EXISTS idx_assoc_bidirectional ON association_links(from_memory_id, to_memory_id, from_layer, to_layer);

CREATE INDEX IF NOT EXISTS idx_activation_project ON activation_state(project_id);
CREATE INDEX IF NOT EXISTS idx_activation_memory ON activation_state(memory_id, memory_layer);
CREATE INDEX IF NOT EXISTS idx_activation_level ON activation_state(activation_level DESC);
CREATE INDEX IF NOT EXISTS idx_activation_time ON activation_state(activated_at DESC);

CREATE INDEX IF NOT EXISTS idx_priming_project ON priming_state(project_id);
CREATE INDEX IF NOT EXISTS idx_priming_memory ON priming_state(memory_id, memory_layer);
CREATE INDEX IF NOT EXISTS idx_priming_expires ON priming_state(expires_at);

-- ============================================================================
-- INDEXES FOR HEBBIAN LEARNING
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_access_project ON memory_access_log(project_id);
CREATE INDEX IF NOT EXISTS idx_access_time ON memory_access_log(accessed_at DESC);
CREATE INDEX IF NOT EXISTS idx_access_memory ON memory_access_log(memory_id, memory_layer);
CREATE INDEX IF NOT EXISTS idx_access_goal ON memory_access_log(context_goal_id) WHERE context_goal_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_hstats_link ON hebbian_stats(link_id);
CREATE INDEX IF NOT EXISTS idx_hstats_project ON hebbian_stats(project_id);
CREATE INDEX IF NOT EXISTS idx_hstats_events ON hebbian_stats(strengthening_events DESC);

-- ============================================================================
-- TRIGGERS FOR AUTOMATIC UPDATES
-- ============================================================================

-- Update attention_state timestamp on changes
CREATE TRIGGER IF NOT EXISTS update_attention_timestamp
AFTER UPDATE ON attention_state
FOR EACH ROW
BEGIN
    UPDATE attention_state SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Auto-strengthen association on co-occurrence
CREATE TRIGGER IF NOT EXISTS strengthen_on_cooccurrence
AFTER UPDATE OF co_occurrence_count ON association_links
FOR EACH ROW
BEGIN
    UPDATE association_links
    SET link_strength = MIN(1.0, link_strength + 0.05),
        last_strengthened = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

-- Log association strengthening events
CREATE TRIGGER IF NOT EXISTS log_strengthening_event
AFTER UPDATE OF link_strength ON association_links
FOR EACH ROW
WHEN NEW.link_strength > OLD.link_strength
BEGIN
    INSERT OR IGNORE INTO hebbian_stats (project_id, link_id, strengthening_events, last_strengthened, total_strength_delta)
    VALUES (NEW.project_id, NEW.id, 0, CURRENT_TIMESTAMP, 0.0);

    UPDATE hebbian_stats
    SET strengthening_events = strengthening_events + 1,
        last_strengthened = CURRENT_TIMESTAMP,
        total_strength_delta = total_strength_delta + (NEW.link_strength - OLD.link_strength)
    WHERE link_id = NEW.id;
END;

-- ============================================================================
-- VIEWS FOR CONVENIENT ACCESS
-- ============================================================================

-- Active attention state
CREATE VIEW IF NOT EXISTS v_attention_current AS
SELECT
    s.id,
    s.project_id,
    s.focus_memory_id,
    s.focus_layer,
    s.attention_weight,
    s.focus_type,
    s.started_at,
    s.updated_at,
    -- Time focused in seconds
    (JULIANDAY('now') - JULIANDAY(s.started_at)) * 86400 as focus_duration_seconds
FROM attention_state s
WHERE s.ended_at IS NULL
ORDER BY s.attention_weight DESC;

-- Highly salient memories
CREATE VIEW IF NOT EXISTS v_salient_memories AS
SELECT
    s.project_id,
    s.memory_id,
    s.memory_layer,
    s.salience_score,
    s.novelty_score,
    s.surprise_score,
    s.contradiction_score,
    s.reason,
    s.detected_at,
    -- Recency-weighted salience (decay over time)
    s.salience_score * EXP(-0.01 * (JULIANDAY('now') - JULIANDAY(s.detected_at)) * 86400) as current_salience
FROM attention_salience s
WHERE s.salience_score > 0.5
ORDER BY current_salience DESC;

-- Active inhibitions
CREATE VIEW IF NOT EXISTS v_active_inhibitions AS
SELECT
    i.project_id,
    i.memory_id,
    i.memory_layer,
    i.inhibition_strength,
    i.inhibition_type,
    i.reason,
    i.inhibited_at,
    i.expires_at,
    -- Time remaining in seconds
    CASE
        WHEN i.expires_at IS NULL THEN NULL
        ELSE MAX(0, (JULIANDAY(i.expires_at) - JULIANDAY('now')) * 86400)
    END as remaining_seconds
FROM attention_inhibition i
WHERE i.expires_at IS NULL OR i.expires_at > CURRENT_TIMESTAMP
ORDER BY i.inhibition_strength DESC;

-- Strong associations (network backbone)
CREATE VIEW IF NOT EXISTS v_strong_associations AS
SELECT
    a.id,
    a.project_id,
    a.from_memory_id,
    a.to_memory_id,
    a.from_layer,
    a.to_layer,
    a.link_strength,
    a.co_occurrence_count,
    a.link_type,
    a.last_strengthened,
    -- Recency-weighted strength
    a.link_strength * (1.0 - 0.01 * MIN(1.0, (JULIANDAY('now') - JULIANDAY(a.last_strengthened)) / 86400)) as effective_strength
FROM association_links a
WHERE a.link_strength > 0.3
ORDER BY effective_strength DESC;

-- Currently activated memories
CREATE VIEW IF NOT EXISTS v_activated_memories AS
SELECT
    a.project_id,
    a.memory_id,
    a.memory_layer,
    a.activation_level,
    a.hop_distance,
    a.activated_at,
    -- Time since activation
    (JULIANDAY('now') - JULIANDAY(a.activated_at)) * 86400 as seconds_since_activation,
    -- Current activation with decay
    a.activation_level * EXP(-0.1 * (JULIANDAY('now') - JULIANDAY(a.activated_at)) * 86400) as current_activation
FROM activation_state a
WHERE a.activation_level > 0.1
ORDER BY current_activation DESC;

-- Currently primed memories
CREATE VIEW IF NOT EXISTS v_primed_memories AS
SELECT
    p.project_id,
    p.memory_id,
    p.memory_layer,
    p.priming_strength,
    p.primed_at,
    p.expires_at,
    -- Time remaining
    (JULIANDAY(p.expires_at) - JULIANDAY('now')) * 86400 as remaining_seconds,
    -- Current priming boost
    CASE
        WHEN (JULIANDAY('now') - JULIANDAY(p.primed_at)) * 86400 < 300 THEN 2.0  -- 0-5 min: 2x
        WHEN (JULIANDAY('now') - JULIANDAY(p.primed_at)) * 86400 < 1800 THEN 1.5  -- 5-30 min: 1.5x
        ELSE 1.2  -- 30-60 min: 1.2x
    END * p.priming_strength as current_boost
FROM priming_state p
WHERE p.expires_at > CURRENT_TIMESTAMP
ORDER BY current_boost DESC;

-- ============================================================================
-- VALIDATION QUERIES
-- ============================================================================

-- Check for duplicate associations
-- SELECT from_memory_id, to_memory_id, from_layer, to_layer, COUNT(*)
-- FROM association_links
-- GROUP BY from_memory_id, to_memory_id, from_layer, to_layer
-- HAVING COUNT(*) > 1;  -- Should be empty (UNIQUE constraint)

-- Check link strength bounds
-- SELECT * FROM association_links WHERE link_strength < 0.0 OR link_strength > 1.0;  -- Should be empty

-- Check activation state cleanliness (no stale activations)
-- SELECT * FROM activation_state
-- WHERE activated_at < datetime('now', '-1 hour');  -- Should be cleaned periodically

-- Check priming expiration (no expired entries)
-- SELECT * FROM priming_state WHERE expires_at < CURRENT_TIMESTAMP;  -- Should be cleaned

-- ============================================================================
-- MAINTENANCE PROCEDURES (SQL comments for documentation)
-- ============================================================================

-- Clean stale activations (run daily):
-- DELETE FROM activation_state WHERE activated_at < datetime('now', '-1 hour');

-- Clean expired priming (run hourly):
-- DELETE FROM priming_state WHERE expires_at < CURRENT_TIMESTAMP;

-- Clean expired inhibitions (run hourly):
-- DELETE FROM attention_inhibition
-- WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP;

-- Decay unused associations (run weekly):
-- UPDATE association_links
-- SET link_strength = link_strength * 0.99
-- WHERE last_strengthened < datetime('now', '-7 days');

-- Archive old access logs (run monthly, keep 90 days):
-- DELETE FROM memory_access_log WHERE accessed_at < datetime('now', '-90 days');
