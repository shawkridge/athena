"""Tests for ProcedureCodeExtractor - Week 6 Phase 2 implementation.

Tests cover:
- Code extraction from templates
- Code extraction from steps
- Code extraction from direct code
- Code validation
- Confidence scoring
- Edge cases
"""

import pytest
from datetime import datetime

from athena.procedural.code_extractor import ProcedureCodeExtractor, extract_code_from_procedure
from athena.procedural.models import (
    Procedure,
    ProcedureCategory,
    ExecutableProcedure,
)


@pytest.fixture
def sample_procedure_with_template():
    """Create a procedure with a template."""
    return Procedure(
        id=1,
        name="Render Template",
        category=ProcedureCategory.DOCUMENTATION,
        description="Renders a template with variables",
        template="""
Dear {{recipient}},

Thank you for using {{product_name}}.

Best regards,
{{sender}}
        """,
        created_at=datetime.now(),
    )


@pytest.fixture
def sample_procedure_with_steps():
    """Create a procedure with steps."""
    return Procedure(
        id=2,
        name="Deploy Application",
        category=ProcedureCategory.DEPLOYMENT,
        description="Deploy application to production",
        template="",  # Required field
        steps=[
            {
                "name": "Build",
                "action": "bash: npm run build",
                "validate": "Check if build succeeded",
            },
            {
                "name": "Test",
                "action": "bash: npm run test",
                "validate": "Check if tests passed",
            },
            {
                "name": "Deploy",
                "action": "bash: npm run deploy",
                "validate": "Check deployment status",
            },
        ],
        created_at=datetime.now(),
    )


@pytest.fixture
def sample_procedure_with_code():
    """Create a procedure with direct code."""
    code = '''def process_data(context: dict, input_path: str) -> dict:
    """Process data from input file."""
    try:
        with open(input_path) as f:
            data = f.read()
        return {'success': True, 'data': data}
    except Exception as e:
        return {'success': False, 'error': str(e)}
'''
    return Procedure(
        id=3,
        name="Process Data",
        category=ProcedureCategory.ARCHITECTURE,
        description="Process data from input file",
        code=code,
        template="",  # Required field
        created_at=datetime.now(),
    )


class TestCodeExtractionFromTemplate:
    """Tests for extracting code from templates."""

    def test_extract_code_from_template(self, sample_procedure_with_template):
        """Test extracting code from procedure template."""
        extractor = ProcedureCodeExtractor(sample_procedure_with_template)
        code, confidence = extractor.extract()

        assert code is not None, "Should extract code from template"
        assert confidence > 0, "Should have some confidence"
        assert "def " in code, "Should have function definition"
        assert "template" in code, "Should reference template"

    def test_template_extraction_creates_valid_python(self, sample_procedure_with_template):
        """Test that extracted code is valid Python."""
        extractor = ProcedureCodeExtractor(sample_procedure_with_template)
        code, confidence = extractor.extract()

        # Should not raise SyntaxError
        compile(code, "<string>", "exec")

    def test_template_extraction_confidence_score(self, sample_procedure_with_template):
        """Test confidence score for template extraction."""
        extractor = ProcedureCodeExtractor(sample_procedure_with_template)
        code, confidence = extractor.extract()

        assert 0.5 <= confidence <= 0.7, "Template extraction should have moderate confidence"

    def test_template_includes_variables(self, sample_procedure_with_template):
        """Test that template extraction recognizes variables."""
        extractor = ProcedureCodeExtractor(sample_procedure_with_template)
        code, confidence = extractor.extract()

        # Should include variable replacement logic
        assert "replace" in code.lower() or "format" in code.lower()


