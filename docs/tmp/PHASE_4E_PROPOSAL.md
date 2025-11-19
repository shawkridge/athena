# Phase 4E Proposal: Quality & Trust

**Status**: Proposed
**Priority**: P0 - Required for production adoption
**Estimated Effort**: 2-3 weeks
**Dependencies**: Phase 4A-4D (complete)

## Problem Statement

Phase 4D provides automated drift detection and sync, but **lacks critical trust-building features**:

1. **Blind Regeneration** - Developers can't preview changes before committing
2. **Data Loss Risk** - Manual edits get overwritten silently
3. **No Quality Verification** - Generated docs might be incorrect
4. **No Progress Visibility** - Can't measure documentation completeness

**Impact**: Without these features, developers **will not trust or adopt** the system.

## Vision

Enable developers to confidently use automated documentation sync by:
- **Seeing exactly what changed** before committing
- **Preserving manual work** when specs update
- **Verifying correctness** automatically
- **Tracking coverage** to measure progress

## Solution Overview

### Phase 4E Components

```
┌─────────────────────────────────────────────────────┐
│              Phase 4E: Quality & Trust              │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1. Diff Visualization                              │
│     ├─ Side-by-side comparison                      │
│     ├─ Semantic diff (section changes)              │
│     ├─ Show spec changes that caused drift          │
│     └─ Rich terminal output + JSON                  │
│                                                     │
│  2. Manual Edit Protection                          │
│     ├─ Detect manual changes                        │
│     ├─ Conflict detection                           │
│     ├─ 3-way merge support                          │
│     └─ Manual override tracking                     │
│                                                     │
│  3. Accuracy Validation                             │
│     ├─ Schema validation                            │
│     ├─ Content coverage                             │
│     ├─ Example validation                           │
│     ├─ Link checking                                │
│     └─ AI self-review                               │
│                                                     │
│  4. Coverage Metrics                                │
│     ├─ Spec coverage (% documented)                 │
│     ├─ Element coverage (endpoints, types)          │
│     ├─ Quality coverage (examples, errors)          │
│     └─ Gap identification                           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Feature Details

### Feature 1: Diff Visualization

**Goal**: Show developers exactly what will change before syncing

#### Technical Design

**New Module**: `src/athena/architecture/sync/diff_engine.py`

```python
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class ChangeType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"

@dataclass
class SectionChange:
    """Semantic change at section level."""
    section_name: str
    section_type: str  # header, paragraph, code_block, list
    change_type: ChangeType
    old_content: Optional[str]
    new_content: Optional[str]
    line_numbers: tuple[int, int]  # (start, end)

@dataclass
class SpecChange:
    """Spec change that caused drift."""
    spec_id: int
    spec_name: str
    change_description: str
    diff_snippet: str

@dataclass
class DiffResult:
    """Complete diff analysis."""
    document_id: int
    document_name: str
    old_hash: str
    new_hash: str

    # Section-level changes
    sections_added: List[SectionChange]
    sections_removed: List[SectionChange]
    sections_modified: List[SectionChange]

    # Root cause analysis
    spec_changes: List[SpecChange]

    # Statistics
    total_additions: int
    total_deletions: int
    total_modifications: int

    # Rendering
    def to_text(self, color=True) -> str:
        """Rich terminal output with colors."""

    def to_json(self) -> dict:
        """Machine-readable format."""

    def to_markdown(self) -> str:
        """Human-readable markdown."""

