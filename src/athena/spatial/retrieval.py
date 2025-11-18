"""Two-stage spatial-semantic retrieval for episodic events.

Inspired by EM-LLM (arXiv:43943928) spatial-temporal grounding approach.
"""

from datetime import datetime
from typing import List

from ..episodic.models import EpisodicEvent
from ..episodic.store import EpisodicStore
from .hierarchy import calculate_spatial_distance
from .models import SpatialQuery, SpatialQueryResult
from .store import SpatialStore


def query_episodic_spatial(
    query: SpatialQuery, episodic_store: EpisodicStore, spatial_store: SpatialStore, project_id: int
) -> List[SpatialQueryResult]:
    """
    Two-stage spatial-semantic retrieval.

    Stage 1: Coarse - Filter events by spatial neighborhood
    Stage 2: Fine - Semantic search within spatial subset

    Args:
        query: Spatial query with text and optional spatial context
        episodic_store: Episodic memory store
        spatial_store: Spatial hierarchy store
        project_id: Project ID to search within

    Returns:
        Ranked list of spatial query results
    """
    # Stage 1: Spatial Filtering
    if query.spatial_context:
        # Get events in spatial neighborhood
        neighbor_paths = spatial_store.get_neighbors(
            project_id=project_id,
            center_path=query.spatial_context,
            max_depth=query.max_spatial_depth,
        )

        # Include the center path itself
        relevant_paths = [query.spatial_context] + neighbor_paths

        # Get all events from these spatial locations
        candidate_events = _get_events_by_paths(
            episodic_store=episodic_store, project_id=project_id, paths=relevant_paths
        )

    else:
        # No spatial context - search all events
        # (Fall back to pure semantic search)
        from datetime import timedelta

        candidate_events = episodic_store.get_events_by_date(
            project_id=project_id,
            start_date=datetime.now() - timedelta(days=365),
            end_date=datetime.now(),
        )

    if not candidate_events:
        return []

    # Stage 2: Semantic Search within spatial subset
    results = _semantic_search_events(
        query_text=query.query_text,
        events=candidate_events,
        spatial_context=query.spatial_context,
        k=query.semantic_k,
        episodic_store=episodic_store,
    )

    return results


def _get_events_by_paths(
    episodic_store: EpisodicStore, project_id: int, paths: List[str]
) -> List[EpisodicEvent]:
    """
    Get all events that occurred in the given spatial paths.

    Args:
        episodic_store: Episodic store
        project_id: Project ID
        paths: List of file paths

    Returns:
        List of events
    """
    events = []

    # Query events by path
    # Note: This requires querying by context.cwd
    cursor = episodic_store.db.conn.cursor()

    # Build query with path list
    placeholders = ",".join("?" * len(paths))
    cursor.execute(
        f"""
        SELECT * FROM episodic_events
        WHERE project_id = ? AND context_cwd IN ({placeholders})
        ORDER BY timestamp DESC
        LIMIT 1000
    """,
        [project_id] + paths,
    )

    for row in cursor.fetchall():
        event = episodic_store._row_to_event(row)
        events.append(event)

    return events


def _semantic_search_events(
    query_text: str,
    events: List[EpisodicEvent],
    spatial_context: str,
    k: int,
    episodic_store: EpisodicStore = None,
) -> List[SpatialQueryResult]:
    """
    Perform semantic search within event candidates using embeddings.

    Args:
        query_text: Query string
        events: Candidate events (spatially filtered)
        spatial_context: Center path for spatial distance calculation
        k: Number of results to return
        episodic_store: EpisodicStore instance for embedding retrieval

    Returns:
        Ranked list of results
    """
    from ..core.embeddings import EmbeddingModel, cosine_similarity

    results = []

    # Generate query embedding
    try:
        embedding_model = EmbeddingModel()
        query_embedding = embedding_model.embed(query_text)
        use_embeddings = True
    except Exception as e:
        import logging

        logging.warning(
            f"Failed to generate query embedding, falling back to keyword matching: {e}"
        )
        use_embeddings = False
        query_lower = query_text.lower()

    for event in events:
        # Calculate semantic score
        if use_embeddings and episodic_store:
            # Use embedding-based similarity
            event_embedding = episodic_store.get_event_embedding(event.id)

            if event_embedding:
                semantic_score = cosine_similarity(query_embedding, event_embedding)
                # Normalize from [-1, 1] to [0, 1]
                semantic_score = (semantic_score + 1.0) / 2.0
            else:
                # Fallback to keyword matching if no embedding
                semantic_score = _calculate_keyword_similarity(query_lower, event.content.lower())
        else:
            # Keyword matching fallback
            semantic_score = _calculate_keyword_similarity(
                query_text.lower(), event.content.lower()
            )

        # Calculate spatial distance
        event_path = event.context.cwd if event.context and event.context.cwd else ""
        spatial_distance = 0

        if spatial_context and event_path:
            spatial_distance = calculate_spatial_distance(spatial_context, event_path)

        # Combined score: semantic (70%) + spatial proximity (30%)
        spatial_score = max(0.0, 1.0 - (spatial_distance / 10.0))  # Decay with distance
        combined_score = 0.7 * semantic_score + 0.3 * spatial_score

        result = SpatialQueryResult(
            event_id=event.id,
            content=event.content,
            spatial_path=event_path,
            spatial_distance=spatial_distance,
            semantic_score=semantic_score,
            timestamp=event.timestamp,
            combined_score=combined_score,
        )

        results.append(result)

    # Sort by combined score and return top k
    results.sort(reverse=True)  # Uses __lt__ from SpatialQueryResult
    return results[:k]


