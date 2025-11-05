"""Phase 7.2 MCP tools for Spatial-Temporal Grounding.

Provides MCP tool handlers for Phase 7.2 integration:
- link_code_to_spatial: Link code context to spatial hierarchy
- get_temporal_context: Retrieve temporal event chains
- traverse_relationships: Navigate entity relationships graph
"""

from typing import Optional

from athena.ai_coordination.integration.spatial_grounding import SpatialGrounder
from athena.ai_coordination.integration.temporal_chaining import TemporalChainer
from athena.ai_coordination.integration.graph_linking import GraphLinker, EntityType, RelationType


class Phase72MCPTools:
    """MCP tool handlers for Phase 7.2 Spatial-Temporal Grounding."""

    def __init__(
        self,
        spatial_grounding: SpatialGrounder,
        temporal_chaining: TemporalChainer,
        graph_linking: GraphLinker
    ):
        """Initialize Phase 7.2 MCP tools.

        Args:
            spatial_grounding: SpatialGrounder instance
            temporal_chaining: TemporalChainer instance
            graph_linking: GraphLinker instance
        """
        self.spatial = spatial_grounding
        self.temporal = temporal_chaining
        self.graph = graph_linking

    def link_code_to_spatial(
        self,
        task_id: str,
        file_paths: list[str],
        episodic_event_id: int
    ) -> dict:
        """Link code context files to spatial hierarchy.

        Creates spatial hierarchy links for code files involved in a task.
        Enables spatial-aware memory queries like "what happened in src/auth/".

        Args:
            task_id: Task identifier
            file_paths: List of file paths involved
            episodic_event_id: Corresponding episodic event ID

        Returns:
            Dict with link results
        """
        try:
            # Create simple code context for linking
            class SimpleCodeContext:
                def __init__(self, file_paths):
                    self.context_id = f"task_{task_id}"
                    self.relevant_files = file_paths
                    self.file_count = len(file_paths)
                    self.dependency_types = []

            code_context = SimpleCodeContext(file_paths)

            # Link to spatial
            link_count = self.spatial.link_code_context_to_spatial(
                code_context,
                episodic_event_id,
                task_id
            )

            return {
                "status": "success",
                "task_id": task_id,
                "file_count": len(file_paths),
                "links_created": link_count,
                "files": file_paths,
            }
        except Exception as e:
            return {
                "status": "error",
                "task_id": task_id,
                "error": str(e),
            }

    def get_temporal_context(
        self,
        event_id: int,
        include_sequence: bool = True,
        include_causality: bool = True
    ) -> dict:
        """Get temporal context for an episodic event.

        Retrieves the temporal chain of events (what came before and after)
        plus causal relationships for understanding event sequences.

        Args:
            event_id: Episodic event ID
            include_sequence: Whether to include full event sequence
            include_causality: Whether to include causal relationships

        Returns:
            Dict with temporal context
        """
        try:
            result = {
                "status": "success",
                "event_id": event_id,
            }

            # Get temporal chain
            chain = self.temporal.get_temporal_chain(event_id)
            result["chain"] = chain

            # Get causal relationships
            if include_causality:
                causality = self.temporal.get_causal_relationships(event_id, min_strength=0.5)
                result["causal_relationships"] = causality

            # Get session sequence if available
            if include_sequence:
                # Find session for this event via temporal chains
                if chain["predecessors"]:
                    # Get full sequence context
                    result["has_sequence_context"] = True
                else:
                    result["has_sequence_context"] = False

            return result
        except Exception as e:
            return {
                "status": "error",
                "event_id": event_id,
                "error": str(e),
            }

    def traverse_relationships(
        self,
        entity_name: str,
        entity_type: str,
        max_depth: int = 3,
        relation_types: Optional[list[str]] = None
    ) -> dict:
        """Traverse entity relationships in knowledge graph.

        Navigate through the knowledge graph starting from an entity,
        following typed relationships up to specified depth.

        Args:
            entity_name: Name of entity to start from
            entity_type: Type of entity (file, function, class, module, pattern)
            max_depth: Maximum traversal depth
            relation_types: Optional list of relationship types to follow

        Returns:
            Dict with graph structure
        """
        try:
            # Get entity
            entity_type_enum = EntityType(entity_type)
            entity = self.graph.get_entity(entity_name, entity_type_enum)

            if not entity:
                return {
                    "status": "not_found",
                    "entity_name": entity_name,
                    "entity_type": entity_type,
                }

            # Convert relation_types to enums if provided
            relation_enums = None
            if relation_types:
                try:
                    relation_enums = [RelationType(rt) for rt in relation_types]
                except ValueError as e:
                    return {
                        "status": "error",
                        "error": f"Invalid relation type: {e}",
                    }

            # Traverse graph
            graph = self.graph.traverse_graph(
                entity["id"],
                max_depth,
                relation_enums
            )

            # Get entity stats
            stats = self.graph.get_entity_stats(entity["id"])

            return {
                "status": "success",
                "entity": entity,
                "stats": stats,
                "graph": {
                    "node_count": len(graph["nodes"]),
                    "edge_count": len(graph["edges"]),
                    "nodes": graph["nodes"],
                    "edges": graph["edges"],
                },
            }
        except ValueError as e:
            return {
                "status": "error",
                "error": f"Invalid entity type: {e}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def get_task_scope(self, task_id: str) -> dict:
        """Get the code scope (files) of a task.

        Args:
            task_id: Task identifier

        Returns:
            Dict with task scope
        """
        try:
            scope = self.spatial.get_task_scope(task_id)
            return {
                "status": "success",
                "scope": scope,
            }
        except Exception as e:
            return {
                "status": "error",
                "task_id": task_id,
                "error": str(e),
            }

    def get_execution_locations(self, execution_id: str) -> dict:
        """Get all code locations accessed during execution.

        Args:
            execution_id: Execution identifier

        Returns:
            Dict with execution locations
        """
        try:
            locations = self.spatial.get_execution_locations(execution_id)
            return {
                "status": "success",
                "execution_id": execution_id,
                "location_count": len(locations),
                "locations": locations,
            }
        except Exception as e:
            return {
                "status": "error",
                "execution_id": execution_id,
                "error": str(e),
            }

    def build_session_sequence(
        self,
        session_id: str,
        goal_id: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> dict:
        """Build execution sequence for a session.

        Args:
            session_id: Session identifier
            goal_id: Optional goal ID
            task_id: Optional task ID

        Returns:
            Dict with sequence results
        """
        try:
            count = self.temporal.build_session_sequence(session_id, goal_id, task_id)
            metrics = self.temporal.calculate_sequence_metrics(session_id)
            return {
                "status": "success",
                "session_id": session_id,
                "sequences_created": count,
                "metrics": metrics,
            }
        except Exception as e:
            return {
                "status": "error",
                "session_id": session_id,
                "error": str(e),
            }

    def detect_event_patterns(
        self,
        session_id: str,
        pattern_length: int = 3
    ) -> dict:
        """Detect repeating patterns in event sequence.

        Args:
            session_id: Session identifier
            pattern_length: Length of patterns to detect

        Returns:
            Dict with detected patterns
        """
        try:
            patterns = self.temporal.detect_event_patterns(session_id, pattern_length)
            return {
                "status": "success",
                "session_id": session_id,
                "pattern_length": pattern_length,
                "pattern_count": len(patterns),
                "patterns": patterns,
            }
        except Exception as e:
            return {
                "status": "error",
                "session_id": session_id,
                "error": str(e),
            }
