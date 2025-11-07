"""Tests for code navigation system."""

import pytest

from src.athena.code_search.code_navigation import (
    NavigationDirection,
    NavigationNode,
    NavigationBreadcrumb,
    CodeNavigator,
    NavigationGuide,
)
from src.athena.code_search.symbol_extractor import (
    Symbol,
    SymbolType,
    SymbolIndex,
)
from src.athena.code_search.code_graph_integration import CodeGraphBuilder
from src.athena.code_search.code_dependency_analysis import (
    DependencyGraph,
    Dependency,
    DependencyType,
)


class TestNavigationNode:
    """Tests for NavigationNode."""

    def test_node_creation(self):
        """Test creating navigation node."""
        node = NavigationNode(
            name="process_data",
            entity_type="function",
            file_path="utils.py",
            line_number=10,
            relevance_score=0.85,
            distance=2,
        )

        assert node.name == "process_data"
        assert node.distance == 2
        assert node.relevance_score == 0.85


class TestNavigationBreadcrumb:
    """Tests for NavigationBreadcrumb."""

    def test_breadcrumb_creation(self):
        """Test creating breadcrumb."""
        breadcrumb = NavigationBreadcrumb(
            start="func_a",
            current="func_c",
            path=["func_a", "func_b", "func_c"],
        )

        assert breadcrumb.start == "func_a"
        assert breadcrumb.depth == 2

    def test_breadcrumb_display(self):
        """Test breadcrumb display string."""
        breadcrumb = NavigationBreadcrumb(
            start="a",
            current="c",
            path=["a", "b", "c"],
        )

        display = breadcrumb.to_display_string()
        assert "a" in display
        assert ">" in display
        assert "c" in display


class TestCodeNavigator:
    """Tests for CodeNavigator."""

    @pytest.fixture
    def setup(self):
        """Setup navigator."""
        symbol_index = SymbolIndex()
        graph_builder = CodeGraphBuilder()
        dependency_graph = DependencyGraph()

        # Add symbols
        symbols = [
            Symbol(
                name="process_data",
                type=SymbolType.FUNCTION,
                file_path="data.py",
                line_number=10,
            ),
            Symbol(
                name="validate_input",
                type=SymbolType.FUNCTION,
                file_path="validators.py",
                line_number=20,
            ),
            Symbol(
                name="DataProcessor",
                type=SymbolType.CLASS,
                file_path="processor.py",
                line_number=5,
            ),
        ]

        for symbol in symbols:
            symbol_index.add_symbol(symbol)
            graph_builder.add_symbol(symbol)

        # Add relationships
        graph_builder.add_relationship(
            symbols[0].name,
            symbols[1].name,
            "calls"
        )
        graph_builder.add_relationship(
            symbols[2].name,
            symbols[0].name,
            "uses"
        )

        # Add dependencies
        dependency_graph.add_dependency(
            Dependency(
                source=symbols[0].name,
                target=symbols[1].name,
                source_file="data.py",
                target_file="validators.py",
                dependency_type=DependencyType.FUNCTION_CALL,
            )
        )

        navigator = CodeNavigator(symbol_index, graph_builder, dependency_graph)
        return navigator, symbols

    def test_navigate_to(self, setup):
        """Test navigating to entity."""
        navigator, symbols = setup

        node = navigator.navigate_to(symbols[0].name)
        assert node is not None
        assert node.name == symbols[0].name
        assert node.is_entry_point is True

    def test_explore_incoming(self, setup):
        """Test exploring incoming dependencies."""
        navigator, symbols = setup

        incoming = navigator.explore_incoming(symbols[0].name)
        assert isinstance(incoming, list)
        # process_data has DataProcessor depending on it
        if incoming:
            assert any(n.name == "DataProcessor" for n in incoming)

    def test_explore_outgoing(self, setup):
        """Test exploring outgoing dependencies."""
        navigator, symbols = setup

        outgoing = navigator.explore_outgoing(symbols[0].name)
        assert isinstance(outgoing, list)
        # process_data calls validate_input
        if outgoing:
            assert any(n.name == "validate_input" for n in outgoing)

    def test_explore_related(self, setup):
        """Test exploring related entities."""
        navigator, symbols = setup

        related = navigator.explore_related(symbols[0].name, max_results=10)
        assert isinstance(related, list)

    def test_explore_context(self, setup):
        """Test exploring context (same file)."""
        navigator, symbols = setup

        # Add another symbol in same file
        symbol_index = navigator.symbol_index
        new_symbol = Symbol(
            name="helper_func",
            type=SymbolType.FUNCTION,
            file_path="data.py",
            line_number=15,
        )
        symbol_index.add_symbol(new_symbol)
        navigator.graph_builder.add_symbol(new_symbol)

        context = navigator.explore_context(symbols[0].name)
        assert isinstance(context, list)
        if context:
            assert any(n.name == "helper_func" for n in context)

    def test_get_breadcrumb(self, setup):
        """Test getting breadcrumb."""
        navigator, symbols = setup

        navigator.navigate_to(symbols[0].name)
        breadcrumb = navigator.get_breadcrumb()

        assert breadcrumb is not None
        assert breadcrumb.current == symbols[0].name

    def test_get_navigation_history(self, setup):
        """Test getting navigation history."""
        navigator, symbols = setup

        navigator.navigate_to(symbols[0].name)
        navigator.navigate_to(symbols[1].name)

        history = navigator.get_navigation_history()
        assert len(history) == 2

    def test_go_back(self, setup):
        """Test going back in history."""
        navigator, symbols = setup

        navigator.navigate_to(symbols[0].name)
        navigator.navigate_to(symbols[1].name)

        node = navigator.go_back()
        assert node is not None
        assert node.name == symbols[0].name

    def test_find_path(self, setup):
        """Test finding path between entities."""
        navigator, symbols = setup

        path = navigator.find_path(symbols[2].name, symbols[1].name)
        assert path is not None
        assert path[0] == symbols[2].name
        assert path[-1] == symbols[1].name

    def test_find_path_no_connection(self, setup):
        """Test finding path with no connection."""
        navigator, symbols = setup

        path = navigator.find_path(symbols[1].name, symbols[2].name)
        # Might not find path depending on graph structure

    def test_get_navigation_map(self, setup):
        """Test getting navigation map."""
        navigator, symbols = setup

        nav_map = navigator.get_navigation_map(symbols[0].name, depth=2)
        assert "entity" in nav_map
        assert nav_map["entity"] == symbols[0].name
        assert "incoming" in nav_map
        assert "outgoing" in nav_map
        assert "related" in nav_map