class DocumentDiffer:
    """Compute diffs between document versions."""

    def __init__(self, spec_store, doc_store):
        self.spec_store = spec_store
        self.doc_store = doc_store

    def compute_diff(
        self,
        doc_id: int,
        new_content: str,
        show_cause: bool = True
    ) -> DiffResult:
        """
        Compute comprehensive diff.

        Args:
            doc_id: Document to compare
            new_content: Proposed new content
            show_cause: Include spec changes that caused drift

        Returns:
            DiffResult with all changes
        """
        # 1. Get current content
        doc = self.doc_store.get(doc_id)
        old_content = doc.content

        # 2. Parse into sections
        old_sections = self._parse_sections(old_content)
        new_sections = self._parse_sections(new_content)

        # 3. Compute section-level diff (semantic)
        changes = self._diff_sections(old_sections, new_sections)

        # 4. Optionally: identify spec changes that caused this
        spec_changes = []
        if show_cause:
            spec_changes = self._analyze_cause(doc, old_content, new_content)

        # 5. Build result
        return DiffResult(...)

    def _parse_sections(self, content: str) -> List[Section]:
        """Parse markdown into semantic sections."""
        # Use markdown parser to identify headers, code blocks, etc.

    def _diff_sections(
        self,
        old: List[Section],
        new: List[Section]
    ) -> List[SectionChange]:
        """Compute semantic diff at section level."""
        # Similar to git diff but at section granularity

    def _analyze_cause(
        self,
        doc: Document,
        old_content: str,
        new_content: str
    ) -> List[SpecChange]:
        """Identify which spec changes caused this drift."""
        # 1. Get specs this doc is based on
        specs = [self.spec_store.get(sid) for sid in doc.based_on_spec_ids]

        # 2. For each spec, get previous version
        # 3. Diff spec versions
        # 4. Correlate spec changes with doc changes

        return spec_changes
```

#### CLI Integration

```python
# In src/athena/cli/doc_manage.py

def cmd_diff(args):
    """Show diff for document regeneration."""
    db = get_database()
    spec_store = SpecificationStore(db)
    doc_store = DocumentStore(db)

    # Generate new content (without saving)
    ai_generator = AIDocGenerator(api_key=args.api_key)
    result = ai_generator.generate(...)
    new_content = result.content

    # Compute diff
    differ = DocumentDiffer(spec_store, doc_store)
    diff_result = differ.compute_diff(
        doc_id=args.doc_id,
        new_content=new_content,
        show_cause=args.show_cause
    )

    # Display
    if args.json:
        print(json.dumps(diff_result.to_json(), indent=2))
    else:
        print(diff_result.to_text(color=not args.no_color))

# Add to sync command
def cmd_sync(args):
    # ... existing code ...

    # NEW: Show preview if requested
    if args.preview:
        # Compute diff first
        diff_result = differ.compute_diff(doc_id, new_content)
        print(diff_result.to_text())

        # Ask for confirmation
        if not args.yes:
            confirm = input("Apply these changes? [y/N] ")
            if confirm.lower() != 'y':
                print("Sync cancelled")
                return

    # ... proceed with sync ...
```

**New CLI Commands**:
```bash
# Show diff for single document
athena-doc-manage diff --doc-id 5 --show-cause

# Preview changes before syncing
athena-doc-manage sync --doc-id 5 --preview

# Auto-approve (skip confirmation)
athena-doc-manage sync --preview --yes
```

**Lines of Code**: ~400 lines
**Tests**: ~8 tests
**Effort**: 3-4 days

---

### Feature 2: Manual Edit Protection

**Goal**: Preserve human work when specs change

#### Technical Design

**New Module**: `src/athena/architecture/sync/conflict_resolver.py`

```python
from dataclasses import dataclass
from enum import Enum

class ConflictStatus(str, Enum):
    NO_CONFLICT = "no_conflict"
    MANUAL_EDIT_DETECTED = "manual_edit_detected"
    CONFLICT_RESOLVED = "conflict_resolved"
    NEEDS_MANUAL_REVIEW = "needs_manual_review"

class MergeStrategy(str, Enum):
    KEEP_MANUAL = "keep_manual"      # Skip regeneration
    KEEP_AI = "keep_ai"              # Discard manual edits
    THREE_WAY_MERGE = "merge"        # Attempt auto-merge
    MANUAL_REVIEW = "manual_review"  # Human decision required

@dataclass
class ConflictResult:
    """Result of conflict detection."""
    document: Document
    status: ConflictStatus
    has_manual_edits: bool
    ai_baseline_hash: Optional[str]
    current_hash: str
    manual_edit_timestamp: Optional[datetime]
    conflicting_sections: List[str]
    recommendation: MergeStrategy
    message: str

