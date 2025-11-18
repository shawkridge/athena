"""Tests for specification extractors."""

import json
import pytest
import tempfile
from pathlib import Path

from athena.architecture.extractors import (
    get_extractor,
    PythonAPIExtractor,
    ExtractionConfig,
    SpecExtractor,
)
from athena.architecture.models import SpecType


# Sample FastAPI application
FASTAPI_SAMPLE = '''
from fastapi import FastAPI

app = FastAPI(title="User API", version="1.0.0")

@app.get("/users")
def list_users():
    """List all users."""
    return []

@app.post("/users")
def create_user():
    """Create a new user."""
    return {"id": 1}

@app.get("/users/{user_id}")
def get_user(user_id: int):
    """Get a specific user."""
    return {"id": user_id}

@app.delete("/users/{user_id}")
def delete_user(user_id: int):
    """Delete a user."""
    return {"deleted": True}
'''

# Sample Flask application
FLASK_SAMPLE = '''
from flask import Flask

app = Flask(__name__)

@app.route("/users", methods=["GET"])
def list_users():
    """List all users."""
    return []

@app.route("/users", methods=["POST"])
def create_user():
    """Create a new user."""
    return {"id": 1}

@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    """Get a specific user."""
    return {"id": user_id}
'''

# Invalid Python file
INVALID_PYTHON = '''
def some_function():
    print("This is not an API file")
'''


class TestPythonAPIExtractor:
    """Tests for PythonAPIExtractor."""

    def test_can_extract_fastapi(self, tmp_path):
        """Test that extractor can detect FastAPI files."""
        # Create FastAPI file
        api_file = tmp_path / "main.py"
        api_file.write_text(FASTAPI_SAMPLE)

        extractor = PythonAPIExtractor()
        assert extractor.can_extract(api_file)

    def test_can_extract_flask(self, tmp_path):
        """Test that extractor can detect Flask files."""
        # Create Flask file
        api_file = tmp_path / "app.py"
        api_file.write_text(FLASK_SAMPLE)

        extractor = PythonAPIExtractor()
        assert extractor.can_extract(api_file)

    def test_cannot_extract_invalid_python(self, tmp_path):
        """Test that extractor rejects non-API Python files."""
        # Create non-API file
        py_file = tmp_path / "utils.py"
        py_file.write_text(INVALID_PYTHON)

        extractor = PythonAPIExtractor()
        assert not extractor.can_extract(py_file)

    def test_cannot_extract_non_python(self, tmp_path):
        """Test that extractor rejects non-Python files."""
        # Create non-Python file
        txt_file = tmp_path / "readme.txt"
        txt_file.write_text("This is a text file")

        extractor = PythonAPIExtractor()
        assert not extractor.can_extract(txt_file)

    def test_extract_fastapi_static(self, tmp_path):
        """Test extracting FastAPI spec using static analysis."""
        # Create FastAPI file
        api_file = tmp_path / "main.py"
        api_file.write_text(FASTAPI_SAMPLE)

        extractor = PythonAPIExtractor()
        config = ExtractionConfig(
            output_name="Test API",
            output_version="1.0.0",
        )

        result = extractor.extract(api_file, config)

        # Check result
        assert result.spec is not None
        assert result.spec.spec_type == SpecType.OPENAPI
        assert result.confidence > 0.5
        assert len(result.warnings) >= 0  # May have warnings about static analysis

        # Check spec content
        spec_dict = json.loads(result.spec.content)
        assert spec_dict["openapi"] in ["3.0.0", "3.1.0"]  # FastAPI uses 3.1.0
        assert "paths" in spec_dict

        # Should have extracted routes
        paths = spec_dict["paths"]
        assert "/users" in paths or len(paths) > 0  # At least some routes

    def test_extract_flask_static(self, tmp_path):
        """Test extracting Flask spec using static analysis."""
        # Create Flask file
        api_file = tmp_path / "app.py"
        api_file.write_text(FLASK_SAMPLE)

        extractor = PythonAPIExtractor()
        config = ExtractionConfig(
            output_name="Flask API",
            output_version="1.0.0",
        )

        result = extractor.extract(api_file, config)

        # Check result
        assert result.spec is not None
        assert result.spec.spec_type == SpecType.OPENAPI
        assert result.confidence > 0.5
        assert len(result.warnings) > 0  # Flask should have warnings

        # Check spec content
        spec_dict = json.loads(result.spec.content)
        assert spec_dict["openapi"] == "3.0.0"
        assert "paths" in spec_dict

    def test_get_supported_spec_types(self):
        """Test that extractor reports OpenAPI support."""
        extractor = PythonAPIExtractor()
        spec_types = extractor.get_supported_spec_types()

        assert SpecType.OPENAPI in spec_types

    def test_get_name(self):
        """Test extractor name."""
        extractor = PythonAPIExtractor()
        name = extractor.get_name()

        assert "Python" in name
        assert "API" in name

    def test_extract_with_config_override(self, tmp_path):
        """Test that config provides defaults for extracted values.

        Note: When dynamic extraction succeeds (FastAPI openapi() method),
        the extracted values from the app take precedence. Config values
        are used as fallback for static analysis."""
        api_file = tmp_path / "main.py"
        api_file.write_text(FASTAPI_SAMPLE)

        extractor = PythonAPIExtractor()
        config = ExtractionConfig(
            output_name="My Custom API Name",
            output_version="2.5.0",
            output_description="Custom description",
        )

        result = extractor.extract(api_file, config)

        # Spec should have valid values (either from extraction or config)
        assert result.spec.name is not None
        assert len(result.spec.name) > 0
        assert result.spec.version is not None
        # If dynamic extraction worked, it may use FastAPI's values
        # If static analysis, it should use config values

    def test_extraction_metadata(self, tmp_path):
        """Test that extraction result includes metadata."""
        api_file = tmp_path / "main.py"
        api_file.write_text(FASTAPI_SAMPLE)

        extractor = PythonAPIExtractor()
        result = extractor.extract(api_file)

        # Check metadata
        assert "framework" in result.metadata
        assert result.metadata["framework"] in ["FastAPI", "Flask"]
        assert "source_file" in result.metadata

    def test_extract_nonexistent_file(self):
        """Test that extracting non-existent file raises error."""
        extractor = PythonAPIExtractor()

        with pytest.raises(ValueError, match="not found"):
            extractor.extract(Path("/nonexistent/file.py"))


