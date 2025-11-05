-- Migration: Consolidation Compression Layer
-- Version: 7
-- Date: 2025-10-23
-- Description: Add consolidation compression support for executive summaries
--
-- During consolidation, generate two outputs:
-- 1. Full semantic memory (original behavior)
-- 2. Compressed executive summary (new - ~20 tokens)
--
-- This enables massive context savings during retrieval while preserving
-- the ability to get full context on demand.

-- ============================================================================
-- Consolidation Compression Columns
-- ============================================================================

-- Add consolidation compression support to memories (SQLite requires separate ALTER TABLE per column)
ALTER TABLE memories ADD COLUMN content_executive TEXT;
ALTER TABLE memories ADD COLUMN compression_source_events TEXT DEFAULT NULL;
ALTER TABLE memories ADD COLUMN compression_generated_at TIMESTAMP DEFAULT NULL;

-- Create indices for consolidation retrieval
CREATE INDEX IF NOT EXISTS idx_memories_compression_generated_at
ON memories(compression_generated_at DESC);

-- Index for finding consolidated memories with executive summaries
CREATE INDEX IF NOT EXISTS idx_memories_has_executive
ON memories(compression_generated_at)
WHERE content_executive IS NOT NULL;

-- ============================================================================
-- Consolidation Compression Quality Tracking
-- ============================================================================

-- Optional: Create consolidation_metrics table for tracking compression quality
CREATE TABLE IF NOT EXISTS consolidation_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id INTEGER NOT NULL,
    compression_ratio REAL NOT NULL,  -- compressed_length / full_length
    fidelity_score REAL NOT NULL CHECK (fidelity_score >= 0.0 AND fidelity_score <= 1.0),
    tokens_original INTEGER,
    tokens_compressed INTEGER,
    source_events_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_consolidation_metrics_memory_id
ON consolidation_metrics(memory_id);

CREATE INDEX IF NOT EXISTS idx_consolidation_metrics_fidelity
ON consolidation_metrics(fidelity_score DESC);

-- ============================================================================
-- Validation & Backward Compatibility
-- ============================================================================

-- Existing memories are marked as uncompressed (content_executive is NULL)
-- Columns are nullable for backward compatibility
-- Executive summaries auto-generated during consolidation

-- ============================================================================
-- Migration Info
-- ============================================================================

-- Rollback: DROP TABLE consolidation_metrics;
--           DROP INDEX idx_consolidation_metrics_memory_id;
--           DROP INDEX idx_consolidation_metrics_fidelity;
--           DROP INDEX idx_memories_compression_generated_at;
--           DROP INDEX idx_memories_has_executive;
--           ALTER TABLE memories DROP COLUMN content_executive;
--           ALTER TABLE memories DROP COLUMN compression_source_events;
--           ALTER TABLE memories DROP COLUMN compression_generated_at;
