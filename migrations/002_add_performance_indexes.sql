-- Migration: Add Composite Indexes for Hot Query Paths
-- Purpose: Improve query performance (30-40% latency reduction expected)
-- Status: Safe (idempotent, concurrent creation)
-- Created: November 16, 2025

-- ============================================================================
-- Episodic Events - Temporal Queries (CRITICAL)
-- ============================================================================
-- Used by: Consolidation, historical queries, temporal analysis
-- Expected improvement: 40-50% for temporal range queries

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_episodic_temporal
ON episodic_events(project_id, timestamp DESC)
WHERE lifecycle_status = 'active';

-- Alternative for recent events
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_episodic_recent
ON episodic_events(project_id, timestamp DESC)
INCLUDE (importance_score, consolidation_status);

-- ============================================================================
-- Episodic Events - Consolidation Queries
-- ============================================================================
-- Used by: Consolidation pipeline, pattern extraction
-- Expected improvement: 30-40% for consolidation queries

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_episodic_consolidation
ON episodic_events(consolidation_status, confidence)
WHERE lifecycle_status = 'active';

-- ============================================================================
-- Entity Relations - Graph Traversal (CRITICAL)
-- ============================================================================
-- Used by: Graph queries, relationship lookups, pathfinding
-- Expected improvement: 50%+ for graph traversal (prevents Cartesian join)

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entity_relations_from
ON entity_relations(from_entity_id, relation_type);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entity_relations_to
ON entity_relations(to_entity_id, relation_type);

-- Partial index for active relations only
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entity_relations_active
ON entity_relations(from_entity_id, to_entity_id)
WHERE valid_until IS NULL;

-- ============================================================================
-- Prospective Tasks - Active Task Filtering (CRITICAL)
-- ============================================================================
-- Used by: Task queries, active task listing, priority filtering
-- Expected improvement: 40-50% for task filtering

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prospective_active
ON prospective_tasks(project_id, status, priority, due_at)
WHERE status != 'COMPLETED';

-- Alternative for blocking analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prospective_blocked
ON prospective_tasks(project_id, blocked_reason)
WHERE blocked_reason IS NOT NULL;

-- ============================================================================
-- Entities - Project + Recency
-- ============================================================================
-- Used by: Entity lookups, recent entity queries
-- Expected improvement: 20-30% for entity filtering

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entities_project_recent
ON entities(project_id, updated_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entities_type
ON entities(entity_type, project_id);

-- ============================================================================
-- Procedural Skills - Lookup
-- ============================================================================
-- Used by: Skill matching, pattern recommendations
-- Expected improvement: 20% for skill queries

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_procedural_category
ON procedural_skills(category, success_rate DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_procedural_learned_from
ON procedural_skills(learned_from_event_id);

-- ============================================================================
-- Extracted Patterns - Consolidation Runs
-- ============================================================================
-- Used by: Pattern retrieval, consolidation analysis
-- Expected improvement: 20% for pattern queries

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pattern_consolidation_run
ON extracted_patterns(consolidation_run_id, pattern_type);

-- ============================================================================
-- Semantic Memories - Full Text Search (OPTIONAL)
-- ============================================================================
-- Used by: Full text search queries
-- Note: Only create if using full-text search frequently

-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_semantic_fts
-- ON semantic_memories USING GIN(to_tsvector('english', content));

-- ============================================================================
-- QUERY STATISTICS (Run these to verify index effectiveness)
-- ============================================================================

-- Check index creation status:
-- SELECT schemaname, tablename, indexname, idx_scan as scans, idx_tup_read as reads
-- FROM pg_stat_user_indexes
-- WHERE tablename IN ('episodic_events', 'entity_relations', 'prospective_tasks', 'entities', 'procedural_skills', 'extracted_patterns')
-- ORDER BY tablename, indexname;

-- Check missing indexes (columns that should have them):
-- SELECT schemaname, tablename, attname
-- FROM pg_stat_user_tables t
-- JOIN pg_attribute a ON t.relid = a.attrelid
-- WHERE schemaname = 'public'
-- AND t.n_live_tup > 10000
-- AND a.attname IN ('project_id', 'status', 'priority', 'timestamp', 'entity_type')
-- ORDER BY t.relname, a.attname;

-- ============================================================================
-- PERFORMANCE BASELINE (Run before/after migration)
-- ============================================================================

-- Before: SELECT COUNT(*) FROM episodic_events WHERE project_id = 1 AND timestamp > NOW() - INTERVAL '7 days';
-- After: Should see reduced query time due to idx_episodic_temporal

-- Before: SELECT * FROM prospective_tasks WHERE project_id = 1 AND status = 'ACTIVE' ORDER BY priority DESC;
-- After: Should see reduced query time due to idx_prospective_active

-- Before: SELECT r.* FROM entity_relations r WHERE r.from_entity_id = 123;
-- After: Should see reduced query time due to idx_entity_relations_from
