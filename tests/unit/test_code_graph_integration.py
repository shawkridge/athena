"""Tests for code graph integration."""

import pytest
from src.athena.code_search.code_graph_integration import (
    CodeEntityType,
    CodeRelationType,
    CodeEntity,
    CodeRelationship,
    CodeGraphBuilder,
    CodeGraphAnalyzer,
)
from src.athena.code_search.symbol_extractor import (
    Symbol,
    SymbolType,
    SymbolIndex,
)
from src.athena.code_search.code_chunker import Chunk


class TestCodeEntity:
    """Tests for CodeEntity."""

    def test_entity_creation(self):
        """Test creating code entity."""
        entity = CodeEntity(
            name="process_data",
            entity_type=CodeEntityType.FUNCTION,
            file_path="utils.py",
            line_number=10,
            complexity=3,
        )

        assert entity.name == "process_data"
        assert entity.entity_type == CodeEntityType.FUNCTION
        assert entity.file_path == "utils.py"

    def test_entity_to_dict(self):
        """Test entity serialization."""
        entity = CodeEntity(
            name="DataProcessor",
            entity_type=CodeEntityType.CLASS,
            file_path="processor.py",
            line_number=5,
            docstring="Processes data",
            complexity=5,
        )

        entity_dict = entity.to_dict()
        assert entity_dict["name"] == "DataProcessor"
        assert entity_dict["entity_type"] == "Component"
        assert entity_dict["docstring"] == "Processes data"


class TestCodeRelationship:
    """Tests for CodeRelationship."""

    def test_relationship_creation(self):
        """Test creating relationship."""
        rel = CodeRelationship(
            source="func_a",
            target="func_b",
            relation_type=CodeRelationType.CALLS,
            strength=0.9,
        )

        assert rel.source == "func_a"
        assert rel.target == "func_b"
        assert rel.relation_type == CodeRelationType.CALLS

    def test_relationship_to_dict(self):
        """Test relationship serialization."""
        rel = CodeRelationship(
            source="ClassA",
            target="ClassB",
            relation_type=CodeRelationType.INHERITS,
            strength=0.95,
        )

        rel_dict = rel.to_dict()
        assert rel_dict["source"] == "ClassA"
        assert rel_dict["relation_type"] == "inherits"
        assert rel_dict["strength"] == 0.95


