---
description: Create an Architecture Decision Record (ADR) - documents important architectural decisions with context, alternatives, and consequences
argument-hint: "Decision title"
---

# Create Architecture Decision Record (ADR)

Create a new ADR to document an important architectural decision following the filesystem API paradigm.

Usage: `/create-adr "Use PostgreSQL for primary datastore"`

## How It Works (Filesystem API Paradigm)

### Step 1: Discover
- List available architecture operations via filesystem API
- Discover ADR creation capabilities
- Progressive disclosure (load only what's needed)

### Step 2: Read
- Read architecture manager code
- Understand ADR model and validation
- Know exactly what fields are required

### Step 3: Execute
- Create ADR locally in Python execution environment
- All validation happens in sandbox
- Store in architecture decisions table

### Step 4: Summarize
- Return ADR ID and status
- Provide next steps guidance
- Keep response under 300 tokens

## Required Information

When creating an ADR, you'll need:

- **Title**: Short descriptive title
- **Context**: The problem or context leading to this decision
- **Decision**: The decision that was made
- **Rationale**: Why this decision was made
- **Alternatives**: Other options considered (optional)
- **Consequences**: Expected outcomes, both positive and negative (optional)

## Example Usage

```python
# Discover architecture operations
operations = list_directory("/athena/architecture")

# Read ADR creation code
adr_code = read_file("/athena/architecture/manager.py")

# Execute locally
from athena.architecture import ArchitectureManager

manager = ArchitectureManager()
adr_id = manager.create_adr(
    project_id=1,
    title="Use PostgreSQL for primary datastore",
    context="Need ACID guarantees and complex queries for memory system",
    decision="Use PostgreSQL with pgvector extension",
    rationale="Provides ACID compliance, mature ecosystem, native vector search",
    alternatives=[
        "MongoDB - Better for unstructured data but lacks ACID",
        "DynamoDB - Cloud-native but expensive and limited query capabilities"
    ],
    consequences=[
        "+ Strong consistency and ACID guarantees",
        "+ Rich query capabilities (joins, aggregations)",
        "+ pgvector for native vector search",
        "- Harder to scale horizontally",
        "- Requires careful connection pool management"
    ],
    author="AI Assistant"
)

# Return summary
print(f"✓ ADR Created: {adr_id}")
print(f"Status: proposed")
print(f"Next: Review with team, then accept with /accept-adr {adr_id}")
```

## Returns (Summary Only)

```json
{
  "status": "success",
  "adr_id": 42,
  "title": "Use PostgreSQL for primary datastore",
  "adr_status": "proposed",
  "created_at": "2025-11-18",
  "next_steps": [
    "Review decision with team",
    "Add related patterns and constraints",
    "Accept with /accept-adr 42"
  ],
  "note": "Full ADR accessible via /get-adr 42"
}
```

## Token Efficiency

**Before (Old Pattern)**:
- Load all ADR definitions: 5K tokens
- Return full ADR object: 2K tokens
- **Total: ~7K tokens**

**After (Filesystem API)**:
- Discover operations: 50 tokens
- Read creation code: 100 tokens
- Execute locally: 0 tokens (sandbox)
- Return summary: 150 tokens
- **Total: <300 tokens**

**Savings: 96% token reduction** 🎯

## Integration with Memory System

ADRs automatically:
- Link to design patterns used
- Reference architectural constraints
- Get stored in episodic memory as decision events
- Become part of architectural context for AI

## Best Practices

1. **Be Specific**: Title should clearly indicate what was decided
2. **Capture Alternatives**: Document options you considered
3. **Note Consequences**: Both positive and negative outcomes
4. **Link Patterns**: Reference relevant design patterns
5. **Update Status**: Move from proposed → accepted → (eventually) deprecated

## Related Commands

- `/get-adr <id>` - Retrieve full ADR details
- `/list-adrs` - List all ADRs for project
- `/accept-adr <id>` - Mark ADR as accepted
- `/get-arch-context` - Get full architectural context including ADRs
