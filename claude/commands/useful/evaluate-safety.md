---
description: Assess change safety and risk - evaluates impact and recommends approval gates
argument-hint: "Description of change to evaluate"
---

# Evaluate Safety

Assess the safety and risk of proposed changes with impact analysis and gate recommendations.

Usage: `/evaluate-safety "update authentication to OAuth2"`

Features:
- **Risk Assessment**: Determine risk level (LOW, MEDIUM, HIGH, CRITICAL)
- **Impact Analysis**: Which components affected
- **Affected Files**: List files that will change
- **Affected Tests**: Which tests may need updates
- **Rollback Plans**: Steps to revert if needed
- **Approval Gates**: Recommended review/approval requirements
- **Testing Requirements**: Suggested test coverage

Risk Factors:
- **Auth/Security Changes**: HIGH-CRITICAL
- **Database Schema**: HIGH-CRITICAL
- **API Contracts**: MEDIUM-HIGH
- **UI Changes**: LOW-MEDIUM
- **Documentation**: LOW
- **Configuration**: LOW-MEDIUM

Returns:
- Risk Level (0-100 score)
- Affected components count
- Suggested approval gates (peer review, security review, testing)
- Recommended test types and coverage
- Pre/post-deployment verification steps
- Rollback difficulty (easy/medium/hard)
- Timeline impact (how long to revert)
- Confidence score (how certain is this assessment)

Example output:
```
Change: "Update authentication to OAuth2"
Risk Level: HIGH (78/100)
Affected Components: 12 (AuthManager, 5 endpoints, 3 middleware, 4 test modules)

Recommended Gates:
  ✓ Peer code review (required)
  ✓ Security review (required)
  ✓ Full test suite (required)
  ✓ Integration testing (required)

Rollback: Medium difficulty (30 minutes to revert)
Timeline: Critical-path item
```

The safety-auditor agent evaluates safety before major changes.
