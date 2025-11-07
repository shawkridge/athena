"""Code search handlers: Semantic code search, pattern matching, code navigation.

This module contains MCP tool handlers for:
- Semantic code search with Tree-Sitter integration
- Pattern-based code search
- Code element extraction and analysis
- Dependency analysis

Uses the TreeSitterCodeSearch system for comprehensive code understanding.
"""

import json
import logging
from typing import Any, List, Optional, Dict
from pathlib import Path

from mcp.types import TextContent

logger = logging.getLogger(__name__)


# ============================================================================
# CODE SEARCH INITIALIZATION
# ============================================================================

def _get_or_init_tree_sitter_search(server: Any, repo_path: str):
    """Initialize TreeSitterCodeSearch for a repository."""
    try:
        from athena.code_search.tree_sitter_search import TreeSitterCodeSearch

        # Use repo_path as key for caching
        cache_key = f"_tree_sitter_search_{repo_path}"

        if not hasattr(server, cache_key):
            search_engine = TreeSitterCodeSearch(repo_path)
            setattr(server, cache_key, search_engine)

        return getattr(server, cache_key)
    except Exception as e:
        logger.error(f"Failed to initialize TreeSitterCodeSearch: {e}")
        raise


# ============================================================================
# CODE SEARCH MODULE HANDLERS
# ============================================================================

