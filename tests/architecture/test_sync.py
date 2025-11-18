"""Tests for drift detection and sync functionality."""

import sys
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

# Add parent directory to path for test imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_database import TestDatabase
from athena.architecture.models import (
    Document,
    DocumentType,
    DocumentStatus,
    Specification,
    SpecType,
    SpecStatus,
)
from athena.architecture.sync import (
    DriftDetector,
    DriftStatus,
    SyncManager,
    SyncStrategy,
    StalenessChecker,
    StalenessLevel,
)


# ========================================================================
# Fixtures
# ========================================================================

@pytest.fixture
def db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test.db"
    return TestDatabase(str(db_path))


@pytest.fixture
def spec_store(db):
    """Create spec store with schema."""
    from athena.architecture.spec_store import SpecificationStore
    return SpecificationStore(db)


@pytest.fixture
def doc_store(db, tmp_path):
    """Create doc store with schema."""
    from athena.architecture.doc_store import DocumentStore
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    return DocumentStore(db, docs_dir=docs_dir)


@pytest.fixture
def sample_spec(spec_store):
    """Create sample specification."""
    spec = Specification(
        project_id=1,
        name="User API",
        spec_type=SpecType.OPENAPI,
        version="1.0.0",
        status=SpecStatus.ACTIVE,
        content='{"openapi": "3.0.0", "info": {"title": "User API"}}',
        description="User management API",
    )
    spec.id = spec_store.create(spec, write_to_file=False)
    return spec


@pytest.fixture
def sample_doc(doc_store, sample_spec):
    """Create sample document based on spec."""
    doc = Document(
        project_id=1,
        name="User API Documentation",
        doc_type=DocumentType.API_DOC,
        version="1.0.0",
        status=DocumentStatus.DRAFT,
        content="# User API Documentation\n\nSample content",
        based_on_spec_ids=[sample_spec.id],
        generated_by="ai",
        sync_hash="abc123def456",  # Mock hash
        last_synced_at=datetime.now() - timedelta(days=5),  # 5 days ago
    )
    doc.id = doc_store.create(doc, write_to_file=False)
    return doc


# ========================================================================
# Drift Detector Tests
# ========================================================================

def test_drift_detector_initialization(spec_store, doc_store):
    """Test drift detector initializes correctly."""
    detector = DriftDetector(spec_store, doc_store)

    assert detector.spec_store == spec_store
    assert detector.doc_store == doc_store


def test_check_document_missing_hash(doc_store):
    """Test checking document with no sync hash."""
    # Create document without sync hash
    doc = Document(
        project_id=1,
        name="Test Doc",
        doc_type=DocumentType.API_DOC,
        version="1.0.0",
        status=DocumentStatus.DRAFT,
        content="# Test",
    )
    doc.id = doc_store.create(doc, write_to_file=False)

    detector = DriftDetector(Mock(), doc_store)
    result = detector.check_document(doc.id)

    assert result.status == DriftStatus.MISSING_HASH
    assert not result.needs_regeneration  # Can't regenerate without baseline


def test_check_document_in_sync(spec_store, doc_store, sample_spec, sample_doc):
    """Test checking document that's in sync."""
    detector = DriftDetector(spec_store, doc_store)

    # Compute actual hash and update document
    actual_hash = detector.compute_document_hash(sample_doc.id)
    sample_doc.sync_hash = actual_hash
    doc_store.update(sample_doc, write_to_file=False)

    result = detector.check_document(sample_doc.id)

    assert result.status == DriftStatus.IN_SYNC
    assert not result.needs_regeneration
    assert result.current_hash == result.stored_hash


def test_check_document_drifted(spec_store, doc_store, sample_spec, sample_doc):
    """Test checking document that has drifted."""
    detector = DriftDetector(spec_store, doc_store)

    # Modify spec to cause drift
    sample_spec.content = '{"openapi": "3.0.0", "info": {"title": "Updated API"}}'
    spec_store.update(sample_spec, write_to_file=False)

    result = detector.check_document(sample_doc.id)

    assert result.status == DriftStatus.DRIFTED
    assert result.needs_regeneration
    assert result.current_hash != result.stored_hash


