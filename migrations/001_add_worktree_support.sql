-- Migration: Add Git Worktree Support
-- Purpose: Enable worktree-scoped todos and worktree-tagged memories
-- Date: 2025-11-20

-- =================================================================
-- Phase 1: Add worktree columns to todowrite_plans
-- =================================================================

ALTER TABLE IF EXISTS todowrite_plans
ADD COLUMN IF NOT EXISTS worktree_path TEXT,
ADD COLUMN IF NOT EXISTS worktree_branch VARCHAR(255),
ADD COLUMN IF NOT EXISTS is_worktree BOOLEAN DEFAULT FALSE;

-- Create indexes for worktree queries
CREATE INDEX IF NOT EXISTS idx_todowrite_worktree_path ON todowrite_plans(worktree_path);
CREATE INDEX IF NOT EXISTS idx_todowrite_worktree_branch ON todowrite_plans(worktree_branch);
CREATE INDEX IF NOT EXISTS idx_todowrite_project_worktree ON todowrite_plans(project_id, worktree_path);

-- =================================================================
-- Phase 2: Add worktree columns to episodic_events
-- =================================================================

ALTER TABLE IF EXISTS episodic_events
ADD COLUMN IF NOT EXISTS worktree_path TEXT,
ADD COLUMN IF NOT EXISTS worktree_branch VARCHAR(255);

-- Create indexes for episodic events worktree queries
CREATE INDEX IF NOT EXISTS idx_episodic_worktree_path ON episodic_events(worktree_path);
CREATE INDEX IF NOT EXISTS idx_episodic_project_worktree ON episodic_events(project_id, worktree_path, timestamp DESC);

-- =================================================================
-- Verification
-- =================================================================

-- Verify todowrite_plans schema
SELECT 'todowrite_plans columns:' as check_name;
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'todowrite_plans'
AND column_name IN ('worktree_path', 'worktree_branch', 'is_worktree')
ORDER BY column_name;

-- Verify episodic_events schema
SELECT 'episodic_events columns:' as check_name;
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'episodic_events'
AND column_name IN ('worktree_path', 'worktree_branch')
ORDER BY column_name;

-- Verify indexes created
SELECT 'Indexes created:' as check_name;
SELECT indexname FROM pg_indexes
WHERE schemaname = 'public'
AND indexname LIKE 'idx_%worktree%'
ORDER BY indexname;
