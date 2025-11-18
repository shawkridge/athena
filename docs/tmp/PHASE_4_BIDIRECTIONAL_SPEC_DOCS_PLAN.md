# Phase 4: Bidirectional Spec ↔ Code ↔ Docs

**Status**: Planning
**Estimated Duration**: 4-5 weeks
**Priority**: High (meets teams where they are)

---

## Overview

Most teams have **existing codebases** but no specs or documentation. Phase 4 enables:

1. **Reverse Engineering**: Extract specs FROM existing code
2. **Document Generation**: Generate docs FROM specs
3. **Drift Detection**: Keep code, specs, and docs in sync

```
Existing Code ──┐
                ├──> Extract Specs ──> Generate Docs ──> Maintain Alignment
New Specs   ────┘         ↑                  ↓                    ↓
                    (OpenAPI, Prisma)   (API docs, PRD)    (Auto-sync)
```

---

## Phase 4A: Spec Extraction (Code → Specs) [1.5 weeks]

### Supported Extraction Types

| Source | Spec Type | Tool/Method | Status |
|--------|-----------|-------------|--------|
| FastAPI routes | OpenAPI | Built-in `app.openapi()` | ✅ Researched |
| Flask routes | OpenAPI | flask-smorest, APIFlask | ✅ Researched |
| Spring Boot | OpenAPI | Respector, Swagger | ✅ Researched |
| Database schema | Prisma | `prisma db pull` | ✅ Researched |
| GraphQL endpoint | GraphQL | Introspection query | ✅ Researched |
| REST endpoints | OpenAPI | Static analysis (Semgrep) | 🔬 Research |
| TypeScript types | JSON Schema | ts-json-schema-generator | 🔬 Research |
| SQL DDL | SQL | Parse CREATE TABLE | 🔬 Research |

### Implementation Strategy

#### 1. Plugin Architecture

```python
# src/athena/architecture/extractors/base.py
class SpecExtractor(ABC):
    """Base class for spec extraction plugins."""

    @abstractmethod
    def can_extract(self, source: Path) -> bool:
        """Check if this extractor can handle the source."""
        pass

    @abstractmethod
    def extract(self, source: Path, config: dict) -> Specification:
        """Extract specification from source."""
        pass

    @abstractmethod
    def get_confidence(self) -> float:
        """Confidence score (0-1) for extraction accuracy."""
        pass
```

#### 2. FastAPI/Flask Extractor

```python
# src/athena/architecture/extractors/python_api.py
class PythonAPIExtractor(SpecExtractor):
    """Extract OpenAPI spec from Python web frameworks."""

    def can_extract(self, source: Path) -> bool:
        # Detect FastAPI/Flask imports
        content = source.read_text()
        return "from fastapi import" in content or "from flask import" in content

    def extract(self, source: Path, config: dict) -> Specification:
        # For FastAPI: Import app and call app.openapi()
        # For Flask: Use apispec to generate spec
        # Return Specification object
        pass
```

#### 3. Database Schema Extractor

```python
# src/athena/architecture/extractors/database.py
class DatabaseExtractor(SpecExtractor):
    """Extract Prisma schema from database."""

    def extract(self, source: str, config: dict) -> Specification:
        # Run: prisma db pull --schema=schema.prisma
        # Parse generated Prisma schema
        # Return Specification object
        pass
```

#### 4. GraphQL Introspection Extractor

```python
# src/athena/architecture/extractors/graphql.py
class GraphQLExtractor(SpecExtractor):
    """Extract GraphQL schema via introspection."""

    def extract(self, source: str, config: dict) -> Specification:
        # Use introspection query
        # Convert to SDL format
        # Return Specification object
        pass
```

### CLI Interface

