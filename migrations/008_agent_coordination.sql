-- Migration: Agent Coordination Infrastructure
-- Purpose: Add multi-agent orchestration support to Athena
-- Date: 2025-11-20
--
-- Creates:
-- 1. agents table - Registry of active agents with status/heartbeat tracking
-- 2. Extends prospective_tasks - Agent assignment, progress tracking, optimistic locking
-- 3. Coordination events - Progress tracking via episodic events

-- 1. Create agents registry table
CREATE TABLE IF NOT EXISTS agents (
    agent_id TEXT PRIMARY KEY,
    agent_type TEXT NOT NULL,              -- 'research', 'analysis', 'synthesis', etc.
    capabilities TEXT[] DEFAULT '{}',      -- ['web_search', 'code_analysis']
    status TEXT NOT NULL DEFAULT 'idle',   -- 'idle', 'busy', 'failed', 'offline'
    tmux_pane_id TEXT,                     -- tmux pane identifier (e.g., 'agents:main.0')
    process_pid INTEGER,                   -- OS process ID
    current_task_id TEXT,                  -- Currently executing task
    restart_count INTEGER DEFAULT 0,       -- Number of times respawned
    last_heartbeat TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for querying by status and type
CREATE INDEX IF NOT EXISTS idx_agents_status_type
ON agents(status, agent_type);

-- Index for detecting stale agents
CREATE INDEX IF NOT EXISTS idx_agents_stale_heartbeat
ON agents(last_heartbeat)
WHERE status != 'offline';

-- 2. Extend prospective_tasks with agent coordination fields
-- These columns are added if they don't exist (idempotent)
DO $$
BEGIN
    -- Add assigned_agent_id if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'prospective_tasks' AND column_name = 'assigned_agent_id'
    ) THEN
        ALTER TABLE prospective_tasks
        ADD COLUMN assigned_agent_id TEXT REFERENCES agents(agent_id) ON DELETE SET NULL,
        ADD COLUMN progress_percentage INTEGER DEFAULT 0 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
        ADD COLUMN blocked_by TEXT,                    -- Reason task is blocked (e.g., 'dependency_X not complete')
        ADD COLUMN claimed_at TIMESTAMPTZ,             -- When task was claimed by agent
        ADD COLUMN version INTEGER DEFAULT 1;           -- For optimistic concurrency control
    END IF;
END $$;

-- Index for finding unclaimed tasks
CREATE INDEX IF NOT EXISTS idx_tasks_unclaimed
ON prospective_tasks(status, assigned_agent_id)
WHERE status = 'PENDING' AND assigned_agent_id IS NULL;

-- Index for finding tasks by assigned agent
CREATE INDEX IF NOT EXISTS idx_tasks_by_agent
ON prospective_tasks(assigned_agent_id, status);

-- Index for dependency graph traversal
CREATE INDEX IF NOT EXISTS idx_tasks_blocked_by
ON prospective_tasks(blocked_by)
WHERE blocked_by IS NOT NULL;

-- 3. Note: Agent progress is tracked via episodic_events with event_type='agent_progress'
-- No separate view needed - agents write to episodic_events directly

-- 4. Helper function: Claim task atomically with optimistic locking
CREATE OR REPLACE FUNCTION claim_task(
    task_id_param TEXT,
    agent_id_param TEXT,
    expected_version INT DEFAULT 1
)
RETURNS TABLE(
    claimed BOOLEAN,
    task_id TEXT,
    error_msg TEXT
) AS $$
BEGIN
    UPDATE prospective_tasks
    SET
        assigned_agent_id = agent_id_param,
        status = 'IN_PROGRESS',
        claimed_at = NOW(),
        version = version + 1
    WHERE
        prospective_tasks.task_id = task_id_param
        AND status = 'PENDING'
        AND version = expected_version;

    -- Return success if one row was updated
    IF FOUND THEN
        RETURN QUERY SELECT TRUE, task_id_param, NULL::TEXT;
    ELSE
        RETURN QUERY SELECT FALSE, task_id_param, 'Task already claimed or version mismatch'::TEXT;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 5. Helper function: Update task progress
