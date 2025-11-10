"""SQLite database with sqlite-vec for vector storage."""

import json
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import sqlite_vec

from .models import Memory, MemoryType, Project
from . import config


class Database:
    """SQLite database manager with vector support."""

    def __init__(self, db_path: str | Path):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Load sqlite-vec extension
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.conn.enable_load_extension(False)

        self._init_schema()

    def _init_schema(self):
        """Create database schema if not exists."""
        cursor = self.conn.cursor()

        # Get embedding dimension from config (standardized to 768D)
        embedding_dim = getattr(config, 'LLAMACPP_EMBEDDING_DIM', 768)

        # Projects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                path TEXT UNIQUE NOT NULL,
                created_at INTEGER NOT NULL,
                last_accessed INTEGER NOT NULL,
                memory_count INTEGER DEFAULT 0
            )
        """)

        # Memory metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                tags TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                last_accessed INTEGER,
                access_count INTEGER DEFAULT 0,
                usefulness_score REAL DEFAULT 0.0,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        # Vector embeddings virtual table - use configured embedding dimension
        cursor.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS memory_vectors USING vec0(
                embedding FLOAT[{embedding_dim}]
            )
        """)

        # Memory relationships
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_relations (
                from_memory_id INTEGER NOT NULL,
                to_memory_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                PRIMARY KEY (from_memory_id, to_memory_id),
                FOREIGN KEY (from_memory_id) REFERENCES memories(id) ON DELETE CASCADE,
                FOREIGN KEY (to_memory_id) REFERENCES memories(id) ON DELETE CASCADE
            )
        """)

        # Optimization stats
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS optimization_stats (
                project_id INTEGER PRIMARY KEY,
                last_optimized INTEGER,
                memories_pruned INTEGER DEFAULT 0,
                avg_usefulness REAL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_score ON memories(usefulness_score DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_accessed ON memories(last_accessed DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)"
        )

        # Episodic memory tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodic_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                content TEXT NOT NULL,
                outcome TEXT,
                context_cwd TEXT,
                context_files TEXT,
                context_task TEXT,
                context_phase TEXT,
                context_branch TEXT,
                duration_ms INTEGER,
                files_changed INTEGER DEFAULT 0,
                lines_added INTEGER DEFAULT 0,
                lines_deleted INTEGER DEFAULT 0,
                learned TEXT,
                confidence REAL DEFAULT 1.0,
                surprise_score REAL,
                surprise_normalized REAL,
                surprise_coherence REAL,
                consolidation_status TEXT DEFAULT 'unconsolidated',
                consolidated_at INTEGER,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value TEXT NOT NULL,
                FOREIGN KEY (event_id) REFERENCES episodic_events(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_relations (
                from_event_id INTEGER NOT NULL,
                to_event_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                PRIMARY KEY (from_event_id, to_event_id),
                FOREIGN KEY (from_event_id) REFERENCES episodic_events(id) ON DELETE CASCADE,
                FOREIGN KEY (to_event_id) REFERENCES episodic_events(id) ON DELETE CASCADE
            )
        """)

        cursor.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS event_vectors USING vec0(
                embedding FLOAT[{embedding_dim}]
            )
        """)

        # Event content hashes for deduplication (pipeline support)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_hashes (
                event_id INTEGER PRIMARY KEY,
                content_hash TEXT NOT NULL UNIQUE,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (event_id) REFERENCES episodic_events(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON episodic_events(timestamp DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_project ON episodic_events(project_id, timestamp DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_session ON episodic_events(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON episodic_events(event_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_hashes_content ON event_hashes(content_hash)")

        # Migrate existing episodic_events table if consolidation_status column is missing
        cursor.execute("PRAGMA table_info(episodic_events)")
        columns = {row[1] for row in cursor.fetchall()}
        if "consolidation_status" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN consolidation_status TEXT DEFAULT 'unconsolidated'")
        if "consolidated_at" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN consolidated_at INTEGER")

        # Add code-aware columns for enhanced code event tracking
        if "code_event_type" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN code_event_type TEXT")
        if "file_path" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN file_path TEXT")
        if "symbol_name" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN symbol_name TEXT")
        if "symbol_type" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN symbol_type TEXT")
        if "language" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN language TEXT")
        if "diff" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN diff TEXT")
        if "git_commit" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN git_commit TEXT")
        if "git_author" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN git_author TEXT")
        if "test_name" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN test_name TEXT")
        if "test_passed" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN test_passed INTEGER")  # SQLite boolean as 0/1
        if "error_type" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN error_type TEXT")
        if "stack_trace" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN stack_trace TEXT")
        if "performance_metrics" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN performance_metrics TEXT")  # JSON string
        if "code_quality_score" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN code_quality_score REAL")

        # Add orchestration task queue columns for multi-agent coordination
        if "task_id" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN task_id TEXT")
        if "task_type" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN task_type TEXT")
        if "task_status" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN task_status TEXT DEFAULT 'pending'")
        if "assigned_to" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN assigned_to TEXT")
        if "assigned_at" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN assigned_at INTEGER")
        if "priority" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN priority TEXT DEFAULT 'medium'")
        if "requirements" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN requirements TEXT")
        if "dependencies" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN dependencies TEXT")
        if "started_at" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN started_at INTEGER")
        if "completed_at" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN completed_at INTEGER")
        if "error_message" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN error_message TEXT")
        if "retry_count" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN retry_count INTEGER DEFAULT 0")
        if "execution_duration_ms" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN execution_duration_ms INTEGER")
        if "success" not in columns:
            cursor.execute("ALTER TABLE episodic_events ADD COLUMN success BOOLEAN")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_consolidation ON episodic_events(project_id, consolidation_status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_code_type ON episodic_events(code_event_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_symbol ON episodic_events(file_path, symbol_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_language ON episodic_events(language)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_git_commit ON episodic_events(git_commit)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_task_status ON episodic_events(task_status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_assigned_to ON episodic_events(assigned_to)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_task_type ON episodic_events(task_type)")

        # Working memory tables (supporting phonological loop and visuospatial sketchpad)
        # Schema must match WorkingMemoryItem model in models.py
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS working_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                content_type TEXT NOT NULL DEFAULT 'verbal',
                component TEXT NOT NULL DEFAULT 'phonological',
                activation_level REAL NOT NULL DEFAULT 1.0 CHECK(activation_level >= 0.0 AND activation_level <= 1.0),
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                last_accessed TEXT NOT NULL DEFAULT (datetime('now')),
                decay_rate REAL DEFAULT 0.1,
                importance_score REAL NOT NULL DEFAULT 0.5 CHECK(importance_score >= 0.0 AND importance_score <= 1.0),
                embedding BLOB,
                metadata TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_working_memory_project ON working_memory(project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_working_memory_type ON working_memory(content_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_working_memory_component ON working_memory(component)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_working_memory_importance ON working_memory(importance_score DESC)")

        # Create view for working memory with activation calculations
        # Used by phonological_loop and visuospatial_sketchpad for decay calculations
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS v_working_memory_current AS
            SELECT
                id,
                project_id,
                content,
                content_type,
                component,
                activation_level,
                created_at,
                last_accessed,
                decay_rate,
                importance_score,
                embedding,
                metadata,
                CAST((julianday('now') - julianday(last_accessed)) * 86400 AS INTEGER) as seconds_since_access,
                activation_level * EXP(-decay_rate * (1 - importance_score * 0.5) *
                    CAST((julianday('now') - julianday(last_accessed)) * 86400 AS REAL)) as current_activation
            FROM working_memory
        """)

        # Procedural memory tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS procedures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                description TEXT,
                trigger_pattern TEXT,
                applicable_contexts TEXT,
                template TEXT NOT NULL,
                steps TEXT,
                examples TEXT,
                success_rate REAL DEFAULT 0.0,
                usage_count INTEGER DEFAULT 0,
                avg_completion_time_ms INTEGER,
                created_at INTEGER NOT NULL,
                last_used INTEGER,
                created_by TEXT DEFAULT 'user'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS procedure_params (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                procedure_id INTEGER NOT NULL,
                param_name TEXT NOT NULL,
                param_type TEXT NOT NULL,
                required BOOLEAN DEFAULT 1,
                default_value TEXT,
                description TEXT,
                FOREIGN KEY (procedure_id) REFERENCES procedures(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS procedure_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                procedure_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                timestamp INTEGER NOT NULL,
                outcome TEXT NOT NULL,
                duration_ms INTEGER,
                variables TEXT,
                learned TEXT,
                FOREIGN KEY (procedure_id) REFERENCES procedures(id) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_procedures_category ON procedures(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_procedures_usage ON procedures(usage_count DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_executions_procedure ON procedure_executions(procedure_id)")

        # Prospective memory tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prospective_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                active_form TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                due_at INTEGER,
                completed_at INTEGER,
                status TEXT NOT NULL,
                priority TEXT NOT NULL,
                assignee TEXT DEFAULT 'claude',
                notes TEXT,
                blocked_reason TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_triggers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                trigger_type TEXT NOT NULL,
                trigger_value TEXT,
                trigger_condition TEXT,
                fired BOOLEAN DEFAULT 0,
                fired_at INTEGER,
                FOREIGN KEY (task_id) REFERENCES prospective_tasks(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_dependencies (
                task_id INTEGER NOT NULL,
                depends_on_task_id INTEGER NOT NULL,
                dependency_type TEXT DEFAULT 'blocks',
                PRIMARY KEY (task_id, depends_on_task_id),
                FOREIGN KEY (task_id) REFERENCES prospective_tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (depends_on_task_id) REFERENCES prospective_tasks(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON prospective_tasks(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON prospective_tasks(priority)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due ON prospective_tasks(due_at)")

        # Knowledge graph tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                project_id INTEGER,
                updated_at INTEGER NOT NULL,
                metadata TEXT,
                created_at INTEGER NOT NULL,
                UNIQUE(name, entity_type, project_id),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entity_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_entity_id INTEGER NOT NULL,
                to_entity_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                confidence REAL DEFAULT 1.0,
                created_at INTEGER NOT NULL,
                valid_from INTEGER,
                valid_until INTEGER,
                metadata TEXT,
                FOREIGN KEY (from_entity_id) REFERENCES entities(id) ON DELETE CASCADE,
                FOREIGN KEY (to_entity_id) REFERENCES entities(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entity_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                observation_type TEXT,
                confidence REAL DEFAULT 1.0,
                source TEXT DEFAULT 'user',
                timestamp INTEGER NOT NULL,
                superseded_by INTEGER,
                FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
                FOREIGN KEY (superseded_by) REFERENCES entity_observations(id) ON DELETE SET NULL
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_project ON entities(project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_from ON entity_relations(from_entity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_to ON entity_relations(to_entity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_type ON entity_relations(relation_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_observations_entity ON entity_observations(entity_id)")

        # Meta-memory tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS domain_coverage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',

                memory_count INTEGER DEFAULT 0,
                episodic_count INTEGER DEFAULT 0,
                procedural_count INTEGER DEFAULT 0,
                entity_count INTEGER DEFAULT 0,

                avg_confidence REAL DEFAULT 0.0,
                avg_usefulness REAL DEFAULT 0.0,
                last_updated INTEGER,

                gaps TEXT,
                strength_areas TEXT,

                first_encounter INTEGER,
                expertise_level TEXT DEFAULT 'beginner'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_transfer (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_project_id INTEGER NOT NULL,
                target_project_id INTEGER NOT NULL,
                domain TEXT NOT NULL,
                transfer_count INTEGER DEFAULT 1,
                last_transferred INTEGER NOT NULL,
                FOREIGN KEY (source_project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (target_project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        # Migrate existing domain_coverage table if columns are missing
        cursor.execute("PRAGMA table_info(domain_coverage)")
        coverage_columns = {row[1] for row in cursor.fetchall()}
        if coverage_columns and "category" not in coverage_columns:
            cursor.execute("ALTER TABLE domain_coverage ADD COLUMN category TEXT NOT NULL DEFAULT 'general'")
        if coverage_columns and "episodic_count" not in coverage_columns:
            cursor.execute("ALTER TABLE domain_coverage ADD COLUMN episodic_count INTEGER DEFAULT 0")
        if coverage_columns and "procedural_count" not in coverage_columns:
            cursor.execute("ALTER TABLE domain_coverage ADD COLUMN procedural_count INTEGER DEFAULT 0")
        if coverage_columns and "entity_count" not in coverage_columns:
            cursor.execute("ALTER TABLE domain_coverage ADD COLUMN entity_count INTEGER DEFAULT 0")
        if coverage_columns and "avg_confidence" not in coverage_columns:
            cursor.execute("ALTER TABLE domain_coverage ADD COLUMN avg_confidence REAL DEFAULT 0.0")
        if coverage_columns and "avg_usefulness" not in coverage_columns:
            cursor.execute("ALTER TABLE domain_coverage ADD COLUMN avg_usefulness REAL DEFAULT 0.0")
        if coverage_columns and "gaps" not in coverage_columns:
            cursor.execute("ALTER TABLE domain_coverage ADD COLUMN gaps TEXT")
        if coverage_columns and "strength_areas" not in coverage_columns:
            cursor.execute("ALTER TABLE domain_coverage ADD COLUMN strength_areas TEXT")
        if coverage_columns and "first_encounter" not in coverage_columns:
            cursor.execute("ALTER TABLE domain_coverage ADD COLUMN first_encounter INTEGER")
        if coverage_columns and "expertise_level" not in coverage_columns:
            cursor.execute("ALTER TABLE domain_coverage ADD COLUMN expertise_level TEXT DEFAULT 'beginner'")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_coverage_domain ON domain_coverage(domain)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_domain_category ON domain_coverage(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transfer_domain ON knowledge_transfer(domain)")

        # Consolidation tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS consolidation_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                started_at INTEGER NOT NULL,
                completed_at INTEGER,
                status TEXT DEFAULT 'running',
                memories_scored INTEGER DEFAULT 0,
                memories_pruned INTEGER DEFAULT 0,
                patterns_extracted INTEGER DEFAULT 0,
                conflicts_resolved INTEGER DEFAULT 0,
                avg_quality_before REAL,
                avg_quality_after REAL,
                consolidation_type TEXT DEFAULT 'scheduled',
                notes TEXT,
                blocked_reason TEXT,
                compression_ratio REAL,
                compression_target_met BOOLEAN,
                retrieval_recall REAL,
                recall_target_met BOOLEAN,
                pattern_consistency REAL,
                consistency_target_met BOOLEAN,
                avg_information_density REAL,
                density_target_met BOOLEAN,
                overall_quality_score REAL,
                quality_metrics_json TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS extracted_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                consolidation_run_id INTEGER NOT NULL,
                pattern_type TEXT NOT NULL,
                pattern_content TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                occurrences INTEGER DEFAULT 1,
                source_events TEXT,
                created_procedure BOOLEAN DEFAULT 0,
                created_semantic_memory BOOLEAN DEFAULT 0,
                updated_entity BOOLEAN DEFAULT 0,
                FOREIGN KEY (consolidation_run_id) REFERENCES consolidation_runs(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                consolidation_run_id INTEGER NOT NULL,
                memory1_id INTEGER NOT NULL,
                memory2_id INTEGER NOT NULL,
                conflict_type TEXT NOT NULL,
                resolution TEXT,
                resolved BOOLEAN DEFAULT 0,
                FOREIGN KEY (consolidation_run_id) REFERENCES consolidation_runs(id) ON DELETE CASCADE
            )
        """)

        # Migrate existing consolidation_runs table to add quality metrics columns
        cursor.execute("PRAGMA table_info(consolidation_runs)")
        columns = {row[1] for row in cursor.fetchall()}
        if "compression_ratio" not in columns:
            cursor.execute("ALTER TABLE consolidation_runs ADD COLUMN compression_ratio REAL")
        if "compression_target_met" not in columns:
            cursor.execute("ALTER TABLE consolidation_runs ADD COLUMN compression_target_met BOOLEAN")
        if "retrieval_recall" not in columns:
            cursor.execute("ALTER TABLE consolidation_runs ADD COLUMN retrieval_recall REAL")
        if "recall_target_met" not in columns:
            cursor.execute("ALTER TABLE consolidation_runs ADD COLUMN recall_target_met BOOLEAN")
        if "pattern_consistency" not in columns:
            cursor.execute("ALTER TABLE consolidation_runs ADD COLUMN pattern_consistency REAL")
        if "consistency_target_met" not in columns:
            cursor.execute("ALTER TABLE consolidation_runs ADD COLUMN consistency_target_met BOOLEAN")
        if "avg_information_density" not in columns:
            cursor.execute("ALTER TABLE consolidation_runs ADD COLUMN avg_information_density REAL")
        if "density_target_met" not in columns:
            cursor.execute("ALTER TABLE consolidation_runs ADD COLUMN density_target_met BOOLEAN")
        if "overall_quality_score" not in columns:
            cursor.execute("ALTER TABLE consolidation_runs ADD COLUMN overall_quality_score REAL")
        if "quality_metrics_json" not in columns:
            cursor.execute("ALTER TABLE consolidation_runs ADD COLUMN quality_metrics_json TEXT")

        # Create indexes for quality metrics
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_consolidation_runs_quality ON consolidation_runs(overall_quality_score DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_consolidation_runs_project_time ON consolidation_runs(project_id, started_at DESC)")

        self.conn.commit()

    def get_cursor(self):
        """Get a database cursor for direct SQL execution.

        This method provides compatibility for code written against SQLite.
        For PostgreSQL, this would be overridden to return a sync wrapper.

        Returns:
            A cursor object for executing SQL commands
        """
        return self.conn.cursor()

    def create_project(self, name: str, path: str) -> Project:
        """Create a new project.

        Args:
            name: Project name
            path: Absolute path to project directory

        Returns:
            Created project
        """
        cursor = self.conn.cursor()
        now = int(time.time())

        cursor.execute(
            """
            INSERT INTO projects (name, path, created_at, last_accessed)
            VALUES (?, ?, ?, ?)
        """,
            (name, path, now, now),
        )
        self.conn.commit()

        return Project(
            id=cursor.lastrowid,
            name=name,
            path=path,
            created_at=datetime.fromtimestamp(now),
            last_accessed=datetime.fromtimestamp(now),
            memory_count=0,
        )

    def get_project_by_path(self, path: str) -> Optional[Project]:
        """Get project by path (matches if path starts with project path).

        Args:
            path: Directory path to match

        Returns:
            Project if found, None otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM projects
            WHERE ? LIKE path || '%'
            ORDER BY LENGTH(path) DESC
            LIMIT 1
        """,
            (path,),
        )
        row = cursor.fetchone()

        if row:
            return Project(
                id=row["id"],
                name=row["name"],
                path=row["path"],
                created_at=datetime.fromtimestamp(row["created_at"]),
                last_accessed=datetime.fromtimestamp(row["last_accessed"]),
                memory_count=row["memory_count"],
            )
        return None

    def update_project_access(self, project_id: int):
        """Update last_accessed timestamp for project.

        Args:
            project_id: Project ID
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE projects SET last_accessed = ? WHERE id = ?",
            (int(time.time()), project_id),
        )
        self.conn.commit()

    def store_memory(self, memory: Memory) -> int:
        """Store a memory with its embedding.

        Args:
            memory: Memory to store

        Returns:
            ID of stored memory
        """
        cursor = self.conn.cursor()

        # Store metadata
        # Handle both MemoryType enum and string
        memory_type_str = (
            memory.memory_type.value
            if isinstance(memory.memory_type, MemoryType)
            else memory.memory_type
        )

        cursor.execute(
            """
            INSERT INTO memories (
                project_id, content, memory_type, tags,
                created_at, updated_at, access_count, usefulness_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                memory.project_id,
                memory.content,
                memory_type_str,
                json.dumps(memory.tags),
                int(memory.created_at.timestamp()),
                int(memory.updated_at.timestamp()),
                memory.access_count,
                memory.usefulness_score,
            ),
        )
        memory_id = cursor.lastrowid

        # Store embedding if present
        if memory.embedding:
            cursor.execute(
                """
                INSERT INTO memory_vectors (rowid, embedding)
                VALUES (?, ?)
            """,
                (memory_id, json.dumps(memory.embedding)),
            )

        # Update project memory count
        cursor.execute(
            """
            UPDATE projects
            SET memory_count = memory_count + 1
            WHERE id = ?
        """,
            (memory.project_id,),
        )

        self.conn.commit()
        return memory_id

    def get_memory(self, memory_id: int) -> Optional[Memory]:
        """Retrieve a memory by ID.

        Args:
            memory_id: Memory ID

        Returns:
            Memory if found, None otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return Memory(
            id=row["id"],
            project_id=row["project_id"],
            content=row["content"],
            memory_type=MemoryType(row["memory_type"]),
            tags=json.loads(row["tags"]) if row["tags"] else [],
            created_at=datetime.fromtimestamp(row["created_at"]),
            updated_at=datetime.fromtimestamp(row["updated_at"]),
            last_accessed=datetime.fromtimestamp(row["last_accessed"]) if row["last_accessed"] else None,
            access_count=row["access_count"],
            usefulness_score=row["usefulness_score"],
        )

    def delete_memory(self, memory_id: int) -> bool:
        """Delete a memory and its embedding.

        Args:
            memory_id: Memory ID to delete

        Returns:
            True if deleted, False if not found
        """
        cursor = self.conn.cursor()

        # Get project_id before deletion
        cursor.execute("SELECT project_id FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()
        if not row:
            return False

        project_id = row["project_id"]

        # Delete from both tables
        cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        cursor.execute("DELETE FROM memory_vectors WHERE rowid = ?", (memory_id,))

        # Update project memory count
        cursor.execute(
            "UPDATE projects SET memory_count = memory_count - 1 WHERE id = ?",
            (project_id,),
        )

        self.conn.commit()
        return True

    def update_access_stats(self, memory_id: int):
        """Update access statistics for a memory.

        Args:
            memory_id: Memory ID
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE memories
            SET last_accessed = ?,
                access_count = access_count + 1
            WHERE id = ?
        """,
            (int(time.time()), memory_id),
        )
        self.conn.commit()

    def list_memories(
        self, project_id: int, limit: int = 20, sort_by: str = "useful"
    ) -> list[Memory]:
        """List memories for a project.

        Args:
            project_id: Project ID
            limit: Maximum number of memories to return
            sort_by: Sort order ('recent', 'useful', 'accessed')

        Returns:
            List of memories
        """
        cursor = self.conn.cursor()

        order_clause = {
            "recent": "created_at DESC",
            "useful": "usefulness_score DESC",
            "accessed": "last_accessed DESC NULLS LAST",
        }.get(sort_by, "usefulness_score DESC")

        cursor.execute(
            f"""
            SELECT * FROM memories
            WHERE project_id = ?
            ORDER BY {order_clause}
            LIMIT ?
        """,
            (project_id, limit),
        )

        memories = []
        for row in cursor.fetchall():
            memories.append(
                Memory(
                    id=row["id"],
                    project_id=row["project_id"],
                    content=row["content"],
                    memory_type=MemoryType(row["memory_type"]),
                    tags=json.loads(row["tags"]) if row["tags"] else [],
                    created_at=datetime.fromtimestamp(row["created_at"]),
                    updated_at=datetime.fromtimestamp(row["updated_at"]),
                    last_accessed=datetime.fromtimestamp(row["last_accessed"]) if row["last_accessed"] else None,
                    access_count=row["access_count"],
                    usefulness_score=row["usefulness_score"],
                )
            )

        return memories

    @contextmanager
    def get_connection(self):
        """Get database connection as context manager.

        Yields the connection and commits on success, rolls back on error.

        Usage:
            with db.get_connection() as conn:
                conn.execute("INSERT ...")
        """
        try:
            yield self.conn
            # Note: commit is handled by calling code or explicit transaction
        except Exception:
            self.conn.rollback()
            raise

    def bulk_insert(self, table: str, rows: list[dict]) -> int:
        """Insert multiple rows efficiently in a single transaction.

        Args:
            table: Table name to insert into
            rows: List of dictionaries with column names as keys

        Returns:
            Number of rows inserted

        Example:
            db.bulk_insert("memories", [
                {"content": "fact1", "memory_type": "fact", ...},
                {"content": "fact2", "memory_type": "fact", ...},
            ])
        """
        if not rows:
            return 0

        try:
            # Extract column names from first row
            columns = list(rows[0].keys())
            placeholders = ", ".join(["?"] * len(columns))
            query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"

            # Convert dicts to tuples in order of columns
            values = [tuple(row[col] for col in columns) for row in rows]

            cursor = self.conn.cursor()
            cursor.executemany(query, values)
            self.conn.commit()

            return cursor.rowcount
        except Exception as e:
            self.conn.rollback()
            raise e

    def filtered_search(
        self,
        table: str,
        filters: Optional[dict] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None
    ) -> list:
        """Execute flexible filtered query on a table.

        Args:
            table: Table name to query
            filters: Filter dict with multiple formats:
                - Simple: {"column": value}  -> WHERE column = value
                - Comparison: {"column": {">": 50}}  -> WHERE column > 50
                - In: {"column": {"IN": [1, 2, 3]}}  -> WHERE column IN (1, 2, 3)
            order_by: Column(s) to order by (e.g., "created_at DESC")
            limit: Maximum number of results

        Returns:
            List of results (sqlite3.Row objects)

        Example:
            results = db.filtered_search(
                "memories",
                filters={
                    "project_id": 1,
                    "usefulness_score": {">": 0.5},
                    "memory_type": {"IN": ["fact", "concept"]}
                },
                order_by="created_at DESC",
                limit=10
            )
        """
        try:
            where_parts = []
            params = []

            if filters:
                for col, value in filters.items():
                    if isinstance(value, dict):
                        # Complex filter: {"op": val}
                        for op, op_value in value.items():
                            if op.upper() == "IN":
                                if isinstance(op_value, (list, tuple)):
                                    placeholders = ",".join(["?"] * len(op_value))
                                    where_parts.append(f"{col} IN ({placeholders})")
                                    params.extend(op_value)
                                else:
                                    raise ValueError(f"IN operator requires list, got {type(op_value)}")
                            else:
                                where_parts.append(f"{col} {op} ?")
                                params.append(op_value)
                    else:
                        # Simple equality filter
                        where_parts.append(f"{col} = ?")
                        params.append(value)

            query = f"SELECT * FROM {table}"
            if where_parts:
                query += " WHERE " + " AND ".join(where_parts)
            if order_by:
                query += f" ORDER BY {order_by}"
            if limit:
                query += f" LIMIT {limit}"

            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        except Exception as e:
            raise e

    def close(self):
        """Close database connection."""
        self.conn.close()
