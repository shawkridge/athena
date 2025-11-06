"""Code search handlers: Semantic code search, pattern matching, code navigation.

This module contains MCP tool handlers for:
- Semantic code search with hybrid ranking
- Pattern-based code search
- Code context and navigation
- Code element extraction and indexing

Organized by domain for clarity and maintainability.
"""

import json
import logging
from typing import Any, List, Optional

from mcp.types import TextContent

logger = logging.getLogger(__name__)


# ============================================================================
# CODE SEARCH MODULE HANDLERS
# ============================================================================

async def handle_search_code_semantically(server: Any, args: dict) -> List[TextContent]:
    """Perform semantic code search across repository.

    Uses hybrid ranking: 40% semantic + 30% AST + 30% spatial.
    """
    try:
        query = args.get("query", "")
        limit = args.get("limit", 5)
        language = args.get("language")  # Optional: filter by language
        element_type = args.get("element_type")  # Optional: function, class, etc.

        if not query:
            return [TextContent(type="text", text="Error: query parameter is required")]

        # Lazy initialize CodeSearchManager
        if not hasattr(server, '_code_search_manager'):
            from ..code.search import CodeSearchManager
            server._code_search_manager = CodeSearchManager(server.store.db)

        # Perform semantic search
        try:
            results = server._code_search_manager.semantic_search(
                query=query,
                limit=limit,
                language=language,
                element_type=element_type
            )

            # Format results
            formatted_results = []
            for i, result in enumerate(results or [], 1):
                formatted_results.append(
                    f"**#{i} {result.element.name}** ({result.element.element_type})\n"
                    f"File: `{result.element.file_path}:{result.element.start_line}`\n"
                    f"Scores: Semantic={result.semantic_score:.2f}, "
                    f"AST={result.ast_score:.2f}, Spatial={result.spatial_score:.2f}\n"
                    f"Combined: {result.combined_score:.2f}"
                )

            if not formatted_results:
                result_text = "No matching code elements found for the query."
            else:
                result_text = "\n\n".join(formatted_results)

            response = f"""**Semantic Code Search**
Query: {query}
Language: {language or 'any'}
Element Type: {element_type or 'any'}
Results: {len(results) if results else 0}

{result_text}"""

            return [TextContent(type="text", text=response)]

        except Exception as search_err:
            logger.debug(f"Code search error: {search_err}")
            return [TextContent(type="text", text=f"Error: {str(search_err)}")]

    except Exception as e:
        logger.error(f"Error in handle_search_code_semantically: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_search_code_by_pattern(server: Any, args: dict) -> List[TextContent]:
    """Search code by AST pattern or regex.

    Finds code matching structural patterns (e.g., function definitions, imports).
    """
    try:
        pattern = args.get("pattern", "")
        pattern_type = args.get("pattern_type", "ast")  # ast or regex
        limit = args.get("limit", 5)
        language = args.get("language")

        if not pattern:
            return [TextContent(type="text", text="Error: pattern parameter is required")]

        # Lazy initialize CodeSearchManager
        if not hasattr(server, '_code_search_manager'):
            from ..code.search import CodeSearchManager
            server._code_search_manager = CodeSearchManager(server.store.db)

        # Perform pattern search
        try:
            if pattern_type == "regex":
                results = server._code_search_manager.regex_search(
                    pattern=pattern,
                    limit=limit,
                    language=language
                )
            else:  # AST pattern
                results = server._code_search_manager.pattern_search(
                    pattern=pattern,
                    limit=limit,
                    language=language
                )

            # Format results
            formatted_results = []
            for i, result in enumerate(results or [], 1):
                formatted_results.append(
                    f"**#{i} {result.element.name}** ({result.element.element_type})\n"
                    f"File: `{result.element.file_path}:{result.element.start_line}`"
                )

            if not formatted_results:
                result_text = "No code elements matched the pattern."
            else:
                result_text = "\n\n".join(formatted_results)

            response = f"""**Pattern-Based Code Search**
Pattern: {pattern}
Type: {pattern_type}
Language: {language or 'any'}
Results: {len(results) if results else 0}

{result_text}"""

            return [TextContent(type="text", text=response)]

        except Exception as search_err:
            logger.debug(f"Pattern search error: {search_err}")
            return [TextContent(type="text", text=f"Error: {str(search_err)}")]

    except Exception as e:
        logger.error(f"Error in handle_search_code_by_pattern: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_get_code_context(server: Any, args: dict) -> List[TextContent]:
    """Get context for a code element (definitions, usage, dependencies).

    Returns related code elements and their relationships.
    """
    try:
        element_id = args.get("element_id", "")
        context_type = args.get("context_type", "full")  # definitions, usages, dependencies, full
        radius = args.get("radius", 3)  # How many hops in the dependency graph

        if not element_id:
            return [TextContent(type="text", text="Error: element_id parameter is required")]

        # Lazy initialize CodeSearchManager
        if not hasattr(server, '_code_search_manager'):
            from ..code.search import CodeSearchManager
            server._code_search_manager = CodeSearchManager(server.store.db)

        # Get context
        try:
            context = server._code_search_manager.get_context(
                element_id=element_id,
                context_type=context_type,
                radius=radius
            )

            # Format context
            context_parts = []

            if context.get("element"):
                elem = context["element"]
                context_parts.append(
                    f"**Element**: {elem.name}\n"
                    f"**File**: `{elem.file_path}:{elem.start_line}`\n"
                    f"**Type**: {elem.element_type}"
                )

            if context.get("definitions"):
                defs = context["definitions"]
                context_parts.append(
                    f"**Definitions** ({len(defs)}):\n" +
                    "\n".join(f"- {d.name} ({d.element_type})" for d in defs[:5])
                )

            if context.get("usages"):
                usages = context["usages"]
                context_parts.append(
                    f"**Usages** ({len(usages)}):\n" +
                    "\n".join(f"- {u.name} in {u.file_path}" for u in usages[:5])
                )

            if context.get("dependencies"):
                deps = context["dependencies"]
                context_parts.append(
                    f"**Dependencies** ({len(deps)}):\n" +
                    "\n".join(f"- {d.name}" for d in deps[:5])
                )

            response = f"""**Code Context**
Element ID: {element_id}
Type: {context_type}

{chr(10).join(context_parts)}"""

            return [TextContent(type="text", text=response)]

        except Exception as context_err:
            logger.debug(f"Context retrieval error: {context_err}")
            return [TextContent(type="text", text=f"Error: {str(context_err)}")]

    except Exception as e:
        logger.error(f"Error in handle_get_code_context: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_index_code_repository(server: Any, args: dict) -> List[TextContent]:
    """Index a code repository for search.

    Parses all source files and builds search indices.
    """
    try:
        repo_path = args.get("repo_path", "")
        languages = args.get("languages", None)  # Optional: filter by language
        update_existing = args.get("update_existing", False)

        if not repo_path:
            return [TextContent(type="text", text="Error: repo_path parameter is required")]

        # Lazy initialize CodeIndexer
        if not hasattr(server, '_code_indexer'):
            from ..code.indexer import CodeIndexer
            server._code_indexer = CodeIndexer(server.store.db)

        # Index repository
        try:
            stats = server._code_indexer.index_repository(
                repo_path=repo_path,
                languages=languages,
                update_existing=update_existing
            )

            response = f"""**Repository Indexing Complete**
Repository: {repo_path}
Status: Success

Indexed Elements:
- Functions: {stats.get('functions', 0)}
- Classes: {stats.get('classes', 0)}
- Modules: {stats.get('modules', 0)}
- Imports: {stats.get('imports', 0)}
- Total: {stats.get('total', 0)}

Languages: {', '.join(stats.get('languages', []))}"""

            return [TextContent(type="text", text=response)]

        except Exception as index_err:
            logger.debug(f"Indexing error: {index_err}")
            return [TextContent(type="text", text=f"Error: {str(index_err)}")]

    except Exception as e:
        logger.error(f"Error in handle_index_code_repository: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]
