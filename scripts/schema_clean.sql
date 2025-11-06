CREATE TABLE projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                path TEXT UNIQUE NOT NULL,
                created_at INTEGER NOT NULL,
                last_accessed INTEGER NOT NULL,
                memory_count INTEGER DEFAULT 0
            , quota_enforced BOOLEAN DEFAULT 1, last_quota_check INTEGER);
CREATE TABLE memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                tags TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                last_accessed INTEGER,
                access_count INTEGER DEFAULT 0,
                usefulness_score REAL DEFAULT 0.0, last_retrieved INTEGER, consolidation_state TEXT DEFAULT 'consolidated', superseded_by INTEGER REFERENCES memories(id), version INTEGER DEFAULT 1, content_compressed TEXT, compression_level INTEGER DEFAULT 0 CHECK (compression_level >= 0 AND compression_level <= 3), compression_timestamp TIMESTAMP DEFAULT NULL, compression_tokens_saved REAL DEFAULT NULL, content_executive TEXT, compression_source_events TEXT DEFAULT NULL, compression_generated_at TIMESTAMP DEFAULT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
CREATE VIRTUAL TABLE memory_vectors USING vec0(
                embedding FLOAT[768]
            );
CREATE TABLE IF NOT EXISTS "memory_vectors_info" (key text primary key, value any);
CREATE TABLE IF NOT EXISTS "memory_vectors_chunks"(chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,size INTEGER NOT NULL,validity BLOB NOT NULL,rowids BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS "memory_vectors_rowids"(rowid INTEGER PRIMARY KEY AUTOINCREMENT,id,chunk_id INTEGER,chunk_offset INTEGER);
CREATE TABLE IF NOT EXISTS "memory_vectors_vector_chunks00"(rowid PRIMARY KEY,vectors BLOB NOT NULL);
CREATE TABLE memory_relations (
                from_memory_id INTEGER NOT NULL,
                to_memory_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                PRIMARY KEY (from_memory_id, to_memory_id),
                FOREIGN KEY (from_memory_id) REFERENCES memories(id) ON DELETE CASCADE,
                FOREIGN KEY (to_memory_id) REFERENCES memories(id) ON DELETE CASCADE
            );
CREATE TABLE optimization_stats (
                project_id INTEGER PRIMARY KEY,
                last_optimized INTEGER,
                memories_pruned INTEGER DEFAULT 0,
                avg_usefulness REAL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
CREATE INDEX idx_memories_project ON memories(project_id);
CREATE INDEX idx_memories_score ON memories(usefulness_score DESC);
CREATE INDEX idx_memories_accessed ON memories(last_accessed DESC);
CREATE INDEX idx_memories_type ON memories(memory_type);
CREATE TABLE episodic_events (
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
                consolidated_at INTEGER, code_event_type TEXT, file_path TEXT, symbol_name TEXT, symbol_type TEXT, language TEXT, diff TEXT, git_commit TEXT, git_author TEXT, test_name TEXT, test_passed INTEGER, error_type TEXT, stack_trace TEXT, performance_metrics TEXT, code_quality_score REAL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
CREATE TABLE event_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value TEXT NOT NULL,
                FOREIGN KEY (event_id) REFERENCES episodic_events(id) ON DELETE CASCADE
            );
CREATE TABLE event_relations (
                from_event_id INTEGER NOT NULL,
                to_event_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                PRIMARY KEY (from_event_id, to_event_id),
                FOREIGN KEY (from_event_id) REFERENCES episodic_events(id) ON DELETE CASCADE,
                FOREIGN KEY (to_event_id) REFERENCES episodic_events(id) ON DELETE CASCADE
            );
CREATE VIRTUAL TABLE event_vectors USING vec0(
                embedding FLOAT[768]
            );
CREATE TABLE IF NOT EXISTS "event_vectors_info" (key text primary key, value any);
CREATE TABLE IF NOT EXISTS "event_vectors_chunks"(chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,size INTEGER NOT NULL,validity BLOB NOT NULL,rowids BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS "event_vectors_rowids"(rowid INTEGER PRIMARY KEY AUTOINCREMENT,id,chunk_id INTEGER,chunk_offset INTEGER);
CREATE TABLE IF NOT EXISTS "event_vectors_vector_chunks00"(rowid PRIMARY KEY,vectors BLOB NOT NULL);
CREATE INDEX idx_events_timestamp ON episodic_events(timestamp DESC);
CREATE INDEX idx_events_project ON episodic_events(project_id, timestamp DESC);
CREATE INDEX idx_events_session ON episodic_events(session_id);
CREATE INDEX idx_events_type ON episodic_events(event_type);
CREATE INDEX idx_events_consolidation ON episodic_events(project_id, consolidation_status);
CREATE INDEX idx_events_code_type ON episodic_events(code_event_type);
CREATE INDEX idx_events_symbol ON episodic_events(file_path, symbol_name);
CREATE INDEX idx_events_language ON episodic_events(language);
CREATE INDEX idx_events_git_commit ON episodic_events(git_commit);
CREATE TABLE working_memory (
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
            );
CREATE INDEX idx_working_memory_project ON working_memory(project_id);
CREATE INDEX idx_working_memory_type ON working_memory(content_type);
CREATE INDEX idx_working_memory_component ON working_memory(component);
CREATE INDEX idx_working_memory_importance ON working_memory(importance_score DESC);
CREATE VIEW v_working_memory_current AS
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
            FROM working_memory;
CREATE TABLE procedures (
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
            );
CREATE TABLE procedure_params (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                procedure_id INTEGER NOT NULL,
                param_name TEXT NOT NULL,
                param_type TEXT NOT NULL,
                required BOOLEAN DEFAULT 1,
                default_value TEXT,
                description TEXT,
                FOREIGN KEY (procedure_id) REFERENCES procedures(id) ON DELETE CASCADE
            );
CREATE TABLE procedure_executions (
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
            );
CREATE INDEX idx_procedures_category ON procedures(category);
CREATE INDEX idx_procedures_usage ON procedures(usage_count DESC);
CREATE INDEX idx_executions_procedure ON procedure_executions(procedure_id);
CREATE TABLE prospective_tasks (
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
                blocked_reason TEXT, phase TEXT DEFAULT 'planning', plan_json TEXT, plan_created_at INTEGER, phase_started_at INTEGER, phase_metrics_json TEXT, actual_duration_minutes REAL, lessons_learned TEXT, failure_reason TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
CREATE TABLE task_triggers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                trigger_type TEXT NOT NULL,
                trigger_value TEXT,
                trigger_condition TEXT,
                fired BOOLEAN DEFAULT 0,
                fired_at INTEGER,
                FOREIGN KEY (task_id) REFERENCES prospective_tasks(id) ON DELETE CASCADE
            );
CREATE TABLE task_dependencies (
                task_id INTEGER NOT NULL,
                depends_on_task_id INTEGER NOT NULL,
                dependency_type TEXT DEFAULT 'blocks',
                PRIMARY KEY (task_id, depends_on_task_id),
                FOREIGN KEY (task_id) REFERENCES prospective_tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (depends_on_task_id) REFERENCES prospective_tasks(id) ON DELETE CASCADE
            );
CREATE INDEX idx_tasks_status ON prospective_tasks(status);
CREATE INDEX idx_tasks_priority ON prospective_tasks(priority);
CREATE INDEX idx_tasks_due ON prospective_tasks(due_at);
CREATE TABLE entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                project_id INTEGER,
                updated_at INTEGER NOT NULL,
                metadata TEXT,
                created_at INTEGER NOT NULL,
                UNIQUE(name, entity_type, project_id),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
CREATE TABLE entity_relations (
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
            );
CREATE TABLE entity_observations (
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
            );
CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_name ON entities(name);
CREATE INDEX idx_entities_project ON entities(project_id);
CREATE INDEX idx_relations_from ON entity_relations(from_entity_id);
CREATE INDEX idx_relations_to ON entity_relations(to_entity_id);
CREATE INDEX idx_relations_type ON entity_relations(relation_type);
CREATE INDEX idx_observations_entity ON entity_observations(entity_id);
CREATE TABLE domain_coverage (
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
            );
CREATE TABLE knowledge_transfer (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_project_id INTEGER NOT NULL,
                target_project_id INTEGER NOT NULL,
                domain TEXT NOT NULL,
                transfer_count INTEGER DEFAULT 1,
                last_transferred INTEGER NOT NULL,
                FOREIGN KEY (source_project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (target_project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
CREATE INDEX idx_coverage_domain ON domain_coverage(domain);
CREATE INDEX idx_domain_category ON domain_coverage(category);
CREATE INDEX idx_transfer_domain ON knowledge_transfer(domain);
CREATE TABLE consolidation_runs (
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
            );
CREATE TABLE extracted_patterns (
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
            );
CREATE TABLE memory_conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                consolidation_run_id INTEGER NOT NULL,
                memory1_id INTEGER NOT NULL,
                memory2_id INTEGER NOT NULL,
                conflict_type TEXT NOT NULL,
                resolution TEXT,
                resolved BOOLEAN DEFAULT 0,
                FOREIGN KEY (consolidation_run_id) REFERENCES consolidation_runs(id) ON DELETE CASCADE
            );
CREATE INDEX idx_consolidation_runs_quality ON consolidation_runs(overall_quality_score DESC);
CREATE INDEX idx_consolidation_runs_project_time ON consolidation_runs(project_id, started_at DESC);
CREATE TABLE phases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                task_id INTEGER NOT NULL,
                phase_name TEXT NOT NULL,
                sequence_number INTEGER,
                start_date INTEGER,
                end_date INTEGER,
                status TEXT DEFAULT 'pending',
                created_at INTEGER NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (task_id) REFERENCES prospective_tasks(id) ON DELETE CASCADE
            );
CREATE INDEX idx_tasks_project ON prospective_tasks(project_id);
CREATE INDEX idx_triggers_task ON task_triggers(task_id);
CREATE TABLE memory_quality (
                memory_id INTEGER NOT NULL,
                memory_layer TEXT NOT NULL,

                access_count INTEGER DEFAULT 0,
                last_accessed INTEGER,
                useful_count INTEGER DEFAULT 0,

                usefulness_score REAL DEFAULT 0.0,
                confidence REAL DEFAULT 1.0,
                relevance_decay REAL DEFAULT 1.0,

                source TEXT DEFAULT 'user',
                verified BOOLEAN DEFAULT 0,

                PRIMARY KEY (memory_id, memory_layer)
            );
CREATE TABLE knowledge_transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_project_id INTEGER NOT NULL,
                to_project_id INTEGER NOT NULL,
                knowledge_item_id INTEGER NOT NULL,
                knowledge_layer TEXT NOT NULL,
                transferred_at INTEGER NOT NULL,
                applicability_score REAL DEFAULT 0.0
            );
CREATE INDEX idx_quality_layer ON memory_quality(memory_layer);
CREATE INDEX idx_quality_usefulness ON memory_quality(usefulness_score);
CREATE INDEX idx_transfer_from ON knowledge_transfers(from_project_id);
CREATE TABLE planning_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                pattern_type TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                success_rate REAL DEFAULT 0.0,
                quality_score REAL DEFAULT 0.0,
                execution_count INTEGER DEFAULT 0,
                applicable_domains TEXT,
                applicable_task_types TEXT,
                complexity_min INTEGER DEFAULT 1,
                complexity_max INTEGER DEFAULT 10,
                conditions TEXT,
                source TEXT DEFAULT 'user',
                research_reference TEXT,
                created_at INTEGER NOT NULL,
                last_used INTEGER,
                feedback_count INTEGER DEFAULT 0,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(project_id, name)
            );
CREATE TABLE decomposition_strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                strategy_name TEXT NOT NULL,
                description TEXT NOT NULL,
                decomposition_type TEXT NOT NULL,
                chunk_size_minutes INTEGER DEFAULT 30,
                max_depth INTEGER,
                adaptive_depth INTEGER DEFAULT 0,
                validation_gates TEXT,
                applicable_task_types TEXT,
                success_rate REAL DEFAULT 0.0,
                avg_actual_vs_planned_ratio REAL DEFAULT 1.0,
                quality_improvement_pct REAL DEFAULT 0.0,
                token_efficiency REAL DEFAULT 1.0,
                created_at INTEGER NOT NULL,
                last_used INTEGER,
                usage_count INTEGER DEFAULT 0,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(project_id, strategy_name)
            );
CREATE TABLE orchestrator_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                pattern_name TEXT NOT NULL,
                description TEXT NOT NULL,
                agent_roles TEXT NOT NULL,
                coordination_type TEXT NOT NULL,
                num_agents INTEGER DEFAULT 1,
                effectiveness_improvement_pct REAL DEFAULT 0.0,
                handoff_success_rate REAL DEFAULT 0.0,
                speedup_factor REAL DEFAULT 1.0,
                token_overhead_multiplier REAL DEFAULT 1.0,
                applicable_domains TEXT,
                applicable_task_types TEXT,
                created_at INTEGER NOT NULL,
                last_used INTEGER,
                execution_count INTEGER DEFAULT 0,
                successful_executions INTEGER DEFAULT 0,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(project_id, pattern_name)
            );
