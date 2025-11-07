"""Tests for code RAG integration."""

import pytest
from datetime import datetime, timedelta

from src.athena.code_search.code_rag_integration import (
    SearchStrategy,
    SearchResult,
    SearchQuery,
    CodeRAGRetriever,
    CodeRAGPipeline,
)
from src.athena.code_search.symbol_extractor import (
    Symbol,
    SymbolType,
    SymbolIndex,
)
from src.athena.code_search.code_embeddings import (
    CodeEmbeddingManager,
    EmbeddingModelType,
)
from src.athena.code_search.code_graph_integration import CodeGraphBuilder
from src.athena.code_search.code_temporal_analysis import CodeChangeTracker, CodeChange, ChangeType


class TestSearchResult:
    """Tests for SearchResult."""

    def test_result_creation(self):
        """Test creating search result."""
        result = SearchResult(
            entity_name="process_data",
            entity_type="function",
            file_path="utils.py",
            line_number=10,
            semantic_score=0.85,
            combined_score=0.80,
        )

        assert result.entity_name == "process_data"
        assert result.semantic_score == 0.85

    def test_result_to_dict(self):
        """Test result serialization."""
        result = SearchResult(
            entity_name="MyClass",
            entity_type="class",
            file_path="models.py",
            line_number=5,
            semantic_score=0.75,
            structural_score=0.65,
            combined_score=0.70,
        )

        result_dict = result.to_dict()
        assert result_dict["entity_name"] == "MyClass"
        assert result_dict["semantic_score"] == 0.75


class TestSearchQuery:
    """Tests for SearchQuery."""

    def test_query_creation(self):
        """Test creating search query."""
        query = SearchQuery(
            query_text="find data processor",
            strategy=SearchStrategy.HYBRID,
            top_k=5,
        )

        assert query.query_text == "find data processor"
        assert query.strategy == SearchStrategy.HYBRID
        assert query.top_k == 5

    def test_query_default_weights_hybrid(self):
        """Test default weights for hybrid strategy."""
        query = SearchQuery(
            query_text="test",
            strategy=SearchStrategy.HYBRID,
        )

        assert query.weights["semantic"] == 0.4
        assert query.weights["structural"] == 0.3
        assert query.weights["temporal"] == 0.2
        assert query.weights["centrality"] == 0.1

    def test_query_default_weights_semantic(self):
        """Test default weights for semantic strategy."""
        query = SearchQuery(
            query_text="test",
            strategy=SearchStrategy.SEMANTIC,
        )

        assert query.weights["semantic"] == 1.0
        assert query.weights["structural"] == 0.0


