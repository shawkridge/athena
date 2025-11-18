"""Athena Client Library for Code Execution Pattern.

Provides a simple client for agents running in code execution environments
to discover and call Athena tools. This implements the pattern described in:
https://www.anthropic.com/engineering/code-execution-with-mcp

Usage:
    from athena import AthenaClient

    client = AthenaClient("http://localhost:3000")

    # Discover tools
    tools = client.discover_tools()

    # Call a tool
    results = client.recall(query="consolidation patterns", k=10)

    # Process locally, don't send back to model
    summary = f"Found {len(results)} patterns"
    print(summary)  # Only summary goes back to model
"""

import json
import logging
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    raise ImportError("requests is required. Install with: pip install requests")

logger = logging.getLogger(__name__)


class AthenaClient:
    """HTTP client for Athena Memory System.

    Designed for code execution environments where agents need to:
    1. Discover tools lazily (don't load all definitions upfront)
    2. Call tools and process results locally
    3. Return only summaries to the model (98% token savings)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:3000",
        timeout: int = 30,
        verify_ssl: bool = True,
    ):
        """Initialize Athena client.

        Args:
            base_url: Base URL of Athena HTTP server
            timeout: Request timeout in seconds
            verify_ssl: Verify SSL certificates (False for local dev)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.session = requests.Session()

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Make HTTP request to Athena server.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON body

        Returns:
            Response data

        Raises:
            requests.RequestException: On network errors
            ValueError: On server errors
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            response.raise_for_status()

            return response.json()
        except requests.RequestException as e:
            logger.error(f"Request failed for {endpoint}: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from {endpoint}: {e}")
            raise ValueError(f"Invalid response from server: {e}")

    # ============================================================================
    # Tools Discovery (Lazy Loading)
    # ============================================================================

    def discover_tools(self) -> Dict[str, Any]:
        """Discover all available tools organized by category.

        Returns tools without loading full definitions - just names and
        descriptions. Use get_tool() to load full definition only when needed.

        Returns:
            Dict with categories and tool summaries

        Example:
            tools = client.discover_tools()
            for category, info in tools['categories'].items():
                print(f"{category}: {info['count']} tools")
        """
        return self._request("GET", "/tools/discover")

    def list_tools(self, category: Optional[str] = None) -> Dict[str, Any]:
        """List all tools, optionally filtered by category.

        Args:
            category: Optional category filter (e.g., "memory", "episodic")

        Returns:
            List of tool names and basic info
        """
        params = {"category": category} if category else None
        return self._request("GET", "/tools/list", params=params)

    def get_tool(self, tool_name: str) -> Dict[str, Any]:
        """Get detailed definition of a specific tool.

        Returns full schema including parameters, return type, and examples.
        Load this only when you actually need to call the tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool definition with schema

        Example:
            tool_def = client.get_tool("recall")
            print(tool_def['parameters'])
        """
        return self._request("GET", f"/tools/{tool_name}")

    # ============================================================================
    # Memory Operations
    # ============================================================================

    def recall(
        self,
        query: str,
        k: int = 5,
        memory_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search memories matching a query.

        Performs semantic + BM25 hybrid search across all memory types.
        Results stay local - process them before returning to model.

        Args:
            query: Search query
            k: Number of results (default: 5)
            memory_type: Filter by type ("fact", "pattern", "decision", "context")

        Returns:
            List of matching memories with scores

        Example:
            results = client.recall("consolidation patterns", k=10)
            relevant = [r for r in results if r['score'] > 0.7]
            summary = f"Found {len(relevant)} high-confidence results"
        """
        params = {"query": query, "k": k}
        if memory_type:
            params["memory_type"] = memory_type

        response = self._request("POST", "/api/memory/recall", params=params)
        return response.get("data", [])

    def remember(
        self,
        content: str,
        memory_type: str = "fact",
        tags: Optional[List[str]] = None,
        importance: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Store new knowledge in memory.

        Args:
            content: Memory content
            memory_type: Type of memory (default: "fact")
            tags: Optional tags for categorization
            importance: Importance score (0.0-1.0)

        Returns:
            Created memory with ID and metadata

        Example:
            memory = client.remember(
                "Consolidation improves query speed by 30%",
                memory_type="pattern",
                tags=["performance", "consolidation"]
            )
        """
        json_data = {
            "content": content,
            "memory_type": memory_type,
        }
        if tags:
            json_data["tags"] = tags
        if importance is not None:
            json_data["importance"] = importance

        response = self._request("POST", "/api/memory/remember", json_data=json_data)
        return response.get("data", {})

    def forget(self, memory_id: int) -> bool:
        """Delete a memory.

        Args:
            memory_id: ID of memory to delete

        Returns:
            Success status
        """
        response = self._request("POST", "/api/memory/forget", params={"memory_id": memory_id})
        return response.get("success", False)

    # ============================================================================
    # Episodic Events
    # ============================================================================

    def record_event(
        self,
        event_type: str,
        content: str,
        outcome: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Record an episodic event (action, decision, error, etc.).

        Args:
            event_type: Type of event (e.g., "action", "decision", "error")
            content: Event description
            outcome: Event outcome ("success", "failure", "partial", "ongoing")
            duration_ms: Duration in milliseconds

        Returns:
            Recorded event with ID and timestamp
        """
        json_data = {
            "event_type": event_type,
            "content": content,
        }
        if outcome:
            json_data["outcome"] = outcome
        if duration_ms is not None:
            json_data["duration_ms"] = duration_ms

        response = self._request("POST", "/api/episodic/record", json_data=json_data)
        return response.get("data", {})

    def recall_events(
        self,
        session_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Retrieve episodic events from a session or time range.

        Args:
            session_id: Optional session ID to filter
            limit: Maximum number of events

        Returns:
            List of episodic events
        """
        params = {"limit": limit}
        if session_id:
            params["session_id"] = session_id

        response = self._request("POST", "/api/episodic/recall", params=params)
        return response.get("data", [])

    # ============================================================================
    # Knowledge Graph
    # ============================================================================

    def create_entity(
        self,
        name: str,
        entity_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create an entity in the knowledge graph.

        Args:
            name: Entity name
            entity_type: Type of entity (Project, Task, File, etc.)
            metadata: Optional additional metadata

        Returns:
            Created entity with ID
        """
        json_data = {
            "name": name,
            "entity_type": entity_type,
        }
        if metadata:
            json_data["metadata"] = metadata

        response = self._request("POST", "/api/graph/entity", json_data=json_data)
        return response.get("data", {})

    def search_graph(
        self,
        query: str,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search knowledge graph for entities and relationships.

        Args:
            query: Search query
            max_results: Maximum results

        Returns:
            Matching entities and relationships
        """
        params = {"query": query, "max_results": max_results}
        response = self._request("GET", "/api/graph/search", params=params)
        return response.get("data", [])

    # ============================================================================
    # Consolidation
    # ============================================================================

    def consolidate(
        self,
        strategy: str = "balanced",
        days_back: Optional[int] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Run consolidation to extract patterns from episodic events.

        Large result processing example:
            # Run consolidation (returns 1000+ patterns)
            result = client.consolidate()

            # Process locally - filter/summarize before returning to model
            patterns = result['patterns']
            high_confidence = [p for p in patterns if p['confidence'] > 0.8]

            # Return only summary (100 bytes instead of 50KB)
            return f"Found {len(high_confidence)} high-confidence patterns"

        Args:
            strategy: Consolidation strategy (balanced/speed/quality/minimal)
            days_back: Days of events to consolidate
            dry_run: Simulate without saving results

        Returns:
            Consolidation results with extracted patterns
        """
        json_data = {"strategy": strategy, "dry_run": dry_run}
        if days_back:
            json_data["days_back"] = days_back

        response = self._request("POST", "/api/consolidation/run", json_data=json_data)
        return response.get("data", {})

    # ============================================================================
    # Generic Tool Execution
    # ============================================================================

    def call_tool(
        self,
        tool_name: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Call any tool by name with parameters.

        This is the generic interface for calling tools discovered from
        the registry. Use specific methods (recall, remember, etc.) for
        better type hints.

        Args:
            tool_name: Name of the tool to call
            **kwargs: Tool parameters

        Returns:
            Tool execution result

        Example:
            result = client.call_tool("recall", query="patterns", k=5)
            result = client.call_tool("consolidate", strategy="quality")
        """
        response = self._request("POST", f"/tools/{tool_name}/execute", json_data=kwargs)
        return response.get("data", {})

    # ============================================================================
    # Health & Info
    # ============================================================================

    def health(self) -> Dict[str, Any]:
        """Check Athena server health.

        Returns:
            Health status with uptime and database size
        """
        return self._request("GET", "/health")

    def info(self) -> Dict[str, Any]:
        """Get API information.

        Returns:
            API version, description, and supported operations
        """
        return self._request("GET", "/info")

    def close(self):
        """Close HTTP session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
