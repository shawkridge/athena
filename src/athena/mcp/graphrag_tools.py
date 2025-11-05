"""MCP tools for GraphRAG community detection and multi-level retrieval."""

from mcp.types import Tool, TextContent
from typing import Any, List

from ..graph.communities import CommunityAnalyzer, LeidenClustering
from ..graph.store import GraphStore
from ..core.database import Database


def get_graphrag_tools() -> list[Tool]:
    """Get GraphRAG MCP tool definitions."""
    return [
        Tool(
            name="detect_graph_communities",
            description="Detect communities in knowledge graph using Leiden clustering algorithm. Returns communities with density, internal edges, and summaries. Better quality than Louvain.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Project ID to analyze"
                    },
                    "min_community_size": {
                        "type": "integer",
                        "description": "Minimum nodes in a community (default: 2)",
                        "default": 2
                    },
                    "max_iterations": {
                        "type": "integer",
                        "description": "Maximum clustering iterations (default: 100)",
                        "default": 100
                    },
                },
                "required": ["project_id"],
            }
        ),
        Tool(
            name="get_community_details",
            description="Get detailed information about a specific community including members, density, edges, and summary.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Project ID"
                    },
                    "community_id": {
                        "type": "integer",
                        "description": "Community ID to get details for"
                    },
                },
                "required": ["project_id", "community_id"],
            }
        ),
        Tool(
            name="query_communities_by_level",
            description="Query communities at specific hierarchical level (0=granular, 1=intermediate, 2=global). Enables multi-level reasoning.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Project ID"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "level": {
                        "type": "integer",
                        "description": "Query level: 0=granular, 1=intermediate, 2=global (default: 0)",
                        "default": 0,
                        "enum": [0, 1, 2]
                    },
                },
                "required": ["project_id", "query"],
            }
        ),
        Tool(
            name="analyze_community_connectivity",
            description="Analyze internal vs external connectivity of communities. Shows cohesion and isolation metrics.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Project ID"
                    },
                },
                "required": ["project_id"],
            }
        ),
        Tool(
            name="find_bridge_entities",
            description="Find entities that bridge multiple communities (high external degree). Useful for understanding cross-cutting concerns.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Project ID"
                    },
                    "threshold": {
                        "type": "integer",
                        "description": "Minimum edges to other communities (default: 3)",
                        "default": 3
                    },
                },
                "required": ["project_id"],
            }
        ),
    ]


