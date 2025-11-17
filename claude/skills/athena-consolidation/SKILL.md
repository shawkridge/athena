---
name: athena-consolidation
description: >
  Consolidation and learning: extract patterns, run consolidation, validate patterns.
  Trigger the dual-process learning system that discovers new patterns.

  Use when: "patterns", "consolidate", "extract", "learn", "validate pattern", "what have I learned"
---

# Athena Consolidation Skill

Trigger pattern extraction and consolidation. Extract new patterns from memories, validate findings.

## What This Skill Does

- **Extract Patterns**: Discover workflow patterns
- **Run Consolidation**: Trigger learning system
- **Validate Patterns**: Verify discovered patterns
- **Get Analytics**: Consolidation statistics

## When to Use

- **"What patterns have I learned?"** - Extract patterns
- **"Run consolidation"** - Trigger learning
- **"Validate this pattern"** - Verify pattern
- **"What has consolidation found?"** - Get analytics

## Available Tools

### extractPatterns(limit)
Discover new patterns.

### runConsolidation()
Trigger dual-process learning.

### validatePattern(pattern)
Verify discovered pattern.

### getAnalytics()
Get consolidation statistics.

## Architecture

Integrates with Athena's Layer 7 (Consolidation):
- Dual-process pattern extraction (100ms System 1, LLM System 2)
- Pattern validation and confidence scoring
- Memory compression through learning