class TestCodeExtractionFromSteps:
    """Tests for extracting code from procedure steps."""

    def test_extract_code_from_steps(self, sample_procedure_with_steps):
        """Test extracting code from procedure steps."""
        extractor = ProcedureCodeExtractor(sample_procedure_with_steps)
        code, confidence = extractor.extract()

        assert code is not None, "Should extract code from steps"
        assert confidence > 0, "Should have some confidence"
        assert "subprocess" in code, "Should reference subprocess for shell commands"

    def test_steps_extraction_creates_valid_python(self, sample_procedure_with_steps):
        """Test that extracted code from steps is valid Python."""
        extractor = ProcedureCodeExtractor(sample_procedure_with_steps)
        code, confidence = extractor.extract()

        # Should not raise SyntaxError
        compile(code, "<string>", "exec")

    def test_steps_extraction_confidence_score(self, sample_procedure_with_steps):
        """Test confidence score for steps extraction."""
        extractor = ProcedureCodeExtractor(sample_procedure_with_steps)
        code, confidence = extractor.extract()

        assert 0.6 <= confidence <= 0.8, "Steps extraction should have moderate-high confidence"

    def test_steps_bash_commands_converted(self, sample_procedure_with_steps):
        """Test that bash commands in steps are converted."""
        extractor = ProcedureCodeExtractor(sample_procedure_with_steps)
        code, confidence = extractor.extract()

        assert "npm run build" in code or "shell=True" in code


class TestCodeExtractionFromDirectCode:
    """Tests for extracting code when directly provided."""

    def test_extract_direct_code(self, sample_procedure_with_code):
        """Test extracting code when directly provided."""
        extractor = ProcedureCodeExtractor(sample_procedure_with_code)
        code, confidence = extractor.extract()

        assert code is not None, "Should extract direct code"
        assert confidence >= 0.9, "Direct code should have high confidence"
        assert "process_data" in code, "Should preserve function name"

    def test_direct_code_is_returned_unchanged(self, sample_procedure_with_code):
        """Test that direct code is returned with minimal changes."""
        extractor = ProcedureCodeExtractor(sample_procedure_with_code)
        code, confidence = extractor.extract()

        # Code should be present in output
        assert sample_procedure_with_code.code in code

    def test_direct_code_confidence_is_high(self, sample_procedure_with_code):
        """Test that direct code extraction has high confidence."""
        extractor = ProcedureCodeExtractor(sample_procedure_with_code)
        code, confidence = extractor.extract()

        assert confidence >= 0.9, "Direct code should have confidence >= 0.9"


class TestCodeValidation:
    """Tests for code validation."""

    def test_validate_correct_code(self, sample_procedure_with_code):
        """Test validation of syntactically correct code."""
        extractor = ProcedureCodeExtractor(sample_procedure_with_code)
        assert extractor._validate_code(sample_procedure_with_code.code)

    def test_validate_incorrect_code(self, sample_procedure_with_code):
        """Test validation of syntactically incorrect code."""
        extractor = ProcedureCodeExtractor(sample_procedure_with_code)
        bad_code = "def broken(:  # Invalid syntax"

        assert not extractor._validate_code(bad_code)

    def test_failed_validation_prevents_extraction(self):
        """Test that failed validation returns None code."""
        proc = Procedure(
            id=1,
            name="Invalid Code Procedure",
            category=ProcedureCategory.TESTING,
            code="def broken(:  # Invalid",
            template="",  # Required field
            created_at=datetime.now(),
        )

        extractor = ProcedureCodeExtractor(proc)
        code, confidence = extractor.extract()

        assert code is None, "Invalid code should not be extracted"


class TestFunctionNameSanitization:
    """Tests for function name sanitization."""

    def test_sanitize_function_name_with_spaces(self):
        """Test sanitizing function name with spaces."""
        proc = Procedure(
            id=1,
            name="My Test Procedure",
            category=ProcedureCategory.TESTING,
            template="",  # Required field
            created_at=datetime.now(),
        )

        extractor = ProcedureCodeExtractor(proc)
        sanitized = extractor._sanitize_function_name("My Test Procedure")

        assert sanitized == "my_test_procedure"

    def test_sanitize_function_name_with_special_chars(self):
        """Test sanitizing function name with special characters."""
        proc = Procedure(
            id=1,
            name="Test",
            category=ProcedureCategory.TESTING,
            template="",
            created_at=datetime.now(),
        )
        extractor = ProcedureCodeExtractor(proc)
        sanitized = extractor._sanitize_function_name("Test/Procedure (v2.0)")

        # Should be alphanumeric or underscores
        assert all(c.isalnum() or c == "_" for c in sanitized)

    def test_sanitize_function_name_starting_with_digit(self):
        """Test sanitizing function name starting with digit."""
        proc = Procedure(
            id=1,
            name="Test",
            category=ProcedureCategory.TESTING,
            template="",
            created_at=datetime.now(),
        )
        extractor = ProcedureCodeExtractor(proc)
        sanitized = extractor._sanitize_function_name("2fast2furious")

        assert not sanitized[0].isdigit()

    def test_sanitize_function_name_empty(self):
        """Test sanitizing empty function name."""
        proc = Procedure(
            id=1,
            name="Test",
            category=ProcedureCategory.TESTING,
            template="",
            created_at=datetime.now(),
        )
        extractor = ProcedureCodeExtractor(proc)
        sanitized = extractor._sanitize_function_name("@#$%")

        assert len(sanitized) > 0, "Should return default procedure name"


