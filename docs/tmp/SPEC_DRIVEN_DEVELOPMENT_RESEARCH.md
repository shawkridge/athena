# Spec-Driven Development Research & Integration Plan

**Date**: November 18, 2025
**Purpose**: Research spec-driven development and design integration with Athena

---

## Executive Summary

Spec-driven development (SDD) is **the major trend of 2025** in AI-assisted coding. The fundamental shift: **"intent is the source of truth"** - specifications define behavior, AI generates code from specs.

**Key Finding**: Specifications are no longer documentation - they're **executable contracts** that AI uses to generate 95%+ accurate code.

**Recommendation for Athena**: Add a **Specification Store** as a new component in the architecture layer, treating specs as first-class citizens alongside ADRs, patterns, and constraints.

---

## What Is Spec-Driven Development?

### The Paradigm Shift

**Old Way** (2024 and before):
```
Code → Documentation
(Code is source of truth, docs get stale)
```

**New Way** (2025):
```
Specification → AI-Generated Code
(Spec is source of truth, code is derived artifact)
```

### The Workflow

**Proven 2025 Workflow**:
```
1. Specify   → Write detailed specification (human)
2. Plan      → Break down into tasks (AI-assisted)
3. Tasks     → Create implementation tasks (AI)
4. Implement → Generate code from spec (AI)
5. Validate  → Verify code matches spec (automated)
```

**Time Investment**:
- Specification: 20-40% of manual implementation time
- AI generation: 50-80% faster than manual coding
- **ROI positive when AI saves 50%+ time**

### Why It's Trending in 2025

1. **AI context windows**: Now 200K+ tokens, can process full specifications
2. **Vibe coding fatigue**: "Just ask AI" leads to inconsistent, unmaintainable code
3. **GitHub Spec Kit**: Released September 2, 2025 (open source)
4. **Kiro IDE**: AI-powered IDE (VS Code fork) with spec-first UI
5. **Major adoption**: JetBrains, GitHub, Red Hat all launched SDD tools in 2025

---

## Spec-Driven Development Tools (2025)

### 1. GitHub Spec Kit (v0.0.30+)

**Released**: September 2, 2025
**Type**: Open-source CLI
**Integration**: Works with GitHub Copilot, Claude Code, Gemini CLI

**Features**:
- Markdown-based specifications
- AI-assisted spec generation
- Code generation from specs
- Spec-to-code validation
- Version control integration

**Workflow**:
```bash
# 1. Initialize spec
spec-kit init my-project

# 2. Write specification
# Edit spec.md with requirements

# 3. Generate code
spec-kit generate

# 4. Validate implementation
spec-kit validate
```

### 2. Kiro IDE

**Type**: AI-powered IDE (fork of VS Code)
**Focus**: Spec-driven development front and center

**Features**:
- Spec editor as primary interface
- Live code generation from specs
- Continuous regeneration on spec changes
- Built-in spec validation

### 3. Tessl

**Type**: Specification-centric platform
**Focus**: Continuous code regeneration

**Approach**: Treat code as ephemeral, regenerate from spec whenever needed

### 4. OpenAPI Ecosystem

**Standard**: OpenAPI Specification (OAS) v3
**Maturity**: Industry standard for APIs

**Tools**:
- OpenAPI Generator: Generate client SDKs, server stubs, docs
- Swagger Codegen: API code generation
- Stainless API: Advanced SDK generation with AI

**Usage**:
```yaml
# openapi.yaml
openapi: 3.0.0
info:
  title: User API
  version: 1.0.0
paths:
  /users:
    get:
      summary: List users
      responses:
        '200':
          description: Success
```

**Code Generation**:
```bash
openapi-generator generate -i openapi.yaml -g python-flask -o ./server
```

---

## Formal Specification Languages

### TLA+ (Temporal Logic of Actions)

**Creator**: Leslie Lamport (Turing Award winner)
**Use**: Distributed systems, concurrent systems
**Adoption**: Amazon (DynamoDB, S3, EBS), Microsoft

