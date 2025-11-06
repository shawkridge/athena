"""External knowledge handlers: ConceptNet API integration, knowledge expansion.

This module contains MCP tool handlers for:
- External knowledge lookup (ConceptNet)
- Knowledge graph expansion
- Relation discovery and exploration
- Knowledge synthesis and summarization

Organized by domain for clarity and maintainability.
"""

import json
import logging
from typing import Any, List, Optional

from mcp.types import TextContent

logger = logging.getLogger(__name__)


# ============================================================================
# EXTERNAL KNOWLEDGE MODULE HANDLERS
# ============================================================================

async def handle_lookup_external_knowledge(server: Any, args: dict) -> List[TextContent]:
    """Look up external knowledge about a concept using ConceptNet.

    Returns semantic relations and contextual information.
    """
    try:
        concept = args.get("concept", "")
        relation_types = args.get("relation_types", None)  # Optional: filter by relation type
        limit = args.get("limit", 10)
        language = args.get("language", "en")

        if not concept:
            return [TextContent(type="text", text="Error: concept parameter is required")]

        # Lazy initialize ConceptNetAPI
        if not hasattr(server, '_conceptnet_api'):
            from ..external.conceptnet_api import ConceptNetAPI
            server._conceptnet_api = ConceptNetAPI()

        # Look up knowledge
        try:
            relations = server._conceptnet_api.get_relations(
                concept=concept,
                relation_types=relation_types,
                limit=limit,
                language=language
            )

            # Format relations
            formatted_relations = []
            for i, rel in enumerate(relations or [], 1):
                formatted_relations.append(
                    f"**{rel['relation']}** → {rel['target']}\n"
                    f"Weight: {rel.get('weight', 'N/A'):.2f}"
                )

            if not formatted_relations:
                result_text = "No external knowledge found for this concept."
            else:
                result_text = "\n\n".join(formatted_relations)

            response = f"""**External Knowledge Lookup**
Concept: {concept}
Language: {language}
Relations Found: {len(relations) if relations else 0}

{result_text}"""

            return [TextContent(type="text", text=response)]

        except Exception as lookup_err:
            logger.debug(f"Knowledge lookup error: {lookup_err}")
            return [TextContent(type="text", text=f"Error: {str(lookup_err)}")]

    except Exception as e:
        logger.error(f"Error in handle_lookup_external_knowledge: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_expand_knowledge_relations(server: Any, args: dict) -> List[TextContent]:
    """Expand knowledge graph by discovering related concepts.

    Performs multi-hop traversal to discover connected concepts.
    """
    try:
        concept = args.get("concept", "")
        max_hops = args.get("max_hops", 2)
        relation_filter = args.get("relation_filter", None)  # Optional: specific relations only
        limit = args.get("limit", 20)

        if not concept:
            return [TextContent(type="text", text="Error: concept parameter is required")]

        # Lazy initialize ConceptNetAPI
        if not hasattr(server, '_conceptnet_api'):
            from ..external.conceptnet_api import ConceptNetAPI
            server._conceptnet_api = ConceptNetAPI()

        # Expand knowledge
        try:
            expansion = server._conceptnet_api.expand_concept(
                concept=concept,
                max_hops=max_hops,
                relation_filter=relation_filter,
                limit=limit
            )

            # Format expansion results
            levels = []
            for hop, concepts in (expansion.get("levels") or {}).items():
                level_text = f"**Hop {hop}**: {', '.join(concepts[:10])}"
                if len(concepts) > 10:
                    level_text += f" (+{len(concepts) - 10} more)"
                levels.append(level_text)

            if not levels:
                levels_text = "No related concepts found."
            else:
                levels_text = "\n".join(levels)

            response = f"""**Knowledge Graph Expansion**
Concept: {concept}
Max Hops: {max_hops}
Total Concepts Found: {expansion.get('total_concepts', 0)}

{levels_text}"""

            return [TextContent(type="text", text=response)]

        except Exception as expand_err:
            logger.debug(f"Knowledge expansion error: {expand_err}")
            return [TextContent(type="text", text=f"Error: {str(expand_err)}")]

    except Exception as e:
        logger.error(f"Error in handle_expand_knowledge_relations: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_synthesize_knowledge(server: Any, args: dict) -> List[TextContent]:
    """Synthesize knowledge from multiple sources.

    Combines ConceptNet relations with internal knowledge graph.
    """
    try:
        concept = args.get("concept", "")
        synthesis_type = args.get("synthesis_type", "comprehensive")  # comprehensive, summary, relationships
        depth = args.get("depth", 2)

        if not concept:
            return [TextContent(type="text", text="Error: concept parameter is required")]

        # Lazy initialize managers
        if not hasattr(server, '_conceptnet_api'):
            from ..external.conceptnet_api import ConceptNetAPI
            server._conceptnet_api = ConceptNetAPI()

        # Get external knowledge
        try:
            external = server._conceptnet_api.get_relations(concept=concept, limit=20)

            # Get internal knowledge from graph if available
            internal = []
            if hasattr(server, 'memory_manager') and server.memory_manager:
                try:
                    internal_results = server.memory_manager.retrieve(concept, k=5)
                    if "graph" in internal_results:
                        internal = internal_results["graph"]
                except Exception as graph_err:
                    logger.debug(f"Graph retrieval error: {graph_err}")

            # Synthesize
            if synthesis_type == "summary":
                # Short summary
                ext_count = len(external) if external else 0
                int_count = len(internal) if internal else 0
                synthesis_text = f"**{concept}** has {ext_count} external relations and {int_count} internal connections."

            elif synthesis_type == "relationships":
                # Show key relationships
                parts = []
                if external:
                    parts.append("**External Relations**:\n" + "\n".join(
                        f"- {r['relation']}: {r['target']}" for r in external[:5]
                    ))
                if internal:
                    parts.append("**Internal Connections**:\n" + "\n".join(
                        f"- {item.get('entity', 'Unknown')}" for item in internal[:5]
                    ))
                synthesis_text = "\n\n".join(parts) if parts else "No knowledge found."

            else:  # comprehensive
                # Full synthesis
                parts = []
                if external:
                    parts.append(f"**External Knowledge** ({len(external)} relations):\n" +
                                "\n".join(f"- {r['relation']}: {r['target']}" for r in external[:10]))
                if internal:
                    parts.append(f"**Internal Knowledge** ({len(internal)} items):\n" +
                                "\n".join(f"- {item.get('entity', 'Unknown')}" for item in internal[:10]))
                synthesis_text = "\n\n".join(parts) if parts else "No knowledge found."

            response = f"""**Knowledge Synthesis**
Concept: {concept}
Type: {synthesis_type}
Depth: {depth}

{synthesis_text}"""

            return [TextContent(type="text", text=response)]

        except Exception as synth_err:
            logger.debug(f"Synthesis error: {synth_err}")
            return [TextContent(type="text", text=f"Error: {str(synth_err)}")]

    except Exception as e:
        logger.error(f"Error in handle_synthesize_knowledge: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_explore_concept_network(server: Any, args: dict) -> List[TextContent]:
    """Explore concept relationships interactively.

    Navigate through related concepts using ConceptNet.
    """
    try:
        start_concept = args.get("start_concept", "")
        relations_of_interest = args.get("relations_of_interest", None)  # Filter relations
        max_concepts = args.get("max_concepts", 30)

        if not start_concept:
            return [TextContent(type="text", text="Error: start_concept parameter is required")]

        # Lazy initialize ConceptNetAPI
        if not hasattr(server, '_conceptnet_api'):
            from ..external.conceptnet_api import ConceptNetAPI
            server._conceptnet_api = ConceptNetAPI()

        # Explore network
        try:
            network = server._conceptnet_api.explore_network(
                start_concept=start_concept,
                relations_of_interest=relations_of_interest,
                max_concepts=max_concepts
            )

            # Format network
            nodes = network.get("nodes", [])
            edges = network.get("edges", [])

            node_text = "\n".join(f"- {n}" for n in nodes[:15])
            if len(nodes) > 15:
                node_text += f"\n... and {len(nodes) - 15} more concepts"

            edge_summary = {}
            for edge in edges or []:
                rel_type = edge.get("relation", "unknown")
                edge_summary[rel_type] = edge_summary.get(rel_type, 0) + 1

            edge_text = "\n".join(
                f"- {rel_type}: {count} connections"
                for rel_type, count in sorted(edge_summary.items(), key=lambda x: -x[1])[:10]
            )

            response = f"""**Concept Network Exploration**
Start: {start_concept}
Total Concepts: {len(nodes)}
Total Relations: {len(edges)}

**Key Concepts**:
{node_text}

**Relations**:
{edge_text}"""

            return [TextContent(type="text", text=response)]

        except Exception as explore_err:
            logger.debug(f"Network exploration error: {explore_err}")
            return [TextContent(type="text", text=f"Error: {str(explore_err)}")]

    except Exception as e:
        logger.error(f"Error in handle_explore_concept_network: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]
