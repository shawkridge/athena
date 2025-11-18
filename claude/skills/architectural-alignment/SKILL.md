---
name: architectural-alignment
description: |
  When discussing design decisions, validate alignment with architectural decisions (ADRs),
  constraints, and established patterns. Auto-triggers on architecture keywords.
  Ensures consistency with documented architectural principles.
---

# Architectural Alignment Skill

## What This Skill Does

Validates proposed changes and designs against established architectural decisions, constraints, and patterns to ensure consistency and prevent architectural drift.

## When to Use

Auto-triggers when conversation includes:
- Design decisions or architectural changes
- Implementation approaches for new features
- Refactoring discussions
- Component structure changes
- Technology selection
- Pattern application

**Keywords**: design, architect, implement, refactor, component, structure, approach, decision, pattern, constraint

## How It Works (Filesystem API Paradigm)

### Step 1: Discover Architectural Context
- Use `MemoryBridge.get_active_adrs()` to get accepted decisions
- Use `MemoryBridge.get_unsatisfied_constraints()` to get active constraints
- Use `MemoryBridge.get_effective_patterns()` to get proven patterns
- Progressive disclosure - load only summaries

### Step 2: Analyze Proposed Change
- Extract design intent from conversation
- Identify affected components/layers
- Determine architectural scope
- Categorize change type (new feature, refactor, fix, etc.)

### Step 3: Validate Alignment
Execute locally (in sandbox):
- **ADR Alignment**: Check if proposal aligns with accepted decisions
- **Constraint Satisfaction**: Verify hard constraints not violated
- **Pattern Consistency**: Compare with effective patterns
- **Conflict Detection**: Identify architectural conflicts

### Step 4: Return Guidance
Return summary with:
- Alignment score (0-1)
- Potential conflicts or concerns
- Relevant ADRs to consider
- Suggested patterns
- Constraint reminders

## Returns (Summary Only)

```json
{
  "status": "success",
  "execution_method": "filesystem_api",
  "execution_time_ms": 120,

  "proposed_change": "Add caching layer to API",
  "alignment_score": 0.85,
  "assessment": "generally_aligned",

  "relevant_adrs": [
    {
      "id": 12,
      "title": "Use Redis for distributed caching",
      "alignment": "strong",
      "note": "Proposal aligns with existing decision"
    }
  ],

  "constraint_checks": [
    {
      "id": 5,
      "type": "performance",
      "description": "API response time < 200ms",
      "satisfied": true,
      "note": "Caching will improve performance"
    }
  ],

  "suggested_patterns": [
    {
      "name": "Cache-Aside Pattern",
      "relevance": 0.95,
      "effectiveness": 0.88,
      "reason": "Proven effective in similar components"
    }
  ],

  "concerns": [
    "Consider cache invalidation strategy",
    "Ensure consistency with ADR-12 Redis usage"
  ],

  "recommendations": [
    "Document as new ADR if approach differs from ADR-12",
    "Verify performance constraint after implementation",
    "Consider applying Cache-Aside pattern"
  ],

  "note": "Get full ADR details via filesystem API if needed"
}
```

## Token Efficiency

**Old Pattern** (manual lookup):
- User asks → Manual ADR search → Load full ADRs → Analyze → Respond
- **Total: ~15K tokens**

**New Pattern** (auto-trigger with summary):
- Auto-detect → Load summaries only → Validate locally → Return guidance
- **Total: <500 tokens**

**Savings: 97% token reduction** 🎯

## Validation Rules

### Strong Alignment (0.8-1.0)
- Proposal directly supports accepted ADR
- All hard constraints satisfied
- Uses proven effective patterns
- No architectural conflicts

### Moderate Alignment (0.5-0.8)
- Generally consistent with ADRs
- Some constraints need attention
- Patterns applicable but not exact match
- Minor concerns to address

### Weak Alignment (0.0-0.5)
- Conflicts with accepted ADRs
- Violates hard constraints
- No proven patterns available
- Significant architectural concerns

## Examples

### Example 1: Feature Implementation
**Conversation**: "I want to add user authentication with JWT tokens"

**Skill Auto-Triggers**:
- Checks for ADRs about authentication
- Verifies security constraints
- Suggests proven auth patterns
- Returns alignment guidance

### Example 2: Refactoring Discussion
**Conversation**: "Should we refactor the database layer to use repository pattern?"

**Skill Auto-Triggers**:
- Checks for data access ADRs
- Reviews effective patterns
- Validates against constraints
- Suggests if repository pattern used effectively before

### Example 3: Technology Selection
**Conversation**: "Thinking about using MongoDB instead of PostgreSQL"

**Skill Auto-Triggers**:
- Finds ADRs about database technology
- Checks if conflicts with existing decisions
- Reviews constraints (ACID, performance, etc.)
- Warns if contradicts ADR

## Best Practices

1. **Trust the Guidance**: Alignment scores based on documented decisions
2. **Document New Decisions**: If deviating, create new ADR
3. **Update Effectiveness**: Record pattern success/failure for future
4. **Respect Hard Constraints**: Don't bypass without explicit approval
5. **Progressive Enhancement**: Start with high-alignment approaches

## Integration with Architecture Layer

This skill uses the architecture layer's filesystem API operations:
- `get_arch_context()` - Get full architectural context
- `validate_alignment()` - Validate proposal against architecture
- Local execution - all validation in sandbox
- Summary-first - only essential guidance returned

## Automatic Activation

This skill is **auto-triggered** when conversation includes:
- Design/architecture keywords
- Implementation discussions
- Technology choices
- Refactoring proposals
- Component structure changes

No manual invocation needed - progressive activation based on context.