**Strengths**:
- Models temporal properties (how system evolves over time)
- Finds subtle concurrency bugs
- Formal verification via model checking

**Example**:
```tla
---- MODULE UserAuth ----
VARIABLES users, sessions

Init == users = {} /\ sessions = {}

Login(u) ==
    /\ u \in users
    /\ sessions' = sessions \cup {u}

Logout(u) ==
    /\ u \in sessions
    /\ sessions' = sessions \ {u}
====
```

**Industry Use**:
- AWS found bugs in 7 distributed systems using TLA+
- Prevented critical issues that code review missed

### Alloy (Structural Modeling)

**Latest**: Alloy 6.2.0 (January 9, 2025)
**Use**: Structural properties, data models
**Adoption**: Academic research, NASA, financial systems

**Strengths**:
- Models structural properties (relationships, constraints)
- Alloy 6 adds temporal logic (now competitive with TLA+)
- Visual model exploration via Alloy Analyzer

**Example**:
```alloy
sig User {
    friends: set User,
    groups: set Group
}

sig Group {
    members: set User
}

// Constraint: Users can only be in groups where they're members
fact {
    all u: User, g: Group |
        u in g.members iff g in u.groups
}
```

**Recent Development** (2025):
- Alloy 6 adds mutable state and temporal operators
- Now handles both structure AND behavior

### Comparison: TLA+ vs. Alloy vs. OpenAPI

| Aspect | TLA+ | Alloy | OpenAPI |
|--------|------|-------|---------|
| **Focus** | Temporal behavior | Structural properties | API contracts |
| **Use Case** | Distributed systems | Data models, systems | REST APIs |
| **Maturity** | Mature (20+ years) | Mature (20+ years) | Mature (industry standard) |
| **AI Integration** | Limited | Limited | Excellent |
| **Learning Curve** | Steep | Moderate | Easy |
| **Industry Adoption** | AWS, Microsoft | Academic | Universal |
| **Code Generation** | No | No | Yes |
| **Verification** | Model checking | Model finding | Validation |

---

## Specification Formats for Different Domains

### API Specifications

**Format**: OpenAPI (YAML/JSON)
**Purpose**: REST API contracts
**Adoption**: Industry standard

**Example**:
```yaml
openapi: 3.0.0
paths:
  /users/{userId}:
    get:
      parameters:
        - name: userId
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: User found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
```

### Data Specifications

**Format**: JSON Schema
**Purpose**: Data structure validation
**Adoption**: Universal

**Example**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "username": {
      "type": "string",
      "minLength": 3,
      "maxLength": 20
    },
    "email": {
      "type": "string",
      "format": "email"
    }
  },
  "required": ["username", "email"]
}
```

### System Behavior Specifications

**Format**: Markdown + Structured Sections
**Purpose**: Feature specifications, requirements
**Adoption**: GitHub Spec Kit, Tessl, Kiro

**Example**:
```markdown
# User Authentication System

## Requirements
- Users must authenticate with username/password
- Sessions expire after 30 minutes of inactivity
- Failed login attempts are rate-limited (5 per hour)

## API Endpoints

### POST /auth/login
**Input**: { username: string, password: string }
**Output**: { token: string, expiresAt: timestamp }
**Errors**: 401 (invalid credentials), 429 (rate limited)

## Security Constraints
- Passwords must be hashed with bcrypt
- Tokens must be JWT with HS256
- Rate limiting per IP address

## Success Criteria
- [ ] Login with valid credentials succeeds
- [ ] Login with invalid credentials returns 401
- [ ] 6th failed attempt within hour returns 429
- [ ] Session expires after 30 minutes
```

### Database Schema Specifications

**Format**: SQL DDL or Prisma Schema
**Purpose**: Database structure
**Adoption**: Universal (SQL), growing (Prisma)

**Example (Prisma)**:
```prisma
model User {
  id        Int      @id @default(autoincrement())
  email     String   @unique
  username  String   @unique
  password  String   // bcrypt hashed
  sessions  Session[]
  createdAt DateTime @default(now())
}

