"""Tests for document diff engine (Phase 4E)."""

import sys
import pytest
from pathlib import Path

# Add parent directory to path for test imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_database import TestDatabase
from athena.architecture.sync.diff_engine import (
    DocumentDiffer,
    SectionParser,
    Section,
    SectionType,
    ChangeType,
)
from athena.architecture.models import Document, DocumentType, DocumentStatus


@pytest.fixture
def sample_markdown():
    """Sample markdown content for testing."""
    return """# API Documentation

## Overview

This is the API overview.

## Endpoints

### GET /users

Returns a list of users.

```python
response = requests.get('/users')
print(response.json())
```

### POST /users

Creates a new user.

## Error Codes

- 400: Bad Request
- 401: Unauthorized
- 404: Not Found
"""


@pytest.fixture
def modified_markdown():
    """Modified version of sample markdown."""
    return """# API Documentation

## Overview

This is the updated API overview with more details.

## Endpoints

### GET /users

Returns a paginated list of users.

```python
response = requests.get('/users?page=1&limit=10')
print(response.json())
```

### POST /users

Creates a new user with validation.

### PUT /users/{id}

Updates an existing user.

## Error Codes

- 400: Bad Request
- 401: Unauthorized
- 404: Not Found
- 500: Internal Server Error
"""


class TestSectionParser:
    """Test markdown section parsing."""

    def test_parse_headers(self):
        """Test parsing markdown headers."""
        parser = SectionParser()
        content = "# Header 1\n## Header 2\n### Header 3"
        sections = parser.parse(content)

        assert len(sections) == 3
        assert sections[0].section_type == SectionType.HEADER
        assert sections[0].header_level == 1
        assert sections[0].header_text == "Header 1"

        assert sections[1].header_level == 2
        assert sections[1].header_text == "Header 2"

    def test_parse_code_block(self):
        """Test parsing code blocks."""
        parser = SectionParser()
        content = "```python\nprint('hello')\n```"
        sections = parser.parse(content)

        assert len(sections) == 1
        assert sections[0].section_type == SectionType.CODE_BLOCK
        assert sections[0].language == "python"
        assert "print('hello')" in sections[0].content

    def test_parse_list(self):
        """Test parsing lists."""
        parser = SectionParser()
        content = "- Item 1\n- Item 2\n- Item 3"
        sections = parser.parse(content)

        assert len(sections) == 1
        assert sections[0].section_type == SectionType.LIST
        assert "Item 1" in sections[0].content

    def test_parse_paragraph(self):
        """Test parsing paragraphs."""
        parser = SectionParser()
        content = "This is a paragraph.\nWith multiple lines."
        sections = parser.parse(content)

        assert len(sections) == 1
        assert sections[0].section_type == SectionType.PARAGRAPH
        assert "This is a paragraph" in sections[0].content

    def test_parse_complete_document(self, sample_markdown):
        """Test parsing a complete markdown document."""
        parser = SectionParser()
        sections = parser.parse(sample_markdown)

        # Should have multiple sections
        assert len(sections) > 0

        # Should have headers
        headers = [s for s in sections if s.section_type == SectionType.HEADER]
        assert len(headers) > 0

        # Should have code blocks
        code_blocks = [s for s in sections if s.section_type == SectionType.CODE_BLOCK]
        assert len(code_blocks) > 0

        # Should have lists
        lists = [s for s in sections if s.section_type == SectionType.LIST]
        assert len(lists) > 0