```bash
# Auto-detect and extract from Python API file
athena-spec extract --from-code api/main.py --name "User API"

# Extract from database
athena-spec extract --from-db postgresql://localhost/mydb --name "Database Schema"

# Extract from GraphQL endpoint
athena-spec extract --from-graphql https://api.example.com/graphql --name "GraphQL API"

# Extract from directory (auto-detect all sources)
athena-spec extract --from-dir src/ --project-id 1

# Output:
# 🔍 Scanning src/ for extractable specs...
#
# ✅ Found FastAPI app in src/api/main.py
#    Extracted: User Management API (OpenAPI 3.0)
#    Confidence: 95%
#    Endpoints: 12
#
# ✅ Found Prisma schema in src/prisma/schema.prisma
#    Extracted: Database Schema (Prisma)
#    Confidence: 100%
#    Models: 8
#
# 📊 Summary:
#    Extracted: 2 specifications
#    Created: 2 database records
#    Files written: specs/api/user-api.yaml, specs/schemas/database.prisma
```

### Quality Metrics

Track extraction quality:

```python
class ExtractionResult:
    spec: Specification
    confidence: float  # 0-1 (how accurate we think it is)
    warnings: List[str]  # Missing info, ambiguities
    coverage: float  # % of code analyzed
    requires_review: bool  # Flag for human review
```

---

## Phase 4B: Document Storage & Templates [1 week]

### Document Types

```python
class DocumentType(Enum):
    # Product Documents
    PRD_LEAN = "prd_lean"              # Lean PRD (essential features only)
    PRD_AGILE = "prd_agile"            # Agile PRD (user stories, sprints)
    PRD_PROBLEM = "prd_problem"        # Problem-focused PRD
    MRD = "mrd"                        # Market Requirements

    # Technical Documents
    TDD = "tdd"                        # Technical Design Doc
    HLD = "hld"                        # High-Level Design
    LLD = "lld"                        # Low-Level Design

    # Architecture Documents
    ARC42 = "arc42"                    # arc42 template (12 sections)
    C4_CONTEXT = "c4_context"          # C4 Context diagram
    C4_CONTAINER = "c4_container"      # C4 Container diagram
    C4_COMPONENT = "c4_component"      # C4 Component diagram

    # API/Integration Documents
    API_DOC = "api_doc"                # API documentation
    API_GUIDE = "api_guide"            # Integration guide
    SDK_DOC = "sdk_doc"                # SDK documentation

    # Operational Documents
    RUNBOOK = "runbook"                # Operational runbook
    DEPLOYMENT_GUIDE = "deployment"    # Deployment guide
    TROUBLESHOOTING = "troubleshooting" # Troubleshooting guide

    # Change Documents
    CHANGELOG = "changelog"            # Release notes
    MIGRATION_GUIDE = "migration"      # Migration guide
    UPGRADE_GUIDE = "upgrade"          # Upgrade guide

class DocumentStatus(Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"

class Document(BaseModel):
    id: Optional[int]
    project_id: int
    name: str
    doc_type: DocumentType
    version: str
    status: DocumentStatus

    # Content
    content: str  # Markdown format
    file_path: Optional[str]  # Relative to docs/ directory

    # Relationships
    based_on_spec_ids: List[int] = []       # Generated from these specs
    based_on_doc_ids: List[int] = []        # Generated from these docs (PRD → TDD)
    related_adr_ids: List[int] = []
    implements_constraint_ids: List[int] = []

    # Generation metadata
    generated_by: Optional[str] = None      # "ai", "manual", "template"
    generation_prompt: Optional[str] = None # Prompt used for AI generation
    generation_model: Optional[str] = None  # "claude-3.5-sonnet", etc.
    last_synced_at: Optional[datetime] = None
    sync_hash: Optional[str] = None         # Hash of source specs (detect drift)

    # Validation
    validation_status: Optional[str] = None
    validated_at: Optional[datetime] = None

    # Metadata
    author: Optional[str] = None
    reviewers: List[str] = []
    tags: List[str] = []
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
```

### Template System