class ConflictDetector:
    """Detect manual edits to AI-generated documents."""

    def detect_conflict(self, doc_id: int) -> ConflictResult:
        """
        Check if document has been manually edited since last AI generation.

        Workflow:
        1. Load document
        2. Check if manually_edited flag is set
        3. Compare current_hash with ai_baseline_hash
        4. If different → manual edit detected
        5. Return conflict status
        """

    def mark_manual_override(self, doc_id: int):
        """Mark document as manually edited (skip future auto-sync)."""

    def clear_manual_flag(self, doc_id: int):
        """Clear manual edit flag (resume auto-sync)."""

class ConflictResolver:
    """Resolve conflicts between manual edits and AI regeneration."""

    def resolve_conflict(
        self,
        doc_id: int,
        new_ai_content: str,
        strategy: MergeStrategy = MergeStrategy.MANUAL_REVIEW
    ) -> ResolveResult:
        """
        Resolve conflict using specified strategy.

        Args:
            doc_id: Document with conflict
            new_ai_content: Newly generated content from AI
            strategy: How to resolve the conflict

        Returns:
            ResolveResult with merged content or error
        """
        doc = self.doc_store.get(doc_id)

        if strategy == MergeStrategy.KEEP_MANUAL:
            return ResolveResult(
                content=doc.content,
                strategy=strategy,
                message="Kept manual edits, skipped regeneration"
            )

        elif strategy == MergeStrategy.KEEP_AI:
            return ResolveResult(
                content=new_ai_content,
                strategy=strategy,
                message="Discarded manual edits, used AI content"
            )

        elif strategy == MergeStrategy.THREE_WAY_MERGE:
            # Attempt 3-way merge
            merged = self._three_way_merge(
                baseline=self._get_ai_baseline(doc),
                manual=doc.content,
                new_ai=new_ai_content
            )
            return merged

        else:  # MANUAL_REVIEW
            return ResolveResult(
                needs_review=True,
                message="Manual review required"
            )

    def _three_way_merge(
        self,
        baseline: str,
        manual: str,
        new_ai: str
    ) -> ResolveResult:
        """
        3-way merge algorithm.

        Logic:
        1. Diff baseline → manual (what human changed)
        2. Diff baseline → new_ai (what AI changed)
        3. If same section changed by both → CONFLICT
        4. Otherwise: merge changes from both
        """
        # Parse into sections
        baseline_sections = parse_sections(baseline)
        manual_sections = parse_sections(manual)
        ai_sections = parse_sections(new_ai)

        merged_sections = []
        conflicts = []

        for section_id in all_section_ids:
            manual_changed = (
                manual_sections[section_id] != baseline_sections[section_id]
            )
            ai_changed = (
                ai_sections[section_id] != baseline_sections[section_id]
            )

            if not manual_changed and not ai_changed:
                # No change → keep baseline
                merged_sections.append(baseline_sections[section_id])

            elif manual_changed and not ai_changed:
                # Only human changed → keep manual
                merged_sections.append(manual_sections[section_id])

            elif ai_changed and not manual_changed:
                # Only AI changed → keep AI
                merged_sections.append(ai_sections[section_id])

            else:
                # BOTH changed → conflict
                conflicts.append(section_id)
                # Could use AI to resolve: "merge these two versions"

        if conflicts:
            return ResolveResult(
                needs_review=True,
                conflicting_sections=conflicts,
                message=f"Conflicts in {len(conflicts)} sections"
            )
        else:
            return ResolveResult(
                content=assemble_sections(merged_sections),
                strategy=MergeStrategy.THREE_WAY_MERGE,
                message="Successfully merged manual and AI changes"
            )
```

#### Database Changes

```sql
-- Track manual edits
ALTER TABLE documents ADD COLUMN ai_baseline_hash TEXT;
ALTER TABLE documents ADD COLUMN ai_baseline_content TEXT;  -- Last AI-generated version
ALTER TABLE documents ADD COLUMN manual_edit_detected BOOLEAN DEFAULT FALSE;
ALTER TABLE documents ADD COLUMN last_manual_edit_at TIMESTAMP;
ALTER TABLE documents ADD COLUMN manual_override BOOLEAN DEFAULT FALSE;  -- Skip auto-sync

