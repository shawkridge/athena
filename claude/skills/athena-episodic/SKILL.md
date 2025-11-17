---
name: athena-episodic
description: >
  Query episodic memory: list events, search history, build timelines, understand what happened when.
  See your complete event history with rich temporal context.

  Use when: "what happened", "show history", "timeline", "when did", "search events", "list events"
---

# Athena Episodic Memory Skill

Access your complete event history. See what happened when, build timelines, and understand execution patterns.

## What This Skill Does

- **List Events**: Get recent episodic events
- **Search Events**: Find specific events by content
- **Build Timeline**: See chronological view of what happened
- **Understand Context**: See importance, files changed, tasks completed

## When to Use

- **"What happened yesterday?"** - List events
- **"When did I work on the API?"** - Search timeline
- **"Show me what I did"** - Get event history
- **"Build a timeline of my work"** - Temporal view

## Available Tools

### listEvents(limit, offset)
Get recent episodic events.

**Parameters:**
- `limit` (number): Events to return (default: 50)
- `offset` (number): Pagination offset (default: 0)

**Returns:**
- Recent events with timestamps
- Importance scores
- Context information

### searchEvents(query, limit)
Search events by content or description.

**Parameters:**
- `query` (string): What to search for
- `limit` (number): Max results (default: 10)

**Returns:**
- Matching events ranked by relevance
- Context for each match

### getTimeline(projectId)
Get chronological timeline of events.

**Parameters:**
- `projectId` (number, optional): Filter by project

**Returns:**
- Events ordered by timestamp
- Temporal relationships

### getEventStats()
Get statistics about episodic memory.

**Returns:**
- Total event count
- Events by type distribution
- Time range covered

## Examples

### Example 1: What Happened Today?

**You ask:**
> "What happened today?"

**Claude Code:**
1. Calls `listEvents(50)`
2. Filters for today only
3. Returns summary

**You get:**
```
15 events recorded today:
- 8 Bash executions (shell commands)
- 4 Read operations (examining code)
- 3 Edit operations (making changes)

Top events: mkdir projects, Read auth.ts, Edit login.ts
```

### Example 2: When Did I Work on Feature X?

**You ask:**
> "When did I work on the authentication feature?"

**Claude Code:**
1. Calls `searchEvents("authentication", 10)`
2. Filters locally
3. Returns timeline

**You get:**
```
Found 5 events about authentication:
1. 2025-11-16 14:22 - Edit auth middleware
2. 2025-11-16 13:45 - Read JWT implementation
3. 2025-11-16 13:20 - Created login test
```

## Architecture

This skill integrates with Athena's Layer 1 (Episodic Memory):
- Stores 8,128+ events with temporal context
- Tracks tools used, files changed, outcomes

Tools use shared HTTP client to call:
- `/api/episodic/events` - List events
- `/api/episodic/search` - Search events
- `/api/episodic/timeline` - Build timelines
- `/api/episodic/stats` - Get statistics
