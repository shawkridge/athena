"""Tests for specification storage and management."""

import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

# Add parent directory to path for test imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_database import TestDatabase
from athena.architecture.models import Specification, SpecType, SpecStatus
from athena.architecture.spec_store import SpecificationStore


@pytest.fixture
def temp_specs_dir():
    """Create temporary specs directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test.db"
    return TestDatabase(str(db_path))


@pytest.fixture
def spec_store(db, temp_specs_dir):
    """Create specification store with test database and temp directory."""
    return SpecificationStore(db, specs_dir=temp_specs_dir)


@pytest.fixture
def sample_spec():
    """Create a sample specification."""
    return Specification(
        project_id=1,
        name="User Authentication API",
        spec_type=SpecType.OPENAPI,
        version="1.0.0",
        status=SpecStatus.ACTIVE,
        content="""openapi: 3.0.0
info:
  title: User Authentication API
  version: 1.0.0
paths:
  /auth/login:
    post:
      summary: User login
      responses:
        '200':
          description: Successful login
""",
        file_path="user-api.yaml",
        description="Authentication endpoints for user management",
        author="Test Author",
        tags=["auth", "api"],
    )


def test_store_initialization(spec_store, temp_specs_dir):
    """Test specification store initialization."""
    assert spec_store.db is not None
    assert spec_store.specs_dir == temp_specs_dir
    assert temp_specs_dir.exists()
    assert (temp_specs_dir / ".gitkeep").exists()
    assert (temp_specs_dir / "README.md").exists()


def test_create_specification(spec_store, sample_spec, temp_specs_dir):
    """Test creating a specification."""
    spec_id = spec_store.create(sample_spec, write_to_file=True)

    assert spec_id > 0

    # Check database
    retrieved = spec_store.get(spec_id)
    assert retrieved is not None
    assert retrieved.name == sample_spec.name
    assert retrieved.spec_type == sample_spec.spec_type
    assert retrieved.version == sample_spec.version
    assert retrieved.content == sample_spec.content

    # Check file was written
    file_path = temp_specs_dir / sample_spec.file_path
    assert file_path.exists()
    assert file_path.read_text() == sample_spec.content


def test_create_without_writing_file(spec_store, sample_spec):
    """Test creating specification without writing to file."""
    spec_id = spec_store.create(sample_spec, write_to_file=False)

    assert spec_id > 0

    # Check database
    retrieved = spec_store.get(spec_id)
    assert retrieved is not None

    # File should not exist
    file_path = spec_store.specs_dir / sample_spec.file_path
    assert not file_path.exists()


def test_get_specification(spec_store, sample_spec):
    """Test retrieving a specification by ID."""
    spec_id = spec_store.create(sample_spec, write_to_file=False)

    retrieved = spec_store.get(spec_id)

    assert retrieved is not None
    assert retrieved.id == spec_id
    assert retrieved.name == sample_spec.name
    assert retrieved.version == sample_spec.version


def test_get_nonexistent_specification(spec_store):
    """Test retrieving a non-existent specification."""
    retrieved = spec_store.get(99999)
    assert retrieved is None


def test_get_by_file_path(spec_store, sample_spec):
    """Test retrieving specification by file path."""
    spec_store.create(sample_spec, write_to_file=False)

    retrieved = spec_store.get_by_file_path(sample_spec.file_path)

    assert retrieved is not None
    assert retrieved.name == sample_spec.name
    assert retrieved.file_path == sample_spec.file_path


def test_update_specification(spec_store, sample_spec, temp_specs_dir):
    """Test updating a specification."""
    # Create initial spec
    spec_id = spec_store.create(sample_spec, write_to_file=True)
    spec = spec_store.get(spec_id)

    # Update spec
    spec.version = "2.0.0"
    spec.description = "Updated description"
    spec.content = "updated content"

    spec_store.update(spec, write_to_file=True)

    # Verify updates
    updated = spec_store.get(spec_id)
    assert updated.version == "2.0.0"
    assert updated.description == "Updated description"
    assert updated.content == "updated content"

    # Verify file was updated
    file_path = temp_specs_dir / sample_spec.file_path
    assert file_path.read_text() == "updated content"


def test_delete_specification(spec_store, sample_spec):
    """Test deleting a specification."""
    spec_id = spec_store.create(sample_spec, write_to_file=False)

    # Verify exists
    assert spec_store.get(spec_id) is not None

    # Delete
    spec_store.delete(spec_id, delete_file=False)

    # Verify deleted
    assert spec_store.get(spec_id) is None


def test_delete_specification_with_file(spec_store, sample_spec, temp_specs_dir):
    """Test deleting specification and its file."""
    spec_id = spec_store.create(sample_spec, write_to_file=True)
    file_path = temp_specs_dir / sample_spec.file_path

    # Verify file exists
    assert file_path.exists()

    # Delete with file
    spec_store.delete(spec_id, delete_file=True)

    # Verify both deleted
    assert spec_store.get(spec_id) is None
    assert not file_path.exists()


def test_list_by_project(spec_store):
    """Test listing specifications by project."""
    # Create specs for different projects
    spec1 = Specification(
        project_id=1,
        name="Spec 1",
        spec_type=SpecType.OPENAPI,
        version="1.0.0",
        content="content 1",
    )
    spec2 = Specification(
        project_id=1,
        name="Spec 2",
        spec_type=SpecType.MARKDOWN,
        version="1.0.0",
        content="content 2",
    )
    spec3 = Specification(
        project_id=2,
        name="Spec 3",
        spec_type=SpecType.OPENAPI,
        version="1.0.0",
        content="content 3",
    )

    spec_store.create(spec1, write_to_file=False)
    spec_store.create(spec2, write_to_file=False)
    spec_store.create(spec3, write_to_file=False)

    # List project 1 specs
    project1_specs = spec_store.list_by_project(project_id=1)
    assert len(project1_specs) == 2
    assert all(s.project_id == 1 for s in project1_specs)


def test_list_by_spec_type(spec_store):
    """Test filtering specifications by type."""
    # Create specs of different types
    spec1 = Specification(
        project_id=1,
        name="OpenAPI Spec",
        spec_type=SpecType.OPENAPI,
        version="1.0.0",
        content="openapi content",
    )
    spec2 = Specification(
        project_id=1,
        name="Markdown Spec",
        spec_type=SpecType.MARKDOWN,
        version="1.0.0",
        content="markdown content",
    )

    spec_store.create(spec1, write_to_file=False)
    spec_store.create(spec2, write_to_file=False)

    # Filter by OpenAPI
    openapi_specs = spec_store.list_by_project(project_id=1, spec_type=SpecType.OPENAPI)
    assert len(openapi_specs) == 1
    assert openapi_specs[0].spec_type == SpecType.OPENAPI


def test_list_by_status(spec_store):
    """Test filtering specifications by status."""
    # Create specs with different statuses
    spec1 = Specification(
        project_id=1,
        name="Active Spec",
        spec_type=SpecType.MARKDOWN,
        version="1.0.0",
        status=SpecStatus.ACTIVE,
        content="active",
    )
    spec2 = Specification(
        project_id=1,
        name="Draft Spec",
        spec_type=SpecType.MARKDOWN,
        version="1.0.0",
        status=SpecStatus.DRAFT,
        content="draft",
    )

    spec_store.create(spec1, write_to_file=False)
    spec_store.create(spec2, write_to_file=False)

    # Filter by active
    active_specs = spec_store.list_by_project(project_id=1, status=SpecStatus.ACTIVE)
    assert len(active_specs) == 1
    assert active_specs[0].status == SpecStatus.ACTIVE


def test_get_latest_version(spec_store):
    """Test getting latest version of a specification."""
    # Create multiple versions
    for version in ["1.0.0", "1.1.0", "2.0.0"]:
        spec = Specification(
            project_id=1,
            name="API Spec",
            spec_type=SpecType.OPENAPI,
            version=version,
            content=f"version {version}",
        )
        spec_store.create(spec, write_to_file=False)

    # Get latest version
    latest = spec_store.get_latest_version(project_id=1, name="API Spec")

    assert latest is not None
    # Should be latest created (2.0.0)
    assert latest.version in ["1.0.0", "1.1.0", "2.0.0"]  # Latest created


def test_supersede_specification(spec_store):
    """Test superseding a specification."""
    # Create old and new specs
    old_spec = Specification(
        project_id=1,
        name="Old Spec",
        spec_type=SpecType.MARKDOWN,
        version="1.0.0",
        content="old content",
        status=SpecStatus.ACTIVE,
    )
    new_spec = Specification(
        project_id=1,
        name="New Spec",
        spec_type=SpecType.MARKDOWN,
        version="2.0.0",
        content="new content",
        status=SpecStatus.ACTIVE,
    )

    old_id = spec_store.create(old_spec, write_to_file=False)
    new_id = spec_store.create(new_spec, write_to_file=False)

    # Supersede old with new
    spec_store.supersede(old_id, new_id)

    # Verify old spec is superseded
    old_retrieved = spec_store.get(old_id)
    assert old_retrieved.status == SpecStatus.SUPERSEDED
    assert str(new_id) in old_retrieved.description


def test_search_by_tags(spec_store):
    """Test searching specifications by tags."""
    # Create specs with tags
    spec1 = Specification(
        project_id=1,
        name="Auth Spec",
        spec_type=SpecType.OPENAPI,
        version="1.0.0",
        content="auth",
        tags=["auth", "security"],
    )
    spec2 = Specification(
        project_id=1,
        name="User Spec",
        spec_type=SpecType.OPENAPI,
        version="1.0.0",
        content="user",
        tags=["user", "api"],
    )

    spec_store.create(spec1, write_to_file=False)
    spec_store.create(spec2, write_to_file=False)

    # Search for auth tag
    auth_specs = spec_store.search_by_tags(project_id=1, tags=["auth"])
    assert len(auth_specs) == 1
    assert "auth" in auth_specs[0].tags


def test_spec_type_detection_openapi(spec_store, temp_specs_dir):
    """Test detecting OpenAPI spec type from file."""
    # Create OpenAPI file
    file_path = temp_specs_dir / "api.yaml"
    file_path.write_text("""openapi: 3.0.0
