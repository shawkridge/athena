-- Version: 1
-- Description: Add reconsolidation support to memories table - Based on neuroscience research (Nader & Hardt 2009): memories become labile when retrieved

-- UP

-- Add new columns to memories table
ALTER TABLE memories ADD COLUMN last_retrieved INTEGER;
ALTER TABLE memories ADD COLUMN consolidation_state TEXT DEFAULT 'consolidated';
ALTER TABLE memories ADD COLUMN superseded_by INTEGER REFERENCES memories(id);
ALTER TABLE memories ADD COLUMN version INTEGER DEFAULT 1;

-- Create memory updates table for tracking reconsolidation history
CREATE TABLE IF NOT EXISTS memory_updates (
    id SERIAL PRIMARY KEY,
    original_id INTEGER NOT NULL,
    updated_id INTEGER NOT NULL,
    update_reason TEXT,
    confidence REAL DEFAULT 1.0,
    timestamp INTEGER NOT NULL,
    FOREIGN KEY (original_id) REFERENCES memories(id) ON DELETE CASCADE,
    FOREIGN KEY (updated_id) REFERENCES memories(id) ON DELETE CASCADE
);

-- Create index for finding update history
CREATE INDEX IF NOT EXISTS idx_memory_updates_original ON memory_updates(original_id);
CREATE INDEX IF NOT EXISTS idx_memory_updates_updated ON memory_updates(updated_id);

-- Create index for labile memories (for cleanup tasks)
CREATE INDEX IF NOT EXISTS idx_memories_consolidation_state ON memories(consolidation_state);
CREATE INDEX IF NOT EXISTS idx_memories_last_retrieved ON memories(last_retrieved);
