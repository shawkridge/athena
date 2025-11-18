"""ConceptNet API wrapper for external knowledge integration.

ConceptNet is a free and open knowledge base containing 21M+ relations
between concepts in many languages. This module provides:
- Structured access to ConceptNet REST API
- Caching for repeated queries
- Relation type support (IsA, UsedFor, AtLocation, CapableOf, Causes, etc.)
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class ConceptNetRelation:
    """Represents a single relation in ConceptNet."""

    # Standard relation types
    IS_A = "IsA"
    PART_OF = "PartOf"
    USED_FOR = "UsedFor"
    AT_LOCATION = "AtLocation"
    CAPABLE_OF = "CapableOf"
    CAUSES = "Causes"
    CAUSED_BY = "CausedBy"
    HAS_PROPERTY = "HasProperty"
    MOTIVATED_BY_GOAL = "MotivatedByGoal"
    PRECEDED_BY = "PrecededBy"
    SIMILAR_TO = "SimilarTo"
    SYNONYM = "Synonym"
    ANTONYM = "Antonym"
    DERIVED_FROM = "DerivedFrom"
    VARIANT_OF = "VariantOf"

    ALL_TYPES = [
        IS_A,
        PART_OF,
        USED_FOR,
        AT_LOCATION,
        CAPABLE_OF,
        CAUSES,
        CAUSED_BY,
        HAS_PROPERTY,
        MOTIVATED_BY_GOAL,
        PRECEDED_BY,
        SIMILAR_TO,
        SYNONYM,
        ANTONYM,
        DERIVED_FROM,
        VARIANT_OF,
    ]


class ConceptNetAPI:
    """Client for ConceptNet API with caching support."""

    BASE_URL = "http://api.conceptnet.io"
    DEFAULT_LIMIT = 50
    CACHE_TTL = timedelta(days=30)

    def __init__(self, cache_store: Optional[Dict[str, Any]] = None):
        """Initialize ConceptNet API client.

        Args:
            cache_store: Optional dictionary-like cache (if None, uses in-memory dict)
        """
        self.cache = cache_store if cache_store is not None else {}
        self.client = httpx.AsyncClient(timeout=30.0)

    async def lookup(
        self,
        concept: str,
        relation_types: Optional[List[str]] = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Look up a concept in ConceptNet.

        Args:
            concept: The concept to look up (e.g., "memory", "neural network")
            relation_types: Filter by relation types (if None, all types returned)
            limit: Maximum number of relations to return
            offset: Pagination offset

        Returns:
            Dictionary with concept information and related concepts
        """
        cache_key = f"conceptnet:{concept}:{relation_types}:{limit}:{offset}"

        # Check cache
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if isinstance(cached, dict) and cached.get("cached_at"):
                age = datetime.now() - datetime.fromisoformat(cached["cached_at"])
                if age < self.CACHE_TTL:
                    logger.debug(f"Cache hit for concept: {concept}")
                    return cached

        try:
            # Query ConceptNet API
            url = f"{self.BASE_URL}/query"
            params = {
                "node": f"/c/en/{concept.lower()}",
                "limit": limit,
                "offset": offset,
            }

            if relation_types:
                params["rel"] = ",".join(relation_types)

            response = await self.client.get(url, params=params)
            response.raise_for_status()

            result = response.json()

            # Parse relations
            parsed = {
                "concept": concept,
                "relations": [],
                "cached_at": datetime.now().isoformat(),
            }

            for edge in result.get("edges", []):
                relation = {
                    "type": edge.get("rel", {}).get("label", "Unknown"),
                    "start": edge.get("start", {}).get("label", ""),
                    "end": edge.get("end", {}).get("label", ""),
                    "weight": edge.get("weight", 1.0),
                    "source": edge.get("sources", []),
                }
                parsed["relations"].append(relation)

            # Cache result
            self.cache[cache_key] = parsed
            logger.debug(f"Cached {len(parsed['relations'])} relations for: {concept}")

            return parsed

        except Exception as e:
            logger.error(f"Error looking up concept '{concept}': {e}")
            return {
                "concept": concept,
                "relations": [],
                "error": str(e),
            }

    async def expand(
        self,
        concept: str,
        hops: int = 2,
        relation_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Expand a concept by retrieving multi-hop related concepts.

        Args:
            concept: The concept to expand
            hops: Number of hops in the expansion graph (default 2)
            relation_types: Filter by relation types

        Returns:
            Dictionary with expanded concept graph
        """
        visited = set()
        graph = {"root": concept, "nodes": {}, "edges": []}

        async def expand_recursive(node: str, depth: int) -> None:
            """Recursively expand concept."""
            if depth > hops or node in visited:
                return

            visited.add(node)

            # Look up node
            result = await self.lookup(node, relation_types=relation_types, limit=10)

            # Add to graph
            graph["nodes"][node] = {
                "depth": hops - depth,
                "relations_count": len(result.get("relations", [])),
            }

            # Add edges and recurse
            for relation in result.get("relations", [])[:5]:  # Limit to 5 per node
                target = relation["end"]
                weight = relation["weight"]

                graph["edges"].append(
                    {
                        "source": node,
                        "target": target,
                        "type": relation["type"],
                        "weight": weight,
                    }
                )

                # Recursive expansion
                await expand_recursive(target, depth + 1)

        # Start expansion
        await expand_recursive(concept, 0)

        return graph

    async def get_relation_types(self) -> List[str]:
        """Get list of available relation types in ConceptNet.

        Returns:
            List of relation type strings
        """
        return ConceptNetRelation.ALL_TYPES

    async def search_relations(
        self,
        pattern: str,
        relation_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search for relations matching a pattern.

        Args:
            pattern: Pattern to search for
            relation_type: Filter by relation type
            limit: Maximum results

        Returns:
            List of matching relations
        """
        try:
            url = f"{self.BASE_URL}/search"
            params = {
                "text": pattern,
                "limit": limit,
            }

            if relation_type:
                params["rel"] = relation_type

            response = await self.client.get(url, params=params)
            response.raise_for_status()

            results = response.json().get("results", [])
            return results[:limit]

        except Exception as e:
            logger.error(f"Error searching for relations: {e}")
            return []

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


# Synchronous wrapper for compatibility
class ConceptNetAPISync(ConceptNetAPI):
    """Synchronous wrapper around ConceptNetAPI using httpx."""

    def __init__(self, cache_store: Optional[Dict[str, Any]] = None):
        """Initialize synchronous ConceptNet API client."""
        self.cache = cache_store if cache_store is not None else {}
        self.client = httpx.Client(timeout=30.0)

    def lookup(
        self,
        concept: str,
        relation_types: Optional[List[str]] = None,
        limit: int = ConceptNetAPI.DEFAULT_LIMIT,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Synchronous lookup wrapper."""
        cache_key = f"conceptnet:{concept}:{relation_types}:{limit}:{offset}"

        # Check cache
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if isinstance(cached, dict) and cached.get("cached_at"):
                age = datetime.now() - datetime.fromisoformat(cached["cached_at"])
                if age < self.CACHE_TTL:
                    logger.debug(f"Cache hit for concept: {concept}")
                    return cached

        try:
            # Query ConceptNet API
            url = f"{self.BASE_URL}/query"
            params = {
                "node": f"/c/en/{concept.lower()}",
                "limit": limit,
                "offset": offset,
            }

            if relation_types:
                params["rel"] = ",".join(relation_types)

            response = self.client.get(url, params=params)
            response.raise_for_status()

            result = response.json()

            # Parse relations
            parsed = {
                "concept": concept,
                "relations": [],
                "cached_at": datetime.now().isoformat(),
            }

            for edge in result.get("edges", []):
                relation = {
                    "type": edge.get("rel", {}).get("label", "Unknown"),
                    "start": edge.get("start", {}).get("label", ""),
                    "end": edge.get("end", {}).get("label", ""),
                    "weight": edge.get("weight", 1.0),
                    "source": edge.get("sources", []),
                }
                parsed["relations"].append(relation)

            # Cache result
            self.cache[cache_key] = parsed
            logger.debug(f"Cached {len(parsed['relations'])} relations for: {concept}")

            return parsed

        except Exception as e:
            logger.error(f"Error looking up concept '{concept}': {e}")
            return {
                "concept": concept,
                "relations": [],
                "error": str(e),
            }

    def expand(
        self,
        concept: str,
        hops: int = 2,
        relation_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Synchronous expand wrapper - simplified version."""
        result = self.lookup(concept, relation_types=relation_types, limit=20)

        graph = {
            "root": concept,
            "nodes": {concept: {"depth": 0, "relations_count": len(result["relations"])}},
            "edges": [],
        }

        for relation in result.get("relations", [])[:10]:
            target = relation["end"]
            graph["edges"].append(
                {
                    "source": concept,
                    "target": target,
                    "type": relation["type"],
                    "weight": relation["weight"],
                }
            )

        return graph

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