def _calculate_keyword_similarity(query: str, text: str) -> float:
    """
    Keyword-based similarity using Jaccard index (fallback).

    Args:
        query: Query text (lowercase)
        text: Event content (lowercase)

    Returns:
        Similarity score [0.0, 1.0]
    """
    # Tokenize
    query_words = set(query.split())
    text_words = set(text.split())

    if not query_words or not text_words:
        return 0.0

    # Jaccard similarity
    intersection = query_words & text_words
    union = query_words | text_words

    return len(intersection) / len(union) if union else 0.0


# ========================================================================
# Symbol-Aware Retrieval
# ========================================================================


def query_symbols_by_file(
    spatial_store: SpatialStore, project_id: int, file_path: str
) -> List[dict]:
    """Query all symbols defined in a specific file.

    Args:
        spatial_store: Spatial store instance
        project_id: Project ID
        file_path: File path to query

    Returns:
        List of symbol nodes (as dicts)
    """
    return spatial_store.list_symbols_by_file(project_id, file_path)


def query_symbols_by_kind(
    spatial_store: SpatialStore, project_id: int, symbol_kind: str
) -> List[dict]:
    """Query all symbols of a specific kind (function, class, method).

    Args:
        spatial_store: Spatial store instance
        project_id: Project ID
        symbol_kind: Type of symbol (function, class, method, etc)

    Returns:
        List of symbol nodes (as dicts)
    """
    return spatial_store.list_symbols_by_kind(project_id, symbol_kind)


def query_symbols_by_language(
    spatial_store: SpatialStore, project_id: int, language: str
) -> List[dict]:
    """Query all symbols in a specific programming language.

    Args:
        spatial_store: Spatial store instance
        project_id: Project ID
        language: Language (python, typescript, go, etc)

    Returns:
        List of symbol nodes (as dicts)
    """
    return spatial_store.list_symbols_by_language(project_id, language)


def find_symbol_definition(
    spatial_store: SpatialStore, project_id: int, symbol_name: str, file_path: str = None
) -> dict:
    """Find the definition of a symbol by name.

    Args:
        spatial_store: Spatial store instance
        project_id: Project ID
        symbol_name: Symbol name to find
        file_path: Optional file path to narrow search

    Returns:
        Symbol node dict or None if not found
    """
    return spatial_store.get_symbol_by_name(project_id, symbol_name, file_path)


def find_symbol_usage(spatial_store: SpatialStore, project_id: int, symbol_id: int) -> dict:
    """Find usage information for a symbol (what calls it, what it calls).

    Args:
        spatial_store: Spatial store instance
        project_id: Project ID
        symbol_id: Symbol ID

    Returns:
        Dict with 'calls' and 'callers' lists
    """
    calls = spatial_store.find_symbol_calls(project_id, symbol_id)
    callers = spatial_store.find_symbol_callers(project_id, symbol_id)

    return {
        "symbol_id": symbol_id,
        "calls": calls,
        "called_by": callers,
    }


def find_complexity_hotspots(
    spatial_store: SpatialStore, project_id: int, threshold: float = 10.0, limit: int = 20
) -> List[dict]:
    """Find symbols with high cyclomatic complexity (potential refactoring targets).

    Args:
        spatial_store: Spatial store instance
        project_id: Project ID
        threshold: Complexity score threshold
        limit: Maximum results

    Returns:
        List of high-complexity symbols
    """
    return spatial_store.find_complexity_hotspots(project_id, threshold, limit)


def query_symbols_contextual(
    query_text: str,
    spatial_store: SpatialStore,
    project_id: int,
    symbol_kind_filter: str = None,
    language_filter: str = None,
) -> List[dict]:
    """Context-aware symbol search with optional filters.

    Useful for: "find all Python methods that handle authentication"

    Args:
        query_text: Search query (e.g., "authenticate", "validate")
        spatial_store: Spatial store instance
        project_id: Project ID
        symbol_kind_filter: Optional filter (function, class, method)
        language_filter: Optional language filter (python, typescript)

    Returns:
        Filtered list of matching symbols
    """
    # Get all symbols matching filters
    if language_filter:
        all_symbols = spatial_store.list_symbols_by_language(project_id, language_filter)
    elif symbol_kind_filter:
        all_symbols = spatial_store.list_symbols_by_kind(project_id, symbol_kind_filter)
    else:
        # Get all symbols
        all_symbols = []
        cursor = spatial_store.execute(
            "SELECT * FROM symbol_nodes WHERE project_id = ? ORDER BY file_path, line_number",
            (project_id,),
            fetch_all=True,
        )
        all_symbols = [dict(row) for row in (cursor or [])]

    # Filter by query text (keyword match in name or signature)
    query_lower = query_text.lower()
    results = []

    for symbol in all_symbols:
        name_match = query_lower in symbol["name"].lower()
        signature_match = symbol.get("signature") and query_lower in symbol["signature"].lower()
        docstring_match = symbol.get("docstring") and query_lower in symbol["docstring"].lower()

        if name_match or signature_match or docstring_match:
            results.append(symbol)

    return results
