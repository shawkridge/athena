-- Version: 9
-- Description: Enhance episodic events with project context and actionability metadata
-- Purpose: Enable optimal working memory ranking with project/goal context

-- UP

-- Add context and actionability metadata columns to episodic_events
ALTER TABLE episodic_events ADD COLUMN IF NOT EXISTS project_name TEXT;
ALTER TABLE episodic_events ADD COLUMN IF NOT EXISTS project_goal TEXT;
ALTER TABLE episodic_events ADD COLUMN IF NOT EXISTS project_phase_status TEXT;
ALTER TABLE episodic_events ADD COLUMN IF NOT EXISTS actionability_score REAL DEFAULT 0.5 CHECK(actionability_score >= 0.0 AND actionability_score <= 1.0);
ALTER TABLE episodic_events ADD COLUMN IF NOT EXISTS context_completeness_score REAL DEFAULT 0.5 CHECK(context_completeness_score >= 0.0 AND context_completeness_score <= 1.0);
ALTER TABLE episodic_events ADD COLUMN IF NOT EXISTS has_next_step INTEGER DEFAULT 0;
ALTER TABLE episodic_events ADD COLUMN IF NOT EXISTS has_blocker INTEGER DEFAULT 0;
ALTER TABLE episodic_events ADD COLUMN IF NOT EXISTS required_decisions TEXT;
ALTER TABLE episodic_events ADD COLUMN IF NOT EXISTS importance_score REAL DEFAULT 0.5 CHECK(importance_score >= 0.0 AND importance_score <= 1.0);

-- Create indexes for new fields (used in ranking queries)
CREATE INDEX IF NOT EXISTS idx_events_importance ON episodic_events(importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_events_actionability ON episodic_events(actionability_score DESC);
CREATE INDEX IF NOT EXISTS idx_events_completeness ON episodic_events(context_completeness_score DESC);
CREATE INDEX IF NOT EXISTS idx_events_project_goal ON episodic_events(project_goal);

-- Create a view for optimal working memory ranking
-- This ranks items by importance × contextuality × actionability
CREATE OR REPLACE VIEW v_working_memory_ranked AS
SELECT
    id,
    project_id,
    session_id,
    timestamp,
    event_type,
    content,
    project_name,
    project_goal,
    project_phase_status,
    importance_score,
    actionability_score,
    context_completeness_score,
    has_next_step,
    has_blocker,
    required_decisions,
    -- Combined ranking score: importance × contextuality × actionability
    (importance_score * context_completeness_score * actionability_score) as combined_rank
FROM episodic_events
WHERE project_id IS NOT NULL
ORDER BY combined_rank DESC, timestamp DESC;

-- DOWN

-- Drop the new view
DROP VIEW IF EXISTS v_working_memory_ranked;

-- Drop indexes
DROP INDEX IF EXISTS idx_events_importance;
DROP INDEX IF EXISTS idx_events_actionability;
DROP INDEX IF EXISTS idx_events_completeness;
DROP INDEX IF EXISTS idx_events_project_goal;

-- Drop columns
ALTER TABLE episodic_events DROP COLUMN IF EXISTS project_name;
ALTER TABLE episodic_events DROP COLUMN IF EXISTS project_goal;
ALTER TABLE episodic_events DROP COLUMN IF EXISTS project_phase_status;
ALTER TABLE episodic_events DROP COLUMN IF EXISTS actionability_score;
ALTER TABLE episodic_events DROP COLUMN IF EXISTS context_completeness_score;
ALTER TABLE episodic_events DROP COLUMN IF EXISTS has_next_step;
ALTER TABLE episodic_events DROP COLUMN IF EXISTS has_blocker;
ALTER TABLE episodic_events DROP COLUMN IF EXISTS required_decisions;
ALTER TABLE episodic_events DROP COLUMN IF EXISTS importance_score;