```
templates/
├── product/
│   ├── lean_prd.md           # Streamlined PRD
│   ├── agile_prd.md          # Agile PRD with user stories
│   ├── problem_prd.md        # Problem-focused PRD
│   └── mrd.md                # Market Requirements
├── technical/
│   ├── tdd_feature.md        # Feature TDD
│   ├── tdd_system.md         # System TDD
│   ├── hld.md                # High-Level Design
│   └── lld.md                # Low-Level Design
├── architecture/
│   ├── arc42/
│   │   ├── 01_introduction.md
│   │   ├── 02_constraints.md
│   │   ├── 03_context.md
│   │   ├── 04_solution_strategy.md
│   │   ├── 05_building_blocks.md
│   │   ├── 06_runtime_view.md
│   │   ├── 07_deployment_view.md
│   │   ├── 08_crosscutting_concepts.md
│   │   ├── 09_design_decisions.md
│   │   ├── 10_quality.md
│   │   ├── 11_risks.md
│   │   └── 12_glossary.md
│   ├── c4_context.md
│   ├── c4_container.md
│   └── c4_component.md
├── api/
│   ├── api_reference.md      # API documentation
│   ├── integration_guide.md  # Integration guide
│   └── sdk_guide.md          # SDK guide
├── operational/
│   ├── runbook.md
│   ├── deployment.md
│   └── troubleshooting.md
└── changelog/
    ├── semver_changelog.md   # Semantic versioning changelog
    └── migration_guide.md    # Migration guide for breaking changes
```

### Hybrid Storage (same as specs)

```
docs/                          # Git-tracked files (source of truth)
├── product/
│   ├── user-api-prd.md
│   └── mobile-app-prd.md
├── technical/
│   ├── auth-system-tdd.md
│   └── database-migration-tdd.md
├── architecture/
│   └── system-architecture-arc42.md
├── api/
│   └── user-api-reference.md
└── operational/
    └── deployment-runbook.md

Database (athena.db):
- documents table (metadata, relationships, generation info)
- Links to specs, ADRs, constraints
```

---

## Phase 4C: Document Generation (Specs → Docs) [2 weeks]

### Generation Strategies

#### 1. Template-Based Generation

```python
class TemplateDocGenerator:
    """Generate docs using Jinja2 templates."""

    def generate(self, template: str, context: dict) -> str:
        # Load template
        template = self.env.get_template(template)

        # Render with context (specs, ADRs, constraints)
        content = template.render(context)

        return content
```

#### 2. AI-Powered Generation

```python
class AIDocGenerator:
    """Generate docs using Claude."""

    def generate(self, doc_type: DocumentType, specs: List[Specification],
                 adrs: List[ADR], constraints: List[Constraint]) -> str:
        prompt = f"""Generate a {doc_type} document based on:

        Specifications:
        {self._format_specs(specs)}

        Architecture Decisions (ADRs):
        {self._format_adrs(adrs)}

        Constraints:
        {self._format_constraints(constraints)}

        Use the {doc_type} template format.
        """

        response = anthropic.messages.create(
            model="claude-3-5-sonnet-20250219",
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text
```

### Generation Types

#### A. API Documentation (from OpenAPI spec)

```bash
athena-doc generate api_doc \
  --from-spec 5 \
  --output docs/api/user-api.md

# Generated content:
# - Endpoint descriptions
# - Request/response examples
# - Authentication requirements
# - Error codes
# - Rate limiting info
```

#### B. PRD (from problem statement + specs)

```bash
athena-doc generate prd_lean \
  --from-spec 5,8 \
  --problem "Users need self-service account management" \
  --output docs/product/user-management-prd.md

# Generated sections:
# - Problem Statement
# - Goals & Success Metrics
# - User Stories
# - Features (from spec endpoints)
# - Out of Scope
# - Timeline
```

#### C. TDD (from PRD + specs)

```bash
athena-doc generate tdd \
  --from-doc 10 \  # PRD
  --from-spec 5,8 \
  --output docs/technical/user-system-tdd.md

# Generated sections:
# - Purpose & Objectives
# - System Architecture (from spec relationships)
# - Component Design (from spec schemas)
# - API Design (from OpenAPI spec)
# - Database Design (from Prisma spec)
# - Implementation Plan
# - Testing Strategy
```

#### D. Changelog (from spec diff)

```bash
athena-doc generate changelog \
  --from-diff 5 8 \
  --version 2.0.0 \
  --output CHANGELOG.md

# Generated content:
# ## v2.0.0 (2025-11-18)
#
# ### ⚠️ BREAKING CHANGES
# - Parameter `limit` is now required in GET /users
# - Endpoint DELETE /users/{id} removed
#
# ### ✨ Features
# - New endpoint POST /users for creating users
# - Added `created_at` field to User schema
#
# ### 🐛 Bug Fixes
# - (manual additions)
```