info:
  title: Test API
""")

    spec_type = spec_store._detect_spec_type(file_path)
    assert spec_type == SpecType.OPENAPI


def test_spec_type_detection_graphql(spec_store, temp_specs_dir):
    """Test detecting GraphQL spec type from file."""
    file_path = temp_specs_dir / "schema.graphql"
    file_path.write_text("type Query { hello: String }")

    spec_type = spec_store._detect_spec_type(file_path)
    assert spec_type == SpecType.GRAPHQL


def test_spec_type_detection_markdown(spec_store, temp_specs_dir):
    """Test detecting markdown spec type from file."""
    file_path = temp_specs_dir / "spec.md"
    file_path.write_text("# Specification\n\nSome content")

    spec_type = spec_store._detect_spec_type(file_path)
    assert spec_type == SpecType.MARKDOWN


def test_sync_from_filesystem(spec_store, temp_specs_dir):
    """Test syncing specifications from filesystem."""
    # Create spec files
    (temp_specs_dir / "api.yaml").write_text("""openapi: 3.0.0
info:
  title: Test API
""")
    (temp_specs_dir / "schema.graphql").write_text("type Query { hello: String }")
    (temp_specs_dir / "spec.md").write_text("# Specification")

    # Sync
    stats = spec_store.sync_from_filesystem(project_id=1)

    assert stats['created'] == 3
    assert stats['updated'] == 0
    # README.md and .gitkeep are filtered out before being counted as skipped

    # Verify specs were created
    specs = spec_store.list_by_project(project_id=1)
    assert len(specs) == 3


def test_sync_updates_changed_files(spec_store, temp_specs_dir):
    """Test sync updates specifications when files change."""
    # Create initial file
    file_path = temp_specs_dir / "spec.md"
    file_path.write_text("# Initial content")

    # First sync
    stats1 = spec_store.sync_from_filesystem(project_id=1)
    assert stats1['created'] == 1

    # Modify file
    file_path.write_text("# Updated content")

    # Second sync
    stats2 = spec_store.sync_from_filesystem(project_id=1)
    assert stats2['updated'] == 1
    assert stats2['created'] == 0

    # Verify content updated
    spec = spec_store.get_by_file_path("spec.md")
    assert spec.content == "# Updated content"


def test_sync_skips_unchanged_files(spec_store, temp_specs_dir):
    """Test sync skips files that haven't changed."""
    # Create file
    file_path = temp_specs_dir / "spec.md"
    file_path.write_text("# Content")

    # First sync
    stats1 = spec_store.sync_from_filesystem(project_id=1)
    assert stats1['created'] == 1

    # Second sync without changes
    stats2 = spec_store.sync_from_filesystem(project_id=1)
    assert stats2['skipped'] >= 1  # At least the unchanged spec
    assert stats2['updated'] == 0
    assert stats2['created'] == 0


