"""Performance benchmarks for Phase 1 APIs.

Measures latency targets:
- SandboxConfig creation/validation: <10ms
- APIRegistry discovery: <50ms
- API documentation generation: <500ms
- MemoryAPI operations: <100ms
"""

import pytest
import time
from athena.sandbox.config import SandboxConfig, SandboxMode
from athena.mcp.api_registry import APIRegistry
from athena.mcp.api_docs import APIDocumentationGenerator


class TestPhase1PerformanceBenchmarks:
    """Performance benchmarks for Phase 1 components."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup benchmarks."""
        self.iterations = 100

    def test_sandbox_config_creation_performance(self):
        """Benchmark SandboxConfig creation."""
        start = time.perf_counter()
        for _ in range(self.iterations):
            config = SandboxConfig()
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed * 1000) / self.iterations
        assert avg_ms < 5, f"SandboxConfig creation too slow: {avg_ms:.2f}ms"

    def test_sandbox_config_validation_performance(self):
        """Benchmark SandboxConfig validation."""
        config = SandboxConfig()

        start = time.perf_counter()
        for _ in range(self.iterations):
            is_valid, errors = config.validate()
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed * 1000) / self.iterations
        assert avg_ms < 5, f"Validation too slow: {avg_ms:.2f}ms"

    def test_sandbox_config_serialization_performance(self):
        """Benchmark SandboxConfig serialization to dict."""
        config = SandboxConfig()

        start = time.perf_counter()
        for _ in range(self.iterations):
            config_dict = config.to_dict()
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed * 1000) / self.iterations
        assert avg_ms < 5, f"Serialization too slow: {avg_ms:.2f}ms"

    def test_api_registry_creation_performance(self):
        """Benchmark APIRegistry creation."""
        start = time.perf_counter()
        for _ in range(10):  # Fewer iterations since registry is heavier
            registry = APIRegistry()
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed * 1000) / 10
        assert avg_ms < 100, f"Registry creation too slow: {avg_ms:.2f}ms"

    def test_api_registry_discovery_performance(self):
        """Benchmark APIRegistry API discovery."""
        registry = APIRegistry.create()

        start = time.perf_counter()
        for _ in range(self.iterations):
            apis = registry.discover_apis()
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed * 1000) / self.iterations
        assert avg_ms < 10, f"Discovery too slow: {avg_ms:.2f}ms"

    def test_api_registry_get_api_performance(self):
        """Benchmark APIRegistry get_api()."""
        registry = APIRegistry.create()

        start = time.perf_counter()
        for _ in range(self.iterations):
            api = registry.get_api("remember")
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed * 1000) / self.iterations
        assert avg_ms < 2, f"Get API too slow: {avg_ms:.2f}ms"

    def test_api_documentation_markdown_generation_performance(self):
        """Benchmark Markdown documentation generation."""
        registry = APIRegistry.create()
        generator = APIDocumentationGenerator(registry)

        start = time.perf_counter()
        for _ in range(10):  # Fewer iterations since generation is heavier
            markdown = generator.generate_markdown()
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed * 1000) / 10
        assert avg_ms < 500, f"Markdown generation too slow: {avg_ms:.2f}ms"

    def test_api_documentation_json_generation_performance(self):
        """Benchmark JSON documentation generation."""
        registry = APIRegistry.create()
        generator = APIDocumentationGenerator(registry)

        start = time.perf_counter()
        for _ in range(10):
            json_doc = generator.generate_json()
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed * 1000) / 10
        assert avg_ms < 300, f"JSON generation too slow: {avg_ms:.2f}ms"

    def test_api_documentation_html_generation_performance(self):
        """Benchmark HTML documentation generation."""
        registry = APIRegistry.create()
        generator = APIDocumentationGenerator(registry)

        start = time.perf_counter()
        for _ in range(10):
            html = generator.generate_html()
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed * 1000) / 10
        assert avg_ms < 500, f"HTML generation too slow: {avg_ms:.2f}ms"

    def test_sandbox_config_factory_methods_performance(self):
        """Benchmark SandboxConfig factory methods."""
        start = time.perf_counter()
        for _ in range(self.iterations):
            strict = SandboxConfig.strict()
            permissive = SandboxConfig.permissive()
            default = SandboxConfig.default()
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed * 1000) / self.iterations
        assert avg_ms < 10, f"Factory methods too slow: {avg_ms:.2f}ms"

    def test_api_registry_to_dict_performance(self):
        """Benchmark APIRegistry serialization."""
        registry = APIRegistry.create()

        start = time.perf_counter()
        for _ in range(10):
            registry_dict = registry.to_dict()
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed * 1000) / 10
        assert avg_ms < 100, f"Registry to_dict too slow: {avg_ms:.2f}ms"


class TestPhase1PerformanceMetrics:
    """Collect and report performance metrics."""

    def test_collect_phase1_metrics(self, benchmark):
        """Collect comprehensive performance metrics."""
        registry = APIRegistry.create()

        metrics = {
            "config_creation": benchmark(SandboxConfig),
            "config_validation": benchmark(lambda: SandboxConfig().validate()),
            "config_to_dict": benchmark(lambda: SandboxConfig().to_dict()),
            "registry_creation": benchmark(APIRegistry),
            "registry_discovery": benchmark(lambda: registry.discover_apis()),
            "registry_to_dict": benchmark(lambda: registry.to_dict()),
        }

        # All metrics should be under 500ms
        for metric_name, duration in metrics.items():
            # Duration is in seconds, convert to ms
            ms = duration * 1000
            assert ms < 500, f"{metric_name}: {ms:.2f}ms exceeds threshold"