CREATE OR REPLACE FUNCTION update_task_progress(
    task_id_param TEXT,
    agent_id_param TEXT,
    progress_pct_param INTEGER,
    blocked_by_param TEXT DEFAULT NULL
)
RETURNS TABLE(
    success BOOLEAN,
    error_msg TEXT
) AS $$
BEGIN
    UPDATE prospective_tasks
    SET
        progress_percentage = progress_pct_param,
        blocked_by = blocked_by_param,
        updated_at = NOW()
    WHERE
        task_id = task_id_param
        AND assigned_agent_id = agent_id_param;

    IF FOUND THEN
        RETURN QUERY SELECT TRUE, NULL::TEXT;
    ELSE
        RETURN QUERY SELECT FALSE, 'Task not found or not assigned to agent'::TEXT;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 6. Helper function: Detect stale agents (heartbeat older than interval)
CREATE OR REPLACE FUNCTION detect_stale_agents(
    stale_threshold_seconds INT DEFAULT 60
)
RETURNS TABLE(
    agent_id TEXT,
    agent_type TEXT,
    status TEXT,
    last_heartbeat TIMESTAMPTZ,
    seconds_since_heartbeat INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.agent_id,
        a.agent_type,
        a.status,
        a.last_heartbeat,
        EXTRACT(EPOCH FROM (NOW() - a.last_heartbeat))::INT
    FROM agents a
    WHERE
        a.status != 'offline'
        AND (NOW() - a.last_heartbeat) > INTERVAL '1 second' * stale_threshold_seconds
    ORDER BY a.last_heartbeat ASC;
END;
$$ LANGUAGE plpgsql;

-- 7. Helper function: Get tasks ready to claim (no unmet dependencies)
CREATE OR REPLACE FUNCTION get_available_tasks(
    agent_types_filter TEXT[] DEFAULT '{}',
    limit_count INT DEFAULT 5
)
RETURNS TABLE(
    task_id TEXT,
    title TEXT,
    description TEXT,
    priority TEXT,
    dependencies TEXT[],
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        pt.task_id,
        pt.title,
        pt.description,
        pt.priority,
        pt.dependencies,
        pt.created_at
    FROM prospective_tasks pt
    WHERE
        pt.status = 'PENDING'
        AND pt.assigned_agent_id IS NULL
        -- Ensure all dependencies are completed
        AND NOT EXISTS (
            SELECT 1
            FROM unnest(pt.dependencies) AS dep_id
            JOIN prospective_tasks dep_task ON dep_task.task_id = dep_id
            WHERE dep_task.status != 'COMPLETED'
        )
    ORDER BY
        CASE pt.priority
            WHEN 'CRITICAL' THEN 1
            WHEN 'HIGH' THEN 2
            WHEN 'MEDIUM' THEN 3
            WHEN 'LOW' THEN 4
            ELSE 5
        END,
        pt.created_at ASC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- 8. Grant permissions
GRANT SELECT, INSERT, UPDATE ON agents TO postgres;
GRANT SELECT, UPDATE ON prospective_tasks TO postgres;
GRANT EXECUTE ON FUNCTION claim_task TO postgres;
GRANT EXECUTE ON FUNCTION update_task_progress TO postgres;
GRANT EXECUTE ON FUNCTION detect_stale_agents TO postgres;
GRANT EXECUTE ON FUNCTION get_available_tasks TO postgres;

-- 9. Add comments for documentation
COMMENT ON TABLE agents IS 'Registry of active agent instances with status and heartbeat tracking';
COMMENT ON COLUMN agents.agent_id IS 'Unique identifier for this agent instance (e.g., research_a1b2c3d4)';
COMMENT ON COLUMN agents.agent_type IS 'Type of agent (research, analysis, synthesis, validation, documentation, testing)';
COMMENT ON COLUMN agents.status IS 'Current status: idle (waiting), busy (working), failed (error), offline (dead)';
COMMENT ON COLUMN agents.last_heartbeat IS 'Timestamp of last heartbeat; stale heartbeat indicates stuck/dead agent';
COMMENT ON FUNCTION claim_task IS 'Atomically claim a task for an agent using optimistic locking (version stamps)';
COMMENT ON FUNCTION update_task_progress IS 'Update progress percentage and blocked_by status for a task';
COMMENT ON FUNCTION detect_stale_agents IS 'Find agents with stale heartbeats (indicating they may be stuck or dead)';
COMMENT ON FUNCTION get_available_tasks IS 'Query for pending tasks with all dependencies satisfied';

-- 10. Print migration summary
SELECT format(
    'Agent coordination tables created: agents table, extended prospective_tasks, %s helper functions',
    COUNT(*)
) AS migration_summary
FROM information_schema.routines
WHERE routine_schema = 'public'
AND routine_name IN ('claim_task', 'update_task_progress', 'detect_stale_agents', 'get_available_tasks');