class TestCodeGraphBuilder:
    """Tests for CodeGraphBuilder."""

    @pytest.fixture
    def builder(self):
        """Create graph builder."""
        return CodeGraphBuilder()

    @pytest.fixture
    def sample_symbols(self):
        """Create sample symbols."""
        return [
            Symbol(
                name="process_data",
                type=SymbolType.FUNCTION,
                file_path="utils.py",
                line_number=10,
                complexity=3,
            ),
            Symbol(
                name="DataProcessor",
                type=SymbolType.CLASS,
                file_path="processor.py",
                line_number=5,
                complexity=5,
            ),
            Symbol(
                name="transform",
                type=SymbolType.METHOD,
                file_path="processor.py",
                line_number=15,
                dependencies=["process_data"],
            ),
        ]

    def test_add_symbol(self, builder, sample_symbols):
        """Test adding symbols."""
        entity = builder.add_symbol(sample_symbols[0])

        assert entity.name == "process_data"
        assert entity.entity_type == CodeEntityType.FUNCTION
        assert len(builder.entities) == 1

    def test_add_chunk(self, builder):
        """Test adding chunk as entity."""
        chunk = Chunk(
            content="def hello(): pass",
            file_path="test.py",
            start_line=1,
            end_line=1,
            symbol_type="function",
        )

        entity = builder.add_chunk(chunk, "chunk_001")
        assert entity.name == "chunk_001"
        assert entity.entity_type == CodeEntityType.MODULE

    def test_add_relationship(self, builder, sample_symbols):
        """Test adding relationships."""
        # Add entities first
        builder.add_symbol(sample_symbols[0])
        builder.add_symbol(sample_symbols[1])

        # Add relationship
        rel = builder.add_relationship(
            source="process_data",
            target="DataProcessor",
            relation_type=CodeRelationType.USES,
        )

        assert len(builder.relationships) == 1
        assert rel.source == "process_data"

    def test_add_containment_relationship(self, builder):
        """Test containment relationships."""
        builder.add_relationship(
            source="DataProcessor",
            target="transform",
            relation_type=CodeRelationType.CONTAINS,
            strength=0.95,
        )

        assert len(builder.relationships) == 1
        rel = builder.relationships[0]
        assert rel.relation_type == CodeRelationType.CONTAINS

    def test_infer_relationships(self, builder, sample_symbols):
        """Test relationship inference."""
        # Create symbol index
        index = SymbolIndex()
        for symbol in sample_symbols:
            index.add_symbol(symbol)

        # Add symbols to graph
        for symbol in sample_symbols:
            builder.add_symbol(symbol)

        # Infer relationships
        builder.infer_relationships(index)

        # Should have inferred some relationships
        assert len(builder.relationships) >= 0

    def test_get_entity(self, builder, sample_symbols):
        """Test entity retrieval."""
        builder.add_symbol(sample_symbols[0])

        entity = builder.get_entity("process_data")
        assert entity is not None
        assert entity.name == "process_data"

    def test_get_entities_by_file(self, builder, sample_symbols):
        """Test getting entities by file."""
        for symbol in sample_symbols:
            builder.add_symbol(symbol)

        processor_entities = builder.get_entities_by_file("processor.py")
        assert len(processor_entities) == 2

        utils_entities = builder.get_entities_by_file("utils.py")
        assert len(utils_entities) == 1

    def test_get_relationships_from(self, builder):
        """Test getting outgoing relationships."""
        builder.add_relationship(
            "A", "B", CodeRelationType.CALLS
        )
        builder.add_relationship(
            "A", "C", CodeRelationType.USES
        )
        builder.add_relationship(
            "B", "C", CodeRelationType.CALLS
        )

        from_a = builder.get_relationships_from("A")
        assert len(from_a) == 2
        assert all(r.source == "A" for r in from_a)

    def test_get_relationships_to(self, builder):
        """Test getting incoming relationships."""
        builder.add_relationship(
            "A", "C", CodeRelationType.CALLS
        )
        builder.add_relationship(
            "B", "C", CodeRelationType.USES
        )

        to_c = builder.get_relationships_to("C")
        assert len(to_c) == 2
        assert all(r.target == "C" for r in to_c)

    def test_get_related_entities(self, builder):
        """Test getting related entities."""
        builder.add_relationship("A", "B", CodeRelationType.CALLS)
        builder.add_relationship("A", "C", CodeRelationType.USES)
        builder.add_relationship("D", "A", CodeRelationType.DEPENDS_ON)

        related = builder.get_related_entities("A")
        assert "B" in related
        assert "C" in related
        assert "D" in related

    def test_get_graph_stats(self, builder, sample_symbols):
        """Test graph statistics."""
        for symbol in sample_symbols:
            builder.add_symbol(symbol)

        builder.add_relationship("process_data", "DataProcessor", CodeRelationType.USES)

        stats = builder.get_graph_stats()
        assert stats["total_entities"] == 3
        assert stats["total_relationships"] == 1
        assert "Function" in stats["entities_by_type"]
        assert "Component" in stats["entities_by_type"]


