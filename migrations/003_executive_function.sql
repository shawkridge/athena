-- Version: 5
-- Migration: Phase 3 Executive Function Schema
-- Date: 2025-10-21
-- Description: Add goal hierarchy, task switching, progress monitoring, strategy selection

-- Core goal hierarchy
CREATE TABLE IF NOT EXISTS executive_goals (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    parent_goal_id INTEGER,
    goal_text TEXT NOT NULL,
    goal_type TEXT NOT NULL CHECK (goal_type IN ('primary', 'subgoal', 'maintenance')),
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'completed', 'failed', 'abandoned')),
    progress REAL DEFAULT 0.0 CHECK (progress >= 0.0 AND progress <= 1.0),
    estimated_hours REAL,
    actual_hours REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deadline TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_goal_id) REFERENCES executive_goals(id) ON DELETE SET NULL
);

-- Task switching events
CREATE TABLE IF NOT EXISTS task_switches (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    from_goal_id INTEGER,
    to_goal_id INTEGER NOT NULL,
    switch_cost_ms INTEGER,
    context_snapshot TEXT,  -- JSON of pinned working memory
    reason TEXT CHECK (reason IN ('priority_change', 'blocker', 'deadline', 'completion', 'user_request')),
    switched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (from_goal_id) REFERENCES executive_goals(id) ON DELETE SET NULL,
    FOREIGN KEY (to_goal_id) REFERENCES executive_goals(id) ON DELETE CASCADE
);

-- Progress milestones
CREATE TABLE IF NOT EXISTS progress_milestones (
    id SERIAL PRIMARY KEY,
    goal_id INTEGER NOT NULL,
    milestone_text TEXT NOT NULL,
    expected_progress REAL CHECK (expected_progress > 0.0 AND expected_progress <= 1.0),
    actual_progress REAL DEFAULT 0.0,
    target_date TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (goal_id) REFERENCES executive_goals(id) ON DELETE CASCADE
);

-- Strategy recommendations
CREATE TABLE IF NOT EXISTS strategy_recommendations (
    id SERIAL PRIMARY KEY,
    goal_id INTEGER NOT NULL,
    strategy_name TEXT NOT NULL CHECK (strategy_name IN (
        'top_down', 'bottom_up', 'spike', 'incremental', 'parallel',
        'sequential', 'deadline_driven', 'quality_first', 'collaboration', 'experimental'
    )),
    confidence REAL DEFAULT 0.5 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    model_version TEXT,
    recommended_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    outcome TEXT CHECK (outcome IS NULL OR outcome IN ('success', 'failure', 'pending')),
    FOREIGN KEY (goal_id) REFERENCES executive_goals(id) ON DELETE CASCADE
);

-- Executive function metrics
CREATE TABLE IF NOT EXISTS executive_metrics (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    metric_date DATE DEFAULT CURRENT_DATE,
    total_goals INTEGER DEFAULT 0,
    completed_goals INTEGER DEFAULT 0,
    abandoned_goals INTEGER DEFAULT 0,
    average_switch_cost_ms REAL DEFAULT 0.0,
    total_switch_overhead_ms INTEGER DEFAULT 0,
    average_goal_completion_hours REAL,
    success_rate REAL DEFAULT 0.0 CHECK (success_rate >= 0.0 AND success_rate <= 1.0),
    efficiency_score REAL DEFAULT 0.0 CHECK (efficiency_score >= 0.0 AND efficiency_score <= 100.0),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, metric_date)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_executive_goals_project ON executive_goals(project_id);
CREATE INDEX IF NOT EXISTS idx_executive_goals_parent ON executive_goals(parent_goal_id);
CREATE INDEX IF NOT EXISTS idx_executive_goals_status ON executive_goals(status);
CREATE INDEX IF NOT EXISTS idx_executive_goals_deadline ON executive_goals(deadline);
CREATE INDEX IF NOT EXISTS idx_task_switches_project ON task_switches(project_id);
CREATE INDEX IF NOT EXISTS idx_task_switches_from_to ON task_switches(from_goal_id, to_goal_id);
CREATE INDEX IF NOT EXISTS idx_task_switches_timestamp ON task_switches(switched_at);
CREATE INDEX IF NOT EXISTS idx_progress_milestones_goal ON progress_milestones(goal_id);
CREATE INDEX IF NOT EXISTS idx_strategy_recommendations_goal ON strategy_recommendations(goal_id);
CREATE INDEX IF NOT EXISTS idx_executive_metrics_project ON executive_metrics(project_id);
CREATE INDEX IF NOT EXISTS idx_executive_metrics_date ON executive_metrics(metric_date);

-- View: Active goals hierarchy
CREATE VIEW IF NOT EXISTS v_active_goals_tree AS
SELECT
    g.id,
    g.project_id,
    g.parent_goal_id,
    g.goal_text,
    g.priority,
    g.progress,
    g.deadline,
    g.estimated_hours,
    COUNT(DISTINCT child.id) as subgoal_count,
    MAX(child.progress) as max_subgoal_progress
FROM executive_goals g
LEFT JOIN executive_goals child ON child.parent_goal_id = g.id AND child.status != 'abandoned'
WHERE g.status IN ('active', 'suspended')
GROUP BY g.id;

-- View: Goals near deadline
CREATE VIEW IF NOT EXISTS v_urgent_goals AS
SELECT
    g.id,
    g.goal_text,
    g.priority,
    g.progress,
    g.deadline,
    CAST((JULIANDAY(g.deadline) - JULIANDAY('now')) AS INTEGER) as days_remaining,
    (1.0 - g.progress) as remaining_work
FROM executive_goals g
WHERE g.status = 'active'
AND g.deadline IS NOT NULL
AND g.deadline <= datetime('now', '+30 days')
ORDER BY g.deadline ASC;

-- View: Strategy effectiveness
CREATE VIEW IF NOT EXISTS v_strategy_effectiveness AS
SELECT
    strategy_name,
    COUNT(*) as total_recommendations,
    SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) as successes,
    ROUND(100.0 * SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) /
          COUNT(*), 2) as success_rate
FROM strategy_recommendations
WHERE outcome IS NOT NULL
GROUP BY strategy_name
ORDER BY success_rate DESC;