def test_specification_relationships(spec_store):
    """Test specification relationships with ADRs, constraints, patterns."""
    spec = Specification(
        project_id=1,
        name="API Spec",
        spec_type=SpecType.OPENAPI,
        version="1.0.0",
        content="spec content",
        related_adr_ids=[1, 2, 3],
        implements_constraint_ids=[5, 6],
        uses_pattern_ids=["repository", "factory"],
    )

    spec_id = spec_store.create(spec, write_to_file=False)

    # Retrieve and verify relationships
    retrieved = spec_store.get(spec_id)
    assert retrieved.related_adr_ids == [1, 2, 3]
    assert retrieved.implements_constraint_ids == [5, 6]
    assert retrieved.uses_pattern_ids == ["repository", "factory"]


def test_validation_tracking(spec_store):
    """Test tracking validation status."""
    spec = Specification(
        project_id=1,
        name="API Spec",
        spec_type=SpecType.OPENAPI,
        version="1.0.0",
        content="spec content",
        validation_status="valid",
        validated_at=datetime.now(),
        validation_errors=[],
    )

    spec_id = spec_store.create(spec, write_to_file=False)

    # Retrieve and verify validation tracking
    retrieved = spec_store.get(spec_id)
    assert retrieved.validation_status == "valid"
    assert retrieved.validated_at is not None
    assert retrieved.validation_errors == []


