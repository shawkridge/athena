"""Tests for Phase 4 API discovery system."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
import sys

from athena.api.discovery import APIDiscovery
from athena.api.models import APISpec, APIParameter, APIExample


class TestAPIModels:
    """Tests for API specification models."""

    def test_api_parameter_creation(self):
        """Test APIParameter creation."""
        param = APIParameter(
            name="query",
            type="str",
            description="Search query",
            required=True,
        )

        assert param.name == "query"
        assert param.type == "str"
        assert param.required is True

    def test_api_parameter_to_dict(self):
        """Test APIParameter.to_dict()."""
        param = APIParameter(
            name="limit",
            type="int",
            default=10,
            description="Result limit",
            required=False,
        )

        param_dict = param.to_dict()
        assert param_dict["name"] == "limit"
        assert param_dict["type"] == "int"
        assert param_dict["required"] is False
        assert "default" in param_dict

    def test_api_example_creation(self):
        """Test APIExample creation."""
        example = APIExample(
            description="Simple search",
            code='api.search("query")',
            expected_output="[result1, result2]",
        )

        assert example.description == "Simple search"
        assert example.code == 'api.search("query")'

    def test_api_spec_creation(self):
        """Test APISpec creation."""
        spec = APISpec(
            name="search",
            module="athena.api.memory",
            signature="def search(query: str) -> List[str]",
            docstring="Search for items",
            parameters=[
                APIParameter(
                    name="query",
                    type="str",
                    description="Search query",
                    required=True,
                )
            ],
            return_type="List[str]",
            examples=[],
            category="memory",
        )

        assert spec.name == "search"
        assert spec.category == "memory"
        assert len(spec.parameters) == 1

    def test_api_spec_to_markdown(self):
        """Test APISpec.to_markdown()."""
        spec = APISpec(
            name="recall",
            module="athena.api.memory",
            signature="def recall(query: str) -> List[Dict]",
            docstring="Recall memories matching query",
            parameters=[
                APIParameter(
                    name="query",
                    type="str",
                    description="Query string",
                    required=True,
                )
            ],
            return_type="List[Dict]",
            examples=[
                APIExample(
                    description="Simple recall",
                    code='result = api.recall("test")',
                )
            ],
            category="memory",
        )

        markdown = spec.to_markdown()
        assert "## recall" in markdown
        assert "Recall memories matching query" in markdown
        assert "def recall(query: str) -> List[Dict]" in markdown
        assert "query" in markdown
        assert "Simple recall" in markdown

    def test_api_spec_to_dict(self):
        """Test APISpec.to_dict()."""
        spec = APISpec(
            name="remember",
            module="athena.api.memory",
            signature="def remember(data: Dict) -> bool",
            docstring="Remember a fact",
            parameters=[],
            return_type="bool",
            examples=[],
            category="memory",
            version="1.0.0",
        )

        spec_dict = spec.to_dict()
        assert spec_dict["name"] == "remember"
        assert spec_dict["module"] == "athena.api.memory"
        assert spec_dict["version"] == "1.0.0"
        assert isinstance(spec_dict["parameters"], list)

    def test_api_spec_to_compact_dict(self):
        """Test APISpec.to_compact_dict()."""
        spec = APISpec(
            name="test_api",
            module="test.module",
            signature="def test_api(param: str) -> str",
            docstring="Test documentation",
            parameters=[
                APIParameter(name="param", type="str", required=True)
            ],
            return_type="str",
            examples=[
                APIExample(description="Example", code="code"),
            ],
            category="test",
        )

        compact = spec.to_compact_dict()
        assert "examples" not in compact  # Not in compact version
        assert compact["name"] == "test_api"
        assert compact["category"] == "test"


class TestAPIDiscovery:
    """Tests for APIDiscovery system."""

    @pytest.fixture
    def temp_api_dir(self):
        """Create temporary API directory structure."""
        with TemporaryDirectory() as tmpdir:
            api_dir = Path(tmpdir) / "api"
            api_dir.mkdir()

            # Create memory category
            memory_dir = api_dir / "memory"
            memory_dir.mkdir()

            # Create recall.py module
            recall_module = memory_dir / "recall.py"
            recall_module.write_text("""
def recall_semantic(query: str) -> list:
    \"\"\"Recall semantic memories matching query.

    Args:
        query: Search query string

    Returns:
        List of matching memories
    \"\"\"
    return []

