-- Migration: Temporal Decay Compression Layer
-- Version: 6
-- Date: 2025-10-23
-- Description: Add temporal decay compression support to semantic_memories table
--
-- Temporal decay allows memories to compress based on age:
-- - < 7 days: 100% fidelity (no compression)
-- - 7-30 days: ~50% compression (detailed summary)
-- - 30-90 days: ~80% compression (gist only)
-- > 90 days: ~95% compression (reference only)

-- ============================================================================
-- Temporal Decay Compression Columns
-- ============================================================================

-- Add compression support to memories (SQLite requires separate ALTER TABLE per column)
ALTER TABLE memories ADD COLUMN content_compressed TEXT;
ALTER TABLE memories ADD COLUMN compression_level INTEGER DEFAULT 0 CHECK (compression_level >= 0 AND compression_level <= 3);
ALTER TABLE memories ADD COLUMN compression_timestamp TIMESTAMP DEFAULT NULL;
ALTER TABLE memories ADD COLUMN compression_tokens_saved REAL DEFAULT NULL;

-- Create indices for efficient age-based queries
CREATE INDEX IF NOT EXISTS idx_memories_compression_level
ON memories(compression_level);

CREATE INDEX IF NOT EXISTS idx_memories_compression_timestamp
ON memories(compression_timestamp);

-- Index for finding memories by age (created_at) - used by temporal decay
CREATE INDEX IF NOT EXISTS idx_memories_created_at
ON memories(created_at DESC);

-- Index for retrieving old memories that need compression
-- Note: WHERE clause removed because SQLite doesn't allow non-deterministic datetime() in indexes
CREATE INDEX IF NOT EXISTS idx_memories_age_uncompressed
ON memories(created_at)
WHERE compression_level = 0;

-- ============================================================================
-- Validation & Backward Compatibility
-- ============================================================================

-- Existing memories are marked as uncompressed (level 0)
-- Columns are nullable for backward compatibility
-- Automatic compression applied during retrieval (lazy evaluation)

-- ============================================================================
-- Migration Info
-- ============================================================================

-- Rollback: DROP INDEX idx_memories_compression_level;
--           DROP INDEX idx_memories_compression_timestamp;
--           DROP INDEX idx_memories_created_at;
--           DROP INDEX idx_memories_age_uncompressed;
--           ALTER TABLE memories DROP COLUMN content_compressed;
--           ALTER TABLE memories DROP COLUMN compression_level;
--           ALTER TABLE memories DROP COLUMN compression_timestamp;
--           ALTER TABLE memories DROP COLUMN compression_tokens_saved;