CREATE TABLE validation_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                rule_name TEXT NOT NULL,
                description TEXT NOT NULL,
                rule_type TEXT NOT NULL,
                check_function TEXT NOT NULL,
                parameters TEXT,
                applicable_to_task_types TEXT,
                applies_to_phases TEXT,
                risk_level TEXT DEFAULT 'medium',
                dependencies TEXT,
                accuracy_pct REAL DEFAULT 0.0,
                precision REAL DEFAULT 0.0,
                recall REAL DEFAULT 0.0,
                f1_score REAL DEFAULT 0.0,
                created_at INTEGER NOT NULL,
                last_used INTEGER,
                execution_count INTEGER DEFAULT 0,
                violations_caught INTEGER DEFAULT 0,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(project_id, rule_name)
            );
CREATE TABLE execution_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                task_id INTEGER,
                pattern_id INTEGER,
                orchestration_pattern_id INTEGER,
                execution_outcome TEXT NOT NULL,
                execution_quality_score REAL DEFAULT 0.0,
                planned_duration_minutes INTEGER,
                actual_duration_minutes INTEGER,
                duration_variance_pct REAL DEFAULT 0.0,
                blockers_encountered TEXT,
                adjustments_made TEXT,
                assumption_violations TEXT,
                learning_extracted TEXT,
                confidence_in_learning REAL DEFAULT 0.0,
                quality_metrics TEXT,
                created_at INTEGER NOT NULL,
                executor_agent TEXT,
                phase_number INTEGER,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (pattern_id) REFERENCES planning_patterns(id) ON DELETE SET NULL,
                FOREIGN KEY (orchestration_pattern_id) REFERENCES orchestrator_patterns(id) ON DELETE SET NULL
            );