def test_check_document_stale(spec_store, doc_store, sample_spec):
    """Test checking document that's stale but not drifted."""
    # Create document with old sync date
    doc = Document(
        project_id=1,
        name="Stale Doc",
        doc_type=DocumentType.API_DOC,
        version="1.0.0",
        status=DocumentStatus.DRAFT,
        content="# Stale",
        based_on_spec_ids=[sample_spec.id],
        sync_hash="test_hash",
        last_synced_at=datetime.now() - timedelta(days=60),  # 60 days ago
    )
    doc.id = doc_store.create(doc, write_to_file=False)

    detector = DriftDetector(spec_store, doc_store)

    # Update hash to match current (no drift, just stale)
    actual_hash = detector.compute_document_hash(doc.id)
    doc.sync_hash = actual_hash
    doc_store.update(doc, write_to_file=False)

    result = detector.check_document(doc.id, staleness_threshold_days=30)

    assert result.status == DriftStatus.STALE
    assert result.needs_regeneration
    assert result.days_since_sync == 60


def test_check_project(spec_store, doc_store, sample_spec):
    """Test checking all documents in a project."""
    # Create multiple documents
    for i in range(3):
        doc = Document(
            project_id=1,
            name=f"Doc {i}",
            doc_type=DocumentType.API_DOC,
            version="1.0.0",
            status=DocumentStatus.DRAFT,
            content=f"# Doc {i}",
            based_on_spec_ids=[sample_spec.id],
            sync_hash=f"hash_{i}",
            last_synced_at=datetime.now() - timedelta(days=i * 10),
        )
        doc_store.create(doc, write_to_file=False)

    detector = DriftDetector(spec_store, doc_store)
    results = detector.check_project(project_id=1)

    assert len(results) == 3


def test_compute_specs_hash(spec_store, doc_store):
    """Test computing hash from multiple specs."""
    # Create specs
    specs = []
    for i in range(2):
        spec = Specification(
            project_id=1,
            name=f"API {i}",
            spec_type=SpecType.OPENAPI,
            version="1.0.0",
            status=SpecStatus.ACTIVE,
            content=f'{{"spec": {i}}}',
        )
        spec.id = spec_store.create(spec, write_to_file=False)
        specs.append(spec)

    detector = DriftDetector(spec_store, doc_store)
    hash1 = detector._compute_specs_hash(specs)

    # Hash should be deterministic
    hash2 = detector._compute_specs_hash(specs)
    assert hash1 == hash2

    # Hash should change if content changes
    specs[0].content = '{"spec": "modified"}'
    hash3 = detector._compute_specs_hash(specs)
    assert hash3 != hash1


# ========================================================================
# Staleness Checker Tests
# ========================================================================

def test_staleness_checker_initialization(doc_store):
    """Test staleness checker initializes correctly."""
    checker = StalenessChecker(doc_store)

    assert checker.doc_store == doc_store
    assert checker.thresholds is not None


def test_check_document_fresh(doc_store):
    """Test checking recently synced document."""
    doc = Document(
        project_id=1,
        name="Fresh Doc",
        doc_type=DocumentType.API_DOC,
        version="1.0.0",
        status=DocumentStatus.DRAFT,
        content="# Fresh",
        last_synced_at=datetime.now() - timedelta(days=2),  # 2 days ago
    )
    doc.id = doc_store.create(doc, write_to_file=False)

    checker = StalenessChecker(doc_store)
    result = checker.check_document(doc.id)

    assert result.level == StalenessLevel.FRESH
    assert not result.needs_review
    assert result.priority == "low"


