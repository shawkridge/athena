"""HTTP client for Athena API.

Provides both synchronous and asynchronous interfaces to call Athena operations
via HTTP. Includes connection pooling, retry logic, and graceful fallback.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional, Union
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)

# Retry configuration
DEFAULT_TIMEOUT = 30.0
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 1.5
CONNECT_TIMEOUT = 5.0


class AthenaHTTPClientError(Exception):
    """Base exception for Athena HTTP client."""

    pass


class AthenaHTTPClientConnectionError(AthenaHTTPClientError):
    """Connection error to Athena HTTP service."""

    pass


class AthenaHTTPClientTimeoutError(AthenaHTTPClientError):
    """Timeout error calling Athena HTTP service."""

    pass


class AthenaHTTPClientOperationError(AthenaHTTPClientError):
    """Operation failed on Athena HTTP service."""

    pass


class AthenaHTTPClient:
    """Synchronous HTTP client for Athena API.

    Provides methods for calling all Athena operations via HTTP.
    Includes automatic retry logic, connection pooling, and error handling.

    Example:
        client = AthenaHTTPClient(url="http://localhost:3000")
        result = client.recall(query="authentication patterns", k=5)
        print(result)
    """

    def __init__(
        self,
        url: str = "http://localhost:3000",
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    ):
        """Initialize HTTP client.

        Args:
            url: Base URL of Athena HTTP service
            timeout: Request timeout in seconds
            retries: Number of retries for failed requests
            backoff_factor: Exponential backoff factor for retries
        """
        self.url = url
        self.timeout = timeout
        self.retries = retries
        self.backoff_factor = backoff_factor
        self._request_id = 0
        self._session_id = None

        # Create HTTP client with connection pooling
        limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
        self._client = httpx.Client(
            base_url=self.url,
            timeout=httpx.Timeout(self.timeout, connect=CONNECT_TIMEOUT),
            limits=limits,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )

        # Initialize MCP session
        self._initialize_session()

        logger.info(f"Initialized AthenaHTTPClient: {self.url}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def close(self):
        """Close HTTP client and cleanup."""
        self._client.close()
        logger.info("Closed AthenaHTTPClient")

    def _get_next_id(self) -> int:
        """Get next request ID."""
        self._request_id += 1
        return self._request_id

    def _parse_sse_response(self, text: str) -> dict:
        """Parse Server-Sent Events response.

        Args:
            text: SSE formatted text

        Returns:
            Parsed JSON data
        """
        # SSE format: "event: message\ndata: {...}\n\n"
        lines = text.strip().split('\n')
        for line in lines:
            if line.startswith('data: '):
                return json.loads(line[6:])  # Remove "data: " prefix
        return {}

    def _initialize_session(self):
        """Initialize MCP session with the server."""
        try:
            # Send initialize request
            init_request = {
                "jsonrpc": "2.0",
                "id": self._get_next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "AthenaHTTPClient",
                        "version": "1.0.0"
                    }
                }
            }

            response = self._client.post("/", json=init_request)
            response.raise_for_status()

            # Extract session ID from headers
            self._session_id = response.headers.get('mcp-session-id')

            # Parse SSE response
            result = self._parse_sse_response(response.text)

            if "error" in result:
                logger.warning(f"MCP initialize error: {result['error']}")
            else:
                logger.debug(f"MCP session initialized: {self._session_id}")

        except Exception as e:
            logger.warning(f"Failed to initialize MCP session: {e}")

    def _map_operation_to_tool(self, operation: str) -> str:
        """Map operation name to MCP tool name.

        Args:
            operation: Operation name (e.g., 'recall', 'list_memories')

        Returns:
            MCP tool name (e.g., 'mcp__athena__memory_tools')
        """
        # Map operations to their corresponding MCP tools
        tool_map = {
            "recall": "memory_tools",
            "remember": "memory_tools",
            "forget": "memory_tools",
            "list_memories": "memory_tools",
            "optimize": "memory_tools",
            "smart_retrieve": "memory_tools",
            "get_memory_quality_summary": "memory_tools",
            "evaluate_memory_quality": "memory_tools",
            "get_learning_rates": "memory_tools",
            "get_metacognition_insights": "memory_tools",
            "check_cognitive_load": "memory_tools",
            "detect_knowledge_gaps": "memory_tools",
            "get_expertise": "memory_tools",
            "record_event": "episodic_tools",
            "recall_events": "episodic_tools",
            "get_timeline": "episodic_tools",
            "batch_record_events": "episodic_tools",
            "run_consolidation": "consolidation_tools",
            "schedule_consolidation": "consolidation_tools",
            "create_task": "task_management_tools",
            "list_tasks": "task_management_tools",
            "update_task_status": "task_management_tools",
            "start_task": "task_management_tools",
            "verify_task": "task_management_tools",
            "set_goal": "task_management_tools",
            "get_active_goals": "task_management_tools",
            "activate_goal": "task_management_tools",
            "get_goal_priority_ranking": "task_management_tools",
            "complete_goal": "task_management_tools",
            "validate_plan": "planning_tools",
            "decompose_with_strategy": "planning_tools",
            "estimate_resources": "planning_tools",
            "create_entity": "graph_tools",
            "create_relation": "graph_tools",
            "search_graph": "graph_tools",
            "get_associations": "graph_tools",
            "find_procedures": "procedural_tools",
            "get_procedure_effectiveness": "procedural_tools",
        }

        tool_suffix = tool_map.get(operation, "memory_tools")
        return tool_suffix  # Tools don't have mcp__athena__ prefix

    def _execute_operation(
        self,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "POST",
    ) -> Any:
        """Execute an operation via MCP protocol with retry logic.

        Args:
            operation: Operation name
            params: Operation parameters
            method: HTTP method (ignored, MCP always uses POST)

        Returns:
            Operation result

        Raises:
            AthenaHTTPClientError: If operation fails after retries
        """
        params = params or {}

        # Get MCP tool name
        tool_name = self._map_operation_to_tool(operation)

        # Build MCP tools/call request
        mcp_request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": {
                    "operation": operation,
                    **params
                }
            }
        }

        last_error = None
        for attempt in range(self.retries):
            try:
                # Add session ID to headers if we have one
                headers = {}
                if self._session_id:
                    headers["mcp-session-id"] = self._session_id

                # Execute MCP request
                response = self._client.post("/", json=mcp_request, headers=headers)

                # Check response
                response.raise_for_status()

                # Parse SSE response
                data = self._parse_sse_response(response.text)

                # Check for JSON-RPC error
                if "error" in data:
                    error = data["error"]
                    error_msg = error.get("message", "Unknown error")
                    raise AthenaHTTPClientOperationError(
                        f"MCP operation '{operation}' failed: {error_msg}"
                    )

                # Extract result from MCP response
                result = data.get("result", {})

                # MCP tool response is wrapped in "content" array
                if isinstance(result, dict) and "content" in result:
                    content = result["content"]
                    if content and isinstance(content, list) and len(content) > 0:
                        # Extract text from first content item
                        first_item = content[0]
                        if isinstance(first_item, dict) and "text" in first_item:
                            try:
                                # Try to parse as JSON
                                parsed = json.loads(first_item["text"])

                                # Check if it's an error response
                                if isinstance(parsed, dict) and parsed.get("status") == "error":
                                    error_msg = parsed.get("error", "Unknown error")
                                    raise AthenaHTTPClientOperationError(
                                        f"MCP operation '{operation}' failed: {error_msg}"
                                    )

                                # Extract data from envelope if present
                                if isinstance(parsed, dict) and "data" in parsed:
                                    return parsed["data"]

                                return parsed
                            except json.JSONDecodeError:
                                # Raw text might be an error message
                                text = first_item["text"]
                                if "error" in text.lower() or "validation" in text.lower():
                                    raise AthenaHTTPClientOperationError(
                                        f"MCP operation '{operation}' failed: {text[:200]}"
                                    )
                                # Return raw text if not JSON and not error
                                return text
                    return content

                logger.debug(f"MCP operation '{operation}' succeeded")
                return result

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(
                    f"Timeout executing '{operation}' (attempt {attempt + 1}/{self.retries}): {e}"
                )
            except httpx.ConnectError as e:
                last_error = e
                logger.warning(
                    f"Connection error executing '{operation}' (attempt {attempt + 1}/{self.retries}): {e}"
                )
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                last_error = e
                logger.warning(
                    f"Request error executing '{operation}' (attempt {attempt + 1}/{self.retries}): {e}"
                )

            # Retry with exponential backoff
            if attempt < self.retries - 1:
                wait_time = self.backoff_factor ** attempt
                logger.debug(f"Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)

        # All retries failed
        if isinstance(last_error, httpx.TimeoutException):
            raise AthenaHTTPClientTimeoutError(
                f"Operation '{operation}' timed out after {self.retries} retries"
            ) from last_error
        else:
            raise AthenaHTTPClientConnectionError(
                f"Failed to execute operation '{operation}' after {self.retries} retries: {last_error}"
            ) from last_error

    # Memory operations
    def recall(self, query: str, k: int = 5, memory_type: Optional[str] = None) -> Any:
        """Recall memories matching query."""
        return self._execute_operation(
            "recall",
            {"query": query, "k": k, **({"memory_type": memory_type} if memory_type else {})},
        )

    def remember(
        self,
        content: str,
        memory_type: str = "fact",
        tags: Optional[list] = None,
        importance: Optional[float] = None,
    ) -> Any:
        """Remember new knowledge."""
        params = {
            "content": content,
            "memory_type": memory_type,
            **({"tags": tags} if tags else {}),
            **({"importance": importance} if importance else {}),
        }
        return self._execute_operation("remember", params)

    def forget(self, memory_id: int) -> Any:
        """Forget a memory."""
        return self._execute_operation("forget", {"memory_id": memory_id})

    def list_memories(self) -> Any:
        """List all memories."""
        return self._execute_operation("list_memories", {})

    def optimize(self) -> Any:
        """Optimize memory storage."""
        return self._execute_operation("optimize", {})

    def smart_retrieve(self, query: str, k: int = 5) -> Any:
        """Retrieve with advanced RAG strategies."""
        return self._execute_operation("smart_retrieve", {"query": query, "k": k})

    def get_memory_quality_summary(self) -> Any:
        """Get memory system quality summary."""
        return self._execute_operation("get_memory_quality_summary", {})

    def evaluate_memory_quality(self) -> Any:
        """Evaluate overall memory quality."""
        return self._execute_operation("evaluate_memory_quality", {})

    def get_learning_rates(self) -> Any:
        """Get learning rate metrics."""
        return self._execute_operation("get_learning_rates", {})

    def get_metacognition_insights(self) -> Any:
        """Get metacognition insights."""
        return self._execute_operation("get_metacognition_insights", {})

    def check_cognitive_load(self) -> Any:
        """Check current cognitive load."""
        return self._execute_operation("check_cognitive_load", {})

    # Episodic operations
    def record_event(
        self,
        content: str,
        event_type: str,
        outcome: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Record an episodic event."""
        params = {
            "content": content,
            "event_type": event_type,
            **({"outcome": outcome} if outcome else {}),
            **({"context": context} if context else {}),
        }
        return self._execute_operation("record_event", params)

    def recall_events(self, query: str, days: int = 7, limit: int = 10) -> Any:
        """Recall episodic events."""
        return self._execute_operation("recall_events", {"query": query, "days": days, "limit": limit})

    def get_timeline(self, days: int = 7, limit: int = 10) -> Any:
        """Get timeline of events."""
        return self._execute_operation("get_timeline", {"days": days, "limit": limit})

    def batch_record_events(self, events: list) -> Any:
        """Batch record multiple events."""
        return self._execute_operation("batch_record_events", {"events": events})

    # Consolidation operations
    def run_consolidation(
        self,
        strategy: str = "balanced",
        days_back: Optional[int] = None,
        dry_run: bool = False,
    ) -> Any:
        """Run consolidation."""
        params = {
            "strategy": strategy,
            "dry_run": dry_run,
            **({"days_back": days_back} if days_back else {}),
        }
        return self._execute_operation("run_consolidation", params)

    def schedule_consolidation(self, strategy: str = "balanced") -> Any:
        """Schedule consolidation."""
        return self._execute_operation("schedule_consolidation", {"strategy": strategy})

    # Task operations
    def create_task(
        self,
        content: str,
        priority: str = "medium",
        project_id: Optional[int] = None,
    ) -> Any:
        """Create a task."""
        params = {
            "content": content,
            "priority": priority,
            **({"project_id": project_id} if project_id else {}),
        }
        return self._execute_operation("create_task", params)

    def list_tasks(self, project_id: Optional[int] = None) -> Any:
        """List tasks."""
        params = {}
        if project_id:
            params["project_id"] = project_id
        return self._execute_operation("list_tasks", params)

    def update_task_status(self, task_id: int, status: str) -> Any:
        """Update task status."""
        return self._execute_operation("update_task_status", {"task_id": task_id, "status": status})

    def start_task(self, task_id: int) -> Any:
        """Start a task."""
        return self._execute_operation("start_task", {"task_id": task_id})

    def verify_task(self, task_id: int) -> Any:
        """Verify task completion."""
        return self._execute_operation("verify_task", {"task_id": task_id})

    # Goal operations
    def set_goal(self, content: str, priority: str = "medium") -> Any:
        """Set a goal."""
        return self._execute_operation("set_goal", {"content": content, "priority": priority})

    def get_active_goals(self) -> Any:
        """Get active goals."""
        return self._execute_operation("get_active_goals", {})

    def activate_goal(self, goal_id: int) -> Any:
        """Activate a goal."""
        return self._execute_operation("activate_goal", {"goal_id": goal_id})

    def get_goal_priority_ranking(self) -> Any:
        """Get goal priority ranking."""
        return self._execute_operation("get_goal_priority_ranking", {})

    def complete_goal(self, goal_id: int, outcome: str = "success") -> Any:
        """Complete a goal."""
        return self._execute_operation("complete_goal", {"goal_id": goal_id, "outcome": outcome})

    # Planning operations
    def validate_plan(self, task_id: int) -> Any:
        """Validate a plan."""
        return self._execute_operation("validate_plan", {"task_id": task_id})

    def decompose_with_strategy(self, task_description: str, strategy: str = "hierarchical") -> Any:
        """Decompose task with strategy."""
        return self._execute_operation(
            "decompose_with_strategy",
            {"task_description": task_description, "strategy": strategy},
        )

    def estimate_resources(self, task_id: int) -> Any:
        """Estimate task resources."""
        return self._execute_operation("estimate_resources", {"task_id": task_id})

    # Graph operations
    def create_entity(self, name: str, entity_type: str) -> Any:
        """Create knowledge graph entity."""
        return self._execute_operation("create_entity", {"name": name, "entity_type": entity_type})

    def create_relation(
        self,
        from_entity: str,
        to_entity: str,
        relation_type: str,
    ) -> Any:
        """Create relation between entities."""
        return self._execute_operation(
            "create_relation",
            {"from_entity": from_entity, "to_entity": to_entity, "relation_type": relation_type},
        )

    def search_graph(self, query: str, max_results: int = 10) -> Any:
        """Search knowledge graph."""
        return self._execute_operation("search_graph", {"query": query, "max_results": max_results})

    def get_associations(self, entity_name: str) -> Any:
        """Get entity associations."""
        return self._execute_operation("get_associations", {"entity_name": entity_name})

    # Procedures
    def find_procedures(self, query: str = "", category: Optional[str] = None) -> Any:
        """Find procedures matching query."""
        params = {"query": query}
        if category:
            params["category"] = category
        return self._execute_operation("find_procedures", params)

    def get_procedure_effectiveness(self, procedure_name: str) -> Any:
        """Get procedure effectiveness metrics."""
        return self._execute_operation("get_procedure_effectiveness", {"name": procedure_name})

    # Knowledge gaps
    def detect_knowledge_gaps(self) -> Any:
        """Detect knowledge gaps and uncertainties."""
        return self._execute_operation("detect_knowledge_gaps", {})

    # Health endpoints
    def health(self) -> Dict[str, Any]:
        """Check service health."""
        try:
            response = self._client.get("/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise AthenaHTTPClientConnectionError(f"Health check failed: {e}") from e

    def info(self) -> Dict[str, Any]:
        """Get service info."""
        try:
            response = self._client.get("/info")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Info request failed: {e}")
            raise AthenaHTTPClientConnectionError(f"Info request failed: {e}") from e


class AthenaHTTPAsyncClient:
    """Asynchronous HTTP client for Athena API.

    Async version of AthenaHTTPClient for use in async contexts.
    All methods are coroutines and must be awaited.

    Example:
        async with AthenaHTTPAsyncClient(url="http://localhost:3000") as client:
            result = await client.recall(query="authentication patterns", k=5)
            print(result)
    """

    def __init__(
        self,
        url: str = "http://localhost:3000",
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    ):
        """Initialize async HTTP client.

        Args:
            url: Base URL of Athena HTTP service
            timeout: Request timeout in seconds
            retries: Number of retries for failed requests
            backoff_factor: Exponential backoff factor for retries
        """
        self.url = url
        self.timeout = timeout
        self.retries = retries
        self.backoff_factor = backoff_factor
        self._client = None

        logger.info(f"Initialized AthenaHTTPAsyncClient: {self.url}")

    async def _init_client(self):
        """Initialize client lazily."""
        if self._client is None:
            limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
            self._client = httpx.AsyncClient(
                base_url=self.url,
                timeout=httpx.Timeout(self.timeout, connect=CONNECT_TIMEOUT),
                limits=limits,
            )

    async def __aenter__(self):
        """Async context manager entry."""
        await self._init_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close async HTTP client and cleanup."""
        if self._client:
            await self._client.aclose()
            logger.info("Closed AthenaHTTPAsyncClient")

    async def _execute_operation(
        self,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "POST",
    ) -> Any:
        """Execute an operation with retry logic (async).

        Args:
            operation: Operation name
            params: Operation parameters
            method: HTTP method (POST, GET)

        Returns:
            Operation result

        Raises:
            AthenaHTTPClientError: If operation fails after retries
        """
        await self._init_client()
        params = params or {}

        last_error = None
        for attempt in range(self.retries):
            try:
                # Execute request
                if method == "GET":
                    response = await self._client.get(
                        f"/api/operation",
                        params={"operation": operation, **params},
                    )
                else:
                    response = await self._client.post(
                        "/api/operation",
                        json={"operation": operation, "params": params},
                    )

                # Check response
                response.raise_for_status()
                data = response.json()

                # Check if operation succeeded
                if not data.get("success", False):
                    error_msg = data.get("error", "Unknown error")
                    raise AthenaHTTPClientOperationError(
                        f"Operation '{operation}' failed: {error_msg}"
                    )

                logger.debug(
                    f"Operation '{operation}' succeeded in {data.get('execution_time_ms', 0):.1f}ms"
                )
                return data.get("data")

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(
                    f"Timeout executing '{operation}' (attempt {attempt + 1}/{self.retries}): {e}"
                )
            except httpx.ConnectError as e:
                last_error = e
                logger.warning(
                    f"Connection error executing '{operation}' (attempt {attempt + 1}/{self.retries}): {e}"
                )
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                last_error = e
                logger.warning(
                    f"Request error executing '{operation}' (attempt {attempt + 1}/{self.retries}): {e}"
                )

            # Retry with exponential backoff
            if attempt < self.retries - 1:
                wait_time = self.backoff_factor ** attempt
                logger.debug(f"Retrying in {wait_time:.2f}s...")
                await asyncio.sleep(wait_time)

        # All retries failed
        if isinstance(last_error, httpx.TimeoutException):
            raise AthenaHTTPClientTimeoutError(
                f"Operation '{operation}' timed out after {self.retries} retries"
            ) from last_error
        else:
            raise AthenaHTTPClientConnectionError(
                f"Failed to execute operation '{operation}' after {self.retries} retries: {last_error}"
            ) from last_error

    # Implement same operations as sync client (all async)
    async def recall(self, query: str, k: int = 5, memory_type: Optional[str] = None) -> Any:
        """Recall memories matching query."""
        return await self._execute_operation(
            "recall",
            {"query": query, "k": k, **({"memory_type": memory_type} if memory_type else {})},
        )

    async def remember(
        self,
        content: str,
        memory_type: str = "fact",
        tags: Optional[list] = None,
        importance: Optional[float] = None,
    ) -> Any:
        """Remember new knowledge."""
        params = {
            "content": content,
            "memory_type": memory_type,
            **({"tags": tags} if tags else {}),
            **({"importance": importance} if importance else {}),
        }
        return await self._execute_operation("remember", params)

    async def forget(self, memory_id: int) -> Any:
        """Forget a memory."""
        return await self._execute_operation("forget", {"memory_id": memory_id})

    async def run_consolidation(
        self,
        strategy: str = "balanced",
        days_back: Optional[int] = None,
        dry_run: bool = False,
    ) -> Any:
        """Run consolidation."""
        params = {
            "strategy": strategy,
            "dry_run": dry_run,
            **({"days_back": days_back} if days_back else {}),
        }
        return await self._execute_operation("run_consolidation", params)

    async def record_event(
        self,
        content: str,
        event_type: str,
        outcome: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Record an episodic event."""
        params = {
            "content": content,
            "event_type": event_type,
            **({"outcome": outcome} if outcome else {}),
            **({"context": context} if context else {}),
        }
        return await self._execute_operation("record_event", params)

    async def create_task(
        self,
        content: str,
        priority: str = "medium",
        project_id: Optional[int] = None,
    ) -> Any:
        """Create a task."""
        params = {
            "content": content,
            "priority": priority,
            **({"project_id": project_id} if project_id else {}),
        }
        return await self._execute_operation("create_task", params)

    async def set_goal(self, content: str, priority: str = "medium") -> Any:
        """Set a goal."""
        return await self._execute_operation("set_goal", {"content": content, "priority": priority})

    async def health(self) -> Dict[str, Any]:
        """Check service health."""
        await self._init_client()
        try:
            response = await self._client.get("/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise AthenaHTTPClientConnectionError(f"Health check failed: {e}") from e


# Convenience function to get default client
def get_client(url: Optional[str] = None) -> AthenaHTTPClient:
    """Get default HTTP client instance.

    Args:
        url: Optional custom URL, defaults to localhost:3000

    Returns:
        AthenaHTTPClient instance
    """
    return AthenaHTTPClient(url or "http://localhost:3000")


def get_async_client(url: Optional[str] = None) -> AthenaHTTPAsyncClient:
    """Get default async HTTP client instance.

    Args:
        url: Optional custom URL, defaults to localhost:3000

    Returns:
        AthenaHTTPAsyncClient instance
    """
    return AthenaHTTPAsyncClient(url or "http://localhost:3000")