CREATE INDEX idx_docs_manual_override ON documents(manual_override);
```

#### CLI Integration

```bash
# Detect conflicts before syncing
athena-doc-manage check-conflicts --project-id 1

# Sync with conflict resolution strategy
athena-doc-manage sync --doc-id 5 --on-conflict keep-manual
athena-doc-manage sync --doc-id 5 --on-conflict merge
athena-doc-manage sync --doc-id 5 --on-conflict keep-ai --force

# Mark document as manual override (skip future auto-sync)
athena-doc-manage mark-manual --doc-id 5
athena-doc-manage unmark-manual --doc-id 5  # Resume auto-sync
```

**Lines of Code**: ~500 lines
**Tests**: ~10 tests
**Effort**: 5-7 days (complex merging logic)

---

### Feature 3: Accuracy Validation

**Goal**: Verify generated docs accurately represent specs

#### Technical Design

**New Module**: `src/athena/architecture/validation/accuracy.py`

```python
class AccuracyValidator:
    """Validate document accuracy against specifications."""

    def validate_document(self, doc_id: int) -> ValidationReport:
        """
        Comprehensive validation.

        Runs all validation checks:
        1. Schema validation (structure)
        2. Coverage validation (completeness)
        3. Example validation (correctness)
        4. Link validation (references)
        5. AI review (semantic accuracy)
        """

    def validate_schema(self, doc: Document) -> SchemaValidationResult:
        """Verify document has required sections."""
        # Based on doc_type, check for required sections
        # e.g., API doc needs: Overview, Endpoints, Examples, Errors

    def validate_coverage(
        self,
        doc: Document,
        specs: List[Specification]
    ) -> CoverageValidationResult:
        """Verify all spec elements are documented."""
        # Extract elements from spec (endpoints, types, fields)
        # Check if each element is mentioned in doc
        # Return: covered_elements, missing_elements, coverage_percent

    def validate_examples(self, doc: Document) -> ExampleValidationResult:
        """Verify code examples are syntactically correct."""
        # Extract code blocks
        # Run syntax check (language-specific)
        # Optional: run examples in sandbox

    def validate_links(self, doc: Document) -> LinkValidationResult:
        """Check cross-references and URLs."""
        # Extract all links [text](url)
        # Check if internal references exist
        # Check if external URLs are reachable

    async def ai_review(
        self,
        doc: Document,
        specs: List[Specification]
    ) -> AIReviewResult:
        """Ask AI to validate accuracy."""
        prompt = f"""
        Review this documentation for accuracy.

        Specification:
        {spec.content}

        Documentation:
        {doc.content}

        Questions:
        1. Does the documentation accurately represent the specification?
        2. Are there any misleading or incorrect statements?
        3. Are all important details from the spec included?
        4. Are the examples correct and helpful?

        Provide:
        - Accuracy score (0-100)
        - Issues found (list)
        - Suggestions for improvement
        """

        response = await self.ai_client.generate(prompt)
        return AIReviewResult(
            score=extract_score(response),
            issues=extract_issues(response),
            suggestions=extract_suggestions(response)
        )

@dataclass
class ValidationReport:
    """Comprehensive validation results."""
    document_id: int
    overall_score: float  # 0-100

    # Individual validations
    schema: SchemaValidationResult
    coverage: CoverageValidationResult
    examples: ExampleValidationResult
    links: LinkValidationResult
    ai_review: Optional[AIReviewResult]

    # Summary
    passed: bool
    critical_issues: List[ValidationIssue]
    warnings: List[ValidationIssue]
    suggestions: List[str]

    def to_text(self) -> str:
        """Human-readable report."""

    def to_json(self) -> dict:
        """Machine-readable report."""
```

#### CLI Integration

```bash
# Validate single document
athena-doc-manage validate --doc-id 5

# Validate all documents
athena-doc-manage validate --project-id 1

# Strict mode (fail on warnings)
athena-doc-manage validate --doc-id 5 --strict

# Include AI review (requires API key)
athena-doc-manage validate --doc-id 5 --ai-review

