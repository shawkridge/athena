"""Semantic code navigation system.

This module provides intuitive navigation through code using semantic relationships,
enabling users to explore code structure, find related code, and understand dependencies.
"""

import logging
from typing import List, Dict, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class NavigationDirection(Enum):
    """Direction of navigation in code graph."""
    INCOMING = "incoming"       # Who depends on this
    OUTGOING = "outgoing"       # What this depends on
    RELATED = "related"         # Semantically related
    CONTEXT = "context"         # Surrounding code (same file, class)


@dataclass
class NavigationNode:
    """Represents a node in code navigation."""
    name: str
    entity_type: str
    file_path: str
    line_number: int
    relevance_score: float = 1.0  # 0-1, relevance to navigation query
    distance: int = 0            # Steps from starting point
    path: List[str] = field(default_factory=list)  # Navigation breadcrumb
    context: Dict[str, Any] = field(default_factory=dict)
    is_entry_point: bool = False


@dataclass
class NavigationBreadcrumb:
    """Represents navigation path/breadcrumb."""
    start: str
    current: str
    path: List[str]
    depth: int = field(default=0)
    visited: Set[str] = field(default_factory=set)

    def __post_init__(self):
        """Auto-calculate depth from path length if not explicitly set."""
        if self.depth == 0 and len(self.path) > 1:
            object.__setattr__(self, "depth", len(self.path) - 1)

    def to_display_string(self) -> str:
        """Convert to human-readable breadcrumb."""
        return " > ".join(self.path)


