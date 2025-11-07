"""Tests for Phase 1 semantic search enhancements."""

import pytest
from src.athena.code_search.symbol_extractor import (
    SymbolExtractor, SymbolType, Symbol, SymbolIndex
)
from src.athena.code_search.code_chunker import (
    CodeChunker, ChunkingStrategy, Chunk
)
from src.athena.code_search.code_embeddings import (
    CodeEmbeddingManager, EmbeddingModelType, MockEmbedding,
    CodeLlamaEmbedding, create_code_embedding_manager
)


class TestSymbolExtractor:
    """Tests for symbol extraction."""

    @pytest.fixture
    def extractor(self):
        """Create symbol extractor."""
        return SymbolExtractor(language="python")

    @pytest.fixture
    def python_code(self):
        """Sample Python code."""
        return '''
def hello_world():
    """Print hello world."""
    print("Hello, World!")

class Calculator:
    """Simple calculator class."""

    def add(self, a, b):
        """Add two numbers."""
        return a + b

    def subtract(self, a, b):
        """Subtract two numbers."""
        return a - b

import json
import os

MY_CONSTANT = 42
'''

    def test_extract_functions(self, extractor, python_code):
        """Test extracting functions."""
        symbols = extractor.extract_symbols(python_code, "test.py")
        functions = [s for s in symbols if s.type == SymbolType.FUNCTION]

        assert len(functions) >= 1
        assert any(s.name == "hello_world" for s in functions)

    def test_extract_classes(self, extractor, python_code):
        """Test extracting classes."""
        symbols = extractor.extract_symbols(python_code, "test.py")
        classes = [s for s in symbols if s.type == SymbolType.CLASS]

        assert len(classes) >= 1
        assert any(s.name == "Calculator" for s in classes)

    def test_extract_imports(self, extractor, python_code):
        """Test extracting imports."""
        symbols = extractor.extract_symbols(python_code, "test.py")
        imports = [s for s in symbols if s.type == SymbolType.IMPORT]

        assert len(imports) >= 1

    def test_extract_constants(self, extractor, python_code):
        """Test extracting constants."""
        symbols = extractor.extract_symbols(python_code, "test.py")
        constants = [s for s in symbols if s.type == SymbolType.CONSTANT]

        assert len(constants) >= 1
        assert any(s.name == "MY_CONSTANT" for s in constants)

    def test_symbol_to_dict(self):
        """Test symbol serialization."""
        symbol = Symbol(
            name="test_func",
            type=SymbolType.FUNCTION,
            file_path="test.py",
            line_number=10,
            docstring="Test function",
        )

        symbol_dict = symbol.to_dict()
        assert symbol_dict["name"] == "test_func"
        assert symbol_dict["type"] == "function"
        assert symbol_dict["file_path"] == "test.py"


class TestSymbolIndex:
    """Tests for symbol indexing."""

    @pytest.fixture
    def index(self):
        """Create symbol index."""
        return SymbolIndex()

    @pytest.fixture
    def symbols(self):
        """Create sample symbols."""
        return [
            Symbol(
                name="func1",
                type=SymbolType.FUNCTION,
                file_path="file1.py",
                line_number=10,
            ),
            Symbol(
                name="func2",
                type=SymbolType.FUNCTION,
                file_path="file1.py",
                line_number=20,
            ),
            Symbol(
                name="MyClass",
                type=SymbolType.CLASS,
                file_path="file2.py",
                line_number=5,
            ),
        ]

    def test_add_symbol(self, index, symbols):
        """Test adding symbols."""
        for symbol in symbols:
            index.add_symbol(symbol)

        assert len(index.get_all()) == 3

    def test_find_by_name(self, index, symbols):
        """Test finding symbols by name."""
        for symbol in symbols:
            index.add_symbol(symbol)

        results = index.find_by_name("func1")
        assert len(results) == 1
        assert results[0].name == "func1"

    def test_find_by_type(self, index, symbols):
        """Test finding symbols by type."""
        for symbol in symbols:
            index.add_symbol(symbol)

        functions = index.find_by_type(SymbolType.FUNCTION)
        assert len(functions) == 2

        classes = index.find_by_type(SymbolType.CLASS)
        assert len(classes) == 1

    def test_find_by_file(self, index, symbols):
        """Test finding symbols in file."""
        for symbol in symbols:
            index.add_symbol(symbol)

        file1_symbols = index.find_by_file("file1.py")
        assert len(file1_symbols) == 2

    def test_search(self, index, symbols):
        """Test searching symbols."""
        for symbol in symbols:
            index.add_symbol(symbol)

        results = index.search("func")
        assert len(results) >= 2

    def test_statistics(self, index, symbols):
        """Test getting index statistics."""
        for symbol in symbols:
            index.add_symbol(symbol)

        stats = index.get_statistics()
        assert stats["total_symbols"] == 3
        assert stats["by_type"]["function"] == 2
        assert stats["by_type"]["class"] == 1


