---
name: athena-memory-core
description: >
  Core memory operations: recall memories by query, store new learnings, trigger consolidation,
  and extract learned patterns. Access the foundation of Athena's memory system.

  Use when: "recall", "remember", "consolidate", "extract patterns", "what have I learned"
---

# Athena Memory Core Skill

Access the foundation layer of Athena's memory system. Query what you know, store new facts,
trigger pattern extraction, and manage memory consolidation.

## What This Skill Does

- **Recall**: Search across all memory layers (semantic, episodic, procedural)
- **Remember**: Store new facts, insights, and learnings
- **Consolidate**: Trigger consolidation to extract new patterns and compress memory
- **Patterns**: List patterns Athena has learned from your actions

## When to Use

- **"Recall what I know about..."** - Search memory
- **"Remember this fact"** - Store a learning
- **"Consolidate memory"** - Extract patterns
- **"What patterns have I learned?"** - See discoveries

## Available Tools

### recall(query, limit)
Search across all memory for matching items.

**Parameters:**
- `query` (string): What to search for
- `limit` (number): Max results (default: 10)

**Returns:**
- Matching memories ranked by relevance
- Metadata about each match

### remember(content, tags)
Store new fact, insight, or learning in memory.

**Parameters:**
- `content` (string): What to remember
- `tags` (array): Optional labels ["learning", "insight", etc]

**Returns:**
- Confirmation of storage
- Memory ID for future reference

### consolidate()
Trigger consolidation to extract patterns from recent memory.

**Returns:**
- Consolidation status
- Number of patterns extracted
- Learning summary

### getPatterns(limit)
List patterns Athena has discovered.

**Parameters:**
- `limit` (number): Max patterns (default: 10)

**Returns:**
- List of learned patterns
- Confidence and frequency for each

## Examples

### Example 1: Recall Something

**You ask:**
> "Recall what I know about authentication systems"

**Claude Code:**
1. Loads athena-memory-core skill
2. Discovers recall() tool
3. Calls Athena API: `recall("authentication systems", 10)`
4. Filters top 3 results locally
5. Returns summary

**You get:**
```
Found 5 memories about authentication systems:
1. JWT tokens are stateless and verified via signatures
2. OAuth2 is used for third-party authorization
3. Multi-factor authentication improves security
```

### Example 2: Store New Learning

**You ask:**
> "Remember that GraphQL subscriptions enable real-time data updates"

**Claude Code:**
1. Calls `remember("GraphQL subscriptions enable real-time data", ["GraphQL", "real-time"])`
2. Returns confirmation

**You get:**
```
✓ Stored: "GraphQL subscriptions enable real-time data updates"
  Tags: GraphQL, real-time
  ID: mem_12345
```

### Example 3: Extract Patterns

**You ask:**
> "Consolidate memory and show me what patterns you've learned"

**Claude Code:**
1. Calls `consolidate()`
2. Waits for pattern extraction
3. Calls `getPatterns(10)`
4. Returns discovered patterns

**You get:**
```
Consolidation complete. Discovered patterns:
1. You use Bash (8 times) for file operations
2. You read code before editing (5 times)
3. You test after implementation (7 times)
```

## Architecture

This skill integrates with Athena's Layer 0 and Layer 7:
- Layer 0: Core memory operations (recall, remember)
- Layer 7: Consolidation & pattern extraction

Tools use the shared HTTP client to call Athena API endpoints:
- `/api/memory/recall` - Search memories
- `/api/memory/remember` - Store learning
- `/api/memory/consolidation` - Trigger consolidation
- `/api/consolidation/patterns` - Get learned patterns

## Data Flow

```
Your question
    ↓
Claude Code recognizes triggers
    ↓
Loads SKILL.md
    ↓
Discovers tools
    ↓
Generates TypeScript code
    ↓
Imports HTTP client from athena-shared
    ↓
Calls Athena API endpoints
    ↓
Real PostgreSQL memory queried
    ↓
Results filtered locally
    ↓
Summary returned (≤300 tokens)
    ↓
Your answer
```
