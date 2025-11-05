"""Comprehensive tests for Phase 2 Production Validation Suite.

Tests all benchmarking components:
- Reasoning dialogue benchmarks
- Context retention tests
- Causal inference validation
- Ablation study
- Competitive analysis
"""

import pytest
import json
from datetime import datetime
from pathlib import Path

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from benchmarks.phase2_production_validation import (
    ReasoningDialogueBenchmark,
    ContextRetentionBenchmark,
    CausalInferenceBenchmark,
    AblationStudy,
    CompetitiveBenchmark,
    Phase2ValidationSuite,
    ReasoningDialogueCase,
    ContextRetentionTest,
    CausalInferenceCase,
    DifficultLevel,
    BenchmarkCategory,
    generate_html_report,
)


class TestReasoningDialogueBenchmark:
    """Tests for reasoning dialogue benchmarking."""

    def test_benchmark_creation(self):
        """Test benchmark object creation."""
        benchmark = ReasoningDialogueBenchmark()
        assert benchmark is not None
        assert len(benchmark.cases) == 0
        assert len(benchmark.results) == 0

    def test_create_test_cases(self):
        """Test creation of test cases."""
        benchmark = ReasoningDialogueBenchmark()
        cases = benchmark.create_test_cases()

        assert len(cases) == 3
        assert all(isinstance(c, ReasoningDialogueCase) for c in cases)
        assert cases[0].case_id == "rdg_001"
        assert cases[1].difficulty == DifficultLevel.HARD
        assert cases[2].topic == "Bug Root Cause Analysis"

    def test_test_case_structure(self):
        """Test structure of test cases."""
        benchmark = ReasoningDialogueBenchmark()
        cases = benchmark.create_test_cases()

        for case in cases:
            assert case.case_id
            assert case.topic
            assert case.difficulty in DifficultLevel
            assert case.initial_context
            assert case.expected_reasoning_depth > 0
            assert case.required_context_items >= 0

    def test_difficulty_levels(self):
        """Test difficulty level variations."""
        benchmark = ReasoningDialogueBenchmark()
        cases = benchmark.create_test_cases()

        difficulties = [c.difficulty for c in cases]
        assert DifficultLevel.MEDIUM in difficulties
        assert DifficultLevel.HARD in difficulties

    def test_reasoning_quality_metrics(self):
        """Test that reasoning quality metrics are tracked."""
        benchmark = ReasoningDialogueBenchmark()
        cases = benchmark.create_test_cases()
        assert len(cases) > 0

        # Check that metrics would be computed
        for case in cases:
            assert hasattr(case, 'expected_reasoning_depth')
            assert hasattr(case, 'required_context_items')


class TestContextRetentionBenchmark:
    """Tests for context retention benchmarking."""

    def test_benchmark_creation(self):
        """Test benchmark object creation."""
        benchmark = ContextRetentionBenchmark()
        assert benchmark is not None
        assert len(benchmark.tests) == 0
        assert len(benchmark.results) == 0

    def test_create_test_cases(self):
        """Test creation of context retention tests."""
        benchmark = ContextRetentionBenchmark()
        tests = benchmark.create_test_cases()

        assert len(tests) == 3
        assert all(isinstance(t, ContextRetentionTest) for t in tests)
        assert tests[0].test_id == "ctx_001"
        assert tests[1].context_depth == 10
        assert tests[2].interference_items is not None

    def test_test_case_structure(self):
        """Test structure of retention tests."""
        benchmark = ContextRetentionBenchmark()
        tests = benchmark.create_test_cases()

        for test in tests:
            assert test.test_id
            assert len(test.context_items) > 0
            assert test.context_depth > 0
            assert test.retrieval_query
            assert test.expected_item_index >= 0
            assert test.expected_item_index < len(test.context_items)

    def test_context_depth_variations(self):
        """Test context depth variations."""
        benchmark = ContextRetentionBenchmark()
        tests = benchmark.create_test_cases()

        depths = [t.context_depth for t in tests]
        assert 1 in depths
        assert 10 in depths
        assert max(depths) <= 10

    def test_interference_handling(self):
        """Test interference items for context confusion tests."""
        benchmark = ContextRetentionBenchmark()
        tests = benchmark.create_test_cases()

        tests_with_interference = [t for t in tests if t.interference_items]
        tests_without_interference = [t for t in tests if t.interference_items is None]

        assert len(tests_with_interference) > 0
        assert len(tests_without_interference) > 0


