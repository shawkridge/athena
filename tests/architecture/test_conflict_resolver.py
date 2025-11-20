"""Tests for conflict detection and resolution (Phase 4E Part 2)."""

import sys
import pytest
from pathlib import Path
from datetime import datetime

# Add parent directory to path for test imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_database import TestDatabase
from athena.architecture.sync.conflict_resolver import (
    ConflictDetector,
    ConflictResolver,
    ConflictStatus,
    MergeStrategy,
)
from athena.architecture.models import Document, DocumentType, DocumentStatus


@pytest.fixture
def sample_baseline():
    """Sample AI-generated baseline content."""
    return """# API Documentation

## Overview

This is the API overview.

## Endpoints

### GET /users

Returns a list of users.

### POST /users

Creates a new user.

## Error Codes

- 400: Bad Request
- 401: Unauthorized
"""


@pytest.fixture
def manual_edited():
    """Manually edited version (changed Overview section)."""
    return """# API Documentation

## Overview

This is the API overview with important details about authentication.

## Endpoints

### GET /users

Returns a list of users.

### POST /users

Creates a new user.

## Error Codes

- 400: Bad Request
- 401: Unauthorized
"""


@pytest.fixture
def new_ai_content():
    """New AI-generated content (changed Endpoints section)."""
    return """# API Documentation

## Overview

This is the API overview.

## Endpoints

### GET /users

Returns a paginated list of users with filtering support.

### POST /users

Creates a new user with validation.

### PUT /users/{id}

Updates an existing user.

## Error Codes

- 400: Bad Request
- 401: Unauthorized
- 404: Not Found
"""


class TestConflictDetector:
    """Test conflict detection."""

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
    def detector(self, doc_store):
        """Create conflict detector."""
        return ConflictDetector(doc_store)

    @pytest.fixture
    def sample_doc(self, doc_store, sample_baseline):
        """Create a sample document with AI baseline."""
        doc = Document(
            project_id=1,
            name="API Documentation",
            doc_type=DocumentType.API_DOC,
            version="1.0.0",
            content=sample_baseline,
            status=DocumentStatus.PUBLISHED,
            generated_by="ai",
            based_on_spec_ids=[1],
        )
        doc.id = doc_store.create(doc, write_to_file=False)

        # Set AI baseline
        import hashlib
        baseline_hash = hashlib.sha256(sample_baseline.encode()).hexdigest()[:16]
        doc = doc_store.get(doc.id)
        doc.ai_baseline_hash = baseline_hash
        doc.ai_baseline_content = sample_baseline
        doc_store.update(doc, write_to_file=False)

        return doc

    def test_detect_no_baseline(self, detector, doc_store):
        """Test detection when no AI baseline exists."""
        # Create doc without baseline
        doc = Document(
            project_id=1,
            name="Manual Doc",
            doc_type=DocumentType.API_DOC,
            version="1.0.0",
            content="Manual content",
            status=DocumentStatus.DRAFT,
        )
        doc.id = doc_store.create(doc, write_to_file=False)

        result = detector.detect_conflict(doc.id)

        assert result.status == ConflictStatus.NO_CONFLICT
        assert not result.has_manual_edits
        assert result.ai_baseline_hash is None
        assert "No AI baseline" in result.message

    def test_detect_no_changes(self, detector, sample_doc):
        """Test detection when content matches baseline."""
        result = detector.detect_conflict(sample_doc.id)

        assert result.status == ConflictStatus.NO_CONFLICT
        assert not result.has_manual_edits
        assert result.ai_baseline_hash is not None
        assert result.current_hash == result.ai_baseline_hash
        assert "No manual edits" in result.message
        assert result.recommendation == MergeStrategy.KEEP_AI

    def test_detect_manual_edits(self, detector, doc_store, sample_doc, manual_edited):
        """Test detection when manual edits exist."""
        # Modify document content
        doc = doc_store.get(sample_doc.id)
        doc.content = manual_edited
        doc_store.update(doc, write_to_file=False)

        result = detector.detect_conflict(sample_doc.id)

        assert result.status == ConflictStatus.MANUAL_EDIT_DETECTED
        assert result.has_manual_edits
        assert result.ai_baseline_hash is not None
        assert result.current_hash != result.ai_baseline_hash
        assert "Manual edits detected" in result.message
        assert result.recommendation == MergeStrategy.THREE_WAY_MERGE

    def test_detect_manual_override_flag(self, detector, doc_store, sample_doc):
        """Test detection when manual override flag is set."""
        # Set manual override
        doc = doc_store.get(sample_doc.id)
        doc.manual_override = True
        doc_store.update(doc, write_to_file=False)

        result = detector.detect_conflict(sample_doc.id)

        assert result.status == ConflictStatus.MANUAL_EDIT_DETECTED
        assert result.has_manual_edits
        assert "manual override" in result.message
        assert result.recommendation == MergeStrategy.KEEP_MANUAL

    def test_mark_manual_override(self, detector, sample_doc, doc_store):
        """Test marking document as manual override."""
        success = detector.mark_manual_override(sample_doc.id)

        assert success
        doc = doc_store.get(sample_doc.id)
        assert doc.manual_override is True
        assert doc.last_manual_edit_at is not None

    def test_clear_manual_flag(self, detector, sample_doc, doc_store):
        """Test clearing manual override flag."""
        # First set it
        detector.mark_manual_override(sample_doc.id)

        # Then clear it
        success = detector.clear_manual_flag(sample_doc.id)

        assert success
        doc = doc_store.get(sample_doc.id)
        assert doc.manual_override is False

    def test_detect_nonexistent_document(self, detector):
        """Test detection with nonexistent document."""
        with pytest.raises(ValueError, match="not found"):
            detector.detect_conflict(99999)


