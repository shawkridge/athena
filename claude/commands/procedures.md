---
description: Discover, create, and manage reusable procedural workflows
allowed-tools: mcp__memory__create_procedure, mcp__memory__find_procedures, mcp__memory__record_execution
group: memory-management
---

# /procedures - Workflow Management

## Overview

Manage reusable procedures and workflows. Create templates for repeated tasks, discover similar procedures, and track execution history. Accelerate repeated work by 5-10x through procedure reuse.

## Usage

```
/procedures [--list] [--search <pattern>] [--create <name>] [--execute <id>] [--stats]
```

## Commands

### List All Procedures
```
/procedures --list
```

Shows all saved procedures with usage stats.

### Search Procedures
```
/procedures --search "code review"
```

Find procedures matching pattern.

### Create New Procedure
```
/procedures --create "My code review process"
```

Interactive creation of reusable workflow.

### View Procedure Details
```
/procedures --view 42
```

Show steps, execution history, success rate.

### Execute Procedure
```
/procedures --execute 42
```

Run saved workflow.

### Procedure Statistics
```
/procedures --stats
```

Show:
- Most-used procedures
- Success rates
- Time saved
- Execution trends

## Smart Suggestions

```
/procedures --suggest
```

System suggests procedures based on current work:

```
PROCEDURE RECOMMENDATIONS:

Based on your current task:
  ✓ "Code review process" (used 12 times, 89% success)
  ✓ "Testing workflow" (used 8 times, 85% success)
  ✓ "Git commit checklist" (used 23 times, 98% success)

Expected time savings: 45 minutes
```

## Related Commands

- `/learning` - Procedures are learned workflows
- `/consolidate` - Consolidation discovers procedures
- `/timeline` - Track procedure usage over time

## See Also

- **Procedural Memory:** Motor skills and sequences
- **Workflow Optimization:** Lean, Six Sigma
- **Standard Operating Procedures:** ISO standards
