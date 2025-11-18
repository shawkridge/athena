"""Tests for document storage."""

import sys
import pytest
from pathlib import Path
from datetime import datetime

# Add parent directory to path for test imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_database import TestDatabase
from athena.architecture.doc_store import DocumentStore
from athena.architecture.models import Document, DocumentType, DocumentStatus


@pytest.fixture
def db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test.db"
    return TestDatabase(str(db_path))


@pytest.fixture
def doc_store(db, tmp_path):
    """Create document store with test database."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    return DocumentStore(db, docs_dir=docs_dir)


def test_store_initialization(doc_store):
    """Test that store initializes schema correctly."""
    # Should be able to create documents without error
    assert doc_store.db is not None
    assert doc_store.docs_dir.name == "docs"


def test_create_document(doc_store):
    """Test creating a document."""
    doc = Document(
        project_id=1,
        name="User API Documentation",
        doc_type=DocumentType.API_DOC,
        version="1.0.0",
        status=DocumentStatus.DRAFT,
        content="# User API\n\nThis is the API documentation.",
        description="Documentation for User API",
    )

    doc_id = doc_store.create(doc, write_to_file=False)

    assert doc_id > 0
    assert isinstance(doc_id, int)


def test_create_document_with_file(doc_store):
    """Test creating a document with filesystem write."""
    doc = Document(
        project_id=1,
        name="API Guide",
        doc_type=DocumentType.API_GUIDE,
        version="1.0.0",
        content="# API Integration Guide\n\nHow to integrate...",
        file_path="api/integration-guide.md",
    )

    doc_id = doc_store.create(doc, write_to_file=True)

    # Check file was created
    file_path = doc_store.docs_dir / "api/integration-guide.md"
    assert file_path.exists()
    assert "API Integration Guide" in file_path.read_text()

    # Check database
    retrieved = doc_store.get(doc_id)
    assert retrieved is not None
    assert retrieved.name == "API Guide"


def test_get_document(doc_store):
    """Test retrieving a document by ID."""
    doc = Document(
        project_id=1,
        name="Test Doc",
        doc_type=DocumentType.TDD,
        version="1.0.0",
        content="# Technical Design",
    )

    doc_id = doc_store.create(doc, write_to_file=False)
    retrieved = doc_store.get(doc_id)

    assert retrieved is not None
    assert retrieved.id == doc_id
    assert retrieved.name == "Test Doc"
    assert retrieved.doc_type == DocumentType.TDD
    assert retrieved.version == "1.0.0"


def test_get_nonexistent_document(doc_store):
    """Test getting a document that doesn't exist."""
    result = doc_store.get(9999)
    assert result is None


def test_get_by_file_path(doc_store):
    """Test retrieving document by file path."""
    doc = Document(
        project_id=1,
        name="Deployment Guide",
        doc_type=DocumentType.DEPLOYMENT_GUIDE,
        version="1.0.0",
        content="# Deployment\n\nHow to deploy...",
        file_path="ops/deployment.md",
    )

    doc_id = doc_store.create(doc, write_to_file=False)
    retrieved = doc_store.get_by_file_path("ops/deployment.md")

    assert retrieved is not None
    assert retrieved.id == doc_id
    assert retrieved.file_path == "ops/deployment.md"


def test_update_document(doc_store):
    """Test updating a document."""
    doc = Document(
        project_id=1,
        name="API Docs",
        doc_type=DocumentType.API_DOC,
        version="1.0.0",
        content="# Version 1.0",
    )

    doc_id = doc_store.create(doc, write_to_file=False)

    # Update the document
    doc.id = doc_id
    doc.version = "2.0.0"
    doc.content = "# Version 2.0 - Updated"
    doc.status = DocumentStatus.PUBLISHED

    doc_store.update(doc, write_to_file=False)

    # Retrieve and verify
    updated = doc_store.get(doc_id)
    assert updated.version == "2.0.0"
    assert "Version 2.0" in updated.content
    assert updated.status == DocumentStatus.PUBLISHED


def test_delete_document(doc_store):
    """Test deleting a document."""
    doc = Document(
        project_id=1,
        name="Temporary Doc",
        doc_type=DocumentType.RUNBOOK,
        version="1.0.0",
        content="# Temporary",
    )

    doc_id = doc_store.create(doc, write_to_file=False)

    # Delete the document
    result = doc_store.delete(doc_id)
    assert result is True

    # Verify it's gone
    retrieved = doc_store.get(doc_id)
    assert retrieved is None


def test_delete_document_with_file(doc_store):
    """Test deleting a document and its file."""
    doc = Document(
        project_id=1,
        name="Temp Guide",
        doc_type=DocumentType.API_GUIDE,
        version="1.0.0",
        content="# Temporary Guide",
        file_path="temp/guide.md",
    )

    doc_id = doc_store.create(doc, write_to_file=True)
    file_path = doc_store.docs_dir / "temp/guide.md"

    # Verify file exists
    assert file_path.exists()

    # Delete with file
    doc_store.delete(doc_id, delete_file=True)

    # Verify both are gone
    assert not file_path.exists()
    assert doc_store.get(doc_id) is None


def test_list_by_project(doc_store):
    """Test listing documents by project."""
    # Create multiple documents
    for i in range(3):
        doc = Document(
            project_id=1,
            name=f"Doc {i}",
            doc_type=DocumentType.API_DOC,
            version="1.0.0",
            content=f"# Document {i}",
        )
        doc_store.create(doc, write_to_file=False)

    docs = doc_store.list_by_project(project_id=1)

    assert len(docs) == 3
    assert all(doc.project_id == 1 for doc in docs)