class TestDocumentDiffer:
    """Test document diff computation."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create test database."""
        db_path = tmp_path / "test.db"
        return TestDatabase(str(db_path))

    @pytest.fixture
    def doc_store(self, db, tmp_path):
        """Create document store."""
        from athena.architecture.doc_store import DocumentStore

        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        return DocumentStore(db, docs_dir=docs_dir)

    @pytest.fixture
    def spec_store(self, db):
        """Create spec store."""
        from athena.architecture.spec_store import SpecificationStore

        return SpecificationStore(db)

    @pytest.fixture
    def sample_doc(self, doc_store, sample_markdown):
        """Create a sample document."""
        doc = Document(
            project_id=1,
            name="API Documentation",
            doc_type=DocumentType.API_DOC,
            version="1.0.0",
            content=sample_markdown,
            status=DocumentStatus.PUBLISHED,
            generated_by="ai",
            based_on_spec_ids=[1],
        )
        doc.id = doc_store.create(doc, write_to_file=False)
        return doc

    def test_compute_diff_with_changes(
        self, spec_store, doc_store, sample_doc, modified_markdown
    ):
        """Test computing diff with changes."""
        differ = DocumentDiffer(spec_store=spec_store, doc_store=doc_store)

        diff_result = differ.compute_diff(
            doc_id=sample_doc.id, new_content=modified_markdown, show_cause=False
        )

        assert diff_result is not None
        assert diff_result.document_id == sample_doc.id
        assert diff_result.document_name == "API Documentation"
        assert diff_result.has_changes

        # Should detect additions
        assert len(diff_result.sections_added) > 0

        # Should detect modifications
        assert len(diff_result.sections_modified) > 0

        # Should have statistics
        assert diff_result.total_additions > 0

    def test_compute_diff_no_changes(self, spec_store, doc_store, sample_doc):
        """Test computing diff with no changes."""
        differ = DocumentDiffer(spec_store=spec_store, doc_store=doc_store)

        # Use same content
        diff_result = differ.compute_diff(
            doc_id=sample_doc.id, new_content=sample_doc.content, show_cause=False
        )

        assert diff_result is not None
        assert not diff_result.has_changes
        assert diff_result.total_additions == 0
        assert diff_result.total_deletions == 0

    def test_diff_output_formats(
        self, spec_store, doc_store, sample_doc, modified_markdown
    ):
        """Test diff output formats."""
        differ = DocumentDiffer(spec_store=spec_store, doc_store=doc_store)

        diff_result = differ.compute_diff(
            doc_id=sample_doc.id, new_content=modified_markdown, show_cause=False
        )

        # Test text output
        text_output = diff_result.to_text(color=False)
        assert "Summary:" in text_output
        assert "Added Sections" in text_output or "Modified Sections" in text_output

        # Test JSON output
        json_output = diff_result.to_json()
        assert "document_id" in json_output
        assert "summary" in json_output
        assert "sections_added" in json_output

        # Test markdown output
        md_output = diff_result.to_markdown()
        assert "# Diff Report" in md_output
        assert "## Summary" in md_output

    def test_section_change_statistics(
        self, spec_store, doc_store, sample_doc, modified_markdown
    ):
        """Test section change statistics."""
        differ = DocumentDiffer(spec_store=spec_store, doc_store=doc_store)

        diff_result = differ.compute_diff(
            doc_id=sample_doc.id, new_content=modified_markdown, show_cause=False
        )

        # Check section changes have proper statistics
        for section in diff_result.sections_added:
            assert section.additions >= 0
            assert section.change_type == ChangeType.ADDED

        for section in diff_result.sections_modified:
            assert section.change_type == ChangeType.MODIFIED

        for section in diff_result.sections_removed:
            assert section.deletions >= 0
            assert section.change_type == ChangeType.REMOVED

    def test_diff_with_nonexistent_document(self, spec_store, doc_store):
        """Test diff with nonexistent document raises error."""
        differ = DocumentDiffer(spec_store=spec_store, doc_store=doc_store)

        with pytest.raises(ValueError, match="not found"):
            differ.compute_diff(doc_id=99999, new_content="test", show_cause=False)


class TestSectionHashing:
    """Test section hashing for diffing."""

    def test_sections_with_same_content_hash_equal(self):
        """Test that sections with same content hash equally."""
        section1 = Section(
            section_type=SectionType.PARAGRAPH,
            content="Test content",
            line_start=1,
            line_end=1,
        )
        section2 = Section(
            section_type=SectionType.PARAGRAPH,
            content="Test content",
            line_start=5,
            line_end=5,
        )

        assert hash(section1) == hash(section2)

    def test_sections_with_different_content_hash_different(self):
        """Test that sections with different content hash differently."""
        section1 = Section(
            section_type=SectionType.PARAGRAPH,
            content="Test content 1",
            line_start=1,
            line_end=1,
        )
        section2 = Section(
            section_type=SectionType.PARAGRAPH,
            content="Test content 2",
            line_start=1,
            line_end=1,
        )

        assert hash(section1) != hash(section2)


class TestDiffPerformance:
    """Test diff performance with larger documents."""

    def test_large_document_diff(self):
        """Test diff with a large document."""
        parser = SectionParser()

        # Generate a large document
        large_doc = "\n\n".join(
            [f"# Section {i}\n\nContent for section {i}" for i in range(100)]
        )

        import time

        start = time.time()
        sections = parser.parse(large_doc)
        elapsed = time.time() - start

        assert len(sections) > 0
        assert elapsed < 1.0  # Should be fast (< 1 second)

    def test_diff_computation_speed(self, tmp_path):
        """Test that diff computation is reasonably fast."""
        from athena.architecture.doc_store import DocumentStore
        from athena.architecture.spec_store import SpecificationStore

        db = TestDatabase(str(tmp_path / "test.db"))
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        doc_store = DocumentStore(db, docs_dir=docs_dir)
        spec_store = SpecificationStore(db)

        # Create document with moderate content
        content = "\n\n".join([f"# Section {i}\n\nContent {i}" for i in range(20)])

        doc = Document(
            project_id=1,
            name="Test Doc",
            doc_type=DocumentType.API_DOC,
            version="1.0.0",
            content=content,
            status=DocumentStatus.DRAFT,
        )
        doc.id = doc_store.create(doc, write_to_file=False)

        # Modified content
        new_content = content + "\n\n# New Section\n\nNew content"

        differ = DocumentDiffer(spec_store=spec_store, doc_store=doc_store)

        import time

        start = time.time()
        diff_result = differ.compute_diff(
            doc_id=doc.id, new_content=new_content, show_cause=False
        )
        elapsed = time.time() - start

        assert diff_result.has_changes
        assert elapsed < 0.5  # Should be very fast (< 500ms)