class TestCodeChunker:
    """Tests for code chunking."""

    @pytest.fixture
    def chunker(self):
        """Create code chunker."""
        return CodeChunker(language="python")

    @pytest.fixture
    def python_code(self):
        """Sample Python code with functions."""
        return '''def function1():
    """First function."""
    return 1

def function2():
    """Second function."""
    return 2

class MyClass:
    def method1(self):
        """Method in class."""
        pass
'''

    def test_chunk_by_function(self, chunker, python_code):
        """Test chunking by function."""
        chunks = chunker.chunk_by_function(python_code, "test.py")

        assert len(chunks) >= 2
        assert all(isinstance(c, Chunk) for c in chunks)
        assert any(c.symbol_type == "function" for c in chunks)

    def test_chunk_by_class(self, chunker, python_code):
        """Test chunking by class."""
        chunks = chunker.chunk_by_class(python_code, "test.py")

        assert len(chunks) >= 1
        assert any(c.symbol_type == "class" for c in chunks)

    def test_chunk_by_module(self, chunker, python_code):
        """Test chunking by module."""
        chunks = chunker.chunk_by_module(python_code, "test.py")

        assert len(chunks) == 1
        assert chunks[0].symbol_type == "module"

    def test_chunk_by_fixed_size(self, chunker, python_code):
        """Test fixed-size chunking."""
        chunks = chunker.chunk_by_fixed_size(
            python_code, "test.py", chunk_size=5, overlap=1
        )

        assert len(chunks) >= 1
        assert all(c.symbol_type == "fixed_size" for c in chunks)

    def test_chunk_strategy_routing(self, chunker, python_code):
        """Test strategy routing."""
        func_chunks = chunker.chunk(
            python_code, "test.py", strategy=ChunkingStrategy.FUNCTION
        )
        assert len(func_chunks) >= 2

        class_chunks = chunker.chunk(
            python_code, "test.py", strategy=ChunkingStrategy.CLASS
        )
        assert len(class_chunks) >= 1

    def test_chunk_to_dict(self, chunker, python_code):
        """Test chunk serialization."""
        chunks = chunker.chunk_by_function(python_code, "test.py")
        chunk_dict = chunks[0].to_dict()

        assert "content" in chunk_dict
        assert "file_path" in chunk_dict
        assert "start_line" in chunk_dict
        assert "symbol_type" in chunk_dict

    def test_suggest_strategy(self, chunker, python_code):
        """Test strategy suggestion."""
        strategy = chunker.suggest_strategy(python_code, "find function")
        assert strategy == ChunkingStrategy.FUNCTION

        strategy = chunker.suggest_strategy(python_code, "find class")
        assert strategy == ChunkingStrategy.CLASS