def test_list_by_doc_type(doc_store):
    """Test filtering documents by type."""
    # Create docs of different types
    doc_store.create(
        Document(
            project_id=1,
            name="API Doc",
            doc_type=DocumentType.API_DOC,
            version="1.0.0",
            content="# API",
        ),
        write_to_file=False,
    )

    doc_store.create(
        Document(
            project_id=1,
            name="TDD",
            doc_type=DocumentType.TDD,
            version="1.0.0",
            content="# TDD",
        ),
        write_to_file=False,
    )

    # Filter by API_DOC type
    api_docs = doc_store.list_by_project(project_id=1, doc_type=DocumentType.API_DOC)

    assert len(api_docs) == 1
    assert api_docs[0].doc_type == DocumentType.API_DOC


def test_list_by_status(doc_store):
    """Test filtering documents by status."""
    # Create docs with different statuses
    doc_store.create(
        Document(
            project_id=1,
            name="Draft Doc",
            doc_type=DocumentType.API_DOC,
            version="1.0.0",
            status=DocumentStatus.DRAFT,
            content="# Draft",
        ),
        write_to_file=False,
    )

    doc_store.create(
        Document(
            project_id=1,
            name="Published Doc",
            doc_type=DocumentType.API_DOC,
            version="1.0.0",
            status=DocumentStatus.PUBLISHED,
            content="# Published",
        ),
        write_to_file=False,
    )

    # Filter by PUBLISHED status
    published = doc_store.list_by_project(project_id=1, status=DocumentStatus.PUBLISHED)

    assert len(published) == 1
    assert published[0].status == DocumentStatus.PUBLISHED


def test_list_by_spec(doc_store):
    """Test listing documents generated from a spec."""
    # Create docs based on different specs
    doc_store.create(
        Document(
            project_id=1,
            name="API Doc from Spec 5",
            doc_type=DocumentType.API_DOC,
            version="1.0.0",
            content="# API",
            based_on_spec_ids=[5],
        ),
        write_to_file=False,
    )

    doc_store.create(
        Document(
            project_id=1,
            name="TDD from Spec 5 and 8",
            doc_type=DocumentType.TDD,
            version="1.0.0",
            content="# TDD",
            based_on_spec_ids=[5, 8],
        ),
        write_to_file=False,
    )

    doc_store.create(
        Document(
            project_id=1,
            name="Unrelated Doc",
            doc_type=DocumentType.RUNBOOK,
            version="1.0.0",
            content="# Runbook",
            based_on_spec_ids=[],
        ),
        write_to_file=False,
    )

    # Get docs based on spec 5
    docs_from_spec_5 = doc_store.list_by_spec(spec_id=5)

    assert len(docs_from_spec_5) == 2
    assert all(5 in doc.based_on_spec_ids for doc in docs_from_spec_5)


def test_document_relationships(doc_store):
    """Test document relationship tracking."""
    doc = Document(
        project_id=1,
        name="Comprehensive Doc",
        doc_type=DocumentType.TDD,
        version="1.0.0",
        content="# TDD",
        based_on_spec_ids=[5, 8],
        based_on_doc_ids=[10],  # PRD
        related_adr_ids=[12, 15],
        implements_constraint_ids=[3, 7],
    )

    doc_id = doc_store.create(doc, write_to_file=False)
    retrieved = doc_store.get(doc_id)

    assert retrieved.based_on_spec_ids == [5, 8]
    assert retrieved.based_on_doc_ids == [10]
    assert retrieved.related_adr_ids == [12, 15]
    assert retrieved.implements_constraint_ids == [3, 7]


def test_generation_metadata(doc_store):
    """Test generation metadata tracking."""
    doc = Document(
        project_id=1,
        name="AI Generated Doc",
        doc_type=DocumentType.API_DOC,
        version="1.0.0",
        content="# Generated API Docs",
        generated_by="ai",
        generation_model="claude-3-5-sonnet-20250219",
        generation_prompt="Generate API docs from OpenAPI spec",
        sync_hash="abc123def456",
    )

    doc_id = doc_store.create(doc, write_to_file=False)
    retrieved = doc_store.get(doc_id)

    assert retrieved.generated_by == "ai"
    assert retrieved.generation_model == "claude-3-5-sonnet-20250219"
    assert "Generate API docs" in retrieved.generation_prompt
    assert retrieved.sync_hash == "abc123def456"


def test_review_tracking(doc_store):
    """Test review workflow tracking."""
    doc = Document(
        project_id=1,
        name="Reviewed Doc",
        doc_type=DocumentType.HLD,
        version="1.0.0",
        content="# High-Level Design",
        author="Alice",
        reviewers=["Bob", "Charlie"],
        tags=["architecture", "design"],
    )

    doc_id = doc_store.create(doc, write_to_file=False)
    retrieved = doc_store.get(doc_id)

    assert retrieved.author == "Alice"
    assert "Bob" in retrieved.reviewers
    assert "Charlie" in retrieved.reviewers
    assert "architecture" in retrieved.tags


def test_timestamps(doc_store):
    """Test that timestamps are set correctly."""
    doc = Document(
        project_id=1,
        name="Timestamped Doc",
        doc_type=DocumentType.API_DOC,
        version="1.0.0",
        content="# Doc",
    )

    doc_id = doc_store.create(doc, write_to_file=False)
    retrieved = doc_store.get(doc_id)

    assert retrieved.created_at is not None
    assert retrieved.updated_at is not None
    assert isinstance(retrieved.created_at, datetime)
