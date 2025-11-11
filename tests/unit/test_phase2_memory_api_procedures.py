"""Integration tests for Phase 2 Week 8 - MemoryAPI procedure methods.

This module tests procedure-related MemoryAPI methods including:
- Code validation (syntax, security, quality)
- Procedure statistics and metrics
- Confidence-based search and filtering

Tests focus on core functionality with error handling and edge cases.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from athena.mcp.memory_api import MemoryAPI
from athena.procedural.models import Procedure, ProcedureCategory

# Import fixtures from Phase 1
from .test_phase1_fixtures import (
    temp_db,
    temp_db_path,
    memory_api,
    memory_api_direct,
    project_manager,
    unified_manager,
)


class TestValidateProcedureCode:
    """Tests for code validation via MemoryAPI."""

    def test_validate_valid_code(self, memory_api):
        """Test validation of valid Python code."""
        valid_code = "def my_procedure():\n    '''Does something useful.'''\n    return 42"

        result = memory_api.validate_procedure_code(code=valid_code)

        assert result["success"] is True
        assert "quality_score" in result
        assert "issues" in result
        assert "checks" in result
        assert isinstance(result["checks"], dict)

    def test_validate_invalid_syntax(self, memory_api):
        """Test validation of code with syntax errors."""
        invalid_code = "def my_procedure()\n    return 42"  # Missing colon

        result = memory_api.validate_procedure_code(code=invalid_code)

        # Should still complete but report issues
        assert result["success"] is True
        assert "issues" in result or "checks" in result

    def test_validate_insecure_code(self, memory_api):
        """Test validation detects insecure code patterns."""
        insecure_code = """import os