CREATE INDEX idx_patterns_project_type
            ON planning_patterns(project_id, pattern_type)
        ;
CREATE INDEX idx_patterns_success
            ON planning_patterns(project_id, success_rate DESC)
        ;
CREATE INDEX idx_strategies_project
            ON decomposition_strategies(project_id, success_rate DESC)
        ;
CREATE INDEX idx_orchestration_project
            ON orchestrator_patterns(project_id, speedup_factor DESC)
        ;
CREATE INDEX idx_rules_project_risk
            ON validation_rules(project_id, risk_level)
        ;
CREATE INDEX idx_feedback_pattern
            ON execution_feedback(pattern_id, execution_outcome)
        ;
CREATE INDEX idx_feedback_created
            ON execution_feedback(project_id, created_at DESC)
        ;
CREATE TABLE spatial_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                full_path TEXT NOT NULL,
                depth INTEGER NOT NULL,
                parent_path TEXT,
                node_type TEXT NOT NULL,
                language TEXT,
                symbol_kind TEXT,
                created_at INTEGER NOT NULL,
                UNIQUE(project_id, full_path),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
CREATE TABLE spatial_relations (
                from_path TEXT NOT NULL,
                to_path TEXT NOT NULL,
                project_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                PRIMARY KEY (from_path, to_path, project_id, relation_type),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
CREATE TABLE symbol_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                line_number INTEGER NOT NULL,
                symbol_kind TEXT NOT NULL,
                language TEXT NOT NULL,
                full_path TEXT NOT NULL UNIQUE,
                parent_class TEXT,
                signature TEXT,
                docstring TEXT,
                complexity_score REAL,
                created_at INTEGER NOT NULL,
                UNIQUE(project_id, file_path, name, line_number),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
CREATE TABLE symbol_relations (
                from_symbol_id INTEGER NOT NULL,
                to_symbol_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                PRIMARY KEY (from_symbol_id, to_symbol_id, relation_type),
                FOREIGN KEY (from_symbol_id) REFERENCES symbol_nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (to_symbol_id) REFERENCES symbol_nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
CREATE INDEX idx_spatial_nodes_project ON spatial_nodes(project_id, full_path);
CREATE INDEX idx_spatial_nodes_depth ON spatial_nodes(project_id, depth);
CREATE INDEX idx_spatial_nodes_type ON spatial_nodes(project_id, node_type);
CREATE INDEX idx_spatial_relations_from ON spatial_relations(project_id, from_path);
CREATE INDEX idx_spatial_relations_to ON spatial_relations(project_id, to_path);
CREATE INDEX idx_symbol_nodes_file ON symbol_nodes(project_id, file_path, line_number);
CREATE INDEX idx_symbol_nodes_kind ON symbol_nodes(project_id, symbol_kind);
CREATE INDEX idx_symbol_nodes_language ON symbol_nodes(project_id, language);
CREATE INDEX idx_symbol_relations_from ON symbol_relations(from_symbol_id);
CREATE INDEX idx_symbol_relations_to ON symbol_relations(to_symbol_id);
CREATE TABLE sessions (
                id TEXT PRIMARY KEY,
                project_id INTEGER NOT NULL,
                started_at INTEGER NOT NULL,
                ended_at INTEGER,
                context TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
CREATE TABLE conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                thread_id TEXT UNIQUE NOT NULL,
                title TEXT,
                status TEXT DEFAULT 'active',
                created_at INTEGER NOT NULL,
                last_message_at INTEGER NOT NULL,
                total_tokens INTEGER DEFAULT 0,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );
CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tokens_estimate INTEGER DEFAULT 0,
                model TEXT,
                metadata TEXT,
                created_at INTEGER NOT NULL
            );
CREATE TABLE conversation_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                turn_number INTEGER NOT NULL,
                user_message_id INTEGER,
                assistant_message_id INTEGER,
                duration_ms INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                FOREIGN KEY (user_message_id) REFERENCES messages(id) ON DELETE SET NULL,
                FOREIGN KEY (assistant_message_id) REFERENCES messages(id) ON DELETE SET NULL
            );