def test_check_document_stale(doc_store):
    """Test checking stale document."""
    doc = Document(
        project_id=1,
        name="Stale Doc",
        doc_type=DocumentType.API_DOC,
        version="1.0.0",
        status=DocumentStatus.DRAFT,
        content="# Stale",
        last_synced_at=datetime.now() - timedelta(days=60),  # 60 days ago
    )
    doc.id = doc_store.create(doc, write_to_file=False)

    checker = StalenessChecker(doc_store)
    result = checker.check_document(doc.id)

    assert result.level == StalenessLevel.STALE
    assert result.needs_review
    assert result.priority == "medium"


def test_check_document_never_synced(doc_store):
    """Test checking document that was never synced."""
    doc = Document(
        project_id=1,
        name="Never Synced",
        doc_type=DocumentType.API_DOC,
        version="1.0.0",
        status=DocumentStatus.DRAFT,
        content="# Never Synced",
    )
    doc.id = doc_store.create(doc, write_to_file=False)

    checker = StalenessChecker(doc_store)
    result = checker.check_document(doc.id)

    assert result.level == StalenessLevel.NEVER_SYNCED
    assert result.needs_review
    assert result.priority == "high"


def test_check_project_staleness(doc_store):
    """Test checking staleness for all documents in project."""
    # Create documents with varying staleness
    sync_dates = [
        datetime.now() - timedelta(days=2),   # Fresh
        datetime.now() - timedelta(days=15),  # Aging
        datetime.now() - timedelta(days=60),  # Stale
        None,                                  # Never synced
    ]

    for i, sync_date in enumerate(sync_dates):
        doc = Document(
            project_id=1,
            name=f"Doc {i}",
            doc_type=DocumentType.API_DOC,
            version="1.0.0",
            status=DocumentStatus.DRAFT,
            content=f"# Doc {i}",
            last_synced_at=sync_date,
        )
        doc_store.create(doc, write_to_file=False)

    checker = StalenessChecker(doc_store)
    results = checker.check_project(project_id=1, include_fresh=True)

    assert len(results) == 4

    # Check summary
    summary = checker.get_summary(results)
    assert summary["total"] == 4
    assert summary["fresh"] == 1
    assert summary["aging"] == 1
    assert summary["stale"] == 1
    assert summary["never_synced"] == 1


# ========================================================================
# Sync Manager Tests
# ========================================================================

@pytest.mark.skip(reason="Requires AI generator mock")
def test_sync_manager_initialization(spec_store, doc_store):
    """Test sync manager initializes correctly."""
    manager = SyncManager(spec_store, doc_store)

    assert manager.spec_store == spec_store
    assert manager.doc_store == doc_store
    assert manager.drift_detector is not None


@pytest.mark.skip(reason="Requires AI generator mock")
def test_sync_document_dry_run(spec_store, doc_store, sample_doc):
    """Test syncing document in dry-run mode."""
    manager = SyncManager(spec_store, doc_store)

    result = manager.sync_document(
        doc_id=sample_doc.id,
        dry_run=True
    )

    assert result.success
    assert not result.regenerated
    assert result.document.id == sample_doc.id


def test_sync_get_summary():
    """Test getting summary from sync results."""
    from athena.architecture.sync.sync_manager import SyncResult

    results = [
        SyncResult(
            document=Mock(id=1, name="Doc 1"),
            success=True,
            strategy=SyncStrategy.REGENERATE,
            regenerated=True,
            generation_time_seconds=2.5
        ),
        SyncResult(
            document=Mock(id=2, name="Doc 2"),
            success=True,
            strategy=SyncStrategy.SKIP,
        ),
        SyncResult(
            document=Mock(id=3, name="Doc 3"),
            success=False,
            strategy=SyncStrategy.REGENERATE,
            error="Failed"
        ),
    ]

    manager = SyncManager(Mock(), Mock())
    summary = manager.get_sync_summary(results)

    assert summary["total"] == 3
    assert summary["successful"] == 2
    assert summary["failed"] == 1
    assert summary["regenerated"] == 1
    assert summary["skipped"] == 1