class TestParameterExtraction:
    """Tests for parameter extraction."""

    def test_extract_parameters_from_template(self, sample_procedure_with_template):
        """Test extracting parameters from template variables."""
        extractor = ProcedureCodeExtractor(sample_procedure_with_template)
        params = extractor._extract_parameters()

        param_names = [p["name"] for p in params]
        assert "recipient" in param_names
        assert "product_name" in param_names
        assert "sender" in param_names

    def test_extract_parameters_from_steps(self, sample_procedure_with_steps):
        """Test extracting parameters from step variables."""
        extractor = ProcedureCodeExtractor(sample_procedure_with_steps)
        params = extractor._extract_parameters()

        # Steps don't have explicit variables in fixture, but should not crash
        assert isinstance(params, list)

    def test_extracted_parameters_have_types(self):
        """Test that extracted parameters have type info."""
        proc = Procedure(
            id=1,
            name="Test",
            category=ProcedureCategory.TESTING,
            template="Hello {{name}}",
            created_at=datetime.now(),
        )

        extractor = ProcedureCodeExtractor(proc)
        params = extractor._extract_parameters()

        for param in params:
            assert "name" in param
            assert "type" in param
            assert "description" in param


class TestConfidenceAnalysis:
    """Tests for confidence analysis."""

    def test_confidence_analysis_direct_code(self, sample_procedure_with_code):
        """Test confidence analysis for direct code."""
        extractor = ProcedureCodeExtractor(sample_procedure_with_code)
        extractor.extract()

        analysis = extractor.get_confidence_analysis()

        assert "overall_confidence" in analysis
        assert "code_source" in analysis
        assert "factors" in analysis
        assert analysis["code_source"] == "direct_code"

    def test_confidence_analysis_template(self, sample_procedure_with_template):
        """Test confidence analysis for template extraction."""
        extractor = ProcedureCodeExtractor(sample_procedure_with_template)
        extractor.extract()

        analysis = extractor.get_confidence_analysis()

        assert analysis["code_source"] == "converted_template"

    def test_confidence_analysis_steps(self, sample_procedure_with_steps):
        """Test confidence analysis for steps extraction."""
        extractor = ProcedureCodeExtractor(sample_procedure_with_steps)
        extractor.extract()

        analysis = extractor.get_confidence_analysis()

        assert analysis["code_source"] == "converted_steps"


class TestExecutableProcedureConversion:
    """Tests for converting to ExecutableProcedure."""

    def test_convert_to_executable_procedure(self, sample_procedure_with_code):
        """Test converting extracted code to ExecutableProcedure."""
        extractor = ProcedureCodeExtractor(sample_procedure_with_code)
        exec_proc = extractor.to_executable_procedure()

        assert exec_proc is not None
        assert isinstance(exec_proc, ExecutableProcedure)
        assert exec_proc.name == sample_procedure_with_code.name
        assert exec_proc.code is not None

    def test_executable_procedure_has_confidence(self, sample_procedure_with_code):
        """Test that ExecutableProcedure has confidence score."""
        extractor = ProcedureCodeExtractor(sample_procedure_with_code)
        exec_proc = extractor.to_executable_procedure()

        assert 0 <= exec_proc.code_generation_confidence <= 1

    def test_failed_extraction_returns_none(self):
        """Test that failed extraction returns None."""
        proc = Procedure(
            id=1,
            name="No Code Procedure",
            category=ProcedureCategory.TESTING,
            description="Procedure with no code or template",
            template="",  # Required field
            created_at=datetime.now(),
        )

        extractor = ProcedureCodeExtractor(proc)
        exec_proc = extractor.to_executable_procedure()

        assert exec_proc is None


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_extract_code_from_procedure_function(self, sample_procedure_with_code):
        """Test convenience function for code extraction."""
        code, confidence = extract_code_from_procedure(sample_procedure_with_code)

        assert code is not None
        assert confidence >= 0.9

    def test_extract_code_from_procedure_invalid(self):
        """Test convenience function with invalid procedure."""
        proc = Procedure(
            id=1,
            name="Empty Procedure",
            category=ProcedureCategory.TESTING,
            template="",  # Required field
            created_at=datetime.now(),
        )

        code, confidence = extract_code_from_procedure(proc)

        assert code is None