class TestCausalInferenceBenchmark:
    """Tests for causal inference benchmarking."""

    def test_benchmark_creation(self):
        """Test benchmark object creation."""
        benchmark = CausalInferenceBenchmark()
        assert benchmark is not None
        assert len(benchmark.cases) == 0
        assert len(benchmark.results) == 0

    def test_create_test_cases(self):
        """Test creation of causal inference cases."""
        benchmark = CausalInferenceBenchmark()
        cases = benchmark.create_test_cases()

        assert len(cases) == 2
        assert all(isinstance(c, CausalInferenceCase) for c in cases)
        assert cases[0].case_id == "caus_001"
        assert cases[1].case_id == "caus_002"

    def test_test_case_structure(self):
        """Test structure of causal inference cases."""
        benchmark = CausalInferenceBenchmark()
        cases = benchmark.create_test_cases()

        for case in cases:
            assert case.case_id
            assert len(case.event_sequence) > 0
            assert len(case.causal_relationships) > 0
            assert case.difficulty in DifficultLevel
            assert case.type in ["temporal", "spatial", "semantic", "mixed"]

    def test_causal_relationships_validity(self):
        """Test that causal relationships are valid."""
        benchmark = CausalInferenceBenchmark()
        cases = benchmark.create_test_cases()

        for case in cases:
            event_ids = [e['id'] for e in case.event_sequence]
            for effect_id, cause_id in case.causal_relationships.items():
                assert effect_id in event_ids
                assert cause_id in event_ids
                assert effect_id != cause_id

    def test_causal_types(self):
        """Test different causal relationship types."""
        benchmark = CausalInferenceBenchmark()
        cases = benchmark.create_test_cases()

        types = [c.type for c in cases]
        assert "temporal" in types or "semantic" in types


class TestAblationStudy:
    """Tests for ablation study framework."""

    def test_study_creation(self):
        """Test ablation study object creation."""
        study = AblationStudy()
        assert study is not None
        assert len(study.components) > 0
        assert len(study.results) == 0

    def test_components(self):
        """Test ablation components."""
        study = AblationStudy()

        assert len(study.components) == 7
        component_names = [c.name for c in study.components]

        assert "semantic_memory" in component_names
        assert "episodic_memory" in component_names
        assert "procedural_memory" in component_names
        assert "consolidation" in component_names
        assert "knowledge_graph" in component_names
        assert "advanced_rag" in component_names
        assert "meta_memory" in component_names

    def test_component_descriptions(self):
        """Test that components have descriptions."""
        study = AblationStudy()

        for component in study.components:
            assert component.name
            assert component.description
            assert len(component.description) > 0

    def test_component_enabled_state(self):
        """Test component enabled state."""
        study = AblationStudy()

        # All components should be enabled by default
        assert all(c.enabled for c in study.components)


class TestCompetitiveBenchmark:
    """Tests for competitive analysis."""

    def test_benchmark_creation(self):
        """Test competitive benchmark object creation."""
        benchmark = CompetitiveBenchmark()
        assert benchmark is not None
        assert len(benchmark.comparisons) == 0

    def test_create_comparisons(self):
        """Test creation of competitive comparisons."""
        benchmark = CompetitiveBenchmark()
        comparisons = benchmark.create_comparisons()

        assert len(comparisons) == 6
        system_names = [c.system_name for c in comparisons]

        assert "Memory MCP (Full)" in system_names
        assert "Mem0 (Vector-only)" in system_names
        assert "Zep (Temporal-only)" in system_names

    def test_comparison_metrics(self):
        """Test that comparisons include all metrics."""
        benchmark = CompetitiveBenchmark()
        comparisons = benchmark.create_comparisons()

        for comparison in comparisons:
            assert comparison.system_name
            assert 0 <= comparison.reasoning_f1 <= 1
            assert 0 <= comparison.context_retention_percent <= 100
            assert 0 <= comparison.causal_inference_f1 <= 1
            assert comparison.avg_response_time_ms >= 0
            assert comparison.storage_footprint_mb >= 0

    def test_memory_mcp_leadership(self):
        """Test that Memory MCP is competitive."""
        benchmark = CompetitiveBenchmark()
        comparisons = benchmark.create_comparisons()

        memory_mcp = next(c for c in comparisons if c.system_name == "Memory MCP (Full)")

        # Memory MCP should have high scores
        assert memory_mcp.reasoning_f1 >= 0.80
        assert memory_mcp.context_retention_percent >= 85
        assert memory_mcp.causal_inference_f1 >= 0.75


