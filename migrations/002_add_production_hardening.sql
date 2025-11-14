-- Version: 3
-- Description: Add production hardening features - advisory locks and resource quotas

-- UP

-- Advisory locks table for multi-user safety
CREATE TABLE IF NOT EXISTS advisory_locks (
    id SERIAL PRIMARY KEY,
    lock_key TEXT NOT NULL UNIQUE,        -- Unique identifier for the lock
    owner TEXT NOT NULL,                  -- Who owns the lock (user/session ID)
    acquired_at INTEGER NOT NULL,         -- When lock was acquired
    expires_at INTEGER,                   -- Optional expiration time
    metadata TEXT,                        -- JSON metadata about the lock

    -- Ensure only one lock per key
    UNIQUE(lock_key)
);

-- Resource quotas table
CREATE TABLE IF NOT EXISTS resource_quotas (
    id SERIAL PRIMARY KEY,
    project_id INTEGER,                   -- NULL for global quotas
    resource_type TEXT NOT NULL,          -- memory_count|episodic_events|procedures|entities|storage_mb
    quota_limit INTEGER NOT NULL,         -- Maximum allowed
    current_usage INTEGER DEFAULT 0,      -- Current usage
    last_updated INTEGER NOT NULL,

    -- Unique constraint per project+resource
    UNIQUE(project_id, resource_type),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Resource usage tracking
CREATE TABLE IF NOT EXISTS resource_usage_log (
    id SERIAL PRIMARY KEY,
    project_id INTEGER,
    resource_type TEXT NOT NULL,
    operation TEXT NOT NULL,              -- create|update|delete
    amount INTEGER NOT NULL,              -- Amount changed (+/-)
    timestamp INTEGER NOT NULL,
    metadata TEXT,                        -- JSON context

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Add quota enforcement columns to projects
ALTER TABLE projects ADD COLUMN quota_enforced BOOLEAN DEFAULT 1;
ALTER TABLE projects ADD COLUMN last_quota_check INTEGER;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_advisory_locks_key ON advisory_locks(lock_key);
CREATE INDEX IF NOT EXISTS idx_advisory_locks_owner ON advisory_locks(owner);
CREATE INDEX IF NOT EXISTS idx_advisory_locks_expires ON advisory_locks(expires_at);

CREATE INDEX IF NOT EXISTS idx_resource_quotas_project ON resource_quotas(project_id);
CREATE INDEX IF NOT EXISTS idx_resource_quotas_type ON resource_quotas(resource_type);

CREATE INDEX IF NOT EXISTS idx_resource_usage_project ON resource_usage_log(project_id);
CREATE INDEX IF NOT EXISTS idx_resource_usage_time ON resource_usage_log(timestamp DESC);

-- DOWN
-- Note: Rollback would need to be implemented manually for production safety</content>
</xai:function_call: write>
<parameter name="filePath">memory-mcp/migrations/002_add_production_hardening.sql