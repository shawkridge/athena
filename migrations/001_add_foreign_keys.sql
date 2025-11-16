-- Migration: Add Foreign Key Relationships to Episodic Memory
-- Purpose: Ensure data integrity and prevent orphaned records
-- Status: Safe (idempotent with IF NOT EXISTS checks)
-- Created: November 16, 2025

-- ============================================================================
-- 1. Link episodic_events to entities (entity_id)
-- ============================================================================

-- Add column if it doesn't exist
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'episodic_events' AND column_name = 'entity_id'
    ) THEN
        ALTER TABLE episodic_events ADD COLUMN entity_id INT;
    END IF;
END $$;

-- Create FK constraint if it doesn't exist
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name = 'episodic_events' AND constraint_name = 'fk_episodic_entity'
    ) THEN
        ALTER TABLE episodic_events
        ADD CONSTRAINT fk_episodic_entity
        FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE SET NULL;
    END IF;
END $$;

-- Create index for FK lookups
CREATE INDEX IF NOT EXISTS idx_episodic_entity
ON episodic_events(entity_id);

-- ============================================================================
-- 2. Link episodic_events to relation_ids (for causality chains)
-- ============================================================================

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'episodic_events' AND column_name = 'relation_id'
    ) THEN
        ALTER TABLE episodic_events ADD COLUMN relation_id INT;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name = 'episodic_events' AND constraint_name = 'fk_episodic_relation'
    ) THEN
        ALTER TABLE episodic_events
        ADD CONSTRAINT fk_episodic_relation
        FOREIGN KEY (relation_id) REFERENCES entity_relations(id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_episodic_relation
ON episodic_events(relation_id);

-- ============================================================================
-- 3. Link prospective_tasks to learned_pattern_id
-- ============================================================================

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'prospective_tasks' AND column_name = 'learned_pattern_id'
    ) THEN
        ALTER TABLE prospective_tasks ADD COLUMN learned_pattern_id INT;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name = 'prospective_tasks' AND constraint_name = 'fk_task_pattern'
    ) THEN
        ALTER TABLE prospective_tasks
        ADD CONSTRAINT fk_task_pattern
        FOREIGN KEY (learned_pattern_id) REFERENCES extracted_patterns(id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_prospective_pattern
ON prospective_tasks(learned_pattern_id);

-- ============================================================================
-- 4. Add cascading deletes to procedural_skills
-- ============================================================================

-- Drop old constraint if it exists (will be replaced)
ALTER TABLE IF EXISTS procedural_skills
DROP CONSTRAINT IF EXISTS learned_from_fk CASCADE;

-- Add new constraint with cascading deletes
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name = 'procedural_skills' AND constraint_name = 'fk_learned_from_event'
    ) THEN
        ALTER TABLE procedural_skills
        ADD CONSTRAINT fk_learned_from_event
        FOREIGN KEY (learned_from_event_id) REFERENCES episodic_events(id) ON DELETE CASCADE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_skill_learned_from
ON procedural_skills(learned_from_event_id);

-- ============================================================================
-- 5. Link consolidation_runs to extracted_patterns
-- ============================================================================

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name = 'extracted_patterns' AND constraint_name = 'fk_pattern_consolidation'
    ) THEN
        ALTER TABLE extracted_patterns
        ADD CONSTRAINT fk_pattern_consolidation
        FOREIGN KEY (consolidation_run_id) REFERENCES consolidation_runs(id) ON DELETE CASCADE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_pattern_consolidation
ON extracted_patterns(consolidation_run_id);

-- ============================================================================
-- VERIFICATION QUERIES (run these to verify)
-- ============================================================================

-- Verify FK columns exist:
-- SELECT column_name FROM information_schema.columns
-- WHERE table_name IN ('episodic_events', 'prospective_tasks', 'procedural_skills')
-- AND column_name IN ('entity_id', 'relation_id', 'learned_from_event_id', 'learned_pattern_id')
-- ORDER BY table_name;

-- Verify constraints exist:
-- SELECT constraint_name, table_name FROM information_schema.table_constraints
-- WHERE constraint_type = 'FOREIGN KEY'
-- AND constraint_name LIKE '%episodic%' OR constraint_name LIKE '%task%' OR constraint_name LIKE '%skill%'
-- ORDER BY table_name;

-- Verify indexes created:
-- SELECT indexname FROM pg_indexes WHERE tablename IN ('episodic_events', 'prospective_tasks', 'procedural_skills')
-- ORDER BY tablename, indexname;
