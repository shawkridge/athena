---
description: Evaluate memory quality and identify gaps - finds contradictions, uncertainties, and missing knowledge
argument-hint: "Optional: --domain (specific domain) or --detail (detailed analysis)"
---

# Assess Memory

Evaluate semantic memory quality and identify knowledge gaps, contradictions, and uncertainties.

Usage:
- `/assess-memory` - Overall quality assessment
- `/assess-memory --domain auth` - Domain-specific assessment
- `/assess-memory --detail` - Deep gap analysis

**Quality Metrics** (4-metric framework):

1. **Compression** (70-85% target)
   - How efficiently patterns compress episodic events
   - Higher = better knowledge extraction

2. **Recall** (>80% target)
   - Ability to retrieve relevant information
   - Coverage of important concepts

3. **Consistency** (>75% target)
   - No contradictions in stored knowledge
   - Coherence across memory layers

4. **Density** (entities per pattern)
   - How rich/detailed patterns are
   - Higher = more useful context

Returns:
- Overall quality score (0.0-1.0)
- Per-domain expertise assessment
- Detected contradictions with severity
- Uncertainties requiring reinforcement
- Missing knowledge areas (gaps)
- Consolidation recommendations
- Domain-specific health breakdowns

**Health Status**:
- **HEALTHY** (≥0.85): Continue current practices
- **WARNING** (0.65-0.85): Schedule consolidation
- **CRITICAL** (<0.65): Immediate consolidation needed

Example output:
```
Overall Quality: 0.78 (WARNING)
Domains:
  - Authentication: 0.92 (HEALTHY)
  - Database Design: 0.68 (WARNING) - last consolidation 10 days ago
  - API Design: 0.45 (CRITICAL) - only 2 episodic events stored

Contradictions Found:
  - JWT expiry: stored as "24h" vs "1h" in observations
  - Database normalization: conflicting approaches in 3 procedures
```

The quality-auditor agent autonomously assesses memory quality weekly.