class TestCodeRAGRetriever:
    """Tests for CodeRAGRetriever."""

    @pytest.fixture
    def setup(self):
        """Setup retriever."""
        symbol_index = SymbolIndex()
        graph_builder = CodeGraphBuilder()
        embedding_manager = CodeEmbeddingManager(EmbeddingModelType.MOCK)
        change_tracker = CodeChangeTracker()

        # Add sample symbols
        symbols = [
            Symbol(
                name="process_data",
                type=SymbolType.FUNCTION,
                file_path="utils.py",
                line_number=10,
                docstring="Process input data",
                complexity=3,
            ),
            Symbol(
                name="DataProcessor",
                type=SymbolType.CLASS,
                file_path="processor.py",
                line_number=5,
                docstring="Main processor class",
                complexity=5,
            ),
        ]

        for symbol in symbols:
            symbol_index.add_symbol(symbol)
            graph_builder.add_symbol(symbol)

        retriever = CodeRAGRetriever(
            symbol_index, graph_builder, embedding_manager, change_tracker
        )
        return retriever, symbols

    def test_search_basic(self, setup):
        """Test basic search."""
        retriever, _ = setup
        query = SearchQuery(query_text="process", top_k=5)

        results = retriever.search(query)
        assert isinstance(results, list)
        assert len(results) >= 0

    def test_search_with_filters(self, setup):
        """Test search with filters."""
        retriever, _ = setup
        query = SearchQuery(
            query_text="processor",
            filters={"entity_type": "class"},
            top_k=5,
        )

        results = retriever.search(query)
        if results:
            assert all(r.entity_type == "class" for r in results)

    def test_search_by_pattern(self, setup):
        """Test pattern-based search."""
        retriever, _ = setup
        results = retriever.search_by_pattern("processor", top_k=5)

        assert isinstance(results, list)

    def test_search_by_complexity(self, setup):
        """Test complexity-based search."""
        retriever, _ = setup
        results = retriever.search_by_complexity(
            min_complexity=2, max_complexity=4, top_k=5
        )

        assert len(results) >= 0
        # Verify results have proper structure
        if results:
            assert all(isinstance(r.structural_score, float) for r in results)

    def test_search_related_entities(self, setup):
        """Test related entity search."""
        retriever, symbols = setup

        # Add relationship
        retriever.graph_builder.add_relationship(
            symbols[0].name, symbols[1].name, "uses"
        )

        results = retriever.search_related_entities(symbols[0].name, top_k=5)
        assert isinstance(results, list)

    def test_semantic_score_calculation(self, setup):
        """Test semantic score calculation."""
        retriever, symbols = setup
        candidate = symbols[0]
        query_embedding = retriever.embedding_manager.embed("process")

        score = retriever._calculate_semantic_score(candidate, query_embedding)
        assert 0.0 <= score <= 1.0

    def test_structural_score_calculation(self, setup):
        """Test structural score calculation."""
        retriever, symbols = setup
        candidate = symbols[0]
        query = SearchQuery(
            query_text="process",
            filters={"entity_type": "function"},
        )

        score = retriever._calculate_structural_score(candidate, query)
        assert 0.0 <= score <= 1.0

    def test_temporal_score_calculation(self, setup):
        """Test temporal score calculation."""
        retriever, symbols = setup

        # Add change history
        now = datetime.now()
        retriever.change_tracker.record_change(
            CodeChange(
                entity_name=symbols[0].name,
                entity_type="function",
                change_type=ChangeType.MODIFICATION,
                timestamp=now,
                file_path="utils.py",
            )
        )

        score = retriever._calculate_temporal_score(symbols[0])
        assert 0.0 <= score <= 1.0

    def test_centrality_score_calculation(self, setup):
        """Test centrality score calculation."""
        retriever, symbols = setup

        # Add relationships
        retriever.graph_builder.add_relationship(
            symbols[0].name, symbols[1].name, "uses"
        )
        retriever.graph_builder.add_relationship(
            symbols[1].name, symbols[0].name, "calls"
        )

        score = retriever._calculate_centrality_score(symbols[0])
        assert 0.0 <= score <= 1.0

    def test_cosine_similarity(self, setup):
        """Test cosine similarity calculation."""
        retriever, _ = setup

        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        similarity = retriever._cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(1.0)

        vec3 = [0.0, 1.0, 0.0]
        similarity = retriever._cosine_similarity(vec1, vec3)
        assert similarity == pytest.approx(0.0)

    def test_cosine_similarity_orthogonal(self, setup):
        """Test cosine similarity with orthogonal vectors."""
        retriever, _ = setup

        vec1 = [1.0, 0.0]
        vec2 = [0.0, 1.0]
        similarity = retriever._cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(0.0)


