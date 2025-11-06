---
name: change-safety
description: |
  Assess change safety and risk. Use before making critical changes to evaluate impact, identify affected components, determine risk levels.
  Recommends approval gates, testing requirements, and rollback plans.
---

# Change Safety Skill

Assess risk and safety implications of proposed changes.

## When to Use

- Before making critical changes
- For security or auth-related changes
- Database schema modifications
- API contract changes
- Major refactoring

## Risk Assessment

**Risk Levels**: LOW, MEDIUM, HIGH, CRITICAL

**Factors**:
- Auth/Security changes: HIGH-CRITICAL
- Database schema: HIGH-CRITICAL
- API contracts: MEDIUM-HIGH
- UI changes: LOW-MEDIUM
- Documentation: LOW

## Analysis

- Risk level (0-100 score)
- Affected components count
- Files that will change
- Tests needing updates
- Required approval gates
- Suggested test coverage
- Rollback difficulty

## Returns

- Risk Level and score
- Affected components
- Suggested approval gates
- Required testing types
- Verification steps
- Rollback difficulty (easy/medium/hard)
- Timeline impact
- Confidence score

The change-safety skill activates before high-risk modifications.