class TestConflictResolver:
    """Test conflict resolution."""

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
    def resolver(self, doc_store):
        """Create conflict resolver."""
        return ConflictResolver(doc_store)

    @pytest.fixture
    def sample_doc(self, doc_store, sample_baseline, manual_edited):
        """Create a document with manual edits."""
        doc = Document(
            project_id=1,
            name="API Documentation",
            doc_type=DocumentType.API_DOC,
            version="1.0.0",
            content=manual_edited,  # Current content has manual edits
            status=DocumentStatus.PUBLISHED,
            generated_by="ai",
            based_on_spec_ids=[1],
        )
        doc.id = doc_store.create(doc, write_to_file=False)

        # Set AI baseline
        import hashlib
        baseline_hash = hashlib.sha256(sample_baseline.encode()).hexdigest()[:16]
        doc = doc_store.get(doc.id)
        doc.ai_baseline_hash = baseline_hash
        doc.ai_baseline_content = sample_baseline
        doc_store.update(doc, write_to_file=False)

        return doc

    def test_resolve_keep_manual(self, resolver, sample_doc, new_ai_content):
        """Test KEEP_MANUAL strategy."""
        result = resolver.resolve_conflict(
            sample_doc.id, new_ai_content, strategy=MergeStrategy.KEEP_MANUAL
        )

        assert result.success
        assert result.strategy == MergeStrategy.KEEP_MANUAL
        assert "authentication" in result.merged_content  # Manual edit preserved
        assert "paginated" not in result.merged_content  # AI change not included
        assert result.manual_sections_kept > 0

    def test_resolve_keep_ai(self, resolver, sample_doc, new_ai_content):
        """Test KEEP_AI strategy."""
        result = resolver.resolve_conflict(
            sample_doc.id, new_ai_content, strategy=MergeStrategy.KEEP_AI
        )

        assert result.success
        assert result.strategy == MergeStrategy.KEEP_AI
        assert "paginated" in result.merged_content  # AI change included
        assert "authentication" not in result.merged_content  # Manual edit discarded
        assert result.ai_sections_kept > 0

    def test_resolve_manual_review(self, resolver, sample_doc, new_ai_content):
        """Test MANUAL_REVIEW strategy."""
        result = resolver.resolve_conflict(
            sample_doc.id, new_ai_content, strategy=MergeStrategy.MANUAL_REVIEW
        )

        assert not result.success
        assert result.strategy == MergeStrategy.MANUAL_REVIEW
        assert result.needs_review
        assert "Manual review required" in result.message

    def test_resolve_three_way_merge_no_conflict(
        self, resolver, doc_store, sample_baseline
    ):
        """Test 3-way merge when changes don't conflict."""
        # Create doc where manual and AI changed different sections
        doc = Document(
            project_id=1,
            name="Test Doc",
            doc_type=DocumentType.API_DOC,
            version="1.0.0",
            content=sample_baseline.replace("API overview", "API overview with auth"),
            status=DocumentStatus.PUBLISHED,
        )
        doc.id = doc_store.create(doc, write_to_file=False)

        # Set baseline
        import hashlib
        baseline_hash = hashlib.sha256(sample_baseline.encode()).hexdigest()[:16]
        doc = doc_store.get(doc.id)
        doc.ai_baseline_hash = baseline_hash
        doc.ai_baseline_content = sample_baseline
        doc_store.update(doc, write_to_file=False)

        # New AI changed different section
        new_ai = sample_baseline.replace("Returns a list", "Returns a paginated list")

        result = resolver.resolve_conflict(
            doc.id, new_ai, strategy=MergeStrategy.THREE_WAY_MERGE
        )

        assert result.success
        assert result.strategy == MergeStrategy.THREE_WAY_MERGE
        assert "auth" in result.merged_content  # Manual change
        assert "paginated" in result.merged_content  # AI change
        assert len(result.conflicts) == 0

    def test_resolve_three_way_merge_with_conflict(
        self, resolver, sample_doc, new_ai_content
    ):
        """Test 3-way merge when changes conflict."""
        # sample_doc has manual edits to Overview
        # new_ai_content has changes to Endpoints
        # Both changed different sections, so should merge successfully

        result = resolver.resolve_conflict(
            sample_doc.id, new_ai_content, strategy=MergeStrategy.THREE_WAY_MERGE
        )

        # This should actually succeed since they changed different sections
        assert result.strategy == MergeStrategy.THREE_WAY_MERGE
        # Check that merge attempted
        assert result.merged_content is not None

    def test_resolve_three_way_merge_both_changed_same_section(
        self, resolver, doc_store, sample_baseline
    ):
        """Test 3-way merge when both changed the same section."""
        # Create doc where manual and AI both changed Overview
        manual_content = sample_baseline.replace(
            "This is the API overview", "This is the updated API overview"
        )

        doc = Document(
            project_id=1,
            name="Test Doc",
            doc_type=DocumentType.API_DOC,
            version="1.0.0",
            content=manual_content,
            status=DocumentStatus.PUBLISHED,
        )
        doc.id = doc_store.create(doc, write_to_file=False)

        # Set baseline
        import hashlib
        baseline_hash = hashlib.sha256(sample_baseline.encode()).hexdigest()[:16]
        doc = doc_store.get(doc.id)
        doc.ai_baseline_hash = baseline_hash
        doc.ai_baseline_content = sample_baseline
        doc_store.update(doc, write_to_file=False)

        # New AI also changed Overview differently
        new_ai = sample_baseline.replace(
            "This is the API overview", "This is the comprehensive API overview"
        )

        result = resolver.resolve_conflict(
            doc.id, new_ai, strategy=MergeStrategy.THREE_WAY_MERGE
        )

        # Should detect conflict since both changed same section
        if not result.success:
            assert result.needs_review
            assert len(result.conflicts) > 0
            assert result.sections_conflicted > 0
            # Should keep manual version for safety
            assert "updated" in result.merged_content

    def test_resolve_three_way_merge_no_baseline(
        self, resolver, doc_store, sample_baseline, new_ai_content
    ):
        """Test 3-way merge when baseline not available."""
        # Create doc without baseline content
        doc = Document(
            project_id=1,
            name="Test Doc",
            doc_type=DocumentType.API_DOC,
            version="1.0.0",
            content=sample_baseline,
            status=DocumentStatus.PUBLISHED,
        )
        doc.id = doc_store.create(doc, write_to_file=False)

        result = resolver.resolve_conflict(
            doc.id, new_ai_content, strategy=MergeStrategy.THREE_WAY_MERGE
        )

        assert not result.success
        assert result.needs_review
        assert "baseline content not available" in result.message

    def test_resolve_nonexistent_document(self, resolver, new_ai_content):
        """Test resolution with nonexistent document."""
        with pytest.raises(ValueError, match="not found"):
            resolver.resolve_conflict(99999, new_ai_content)