model Session {
  id        String   @id @default(uuid())
  userId    Int
  user      User     @relation(fields: [userId], references: [id])
  token     String   @unique
  expiresAt DateTime
  createdAt DateTime @default(now())
}
```

---

## Specification Versioning & Storage

### Versioning Approaches

#### 1. Semantic Versioning (SemVer)

**Format**: MAJOR.MINOR.PATCH (e.g., 2.1.3)
**Use**: Most common, recommended by AWS
**Meaning**:
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes (backward compatible)

**Example**:
```yaml
# spec.yaml
version: 2.1.3
specification:
  # ... spec content ...
```

#### 2. Date-Based Versioning

**Format**: YYYY-MM-DD
**Use**: MCP (Model Context Protocol), calendar versioning
**Example**: 2025-06-18

**Benefits**:
- Clear chronological ordering
- No ambiguity about age
- Easy to understand

#### 3. Git-Based Versioning

**Format**: Git commit SHA or tag
**Use**: Treat specs as code, version in git
**Example**: v1.2.3 (tag) or abc123def (commit)

**Benefits**:
- Leverages existing version control
- Automatic history tracking
- Branching for spec variants

### Storage Strategies

#### Option 1: File-Based (Recommended for Start)

**Structure**:
```
specs/
├── api/
│   ├── openapi.yaml (v3.1.0)
│   └── schemas/
│       ├── user.json
│       └── session.json
├── features/
│   ├── authentication.md
│   ├── user-management.md
│   └── notifications.md
├── formal/
│   ├── consistency.tla
│   └── data-model.als
└── database/
    └── schema.prisma
```

**Benefits**:
- Works with git naturally
- Easy to edit (text files)
- Diffable and mergeable
- Tools can process directly

**Version Control**:
```bash
git add specs/api/openapi.yaml
git commit -m "spec: Add user authentication endpoints"
git tag v1.2.0
```

#### Option 2: Database-Based

**Structure** (PostgreSQL):
```sql
CREATE TABLE specifications (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    name VARCHAR(255) NOT NULL,
    spec_type VARCHAR(50), -- 'openapi', 'markdown', 'tla+', etc.
    version VARCHAR(50),    -- SemVer or date
    content TEXT,           -- Actual spec content
    format VARCHAR(20),     -- 'yaml', 'json', 'markdown', 'tla+'
    status VARCHAR(20),     -- 'draft', 'active', 'deprecated'

    -- Relationships
    related_adr_ids INTEGER[], -- Link to ADRs
    implements_constraint_ids INTEGER[], -- Which constraints it satisfies
    uses_pattern_ids INTEGER[], -- Which patterns it uses

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255),

    -- Validation
    is_valid BOOLEAN DEFAULT TRUE,
    validation_errors JSONB,
    last_validated_at TIMESTAMP,

    UNIQUE(project_id, name, version)
);

CREATE TABLE spec_versions (
    id SERIAL PRIMARY KEY,
    spec_id INTEGER REFERENCES specifications(id),
    version VARCHAR(50),
    content TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255),
    change_summary TEXT
);

CREATE TABLE spec_dependencies (
    id SERIAL PRIMARY KEY,
    source_spec_id INTEGER REFERENCES specifications(id),
    target_spec_id INTEGER REFERENCES specifications(id),
    dependency_type VARCHAR(50), -- 'imports', 'extends', 'implements'
    UNIQUE(source_spec_id, target_spec_id, dependency_type)
);
```

**Benefits**:
- Queryable (find all specs using pattern X)
- Relationships tracked (spec → ADR → constraint)
- Version history built-in
- Access control possible

**Challenges**:
- Not as git-friendly (binary blob in db)
- Harder to diff
- Need tooling to extract/edit

#### Option 3: Hybrid (Best of Both)

**Approach**: Store specs as files in git, metadata in database

**File Structure**:
```
specs/
└── features/
    ├── authentication.md (actual spec)
    └── metadata.json (links to ADRs, constraints)