# Validate during sync (block if score < threshold)
athena-doc-manage sync --doc-id 5 --validate --min-score 80
```

**Lines of Code**: ~450 lines
**Tests**: ~12 tests
**Effort**: 4-6 days

---

### Feature 4: Coverage Metrics

**Goal**: Measure documentation completeness

#### Technical Design

**New Module**: `src/athena/architecture/metrics/coverage.py`

```python
class CoverageAnalyzer:
    """Analyze documentation coverage across project."""

    def analyze_project(self, project_id: int) -> CoverageReport:
        """Comprehensive coverage analysis."""

        # 1. Spec coverage
        spec_coverage = self.compute_spec_coverage(project_id)

        # 2. Element coverage (endpoints, types, etc.)
        element_coverage = self.compute_element_coverage(project_id)

        # 3. Quality coverage (examples, errors, guides)
        quality_coverage = self.compute_quality_coverage(project_id)

        # 4. Identify gaps
        gaps = self.identify_gaps(project_id)

        return CoverageReport(...)

    def compute_spec_coverage(self, project_id: int) -> SpecCoverage:
        """What % of specs have documentation?"""
        all_specs = self.spec_store.list_by_project(project_id)

        documented_specs = []
        undocumented_specs = []

        for spec in all_specs:
            docs = self.doc_store.find_by_spec(spec.id)
            if docs:
                documented_specs.append(spec)
            else:
                undocumented_specs.append(spec)

        return SpecCoverage(
            total_specs=len(all_specs),
            documented_specs=len(documented_specs),
            coverage_percent=len(documented_specs) / len(all_specs) * 100,
            undocumented=undocumented_specs
        )

    def compute_element_coverage(self, project_id: int) -> ElementCoverage:
        """What % of spec elements (endpoints, types) are documented?"""
        # For each spec, extract elements (depends on spec type)
        # For each element, check if documented
        # Return coverage %

    def compute_quality_coverage(self, project_id: int) -> QualityCoverage:
        """What % of docs have examples, error docs, etc.?"""
        all_docs = self.doc_store.list_by_project(project_id)

        stats = {
            'has_examples': 0,
            'has_error_docs': 0,
            'has_migration_guide': 0,
            'has_changelog': 0
        }

        for doc in all_docs:
            if self._has_examples(doc):
                stats['has_examples'] += 1
            if self._has_error_docs(doc):
                stats['has_error_docs'] += 1
            # etc.

        return QualityCoverage(
            total_docs=len(all_docs),
            with_examples=stats['has_examples'],
            with_error_docs=stats['has_error_docs'],
            # percentages
        )

    def identify_gaps(self, project_id: int) -> List[Gap]:
        """Identify top documentation gaps."""
        gaps = []

        # 1. Undocumented specs
        spec_cov = self.compute_spec_coverage(project_id)
        for spec in spec_cov.undocumented:
            gaps.append(Gap(
                type="missing_doc",
                severity="high",
                spec=spec,
                recommendation="Create documentation for this spec"
            ))

        # 2. Docs missing examples
        # 3. Docs missing error documentation
        # etc.

        return sorted(gaps, key=lambda g: g.severity, reverse=True)

@dataclass
class CoverageReport:
    """Complete coverage analysis."""
    project_id: int
    generated_at: datetime

    # Coverage metrics
    spec_coverage: SpecCoverage
    element_coverage: ElementCoverage
    quality_coverage: QualityCoverage

    # Overall score
    overall_coverage_percent: float
    overall_quality_score: float

    # Gaps and recommendations
    top_gaps: List[Gap]
    recommendations: List[str]

    def to_text(self) -> str:
        """Rich terminal output."""

    def to_json(self) -> dict:
        """Machine-readable."""
```

#### CLI Integration

```bash
# Show coverage for project
athena-doc-manage coverage --project-id 1

