"""
Conflict Detection and Resolution - Phase 4E Component 2.

Detects manual edits to AI-generated documents and provides strategies to
resolve conflicts when specifications change after manual editing.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Tuple

from ..models import Document
from ..doc_store import DocumentStore
from .diff_engine import DocumentDiffer, SectionParser, Section


class ConflictStatus(str, Enum):
    """Status of conflict detection."""

    NO_CONFLICT = "no_conflict"
    MANUAL_EDIT_DETECTED = "manual_edit_detected"
    CONFLICT_RESOLVED = "conflict_resolved"
    NEEDS_MANUAL_REVIEW = "needs_manual_review"


class MergeStrategy(str, Enum):
    """Strategy for resolving conflicts."""

    KEEP_MANUAL = "keep_manual"  # Keep human edits, skip AI regeneration
    KEEP_AI = "keep_ai"  # Discard human edits, use new AI content
    THREE_WAY_MERGE = "merge"  # Attempt automatic 3-way merge
    MANUAL_REVIEW = "manual_review"  # Flag for human review


@dataclass
class ConflictResult:
    """Result of conflict detection."""

    document: Document
    status: ConflictStatus
    has_manual_edits: bool
    ai_baseline_hash: Optional[str] = None
    current_hash: Optional[str] = None
    manual_edit_timestamp: Optional[datetime] = None
    conflicting_sections: List[str] = field(default_factory=list)
    recommendation: MergeStrategy = MergeStrategy.MANUAL_REVIEW
    message: str = ""

    @property
    def needs_resolution(self) -> bool:
        """Whether this conflict needs resolution."""
        return self.has_manual_edits


@dataclass
class MergeResult:
    """Result of a merge operation."""

    success: bool
    strategy: MergeStrategy
    merged_content: Optional[str] = None
    conflicts: List[str] = field(default_factory=list)
    message: str = ""
    needs_review: bool = False

    # Statistics
    sections_merged: int = 0
    sections_conflicted: int = 0
    manual_sections_kept: int = 0
    ai_sections_kept: int = 0


class ConflictDetector:
    """Detect manual edits to AI-generated documents."""

    def __init__(self, doc_store: DocumentStore):
        self.doc_store = doc_store

    def detect_conflict(self, doc_id: int) -> ConflictResult:
        """
        Check if document has been manually edited since last AI generation.

        Workflow:
        1. Load document
        2. Check if manually_edited flag is set
        3. Compare current_hash with ai_baseline_hash
        4. If different → manual edit detected
        5. Return conflict status

        Args:
            doc_id: Document ID to check

        Returns:
            ConflictResult with detection details
        """
        doc = self.doc_store.get(doc_id)
        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        # Compute current content hash
        current_hash = self._compute_hash(doc.content or "")

        # Check for AI baseline
        ai_baseline_hash = doc.ai_baseline_hash if hasattr(doc, "ai_baseline_hash") else None

        # No baseline means never AI-generated or baseline not tracked
        if not ai_baseline_hash:
            return ConflictResult(
                document=doc,
                status=ConflictStatus.NO_CONFLICT,
                has_manual_edits=False,
                current_hash=current_hash,
                message="No AI baseline - document may be manually created or baseline not tracked",
                recommendation=MergeStrategy.MANUAL_REVIEW,
            )

        # Check if manual override flag is set
        manual_override = getattr(doc, "manual_override", False)
        if manual_override:
            return ConflictResult(
                document=doc,
                status=ConflictStatus.MANUAL_EDIT_DETECTED,
                has_manual_edits=True,
                ai_baseline_hash=ai_baseline_hash,
                current_hash=current_hash,
                manual_edit_timestamp=getattr(doc, "last_manual_edit_at", None),
                message="Document marked as manual override - skip auto-sync",
                recommendation=MergeStrategy.KEEP_MANUAL,
            )

        # Compare hashes
        if current_hash != ai_baseline_hash:
            # Manual edit detected
            return ConflictResult(
                document=doc,
                status=ConflictStatus.MANUAL_EDIT_DETECTED,
                has_manual_edits=True,
                ai_baseline_hash=ai_baseline_hash,
                current_hash=current_hash,
                manual_edit_timestamp=getattr(doc, "last_manual_edit_at", None),
                message="Manual edits detected - content differs from AI baseline",
                recommendation=MergeStrategy.THREE_WAY_MERGE,
            )

        # No conflict
        return ConflictResult(
            document=doc,
            status=ConflictStatus.NO_CONFLICT,
            has_manual_edits=False,
            ai_baseline_hash=ai_baseline_hash,
            current_hash=current_hash,
            message="No manual edits detected",
            recommendation=MergeStrategy.KEEP_AI,
        )

    def mark_manual_override(self, doc_id: int) -> bool:
        """
        Mark document as manually edited (skip future auto-sync).

        Args:
            doc_id: Document ID

        Returns:
            True if marked successfully
        """
        doc = self.doc_store.get(doc_id)
        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        # Set manual override flag
        doc.manual_override = True
        doc.last_manual_edit_at = datetime.now()

        # Update in database
        self.doc_store.update(doc, write_to_file=False)

        return True

    def clear_manual_flag(self, doc_id: int) -> bool:
        """
        Clear manual edit flag (resume auto-sync).

        Args:
            doc_id: Document ID

        Returns:
            True if cleared successfully
        """
        doc = self.doc_store.get(doc_id)
        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        # Clear manual override flag
        doc.manual_override = False

        # Update in database
        self.doc_store.update(doc, write_to_file=False)

        return True

    def _compute_hash(self, content: str) -> str:
        """Compute hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class ConflictResolver:
    """Resolve conflicts between manual edits and AI regeneration."""

    def __init__(self, doc_store: DocumentStore):
        self.doc_store = doc_store
        self.parser = SectionParser()

    def resolve_conflict(
        self,
        doc_id: int,
        new_ai_content: str,
        strategy: MergeStrategy = MergeStrategy.MANUAL_REVIEW,
    ) -> MergeResult:
        """
        Resolve conflict using specified strategy.

        Args:
            doc_id: Document with conflict
            new_ai_content: Newly generated content from AI
            strategy: How to resolve the conflict

        Returns:
            MergeResult with merged content or error
        """
        doc = self.doc_store.get(doc_id)
        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        current_content = doc.content or ""

        if strategy == MergeStrategy.KEEP_MANUAL:
            return MergeResult(
                success=True,
                strategy=strategy,
                merged_content=current_content,
                message="Kept manual edits, skipped regeneration",
                manual_sections_kept=len(self.parser.parse(current_content)),
            )

        elif strategy == MergeStrategy.KEEP_AI:
            return MergeResult(
                success=True,
                strategy=strategy,
                merged_content=new_ai_content,
                message="Discarded manual edits, used AI content",
                ai_sections_kept=len(self.parser.parse(new_ai_content)),
            )

        elif strategy == MergeStrategy.THREE_WAY_MERGE:
            # Attempt 3-way merge
            baseline = getattr(doc, "ai_baseline_content", None)

            if not baseline:
                return MergeResult(
                    success=False,
                    strategy=strategy,
                    needs_review=True,
                    message="Cannot 3-way merge: AI baseline content not available",
                )

            return self._three_way_merge(
                baseline=baseline, manual=current_content, new_ai=new_ai_content
            )

        else:  # MANUAL_REVIEW
            return MergeResult(
                success=False,
                strategy=strategy,
                needs_review=True,
                message="Manual review required - no automatic resolution",
            )

    def _three_way_merge(
        self, baseline: str, manual: str, new_ai: str
    ) -> MergeResult:
        """
        3-way merge algorithm.

        Logic:
        1. Parse all three versions into sections
        2. For each section:
           - If only manual changed → keep manual
           - If only AI changed → keep AI
           - If both changed → CONFLICT
           - If neither changed → keep baseline
        3. Assemble merged content
        4. Report conflicts if any

        Args:
            baseline: Original AI-generated content
            manual: Current content with manual edits
            new_ai: Newly generated AI content

        Returns:
            MergeResult with merged content or conflicts
        """
        # Parse into sections
        baseline_sections = self.parser.parse(baseline)
        manual_sections = self.parser.parse(manual)
        ai_sections = self.parser.parse(new_ai)

        # Build section index by content hash for matching
        baseline_idx = {self._section_hash(s): s for s in baseline_sections}
        manual_idx = {self._section_hash(s): s for s in manual_sections}
        ai_idx = {self._section_hash(s): s for s in ai_sections}

        merged_sections = []
        conflicts = []
        sections_merged = 0
        sections_conflicted = 0
        manual_sections_kept = 0
        ai_sections_kept = 0

        # Get all unique section positions (union of all versions)
        all_positions = set(range(max(len(baseline_sections), len(manual_sections), len(ai_sections))))

        for pos in sorted(all_positions):
            baseline_sec = baseline_sections[pos] if pos < len(baseline_sections) else None
            manual_sec = manual_sections[pos] if pos < len(manual_sections) else None
            ai_sec = ai_sections[pos] if pos < len(ai_sections) else None

            # Compute hashes for comparison
            baseline_hash = self._section_hash(baseline_sec) if baseline_sec else None
            manual_hash = self._section_hash(manual_sec) if manual_sec else None
            ai_hash = self._section_hash(ai_sec) if ai_sec else None

            # Decision tree
            if not manual_sec and not ai_sec:
                # Section removed in both → skip
                continue

            elif not manual_sec and ai_sec:
                # Section only in AI (new AI addition)
                merged_sections.append(ai_sec)
                ai_sections_kept += 1

            elif manual_sec and not ai_sec:
                # Section only in manual (manual addition or AI removed it)
                if baseline_hash == manual_hash:
                    # AI removed it, manual kept baseline → conflict
                    conflicts.append(f"Section {pos}: AI removed, manual kept")
                    merged_sections.append(manual_sec)  # Keep manual for now
                    sections_conflicted += 1
                else:
                    # Manual addition
                    merged_sections.append(manual_sec)
                    manual_sections_kept += 1

            elif manual_hash == ai_hash:
                # Both versions identical → no conflict
                merged_sections.append(manual_sec)
                sections_merged += 1

            elif baseline_hash == manual_hash and baseline_hash != ai_hash:
                # Only AI changed → keep AI
                merged_sections.append(ai_sec)
                ai_sections_kept += 1

            elif baseline_hash == ai_hash and baseline_hash != manual_hash:
                # Only manual changed → keep manual
                merged_sections.append(manual_sec)
                manual_sections_kept += 1

            else:
                # BOTH changed differently → CONFLICT
                conflicts.append(
                    f"Section {pos}: Both manual and AI modified - {self._get_section_name(manual_sec)}"
                )
                # Keep manual version for safety (don't lose human work)
                merged_sections.append(manual_sec)
                sections_conflicted += 1

        # Assemble merged content
        merged_content = "\n".join(s.content for s in merged_sections)

        if conflicts:
            return MergeResult(
                success=False,
                strategy=MergeStrategy.THREE_WAY_MERGE,
                merged_content=merged_content,
                conflicts=conflicts,
                needs_review=True,
                message=f"3-way merge completed with {len(conflicts)} conflict(s)",
                sections_merged=sections_merged,
                sections_conflicted=sections_conflicted,
                manual_sections_kept=manual_sections_kept,
                ai_sections_kept=ai_sections_kept,
            )
        else:
            return MergeResult(
                success=True,
                strategy=MergeStrategy.THREE_WAY_MERGE,
                merged_content=merged_content,
                message=f"3-way merge successful - merged {sections_merged} sections",
                sections_merged=sections_merged,
                sections_conflicted=0,
                manual_sections_kept=manual_sections_kept,
                ai_sections_kept=ai_sections_kept,
            )

    def _section_hash(self, section: Optional[Section]) -> Optional[str]:
        """Compute hash of section content."""
        if not section:
            return None
        return hashlib.sha256(section.content.encode()).hexdigest()[:16]

    def _get_section_name(self, section: Section) -> str:
        """Get human-readable section name."""
        if section.section_type.value == "header" and section.header_text:
            return section.header_text
        else:
            # Use first few words
            words = section.content.split()[:5]
            preview = " ".join(words)
            if len(section.content.split()) > 5:
                preview += "..."
            return f"{section.section_type.value}: {preview}"