CREATE TABLE conversation_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                turn_count INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                avg_turn_duration_ms REAL DEFAULT 0.0,
                topics TEXT,
                quality_score REAL DEFAULT 0.5,
                is_useful INTEGER DEFAULT 1,
                notes TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );
CREATE INDEX idx_sessions_project ON sessions(project_id, started_at DESC);
CREATE INDEX idx_conversations_project ON conversations(project_id, created_at DESC);
CREATE INDEX idx_conversations_session ON conversations(session_id);
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_turns_conversation ON conversation_turns(conversation_id);
CREATE INDEX idx_messages_role ON messages(role);
CREATE TABLE safety_policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,

                approval_required_for TEXT NOT NULL,  -- JSON list of ChangeType
                auto_approve_threshold REAL DEFAULT 0.85,
                auto_reject_threshold REAL DEFAULT 0.2,

                require_tests_for TEXT NOT NULL,  -- JSON list of file patterns
                min_test_coverage REAL DEFAULT 0.0,

                audit_enabled INTEGER DEFAULT 1,
                keep_pre_modification_snapshot INTEGER DEFAULT 1,
                require_human_approval INTEGER DEFAULT 0,
                max_approval_time_hours INTEGER DEFAULT 24,

                enable_rollback INTEGER DEFAULT 1,
                keep_rollback_snapshots INTEGER DEFAULT 10,

                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,

                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(project_id, name)
            );
CREATE TABLE approval_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                agent_id TEXT,
                change_type TEXT NOT NULL,
                change_description TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                risk_level TEXT NOT NULL,

                affected_files TEXT NOT NULL,  -- JSON list
                affected_lines TEXT,  -- JSON [start, end]

                pre_snapshot_id INTEGER,
                status TEXT DEFAULT 'pending',
                requested_at INTEGER NOT NULL,
                approved_by TEXT,
                approved_at INTEGER,
                rejection_reason TEXT,

                auto_approved INTEGER DEFAULT 0,
                auto_approved_reason TEXT,

                policy_id INTEGER,

                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (policy_id) REFERENCES safety_policies(id) ON DELETE SET NULL,
                FOREIGN KEY (pre_snapshot_id) REFERENCES code_snapshots(id) ON DELETE SET NULL
            );
CREATE TABLE audit_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                timestamp INTEGER NOT NULL,

                agent_id TEXT,
                user_id TEXT,

                change_type TEXT NOT NULL,
                affected_files TEXT NOT NULL,  -- JSON list
                description TEXT NOT NULL,

                approval_request_id INTEGER,
                pre_snapshot_id INTEGER,
                post_snapshot_id INTEGER,

                success INTEGER DEFAULT 1,
                error_message TEXT,

                risk_level TEXT NOT NULL,
                confidence_score REAL NOT NULL,

                reverted INTEGER DEFAULT 0,
                reverted_at INTEGER,
                revert_reason TEXT,

                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (approval_request_id) REFERENCES approval_requests(id) ON DELETE SET NULL,
                FOREIGN KEY (pre_snapshot_id) REFERENCES code_snapshots(id) ON DELETE SET NULL,
                FOREIGN KEY (post_snapshot_id) REFERENCES code_snapshots(id) ON DELETE SET NULL
            );
CREATE TABLE code_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                created_at INTEGER NOT NULL,

                file_path TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                content_preview TEXT NOT NULL,
                full_content TEXT,

                change_type TEXT NOT NULL,
                change_id INTEGER,
                agent_id TEXT,

                expires_at INTEGER,
                keep_indefinitely INTEGER DEFAULT 0,

                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
CREATE TABLE change_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                approval_request_id INTEGER NOT NULL,

                recommendation TEXT NOT NULL,  -- "approve" | "reject" | "request_changes" | "escalate"
                reasoning TEXT NOT NULL,
                confidence REAL NOT NULL,

                suggested_tests TEXT NOT NULL,  -- JSON list
                suggested_reviewers TEXT NOT NULL,  -- JSON list
                risk_mitigation_steps TEXT NOT NULL,  -- JSON list

                created_at INTEGER NOT NULL,

                FOREIGN KEY (approval_request_id) REFERENCES approval_requests(id) ON DELETE CASCADE
            );
CREATE INDEX idx_approval_requests_project ON approval_requests(project_id);
CREATE INDEX idx_approval_requests_status ON approval_requests(status);
CREATE INDEX idx_audit_entries_project ON audit_entries(project_id);
CREATE INDEX idx_audit_entries_timestamp ON audit_entries(timestamp);
CREATE INDEX idx_code_snapshots_project ON code_snapshots(project_id);
CREATE INDEX idx_code_snapshots_file ON code_snapshots(file_path);
CREATE TABLE schema_version (
                version INTEGER PRIMARY KEY,
                applied_at INTEGER NOT NULL,
                description TEXT,
                migration_file TEXT
            );