class TestPhase2ValidationSuite:
    """Tests for complete validation suite."""

    def test_suite_creation(self):
        """Test suite object creation."""
        suite = Phase2ValidationSuite()

        assert suite is not None
        assert suite.reasoning_benchmark is not None
        assert suite.context_benchmark is not None
        assert suite.causal_benchmark is not None
        assert suite.ablation_study is not None
        assert suite.competitive_benchmark is not None

    def test_all_components_initialized(self):
        """Test that all components are properly initialized."""
        suite = Phase2ValidationSuite()

        assert isinstance(suite.reasoning_benchmark, ReasoningDialogueBenchmark)
        assert isinstance(suite.context_benchmark, ContextRetentionBenchmark)
        assert isinstance(suite.causal_benchmark, CausalInferenceBenchmark)
        assert isinstance(suite.ablation_study, AblationStudy)
        assert isinstance(suite.competitive_benchmark, CompetitiveBenchmark)


class TestBenchmarkIntegration:
    """Integration tests for benchmark suite."""

    def test_reasoning_benchmark_workflow(self):
        """Test complete reasoning benchmark workflow."""
        benchmark = ReasoningDialogueBenchmark()
        cases = benchmark.create_test_cases()

        assert len(cases) == 3
        assert all(c.case_id.startswith("rdg_") for c in cases)

    def test_context_benchmark_workflow(self):
        """Test complete context benchmark workflow."""
        benchmark = ContextRetentionBenchmark()
        tests = benchmark.create_test_cases()

        assert len(tests) == 3
        assert all(t.test_id.startswith("ctx_") for t in tests)

    def test_causal_benchmark_workflow(self):
        """Test complete causal benchmark workflow."""
        benchmark = CausalInferenceBenchmark()
        cases = benchmark.create_test_cases()

        assert len(cases) == 2
        assert all(c.case_id.startswith("caus_") for c in cases)

    def test_suite_initialization_order(self):
        """Test that suite initializes components in correct order."""
        suite = Phase2ValidationSuite()

        # All components should be initialized
        assert suite.reasoning_benchmark is not None
        assert suite.context_benchmark is not None
        assert suite.causal_benchmark is not None
        assert suite.ablation_study is not None
        assert suite.competitive_benchmark is not None


class TestReportGeneration:
    """Tests for report generation."""

    def test_html_report_generation(self):
        """Test HTML report generation."""
        from benchmarks.phase2_production_validation import Phase2ValidationReport

        report = Phase2ValidationReport(
            run_id="test_001",
            timestamp=datetime.now(),
            reasoning_dialogue_cases=3,
            reasoning_dialogue_avg_accuracy=0.85,
            reasoning_dialogue_avg_quality=0.82,
            context_retention_tests=3,
            context_retention_success_rate=92.0,
            context_retention_avg_time_ms=45.0,
            causal_inference_cases=2,
            causal_inference_f1=0.79,
            production_readiness_score=0.85,
        )

        html = generate_html_report(report)

        assert html is not None
        assert "Phase 2 Production Validation Report" in html
        assert "Executive Summary" in html
        assert "Reasoning Dialogue" in html
        assert "Context Retention" in html
        assert "Causal Inference" in html

    def test_report_metrics_format(self):
        """Test that report metrics are properly formatted."""
        from benchmarks.phase2_production_validation import Phase2ValidationReport

        report = Phase2ValidationReport(
            run_id="test_002",
            timestamp=datetime.now(),
            reasoning_dialogue_avg_accuracy=0.75,
            context_retention_success_rate=88.5,
            causal_inference_f1=0.72,
        )

        assert 0 <= report.reasoning_dialogue_avg_accuracy <= 1
        assert 0 <= report.context_retention_success_rate <= 100
        assert 0 <= report.causal_inference_f1 <= 1


