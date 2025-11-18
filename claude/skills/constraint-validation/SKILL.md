---
name: constraint-validation
description: |
  When implementing or changing code, automatically validate against architectural constraints
  (performance, security, scalability). Auto-triggers on implementation discussions.
  Prevents constraint violations before they happen.
---

# Constraint Validation Skill

## What This Skill Does

Automatically validates proposed implementations against architectural constraints to catch violations early. Prevents performance regressions, security issues, and scalability problems.

## When to Use

Auto-triggers when conversation includes:
- Implementation discussions
- Code changes or additions
- Performance-sensitive operations
- Security-related functionality
- Data handling or storage
- External integrations

**Keywords**: implement, add, change, modify, create, build, performance, security, scale, load, users, data, api

## How It Works (Filesystem API Paradigm)

### Step 1: Extract Implementation Details
- Identify what's being implemented
- Determine affected components
- Detect constraint categories (performance, security, etc.)
- Extract mentioned requirements

### Step 2: Discover Relevant Constraints
- Use `MemoryBridge.get_unsatisfied_constraints()` for active constraints
- Query constraint tracker via filesystem API
- Filter by component and type
- Progressive disclosure - summaries only

### Step 3: Validate Locally
Execute validation in sandbox:
- **Hard Constraint Check**: Must-satisfy requirements
- **Soft Constraint Check**: Should-satisfy requirements
- **Priority Assessment**: High-priority constraints first
- **Impact Analysis**: Predict constraint satisfaction

### Step 4: Return Validation Report
Return summary with:
- Constraint satisfaction assessment
- Violated or at-risk constraints
- Recommendations to address
- Priority of issues
- Validation confidence

## Returns (Summary Only)

```json
{
  "status": "success",
  "execution_method": "filesystem_api",
  "execution_time_ms": 85,

  "implementation_summary": "Add file upload endpoint with 100MB limit",
  "affected_components": ["API", "Storage", "Upload Service"],

  "constraint_checks": [
    {
      "id": 5,
      "type": "performance",
      "description": "API endpoints must respond within 200ms",
      "is_hard_constraint": true,
      "priority": 9,
      "status": "at_risk",
      "reason": "File uploads >100MB will exceed 200ms",
      "recommendation": "Use async upload with status endpoint",
      "validation_confidence": 0.85
    },
    {
      "id": 8,
      "type": "security",
      "description": "All file uploads must be virus scanned",
      "is_hard_constraint": true,
      "priority": 10,
      "status": "needs_attention",
      "reason": "No virus scanning mentioned in implementation",
      "recommendation": "Add virus scanning step before storage",
      "validation_confidence": 0.95
    },
    {
      "id": 12,
      "type": "scalability",
      "description": "Storage operations must handle 10K concurrent users",
      "is_hard_constraint": false,
      "priority": 7,
      "status": "satisfied",
      "reason": "S3 storage handles this scale naturally",
      "recommendation": "None",
      "validation_confidence": 0.90
    }
  ],

  "overall_assessment": {
    "hard_constraints_satisfied": 0,
    "hard_constraints_violated": 2,
    "soft_constraints_satisfied": 1,
    "soft_constraints_at_risk": 0,
    "critical_issues": 2,
    "warnings": 0
  },

  "critical_actions_required": [
    "Must add virus scanning before storage (security constraint #8)",
    "Must use async upload for files >10MB (performance constraint #5)"
  ],

  "suggested_approach": "Implement async upload with status polling + virus scanning middleware",

  "related_adrs": [15, 22],
  "related_patterns": ["Async Processing Pattern", "Security Middleware Pattern"],

  "note": "Get full constraint details via filesystem API if needed"
}
```

## Token Efficiency

**Old Pattern** (manual constraint checking):
- Load all constraints: 10K tokens
- User checks manually: N/A
- Discover violations after implementation: Expensive
- **Total: ~10K tokens + fixing cost**

**New Pattern** (auto-validation):
- Extract implementation details: 0 tokens (sandbox)
- Load relevant constraints only: 150 tokens
- Validate locally: 0 tokens (sandbox)
- Return focused report: 350 tokens
- **Total: <500 tokens**

**Savings: 95% token reduction + prevents costly fixes** 🎯

## Constraint Types Tracked

### Performance Constraints
- Response time requirements
- Throughput targets
- Resource usage limits
- Latency budgets
- Query performance

**Example**: "API endpoints < 200ms", "Database queries < 50ms"

### Security Constraints
- Authentication requirements
- Authorization rules
- Data encryption
- Input validation
- Audit logging

**Example**: "All endpoints require authentication", "PII must be encrypted"