```

**Database**:
```sql
CREATE TABLE spec_metadata (
    id SERIAL PRIMARY KEY,
    project_id INTEGER,
    file_path TEXT NOT NULL, -- Path in git repo
    spec_type VARCHAR(50),
    version VARCHAR(50),
    git_sha VARCHAR(40),     -- Git commit SHA

    -- Relationships
    related_adr_ids INTEGER[],
    implements_constraint_ids INTEGER[],
    uses_pattern_ids INTEGER[],

    -- Validation
    is_valid BOOLEAN,
    validation_errors JSONB,
    last_validated_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Workflow**:
1. Edit spec file in `specs/features/auth.md`
2. Commit to git: `git commit -m "spec: Update auth flow"`
3. Hook updates database with metadata: `INSERT INTO spec_metadata ...`
4. Can query: "Show all specs that use ADR-12"
5. Can view: `git show abc123:specs/features/auth.md`

**Benefits**:
- ✅ Files in git (easy to edit, diff, merge)
- ✅ Metadata in database (queryable, relational)
- ✅ Best of both worlds

---

## Integration with Athena Architecture Layer

### Current State

Athena has:
- **ADRs** - Document DECISIONS (why we chose X)
- **Patterns** - Provide SOLUTIONS (how to solve problem Y)
- **Constraints** - Define RULES (system must satisfy Z)

**Missing**: **Specifications** - Define BEHAVIOR (what system should do)

### Proposed Integration

Add **Specification Store** as 4th pillar:

```
Architecture Layer (Layer 9)
├── ADR Store         → WHY (decisions)
├── Pattern Library   → HOW (solutions)
├── Constraint Tracker → RULES (requirements)
└── Specification Store → WHAT (behavior)  ← NEW
```

### Relationship Model

```
Specification
  ↓ implements
ADR (decision)
  ↓ uses
Pattern (solution)
  ↓ satisfies
Constraint (rule)
```

**Example Flow**:
1. **ADR-12**: Decide to use JWT authentication
2. **Pattern**: Token-Based Auth pattern
3. **Constraint**: All endpoints must require authentication
4. **Specification**: Define JWT auth endpoints, token format, expiration

### Data Model

```python
@dataclass
class Specification:
    """A formal specification of system behavior."""
    id: Optional[int]
    project_id: int
    name: str  # e.g., "User Authentication"
    spec_type: SpecType  # openapi, markdown, tla+, alloy, prisma
    version: str  # SemVer or date
    content: str  # Actual spec content
    format: SpecFormat  # yaml, json, markdown, tla+
    status: SpecStatus  # draft, active, deprecated

    # Relationships
    related_adr_ids: List[int]
    implements_constraint_ids: List[int]
    uses_pattern_ids: List[int]

    # Validation
    is_valid: bool
    validation_errors: Optional[Dict[str, Any]]
    last_validated_at: Optional[datetime]

    # Metadata
    created_at: datetime
    updated_at: datetime
    created_by: str

class SpecType(str, Enum):
    OPENAPI = "openapi"       # REST APIs
    MARKDOWN = "markdown"     # Feature specs
    TLA_PLUS = "tla+"        # Formal verification
    ALLOY = "alloy"          # Structural models
    PRISMA = "prisma"        # Database schemas
    JSON_SCHEMA = "json_schema"  # Data structures
    GRAPHQL = "graphql"      # GraphQL schemas

class SpecFormat(str, Enum):
    YAML = "yaml"
    JSON = "json"
    MARKDOWN = "markdown"
    TLA_PLUS = "tla+"
    ALLOY = "alloy"

class SpecStatus(str, Enum):
    DRAFT = "draft"          # Work in progress
    ACTIVE = "active"        # Current, in use
    DEPRECATED = "deprecated"  # Superseded
```

### Storage Recommendation

**Use Hybrid Approach**:

1. **Specs as files** in `specs/` directory (git-tracked)
2. **Metadata in database** (relationships, validation)
3. **Git hooks** sync file changes to database

**Directory Structure**:
```
athena-project/
├── specs/
│   ├── api/
│   │   ├── openapi.yaml (v1.2.0)
│   │   └── README.md
│   ├── features/
│   │   ├── authentication.md
│   │   ├── user-management.md
│   │   └── notifications.md
│   ├── formal/
│   │   ├── auth-flow.tla
│   │   └── data-consistency.als
│   ├── database/
│   │   └── schema.prisma
│   └── metadata/
│       ├── authentication.json  # Links to ADR-12, Constraint-8
│       └── user-management.json
├── docs/
│   └── adrs/
│       └── ADR-012-jwt-auth.md  # Referenced by auth spec
└── src/
    └── api/  # Generated from openapi.yaml
```

**Metadata File Example** (`specs/metadata/authentication.json`):
```json
{
  "spec_name": "User Authentication",
  "file_path": "specs/features/authentication.md",
  "version": "1.2.0",
  "spec_type": "markdown",
  "status": "active",

  "relationships": {
    "implements_adrs": [12, 15],
    "satisfies_constraints": [8, 10],
    "uses_patterns": ["Token-Based Auth", "Rate Limiting"]
  },

  "validation": {
    "is_valid": true,
    "last_validated": "2025-11-18T10:30:00Z",
    "validation_tool": "spec-kit validate"
  },

  "git_info": {
    "last_commit": "abc123def456",
    "last_updated": "2025-11-15T14:22:00Z",
    "author": "john@example.com"
  }
}
```

---

## Workflow: Spec-Driven Development with Athena

### Phase 1: Architectural Decision
```
1. Discuss architecture with Claude
2. architectural-alignment skill validates
3. decision-documentation skill suggests creating ADR
4. Create ADR-12: "Use JWT Authentication"
```

### Phase 2: Specification
```
5. Create specification: specs/features/authentication.md
6. Link to ADR-12 in metadata
7. Define:
   - Requirements
   - API endpoints
   - Security constraints
   - Success criteria
8. Validate spec: spec-kit validate
```

### Phase 3: Planning
```
9. Use planning layer: "Plan implementation of authentication.md"
10. Planning reads spec + ADR-12 + constraints
11. Creates implementation plan:
    - Task 1: Set up JWT library
    - Task 2: Implement login endpoint
    - Task 3: Add rate limiting
    - Task 4: Write tests
```

### Phase 4: Implementation
```
12. AI generates code from spec
13. Fitness functions validate:
    - Code matches ADR decisions
    - Satisfies constraints
    - Follows patterns
14. Impact analysis checks blast radius
15. PR review bot validates architecture alignment
```

### Phase 5: Validation
```
16. Run spec validation: spec-kit validate
17. Compare generated code against spec
18. Measure spec-to-code accuracy (target: 95%+)
19. Update spec if implementation reveals issues
```

---

## Implementation Roadmap for Athena

### Phase 1: Basic Spec Storage (1 week)

**Goal**: Store specs as files, track in database

**Tasks**:
1. Create `SpecificationStore` class
2. Add database schema for spec metadata
3. Support markdown and OpenAPI formats
4. Link specs to ADRs/patterns/constraints
5. Add CLI: `athena-spec create/list/get`

**Deliverables**:
- `src/athena/architecture/spec_store.py`
- `specs/` directory structure
- Basic CRUD operations
- Documentation

### Phase 2: Spec Validation (1 week)

**Goal**: Validate specs and track accuracy

**Tasks**:
1. Integrate OpenAPI validation (swagger-cli)
2. Add custom markdown spec validation
3. Track spec-to-code accuracy
4. Add fitness function: "Code matches spec"
5. CLI: `athena-spec validate`

**Deliverables**:
- Validation framework
- Accuracy tracking
- Fitness function integration
- Validation reports

### Phase 3: Spec-to-Plan Integration (3 days)

**Goal**: Planning layer reads specs

**Tasks**:
1. Update planning layer to read specs
2. Generate tasks from spec requirements
3. Validate plan against spec
4. Link plan items to spec sections

**Deliverables**:
- Spec-aware planning
- Spec → Plan workflow
- Validation integration

### Phase 4: AI Code Generation (1 week)

**Goal**: Generate code from specs

**Tasks**:
1. Integrate OpenAPI Generator
2. Add spec-to-code generation tool
3. Measure generation accuracy
4. Add feedback loop (spec ↔ code)
5. CLI: `athena-spec generate`

**Deliverables**:
- Code generation from OpenAPI
- Accuracy measurement
- Generation reports

### Phase 5: Advanced Formats (2 weeks - Optional)

**Goal**: Support TLA+, Alloy, Prisma

**Tasks**:
1. Add TLA+ spec storage
2. Add Alloy spec storage
3. Integrate model checkers
4. Add Prisma schema support
5. Documentation and examples

**Deliverables**:
- Multi-format support
- Formal verification integration
- Database schema generation

---

## Recommended Approach for Athena

### Minimal Viable Implementation

**Start Simple**:
1. **Markdown specs** for feature specifications
2. **OpenAPI specs** for API contracts
3. **Store as files** in `specs/` directory
4. **Metadata in database** for relationships
5. **Basic validation** (format checking, link validation)

**Example**:
```python
# src/athena/architecture/spec_store.py
class SpecificationStore:
    def create_spec(
        self,
        project_id: int,
        name: str,
        spec_type: SpecType,
        content: str,
        related_adr_ids: List[int] = [],
    ) -> int:
        """Create new specification."""
        # Save content to file
        file_path = self._save_to_file(name, content, spec_type)

        # Store metadata in database
        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO specifications
            (project_id, name, spec_type, file_path, related_adr_ids)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (project_id, name, spec_type.value, file_path, related_adr_ids))

        return cursor.fetchone()[0]

    def validate_spec(self, spec_id: int) -> Dict[str, Any]:
        """Validate specification."""
        spec = self.get_spec(spec_id)

        if spec.spec_type == SpecType.OPENAPI:
            return self._validate_openapi(spec.content)
        elif spec.spec_type == SpecType.MARKDOWN:
            return self._validate_markdown(spec.content)

        return {"is_valid": True, "errors": []}
```

### Integration Points

1. **With ADRs**: Specs implement decisions
2. **With Constraints**: Specs must satisfy constraints
3. **With Patterns**: Specs use patterns
4. **With Planning**: Plans generated from specs
5. **With Fitness**: Code validated against specs
6. **With Impact Analysis**: Spec changes analyzed

---

## Metrics to Track

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Spec Coverage** | 80%+ | % of features with specs |
| **Spec-to-Code Accuracy** | 95%+ | % of generated code matching spec |
| **Spec Freshness** | <1 month | Days since last spec update |
| **Spec Completeness** | 90%+ | % of spec sections completed |
| **Validation Success Rate** | 95%+ | % of specs passing validation |
| **Spec-Driven Workflow Adoption** | 70%+ | % of features starting with spec |

---

## Conclusion

**Spec-driven development is the future** (or rather, the present as of 2025). For Athena to be a complete architecture-AI system, it should:

1. ✅ **Add Specification Store** - 4th pillar alongside ADRs, patterns, constraints
2. ✅ **Hybrid storage** - Files in git, metadata in database
3. ✅ **Start simple** - Markdown + OpenAPI, expand later
4. ✅ **Integrate with existing** - Specs link to ADRs, constraints, patterns
5. ✅ **Enable spec-to-code** - Generate code, validate accuracy
6. ✅ **Track metrics** - Measure spec coverage and accuracy

**Estimated Effort**: 2-3 weeks for complete implementation
**Priority**: High (aligns with 2025 industry trend)

---

**Research Sources**: 5 web searches covering spec-driven development, OpenAPI, TLA+/Alloy, specification storage, and spec-first API development (November 2025)
