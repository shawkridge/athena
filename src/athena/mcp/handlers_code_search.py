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
from .structured_result import StructuredResult, PaginationMetadata

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
        limit = min(args.get("limit", 10), 100)
        min_score = args.get("min_score", 0.3)

        if not query:
            result = StructuredResult.error("query parameter is required", metadata={"operation": "search_code_semantically"})
            return [result.as_optimized_content(schema_name="code_analysis")]
        if not repo_path:
            result = StructuredResult.error("repo_path parameter is required", metadata={"operation": "search_code_semantically"})
            return [result.as_optimized_content(schema_name="code_analysis")]

        # Initialize search engine and build index
        search_engine = _get_or_init_tree_sitter_search(server, repo_path)

        if not search_engine.is_indexed:
            stats = search_engine.build_index()
            logger.info(f"Indexed repository: {stats}")

        # Perform semantic search
        try:
            results = search_engine.search(query, top_k=limit, min_score=min_score)

            # Format results for structured response
            formatted_results = []
            for i, search_result in enumerate(results or [], 1):
                unit = search_result.unit
                formatted_results.append({
                    "rank": i,
                    "name": unit.name,
                    "type": unit.type,
                    "file": unit.file_path,
                    "lines": f"{unit.start_line}-{unit.end_line}",
                    "relevance": round(search_result.relevance * 100, 1),
                    "signature": unit.signature[:60] if hasattr(unit, 'signature') else "N/A"
                })

            result = StructuredResult.success(
                data=formatted_results,
                metadata={
                    "operation": "search_code_semantically",
                    "schema": "code_analysis",
                    "query": query,
                    "repo_path": repo_path,
                    "min_score": min_score,
                },
                pagination=PaginationMetadata(
                    returned=len(formatted_results),
                    limit=limit,
                )
            )

        except Exception as search_err:
            logger.debug(f"Code search error: {search_err}")
            result = StructuredResult.error(f"Search Error: {str(search_err)}", metadata={"operation": "search_code_semantically"})

    except Exception as e:
        logger.error(f"Error in handle_search_code_semantically: {e}", exc_info=True)
        result = StructuredResult.error(str(e), metadata={"operation": "search_code_semantically"})

    return [result.as_optimized_content(schema_name="code_analysis")]


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
        limit = min(args.get("limit", 10), 100)

        if not unit_type:
            result = StructuredResult.error("unit_type parameter is required", metadata={"operation": "search_code_by_type"})
            return [result.as_optimized_content(schema_name="code_analysis")]
        if not repo_path:
            result = StructuredResult.error("repo_path parameter is required", metadata={"operation": "search_code_by_type"})
            return [result.as_optimized_content(schema_name="code_analysis")]

        # Initialize search engine
        search_engine = _get_or_init_tree_sitter_search(server, repo_path)

        if not search_engine.is_indexed:
            search_engine.build_index()

        # Search by type
        try:
            results = search_engine.search_by_type(unit_type, query, limit)

            # Format results for structured response
            formatted_results = []
            for i, search_result in enumerate(results or [], 1):
                unit = search_result.unit
                formatted_results.append({
                    "rank": i,
                    "name": unit.name,
                    "type": unit.type,
                    "file": unit.file_path,
                    "line": unit.start_line,
                    "relevance": round(search_result.relevance * 100, 1)
                })

            result = StructuredResult.success(
                data=formatted_results,
                metadata={
                    "operation": "search_code_by_type",
                    "schema": "code_analysis",
                    "unit_type": unit_type,
                    "query_filter": query,
                    "repo_path": repo_path,
                },
                pagination=PaginationMetadata(
                    returned=len(formatted_results),
                    limit=limit,
                )
            )

        except Exception as search_err:
            logger.debug(f"Type search error: {search_err}")
            result = StructuredResult.error(f"Search Error: {str(search_err)}", metadata={"operation": "search_code_by_type"})

    except Exception as e:
        logger.error(f"Error in handle_search_code_by_type: {e}", exc_info=True)
        result = StructuredResult.error(str(e), metadata={"operation": "search_code_by_type"})

    return [result.as_optimized_content(schema_name="code_analysis")]


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
        limit = min(args.get("limit", 10), 100)

        if not name:
            result = StructuredResult.error("name parameter is required", metadata={"operation": "search_code_by_name"})
            return [result.as_optimized_content(schema_name="code_analysis")]
        if not repo_path:
            result = StructuredResult.error("repo_path parameter is required", metadata={"operation": "search_code_by_name"})
            return [result.as_optimized_content(schema_name="code_analysis")]

        # Initialize search engine
        search_engine = _get_or_init_tree_sitter_search(server, repo_path)

        if not search_engine.is_indexed:
            search_engine.build_index()

        # Search by name
        try:
            results = search_engine.search_by_name(name, limit, exact)

            # Format results for structured response
            formatted_results = []
            for i, search_result in enumerate(results or [], 1):
                unit = search_result.unit
                formatted_results.append({
                    "rank": i,
                    "name": unit.name,
                    "type": unit.type,
                    "file": unit.file_path,
                    "line": unit.start_line,
                    "match_score": round(search_result.relevance * 100, 1)
                })

            result = StructuredResult.success(
                data=formatted_results,
                metadata={
                    "operation": "search_code_by_name",
                    "schema": "code_analysis",
                    "name": name,
                    "exact_match": exact,
                    "repo_path": repo_path,
                },
                pagination=PaginationMetadata(
                    returned=len(formatted_results),
                    limit=limit,
                )
            )

        except Exception as search_err:
            logger.debug(f"Name search error: {search_err}")
            result = StructuredResult.error(f"Search Error: {str(search_err)}", metadata={"operation": "search_code_by_name"})

    except Exception as e:
        logger.error(f"Error in handle_search_code_by_name: {e}", exc_info=True)
        result = StructuredResult.error(str(e), metadata={"operation": "search_code_by_name"})

    return [result.as_optimized_content(schema_name="code_analysis")]


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
        limit = min(args.get("limit", 10), 100)

        if not file_path:
            result = StructuredResult.error("file_path parameter is required", metadata={"operation": "find_code_dependencies"})
            return [result.as_optimized_content(schema_name="code_analysis")]
        if not entity_name:
            result = StructuredResult.error("entity_name parameter is required", metadata={"operation": "find_code_dependencies"})
            return [result.as_optimized_content(schema_name="code_analysis")]
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
                result = StructuredResult.success(
                    data=[],
                    metadata={
                        "operation": "find_code_dependencies",
                        "schema": "code_analysis",
                        "entity": entity_name,
                        "file": file_path,
                        "found": False,
                    }
                )
            else:
                # Format dependencies for structured response
                direct_deps = deps.get("direct_dependencies", [])[:limit]
                transitive_deps = deps.get("transitive_dependencies", [])[:limit]
                dependents = deps.get("dependents", [])[:limit]

                formatted_data = {
                    "entity": deps['entity'],
                    "file": deps['file'],
                    "direct_dependencies": direct_deps,
                    "transitive_dependencies": sorted(transitive_deps)[:limit],
                    "dependents": sorted(dependents)[:limit],
                }

                result = StructuredResult.success(
                    data=formatted_data,
                    metadata={
                        "operation": "find_code_dependencies",
                        "schema": "code_analysis",
                        "entity": entity_name,
                        "file": file_path,
                        "direct_count": len(direct_deps),
                        "transitive_count": len(transitive_deps),
                        "dependents_count": len(dependents),
                    },
                    pagination=PaginationMetadata(
                        returned=len(direct_deps) + len(transitive_deps) + len(dependents),
                        limit=limit,
                    )
                )

        except Exception as deps_err:
            logger.debug(f"Dependency finding error: {deps_err}")
            result = StructuredResult.error(f"Analysis Error: {str(deps_err)}", metadata={"operation": "find_code_dependencies"})

    except Exception as e:
        logger.error(f"Error in handle_find_code_dependencies: {e}", exc_info=True)
        result = StructuredResult.error(str(e), metadata={"operation": "find_code_dependencies"})

    return [result.as_optimized_content(schema_name="code_analysis")]


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