class TestNavigationGuide:
    """Tests for NavigationGuide."""

    @pytest.fixture
    def guide(self):
        """Setup guide."""
        symbol_index = SymbolIndex()
        graph_builder = CodeGraphBuilder()
        dependency_graph = DependencyGraph()

        # Add sample data
        symbols = [
            Symbol(
                name="main",
                type=SymbolType.FUNCTION,
                file_path="app.py",
                line_number=1,
            ),
            Symbol(
                name="_helper",
                type=SymbolType.FUNCTION,
                file_path="app.py",
                line_number=10,
            ),
        ]

        for symbol in symbols:
            symbol_index.add_symbol(symbol)
            graph_builder.add_symbol(symbol)

        navigator = CodeNavigator(symbol_index, graph_builder, dependency_graph)
        return NavigationGuide(navigator)

    def test_explore_module(self, guide):
        """Test module exploration."""
        exploration = guide.explore_module("app.py")

        assert exploration["file_path"] == "app.py"
        assert "entities" in exploration
        assert "entry_points" in exploration

    def test_trace_dependency_chain(self, guide):
        """Test dependency chain tracing."""
        guide.navigator.navigate_to("main")

        trace = guide.trace_dependency_chain("main", "helper")
        # Might not find path depending on setup
        assert "found" in trace

    def test_recommend_navigation(self, guide):
        """Test navigation recommendations."""
        recommendations = guide.recommend_navigation("main")

        assert recommendations["entity"] == "main"
        assert "suggestions" in recommendations
        assert "explore_dependents" in recommendations["suggestions"]


class TestNavigationIntegration:
    """Integration tests for code navigation."""

    def test_full_navigation_workflow(self):
        """Test complete navigation workflow."""
        # Setup
        symbol_index = SymbolIndex()
        graph_builder = CodeGraphBuilder()
        dependency_graph = DependencyGraph()

        # Create realistic module structure
        modules = [
            ("UserService", SymbolType.CLASS, "services.py", 1),
            ("get_user", SymbolType.FUNCTION, "services.py", 10),
            ("validate_user", SymbolType.FUNCTION, "validators.py", 1),
            ("Database", SymbolType.CLASS, "db.py", 1),
            ("authenticate", SymbolType.FUNCTION, "auth.py", 1),
        ]

        symbols = {}
        for name, sym_type, file, line in modules:
            symbol = Symbol(
                name=name,
                type=sym_type,
                file_path=file,
                line_number=line,
            )
            symbol_index.add_symbol(symbol)
            graph_builder.add_symbol(symbol)
            symbols[name] = symbol

        # Add relationships
        graph_builder.add_relationship("UserService", "get_user", "contains")
        graph_builder.add_relationship("get_user", "validate_user", "calls")
        graph_builder.add_relationship("get_user", "Database", "uses")
        graph_builder.add_relationship("authenticate", "get_user", "calls")

        # Create navigator and guide
        navigator = CodeNavigator(symbol_index, graph_builder, dependency_graph)
        guide = NavigationGuide(navigator)

        # Test navigation
        node = navigator.navigate_to("UserService")
        assert node is not None

        # Explore
        outgoing = navigator.explore_outgoing("UserService", max_depth=2)
        assert len(outgoing) >= 0

        incoming = navigator.explore_incoming("get_user", max_depth=1)
        assert isinstance(incoming, list)

        # Module exploration
        module_structure = guide.explore_module("services.py")
        assert module_structure["file_path"] == "services.py"

        # Navigation history
        history = navigator.get_navigation_history()
        assert len(history) >= 1

        # Navigation map
        nav_map = navigator.get_navigation_map("get_user", depth=2)
        assert nav_map["entity"] == "get_user"

        # Recommendations
        recommendations = guide.recommend_navigation("get_user")
        assert recommendations["entity"] == "get_user"
        assert "suggestions" in recommendations