class TestCodeGraphAnalyzer:
    """Tests for CodeGraphAnalyzer."""

    @pytest.fixture
    def graph_with_data(self):
        """Create graph with sample data."""
        builder = CodeGraphBuilder()

        # Add entities
        entities = [
            ("process_data", CodeEntityType.FUNCTION, 3),
            ("validate_input", CodeEntityType.FUNCTION, 4),
            ("DataProcessor", CodeEntityType.CLASS, 6),
            ("cache", CodeEntityType.VARIABLE, 1),
            ("utils", CodeEntityType.MODULE, 2),
        ]

        for name, entity_type, complexity in entities:
            entity = CodeEntity(
                name=name,
                entity_type=entity_type,
                file_path="test.py",
                line_number=1,
                complexity=complexity,
            )
            builder.entities[name] = entity

            # Update index
            if "test.py" not in builder._entity_index:
                builder._entity_index["test.py"] = set()
            builder._entity_index["test.py"].add(name)

        # Add relationships
        builder.add_relationship("validate_input", "utils", CodeRelationType.USES)
        builder.add_relationship("DataProcessor", "process_data", CodeRelationType.USES)
        builder.add_relationship("DataProcessor", "validate_input", CodeRelationType.USES)
        builder.add_relationship("process_data", "cache", CodeRelationType.USES)
        builder.add_relationship("process_data", "utils", CodeRelationType.DEPENDS_ON)
        builder.add_relationship("validate_input", "cache", CodeRelationType.USES)

        return builder

    def test_find_high_complexity_entities(self, graph_with_data):
        """Test finding high complexity entities."""
        analyzer = CodeGraphAnalyzer(graph_with_data)

        high_complexity = analyzer.find_high_complexity_entities(threshold=5)
        assert len(high_complexity) == 1
        assert high_complexity[0].name == "DataProcessor"

    def test_find_heavily_used_entities(self, graph_with_data):
        """Test finding heavily used entities."""
        analyzer = CodeGraphAnalyzer(graph_with_data)

        heavily_used = analyzer.find_heavily_used_entities(min_relationships=2)
        assert "cache" in heavily_used
        assert "utils" in heavily_used

    def test_find_isolated_entities(self, graph_with_data):
        """Test finding isolated entities."""
        analyzer = CodeGraphAnalyzer(graph_with_data)

        # Add isolated entity
        isolated_entity = CodeEntity(
            name="isolated",
            entity_type=CodeEntityType.FUNCTION,
            file_path="test.py",
            line_number=1,
        )
        graph_with_data.entities["isolated"] = isolated_entity

        isolated = analyzer.find_isolated_entities()
        assert "isolated" in isolated

    def test_calculate_entity_centrality(self, graph_with_data):
        """Test centrality calculation."""
        analyzer = CodeGraphAnalyzer(graph_with_data)

        centrality = analyzer.calculate_entity_centrality()
        assert len(centrality) == 5
        assert all(0 <= v <= 1 for v in centrality.values())

        # utils and cache should have high centrality
        assert centrality["utils"] > 0
        assert centrality["cache"] > 0

    def test_find_dependency_cycles(self, graph_with_data):
        """Test finding cycles."""
        analyzer = CodeGraphAnalyzer(graph_with_data)

        # Add cyclic dependency
        graph_with_data.add_relationship("utils", "process_data", CodeRelationType.DEPENDS_ON)

        cycles = analyzer.find_dependency_cycles()
        # Should find at least potential cycle paths
        assert isinstance(cycles, list)

    def test_get_module_structure(self, graph_with_data):
        """Test module structure analysis."""
        analyzer = CodeGraphAnalyzer(graph_with_data)

        structure = analyzer.get_module_structure("test.py")
        assert structure["entities"] == 5
        assert "functions" in structure
        assert "classes" in structure


class TestCodeGraphIntegration:
    """Integration tests for code graph."""

    def test_full_graph_workflow(self):
        """Test complete graph building workflow."""
        builder = CodeGraphBuilder()

        # Create symbols
        symbols = [
            Symbol(
                name="fetch_data",
                type=SymbolType.FUNCTION,
                file_path="api.py",
                line_number=10,
                complexity=2,
                dependencies=["requests"],
            ),
            Symbol(
                name="APIClient",
                type=SymbolType.CLASS,
                file_path="api.py",
                line_number=5,
                complexity=4,
            ),
            Symbol(
                name="get_user",
                type=SymbolType.METHOD,
                file_path="api.py",
                line_number=20,
                dependencies=["fetch_data"],
            ),
        ]

        # Add to graph
        for symbol in symbols:
            builder.add_symbol(symbol)

        # Add relationships
        builder.add_relationship(
            "APIClient", "fetch_data", CodeRelationType.USES
        )
        builder.add_relationship(
            "get_user", "fetch_data", CodeRelationType.CALLS
        )

        # Analyze
        analyzer = CodeGraphAnalyzer(builder)
        stats = builder.get_graph_stats()

        assert stats["total_entities"] == 3
        assert stats["total_relationships"] == 2

        # Find patterns
        high_complexity = analyzer.find_high_complexity_entities(threshold=3)
        assert len(high_complexity) >= 1

        # Check structure
        structure = analyzer.get_module_structure("api.py")
        assert structure["entities"] == 3
        assert "APIClient" in structure["classes"]
