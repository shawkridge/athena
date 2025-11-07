"""Knowledge graph integration for code analysis.

This module bridges code symbols, chunks, and embeddings with the knowledge graph
layer for semantic relationship discovery and traversal.
"""

import logging
from typing import List, Dict, Optional, Set, Any
from dataclasses import dataclass
from enum import Enum

from src.athena.code_search.symbol_extractor import Symbol, SymbolType, SymbolIndex
from src.athena.code_search.code_chunker import Chunk, CodeChunker

logger = logging.getLogger(__name__)


class CodeEntityType(Enum):
    """Types of code entities in the knowledge graph."""
    FUNCTION = "Function"
    CLASS = "Component"
    MODULE = "Module"
    PACKAGE = "Package"
    VARIABLE = "Variable"
    CONSTANT = "Constant"
    IMPORT = "Import"
    INTERFACE = "Interface"
    ENUM = "Enum"
    TYPE = "Type"


class CodeRelationType(Enum):
    """Types of relationships between code entities."""
    CALLS = "calls"
    CALLS_FROM = "called_by"
    IMPORTS = "imports"
    IMPORTED_BY = "imported_by"
    INHERITS = "inherits"
    INHERITED_BY = "inherited_by"
    CONTAINS = "contains"
    CONTAINED_BY = "contained_in"
    USES = "uses"
    USED_BY = "used_by"
    DEFINES = "defines"
    DEFINED_IN = "defined_in"
    DEPENDS_ON = "depends_on"
    DEPENDED_ON_BY = "depended_on_by"
    IMPLEMENTS = "implements"
    IMPLEMENTED_BY = "implemented_by"


@dataclass
class CodeEntity:
    """Represents a code entity in the knowledge graph."""
    name: str
    entity_type: CodeEntityType
    file_path: str
    line_number: int
    namespace: Optional[str] = None
    docstring: Optional[str] = None
    complexity: int = 1
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize metadata."""
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "entity_type": self.entity_type.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "namespace": self.namespace,
            "docstring": self.docstring,
            "complexity": self.complexity,
            "metadata": self.metadata,
        }


@dataclass
class CodeRelationship:
    """Represents a relationship between code entities."""
    source: str  # Source entity name
    target: str  # Target entity name
    relation_type: CodeRelationType
    strength: float = 1.0  # 0-1, how direct/strong the relationship
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize metadata."""
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "target": self.target,
            "relation_type": self.relation_type.value,
            "strength": self.strength,
            "metadata": self.metadata,
        }


