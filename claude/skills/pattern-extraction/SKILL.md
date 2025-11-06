---
name: pattern-extraction
description: |
  Extract patterns using dual-process reasoning (fast statistical clustering + slow LLM validation).
  Use after completing work to consolidate episodic events into semantic knowledge.
  Target: 70-85% compression, >80% recall, >75% consistency. Learns when uncertainty warrants LLM validation.
---

# Pattern Extraction Skill

Consolidate completed work into lasting patterns and procedures using dual-process reasoning.

## When to Use

- After completing major work sessions
- To extract learnings and create procedures
- Improving memory quality and compression
- Creating reusable workflows

## Dual Process

**System 1 (Fast, ~100ms)**:
- Statistical clustering
- Frequency-based patterns
- Heuristic weighting

**System 2 (Slow, ~1-5s)**:
- LLM validation (triggered when uncertainty > 0.5)
- Semantic understanding
- Confidence verification

## Quality Targets

- Compression: 70-85% (episodic → semantic)
- Recall: >80% (retrieve what you need)
- Consistency: >75% (no contradictions)
- Density: Rich context per pattern

## Returns

- New memories extracted (count)
- Procedures created (with effectiveness)
- Quality metrics achieved
- Pattern categories discovered
- Uncertainty regions (System 2 areas)
- Consolidation recommendations

The pattern-extraction skill activates after completing complex work sessions.