CREATE TABLE memory_updates (
id INTEGER PRIMARY KEY AUTOINCREMENT,
original_id INTEGER NOT NULL,
updated_id INTEGER NOT NULL,
update_reason TEXT,
confidence REAL DEFAULT 1.0,
timestamp INTEGER NOT NULL,
FOREIGN KEY (original_id) REFERENCES memories(id) ON DELETE CASCADE,
FOREIGN KEY (updated_id) REFERENCES memories(id) ON DELETE CASCADE
);
CREATE INDEX idx_memory_updates_original ON memory_updates(original_id);
CREATE INDEX idx_memory_updates_updated ON memory_updates(updated_id);
CREATE INDEX idx_memories_consolidation_state ON memories(consolidation_state);
CREATE INDEX idx_memories_last_retrieved ON memories(last_retrieved);
CREATE TABLE active_goals (
id INTEGER PRIMARY KEY AUTOINCREMENT,
project_id INTEGER NOT NULL,
goal_text TEXT NOT NULL,
goal_type TEXT NOT NULL CHECK (goal_type IN ('primary', 'subgoal', 'maintenance')),
parent_goal_id INTEGER,
priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
status TEXT DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'completed', 'failed', 'in_progress', 'blocked')),
progress REAL DEFAULT 0.0 CHECK (progress >= 0.0 AND progress <= 1.0),
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
deadline TIMESTAMP,
completion_criteria TEXT,
metadata TEXT,  -- JSON
FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
FOREIGN KEY (parent_goal_id) REFERENCES active_goals(id) ON DELETE SET NULL
);
CREATE TABLE attention_focus (
id INTEGER PRIMARY KEY AUTOINCREMENT,
project_id INTEGER NOT NULL,
goal_id INTEGER,
focus_target TEXT,
focus_type TEXT CHECK (focus_type IN ('file', 'concept', 'task', 'problem', 'memory')),
attention_weight REAL DEFAULT 1.0 CHECK (attention_weight >= 0.0),
started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
focused_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
duration_seconds INTEGER DEFAULT 0,
FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
FOREIGN KEY (goal_id) REFERENCES active_goals(id) ON DELETE CASCADE
);
CREATE TABLE working_memory_decay_log (
id INTEGER PRIMARY KEY AUTOINCREMENT,
wm_id INTEGER NOT NULL,
timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
activation_level REAL CHECK (activation_level >= 0.0 AND activation_level <= 1.0),
access_count INTEGER DEFAULT 0,
FOREIGN KEY (wm_id) REFERENCES working_memory(id) ON DELETE CASCADE
);
CREATE TABLE consolidation_routes (
id INTEGER PRIMARY KEY AUTOINCREMENT,
wm_id INTEGER NOT NULL,
target_layer TEXT NOT NULL CHECK (target_layer IN ('semantic', 'episodic', 'procedural', 'prospective')),
confidence REAL CHECK (confidence >= 0.0 AND confidence <= 1.0),
was_correct BOOLEAN,
routed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
features TEXT,  -- JSON array of feature values
FOREIGN KEY (wm_id) REFERENCES working_memory(id) ON DELETE CASCADE
);
CREATE INDEX idx_wm_project ON working_memory(project_id);
CREATE INDEX idx_wm_activation ON working_memory(activation_level DESC);
CREATE INDEX idx_wm_component ON working_memory(component);
CREATE INDEX idx_wm_accessed ON working_memory(last_accessed DESC);
CREATE INDEX idx_wm_project_component ON working_memory(project_id, component);
CREATE INDEX idx_goals_project ON active_goals(project_id);
CREATE INDEX idx_goals_status ON active_goals(status);
CREATE INDEX idx_goals_parent ON active_goals(parent_goal_id);
CREATE INDEX idx_goals_priority ON active_goals(priority DESC);
CREATE INDEX idx_goals_project_status ON active_goals(project_id, status);
CREATE INDEX idx_attention_project ON attention_focus(project_id);
CREATE INDEX idx_attention_started ON attention_focus(started_at DESC);
CREATE INDEX idx_decay_wm ON working_memory_decay_log(wm_id);
CREATE INDEX idx_decay_timestamp ON working_memory_decay_log(timestamp DESC);
CREATE INDEX idx_routes_wm ON consolidation_routes(wm_id);
CREATE INDEX idx_routes_layer ON consolidation_routes(target_layer);
CREATE INDEX idx_routes_correct ON consolidation_routes(was_correct);
CREATE TRIGGER update_goal_timestamp
AFTER UPDATE ON active_goals
FOR EACH ROW
BEGIN
UPDATE active_goals SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
CREATE TRIGGER log_wm_access
AFTER UPDATE OF last_accessed ON working_memory
FOR EACH ROW
BEGIN
INSERT INTO working_memory_decay_log (wm_id, activation_level, access_count)
VALUES (NEW.id, NEW.activation_level,
(SELECT COUNT(*) FROM working_memory_decay_log WHERE wm_id = NEW.id) + 1);
END;
CREATE VIEW v_goals_hierarchy AS
WITH RECURSIVE goal_tree AS (
SELECT
id, project_id, goal_text, goal_type, parent_goal_id,
priority, status, progress, created_at, deadline,
0 as depth,
goal_text as path
FROM active_goals
WHERE parent_goal_id IS NULL
UNION ALL
SELECT
g.id, g.project_id, g.goal_text, g.goal_type, g.parent_goal_id,
g.priority, g.status, g.progress, g.created_at, g.deadline,
gt.depth + 1,
gt.path || ' > ' || g.goal_text
FROM active_goals g
INNER JOIN goal_tree gt ON g.parent_goal_id = gt.id
)
SELECT * FROM goal_tree
ORDER BY depth, priority DESC
/* v_goals_hierarchy(id,project_id,goal_text,goal_type,parent_goal_id,priority,status,progress,created_at,deadline,depth,path) */;
CREATE VIEW v_wm_capacity AS
SELECT
project_id,
COUNT(*) as item_count,
7 as max_capacity,
CASE
WHEN COUNT(*) >= 7 THEN 'full'
WHEN COUNT(*) >= 5 THEN 'near_full'
ELSE 'available'
END as status,
AVG(current_activation) as avg_activation
FROM v_working_memory_current
GROUP BY project_id;
CREATE TABLE advisory_locks (
id INTEGER PRIMARY KEY AUTOINCREMENT,
lock_key TEXT NOT NULL UNIQUE,        -- Unique identifier for the lock
owner TEXT NOT NULL,                  -- Who owns the lock (user/session ID)
acquired_at INTEGER NOT NULL,         -- When lock was acquired
expires_at INTEGER,                   -- Optional expiration time
metadata TEXT,                        -- JSON metadata about the lock
UNIQUE(lock_key)
);
CREATE TABLE resource_quotas (
id INTEGER PRIMARY KEY AUTOINCREMENT,
project_id INTEGER,                   -- NULL for global quotas
resource_type TEXT NOT NULL,          -- memory_count|episodic_events|procedures|entities|storage_mb
quota_limit INTEGER NOT NULL,         -- Maximum allowed
current_usage INTEGER DEFAULT 0,      -- Current usage
last_updated INTEGER NOT NULL,
UNIQUE(project_id, resource_type),
FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
CREATE TABLE resource_usage_log (
id INTEGER PRIMARY KEY AUTOINCREMENT,
project_id INTEGER,
resource_type TEXT NOT NULL,
operation TEXT NOT NULL,              -- create|update|delete
amount INTEGER NOT NULL,              -- Amount changed (+/-)
timestamp INTEGER NOT NULL,
metadata TEXT,                        -- JSON context
FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
CREATE INDEX idx_advisory_locks_key ON advisory_locks(lock_key);
CREATE INDEX idx_advisory_locks_owner ON advisory_locks(owner);
CREATE INDEX idx_advisory_locks_expires ON advisory_locks(expires_at);
CREATE INDEX idx_resource_quotas_project ON resource_quotas(project_id);
CREATE INDEX idx_resource_quotas_type ON resource_quotas(resource_type);
CREATE INDEX idx_resource_usage_project ON resource_usage_log(project_id);
CREATE INDEX idx_resource_usage_time ON resource_usage_log(timestamp DESC);
CREATE TABLE attention_salience (
id INTEGER PRIMARY KEY AUTOINCREMENT,
project_id INTEGER NOT NULL,
memory_id INTEGER NOT NULL,
memory_layer TEXT NOT NULL CHECK (memory_layer IN ('working', 'semantic', 'episodic', 'procedural', 'prospective', 'graph')),
salience_score REAL DEFAULT 0.0 CHECK (salience_score >= 0.0 AND salience_score <= 1.0),
novelty_score REAL DEFAULT 0.0 CHECK (novelty_score >= 0.0 AND novelty_score <= 1.0),
surprise_score REAL DEFAULT 0.0 CHECK (surprise_score >= 0.0 AND surprise_score <= 1.0),
contradiction_score REAL DEFAULT 0.0 CHECK (contradiction_score >= 0.0 AND contradiction_score <= 1.0),
detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
reason TEXT,
conflicting_memory_id INTEGER,
FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
CREATE TABLE attention_state (
id INTEGER PRIMARY KEY AUTOINCREMENT,
project_id INTEGER NOT NULL,
focus_memory_id INTEGER NOT NULL,
focus_layer TEXT NOT NULL,
attention_weight REAL DEFAULT 1.0 CHECK (attention_weight >= 0.0 AND attention_weight <= 1.0),
focus_type TEXT DEFAULT 'primary' CHECK (focus_type IN ('primary', 'secondary', 'background')),
started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
ended_at TIMESTAMP,
transition_type TEXT CHECK (transition_type IN ('voluntary', 'automatic', 'interruption', 'return')),
previous_focus_id INTEGER,  -- For context preservation
FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
FOREIGN KEY (previous_focus_id) REFERENCES attention_state(id) ON DELETE SET NULL
);
CREATE TABLE attention_inhibition (
id INTEGER PRIMARY KEY AUTOINCREMENT,
project_id INTEGER NOT NULL,
memory_id INTEGER NOT NULL,
memory_layer TEXT NOT NULL,
inhibition_strength REAL DEFAULT 0.5 CHECK (inhibition_strength >= 0.0 AND inhibition_strength <= 1.0),
inhibition_type TEXT CHECK (inhibition_type IN ('proactive', 'retroactive', 'selective')),
reason TEXT,
inhibited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
expires_at TIMESTAMP,
FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
CREATE TABLE association_links (
id INTEGER PRIMARY KEY AUTOINCREMENT,
project_id INTEGER NOT NULL,
from_memory_id INTEGER NOT NULL,
to_memory_id INTEGER NOT NULL,
from_layer TEXT NOT NULL,
to_layer TEXT NOT NULL,
link_strength REAL DEFAULT 0.5 CHECK (link_strength >= 0.0 AND link_strength <= 1.0),
co_occurrence_count INTEGER DEFAULT 1,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
last_strengthened TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
link_type TEXT DEFAULT 'semantic' CHECK (link_type IN ('semantic', 'temporal', 'causal', 'similarity')),
FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
UNIQUE(project_id, from_memory_id, to_memory_id, from_layer, to_layer)
);
CREATE TABLE activation_state (
id INTEGER PRIMARY KEY AUTOINCREMENT,
project_id INTEGER NOT NULL,
memory_id INTEGER NOT NULL,
memory_layer TEXT NOT NULL,
activation_level REAL DEFAULT 0.0 CHECK (activation_level >= 0.0 AND activation_level <= 1.0),
source_activation_id INTEGER,  -- What triggered this activation
hop_distance INTEGER DEFAULT 0,  -- How many hops from source
activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
UNIQUE(project_id, memory_id, memory_layer)
);
CREATE TABLE priming_state (
id INTEGER PRIMARY KEY AUTOINCREMENT,
project_id INTEGER NOT NULL,
memory_id INTEGER NOT NULL,
memory_layer TEXT NOT NULL,
priming_strength REAL DEFAULT 1.0 CHECK (priming_strength >= 0.0),
primed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
expires_at TIMESTAMP NOT NULL,
FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
UNIQUE(project_id, memory_id, memory_layer)
);
CREATE TABLE memory_access_log (
id INTEGER PRIMARY KEY AUTOINCREMENT,
project_id INTEGER NOT NULL,
memory_id INTEGER NOT NULL,
memory_layer TEXT NOT NULL,
accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
access_type TEXT CHECK (access_type IN ('read', 'update', 'consolidate', 'search')),
context_goal_id INTEGER,  -- What goal was active during access
FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
CREATE TABLE hebbian_stats (
id INTEGER PRIMARY KEY AUTOINCREMENT,
project_id INTEGER NOT NULL,
link_id INTEGER NOT NULL,
strengthening_events INTEGER DEFAULT 0,
last_strengthened TIMESTAMP,
total_strength_delta REAL DEFAULT 0.0,
FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
FOREIGN KEY (link_id) REFERENCES association_links(id) ON DELETE CASCADE,
UNIQUE(project_id, link_id)
);
CREATE INDEX idx_salience_project ON attention_salience(project_id);
CREATE INDEX idx_salience_score ON attention_salience(salience_score DESC);
CREATE INDEX idx_salience_layer ON attention_salience(memory_layer);
CREATE INDEX idx_salience_memory ON attention_salience(memory_id, memory_layer);
CREATE INDEX idx_salience_detected ON attention_salience(detected_at DESC);
CREATE INDEX idx_attention_active ON attention_state(project_id, ended_at) WHERE ended_at IS NULL;
CREATE INDEX idx_attention_weight ON attention_state(attention_weight DESC);
CREATE INDEX idx_attention_memory ON attention_state(focus_memory_id, focus_layer);
CREATE INDEX idx_inhibition_project ON attention_inhibition(project_id);
CREATE INDEX idx_inhibition_memory ON attention_inhibition(memory_id, memory_layer);
CREATE INDEX idx_inhibition_expires ON attention_inhibition(expires_at);
CREATE INDEX idx_inhibition_strength ON attention_inhibition(inhibition_strength DESC);
CREATE INDEX idx_assoc_from ON association_links(from_memory_id, from_layer);
CREATE INDEX idx_assoc_to ON association_links(to_memory_id, to_layer);
CREATE INDEX idx_assoc_strength ON association_links(link_strength DESC);
CREATE INDEX idx_assoc_project ON association_links(project_id);
CREATE INDEX idx_assoc_bidirectional ON association_links(from_memory_id, to_memory_id, from_layer, to_layer);
CREATE INDEX idx_activation_project ON activation_state(project_id);
CREATE INDEX idx_activation_memory ON activation_state(memory_id, memory_layer);
CREATE INDEX idx_activation_level ON activation_state(activation_level DESC);
CREATE INDEX idx_activation_time ON activation_state(activated_at DESC);
CREATE INDEX idx_priming_project ON priming_state(project_id);
CREATE INDEX idx_priming_memory ON priming_state(memory_id, memory_layer);
CREATE INDEX idx_priming_expires ON priming_state(expires_at);
CREATE INDEX idx_access_project ON memory_access_log(project_id);
CREATE INDEX idx_access_time ON memory_access_log(accessed_at DESC);
CREATE INDEX idx_access_memory ON memory_access_log(memory_id, memory_layer);
CREATE INDEX idx_access_goal ON memory_access_log(context_goal_id) WHERE context_goal_id IS NOT NULL;
CREATE INDEX idx_hstats_link ON hebbian_stats(link_id);
CREATE INDEX idx_hstats_project ON hebbian_stats(project_id);
CREATE INDEX idx_hstats_events ON hebbian_stats(strengthening_events DESC);
CREATE TRIGGER update_attention_timestamp
AFTER UPDATE ON attention_state
FOR EACH ROW
BEGIN
UPDATE attention_state SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
CREATE TRIGGER strengthen_on_cooccurrence
AFTER UPDATE OF co_occurrence_count ON association_links
FOR EACH ROW
BEGIN
UPDATE association_links
SET link_strength = MIN(1.0, link_strength + 0.05),
last_strengthened = CURRENT_TIMESTAMP
WHERE id = NEW.id;
END;
CREATE TRIGGER log_strengthening_event
AFTER UPDATE OF link_strength ON association_links
FOR EACH ROW
WHEN NEW.link_strength > OLD.link_strength
BEGIN
INSERT OR IGNORE INTO hebbian_stats (project_id, link_id, strengthening_events, last_strengthened, total_strength_delta)
VALUES (NEW.project_id, NEW.id, 0, CURRENT_TIMESTAMP, 0.0);
UPDATE hebbian_stats
SET strengthening_events = strengthening_events + 1,
last_strengthened = CURRENT_TIMESTAMP,
total_strength_delta = total_strength_delta + (NEW.link_strength - OLD.link_strength)
WHERE link_id = NEW.id;
END;
CREATE VIEW v_attention_current AS
SELECT
s.id,
s.project_id,
s.focus_memory_id,
s.focus_layer,
s.attention_weight,
s.focus_type,
s.started_at,
s.updated_at,
(JULIANDAY('now') - JULIANDAY(s.started_at)) * 86400 as focus_duration_seconds
FROM attention_state s
WHERE s.ended_at IS NULL
ORDER BY s.attention_weight DESC
/* v_attention_current(id,project_id,focus_memory_id,focus_layer,attention_weight,focus_type,started_at,updated_at,focus_duration_seconds) */;
CREATE VIEW v_salient_memories AS
SELECT
s.project_id,
s.memory_id,
s.memory_layer,
s.salience_score,
s.novelty_score,
s.surprise_score,
s.contradiction_score,
s.reason,
s.detected_at,
s.salience_score * EXP(-0.01 * (JULIANDAY('now') - JULIANDAY(s.detected_at)) * 86400) as current_salience
FROM attention_salience s
WHERE s.salience_score > 0.5
ORDER BY current_salience DESC;
CREATE VIEW v_active_inhibitions AS
SELECT
i.project_id,
i.memory_id,
i.memory_layer,
i.inhibition_strength,
i.inhibition_type,
i.reason,
i.inhibited_at,
i.expires_at,
CASE
WHEN i.expires_at IS NULL THEN NULL
ELSE MAX(0, (JULIANDAY(i.expires_at) - JULIANDAY('now')) * 86400)
END as remaining_seconds
FROM attention_inhibition i
WHERE i.expires_at IS NULL OR i.expires_at > CURRENT_TIMESTAMP
ORDER BY i.inhibition_strength DESC
/* v_active_inhibitions(project_id,memory_id,memory_layer,inhibition_strength,inhibition_type,reason,inhibited_at,expires_at,remaining_seconds) */;
CREATE VIEW v_strong_associations AS
SELECT
a.id,
a.project_id,
a.from_memory_id,
a.to_memory_id,
a.from_layer,
a.to_layer,
a.link_strength,
a.co_occurrence_count,
a.link_type,
a.last_strengthened,
a.link_strength * (1.0 - 0.01 * MIN(1.0, (JULIANDAY('now') - JULIANDAY(a.last_strengthened)) / 86400)) as effective_strength
FROM association_links a
WHERE a.link_strength > 0.3
ORDER BY effective_strength DESC
/* v_strong_associations(id,project_id,from_memory_id,to_memory_id,from_layer,to_layer,link_strength,co_occurrence_count,link_type,last_strengthened,effective_strength) */;
CREATE VIEW v_activated_memories AS
SELECT
a.project_id,
a.memory_id,
a.memory_layer,
a.activation_level,
a.hop_distance,
a.activated_at,
(JULIANDAY('now') - JULIANDAY(a.activated_at)) * 86400 as seconds_since_activation,
a.activation_level * EXP(-0.1 * (JULIANDAY('now') - JULIANDAY(a.activated_at)) * 86400) as current_activation
FROM activation_state a
WHERE a.activation_level > 0.1
ORDER BY current_activation DESC;
CREATE VIEW v_primed_memories AS
SELECT
p.project_id,
p.memory_id,
p.memory_layer,
p.priming_strength,
p.primed_at,
p.expires_at,
(JULIANDAY(p.expires_at) - JULIANDAY('now')) * 86400 as remaining_seconds,
CASE
WHEN (JULIANDAY('now') - JULIANDAY(p.primed_at)) * 86400 < 300 THEN 2.0  -- 0-5 min: 2x
WHEN (JULIANDAY('now') - JULIANDAY(p.primed_at)) * 86400 < 1800 THEN 1.5  -- 5-30 min: 1.5x
ELSE 1.2  -- 30-60 min: 1.2x
END * p.priming_strength as current_boost
FROM priming_state p
WHERE p.expires_at > CURRENT_TIMESTAMP
ORDER BY current_boost DESC
/* v_primed_memories(project_id,memory_id,memory_layer,priming_strength,primed_at,expires_at,remaining_seconds,current_boost) */;
CREATE TABLE executive_goals (
id INTEGER PRIMARY KEY AUTOINCREMENT,
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
CREATE TABLE task_switches (
id INTEGER PRIMARY KEY AUTOINCREMENT,
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
CREATE TABLE progress_milestones (
id INTEGER PRIMARY KEY AUTOINCREMENT,
goal_id INTEGER NOT NULL,
milestone_text TEXT NOT NULL,
expected_progress REAL CHECK (expected_progress > 0.0 AND expected_progress <= 1.0),
actual_progress REAL DEFAULT 0.0,
target_date TIMESTAMP,
completed_at TIMESTAMP,
FOREIGN KEY (goal_id) REFERENCES executive_goals(id) ON DELETE CASCADE
);
CREATE TABLE strategy_recommendations (
id INTEGER PRIMARY KEY AUTOINCREMENT,
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
CREATE TABLE executive_metrics (
id INTEGER PRIMARY KEY AUTOINCREMENT,
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
CREATE INDEX idx_executive_goals_project ON executive_goals(project_id);
CREATE INDEX idx_executive_goals_parent ON executive_goals(parent_goal_id);
CREATE INDEX idx_executive_goals_status ON executive_goals(status);
CREATE INDEX idx_executive_goals_deadline ON executive_goals(deadline);
CREATE INDEX idx_task_switches_project ON task_switches(project_id);
CREATE INDEX idx_task_switches_from_to ON task_switches(from_goal_id, to_goal_id);
CREATE INDEX idx_task_switches_timestamp ON task_switches(switched_at);
CREATE INDEX idx_progress_milestones_goal ON progress_milestones(goal_id);
CREATE INDEX idx_strategy_recommendations_goal ON strategy_recommendations(goal_id);
CREATE INDEX idx_executive_metrics_project ON executive_metrics(project_id);
CREATE INDEX idx_executive_metrics_date ON executive_metrics(metric_date);
CREATE VIEW v_active_goals_tree AS
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
GROUP BY g.id
/* v_active_goals_tree(id,project_id,parent_goal_id,goal_text,priority,progress,deadline,estimated_hours,subgoal_count,max_subgoal_progress) */;
CREATE VIEW v_urgent_goals AS
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
ORDER BY g.deadline ASC
/* v_urgent_goals(id,goal_text,priority,progress,deadline,days_remaining,remaining_work) */;
CREATE VIEW v_strategy_effectiveness AS
SELECT
strategy_name,
COUNT(*) as total_recommendations,
SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) as successes,
ROUND(100.0 * SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) /
COUNT(*), 2) as success_rate
FROM strategy_recommendations
WHERE outcome IS NOT NULL
GROUP BY strategy_name
ORDER BY success_rate DESC
/* v_strategy_effectiveness(strategy_name,total_recommendations,successes,success_rate) */;
CREATE INDEX idx_memories_compression_level
ON memories(compression_level);
CREATE INDEX idx_memories_compression_timestamp
ON memories(compression_timestamp);
CREATE INDEX idx_memories_created_at
ON memories(created_at DESC);
CREATE INDEX idx_memories_age_uncompressed
ON memories(created_at)
WHERE compression_level = 0;
CREATE INDEX idx_memories_compression_generated_at
ON memories(compression_generated_at DESC);
CREATE INDEX idx_memories_has_executive
ON memories(compression_generated_at)
WHERE content_executive IS NOT NULL;
CREATE TABLE consolidation_metrics (
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
CREATE INDEX idx_consolidation_metrics_memory_id
ON consolidation_metrics(memory_id);
CREATE INDEX idx_consolidation_metrics_fidelity
ON consolidation_metrics(fidelity_score DESC);
CREATE TABLE project_rules (
id INTEGER PRIMARY KEY AUTOINCREMENT,
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
CREATE INDEX idx_project_rules_project_id ON project_rules(project_id);
CREATE INDEX idx_project_rules_category ON project_rules(category);
CREATE INDEX idx_project_rules_enabled ON project_rules(enabled);
CREATE TABLE rule_validation_history (
id INTEGER PRIMARY KEY AUTOINCREMENT,
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
CREATE INDEX idx_validation_history_task ON rule_validation_history(task_id);
CREATE INDEX idx_validation_history_project ON rule_validation_history(project_id);
CREATE INDEX idx_validation_history_compliant ON rule_validation_history(is_compliant);
CREATE TABLE rule_overrides (
id INTEGER PRIMARY KEY AUTOINCREMENT,
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
CREATE INDEX idx_overrides_project ON rule_overrides(project_id);
CREATE INDEX idx_overrides_rule ON rule_overrides(rule_id);
CREATE INDEX idx_overrides_status ON rule_overrides(status);
CREATE TABLE rule_templates (
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT NOT NULL UNIQUE,
description TEXT NOT NULL,
category TEXT NOT NULL,
rules TEXT NOT NULL,  -- JSON array of Rule objects
usage_count INTEGER DEFAULT 0,
created_at INTEGER NOT NULL
);
CREATE INDEX idx_templates_category ON rule_templates(category);
CREATE TABLE project_rule_config (
id INTEGER PRIMARY KEY AUTOINCREMENT,
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
CREATE INDEX idx_rule_config_project ON project_rule_config(project_id);
CREATE VIEW tasks AS SELECT * FROM prospective_tasks
/* tasks(id,project_id,content,active_form,created_at,due_at,completed_at,status,priority,assignee,notes,blocked_reason,phase,plan_json,plan_created_at,phase_started_at,phase_metrics_json,actual_duration_minutes,lessons_learned,failure_reason) */;
CREATE TABLE semantic_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                tags TEXT,
                importance REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
CREATE TABLE knowledge_gaps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gap_type TEXT NOT NULL,
                domain TEXT,
                severity TEXT DEFAULT 'medium',
                description TEXT NOT NULL,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                resolution_notes TEXT
            );