def recall_episodic(session_id: str) -> list:
    \"\"\"Recall episodic events from session.

    Args:
        session_id: Session identifier

    Returns:
        List of events
    \"\"\"
    return []
""")

            # Create remember.py module
            remember_module = memory_dir / "remember.py"
            remember_module.write_text("""
def remember_semantic(fact: dict) -> bool:
    \"\"\"Remember a semantic fact.

    Args:
        fact: Fact to remember

    Returns:
        Success indicator
    \"\"\"
    return True
""")

            # Create graph category
            graph_dir = api_dir / "graph"
            graph_dir.mkdir()

            entities_module = graph_dir / "entities.py"
            entities_module.write_text("""
def get_entities(limit: int = 10) -> list:
    \"\"\"Get all entities in knowledge graph.

    Args:
        limit: Maximum number of entities to return (default: 10)

    Returns:
        List of entities
    \"\"\"
    return []
""")

            yield api_dir

    def test_discovery_initialization(self, temp_api_dir):
        """Test APIDiscovery initialization."""
        discovery = APIDiscovery(str(temp_api_dir))
        assert discovery.api_root == temp_api_dir

    def test_discover_all_categories(self, temp_api_dir):
        """Test discovering all API categories."""
        discovery = APIDiscovery(str(temp_api_dir))
        apis = discovery.discover_all()

        assert "memory" in apis
        assert "graph" in apis
        assert isinstance(apis["memory"], list)
        assert isinstance(apis["graph"], list)

    def test_discover_all_caches_results(self, temp_api_dir):
        """Test that discover_all() caches results."""
        discovery = APIDiscovery(str(temp_api_dir))

        # First call
        apis1 = discovery.discover_all(use_cache=True)

        # Modify directory (shouldn't be discovered)
        (temp_api_dir / "new_category").mkdir(exist_ok=True)

        # Second call should return cached results
        apis2 = discovery.discover_all(use_cache=True)

        assert apis1 == apis2
        assert "new_category" not in apis2

    def test_discover_specific_category(self, temp_api_dir):
        """Test discovering APIs in specific category."""
        discovery = APIDiscovery(str(temp_api_dir))
        memory_apis = discovery.get_apis_by_category("memory")

        assert len(memory_apis) >= 3  # recall_semantic, recall_episodic, remember_semantic
        assert any(api.name == "recall_semantic" for api in memory_apis)
        assert any(api.name == "remember_semantic" for api in memory_apis)

    def test_get_specific_api(self, temp_api_dir):
        """Test getting specific API by path."""
        discovery = APIDiscovery(str(temp_api_dir))
        api = discovery.get_api("memory/recall_semantic")

        assert api is not None
        assert api.name == "recall_semantic"
        assert api.category == "memory"

    def test_get_nonexistent_api(self, temp_api_dir):
        """Test getting non-existent API."""
        discovery = APIDiscovery(str(temp_api_dir))
        api = discovery.get_api("nonexistent/api")

        assert api is None

    def test_search_apis_by_name(self, temp_api_dir):
        """Test searching APIs by name."""
        discovery = APIDiscovery(str(temp_api_dir))
        results = discovery.search_apis("recall")

        assert len(results) > 0
        assert all("recall" in api.name.lower() for api in results)

    def test_search_apis_by_docstring(self, temp_api_dir):
        """Test searching APIs by docstring."""
        discovery = APIDiscovery(str(temp_api_dir))
        results = discovery.search_apis("semantic")

        assert len(results) > 0
        assert any("recall_semantic" in api.name for api in results)

    def test_search_apis_limit(self, temp_api_dir):
        """Test search limit parameter."""
        discovery = APIDiscovery(str(temp_api_dir))
        results = discovery.search_apis("a", limit=2)

        assert len(results) <= 2

    def test_get_api_categories(self, temp_api_dir):
        """Test getting all categories."""
        discovery = APIDiscovery(str(temp_api_dir))
        categories = discovery.get_api_categories()

        assert "memory" in categories
        assert "graph" in categories

    def test_clear_cache(self, temp_api_dir):
        """Test clearing discovery cache."""
        discovery = APIDiscovery(str(temp_api_dir))

        # Populate cache
        discovery.discover_all()
        assert discovery._cache

        # Clear cache
        discovery.clear_cache()
        assert not discovery._cache
        assert discovery._all_apis_cache is None

    def test_api_spec_extraction(self, temp_api_dir):
        """Test API spec extraction from function."""
        discovery = APIDiscovery(str(temp_api_dir))
        api = discovery.get_api("memory/recall_semantic")

        assert api is not None
        assert api.name == "recall_semantic"
        assert len(api.parameters) == 1
        assert api.parameters[0].name == "query"
        assert api.parameters[0].type == "str"
        assert api.parameters[0].required is True

    def test_api_with_default_parameters(self, temp_api_dir):
        """Test API with default parameters."""
        discovery = APIDiscovery(str(temp_api_dir))
        api = discovery.get_api("graph/get_entities")

        assert api is not None
        assert len(api.parameters) == 1
        assert api.parameters[0].name == "limit"
        assert api.parameters[0].required is False
        assert api.parameters[0].default == 10

    def test_invalid_api_path_format(self, temp_api_dir):
        """Test invalid API path format."""
        discovery = APIDiscovery(str(temp_api_dir))

        assert discovery.get_api("invalid") is None
        assert discovery.get_api("category/api/extra") is None

    def test_empty_api_directory(self):
        """Test discovery with empty directory."""
        with TemporaryDirectory() as tmpdir:
            discovery = APIDiscovery(tmpdir)
            apis = discovery.discover_all()

            assert apis == {}

    def test_nonexistent_directory(self):
        """Test discovery with nonexistent directory."""
        discovery = APIDiscovery("/nonexistent/path/that/does/not/exist")
        apis = discovery.discover_all()

        assert apis == {}

    def test_api_parameter_extraction(self, temp_api_dir):
        """Test parameter extraction from function signature."""
        discovery = APIDiscovery(str(temp_api_dir))
        api = discovery.get_api("memory/recall_episodic")

        assert api is not None
        assert len(api.parameters) == 1
        param = api.parameters[0]
        assert param.name == "session_id"
        assert param.type == "str"


class TestAPIDiscoveryIntegration:
    """Integration tests for API discovery."""

    @pytest.fixture
    def discovery_with_samples(self, tmp_path):
        """Create discovery with sample APIs."""
        api_dir = tmp_path / "api"
        api_dir.mkdir()

        # Create sample category
        sample_dir = api_dir / "samples"
        sample_dir.mkdir()

        sample_file = sample_dir / "utils.py"
        sample_file.write_text("""