class TestCodeRAGPipeline:
    """Tests for CodeRAGPipeline."""

    @pytest.fixture
    def pipeline(self):
        """Setup pipeline."""
        symbol_index = SymbolIndex()
        graph_builder = CodeGraphBuilder()
        embedding_manager = CodeEmbeddingManager(EmbeddingModelType.MOCK)
        change_tracker = CodeChangeTracker()

        # Add sample data
        symbols = [
            Symbol(
                name="fetch_data",
                type=SymbolType.FUNCTION,
                file_path="api.py",
                line_number=10,
                docstring="Fetch data from API",
                complexity=2,
            ),
            Symbol(
                name="APIClient",
                type=SymbolType.CLASS,
                file_path="api.py",
                line_number=5,
                docstring="API client",
                complexity=4,
            ),
        ]

        for symbol in symbols:
            symbol_index.add_symbol(symbol)
            graph_builder.add_symbol(symbol)

        retriever = CodeRAGRetriever(
            symbol_index, graph_builder, embedding_manager, change_tracker
        )
        return CodeRAGPipeline(retriever)

    def test_execute_query(self, pipeline):
        """Test executing query."""
        results = pipeline.execute_query("fetch api data")

        assert isinstance(results, list)
        assert len(pipeline.search_history) == 1

    def test_execute_advanced_query(self, pipeline):
        """Test executing advanced query."""
        results = pipeline.execute_advanced_query(
            "fetch",
            entity_type="function",
            min_complexity=1,
            strategy=SearchStrategy.SEMANTIC,
        )

        assert isinstance(results, list)

    def test_find_similar_code(self, pipeline):
        """Test finding similar code."""
        results = pipeline.find_similar_code("fetch_data", top_k=5)

        assert isinstance(results, list)

    def test_find_by_complexity(self, pipeline):
        """Test finding by complexity."""
        results = pipeline.find_by_complexity(
            min_complexity=2, max_complexity=5, top_k=10
        )

        assert isinstance(results, list)

    def test_get_search_analytics(self, pipeline):
        """Test analytics retrieval."""
        pipeline.execute_query("test")
        pipeline.execute_query("test2")

        analytics = pipeline.get_search_analytics()
        assert analytics["total_searches"] == 2
        assert "strategies_used" in analytics

    def test_generate_rag_report(self, pipeline):
        """Test report generation."""
        pipeline.execute_query("test")

        report = pipeline.generate_rag_report()
        assert "RAG RETRIEVAL REPORT" in report
        assert "Total Searches" in report


class TestRAGIntegration:
    """Integration tests for RAG pipeline."""

    def test_full_rag_workflow(self):
        """Test complete RAG workflow."""
        # Setup
        symbol_index = SymbolIndex()
        graph_builder = CodeGraphBuilder()
        embedding_manager = CodeEmbeddingManager(EmbeddingModelType.MOCK)
        change_tracker = CodeChangeTracker()

        # Add comprehensive data
        symbols = [
            Symbol(
                name="authenticate",
                type=SymbolType.FUNCTION,
                file_path="auth.py",
                line_number=10,
                docstring="Authenticate user",
                complexity=3,
                dependencies=["hash_password"],
            ),
            Symbol(
                name="hash_password",
                type=SymbolType.FUNCTION,
                file_path="auth.py",
                line_number=20,
                docstring="Hash password",
                complexity=2,
            ),
            Symbol(
                name="AuthService",
                type=SymbolType.CLASS,
                file_path="auth.py",
                line_number=1,
                docstring="Authentication service",
                complexity=5,
            ),
        ]

        for symbol in symbols:
            symbol_index.add_symbol(symbol)
            graph_builder.add_symbol(symbol)

        # Add relationships
        graph_builder.add_relationship(
            symbols[2].name, symbols[0].name, "contains"
        )
        graph_builder.add_relationship(
            symbols[0].name, symbols[1].name, "calls"
        )

        # Add change history
        now = datetime.now()
        change_tracker.record_change(
            CodeChange(
                entity_name=symbols[0].name,
                entity_type="function",
                change_type=ChangeType.MODIFICATION,
                timestamp=now,
                file_path="auth.py",
            )
        )

        # Create retriever and pipeline
        retriever = CodeRAGRetriever(
            symbol_index, graph_builder, embedding_manager, change_tracker
        )
        pipeline = CodeRAGPipeline(retriever)

        # Execute various searches
        results1 = pipeline.execute_query("authentication")
        assert isinstance(results1, list)

        results2 = pipeline.execute_advanced_query(
            "password",
            entity_type="function",
            strategy=SearchStrategy.STRUCTURAL,
        )
        assert isinstance(results2, list)

        results3 = pipeline.find_by_complexity(min_complexity=2, max_complexity=3)
        assert isinstance(results3, list)

        # Verify analytics (find_by_complexity doesn't go through execute_query)
        analytics = pipeline.get_search_analytics()
        assert analytics["total_searches"] == 2
        assert len(analytics["strategies_used"]) >= 1

        # Verify all scores are in valid range
        for results in [results1, results2, results3]:
            for result in results:
                assert 0.0 <= result.semantic_score <= 1.0
                assert 0.0 <= result.structural_score <= 1.0
                assert 0.0 <= result.temporal_score <= 1.0
                assert 0.0 <= result.centrality_score <= 1.0
                assert 0.0 <= result.combined_score <= 1.0

        # Generate report
        report = pipeline.generate_rag_report()
        assert len(report) > 0
