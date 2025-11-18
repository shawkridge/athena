# Spec-Driven Development in Athena

**Status**: Phase 2 Complete (Validation)
**Version**: 2.0.0
**Last Updated**: November 18, 2025

## Table of Contents

- [Overview](#overview)
- [Key Concepts](#key-concepts)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [CLI Reference](#cli-reference)
- [Integration with Architecture Layer](#integration-with-architecture-layer)
- [Workflow Examples](#workflow-examples)
- [Roadmap](#roadmap)

---

## Overview

Spec-driven development treats specifications as the **source of truth** for system behavior. Instead of writing code first and documenting later, you write specifications first and derive code from them.

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

### Benefits

- **Intent is Source of Truth**: Specifications define WHAT the system should do
- **Automated Validation**: Detect drift between spec and implementation
- **AI Code Generation**: Generate code from specs (coming in Phase 4)
- **Architecture Alignment**: Specs integrate with ADRs, constraints, and patterns
- **Version Control**: Track spec evolution alongside code

---

## Key Concepts

### 1. Specification Types

Athena supports multiple specification formats:

| Type | Extension | Use Case |
|------|-----------|----------|
| **OpenAPI** | `.yaml`, `.json` | REST API contracts |
| **GraphQL** | `.graphql`, `.gql` | GraphQL schemas |
| **AsyncAPI** | `.yaml` | Event-driven API specs |
| **TLA+** | `.tla` | Formal specifications for distributed systems |
| **Alloy** | `.als` | Structural modeling |
| **Prisma** | `.prisma` | Database schemas |
| **Proto** | `.proto` | Protocol Buffers |
| **JSON Schema** | `.json` | Data structure validation |
| **Markdown** | `.md` | General specifications |

### 2. Specification Lifecycle

```
draft → active → deprecated → superseded
```

- **draft**: Work in progress
- **active**: Current specification in use
- **deprecated**: No longer recommended but still valid
- **superseded**: Replaced by newer specification

### 3. Relationships

Specifications connect to other architecture components:

- **ADRs** (related_adr_ids): WHY decisions were made
- **Constraints** (implements_constraint_ids): RULES the spec must satisfy
- **Patterns** (uses_pattern_ids): HOW solutions are implemented

---

## Architecture

### Hybrid Storage Approach

Athena uses a **hybrid storage model**:

```
specs/                          # Git-tracked files (source of truth)
├── api/
│   ├── users.yaml              # OpenAPI spec for users API
│   └── auth.yaml               # OpenAPI spec for auth API
├── schemas/
│   └── database.prisma         # Prisma schema
└── formal/
    └── consensus.tla           # TLA+ specification

Database (PostgreSQL/SQLite)    # Metadata and relationships
├── specifications table
│   ├── id, name, version
│   ├── file_path               # Link to git file
│   ├── spec_type, status
│   ├── related_adr_ids         # Relationships
│   ├── validation_status       # Validation results
│   └── ...
```

**Why Hybrid?**

- **Files in Git**: Enables diff, blame, PR reviews, version control
- **Metadata in DB**: Enables queries, relationships, validation tracking
- **Sync Mechanism**: Keep files and database in sync

### Architecture Layer Integration

```
Layer 9: Architecture (Design & Context Engineering)
├── ADR Store         → WHY (decisions)
├── Pattern Library   → HOW (solutions)
├── Constraint Tracker → RULES (requirements)
└── Specification Store → WHAT (behavior)  ← NEW!
```

---

## Getting Started

### 1. Install Athena

```bash
pip install -e .
```

### 2. Initialize Specs Directory

The `specs/` directory is automatically created when you first use the specification store:

```bash
athena-spec-manage list
```

This creates:
```
specs/
├── .gitkeep        # Track empty directory in git
└── README.md       # Documentation
```

### 3. Create Your First Specification

**Option A: Using CLI**

```bash
athena-spec-manage create \
  --name "User API" \
  --type openapi \
  --file-path "api/users.yaml" \
  --content-file my-openapi-spec.yaml
```

**Option B: Using Python API**

```python
from athena.core.database import get_database
from athena.architecture.spec_store import SpecificationStore
from athena.architecture.models import Specification, SpecType, SpecStatus

db = get_database()
store = SpecificationStore(db)

spec = Specification(
    project_id=1,
    name="User Authentication API",
    spec_type=SpecType.OPENAPI,
    version="1.0.0",
    status=SpecStatus.ACTIVE,
    content="""openapi: 3.0.0
info:
  title: User API
  version: 1.0.0
paths:
  /auth/login:
    post:
      summary: User login
      responses:
        '200':
          description: Successful login
""",
    file_path="api/auth.yaml",
    description="Authentication endpoints",
)

spec_id = store.create(spec, write_to_file=True)
```

### 4. Link to Architecture

```python
# Link spec to ADR
spec.related_adr_ids = [12]  # ADR-12: Use JWT authentication

# Link spec to constraints
spec.implements_constraint_ids = [5, 6]  # Security constraints

# Link spec to patterns
spec.uses_pattern_ids = ["repository", "factory"]

store.update(spec)
```

---

## CLI Reference

### List Specifications

```bash
# List all specifications
athena-spec-manage list

# Filter by type
athena-spec-manage list --type openapi

# Filter by status
athena-spec-manage list --status active

# JSON output
athena-spec-manage list --json
```

### Create Specification

```bash
# From file
athena-spec-manage create \
  --name "User API" \
  --type openapi \
  --file-path "api/users.yaml" \
  --content-file spec.yaml

# From stdin
cat spec.yaml | athena-spec-manage create \
  --name "User API" \
  --type openapi \
  --file-path "api/users.yaml"

# With metadata
athena-spec-manage create \
  --name "User API" \
  --type openapi \
  --file-path "api/users.yaml" \
  --content-file spec.yaml \
  --description "User management endpoints" \
  --author "Jane Doe" \
  --tags "auth,api,users"
```

### Update Specification

```bash
# Update content
athena-spec-manage update \
  --spec-id 5 \
  --content-file updated-spec.yaml

# Update metadata
athena-spec-manage update \
  --spec-id 5 \
  --version "2.0.0" \
  --status deprecated

# Update without touching file
athena-spec-manage update \
  --spec-id 5 \
  --version "2.0.0" \
  --no-write-file
```

### Show Specification

```bash
# Show metadata
athena-spec-manage show --spec-id 5

# Show with full content
athena-spec-manage show --spec-id 5 --show-content

# JSON output
athena-spec-manage show --spec-id 5 --json
```

### Delete Specification

```bash
# Delete from database only
athena-spec-manage delete --spec-id 5

# Delete database record AND file
athena-spec-manage delete --spec-id 5 --delete-file

# Skip confirmation
athena-spec-manage delete --spec-id 5 --yes
```

### Sync from Filesystem

```bash
# Sync all spec files to database
athena-spec-manage sync --project-id 1

# Output:
# ✅ Sync complete:
#    Created: 5
#    Updated: 2
#    Skipped: 3
```

### Validate Specification

```bash
# Validate spec and update database
athena-spec-manage validate --spec-id 5

# Output:
# 🔍 Validating User Authentication API (v1.0.0)...
#    Type: openapi
#
# ✅ Validation passed - specification is valid!
#    Validator: openapi-spec-validator
#
# Validated at: 2025-11-18 14:30:45
# Status: valid

# Validate without updating database
athena-spec-manage validate --spec-id 5 --no-update-db
```

**Supported Validators**:
- **OpenAPI 3.0/3.1**: Validates against OpenAPI specification
- **JSON Schema**: Validates schema structure
- **GraphQL**: Validates GraphQL SDL syntax
- **AsyncAPI**: Coming in Phase 5

**Installation**:
```bash
# Install validation libraries (optional)
pip install 'athena[validation]'
```

---

## Integration with Architecture Layer

### 1. Link Spec to ADR

When a specification implements an architectural decision:

```python
# Spec for authentication API
auth_spec = store.get(5)
auth_spec.related_adr_ids = [12]  # ADR-12: Use JWT authentication
store.update(auth_spec)
```

### 2. Link Spec to Constraints

When a specification must satisfy constraints:

```python
# Spec must meet security constraints
api_spec = store.get(10)
api_spec.implements_constraint_ids = [
    5,   # Must use HTTPS
    6,   # Must support OAuth 2.0
    7,   # Must rate-limit to 1000 req/min
]
store.update(api_spec)
```

### 3. Link Spec to Patterns

When a specification uses design patterns:

```python
# Spec uses repository and factory patterns
service_spec = store.get(15)
service_spec.uses_pattern_ids = ["repository", "factory", "singleton"]
store.update(service_spec)
```

### 4. Use in Planning Layer (Phase 3)

```python
# Planning reads specs to understand system behavior (coming soon)
from athena.planning import PlanValidator

validator = PlanValidator(spec_store)
plan = validator.create_plan_from_spec(spec_id=5)
```

---

## Workflow Examples

### Example 1: API-First Development

```bash
# 1. Write OpenAPI specification
cat > specs/api/users.yaml <<'EOF'
openapi: 3.0.0
info:
  title: User Management API
  version: 1.0.0
paths:
  /users:
    get:
      summary: List users
      responses:
        '200':
          description: List of users
EOF

# 2. Import spec to Athena
athena-spec-manage create \
  --name "User Management API" \
  --type openapi \
  --version "1.0.0" \
  --file-path "api/users.yaml" \
  --content-file specs/api/users.yaml

# 3. Link to architecture
# (Add related_adr_ids, implements_constraint_ids in Python or future CLI)

# 4. Generate code from spec (Phase 4 - coming soon)
# athena-codegen --spec-id 5 --output src/api/users.py

# 5. Validate generated code matches spec (Phase 4)
# athena-spec-validate --spec-id 5 --code src/api/users.py
```

### Example 2: Formal Specification with TLA+

```bash
# 1. Write TLA+ specification
cat > specs/formal/consensus.tla <<'EOF'
---- MODULE Consensus ----
EXTENDS Naturals
VARIABLES votes, decision

Init == votes = {} /\ decision = "none"

Vote(v) ==
  /\ v \notin votes
  /\ votes' = votes \cup {v}
  /\ decision' = IF Cardinality(votes') > 2 THEN "committed" ELSE decision

Next == \E v \in Voters: Vote(v)
EOF

# 2. Import to Athena
athena-spec-manage create \
  --name "Consensus Protocol" \
  --type tla+ \
  --file-path "formal/consensus.tla" \
  --content-file specs/formal/consensus.tla \
  --description "Three-phase commit protocol"

# 3. Validate with TLC (external tool)
# tlc consensus.tla
```

### Example 3: Database Schema with Prisma

```bash
# 1. Write Prisma schema
cat > specs/schemas/database.prisma <<'EOF'
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id        Int      @id @default(autoincrement())
  email     String   @unique
  name      String?
  createdAt DateTime @default(now())
}
EOF

# 2. Import to Athena
athena-spec-manage create \
  --name "Database Schema" \
  --type prisma \
  --file-path "schemas/database.prisma" \
  --content-file specs/schemas/database.prisma

# 3. Generate Prisma client
# npx prisma generate

# 4. Migrate database
# npx prisma migrate dev
```

### Example 4: Validation Workflow

```bash
# 1. Create an OpenAPI spec
cat > specs/api/users.yaml <<'EOF'
openapi: 3.0.0
info:
  title: User Management API
  version: 1.0.0
paths:
  /users:
    get:
      summary: List users
      responses:
        '200':
          description: List of users
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
EOF

# 2. Import to Athena
athena-spec-manage create \
  --name "User Management API" \
  --type openapi \
  --file-path "api/users.yaml" \
  --content-file specs/api/users.yaml

# 3. Validate the specification
athena-spec-manage validate --spec-id 1

# Output:
# 🔍 Validating User Management API (v1.0.0)...
#    Type: openapi
#
# ✅ Validation passed - specification is valid!
#    Validator: openapi-spec-validator
#
# Validated at: 2025-11-18 14:30:45
# Status: valid

# 4. Make a change that breaks validation
cat >> specs/api/users.yaml <<'EOF'
  /invalid:
    post:
      # Missing responses - will fail validation
EOF

# 5. Sync and validate again
athena-spec-manage sync --project-id 1
athena-spec-manage validate --spec-id 1

# Output:
# ❌ Validation failed with 1 error(s)
#
# ❌ Errors:
#   1. Missing required field 'responses' in operation
#
# Validated at: 2025-11-18 14:35:22
# Status: invalid
```

---

## Roadmap

### Phase 1: Basic Storage & CLI ✅ (Complete)

- [x] Specification model with multiple types
- [x] Hybrid storage (files + database)
- [x] CRUD operations
- [x] File synchronization
- [x] CLI commands
- [x] Tests (26/26 passing)

### Phase 2: Validation ✅ (Complete)

- [x] OpenAPI validation (openapi-spec-validator)
- [x] JSON Schema validation
- [x] GraphQL schema validation
- [x] Validation error tracking
- [x] Validation status in database
- [x] CLI validation command
- [x] Graceful degradation (optional dependencies)
- [x] Tests (15 validation tests passing)

### Phase 3: Planning Integration (1 week)

- [ ] Planning layer reads specs
- [ ] Generate task breakdowns from specs
- [ ] Validate plans against specs
- [ ] Track spec-to-plan mappings

### Phase 4: AI Code Generation (1 week)

- [ ] Generate code from OpenAPI specs
- [ ] Generate code from Prisma schemas
- [ ] Generate code from GraphQL schemas
- [ ] Track generation accuracy
- [ ] Detect spec-code drift

### Phase 5: Advanced Formats (Optional, 2 weeks)

- [ ] TLA+ model checking integration
- [ ] Alloy analyzer integration
- [ ] AsyncAPI event validation
- [ ] Custom spec type plugins

---

## Frequently Asked Questions

### Q: Do I have to use spec-driven development?

No! Athena supports both approaches:
- **Spec-driven**: Write spec first, generate code
- **Code-first**: Write code first, extract spec later

### Q: Can I use my existing OpenAPI specs?

Yes! Use `athena-spec-manage sync` to import all specs from `specs/` directory.

### Q: How do specs relate to ADRs?

- **ADRs** document WHY decisions were made
- **Specs** document WHAT the system should do
- **Patterns** document HOW to implement solutions

Specs can reference ADRs to show which decisions they implement.

### Q: Can I version specifications?

Yes! Use semantic versioning (MAJOR.MINOR.PATCH) in the `version` field. When creating a new version, you can supersede the old one:

```python
# Mark old spec as superseded
store.supersede(old_spec_id=5, new_spec_id=10)
```

### Q: How do I validate specs?

Use the built-in validation command:

```bash
# Install validation libraries (optional)
pip install 'athena[validation]'

# Validate a specification
athena-spec-manage validate --spec-id 5
```

**Supported validators**:
- **OpenAPI 3.0/3.1**: Automatic validation with `openapi-spec-validator`
- **JSON Schema**: Validates schema structure with `jsonschema`
- **GraphQL**: Validates SDL syntax with `graphql-core`

If validation libraries aren't installed, Athena will show a warning but continue to work. You can also use external tools:
- OpenAPI: `openapi-spec-validator spec.yaml`
- JSON Schema: `ajv validate schema.json`
- TLA+: `tlc spec.tla`

---

## Resources

### Tools

- **OpenAPI**: [Swagger Editor](https://editor.swagger.io/)
- **GraphQL**: [GraphQL Playground](https://github.com/graphql/graphql-playground)
- **TLA+**: [TLA+ Toolbox](https://lamport.azurewebsites.net/tla/toolbox.html)
- **Alloy**: [Alloy Analyzer](https://alloytools.org/)
- **Prisma**: [Prisma Studio](https://www.prisma.io/studio)

### References

- [GitHub Spec Kit (v0.0.30+)](https://github.com/github/spec-kit) - Released September 2, 2025
- [OpenAPI Specification 3.1](https://spec.openapis.org/oas/v3.1.0)
- [AsyncAPI 2.6](https://www.asyncapi.com/docs/reference/specification/v2.6.0)
- [TLA+ Homepage](https://lamport.azurewebsites.net/tla/tla.html)
- [Alloy 6.2.0 Release](https://github.com/AlloyTools/org.alloytools.alloy/releases/tag/v6.2.0)

---

**For more information**, see:
- [Architecture Layer Documentation](ARCHITECTURE_LAYER.md)
- [Research: Spec-Driven Development](tmp/SPEC_DRIVEN_DEVELOPMENT_RESEARCH.md)
- [API Reference](API_REFERENCE.md)
