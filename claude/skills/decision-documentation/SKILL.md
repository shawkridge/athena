---
name: decision-documentation
description: |
  When important architectural decisions are discussed, automatically detect and suggest
  documenting as ADRs. Ensures decisions are captured with context, rationale, and alternatives.
  Auto-triggers on decision-making conversations.
---

# Decision Documentation Skill

## What This Skill Does

Automatically detects when important architectural decisions are being made and suggests documenting them as Architecture Decision Records (ADRs). Ensures knowledge isn't lost and future context is preserved.

## When to Use

Auto-triggers when conversation includes:
- Technology selection decisions
- Architectural approach discussions
- Design pattern choices
- Important trade-off evaluations
- "We should use..." or "Let's go with..." statements
- Comparing alternatives

**Keywords**: decide, choose, use, select, go with, switch to, migrate to, adopt, replace, versus, vs, compare, alternative, option

## How It Works (Filesystem API Paradigm)

### Step 1: Detect Decision Points
- Identify decision-making language
- Extract decision subject (what's being decided)
- Detect alternatives being considered
- Assess decision importance

### Step 2: Check Existing Documentation
- Use `MemoryBridge.get_active_adrs()` for existing ADRs
- Query if decision already documented
- Check for related or conflicting decisions
- Progressive disclosure - summaries only

### Step 3: Assess Documentation Need
Execute assessment locally:
- **Impact Analysis**: How many components affected?
- **Reversibility**: How hard to change later?
- **Complexity**: How complex is the decision?
- **Knowledge Risk**: What's lost if not documented?

### Step 4: Suggest ADR Creation
If important enough, suggest documentation with:
- Extracted decision summary
- Identified alternatives
- Potential consequences to consider
- Suggested ADR title
- Quick-start template

## Returns (Summary Only)

```json
{
  "status": "success",
  "execution_method": "filesystem_api",
  "execution_time_ms": 75,

  "decision_detected": true,
  "decision_summary": "Use PostgreSQL instead of MongoDB for primary datastore",
  "importance_score": 0.92,
  "documentation_recommended": true,

  "extracted_context": {
    "decision": "Use PostgreSQL with pgvector extension",
    "alternatives_discussed": [
      "MongoDB - Better for unstructured data",
      "DynamoDB - Cloud-native solution"
    ],
    "rationale_mentioned": [
      "Need ACID guarantees for transactions",
      "Complex queries require SQL",
      "pgvector for vector search support"
    ],
    "concerns_raised": [
      "Horizontal scaling is harder",
      "Connection pool management complexity"
    ]
  },

  "impact_assessment": {
    "affected_components": ["Data Layer", "API Layer", "Memory System"],
    "reversibility": "difficult",
    "complexity": "high",
    "knowledge_risk": "high"
  },

  "existing_related_adrs": [
    {
      "id": 8,
      "title": "Use async database access pattern",
      "relation": "supports",
      "note": "PostgreSQL works well with async pattern"
    }
  ],

  "suggested_adr": {
    "title": "Use PostgreSQL for primary datastore",
    "status": "proposed",
    "template": {
      "context": "Need ACID guarantees and complex queries for memory system",
      "decision": "Use PostgreSQL with pgvector extension",
      "alternatives": ["MongoDB", "DynamoDB"],
      "consequences": [
        "+ Strong consistency and ACID guarantees",
        "+ Rich query capabilities",
        "+ pgvector for native vector search",
        "- Harder to scale horizontally",
        "- Connection pool management needed"
      ]
    }
  },

  "recommendation": "Document as ADR-09: High importance (0.92), affects multiple components, difficult to reverse",

  "quick_action": "Use /create-adr or filesystem API to document this decision",

  "note": "ADR preserves context and rationale for future reference"
}
```

## Token Efficiency

**Old Pattern** (decision lost):
- Decision made in conversation
- Context forgotten over time
- Future confusion: "Why did we choose this?"
- Rediscovery cost: High
- **Total: Unmeasured but expensive**

**New Pattern** (auto-detect and capture):
- Detect decision: 0 tokens (sandbox)
- Check existing ADRs: 100 tokens
- Assess importance: 0 tokens (sandbox)
- Suggest documentation: 300 tokens
- **Total: <400 tokens + preserved knowledge**

**Value: Prevents knowledge loss + reduces future confusion** 🎯

## Importance Scoring

### Critical Importance (0.8-1.0)
- Affects core architecture
- Difficult or impossible to reverse
- Impacts multiple teams/components
- **Always document**

### High Importance (0.6-0.8)
- Affects significant subsystems
- Expensive to reverse
- Impacts development workflow
- **Strongly recommend documenting**

### Medium Importance (0.4-0.6)
- Affects single component
- Moderately expensive to reverse
- Local impact
- **Consider documenting**

### Low Importance (0.0-0.4)
- Implementation detail
- Easy to reverse
- Minimal impact
- **Optional documentation**

## Decision Types Detected

### Technology Selection
"Use Redis for caching", "Switch to React", "Adopt Kubernetes"
- **Impact**: High
- **Reversibility**: Difficult
- **Document**: Always

### Architectural Patterns
"Use microservices architecture", "Apply CQRS pattern"
- **Impact**: Very High
- **Reversibility**: Very Difficult
- **Document**: Always

### Design Approaches
"Use repository pattern for data access", "Implement event sourcing"
- **Impact**: Medium-High
- **Reversibility**: Moderate
- **Document**: Recommended

### Infrastructure Decisions
"Deploy on AWS", "Use Docker containers", "Set up CI/CD pipeline"
- **Impact**: High
- **Reversibility**: Difficult
- **Document**: Recommended

### Process Decisions
"Adopt TDD", "Use trunk-based development", "Implement code review process"
- **Impact**: Medium
- **Reversibility**: Easy-Moderate
- **Document**: Consider

## Examples

### Example 1: Technology Choice
**User**: "Let's use Redis for session storage instead of in-memory"

**Skill Auto-Triggers**:
- Detects decision: Redis for sessions
- Assesses importance: High (affects scalability)
- Extracts rationale: Distributed sessions, persistence
- Suggests: "Document as ADR - affects all API servers"

### Example 2: Pattern Selection
**User**: "I think we should use the repository pattern here"

**Skill Auto-Triggers**:
- Detects pattern decision
- Checks: Is repository pattern already an ADR?
- Finds: ADR-12 already covers data access patterns
- Responds: "Aligns with ADR-12, no new ADR needed"

### Example 3: Architecture Change
**User**: "We need to split the monolith into microservices"

**Skill Auto-Triggers**:
- Detects major architectural decision
- Importance: Critical (0.95)
- Extracts: Splitting strategy, service boundaries
- Suggests: "Critical decision - must document as ADR with migration plan"

### Example 4: Trade-off Discussion
**User**: "Should we prioritize performance or maintainability here?"

**Skill Auto-Triggers**:
- Detects trade-off decision point
- Waits for resolution
- Once decided: Suggests documenting rationale
- Captures: Why one was chosen over the other

## ADR Template Generation

When suggesting ADR, auto-generates template from conversation:

```markdown
# ADR-{next_id}: {extracted_title}

## Status
Proposed

## Context
{extracted_from_conversation}

## Decision
{main_decision_statement}

## Alternatives Considered
{alternatives_discussed}

## Consequences
### Positive
{benefits_mentioned}

### Negative
{concerns_raised}

## Related
- ADR-{related_id}: {related_title}
- Pattern: {suggested_pattern}
- Constraint: {affected_constraint}
```

## Learning From Documentation

The skill **improves over time**:

1. **Decision Documented**: ADR created for decision
2. **Outcome Tracked**: Success/failure of decision
3. **Patterns Identified**: Common decision types
4. **Better Detection**: More accurate importance scoring

**Example**:
```
Week 1: Detects 50% of important decisions
Week 4: Detects 80% of important decisions
Week 8: Suggests ADR before decision finalized
```

## Best Practices

1. **Document Before Implementing**: Easier to capture context
2. **Include Alternatives**: Shows what was considered
3. **Note Trade-offs**: Helps future decisions
4. **Update Status**: Proposed → Accepted → Deprecated lifecycle
5. **Link Related ADRs**: Build decision network

## Integration with Architecture Layer

Uses filesystem API operations:
- `create_adr()` - Create new ADR with template
- `get_active_adrs()` - Check existing decisions
- `list_adrs()` - Find related decisions
- Local processing - extraction in sandbox
- Summary-first - only suggestion returned

## Automatic Activation

This skill is **auto-triggered** when conversation includes:
- Decision-making language
- Technology comparisons
- Pattern discussions
- "Use X instead of Y" statements
- Trade-off evaluations
- Important choices

No manual invocation needed - progressive activation based on context.

## Success Metrics

Track to improve over time:
- **Decision Capture Rate**: % of important decisions documented
- **Context Completeness**: Quality of captured rationale
- **Future Reference Usage**: How often ADRs are referenced later
- **Decision Reversals**: Fewer reversals when well-documented
- **Onboarding Speed**: New team members understand decisions faster

## When NOT to Create ADR

Skip ADR for:
- **Temporary decisions**: Short-term workarounds
- **Implementation details**: Variable naming, file organization
- **Obvious choices**: Industry standard practices
- **Easily reversible**: Low-cost changes
- **Already documented**: Covered by existing ADR

## ADR Lifecycle

1. **Proposed**: Decision suggested, under review
2. **Accepted**: Decision approved and active
3. **Deprecated**: Decision no longer recommended
4. **Superseded**: Replaced by newer ADR

This skill helps capture decisions at **Proposed** stage before context is lost.

## Cross-Project Learning

ADRs can be shared across projects:
- Patterns that work well become reusable
- Failed decisions prevent repeat mistakes
- Best practices emerge naturally
- Organizational knowledge grows

**Example**: "ADR-15 in ProjectA worked well → Suggests similar approach in ProjectB"