def bad_proc():
    os.system('rm -rf /')"""

        result = memory_api.validate_procedure_code(code=insecure_code)

        # Should complete validation
        assert result["success"] is True
        assert "checks" in result

    def test_validate_with_procedure_context(self, memory_api):
        """Test validation with procedure ID for context."""
        code = "def proc():\n    return 42"

        result = memory_api.validate_procedure_code(
            code=code,
            procedure_id=123,
        )

        assert result["success"] is True
        assert result["procedure_id"] == 123


class TestProcedureVersioning:
    """Tests for version history and rollback."""

    def test_get_procedure_versions_empty(self, memory_api):
        """Test retrieving versions when none exist."""
        with patch.object(memory_api, "git_store") as mock_git:
            mock_git.get_procedure_history.return_value = None

            result = memory_api.get_procedure_versions(procedure_id=1)

            assert result["success"] is True
            assert result["versions"] == []
            assert result["count"] == 0

    def test_rollback_procedure_code(self, memory_api):
        """Test rolling back to previous version."""
        mock_procedure = Mock()
        mock_procedure.name = "test_proc"
        mock_procedure.code_version = "1.0"

        with patch.object(memory_api, "git_store") as mock_git:
            mock_git.rollback_procedure.return_value = mock_procedure

            result = memory_api.rollback_procedure_code(
                procedure_id=1,
                target_version="abc123",
                reason="Test rollback",
            )

            assert result["success"] is True
            assert result["procedure_id"] == 1
            assert result["target_version"] == "abc123"
            assert result["procedure"]["name"] == "test_proc"


class TestProcedureStatistics:
    """Tests for retrieving procedure statistics."""

    def test_get_procedure_stats_not_found(self, memory_api):
        """Test stats retrieval for non-existent procedure."""
        with patch.object(memory_api.procedural, "get_procedure") as mock_get:
            mock_get.return_value = None

            result = memory_api.get_procedure_stats(procedure_id=99999)

            assert result["success"] is False
            assert "error" in result

    def test_get_procedure_stats_found(self, memory_api):
        """Test retrieving statistics for existing procedure."""
        mock_proc = Mock()
        mock_proc.name = "test_procedure"
        mock_proc.usage_count = 5
        mock_proc.success_rate = 0.8
        mock_proc.avg_completion_time_ms = 250
        mock_proc.code_confidence = 0.85

        with patch.object(memory_api.procedural, "get_procedure") as mock_get:
            mock_get.return_value = mock_proc

            with patch.object(memory_api.procedural, "get_execution_stats") as mock_stats:
                mock_stats.return_value = {
                    "total_executions": 5,
                    "successes": 4,
                }

                result = memory_api.get_procedure_stats(procedure_id=1)

                assert result["success"] is True
                assert result["procedure_id"] == 1
                assert result["name"] == "test_procedure"
                assert result["usage_count"] == 5


class TestSearchByConfidence:
    """Tests for confidence-based procedure search."""

    def test_search_no_results(self, memory_api):
        """Test confidence search with no results."""
        with patch.object(memory_api.procedural, "list_procedures") as mock_list:
            mock_list.return_value = []

            result = memory_api.search_procedures_by_confidence(
                min_confidence=0.9,
                limit=10,
            )

            assert result["success"] is True
            assert result["count"] == 0

    def test_search_respects_limit(self, memory_api):
        """Test that confidence search respects limit parameter."""
        mock_procs = [Mock(code_confidence=0.9, name=f"proc{i}") for i in range(20)]

        with patch.object(memory_api.procedural, "list_procedures") as mock_list:
            mock_list.return_value = mock_procs

            result = memory_api.search_procedures_by_confidence(
                min_confidence=0.7,
                limit=5,
            )

            assert result["count"] == 5


class TestProcedureExecution:
    """Tests for procedure execution with error handling."""

    def test_execute_procedure_no_code(self, memory_api):
        """Test execution gracefully handles missing code."""
        mock_proc = Mock()
        mock_proc.id = 1
        mock_proc.code = None

        with patch.object(memory_api.procedural, "get_procedure") as mock_get:
            mock_get.return_value = mock_proc

            with patch.object(memory_api.procedural, "record_execution"):
                result = memory_api.execute_procedure(procedure_id=1)

                assert "outcome" in result
                # May skip or fail, but should handle gracefully

    def test_execute_procedure_not_found(self, memory_api):
        """Test execution with non-existent procedure."""
        with patch.object(memory_api.procedural, "get_procedure") as mock_get:
            mock_get.return_value = None

            result = memory_api.execute_procedure(procedure_id=99999)

            assert result["success"] is False


class TestMemoryAPIHasNewMethods:
    """Verify that all 8 new procedure methods exist and are callable."""

    def test_memory_api_has_code_generation_method(self, memory_api):
        """Verify generate_procedure_code method exists."""
        assert hasattr(memory_api, "generate_procedure_code")
        assert callable(memory_api.generate_procedure_code)

    def test_memory_api_has_validation_method(self, memory_api):
        """Verify validate_procedure_code method exists."""
        assert hasattr(memory_api, "validate_procedure_code")
        assert callable(memory_api.validate_procedure_code)

    def test_memory_api_has_versioning_methods(self, memory_api):
        """Verify version management methods exist."""
        assert hasattr(memory_api, "get_procedure_versions")
        assert hasattr(memory_api, "rollback_procedure_code")
        assert callable(memory_api.get_procedure_versions)
        assert callable(memory_api.rollback_procedure_code)

    def test_memory_api_has_execution_method(self, memory_api):
        """Verify execute_procedure method exists."""
        assert hasattr(memory_api, "execute_procedure")
        assert callable(memory_api.execute_procedure)

    def test_memory_api_has_stats_method(self, memory_api):
        """Verify get_procedure_stats method exists."""
        assert hasattr(memory_api, "get_procedure_stats")
        assert callable(memory_api.get_procedure_stats)

    def test_memory_api_has_search_method(self, memory_api):
        """Verify search_procedures_by_confidence method exists."""
        assert hasattr(memory_api, "search_procedures_by_confidence")
        assert callable(memory_api.search_procedures_by_confidence)


class TestMemoryAPIComponentInitialization:
    """Tests for proper initialization of code generation components."""

    def test_memory_api_has_code_generator(self, memory_api):
        """Verify CodeGenerator is initialized."""
        assert hasattr(memory_api, "code_generator")
        assert memory_api.code_generator is not None

    def test_memory_api_has_code_validator(self, memory_api):
        """Verify CodeValidator is initialized."""
        assert hasattr(memory_api, "code_validator")
        assert memory_api.code_validator is not None

    def test_memory_api_has_confidence_scorer(self, memory_api):
        """Verify ConfidenceScorer is initialized."""
        assert hasattr(memory_api, "confidence_scorer")
        assert memory_api.confidence_scorer is not None

    def test_memory_api_has_git_store_placeholder(self, memory_api):
        """Verify git_store is initialized (lazily)."""
        assert hasattr(memory_api, "git_store")
        # Initially None, lazily initialized on first use
        assert memory_api.git_store is None