class GraphRAGMCPHandlers:
    """MCP handlers for GraphRAG operations."""

    def __init__(self, db: Database):
        """Initialize handlers.

        Args:
            db: Database connection
        """
        self.db = db
        self.graph_store = GraphStore(db)
        self.analyzer = CommunityAnalyzer(db)
        self.communities_cache = {}

    async def detect_graph_communities(
        self,
        project_id: int,
        min_community_size: int = 2,
        max_iterations: int = 100,
    ) -> TextContent:
        """Detect communities using Leiden algorithm."""
        try:
            # Get all entities and relations
            entities = self.graph_store.list_entities(project_id)
            relations = self.graph_store.list_relations(project_id)

            if not entities:
                return TextContent(type="text", text=f"No entities found in project {project_id}")

            # Analyze with Leiden
            communities = self.analyzer.analyze_with_leiden(
                entities, relations, project_id
            )

            # Cache results
            self.communities_cache[project_id] = communities

            # Format output
            lines = [f"Community Detection Results (Leiden Algorithm):\n"]
            lines.append(f"Project: {project_id}")
            lines.append(f"Total Communities: {len(communities)}")
            lines.append(f"Total Entities: {len(entities)}\n")

            for comm in sorted(communities.values(), key=lambda c: c.size, reverse=True)[:10]:
                lines.append(f"Community {comm.id} (Size: {comm.size}):")
                lines.append(f"  Entities: {', '.join(comm.entity_names[:5])}")
                if len(comm.entity_names) > 5:
                    lines.append(f"    + {len(comm.entity_names) - 5} more")
                lines.append(f"  Density: {comm.density:.2%}")
                lines.append(f"  Internal Edges: {comm.internal_edges}")
                lines.append(f"  External Edges: {comm.external_edges}")
                lines.append(f"  Summary: {comm.summary}\n")

            return TextContent(type="text", text="\n".join(lines))
        except Exception as e:
            return TextContent(type="text", text=f"❌ Error: {str(e)}")

    async def get_community_details(self, project_id: int, community_id: int) -> TextContent:
        """Get community details."""
        try:
            communities = self.communities_cache.get(project_id)
            if not communities:
                return TextContent(
                    type="text",
                    text=f"Run detect_graph_communities first to load communities for project {project_id}"
                )

            community = communities.get(community_id)
            if not community:
                return TextContent(
                    type="text",
                    text=f"Community {community_id} not found in project {project_id}"
                )

            lines = [f"Community {community.id} Details:\n"]
            lines.append(f"Size: {community.size} entities")
            lines.append(f"Density: {community.density:.2%}")
            lines.append(f"Internal Edges: {community.internal_edges}")
            lines.append(f"External Edges: {community.external_edges}")
            lines.append(f"Cohesion: {community.internal_edges / (community.internal_edges + community.external_edges + 1):.2%}\n")
            lines.append("Members:")
            for i, name in enumerate(community.entity_names, 1):
                lines.append(f"  {i}. {name}")
            lines.append(f"\nSummary: {community.summary}")

            return TextContent(type="text", text="\n".join(lines))
        except Exception as e:
            return TextContent(type="text", text=f"❌ Error: {str(e)}")

    async def query_communities_by_level(
        self,
        project_id: int,
        query: str,
        level: int = 0,
    ) -> TextContent:
        """Query communities at specific level."""
        try:
            communities = self.communities_cache.get(project_id)
            if not communities:
                return TextContent(
                    type="text",
                    text=f"Run detect_graph_communities first for project {project_id}"
                )

            # Filter by level
            matching = self.analyzer.multi_level_query(query, communities, level)

            lines = [f"Communities matching '{query}' at level {level}:\n"]
            lines.append(f"Found: {len(matching)} communities\n")

            for comm in matching[:10]:
                lines.append(f"Community {comm.id}:")
                lines.append(f"  Members: {', '.join(comm.entity_names[:5])}")
                if len(comm.entity_names) > 5:
                    lines.append(f"    + {len(comm.entity_names) - 5} more")
                lines.append(f"  Density: {comm.density:.2%}\n")

            return TextContent(type="text", text="\n".join(lines))
        except Exception as e:
            return TextContent(type="text", text=f"❌ Error: {str(e)}")

    async def analyze_community_connectivity(self, project_id: int) -> TextContent:
        """Analyze community connectivity."""
        try:
            communities = self.communities_cache.get(project_id)
            if not communities:
                return TextContent(
                    type="text",
                    text=f"Run detect_graph_communities first for project {project_id}"
                )

            total_internal = sum(c.internal_edges for c in communities.values())
            total_external = sum(c.external_edges for c in communities.values())
            total_edges = total_internal + total_external

            avg_density = sum(c.density for c in communities.values()) / len(communities) if communities else 0
            avg_size = sum(c.size for c in communities.values()) / len(communities) if communities else 0

            lines = [f"Community Connectivity Analysis:\n"]
            lines.append(f"Communities: {len(communities)}")
            lines.append(f"Total Internal Edges: {total_internal}")
            lines.append(f"Total External Edges: {total_external}")
            lines.append(f"Total Edges: {total_edges}")
            lines.append(f"Internal/External Ratio: {total_internal / (total_external + 1):.2f}\n")
            lines.append(f"Average Density: {avg_density:.2%}")
            lines.append(f"Average Community Size: {avg_size:.1f}")

            # Show most/least connected
            sorted_by_cohesion = sorted(
                communities.values(),
                key=lambda c: c.internal_edges / (c.internal_edges + c.external_edges + 1),
                reverse=True
            )

            lines.append(f"\nMost Cohesive Communities:")
            for c in sorted_by_cohesion[:5]:
                cohesion = c.internal_edges / (c.internal_edges + c.external_edges + 1)
                lines.append(f"  Community {c.id}: {cohesion:.2%}")

            return TextContent(type="text", text="\n".join(lines))
        except Exception as e:
            return TextContent(type="text", text=f"❌ Error: {str(e)}")

    async def find_bridge_entities(self, project_id: int, threshold: int = 3) -> TextContent:
        """Find bridge entities connecting communities."""
        try:
            # Get all entities and relations
            entities = self.graph_store.list_entities(project_id)
            relations = self.graph_store.list_relations(project_id)

            communities = self.communities_cache.get(project_id)
            if not communities:
                return TextContent(
                    type="text",
                    text=f"Run detect_graph_communities first for project {project_id}"
                )

            # Map entity_id to community_id
            entity_to_community = {}
            for comm in communities.values():
                for entity_id in comm.entity_ids:
                    entity_to_community[entity_id] = comm.id

            # Count external connections per entity
            entity_external_edges = {}
            for rel in relations:
                from_comm = entity_to_community.get(rel.from_entity_id)
                to_comm = entity_to_community.get(rel.to_entity_id)

                if from_comm and to_comm and from_comm != to_comm:
                    entity_external_edges[rel.from_entity_id] = entity_external_edges.get(rel.from_entity_id, 0) + 1
                    entity_external_edges[rel.to_entity_id] = entity_external_edges.get(rel.to_entity_id, 0) + 1

            # Find entities with external_edges >= threshold
            entity_map = {e.id: e for e in entities}
            bridges = [
                (entity_id, entity_external_edges[entity_id])
                for entity_id in entity_external_edges
                if entity_external_edges[entity_id] >= threshold
            ]

            bridges.sort(key=lambda x: x[1], reverse=True)

            lines = [f"Bridge Entities (threshold: {threshold} external edges):\n"]
            lines.append(f"Found: {len(bridges)} bridge entities\n")

            for entity_id, edge_count in bridges[:20]:
                entity = entity_map.get(entity_id)
                comm_id = entity_to_community.get(entity_id)
                lines.append(f"Entity: {entity.name if entity else f'ID_{entity_id}'}")
                lines.append(f"  Community: {comm_id}")
                lines.append(f"  External Edges: {edge_count}\n")

            return TextContent(type="text", text="\n".join(lines))
        except Exception as e:
            return TextContent(type="text", text=f"❌ Error: {str(e)}")