def count_items(items: list) -> int:
    \"\"\"Count items in list.

    Args:
        items: List to count

    Returns:
        Number of items
    \"\"\"
    return len(items)

def filter_items(items: list, predicate: callable) -> list:
    \"\"\"Filter items based on predicate.

    Args:
        items: Items to filter
        predicate: Filter function

    Returns:
        Filtered items
    \"\"\"
    return [item for item in items if predicate(item)]
""")

        discovery = APIDiscovery(str(api_dir))
        return discovery, api_dir

    def test_discover_all_returns_organized_structure(self, discovery_with_samples):
        """Test that discover_all returns properly organized APIs."""
        discovery, _ = discovery_with_samples
        apis = discovery.discover_all()

        assert "samples" in apis
        assert len(apis["samples"]) == 2

    def test_api_specs_have_all_fields(self, discovery_with_samples):
        """Test that extracted API specs have all required fields."""
        discovery, _ = discovery_with_samples
        api = discovery.get_api("samples/count_items")

        assert api is not None
        assert api.name
        assert api.module
        assert api.signature
        assert api.docstring
        assert isinstance(api.parameters, list)
        assert api.return_type
        assert isinstance(api.examples, list)
        assert api.category

    def test_multiple_searches_consistent(self, discovery_with_samples):
        """Test that multiple searches return consistent results."""
        discovery, _ = discovery_with_samples

        results1 = discovery.search_apis("count")
        results2 = discovery.search_apis("count")

        assert len(results1) == len(results2)
        assert results1[0].name == results2[0].name

    def test_discovery_preserves_docstring(self, discovery_with_samples):
        """Test that discovery preserves function docstrings."""
        discovery, _ = discovery_with_samples
        api = discovery.get_api("samples/filter_items")

        assert api is not None
        assert "Filter items based on predicate" in api.docstring
