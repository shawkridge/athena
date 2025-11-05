---
description: Selectively delete low-value memories by ID or pattern
allowed-tools: mcp__memory__forget, mcp__memory__list_memories, mcp__memory__optimize
group: memory-management
---

# /memory-forget - Selective Memory Deletion

## Overview

Delete specific low-value memories to keep your memory system clean and focused. Use patterns to remove categories of memories at once. Includes safety checks to prevent accidental deletion of important information.

## Usage

```
/memory-forget <memory_id|pattern> [--confirm] [--dry-run] [--force]
```

## Commands

### Delete by Memory ID
```
/memory-forget 123
```

Delete single memory by ID. Requests confirmation unless `--confirm` flag used.

**Example:**
```
/memory-forget 456 --confirm

Deleted memory #456: "Failed approach to feature X"
Space freed: 2.4 KB
Remaining memories: 1,247
```

### Delete by Pattern
```
/memory-forget "old debugging notes" --dry-run
```

Delete all memories matching pattern. Use `--dry-run` to preview before deletion.

**Example:**
```
/memory-forget "temporary workaround" --dry-run

Would delete 7 memories matching pattern "temporary workaround":
  - #234: "Temporary workaround for bug X" (2h ago)
  - #567: "Workaround: API timeout issue" (1d ago)
  - #789: "Temporary fix for formatting" (3d ago)
  ...

Total would free: 12.3 KB

Confirm deletion with: /memory-forget "temporary workaround" --confirm
```

### Delete with Confirmation
```
/memory-forget 789 --confirm
```

Skip confirmation prompt (use for scripting).

### Force Delete
```
/memory-forget 890 --force
```

Force delete even if memory appears important. Use cautiously.

### Safe Deletion (Default)
```
/memory-forget 123
```

Shows memory content and asks for confirmation:

```
Memory to delete:
  ID: 123
  Type: Decision
  Content: "Decided to use approach X instead of Y"
  Created: 2025-10-20 14:30
  Last accessed: 2025-10-23 10:15
  Importance score: 0.42 (Low)
  Uniqueness: Referenced nowhere

⚠️  Confirm deletion (Y/n)?
```

## Deletion Scenarios

### Low-Value Removal
```
/memory-forget "debugging attempts" --dry-run
```

Preview memories to delete:
- Encoding rate <0.5
- Never retrieved
- Superseded by better memories
- Personal notes that are stale

### Cleanup Campaign
```
/memory-forget pattern --cleanup-old
```

Remove old memories:
- Created >90 days ago
- Never accessed in 30+ days
- Usefulness <0.3

### Domain Cleanup
```
/memory-forget domain:"old_project_name" --dry-run
```

Remove all memories from a domain/project.

## Safety Features

### 1. Importance Scoring
System prevents deletion of high-importance memories:
- **Importance 0.8+:** Requires `--force`
- **Importance 0.5-0.8:** Requires `--confirm`
- **Importance <0.5:** Deletes directly

### 2. Reference Checking
Warns if memory is referenced by other memories:
```
⚠️  This memory is referenced by 3 other memories:
  - #456 depends on this
  - #789 uses this concept
  - #321 contradicts this

Delete anyway? (Y/n):
```

### 3. Dry Run
Preview deletions before committing:
```
/memory-forget <pattern> --dry-run
```

### 4. Consolidation Preservation
Doesn't delete memories that were just consolidated. Waits 24h.

## Examples

### Clean Up Failed Experiments
```
/memory-forget "failed approach" --dry-run

Would delete 5 memories:
  - #100: "Failed attempt 1"
  - #101: "Failed attempt 2"
  - #102: "Failed attempt 3"
  - #103: "Mistake: didn't check constraints"
  - #104: "Debugging dead end"

Total space: 3.2 KB

/memory-forget "failed approach" --confirm
```

### Remove Outdated Decisions
```
/memory-forget type:decision created:before:"2025-09-01" --dry-run

Would delete 23 old decisions:
  - #500: "Decided on approach X (now using Y)"
  - #501: "Considered using library A (using B instead)"
  ...

/memory-forget type:decision created:before:"2025-09-01" --confirm
```

### Clear Project After Completion
```
/memory-forget project:"completed_project" --dry-run

Would delete 47 project-specific memories:
  - Task notes (12)
  - Debugging info (15)
  - Experimental approaches (8)
  - Design decisions (12)

Total space: 18.7 KB

/memory-forget project:"completed_project" --confirm
```

### Delete Duplicate Information
```
/memory-forget "superseded by memory #999" --dry-run

Would delete 3 memories that have been superseded:
  - #100: Old version of #999
  - #101: Outdated analysis
  - #102: Earlier draft

/memory-forget "superseded by memory #999" --confirm
```

## Best Practices

### 1. Use Dry Run First
Always preview before deleting:
```
/memory-forget <pattern> --dry-run
```

### 2. Delete in Batches
Rather than individual IDs, use patterns:
```
# Good: Delete category
/memory-forget "failed experiment" --confirm

# Avoid: Delete one by one
/memory-forget 123 --confirm
/memory-forget 124 --confirm
```

### 3. Archive Instead of Delete
For important memories you want to keep but deprioritize:
```
/focus --inhibit "old_project_name" --duration 30d
```
(This suppresses retrieval rather than deleting)

### 4. Review After Deletion
Check memory count periodically:
```
/memory-health --summary
```

### 5. Document Why You're Deleting
Add note before deletion:
```
# In your context:
# Cleaning up: Experiments from Project X (completed, moved to archive)

/memory-forget project:"project_x" experiment:true --confirm
```

## Related Commands

- `/memory-health` - See overall memory status
- `/consolidate` - Identify low-value memories to delete
- `/focus` - Suppress memories without deleting
- `/memory-query` - Search before deleting

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Delete by ID | <10ms | Single item, instant |
| Delete by pattern | 500-2000ms | Depends on pattern matching |
| Safety checks | 50-500ms | Reference checking, importance scoring |
| Dry run | 100-1000ms | Preview without deletion |

## Notes

- Deletions are immediate and permanent
- Use `--dry-run` to preview
- High-importance memories require `--force`
- Referenced memories show warnings
- Consider using `/focus` instead of deleting important context

## See Also

- **Selective Forgetting:** Cognitive science concept (Anderson & Levy)
- **Memory Consolidation:** Jung & McNaughton on systems consolidation
- **Importance Weighting:** Cognitive relevance theory