class TestCodeEmbeddings:
    """Tests for code embeddings."""

    def test_mock_embedding_creation(self):
        """Test creating mock embedding model."""
        model = MockEmbedding(embedding_dim=384)

        embedding = model.embed("test code")
        assert len(embedding) == 384
        assert all(-1 <= val <= 1 for val in embedding)

    def test_mock_embedding_consistency(self):
        """Test mock embedding consistency."""
        model = MockEmbedding()

        emb1 = model.embed("same code")
        emb2 = model.embed("same code")
        assert emb1 == emb2

    def test_mock_embedding_batch(self):
        """Test batch mock embedding."""
        model = MockEmbedding()

        texts = ["code1", "code2", "code3"]
        embeddings = model.embed_batch(texts)

        assert len(embeddings) == 3
        assert all(len(emb) == 384 for emb in embeddings)

    def test_embedding_manager_creation(self):
        """Test creating embedding manager."""
        manager = CodeEmbeddingManager(EmbeddingModelType.MOCK)

        assert manager.model_name == "mock"
        assert manager.embedding_dimension > 0

    def test_embedding_manager_embed(self):
        """Test embedding manager."""
        manager = CodeEmbeddingManager(EmbeddingModelType.MOCK)

        embedding = manager.embed("def hello(): pass")
        assert isinstance(embedding, list)
        assert len(embedding) > 0

    def test_embedding_manager_batch(self):
        """Test batch embedding."""
        manager = CodeEmbeddingManager(EmbeddingModelType.MOCK)

        codes = ["def foo(): pass", "def bar(): pass"]
        embeddings = manager.embed_batch(codes)

        assert len(embeddings) == 2
        assert all(isinstance(emb, list) for emb in embeddings)

    def test_code_specific_embedding(self):
        """Test code-specific embedding."""
        manager = CodeEmbeddingManager(EmbeddingModelType.MOCK)

        embedding = manager.embed_code("def test(): pass", language="python")
        assert isinstance(embedding, list)

    def test_switch_model(self):
        """Test switching embedding models."""
        manager = CodeEmbeddingManager(EmbeddingModelType.MOCK)
        assert manager.model_name == "mock"

        manager.switch_model(EmbeddingModelType.MOCK)
        assert manager.model_name == "mock"

    def test_create_embedding_manager(self):
        """Test convenience function."""
        manager = create_code_embedding_manager(model_type="mock")
        assert manager.model_type == EmbeddingModelType.MOCK

    def test_embedding_statistics(self):
        """Test getting embedding statistics."""
        manager = CodeEmbeddingManager(EmbeddingModelType.MOCK)
        stats = manager.get_statistics()

        assert "model_type" in stats
        assert "model_name" in stats
        assert "embedding_dimension" in stats


class TestPhase1Integration:
    """Integration tests for Phase 1 enhancements."""

    @pytest.fixture
    def sample_project(self):
        """Sample code project."""
        return {
            "file1.py": '''
def process_data(data):
    """Process input data."""
    return [x * 2 for x in data]

class DataProcessor:
    def transform(self, data):
        """Transform data."""
        return processed_data
''',
            "file2.py": '''
def validate_input(value):
    """Validate input."""
    return isinstance(value, int)

import json
''',
        }

    def test_symbol_extraction_pipeline(self, sample_project):
        """Test full symbol extraction pipeline."""
        extractor = SymbolExtractor(language="python")
        index = SymbolIndex()

        for file_path, code in sample_project.items():
            symbols = extractor.extract_symbols(code, file_path)
            for symbol in symbols:
                index.add_symbol(symbol)

        assert len(index.get_all()) > 0
        assert len(index.find_by_type(SymbolType.FUNCTION)) >= 3

    def test_chunking_pipeline(self, sample_project):
        """Test full chunking pipeline."""
        chunker = CodeChunker(language="python")

        all_chunks = []
        for file_path, code in sample_project.items():
            chunks = chunker.chunk(
                code, file_path, strategy=ChunkingStrategy.FUNCTION
            )
            all_chunks.extend(chunks)

        assert len(all_chunks) >= 2

    def test_embedding_pipeline(self, sample_project):
        """Test embedding pipeline."""
        manager = CodeEmbeddingManager(EmbeddingModelType.MOCK)

        for file_path, code in sample_project.items():
            embedding = manager.embed_code(code, language="python")
            assert isinstance(embedding, list)
            assert len(embedding) > 0

    def test_combined_workflow(self, sample_project):
        """Test combined symbol + chunking + embedding workflow."""
        extractor = SymbolExtractor(language="python")
        chunker = CodeChunker(language="python")
        embedding_manager = CodeEmbeddingManager(EmbeddingModelType.MOCK)
        symbol_index = SymbolIndex()
        all_chunks = []

        for file_path, code in sample_project.items():
            # Extract symbols
            symbols = extractor.extract_symbols(code, file_path)
            for symbol in symbols:
                symbol_index.add_symbol(symbol)

            # Chunk code
            chunks = chunker.chunk(code, file_path)
            all_chunks.extend(chunks)

            # Generate embeddings for chunks
            for chunk in chunks:
                embedding = embedding_manager.embed(chunk.content)
                chunk.metadata["embedding"] = len(embedding)  # Store size instead

        assert len(symbol_index.get_all()) > 0
        # Verify embeddings were added to all chunks in the workflow
        assert len(all_chunks) > 0
        assert all("embedding" in c.metadata for c in all_chunks)