### Scalability Constraints
- Concurrent user capacity
- Data volume limits
- Horizontal scaling requirements
- Stateless design requirements

**Example**: "Support 10K concurrent users", "Stateless service design"

### Reliability Constraints
- Uptime requirements
- Error rate limits
- Retry policies
- Timeout configurations

**Example**: "99.9% uptime", "Error rate < 0.1%"

### Compliance Constraints
- Regulatory requirements
- Data retention policies
- Privacy requirements
- Audit requirements

**Example**: "GDPR compliant", "Data retention 7 years"

## Validation Confidence Levels

### High Confidence (0.8-1.0)
- Clear implementation details provided
- Exact constraint match
- Well-understood impact
- Historical data available

### Medium Confidence (0.5-0.8)
- Some implementation details
- Partial constraint match
- Estimated impact
- Limited historical data

### Low Confidence (0.0-0.5)
- Vague implementation details
- Unclear constraint applicability
- Unknown impact
- No historical data

## Examples

### Example 1: Database Query Addition
**User**: "I'll add a query to fetch all users with their posts"

**Skill Auto-Triggers**:
- Detects database operation
- Checks performance constraints (query time < 50ms)
- Warns: "N+1 query problem likely, will violate constraint"
- Suggests: "Use JOIN or eager loading"

### Example 2: API Endpoint Creation
**User**: "Creating an endpoint to export user data as CSV"

**Skill Auto-Triggers**:
- Detects API endpoint creation
- Checks: Response time, authentication, data privacy constraints
- Warns: "Large CSV will exceed 200ms constraint"
- Suggests: "Use async job with download link"

### Example 3: File Storage Implementation
**User**: "Store uploaded images directly to disk"

**Skill Auto-Triggers**:
- Detects storage operation
- Checks: Scalability, security, backup constraints
- Warns: "Disk storage doesn't scale horizontally"
- Suggests: "Use object storage (S3) per ADR-18"

## Critical vs. Warning Classification

### Critical Issues (Must Fix)
- **Hard constraint violated**
- High priority (8-10)
- Security or reliability impact
- **Blocks implementation**

### Warnings (Should Fix)
- **Soft constraint at risk**
- Medium priority (5-7)
- Performance or usability impact
- **Guidance for improvement**

### Informational (Good to Know)
- Low priority (<5)
- Best practice suggestions
- Optimization opportunities
- **No blocking issues**

## Learning From Violations

The skill **learns from past violations**:

1. **Violation Detected**: Constraint broken in implementation
2. **Impact Recorded**: Severity and consequences tracked
3. **Pattern Extracted**: Common violation patterns identified
4. **Better Predictions**: Future validations more accurate

**Example**:
```
Initial: 60% of N+1 queries detected before implementation
After 3 months: 95% of N+1 queries detected before implementation
```

## Best Practices

1. **Fix Critical Issues First**: Hard constraints are non-negotiable
2. **Address Warnings**: Soft constraints prevent future problems
3. **Validate Early**: Check constraints before detailed implementation
4. **Update Constraints**: Keep constraint list current and relevant
5. **Document Exceptions**: If bypassing constraint, document why in ADR

## Integration with Architecture Layer

Uses filesystem API operations:
- `get_constraints_for_component()` - Get relevant constraints
- `verify_constraint()` - Mark constraint satisfaction
- `get_constraint_violations()` - Historical violations
- Local validation - all checks in sandbox
- Summary-first - only issues returned

## Automatic Activation

This skill is **auto-triggered** when conversation includes:
- Implementation discussions
- Code change descriptions
- Feature additions
- Performance-sensitive operations
- Security-related work
- Integration work

No manual invocation needed - progressive activation based on context.

## Success Metrics

Track to improve over time:
- **Pre-Implementation Detection**: % of constraint violations caught before coding
- **False Positive Rate**: % of warnings that weren't real issues
- **Resolution Time**: Time to address constraint issues
- **Constraint Satisfaction**: % of hard constraints satisfied
- **Violation Recurrence**: How often same violations repeat

## Constraint Priority Guidelines

**Priority 10 (Critical)**: Security, data loss, legal compliance
**Priority 8-9 (High)**: Performance SLAs, reliability requirements
**Priority 5-7 (Medium)**: Scalability, maintainability, cost
**Priority 1-4 (Low)**: Nice-to-have, optimization, standards

## When Constraints Conflict

If multiple constraints conflict:
1. **Hard constraints beat soft constraints** always
2. **Higher priority beats lower priority**
3. **Security beats performance** in most cases
4. **Compliance beats all** for regulated systems
5. **Document trade-offs** in ADR if needed