# Output:
# Documentation Coverage Report
# =============================
#
# Spec Coverage:        73% (22/30 specs documented)
# Element Coverage:     85% (127/150 endpoints documented)
# Quality Coverage:     68%
#   - With examples:    12/22 (55%)
#   - With errors:      18/22 (82%)
#   - With migrations:  5/22 (23%)
#
# Overall Score: 75%
#
# Top Gaps:
# 1. [HIGH] Missing docs: Authentication API (spec #15)
# 2. [HIGH] Missing docs: Webhook Events (spec #23)
# 3. [MEDIUM] Missing examples: User Management API (doc #5)
# 4. [MEDIUM] Missing migration guide: Payment API v2 (doc #8)
#
# Recommendations:
# - Create documentation for 8 undocumented specs
# - Add code examples to 10 docs
# - Add error documentation to 4 docs

# JSON output for dashboards
athena-doc-manage coverage --project-id 1 --json

# Track over time
athena-doc-manage coverage --project-id 1 --save-history
```

**Lines of Code**: ~350 lines
**Tests**: ~8 tests
**Effort**: 2-3 days

---

## Implementation Plan

### Week 1: Diff & Validation Foundation
- **Day 1-2**: Diff engine (section parsing, diff algorithm)
- **Day 3**: Diff visualization (rich terminal output)
- **Day 4**: Schema validation (required sections)
- **Day 5**: Coverage metrics (spec coverage, element coverage)

**Deliverable**: Can preview changes before syncing, basic validation

### Week 2: Conflict Resolution
- **Day 6-7**: Conflict detection (manual edit tracking)
- **Day 8-9**: 3-way merge algorithm
- **Day 10**: Conflict resolution CLI integration

**Deliverable**: Manual edits are preserved during sync

### Week 3: Advanced Validation & Polish
- **Day 11**: Example validation, link checking
- **Day 12**: AI accuracy review
- **Day 13**: Quality coverage metrics
- **Day 14**: CLI polish, documentation
- **Day 15**: Integration tests, bug fixes

**Deliverable**: Production-ready Phase 4E

## Success Metrics

### Adoption Metrics
- **Trust Score**: % of developers who use auto-sync without fear
  - Target: >80% confidence in auto-sync
- **Preview Usage**: % of syncs that use --preview flag first
  - Target: >90% preview before sync
- **Manual Override Rate**: % of docs marked as manual override
  - Target: <10% (most docs stay auto-synced)

### Quality Metrics
- **Validation Pass Rate**: % of generated docs that pass validation
  - Target: >95% pass on first try
- **Coverage Improvement**: Month-over-month coverage increase
  - Target: +10% coverage per month
- **Conflict Rate**: % of syncs that encounter manual edit conflicts
  - Target: <5% conflicts, >95% clean syncs

### Performance Metrics
- **Diff Computation**: Time to compute diff
  - Target: <500ms per document
- **Validation Time**: Time to run all validations
  - Target: <3s per document (without AI review)
  - Target: <10s per document (with AI review)

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| 3-way merge too complex | High | Start with simple strategy: prompt user to choose |
| Diff visualization unclear | Medium | User testing with 5 developers, iterate |
| AI review too slow/expensive | Medium | Make optional, cache results, batch |
| Validation false positives | Medium | Tunable strictness, warning vs error levels |

## Open Questions

1. **Merge UX**: How to present conflicts to users?
   - Option A: Show side-by-side, let user edit
   - Option B: Ask AI to merge ("combine these two versions")
   - Recommendation: Start with A, add B later

2. **Validation thresholds**: What score is "passing"?
   - Option A: Hard threshold (must be >80%)
   - Option B: Soft warnings (show score, don't block)
   - Recommendation: Soft warnings by default, strict mode available

3. **Coverage targets**: What's a "good" coverage %?
   - Depends on project maturity
   - Recommendation: Show trend, not absolute target

## Conclusion

Phase 4E transforms the documentation system from **"works but scary"** to **"works and trustworthy"**.

Without it, developers won't adopt auto-sync because:
- ❌ Can't see what changes
- ❌ Risk losing manual work
- ❌ No confidence in quality

With it, developers confidently use auto-sync because:
- ✅ Can preview every change
- ✅ Manual work is preserved
- ✅ Quality is validated
- ✅ Progress is visible

**Recommendation: Implement Phase 4E immediately before moving to other features.**

---

**Proposal Date**: November 18, 2025
**Status**: Awaiting approval
**Next Steps**: If approved, create detailed implementation tasks