class CodeGraphBuilder:
    """Builds knowledge graph representation of code structure."""

    def __init__(self):
        """Initialize graph builder."""
        self.entities: Dict[str, CodeEntity] = {}
        self.relationships: List[CodeRelationship] = []
        self._entity_index: Dict[str, Set[str]] = {}  # Map file_path -> entity names

    def add_symbol(self, symbol: Symbol) -> CodeEntity:
        """Convert symbol to graph entity and add."""
        entity_type = self._symbol_type_to_entity_type(symbol.type)

        entity = CodeEntity(
            name=symbol.name,
            entity_type=entity_type,
            file_path=symbol.file_path,
            line_number=symbol.line_number,
            docstring=symbol.docstring,
            complexity=symbol.complexity,
            metadata={
                "signature": symbol.signature,
                "dependencies": symbol.dependencies,
                "symbol_metadata": symbol.metadata,
            },
        )

        self.entities[symbol.name] = entity

        # Index by file
        if symbol.file_path not in self._entity_index:
            self._entity_index[symbol.file_path] = set()
        self._entity_index[symbol.file_path].add(symbol.name)

        return entity

    def add_chunk(self, chunk: Chunk, chunk_id: str) -> CodeEntity:
        """Convert chunk to graph entity and add."""
        entity = CodeEntity(
            name=chunk_id,
            entity_type=CodeEntityType.MODULE,
            file_path=chunk.file_path,
            line_number=chunk.start_line,
            namespace=chunk.symbol_name or "module",
            metadata={
                "content_hash": hash(chunk.content),
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "symbol_type": chunk.symbol_type,
                "chunk_metadata": chunk.metadata,
            },
        )

        self.entities[chunk_id] = entity

        # Index by file
        if chunk.file_path not in self._entity_index:
            self._entity_index[chunk.file_path] = set()
        self._entity_index[chunk.file_path].add(chunk_id)

        return entity

    def add_relationship(
        self,
        source: str,
        target: str,
        relation_type: CodeRelationType,
        strength: float = 1.0,
    ) -> CodeRelationship:
        """Add relationship between entities."""
        relationship = CodeRelationship(
            source=source,
            target=target,
            relation_type=relation_type,
            strength=min(strength, 1.0),  # Cap at 1.0
        )

        self.relationships.append(relationship)
        return relationship

    def add_import_relationships(self, symbol: Symbol, imports: List[str]):
        """Add import relationships for a symbol."""
        for import_module in imports:
            self.add_relationship(
                source=symbol.name,
                target=import_module,
                relation_type=CodeRelationType.IMPORTS,
                strength=0.8,
            )

    def add_dependency_relationships(self, symbol: Symbol, dependencies: List[str]):
        """Add dependency relationships from symbol."""
        for dep in dependencies:
            self.add_relationship(
                source=symbol.name,
                target=dep,
                relation_type=CodeRelationType.DEPENDS_ON,
                strength=0.7,
            )

    def add_containment_relationship(
        self, container: str, contained: str, direct: bool = True
    ):
        """Add containment relationship (e.g., class contains method)."""
        strength = 0.95 if direct else 0.5
        self.add_relationship(
            source=container,
            target=contained,
            relation_type=CodeRelationType.CONTAINS,
            strength=strength,
        )

    def add_inheritance_relationship(self, child: str, parent: str):
        """Add inheritance relationship."""
        self.add_relationship(
            source=child,
            target=parent,
            relation_type=CodeRelationType.INHERITS,
            strength=0.9,
        )

    def infer_relationships(self, symbol_index: SymbolIndex):
        """Infer relationships from symbol index."""
        symbols = symbol_index.get_all()

        # Group symbols by file for scope analysis
        symbols_by_file: Dict[str, List[Symbol]] = {}
        for symbol in symbols:
            if symbol.file_path not in symbols_by_file:
                symbols_by_file[symbol.file_path] = []
            symbols_by_file[symbol.file_path].append(symbol)

        # Infer containment (e.g., methods in classes)
        for file_path, file_symbols in symbols_by_file.items():
            classes = [s for s in file_symbols if s.type == SymbolType.CLASS]
            methods = [s for s in file_symbols if s.type == SymbolType.METHOD]

            # Simple heuristic: method after class in same file likely contained
            for class_sym in classes:
                for method_sym in methods:
                    if method_sym.line_number > class_sym.line_number:
                        self.add_containment_relationship(
                            class_sym.name, method_sym.name
                        )

        # Add dependency relationships from symbol metadata
        for symbol in symbols:
            if symbol.dependencies:
                self.add_dependency_relationships(symbol, symbol.dependencies)

    def get_entity(self, name: str) -> Optional[CodeEntity]:
        """Get entity by name."""
        return self.entities.get(name)

    def get_entities_by_file(self, file_path: str) -> List[CodeEntity]:
        """Get all entities in a file."""
        entity_names = self._entity_index.get(file_path, set())
        return [self.entities[name] for name in entity_names if name in self.entities]

    def get_relationships_from(self, entity: str) -> List[CodeRelationship]:
        """Get all outgoing relationships from entity."""
        return [r for r in self.relationships if r.source == entity]

    def get_relationships_to(self, entity: str) -> List[CodeRelationship]:
        """Get all incoming relationships to entity."""
        return [r for r in self.relationships if r.target == entity]

    def get_related_entities(
        self, entity: str, relation_type: Optional[CodeRelationType] = None
    ) -> List[str]:
        """Get entities related to given entity."""
        related = set()

        # Get outgoing relationships
        outgoing = self.get_relationships_from(entity)
        for rel in outgoing:
            if relation_type is None or rel.relation_type == relation_type:
                related.add(rel.target)

        # Get incoming relationships
        incoming = self.get_relationships_to(entity)
        for rel in incoming:
            if relation_type is None or rel.relation_type == relation_type:
                related.add(rel.source)

        return list(related)

    def get_graph_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        entity_types = {}
        for entity in self.entities.values():
            type_name = entity.entity_type.value
            entity_types[type_name] = entity_types.get(type_name, 0) + 1

        relation_types = {}
        for rel in self.relationships:
            type_name = rel.relation_type.value
            relation_types[type_name] = relation_types.get(type_name, 0) + 1

        return {
            "total_entities": len(self.entities),
            "entities_by_type": entity_types,
            "total_relationships": len(self.relationships),
            "relationships_by_type": relation_types,
            "total_files": len(self._entity_index),
        }

    @staticmethod
    def _symbol_type_to_entity_type(symbol_type: SymbolType) -> CodeEntityType:
        """Map symbol type to entity type."""
        mapping = {
            SymbolType.FUNCTION: CodeEntityType.FUNCTION,
            SymbolType.CLASS: CodeEntityType.CLASS,
            SymbolType.METHOD: CodeEntityType.FUNCTION,
            SymbolType.VARIABLE: CodeEntityType.VARIABLE,
            SymbolType.IMPORT: CodeEntityType.IMPORT,
            SymbolType.CONSTANT: CodeEntityType.CONSTANT,
            SymbolType.INTERFACE: CodeEntityType.INTERFACE,
            SymbolType.ENUM: CodeEntityType.ENUM,
            SymbolType.DECORATOR: CodeEntityType.TYPE,
            SymbolType.TYPE_ALIAS: CodeEntityType.TYPE,
        }
        return mapping.get(symbol_type, CodeEntityType.MODULE)


