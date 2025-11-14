-- Version: 8
-- Description: Phase 9 Project Rules Engine - Initialize database schema

-- UP

-- Rule definitions table
CREATE TABLE IF NOT EXISTS project_rules (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,

    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,  -- coding_standard, process, security, deployment, resource, quality, custom
    rule_type TEXT NOT NULL,  -- constraint, pattern, threshold, approval, schedule, dependency, custom
    severity TEXT NOT NULL,   -- info, warning, error, critical

    condition TEXT NOT NULL,  -- JSON or expression
    exception_condition TEXT,

    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    created_by TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,

    auto_block INTEGER DEFAULT 1,
    can_override INTEGER DEFAULT 1,
    override_requires_approval INTEGER DEFAULT 0,

    tags TEXT,  -- JSON array
    related_rules TEXT,  -- JSON array of rule IDs
    documentation_url TEXT,

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, name)
);

CREATE INDEX IF NOT EXISTS idx_project_rules_project_id ON project_rules(project_id);
CREATE INDEX IF NOT EXISTS idx_project_rules_category ON project_rules(category);
CREATE INDEX IF NOT EXISTS idx_project_rules_enabled ON project_rules(enabled);

-- Rule validation history table
CREATE TABLE IF NOT EXISTS rule_validation_history (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,

    is_compliant INTEGER NOT NULL,
    violation_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,

    violations TEXT NOT NULL,  -- JSON array
    suggestions TEXT,  -- JSON array
    blocking_violations TEXT,  -- JSON array of rule IDs

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES prospective_tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_validation_history_task ON rule_validation_history(task_id);
CREATE INDEX IF NOT EXISTS idx_validation_history_project ON rule_validation_history(project_id);
CREATE INDEX IF NOT EXISTS idx_validation_history_compliant ON rule_validation_history(is_compliant);

-- Rule overrides table
CREATE TABLE IF NOT EXISTS rule_overrides (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    rule_id INTEGER NOT NULL,
    task_id INTEGER NOT NULL,

    overridden_at INTEGER NOT NULL,
    overridden_by TEXT NOT NULL,
    justification TEXT NOT NULL,

    approved_by TEXT,
    approval_at INTEGER,

    expires_at INTEGER,
    status TEXT DEFAULT 'active',  -- active, expired, revoked

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (rule_id) REFERENCES project_rules(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES prospective_tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_overrides_project ON rule_overrides(project_id);
CREATE INDEX IF NOT EXISTS idx_overrides_rule ON rule_overrides(rule_id);
CREATE INDEX IF NOT EXISTS idx_overrides_status ON rule_overrides(status);

-- Rule templates table
CREATE TABLE IF NOT EXISTS rule_templates (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    rules TEXT NOT NULL,  -- JSON array of Rule objects
    usage_count INTEGER DEFAULT 0,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_templates_category ON rule_templates(category);

-- Project rule configuration table
CREATE TABLE IF NOT EXISTS project_rule_config (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,

    enforcement_level TEXT DEFAULT 'warning',
    auto_suggest_compliant_alternatives INTEGER DEFAULT 1,
    auto_block_violations INTEGER DEFAULT 0,

    require_approval_for_override INTEGER DEFAULT 0,
    min_approvers INTEGER DEFAULT 1,
    approval_ttl_hours INTEGER DEFAULT 24,

    notify_on_violation INTEGER DEFAULT 1,
    notify_channels TEXT,  -- JSON array

    auto_generate_rules_from_patterns INTEGER DEFAULT 0,
    confidence_threshold_for_auto_rules REAL DEFAULT 0.85,

    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id)
);

CREATE INDEX IF NOT EXISTS idx_rule_config_project ON project_rule_config(project_id);

-- DOWN
-- Rollback: Drop all tables and indexes
DROP TABLE IF EXISTS project_rule_config;
DROP TABLE IF EXISTS rule_templates;
DROP TABLE IF EXISTS rule_overrides;
DROP TABLE IF EXISTS rule_validation_history;
DROP TABLE IF EXISTS project_rules;