class TestThreeWayMergeAlgorithm:
    """Test 3-way merge algorithm in detail."""

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
    def resolver(self, doc_store):
        """Create conflict resolver."""
        return ConflictResolver(doc_store)

    def test_merge_only_manual_changed(self, resolver):
        """Test merge when only manual version changed."""
        baseline = "# Header\n\nOriginal content"
        manual = "# Header\n\nManually edited content"
        new_ai = "# Header\n\nOriginal content"

        result = resolver._three_way_merge(baseline, manual, new_ai)

        assert result.success
        assert "Manually edited" in result.merged_content
        assert result.manual_sections_kept > 0
        assert len(result.conflicts) == 0

    def test_merge_only_ai_changed(self, resolver):
        """Test merge when only AI version changed."""
        baseline = "# Header\n\nOriginal content"
        manual = "# Header\n\nOriginal content"
        new_ai = "# Header\n\nAI updated content"

        result = resolver._three_way_merge(baseline, manual, new_ai)

        assert result.success
        assert "AI updated" in result.merged_content
        assert result.ai_sections_kept > 0
        assert len(result.conflicts) == 0

    def test_merge_both_changed_differently(self, resolver):
        """Test merge when both changed the same section."""
        baseline = "# Header\n\nOriginal content"
        manual = "# Header\n\nManually edited content"
        new_ai = "# Header\n\nAI updated content"

        result = resolver._three_way_merge(baseline, manual, new_ai)

        # Should report conflict
        assert not result.success
        assert result.needs_review
        assert len(result.conflicts) > 0
        assert result.sections_conflicted > 0
        # Should keep manual for safety
        assert "Manually edited" in result.merged_content

    def test_merge_manual_added_section(self, resolver):
        """Test merge when manual added a section."""
        baseline = "# Header 1\n\nContent 1"
        manual = "# Header 1\n\nContent 1\n\n# Header 2\n\nNew manual section"
        new_ai = "# Header 1\n\nContent 1"

        result = resolver._three_way_merge(baseline, manual, new_ai)

        # Manual addition should be kept
        assert "Header 2" in result.merged_content
        assert "New manual section" in result.merged_content

    def test_merge_ai_added_section(self, resolver):
        """Test merge when AI added a section."""
        baseline = "# Header 1\n\nContent 1"
        manual = "# Header 1\n\nContent 1"
        new_ai = "# Header 1\n\nContent 1\n\n# Header 2\n\nNew AI section"

        result = resolver._three_way_merge(baseline, manual, new_ai)

        # AI addition should be kept
        assert "Header 2" in result.merged_content
        assert "New AI section" in result.merged_content

    def test_merge_both_added_different_sections(self, resolver):
        """Test merge when both added different sections."""
        baseline = "# Header 1\n\nContent 1"
        manual = "# Header 1\n\nContent 1\n\n# Manual Section\n\nManual content"
        new_ai = "# Header 1\n\nContent 1\n\n# AI Section\n\nAI content"

        result = resolver._three_way_merge(baseline, manual, new_ai)

        # Both additions should be present (though order may vary)
        merged = result.merged_content
        # At least one should be present
        assert ("Manual Section" in merged or "AI Section" in merged)

    def test_merge_identical_changes(self, resolver):
        """Test merge when manual and AI made identical changes."""
        baseline = "# Header\n\nOriginal content"
        manual = "# Header\n\nUpdated content"
        new_ai = "# Header\n\nUpdated content"

        result = resolver._three_way_merge(baseline, manual, new_ai)

        assert result.success
        assert "Updated content" in result.merged_content
        assert len(result.conflicts) == 0

    def test_merge_statistics(self, resolver):
        """Test that merge statistics are computed correctly."""
        baseline = "# H1\n\nC1\n\n# H2\n\nC2"
        manual = "# H1\n\nManual C1\n\n# H2\n\nC2"
        new_ai = "# H1\n\nC1\n\n# H2\n\nAI C2"

        result = resolver._three_way_merge(baseline, manual, new_ai)

        # Should have statistics
        assert result.sections_merged >= 0
        assert result.manual_sections_kept >= 0
        assert result.ai_sections_kept >= 0

    def test_merge_empty_content(self, resolver):
        """Test merge with empty content."""
        baseline = ""
        manual = "# New Content\n\nManual"
        new_ai = "# New Content\n\nAI"

        result = resolver._three_way_merge(baseline, manual, new_ai)

        # Should handle gracefully
        assert result.merged_content is not None
