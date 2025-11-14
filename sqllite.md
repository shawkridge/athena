📋 COMPREHENSIVE SQLITE PATTERNS TO FIX
🔴 CRITICAL: SQL Syntax Issues (Will Cause Runtime Failures)
1. SQLite datetime() Functions → PostgreSQL NOW()/CURRENT_TIMESTAMP
15 files, 20+ instances
| File | Line | Current SQLite | PostgreSQL Fix |
|------|------|----------------|----------------|
| src/athena/working_memory/central_executive.py | 266 | datetime('now') | NOW() |
| src/athena/working_memory/central_executive.py | 402 | datetime('now') | NOW() |
| src/athena/performance/query_optimizer.py | 70 | datetime('now', '-7 days') | NOW() - INTERVAL '7 days' |
| src/athena/mcp/handlers_episodic.py | 132 | datetime('now', '-5 minutes') | NOW() - INTERVAL '5 minutes' |
| src/athena/tools/memory/store.py | 197 | datetime('now') | NOW() |
| src/athena/consolidation/dream_metrics.py | 213 | datetime('now', '-7 days') | NOW() - INTERVAL '7 days' |
| src/athena/consolidation/dream_metrics.py | 312 | `datetime('now', ? || ' days')` | NOW() - INTERVAL '%s days' |
| src/athena/working_memory/visuospatial_sketchpad.py | 398 | datetime('now') | NOW() |
| src/athena/associations/priming.py | 68,79,130,214,241 | datetime('now', 'utc') | NOW() AT TIME ZONE 'UTC' |
| src/athena/filesystem_api/operations/health_check.py | 129 | datetime('now', '-24 hours') | NOW() - INTERVAL '24 hours' |
| src/athena/rag/context_injector.py | 340 | datetime('now') | NOW() |
2. SQLite julianday() Functions → PostgreSQL Date Math
3 files, 3 instances
| File | Line | Current SQLite | PostgreSQL Fix |
|------|------|----------------|----------------|
| src/athena/filesystem_api/layers/episodic/timeline.py | 155 | julianday(timestamp) - julianday(%s) | EXTRACT(EPOCH FROM (timestamp - %s))/86400 |
| src/athena/memory/optimize.py | 40 | julianday('now') - julianday(created_at, 'unixepoch') | EXTRACT(EPOCH FROM (NOW() - created_at))/86400 |
| src/athena/memory/optimize.py | 46 | julianday('now') - julianday(last_accessed, 'unixepoch') | EXTRACT(EPOCH FROM (NOW() - last_accessed))/86400 |
3. SQLite INTEGER PRIMARY KEY → PostgreSQL SERIAL PRIMARY KEY
20+ files, 53+ instances
| File | Count | Pattern | Fix |
|------|-------|---------|-----|
| src/athena/procedural/pattern_store.py | 6 | id INTEGER PRIMARY KEY, | id SERIAL PRIMARY KEY, |
| src/athena/ide_context/store.py | 6 | id INTEGER PRIMARY KEY, | id SERIAL PRIMARY KEY, |
| src/athena/procedural/versioning.py | 1 | id INTEGER PRIMARY KEY, | id SERIAL PRIMARY KEY, |
| src/athena/reflection/scheduler.py | 2 | id INTEGER PRIMARY KEY, | id SERIAL PRIMARY KEY, |
| src/athena/temporal/git_store.py | 6 | id INTEGER PRIMARY KEY, | id SERIAL PRIMARY KEY, |
| src/athena/associations/zettelkasten.py | 3 | id INTEGER PRIMARY KEY, | id SERIAL PRIMARY KEY, |
| src/athena/code_artifact/store.py | 9 | id INTEGER PRIMARY KEY, | id SERIAL PRIMARY KEY, |
| src/athena/ai_coordination/integration/action_cycle_enhancer.py | 2 | id INTEGER PRIMARY KEY, | id SERIAL PRIMARY KEY, |
| src/athena/ai_coordination/integration/graph_linking.py | 2 | id INTEGER PRIMARY KEY, | id SERIAL PRIMARY KEY, |
| src/athena/ai_coordination/integration/temporal_chaining.py | 2 | id INTEGER PRIMARY KEY, | id SERIAL PRIMARY KEY, |
| src/athena/ai_coordination/integration/event_forwarder_store.py | 2 | id INTEGER PRIMARY KEY, | id SERIAL PRIMARY KEY, |
| src/athena/ai_coordination/integration/spatial_grounding.py | 2 | id INTEGER PRIMARY KEY, | id SERIAL PRIMARY KEY, |
| src/athena/ai_coordination/integration/smart_recall.py | 2 | id INTEGER PRIMARY KEY, | id SERIAL PRIMARY KEY, |
| src/athena/ai_coordination/integration/learning_pathway.py | 2 | id INTEGER PRIMARY KEY, | id SERIAL PRIMARY KEY, |
| src/athena/ai_coordination/integration/procedure_auto_creator.py | 2 | id INTEGER PRIMARY KEY, | id SERIAL PRIMARY KEY, |
| src/athena/ai_coordination/integration/prospective_integration.py | 2 | id SERIAL PRIMARY KEY, | id SERIAL PRIMARY KEY, |
| src/athena/ai_coordination/integration/consolidation_trigger.py | 3 | id INTEGER PRIMARY KEY, | id SERIAL PRIMARY KEY, |
🟡 MEDIUM: Code Comments & References
4. Comments Referencing SQLite Support
6 files, 6 instances
| File | Line | Current | Fix |
|------|------|---------|-----|
| src/athena/working_memory/central_executive.py | 30,34 | SQLite or Postgres | PostgreSQL |
| src/athena/working_memory/visuospatial_sketchpad.py | 36 | SQLite or Postgres | PostgreSQL |
| src/athena/working_memory/phonological_loop.py | 37 | SQLite or Postgres | PostgreSQL |
| src/athena/working_memory/episodic_buffer.py | 40 | SQLite or Postgres | PostgreSQL |
| src/athena/working_memory/consolidation_router.py | 51 | SQLite or Postgres | PostgreSQL |
5. SQLite-Specific Timestamp Handling
2 files, 4 instances
| File | Line | Current | Fix |
|------|------|---------|-----|
| src/athena/learning/hebbian.py | 256 | Normalize to SQLite format | Normalize to PostgreSQL format |
| src/athena/associations/priming.py | 89,141,144 | SQLite timestamp normalization | PostgreSQL timestamp handling |
6. Schema Validation Code
1 file, 2 instances
| File | Line | Current | Fix |
|------|------|---------|-----|
| src/athena/compression/schema.py | 54,122 | db_path: Path to SQLite database | db_path: Path to PostgreSQL database |
🟢 LOW: Documentation & Comments
7. Informational Comments
7 files, 7 instances
| File | Line | Current | Fix |
|------|------|---------|-----|
| src/athena/mcp/handlers.py | 213 | PostgreSQL-only backend (SQLite removed) | Keep as-is (accurate) |
| src/athena/core/database_factory.py | 4 | No SQLite fallback. | Keep as-is (accurate) |
| src/athena/core/config.py | 10 | SQLite and Qdrant backends have been removed. | Keep as-is (accurate) |
| src/athena/episodic/store.py | 68 | SQLite integer (0/1) to boolean | PostgreSQL boolean handling |
| src/athena/core/database_postgres.py | 115 | not SQLite ? | not SQLite ? placeholders |
| src/athena/core/database.py | 1 | PostgreSQL only (no SQLite). | Keep as-is (accurate) |
| src/athena/core/__init__.py | 3 | PostgreSQL only (local or Docker) | PostgreSQL only (localhost) |
| src/athena/symbols/symbol_store.py | 10 | SQLite support has been removed. | Keep as-is (accurate) |
| src/athena/planning/postgres_planning_integration.py | 72 | PostgreSQL or SQLite | PostgreSQL |
| src/athena/code_search/postgres_code_integration.py | 55 | PostgreSQL or SQLite | PostgreSQL |
---
📊 SUMMARY STATISTICS
| Category | Files | Instances | Priority |
|----------|-------|-----------|----------|
| SQL datetime() functions | 11 | 20+ | 🔴 CRITICAL |
| SQL julianday() functions | 2 | 3 | 🔴 CRITICAL |
| Schema PRIMARY KEY | 17 | 53+ | 🔴 CRITICAL |
| Comments "SQLite or Postgres" | 5 | 6 | 🟡 MEDIUM |
| Timestamp handling code | 2 | 4 | 🟡 MEDIUM |
| Schema validation comments | 1 | 2 | 🟡 MEDIUM |
| Informational comments | 10 | 10 | 🟢 LOW |
Total: 48 files, 98+ instances
🎯 EXECUTION ORDER
1. Phase 1 (CRITICAL): Fix SQL syntax (datetime, julianday, PRIMARY KEY) - Will prevent runtime failures
2. Phase 2 (MEDIUM): Update comments and timestamp handling - Code clarity
3. Phase 3 (LOW): Clean up remaining references - Documentation polish
This comprehensive list provides everything needed to complete the SQLite removal from the codebase.