class CodeNavigator:
    """Navigates through code using semantic relationships."""

    def __init__(self, symbol_index, graph_builder, dependency_graph, rag_retriever=None):
        """Initialize navigator."""
        self.symbol_index = symbol_index
        self.graph_builder = graph_builder
        self.dependency_graph = dependency_graph
        self.rag_retriever = rag_retriever
        self.navigation_history: List[NavigationBreadcrumb] = []
        self.current_location: Optional[str] = None

    def navigate_to(self, entity_name: str) -> NavigationNode:
        """Navigate to specific entity."""
        entity = self.graph_builder.get_entity(entity_name)
        if not entity:
            symbol = self.symbol_index.find_by_name(entity_name)
            if not symbol:
                return None

            entity_data = symbol[0] if symbol else None
            node = NavigationNode(
                name=entity_name,
                entity_type=entity_data.type.value if entity_data else "unknown",
                file_path=entity_data.file_path if entity_data else "",
                line_number=entity_data.line_number if entity_data else 0,
                is_entry_point=True,
            )
        else:
            node = NavigationNode(
                name=entity.name,
                entity_type=entity.entity_type.value,
                file_path=entity.file_path,
                line_number=entity.line_number,
                is_entry_point=True,
            )

        self.current_location = entity_name
        self._add_to_history(entity_name, [entity_name])
        return node

    def explore_incoming(self, entity_name: str, max_depth: int = 2) -> List[NavigationNode]:
        """Explore entities that depend on this entity."""
        return self._explore_direction(
            entity_name, NavigationDirection.INCOMING, max_depth
        )

    def explore_outgoing(self, entity_name: str, max_depth: int = 2) -> List[NavigationNode]:
        """Explore entities that this depends on."""
        return self._explore_direction(
            entity_name, NavigationDirection.OUTGOING, max_depth
        )

    def explore_related(self, entity_name: str, max_results: int = 10) -> List[NavigationNode]:
        """Find semantically related entities."""
        results = []

        if self.rag_retriever:
            # Use RAG to find similar code
            rag_results = self.rag_retriever.search_related_entities(
                entity_name, top_k=max_results
            )

            for i, rag_result in enumerate(rag_results):
                node = NavigationNode(
                    name=rag_result.entity_name,
                    entity_type=rag_result.entity_type,
                    file_path=rag_result.file_path,
                    line_number=rag_result.line_number,
                    relevance_score=rag_result.combined_score,
                    distance=1,
                    path=[entity_name, rag_result.entity_name],
                )
                results.append(node)
        else:
            # Fall back to graph relationships
            related = self.graph_builder.get_related_entities(entity_name)
            for related_name in related[:max_results]:
                entity = self.graph_builder.get_entity(related_name)
                if entity:
                    node = NavigationNode(
                        name=related_name,
                        entity_type=entity.entity_type.value,
                        file_path=entity.file_path,
                        line_number=entity.line_number,
                        distance=1,
                        path=[entity_name, related_name],
                    )
                    results.append(node)

        return results

    def explore_context(self, entity_name: str) -> List[NavigationNode]:
        """Explore context (same file/class)."""
        entity = self.graph_builder.get_entity(entity_name)
        if not entity:
            return []

        results = []
        file_entities = self.graph_builder.get_entities_by_file(entity.file_path)

        for file_entity in file_entities:
            if file_entity.name != entity_name:
                node = NavigationNode(
                    name=file_entity.name,
                    entity_type=file_entity.entity_type.value,
                    file_path=file_entity.file_path,
                    line_number=file_entity.line_number,
                    distance=1,
                    path=[entity_name, file_entity.name],
                    context={"same_file": True},
                )
                results.append(node)

        return results

    def get_breadcrumb(self) -> Optional[NavigationBreadcrumb]:
        """Get current navigation breadcrumb."""
        if self.navigation_history:
            return self.navigation_history[-1]
        return None

    def get_navigation_history(self) -> List[NavigationBreadcrumb]:
        """Get full navigation history."""
        return self.navigation_history.copy()

    def go_back(self) -> Optional[NavigationNode]:
        """Navigate back in history."""
        if len(self.navigation_history) > 1:
            self.navigation_history.pop()
            breadcrumb = self.navigation_history[-1]
            self.current_location = breadcrumb.current

            entity = self.graph_builder.get_entity(breadcrumb.current)
            if entity:
                return NavigationNode(
                    name=entity.name,
                    entity_type=entity.entity_type.value,
                    file_path=entity.file_path,
                    line_number=entity.line_number,
                    path=breadcrumb.path,
                )

        return None

    def find_path(self, source: str, target: str) -> Optional[List[str]]:
        """Find path between two entities."""
        # Try dependency graph first
        if hasattr(self.dependency_graph, 'find_import_chain'):
            path = self.dependency_graph.find_import_chain(source, target)
            if path:
                return path

        # Use BFS through graph
        visited = set()
        queue = deque([(source, [source])])

        while queue:
            current, path = queue.popleft()
            if current == target:
                self._add_to_history(target, path)
                return path

            if current in visited:
                continue
            visited.add(current)

            related = self.graph_builder.get_related_entities(current)
            for neighbor in related:
                if neighbor not in visited:
                    queue.append((neighbor, path + [neighbor]))

        return None

    def get_navigation_map(self, entity_name: str, depth: int = 2) -> Dict[str, Any]:
        """Get complete navigation map around entity."""
        incoming = self.explore_incoming(entity_name, max_depth=depth)
        outgoing = self.explore_outgoing(entity_name, max_depth=depth)
        related = self.explore_related(entity_name)
        context = self.explore_context(entity_name)

        return {
            "entity": entity_name,
            "incoming": [
                {
                    "name": n.name,
                    "type": n.entity_type,
                    "distance": n.distance,
                    "score": n.relevance_score,
                }
                for n in incoming
            ],
            "outgoing": [
                {
                    "name": n.name,
                    "type": n.entity_type,
                    "distance": n.distance,
                    "score": n.relevance_score,
                }
                for n in outgoing
            ],
            "related": [
                {
                    "name": n.name,
                    "type": n.entity_type,
                    "score": n.relevance_score,
                }
                for n in related
            ],
            "context": [
                {
                    "name": n.name,
                    "type": n.entity_type,
                    "line": n.line_number,
                }
                for n in context
            ],
        }

    def _explore_direction(
        self,
        entity_name: str,
        direction: NavigationDirection,
        max_depth: int,
    ) -> List[NavigationNode]:
        """Explore in specific direction up to max_depth."""
        results = []
        visited = set()
        queue = deque([(entity_name, 0, [entity_name])])

        while queue:
            current, depth, path = queue.popleft()

            if depth > max_depth or current in visited:
                continue

            visited.add(current)

            # Get neighbors based on direction (use get_related_entities from graph_builder)
            if direction == NavigationDirection.INCOMING:
                neighbors = self.graph_builder.get_related_entities(current)
            elif direction == NavigationDirection.OUTGOING:
                neighbors = self.graph_builder.get_related_entities(current)
            else:
                neighbors = []

            for neighbor in neighbors:
                if neighbor not in visited and neighbor != entity_name:
                    entity = self.graph_builder.get_entity(neighbor)
                    if entity:
                        node = NavigationNode(
                            name=neighbor,
                            entity_type=entity.entity_type.value,
                            file_path=entity.file_path,
                            line_number=entity.line_number,
                            distance=depth + 1,
                            path=path + [neighbor],
                        )
                        results.append(node)

                        if depth + 1 < max_depth:
                            queue.append((neighbor, depth + 1, path + [neighbor]))

        return results

    def _add_to_history(self, entity_name: str, path: List[str]):
        """Add navigation to history."""
        breadcrumb = NavigationBreadcrumb(
            start=path[0],
            current=entity_name,
            path=path,
            depth=len(path) - 1,
        )
        self.navigation_history.append(breadcrumb)

        # Limit history to last 50 items
        if len(self.navigation_history) > 50:
            self.navigation_history = self.navigation_history[-50:]


