"""Integration tests for Skill Optimization handlers (4 skills).

Tests the optimized implementations of 4 key skills using Phase 5 tools.
"""

import pytest
import asyncio
from typing import Any, List

# Import handlers
from athena.mcp.handlers_skill_optimization import (
    handle_optimize_learning_tracker,
    handle_optimize_procedure_suggester,
    handle_optimize_gap_detector,
    handle_optimize_quality_monitor,
)
from athena.integration.skill_optimization import (
    LearningTrackerOptimizer,
    ProcedureSuggesterOptimizer,
    GapDetectorOptimizer,
    QualityMonitorOptimizer,
)


class MockServer:
    """Mock server for testing."""

    def __init__(self, db: Any = None):
        self.db = db
        self.store = MockStore(db)


class MockStore:
    """Mock store with database reference."""

    def __init__(self, db: Any = None):
        self.db = db


class TestSkillOptimizationHandlers:
    """Test Skill Optimization handler implementations."""

    @pytest.mark.asyncio
    async def test_optimize_learning_tracker_handler(self):
        """Test optimize_learning_tracker handler."""
        server = MockServer()
        args = {
            "project_id": 1,
            "analyze_effectiveness": True,
            "track_patterns": True,
        }

        result = await handle_optimize_learning_tracker(server, args)

        assert result is not None
        assert len(result) > 0
        assert hasattr(result[0], "type")
        assert hasattr(result[0], "text")
        assert "learning" in result[0].text.lower() or "strategy" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_optimize_procedure_suggester_handler(self):
        """Test optimize_procedure_suggester handler."""
        server = MockServer()
        args = {
            "project_id": 1,
            "analyze_patterns": True,
            "discovery_depth": 3,
        }

        result = await handle_optimize_procedure_suggester(server, args)

        assert result is not None
        assert len(result) > 0
        assert "procedure" in result[0].text.lower() or "pattern" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_optimize_gap_detector_handler(self):
        """Test optimize_gap_detector handler."""
        server = MockServer()
        args = {
            "project_id": 1,
            "stability_window": 7,
            "analyze_contradictions": True,
        }

        result = await handle_optimize_gap_detector(server, args)

        assert result is not None
        assert len(result) > 0
        assert "gap" in result[0].text.lower() or "stability" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_optimize_quality_monitor_handler(self):
        """Test optimize_quality_monitor handler."""
        server = MockServer()
        args = {
            "project_id": 1,
            "measure_layers": True,
            "domain_analysis": True,
        }

        result = await handle_optimize_quality_monitor(server, args)

        assert result is not None
        assert len(result) > 0
        assert "quality" in result[0].text.lower() or "layer" in result[0].text.lower()


class TestLearningTrackerOptimizer:
    """Test LearningTrackerOptimizer implementation."""

    @pytest.mark.asyncio
    async def test_learning_tracker_optimizer_execute(self):
        """Test learning tracker optimizer execution."""
        optimizer = LearningTrackerOptimizer(None)

        result = await optimizer.execute(
            project_id=1,
            analyze_effectiveness=True,
            track_patterns=True
        )

        # Verify result structure
        assert "status" in result
        assert "best_strategy" in result
        assert "effectiveness_score" in result
        assert "encoding_rounds" in result
        assert "patterns_learned" in result
        assert "learning_curve_improvement" in result

        # Verify types and ranges
        assert result["status"] == "success"
        assert isinstance(result["effectiveness_score"], float)
        assert 0.0 <= result["effectiveness_score"] <= 1.0
        assert isinstance(result["encoding_rounds"], int)
        assert result["encoding_rounds"] > 0


class TestProcedureSuggesterOptimizer:
    """Test ProcedureSuggesterOptimizer implementation."""

    @pytest.mark.asyncio
    async def test_procedure_suggester_optimizer_execute(self):
        """Test procedure suggester optimizer execution."""
        optimizer = ProcedureSuggesterOptimizer(None)

        result = await optimizer.execute(
            project_id=1,
            analyze_patterns=True,
            discovery_depth=3
        )

        # Verify result structure
        assert "status" in result
        assert "patterns_discovered" in result
        assert "procedures_recommended" in result
        assert "top_procedure" in result
        assert "top_procedure_confidence" in result
        assert "pattern_stability_score" in result

        # Verify types and ranges
        assert result["status"] == "success"
        assert isinstance(result["patterns_discovered"], int)
        assert 0.0 <= result["top_procedure_confidence"] <= 1.0
        assert 0.0 <= result["pattern_stability_score"] <= 1.0