class CodeGraphAnalyzer:
    """Analyzes code graph for patterns and metrics."""

    def __init__(self, graph: CodeGraphBuilder):
        """Initialize analyzer with graph."""
        self.graph = graph

    def find_high_complexity_entities(self, threshold: int = 5) -> List[CodeEntity]:
        """Find entities with high cyclomatic complexity."""
        return [
            entity
            for entity in self.graph.entities.values()
            if entity.complexity >= threshold
        ]

    def find_heavily_used_entities(self, min_relationships: int = 3) -> List[str]:
        """Find entities that are heavily used (many incoming dependencies)."""
        usage_count = {}
        for rel in self.graph.relationships:
            if rel.relation_type in [
                CodeRelationType.CALLS,
                CodeRelationType.USES,
                CodeRelationType.DEPENDS_ON,
            ]:
                usage_count[rel.target] = usage_count.get(rel.target, 0) + 1

        return [entity for entity, count in usage_count.items() if count >= min_relationships]

    def find_isolated_entities(self) -> List[str]:
        """Find entities with no relationships."""
        related_entities = set()
        for rel in self.graph.relationships:
            related_entities.add(rel.source)
            related_entities.add(rel.target)

        return [
            name
            for name in self.graph.entities.keys()
            if name not in related_entities
        ]

    def find_coupling_issues(self, max_dependencies: int = 5) -> Dict[str, List[str]]:
        """Find entities with excessive dependencies."""
        issues = {}
        for entity_name in self.graph.entities.keys():
            dependencies = self.graph.get_related_entities(
                entity_name, CodeRelationType.DEPENDS_ON
            )
            if len(dependencies) > max_dependencies:
                issues[entity_name] = dependencies

        return issues

    def calculate_entity_centrality(self) -> Dict[str, float]:
        """Calculate centrality score for each entity (betweenness-like)."""
        centrality = {}

        for entity_name in self.graph.entities.keys():
            outgoing = len(self.graph.get_relationships_from(entity_name))
            incoming = len(self.graph.get_relationships_to(entity_name))
            centrality[entity_name] = (outgoing + incoming) / (
                len(self.graph.relationships) + 1
            )

        return centrality

    def find_dependency_cycles(self) -> List[List[str]]:
        """Find circular dependencies in code."""
        cycles = []
        visited = set()

        def dfs(node: str, path: List[str]) -> bool:
            if node in path:
                # Found cycle
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return True

            if node in visited:
                return False

            visited.add(node)
            path.append(node)

            related = self.graph.get_related_entities(
                node, CodeRelationType.DEPENDS_ON
            )
            for neighbor in related:
                if dfs(neighbor, path.copy()):
                    break

            return False

        for entity_name in self.graph.entities.keys():
            if entity_name not in visited:
                dfs(entity_name, [])

        return cycles

    def get_module_structure(self, file_path: str) -> Dict[str, Any]:
        """Analyze structure of a module."""
        entities = self.graph.get_entities_by_file(file_path)

        structure = {
            "file_path": file_path,
            "entities": len(entities),
            "by_type": {},
            "functions": [],
            "classes": [],
            "imports": [],
            "total_complexity": 0,
        }

        for entity in entities:
            type_name = entity.entity_type.value
            structure["by_type"][type_name] = structure["by_type"].get(type_name, 0) + 1
            structure["total_complexity"] += entity.complexity

            if entity.entity_type == CodeEntityType.FUNCTION:
                structure["functions"].append(entity.name)
            elif entity.entity_type == CodeEntityType.CLASS:
                structure["classes"].append(entity.name)
            elif entity.entity_type == CodeEntityType.IMPORT:
                structure["imports"].append(entity.name)

        return structure