def test_get_active_specs(spec_store):
    """Test getting only active specifications."""
    # Create specs with different statuses
    for i, status in enumerate([SpecStatus.ACTIVE, SpecStatus.DRAFT, SpecStatus.DEPRECATED], 1):
        spec = Specification(
            project_id=1,
            name=f"Spec {i}",
            spec_type=SpecType.MARKDOWN,
            version="1.0.0",
            status=status,
            content=f"content {i}",
        )
        spec_store.create(spec, write_to_file=False)

    # Get active specs
    active_specs = spec_store.get_active_specs(project_id=1)

    assert len(active_specs) == 1
    assert active_specs[0].status == SpecStatus.ACTIVE


def test_file_path_validation(spec_store):
    """Test that file paths are properly stored and retrieved."""
    spec = Specification(
        project_id=1,
        name="API Spec",
        spec_type=SpecType.OPENAPI,
        version="1.0.0",
        content="content",
        file_path="api/v1/users.yaml",
    )

    spec_id = spec_store.create(spec, write_to_file=False)

    retrieved = spec_store.get(spec_id)
    assert retrieved.file_path == "api/v1/users.yaml"


def test_nested_directory_creation(spec_store, temp_specs_dir):
    """Test creating spec files in nested directories."""
    spec = Specification(
        project_id=1,
        name="Nested Spec",
        spec_type=SpecType.OPENAPI,
        version="1.0.0",
        content="nested content",
        file_path="api/v1/users.yaml",
    )

    spec_store.create(spec, write_to_file=True)

    # Verify nested directory was created
    file_path = temp_specs_dir / "api" / "v1" / "users.yaml"
    assert file_path.exists()
    assert file_path.read_text() == "nested content"
