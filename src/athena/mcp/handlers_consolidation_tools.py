"""
High-level MCP tools for knowledge graph consolidation.

Following Anthropic's code execution with MCP pattern:
- Expose consolidation operations as tools
- Let orchestration layer write code to call these tools
- Reduce token usage by batching operations
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ConsolidationTools:
    """MCP tools for knowledge graph consolidation and extraction."""

    def __init__(self, memory_manager):
        """Initialize consolidation tools.

        Args:
            memory_manager: UnifiedMemoryManager instance
        """
        self.memory_manager = memory_manager

    def extract_entities_from_episodic_events(
        self,
        project_id: int,
        hours_back: int = 24,
        min_events: int = 3
    ) -> Dict[str, Any]:
        """Extract entities from episodic events using NLP and pattern matching.

        Consolidates episodic events into knowledge graph entities by:
        1. Querying recent episodic events
        2. Extracting named entities and concepts
        3. Creating entities in knowledge graph
        4. Linking related events

        Args:
            project_id: Project to consolidate
            hours_back: How many hours of events to process
            min_events: Minimum events to trigger consolidation

        Returns:
            {
                "success": bool,
                "entities_created": int,
                "entities_updated": int,
                "observations_added": int,
                "events_processed": int,
                "timestamp": str
            }
        """
        try:
            from ..integration.episodic_to_graph import EpisodicGraphExtractor

            extractor = EpisodicGraphExtractor(self.memory_manager.db)
            result = extractor.extract_and_populate(
                project_id=project_id,
                hours_back=hours_back,
                min_events=min_events
            )

            logger.info(
                f"Extracted {result.get('entities_created', 0)} entities "
                f"from {result.get('events_processed', 0)} episodic events "
                f"for project {project_id}"
            )
            return result

        except Exception as e:
            logger.error(f"Error extracting entities from episodic events: {e}")
            return {
                "success": False,
                "error": str(e),
                "entities_created": 0,
                "entities_updated": 0,
                "observations_added": 0,
                "events_processed": 0,
            }

    def synthesize_temporal_relationships(
        self,
        project_id: int,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Synthesize temporal relationships in knowledge graph.

        Uses temporal KG synthesis to infer relationships based on:
        1. Event causality (what caused what)
        2. Event recency (recent events are related)
        3. Event frequency (repeated patterns)
        4. Dependencies (prerequisite relationships)

        Args:
            project_id: Project to synthesize
            session_id: Optional session ID to limit scope

        Returns:
            {
                "success": bool,
                "relationships_created": int,
                "relationships_updated": int,
                "causality_inferred": int,
                "dependencies_discovered": int,
                "timestamp": str
            }
        """
        try:
            from ..temporal.kg_synthesis import TemporalKGSynthesizer

            synthesizer = TemporalKGSynthesizer(self.memory_manager.db)
            result = synthesizer.synthesize(
                project_id=project_id,
                session_id=session_id
            )

            logger.info(
                f"Synthesized {result.get('relationships_created', 0)} temporal "
                f"relationships for project {project_id}"
            )
            return result

        except Exception as e:
            logger.error(f"Error synthesizing temporal relationships: {e}")
            return {
                "success": False,
                "error": str(e),
                "relationships_created": 0,
                "relationships_updated": 0,
                "causality_inferred": 0,
                "dependencies_discovered": 0,
            }

    def extract_code_graph(
        self,
        project_id: int,
        project_path: str
    ) -> Dict[str, Any]:
        """Extract code structure into knowledge graph.

        Analyzes code symbols and creates entities for:
        1. Functions, classes, modules
        2. Code relationships (imports, inheritance, calls)
        3. Code metrics (complexity, coupling)
        4. Dependencies and patterns

        Args:
            project_id: Project ID
            project_path: Path to project code

        Returns:
            {
                "success": bool,
                "entities_created": int,
                "relationships_created": int,
                "files_analyzed": int,
                "symbols_found": int,
                "timestamp": str
            }
        """
        try:
            from ..code_search.code_graph_integration import CodeGraphBuilder

            builder = CodeGraphBuilder(self.memory_manager.db)
            result = builder.analyze_project(
                project_id=project_id,
                project_path=project_path
            )

            logger.info(
                f"Extracted {result.get('entities_created', 0)} code entities "
                f"from {result.get('files_analyzed', 0)} files in project {project_id}"
            )
            return result

        except Exception as e:
            logger.error(f"Error extracting code graph: {e}")
            return {
                "success": False,
                "error": str(e),
                "entities_created": 0,
                "relationships_created": 0,
                "files_analyzed": 0,
                "symbols_found": 0,
            }

    def consolidate_learned_patterns(
        self,
        project_id: int,
        pattern_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Link learned patterns to knowledge graph entities.

        Creates entities for discovered patterns and links them to:
        1. Code entities that implement patterns
        2. Procedural memories that use patterns
        3. Related semantic insights

        Args:
            project_id: Project ID
            pattern_ids: Optional list of pattern IDs to consolidate

        Returns:
            {
                "success": bool,
                "patterns_linked": int,
                "entities_created": int,
                "relationships_created": int,
                "timestamp": str
            }
        """
        try:
            from ..consolidation.pattern_consolidator import PatternConsolidator

            consolidator = PatternConsolidator(self.memory_manager.db)
            result = consolidator.link_patterns_to_graph(
                project_id=project_id,
                pattern_ids=pattern_ids
            )

            logger.info(
                f"Linked {result.get('patterns_linked', 0)} patterns "
                f"to knowledge graph for project {project_id}"
            )
            return result

        except Exception as e:
            logger.error(f"Error consolidating patterns: {e}")
            return {
                "success": False,
                "error": str(e),
                "patterns_linked": 0,
                "entities_created": 0,
                "relationships_created": 0,
            }

    def perform_full_consolidation(
        self,
        project_id: int,
        session_id: Optional[str] = None,
        include_code_analysis: bool = True
    ) -> Dict[str, Any]:
        """Perform complete consolidation (semantic + knowledge graph).

        Orchestrates all consolidation steps:
        1. Run semantic consolidation (episodic→semantic memory conversion)
        2. Extract entities from episodic events (for graph)
        3. Synthesize temporal relationships
        4. Consolidate learned patterns
        5. Optionally analyze code graph

        This is the main consolidation entry point that unifies both
        semantic and graph consolidation in a single pass.

        Args:
            project_id: Project ID
            session_id: Optional session ID to limit scope
            include_code_analysis: Whether to analyze code graph

        Returns:
            {
                "success": bool,
                "total_entities_created": int,
                "total_relationships_created": int,
                "consolidation_stages": {
                    "semantic_consolidation": {...},
                    "episodic_extraction": {...},
                    "temporal_synthesis": {...},
                    "pattern_consolidation": {...},
                    "code_analysis": {...}
                },
                "duration_seconds": float,
                "timestamp": str
            }
        """
        try:
            import time
            start_time = time.time()

            results = {
                "success": True,
                "total_entities_created": 0,
                "total_relationships_created": 0,
                "consolidation_stages": {},
                "timestamp": datetime.now().isoformat(),
            }

            # Stage 0: Run semantic consolidation (episodic→semantic→graph)
            # This unified step handles: episodic memory processing, semantic learning,
            # temporal KG synthesis, and graph-to-semantic feedback
            logger.info(f"Stage 0: Running semantic consolidation (project {project_id})")
            try:
                if hasattr(self.memory_manager, 'consolidation_system'):
                    semantic_run_id = self.memory_manager.consolidation_system.run_consolidation(
                        project_id=project_id
                    )
                    results["consolidation_stages"]["semantic_consolidation"] = {
                        "success": True,
                        "run_id": semantic_run_id,
                        "includes": ["episodic_processing", "semantic_learning", "temporal_kg_synthesis", "graph_feedback"]
                    }
                    logger.info(f"Semantic consolidation completed with run_id {semantic_run_id}")
            except Exception as e:
                logger.warning(f"Semantic consolidation failed: {e}")
                results["consolidation_stages"]["semantic_consolidation"] = {
                    "success": False,
                    "error": str(e)
                }

            # Stage 1: Extract from episodic events
            logger.info(f"Stage 1: Extracting entities from episodic events (project {project_id})")
            episodic_result = self.extract_entities_from_episodic_events(project_id)
            results["consolidation_stages"]["episodic_extraction"] = episodic_result
            if episodic_result.get("success"):
                results["total_entities_created"] += episodic_result.get("entities_created", 0)

            # Stage 2: Synthesize temporal relationships
            logger.info(f"Stage 2: Synthesizing temporal relationships (project {project_id})")
            temporal_result = self.synthesize_temporal_relationships(project_id, session_id)
            results["consolidation_stages"]["temporal_synthesis"] = temporal_result
            if temporal_result.get("success"):
                results["total_relationships_created"] += temporal_result.get("relationships_created", 0)

            # Stage 3: Consolidate patterns
            logger.info(f"Stage 3: Consolidating learned patterns (project {project_id})")
            pattern_result = self.consolidate_learned_patterns(project_id)
            results["consolidation_stages"]["pattern_consolidation"] = pattern_result
            if pattern_result.get("success"):
                results["total_entities_created"] += pattern_result.get("entities_created", 0)
                results["total_relationships_created"] += pattern_result.get("relationships_created", 0)

            # Stage 4: Code analysis (optional)
            if include_code_analysis:
                logger.info(f"Stage 4: Analyzing code graph (project {project_id})")
                try:
                    # Get project path
                    project = self.memory_manager.db.get_project(project_id)
                    if project and project.get("path"):
                        code_result = self.extract_code_graph(project_id, project["path"])
                        results["consolidation_stages"]["code_analysis"] = code_result
                        if code_result.get("success"):
                            results["total_entities_created"] += code_result.get("entities_created", 0)
                            results["total_relationships_created"] += code_result.get("relationships_created", 0)
                except Exception as e:
                    logger.warning(f"Code analysis skipped: {e}")
                    results["consolidation_stages"]["code_analysis"] = {
                        "skipped": True,
                        "reason": str(e)
                    }

            results["duration_seconds"] = time.time() - start_time

            logger.info(
                f"Full consolidation complete: {results['total_entities_created']} entities, "
                f"{results['total_relationships_created']} relationships in {results['duration_seconds']:.1f}s"
            )

            return results

        except Exception as e:
            logger.error(f"Error during full consolidation: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_entities_created": 0,
                "total_relationships_created": 0,
                "consolidation_stages": {},
                "timestamp": datetime.now().isoformat(),
            }

    def get_consolidation_status(
        self,
        project_id: int
    ) -> Dict[str, Any]:
        """Get current consolidation status and statistics.

        Returns:
            {
                "project_id": int,
                "total_entities": int,
                "total_relationships": int,
                "total_observations": int,
                "communities_detected": int,
                "last_consolidation": str,
                "entities_by_type": {type: count},
                "relationships_by_type": {type: count}
            }
        """
        try:
            from ..graph.store import GraphStore

            graph_store = GraphStore(self.memory_manager.db)

            # Count entities
            entities = graph_store.get_all_for_project(project_id)
            entity_types = {}
            for entity in entities:
                etype = entity.entity_type.value if hasattr(entity.entity_type, 'value') else str(entity.entity_type)
                entity_types[etype] = entity_types.get(etype, 0) + 1

            # Count relationships
            relations = graph_store.get_relations_for_project(project_id)
            relation_types = {}
            for relation in relations:
                rtype = relation.relation_type.value if hasattr(relation.relation_type, 'value') else str(relation.relation_type)
                relation_types[rtype] = relation_types.get(rtype, 0) + 1

            return {
                "project_id": project_id,
                "total_entities": len(entities),
                "total_relationships": len(relations),
                "total_observations": graph_store.count_observations(project_id),
                "communities_detected": graph_store.count_communities(project_id),
                "entities_by_type": entity_types,
                "relationships_by_type": relation_types,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting consolidation status: {e}")
            return {
                "project_id": project_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