#### E. arc42 Architecture Doc (from ADRs + specs + constraints)

```bash
athena-doc generate arc42 \
  --from-adr 1,5,12 \
  --from-spec 5,8,10 \
  --from-constraint 3,7 \
  --output docs/architecture/system-architecture.md

# Generated 12 sections:
# 1. Introduction & Goals (from ADRs)
# 2. Constraints (from constraint records)
# 3. Context & Scope (from spec relationships)
# 4. Solution Strategy (from ADRs + patterns)
# 5. Building Block View (from specs)
# 6-12. ... (other arc42 sections)
```

### CLI Interface

```bash
# Generate single document
athena-doc generate <doc_type> \
  --from-spec <spec_ids> \
  --from-doc <doc_ids> \
  --from-adr <adr_ids> \
  --template <template_name> \
  --output <file_path> \
  --ai-enhanced  # Use Claude for generation

# Generate multiple related docs
athena-doc generate-suite \
  --from-spec 5 \
  --output-dir docs/user-api/ \
  --include api_doc,tdd,runbook

# Regenerate all docs for project
athena-doc regenerate-all --project-id 1

# Interactive generation (CLI prompts for inputs)
athena-doc generate-interactive
```

---

## Phase 4D: Sync & Drift Detection [1 week]

### Drift Detection

```python
class DriftDetector:
    """Detect when docs are out of sync with specs."""

    def detect_drift(self, doc: Document) -> DriftReport:
        # Get source specs
        specs = [self.spec_store.get(sid) for sid in doc.based_on_spec_ids]

        # Compute current hash
        current_hash = self._compute_spec_hash(specs)

        # Compare with stored hash
        if current_hash != doc.sync_hash:
            # Specs have changed - doc is stale
            changes = self._detect_spec_changes(doc.sync_hash, current_hash)
            return DriftReport(
                has_drift=True,
                drift_severity="high" if changes.breaking else "low",
                changes=changes,
                recommendation="Regenerate document"
            )

        return DriftReport(has_drift=False)
```

### Auto-Sync Strategies

#### 1. Manual Sync (user-triggered)

```bash
athena-doc sync --doc-id 15
# Regenerates doc from latest specs

athena-doc sync-all --project-id 1
# Syncs all docs in project
```

#### 2. Git Hook Sync (on spec changes)

```bash
# .git/hooks/post-commit
#!/bin/bash
# Auto-sync docs when specs change

changed_specs=$(git diff HEAD~1 --name-only | grep "^specs/")

if [ -n "$changed_specs" ]; then
    echo "Specs changed, syncing affected docs..."
    athena-doc auto-sync --changed-files "$changed_specs"
fi
```

#### 3. CI/CD Validation (fail on drift)

```yaml
# .github/workflows/docs-validation.yml
name: Validate Docs

on: [pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: pip install athena[docs]
      - run: athena-doc validate-all --strict
        # Exit code 1 if any doc has drift
```

### Validation Commands

```bash
# Check single doc for drift
athena-doc validate --doc-id 15

# Output:
# 🔍 Validating User API Documentation...
#
# ⚠️  DRIFT DETECTED
#    Based on specs: [5, 8]
#    Last synced: 2025-11-15 10:30:00
#    Specs changed: 2025-11-18 14:45:00
#
#    Changes detected:
#    - Spec 8: New endpoint POST /users/bulk
#    - Spec 8: Modified schema User (added field `roles`)
#
#    Recommendation: Run `athena-doc sync --doc-id 15`

# Check all docs in project
athena-doc validate-all --project-id 1

# Strict mode (for CI/CD)
athena-doc validate-all --strict
# Exit code 0: all docs synced
# Exit code 1: drift detected
```

---

## Phase 4E: Integration & Testing [0.5 weeks]

### Integration Points

1. **With existing spec system**:
   - Documents reference specs via `based_on_spec_ids`
   - Specs link back to generated docs

2. **With ADR system**:
   - Architecture docs pull from ADRs
   - ADRs can generate architecture sections

3. **With constraint system**:
   - TDDs include constraint validation
   - arc42 docs list constraints

4. **With diff system**:
   - Changelogs generated from diffs
   - Migration guides from breaking changes

### Testing Strategy