class NavigationGuide:
    """Provides guided navigation through code."""

    def __init__(self, navigator: CodeNavigator):
        """Initialize guide."""
        self.navigator = navigator

    def explore_module(self, file_path: str) -> Dict[str, Any]:
        """Guide through module exploration."""
        entities = self.navigator.graph_builder.get_entities_by_file(file_path)

        structure = {
            "file_path": file_path,
            "entities": [],
            "entry_points": [],
        }

        for entity in entities:
            # Count incoming relationships (who depends on this entity)
            incoming_rels = self.navigator.graph_builder.get_relationships_to(entity.name)
            incoming = len(incoming_rels)

            entity_info = {
                "name": entity.name,
                "type": entity.entity_type.value,
                "line": entity.line_number,
                "incoming_deps": incoming,
            }

            structure["entities"].append(entity_info)

            # Entry points are public with low incoming deps
            if not entity.name.startswith("_") and incoming == 0:
                structure["entry_points"].append(entity_info)

        return structure

    def trace_dependency_chain(self, source: str, target: str) -> Dict[str, Any]:
        """Trace and explain dependency path."""
        path = self.navigator.find_path(source, target)

        if not path:
            return {"found": False, "source": source, "target": target}

        chain_details = []
        for i, entity in enumerate(path):
            node = self.navigator.navigate_to(entity)
            chain_details.append({
                "step": i,
                "entity": entity,
                "type": node.entity_type if node else "unknown",
                "file": node.file_path if node else "",
            })

        return {
            "found": True,
            "source": source,
            "target": target,
            "distance": len(path) - 1,
            "path": path,
            "chain_details": chain_details,
        }

    def recommend_navigation(self, entity_name: str) -> Dict[str, Any]:
        """Recommend next navigation steps."""
        incoming = self.navigator.explore_incoming(entity_name, max_depth=1)
        outgoing = self.navigator.explore_outgoing(entity_name, max_depth=1)
        related = self.navigator.explore_related(entity_name, max_results=5)

        recommendations = {
            "entity": entity_name,
            "suggestions": {
                "explore_dependents": [
                    {"name": n.name, "type": n.entity_type}
                    for n in incoming[:3]
                ],
                "explore_dependencies": [
                    {"name": n.name, "type": n.entity_type}
                    for n in outgoing[:3]
                ],
                "explore_related": [
                    {"name": n.name, "type": n.entity_type, "score": n.relevance_score}
                    for n in related[:3]
                ],
            },
        }

        return recommendations