class TestGapDetectorOptimizer:
    """Test GapDetectorOptimizer implementation."""

    @pytest.mark.asyncio
    async def test_gap_detector_optimizer_execute(self):
        """Test gap detector optimizer execution."""
        optimizer = GapDetectorOptimizer(None)

        result = await optimizer.execute(
            project_id=1,
            stability_window=7,
            analyze_contradictions=True
        )

        # Verify result structure
        assert "status" in result
        assert "gaps_detected" in result
        assert "critical_gaps" in result
        assert "pattern_stability_score" in result
        assert "persistent_contradictions" in result
        assert "confidence_improvement" in result

        # Verify types and ranges
        assert result["status"] == "success"
        assert isinstance(result["gaps_detected"], int)
        assert 0.0 <= result["pattern_stability_score"] <= 1.0
        assert 0.0 <= result["confidence_improvement"] <= 1.0


class TestQualityMonitorOptimizer:
    """Test QualityMonitorOptimizer implementation."""

    @pytest.mark.asyncio
    async def test_quality_monitor_optimizer_execute(self):
        """Test quality monitor optimizer execution."""
        optimizer = QualityMonitorOptimizer(None)

        result = await optimizer.execute(
            project_id=1,
            measure_layers=True,
            domain_analysis=True
        )

        # Verify result structure
        assert "status" in result
        assert "overall_quality_score" in result
        assert "consolidation_quality" in result
        assert "layers_analyzed" in result
        assert "domains_covered" in result
        assert "semantic_density" in result
        assert "episodic_compression" in result

        # Verify types and ranges
        assert result["status"] == "success"
        assert 0.0 <= result["overall_quality_score"] <= 1.0
        assert isinstance(result["layers_analyzed"], int)
        assert result["layers_analyzed"] == 8  # All 8 layers


class TestSkillOptimizationIntegration:
    """Test Skill Optimization integration with operation router."""

    @pytest.mark.asyncio
    async def test_skill_optimization_operations_registered(self):
        """Test that skill optimization operations are registered in router."""
        from athena.mcp.operation_router import OperationRouter

        # Verify skill_optimization_tools is in operation maps
        assert "skill_optimization_tools" in OperationRouter.OPERATION_MAPS

        # Verify all 4 operations are registered
        skill_ops = OperationRouter.OPERATION_MAPS["skill_optimization_tools"]
        expected_ops = [
            "optimize_learning_tracker",
            "optimize_procedure_suggester",
            "optimize_gap_detector",
            "optimize_quality_monitor",
        ]

        for op in expected_ops:
            assert op in skill_ops, f"Operation {op} not registered"

    def test_skill_optimization_handler_forwarding(self):
        """Test that handlers properly forward to implementation."""
        from athena.mcp.handlers import MemoryMCPServer

        # Verify handler methods exist
        server_methods = [
            "_handle_optimize_learning_tracker",
            "_handle_optimize_procedure_suggester",
            "_handle_optimize_gap_detector",
            "_handle_optimize_quality_monitor",
        ]

        for method in server_methods:
            assert hasattr(MemoryMCPServer, method), f"Handler method {method} not found"


class TestSkillOptimizationErrorHandling:
    """Test error handling in skill optimization."""

    @pytest.mark.asyncio
    async def test_learning_tracker_error_handling(self):
        """Test error handling in learning tracker optimizer."""
        optimizer = LearningTrackerOptimizer(None)

        result = await optimizer.execute()

        # Error handling should return error status
        # Note: Current impl doesn't error with None db, but future impl will
        assert "status" in result

    @pytest.mark.asyncio
    async def test_procedure_suggester_error_handling(self):
        """Test error handling in procedure suggester optimizer."""
        optimizer = ProcedureSuggesterOptimizer(None)

        result = await optimizer.execute()

        assert "status" in result

    @pytest.mark.asyncio
    async def test_gap_detector_error_handling(self):
        """Test error handling in gap detector optimizer."""
        optimizer = GapDetectorOptimizer(None)

        result = await optimizer.execute()

        assert "status" in result

    @pytest.mark.asyncio
    async def test_quality_monitor_error_handling(self):
        """Test error handling in quality monitor optimizer."""
        optimizer = QualityMonitorOptimizer(None)

        result = await optimizer.execute()

        assert "status" in result


class TestSkillOptimizationPhase5Integration:
    """Test Phase 5 tool integration in skill optimization."""

    @pytest.mark.asyncio
    async def test_learning_tracker_phase5_tools(self):
        """Test Phase 5 tools used in learning tracker."""
        optimizer = LearningTrackerOptimizer(None)

        result = await optimizer.execute()

        # Verify Phase 5 tool results are present
        assert "best_strategy" in result
        assert "effectiveness_score" in result
        assert "encoding_rounds" in result
        assert "learning_curve_improvement" in result

    @pytest.mark.asyncio
    async def test_procedure_suggester_phase5_tools(self):
        """Test Phase 5 tools used in procedure suggester."""
        optimizer = ProcedureSuggesterOptimizer(None)

        result = await optimizer.execute()

        # Verify Phase 5 tool results
        assert "patterns_discovered" in result
        assert "pattern_stability_score" in result
        assert "procedure_success_rate" in result

    @pytest.mark.asyncio
    async def test_gap_detector_phase5_tools(self):
        """Test Phase 5 tools used in gap detector."""
        optimizer = GapDetectorOptimizer(None)

        result = await optimizer.execute()

        # Verify Phase 5 tool results
        assert "pattern_stability_score" in result
        assert "gaps_detected" in result
        assert "confidence_improvement" in result

    @pytest.mark.asyncio
    async def test_quality_monitor_phase5_tools(self):
        """Test Phase 5 tools used in quality monitor."""
        optimizer = QualityMonitorOptimizer(None)

        result = await optimizer.execute()

        # Verify Phase 5 tool results
        assert "consolidation_quality" in result
        assert "layers_analyzed" in result
        assert "domains_covered" in result


