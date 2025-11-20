-- Migration: Advanced Scheduling Infrastructure
-- Purpose: Add priority queuing, task dependencies, and workflow templates
-- Date: 2025-11-20

-- 1. Add task dependency tracking table
CREATE TABLE IF NOT EXISTS task_dependencies (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES prospective_tasks(id) ON DELETE CASCADE,
    depends_on_task_id INTEGER NOT NULL REFERENCES prospective_tasks(id) ON DELETE CASCADE,
    dependency_type TEXT NOT NULL DEFAULT 'blocks',  -- 'blocks', 'triggers', 'requires'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(task_id, depends_on_task_id),
    CHECK (task_id != depends_on_task_id)
);

CREATE INDEX IF NOT EXISTS idx_task_dependencies_task
ON task_dependencies(task_id);

CREATE INDEX IF NOT EXISTS idx_task_dependencies_depends_on
ON task_dependencies(depends_on_task_id);

-- 2. Add workflow templates table
CREATE TABLE IF NOT EXISTS workflow_templates (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    template_json TEXT NOT NULL,  -- JSON with task structure and dependencies
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Enhance prospective_tasks with scheduling fields
DO $$
BEGIN
    -- Add priority field (normalize to 1-10 integer if not exists)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'prospective_tasks' AND column_name = 'priority_number'
    ) THEN
        ALTER TABLE prospective_tasks
        ADD COLUMN priority_number INTEGER DEFAULT 5 CHECK (priority_number >= 1 AND priority_number <= 10);
    END IF;

    -- Add depends_on_task_id field
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'prospective_tasks' AND column_name = 'depends_on_task_id'
    ) THEN
        ALTER TABLE prospective_tasks
        ADD COLUMN depends_on_task_id INTEGER REFERENCES prospective_tasks(id) ON DELETE SET NULL;
    END IF;

    -- Add estimated_duration_minutes field
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'prospective_tasks' AND column_name = 'estimated_duration_minutes'
    ) THEN
        ALTER TABLE prospective_tasks
        ADD COLUMN estimated_duration_minutes INTEGER;
    END IF;

    -- Add resource_requirements field (JSON)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'prospective_tasks' AND column_name = 'resource_requirements'
    ) THEN
        ALTER TABLE prospective_tasks
        ADD COLUMN resource_requirements TEXT;  -- JSON: {"agent_types": ["research"], "memory_mb": 512}
    END IF;

    -- Add template_id field
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'prospective_tasks' AND column_name = 'template_id'
    ) THEN
        ALTER TABLE prospective_tasks
        ADD COLUMN template_id INTEGER REFERENCES workflow_templates(id) ON DELETE SET NULL;
    END IF;
END $$;

-- 4. Create index for priority-based queuing
CREATE INDEX IF NOT EXISTS idx_tasks_priority_queue
ON prospective_tasks(priority_number DESC, created_at ASC)
WHERE status = 'PENDING';

-- 5. Create index for dependency queries
CREATE INDEX IF NOT EXISTS idx_tasks_depends_on
ON prospective_tasks(depends_on_task_id)
WHERE depends_on_task_id IS NOT NULL;

-- 6. Helper function: Get tasks ready to execute (dependencies satisfied)
CREATE OR REPLACE FUNCTION get_ready_tasks(
    limit_count INT DEFAULT 10
)
RETURNS TABLE(
    task_id INTEGER,
    content TEXT,
    priority_number INTEGER,
    estimated_duration_minutes INTEGER,
    resource_requirements TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.id,
        t.content,
        t.priority_number,
        t.estimated_duration_minutes,
        t.resource_requirements
    FROM prospective_tasks t
    WHERE t.status = 'PENDING'
      AND (t.depends_on_task_id IS NULL
           OR EXISTS (
               SELECT 1 FROM prospective_tasks dep
               WHERE dep.id = t.depends_on_task_id
               AND dep.status = 'COMPLETED'
           ))
    ORDER BY t.priority_number DESC, t.created_at ASC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- 7. Helper function: Get task dependency graph
CREATE OR REPLACE FUNCTION get_task_dependency_graph(
    root_task_id INT
)
RETURNS TABLE(
    task_id INTEGER,
    depth INTEGER,
    dependency_type TEXT
) AS $$
WITH RECURSIVE task_graph AS (
    SELECT id, 1 as depth, 'self'::TEXT as dep_type
    FROM prospective_tasks
    WHERE id = root_task_id

    UNION ALL

    SELECT
        td.depends_on_task_id,
        tg.depth + 1,
        td.dependency_type
    FROM task_dependencies td
    JOIN task_graph tg ON td.task_id = tg.task_id
    WHERE tg.depth < 10  -- Prevent infinite recursion
)
SELECT task_id, depth, dep_type
FROM task_graph
WHERE task_id != root_task_id;
$$ LANGUAGE sql;

-- 8. Helper function: Calculate estimated completion time
CREATE OR REPLACE FUNCTION estimate_task_completion(
    task_id_param INTEGER
)
RETURNS TABLE(
    task_id INTEGER,
    estimated_completion_minutes INTEGER,
    critical_path_minutes INTEGER
) AS $$
DECLARE
    v_duration INTEGER;
    v_critical_path INTEGER := 0;
    v_dep_id INTEGER;
BEGIN
    SELECT estimated_duration_minutes INTO v_duration
    FROM prospective_tasks WHERE id = task_id_param;

    -- If no dependencies, just return the duration
    IF v_duration IS NULL THEN
        RETURN QUERY SELECT task_id_param, NULL::INTEGER, NULL::INTEGER;
        RETURN;
    END IF;

    -- Get longest dependency chain
    SELECT COALESCE(MAX(estimated_duration_minutes), 0)
    INTO v_critical_path
    FROM prospective_tasks
    WHERE id IN (
        SELECT depends_on_task_id FROM task_dependencies
        WHERE task_id = task_id_param
    );

    RETURN QUERY
    SELECT task_id_param, v_duration, v_critical_path + v_duration;
END;
$$ LANGUAGE plpgsql;

-- 9. Insert some default workflow templates
INSERT INTO workflow_templates (name, description, template_json)
VALUES
(
    'Research & Analysis',
    'Standard workflow: research topic → analyze findings → synthesize results',
    '{"phases": ["research", "analysis", "synthesis"], "dependencies": [[1,2], [2,3]]}'::TEXT
),
(
    'Data Processing Pipeline',
    'ETL workflow: extract → transform → load → validate',
    '{"phases": ["extract", "transform", "load", "validate"], "dependencies": [[1,2], [2,3], [3,4]]}'::TEXT
),
(
    'Code Review Flow',
    'Review workflow: analyze → test → review → merge',
    '{"phases": ["analyze", "test", "review", "merge"], "dependencies": [[1,2], [2,3], [3,4]]}'::TEXT
)
ON CONFLICT (name) DO NOTHING;