class TestEdgeCases:
    """Tests for edge cases."""

    def test_procedure_with_empty_template(self):
        """Test handling procedure with empty template."""
        proc = Procedure(
            id=1,
            name="Empty Template",
            category=ProcedureCategory.TESTING,
            template="",
            created_at=datetime.now(),
        )

        extractor = ProcedureCodeExtractor(proc)
        code, confidence = extractor.extract()

        assert code is None

    def test_procedure_with_empty_steps(self):
        """Test handling procedure with empty steps."""
        proc = Procedure(
            id=1,
            name="Empty Steps",
            category=ProcedureCategory.TESTING,
            template="",  # Required field
            steps=[],
            created_at=datetime.now(),
        )

        extractor = ProcedureCodeExtractor(proc)
        code, confidence = extractor.extract()

        assert code is None

    def test_procedure_with_mixed_sources(self):
        """Test that code takes priority over other sources."""
        proc = Procedure(
            id=1,
            name="Mixed Sources",
            category=ProcedureCategory.TESTING,
            code="def primary(): pass",
            template="Fallback {{template}}",
            steps=[{"action": "fallback step"}],
            created_at=datetime.now(),
        )

        extractor = ProcedureCodeExtractor(proc)
        code, confidence = extractor.extract()

        assert code is not None, "Should extract code"
        assert "primary" in code, "Should use direct code"
        assert confidence >= 0.9, "Should have high confidence"

    def test_extraction_with_unicode(self):
        """Test handling procedure with unicode characters."""
        proc = Procedure(
            id=1,
            name="Unicode Procedure 🚀",
            category=ProcedureCategory.TESTING,
            template="Hello {{name}} 👋",
            created_at=datetime.now(),
        )

        extractor = ProcedureCodeExtractor(proc)
        code, confidence = extractor.extract()

        assert code is not None
        # Should handle unicode without errors

    def test_extraction_with_large_procedure(self):
        """Test extraction with very large procedure."""
        large_steps = [
            {"name": f"Step {i}", "action": f"bash: echo 'Step {i}'"}
            for i in range(100)
        ]

        proc = Procedure(
            id=1,
            name="Large Procedure",
            category=ProcedureCategory.TESTING,
            template="",  # Required field
            steps=large_steps,
            created_at=datetime.now(),
        )

        extractor = ProcedureCodeExtractor(proc)
        code, confidence = extractor.extract()

        assert code is not None
        assert len(code) > 1000  # Should generate substantial code


class TestMultipleExtractions:
    """Tests for extracting from the same procedure multiple times."""

    def test_idempotent_extraction(self, sample_procedure_with_code):
        """Test that multiple extractions produce same result."""
        extractor1 = ProcedureCodeExtractor(sample_procedure_with_code)
        code1, conf1 = extractor1.extract()

        extractor2 = ProcedureCodeExtractor(sample_procedure_with_code)
        code2, conf2 = extractor2.extract()

        assert code1 == code2
        assert conf1 == conf2

    def test_multiple_procedures_independent(self):
        """Test that extracting different procedures doesn't interfere."""
        proc1 = Procedure(
            id=1,
            name="Procedure 1",
            category=ProcedureCategory.TESTING,
            code="def proc1(): pass",
            template="",  # Required field
            created_at=datetime.now(),
        )
        proc2 = Procedure(
            id=2,
            name="Procedure 2",
            category=ProcedureCategory.TESTING,
            code="def proc2(): pass",
            template="",  # Required field
            created_at=datetime.now(),
        )

        ext1 = ProcedureCodeExtractor(proc1)
        code1, _ = ext1.extract()

        ext2 = ProcedureCodeExtractor(proc2)
        code2, _ = ext2.extract()

        assert "proc1" in code1
        assert "proc2" in code2
        assert code1 != code2