async def handle_search_code_semantically(server: Any, args: dict) -> List[TextContent]:
    """Perform semantic code search across repository.

    Uses embedding-based similarity with multi-factor scoring.

    Args:
        query: Search query string
        repo_path: Path to repository (required)
        limit: Maximum results (default: 10)
        min_score: Minimum relevance score (default: 0.3)
    """
    try:
        query = args.get("query", "")
        repo_path = args.get("repo_path", "")
        limit = args.get("limit", 10)
        min_score = args.get("min_score", 0.3)

        if not query:
            return [TextContent(type="text", text="Error: query parameter is required")]
        if not repo_path:
            return [TextContent(type="text", text="Error: repo_path parameter is required")]

        # Initialize search engine and build index
        search_engine = _get_or_init_tree_sitter_search(server, repo_path)

        if not search_engine.is_indexed:
            stats = search_engine.build_index()
            logger.info(f"Indexed repository: {stats}")

        # Perform semantic search
        try:
            results = search_engine.search(query, top_k=limit, min_score=min_score)

            # Format results
            formatted_results = []
            for i, result in enumerate(results or [], 1):
                unit = result.unit
                formatted_results.append(
                    f"**#{i} {unit.name}** (`{unit.type}`)\n"
                    f"File: `{unit.file_path}:{unit.start_line}-{unit.end_line}`\n"
                    f"Relevance: {result.relevance:.2%}\n"
                    f"Signature: `{unit.signature[:60]}...`"
                )

            if not formatted_results:
                result_text = "No matching code elements found for the query."
            else:
                result_text = "\n\n".join(formatted_results)

            response = f"""**Semantic Code Search Results**
Query: {query}
Repository: {repo_path}
Limit: {limit}
Min Score: {min_score}
Results Found: {len(results) if results else 0}

{result_text}"""

            return [TextContent(type="text", text=response)]

        except Exception as search_err:
            logger.debug(f"Code search error: {search_err}")
            return [TextContent(type="text", text=f"Search Error: {str(search_err)}")]

    except Exception as e:
        logger.error(f"Error in handle_search_code_semantically: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_search_code_by_type(server: Any, args: dict) -> List[TextContent]:
    """Search code by element type (function, class, import).

    Args:
        unit_type: Type to search for (function, class, import)
        repo_path: Path to repository (required)
        query: Optional text query for filtering
        limit: Maximum results (default: 10)
    """
    try:
        unit_type = args.get("unit_type", "")
        repo_path = args.get("repo_path", "")
        query = args.get("query")
        limit = args.get("limit", 10)

        if not unit_type:
            return [TextContent(type="text", text="Error: unit_type parameter is required")]
        if not repo_path:
            return [TextContent(type="text", text="Error: repo_path parameter is required")]

        # Initialize search engine
        search_engine = _get_or_init_tree_sitter_search(server, repo_path)

        if not search_engine.is_indexed:
            search_engine.build_index()

        # Search by type
        try:
            results = search_engine.search_by_type(unit_type, query, limit)

            # Format results
            formatted_results = []
            for i, result in enumerate(results or [], 1):
                unit = result.unit
                formatted_results.append(
                    f"**#{i} {unit.name}** ({unit.type})\n"
                    f"File: `{unit.file_path}:{unit.start_line}`\n"
                    f"Relevance: {result.relevance:.2%}"
                )

            if not formatted_results:
                result_text = f"No {unit_type} elements found."
            else:
                result_text = "\n\n".join(formatted_results)

            response = f"""**Code Search by Type**
Type: {unit_type}
Query: {query or 'None'}
Repository: {repo_path}
Results: {len(results) if results else 0}

{result_text}"""

            return [TextContent(type="text", text=response)]

        except Exception as search_err:
            logger.debug(f"Type search error: {search_err}")
            return [TextContent(type="text", text=f"Search Error: {str(search_err)}")]

    except Exception as e:
        logger.error(f"Error in handle_search_code_by_type: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_search_code_by_name(server: Any, args: dict) -> List[TextContent]:
    """Search code by name (exact or partial match).

    Args:
        name: Name to search for
        repo_path: Path to repository (required)
        exact: Exact match only (default: False)
        limit: Maximum results (default: 10)
    """
    try:
        name = args.get("name", "")
        repo_path = args.get("repo_path", "")
        exact = args.get("exact", False)
        limit = args.get("limit", 10)

        if not name:
            return [TextContent(type="text", text="Error: name parameter is required")]
        if not repo_path:
            return [TextContent(type="text", text="Error: repo_path parameter is required")]

        # Initialize search engine
        search_engine = _get_or_init_tree_sitter_search(server, repo_path)

        if not search_engine.is_indexed:
            search_engine.build_index()

        # Search by name
        try:
            results = search_engine.search_by_name(name, limit, exact)

            # Format results
            formatted_results = []
            for i, result in enumerate(results or [], 1):
                unit = result.unit
                formatted_results.append(
                    f"**#{i} {unit.name}** ({unit.type})\n"
                    f"File: `{unit.file_path}:{unit.start_line}`\n"
                    f"Match Score: {result.relevance:.2%}"
                )

            if not formatted_results:
                result_text = f"No elements with name '{name}' found."
            else:
                result_text = "\n\n".join(formatted_results)

            response = f"""**Code Search by Name**
Name: {name}
Exact Match: {exact}
Repository: {repo_path}
Results: {len(results) if results else 0}

{result_text}"""

            return [TextContent(type="text", text=response)]

        except Exception as search_err:
            logger.debug(f"Name search error: {search_err}")
            return [TextContent(type="text", text=f"Search Error: {str(search_err)}")]

    except Exception as e:
        logger.error(f"Error in handle_search_code_by_name: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_analyze_code_file(server: Any, args: dict) -> List[TextContent]:
    """Analyze structure of a code file.

    Args:
        file_path: Path to code file
        repo_path: Path to repository (for context)
    """
    try:
        file_path = args.get("file_path", "")
        repo_path = args.get("repo_path", "")

        if not file_path:
            return [TextContent(type="text", text="Error: file_path parameter is required")]
        if not repo_path:
            repo_path = str(Path(file_path).parent)

        # Initialize search engine
        search_engine = _get_or_init_tree_sitter_search(server, repo_path)

        # Analyze file
        try:
            analysis = search_engine.analyze_file(file_path)

            # Format analysis
            response_parts = [
                f"**File Analysis**",
                f"File: `{analysis['file']}`",
                f"Total Units: {analysis['total_units']}",
            ]

            if analysis.get("functions"):
                response_parts.append(
                    f"\n**Functions** ({len(analysis['functions'])}):"
                )
                for func in analysis["functions"][:10]:
                    response_parts.append(
                        f"- `{func['name']}` ({func['type']}) "
                        f"lines {func['start_line']}-{func['end_line']}"
                    )

            if analysis.get("classes"):
                response_parts.append(
                    f"\n**Classes** ({len(analysis['classes'])}):"
                )
                for cls in analysis["classes"][:10]:
                    response_parts.append(
                        f"- `{cls['name']}` ({cls['type']}) "
                        f"lines {cls['start_line']}-{cls['end_line']}"
                    )

            if analysis.get("imports"):
                response_parts.append(
                    f"\n**Imports** ({len(analysis['imports'])}):"
                )
                for imp in analysis["imports"][:10]:
                    response_parts.append(f"- {imp['name']}")

            response = "\n".join(response_parts)
            return [TextContent(type="text", text=response)]

        except Exception as analysis_err:
            logger.debug(f"File analysis error: {analysis_err}")
            return [TextContent(type="text", text=f"Analysis Error: {str(analysis_err)}")]

    except Exception as e:
        logger.error(f"Error in handle_analyze_code_file: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_find_code_dependencies(server: Any, args: dict) -> List[TextContent]:
    """Find dependencies of a code entity.

    Args:
        file_path: Path to code file
        entity_name: Name of function/class to analyze
        repo_path: Path to repository (optional)
    """
    try:
        file_path = args.get("file_path", "")
        entity_name = args.get("entity_name", "")
        repo_path = args.get("repo_path", "")

        if not file_path:
            return [TextContent(type="text", text="Error: file_path parameter is required")]
        if not entity_name:
            return [TextContent(type="text", text="Error: entity_name parameter is required")]
        if not repo_path:
            repo_path = str(Path(file_path).parent)

        # Initialize search engine
        search_engine = _get_or_init_tree_sitter_search(server, repo_path)

        if not search_engine.is_indexed:
            search_engine.build_index()

        # Find dependencies
        try:
            deps = search_engine.find_dependencies(file_path, entity_name)

            if not deps.get("found"):
                return [TextContent(
                    type="text",
                    text=f"Entity '{entity_name}' not found in {file_path}"
                )]

            # Format dependencies
            response_parts = [
                f"**Dependency Analysis**",
                f"Entity: `{deps['entity']}`",
                f"File: `{deps['file']}`",
            ]

            if deps.get("direct_dependencies"):
                response_parts.append(
                    f"\n**Direct Dependencies** ({len(deps['direct_dependencies'])}):"
                )
                for dep in deps["direct_dependencies"][:10]:
                    response_parts.append(f"- `{dep}`")

            if deps.get("transitive_dependencies"):
                response_parts.append(
                    f"\n**Transitive Dependencies** ({len(deps['transitive_dependencies'])}):"
                )
                for dep in sorted(deps["transitive_dependencies"])[:10]:
                    response_parts.append(f"- `{dep}`")

            if deps.get("dependents"):
                response_parts.append(
                    f"\n**Dependents** ({len(deps['dependents'])}):"
                )
                for dep in sorted(deps["dependents"])[:10]:
                    response_parts.append(f"- `{dep}`")

            response = "\n".join(response_parts)
            return [TextContent(type="text", text=response)]

        except Exception as deps_err:
            logger.debug(f"Dependency finding error: {deps_err}")
            return [TextContent(type="text", text=f"Analysis Error: {str(deps_err)}")]

    except Exception as e:
        logger.error(f"Error in handle_find_code_dependencies: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_index_code_repository(server: Any, args: dict) -> List[TextContent]:
    """Index a code repository for semantic search.

    Builds semantic index using TreeSitterCodeSearch.

    Args:
        repo_path: Path to repository
        rebuild: Force rebuild even if already indexed (default: False)
    """
    try:
        repo_path = args.get("repo_path", "")
        rebuild = args.get("rebuild", False)

        if not repo_path:
            return [TextContent(type="text", text="Error: repo_path parameter is required")]

        # Initialize and build index
        try:
            search_engine = _get_or_init_tree_sitter_search(server, repo_path)

            if search_engine.is_indexed and not rebuild:
                stats = search_engine.index_stats
                response = f"""**Repository Already Indexed**
Repository: {repo_path}
Status: Ready

Indexed Statistics:
- Total Units: {stats.get('units_extracted', 0)}
- Files Indexed: {stats.get('files_indexed', 0)}
- Files Skipped: {stats.get('files_skipped', 0)}
- Indexing Time: {stats.get('indexing_time', 0):.2f}s
- Errors: {stats.get('errors', 0)}"""
            else:
                stats = search_engine.build_index()
                response = f"""**Repository Indexing Complete**
Repository: {repo_path}
Status: Success

Indexed Statistics:
- Total Units: {stats.get('units_extracted', 0)}
- Files Indexed: {stats.get('files_indexed', 0)}
- Files Skipped: {stats.get('files_skipped', 0)}
- Indexing Time: {stats.get('indexing_time', 0):.2f}s
- Errors: {stats.get('errors', 0)}"""

            return [TextContent(type="text", text=response)]

        except Exception as index_err:
            logger.debug(f"Indexing error: {index_err}")
            return [TextContent(type="text", text=f"Indexing Error: {str(index_err)}")]

    except Exception as e:
        logger.error(f"Error in handle_index_code_repository: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_get_code_statistics(server: Any, args: dict) -> List[TextContent]:
    """Get comprehensive statistics about indexed code.

    Args:
        repo_path: Path to repository
    """
    try:
        repo_path = args.get("repo_path", "")

        if not repo_path:
            return [TextContent(type="text", text="Error: repo_path parameter is required")]

        # Initialize search engine
        search_engine = _get_or_init_tree_sitter_search(server, repo_path)

        if not search_engine.is_indexed:
            return [TextContent(
                type="text",
                text="Repository not indexed. Call index_code_repository first."
            )]

        # Get statistics
        try:
            stats = search_engine.get_code_statistics()

            # Format statistics
            response_parts = [
                f"**Code Statistics**",
                f"Repository: {repo_path}",
                f"\nTotal Units: {stats.get('total_units', 0)}",
            ]

            if stats.get("units_by_type"):
                response_parts.append("\n**Units by Type**:")
                for unit_type, count in sorted(stats["units_by_type"].items()):
                    response_parts.append(f"- {unit_type}: {count}")

            response_parts.append(
                f"\n**Embedding Coverage**: {stats.get('embedding_coverage', 0):.1%}"
            )

            response = "\n".join(response_parts)
            return [TextContent(type="text", text=response)]

        except Exception as stats_err:
            logger.debug(f"Statistics error: {stats_err}")
            return [TextContent(type="text", text=f"Stats Error: {str(stats_err)}")]

    except Exception as e:
        logger.error(f"Error in handle_get_code_statistics: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]