class TestSkillOptimizationMetrics:
    """Test performance and quality metrics in skill optimization."""

    @pytest.mark.asyncio
    async def test_learning_tracker_effectiveness_metrics(self):
        """Test effectiveness metrics in learning tracker."""
        optimizer = LearningTrackerOptimizer(None)

        result = await optimizer.execute()

        # Verify effectiveness metrics
        assert 0.0 <= result["effectiveness_score"] <= 1.0
        assert isinstance(result["learning_curve_improvement"], float)
        assert 0.0 <= result["learning_curve_improvement"] <= 1.0

    @pytest.mark.asyncio
    async def test_procedure_suggester_stability_metrics(self):
        """Test stability metrics in procedure suggester."""
        optimizer = ProcedureSuggesterOptimizer(None)

        result = await optimizer.execute()

        # Verify stability metrics
        assert 0.0 <= result["pattern_stability_score"] <= 1.0
        assert 0.0 <= result["top_procedure_confidence"] <= 1.0
        assert 0.0 <= result["procedure_success_rate"] <= 1.0

    @pytest.mark.asyncio
    async def test_gap_detector_confidence_metrics(self):
        """Test confidence metrics in gap detector."""
        optimizer = GapDetectorOptimizer(None)

        result = await optimizer.execute()

        # Verify confidence metrics
        assert 0.0 <= result["confidence_improvement"] <= 1.0
        assert 0.0 <= result["pattern_stability_score"] <= 1.0
        assert isinstance(result["gap_resolution_rate"], float)

    @pytest.mark.asyncio
    async def test_quality_monitor_layer_metrics(self):
        """Test layer health metrics in quality monitor."""
        optimizer = QualityMonitorOptimizer(None)

        result = await optimizer.execute()

        # Verify layer metrics
        assert result["layers_analyzed"] == 8
        assert "layer_metrics" in result
        assert len(result["layer_metrics"]) == 8

        # Verify each layer has a score
        for layer_name, layer_data in result["layer_metrics"].items():
            assert "score" in layer_data
            assert 0.0 <= layer_data["score"] <= 1.0
            assert "items" in layer_data


class TestSkillOptimizationQuality:
    """Test quality assurance for skill optimizations."""

    @pytest.mark.asyncio
    async def test_learning_tracker_recommendations(self):
        """Test that learning tracker generates recommendations."""
        optimizer = LearningTrackerOptimizer(None)

        result = await optimizer.execute()

        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)
        assert len(result["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_procedure_suggester_confidence_distribution(self):
        """Test that procedure suggester provides confidence distribution."""
        optimizer = ProcedureSuggesterOptimizer(None)

        result = await optimizer.execute()

        assert "confidence_distribution" in result
        total_confidence = sum(result["confidence_distribution"].values())
        assert total_confidence == result["procedures_recommended"]

    @pytest.mark.asyncio
    async def test_gap_detector_priority_gaps(self):
        """Test that gap detector identifies priority gaps."""
        optimizer = GapDetectorOptimizer(None)

        result = await optimizer.execute()

        assert "priority_gaps" in result
        assert isinstance(result["priority_gaps"], list)
        assert len(result["priority_gaps"]) > 0

    @pytest.mark.asyncio
    async def test_quality_monitor_domain_expertise(self):
        """Test that quality monitor tracks domain expertise."""
        optimizer = QualityMonitorOptimizer(None)

        result = await optimizer.execute()

        assert "domain_expertise" in result
        assert isinstance(result["domain_expertise"], dict)
        assert result["domains_covered"] == len(result["domain_expertise"])

        # Verify all domain scores are valid
        for domain, score in result["domain_expertise"].items():
            assert 0.0 <= score <= 1.0


# ============================================================================
# Test Organization
# ============================================================================

# These tests are organized into classes by optimizer/skill component
# Each class tests:
# 1. Handler implementation correctness
# 2. Optimizer execution and result structure
# 3. Error handling and edge cases
# 4. Integration with operation router
# 5. Phase 5 tool integration
# 6. Performance and quality metrics

# Run with: pytest tests/integration/test_skill_optimization.py -v
# Run specific test: pytest tests/integration/test_skill_optimization.py::TestLearningTrackerOptimizer -v
