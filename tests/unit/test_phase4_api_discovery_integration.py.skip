"""Tests for API discovery integration with MemoryAPI."""

import pytest

from athena.mcp.memory_api import MemoryAPI


class TestMemoryAPIDiscoveryIntegration:
    """Tests for API discovery integration with MemoryAPI."""

    @pytest.fixture
    def api(self, tmp_path):
        """Create a test MemoryAPI instance."""
        db_path = tmp_path / "test.db"
        return MemoryAPI.create(db_path=str(db_path))

    def test_memory_api_discovers_apis(self, api):
        """Test that MemoryAPI can discover available APIs."""
        # Should not raise an error
        categories = api.list_api_categories()
        assert isinstance(categories, list)

    def test_discover_apis_returns_dict(self, api):
        """Test that discover_apis returns proper structure."""
        apis = api.discover_apis()

        assert isinstance(apis, dict)
        # Should have some categories
        for category, specs in apis.items():
            assert isinstance(specs, list)
            for spec in specs:
                assert "name" in spec
                assert "module" in spec
                assert "category" in spec

    def test_discover_apis_with_category_filter(self, api):
        """Test discover_apis with category filter."""
        apis = api.discover_apis()

        if apis:
            # Pick first category
            category = list(apis.keys())[0]
            filtered = api.discover_apis(category=category)

            assert category in filtered
            assert len(filtered) == 1

    def test_search_apis(self, api):
        """Test searching for APIs."""
        # Should not raise an error
        results = api.search_apis("api")
        assert isinstance(results, list)

    def test_search_apis_with_limit(self, api):
        """Test search_apis respects limit parameter."""
        results = api.search_apis("a", limit=2)
        assert len(results) <= 2

    def test_list_api_categories(self, api):
        """Test listing API categories."""
        categories = api.list_api_categories()
        assert isinstance(categories, list)

    def test_discovery_error_handling(self, api):
        """Test that discovery handles errors gracefully."""
        # Should not raise an error even if something goes wrong
        apis = api.discover_apis()
        assert isinstance(apis, dict)

        results = api.search_apis("test")
        assert isinstance(results, list)

        categories = api.list_api_categories()
        assert isinstance(categories, list)

    def test_get_api_spec_returns_none_for_invalid(self, api):
        """Test that get_api_spec returns None for invalid paths."""
        spec = api.get_api_spec("nonexistent/api")
        assert spec is None

    def test_get_api_documentation_returns_none_for_invalid(self, api):
        """Test that get_api_documentation returns None for invalid paths."""
        docs = api.get_api_documentation("nonexistent/api")
        assert docs is None

    def test_memory_api_has_discovery_methods(self, api):
        """Test that MemoryAPI has all discovery methods."""
        assert hasattr(api, "discover_apis")
        assert hasattr(api, "get_api_spec")
        assert hasattr(api, "get_api_documentation")
        assert hasattr(api, "search_apis")
        assert hasattr(api, "list_api_categories")

    def test_discovery_methods_are_callable(self, api):
        """Test that discovery methods are callable."""
        assert callable(api.discover_apis)
        assert callable(api.get_api_spec)
        assert callable(api.get_api_documentation)
        assert callable(api.search_apis)
        assert callable(api.list_api_categories)