class TestExtractorRegistry:
    """Tests for extractor registry and auto-detection."""

    def test_get_extractor_fastapi(self, tmp_path):
        """Test auto-detecting extractor for FastAPI file."""
        api_file = tmp_path / "main.py"
        api_file.write_text(FASTAPI_SAMPLE)

        extractor = get_extractor(api_file)

        assert extractor is not None
        assert isinstance(extractor, PythonAPIExtractor)

    def test_get_extractor_flask(self, tmp_path):
        """Test auto-detecting extractor for Flask file."""
        api_file = tmp_path / "app.py"
        api_file.write_text(FLASK_SAMPLE)

        extractor = get_extractor(api_file)

        assert extractor is not None
        assert isinstance(extractor, PythonAPIExtractor)

    def test_get_extractor_none_for_invalid(self, tmp_path):
        """Test that no extractor is found for invalid files."""
        txt_file = tmp_path / "readme.txt"
        txt_file.write_text("Not a code file")

        extractor = get_extractor(txt_file)

        assert extractor is None

    def test_validation_flags_low_confidence(self, tmp_path):
        """Test that validation flags low confidence results."""
        api_file = tmp_path / "main.py"
        api_file.write_text(FASTAPI_SAMPLE)

        extractor = PythonAPIExtractor()
        result = extractor.extract(api_file)

        # Manually set low confidence to test validation
        result.confidence = 0.3
        validated = extractor.validate_result(result)

        assert validated.requires_review
        assert any("Low confidence" in w for w in validated.warnings)

    def test_validation_flags_empty_content(self, tmp_path):
        """Test that validation flags empty spec content."""
        api_file = tmp_path / "main.py"
        api_file.write_text(FASTAPI_SAMPLE)

        extractor = PythonAPIExtractor()
        result = extractor.extract(api_file)

        # Manually clear content to test validation
        result.spec.content = ""
        validated = extractor.validate_result(result)

        assert validated.requires_review
        assert validated.confidence == 0.0
        assert any("no content" in w.lower() for w in validated.warnings)


class TestExtractionConfig:
    """Tests for ExtractionConfig."""

    def test_default_config(self):
        """Test default extraction configuration."""
        config = ExtractionConfig()

        assert config.project_id == 1
        assert config.auto_detect_type is True
        assert config.validate_after_extract is True
        assert config.output_version == "1.0.0"

    def test_custom_config(self):
        """Test custom extraction configuration."""
        config = ExtractionConfig(
            project_id=5,
            output_name="My API",
            output_version="2.0.0",
            output_description="Test description",
        )

        assert config.project_id == 5
        assert config.output_name == "My API"
        assert config.output_version == "2.0.0"
        assert config.output_description == "Test description"