```bash
# Unit tests
tests/architecture/test_extractors.py     # 15+ tests per extractor
tests/architecture/test_doc_store.py      # CRUD operations
tests/architecture/test_doc_generator.py  # Generation logic
tests/architecture/test_drift_detector.py # Drift detection

# Integration tests
tests/architecture/test_extract_to_spec.py  # End-to-end extraction
tests/architecture/test_spec_to_doc.py      # End-to-end generation
tests/architecture/test_doc_sync.py         # Sync workflows

# CLI tests
tests/cli/test_spec_extract.py
tests/cli/test_doc_generate.py

# Total: 60+ tests
```

---

## Benefits

### For Teams Starting Fresh
1. Write specs first → Generate docs → Generate code
2. Specs are source of truth
3. Docs always in sync with specs

### For Teams with Existing Code (Most Common!)
1. Extract specs from code → Generate docs from specs
2. Now specs become source of truth
3. Future changes: Update specs → Regenerate docs

### Universal Benefits
1. **Single Source of Truth**: Specs drive everything
2. **Always Up-to-Date**: Regenerate docs when specs change
3. **Consistent Format**: Templates ensure uniformity
4. **Traceability**: Link code ↔ specs ↔ docs ↔ ADRs
5. **Drift Detection**: Know when docs are stale
6. **CI/CD Integration**: Fail builds on drift

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Extraction inaccuracy | Low confidence specs | Quality scores, human review flags |
| Template complexity | Hard to maintain | Start simple, add templates gradually |
| AI generation cost | High API usage | Cache, incremental updates, user opt-in |
| Storage overhead | More files to manage | Hybrid storage, prune old versions |
| User confusion | Too many doc types | Start with 3-5 core types, expand later |

---

## Rollout Plan

### MVP (Phase 4 Core)

**Week 1-2: Extraction**
- FastAPI/Flask extractor
- Database introspection (Prisma)
- CLI: `athena-spec extract`

**Week 3: Document Storage**
- Document model & store
- Hybrid storage (files + DB)
- CLI: `athena-doc create`

**Week 4: Generation (Basic)**
- API doc generation (OpenAPI → Markdown)
- Changelog generation (diff → CHANGELOG.md)
- Template system

**Week 5: Sync & Validation**
- Drift detection
- Manual sync
- CLI: `athena-doc validate`

### Future Enhancements (Phase 5+)

- GraphQL introspection extractor
- Static analysis extractor (Semgrep)
- C4 diagram generation (Mermaid)
- arc42 full template
- PRD → TDD workflow
- Real-time sync (file watchers)
- Visual Studio Code extension

---

## Success Metrics

### Extraction Quality
- Confidence score > 80% for supported frameworks
- Coverage: 90%+ of API endpoints detected
- False positive rate < 5%

### Generation Quality
- User satisfaction: 4+ / 5 stars
- Docs require < 20% manual edits
- Generation time < 30s per doc

### Adoption
- 50%+ of users use extraction within 1 month
- 75%+ of users use doc generation within 2 months
- 5+ doc types in active use

---

## Open Questions

1. **Should we support bidirectional sync?** (docs → specs)
   - Pro: Full round-trip editing
   - Con: Complex, risk of conflicts

2. **How much AI to use?**
   - Option A: AI-first (Claude generates everything)
   - Option B: Template-first (AI enhances)
   - Option C: Hybrid (user chooses)

3. **What's the right granularity?**
   - Per-endpoint docs vs whole API docs?
   - Monolithic arc42 vs modular sections?

4. **How to handle conflicts?**
   - Manual sync overwrites docs?
   - Three-way merge (base, spec, doc)?
   - Git-like conflict markers?

---

## Next Steps

1. **User Research** (1 day)
   - Survey users: What docs do you need most?
   - What extraction sources are most common?
   - Current pain points with docs?

2. **Prototype** (3 days)
   - Build FastAPI extractor
   - Build API doc generator
   - Test end-to-end workflow

3. **Design Review** (1 day)
   - Review this plan with stakeholders
   - Prioritize features
   - Set timeline

4. **Implementation** (4-5 weeks)
   - Follow rollout plan above

---

**Ready to proceed? Should we start with a prototype to validate the approach?**