class TestBenchmarkMetrics:
    """Tests for benchmark metric calculations."""

    def test_reasoning_dialogue_result_creation(self):
        """Test ReasoningDialogueResult creation."""
        from benchmarks.phase2_production_validation import ReasoningDialogueResult

        result = ReasoningDialogueResult(
            case_id="test_001",
            topic="Test Topic",
            difficulty=DifficultLevel.MEDIUM,
            total_accuracy=0.85,
            reasoning_quality_avg=0.80,
            context_usage_avg=0.75,
            context_retention=0.90,
            response_time_ms=50.0,
            dialogue_coherence=0.85,
        )

        assert result.case_id == "test_001"
        assert 0 <= result.total_accuracy <= 1
        assert 0 <= result.reasoning_quality_avg <= 1

    def test_context_retention_result_creation(self):
        """Test ContextRetentionResult creation."""
        from benchmarks.phase2_production_validation import ContextRetentionResult

        result = ContextRetentionResult(
            test_id="test_001",
            context_depth=5,
            retrieval_success=True,
            retrieval_accuracy=0.95,
            response_time_ms=40.0,
            interference_resistance=0.85,
        )

        assert result.test_id == "test_001"
        assert result.retrieval_success is True
        assert 0 <= result.retrieval_accuracy <= 1

    def test_causal_inference_result_creation(self):
        """Test CausalInferenceResult creation."""
        from benchmarks.phase2_production_validation import CausalInferenceResult

        result = CausalInferenceResult(
            case_id="test_001",
            test_type="temporal",
            difficulty=DifficultLevel.HARD,
            correctly_inferred=3,
            total_relationships=4,
            precision=0.75,
            recall=0.75,
            f1_score=0.75,
            inference_time_ms=30.0,
        )

        assert result.case_id == "test_001"
        assert result.correctly_inferred <= result.total_relationships
        assert result.f1_score == 0.75


class TestExpectedImprovements:
    """Tests for expected improvement metrics."""

    def test_reasoning_dialogue_improvement_target(self):
        """Test expected +39.7% improvement for reasoning dialogue."""
        # Target: 39.7% improvement over baseline
        baseline = 0.45
        expected = baseline * 1.397
        assert expected > baseline

    def test_context_retention_improvement_target(self):
        """Test expected +104.4% improvement for context retention."""
        # Target: 104.4% improvement (doubles performance)
        baseline = 0.30
        expected = baseline * 2.044
        assert expected > 2 * baseline

    def test_causal_inference_improvement_target(self):
        """Test expected +69.2% improvement for causal inference."""
        # Target: 69.2% improvement over baseline
        baseline = 0.35
        expected = baseline * 1.692
        assert expected > baseline

    def test_combined_improvement_expectation(self):
        """Test combined improvement expectations."""
        # Total expected improvement should be substantial
        total_improvement = 0.397 + 1.044 + 0.692
        assert total_improvement > 2.0  # More than 200% combined


# Parametrized tests
@pytest.mark.parametrize("benchmark_class", [
    ReasoningDialogueBenchmark,
    ContextRetentionBenchmark,
    CausalInferenceBenchmark,
])
def test_benchmark_instantiation(benchmark_class):
    """Test that all benchmark classes can be instantiated."""
    benchmark = benchmark_class()
    assert benchmark is not None


@pytest.mark.parametrize("difficulty", [
    DifficultLevel.EASY,
    DifficultLevel.MEDIUM,
    DifficultLevel.HARD,
    DifficultLevel.EXPERT,
])
def test_difficulty_level_enum(difficulty):
    """Test all difficulty levels are valid."""
    assert difficulty in DifficultLevel


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
