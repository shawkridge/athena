---
description: Extract patterns from completed work using dual-process consolidation (System 1 + System 2 reasoning)
argument-hint: "Optional: --strategy (balanced|speed|quality|minimal) or --domain (specific domain)"
---

# Consolidate

Extract patterns from episodic events using dual-process reasoning consolidation.

Usage:
- `/consolidate` - Quick consolidation
- `/consolidate --strategy quality` - Deep quality-focused consolidation
- `/consolidate --domain auth` - Domain-specific consolidation

**Dual-Process Consolidation**:

**System 1 (Fast ~100ms)**:
- Statistical clustering of episodic events
- Frequency-based pattern detection
- Heuristic weighting
- Always runs as baseline

**System 2 (Slow ~1-5 seconds)**:
- LLM extended thinking with pattern validation
- Semantic understanding of relationships
- Confidence-based verification
- Triggered when uncertainty >0.5

**5 Consolidation Strategies**:
1. **Balanced**: Fast System 1 + selective System 2 (recommended)
2. **Speed**: System 1 only, optimize for <2 second execution
3. **Quality**: Aggressive System 2 for maximum accuracy >0.85
4. **Minimal**: Compress >80%, minimal quality impact
5. **Custom**: Mix strategies by domain

Returns:
- New semantic memories extracted (target: 5+)
- New procedures created (target: 2+)
- Quality metrics:
  - Compression ratio (target: 70-85%)
  - Recall percentage (target: >80%)
  - Consistency score (target: >75%)
  - Density (entities/patterns per memory)
- Pattern categories discovered
- Uncertainty regions that triggered System 2
- Recommendations for follow-up consolidation

The consolidation-engine agent autonomously triggers consolidations at strategic points (session end, after major work sessions).
