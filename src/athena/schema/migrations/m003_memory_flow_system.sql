-- Migration m003: Memory Flow System
--
-- Implements neuroscience-inspired memory flow routing with:
-- 1. Activation tracking for temporal decay and interference effects
-- 2. Tier management (working → session → episodic) based on Baddeley's limit
-- 3. Selective consolidation rules (strong → semantic, weak → decay)
-- 4. Temporal clustering for related event consolidation
--
-- Tables created:
-- 1. activation_history - Track activation state changes over time
--
-- Columns added to episodic_events:
-- - activation_level: Current activation strength (0.0-1.0) after decay
--
-- ============================================================================
-- EPISODIC LAYER MODIFICATIONS
-- ============================================================================

-- Add activation_level column to episodic_events (tracks current state after decay)
ALTER TABLE IF EXISTS episodic_events
ADD COLUMN IF NOT EXISTS activation_level FLOAT DEFAULT 1.0;

-- Comment on the new column
COMMENT ON COLUMN episodic_events.activation_level IS
    'Current activation strength after temporal decay (0.0-1.0). Updated periodically. Formula: e^(-decay_rate * hours_since_access) * interference_factor';

-- ============================================================================
-- FLOW SYSTEM TABLES
-- ============================================================================

-- Track activation state changes over time
-- Used to understand memory dynamics and validate decay models
CREATE TABLE IF NOT EXISTS activation_history (
    id BIGSERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Activation state at this point in time
    activation_value FLOAT NOT NULL,

    -- Decay and interference factors
    interference_factor FLOAT DEFAULT 1.0,

    -- Access metrics
    access_count INTEGER DEFAULT 0,

    -- Tier information
    current_tier VARCHAR(32) DEFAULT 'episodic',  -- 'working', 'session', 'episodic'

    -- Consolidation state
    consolidation_strength FLOAT DEFAULT 0.0,

    FOREIGN KEY (event_id) REFERENCES episodic_events(id) ON DELETE CASCADE
);

COMMENT ON TABLE activation_history IS
    'Historical record of activation state changes. Used to analyze memory dynamics, validate decay models, and compute consolidation metrics.';

COMMENT ON COLUMN activation_history.activation_value IS
    'Activation at this moment: base_activation * e^(-lambda*t) * interference_factor';

COMMENT ON COLUMN activation_history.interference_factor IS
    'RIF (Retrieval-Induced Forgetting) suppression: reduces when similar items accessed';

COMMENT ON COLUMN activation_history.current_tier IS
    'Memory tier: working (7±2 items, ~5-30 min), session (100 items, ~30 min-1 hr), episodic (unlimited, archived)';

-- Create indexes on activation_history
CREATE INDEX IF NOT EXISTS idx_activation_event ON activation_history(event_id);
CREATE INDEX IF NOT EXISTS idx_activation_timestamp ON activation_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_activation_tier ON activation_history(current_tier);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Optimize queries on episodic_events with activation
CREATE INDEX IF NOT EXISTS idx_episodic_activation_level ON episodic_events(activation_level DESC);
CREATE INDEX IF NOT EXISTS idx_episodic_lifecycle_status ON episodic_events(lifecycle_status);
CREATE INDEX IF NOT EXISTS idx_episodic_importance ON episodic_events(importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_episodic_last_activation ON episodic_events(last_activation DESC);

-- ============================================================================
-- VERIFICATION QUERIES (commented for documentation)
-- ============================================================================

-- Verify migration was successful
-- SELECT COUNT(*) as episodic_count FROM episodic_events WHERE activation_level IS NOT NULL;
-- SELECT COUNT(*) as activation_history_rows FROM activation_history;
-- SELECT DISTINCT current_tier FROM activation_history ORDER BY current_tier;
